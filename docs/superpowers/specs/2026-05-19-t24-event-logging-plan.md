# T24 Event-Logging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the `src/event_log/` subsystem — a passive `Scheduler.event_sink` consumer that normalises the simulator's consensus event stream into uniform records and exports them to CSV.

**Architecture:** A single `EventLogger` class whose `sink` method pattern-matches the two `event_sink` payload shapes (emit tuples and typed transport events) into `EventRecord`s, buffers them in memory, and writes them on an explicit `to_csv()` call. Event-type names live in a shared `event_types.py`, adopted by `src/nodes/node.py`. Approved design: `docs/superpowers/specs/2026-05-19-t24-event-logging-design.md`.

**Tech Stack:** Python 3.13, stdlib only (`csv`, `dataclasses`, `pathlib`). Tests are `unittest.TestCase` (no `pytest` in this environment).

**Test commands** (the project has no `conftest.py` / `pyproject.toml`; `src` and the test dir go on `PYTHONPATH`):
- All event_log tests: `PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v`
- One module: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger -v`
- One test: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestSinkEmit.test_emit_tuple_becomes_record -v`
- Regression (node.py edit): `PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v`

**Commit policy:** `docs/workflow.md` § Commit convention specifies per-task commits (`task 24: <imperative>`); the `/prj-pickup` session instruction says the human performs commits. Each task below ends with a commit checkpoint — the executor stages the listed files and either commits with the given message or pauses for the human, per the decision taken at execution handoff. The human always performs the In-Review status flip.

**Naming note (design Decision E):** the subsystem is `src/event_log/`, not the `TASKS.md`-literal `src/logging/` — a `logging` package on `PYTHONPATH=src` shadows the stdlib `logging` module. Documented deviation per `docs/workflow.md` § Evolution.

---

## Task 1: Event-type name constants

**Files:**
- Create: `src/event_log/event_types.py`
- Create: `src/event_log/__init__.py` (minimal placeholder this task; finalised in Task 6)
- Test: `tests/event_log/test_event_types.py`

**Step 1: Write the failing test**

```python
# tests/event_log/test_event_types.py
"""T24 event-type constant vocabulary."""
import unittest

from event_log import event_types as et


class TestEventTypes(unittest.TestCase):
    def test_emit_event_names(self):
        self.assertEqual(et.HALTED, "halted")
        self.assertEqual(et.DECIDED, "decided")

    def test_transport_event_names(self):
        self.assertEqual(et.DELIVERY, "delivery")
        self.assertEqual(et.TIMER_FIRE, "timer_fire")
        self.assertEqual(et.PHASE_ADVANCE, "phase_advance")

    def test_transport_set_is_exactly_the_three_transport_types(self):
        self.assertEqual(
            et.TRANSPORT_EVENT_TYPES,
            frozenset({"delivery", "timer_fire", "phase_advance"}))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_event_types -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'event_log'`.

**Step 3: Write minimal implementation**

```python
# src/event_log/__init__.py  (placeholder — Task 6 finalises the re-exports)
"""Structured event-logging subsystem (T24).

Named `event_log`, not `logging`, to avoid shadowing the stdlib module
under PYTHONPATH=src. See the design spec, Decision E, and
wiki/concepts/event-log-schema.md.
"""
```

```python
# src/event_log/event_types.py
"""Event-type name vocabulary for the structured event log (T24).

Single source of truth for the `event_type` string of every EventRecord.
Referencing a constant fails fast (NameError) on a typo; a bare string
literal does not. `src/nodes/node.py` imports HALTED / DECIDED from here
(node-model.md Revision 2026-05-19); the logger derives the transport names.

Design spec: docs/superpowers/specs/2026-05-19-t24-event-logging-design.md
"""
from __future__ import annotations

# Emit events — produced by Node.emit() (node-model.md §3 / §4 / §7).
HALTED = "halted"
DECIDED = "decided"

# Transport events — derived by the logger from the scheduler's typed
# event classes (simulation-design.md §5).
DELIVERY = "delivery"
TIMER_FIRE = "timer_fire"
PHASE_ADVANCE = "phase_advance"

# The event types the logger derives from a typed scheduler Event (as
# opposed to an ("emit", ...) tuple). Used by tests and documentation.
TRANSPORT_EVENT_TYPES = frozenset({DELIVERY, TIMER_FIRE, PHASE_ADVANCE})
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_event_types -v`
Expected: PASS — 3 tests OK.

