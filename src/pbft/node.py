# src/pbft/node.py
"""Simplified PBFT validator (T28 spec § 7, T29 spec § 6-7).

T28 shipped the pre-prepare phase: the primary drains a stub workload,
broadcasts PRE-PREPARE, locally self-transitions; recipients validate
against five rules and reach PRE_PREPARED.

T29 wires the full classical protocol:
  - PREPARE / COMMIT voting on a uniform 2f+1 quorum (Decision B — every
    replica including the primary votes and self-records);
  - commit / finalization (the `decided` event, once per seq — Decision G);
  - the VIEW-CHANGE -> NEW-VIEW recovery path, driven by a per-instance
    view-change timer with per-view exponential backoff (Decision F).
"""
from __future__ import annotations

from typing import Any

from nodes import Message, Node

from .digest import digest
from .instance import Instance, InstanceState
from .messages import (
    CommitPayload,
    NewViewPayload,
    PreparePayload,
    PrePreparePayload,
    ViewChangePayload,
)
from .viewchange import collect_evidence, compute_reissue


PBFT_REJECTED = "pbft_rejected"            # T28
PBFT_PRE_PREPARED = "pbft_pre_prepared"    # T28
PBFT_PREPARED = "pbft_prepared"            # T29 — instance reached PREPARED
PBFT_COMMITTED = "pbft_committed"          # T29 — instance reached COMMITTED
PBFT_VIEW_CHANGE = "pbft_view_change"      # T29 — one per view-change initiated
PBFT_NEW_VIEW = "pbft_new_view"            # T29 — emitted inside _enter_new_view


