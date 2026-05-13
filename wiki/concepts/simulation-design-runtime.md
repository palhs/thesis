# Simulation Design — Runtime

Companion page to [[concepts/simulation-design]] (T17). The main page
pins the data model, public API, and integration shape; this page pins
the runtime obligations the implementation (T21) must hold, plus an
illustrative Python reference sketch and the consolidated
open-to-revision register spanning both pages. Out of scope and
deferred to siblings: per-protocol FSM logic (T22, T28, T32, T38);
adversary semantics (T18); experiment harness + YAML configuration
(T19, T27); unified output schema (T40).

The split from [[concepts/simulation-design]] follows
`docs/wiki-spec.md` § Page size. Read the main page first for the
contract surface (sections §1–§7); this page assumes that contract as
given.

## 1. Determinism contract

**Claim.** Same `global_seed` + same configuration → byte-identical
event stream emitted via `event_sink`. This is T27's core promise and
the scheduler is one of three components that must hold it (the
others — `Node` and `Network` — close their halves in
[[concepts/node-model]] §8 and [[concepts/network-model-phases]] §6).

**Mechanisms.**

| Mechanism | Effect |
| :-- | :-- |
| Heap key `(t, node_id, seq)` uniquely valued by construction (per [[concepts/simulation-design]] §3 D2) | No ambiguous ordering of simultaneous events. |
| `now` monotonically non-decreasing; only written on pop | No clock rewinds. |
| `schedule()` validates `t >= self.now` | No time travel. |
| `seq_per` increments only via `schedule()`; values never reused | No tie-break collisions even on overwrite. |
| Scheduler holds no RNG | All randomness lives in `Network.net_rng` and `Node.self.rng`. |
| `registry` accessed by key, never iterated | Dict-key access is deterministic. |
| Handler exception propagates out of `run()` | Failure is loud; T25 detects regressions. |

**Test surface (T25).** Two `global_seed`-identical runs MUST produce
identical `event_sink` capture sequences. Determinism regression test
compares two captures and asserts byte-equality.

**Observability surface.** The scheduler exposes one structured
observability point — `event_sink`, called per non-stale event pop
after the tombstone check and before dispatch
([[diagrams/scheduler/event-dispatch]]). T24 wires its logger here.
Node-level `emit` is also routed through `event_sink` by
`Scheduler.bind` ([[concepts/simulation-design]] §6.4). The scheduler
does not compute metrics — T40 derives latency, throughput, finality,
and fork rate from the event stream produced via these two surfaces.

## 2. Adversary boundary

The scheduler has **no** adversary attachment slot.

Per [[concepts/node-model]] §9 and [[concepts/network-model]] §6, all
adversary semantics live at `Node.adversary` and gate the Node's
outbound API before any call reaches `Network.submit_*` or
`Scheduler.schedule`. By the time data reaches the scheduler,
adversarial behaviour has already been applied at the Node boundary.
Network is also unaware; the scheduler closes the loop.

Honest reason: in real distributed systems, the scheduler is not a
network element you can attack. Real-world equivalents are kernel
schedulers and event loops, which adversaries do not have direct
access to. Modelling a scheduler-layer adversary would simulate a
threat with no production analogue. If a future RQ requires one
(e.g., event reordering at the queue layer to study scheduler-
implementation bugs), that lands as a `## Revisions` entry on this
page; v1 intentionally omits the slot.

Visual: [[diagrams/scheduler/constraints]] §"adversary boundary"
shows the gate happening at the Node boundary; the scheduler only
sees post-adversary calls.

## 3. Failure modes (fail-fast)

| Condition | Behaviour |
| :-- | :-- |
| `schedule(event, t)` with `t < self.now` | `ValueError` raised by `schedule()` |
| `set_timer(..., delay)` with `delay < 0` | `ValueError` raised by `set_timer()` |
| Exception inside any handler (`on_message`, `on_timer`, `network.advance_phase`) | propagates out of `run()`; scheduler does not catch |
| Exception inside `event_sink` callback | propagates out of `run()`; T24 wraps its own `try/except` if it wants graceful logging |
| `t_max <= self.now` at start of `run()` | returns immediately with `stopped_by='deadline'` (not an error — an empty run) |
| `Delivery.msg.dst` not in `Network.registry` | caught by `Network.submit_unicast` before reaching scheduler ([[concepts/network-model]] §3.2) |

