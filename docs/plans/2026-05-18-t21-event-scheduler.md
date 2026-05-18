# T21 — Event Scheduler Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement `src/scheduler/` — the discrete-event scheduler that owns
virtual time, holds the event queue, and dispatches events to `Node` and
`Network` handlers — with unit tests and one end-to-end test proving it drives
a simulation to completion.

**Architecture:** A custom min-heap scheduler over `(t, node_id, seq, event)`
tuples (no SimPy), per the binding spec
`docs/superpowers/specs/2026-05-13-t17-scheduler-design.md` and the design
contract `wiki/concepts/simulation-design.md` (+ `-runtime` companion). Three
typed event classes (`Delivery`, `TimerFire`, `PhaseAdvance`); lazy-tombstone
timer cancellation; three OR-composed stop conditions. Stdlib only.

**Tech Stack:** Python 3.13, stdlib `heapq` / `dataclasses` / `typing`,
stdlib `unittest` for tests. No third-party dependencies (T26/T27 own
dependency management; this task ships before them).

---

## Design decisions (read before executing — needs human approval)

Five choices the spec left open or under-specified. The plan implements the
**Resolution**; reject any before execution and the plan changes.

**DD1 — Test framework: stdlib `unittest`.** T21 ships before T26 (`/tests`
scaffolding) and T27 (dependency management); no `pyproject.toml`, no pytest.
*Resolution:* stdlib `unittest` — zero install, fully reproducible. Tradeoff:
less ergonomic than pytest, but `unittest.TestCase` classes are pytest-
discoverable, so T31 can adopt pytest later without rewriting these tests.

**DD2 — Test location: `tests/scheduler/`.** No `tests/` dir exists yet; T26
will formalize it. *Resolution:* create `tests/scheduler/` now; T26 builds on
it. Tradeoff: a small slice of T26's scaffolding lands early — unavoidable,
T21's outcome requires runnable tests.

**DD3 — Dispatch references (spec gap → wiki Revision R1).** `run()` must call
`node.on_message` / `node.on_timer` / `network.advance_phase`, but the spec
never says how the scheduler *holds* those references. *Resolution:* `bind(node)`
also registers the node in `self.nodes: dict[NodeId, Node]`; a new
`bind_network(network)` method sets `self.network` (called in bootstrap
phase 3). Spec §6.3's "no `Scheduler→Network` reference" forbids the *outbound-
binding cycle* (`set_timer`/`send` cross-wiring) — a dispatch-only handle for
`PhaseAdvance` does not create that cycle. Lands as `## Revisions` entry R1 on
`simulation-design.md`.

**DD4 — `set_timer` seq funnel (spec bug → wiki Revision R2).** Spec §5.2 /
wiki §6.2 say `set_timer` computes `seq = next_seq(...)` *and then* calls
`schedule()` — but `schedule()` also calls `next_seq()`, so the seq would be
incremented twice and the registry seq would never match the heap entry's
seq, breaking the tombstone check. *Resolution:* `schedule()` returns the
`seq` it assigned (`-> int`, not `-> None`); `set_timer` funnels through
`schedule()` once and registers the returned seq. Preserves the single-funnel
invariant (§5.1) and correctness. Lands as `## Revisions` entry R2.

**DD5 — `Delivery.msg` type.** The `Message` envelope is defined in T23.
*Resolution:* annotate `msg: Any` with a comment pointing at `network-model
§3.1` / T23. No Revision needed — the runtime reference sketch already uses a
forward-ref string for the same reason.

**Open question for the human — commit ownership.** Repo `docs/workflow.md`
has the agent commit per task (`task 21: <imperative>`); the `/prj-pickup`
flow says the human commits. The plan below includes per-task commit steps
(skill convention). Confirm at approval whether the executor runs them or
batches the work for your review.

---

## Task 1: Module scaffold + event taxonomy

**Files:**
- Create: `src/scheduler/__init__.py`
- Create: `src/scheduler/events.py`
- Create: `tests/scheduler/test_events.py`

**Step 1: Write the failing test**

`tests/scheduler/test_events.py`:

```python
"""Unit tests for the scheduler event taxonomy (simulation-design.md §5)."""
import unittest

from scheduler import Delivery, Event, PhaseAdvance, TimerFire


class TestEventTaxonomy(unittest.TestCase):
    def test_delivery_carries_message(self):
        d = Delivery(msg="envelope")
        self.assertEqual(d.msg, "envelope")

    def test_timerfire_carries_id_and_payload(self):
        tf = TimerFire(timer_id="round", payload={"view": 3})
        self.assertEqual(tf.timer_id, "round")
        self.assertEqual(tf.payload, {"view": 3})

    def test_phaseadvance_carries_phase_id(self):
        pa = PhaseAdvance(phase_id=2)
        self.assertEqual(pa.phase_id, 2)

    def test_event_union_includes_all_three(self):
        for ev in (Delivery(msg=None), TimerFire(timer_id="t", payload=None),
                   PhaseAdvance(phase_id=0)):
            self.assertIsInstance(ev, Event.__args__)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_events -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scheduler'`.

