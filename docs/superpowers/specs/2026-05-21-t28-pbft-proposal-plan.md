# T28 PBFT Proposal Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Wrap each implementation task in superpowers:test-driven-development.

**Goal:** Build the `src/pbft/` subsystem implementing the **pre-prepare phase** of PBFT — the primary drains a stub workload, broadcasts `PRE-PREPARE`, locally self-transitions, and recipients validate against five rules to reach `PRE_PREPARED`. Voting, finalisation, and view-change are explicitly **T29**.

**Architecture:** A `PBFTNode(Node)` subclass over the W3 contracts (`Node` / `Network` / `Scheduler` / `event_log`). The four-state `Instance` FSM is declared in full but only `IDLE → PRE_PREPARED` is wired (skeleton-cut, Decision A in the spec). A `propose` timer drains a stub `workload: list[bytes]`; the primary self-loops the transition because `Network.submit_broadcast` excludes the sender. The five-rule validator emits a single `pbft_rejected` observable on any failure. Approved design: `docs/superpowers/specs/2026-05-21-t28-pbft-proposal-design.md`.

**Tech Stack:** Python 3.13, stdlib only (`hashlib`, `dataclasses`, `enum`, `typing`). Tests are `unittest.TestCase` (no `pytest` in this environment). Imports under `PYTHONPATH=src`.

**Test commands** (no `conftest.py` / `pyproject.toml`; `src` plus the test dir go on `PYTHONPATH`):
- All pbft tests: `PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v`
- One module: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_validation -v`
- One test: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_validation.TestPrePrepareValidation.test_view_mismatch_rejects -v`
- Integration: `PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_proposal -v`
- Regression (no upstream src/ changes in T28, but the integration test depends on every W3 module): `PYTHONPATH=src:tests/integration python3 -m unittest discover -s tests/integration -v`

**Commit policy:** `docs/workflow.md` § Commit convention specifies per-task commits (`task 28: <imperative>`). The `/prj-pickup` session instruction says the human performs commits. Each task below ends with a commit checkpoint — the executor stages the listed files and either commits with the given message or pauses for the human, per the decision taken at execution handoff. The human always performs the In-Review status flip.

**Scope guard (Decision A — skeleton FSM):** `Instance` declares all four states (`IDLE`, `PRE_PREPARED`, `PREPARED`, `COMMITTED`) and reserves the per-`(view, seq)` quorum dicts. T28 wires only `IDLE → PRE_PREPARED`. PREPARE / COMMIT / VIEW-CHANGE / NEW-VIEW messages route to a **silent no-op** branch (no rejection event). The four placeholder payload dataclasses are declared so T29 fills in handlers, not dataclasses. If a task below asks you to wire any handler beyond `_handle_pre_prepare`, stop — that is T29 territory.

---

## Task 1: `digest` helper

**Files:**
- Create: `src/pbft/__init__.py` (minimal placeholder this task; finalised in Task 7)
- Create: `src/pbft/digest.py`
- Create: `tests/pbft/__init__.py` (empty — enables `unittest discover`)
- Create: `tests/pbft/test_digest.py`

**Step 1: Write the failing test**

```python
# tests/pbft/test_digest.py
"""32-byte blake2b digest helper used by PRE-PREPARE construction and
validation (T28 spec § 6)."""
import unittest

from pbft.digest import digest


class TestDigest(unittest.TestCase):
    def test_output_width_is_32_bytes(self):
        self.assertEqual(len(digest(b"")), 32)
        self.assertEqual(len(digest(b"hello")), 32)

    def test_deterministic_across_calls(self):
        # Same input -> same output, across calls and within a process.
        self.assertEqual(digest(b"hello"), digest(b"hello"))

    def test_distinct_inputs_yield_distinct_outputs(self):
        # Collision resistance check is not the unit's job; this is a
        # sanity guard that we did not accidentally return a constant.
        self.assertNotEqual(digest(b"A"), digest(b"B"))

    def test_accepts_bytes_only(self):
        with self.assertRaises(TypeError):
            digest("not-bytes")             # str, not bytes


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_digest -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pbft'`.

**Step 3: Write minimal implementation**

```python
# src/pbft/__init__.py  (placeholder — Task 7 finalises the re-exports)
"""Simplified PBFT consensus subsystem (T28 + T29).

T28 ships the pre-prepare phase. Voting, finalisation, and view-change
are T29. See docs/superpowers/specs/2026-05-21-t28-pbft-proposal-design.md.
"""
```

```python
# src/pbft/digest.py
"""32-byte blake2b digest helper for PBFT message integrity (T28 spec § 6).

Matches the process-stable hash discipline established for the per-Node
RNG seed (src/nodes/node.py:_stable_seed) and the network RNG seed
(src/network/network.py:_network_seed). blake2b, not hash() — Python's
hash() of bytes is process-stable but the discipline is uniform.
"""
from __future__ import annotations

import hashlib


def digest(payload: bytes) -> bytes:
    """Return the 32-byte blake2b digest of `payload`.

    Width matches `wiki/concepts/message-types.md` § 7 (Hash digest = 32B).
    """
    return hashlib.blake2b(payload, digest_size=32).digest()
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_digest -v`
Expected: PASS — 4 tests.

**Step 5: Commit**

```bash
git add src/pbft/__init__.py src/pbft/digest.py tests/pbft/__init__.py tests/pbft/test_digest.py
git commit -m "task 28: blake2b digest helper for PBFT"
```

---

## Task 2: Message payload dataclasses

**Files:**
- Create: `src/pbft/messages.py`
- Create: `tests/pbft/test_messages.py`

**Step 1: Write the failing test**

