# T29 — PBFT voting, commit/finalization, and view-change: design spec

Engineer-register design spec for T29, consumed by `superpowers:writing-plans`.
Extends the **pre-prepare phase** shipped by T28 into the **full classical
PBFT protocol**: the `PREPARE` and `COMMIT` voting phases, commit /
finalization, and the `VIEW-CHANGE` → `NEW-VIEW` recovery path.

- **Task:** T29 (`TASKS.md`, Week 5) — Implement PBFT voting and
  commit/finalization. Role: Engineer. Artifact: `src/pbft/`.
- **Scope decision:** the human chose **full view-change recovery**
  (2026-05-21), superseding the original `TASKS.md` "view change stub"
  wording and reconciling with `wiki/concepts/system-design-protocols.md`
  §6 ("T29 implements the full recovery path"). `TASKS.md` T29 amended to
  match.
- **Design contracts:** `wiki/algorithms/pbft.md`,
  `wiki/concepts/message-types.md` §3, `wiki/concepts/system-design-protocols.md`
  §2, `wiki/concepts/node-model.md` §4.
- **Builds on:** T28 (`docs/superpowers/specs/2026-05-21-t28-pbft-proposal-design.md`,
  `src/pbft/`).

## 1. Scope

T29 grows `PBFTNode` from a pre-prepare-only skeleton into the complete
classical PBFT validator. Concretely:

1. **Prepare phase.** On reaching `PRE_PREPARED`, a replica broadcasts a
   `PREPARE`, collects `PREPARE`s into the per-instance quorum dict, and
   transitions `PRE_PREPARED → PREPARED` on `2f+1` matching.
2. **Commit phase.** On reaching `PREPARED`, a replica broadcasts a
   `COMMIT`, collects `COMMIT`s, transitions `PREPARED → COMMITTED` on
   `2f+1` matching, and emits the `decided` event — finalization in the
   simulator.
3. **View-change.** A per-instance view-change timer is armed when an
   instance reaches `PRE_PREPARED` and cancelled on `COMMITTED`. If it
   fires, the replica initiates a `VIEW-CHANGE`; the new primary collects
   `2f+1` `VIEW-CHANGE`s and broadcasts a `NEW-VIEW` that reissues
   prepared-but-not-committed instances; replicas enter the new view and
   resume the three-phase commit.

Explicit non-goals (deferred to other tasks):

- Signature simulation, spoofed-`src` adversary surface, malformed-message
  injection at experiment scale — T18.
- Workload from a real mempool / the experiment-harness workload loader —
  T19 / T27 / T39.
- The unified `run()` interface and CSV output — T39 / T40.
- The honest-node correctness sweep (n = 4 / 7 / 10, latency logged) — T30.
- PBFT unit-test battery beyond what T29 ships for its own verification —
  T31.
- Adaptive / exponential-backoff timeout *as a tunable enhancement* — T57.
  T29 ships a fixed per-view doubling (§2 Decision F) because view-change
  recovery cannot terminate deterministically without it; T57 refines the
  policy.

## 2. Settled design decisions

Decisions taken with the human during brainstorming, before this spec was
written.

- **Decision A — Skeleton-cut continuation.** T28 declared the full
  four-state `Instance` FSM (`IDLE`, `PRE_PREPARED`, `PREPARED`,
  `COMMITTED`) and reserved the `prepares` / `commits` quorum dicts. T29
  fills in the transitions and handlers; it adds **one** `Instance` field
  (`request_payload`, §5) and grows `node.py` plus one new module
  (`viewchange.py`). No structural rework of T28 code: the propose path
  and the five-rule `PRE-PREPARE` validator are unchanged; the
  `_accept_pre_prepare` transition seam is *extended*, not rewritten.

