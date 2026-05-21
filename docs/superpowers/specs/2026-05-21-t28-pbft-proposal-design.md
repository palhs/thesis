# T28 — PBFT proposal logic: design spec

Engineer-register design spec for T28, consumed by `superpowers:writing-plans`.
Implements the **pre-prepare phase** of the PBFT three-phase commit defined by
the W3 design contracts. Voting (PREPARE → COMMIT), finalisation, and
view-change are explicitly **T29**, not T28.

- **Task:** T28 (`TASKS.md`, Week 5) — Implement simplified PBFT proposal
  logic. Role: Engineer. Artifact: `src/pbft/`.
- **Design contracts:** `wiki/algorithms/pbft.md`, `wiki/concepts/message-types.md` §3,
  `wiki/concepts/system-design-protocols.md` §2, `wiki/concepts/node-model.md`.
- **Upstream code:** `src/scheduler/` (T21), `src/nodes/` (T22), `src/network/`
  (T23), `src/event_log/` (T24), `src/config/` (T27).

## 1. Scope

T28 ships the **leader-proposes + recipients-validate** half of the PBFT
three-phase commit. Concretely:

1. The primary for view `v` builds a request batch from a stub workload,
   broadcasts a `PRE-PREPARE(view, seq, request_digest, request_payload)`,
   and locally transitions its own `(view, seq)` instance to `PRE_PREPARED`.
2. Each recipient validates the `PRE-PREPARE` against five rules. On
   success, transitions the local `(view, seq)` instance to `PRE_PREPARED`
   and emits an observable event. On any failure, emits a `pbft_rejected`
   event with the rejection reason and drops the message.
3. The propose timer re-arms while the workload is non-empty; when the
   workload drains, the timer chain ends and the simulator reaches
   quiescence naturally.

Explicit non-goals (deferred to T29):

- `PREPARE` and `COMMIT` handler logic, quorum collection, the
  `PRE_PREPARED → PREPARED → COMMITTED` transitions, `decided` emission.
- `VIEW-CHANGE` and `NEW-VIEW` handler logic, view-change timer arming,
  the `view_changing` true-branch.
- Re-issue of prepared-but-not-committed `(view, seq)` instances under
  `NEW-VIEW`.

Explicit non-goals (deferred to other tasks):

- Signature simulation and the spoofed-`src` adversary surface — T18.
- Workload coming from a real mempool or the experiment-harness workload
  loader — T19 / T27 / T39 (the `load_workload` seam named in
  `wiki/concepts/system-design.md`).
- The unified `run()` interface and CSV output — T39 / T40.

## 2. Settled design decisions

Five decisions were taken with the human during brainstorming, before this
spec was written. Each binds T28 and the matching T29 PR.

- **Decision A — Skeleton FSM.** `Instance` declares all four states
  (`IDLE`, `PRE_PREPARED`, `PREPARED`, `COMMITTED`) and reserves the
  per-`(view, seq)` quorum dicts. T28 wires only `IDLE → PRE_PREPARED`.
  PREPARE / COMMIT / VIEW-CHANGE / NEW-VIEW messages route to a silent
  no-op branch (no rejection event). T29 grows the FSM by filling in
  transitions, not by adding new data structures. Rationale: append-only
  diff for T29; keeps `messages.py` honest about the full PBFT vocabulary;
  the unwired branches are quiet, not loud (no false-positive
  `pbft_rejected` noise once T29 lands).
- **Decision B — Stub workload injected at construction.** `PBFTNode`
  takes `workload: list[bytes] | None` as a keyword-only constructor
  parameter, copied at construction. Non-primaries pass `None`. The
  primary pops one item per propose timer fire. No `Mempool` class.
  Rationale: pins the eventual workload-seam shape (a list of ACUs) at
  the right surface without abstracting; T29 view-change replays from
  `prepared_evidence`, not from this list, so T29 is not blocked.