```python
# tests/pbft/test_messages.py
"""PBFT payload dataclasses (T28 spec § 4).

T28 only constructs `PrePreparePayload`. The four placeholder payloads
exist so T29 grows by filling in handlers, not by adding new dataclasses;
the tests guard their shape so a T29 PR cannot silently break it.
"""
import unittest
from dataclasses import FrozenInstanceError

from pbft.messages import (
    CommitPayload,
    NewViewPayload,
    PreparePayload,
    PrePreparePayload,
    ViewChangePayload,
)


class TestPrePreparePayload(unittest.TestCase):
    def test_required_field_construction(self):
        pp = PrePreparePayload(view=0, seq=0,
                               request_digest=b"\x00" * 32,
                               request_payload=b"BATCH")
        self.assertEqual(pp.view, 0)
        self.assertEqual(pp.seq, 0)
        self.assertEqual(pp.request_digest, b"\x00" * 32)
        self.assertEqual(pp.request_payload, b"BATCH")

    def test_frozen(self):
        pp = PrePreparePayload(view=0, seq=0,
                               request_digest=b"\x00" * 32,
                               request_payload=b"BATCH")
        with self.assertRaises(FrozenInstanceError):
            pp.view = 1


class TestPlaceholderPayloads(unittest.TestCase):
    """T29 owns these. The shapes are pinned here so a T29 change is loud."""

    def test_prepare_payload_fields(self):
        p = PreparePayload(view=0, seq=0, request_digest=b"\x00" * 32)
        self.assertEqual((p.view, p.seq, p.request_digest),
                         (0, 0, b"\x00" * 32))

    def test_commit_payload_fields(self):
        c = CommitPayload(view=0, seq=0, request_digest=b"\x00" * 32)
        self.assertEqual((c.view, c.seq, c.request_digest),
                         (0, 0, b"\x00" * 32))

    def test_view_change_payload_fields(self):
        vc = ViewChangePayload(new_view=1, last_stable_seq=0, prepared=[])
        self.assertEqual(vc.new_view, 1)
        self.assertEqual(vc.last_stable_seq, 0)
        self.assertEqual(vc.prepared, [])

    def test_new_view_payload_fields(self):
        nv = NewViewPayload(new_view=1, vc_proofs=[], reissued=[])
        self.assertEqual(nv.new_view, 1)
        self.assertEqual(nv.vc_proofs, [])
        self.assertEqual(nv.reissued, [])


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_messages -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pbft.messages'`.

**Step 3: Write minimal implementation**

```python
# src/pbft/messages.py
"""PBFT wire-payload dataclasses (T28 spec § 4).

Realises `wiki/concepts/message-types.md` § 3 for the PBFT row set. T28
only constructs `PrePreparePayload`; the other four are declared so T29
grows by filling in handlers, not by adding new dataclasses.

The shared `Message` envelope (src.nodes.message.Message) carries these
as its `payload` field; envelope-level `src` / `dst` / `t_sent` are never
duplicated in the payload (`message-types.md` § 1).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PrePreparePayload:
    """`PRE-PREPARE` wire payload (message-types.md § 3).

    `request_payload` is `bytes` here (the v1 abstraction does not split
    transactions); widens to `list[Transaction]` if T19/T27 grows a
    per-transaction model (spec § 4 / § 12).
    """
    view: int
    seq: int
    request_digest: bytes
    request_payload: bytes


# --- T29 placeholders. Declared, not consumed in T28. ---

@dataclass(frozen=True)
class PreparePayload:
    view: int
    seq: int
    request_digest: bytes


@dataclass(frozen=True)
class CommitPayload:
    view: int
    seq: int
    request_digest: bytes


@dataclass(frozen=True)
class ViewChangePayload:
    new_view: int
    last_stable_seq: int
    prepared: list[tuple[int, int, bytes]] = field(default_factory=list)


@dataclass(frozen=True)
class NewViewPayload:
    new_view: int
    vc_proofs: list[ViewChangePayload] = field(default_factory=list)
    reissued: list[PrePreparePayload] = field(default_factory=list)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_messages -v`
Expected: PASS — 6 tests.

**Step 5: Commit**

```bash
git add src/pbft/messages.py tests/pbft/test_messages.py
git commit -m "task 28: PBFT payload dataclasses (PrePreparePayload + T29 placeholders)"
```

---

## Task 3: `Instance` and `InstanceState`

**Files:**
- Create: `src/pbft/instance.py`
- Create: `tests/pbft/test_instance.py`

**Step 1: Write the failing test**

```python
# tests/pbft/test_instance.py
"""Per-(view, seq) PBFT instance state (T28 spec § 5)."""
import unittest

from pbft.instance import Instance, InstanceState


class TestInstanceState(unittest.TestCase):
    def test_members_present(self):
        # Four states declared up front (skeleton-cut, Decision A);
        # PREPARED and COMMITTED stay unreachable in T28.
        self.assertEqual(InstanceState.IDLE.value, 0)
        self.assertEqual(InstanceState.PRE_PREPARED.value, 1)
        self.assertEqual(InstanceState.PREPARED.value, 2)
        self.assertEqual(InstanceState.COMMITTED.value, 3)

    def test_distinct_identities(self):
        members = {InstanceState.IDLE, InstanceState.PRE_PREPARED,
                   InstanceState.PREPARED, InstanceState.COMMITTED}
        self.assertEqual(len(members), 4)


class TestInstance(unittest.TestCase):
    def test_defaults(self):
        i = Instance(view=0, seq=0)
        self.assertEqual(i.view, 0)
        self.assertEqual(i.seq, 0)
        self.assertIs(i.state, InstanceState.IDLE)
        self.assertIsNone(i.digest)
        self.assertEqual(i.prepares, {})       # T29-owned, must start empty
        self.assertEqual(i.commits, {})        # T29-owned, must start empty

    def test_prepares_commits_are_independent_per_instance(self):
        # Default factory: every Instance gets its own dict, not a shared one.
        a, b = Instance(view=0, seq=0), Instance(view=0, seq=1)
        a.prepares[1] = b"\x00" * 32
        self.assertEqual(a.prepares, {1: b"\x00" * 32})
        self.assertEqual(b.prepares, {})

    def test_state_is_mutable(self):
        # The dataclass is not frozen; T28's _accept_pre_prepare assigns
        # state and digest in place.
        i = Instance(view=0, seq=0)
        i.state = InstanceState.PRE_PREPARED
        i.digest = b"\x11" * 32
        self.assertIs(i.state, InstanceState.PRE_PREPARED)
        self.assertEqual(i.digest, b"\x11" * 32)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_instance -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pbft.instance'`.

**Step 3: Write minimal implementation**

