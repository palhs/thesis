# T23 — Message passing with configurable delay: design spec

Engineer-register design spec for T23, consumed by `superpowers:writing-plans`.
Implements the honest inter-node delivery layer (`Network`) defined by the T15
design contract `wiki/concepts/network-model.md` and its companion
`wiki/concepts/network-model-phases.md`. The scheduler it queues events on
(T21) and the `Node` it binds against (T22) are both complete in `src/`.

- **Task:** T23 (`TASKS.md`, Week 4) — Implement message passing with
  configurable delay. Role: Engineer. Artifact: `src/network/`.
- **Design contract:** `wiki/concepts/network-model.md` +
  `wiki/concepts/network-model-phases.md` (T15).
- **Upstream code:** `src/scheduler/` (T21) — `Scheduler.schedule`,
  `Delivery` / `PhaseAdvance` events, `bind_network`, the six-phase bootstrap;
  `src/nodes/` (T22) — the `Node` ABC, the `Message` envelope, `Node.send` /
  `Node.broadcast` outbound placeholders.

## 1. Scope

T23 builds the **complete honest delivery infrastructure** — the system-level
`Network` object shared by every `Node`. Per the human decision at
brainstorming (2026-05-19), T23 implements the **full contract**: phase
timeline, all five delay distributions, Bernoulli drop, *and* the partition
predicate. The `TASKS.md` outcome line ("delay injection and drop simulation")
is narrower than the contract; the contract is one coherent unit and partition
is required to model pre-GST asynchrony that the W8 baseline tests rely on.

Out of scope, deferred to the owning task:

- Adversary semantics — T18. The `Network` is *honest infrastructure*
  (`network-model.md §6`); no adversary attaches here.
- Per-protocol message `type` / `payload` contents — T16. The `Network`
  treats both as opaque transit cargo.
- Experiment harness, YAML phase-timeline loading, `global_seed` sourcing —
  T19 / T27. T23's `Network` is constructed in code/tests with an explicit
  `list[Phase]`.
- The cross-component scrambled-call-order determinism test — T25
  (`TASKS.md` § Backlog). T23 ships its own network-level determinism check
  as build verification (§7.2).
- Bandwidth / region-aware delay / bursty drop / network-layer adversary —
  all `network-model.md §8` open-to-revision items, not v1.

### Settled design decisions

Taken with the human before this spec was written:

- **Decision A — full-contract scope.** Phases + delay + drop + partition,
  per §1 above.
- **Decision B — broadcast targets the full registry minus sender.** The
  contract `§5` sources broadcast recipients from
  `node.fsm.active_validator_set()`, but the per-protocol FSM (T28+) does not
  exist yet — the T22 `Node` has no `fsm` attribute. v1 `broadcast` reaches
  every registered `Node` except the sender. The FSM-membership seam is
  recorded as a known limitation, to be repointed when T28 lands.
- **Decision C — phase tracking by pointer, not bisect.** A `_phase_idx`
  pointer advanced by `PhaseAdvance` events, not an `O(log P)` `_phase_at(t)`
  bisect on every send (§5.4). The `network-model.md §7` sketch's `_phase_at`
  is "illustrative, non-binding"; dropping it is within latitude.
- **Decision D — stable RNG seed hash.** The network RNG is seeded with a
  `blake2b`-derived stable hash, not the contract `§6.1` formula
  `hash(("network", global_seed))`, which is process-randomised. Recorded as
  a `## Revisions` entry on `network-model-phases.md §6.1` (§9). Same class
  of fix T22 applied to the per-Node RNG.

## 2. Module layout — `src/network/`

| File | Contents |
| :-- | :-- |
| `phases.py` | `DelayDist`, `Partition`, `Phase` dataclasses; `validate_timeline()` |
| `network.py` | the `Network` class |
| `__init__.py` | package exports: `Network`, `DelayDist`, `Partition`, `Phase` |

Tests land in `tests/network/` (mirrors `tests/scheduler/` and
`tests/nodes/`). Mirrors the wiki's own split: `network-model.md` is the
contract (→ `network.py`), `network-model-phases.md` is the phase mechanics
(→ `phases.py`).

## 3. Phase configuration — `phases.py`

### 3.1 `DelayDist`

```python
@dataclass(frozen=True)
class DelayDist:
    kind: str        # "constant"|"uniform"|"normal"|"exponential"|"heavy_tail"
    params: dict
    def sample(self, rng: random.Random) -> float: ...
```

`__post_init__` validates `kind` is one of the five and that `params` are
well-formed for that `kind`; an unknown `kind` or a degenerate parameter set
raises `ValueError` at construction (fail-fast, before any run).