**Step 3: Write minimal implementation**

`src/scheduler/events.py`:

```python
"""Scheduler event taxonomy and core type aliases.

Design contract: wiki/concepts/simulation-design.md §4-§5
Spec: docs/superpowers/specs/2026-05-13-t17-scheduler-design.md §4.2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Core type aliases (simulation-design.md §4).
SimTime = float   # virtual time, milliseconds (network-model §1)
NodeId = int      # validator identifier (node-model §2)
TimerId = Any     # caller-supplied timer key (node-model §7)


@dataclass
class Delivery:
    """A message arriving at a Node."""
    msg: Any   # Message envelope (network-model §3.1); concrete type from T23.


@dataclass
class TimerFire:
    """A Node's self-scheduled wake-up."""
    timer_id: TimerId
    payload: Any


@dataclass
class PhaseAdvance:
    """A network-phase boundary transition."""
    phase_id: int


Event = Delivery | TimerFire | PhaseAdvance
```

`src/scheduler/__init__.py`:

```python
"""Discrete-event scheduler package — the simulator's virtual-time engine.

See wiki/concepts/simulation-design.md for the design contract.
"""
from .events import (
    Delivery,
    Event,
    NodeId,
    PhaseAdvance,
    SimTime,
    TimerFire,
    TimerId,
)
from .scheduler import RunResult, Scheduler

__all__ = [
    "Delivery",
    "Event",
    "NodeId",
    "PhaseAdvance",
    "RunResult",
    "Scheduler",
    "SimTime",
    "TimerFire",
    "TimerId",
]
```

> Note: `__init__.py` imports `.scheduler`, created in Task 2. Until then the
> package import fails — expected; Task 1's test only needs `events`. If you
> want Task 1 green in isolation, temporarily comment the `.scheduler` import
> line and restore it in Task 2. Otherwise run Tasks 1-2 back-to-back.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_events -v`
Expected: PASS — 4 tests (after Task 2's `scheduler.py` exists).

**Step 5: Commit**

```bash
git add src/scheduler/__init__.py src/scheduler/events.py tests/scheduler/test_events.py
git commit -m "task 21: add scheduler event taxonomy"
```

---

## Task 2: Scheduler skeleton — state, `now`, `_next_seq`

**Files:**
- Create: `src/scheduler/scheduler.py`
- Create: `tests/scheduler/test_scheduler.py`

**Step 1: Write the failing test**

`tests/scheduler/test_scheduler.py`:

```python
"""Unit tests for the Scheduler class (simulation-design.md §4-§7)."""
import unittest

from scheduler import Scheduler


class TestSchedulerSkeleton(unittest.TestCase):
    def test_fresh_scheduler_has_empty_state(self):
        s = Scheduler()
        self.assertEqual(s.heap, [])
        self.assertEqual(s.registry, {})
        self.assertEqual(s.seq_per, {})
        self.assertEqual(s.now, 0.0)
        self.assertIsNone(s.event_sink)

    def test_now_is_read_only(self):
        s = Scheduler()
        with self.assertRaises(AttributeError):
            s.now = 5.0  # type: ignore[misc]

    def test_next_seq_increments_per_node_independently(self):
        s = Scheduler()
        self.assertEqual(s._next_seq(0), 1)
        self.assertEqual(s._next_seq(0), 2)
        self.assertEqual(s._next_seq(1), 1)   # node 1 counter is independent
        self.assertEqual(s._next_seq(0), 3)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestSchedulerSkeleton -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scheduler.scheduler'`.

**Step 3: Write minimal implementation**

`src/scheduler/scheduler.py`:

```python
"""Discrete-event scheduler — the simulator's virtual-time engine.

Design contract: wiki/concepts/simulation-design.md (+ -runtime companion)
Spec: docs/superpowers/specs/2026-05-13-t17-scheduler-design.md
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, Callable, Literal

from .events import (
    Delivery,
    Event,
    NodeId,
    PhaseAdvance,
    SimTime,
    TimerFire,
    TimerId,
)


@dataclass
class RunResult:
    """Outcome of a Scheduler.run() call (simulation-design.md §6.5)."""
    stopped_by: Literal["quiescence", "deadline", "predicate"]
    now: SimTime
    events_processed: int
    events_tombstoned: int


class Scheduler:
    """Custom min-heap discrete-event scheduler (simulation-design.md §3 D1)."""

    PHASE_NODE_ID: NodeId = -1   # sentinel node_id for PhaseAdvance (§3 D2)

    def __init__(self) -> None:
        self.heap: list[tuple[SimTime, NodeId, int, Event]] = []
        self.registry: dict[tuple[NodeId, TimerId], int] = {}
        self.seq_per: dict[NodeId, int] = {}
        self._now: SimTime = 0.0
        self.event_sink: Callable[[SimTime, NodeId, int, Event], None] | None = None
        # DD3 (Revision R1): dispatch targets held by the scheduler.
        self.nodes: dict[NodeId, Any] = {}   # populated by bind()
        self.network: Any | None = None      # set by bind_network()

    @property
    def now(self) -> SimTime:
        """Virtual clock. Read-only; Node handlers receive `t` as a param."""
        return self._now

    def _next_seq(self, node_id: NodeId) -> int:
        seq = self.seq_per.get(node_id, 0) + 1
        self.seq_per[node_id] = seq
        return seq
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestSchedulerSkeleton test_events -v`
Expected: PASS — 3 skeleton tests + 4 event tests.