```python
# src/pbft/instance.py
"""Per-(view, seq) PBFT instance data plane (T28 spec § 5).

Realises wiki/algorithms/pbft.md § Three-phase commit. The four-state
enum is declared up front (skeleton-cut, Decision A); T28 only wires
IDLE -> PRE_PREPARED. The prepares / commits quorum dicts are reserved
for T29.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class InstanceState(Enum):
    IDLE = 0
    PRE_PREPARED = 1
    PREPARED = 2       # T29-wired
    COMMITTED = 3      # T29-wired


@dataclass
class Instance:
    """One PBFT (view, seq) instance. Lazily created on the first valid
    PRE-PREPARE (or on the primary's self-loop) per spec § 7.5.
    """
    view: int
    seq: int
    state: InstanceState = InstanceState.IDLE
    digest: Optional[bytes] = None
    # T29: quorum collection. src -> digest, one entry per matching message.
    prepares: dict[int, bytes] = field(default_factory=dict)
    commits: dict[int, bytes] = field(default_factory=dict)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_instance -v`
Expected: PASS — 5 tests.

**Step 5: Commit**

```bash
git add src/pbft/instance.py tests/pbft/test_instance.py
git commit -m "task 28: Instance / InstanceState (four-state skeleton, T28 wires IDLE→PRE_PREPARED)"
```

---

## Task 4: `PBFTNode` constructor + primary detection

**Files:**
- Create: `src/pbft/node.py`
- Create: `tests/pbft/test_node_propose.py` (this task: constructor + primary detection only; the propose body lands in Task 6)

**Step 1: Write the failing test**

```python
# tests/pbft/test_node_propose.py
"""PBFTNode construction, primary detection, and (Task 6) propose path."""
import unittest

from pbft.node import PBFTNode


def _node(node_id: int, n: int, *, workload=None, propose_delay=1.0,
          initial_view=0, weight=1.0, global_seed=42) -> PBFTNode:
    return PBFTNode(node_id=node_id, weight=weight, endpoint=None,
                    global_seed=global_seed, n=n, workload=workload,
                    propose_delay=propose_delay, initial_view=initial_view)


class TestPBFTNodeConstructor(unittest.TestCase):
    def test_defaults_for_non_primary(self):
        # workload=None -> empty list copy; never blocks construction.
        n = _node(1, n=4)
        self.assertEqual(n.n, 4)
        self.assertEqual(n.f, 1)             # (4-1)//3 = 1
        self.assertEqual(n.view, 0)
        self.assertFalse(n.view_changing)
        self.assertEqual(n.workload, [])
        self.assertEqual(n.propose_delay, 1.0)
        self.assertEqual(n.next_seq, 0)
        self.assertEqual(n.inst, {})

    def test_workload_is_copied(self):
        # Caller's list must not be mutated when the primary drains.
        src = [b"A", b"B"]
        n = _node(0, n=4, workload=src)
        n.workload.append(b"C")
        self.assertEqual(src, [b"A", b"B"])  # untouched

    def test_f_for_n_7(self):
        self.assertEqual(_node(0, n=7).f, 2)     # (7-1)//3 = 2

    def test_rejects_non_positive_n(self):
        with self.assertRaises(ValueError):
            _node(0, n=0)
        with self.assertRaises(ValueError):
            _node(0, n=-1)

    def test_rejects_node_id_outside_range(self):
        with self.assertRaises(ValueError):
            _node(4, n=4)                    # id == n is out of range
        # Negative node_id is caught upstream by Node.__init__; PBFTNode
        # narrows it to "must be < n".

    def test_rejects_non_positive_propose_delay(self):
        with self.assertRaises(ValueError):
            _node(0, n=4, propose_delay=0.0)
        with self.assertRaises(ValueError):
            _node(0, n=4, propose_delay=-1.0)


class TestIsPrimary(unittest.TestCase):
    def test_v_mod_n_rule_n4(self):
        nodes = [_node(i, n=4) for i in range(4)]
        # view 0 -> node 0; view 1 -> node 1; view 5 -> node 1.
        self.assertTrue(nodes[0]._is_primary(0))
        self.assertFalse(nodes[1]._is_primary(0))
        self.assertTrue(nodes[1]._is_primary(1))
        self.assertTrue(nodes[1]._is_primary(5))

    def test_v_mod_n_rule_n7(self):
        nodes = [_node(i, n=7) for i in range(7)]
        for v in range(14):
            primary_id = v % 7
            for i in range(7):
                self.assertEqual(nodes[i]._is_primary(v), i == primary_id,
                                 f"view={v} node={i} primary_id={primary_id}")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_propose -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'pbft.node'`.

**Step 3: Write minimal implementation**

```python
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

    # --- Node ABC hooks: stubs in this task; Tasks 5 + 6 fill them in. ---

    def _on_start(self, t: float) -> None:
        raise NotImplementedError("Task 6")

    def _on_message(self, msg: Message, t: float) -> None:
        raise NotImplementedError("Task 5")

    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        raise NotImplementedError("Task 6")

    # --- Primary detection (Decision D). ---

    def _is_primary(self, view: int) -> bool:
        return self.id == (view % self.n)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_propose -v`
Expected: PASS — 8 tests (the `NotImplementedError` stubs are not exercised yet).

**Step 5: Commit**

```bash
git add src/pbft/node.py tests/pbft/test_node_propose.py
git commit -m "task 28: PBFTNode constructor + v-mod-n primary detection"
```

---

## Task 5: `_on_message` dispatch + `_handle_pre_prepare` validation

**Files:**
- Modify: `src/pbft/node.py` (replace `_on_message` stub; add `_handle_pre_prepare`, `_accept_pre_prepare`, `_reject`)
- Create: `tests/pbft/test_node_validation.py`

**Step 1: Write the failing test**