| `kind` | `params` | `sample` | Construction-time rejection |
| :-- | :-- | :-- | :-- |
| `constant` | `delay` | `delay` | `delay <= 0` |
| `uniform` | `low`, `high` | `rng.uniform(low, high)` | `low <= 0` or `high < low` |
| `normal` | `mean`, `std`, `clip_low` (default `1.0`) | `max(rng.normalvariate(mean, std), clip_low)` | `std < 0` or `clip_low <= 0` |
| `exponential` | `mean` | `rng.expovariate(1.0 / mean)` | `mean <= 0` |
| `heavy_tail` | `scale`, `shape` | `scale * rng.paretovariate(shape)` | `scale <= 0` or `shape <= 0` |

**Latency floor (`network-model.md §4`).** Every distribution must yield a
strictly-positive sample so `t_delivered > t_sent` and send/receive never
collapse to one instant. `constant`, `uniform`, `heavy_tail` are positive by
their validated params; `normal` is floored by `clip_low`. `exponential` can
in principle return `0.0` (when `rng.random()` returns exactly `0.0`); `sample`
therefore wraps every result in `max(raw, _LATENCY_FLOOR)` where
`_LATENCY_FLOOR` is a module constant (`1e-9`). The floor is a safety net, not
the primary mechanism — it only ever binds on the measure-zero `exponential`
edge case.

### 3.2 `Partition`

```python
@dataclass(frozen=True)
class Partition:
    groups: tuple[tuple[int, ...], ...]   # >= 2 disjoint groups
    symmetric: bool = True
    def blocks(self, src: int, dst: int) -> bool: ...
```

`blocks(src, dst)` — find the group containing `src` and the group containing
`dst`:

- Either endpoint in **no** group → `False` (unconstrained validators are
  reachable, `network-model-phases.md §4`).
- Both endpoints in groups → `True` iff the groups differ.

v1 asymmetric (`symmetric=False`) blocks **all** directed cross-group edges,
identically to symmetric — per-edge allowlisting is a deferred
`network-model.md §8` revision. The `symmetric` field is carried (so the
future revision is non-breaking) but does not yet change `blocks` behaviour;
this is noted in the docstring.

### 3.3 `Phase`

```python
@dataclass(frozen=True)
class Phase:
    t_start: float
    t_end:   float                       # half-open [t_start, t_end)
    delay:   DelayDist
    p_drop:  float = 0.0
    partitions: tuple[Partition, ...] = ()
```

Half-open interval per `network-model-phases.md §5`. The final phase may have
`t_end = math.inf` (open-ended run); every interior phase has finite `t_end`.

### 3.4 `validate_timeline`

```python
def validate_timeline(phases: tuple[Phase, ...],
                       registered_ids: set[int]) -> None: ...
```

Run once by `Network.start()` (§5.3), before `t = 0`. Raises `ValueError`
naming the first violation found. Checks (`network-model-phases.md §5`):

| Check | Rejection |
| :-- | :-- |
| Minimum count | zero phases |
| Coverage | `phases[0].t_start != 0` |
| Positive width | any `phase.t_start >= phase.t_end` (zero/negative width) |
| Contiguity | any `phases[i].t_end != phases[i+1].t_start` |
| Finite interior boundary | any non-final `phase.t_end` is not finite |
| Drop range | any `p_drop` not in `[0, 1)` (`1.0` forbidden — use a covering partition) |
| Partition group count | any `Partition` with `< 2` groups |
| Partition group non-empty | any empty group |
| Partition group disjoint | a `NodeId` appearing in two groups of one partition |
| Partition `NodeId` declared | a group `NodeId` absent from `registered_ids` |

The "positive width" and "finite interior boundary" checks are what make the
Decision C phase-pointer mechanism safe: they guarantee every interior
boundary is a distinct, finite, schedulable instant (§5.4).

## 4. The `Network` class — `network.py`

### 4.1 Construction and state

```python
def __init__(self, scheduler: Scheduler,
             phases: tuple[Phase, ...], global_seed: int) -> None:
```

| Field | Type | Purpose |
| :-- | :-- | :-- |
| `scheduler` | `Scheduler` | T21 scheduler; `submit_*` queues `Delivery` events on it. |
| `phases` | `tuple[Phase, ...]` | The phase timeline. Validated in `start()`, not `__init__` (the registry is not yet populated at construction). |
| `registry` | `dict[int, Node]` | `NodeId → Node`. Populated by `register()`. |
| `net_rng` | `random.Random` | Network-scoped RNG (§4.2). |
| `_phase_idx` | `int` | Index of the active phase. Initialised to `0`; advanced by `advance_phase` (§5.4). |
| `_started` | `bool` | `False` until `start()` completes; guards `submit_*` (§5.5). |

