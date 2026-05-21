# src/pbft/node.py
"""Simplified PBFT validator (T28 spec § 7).

T28 ships the pre-prepare phase: the primary drains a stub workload,
broadcasts PRE-PREPARE, locally self-transitions; recipients validate
against five rules and reach PRE_PREPARED. PREPARE / COMMIT /
VIEW-CHANGE / NEW-VIEW are silently no-op'd (skeleton cut, Decision A);
T29 wires them.
"""
from __future__ import annotations

from typing import Any

from nodes import Message, Node

from .digest import digest
from .instance import Instance, InstanceState
from .messages import PrePreparePayload


PBFT_REJECTED = "pbft_rejected"
PBFT_PRE_PREPARED = "pbft_pre_prepared"


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
    """

    def __init__(self, node_id: int, weight: float, endpoint: object,
                 global_seed: int, *,
                 n: int,
                 workload: list[bytes] | None = None,
                 propose_delay: float = 1.0,
                 initial_view: int = 0) -> None:
        super().__init__(node_id, weight, endpoint, global_seed)
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        if not 0 <= node_id < n:
            raise ValueError(
                f"node_id {node_id} outside [0, {n})")
        if propose_delay <= 0:
            raise ValueError(
                f"propose_delay must be positive, got {propose_delay}")
        self.n: int = n
        self.f: int = (n - 1) // 3
        self.view: int = initial_view
        self.view_changing: bool = False
        self.workload: list[bytes] = list(workload or [])
        self.propose_delay: float = propose_delay
        self.next_seq: int = 0
        self.inst: dict[tuple[int, int], Instance] = {}

    # --- Lifecycle hooks (spec § 7.2 / § 7.3). ---

    def _on_start(self, t: float) -> None:
        if self._is_primary(self.view):
            self.set_timer("propose", self.propose_delay, None, t)

    def _on_message(self, msg: Message, t: float) -> None:
        if msg.type == "PRE-PREPARE":
            self._handle_pre_prepare(msg, t)
        elif msg.type in ("PREPARE", "COMMIT", "VIEW-CHANGE", "NEW-VIEW"):
            return                              # T29 wires these
        else:
            self.emit(PBFT_REJECTED,
                      {"reason": "unknown_type", "msg_type": msg.type,
                       "src": msg.src}, t)

    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        if timer_id == "propose":
            self._propose(t)
        # else: silent no-op. T29 owns ("view_change", instance_key).

    def _propose(self, t: float) -> None:
        if not self.workload:
            return                              # drain complete; no re-arm
        if not self._is_primary(self.view):
            return                              # demoted mid-flight (T29)
        request = self.workload.pop(0)
        seq = self.next_seq
        self.next_seq += 1
        d = digest(request)
        pp = PrePreparePayload(view=self.view, seq=seq,
                               request_digest=d, request_payload=request)
        self.broadcast("PRE-PREPARE", pp, t)
        self._accept_pre_prepare(self.view, seq, d, src=self.id, t=t)
        self.set_timer("propose", self.propose_delay, None, t)

    # --- Recipient PRE-PREPARE pipeline (spec § 7.4 / § 7.5). ---

    def _handle_pre_prepare(self, msg: Message, t: float) -> None:
        pp: PrePreparePayload = msg.payload
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
                                 src=msg.src, t=t)

    def _accept_pre_prepare(self, view: int, seq: int, d: bytes,
                            src: int, t: float) -> None:
        """Shared IDLE -> PRE_PREPARED transition. Caller (recipient
        validator or primary self-loop) guarantees validation has
        passed; this method is unconditional."""
        inst = self.inst.setdefault((view, seq),
                                    Instance(view=view, seq=seq))
        inst.state = InstanceState.PRE_PREPARED
        inst.digest = d
        self.emit(PBFT_PRE_PREPARED,
                  {"view": view, "seq": seq, "digest": d.hex(),
                   "src": src}, t)

    def _reject(self, t: float, reason: str, **fields) -> None:
        self.emit(PBFT_REJECTED, {"reason": reason, **fields}, t)

    # --- Primary detection (Decision D). ---

    def _is_primary(self, view: int) -> bool:
        return self.id == (view % self.n)
