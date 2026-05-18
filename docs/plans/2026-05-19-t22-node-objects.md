# T22 — Node Objects Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the shared lifecycle layer of the simulator's validator abstraction — an abstract `Node` base class in `src/nodes/` that protocol subclasses (T28/T32/T38) will extend.

**Architecture:** `Node` is an `abc.ABC` providing identity, a `created→running→halted` lifecycle FSM, a per-Node deterministic RNG, template-method inbound hooks (public `start`/`on_message`/`on_timer` guard lifecycle then delegate to abstract `_on_*`), outbound-API placeholders bound at bootstrap by `Scheduler`/`Network`, and an opaque `adversary` slot. Per-protocol decision logic is out of scope. The full design rationale is in `docs/superpowers/specs/2026-05-19-t22-node-objects-design.md`.

**Tech Stack:** Python 3.13, standard library only (`abc`, `enum`, `dataclasses`, `hashlib`, `random`). Tests use `unittest`. Binds against the completed T21 scheduler in `src/scheduler/`.

---

## Conventions

- **Run all tests:** `PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v`
- **Run one test module:** `PYTHONPATH=src:tests/nodes python3 -m unittest test_<name> -v`
- **Run one test:** `PYTHONPATH=src:tests/nodes python3 -m unittest test_<name>.<Class>.<method> -v`
- Test files import the package as `from nodes import ...` and helpers as `from _helpers import ...`.
- Commit messages follow the project convention: `task 22: <imperative>`. (Per `docs/workflow.md`; confirm with the human whether you or they run each commit.)
- TDD: every task writes the failing test first, watches it fail, implements the minimum, watches it pass.

---

## Task 1: Package scaffold + lifecycle enums

**Files:**
- Create: `src/nodes/__init__.py` (temporary minimal — finalised in Task 10)
- Create: `src/nodes/lifecycle.py`
- Test: `tests/nodes/test_lifecycle.py`

**Step 1: Write the failing test**

```python
# tests/nodes/test_lifecycle.py
"""Unit tests for the Node lifecycle enums (node-model.md §3)."""
import unittest

from nodes import HaltReason, Lifecycle


class TestLifecycleEnums(unittest.TestCase):
    def test_lifecycle_has_three_monotonic_stages(self):
        self.assertEqual([s.name for s in Lifecycle],
                         ["CREATED", "RUNNING", "HALTED"])

    def test_halt_reason_has_four_members(self):
        self.assertEqual({r.name for r in HaltReason},
                         {"RUN_END", "CRASHED", "SLASHED", "EXITED"})


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_lifecycle -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'nodes'`

**Step 3: Write minimal implementation**

```python
# src/nodes/lifecycle.py
"""Node lifecycle and halt-reason enumerations (node-model.md §3)."""
from __future__ import annotations

from enum import Enum


class Lifecycle(Enum):
    """Shared lifecycle stages every Node traverses, monotonically."""
    CREATED = 0
    RUNNING = 1
    HALTED = 2


class HaltReason(Enum):
    """Why a Node transitioned to HALTED (node-model.md §3 halt reasons)."""
    RUN_END = 0   # harness: configured stop condition reached
    CRASHED = 1   # harness: fault injection / non-participant adversary
    SLASHED = 2   # FSM (Casper FFG only): slashable equivocation detected
    EXITED = 3    # FSM (Casper FFG only): voluntary withdrawal at epoch end
```

```python
# src/nodes/__init__.py
"""Validator (Node) package — shared lifecycle layer (node-model.md, T22).

See docs/superpowers/specs/2026-05-19-t22-node-objects-design.md.
"""
from .lifecycle import HaltReason, Lifecycle

__all__ = ["HaltReason", "Lifecycle"]
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_lifecycle -v`
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
git add src/nodes/__init__.py src/nodes/lifecycle.py tests/nodes/test_lifecycle.py
git commit -m "task 22: add Node lifecycle and halt-reason enums"
```

---

## Task 2: Message envelope

**Files:**
- Create: `src/nodes/message.py`
- Modify: `src/nodes/__init__.py`
- Test: `tests/nodes/test_message.py`

**Step 1: Write the failing test**

```python
# tests/nodes/test_message.py
"""Unit tests for the Message envelope (node-model.md §6)."""
import dataclasses
import unittest

from nodes import Message


