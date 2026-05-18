# Simulation Design

Design contract for the discrete-event scheduler (`Scheduler`) that drives
the thesis simulator. Specifies the data model, public API, and
integration shape the four protocols rely on. Consumed by the W4
implementation in `src/scheduler/` (T21) and exercised by every
downstream W5+ task. Out of scope and deferred to siblings: per-protocol
FSM logic (T22, T28, T32, T38); adversary semantics (T18); experiment
harness + YAML configuration (T19, T27); unified output schema (T40).

This page closes the W3 design-contract set together with
[[concepts/node-model]] (T14), [[concepts/network-model]] +
[[concepts/network-model-phases]] (T15), and [[concepts/message-types]]
(T16). The page is split per `docs/wiki-spec.md` § Page size:

- **This page (the contract).** Discrete-event framing, structural
  decisions, scheduler state, event taxonomy, public API, harness
  integration.
- **[[concepts/simulation-design-runtime]] (the runtime companion).**
  Determinism contract, adversary boundary, failure modes, reference
  sketch in Python, open-to-revision register spanning both pages.

The visual half of the contract lives in [[diagrams/scheduler/bootstrap]],
[[diagrams/scheduler/event-enqueue]], [[diagrams/scheduler/event-dispatch]],
[[diagrams/scheduler/timer-lifecycle]], and
[[diagrams/scheduler/constraints]]; navigation hub [[diagrams/index]].
A reader can reconstruct §3–§7 below from the diagrams alone.

## 1. The discrete-event worldview

Simulation here follows the **event-scheduling worldview** of discrete-
event simulation — the standard pattern in network and consensus
simulators (ns-3, OMNeT++, the Gervais PoW simulator ([17])). Two
requirements force the design:

1. **Virtual time is owned by the scheduler.** Wall-clock-driven nodes
   block and cannot answer "what if this message takes 5 seconds?"
   Time is therefore an external authority every clock-relevant
   action flows through.
2. **Non-determinism is centralised.** T27's byte-identical
   reproducibility ([[concepts/node-model]] §8) requires every "what
   happens next" decision to live in one place with a deterministic
   rule.

[[concepts/node-model]] §6 and [[concepts/network-model-phases]] §6
forbid the Node and Network sides from reading wallclock; this page
closes the loop on the scheduler.

## 2. Two-layer commitment

Mirrors [[concepts/node-model]] §1 and [[concepts/network-model]] §2.
**Scheduler infrastructure (T17, this page)** owns the event queue,
virtual clock, dispatch loop, and determinism contract; uniform
across the four protocols; does not introspect message contents or
FSM state. **Protocol behaviour (T22, T28, T32, T38)** is the
Node-side FSM that decides what to send / set / emit; each protocol
implements its own FSM module against the `Node` contract; the
scheduler routes events without inspection.

## 3. Structural decisions

Five pinning choices. Rationale here is compressed; full discussion
lives in the engineer-register spec linked from §8.

### D1. Custom min-heap scheduler

`heapq`-based over `(t, node_id, seq, event)` tuples; no SimPy.
Determinism is easier to defend when the run loop is explicit in our
repo than when it depends on auditing a third-party library. ~100
LoC in T21.

### D2. Tie-break key `(t, node_id, seq)`

Realises [[concepts/node-model]] §8.3. `node_id` is per-event-class:
recipient for `Delivery`, owner for `TimerFire`, sentinel (`-1`) for
`PhaseAdvance`. `seq` is a per-Node monotonic counter incremented on
every `schedule()` call. Uniquely valued by construction.

### D3. Typed event classes

Heap entries carry typed dataclasses (`Delivery`, `TimerFire`,
`PhaseAdvance`), not opaque callables. Matches production DES
practice; better audit trail and schema-stable observability for T24
/ T40 plumbing.

### D4. Lazy-tombstone cancellation

`cancel_timer` updates `registry`; the heap entry is left in place
and silently skipped at pop time if its seq no longer matches.
Re-registration overwrites the registry seq and pushes a new entry,
making the old one stale. O(1) cancel; heap invariant untouched.

### D5. Three OR-composed stop conditions

`run(t_max=None, stop_when=None)` supports deadline, predicate, and
quiescence — mapping to T46/T51–T55 delay/adversarial, T41 baseline,
and T25 determinism-regression use cases respectively.
`RunResult.stopped_by` labels which fired, for T40 aggregation.

## 4. Scheduler state