### 4.2 Determinism — network RNG (Decision D)

```python
self.net_rng = random.Random(_network_seed(global_seed))

def _network_seed(global_seed: int) -> int:
    h = hashlib.blake2b(b"network:" + str(global_seed).encode(),
                        digest_size=8)
    return int.from_bytes(h.digest(), "big")
```

`network-model-phases.md §6.1` writes `Random(seed=hash(("network",
global_seed)))`. Python's `hash()` of a tuple containing a `str` is
process-randomised (`PYTHONHASHSEED`), so the contract formula breaks
byte-identical replay across processes — the identical bug T22 fixed for the
per-Node RNG (`node-model.md §8` Revision, 2026-05-19). `blake2b` is stable
across processes and machines. The divergence is recorded as a `## Revisions`
entry on `network-model-phases.md §6.1` (§9).

The network RNG is deliberately distinct from every `Node.rng` — the network
is a system-level entity, not the property of any one validator
(`network-model-phases.md §6.1`). All delay sampling and drop coin-flipping
flow through `net_rng`; no other randomness source is permitted (forbidden
surfaces, `§6.3`).

## 5. API surface — `Network`

### 5.1 `register(node)`

```python
def register(self, node: Node) -> None:
    self.registry[node.id] = node
```

Called once per `Node` at bootstrap phase 2. O(1).

### 5.2 `bind(node)`

```python
def bind(self, node: Node) -> None:
    node.send = lambda dst, type, payload, t: \
        self.submit_unicast(node.id, dst, type, payload, t)
    node.broadcast = lambda type, payload, t: \
        self.submit_broadcast(node.id, type, payload, t)
```