- **Decision C — Drain-workload propose cadence.** The primary re-arms
  its `propose` timer with `propose_delay` while the workload is
  non-empty. Each fire bumps `seq`, pops the next batch, broadcasts
  `PRE-PREPARE`, and self-transitions. When the workload drains, the
  timer chain ends. Rationale: matches the
  `system-design-protocols.md` §2 sketch's re-arm; gives T28 multiple
  instances to test against; PROPOSE_DELAY is the same knob T57 (adaptive
  timeout) will eventually tune.
- **Decision D — Classical `v mod n` primary rule, `n` passed at
  construction.** `is_primary(view) = self.id == (view % self.n)`.
  `PBFTNode.__init__` takes `n: int` keyword-only. Rationale: every
  BFT-family protocol Node will need `n` for quorum thresholds (`2f+1`)
  anyway; the duplication of state Network already holds is honest
  rather than backdoored.
- **Decision E — Five-rule recipient validation, log-and-drop on
  failure.** Recipient drops the PRE-PREPARE unless: (1) `msg.src ==
  primary_of(msg.payload.view)`, (2) `msg.payload.view == self.view`,
  (3) `not self.view_changing`, (4) `(view, seq)` not already advanced
  past `IDLE`, (5) `digest(payload.request_payload) ==
  payload.request_digest`. Any failure: emit `pbft_rejected` with
  `reason + (view, seq, src)`, drop. Rationale: establishes the rejection
  pattern T29's invalid PREPARE / COMMIT will reuse; raises are too
  strong (T18 may legitimately inject malformed PRE-PREPAREs); silent
  drops lose observability T28's tests need.

## 3. Module layout — `src/pbft/`

| File | Contents | Approx LoC |
| :-- | :-- | :-- |
| `__init__.py` | Package exports: `PBFTNode`, `Instance`, `InstanceState`, `PrePreparePayload`, the rejection-event constants. | ~15 |
| `messages.py` | `PrePreparePayload` dataclass (frozen). Placeholders for `PreparePayload`, `CommitPayload`, `ViewChangePayload`, `NewViewPayload` — declared but unused in T28; T29 wires them. | ~50 |
| `instance.py` | `InstanceState` enum (`IDLE`, `PRE_PREPARED`, `PREPARED`, `COMMITTED`). `Instance` dataclass keyed by `(view, seq)` — state, digest, empty `prepares`/`commits` dicts reserved for T29. | ~40 |
| `digest.py` | `digest(payload) -> bytes` — 32-byte blake2b, process-stable. Same pattern as `_stable_seed` in `src/nodes/node.py`. | ~12 |
| `node.py` | `PBFTNode(Node)` — propose timer, primary detection, the five-rule validator, the `IDLE → PRE_PREPARED` transition, the silent-no-op branch for unwired message types, the `unknown_type` rejection branch. | ~130 |

Tests:

- `tests/pbft/test_digest.py`, `test_messages.py`, `test_instance.py`,
  `test_node_validation.py`, `test_node_propose.py` — unit-level, no
  Scheduler / Network bootstrap.
- `tests/integration/test_pbft_proposal.py` — two e2e scenarios driven
  through `config.factory.build_run`.

Experiment page: `wiki/experiments/2026-05-21_pbft-proposal-baseline.md`.

## 4. `PrePreparePayload` and friends — `messages.py`

Realises `wiki/concepts/message-types.md` §3 for the `PRE-PREPARE` row.
The four placeholder payloads exist so T29 grows by filling in handlers,
not by adding new dataclasses.

```python
@dataclass(frozen=True)
class PrePreparePayload:
    view: int
    seq: int
    request_digest: bytes        # 32 bytes (blake2b)
    request_payload: bytes       # the batch itself; arbitrary length

# --- T29 placeholders. Declared, not consumed in T28. ---
@dataclass(frozen=True)
class PreparePayload:
    view: int; seq: int; request_digest: bytes

@dataclass(frozen=True)
class CommitPayload:
    view: int; seq: int; request_digest: bytes

@dataclass(frozen=True)
class ViewChangePayload:
    new_view: int; last_stable_seq: int
    prepared: list[tuple[int, int, bytes]]   # (view, seq, digest)

@dataclass(frozen=True)
class NewViewPayload:
    new_view: int
    vc_proofs: list[ViewChangePayload]
    reissued: list[PrePreparePayload]
```