For a thesis whose central artefact is reproducible numbers,
wrong-but-quiet is the worst outcome. The scheduler crashes loudly
on contract violations so bugs surface at the first run, not three
weeks into result analysis.

**`delay == 0` is allowed.** A zero-delay `TimerFire` is scheduled at
`self.now` and pops on the next iteration — the tie-break key sorts
it after the current handler's continuation because `seq` increments
on every `schedule()` call. This is the natural "yield to the
scheduler" idiom for protocols that want to schedule self-callbacks
without advancing virtual time.

## 4. Reference sketch (illustrative, non-binding)

Per the W3 design-contract style. T21 may diverge; divergences land
as `## Revisions` entries on the relevant page.

```python
# Reference sketch — illustrative, non-binding.
import heapq
from dataclasses import dataclass
from typing import Any, Callable, Literal

SimTime = float
NodeId  = int
TimerId = Any

@dataclass
class Delivery:     msg: "Message"
@dataclass
class TimerFire:    timer_id: Any; payload: Any
@dataclass
class PhaseAdvance: phase_id: int
Event = Delivery | TimerFire | PhaseAdvance

@dataclass
class RunResult:
    stopped_by: Literal['quiescence','deadline','predicate']
    now: SimTime
    events_processed:  int
    events_tombstoned: int

class Scheduler:
    PHASE_NODE_ID: NodeId = -1                       # sentinel (D2)

    def __init__(self) -> None:
        self.heap: list = []
        self.registry: dict[tuple[NodeId, TimerId], int] = {}
        self.seq_per:  dict[NodeId, int] = {}
        self._now: SimTime = 0.0
        self.event_sink: Callable | None = None

    @property
    def now(self) -> SimTime: return self._now

    def _next_seq(self, node_id: NodeId) -> int:
        s = self.seq_per.get(node_id, 0) + 1
        self.seq_per[node_id] = s
        return s

    def schedule(self, event: Event, t: SimTime,
                 node_id: NodeId) -> None:
        if t < self._now:
            raise ValueError("schedule in the past")
        seq = self._next_seq(node_id)
        heapq.heappush(self.heap, (t, node_id, seq, event))

    def set_timer(self, node_id: NodeId, timer_id: TimerId,
                  delay: SimTime, payload: Any, t: SimTime) -> None:
        if delay < 0:
            raise ValueError("negative timer delay")
        seq = self._next_seq(node_id)
        self.registry[(node_id, timer_id)] = seq
        heapq.heappush(
            self.heap,
            (t + delay, node_id, seq, TimerFire(timer_id, payload)),
        )

    def cancel_timer(self, node_id: NodeId,
                     timer_id: TimerId) -> None:
        self.registry.pop((node_id, timer_id), None)

    def bind(self, node) -> None:
        node.set_timer = lambda tid, d, p, t: \
            self.set_timer(node.id, tid, d, p, t)
        node.cancel_timer = lambda tid: \
            self.cancel_timer(node.id, tid)
        node.emit = lambda et, fs, t: (
            self.event_sink(t, node.id, -1, ("emit", et, fs))
            if self.event_sink else None
        )

    def run(self, t_max: SimTime | None = None,
            stop_when: Callable[[], bool] | None = None) -> RunResult:
        n_proc = n_tomb = 0
        while self.heap:
            if t_max is not None and self._now >= t_max:
                return RunResult('deadline', self._now, n_proc, n_tomb)
            t, nid, seq, ev = heapq.heappop(self.heap)
            self._now = t
            if isinstance(ev, TimerFire) \
               and self.registry.get((nid, ev.timer_id)) != seq:
                n_tomb += 1
                continue
            if self.event_sink:
                self.event_sink(t, nid, seq, ev)
            # dispatch elided — calls node.on_message / on_timer /
            # network.advance_phase keyed on type(ev)
            n_proc += 1
            if stop_when is not None and stop_when():
                return RunResult('predicate', self._now, n_proc, n_tomb)
        return RunResult('quiescence', self._now, n_proc, n_tomb)
```