**Step 5: Commit**

```bash
git add src/event_log/__init__.py src/event_log/event_types.py tests/event_log/test_event_types.py
git commit -m "task 24: event-type name constants"
```

---

## Task 2: `EventRecord` dataclass

**Files:**
- Create: `src/event_log/logger.py`
- Test: `tests/event_log/test_logger.py`

**Step 1: Write the failing test**

```python
# tests/event_log/test_logger.py
"""T24 EventLogger: normalisation, CSV export, determinism."""
import ast
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from nodes import Message
from scheduler import Delivery, PhaseAdvance, TimerFire

from event_log import EventLogger, EventRecord


class TestEventRecord(unittest.TestCase):
    def test_fields_are_accessible(self):
        r = EventRecord(t=12.0, node_id=5, event_type="decided",
                        seq=-1, fields={"value": "0xab"})
        self.assertEqual(r.t, 12.0)
        self.assertEqual(r.node_id, 5)
        self.assertEqual(r.event_type, "decided")
        self.assertEqual(r.seq, -1)
        self.assertEqual(r.fields, {"value": "0xab"})

    def test_record_is_frozen(self):
        r = EventRecord(t=0.0, node_id=0, event_type="halted",
                        seq=-1, fields={})
        with self.assertRaises(FrozenInstanceError):
            r.t = 9.0


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestEventRecord -v`
Expected: FAIL — `ImportError: cannot import name 'EventLogger' from 'event_log'` (or `No module named 'event_log.logger'`).

**Step 3: Write minimal implementation**

```python
# src/event_log/logger.py
"""Structured event logger for the consensus simulator (T24).

A passive Scheduler.event_sink consumer: normalises the scheduler's
heterogeneous event stream (emit tuples + typed transport events) into
uniform EventRecords, buffers them, and exports to CSV.

Design contract: wiki/concepts/event-log-schema.md
Design spec: docs/superpowers/specs/2026-05-19-t24-event-logging-design.md
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scheduler import Delivery, PhaseAdvance, TimerFire

from .event_types import DELIVERY, PHASE_ADVANCE, TIMER_FIRE

_CSV_HEADER = ("t", "node_id", "event_type", "seq", "fields")


@dataclass(frozen=True)
class EventRecord:
    """One normalised entry in the event log (event-log-schema.md)."""
    t: float
    node_id: int
    event_type: str
    seq: int
    fields: dict
```

(`EventLogger` is added in Task 3; the `csv` / `Path` / event-class imports
land now so later tasks add no import churn.)

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestEventRecord -v`
Expected: PASS — 2 tests OK.

**Step 5: Commit**

```bash
git add src/event_log/logger.py tests/event_log/test_logger.py
git commit -m "task 24: EventRecord dataclass"
```

---

## Task 3: `EventLogger.sink` — emit-tuple normalisation

**Files:**
- Modify: `src/event_log/logger.py` (append `EventLogger` class)
- Test: `tests/event_log/test_logger.py` (append `TestSinkEmit`)

**Step 1: Write the failing test**

```python
# append to tests/event_log/test_logger.py
class TestSinkEmit(unittest.TestCase):
    def test_emit_tuple_becomes_record(self):
        logger = EventLogger()
        logger.sink(12.0, 5, -1,
                    ("emit", "decided",
                     {"value": "0xab", "instance_id": (2, 7)}))
        self.assertEqual(len(logger), 1)
        r = logger.records[0]
        self.assertEqual((r.t, r.node_id, r.event_type, r.seq),
                         (12.0, 5, "decided", -1))
        self.assertEqual(r.fields,
                         {"value": "0xab", "instance_id": (2, 7)})

    def test_emit_fields_dict_is_copied_not_aliased(self):
        logger = EventLogger()
        original = {"reason": "RUN_END"}
        logger.sink(3.0, 1, -1, ("emit", "halted", original))
        original["reason"] = "MUTATED"
        self.assertEqual(logger.records[0].fields, {"reason": "RUN_END"})

    def test_len_reflects_record_count(self):
        logger = EventLogger()
        self.assertEqual(len(logger), 0)
        logger.sink(1.0, 0, -1, ("emit", "halted", {}))
        logger.sink(2.0, 0, -1, ("emit", "decided", {}))
        self.assertEqual(len(logger), 2)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestSinkEmit -v`
Expected: FAIL — `ImportError: cannot import name 'EventLogger'`.

**Step 3: Write minimal implementation**

Append to `src/event_log/logger.py`:

```python
class EventLogger:
    """Passive event_sink consumer. Buffers EventRecords; exports to CSV.

    Wired at bootstrap phase 4: `scheduler.event_sink = logger.sink`
    (simulation-design.md §7.2). Holds no file handle and no scheduler
    reference — a pure passive recorder.
    """

    def __init__(self) -> None:
        self.records: list[EventRecord] = []

    def __len__(self) -> int:
        return len(self.records)

    def sink(self, t: float, node_id: int, seq: int,
             payload: Any) -> None:
        """The Scheduler.event_sink callback. Normalises one event into an
        EventRecord and appends it. Raises TypeError on an unknown shape.

        Two payload shapes (event-log-schema.md §seam):
          - ("emit", event_type, fields)  — from Node.emit() via bind()
          - a typed Delivery / TimerFire / PhaseAdvance — from run()
        """
        if (isinstance(payload, tuple) and len(payload) == 3
                and payload[0] == "emit"):
            _, event_type, fields = payload
            self.records.append(
                EventRecord(t, node_id, event_type, seq, dict(fields)))
        else:
            raise TypeError(
                f"EventLogger.sink: unrecognised payload {payload!r}")