Notes:

- `request_payload` is `bytes` in T28 (matches the `workload: list[bytes]`
  constructor type). `message-types.md` §3 typed it as `list` (transaction
  batch); the v1 abstraction does not split transactions inside a batch,
  so a single `bytes` blob suffices and is cheaper. If T19 / T27 grows a
  per-transaction model, this widens to `list[Transaction]` as a
  `## Revisions` entry on the wiki page.
- Field order matches `message-types.md` §3 exactly so the row reads
  one-to-one against the wiki.

## 5. `InstanceState` and `Instance` — `instance.py`

Realises `wiki/algorithms/pbft.md` §Three-phase commit for the per-`(view,
seq)` data plane.

```python
class InstanceState(Enum):
    IDLE          = 0
    PRE_PREPARED  = 1
    PREPARED      = 2     # T29-wired
    COMMITTED     = 3     # T29-wired

@dataclass
class Instance:
    view: int
    seq: int
    state: InstanceState = InstanceState.IDLE
    digest: Optional[bytes] = None
    # T29: prepare and commit quorum collection.
    prepares: dict[int, bytes] = field(default_factory=dict)   # src -> digest
    commits:  dict[int, bytes] = field(default_factory=dict)   # src -> digest
```

The `prepares` / `commits` dicts are pre-declared so T29 fills them in
without touching the dataclass shape. T28 does not write to them; tests
assert they stay empty across the proposal phase.

## 6. `digest` — `digest.py`

```python
import hashlib

def digest(payload: bytes) -> bytes:
    """32-byte blake2b digest of `payload`. Process-stable, like the
    _stable_seed helper in src/nodes/node.py."""
    return hashlib.blake2b(payload, digest_size=32).digest()
```

Used by the primary on every propose to populate `PrePreparePayload.
request_digest`, and by recipients on every PRE-PREPARE to validate
rule 5. The widths match `message-types.md` §7 (Hash digest = 32 bytes).

## 7. `PBFTNode` — `node.py`

### 7.1 Constructor

```python
class PBFTNode(Node):
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
            raise ValueError(f"node_id {node_id} outside [0, {n})")
        if propose_delay <= 0:
            raise ValueError(f"propose_delay must be positive, got {propose_delay}")
        self.n: int = n
        self.f: int = (n - 1) // 3
        self.view: int = initial_view
        self.view_changing: bool = False
        self.workload: list[bytes] = list(workload or [])
        self.propose_delay: float = propose_delay
        self.next_seq: int = 0
        self.inst: dict[tuple[int, int], Instance] = {}
```

`n` is keyword-only and required; `workload`, `propose_delay`,
`initial_view` are keyword-only with defaults. `f` is unused in T28 but
computed at construction for T29.

### 7.2 Lifecycle hooks

```python
def _on_start(self, t: float) -> None:
    if self._is_primary(self.view):
        self.set_timer("propose", self.propose_delay, None, t)

def _on_timer(self, timer_id, payload, t: float) -> None:
    if timer_id == "propose":
        self._propose(t)
    # else: unknown timer; silent no-op (T29 owns view-change timers).

def _on_message(self, msg: Message, t: float) -> None:
    if msg.type == "PRE-PREPARE":
        self._handle_pre_prepare(msg, t)
    elif msg.type in ("PREPARE", "COMMIT", "VIEW-CHANGE", "NEW-VIEW"):
        return                              # T29 wires these
    else:
        self.emit(PBFT_REJECTED,
                  {"reason": "unknown_type", "msg_type": msg.type,
                   "src": msg.src}, t)
```

PREPARE / COMMIT / VIEW-CHANGE / NEW-VIEW are silently no-op'd because
they are known protocol-vocabulary types T29 will wire; emitting
`pbft_rejected` for them would create false-positive noise during T29's
mid-flight test runs. Stray types (a hand-rolled `"PING"` in a test, an
adversary fabrication T18 may inject) hit the `unknown_type` branch.

### 7.3 Propose path

```python
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
```

Two decisions worth flagging:

- **Primary self-transition is explicit.** `Network.submit_broadcast`
  excludes the sender (`src/network/network.py:121`), so the primary
  never receives its own PRE-PREPARE through delivery. Without the
  explicit `_accept_pre_prepare(..., src=self.id, t=t)` self-loop, the
  primary's `(view, seq)` instance would sit in `IDLE` forever — a real
  protocol violation. Calling the shared `_accept_pre_prepare`, not
  `_on_message`, keeps the lifecycle hook off the trusted-source path.
- **Demoted-primary guard.** `if not self._is_primary(self.view): return`
  is dead in T28 (view never changes). It is one line of insurance that
  documents the timer-survives-view-change semantics T29 will own.

### 7.4 Validation

```python
def _handle_pre_prepare(self, msg: Message, t: float) -> None:
    pp: PrePreparePayload = msg.payload

    if msg.src != (pp.view % self.n):
        self._reject(t, "non_primary_sender", view=pp.view, seq=pp.seq,
                     src=msg.src);  return
    if pp.view != self.view:
        self._reject(t, "view_mismatch", view=pp.view, seq=pp.seq,
                     src=msg.src);  return
    if self.view_changing:
        self._reject(t, "view_changing", view=pp.view, seq=pp.seq,
                     src=msg.src);  return
    existing = self.inst.get((pp.view, pp.seq))
    if existing is not None and existing.state is not InstanceState.IDLE:
        self._reject(t, "duplicate_pre_prepare", view=pp.view, seq=pp.seq,
                     src=msg.src);  return
    if digest(pp.request_payload) != pp.request_digest:
        self._reject(t, "digest_mismatch", view=pp.view, seq=pp.seq,
                     src=msg.src);  return

    self._accept_pre_prepare(pp.view, pp.seq, pp.request_digest,
                             src=msg.src, t=t)
```

Order matters for the rejection-event taxonomy: cheap checks first, the
hash comparison last. Each rejection reason is a distinct string so the
event log can be filtered by failure mode.

### 7.5 Transition seam

```python
def _accept_pre_prepare(self, view: int, seq: int, d: bytes,
                        src: int, t: float) -> None:
    """Shared IDLE -> PRE_PREPARED transition. Caller (recipient handler
    or primary self-loop) guarantees validation has passed."""
    inst = self.inst.setdefault((view, seq), Instance(view=view, seq=seq))
    inst.state = InstanceState.PRE_PREPARED
    inst.digest = d
    self.emit("pbft_pre_prepared",
              {"view": view, "seq": seq, "digest": d.hex(), "src": src}, t)

def _reject(self, t: float, reason: str, **fields) -> None:
    self.emit(PBFT_REJECTED, {"reason": reason, **fields}, t)

def _is_primary(self, view: int) -> bool:
    return self.id == (view % self.n)
```

`_accept_pre_prepare` is the single transition seam; T29's
`_accept_prepare` / `_accept_commit` will follow the same shape.

### 7.6 Event-type constants

```python
PBFT_REJECTED      = "pbft_rejected"
PBFT_PRE_PREPARED  = "pbft_pre_prepared"
```

Exported from `__init__.py` so tests and (later) T40 / T55 metric code
reference them by name, not as bare string literals (per the Backlog
entry noting bare-string event names are a smell).

## 8. Harness construction

`config.factory.build_run` takes a `node_factory: Callable[[NodeId,
global_seed], Node]`. T28 ships a small builder helper:

```python
def make_pbft_node_factory(
        n: int,
        workload_for: Callable[[int], list[bytes] | None],
        propose_delay: float = 1.0,
        initial_view: int = 0,
        weight: float = 1.0) -> Callable[[int, int], PBFTNode]:
    def factory(node_id: int, global_seed: int) -> PBFTNode:
        return PBFTNode(node_id=node_id, weight=weight,
                        endpoint=None, global_seed=global_seed,
                        n=n, workload=workload_for(node_id),
                        propose_delay=propose_delay,
                        initial_view=initial_view)
    return factory
```

`workload_for(node_id)` returns the workload for node `node_id` (the
caller pins which validator gets the batches; for view-0 baseline that
is node 0). No changes to `src/config/factory.py` itself.