Five fields. All access is via the §6 API surface.

| Field | Type | Purpose |
| :-- | :-- | :-- |
| `heap` | `list[tuple[SimTime, NodeId, int, Event]]` | Min-heap over `(t, node_id, seq, event)`. Tie-break per D2. |
| `registry` | `dict[(NodeId, TimerId), int]` | Latest valid `seq` per `(node, timer_id)`. Source of truth for "timer alive?" |
| `seq_per` | `dict[NodeId, int]` | Per-Node monotonic counter. Lazily initialised. |
| `_now` | `SimTime = 0.0` | Virtual clock. Private; exposed via `now` property. |
| `event_sink` | `Callable[..., None] \| None = None` | Optional observability hook called per non-stale pop. |

`SimTime = float` (milliseconds, per [[concepts/network-model]] §1).
`NodeId = int` (per [[concepts/node-model]] §2).
`TimerId = Any` (caller-supplied, per [[concepts/node-model]] §7).

## 5. Event taxonomy

```
@dataclass
class Delivery:      msg: Message            # per [[concepts/node-model]] §6
@dataclass
class TimerFire:     timer_id: Any; payload: Any
@dataclass
class PhaseAdvance:  phase_id: int           # per [[concepts/network-model-phases]] §5

Event = Delivery | TimerFire | PhaseAdvance
```

Three classes pin the v1 contract; the set is open in principle (new
event classes may be added by future revisions). `TimerFire` is the
only class that interacts with `registry` — the other two are
fire-and-forget once queued.

## 6. API surface

### 6.1. Construction and observability

```
Scheduler() -> Scheduler            # empty state
event_sink: Callable | None          # assignable; default None
```

### 6.2. Enqueue (single funnel)

```
schedule(event: Event, t: SimTime, node_id: NodeId) -> None
```

Validates `t >= self.now` (raises `ValueError`), increments
`seq_per[node_id]`, `heappush`es `(t, node_id, seq, event)`.
Called by `Network.submit_*` (Deliveries), `Network.start`
(PhaseAdvance), and `set_timer` (TimerFires). The only path into
the heap.

```
set_timer(node_id, timer_id, delay, payload, t) -> None
```

Validates `delay >= 0` (`delay == 0` is legal); writes
`registry[(node_id, timer_id)] = new_seq`; calls
`schedule(TimerFire(...), t + delay, node_id)`.

### 6.3. Cancel

```
cancel_timer(node_id, timer_id) -> None
```

`registry.pop((node_id, timer_id), None)`. O(1). Heap entry left in
place (lazy tombstone). No-op on unknown ids per
[[concepts/node-model]] §7.

### 6.4. Wiring

```
bind(node: Node) -> None
```

Wires `node.set_timer`, `node.cancel_timer`, `node.emit` to
scheduler-side implementations curried on `node.id`. Does **not**
wire `send` / `broadcast` — that is `Network.bind`'s half. See §7.2.

### 6.5. Run

```
@dataclass
class RunResult:
    stopped_by: Literal['quiescence','deadline','predicate']
    now: SimTime
    events_processed: int
    events_tombstoned: int

run(t_max: SimTime | None = None,
    stop_when: Callable[[], bool] | None = None) -> RunResult
```

One iteration of the loop (visual:
[[diagrams/scheduler/event-dispatch]]):

```
while heap:
    if t_max is not None and now >= t_max:
        return RunResult('deadline', ...)
    t, node_id, seq, ev = heappop(heap)
    self._now = t
    if isinstance(ev, TimerFire) \
       and registry.get((node_id, ev.timer_id)) != seq:
        continue                              # tombstoned
    if event_sink is not None:
        event_sink(t, node_id, seq, ev)
    # dispatch by event class:
    #   Delivery     -> node.on_message
    #   TimerFire    -> node.on_timer
    #   PhaseAdvance -> network.advance_phase
    dispatch(ev, node_id, t)
    if stop_when is not None and stop_when():
        return RunResult('predicate', ...)
return RunResult('quiescence', ...)
```

Determinism guarantees, fail-fast on contract violations, and the
empty-run case are specified in
[[concepts/simulation-design-runtime]] §1 and §3.

### 6.6. Read-only

```
@property now(self) -> SimTime
```

Returns `self._now`. Node handlers do **not** read this; they receive
`t` as a parameter per [[concepts/node-model]] §6.

## 7. Integration