class TestMessage(unittest.TestCase):
    def test_fields_round_trip(self):
        m = Message(src=1, dst=2, type="PING", payload={"k": 1}, t_sent=3.0)
        self.assertEqual((m.src, m.dst, m.type, m.payload, m.t_sent),
                         (1, 2, "PING", {"k": 1}, 3.0))

    def test_dst_accepts_broadcast_literal(self):
        m = Message(src=1, dst="broadcast", type="X", payload=None, t_sent=0.0)
        self.assertEqual(m.dst, "broadcast")

    def test_message_is_frozen(self):
        m = Message(src=1, dst=2, type="PING", payload=None, t_sent=0.0)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            m.src = 9  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_message -v`
Expected: FAIL — `ImportError: cannot import name 'Message'`

**Step 3: Write minimal implementation**

```python
# src/nodes/message.py
"""The Message envelope exchanged between Nodes (node-model.md §6).

Declared by the node-model contract; owned here (T22) so the Node inbound
hooks are typed against it. T23 (network) imports this rather than redefining.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """Wire envelope. `type` / `payload` are filled per protocol by T16."""
    src: int               # NodeId of the sender
    dst: int | str         # NodeId, or the literal "broadcast"
    type: str              # protocol-specific tag (message-types, T16)
    payload: object        # T16-defined per (protocol, type)
    t_sent: float          # SimTime the sender emitted the message
```

Add `Message` to `src/nodes/__init__.py`:

```python
from .lifecycle import HaltReason, Lifecycle
from .message import Message

__all__ = ["HaltReason", "Lifecycle", "Message"]
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_message -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/nodes/message.py src/nodes/__init__.py tests/nodes/test_message.py
git commit -m "task 22: add Message envelope dataclass"
```

---

## Task 3: Node skeleton — ABC, identity, weight validation

**Files:**
- Create: `src/nodes/node.py`
- Create: `tests/nodes/_helpers.py`
- Test: `tests/nodes/test_node.py`

The `Node` ABC declares the three abstract protected hooks now so a concrete
test subclass (`FakeNode`) can exist; their public wrappers arrive in later
tasks.

**Step 1: Write the failing test**

```python
# tests/nodes/_helpers.py
"""Test doubles for the shared-layer Node (T22)."""
from __future__ import annotations

from nodes import Node


class FakeNode(Node):
    """Minimal concrete Node: records every protected-hook invocation."""

    def __init__(self, node_id=0, weight=1.0, endpoint=None, global_seed=0):
        super().__init__(node_id, weight, endpoint, global_seed)
        self.calls: list[tuple] = []

    def _on_start(self, t):
        self.calls.append(("_on_start", t))

    def _on_message(self, msg, t):
        self.calls.append(("_on_message", msg, t))

    def _on_timer(self, timer_id, payload, t):
        self.calls.append(("_on_timer", timer_id, payload, t))
```

```python
# tests/nodes/test_node.py
"""Unit tests for the shared-layer Node (node-model.md, T22)."""
import unittest

from nodes import Lifecycle, Node
from _helpers import FakeNode


class TestConstruction(unittest.TestCase):
    def test_identity_attributes_stored(self):
        n = FakeNode(node_id=7, weight=2.5, endpoint="addr", global_seed=1)
        self.assertEqual((n.id, n.weight, n.endpoint), (7, 2.5, "addr"))

    def test_starts_in_created_status(self):
        self.assertIs(FakeNode().status, Lifecycle.CREATED)

    def test_adversary_slot_defaults_none(self):
        self.assertIsNone(FakeNode().adversary)

    def test_zero_weight_accepted(self):
        self.assertEqual(FakeNode(weight=0.0).weight, 0.0)

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            FakeNode(weight=-1.0)

    def test_node_is_abstract(self):
        with self.assertRaises(TypeError):
            Node(0, 1.0, None, 0)  # type: ignore[abstract]


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node -v`
Expected: FAIL — `ImportError: cannot import name 'Node'`

**Step 3: Write minimal implementation**

```python
# src/nodes/node.py
"""Shared-layer validator abstraction (node-model.md, T14 / T22).