- **Decision B — Uniform quorum model.** Every replica, *including the
  primary*, broadcasts a `PREPARE` on reaching `PRE_PREPARED` and a
  `COMMIT` on reaching `PREPARED`, and records its own vote via an
  explicit self-loop (`Network.broadcast` excludes the sender — the same
  fact that forced T28's pre-prepare self-loop). A replica is *prepared*
  at `2f+1` matching `PREPARE`s (its own + `2f` others) and *committed* at
  `2f+1` matching `COMMIT`s. Rationale: a single uniform quorum predicate
  `count_matching ≥ 2f+1` for both phases; extends T28's self-loop seam
  without special-casing the primary; matches the
  `system-design-protocols.md` §2 sketch (`add_prepare(msg) ≥ 2f+1`). Cost
  vs. textbook PBFT (primary sends no `PREPARE`): one extra message per
  instance — negligible, both are `O(n²)`. The `2f+1` quorum and the
  quorum-intersection safety argument (`wiki/algorithms/pbft.md` §Safety)
  are unchanged.

- **Decision C — Out-of-order tolerance.** The network gives no ordering
  guarantee (`wiki/concepts/network-model.md`); a `PREPARE` or `COMMIT`
  can arrive before the local `PRE-PREPARE`. Every well-formed `PREPARE` /
  `COMMIT` is filed into the (lazily created) `Instance`'s quorum dict
  regardless of the instance's current state; the quorum transition is
  re-checked both on each filed vote *and* when the `PRE-PREPARE` lands. A
  vote counts only if its `request_digest` equals the instance's
  pre-prepared `digest`, so a vote filed before the digest is known, and
  any minority-digest (equivocating) vote, self-excludes.

- **Decision D — Faithful, simplified view-change.** Full classical
  `VIEW-CHANGE` / `NEW-VIEW` with the thesis's standing simplifications:
  no signatures (T18's surface) and **no checkpoint protocol**.
  Consequently `last_stable_seq` is a vestigial payload field fixed at
  `-1`, and `VIEW-CHANGE` evidence is *every* instance the replica has at
  state ≥ `PREPARED`, uncapped. (`message-types.md` §9 anticipates this:
  "T29 may need a stricter cap" — T29 deliberately uses none; recorded as
  a `## Revisions` note.) Rejected: a "lite" variant skipping the
  `NEW-VIEW` reissue — it can silently drop a request prepared in the old
  view, a real safety regression.

- **Decision E — Self-contained view-change evidence.** `VIEW-CHANGE`
  evidence carries the **request payload**, not just the digest:
  `prepared` becomes `list[(view, seq, request_digest, request_payload)]`
  (T28 declared a 3-tuple). This lets the new primary reissue a valid
  `PRE-PREPARE` (which must satisfy the digest-integrity rule) even for an
  instance it never personally prepared. `Instance` gains a
  `request_payload` field (§5) so a replica can cite its own prepared
  instances as evidence. Divergence from `message-types.md` §3 (3-tuple)
  → `## Revisions` entry on that page.

- **Decision F — Per-view exponential timer backoff.** The view-change
  timer delay is `vc_delay · 2^view`. Doubling per view is classical PBFT
  (Castro–Liskov) and it makes view-change recovery *deterministically
  terminating*: a delay regime under which view `v`'s timer fires before
  the commit quorum forms will, two views later, have a timer long enough
  to let the commit complete. Without backoff a stalled run view-changes
  forever. T57 (adaptive timeout) later refines the policy; T29 ships the
  fixed doubling because the recovery path cannot be demonstrated without
  it.

- **Decision G — `decided` is emitted once per sequence number.** A
  request prepared in view `v` and reissued in view `v+1` produces two
  `Instance`s — `(v, seq)` and `(v+1, seq)` — either of which may reach
  `COMMITTED`. The FSM transition runs for both, but the mandatory
  `decided` event (and the protocol-level `pbft_committed`) is emitted
  only the first time a given `seq` commits, tracked in a per-node
  `_decided_seqs` set. This is the simulator analogue of PBFT's
  "execute each request once" rule and keeps finality-count metrics
  (T40) honest.

## 3. Module layout — `src/pbft/`

| File | T29 change | Approx LoC after |
| :-- | :-- | :-- |
| `__init__.py` | Export the new event constants and `viewchange.py` helpers. | ~30 |
| `messages.py` | `ViewChangePayload.prepared` 3-tuple → 4-tuple (Decision E). No new classes — T28 declared all five payloads. | ~55 |
| `instance.py` | Add `request_payload` field; add `matching_prepares()` / `matching_commits()` count helpers. | ~55 |
| `digest.py` | Unchanged. | ~12 |
| `viewchange.py` | **New.** Pure functions: `collect_evidence`, `compute_reissue`. No `PBFTNode` dependency — operate on plain data. | ~50 |
| `node.py` | Grows: `PREPARE` / `COMMIT` / `VIEW-CHANGE` / `NEW-VIEW` handlers, `_accept_prepare` / `_accept_commit`, quorum checks, view-change timer + initiation + escalation, `_enter_new_view`. | ~330 |

Tests:

- `tests/pbft/test_messages.py`, `test_instance.py` — extended for the
  new field / helpers.
- `tests/pbft/test_node_voting.py` — **new**; prepare/commit phase units.
- `tests/pbft/test_node_viewchange.py` — **new**; view-change units.
- `tests/pbft/test_viewchange.py` — **new**; the pure `viewchange.py`
  helpers.
- `tests/integration/test_pbft_consensus.py` — **new**; two e2e scenarios.

Experiment page: `wiki/experiments/2026-05-21_pbft-consensus-baseline.md`.

## 4. `messages.py`

Only one change: `ViewChangePayload.prepared` carries the request payload
(Decision E).

```python
@dataclass(frozen=True)
class ViewChangePayload:
    new_view: int
    last_stable_seq: int                                  # fixed -1 in T29 (Decision D)
    prepared: list[tuple[int, int, bytes, bytes]] = field(default_factory=list)
    # each tuple: (view, seq, request_digest, request_payload)
```

`PreparePayload`, `CommitPayload`, `NewViewPayload`, `PrePreparePayload`
are unchanged from T28. `NewViewPayload.reissued` is a
`list[PrePreparePayload]`; each reissued `PrePreparePayload` carries its
`request_payload`, so a `NEW-VIEW` recipient can install the instance and
satisfy the digest rule.

## 5. `instance.py`

```python
@dataclass
class Instance:
    view: int
    seq: int
    state: InstanceState = InstanceState.IDLE
    digest: Optional[bytes] = None
    request_payload: Optional[bytes] = None               # NEW (T29) — for view-change evidence
    prepares: dict[int, bytes] = field(default_factory=dict)   # src -> asserted digest
    commits: dict[int, bytes] = field(default_factory=dict)    # src -> asserted digest

    def matching_prepares(self) -> int:
        """Count PREPAREs whose asserted digest matches this instance's
        pre-prepared digest. Zero while digest is None (Decision C)."""
        if self.digest is None:
            return 0
        return sum(1 for d in self.prepares.values() if d == self.digest)

    def matching_commits(self) -> int:
        if self.digest is None:
            return 0
        return sum(1 for d in self.commits.values() if d == self.digest)
```

`InstanceState` is unchanged (T28 already declared all four members).
`request_payload` is set by `_accept_pre_prepare` (§6.3).

## 6. `node.py` — three-phase commit

### 6.1 Constructor

`PBFTNode.__init__` gains one keyword-only parameter and cross-instance
view-change state:

```python
def __init__(self, node_id, weight, endpoint, global_seed, *,
             n, workload=None, propose_delay=1.0, initial_view=0,
             vc_delay: float = 10.0) -> None:
    super().__init__(...)            # unchanged T28 validation
    if vc_delay <= 0:
        raise ValueError(f"vc_delay must be positive, got {vc_delay}")
    # ... T28 fields unchanged ...
    self.vc_delay: float = vc_delay
    # view-change cross-instance state (node-model.md §4):
    self._target_view: int = initial_view                 # view this node is changing toward
    self._view_changes: dict[int, dict[int, ViewChangePayload]] = {}  # new_view -> {src -> payload}
    self._new_view_sent: set[int] = set()                 # new_view values this node (as primary) issued NEW-VIEW for
    self._new_view_installed: set[int] = set()            # new_view values this node has entered
    self._decided_seqs: set[int] = set()                  # seqs that have emitted `decided` (Decision G)
```

`vc_delay` default `10.0` is generous — an honest, low-delay run never
spuriously view-changes. The e2e recovery scenario (§10.2) overrides it.

### 6.2 Inbound dispatch

```python
def _on_message(self, msg, t):
    if   msg.type == "PRE-PREPARE": self._handle_pre_prepare(msg, t)
    elif msg.type == "PREPARE":     self._handle_prepare(msg, t)
    elif msg.type == "COMMIT":      self._handle_commit(msg, t)
    elif msg.type == "VIEW-CHANGE": self._handle_view_change(msg, t)
    elif msg.type == "NEW-VIEW":    self._handle_new_view(msg, t)
    else:
        self.emit(PBFT_REJECTED, {"reason": "unknown_type",
                                  "msg_type": msg.type, "src": msg.src}, t)

def _on_timer(self, timer_id, payload, t):
    if timer_id == "propose":
        self._propose(t)
    elif isinstance(timer_id, tuple) and timer_id[0] == "view_change":
        self._on_view_change_timeout(timer_id[1], timer_id[2], t)
    elif isinstance(timer_id, tuple) and timer_id[0] == "vc_escalate":
        self._on_escalation_timeout(timer_id[1], t)
```

The T28 silent-no-op branch for `PREPARE` / `COMMIT` / `VIEW-CHANGE` /
`NEW-VIEW` is gone — they are now wired. `unknown_type` is unchanged.

Every handler begins with a **payload-shape guard** (Backlog item
"PBFT proposal-phase review follow-ups (a)"): if `msg.payload` is not the
expected dataclass, emit `pbft_rejected` with `reason="malformed_payload"`
and drop, rather than letting an `AttributeError` escape `Node.on_message`.

### 6.3 `_accept_pre_prepare` — extended transition seam

T28's single `IDLE → PRE_PREPARED` seam is extended to also start the
voting phase and arm the view-change timer. Both callers (the recipient
validator and the primary's propose self-loop) get the new behaviour for
free.

```python
def _accept_pre_prepare(self, view, seq, d, payload, src, t):
    inst = self.inst.setdefault((view, seq), Instance(view=view, seq=seq))
    inst.state = InstanceState.PRE_PREPARED
    inst.digest = d
    inst.request_payload = payload                        # NEW — for evidence (Decision E)
    self.emit(PBFT_PRE_PREPARED, {"view": view, "seq": seq,
                                  "digest": d.hex(), "src": src}, t)
    self._arm_view_change_timer(view, seq, t)             # NEW
    self._broadcast_prepare(inst, t)                      # NEW
    self._check_prepare_quorum(inst, t)                   # NEW — buffered PREPAREs may already suffice
```

The signature gains `payload` (T28: `(view, seq, d, src, t)`). The
recipient handler passes `pp.request_payload`; the propose self-loop
passes the `request` it just popped. The T28 five-rule `_handle_pre_prepare`
validator is otherwise unchanged except for the §6.2 payload-shape guard.

### 6.4 Prepare phase

```python
def _broadcast_prepare(self, inst, t):
    self.broadcast("PREPARE", PreparePayload(inst.view, inst.seq, inst.digest), t)
    inst.prepares[self.id] = inst.digest                  # self-loop (Decision B)

def _handle_prepare(self, msg, t):
    pp = msg.payload
    if not isinstance(pp, PreparePayload):
        self._reject(t, "malformed_payload", msg_type="PREPARE", src=msg.src); return
    inst = self.inst.setdefault((pp.view, pp.seq),
                                Instance(view=pp.view, seq=pp.seq))
    inst.prepares[msg.src] = pp.request_digest            # file unconditionally (Decision C)
    self._check_prepare_quorum(inst, t)

def _check_prepare_quorum(self, inst, t):
    if inst.state is InstanceState.PRE_PREPARED \
            and inst.matching_prepares() >= 2 * self.f + 1:
        self._accept_prepare(inst, t)

def _accept_prepare(self, inst, t):
    inst.state = InstanceState.PREPARED
    self.emit(PBFT_PREPARED, {"view": inst.view, "seq": inst.seq,
                              "digest": inst.digest.hex()}, t)
    self._broadcast_commit(inst, t)
    self._check_commit_quorum(inst, t)
```

A `PREPARE` is filed into `inst.prepares` by the **instance's own**
`(view, seq)` key, independent of `self.view` — this lets an old-view
instance still gather its quorum after the node has moved on, and lets a
vote that arrives before the local `PRE-PREPARE` be counted retroactively.

### 6.5 Commit phase

```python
def _broadcast_commit(self, inst, t):
    self.broadcast("COMMIT", CommitPayload(inst.view, inst.seq, inst.digest), t)
    inst.commits[self.id] = inst.digest

def _handle_commit(self, msg, t):
    cp = msg.payload
    if not isinstance(cp, CommitPayload):
        self._reject(t, "malformed_payload", msg_type="COMMIT", src=msg.src); return
    inst = self.inst.setdefault((cp.view, cp.seq),
                                Instance(view=cp.view, seq=cp.seq))
    inst.commits[msg.src] = cp.request_digest
    self._check_commit_quorum(inst, t)

def _check_commit_quorum(self, inst, t):
    if inst.state is InstanceState.PREPARED \
            and inst.matching_commits() >= 2 * self.f + 1:
        self._accept_commit(inst, t)

def _accept_commit(self, inst, t):
    inst.state = InstanceState.COMMITTED
    self._cancel_view_change_timer(inst.view, inst.seq)
    if inst.seq not in self._decided_seqs:                # Decision G
        self._decided_seqs.add(inst.seq)
        self.emit(PBFT_COMMITTED, {"view": inst.view, "seq": inst.seq,
                                   "digest": inst.digest.hex()}, t)
        self._emit_decided(inst.digest.hex(), (inst.view, inst.seq), t)
```

`_emit_decided` is the shared `Node` helper (`src/nodes/node.py`); it
emits the contract-mandated `decided(value, instance_id, t)` event with
`value = request_digest.hex()`, `instance_id = (view, seq)` per
`node-model.md` §4.

## 7. `node.py` — view-change

### 7.1 View-change timer

```python
def _arm_view_change_timer(self, view, seq, t):
    delay = self.vc_delay * (2 ** view)                   # Decision F
    self.set_timer(("view_change", view, seq), delay, (view, seq), t)

def _cancel_view_change_timer(self, view, seq):
    self.cancel_timer(("view_change", view, seq))         # no-op if unknown

def _on_view_change_timeout(self, view, seq, t):
    inst = self.inst.get((view, seq))
    if inst is None or inst.state is InstanceState.COMMITTED:
        return                                            # already resolved
    self._initiate_view_change(view + 1, t)
```

### 7.2 Initiating a view-change

```python
def _initiate_view_change(self, new_view, t):
    if new_view <= self.view:
        return                                            # already at/past it
    if self.view_changing and new_view <= self._target_view:
        return                                            # already changing to >= this
    self.view_changing = True
    self._target_view = new_view
    self.emit(PBFT_VIEW_CHANGE, {"from_view": self.view,
                                 "new_view": new_view}, t)
    evidence = collect_evidence(self.inst)                # viewchange.py
    payload = ViewChangePayload(new_view=new_view, last_stable_seq=-1,
                                prepared=evidence)
    self.broadcast("VIEW-CHANGE", payload, t)
    self._view_changes.setdefault(new_view, {})[self.id] = payload   # self-loop
    self._arm_escalation_timer(new_view, t)
    self._check_new_view_quorum(new_view, t)              # this node may itself be the new primary
```

`_initiate_view_change` is idempotent: a second per-instance timeout for
the same (or a lower) target view is a no-op. `view_changing` is the flag
`node-model.md` §4 names; it gates `PRE-PREPARE` acceptance (T28 Rule 3,
already implemented) and proposing (§9).

### 7.3 Escalation timer

If the `NEW-VIEW` never arrives, escalate to the next view.

```python
def _arm_escalation_timer(self, new_view, t):
    delay = self.vc_delay * (2 ** new_view)
    self.set_timer(("vc_escalate", new_view), delay, new_view, t)

def _on_escalation_timeout(self, new_view, t):
    if new_view in self._new_view_installed or new_view < self._target_view:
        return                                            # NEW-VIEW arrived, or already escalated past
    self._initiate_view_change(new_view + 1, t)
```

The escalation timer is cancelled inside `_enter_new_view`.

### 7.4 Handling `VIEW-CHANGE`

```python
def _handle_view_change(self, msg, t):
    vc = msg.payload
    if not isinstance(vc, ViewChangePayload):
        self._reject(t, "malformed_payload", msg_type="VIEW-CHANGE", src=msg.src); return
    self._view_changes.setdefault(vc.new_view, {})[msg.src] = vc
    seen = len(self._view_changes[vc.new_view])
    # Decision D5 — f+1 catch-up: join a view-change a quorum of others want.
    if seen >= self.f + 1 and vc.new_view > self.view \
            and (not self.view_changing or vc.new_view > self._target_view):
        self._initiate_view_change(vc.new_view, t)
    self._check_new_view_quorum(vc.new_view, t)
```

### 7.5 Issuing `NEW-VIEW` (the new primary)

```python
def _check_new_view_quorum(self, new_view, t):
    if not self._is_primary(new_view):       return
    if new_view in self._new_view_sent:      return
    proofs_by_src = self._view_changes.get(new_view, {})
    if len(proofs_by_src) < 2 * self.f + 1:  return
    chosen = [proofs_by_src[s] for s in sorted(proofs_by_src)][:2 * self.f + 1]
    reissued = compute_reissue(chosen, new_view)          # viewchange.py
    self._new_view_sent.add(new_view)
    self.broadcast("NEW-VIEW", NewViewPayload(new_view, chosen, reissued), t)
    self._enter_new_view(new_view, reissued, t)           # primary installs locally (broadcast excludes sender)
```

The `2f+1` proofs are picked by sorted `src` so the `NEW-VIEW` is
deterministic.

### 7.6 Handling `NEW-VIEW`

```python
def _handle_new_view(self, msg, t):
    nv = msg.payload
    if not isinstance(nv, NewViewPayload):
        self._reject(t, "malformed_payload", msg_type="NEW-VIEW", src=msg.src); return
    if msg.src != nv.new_view % self.n:
        self._reject(t, "non_primary_sender", new_view=nv.new_view, src=msg.src); return
    if nv.new_view <= self.view:
        self._reject(t, "stale_new_view", new_view=nv.new_view, src=msg.src); return
    if len(nv.vc_proofs) < 2 * self.f + 1 \
            or any(p.new_view != nv.new_view for p in nv.vc_proofs):
        self._reject(t, "insufficient_proofs", new_view=nv.new_view, src=msg.src); return
    self._enter_new_view(nv.new_view, nv.reissued, t)
```

`NEW-VIEW` is accepted even by a replica whose own view-change timer never
fired — the standard catch-up.

### 7.7 Entering a new view

```python
def _enter_new_view(self, new_view, reissued, t):
    if new_view in self._new_view_installed:
        return
    self._new_view_installed.add(new_view)
    self.view = new_view
    self._target_view = new_view
    self.view_changing = False
    self.cancel_timer(("vc_escalate", new_view))
    for pp in reissued:                                   # pp: PrePreparePayload in new_view
        if digest(pp.request_payload) != pp.request_digest:
            self._reject(t, "digest_mismatch", view=pp.view, seq=pp.seq,
                         src=new_view % self.n)
            continue
        self._accept_pre_prepare(pp.view, pp.seq, pp.request_digest,
                                 pp.request_payload, src=new_view % self.n, t=t)
    if self._is_primary(new_view):
        reissued_max = max((pp.seq for pp in reissued), default=-1)
        self.next_seq = max(self.next_seq, reissued_max + 1)   # avoid seq collision
        if self.workload:
            self.set_timer("propose", self.propose_delay, None, t)
```

Re-running `_accept_pre_prepare` for each reissued instance arms a fresh
view-change timer for `(new_view, seq)` — with delay `vc_delay · 2^new_view`,
the doubled value of Decision F — and resumes the three-phase commit.

### 7.8 Propose-path guard

`_propose` (T28 §7.3) gains one line — Backlog item "PBFT proposal-phase
review follow-ups (b)":

```python
def _propose(self, t):
    if self.view_changing:        return                  # NEW — quiescent during view-change
    if not self.workload:         return
    if not self._is_primary(self.view):  return           # T28 demoted-primary guard, now live
    ...
```

### 7.9 Event-type constants

```python
PBFT_REJECTED      = "pbft_rejected"        # T28
PBFT_PRE_PREPARED  = "pbft_pre_prepared"    # T28
PBFT_PREPARED      = "pbft_prepared"        # NEW
PBFT_COMMITTED     = "pbft_committed"       # NEW
PBFT_VIEW_CHANGE   = "pbft_view_change"     # NEW — one per view-change a node initiates (feeds T54 view-change rate)
PBFT_NEW_VIEW      = "pbft_new_view"        # NEW — emitted inside _enter_new_view
```

All exported from `__init__.py`. `decided` (mandated) is emitted via the
shared `Node._emit_decided`; `pbft_new_view` is emitted in `_enter_new_view`
with `{new_view, n_reissued}`.

## 8. `viewchange.py` — pure helpers

No `PBFTNode` dependency; operate on plain data so they are unit-testable
in isolation.

```python
def collect_evidence(inst: dict[tuple[int, int], Instance]
                     ) -> list[tuple[int, int, bytes, bytes]]:
    """Every instance at state >= PREPARED, as (view, seq, digest,
    request_payload) 4-tuples, sorted by (view, seq). Decision D: no
    checkpoint bound — all prepared instances are evidence."""

def compute_reissue(proofs: list[ViewChangePayload],
                     new_view: int) -> list[PrePreparePayload]:
    """Union the `prepared` evidence across all proofs; for each distinct
    seq pick the tuple from the highest view (most recent prepared cert);
    return one PrePreparePayload(view=new_view, seq, digest, payload) per
    seq, sorted by seq."""
```

`compute_reissue` picking the highest-view evidence per `seq` is the
simulator's analogue of classical PBFT's `O`-set "max prepared view"
rule; with no equivocation (T29 honest scope) every proof agrees, so the
choice is only load-bearing once T18 / T53 inject conflicting evidence.

## 9. Harness construction

No change to `src/config/factory.py`. The integration test (§10) rolls
its own `(node_id, global_seed) -> PBFTNode` factory closing over `n`,
the per-node workload assignment, and `vc_delay` — the same pattern
`tests/integration/test_pbft_proposal.py` uses for T28. T29 ships no
`make_pbft_node_factory` src helper (T28 did not either).

## 10. Test plan

### 10.1 Unit tests — `tests/pbft/`

Same idiom as `tests/pbft/test_node_validation.py`: one `PBFTNode` in
isolation, bind-time outbound API replaced with capturers, `_kickoff` to
`RUNNING`, hand-built `Message`s, direct `on_message` / `on_timer` calls.

| File | Coverage |
| :-- | :-- |
| `test_messages.py` (extend) | `ViewChangePayload.prepared` accepts 4-tuples; frozen. |
| `test_instance.py` (extend) | `request_payload` default `None`; `matching_prepares` / `matching_commits` count only digest-matching entries, return 0 while `digest is None`. |
| `test_node_voting.py` (new) | `PRE_PREPARED` broadcasts `PREPARE` + self-records; `2f+1` matching `PREPARE`s → `PREPARED` + `COMMIT` broadcast; `2f+1` `COMMIT`s → `COMMITTED` + `decided`; digest-mismatched votes do not count; out-of-order (`PREPARE` before `PRE-PREPARE`) is buffered then counted; `2f` is insufficient; `decided` fires once per `seq` (Decision G); malformed `PREPARE` / `COMMIT` payload → `pbft_rejected`. |
| `test_node_viewchange.py` (new) | view-change timer armed on `PRE_PREPARED`, cancelled on `COMMITTED`; timer fire on a stalled instance → `view_changing=True` + `VIEW-CHANGE` broadcast + `pbft_view_change`; timer delay doubles per view (Decision F); `f+1` `VIEW-CHANGE`s → catch-up initiation; new primary collecting `2f+1` `VIEW-CHANGE`s → `NEW-VIEW` broadcast; `NEW-VIEW` recipient advances `view`, clears `view_changing`, installs reissued instances; `NEW-VIEW` validation rejections (`non_primary_sender`, `stale_new_view`, `insufficient_proofs`); escalation timer fires when no `NEW-VIEW` arrives; `_propose` is quiescent while `view_changing`. |
| `test_viewchange.py` (new) | `collect_evidence` returns only state ≥ `PREPARED`, sorted, 4-tuples; `compute_reissue` unions across proofs, picks highest-view per `seq`, stamps `new_view`, sorted by `seq`. |

### 10.2 Integration tests — `tests/integration/test_pbft_consensus.py`

Driven through `config.factory.build_run`; real six-phase bootstrap and
determinism contract.

**Scenario A — honest full commit (n = 4 and n = 7).** Single network
phase, minimal delay, zero drop; `vc_delay` at its generous default so no
view-change occurs. Workload `[b"X"]` on node 0. Assertions:

- Every node emits `pbft_pre_prepared`, `pbft_prepared`, `pbft_committed`,
  and `decided` for `(view=0, seq=0)` — `n` of each.
- Zero `pbft_rejected`, zero `pbft_view_change`, zero `NEW-VIEW`.
- `decided.value == digest(b"X").hex()` for every node.
- Determinism: a seed-identical re-run produces a byte-identical record
  stream.

**Scenario B — view-change under delay (n = 4).** A constant-delay regime
`D` and a `vc_delay` chosen so view 0's timer (`vc_delay`) fires before
its commit quorum forms but view 1's (`2·vc_delay`) does not — i.e.
`D < vc_delay < 2·D` (Decision F). The exact `D` / `vc_delay` / phase
layout is tuned during TDD execution against the real network model; the
spec fixes the *assertions*, not the constants:

- At least one `VIEW-CHANGE` and at least one `NEW-VIEW` are delivered.
- Every node reaches `self.view == 1`.
- The request still reaches `decided` with `value == digest(b"X").hex())`
  — view-change does not break safety: the digest decided is the digest
  proposed.
- No `pbft_rejected`.
- Determinism: seed-identical re-run is byte-identical.

This scenario is a *spurious* view-change (the honest primary's request
also commits in view 0, just after the timer fired) — exactly the
"spurious view change under delay variance" phenomenon
`wiki/algorithms/pbft.md` §Behaviour-under-network-delay describes and T57
later targets. It exercises the complete recovery path — timer fire →
`VIEW-CHANGE` → `2f+1` collection → `NEW-VIEW` → reissue → re-commit —
deterministically, with comfortable timing margins on both sides.

### 10.3 Coverage expectation

Every handler, transition, quorum check, view-change branch, and rejection
reason is reached by at least one unit test. The escalation timer
(§7.3) is covered by a unit test that withholds the `NEW-VIEW`; it is not
exercised by either e2e scenario (both deliver `NEW-VIEW` in time), which
is intentional and noted so a future branch-coverage gate does not flag
it.

## 11. Experiment page

`wiki/experiments/2026-05-21_pbft-consensus-baseline.md`, following the
T28 template (`2026-05-21_pbft-proposal-baseline.md`):

- **Config:** both scenarios — `n`, `workload`, `propose_delay`,
  `vc_delay`, network phases, `global_seed`.
- **Commit hash:** filled at write time.
- **Re-run commands:** the `pytest` / `unittest` invocations.
- **Result:** event counts per scenario; determinism confirmation.
- **Observation:** one paragraph — the full three-phase commit reaches
  `decided` across the W3 stack; view-change recovers a delayed instance
  without a safety break; per-view timer backoff terminates the recovery.
  Report `RunResult.events_tombstoned` vs `events_processed` (Backlog item
  "Scheduler heap growth under high timer churn" — heap compaction is
  added only if tombstones approach processed-event count; expected far
  below at this scale).

## 12. Wiki updates

- `wiki/index.md` — one new line under `## Experiments`.
- `wiki/log.md` — one `## [2026-05-21] code | task 29 — ...` entry.
- `## Revisions` entries (per `docs/wiki-spec.md` § Revisions rule):
  - `wiki/concepts/message-types.md` §3 — `VIEW-CHANGE` `prepared_evidence`
    is a 4-tuple `(view, seq, digest, request_payload)`, not the declared
    3-tuple (Decision E); the size column grows by `k·|req|`. §9's
    "VIEW-CHANGE evidence size cap" item: T29 uses no cap (Decision D).
  - `wiki/concepts/system-design-protocols.md` §2 — record any divergence
    of the implementation from the §2 sketch (the uniform quorum model
    of Decision B; the explicit timer-backoff of Decision F; the
    self-loop `PREPARE` / `COMMIT` broadcasts). Decision deferred to
    execution: revise only where a reader following the sketch would
    write incorrect code.
- **No new Concepts or Algorithms pages** — the design contracts already
  exist; T29 implements them.

## 13. Open to revision

- **Old-view instances may still commit after a view-change.** Votes are
  filed by `(view, seq)` key regardless of `self.view`, so a view-0
  instance can reach `COMMITTED` after the node entered view 1. This is
  correct PBFT (a late commit is safe) and Decision G suppresses the
  duplicate `decided`. If a future task needs strict per-view quiescence,
  freeze old-view instances on `_enter_new_view`.
- **Undrained workload after a view-change.** A primary demoted
  mid-drain leaves its remaining workload unproposed (no client-resend
  model — `message-types.md` §1). The §10 scenarios use a one-item
  workload so nothing is stranded; T19 / T39 may add resend.
- **`compute_reissue` highest-view tie-break** (§8). With honest nodes
  every proof agrees; the rule only becomes load-bearing under T18 / T53
  conflicting evidence.
- **`vc_delay` as a constructor param vs. config knob** (§6.1). A
  constructor param now; T19's experiment matrix may pull it into YAML.
  T57 (adaptive timeout) replaces the fixed `2^view` backoff.
- **Escalation-timer delay** (§7.3) reuses `vc_delay · 2^new_view`; T57
  may want a separate policy.

## 14. Out of scope (recorded so the implementation does not drift)

- Checkpoint / garbage-collection protocol (`CHECKPOINT` messages,
  stable-checkpoint evidence bounding) — not modelled; `last_stable_seq`
  is vestigial (Decision D).
- Signature simulation, spoofed-`src`, experiment-scale malformed-message
  injection — T18.
- The honest n = 4 / 7 / 10 latency sweep — T30.
- The full PBFT unit-test battery (timeout, message-loss, multi-round at
  scale) — T31.
- Adaptive / calibrated timeout — T57.
- Unified `run()` interface and CSV output — T39 / T40.

## 15. Sources

Implementation spec; no primary-literature citations. Mechanism semantics
are deferred to the algorithm and concept pages.

**Inbound:**
- `wiki/algorithms/pbft.md` — three-phase commit (§Three-phase commit),
  view change (§View change), the quorum-intersection safety argument.
- `wiki/concepts/message-types.md` §3 — `PREPARE` / `COMMIT` /
  `VIEW-CHANGE` / `NEW-VIEW` rows.
- `wiki/concepts/system-design-protocols.md` §2 — PBFT main-loop sketch.
- `wiki/concepts/node-model.md` §4 — PBFT FSM, terminal state, `decided`
  payload; §4 cross-instance state (`view`, `view_changing`).
- `docs/superpowers/specs/2026-05-21-t28-pbft-proposal-design.md` — the
  pre-prepare phase this spec extends; Decisions A–E carry forward.

**Outbound:**
- T30 consumes `src/pbft/` for the honest correctness sweep.
- T31 consumes it for the unit-test battery.
- T54 consumes the `pbft_view_change` event for view-change-rate metrics.
- T57 replaces the fixed `2^view` timer backoff with an adaptive policy.