```python
# tests/pbft/test_node_validation.py
"""Recipient validation of PRE-PREPARE (T28 spec § 7.4).

Each test instantiates one PBFTNode in isolation, hand-builds a Message,
stubs the bind-time outbound API (broadcast / set_timer / emit) with
capturers, and calls node.on_message directly. The five rejection rules
are exercised one-per-test plus the happy path.

Lifecycle: Node.on_message refuses CREATED nodes (src/nodes/node.py),
so every test calls _kickoff(node) to walk through start() -> RUNNING
without running the real propose path.
"""
import unittest
from typing import Any

from nodes import Message
from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import PrePreparePayload
from pbft.node import PBFT_PRE_PREPARED, PBFT_REJECTED, PBFTNode


def _node(node_id: int, n: int, *, view=0) -> PBFTNode:
    return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                    global_seed=42, n=n, workload=None,
                    propose_delay=1.0, initial_view=view)


def _install_capturers(node: PBFTNode):
    """Replace bind-time placeholders with capturers, returning the lists
    each captures into. Tests assert against these lists."""
    emitted: list[tuple[str, dict, float]] = []
    broadcasts: list[tuple[str, object, float]] = []
    sends: list[tuple[int, str, object, float]] = []
    timers: list[tuple[Any, float, object, float]] = []
    node.emit = lambda et, fields, t: emitted.append((et, fields, t))
    node.broadcast = lambda type, payload, t: broadcasts.append(
        (type, payload, t))
    node.send = lambda dst, type, payload, t: sends.append(
        (dst, type, payload, t))
    node.set_timer = lambda tid, delay, payload, t: timers.append(
        (tid, delay, payload, t))
    return emitted, broadcasts, sends, timers


def _kickoff(node: PBFTNode):
    """Force RUNNING without firing the real propose path. The Node ABC
    forbids on_message in CREATED; this is the minimum incantation."""
    from nodes.lifecycle import Lifecycle
    node.status = Lifecycle.RUNNING


def _pre_prepare_msg(src: int, view: int, seq: int, batch: bytes,
                     digest_override: bytes | None = None) -> Message:
    d = digest_override if digest_override is not None else digest(batch)
    pp = PrePreparePayload(view=view, seq=seq,
                           request_digest=d, request_payload=batch)
    return Message(src=src, dst=1, type="PRE-PREPARE", payload=pp,
                   t_sent=0.0)


# --- Happy path -----------------------------------------------------------

class TestHappyPath(unittest.TestCase):
    def test_valid_pre_prepare_transitions_idle_to_pre_prepared(self):
        node = _node(node_id=1, n=4)        # primary in view 0 is node 0
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"A")
        node.on_message(msg, t=5.0)

        inst = node.inst[(0, 0)]
        self.assertIs(inst.state, InstanceState.PRE_PREPARED)
        self.assertEqual(inst.digest, digest(b"A"))
        # One pbft_pre_prepared event, zero rejections.
        kinds = [e[0] for e in emitted]
        self.assertIn(PBFT_PRE_PREPARED, kinds)
        self.assertNotIn(PBFT_REJECTED, kinds)


# --- Rule 1: sender is the primary for the asserted view -----------------

class TestRule1NonPrimarySender(unittest.TestCase):
    def test_non_primary_sender_rejects(self):
        # In view 0 the primary is node 0; node 2 spoofing a PRE-PREPARE
        # must be rejected.
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = _pre_prepare_msg(src=2, view=0, seq=0, batch=b"A")
        node.on_message(msg, t=5.0)

        self.assertNotIn((0, 0), node.inst)
        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "non_primary_sender")


# --- Rule 2: view matches recipient's current view -----------------------

class TestRule2ViewMismatch(unittest.TestCase):
    def test_future_view_rejects(self):
        # Recipient is in view 0; primary for view 1 (node 1) sends a
        # PRE-PREPARE asserting view 1. The recipient drops it.
        node = _node(node_id=2, n=4, view=0)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = _pre_prepare_msg(src=1, view=1, seq=0, batch=b"A")
        node.on_message(msg, t=5.0)

        self.assertNotIn((1, 0), node.inst)
        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "view_mismatch")


# --- Rule 3: not view-changing ------------------------------------------

class TestRule3ViewChanging(unittest.TestCase):
    def test_view_changing_blocks_pre_prepare(self):
        # T29 will set view_changing; we set it by hand to exercise the
        # branch in T28.
        node = _node(node_id=1, n=4)
        node.view_changing = True
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"A")
        node.on_message(msg, t=5.0)

        self.assertNotIn((0, 0), node.inst)
        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "view_changing")


# --- Rule 4: not already advanced past IDLE for (view, seq) -------------

class TestRule4DuplicatePrePrepare(unittest.TestCase):
    def test_second_pre_prepare_for_same_view_seq_rejects(self):
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        first = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"A")
        node.on_message(first, t=5.0)
        # First call accepted (covered by TestHappyPath); reset emitted to
        # isolate the second one's effect.
        emitted.clear()

        # A second PRE-PREPARE for (0, 0), even with the same batch, is
        # a duplicate at this instance and must be dropped. Equivocation
        # (a different batch) is a stronger form of the same reject.
        second = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"B")
        node.on_message(second, t=6.0)

        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "duplicate_pre_prepare")
        # Instance state stays at the first PRE-PREPARE's digest.
        self.assertEqual(node.inst[(0, 0)].digest, digest(b"A"))


# --- Rule 5: digest integrity --------------------------------------------

class TestRule5DigestMismatch(unittest.TestCase):
    def test_payload_does_not_match_declared_digest(self):
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        # Honest digest is digest(b"A"); inject digest(b"B").
        msg = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"A",
                               digest_override=digest(b"B"))
        node.on_message(msg, t=5.0)

        self.assertNotIn((0, 0), node.inst)
        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "digest_mismatch")


# --- Unknown-type rejection + known-but-unwired silent no-op ------------

class TestOnMessageDispatch(unittest.TestCase):
    def test_known_but_unwired_types_silently_no_op(self):
        # T29's PREPARE/COMMIT/VIEW-CHANGE/NEW-VIEW are vocabulary T28
        # acknowledges but does not handle. No pbft_rejected event.
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        for typ in ("PREPARE", "COMMIT", "VIEW-CHANGE", "NEW-VIEW"):
            msg = Message(src=0, dst=1, type=typ, payload=None, t_sent=0.0)
            node.on_message(msg, t=5.0)

        self.assertEqual(emitted, [])

    def test_unknown_type_rejects(self):
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = Message(src=0, dst=1, type="PING", payload=None, t_sent=0.0)
        node.on_message(msg, t=5.0)

        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "unknown_type")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_validation -v`