Design spec: docs/superpowers/specs/2026-05-19-t22-node-objects-design.md
Protocol behaviour is supplied by subclasses (PBFTNode = T28, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .lifecycle import HaltReason, Lifecycle
from .message import Message


class Node(ABC):
    """Shared lifecycle layer of a validator. Identity, lifecycle FSM,
    per-Node RNG, template-method inbound hooks, outbound-API placeholders,
    and the opaque adversary slot. Subclasses supply the protocol FSM."""

    def __init__(self, node_id: int, weight: float,
                 endpoint: object, global_seed: int) -> None:
        if weight < 0:
            raise ValueError(f"weight must be non-negative, got {weight}")
        self.id: int = node_id
        self.weight: float = weight
        self.endpoint: object = endpoint
        self.status: Lifecycle = Lifecycle.CREATED
        self._halt_reason: Optional[HaltReason] = None
        self.adversary: Optional[object] = None   # typed in Task 10

    # --- Inbound hooks: protected; protocol subclasses override these. ---

    @abstractmethod
    def _on_start(self, t: float) -> None:
        """Protocol kickoff: schedule initial timers, emit first messages."""

    @abstractmethod
    def _on_message(self, msg: Message, t: float) -> None:
        """Handle a delivered message."""

    @abstractmethod
    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        """Handle a fired timer."""
```

Add `Node` to `src/nodes/__init__.py` `__all__` and imports.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node -v`
Expected: PASS (6 tests)

**Step 5: Commit**

```bash
git add src/nodes/node.py src/nodes/__init__.py tests/nodes/_helpers.py tests/nodes/test_node.py
git commit -m "task 22: add Node ABC skeleton with identity and weight validation"
```

---

## Task 4: Per-Node deterministic RNG

**Files:**
- Modify: `src/nodes/node.py`
- Test: `tests/nodes/test_node.py` (add `TestRng`)

Implements design spec §5.2 / Decision B — `blake2b`-derived stable seed.

**Step 1: Write the failing test**

```python
# append to tests/nodes/test_node.py
from nodes.node import _stable_seed
from _helpers import FakeNode


class TestRng(unittest.TestCase):
    def test_stable_seed_is_fixed_for_fixed_input(self):
        # Process-stable: blake2b, not Python's randomised hash().
        self.assertEqual(_stable_seed(0, 0), _stable_seed(0, 0))
        self.assertIsInstance(_stable_seed(7, 3), int)

    def test_same_seed_and_id_give_identical_streams(self):
        a = FakeNode(node_id=5, global_seed=42)
        b = FakeNode(node_id=5, global_seed=42)
        self.assertEqual([a.rng.random() for _ in range(5)],
                         [b.rng.random() for _ in range(5)])

    def test_different_id_diverges(self):
        a = FakeNode(node_id=1, global_seed=42)
        b = FakeNode(node_id=2, global_seed=42)
        self.assertNotEqual(a.rng.random(), b.rng.random())

    def test_different_global_seed_diverges(self):
        a = FakeNode(node_id=1, global_seed=1)
        b = FakeNode(node_id=1, global_seed=2)
        self.assertNotEqual(a.rng.random(), b.rng.random())
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node.TestRng -v`
Expected: FAIL — `ImportError: cannot import name '_stable_seed'`

**Step 3: Write minimal implementation**

In `src/nodes/node.py`, add imports `import hashlib`, `import random`, and a
module-level helper above the class:

```python
def _stable_seed(global_seed: int, node_id: int) -> int:
    """Derive a process-stable 64-bit RNG seed from (global_seed, node_id).

    Python's built-in hash() is process-randomised for some inputs; blake2b
    is identical across processes and machines. See the node-model.md §8
    Revision dated 2026-05-19.
    """
    digest = hashlib.blake2b(f"{global_seed}:{node_id}".encode(),
                             digest_size=8).digest()
    return int.from_bytes(digest, "big")
```

In `__init__`, after `self.endpoint = ...`:

```python
        self.rng: random.Random = random.Random(
            _stable_seed(global_seed, node_id))
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node -v`
Expected: PASS (all `TestConstruction` + `TestRng` tests)

**Step 5: Commit**

```bash
git add src/nodes/node.py tests/nodes/test_node.py
git commit -m "task 22: seed per-Node RNG with a stable blake2b hash"
```

---

## Task 5: Outbound-API placeholders

**Files:**
- Modify: `src/nodes/node.py`
- Test: `tests/nodes/test_node.py` (add `TestOutboundUnbound`)

Design spec §5.5 — the five outbound methods raise until `Scheduler.bind` /
`Network.bind` overwrite them as instance attributes.

**Step 1: Write the failing test**

```python
# append to tests/nodes/test_node.py
class TestOutboundUnbound(unittest.TestCase):
    def test_send_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().send(1, "X", None, 0.0)

    def test_broadcast_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().broadcast("X", None, 0.0)

    def test_set_timer_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().set_timer("tid", 1.0, None, 0.0)

    def test_cancel_timer_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().cancel_timer("tid")

    def test_emit_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().emit("evt", {}, 0.0)

    def test_bind_overwrites_placeholder(self):
        n = FakeNode()
        n.emit = lambda et, fs, t: ("bound", et)   # simulate Scheduler.bind
        self.assertEqual(n.emit("evt", {}, 0.0), ("bound", "evt"))
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node.TestOutboundUnbound -v`
Expected: FAIL — `AttributeError: 'FakeNode' object has no attribute 'send'`

**Step 3: Write minimal implementation**

Add to `Node` in `src/nodes/node.py` (signatures match node-model.md §7
exactly; `type` shadows the builtin but is contract-faithful and unused in
these bodies):

```python
    # --- Outbound API: placeholders overwritten at bind time (spec §5.5). ---

    def send(self, dst: int, type: str, payload: object, t: float) -> None:
        raise RuntimeError(
            f"Node {self.id}.send called before Network.bind()")

    def broadcast(self, type: str, payload: object, t: float) -> None:
        raise RuntimeError(
            f"Node {self.id}.broadcast called before Network.bind()")

    def set_timer(self, timer_id: Any, delay: float,
                  payload: object, t: float) -> None:
        raise RuntimeError(
            f"Node {self.id}.set_timer called before Scheduler.bind()")

    def cancel_timer(self, timer_id: Any) -> None:
        raise RuntimeError(
            f"Node {self.id}.cancel_timer called before Scheduler.bind()")

    def emit(self, event_type: str, fields: dict, t: float) -> None:
        raise RuntimeError(
            f"Node {self.id}.emit called before Scheduler.bind()")
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/nodes/node.py tests/nodes/test_node.py
git commit -m "task 22: add fail-fast outbound-API placeholders"
```

---

## Task 6: `start()` — CREATED → RUNNING transition

**Files:**
- Modify: `src/nodes/node.py`
- Test: `tests/nodes/test_node.py` (add `TestStart`)

**Step 1: Write the failing test**

```python
# append to tests/nodes/test_node.py
class TestStart(unittest.TestCase):
    def test_start_transitions_to_running(self):
        n = FakeNode()
        n.start(0.0)
        self.assertIs(n.status, Lifecycle.RUNNING)

    def test_start_delegates_to_on_start(self):
        n = FakeNode()
        n.start(0.0)
        self.assertIn(("_on_start", 0.0), n.calls)

    def test_second_start_raises(self):
        n = FakeNode()
        n.start(0.0)
        with self.assertRaises(RuntimeError):
            n.start(0.0)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node.TestStart -v`
Expected: FAIL — `AttributeError: 'FakeNode' object has no attribute 'start'`

**Step 3: Write minimal implementation**

Add to `Node`:

```python
    # --- Inbound hooks: public; called by the Scheduler (spec §5.4). ---

    def start(self, t: float) -> None:
        """Bootstrap kickoff (scheduler phase 5). CREATED -> RUNNING."""
        if self.status is not Lifecycle.CREATED:
            raise RuntimeError(
                f"start() on Node {self.id} with status {self.status.name}")
        self.status = Lifecycle.RUNNING
        self._on_start(t)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/nodes/node.py tests/nodes/test_node.py
git commit -m "task 22: implement Node.start lifecycle transition"
```

---

## Task 7: `halt()` + mandatory `halted` event

**Files:**
- Modify: `src/nodes/node.py`
- Test: `tests/nodes/test_node.py` (add `TestHalt`)

Design spec §5.3 / §5.6. The unit test injects a recording `emit` (the real
one is bound by `Scheduler.bind`).

**Step 1: Write the failing test**

```python
# append to tests/nodes/test_node.py
from nodes import HaltReason


def _running_node_with_recorder():
    n = FakeNode()
    emitted = []
    n.emit = lambda et, fs, t: emitted.append((et, fs, t))
    n.start(0.0)
    return n, emitted


class TestHalt(unittest.TestCase):
    def test_halt_transitions_to_halted(self):
        n, _ = _running_node_with_recorder()
        n.halt(HaltReason.RUN_END, 5.0)
        self.assertIs(n.status, Lifecycle.HALTED)

    def test_halt_emits_halted_event(self):
        n, emitted = _running_node_with_recorder()
        n.halt(HaltReason.CRASHED, 9.0)
        self.assertEqual(
            emitted,
            [("halted", {"node_id": n.id, "reason": "CRASHED", "t": 9.0}, 9.0)])

    def test_second_halt_is_noop_and_keeps_first_reason(self):
        n, emitted = _running_node_with_recorder()
        n.halt(HaltReason.CRASHED, 9.0)
        n.halt(HaltReason.RUN_END, 12.0)        # blanket run-end halt
        self.assertIs(n._halt_reason, HaltReason.CRASHED)
        self.assertEqual(len(emitted), 1)        # no second event
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node.TestHalt -v`
Expected: FAIL — `AttributeError: 'FakeNode' object has no attribute 'halt'`

**Step 3: Write minimal implementation**

Add to `Node`:

```python
    def halt(self, reason: HaltReason, t: float) -> None:
        """Transition to HALTED and emit the mandatory `halted` event.
        Re-halting is a no-op: the first reason wins (the harness blanket-
        halts every Node with RUN_END at run's end). See spec §5.3."""
        if self.status is Lifecycle.HALTED:
            return
        self.status = Lifecycle.HALTED
        self._halt_reason = reason
        self.emit("halted",
                  {"node_id": self.id, "reason": reason.name, "t": t}, t)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/nodes/node.py tests/nodes/test_node.py
git commit -m "task 22: implement Node.halt and the mandatory halted event"
```

---

## Task 8: Inbound guards — `on_message` / `on_timer`

**Files:**
- Modify: `src/nodes/node.py`
- Test: `tests/nodes/test_node.py` (add `TestInboundGuards`)

Design spec §5.4 — public hooks guard lifecycle, then delegate.

**Step 1: Write the failing test**

```python
# append to tests/nodes/test_node.py
class TestInboundGuards(unittest.TestCase):
    def _msg(self):
        return Message(src=1, dst=0, type="X", payload=None, t_sent=0.0)

    def test_on_message_before_start_raises(self):
        with self.assertRaises(RuntimeError):
            FakeNode().on_message(self._msg(), 1.0)

    def test_on_timer_before_start_raises(self):
        with self.assertRaises(RuntimeError):
            FakeNode().on_timer("tid", None, 1.0)

    def test_on_message_while_running_delegates(self):
        n = FakeNode()
        n.start(0.0)
        m = self._msg()
        n.on_message(m, 2.0)
        self.assertIn(("_on_message", m, 2.0), n.calls)

    def test_on_timer_while_running_delegates(self):
        n = FakeNode()
        n.start(0.0)
        n.on_timer("tid", "pl", 2.0)
        self.assertIn(("_on_timer", "tid", "pl", 2.0), n.calls)

    def test_on_message_after_halt_is_dropped(self):
        n, _ = _running_node_with_recorder()
        n.halt(HaltReason.RUN_END, 3.0)
        before = list(n.calls)
        n.on_message(self._msg(), 4.0)
        self.assertEqual(n.calls, before)        # _on_message NOT invoked

    def test_on_timer_after_halt_is_dropped(self):
        n, _ = _running_node_with_recorder()
        n.halt(HaltReason.RUN_END, 3.0)
        before = list(n.calls)
        n.on_timer("tid", None, 4.0)
        self.assertEqual(n.calls, before)
```

Add `from nodes import Message` to the test imports if not already present.

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node.TestInboundGuards -v`
Expected: FAIL — `AttributeError: ... 'on_message'`

**Step 3: Write minimal implementation**

Add to `Node` (after `start`):

```python
    def on_message(self, msg: Message, t: float) -> None:
        """Scheduler-dispatched message delivery. Drops if halted, errors if
        not yet started, otherwise delegates to _on_message."""
        if self.status is Lifecycle.HALTED:
            return                       # halted Node ceases handling (§3)
        if self.status is Lifecycle.CREATED:
            raise RuntimeError(
                f"on_message before start() on Node {self.id}")
        self._on_message(msg, t)

    def on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        """Scheduler-dispatched timer fire. Same lifecycle guard as
        on_message, then delegates to _on_timer."""
        if self.status is Lifecycle.HALTED:
            return
        if self.status is Lifecycle.CREATED:
            raise RuntimeError(
                f"on_timer before start() on Node {self.id}")
        self._on_timer(timer_id, payload, t)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/nodes/node.py tests/nodes/test_node.py
git commit -m "task 22: add template-method inbound-hook lifecycle guards"
```

---

## Task 9: `_emit_decided` helper

**Files:**
- Modify: `src/nodes/node.py`
- Test: `tests/nodes/test_node.py` (add `TestEmitDecided`)

Design spec §5.6 — convenience so the four protocols emit `decided` with a
uniform field schema.

**Step 1: Write the failing test**

```python
# append to tests/nodes/test_node.py
class TestEmitDecided(unittest.TestCase):
    def test_emit_decided_uses_uniform_schema(self):
        n = FakeNode()
        emitted = []
        n.emit = lambda et, fs, t: emitted.append((et, fs, t))
        n._emit_decided(value="digest", instance_id=(1, 2), t=8.0)
        self.assertEqual(
            emitted,
            [("decided",
              {"value": "digest", "instance_id": (1, 2), "t": 8.0}, 8.0)])
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node.TestEmitDecided -v`
Expected: FAIL — `AttributeError: ... '_emit_decided'`

**Step 3: Write minimal implementation**

Add to `Node`:

```python
    def _emit_decided(self, value: Any, instance_id: Any, t: float) -> None:
        """Emit a `decided` event for an FSM instance reaching its terminal
        state. Convenience for protocol subclasses (spec §5.6); the FSM layer
        decides *when* to call it."""
        self.emit("decided",
                  {"value": value, "instance_id": instance_id, "t": t}, t)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/nodes/node.py tests/nodes/test_node.py
git commit -m "task 22: add _emit_decided convenience helper"
```

---

## Task 10: `AdversaryProfile` placeholder type + finalise exports

**Files:**
- Modify: `src/nodes/node.py`
- Modify: `src/nodes/__init__.py`
- Test: `tests/nodes/test_node.py` (add `TestAdversarySlot`)

Design spec §5.7 — opaque slot; T18 fills the strategy.

**Step 1: Write the failing test**

```python
# append to tests/nodes/test_node.py
from nodes import AdversaryProfile


class TestAdversarySlot(unittest.TestCase):
    def test_adversary_profile_is_importable(self):
        self.assertTrue(hasattr(AdversaryProfile, "__mro_entries__")
                        or AdversaryProfile is not None)

    def test_adversary_slot_is_assignable(self):
        n = FakeNode()
        sentinel = object()
        n.adversary = sentinel
        self.assertIs(n.adversary, sentinel)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_node.TestAdversarySlot -v`
Expected: FAIL — `ImportError: cannot import name 'AdversaryProfile'`

**Step 3: Write minimal implementation**

In `src/nodes/node.py`, add `Protocol` to the typing import and define above
`Node`:

```python
class AdversaryProfile(Protocol):
    """Opaque adversary strategy slot. Owned by T18 (adversary-model.md);
    this placeholder exists only so Node.adversary is typed. T22 holds the
    slot and does not introspect it."""
    ...
```

Change the `__init__` adversary line to the typed form:

```python
        self.adversary: Optional[AdversaryProfile] = None
```

Finalise `src/nodes/__init__.py`:

```python
"""Validator (Node) package — shared lifecycle layer (node-model.md, T22).

See docs/superpowers/specs/2026-05-19-t22-node-objects-design.md.
"""
from .lifecycle import HaltReason, Lifecycle
from .message import Message
from .node import AdversaryProfile, Node

__all__ = [
    "AdversaryProfile",
    "HaltReason",
    "Lifecycle",
    "Message",
    "Node",
]
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v`
Expected: PASS — full unit suite green.

**Step 5: Commit**

```bash
git add src/nodes/node.py src/nodes/__init__.py tests/nodes/test_node.py
git commit -m "task 22: add AdversaryProfile placeholder type and finalise exports"
```

---

## Task 11: End-to-end test — ping-pong through the real Scheduler

**Files:**
- Modify: `tests/nodes/_helpers.py` (add `PingPongNode`, `LoopbackNetwork`)
- Test: `tests/nodes/test_e2e.py`

Design spec §7.2 — a minimal real protocol driven through the completed T21
scheduler's six-phase bootstrap, plus a determinism check.

**Step 1: Write the failing test**

Add to `tests/nodes/_helpers.py`:

```python
from nodes import HaltReason, Message, Node
from scheduler import Delivery, Scheduler


class PingPongNode(Node):
    """Minimal real protocol: two nodes bounce a token; each halts after
    `budget` inbound messages. Draws from self.rng so the e2e determinism
    check exercises per-Node RNG seeding end-to-end."""

    def __init__(self, node_id, peer_id, budget, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.peer_id = peer_id
        self.budget = budget
        self.hops = 0

    def _on_start(self, t):
        if self.id == 0:
            self.send(self.peer_id, "PING",
                      {"hop": 0, "r": self.rng.random()}, t)

    def _on_message(self, msg, t):
        self.hops += 1
        if self.hops >= self.budget:
            self._emit_decided(value="done", instance_id=self.id, t=t)
            self.halt(HaltReason.RUN_END, t)
            return
        reply = "PONG" if msg.type == "PING" else "PING"
        self.send(msg.src, reply,
                  {"hop": self.hops, "r": self.rng.random()}, t)

    def _on_timer(self, timer_id, payload, t):
        pass


class LoopbackNetwork:
    """Minimal stand-in for the T23 Network: delivers each send/broadcast as a
    Scheduler Delivery after a fixed link delay. The real Network is T23."""

    LINK_DELAY = 10.0

    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.members: dict[int, Node] = {}

    def register(self, node):
        self.members[node.id] = node

    def bind(self, node):
        node.send = lambda dst, type, payload, t: self._deliver(
            node.id, dst, type, payload, t)
        node.broadcast = lambda type, payload, t: self._broadcast(
            node.id, type, payload, t)

    def _deliver(self, src, dst, type, payload, t):
        msg = Message(src=src, dst=dst, type=type, payload=payload, t_sent=t)
        self.scheduler.schedule(Delivery(msg), t + self.LINK_DELAY, dst)

    def _broadcast(self, src, type, payload, t):
        for dst in sorted(self.members):          # deterministic order
            if dst != src:
                self._deliver(src, dst, type, payload, t)
```

```python
# tests/nodes/test_e2e.py
"""End-to-end: the Scheduler drives Nodes through the six-phase bootstrap.

Exercises node-model.md lifecycle + the simulation-design.md §7.2 bootstrap
and the determinism contract (node-model.md §8).
"""
import unittest

from scheduler import Scheduler
from _helpers import LoopbackNetwork, PingPongNode


def _run(global_seed, budget=4):
    sched = Scheduler()
    net = LoopbackNetwork(sched)
    nodes = [
        PingPongNode(0, peer_id=1, budget=budget, global_seed=global_seed),
        PingPongNode(1, peer_id=0, budget=budget, global_seed=global_seed),
    ]
    capture: list = []
    sched.event_sink = lambda t, nid, seq, ev: capture.append(
        (t, nid, seq, repr(ev)))
    for n in nodes:                       # phase 2: register
        net.register(n)
    for n in nodes:                       # phase 3: split bind
        sched.bind(n)
        net.bind(n)
    for n in nodes:                       # phase 5: kickoff
        n.start(0.0)
    result = sched.run()                  # phase 6
    return result, capture


class TestNodeE2E(unittest.TestCase):
    def test_run_reaches_quiescence(self):
        result, _ = _run(global_seed=42)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_decided_and_halted_events_emitted(self):
        _, capture = _run(global_seed=42)
        kinds = [ev for (_, _, _, ev) in capture]
        self.assertTrue(any("'decided'" in k for k in kinds))
        self.assertTrue(any("'halted'" in k for k in kinds))

    def test_two_seed_identical_runs_are_byte_identical(self):
        _, cap_a = _run(global_seed=42)
        _, cap_b = _run(global_seed=42)
        self.assertEqual(cap_a, cap_b)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_e2e -v`
Expected: FAIL — `ImportError: cannot import name 'PingPongNode'` (before
the `_helpers.py` edit) then PASS once both edits are in. Make the test fail
first by writing `test_e2e.py` before editing `_helpers.py`.

**Step 3: Write minimal implementation**

The `_helpers.py` additions above are the implementation. No `src/` change.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest test_e2e -v`
Expected: PASS (3 tests)

Then run the full suite:
Run: `PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v`
Expected: PASS (all unit + e2e tests)

And confirm no scheduler regression from the shared `Message` type:
Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v`
Expected: PASS (unchanged from T21)

**Step 5: Commit**

```bash
git add tests/nodes/_helpers.py tests/nodes/test_e2e.py
git commit -m "task 22: add end-to-end ping-pong and determinism test"
```

---

## Task 12: Wiki deliverables

**Files:**
- Create: `wiki/experiments/2026-05-19_node-baseline.md`
- Modify: `wiki/concepts/node-model.md` (append a `## Revisions` entry)
- Modify: `wiki/index.md`
- Modify: `wiki/log.md`

No tests. This task records durable knowledge per `docs/wiki-spec.md`.

**Step 1: Run `superpowers:verification-before-completion`**

Re-run both suites and capture the passing output for the experiment page:

```
PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
```

Record the current commit hash: `git rev-parse --short HEAD`.

**Step 2: Write the experiment page**

`wiki/experiments/2026-05-19_node-baseline.md` — follow the structure of
`wiki/experiments/2026-05-18_scheduler-baseline.md`:
- One-line summary; config (n=2 PingPong nodes, budget=4, link delay 10.0,
  `global_seed=42`); seeds; commit hash; re-run commands (the two `unittest`
  lines above); raw result location (the test suite itself — no CSV);
  one-paragraph observation: the shared-layer `Node` drives a 2-node
  ping-pong through the full six-phase bootstrap to quiescence; `decided` and
  `halted` events emit; two seed-identical runs are byte-identical.
- Back-links: `[[concepts/node-model]]`, `[[concepts/simulation-design]]`.

**Step 3: Append the node-model Revision**

Append to `wiki/concepts/node-model.md` under `## Revisions`:

```markdown
### 2026-05-19 — §8 per-Node RNG seeding uses a stable hash

T22 (`src/nodes/`) implements per-Node RNG seeding with a `blake2b`-derived
stable hash — `int.from_bytes(blake2b(f"{global_seed}:{node_id}").digest())`
— rather than the literal `seed = hash((global_seed, node_id))` of §8.
Python's built-in `hash()` is process-randomised for string and bytes inputs
and is not guaranteed stable across processes or machines; `blake2b` is. This
resolves the §11 open-to-revision item "Per-`Node` RNG seeding hash" and
upholds the §8 byte-identical-replay contract under T27's cross-process
reproducibility. No other §s are affected: the determinism *contract* is
unchanged; only the seed-derivation primitive is pinned.
```

**Step 4: Update `wiki/index.md` and `wiki/log.md`**

In `wiki/index.md`, add under `## Experiments`:

```markdown
- [[experiments/2026-05-19_node-baseline]] — T22 build-verification baseline: the shared-layer `Node` drives a 2-node ping-pong through the six-phase bootstrap to quiescence; lifecycle, event emission, and the determinism contract hold.
```

Append to `wiki/log.md` (format per `docs/wiki-spec.md` § Log format):

```markdown
## [2026-05-19] code | task 22 — shared-layer Node objects

- role: Engineer
- touched: src/nodes/, tests/nodes/, docs/superpowers/specs/2026-05-19-t22-node-objects-design.md, docs/plans/2026-05-19-t22-node-objects.md, wiki/concepts/node-model.md, wiki/experiments/2026-05-19_node-baseline.md, wiki/index.md
- notes: Implemented the shared lifecycle layer of the validator abstraction (abstract `Node`: lifecycle FSM, per-Node RNG, template-method inbound hooks, outbound-API placeholders, opaque adversary slot, `Message` envelope). Per-protocol FSMs deferred to T28/T32/T38. Recorded a node-model.md §8 Revision for stable blake2b RNG seeding.
```

**Step 5: Commit**

```bash
git add wiki/
git commit -m "task 22: add node-baseline experiment page and node-model RNG-seeding revision"
```

---

## Done criteria

- `src/nodes/` contains `__init__.py`, `lifecycle.py`, `message.py`, `node.py`.
- Full `tests/nodes/` suite passes (unit + e2e); `tests/scheduler/` still green.
- `wiki/` updated: experiment page, node-model Revision, index, log.
- Then (outside this plan): flip T22 to In Review in `TASKS.md`, push the
  branch, summarise for the human. The human flips to Completed on merge.