### 7.1. New inbound seams (registered as Revisions on T14 / T15)

This contract extends two existing contracts; both extensions land as
`## Revisions` entries on the respective wiki pages.

| Page | Section | New seam |
| :-- | :-- | :-- |
| [[concepts/node-model]] | §6 | `Node.start(t: SimTime) -> None` — called once during bootstrap phase 5; FSM uses this to schedule initial timers and emit first messages. |
| [[concepts/network-model]] | §5 | `Network.start() -> None` — called once during bootstrap phase 5; schedules `PhaseAdvance` events at phase boundaries. |

### 7.2. Bootstrap (six phases, harness-driven)

Visual: [[diagrams/scheduler/bootstrap]].

| Phase | Step |
| :-: | :-- |
| 1 | Construct `Scheduler`, `Network`, `Node × n`. |
| 2 | `Network.register(node)` per Node. |
| 3 | `Scheduler.bind(node)` + `Network.bind(node)` per Node (split ownership). |
| 4 | `scheduler.event_sink = logger.sink`. |
| 5 | `Network.start()` + `Node.start(t=0)` per Node — populates the heap. |
| 6 | `scheduler.run(t_max, stop_when) -> RunResult`. |

**Split bind, no cycle.** Scheduler wires `set_timer` / `cancel_timer`
/ `emit`. Network wires `send` / `broadcast`. The harness calls both.
No `Scheduler → Network` reference is ever created; Network already
holds a scheduler ref from its constructor.

## 8. Sources

Design contract; no primary-literature citations. Companion wiki page:
[[concepts/simulation-design-runtime]] — determinism, adversary
boundary, failure modes, reference sketch, open-to-revision register
spanning both pages.

**Implementation-planning spec:**

- `docs/superpowers/specs/2026-05-13-t17-scheduler-design.md` —
  engineer-register companion (476 lines, 10 sections) consumed by
  `superpowers:writing-plans` when T21 picks up. Carries the full §3
  decision rationale the wiki pages compressed.

**Inbound (existing wiki pages):**

- [[concepts/node-model]] §6 / §7 / §8 / §9 — inbound hooks,
  outbound API, determinism, adversary attachment.
- [[concepts/network-model]] §1 / §3 / §5 / §6 +
  [[concepts/network-model-phases]] §5 / §6 — delivery pipeline,
  envelope, integration, phase timeline, determinism.
- [[concepts/message-types]] — per-protocol wire-level catalog.
- [[concepts/evaluation-metrics]] — T9.1 metric reconciliation;
  consumes the event stream via `event_sink`.

**Visual contract:** [[diagrams/scheduler/bootstrap]],
[[diagrams/scheduler/event-enqueue]],
[[diagrams/scheduler/event-dispatch]],
[[diagrams/scheduler/timer-lifecycle]],
[[diagrams/scheduler/constraints]] under [[diagrams/index]].

**Forward references (sibling pages, not yet authored):**
[[concepts/adversary-model]] (T18, fills the runtime §2 boundary);
[[concepts/experiment-matrix]] (T19, consumes §6.5 `run()` via the
harness); [[concepts/reproducibility]] (T27, exercises the runtime
§1 determinism contract); [[concepts/output-format]] (T40, consumes
`event_sink` for CSV columns).

## 9. Revisions

### [2026-05-18] T21 implementation — R1: scheduler dispatch references

§6.4 / §7 left unspecified *how* the scheduler holds the `Node` and
`Network` references its `run()` dispatch calls. T21 resolves this:
`bind(node)` additionally registers the node in `Scheduler.nodes:
dict[NodeId, Node]`, and a new `bind_network(network)` method (bootstrap
phase 3) sets `Scheduler.network`. §6.3's "no `Scheduler → Network`
reference" forbids the *outbound-binding cycle* (`set_timer` / `send`
cross-wiring); a dispatch-only handle for `PhaseAdvance` does not create
that cycle.

### [2026-05-18] T21 implementation — R2: `schedule()` returns `seq`

§6.2 described `set_timer` as computing its own `seq` *and*
funnelling through `schedule()`, which also assigns a `seq` — a double
increment that desynchronises the registry seq from the heap entry's seq
and breaks the tombstone check. T21 resolves this: `schedule()` returns
the `seq` it assigned (`-> int`, not `-> None`); `set_timer` funnels
through `schedule()` once and registers the returned value. The
single-funnel invariant (§6.2) is preserved.