**Step 5: Commit**

```bash
git add src/scheduler/scheduler.py tests/scheduler/test_scheduler.py
git commit -m "task 21: add Scheduler skeleton (state, now, seq counter)"
```

---

## Task 3: `schedule()` — enqueue, past-time guard, returns seq

**Files:**
- Modify: `src/scheduler/scheduler.py` (add `schedule` method)
- Modify: `tests/scheduler/test_scheduler.py` (add `TestSchedule` class)

**Step 1: Write the failing test**

Append to `tests/scheduler/test_scheduler.py`:

```python
from scheduler import PhaseAdvance, TimerFire


class TestSchedule(unittest.TestCase):
    def test_schedule_pushes_and_returns_seq(self):
        s = Scheduler()
        seq = s.schedule(PhaseAdvance(0), t=10.0, node_id=0)
        self.assertEqual(seq, 1)
        self.assertEqual(len(s.heap), 1)
        t, node_id, heap_seq, ev = s.heap[0]
        self.assertEqual((t, node_id, heap_seq), (10.0, 0, 1))

    def test_heap_orders_by_time_then_node_then_seq(self):
        s = Scheduler()
        # seq is a per-node counter incremented in schedule() CALL order,
        # not virtual-time order (simulation-design.md §3 D2). So node 0's
        # t=20 event gets seq 1 and its t=10 event gets seq 2.
        s.schedule(TimerFire("b", None), t=20.0, node_id=0)   # node 0, seq 1
        s.schedule(TimerFire("a", None), t=10.0, node_id=1)   # node 1, seq 1
        s.schedule(TimerFire("c", None), t=10.0, node_id=0)   # node 0, seq 2
        order = [heapq.heappop(s.heap)[:3] for _ in range(3)]
        self.assertEqual(order, [(10.0, 0, 2), (10.0, 1, 1), (20.0, 0, 1)])

    def test_schedule_in_the_past_raises(self):
        s = Scheduler()
        s.schedule(PhaseAdvance(0), t=10.0, node_id=0)
        s._now = 10.0
        with self.assertRaises(ValueError):
            s.schedule(PhaseAdvance(1), t=9.999, node_id=0)

    def test_schedule_at_now_is_allowed(self):
        s = Scheduler()
        s._now = 5.0
        seq = s.schedule(PhaseAdvance(0), t=5.0, node_id=0)
        self.assertEqual(seq, 1)
```