Expected: FAIL — every test hits `NotImplementedError("Task 5")` raised by the stub `_on_message`.

**Step 3: Write minimal implementation**

In `src/pbft/node.py`, replace the `_on_message` stub and append the three helpers below the existing `_is_primary`:

```python
    def _on_message(self, msg: Message, t: float) -> None:
        if msg.type == "PRE-PREPARE":
            self._handle_pre_prepare(msg, t)
        elif msg.type in ("PREPARE", "COMMIT", "VIEW-CHANGE", "NEW-VIEW"):
            return                              # T29 wires these
        else:
            self.emit(PBFT_REJECTED,
                      {"reason": "unknown_type", "msg_type": msg.type,
                       "src": msg.src}, t)

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
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_validation -v`
Expected: PASS — 8 tests.

Then run the broader pbft suite to make sure no earlier task regressed:

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v`
Expected: PASS — Tasks 1-3 plus Task 4 plus Task 5 = ~22 tests.

**Step 5: Commit**

```bash
git add src/pbft/node.py tests/pbft/test_node_validation.py
git commit -m "task 28: PRE-PREPARE five-rule validator + IDLE→PRE_PREPARED transition"
```

---

## Task 6: `_on_start` + `_on_timer` + `_propose` (drain workload, self-loop)

**Files:**
- Modify: `src/pbft/node.py` (replace `_on_start` and `_on_timer` stubs; add `_propose`)
- Modify: `tests/pbft/test_node_propose.py` (extend with the propose-body tests)

**Step 1: Extend the failing test file**

Append these test classes to `tests/pbft/test_node_propose.py`:

```python
# Appended to tests/pbft/test_node_propose.py from Task 4.

from typing import Any

from nodes import Message
from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import PrePreparePayload
from pbft.node import PBFT_PRE_PREPARED, PBFT_REJECTED


def _install_capturers(node: PBFTNode):
    emitted: list[tuple[str, dict, float]] = []
    broadcasts: list[tuple[str, object, float]] = []
    timers: list[tuple[Any, float, object, float]] = []
    node.emit = lambda et, fields, t: emitted.append((et, fields, t))
    node.broadcast = lambda type, payload, t: broadcasts.append(
        (type, payload, t))
    node.set_timer = lambda tid, delay, payload, t: timers.append(
        (tid, delay, payload, t))
    node.send = lambda *a, **kw: None
    node.cancel_timer = lambda tid: None
    return emitted, broadcasts, timers


class TestOnStart(unittest.TestCase):
    def test_primary_arms_propose_timer(self):
        primary = _node(0, n=4, propose_delay=0.5)
        _, _, timers = _install_capturers(primary)
        primary.start(t=0.0)            # CREATED -> RUNNING -> _on_start

        self.assertEqual(len(timers), 1)
        tid, delay, payload, t = timers[0]
        self.assertEqual(tid, "propose")
        self.assertEqual(delay, 0.5)
        self.assertEqual(t, 0.0)

    def test_non_primary_does_not_arm_anything(self):
        replica = _node(2, n=4)
        emitted, broadcasts, timers = _install_capturers(replica)
        replica.start(t=0.0)

        self.assertEqual(timers, [])
        self.assertEqual(broadcasts, [])
        self.assertEqual(emitted, [])


class TestProposePath(unittest.TestCase):
    def test_one_propose_broadcasts_and_self_transitions(self):
        primary = _node(0, n=4, workload=[b"A"], propose_delay=1.0)
        emitted, broadcasts, timers = _install_capturers(primary)
        primary.start(t=0.0)
        # _on_start armed the timer; fire it manually.
        primary.on_timer("propose", None, t=1.0)

        # One PRE-PREPARE broadcast with the right shape.
        self.assertEqual(len(broadcasts), 1)
        typ, pp, t = broadcasts[0]
        self.assertEqual(typ, "PRE-PREPARE")
        self.assertIsInstance(pp, PrePreparePayload)
        self.assertEqual(pp.view, 0)
        self.assertEqual(pp.seq, 0)
        self.assertEqual(pp.request_payload, b"A")
        self.assertEqual(pp.request_digest, digest(b"A"))

        # Self-loop: primary's own (0, 0) is PRE_PREPARED with one
        # pbft_pre_prepared event whose src == self.id.
        inst = primary.inst[(0, 0)]
        self.assertIs(inst.state, InstanceState.PRE_PREPARED)
        pre_prepared = [e for e in emitted if e[0] == PBFT_PRE_PREPARED]
        self.assertEqual(len(pre_prepared), 1)
        self.assertEqual(pre_prepared[0][1]["src"], 0)
        # No rejections on the primary's own work.
        self.assertNotIn(PBFT_REJECTED, [e[0] for e in emitted])

        # next_seq advanced.
        self.assertEqual(primary.next_seq, 1)

        # Re-arm: the propose timer was re-set after broadcast (the
        # original from _on_start plus one from _propose).
        self.assertEqual(len(timers), 2)
        self.assertEqual(timers[1][0], "propose")

    def test_drain_stops_when_workload_empty(self):
        primary = _node(0, n=4, workload=[b"A"], propose_delay=1.0)
        _, broadcasts, timers = _install_capturers(primary)
        primary.start(t=0.0)            # 1 timer armed
        primary.on_timer("propose", None, t=1.0)    # drains; re-arms 1 more
        primary.on_timer("propose", None, t=2.0)    # workload empty: no-op

        # Exactly one PRE-PREPARE; the second fire was a drain no-op.
        self.assertEqual(len(broadcasts), 1)
        # No additional timer past the re-arm from the first _propose.
        self.assertEqual(len(timers), 2)

    def test_next_seq_monotone_across_drain(self):
        primary = _node(0, n=4, workload=[b"A", b"B", b"C"],
                        propose_delay=1.0)
        _, broadcasts, _ = _install_capturers(primary)
        primary.start(t=0.0)
        for k in range(3):
            primary.on_timer("propose", None, t=float(k + 1))
        seqs = [b[1].seq for b in broadcasts]
        self.assertEqual(seqs, [0, 1, 2])

    def test_unknown_timer_silently_no_op(self):
        primary = _node(0, n=4, workload=[b"A"])
        emitted, broadcasts, _ = _install_capturers(primary)
        primary.start(t=0.0)
        primary.on_timer("bogus", None, t=1.0)

        # Bogus timer did not propose, did not emit anything.
        self.assertEqual(broadcasts, [])
        self.assertEqual(emitted, [])