```

(The transport-event branches are added in Task 4; the `else: raise` keeps
the method total in the meantime.)

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestSinkEmit -v`
Expected: PASS — 3 tests OK.

**Step 5: Commit**

```bash
git add src/event_log/logger.py tests/event_log/test_logger.py
git commit -m "task 24: EventLogger.sink emit-tuple normalisation"
```

---

## Task 4: `EventLogger.sink` — transport events + fail-fast

**Files:**
- Modify: `src/event_log/logger.py` (add transport branches)
- Test: `tests/event_log/test_logger.py` (append `TestSinkTransport`, `TestSinkFailFast`)

**Step 1: Write the failing test**

```python
# append to tests/event_log/test_logger.py
class TestSinkTransport(unittest.TestCase):
    def test_delivery_records_envelope_facts(self):
        logger = EventLogger()
        msg = Message(src=1, dst=3, type="PREPARE",
                      payload={"v": 0}, t_sent=4.0)
        logger.sink(8.5, 3, 4, Delivery(msg))
        r = logger.records[0]
        self.assertEqual(r.event_type, "delivery")
        self.assertEqual((r.t, r.node_id, r.seq), (8.5, 3, 4))
        self.assertEqual(r.fields,
                         {"msg_type": "PREPARE", "src": 1, "dst": 3})

    def test_timer_fire_records_timer_id_only(self):
        logger = EventLogger()
        logger.sink(5.0, 2, 7, TimerFire(timer_id="view-change",
                                         payload={"big": "object"}))
        r = logger.records[0]
        self.assertEqual(r.event_type, "timer_fire")
        self.assertEqual(r.fields, {"timer_id": "view-change"})

    def test_phase_advance_records_phase_id(self):
        logger = EventLogger()
        logger.sink(20.0, -1, 1, PhaseAdvance(phase_id=2))
        r = logger.records[0]
        self.assertEqual(r.event_type, "phase_advance")
        self.assertEqual(r.fields, {"phase_id": 2})


class TestSinkFailFast(unittest.TestCase):
    def test_unknown_payload_raises_type_error(self):
        logger = EventLogger()
        with self.assertRaises(TypeError):
            logger.sink(1.0, 0, 1, "not an event")

    def test_non_emit_tuple_raises_type_error(self):
        logger = EventLogger()
        with self.assertRaises(TypeError):
            logger.sink(1.0, 0, 1, ("notemit", "x", {}))
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestSinkTransport -v`
Expected: FAIL — `TestSinkTransport` cases raise `TypeError` (transport branches not yet implemented).

**Step 3: Write minimal implementation**

In `src/event_log/logger.py`, replace the `else: raise TypeError(...)` clause
of `sink` with the transport branches before it:

```python
        elif isinstance(payload, Delivery):
            msg = payload.msg
            self.records.append(EventRecord(
                t, node_id, DELIVERY, seq,
                {"msg_type": msg.type, "src": msg.src, "dst": msg.dst}))
        elif isinstance(payload, TimerFire):
            self.records.append(EventRecord(
                t, node_id, TIMER_FIRE, seq,
                {"timer_id": payload.timer_id}))
        elif isinstance(payload, PhaseAdvance):
            self.records.append(EventRecord(
                t, node_id, PHASE_ADVANCE, seq,
                {"phase_id": payload.phase_id}))
        else:
            raise TypeError(
                f"EventLogger.sink: unrecognised payload {payload!r}")
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestSinkTransport test_logger.TestSinkFailFast test_logger.TestSinkEmit -v`
Expected: PASS — all sink tests OK.

**Step 5: Commit**

```bash
git add src/event_log/logger.py tests/event_log/test_logger.py
git commit -m "task 24: EventLogger.sink transport-event normalisation"
```

---

## Task 5: `EventLogger.to_csv`

**Files:**
- Modify: `src/event_log/logger.py` (add `to_csv`)
- Test: `tests/event_log/test_logger.py` (append `TestToCsv`)

**Step 1: Write the failing test**

```python
# append to tests/event_log/test_logger.py
class TestToCsv(unittest.TestCase):
    def test_header_and_rows(self):
        logger = EventLogger()
        logger.sink(12.0, 5, -1, ("emit", "decided", {"value": "0xab"}))
        logger.sink(8.5, 3, 4,
                    Delivery(Message(1, 3, "PREPARE", None, 4.0)))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "events.csv"
            logger.to_csv(out)
            rows = out.read_text().splitlines()
        self.assertEqual(rows[0], "t,node_id,event_type,seq,fields")
        self.assertEqual(len(rows), 3)            # header + 2 records
        self.assertTrue(rows[1].startswith("12.0,5,decided,-1,"))

    def test_fields_cell_has_sorted_keys(self):
        logger = EventLogger()
        # insertion order b, a — serialisation must sort to a, b.
        logger.sink(1.0, 0, -1, ("emit", "x", {"b": 2, "a": 1}))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "e.csv"
            logger.to_csv(out)
            data_row = out.read_text().splitlines()[1]
        # last CSV cell is the fields repr; parse it back.
        import csv as _csv
        fields_cell = next(_csv.reader([data_row]))[-1]
        self.assertEqual(fields_cell, "{'a': 1, 'b': 2}")
        self.assertEqual(ast.literal_eval(fields_cell), {"a": 1, "b": 2})

    def test_empty_buffer_writes_header_only(self):
        logger = EventLogger()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "empty.csv"
            logger.to_csv(out)
            rows = out.read_text().splitlines()
        self.assertEqual(rows, ["t,node_id,event_type,seq,fields"])

    def test_creates_missing_parent_dirs(self):
        logger = EventLogger()
        logger.sink(1.0, 0, -1, ("emit", "halted", {}))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "nested" / "deeper" / "events.csv"
            logger.to_csv(out)
            self.assertTrue(out.exists())
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestToCsv -v`
Expected: FAIL — `AttributeError: 'EventLogger' object has no attribute 'to_csv'`.

**Step 3: Write minimal implementation**

Append the `to_csv` method to `EventLogger` in `src/event_log/logger.py`:

```python
    def to_csv(self, path) -> None:
        """Write the buffered records to `path` as CSV. Creates parent
        directories. The `fields` cell is the sorted-key repr of the dict —
        deterministic (insertion-order-independent) and round-trips simple
        types, including the tuple instance_id of PBFT/Narwhal decided
        events, via ast.literal_eval. An empty buffer writes header only.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(_CSV_HEADER)
            for r in self.records:
                writer.writerow((
                    r.t, r.node_id, r.event_type, r.seq,
                    repr(dict(sorted(r.fields.items()))),
                ))
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestToCsv -v`
Expected: PASS — 4 tests OK.

**Step 5: Commit**

```bash
git add src/event_log/logger.py tests/event_log/test_logger.py
git commit -m "task 24: EventLogger.to_csv export"
```

---

## Task 6: Finalise `__init__.py` re-exports

**Files:**
- Modify: `src/event_log/__init__.py`
- Test: `tests/event_log/test_logger.py` (append `TestPackageExports`)