Add `import heapq` at the top of the test file.

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestSchedule -v`
Expected: FAIL — `AttributeError: 'Scheduler' object has no attribute 'schedule'`.

**Step 3: Write minimal implementation**

Add to `Scheduler` in `src/scheduler/scheduler.py`:

```python
    def schedule(self, event: Event, t: SimTime, node_id: NodeId) -> int:
        """Enqueue an event. The single funnel into the heap.

        Returns the per-Node seq assigned (DD4 / Revision R2), so set_timer
        can register the heap entry's exact seq without a second increment.
        Raises ValueError if `t` is in the past (fail-fast, runtime §3).
        """
        if t < self._now:
            raise ValueError(f"schedule in the past: t={t} < now={self._now}")
        seq = self._next_seq(node_id)
        heapq.heappush(self.heap, (t, node_id, seq, event))
        return seq
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestSchedule -v`
Expected: PASS — 4 tests.

**Step 5: Commit**

```bash
git add src/scheduler/scheduler.py tests/scheduler/test_scheduler.py
git commit -m "task 21: implement Scheduler.schedule with past-time guard"
```

---

## Task 4: `set_timer()` + `cancel_timer()` — registry + lazy tombstone

**Files:**
- Modify: `src/scheduler/scheduler.py`
- Modify: `tests/scheduler/test_scheduler.py` (add `TestTimers` class)

**Step 1: Write the failing test**

Append to `tests/scheduler/test_scheduler.py`:

```python
class TestTimers(unittest.TestCase):
    def test_set_timer_registers_heap_entry_seq(self):
        s = Scheduler()
        s.set_timer(node_id=0, timer_id="round", delay=5.0, payload=None, t=0.0)
        self.assertEqual(len(s.heap), 1)
        t, node_id, seq, ev = s.heap[0]
        self.assertEqual((t, node_id), (5.0, 0))
        self.assertIsInstance(ev, TimerFire)
        # Registry seq MUST equal the heap entry's seq (tombstone correctness).
        self.assertEqual(s.registry[(0, "round")], seq)

    def test_zero_delay_is_allowed(self):
        s = Scheduler()
        s.set_timer(node_id=0, timer_id="yield", delay=0.0, payload=None, t=3.0)
        self.assertEqual(s.heap[0][0], 3.0)

    def test_negative_delay_raises(self):
        s = Scheduler()
        with self.assertRaises(ValueError):
            s.set_timer(node_id=0, timer_id="x", delay=-1.0, payload=None, t=0.0)

    def test_cancel_timer_removes_registry_entry(self):
        s = Scheduler()
        s.set_timer(node_id=0, timer_id="round", delay=5.0, payload=None, t=0.0)
        s.cancel_timer(node_id=0, timer_id="round")
        self.assertNotIn((0, "round"), s.registry)
        # Lazy tombstone: heap entry is left in place.
        self.assertEqual(len(s.heap), 1)

    def test_cancel_unknown_timer_is_noop(self):
        s = Scheduler()
        s.cancel_timer(node_id=0, timer_id="never-set")  # must not raise

    def test_reregistration_overwrites_registry_seq(self):
        s = Scheduler()
        s.set_timer(node_id=0, timer_id="round", delay=5.0, payload=None, t=0.0)
        first_seq = s.registry[(0, "round")]
        s.set_timer(node_id=0, timer_id="round", delay=8.0, payload=None, t=0.0)
        second_seq = s.registry[(0, "round")]
        self.assertNotEqual(first_seq, second_seq)
        self.assertEqual(len(s.heap), 2)  # old entry left as a tombstone
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestTimers -v`
Expected: FAIL — `AttributeError: ... has no attribute 'set_timer'`.

**Step 3: Write minimal implementation**

Add to `Scheduler`:

```python
    def set_timer(self, node_id: NodeId, timer_id: TimerId,
                  delay: SimTime, payload: Any, t: SimTime) -> None:
        """Schedule a TimerFire for a Node. `delay == 0` is legal."""
        if delay < 0:
            raise ValueError(f"negative timer delay: {delay}")
        # Funnel through schedule() (single-funnel invariant, §5.1) and
        # register the seq it assigned (DD4 / Revision R2).
        seq = self.schedule(TimerFire(timer_id, payload), t + delay, node_id)
        self.registry[(node_id, timer_id)] = seq

    def cancel_timer(self, node_id: NodeId, timer_id: TimerId) -> None:
        """Cancel a timer. O(1); the heap entry is left as a lazy tombstone."""
        self.registry.pop((node_id, timer_id), None)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestTimers -v`
Expected: PASS — 6 tests.

**Step 5: Commit**

```bash
git add src/scheduler/scheduler.py tests/scheduler/test_scheduler.py
git commit -m "task 21: implement timer set/cancel with lazy tombstone"
```

---

## Task 5: `bind()` + `bind_network()` — wiring + dispatch registries

**Files:**
- Modify: `src/scheduler/scheduler.py`
- Create: `tests/scheduler/_stubs.py`
- Modify: `tests/scheduler/test_scheduler.py` (add `TestBind` class)

**Step 1: Write the failing test**

`tests/scheduler/_stubs.py`:

```python
"""Recording stubs standing in for Node / Network in Scheduler tests.

Real Node / Network land in T22 / T23; these record calls so the scheduler
can be tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SimpleMessage:
    """Stand-in for the T23 Message envelope (network-model §3.1)."""
    src: int
    dst: int
    payload: Any


class RecordingNode:
    """Minimal Node stub: records inbound-hook calls in order."""

    def __init__(self, node_id: int) -> None:
        self.id = node_id
        self.calls: list[tuple] = []

    def on_message(self, msg: Any, t: float) -> None:
        self.calls.append(("on_message", msg, t))

    def on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        self.calls.append(("on_timer", timer_id, payload, t))

    def start(self, t: float) -> None:
        self.calls.append(("start", t))


class RecordingNetwork:
    """Minimal Network stub: records advance_phase calls in order."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def advance_phase(self, phase_id: int) -> None:
        self.calls.append(("advance_phase", phase_id))
```

Append to `tests/scheduler/test_scheduler.py`:

```python
from _stubs import RecordingNetwork, RecordingNode