```

**Step 2: Run the new tests to verify they fail**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_propose -v`
Expected: FAIL — `_on_start` and `_on_timer` raise `NotImplementedError("Task 6")`.

**Step 3: Replace the stubs in `src/pbft/node.py`**

Delete the two `NotImplementedError` stubs for `_on_start` and `_on_timer`; replace with:

```python
    # --- Lifecycle hooks (spec § 7.2 / § 7.3). ---

    def _on_start(self, t: float) -> None:
        if self._is_primary(self.view):
            self.set_timer("propose", self.propose_delay, None, t)

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
```

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_node_propose -v`
Expected: PASS — original 8 tests plus 6 new = 14 tests.

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v`
Expected: PASS — whole pbft unit suite green (~28 tests).

**Step 5: Commit**

```bash
git add src/pbft/node.py tests/pbft/test_node_propose.py
git commit -m "task 28: propose timer (drain workload, self-loop, re-arm)"
```

---

## Task 7: Finalise `__init__.py` re-exports

**Files:**
- Modify: `src/pbft/__init__.py`
- Create: `tests/pbft/test_init.py`

**Step 1: Write the failing test**

```python
# tests/pbft/test_init.py
"""Public surface of the pbft package."""
import unittest


class TestPublicSurface(unittest.TestCase):
    def test_expected_names_reexported(self):
        import pbft
        # Constructor + FSM data plane.
        self.assertTrue(hasattr(pbft, "PBFTNode"))
        self.assertTrue(hasattr(pbft, "Instance"))
        self.assertTrue(hasattr(pbft, "InstanceState"))
        # Wire payloads (PrePrepare consumed in T28; rest declared for T29).
        for name in ("PrePreparePayload", "PreparePayload",
                     "CommitPayload", "ViewChangePayload",
                     "NewViewPayload"):
            self.assertTrue(hasattr(pbft, name), name)
        # Observable event-type constants.
        self.assertEqual(pbft.PBFT_PRE_PREPARED, "pbft_pre_prepared")
        self.assertEqual(pbft.PBFT_REJECTED, "pbft_rejected")
        # Digest helper.
        self.assertTrue(callable(pbft.digest))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_init -v`
Expected: FAIL — the package re-exports nothing yet.

**Step 3: Replace `src/pbft/__init__.py`**

```python
"""Simplified PBFT consensus subsystem (T28 + T29).

T28 (this PR) ships the pre-prepare phase: the primary drains a stub
workload, broadcasts PRE-PREPARE, locally self-transitions, recipients
validate against five rules and reach PRE_PREPARED. PREPARE / COMMIT /
VIEW-CHANGE / NEW-VIEW are silently no-op'd (skeleton-cut, Decision A);
T29 wires them.

Design spec: docs/superpowers/specs/2026-05-21-t28-pbft-proposal-design.md
Plan:        docs/superpowers/specs/2026-05-21-t28-pbft-proposal-plan.md
"""
from .digest import digest
from .instance import Instance, InstanceState
from .messages import (
    CommitPayload,
    NewViewPayload,
    PreparePayload,
    PrePreparePayload,
    ViewChangePayload,
)
from .node import PBFT_PRE_PREPARED, PBFT_REJECTED, PBFTNode

__all__ = [
    "PBFTNode",
    "Instance", "InstanceState",
    "PrePreparePayload", "PreparePayload", "CommitPayload",
    "ViewChangePayload", "NewViewPayload",
    "PBFT_PRE_PREPARED", "PBFT_REJECTED",
    "digest",
]
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest test_init -v`
Expected: PASS — 1 test.

Run: `PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v`
Expected: PASS — whole pbft unit suite.

**Step 5: Commit**

```bash
git add src/pbft/__init__.py tests/pbft/test_init.py
git commit -m "task 28: finalise pbft package re-exports"
```

---

## Task 8: End-to-end integration — `tests/integration/test_pbft_proposal.py`

**Files:**
- Create: `tests/integration/test_pbft_proposal.py`

**Step 1: Write the failing test**

This test drives the real Scheduler + Network + Node + event-log stack through `config.factory.build_run` and asserts the design spec's § 9.2 expectations.