Wires the network half of the outbound API (`simulation-design.md §7.2`
split-bind: the scheduler's `bind` wires `set_timer` / `cancel_timer` /
`emit`; the network's `bind` wires `send` / `broadcast`). `type` shadows the
builtin to match the `node-model.md §7` signature — consistent with the
existing `LoopbackNetwork` stub.

### 5.3 `start()`

```python
def start(self) -> None:
```

Called once at bootstrap phase 5, after registration (phase 2) and before
`Scheduler.run()` (phase 6). Steps:

1. `validate_timeline(self.phases, set(self.registry))` — fail-fast (§3.4).
2. For each **interior** boundary `i in range(len(phases) - 1)`: schedule a
   `PhaseAdvance(phase_id = i + 1)` event at `phases[i].t_end` via
   `scheduler.schedule(PhaseAdvance(i + 1), phases[i].t_end, PHASE_NODE_ID)`.
   The final phase's `t_end` (possibly `math.inf`) is **never scheduled** —
   there is no phase after it, and `Scheduler.schedule` rejects non-finite
   `t`. `validate_timeline`'s "finite interior boundary" check guarantees
   every scheduled boundary is finite.
3. Set `self._started = True`.

`PHASE_NODE_ID` is the scheduler's existing sentinel (`Scheduler.PHASE_NODE_ID
= -1`). The scheduler must also have `bind_network(self)` called (bootstrap
phase 3) so its `_dispatch` can route `PhaseAdvance` to `advance_phase`; that
call is the harness's responsibility, noted here for the bootstrap contract.

### 5.4 `advance_phase(phase_id)` — Decision C

```python
def advance_phase(self, phase_id: int) -> None:
    if not (0 <= phase_id < len(self.phases)):
        raise ValueError(
            f"advance_phase: phase_id={phase_id} out of range "
            f"[0, {len(self.phases)})")
    if phase_id != self._phase_idx + 1:
        raise RuntimeError(
            f"advance_phase: non-monotonic transition "
            f"{self._phase_idx} -> {phase_id} (expected +1)")
    self._phase_idx = phase_id
```

Invoked by `Scheduler._dispatch` when a `PhaseAdvance` event fires. The two
guards are the **3a exception surface** the human asked to be handled
exhaustively:

- **Range guard** — `phase_id` outside `[0, len(phases))` indexes a
  non-existent phase; `ValueError`.
- **Monotonicity guard** — `start()` schedules exactly one `PhaseAdvance` per
  interior boundary, in increasing order; `PhaseAdvance` is not a `TimerFire`
  and is never tombstoned, so the dispatch order is fixed. Any `phase_id` that
  is not `_phase_idx + 1` (a skip, a repeat, a regression) is a
  scheduler-wiring bug; `RuntimeError` rather than silent corruption.

**Why the pointer is correct (no boundary race).** `PhaseAdvance` carries the
sentinel `node_id = -1`. The scheduler's heap orders by `(t, node_id, seq)`,
and `-1` sorts before every real `NodeId` (`>= 0`). So at a boundary instant
`t = phases[i].t_end`, the `PhaseAdvance(i+1)` event is dispatched **before**
any `Delivery` or `TimerFire` at that same `t`. A `Node` handler running at
`t` therefore sees `_phase_idx == i + 1`, which is exactly the half-open
`[t_start, t_end)` convention ("a message sent at `t = phases[i].t_end` is in
`phases[i+1]`", `network-model-phases.md §5`). Because `submit_*` is only ever
called synchronously from inside a handler dispatched at `now`, `_phase_idx`
is always the phase containing `t_sent`. No bisect, O(1) per send.

### 5.5 `submit_unicast` / `submit_broadcast`

```python
def submit_unicast(self, src: int, dst: int,
                   type: str, payload: object, t_sent: float) -> None:
    self._guard_started()
    self._try_deliver(src, dst, type, payload, t_sent)

def submit_broadcast(self, src: int,
                     type: str, payload: object, t_sent: float) -> None:
    self._guard_started()
    for dst in sorted(self.registry):          # deterministic order (§6.3)
        if dst != src:
            self._try_deliver(src, dst, type, payload, t_sent)
```

`submit_broadcast` targets the full registry minus the sender (Decision B).
Recipients are iterated in `sorted(NodeId)` order so the per-recipient delay
samples are consumed in a fixed order (`network-model-phases.md §6.3`).

`_guard_started` raises `RuntimeError` if `submit_*` is called before
`start()` — the timeline is unvalidated and `_phase_idx` semantics are not
live until then. This is part of the 3a exception surface: it ensures no
delivery is ever scheduled against an unvalidated phase pointer.

`broadcast` is per-recipient independent (`network-model.md §4`): each
recipient gets its own drop coin, partition check, and delay sample. A
broadcast is not atomic.

### 5.6 `_try_deliver` — the five-step pipeline

```python
def _try_deliver(self, src, dst, type, payload, t_sent) -> None:
    if dst not in self.registry:                       # step 1: resolve
        raise KeyError(
            f"submit: dst={dst} not registered (configuration error)")
    phase = self.phases[self._phase_idx]
    if self.net_rng.random() < phase.p_drop:           # step 2: drop coin
        return
    if any(p.blocks(src, dst) for p in phase.partitions):  # step 3: partition
        return
    delay = phase.delay.sample(self.net_rng)           # step 4: delay
    msg = Message(src=src, dst=dst, type=type, payload=payload,
                  t_sent=t_sent)
    self.scheduler.schedule(Delivery(msg), t_sent + delay, dst)  # step 5
```

**Sampling order is pinned** (`network-model-phases.md §6.2`): drop coin
(consumes RNG) → partition check (deterministic, no RNG) → delay sample
(consumes RNG). A partition-dropped message consumes **no** delay sample, so
two runs that differ only in partition topology keep identical `net_rng`
state for every non-partitioned message.

The scheduled `Delivery` carries `node_id = dst` (the recipient) — matching
the scheduler's tie-break key `D2` ("recipient for `Delivery`") and the
existing `LoopbackNetwork` stub. When the scheduler fires the event it invokes
`registry[dst].on_message(msg, t_sent + delay)`.

An unregistered `dst` is a **configuration error** that aborts the run
(`network-model.md §3.2`: "not a runtime drop"), surfaced as `KeyError`.

## 6. Error handling — fail-fast

Consistent with the scheduler and node layers
(`simulation-design-runtime.md §3`): wrong-but-quiet is the worst outcome for
a reproducible-numbers thesis.

| Condition | Behaviour |
| :-- | :-- |
| `DelayDist` unknown `kind` / degenerate `params` | `ValueError` at construction |
| `Phase` / timeline violation (§3.4) | `ValueError` from `validate_timeline` in `start()` |
| `submit_*` before `start()` | `RuntimeError` |
| `submit_*` to an unregistered `dst` | `KeyError` (config error, aborts run) |
| `advance_phase` `phase_id` out of range | `ValueError` |
| `advance_phase` non-monotonic transition | `RuntimeError` |
| `p_drop == 1.0` | `ValueError` from `validate_timeline` |
| message dropped (coin) or blocked (partition) | silent return — no sender feedback (`network-model.md §4`) |

## 7. Testing

Test-driven: each behaviour gets a failing test before implementation.
`tests/network/` mirrors `tests/scheduler/` and `tests/nodes/`. Run:
`PYTHONPATH=src:tests/network python3 -m unittest discover -s tests/network -v`.

### 7.1 Unit

- **`test_delay_dist.py`** — each of the five `kind`s: samples strictly
  positive; degenerate `params` rejected at construction; same `rng` state →
  same sample (determinism); `normal` honours `clip_low`; `exponential`
  floored by `_LATENCY_FLOOR`.
- **`test_partition.py`** — `blocks()` truth table: same-group reachable,
  cross-group blocked, unconstrained `NodeId` reachable to/from everyone,
  asymmetric == symmetric for v1; `Network`-level multi-partition disjunctive
  composition (a message blocked iff *any* partition blocks it).
- **`test_phases.py`** — `validate_timeline`: each rejection in the §3.4 table
  fires its `ValueError`; a valid single-phase `[0, inf)` timeline and a valid
  multi-phase timeline pass.
- **`test_network.py`** — `submit_unicast` schedules one `Delivery` at
  `t_sent + delay` addressed to `dst`; `submit_broadcast` schedules to
  registry-minus-sender in sorted order; `p_drop` suppresses delivery; an
  active partition suppresses delivery; a partition-dropped message consumes
  no delay sample (assert `net_rng` state unchanged vs. a no-partition
  control); unregistered `dst` raises `KeyError`; `submit_*` before `start()`
  raises `RuntimeError`; `advance_phase` switches the active phase's params;
  `advance_phase` out-of-range raises `ValueError`; `advance_phase`
  non-monotonic raises `RuntimeError`.

### 7.2 End-to-end — `test_e2e.py`

The **real `Network`** replaces the `LoopbackNetwork` stub, driving a 2-node
ping-pong `Node` subclass through the full six-phase bootstrap to quiescence.
A `tests/network/_helpers.py` provides a minimal `PingPongNode` (a local copy
of the `tests/nodes/` one — cross-test-dir import is avoided; the run command
puts only `tests/network` on the path).

- **Build verification:** the run reaches `quiescence`; `decided` and
  `halted` events appear in the `event_sink` capture; deliveries respect the
  configured `constant` delay.
- **Network-level determinism (`network-model-phases.md §6.4`):** two
  `global_seed`-identical runs produce byte-identical delivery streams
  (`(src, dst, type, t_sent, t_delivered)` tuples). This is the network-side
  pair of the `node-model.md §8.4` node-level check. The cross-component
  scrambled-call-order test stays T25's (`TASKS.md` § Backlog).
- **Multi-phase exercise:** a 2-phase timeline (e.g. a slow phase then a fast
  phase) confirms `advance_phase` fires and later sends draw from the second
  phase's `DelayDist`.

## 8. Verification before In Review

Per the Engineer role, `superpowers:verification-before-completion` runs
before the task flips to In Review: execute the full `tests/network/` suite
**and** the existing `tests/scheduler/` and `tests/nodes/` suites (confirm no
regression — `Network` imports `Message` from `src/nodes/`), and paste the
passing output into the experiment page.

## 9. Wiki deliverables

- `wiki/experiments/2026-05-19_network-baseline.md` — build-verification page:
  config, seeds, commit hash, commands to re-run, raw result location,
  one-paragraph observation. Back-links `[[concepts/network-model]]`,
  `[[concepts/network-model-phases]]`, `[[concepts/simulation-design]]`.
- `## Revisions` entry on `wiki/concepts/network-model-phases.md §6.1` —
  records the Decision D divergence: `Random(hash(("network", global_seed)))`
  → `blake2b`-derived stable seed; notes it mirrors the `node-model.md §8`
  fix and protects byte-identical replay.
- `wiki/index.md` — add the experiment page under Experiments.
- `wiki/log.md` — one `code`-type entry for T23.
- No new concept page: `network-model.md` / `network-model-phases.md` are
  already the design contract; T23 produces code + an experiment page.

## 10. Out of scope (deferred, with owning task)

- Adversary semantics, network-layer adversary slot — T18.
- Per-protocol message `type` / `payload` contents — T16.
- Experiment harness, YAML phase-timeline loading, `global_seed` sourcing —
  T19 / T27.
- Cross-component scrambled-call-order determinism test — T25.
- Bandwidth / link-capacity model, region-aware delay, bursty/correlated
  drop, per-edge asymmetric partition allowlisting — `network-model.md §8`
  open-to-revision items.
- Repointing `broadcast` at the FSM `active_validator_set()` view — T28
  (the Decision B known limitation).