class TestBind(unittest.TestCase):
    def test_bind_registers_node_for_dispatch(self):
        s = Scheduler()
        node = RecordingNode(7)
        s.bind(node)
        self.assertIs(s.nodes[7], node)

    def test_bind_wires_set_timer_curried_on_node_id(self):
        s = Scheduler()
        node = RecordingNode(7)
        s.bind(node)
        node.set_timer("round", 5.0, None, 0.0)
        self.assertEqual(s.registry[(7, "round")], s.heap[0][2])

    def test_bind_wires_cancel_timer_curried_on_node_id(self):
        s = Scheduler()
        node = RecordingNode(7)
        s.bind(node)
        node.set_timer("round", 5.0, None, 0.0)
        node.cancel_timer("round")
        self.assertNotIn((7, "round"), s.registry)

    def test_bind_wires_emit_through_event_sink(self):
        s = Scheduler()
        captured: list[tuple] = []
        s.event_sink = lambda t, nid, seq, ev: captured.append((t, nid, seq, ev))
        node = RecordingNode(7)
        s.bind(node)
        node.emit("committed", {"block": 1}, 12.0)
        self.assertEqual(captured,
                         [(12.0, 7, -1, ("emit", "committed", {"block": 1}))])

    def test_bind_network_sets_network_handle(self):
        s = Scheduler()
        net = RecordingNetwork()
        s.bind_network(net)
        self.assertIs(s.network, net)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestBind -v`
Expected: FAIL — `AttributeError: ... has no attribute 'bind'`.

**Step 3: Write minimal implementation**

Add to `Scheduler`:

```python
    def bind(self, node: Any) -> None:
        """Wire a Node's scheduler-owned outbound API and register it for
        dispatch. Does NOT wire send/broadcast — that is Network.bind's half.
        """
        self.nodes[node.id] = node   # DD3 / Revision R1: dispatch target.
        node.set_timer = lambda timer_id, delay, payload, t: self.set_timer(
            node.id, timer_id, delay, payload, t
        )
        node.cancel_timer = lambda timer_id: self.cancel_timer(
            node.id, timer_id
        )
        node.emit = lambda event_type, fields, t: (
            self.event_sink(t, node.id, -1, ("emit", event_type, fields))
            if self.event_sink is not None
            else None
        )

    def bind_network(self, network: Any) -> None:
        """Register the Network as the dispatch target for PhaseAdvance
        events (DD3 / Revision R1). Called once during bootstrap phase 3.
        """
        self.network = network
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestBind -v`
Expected: PASS — 5 tests.

**Step 5: Commit**

```bash
git add src/scheduler/scheduler.py tests/scheduler/_stubs.py tests/scheduler/test_scheduler.py
git commit -m "task 21: implement bind / bind_network wiring"
```

---

## Task 6: `run()` — loop, dispatch, tombstone skip, stop conditions

**Files:**
- Modify: `src/scheduler/scheduler.py`
- Modify: `tests/scheduler/test_scheduler.py` (add `TestRun` class)

**Step 1: Write the failing test**

Append to `tests/scheduler/test_scheduler.py`:

```python
from scheduler import Delivery, RunResult
from _stubs import SimpleMessage