```python
# tests/integration/test_pbft_proposal.py
"""End-to-end: PBFT pre-prepare phase across the W3 stack (T28 spec § 9.2).

Two scenarios, both driven through config.factory.build_run so the
six-phase bootstrap is real and the determinism contract holds end-to-end:

  Scenario A — n=4, workload=[b"A", b"B", b"C"]
  Scenario B — n=7, workload=[b"X"]

Both run under a single phase, zero delay, zero drop. The propose-timer
chain ends on workload drain; the run reaches quiescence without a t_max.
"""
import math
import unittest
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from pbft import PBFT_PRE_PREPARED, PBFT_REJECTED, PBFTNode, digest


_CONSTANT_ZERO = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 0.0})),)


def _config(n: int) -> Config:
    return Config(
        n=n,
        t_max=math.inf,
        seeds=SeedsConfig(n_runs=1),
        network=_CONSTANT_ZERO,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _factory(n: int, workload_for):
    """build_run wants (node_id, global_seed) -> Node. Close over n +
    workload assignment. propose_delay=1.0; initial_view=0; weight=1.0."""
    def make(node_id: int, global_seed: int) -> PBFTNode:
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n,
                        workload=workload_for(node_id),
                        propose_delay=1.0, initial_view=0)
    return make


def _run(n: int, workload_for, global_seed=42):
    """Build, attach logger, run to quiescence. Returns (logger, result)."""
    logger = EventLogger()
    handle = build_run(_config(n), global_seed, _factory(n, workload_for))
    handle.scheduler.event_sink = logger.sink
    result = handle.scheduler.run()
    return logger, result


def _count_event(records, event_type: str) -> int:
    return sum(1 for r in records if r.event_type == event_type)


def _count_msg_type(records, msg_type: str) -> int:
    # Transport events (T24) carry the wire `type` inside `fields`.
    # delivery records have event_type == "delivery" with fields["type"].
    return sum(1 for r in records
               if r.event_type == "delivery"
               and r.fields.get("type") == msg_type)


class TestScenarioA_n4(unittest.TestCase):
    """n=4, workload=[b"A", b"B", b"C"]; primary = node 0."""

    WORKLOAD = [b"A", b"B", b"C"]

    def _workload_for(self, node_id: int):
        return self.WORKLOAD if node_id == 0 else None

    def test_run_reaches_quiescence(self):
        _, result = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_all_four_nodes_pre_prepared_for_every_seq(self):
        # 4 nodes x 3 seqs = 12 pbft_pre_prepared events.
        logger, _ = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, PBFT_PRE_PREPARED), 12)

    def test_no_rejections(self):
        logger, _ = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, PBFT_REJECTED), 0)

    def test_no_voting_messages_emitted(self):
        # PREPARE / COMMIT / VIEW-CHANGE / NEW-VIEW must be zero in T28.
        logger, _ = _run(n=4, workload_for=self._workload_for)
        for typ in ("PREPARE", "COMMIT", "VIEW-CHANGE", "NEW-VIEW"):
            self.assertEqual(_count_msg_type(logger.records, typ), 0,
                             f"unexpected {typ} delivery in T28")

    def test_pre_prepare_deliveries_count(self):
        # 3 broadcasts x 3 non-primary recipients = 9 PRE-PREPARE deliveries.
        # The primary's self-loop is in-process and does NOT generate a
        # Delivery event (Network.submit_broadcast excludes the sender).
        logger, _ = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(_count_msg_type(logger.records, "PRE-PREPARE"), 9)

    def test_digests_match_workload(self):
        logger, _ = _run(n=4, workload_for=self._workload_for)
        seen_digests = {r.fields["digest"]
                        for r in logger.records
                        if r.event_type == PBFT_PRE_PREPARED}
        expected = {digest(b).hex() for b in self.WORKLOAD}
        self.assertEqual(seen_digests, expected)

    def test_determinism_byte_identical_records(self):
        # Two seed-identical runs produce the same record stream
        # (records compared as tuples).
        la, _ = _run(n=4, workload_for=self._workload_for, global_seed=42)
        lb, _ = _run(n=4, workload_for=self._workload_for, global_seed=42)
        self.assertEqual(list(la.records), list(lb.records))


class TestScenarioB_n7(unittest.TestCase):
    """n=7, workload=[b"X"]; primary = node 0; f = 2."""

    WORKLOAD = [b"X"]

    def _workload_for(self, node_id: int):
        return self.WORKLOAD if node_id == 0 else None

    def test_run_reaches_quiescence(self):
        _, result = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_all_seven_nodes_pre_prepared_for_seq_0(self):
        logger, _ = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, PBFT_PRE_PREPARED), 7)

    def test_no_rejections(self):
        logger, _ = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, PBFT_REJECTED), 0)

    def test_pre_prepare_deliveries_count(self):
        # 1 broadcast x 6 non-primary recipients = 6 PRE-PREPARE deliveries.
        logger, _ = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(_count_msg_type(logger.records, "PRE-PREPARE"), 6)

    def test_determinism_byte_identical_records(self):
        la, _ = _run(n=7, workload_for=self._workload_for, global_seed=42)
        lb, _ = _run(n=7, workload_for=self._workload_for, global_seed=42)
        self.assertEqual(list(la.records), list(lb.records))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails — then passes**

Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_proposal -v`

Expected: PASS immediately — every dependency is shipped (PBFTNode is Tasks 1-7, build_run is T27, EventLogger is T24, Network/Scheduler/Node are T21-T23). This task is an integration *guard*: it composes the W3 stack with the new pbft layer and asserts the spec's § 9.2 expectations.

If a test fails:
- **`_count_msg_type` returns 0 across the board** → confirm the EventLogger normalises `Delivery` into records with `event_type == "delivery"` and `fields["type"] == msg.type`. Inspect with `print(logger.records[:3])` once.
- **Determinism mismatch** → invoke `superpowers:systematic-debugging`; the determinism contract (`network-model-phases.md §6`, `node-model.md §8`) requires byte-identical replay. Do not weaken the test.
- **Extra/missing pbft_pre_prepared events** → check the primary self-loop in `_propose` runs exactly once per propose (not twice from `broadcast` plus self-loop).

**Step 3: (no implementation — integration guard)**

**Step 4: Run the broader regression sweep**

Run each W3 suite to confirm no regression from the integration test's surface:

```
PYTHONPATH=src:tests/pbft        python3 -m unittest discover -s tests/pbft        -v
PYTHONPATH=src:tests/integration python3 -m unittest discover -s tests/integration -v
PYTHONPATH=src:tests/event_log   python3 -m unittest discover -s tests/event_log   -v
PYTHONPATH=src:tests/network     python3 -m unittest discover -s tests/network     -v
PYTHONPATH=src:tests/scheduler   python3 -m unittest discover -s tests/scheduler   -v
PYTHONPATH=src:tests/nodes       python3 -m unittest discover -s tests/nodes       -v
PYTHONPATH=src:tests/config      python3 -m unittest discover -s tests/config      -v
```

Expected: all green. T28 adds files, modifies no upstream src/.

**Step 5: Commit**

```bash
git add tests/integration/test_pbft_proposal.py
git commit -m "task 28: end-to-end PBFT proposal integration (n=4, n=7)"
```

---

## Task 9: Experiment page + index + log

**Files:**
- Create: `wiki/experiments/2026-05-21_pbft-proposal-baseline.md`
- Modify: `wiki/index.md` (add the new experiment line under `## Experiments`)
- Modify: `wiki/log.md` (append one task entry)

**Step 1: Capture the verification facts**