## 9. Test plan

### 9.1 Unit tests — `tests/pbft/`

| File | Coverage |
| :-- | :-- |
| `test_digest.py` | `digest` is deterministic across calls; two inputs give two distinct outputs; output width = 32 bytes. |
| `test_messages.py` | `PrePreparePayload` is frozen (mutation raises); required-field construction; placeholder payload classes import cleanly. |
| `test_instance.py` | `InstanceState` member identity (`IDLE = 0`, ...); `Instance` defaults (`state=IDLE`, `digest=None`, empty `prepares`/`commits`). |
| `test_node_validation.py` | Each of the five rejection branches in isolation (one PBFTNode, hand-built Message, `node.on_message`, assert the `pbft_rejected` event with the expected `reason`). Plus the happy-path acceptance. Uses stubbed `set_timer` / `broadcast` / `emit` (same pattern as `tests/nodes/`). |
| `test_node_propose.py` | `_is_primary` across views 0/1/2 for n=4 and n=7; workload-drain (3-batch workload → 3 propose timer fires, then the chain stops); `next_seq` monotone; self-transition correctness (primary's `(0, 0)` instance reaches PRE_PREPARED after one propose); non-primary `_on_start` is a no-op (does not arm a timer). |

### 9.2 Integration tests — `tests/integration/test_pbft_proposal.py`

Two scenarios, both driven through `config.factory.build_run` so the
six-phase bootstrap is real and the determinism contract is exercised
end-to-end.

**Scenario A — n=4, workload = [b"A", b"B", b"C"], primary = node 0.**

- Build the run via `build_run(config, global_seed, make_pbft_node_factory(...))`.
- Drive `scheduler.run()` to quiescence (no time bound; the propose-
  timer chain ends on drain, no other events on the heap).
- Assertions:
  - Exactly twelve `pbft_pre_prepared` events: three per node (4 × 3),
    with `(view=0, seq=k, digest=blake2b(workload[k]))`.
  - Zero `pbft_rejected` events.
  - Zero `PREPARE` / `COMMIT` / `VIEW-CHANGE` / `NEW-VIEW` messages
    emitted (count via the event log's send-shape).
  - Determinism: a second `build_run` with the same `global_seed`
    produces a byte-identical event-log CSV (mirrors
    `tests/event_log/test_e2e.py`).

**Scenario B — n=7, workload = [b"X"], primary = node 0.**

- Same harness path. Asserts:
  - Exactly seven `pbft_pre_prepared` events (1 self-loop + 6
    deliveries).
  - Zero `pbft_rejected`.
  - Determinism re-run identical.

Both scenarios run under a single network phase with zero delay and
zero drop (the trivial network configuration that
`tests/integration/test_message_exchange.py` already uses).

### 9.3 Coverage expectation

T28's code paths are deliberately small. All five rejection branches,
the happy-path acceptance, the self-loop, the workload drain, the
non-primary `_on_start` no-op, and the unknown-type rejection are each
covered by at least one test. The PREPARE / COMMIT / VIEW-CHANGE /
NEW-VIEW silent no-op branch is *not* covered in T28 — it is dead until
T29 wires the senders. That gap is intentional; flagged so the (future)
coverage gate from Backlog item "coverage tooling" does not flag it as
a regression.

## 10. Experiment page

`wiki/experiments/2026-05-21_pbft-proposal-baseline.md`, following the
T22 / T23 / T24 / T25 template:

- **Config used:** n, workload, propose_delay, global_seed, network
  phases (single phase, zero delay, zero drop).
- **Commit hash:** filled in at write time.
- **Commands to re-run:** `pytest tests/integration/test_pbft_proposal.py`.
- **Raw result location:** the test emits its event-log CSV under
  `results/<run_id>/` (mirroring T25's pattern); the page links to one
  representative CSV.
- **Observation paragraph:** one paragraph confirming the PRE-PREPARE
  phase reaches self-consistent pre-prepared state across n=4 and n=7;
  noting that the T28/T29 cut at the IDLE → PRE_PREPARED transition
  holds (no PREPARE / COMMIT messages were emitted); noting that T29
  grows the FSM with no upstream rework needed.

## 11. Wiki updates

- `wiki/index.md` — one new line under `## Experiments` for the new
  experiment page. **No new Concepts or Algorithms pages** — the design
  contracts already exist (`algorithms/pbft.md`, `concepts/message-types.md`
  §3, `concepts/system-design-protocols.md` §2); T28 is the implementation
  of those contracts.
- `wiki/log.md` — one entry per `docs/wiki-spec.md` § Log format:
  `## [2026-05-21] code | task 28 — implement PBFT proposal logic`,
  role Engineer, touched files, one-sentence note.
- Possible `## Revisions` on `concepts/system-design-protocols.md` §2 if
  the implementation diverges from the sketch in a way that would
  mislead a reader following the sketch. Anticipated divergences are
  concretisations rather than contradictions: (i) the explicit
  `_accept_pre_prepare` self-loop, which the sketch hides inside
  `broadcast`; (ii) the five-rule validator structure, more explicit
  than the sketch's bare `if` chain; (iii) `next_seq` as a primary-only
  counter, vs. the sketch's `self.next_seq()` method call. Decision
  deferred to execution; revise only if a reader would write incorrect
  code from the sketch.

## 12. Open to revision

Items below are visible fit issues; any change beyond a typo lands as a
`## Revisions` entry per `docs/wiki-spec.md` § Revisions rule.

- **`request_payload: bytes` vs `list[Transaction]`** (§4). T19 / T27
  may grow a per-transaction model; the field widens to
  `list[Transaction]` then.
- **`make_pbft_node_factory` location** (§8). Lives in `src/pbft/`
  initially; if T39's unified `run()` interface centralises factory
  construction, it migrates to `src/common/`.
- **PROPOSE_DELAY as constructor param vs. config knob** (§2 Decision C).
  Currently a constructor param with default 1.0. T19's experiment
  matrix may pull it into the YAML config; constructor stays as the
  injection point.
- **`pbft_pre_prepared` event payload fields** (§7.5). `view`, `seq`,
  `digest.hex()`, `src` are the minimum the e2e test asserts against.
  T40's CSV schema may want additional fields (e.g. `t_sent`,
  `request_size`); add then.
- **Wiki Revisions on `system-design-protocols.md` §2** (§11). Decision
  deferred to execution.

## 13. Out of scope (recorded so the implementation does not drift)

- PREPARE / COMMIT / VIEW-CHANGE / NEW-VIEW handler bodies → T29
- `Instance.prepares` / `Instance.commits` population → T29
- View-change timer (`("view_change", instance_key)`) → T29
- The `_reject_*` path for PREPARE / COMMIT once T29 lands → T29
- Signature simulation, spoofed-`src` adversary → T18
- Workload from real mempool / experiment harness → T19, T27, T39
- The unified `run()` interface and CSV output → T39 / T40
- Adversarial PRE-PREPAREs at e2e scale (a rogue Node injecting
  wrong-view / bad-digest in a 4-node run) → unit tests against the
  validator cover the cases; T51–T53 own the experiment-scale variant.

## 14. Sources

Implementation spec; no primary-literature citations. Mechanism
semantics are deferred to the algorithm and concept pages.

**Inbound:**
- `wiki/algorithms/pbft.md` — three-phase commit (§Three-phase commit).
- `wiki/concepts/message-types.md` §3 — PRE-PREPARE row.
- `wiki/concepts/system-design-protocols.md` §2 — PBFT main loop sketch.
- `wiki/concepts/node-model.md` §4, §6, §7 — FSM, envelope, outbound API.
- `wiki/concepts/simulation-design.md` — six-phase bootstrap.

**Outbound (T29 dependency):**
- T29 implements PREPARE / COMMIT / VIEW-CHANGE / NEW-VIEW handlers on
  top of `Instance` and `PBFTNode` shipped by T28. The T28/T29 cut is
  the `_accept_pre_prepare` transition: T29 adds `_accept_prepare`,
  `_accept_commit`, and the equivalent view-change machinery without
  touching the propose path or the validator.