**Step 1: Write the failing test**

```python
# append to tests/event_log/test_logger.py
class TestPackageExports(unittest.TestCase):
    def test_public_names_importable_from_package_root(self):
        import event_log
        for name in ("EventLogger", "EventRecord", "HALTED", "DECIDED",
                     "DELIVERY", "TIMER_FIRE", "PHASE_ADVANCE",
                     "TRANSPORT_EVENT_TYPES"):
            self.assertIn(name, dir(event_log), name)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestPackageExports -v`
Expected: FAIL — `HALTED` etc. not exported from the placeholder `__init__.py`.

**Step 3: Write minimal implementation**

Replace `src/event_log/__init__.py` with:

```python
"""Structured event-logging subsystem (T24).

Records the simulator's consensus event stream and exports it to CSV.
See wiki/concepts/event-log-schema.md for the design contract.

Named `event_log`, not `logging`, to avoid shadowing the stdlib module
under PYTHONPATH=src (design spec, Decision E).
"""
from .event_types import (
    DECIDED,
    DELIVERY,
    HALTED,
    PHASE_ADVANCE,
    TIMER_FIRE,
    TRANSPORT_EVENT_TYPES,
)
from .logger import EventLogger, EventRecord

__all__ = [
    "DECIDED",
    "DELIVERY",
    "EventLogger",
    "EventRecord",
    "HALTED",
    "PHASE_ADVANCE",
    "TIMER_FIRE",
    "TRANSPORT_EVENT_TYPES",
]
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v`
Expected: PASS — every event_log test green.

**Step 5: Commit**

```bash
git add src/event_log/__init__.py tests/event_log/test_logger.py
git commit -m "task 24: finalise event_log package exports"
```

---

## Task 7: Logger determinism unit test

**Files:**
- Test only: `tests/event_log/test_logger.py` (append `TestDeterminism`)

**Step 1: Write the failing test**

```python
# append to tests/event_log/test_logger.py
class TestDeterminism(unittest.TestCase):
    def test_identical_event_sequences_yield_identical_csv(self):
        # Same event sequence -> byte-identical CSV. fields dicts are
        # supplied in DIFFERENT insertion orders to prove sorted-key
        # serialisation makes the output order-independent.
        seq_a = [
            (1.0, 0, -1, ("emit", "decided", {"value": "v", "n": 1})),
            (2.0, 1, 4, Delivery(Message(0, 1, "PING", None, 1.0))),
        ]
        seq_b = [
            (1.0, 0, -1, ("emit", "decided", {"n": 1, "value": "v"})),
            (2.0, 1, 4, Delivery(Message(0, 1, "PING", None, 1.0))),
        ]
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.csv", Path(d) / "b.csv"
            la, lb = EventLogger(), EventLogger()
            for ev in seq_a:
                la.sink(*ev)
            for ev in seq_b:
                lb.sink(*ev)
            la.to_csv(a)
            lb.to_csv(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
```

**Step 2: Run test to verify it fails**

This is a test-only task; the test should **pass immediately** if Tasks 2–5
are correct (sorted-key serialisation already implemented). First run it and
confirm — if it fails, the determinism contract (design §4) is violated and
the bug is in `to_csv`, not the test.

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger.TestDeterminism -v`
Expected: PASS — 1 test OK (regression guard for design §4).

**Step 3: (no implementation — guard test)**

If Step 2 fails, fix `to_csv` so `fields` is serialised with sorted keys;
do not weaken the test.

**Step 4: Re-run full module**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_logger -v`
Expected: PASS — all `test_logger` cases OK.

**Step 5: Commit**

```bash
git add tests/event_log/test_logger.py
git commit -m "task 24: logger determinism regression test"
```

---

## Task 8: Adopt the constants in `src/nodes/node.py`

**Files:**
- Modify: `src/nodes/node.py` (import + two `emit` call sites)
- Regression test: `tests/nodes/` (existing suite must stay green)

**Step 1: Establish the regression baseline**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v`
Expected: PASS — record the test count; this is the green baseline the edit must preserve.

**Step 2: Apply the edit**

In `src/nodes/node.py`, add to the import block (after `from .message import Message`):

```python
from event_log.event_types import DECIDED, HALTED
```

In `Node.halt`, change:

```python
        self.emit("halted",
                  {"node_id": self.id, "reason": reason.name, "t": t}, t)