class PBFTNode(Node):
    """Classical PBFT validator restricted to the pre-prepare phase.

    Constructor parameters (keyword-only past super().__init__'s positional
    set; see spec § 7.1):
      n:             validator count (drives the v mod n primary rule and,
                     in T29, the 2f+1 quorum threshold).
      workload:      stub list[bytes] copied at construction; the primary
                     pops one item per propose timer fire (spec § 2 / Dec B).
      propose_delay: time between consecutive PRE-PREPARE emissions
                     (spec § 2 / Dec C).
      initial_view:  starting view; tests use 0. T29 may construct nodes in
                     a non-zero view to exercise view-change.
      vc_delay:      base view-change timer delay; the per-instance timer
                     fires after vc_delay·2^view (spec § 7.1 / Decision F).
    """

    def __init__(self, node_id: int, weight: float, endpoint: object,
                 global_seed: int, *,
                 n: int,
                 workload: list[bytes] | None = None,
                 propose_delay: float = 1.0,
                 initial_view: int = 0,
                 vc_delay: float = 10.0) -> None:
        super().__init__(node_id, weight, endpoint, global_seed)
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        if not 0 <= node_id < n:
            raise ValueError(
                f"node_id {node_id} outside [0, {n})")
        if propose_delay <= 0:
            raise ValueError(
                f"propose_delay must be positive, got {propose_delay}")
        if vc_delay <= 0:
            raise ValueError(f"vc_delay must be positive, got {vc_delay}")
        self.n: int = n
        self.f: int = (n - 1) // 3
        self.view: int = initial_view
        self.view_changing: bool = False
        self.workload: list[bytes] = list(workload or [])
        self.propose_delay: float = propose_delay
        self.vc_delay: float = vc_delay
        self.next_seq: int = 0
        self.inst: dict[tuple[int, int], Instance] = {}
        # View-change cross-instance state (node-model.md § 4, spec § 6.1).
        self._target_view: int = initial_view
        self._view_changes: dict[int, dict[int, ViewChangePayload]] = {}
        self._new_view_sent: set[int] = set()
        self._new_view_installed: set[int] = set()
        self._decided_seqs: set[int] = set()

    # --- Lifecycle hooks (spec § 7.2 / § 7.3). ---

    def _on_start(self, t: float) -> None:
        if self._is_primary(self.view):
            self.set_timer("propose", self.propose_delay, None, t)

    def _on_message(self, msg: Message, t: float) -> None:
        if msg.type == "PRE-PREPARE":
            self._handle_pre_prepare(msg, t)
        elif msg.type == "PREPARE":
            self._handle_prepare(msg, t)
        elif msg.type == "COMMIT":
            self._handle_commit(msg, t)
        elif msg.type == "VIEW-CHANGE":
            self._handle_view_change(msg, t)
        elif msg.type == "NEW-VIEW":
            self._handle_new_view(msg, t)
        else:
            self.emit(PBFT_REJECTED,
                      {"reason": "unknown_type", "msg_type": msg.type,
                       "src": msg.src}, t)

    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        if timer_id == "propose":
            self._propose(t)
        elif isinstance(timer_id, tuple) and timer_id[0] == "view_change":
            self._on_view_change_timeout(timer_id[1], timer_id[2], t)
        elif isinstance(timer_id, tuple) and timer_id[0] == "vc_escalate":
            self._on_escalation_timeout(timer_id[1], t)
        # else: silent no-op.

    def _propose(self, t: float) -> None:
        if self.view_changing:
            return                              # quiescent during view-change
        if not self.workload:
            return                              # drain complete; no re-arm
        if not self._is_primary(self.view):
            return                              # demoted mid-flight
        request = self.workload.pop(0)
        seq = self.next_seq
        self.next_seq += 1
        d = digest(request)
        pp = PrePreparePayload(view=self.view, seq=seq,
                               request_digest=d, request_payload=request)
        self.broadcast("PRE-PREPARE", pp, t)
        self._accept_pre_prepare(self.view, seq, d, request,
                                 src=self.id, t=t)
        self.set_timer("propose", self.propose_delay, None, t)

    # --- Recipient PRE-PREPARE pipeline (spec § 7.4 / § 7.5). ---

    def _handle_pre_prepare(self, msg: Message, t: float) -> None:
        pp = msg.payload
        # Payload-shape guard (spec § 6.2): T18 will inject malformed
        # PRE-PREPAREs; log-and-drop instead of letting AttributeError escape.
        if not isinstance(pp, PrePreparePayload):
            self._reject(t, "malformed_payload",
                         msg_type="PRE-PREPARE", src=msg.src)
            return
        # Rule 1: sender is the asserted view's primary.
        if msg.src != (pp.view % self.n):
            self._reject(t, "non_primary_sender",
                         view=pp.view, seq=pp.seq, src=msg.src)
            return
        # Rule 2: view matches recipient's current view.
        if pp.view != self.view:
            self._reject(t, "view_mismatch",
                         view=pp.view, seq=pp.seq, src=msg.src)
            return
        # Rule 3: not in the middle of a view change.
        if self.view_changing:
            self._reject(t, "view_changing",
                         view=pp.view, seq=pp.seq, src=msg.src)
            return
        # Rule 4: (view, seq) instance not already past IDLE.
        existing = self.inst.get((pp.view, pp.seq))
        if existing is not None and existing.state is not InstanceState.IDLE:
            self._reject(t, "duplicate_pre_prepare",
                         view=pp.view, seq=pp.seq, src=msg.src)
            return
        # Rule 5: digest integrity.
        if digest(pp.request_payload) != pp.request_digest:
            self._reject(t, "digest_mismatch",
                         view=pp.view, seq=pp.seq, src=msg.src)
            return

        self._accept_pre_prepare(pp.view, pp.seq, pp.request_digest,
                                 pp.request_payload, src=msg.src, t=t)

    def _accept_pre_prepare(self, view: int, seq: int, d: bytes,
                            payload: bytes, src: int, t: float) -> None:
        """Shared IDLE -> PRE_PREPARED transition seam (spec § 6.3). Caller
        (recipient validator or primary self-loop) guarantees validation has
        passed; this method is unconditional. It also starts the prepare
        phase and arms the per-instance view-change timer, so both callers
        get the voting behaviour for free."""
        inst = self.inst.setdefault((view, seq),
                                    Instance(view=view, seq=seq))
        inst.state = InstanceState.PRE_PREPARED
        inst.digest = d
        inst.request_payload = payload          # for view-change evidence
        self.emit(PBFT_PRE_PREPARED,
                  {"view": view, "seq": seq, "digest": d.hex(),
                   "src": src}, t)
        self._arm_view_change_timer(view, seq, t)
        self._broadcast_prepare(inst, t)
        self._check_prepare_quorum(inst, t)     # buffered PREPAREs may suffice

    def _reject(self, t: float, reason: str, **fields) -> None:
        self.emit(PBFT_REJECTED, {"reason": reason, **fields}, t)

    # --- Prepare phase (spec § 6.4). ---

    def _broadcast_prepare(self, inst: Instance, t: float) -> None:
        """Broadcast a PREPARE and self-record the vote (Decision B —
        Network.broadcast excludes the sender, so the self-loop is explicit)."""
        self.broadcast("PREPARE",
                       PreparePayload(inst.view, inst.seq, inst.digest), t)
        inst.prepares[self.id] = inst.digest

    def _handle_prepare(self, msg: Message, t: float) -> None:
        pp = msg.payload
        if not isinstance(pp, PreparePayload):
            self._reject(t, "malformed_payload",
                         msg_type="PREPARE", src=msg.src)
            return
        # File unconditionally by the instance's own (view, seq) key
        # (Decision C): a vote arriving before the local PRE-PREPARE is
        # counted retroactively once the digest is known.
        inst = self.inst.setdefault((pp.view, pp.seq),
                                    Instance(view=pp.view, seq=pp.seq))
        inst.prepares[msg.src] = pp.request_digest
        self._check_prepare_quorum(inst, t)

    def _check_prepare_quorum(self, inst: Instance, t: float) -> None:
        if inst.state is InstanceState.PRE_PREPARED \
                and inst.matching_prepares() >= 2 * self.f + 1:
            self._accept_prepare(inst, t)

    def _accept_prepare(self, inst: Instance, t: float) -> None:
        inst.state = InstanceState.PREPARED
        self.emit(PBFT_PREPARED,
                  {"view": inst.view, "seq": inst.seq,
                   "digest": inst.digest.hex()}, t)
        self._broadcast_commit(inst, t)
        self._check_commit_quorum(inst, t)

    # --- Commit phase (spec § 6.5). ---

    def _broadcast_commit(self, inst: Instance, t: float) -> None:
        """Broadcast a COMMIT and self-record the vote (Decision B)."""
        self.broadcast("COMMIT",
                       CommitPayload(inst.view, inst.seq, inst.digest), t)
        inst.commits[self.id] = inst.digest

    def _handle_commit(self, msg: Message, t: float) -> None:
        cp = msg.payload
        if not isinstance(cp, CommitPayload):
            self._reject(t, "malformed_payload",
                         msg_type="COMMIT", src=msg.src)
            return
        inst = self.inst.setdefault((cp.view, cp.seq),
                                    Instance(view=cp.view, seq=cp.seq))
        inst.commits[msg.src] = cp.request_digest
        self._check_commit_quorum(inst, t)

    def _check_commit_quorum(self, inst: Instance, t: float) -> None:
        if inst.state is InstanceState.PREPARED \
                and inst.matching_commits() >= 2 * self.f + 1:
            self._accept_commit(inst, t)

    def _accept_commit(self, inst: Instance, t: float) -> None:
        """PREPARED -> COMMITTED. The view-change timer is cancelled (the
        instance is resolved) and finalization is recorded. The `decided`
        and `pbft_committed` events fire only the first time a given seq
        commits (Decision G): a request reissued across a view-change
        produces two instances, but the simulator executes each seq once."""
        inst.state = InstanceState.COMMITTED
        self._cancel_view_change_timer(inst.view, inst.seq)
        if inst.seq not in self._decided_seqs:
            self._decided_seqs.add(inst.seq)
            self.emit(PBFT_COMMITTED,
                      {"view": inst.view, "seq": inst.seq,
                       "digest": inst.digest.hex()}, t)
            self._emit_decided(inst.digest.hex(), (inst.view, inst.seq), t)

    # --- Primary detection (Decision D). ---

    def _is_primary(self, view: int) -> bool:
        return self.id == (view % self.n)

    # --- View-change timer (spec § 7.1 / Decision F). ---

    def _arm_view_change_timer(self, view: int, seq: int, t: float) -> None:
        """Arm the per-instance view-change timer. Delay doubles per view
        (Decision F) so a stalled recovery terminates deterministically."""
        delay = self.vc_delay * (2 ** view)
        self.set_timer(("view_change", view, seq), delay, (view, seq), t)

    def _cancel_view_change_timer(self, view: int, seq: int) -> None:
        """Cancel the per-instance view-change timer; no-op if unknown."""
        self.cancel_timer(("view_change", view, seq))

    # --- View-change handlers (spec § 7.4 / § 7.6). ---

    def _handle_view_change(self, msg: Message, t: float) -> None:
        vc = msg.payload
        if not isinstance(vc, ViewChangePayload):
            self._reject(t, "malformed_payload",
                         msg_type="VIEW-CHANGE", src=msg.src)
            return
        self._view_changes.setdefault(vc.new_view, {})[msg.src] = vc
        seen = len(self._view_changes[vc.new_view])
        # f+1 catch-up (Decision D): a node that has not timed out itself
        # joins a view-change a fault-tolerant quorum of others already want.
        if seen >= self.f + 1 and vc.new_view > self.view \
                and (not self.view_changing
                     or vc.new_view > self._target_view):
            self._initiate_view_change(vc.new_view, t)
        self._check_new_view_quorum(vc.new_view, t)

    def _handle_new_view(self, msg: Message, t: float) -> None:
        nv = msg.payload
        if not isinstance(nv, NewViewPayload):
            self._reject(t, "malformed_payload",
                         msg_type="NEW-VIEW", src=msg.src)
            return
        if msg.src != nv.new_view % self.n:
            self._reject(t, "non_primary_sender",
                         new_view=nv.new_view, src=msg.src)
            return
        if nv.new_view <= self.view:
            self._reject(t, "stale_new_view",
                         new_view=nv.new_view, src=msg.src)
            return
        if len(nv.vc_proofs) < 2 * self.f + 1 \
                or any(p.new_view != nv.new_view for p in nv.vc_proofs):
            self._reject(t, "insufficient_proofs",
                         new_view=nv.new_view, src=msg.src)
            return
        self._enter_new_view(nv.new_view, nv.reissued, t)

    # --- View-change initiation (spec § 7.1 / § 7.2). ---

    def _on_view_change_timeout(self, view: int, seq: int, t: float) -> None:
        """Per-instance view-change timer fired. If the instance is still
        unresolved, initiate a change to the next view."""
        inst = self.inst.get((view, seq))
        if inst is None or inst.state is InstanceState.COMMITTED:
            return                              # already resolved
        self._initiate_view_change(view + 1, t)

    def _initiate_view_change(self, new_view: int, t: float) -> None:
        """Broadcast a VIEW-CHANGE toward `new_view`. Idempotent: a repeat
        for the same or a lower target view is a no-op."""
        if new_view <= self.view:
            return                              # already at/past it
        if self.view_changing and new_view <= self._target_view:
            return                              # already changing to >= this
        self.view_changing = True
        self._target_view = new_view
        self.emit(PBFT_VIEW_CHANGE,
                  {"from_view": self.view, "new_view": new_view}, t)
        evidence = collect_evidence(self.inst)
        payload = ViewChangePayload(new_view=new_view, last_stable_seq=-1,
                                    prepared=evidence)
        self.broadcast("VIEW-CHANGE", payload, t)
        self._view_changes.setdefault(new_view, {})[self.id] = payload
        self._arm_escalation_timer(new_view, t)
        self._check_new_view_quorum(new_view, t)  # this node may be primary

    def _arm_escalation_timer(self, new_view: int, t: float) -> None:
        """Arm the escalation timer (spec § 7.3): if no NEW-VIEW for
        `new_view` arrives in time, the node escalates to the next view.
        Without escalation a lost NEW-VIEW would stall recovery forever."""
        delay = self.vc_delay * (2 ** new_view)
        self.set_timer(("vc_escalate", new_view), delay, new_view, t)

    def _on_escalation_timeout(self, new_view: int, t: float) -> None:
        if new_view in self._new_view_installed \
                or new_view < self._target_view:
            return                              # NEW-VIEW arrived / escalated
        self._initiate_view_change(new_view + 1, t)

    # --- NEW-VIEW issuance and view entry (spec § 7.5 / § 7.7). ---

    def _check_new_view_quorum(self, new_view: int, t: float) -> None:
        """The prospective primary of `new_view`, on collecting 2f+1
        VIEW-CHANGEs for it, issues a NEW-VIEW reissuing every
        prepared-but-uncommitted instance and self-enters the view."""
        if not self._is_primary(new_view):
            return
        if new_view in self._new_view_sent:
            return
        proofs_by_src = self._view_changes.get(new_view, {})
        if len(proofs_by_src) < 2 * self.f + 1:
            return
        # Pick 2f+1 proofs by sorted src so the NEW-VIEW is deterministic.
        chosen = [proofs_by_src[s]
                  for s in sorted(proofs_by_src)][:2 * self.f + 1]
        reissued = compute_reissue(chosen, new_view)
        self._new_view_sent.add(new_view)
        self.broadcast("NEW-VIEW",
                       NewViewPayload(new_view, chosen, reissued), t)
        # broadcast excludes the sender — the primary installs locally.
        self._enter_new_view(new_view, reissued, t)

    def _enter_new_view(self, new_view: int,
                        reissued: list[PrePreparePayload], t: float) -> None:
        """Adopt `new_view`: clear the view-change flag, cancel the
        escalation timer, install each reissued instance, and (if primary)
        resume proposing."""
        if new_view in self._new_view_installed:
            return
        self._new_view_installed.add(new_view)
        self.view = new_view
        self._target_view = new_view
        self.view_changing = False
        self.cancel_timer(("vc_escalate", new_view))
        self.emit(PBFT_NEW_VIEW,
                  {"new_view": new_view, "n_reissued": len(reissued)}, t)
        for pp in reissued:
            if digest(pp.request_payload) != pp.request_digest:
                self._reject(t, "digest_mismatch", view=pp.view,
                             seq=pp.seq, src=new_view % self.n)
                continue
            self._accept_pre_prepare(pp.view, pp.seq, pp.request_digest,
                                     pp.request_payload,
                                     src=new_view % self.n, t=t)
        if self._is_primary(new_view):
            reissued_max = max((pp.seq for pp in reissued), default=-1)
            self.next_seq = max(self.next_seq, reissued_max + 1)
            if self.workload:
                self.set_timer("propose", self.propose_delay, None, t)
