# T17 — Discrete-Event Scheduler Design

**Task:** T17 (Engineer)
**Date:** 2026-05-13
**Outcome:** Design contract for the discrete-event scheduler that drives the
four-protocol consensus simulator (PBFT, Casper FFG, Snowman, Narwhal+Tusk).
**Consumed by:** `superpowers:writing-plans` (next), then T21 (implementation
in `src/scheduler/`), then [[concepts/simulation-design]] (wiki page write
following the W3 reference-sketch + revisions convention).

---

## 1. Goal

Define the design contract for `Scheduler` — the discrete-event simulation
engine that owns virtual time, holds the event queue, dispatches events to
`Node` and `Network` handlers, and provides the deterministic substrate on
which T27's "byte-identical replay from a seed" claim rests.

**In scope.** The scheduler's data model, public API, run-loop semantics,
determinism contract, observability surface, failure modes, and integration
with the existing `Node` and `Network` contracts.

**Out of scope.** The implementation itself (T21), protocol-specific FSM
logic (T22/T28/T32/T38), the experiment harness (T19/T27), the unified
output schema (T40), and adversary semantics (T18).

---

## 2. Context — upstream contracts taken as given

This spec composes with three upstream design contracts already on the wiki.
The decisions in §3 take their content as given and do not re-debate them.

| Upstream contract | Role |
| :-- | :-- |
| [[concepts/node-model]] (T14) | Declares the `Node` class. Specifies inbound hooks (`on_message`, `on_timer`), outbound API (`send`, `broadcast`, `set_timer`, `cancel_timer`, `emit`), determinism rules (§8), adversary attachment surface (§9). |
| [[concepts/network-model]] (T15) | Declares the `Network` class. Specifies the `Message` envelope (§3.1), endpoint resolution (§3.2), the five-step delivery pipeline (§1), outbound API integration (§5), the honest-infrastructure adversary boundary (§6). |
| [[concepts/network-model-phases]] (T15) | Per-phase configuration mechanics — delay distributions, drop coin, partition predicate, phase timeline (§5), network-level determinism contract (§6). |
| [[concepts/message-types]] (T16) | Per-protocol wire-level message catalog. Scheduler is type-agnostic but must produce enough observability for T40's CSV columns to be computed. |

---

## 3. Decisions

Five structural decisions taken during the brainstorm phase. Each carries a
one-line statement and the rationale that locked it in.

### D1. Framework: custom min-heap (not SimPy)

**Decision.** Custom min-heap scheduler over `(t, node_id, seq, event)`
tuples (~100 LoC). No SimPy, no third-party DES library.

**Rationale.** T27's byte-identical event-order claim is easier to defend
when the run loop is explicit in our repo than when it depends on auditing
a third-party library. The protocols are inherently callback-shaped
(`on_message`, `on_timer`); SimPy's generator/process model solves a problem
we do not have. Cost: ~100 LoC of scheduler skeleton in T21.

### D2. Tie-break key: `(t, node_id, seq)` with per-class `node_id`

**Decision.** When two heap entries share `t`, sort by `(t, node_id, seq)`
where:
- `node_id` is the recipient for `Delivery`, the owner for `TimerFire`, and
  a sentinel (`NodeId = -1`) for `PhaseAdvance`.
- `seq` is a per-Node monotonic counter, incremented at every `schedule()`
  call.

**Rationale.** Keeps [[concepts/node-model]] §8.3 intact (no Revisions
amendment needed). The per-class `node_id` interpretation resolves the
ambiguity (whose NodeId? sender's or recipient's?) left open upstream.
Event logs are readable: all of NodeA's same-time events group before
NodeB's.

### D3. Event shape: typed dataclasses (not opaque callables)

**Decision.** Heap entries carry typed event objects, not opaque callables.
Initial event taxonomy:
- `Delivery(msg: Message)` — a message arriving at a Node.
- `TimerFire(timer_id: Any, payload: Any)` — a Node's self-scheduled wake-up.
- `PhaseAdvance(phase_id: int)` — a network-phase boundary transition.