class TestRun(unittest.TestCase):
    def _scheduler_with_two_nodes(self):
        s = Scheduler()
        n0, n1 = RecordingNode(0), RecordingNode(1)
        s.bind(n0)
        s.bind(n1)
        return s, n0, n1

    def test_dispatch_delivery_to_on_message(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        msg = SimpleMessage(0, 1, "hello")
        s.schedule(Delivery(msg), t=10.0, node_id=1)
        result = s.run()
        self.assertEqual(n1.calls, [("on_message", msg, 10.0)])
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(result.events_processed, 1)

    def test_dispatch_timerfire_to_on_timer(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        n0.set_timer("round", 5.0, {"view": 2}, 0.0)
        s.run()
        self.assertEqual(n0.calls, [("on_timer", "round", {"view": 2}, 5.0)])

    def test_dispatch_phaseadvance_to_network(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        net = RecordingNetwork()
        s.bind_network(net)
        s.schedule(PhaseAdvance(3), t=7.0, node_id=Scheduler.PHASE_NODE_ID)
        s.run()
        self.assertEqual(net.calls, [("advance_phase", 3)])

    def test_cancelled_timer_is_tombstoned_not_dispatched(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        n0.set_timer("round", 5.0, None, 0.0)
        n0.cancel_timer("round")
        result = s.run()
        self.assertEqual(n0.calls, [])
        self.assertEqual(result.events_tombstoned, 1)
        self.assertEqual(result.events_processed, 0)

    def test_reregistered_timer_fires_once_old_entry_tombstoned(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        n0.set_timer("round", 5.0, "stale", 0.0)
        n0.set_timer("round", 8.0, "fresh", 0.0)
        result = s.run()
        self.assertEqual(n0.calls, [("on_timer", "round", "fresh", 8.0)])
        self.assertEqual(result.events_tombstoned, 1)

    def test_quiescence_on_drained_heap(self):
        s, _, _ = self._scheduler_with_two_nodes()
        result = s.run()
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(result.now, 0.0)

    def test_deadline_stops_after_pop_past_t_max(self):
        # Deadline semantics (simulation-design.md §3 D5): "Loop exits when
        # now >= t_max after a pop." Events strictly inside t_max run; the
        # first event that pushes `now` past t_max runs too (overshoot by
        # one); anything later is left unprocessed on the heap.
        s, n0, n1 = self._scheduler_with_two_nodes()
        s.schedule(Delivery(SimpleMessage(0, 1, "a")), t=10.0, node_id=1)
        s.schedule(Delivery(SimpleMessage(0, 1, "b")), t=30.0, node_id=1)
        s.schedule(Delivery(SimpleMessage(0, 1, "c")), t=50.0, node_id=1)
        result = s.run(t_max=20.0)
        self.assertEqual(result.stopped_by, "deadline")
        self.assertEqual(result.events_processed, 2)   # t=10 and t=30
        self.assertEqual(result.now, 30.0)
        self.assertEqual(len(s.heap), 1)               # t=50 still queued

    def test_empty_run_with_past_deadline_returns_deadline(self):
        s, _, _ = self._scheduler_with_two_nodes()
        result = s.run(t_max=0.0)
        self.assertEqual(result.stopped_by, "deadline")

    def test_predicate_stops_after_dispatch(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        for i in range(5):
            s.schedule(Delivery(SimpleMessage(0, 1, i)), t=float(i + 1),
                       node_id=1)
        result = s.run(stop_when=lambda: len(n1.calls) >= 3)
        self.assertEqual(result.stopped_by, "predicate")
        self.assertEqual(result.events_processed, 3)

    def test_event_sink_called_before_dispatch_per_non_stale_event(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        seen: list[tuple] = []
        s.event_sink = lambda t, nid, seq, ev: seen.append((t, nid, type(ev).__name__))
        n0.set_timer("a", 5.0, None, 0.0)
        s.schedule(Delivery(SimpleMessage(0, 1, "m")), t=8.0, node_id=1)
        s.run()
        self.assertEqual(seen, [(5.0, 0, "TimerFire"), (8.0, 1, "Delivery")])
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_scheduler.TestRun -v`
Expected: FAIL — `AttributeError: ... has no attribute 'run'`.

**Step 3: Write minimal implementation**

Add to `Scheduler`:

```python
    def run(self, t_max: SimTime | None = None,
            stop_when: Callable[[], bool] | None = None) -> RunResult:
        """Run the dispatch loop until a stop condition fires.

        Stop conditions (OR-composed, §3 D5):
          - deadline   : `now >= t_max` checked before each pop;
          - quiescence : the heap drains;
          - predicate  : `stop_when()` returns True after a dispatch.
        """
        n_processed = 0
        n_tombstoned = 0
        while True:
            if t_max is not None and self._now >= t_max:
                return RunResult("deadline", self._now,
                                 n_processed, n_tombstoned)
            if not self.heap:
                return RunResult("quiescence", self._now,
                                 n_processed, n_tombstoned)
            t, node_id, seq, event = heapq.heappop(self.heap)
            self._now = t
            if isinstance(event, TimerFire) and \
                    self.registry.get((node_id, event.timer_id)) != seq:
                n_tombstoned += 1
                continue
            if self.event_sink is not None:
                self.event_sink(t, node_id, seq, event)
            self._dispatch(event, node_id, t)
            n_processed += 1
            if stop_when is not None and stop_when():
                return RunResult("predicate", self._now,
                                 n_processed, n_tombstoned)

    def _dispatch(self, event: Event, node_id: NodeId, t: SimTime) -> None:
        """Route a popped event to its handler, keyed on event class."""
        if isinstance(event, Delivery):
            self.nodes[node_id].on_message(event.msg, t)
        elif isinstance(event, TimerFire):
            self.nodes[node_id].on_timer(event.timer_id, event.payload, t)
        elif isinstance(event, PhaseAdvance):
            self.network.advance_phase(event.phase_id)
        else:  # fail-fast on an unknown event class (runtime §3).
            raise TypeError(f"unknown event class: {type(event).__name__}")
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v`
Expected: PASS — all unit tests across `test_events` + `test_scheduler` (~28).

**Step 5: Commit**

```bash
git add src/scheduler/scheduler.py tests/scheduler/test_scheduler.py
git commit -m "task 21: implement run loop, dispatch, and stop conditions"
```

---

## Task 7: End-to-end test — six-phase bootstrap + determinism

**Files:**
- Create: `tests/scheduler/test_e2e.py`

This test proves the scheduler *drives a whole simulation*, not just that
units work. It builds a 2-node ping-pong, runs the full six-phase bootstrap
(simulation-design.md §7.2), and asserts the end-to-end event stream — then
runs it a second time from fresh objects and asserts byte-identical output
(the determinism contract, runtime §1).

**Step 1: Write the failing test**

`tests/scheduler/test_e2e.py`:

```python
"""End-to-end test: the Scheduler drives a 2-node ping-pong simulation.

Exercises the full six-phase bootstrap (simulation-design.md §7.2) and the
determinism contract (simulation-design-runtime.md §1).
"""
import unittest

from scheduler import Delivery, PhaseAdvance, Scheduler
from _stubs import SimpleMessage


class EchoNode:
    """Stub protocol Node: node 0 kicks off, node 1 echoes PING -> PONG.

    set_timer / cancel_timer / emit are injected by Scheduler.bind;
    send / broadcast by LoopbackNetwork.bind. Both happen in phase 3,
    before start() runs in phase 5.
    """

    def __init__(self, node_id: int) -> None:
        self.id = node_id

    def start(self, t: float) -> None:
        if self.id == 0:
            self.set_timer("kickoff", 5.0, None, t)   # noqa: attr injected

    def on_timer(self, timer_id, payload, t) -> None:
        if timer_id == "kickoff":
            self.broadcast("PING", t)                  # noqa: attr injected

    def on_message(self, msg, t) -> None:
        if msg.payload == "PING":
            self.send(msg.src, "PONG", t)              # noqa: attr injected
        # PONG is terminal — no further events.


class LoopbackNetwork:
    """Stub Network with a fixed delivery delay. Real Network lands in T23."""

    DELAY: float = 10.0
    PHASE_AT: float = 20.0

    def __init__(self, scheduler: Scheduler) -> None:
        self.scheduler = scheduler
        self.members: dict[int, EchoNode] = {}
        self.phases_advanced: list[int] = []

    def register(self, node: EchoNode) -> None:
        self.members[node.id] = node

    def bind(self, node: EchoNode) -> None:
        node.send = lambda dst, payload, t: self._unicast(node.id, dst,
                                                          payload, t)
        node.broadcast = lambda payload, t: self._broadcast(node.id,
                                                            payload, t)

    def start(self) -> None:
        self.scheduler.schedule(PhaseAdvance(1), self.PHASE_AT,
                                Scheduler.PHASE_NODE_ID)

    def advance_phase(self, phase_id: int) -> None:
        self.phases_advanced.append(phase_id)

    def _unicast(self, src, dst, payload, t) -> None:
        msg = SimpleMessage(src, dst, payload)
        self.scheduler.schedule(Delivery(msg), t + self.DELAY, dst)

    def _broadcast(self, src, payload, t) -> None:
        for node_id in self.members:        # insertion order: deterministic
            if node_id != src:
                self._unicast(src, node_id, payload, t)


def run_pingpong() -> tuple:
    """Run one full bootstrap + run cycle. Returns (sink_stream, result, net)."""
    stream: list[str] = []
    # Phase 1 — construct.
    scheduler = Scheduler()
    network = LoopbackNetwork(scheduler)
    nodes = [EchoNode(0), EchoNode(1)]
    # Phase 2 — register.
    for node in nodes:
        network.register(node)
    # Phase 3 — bind (split ownership) + network dispatch handle.
    for node in nodes:
        scheduler.bind(node)
        network.bind(node)
    scheduler.bind_network(network)
    # Phase 4 — observe.
    scheduler.event_sink = lambda t, nid, seq, ev: stream.append(
        f"{t}|{nid}|{seq}|{ev!r}"
    )
    # Phase 5 — kickoff.
    network.start()
    for node in nodes:
        node.start(0.0)
    # Phase 6 — run.
    result = scheduler.run()
    return stream, result, network


class TestEndToEnd(unittest.TestCase):
    def test_pingpong_runs_to_quiescence(self):
        stream, result, network = run_pingpong()
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(result.events_processed, 4)
        self.assertEqual(result.events_tombstoned, 0)
        self.assertEqual(result.now, 25.0)
        self.assertEqual(network.phases_advanced, [1])

    def test_pingpong_event_stream_is_exact(self):
        stream, _, _ = run_pingpong()
        expected = [
            "5.0|0|1|TimerFire(timer_id='kickoff', payload=None)",
            "15.0|1|1|Delivery(msg=SimpleMessage(src=0, dst=1, payload='PING'))",
            "20.0|-1|1|PhaseAdvance(phase_id=1)",
            "25.0|0|2|Delivery(msg=SimpleMessage(src=1, dst=0, payload='PONG'))",
        ]
        self.assertEqual(stream, expected)

    def test_two_runs_are_byte_identical(self):
        first, _, _ = run_pingpong()
        second, _, _ = run_pingpong()
        self.assertEqual(first, second)   # determinism contract, runtime §1


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest test_e2e -v`
Expected: FAIL initially only if any earlier task is incomplete. If Tasks 1-6
are done, this test should PASS immediately — it composes already-built
behavior. If it fails, the failure is a real integration bug: debug per
`superpowers:systematic-debugging` before proceeding. Do NOT weaken the
assertions to make it pass.

**Step 3: (no new implementation)**

The e2e test exercises only the public API built in Tasks 1-6. If it passes,
move on. If the exact-stream assertion fails, inspect the diff — a wrong seq
or event order is a determinism bug worth catching now.

**Step 4: Run the full suite**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v`
Expected: PASS — every test in `test_events`, `test_scheduler`, `test_e2e`.

**Step 5: Commit**

```bash
git add tests/scheduler/test_e2e.py
git commit -m "task 21: add end-to-end ping-pong + determinism test"
```

---

## Task 8: Wiki — Revisions, experiment page, index + log

**Files:**
- Modify: `wiki/concepts/simulation-design.md` (§9 Revisions)
- Create: `wiki/experiments/2026-05-18_scheduler-baseline.md`
- Modify: `wiki/index.md` (Experiments section)
- Modify: `wiki/log.md` (append entry)

**Step 1: Replace the `## 9. Revisions` section of `simulation-design.md`**

Replace `## 9. Revisions\n\nNone.` with:

```markdown
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

§5.1-§5.2 / §6.2 described `set_timer` as computing its own `seq` *and*
funnelling through `schedule()`, which also assigns a `seq` — a double
increment that desynchronises the registry seq from the heap entry's seq
and breaks the tombstone check. T21 resolves this: `schedule()` returns
the `seq` it assigned (`-> int`, not `-> None`); `set_timer` funnels
through `schedule()` once and registers the returned value. The
single-funnel invariant (§5.1) is preserved.
```

**Step 2: Create the experiment page**

`wiki/experiments/2026-05-18_scheduler-baseline.md`:

```markdown
# Scheduler baseline — T21

First runnable artifact of the simulator: the discrete-event scheduler
([[concepts/simulation-design]]) executing a minimal end-to-end scenario.
Not a protocol experiment — a build-verification baseline confirming the
scheduler drives a simulation correctly and deterministically.

## Configuration

- Component under test: `src/scheduler/` (`Scheduler`, `RunResult`,
  `Delivery` / `TimerFire` / `PhaseAdvance`).
- Scenario: 2-node ping-pong. Node 0 sets a 5 ms kickoff timer, broadcasts
  `PING`; node 1 echoes `PONG`. Fixed 10 ms link delay; one `PhaseAdvance`
  at 20 ms. Full six-phase bootstrap (simulation-design §7.2).
- Stubs: `EchoNode` / `LoopbackNetwork` (real Node / Network are T22 / T23).
- Seeds: none — the scheduler holds no RNG; determinism is structural
  (unique heap key `(t, node_id, seq)`).
- Commit: TODO(commit-hash — fill on merge).

## Re-run

```
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
```

## Result

`run()` processes 4 events to quiescence at virtual time 25.0 ms, 0
tombstoned. Two fresh runs of the scenario produce byte-identical
`event_sink` streams. Raw result: assertions in
`tests/scheduler/test_e2e.py` (no CSV — pre-T40).

## Observation

The scheduler drives a complete bootstrap-to-quiescence simulation with
the expected event ordering, and the determinism contract holds for a
non-trivial multi-node scenario. Two spec gaps surfaced and were resolved
during implementation — see [[concepts/simulation-design]] §9 Revisions
R1 (dispatch references) and R2 (`schedule()` returns `seq`).
```

**Step 3: Add the Experiments entry to `wiki/index.md`**

Under `## Experiments` (currently empty), add:

```markdown
- [[experiments/2026-05-18_scheduler-baseline]] — T21 build-verification baseline: the discrete-event scheduler drives a 2-node ping-pong through the full six-phase bootstrap to quiescence; determinism contract holds (byte-identical re-run).
```

**Step 4: Append to `wiki/log.md`**

```markdown
## [2026-05-18] code | task 21 — Implement event scheduler

- role: Engineer
- touched: src/scheduler/{__init__,events,scheduler}.py, tests/scheduler/{_stubs,test_events,test_scheduler,test_e2e}.py, wiki/concepts/simulation-design.md, wiki/experiments/2026-05-18_scheduler-baseline.md, wiki/index.md
- notes: Implemented the custom min-heap discrete-event scheduler per the T17 design contract — schedule/set_timer/cancel_timer/bind/run, lazy-tombstone cancellation, three stop conditions. Unit tests + an end-to-end 2-node ping-pong determinism test. Two spec gaps resolved as Revisions R1 (dispatch references) and R2 (schedule() returns seq).
```

**Step 5: Run the full suite once more, then commit**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v`
Expected: PASS — full suite, unchanged from Task 7.

```bash
git add wiki/concepts/simulation-design.md wiki/experiments/2026-05-18_scheduler-baseline.md wiki/index.md wiki/log.md
git commit -m "task 21: document scheduler — revisions, experiment page, index, log"
```

---

## Done criteria

- [ ] `src/scheduler/` implements `Scheduler` per the spec + DD1-DD5.
- [ ] Full suite green: `PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v`.
- [ ] Unit tests cover heap order, past-time guard, timer set/cancel/tombstone,
      re-registration, bind wiring, dispatch, all three stop conditions.
- [ ] End-to-end test drives the full six-phase bootstrap to quiescence and
      asserts a byte-identical re-run.
- [ ] Revisions R1 + R2 recorded on `simulation-design.md`.
- [ ] Experiment page + `index.md` + `log.md` updated.
- [ ] Run `superpowers:verification-before-completion` before flipping T21 to
      In Review.
- [ ] Human flips T21 to Completed on merge (never the agent).
```