## 5. Open to revision

Consolidated register spanning both halves of T17 (contract on
[[concepts/simulation-design]], runtime on this page). The contract
is precise but not final; items below are expected to be re-examined
as T21+ implementation reveals fit issues. Each change beyond a
typo lands as a `## Revisions` entry per `docs/wiki-spec.md`
§ Revisions rule, on the page that hosts the affected section.

- **Sentinel `node_id = -1`** ([[concepts/simulation-design]] §4).
  Reserved for `PhaseAdvance`. T19 / T27 may introduce additional
  non-Node event classes (e.g., experiment-harness checkpoints); if
  so, the sentinel scheme generalises to a named constant per class
  or a `NodeId | None` slot.
- **`event_sink` signature** ([[concepts/simulation-design]] §4 /
  §6.1; this page §1). Tuple `(t, node_id, seq, event)`. T24 may want
  richer context (e.g., `events_processed` count); if so, the sink
  signature widens to a small dataclass.
- **Tombstone garbage** ([[concepts/simulation-design]] §3 D4 / §6.3;
  this page §3). Heap may accumulate stale entries proportional to
  cancel frequency. Bounded at thesis scale; if T21 stress tests show
  pathological growth, switch to indexed-heap with O(log n) eager
  cancel.
- **`Node.start(t)` seam** ([[concepts/simulation-design]] §7.1). New
  inbound hook on the Node contract. If protocol FSM implementations
  find one-shot kickoff insufficient (e.g., need a "pre-network-ready"
  and a "post-network-ready" call), splits into a two-phase start
  hook.
- **Adversary slot at scheduler layer** (this page §2). Intentionally
  absent. If a future RQ requires modelling event reordering /
  duplication at the queue layer (e.g., to study scheduler-
  implementation bugs), introduce `SchedulerAdversaryProfile`.

## 6. Sources

Companion to a design contract; no primary-literature citations.
Methodological lineage notes in [[concepts/simulation-design]] §1.

**Parent page:**

- [[concepts/simulation-design]] — the contract this page extends.
  §1 frames the discrete-event worldview; §3 D1–D5 pin the structural
  decisions whose runtime consequences this page specifies; §6 pins
  the API surface whose determinism, failure, and reference behaviour
  live here.

**Inbound (existing wiki pages):**

- [[concepts/node-model]] §8 — Node-side determinism contract paired
  with §1 here.
- [[concepts/network-model-phases]] §6 — Network-side determinism
  contract paired with §1 here.
- [[concepts/node-model]] §9 / [[concepts/network-model]] §6 — close
  the §2 adversary boundary on the Node and Network sides.
- [[concepts/evaluation-metrics]] — consumes the §1 observability
  surface (event stream + Node-emitted events) to derive metrics
  downstream.

**Visual contract:**

- [[diagrams/scheduler/event-dispatch]] — visualises the §1 run-loop
  determinism gates and §3 fail-fast exit paths.
- [[diagrams/scheduler/timer-lifecycle]] — visualises the §3 timer
  lifecycle invariants (set / cancel / overwrite / fire).
- [[diagrams/scheduler/constraints]] — visualises §2 adversary
  boundary, the absence of RNG / wallclock, and the §3 fail-fast
  gates in one place.

**Forward references (sibling pages, not yet authored):**

- [[concepts/adversary-model]] (T18) — fills the §2 boundary.
- [[concepts/reproducibility]] (T27) — exercises the §1 determinism
  contract via `global_seed` injection.
- [[concepts/output-format]] (T40) — consumes the §1 observability
  surface to project CSV columns.

## 7. Revisions

None.