```

to:

```python
        self.emit(HALTED,
                  {"node_id": self.id, "reason": reason.name, "t": t}, t)
```

In `Node._emit_decided`, change:

```python
        self.emit("decided",
                  {"value": value, "instance_id": instance_id, "t": t}, t)
```

to:

```python
        self.emit(DECIDED,
                  {"value": value, "instance_id": instance_id, "t": t}, t)
```

**Step 3: Verify no import cycle**

Run: `PYTHONPATH=src python3 -c "import nodes; import event_log; print('import ok')"`
Expected: `import ok`. Dependency direction is `nodes -> event_log -> scheduler`; `event_log` never imports `nodes`, so no cycle.

**Step 4: Run the regression suite**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v`
Expected: PASS — same count as Step 1. `HALTED == "halted"` and `DECIDED == "decided"`, so the emitted events are byte-identical; existing assertions on the string values still hold.

Also re-run event_log + scheduler suites for safety:
Run: `PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v`
Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v`
Expected: PASS — both.

**Step 5: Commit**

```bash
git add src/nodes/node.py
git commit -m "task 24: adopt shared event-type constants in node.py"
```

---

## Task 9: End-to-end test — logger on a real run

**Files:**
- Create: `tests/event_log/test_e2e.py`

**Step 1: Write the failing test**

```python
# tests/event_log/test_e2e.py
"""End-to-end: the EventLogger records a real 2-node run.

A real Network drives two real Nodes through the six-phase bootstrap
(simulation-design.md §7.2) with the logger wired as event_sink at phase 4.
Exercises both event_sink shapes: emit events (decided / halted) and
transport events (delivery).
"""
import math
import tempfile
import unittest
from pathlib import Path

from nodes import HaltReason, Node
from network import DelayDist, Network, Phase
from scheduler import Scheduler

from event_log import EventLogger