**Rationale.** Typed events match production discrete-event simulators
(`ns-3`, `OMNeT++`, Algorand's internal sim, the Gervais PoW sim cited as
[17] in the bibliography). Better audit trail, schema-stable observability,
cleaner T24 plumbing. Cost: ~30–50 LoC of dispatch dataclasses in T21.
Note: these are *scheduler-domain* types, not *protocol-domain* — the
scheduler still does not know what PBFT is.

### D4. Timer cancellation: lazy tombstone

**Decision.** `cancel_timer` removes the entry from
`registry: dict[(NodeId, TimerId), int]`. The corresponding heap entry is
left in place; at pop time the scheduler checks
`registry.get((node_id, timer_id)) == event.seq` and silently skips stale
events. Re-registration with the same `timer_id` overwrites the registry
seq and pushes a new heap entry; the old one becomes stale by definition.

**Rationale.** Cancel is O(1). Heap invariant is never touched.
Re-registration semantics ([[concepts/node-model]] §7) are realised
naturally. Garbage (stale heap entries) is bounded by cancel frequency,
which is small at thesis scale.

### D5. Stop conditions: three, OR-composed

**Decision.** `Scheduler.run(t_max=None, stop_when=None)` accepts up to
three stop conditions:
- `t_max: SimTime | None` — deadline. Loop exits when `now >= t_max` after
  a pop.
- `stop_when: Callable[[], bool] | None` — predicate. Loop exits when it
  returns true after a dispatch.
- Quiescence — loop exits naturally when the heap drains.

`RunResult.stopped_by` records which one fired
(`'quiescence' | 'deadline' | 'predicate'`).