Run: `git rev-parse HEAD` — record the commit hash.
Run: `PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v` — record the unit pass count.
Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_proposal -v` — record the integration pass count.

**Step 2: Write `wiki/experiments/2026-05-21_pbft-proposal-baseline.md`**

A build-verification experiment page (per the Engineer role) covering:

- **Purpose** — first end-to-end run of the PBFT proposal phase across the W3 stack; confirms the T28/T29 cut at the IDLE → PRE_PREPARED transition is self-consistent.
- **Config — Scenario A** — `n=4`, `workload=[b"A", b"B", b"C"]` on node 0, `propose_delay=1.0`, `initial_view=0`, single phase `[0, ∞)` with `DelayDist("constant", {"delay": 0.0})`, `p_drop=0`, no partitions.
- **Config — Scenario B** — `n=7`, `workload=[b"X"]` on node 0, otherwise identical.
- **Seed** — `global_seed=42`.
- **Commit hash** — from Step 1.
- **Commands to re-run** — the three test commands from Step 1.
- **Raw result location** — none persisted; results are observed through the in-test `EventLogger` (no CSV file produced by this test). Note this and the rationale (matches T24's `test_e2e.py` pattern).
- **Observation paragraph** — one paragraph: the pre-prepare phase reached a self-consistent `PRE_PREPARED` state across n=4 and n=7; zero `PREPARE` / `COMMIT` / `VIEW-CHANGE` / `NEW-VIEW` deliveries were observed; the primary's self-loop produced exactly one `pbft_pre_prepared` event per `seq`; the two seed-identical re-runs produced byte-identical record streams (determinism contract held); the T28/T29 cut at `_accept_pre_prepare` will let T29 grow the FSM without upstream rework.
- **Wikilinks** — `[[algorithms/pbft]]`, `[[concepts/message-types]]`, `[[concepts/system-design-protocols]]`, `[[concepts/node-model]]`, `[[concepts/simulation-design]]`.

**Step 3: Append to `wiki/index.md`**

Under `## Experiments`, append (preserving the existing date-ordered grouping):

```
- [[experiments/2026-05-21_pbft-proposal-baseline]] — T28 build-verification baseline: PBFT pre-prepare phase across the W3 stack; n=4 and n=7 scenarios reach a self-consistent PRE_PREPARED state with zero voting messages emitted and byte-identical determinism re-runs.
```

**Step 4: Append to `wiki/log.md`**

```markdown
## [2026-05-21] code | task 28 — implement PBFT proposal logic

- role: Engineer
- touched: src/pbft/{__init__,digest,messages,instance,node}.py, tests/pbft/{__init__,test_digest,test_messages,test_instance,test_node_propose,test_node_validation,test_init}.py, tests/integration/test_pbft_proposal.py, wiki/index.md, wiki/experiments/2026-05-21_pbft-proposal-baseline.md
- notes: Built the pre-prepare phase of PBFT: PBFTNode drains a stub workload, broadcasts PRE-PREPARE, locally self-transitions, recipients validate against five rules and reach PRE_PREPARED. Skeleton-cut FSM declares all four states; T28 only wires IDLE→PRE_PREPARED. PREPARE/COMMIT/VIEW-CHANGE/NEW-VIEW are vocabulary-acknowledged silent no-ops awaiting T29.
```

**Step 5: Commit**

```bash
git add wiki/experiments/2026-05-21_pbft-proposal-baseline.md wiki/index.md wiki/log.md
git commit -m "wiki: T28 pbft-proposal-baseline experiment page + log entry"
```

---

## Final verification (before In Review)

Invoke `superpowers:verification-before-completion`. Run, and confirm all green:

```bash
PYTHONPATH=src:tests/pbft        python3 -m unittest discover -s tests/pbft        -v
PYTHONPATH=src:tests/integration python3 -m unittest discover -s tests/integration -v
PYTHONPATH=src:tests/event_log   python3 -m unittest discover -s tests/event_log   -v
PYTHONPATH=src:tests/network     python3 -m unittest discover -s tests/network     -v
PYTHONPATH=src:tests/scheduler   python3 -m unittest discover -s tests/scheduler   -v
PYTHONPATH=src:tests/nodes       python3 -m unittest discover -s tests/nodes       -v
PYTHONPATH=src:tests/config      python3 -m unittest discover -s tests/config      -v
```

All seven suites must pass. The pbft suite (Tasks 1-7) and the new integration test (Task 8) are new; the other five are regression guards. T28 modifies no upstream `src/` files, so any regression in tests/nodes/, tests/scheduler/, tests/network/, tests/config/, or tests/event_log/ indicates the integration test or the import surface in `src/pbft/__init__.py` introduced an interaction.

Then hand off to the human:
- **TASKS.md** flip: T28 from `[~]` In Progress → `[?]` In Review (the agent flips per `docs/workflow.md` § Per-task workflow step 8; the dashboard counters are updated in the same flip).
- **Handoff summary** for the human reviewer:
  - Files added: `src/pbft/{__init__,digest,messages,instance,node}.py`, `tests/pbft/{__init__,test_digest,test_messages,test_instance,test_node_propose,test_node_validation,test_init}.py`, `tests/integration/test_pbft_proposal.py`, `wiki/experiments/2026-05-21_pbft-proposal-baseline.md`.
  - Files modified: `wiki/index.md`, `wiki/log.md`. **No** `src/` files outside `src/pbft/` and **no** wiki concept/algorithm pages are touched.
  - Settled design decisions from brainstorming: skeleton FSM (Dec A), stub `list[bytes]` workload (Dec B), drain-workload cadence (Dec C), `v mod n` primary rule (Dec D), five-rule log-and-drop validator (Dec E) — all pinned in the design spec.
  - Open question for the human: whether the anticipated divergences from the `concepts/system-design-protocols.md` §2 sketch (the explicit `_accept_pre_prepare` self-loop; the five-rule validator structure; `next_seq` as primary-only counter) warrant a `## Revisions` entry on the wiki page. The design spec § 11 left this deferred to execution; the implementation matches the spec, so the question is preserved as-is for the human.
  - T29 dependency: T29 grows the FSM by filling in `_accept_prepare` / `_accept_commit` / view-change handlers; the `Instance.prepares` / `Instance.commits` dicts, the four placeholder payload classes, and the silent-no-op message branch are all in place to receive T29's wiring without dataclass churn.