class PingPongNode(Node):
    """Minimal real protocol: two nodes bounce a token; each halts after
    `budget` inbound messages, emitting `decided` then `halted`."""

    def __init__(self, node_id, peer_id, budget, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.peer_id = peer_id
        self.budget = budget
        self.hops = 0

    def _on_start(self, t):
        if self.id == 0:
            self.send(self.peer_id, "PING", {"hop": 0}, t)

    def _on_message(self, msg, t):
        self.hops += 1
        if self.hops >= self.budget:
            self._emit_decided(value="done", instance_id=self.id, t=t)
            self.halt(HaltReason.RUN_END, t)
            return
        reply = "PONG" if msg.type == "PING" else "PING"
        self.send(msg.src, reply, {"hop": self.hops}, t)

    def _on_timer(self, timer_id, payload, t):
        pass


def _run(global_seed, budget=4):
    """Six-phase bootstrap over the real Network; logger as event_sink."""
    sched = Scheduler()
    net = Network(sched,
                  (Phase(0.0, math.inf, DelayDist("constant", {"delay": 10.0})),),
                  global_seed)
    nodes = [PingPongNode(0, peer_id=1, budget=budget, global_seed=global_seed),
             PingPongNode(1, peer_id=0, budget=budget, global_seed=global_seed)]
    logger = EventLogger()
    for n in nodes:                       # phase 2: register
        net.register(n)
    sched.bind_network(net)               # phase 3: PhaseAdvance dispatch
    for n in nodes:                       # phase 3: split bind
        sched.bind(n)
        net.bind(n)
    sched.event_sink = logger.sink        # phase 4: observe
    net.start()                           # phase 5: arm
    for n in nodes:                       # phase 5: kickoff
        n.start(0.0)
    result = sched.run()                  # phase 6
    return logger, result


class TestEventLogE2E(unittest.TestCase):
    def test_run_reaches_quiescence_and_logger_captures_events(self):
        logger, result = _run(global_seed=42)
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertGreater(len(logger), 0)

    def test_both_event_sink_shapes_are_recorded(self):
        logger, _ = _run(global_seed=42)
        seen = {r.event_type for r in logger.records}
        # emit shape: decided + halted; transport shape: delivery.
        self.assertIn("decided", seen)
        self.assertIn("halted", seen)
        self.assertIn("delivery", seen)

    def test_to_csv_produces_well_formed_file(self):
        logger, _ = _run(global_seed=42)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "baseline" / "events.csv"
            logger.to_csv(out)
            rows = out.read_text().splitlines()
        self.assertEqual(rows[0], "t,node_id,event_type,seq,fields")
        self.assertEqual(len(rows), len(logger) + 1)   # header + records

    def test_two_seed_identical_runs_yield_byte_identical_csv(self):
        # determinism contract (node-model.md §8): the logger preserves
        # byte-identical replay.
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.csv", Path(d) / "b.csv"
            la, _ = _run(global_seed=42)
            lb, _ = _run(global_seed=42)
            la.to_csv(a)
            lb.to_csv(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails — then passes**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest test_e2e -v`
Expected: PASS immediately — every dependency (`EventLogger`, real `Node` /
`Network` / `Scheduler`) is already implemented. This task is an integration
*guard*, not new production code. If it fails, the defect is real — debug
with `superpowers:systematic-debugging`, do not weaken the test.

**Step 3: (no implementation — integration guard)**

**Step 4: Run the whole event_log suite**

Run: `PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v`
Expected: PASS — `test_event_types`, `test_logger`, `test_e2e` all green.

**Step 5: Commit**

```bash
git add tests/event_log/test_e2e.py
git commit -m "task 24: end-to-end logger integration test"
```

---

## Task 10: Wiki — event-log schema page, index, node-model Revision

**Files:**
- Create: `wiki/concepts/event-log-schema.md`
- Modify: `wiki/index.md` (add the new page under Concepts)
- Modify: `wiki/concepts/node-model.md` (append a `## Revisions` entry)

**Step 1: Write `wiki/concepts/event-log-schema.md`**

Author a concept page (technical register, under ~300 lines) covering:

- **Purpose** — the structured event log produced by `src/event_log/` (T24);
  raw event substrate that T40 (`output-format`) derives the metrics CSV from.
- **The `event_sink` seam** — pin the two payload shapes the scheduler emits
  (design §3.1): the `("emit", event_type, fields)` tuple from
  `Scheduler.bind`'s emit lambda (carrying `EMIT_SEQ = -1`), and the typed
  `Delivery` / `TimerFire` / `PhaseAdvance` from `Scheduler.run`. This is the
  cross-component contract the `TASKS.md` § Backlog item asked T24 to document.
- **`EventRecord` schema** — the five fields (`t`, `node_id`, `event_type`,
  `seq`, `fields`); the open-`fields`-dict convention (design Decision A) and
  why `round` / `msg_id` are `fields` keys, not columns.
- **Event-type vocabulary** — `halted`, `decided` (emit); `delivery`,
  `timer_fire`, `phase_advance` (transport); the `event_types.py` constants as
  the single source of truth.
- **Per-event `fields`** — a table: which keys each event type carries.
- **CSV format** — header, one row per record, sorted-key `repr` of `fields`.
- **Determinism** — record order = dispatch order; sorted-key serialisation
  (design §4).
- **`msg_id`** — explicitly *not* logger-synthesized (design Decision D);
  a `fields` key for protocol code (T28+) carrying a real id; record the
  broadcast-expansion rationale.
- Wikilinks: `[[concepts/simulation-design]]`, `[[concepts/node-model]]`,
  `[[concepts/network-model]]`, `[[concepts/evaluation-metrics]]`; forward
  ref to `[[concepts/output-format]]` (T40).

**Step 2: Update `wiki/index.md`**

Under `## Concepts`, add one line (alphabetical-ish, near `evaluation-metrics`):

```
- [[concepts/event-log-schema]] — Structured event-log subsystem (T24): the two-shape `event_sink` seam, the `EventRecord` schema with its open `fields` dict, the event-type vocabulary, and the CSV format. Raw event substrate T40 derives metrics from.
```

**Step 3: Append the node-model Revision**

At the end of `wiki/concepts/node-model.md` § Revisions, add:

```markdown
### 2026-05-19 — §7 event-emission names sourced from the shared `event_types` module

T24 (`src/event_log/`) introduces `event_log/event_types.py` as the single
source of truth for `event_type` strings. `src/nodes/node.py` now imports
`HALTED` / `DECIDED` from it instead of the bare string literals `"halted"` /
`"decided"` in `Node.halt` and `Node._emit_decided`. A typo in an event-type
name now fails fast (`NameError`) rather than silently producing an
unrecognised event. The §7 mandatory-event table is unchanged in content —
the emitted strings are byte-identical; only their definition site moved.
No other §s affected.
```

**Step 4: Verify wikilinks resolve**

Run: `grep -o '\[\[[^]]*\]\]' wiki/concepts/event-log-schema.md`
Manually confirm each target file exists under `wiki/` (forward ref to
`output-format` is a known not-yet-authored T40 page — acceptable).

**Step 5: Commit**

```bash
git add wiki/concepts/event-log-schema.md wiki/index.md wiki/concepts/node-model.md
git commit -m "wiki: event-log schema page; node-model Revision for T24"
```

---

## Task 11: Experiment page + log.md entry

**Files:**
- Create: `wiki/experiments/2026-05-19_logging-baseline.md`
- Modify: `wiki/log.md` (append one task entry)

**Step 1: Capture the verification facts**

Run: `git rev-parse HEAD` — record the commit hash.
Run: `PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v` — record the pass count.

**Step 2: Write `wiki/experiments/2026-05-19_logging-baseline.md`**

A build-verification experiment page (per the Engineer role) with:
- **Config** — the `test_e2e.py` 2-node ping-pong, constant 10.0 delay,
  `budget=4`, single infinite phase.
- **Seed** — `global_seed=42`.
- **Commit hash** — from Step 1.
- **Commands to re-run** — the three event_log test commands from the plan
  header.
- **Raw result location** — none persisted; the e2e writes CSV to a
  `tempfile` directory (in-memory-buffer design, Decision B).
- **Observation** — one paragraph: the logger captured both `event_sink`
  shapes, `to_csv` produced a well-formed file, two seed-identical runs were
  byte-identical (determinism contract held).
- **Decision E note** — the subsystem is `src/event_log/`, not the
  `TASKS.md`-literal `src/logging/`, to avoid shadowing stdlib `logging`.
- Wikilinks: `[[concepts/event-log-schema]]`, `[[concepts/simulation-design]]`,
  `[[concepts/node-model]]`.

**Step 3: Append to `wiki/index.md`**

Under `## Experiments`:

```
- [[experiments/2026-05-19_logging-baseline]] — T24 build-verification baseline: the EventLogger records a real 2-node ping-pong; both `event_sink` shapes captured, CSV well-formed, determinism contract holds.
```

**Step 4: Append to `wiki/log.md`**

```markdown
## [2026-05-19] code | task 24 — event-logging subsystem

- role: Engineer
- touched: src/event_log/{__init__,event_types,logger}.py, src/nodes/node.py, tests/event_log/{test_event_types,test_logger,test_e2e}.py, wiki/concepts/event-log-schema.md, wiki/concepts/node-model.md, wiki/index.md, wiki/experiments/2026-05-19_logging-baseline.md
- notes: Added the structured event-logging subsystem — a passive Scheduler.event_sink consumer normalising emit + transport events into CSV-exportable EventRecords. Pinned the two-shape event_sink seam in a new concept page; adopted shared event-type constants in node.py. Subsystem named `event_log` (not `logging`) to avoid shadowing the stdlib module.
```

**Step 5: Commit**

```bash
git add wiki/experiments/2026-05-19_logging-baseline.md wiki/index.md wiki/log.md
git commit -m "wiki: T24 logging-baseline experiment page + log entry"
```

---

## Final verification (before In Review)

Invoke `superpowers:verification-before-completion`. Run, and confirm green:

```bash
PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v
PYTHONPATH=src:tests/nodes     python3 -m unittest discover -s tests/nodes -v
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
PYTHONPATH=src:tests/network   python3 -m unittest discover -s tests/network -v
```

All four suites must pass — the event_log suite is new; the other three are
regression guards for the `node.py` edit.

Then hand off to the human:
- Flip **T24** to In Review in `TASKS.md` (the human, or the agent per
  `docs/workflow.md` — confirm at handoff); update the Dashboard counts.
- Handoff summary: files touched, wiki pages added/updated, the Decision E
  deviation (`src/logging/` → `src/event_log/`), and the open question of
  whether the `TASKS.md` T24 artifact line should be amended to match.
```