**Rationale.** Each maps to a real thesis experiment use case. T41
baseline experiments use predicate ("stop when k blocks committed").
T46/T47 delay experiments use deadline ("run for 60s, measure how far we
got"). T25 determinism regression tests use quiescence ("run to
completion, compare event streams"). One scheduler, three stop modes, no
ambiguity at run-result-labeling time.

---

## 4. Architecture

### 4.1. Scheduler state

The `Scheduler` class holds five fields. All other components access state
only via the public method surface in §5.

```python
class Scheduler:
    heap:       list[tuple[SimTime, NodeId, int, Event]]   # min-heap (heapq)
    registry:   dict[tuple[NodeId, TimerId], int]           # latest valid seq per timer
    seq_per:    dict[NodeId, int]                           # per-Node monotonic counter
    _now:       SimTime = 0.0                                # private; exposed via `now` property
    event_sink: Callable[[SimTime, NodeId, int, Event], None] | None = None
```

**The heap.** Min-heap on the 4-tuple `(t, node_id, seq, event)`. Python's
`heapq` operates in-place on a list; the tuple sorts lexicographically. The
fourth element (`event`) is never compared because the first three uniquely
identify the entry — `seq` is strictly monotonic per `node_id`.

**The registry.** Source of truth for "is this timer still alive?" Mutated
by `set_timer` (write) and `cancel_timer` (delete). Read at pop time to
gate `TimerFire` dispatch.

**Per-Node sequence counters.** `seq_per[node_id]` is incremented before
being assigned. Lazily initialised: `seq_per.get(node_id, 0) + 1` produces
`seq=1` for the first event scheduled for any Node.

**Virtual time.** Monotonically non-decreasing. Only the run loop writes
via `self._now = t` on pop. Public access is via the `now` property
(read-only).

**Event sink.** Optional. If set, called on every popped non-stale event
before dispatch. T24 wires its logger here.

### 4.2. Event taxonomy

```python
@dataclass
class Delivery:
    msg: Message       # node-model §6

@dataclass
class TimerFire:
    timer_id: Any
    payload:  Any

@dataclass
class PhaseAdvance:
    phase_id: int      # network-model-phases §5

Event = Delivery | TimerFire | PhaseAdvance
```

Three event classes. Two carry a small payload; `PhaseAdvance` carries
only an index. The set is open in principle — new event classes may be
added by future revisions — but the v1 contract pins exactly these three.

---

## 5. API surface

Public methods of `Scheduler`. Each has exactly one job.

### 5.1. Construction and configuration

```python
def __init__(self) -> None
```

Initialise empty state. No arguments.

```python
event_sink: Callable[[SimTime, NodeId, int, Event], None] | None
```

Public attribute. Assignable. Default `None`.

### 5.2. Enqueue

```python
def schedule(self, event: Event, t: SimTime, node_id: NodeId) -> None
```

The single funnel into the heap. All other enqueue methods funnel through
this.

- Validates `t >= self.now`. Raises `ValueError` otherwise.
- `seq = next_seq(node_id)`.
- `heappush(self.heap, (t, node_id, seq, event))`.

```python
def set_timer(self, node_id: NodeId, timer_id: TimerId,
              delay: SimTime, payload: Any, t: SimTime) -> None
```

Schedule a `TimerFire` for a Node.

- Validates `delay >= 0`. Raises `ValueError` otherwise. (`delay == 0` is
  legal — fires on the next iteration.)
- `seq = next_seq(node_id)`.
- `self.registry[(node_id, timer_id)] = seq`.
- `self.schedule(TimerFire(timer_id, payload), t + delay, node_id)`.

### 5.3. Cancel

```python
def cancel_timer(self, node_id: NodeId, timer_id: TimerId) -> None
```

`self.registry.pop((node_id, timer_id), None)`. No-op on unknown ids. Heap
entry untouched (lazy tombstone).

### 5.4. Wiring

```python
def bind(self, node: Node) -> None
```

Wires Node's outbound API for the methods Scheduler owns. After
`bind(node)`:

- `node.set_timer(timer_id, delay, payload, t)` calls
  `self.set_timer(node.id, timer_id, delay, payload, t)`.
- `node.cancel_timer(timer_id)` calls
  `self.cancel_timer(node.id, timer_id)`.
- `node.emit(event_type, fields, t)` routes through `self.event_sink` (if
  set) as an `EmitWrapper` event.

Does **not** wire `send` / `broadcast`. Those are `Network.bind`'s half
(see §6 integration).

### 5.5. Run

```python
@dataclass
class RunResult:
    stopped_by:        Literal['quiescence', 'deadline', 'predicate']
    now:               SimTime
    events_processed:  int
    events_tombstoned: int

def run(self, t_max: SimTime | None = None,
        stop_when: Callable[[], bool] | None = None) -> RunResult
```

The main loop. Pseudocode for one iteration:

```
while heap:
    if heap empty:
        return RunResult('quiescence', now, n_processed, n_tombstoned)
    if t_max is not None and now >= t_max:
        return RunResult('deadline', now, n_processed, n_tombstoned)
    t, node_id, seq, ev = heappop(heap)
    self._now = t
    if isinstance(ev, TimerFire) \
       and registry.get((node_id, ev.timer_id)) != seq:
        n_tombstoned += 1
        continue
    if event_sink is not None:
        event_sink(t, node_id, seq, ev)
    dispatch(ev, node_id, t)             # by event class
    n_processed += 1
    if stop_when is not None and stop_when():
        return RunResult('predicate', now, n_processed, n_tombstoned)
return RunResult('quiescence', now, n_processed, n_tombstoned)
```

`dispatch` is class-based:
- `Delivery` → `node.on_message(ev.msg, t)`
- `TimerFire` → `node.on_timer(ev.timer_id, ev.payload, t)`
- `PhaseAdvance` → `network.advance_phase(ev.phase_id)`

### 5.6. Read-only

```python
@property
def now(self) -> SimTime
```

Returns `self._now`. Read-only; the underlying field is private. Per
[[concepts/node-model]] §6, Node handlers do not call this — they receive
`t` as a parameter.

---

## 6. Integration

### 6.1. New seams added by T17

This spec extends two existing contracts; both extensions land as
`## Revisions` entries on the respective wiki pages when T17 is finalised.

| Contract | Extension |
| :-- | :-- |
| [[concepts/node-model]] §6 (Inbound hook surface) | Add `start(t: SimTime) -> None` as a third inbound hook, called once by the harness during bootstrap phase 5. The Node's FSM uses this to schedule its initial timers and emit its first messages. Without it, the heap could never be populated before `run()` begins. |
| [[concepts/network-model]] §5 (Outbound API integration) | Add `Network.start() -> None` as a one-shot kickoff. Schedules the `PhaseAdvance` events at phase boundaries. Internal-only; not part of the Node-facing API. |

### 6.2. Bootstrap sequence

Six phases, all driven by the harness. Visual: [[diagrams/scheduler/bootstrap]].

| Phase | Step | Owner |
| :-- | :-- | :-- |
| 1. Construct | `Scheduler()`, `Network(scheduler, phases, net_rng)`, `Node(id, weight, rng)` ×N | Harness |
| 2. Register | `Network.register(node)` per Node | Harness |
| 3. Bind | `Scheduler.bind(node)` + `Network.bind(node)` per Node | Harness |
| 4. Observe | `scheduler.event_sink = logger.sink` | Harness |
| 5. Kickoff | `Network.start()` + `Node.start(t=0)` per Node | Harness |
| 6. Run | `scheduler.run(t_max, stop_when) -> RunResult` | Harness |

### 6.3. Outbound API binding (split ownership)

Two components, two halves.

| Wired by | Method on Node | Routes to |
| :-- | :-- | :-- |
| `Scheduler.bind` | `set_timer` | `Scheduler.set_timer` |
| `Scheduler.bind` | `cancel_timer` | `Scheduler.cancel_timer` |
| `Scheduler.bind` | `emit` | `Scheduler.event_sink` (if set) |
| `Network.bind` | `send` | `Network.submit_unicast` |
| `Network.bind` | `broadcast` | `Network.submit_broadcast` |

No `Scheduler → Network` reference is created. The Network's `submit_*`
methods call back into the scheduler via the existing scheduler reference
Network was constructed with.

---

## 7. Constraints

### 7.1. Determinism

**Claim.** Same `global_seed` + same configuration → byte-identical event
stream produced via `event_sink`.

**Mechanisms.**
- Heap key `(t, node_id, seq)` is uniquely valued by construction (per D2).
- `now` is monotonically non-decreasing.
- `seq_per` increments only via `schedule()`; values are never reused.
- Scheduler holds no RNG. Network (`net_rng`) and Node (`self.rng`) hold
  the only RNGs.
- `schedule()` validates `t >= self.now` — no time travel.
- Iteration over `registry` is never required; access is by key only.
- Exception in a handler propagates out of `run()` — failure is loud.

**Test surface (T25).** Two `global_seed`-identical runs MUST produce
identical `event_sink` streams. Determinism regression test compares two
captures and asserts byte-equality.

### 7.2. Observability

Two surfaces:

1. **`event_sink`** — called per event pop, after tombstone check, before
   dispatch. Carries `(t, node_id, seq, event)`. T24 plumbing target.
2. **`Node.emit`** — wired by `Scheduler.bind` to flow through the same
   `event_sink`, distinguishable by event class.

The scheduler does not compute metrics. T40 derives latency, throughput,
finality, fork rate, etc., from the event stream produced via these two
surfaces.

### 7.3. Adversary boundary

The scheduler has **no** adversary attachment slot.

Per [[concepts/node-model]] §9 and [[concepts/network-model]] §6, all
adversary semantics live at `Node.adversary`. By the time a call reaches
`Scheduler.schedule`, adversary modifications have already been applied at
the Node boundary. The scheduler is unaware.

If a future research question requires a scheduler-level adversary (e.g.,
event reordering at the queue layer), that lands as a `## Revisions` entry
on this spec. The v1 contract intentionally omits this slot.

### 7.4. Failure modes (fail-fast)

| Condition | Behaviour |
| :-- | :-- |
| `schedule(event, t, node_id)` with `t < self.now` | `ValueError` raised by `schedule()` |
| `set_timer(..., delay)` with `delay < 0` | `ValueError` raised by `set_timer()` |
| Exception inside any handler | propagates out of `run()`; scheduler does not catch |
| Exception inside `event_sink` callback | propagates out of `run()`; T24 wraps its own `try/except` if needed |
| `t_max <= self.now` at start of `run()` | returns immediately with `stopped_by='deadline'` (not an error — an empty run) |
| `Delivery.msg.dst` not in `Network.registry` | caught by `Network.submit_unicast` before reaching scheduler |

**Why fail-fast.** For a thesis whose central artifact is "this experiment
can be re-run and you get the same numbers," wrong-but-quiet is the worst
outcome — far worse than crashing with a clear traceback that says "delay
= −1 at line 47."

---

## 8. Visual contract

The five Mermaid `sequenceDiagram` diagrams below are the binding visual
specification for this spec. A reader who reads only these diagrams
should be able to reconstruct §4–§7 above.

- [[diagrams/scheduler/bootstrap]] — six-phase bootstrap sequence.
- [[diagrams/scheduler/event-enqueue]] — three sources funnelling through
  `schedule()`.
- [[diagrams/scheduler/event-dispatch]] — one iteration of `run()`, three
  exit paths.
- [[diagrams/scheduler/timer-lifecycle]] — set / cancel / overwrite / fire
  under lazy tombstone.
- [[diagrams/scheduler/constraints]] — adversary boundary, determinism
  rules, fail-fast gates.

Navigation entry point: [[diagrams/index]] (also contains the legend for
the Mermaid syntax used).

---

## 9. Upstream Revisions register

T17 lands these `## Revisions` entries on upstream pages as part of its
merge. They do not block this spec; they accompany it.

| Target | Section | Amendment |
| :-- | :-- | :-- |
| [[concepts/node-model]] | §6 (Inbound hook surface) | Add `start(t: SimTime) -> None` as a third inbound hook. Triggered once by the harness during bootstrap phase 5. The Node's FSM uses this to schedule its initial timers / messages. |
| [[concepts/network-model]] | §5 (Outbound API integration) | Add `Network.start() -> None`. Schedules `PhaseAdvance` events at phase boundaries during bootstrap phase 5. |

---

## 10. Handoff

This spec is consumed by, in order:

1. **`superpowers:writing-plans`** — produces an implementation plan for
   T21 referencing this document as the binding contract.
2. **T17 wiki pages** — split into `wiki/concepts/simulation-design.md`
   (contract: §1–§7 of this spec) + `wiki/concepts/simulation-design-runtime.md`
   (runtime obligations: §7–§10 of this spec, plus reference sketch and
   open-to-revision register). Split applied to comply with
   `docs/wiki-spec.md` § Page size; same precedent as
   `network-model` / `network-model-phases`. The spec is for engineers;
   the wiki pages are for future-self and the thesis defence.
3. **T21 implementation** — read this spec plus the diagrams, implement
   `src/scheduler/`, drive correctness via T22-style unit tests.

Forward references that land elsewhere:
- T22 (Node implementation) — consumes the `start(t)` seam.
- T23 (Network implementation) — consumes the `Network.start()` seam.
- T24 (logging) — consumes `event_sink`.
- T25 (tests) — exercises determinism, tombstone, and stop-condition
  paths.
- T27 (reproducibility) — wraps a `global_seed` and asserts byte-identical
  replay.
- T40 (output format) — consumes the event stream to project CSV columns.
