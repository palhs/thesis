# T23 — Message Passing with Configurable Delay: Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build `src/network/` — the honest inter-node delivery layer (`Network`): phase timeline, five delay distributions, Bernoulli drop, partition predicate, and network-scoped deterministic RNG.

**Architecture:** A system-level `Network` object shared by every `Node`. `phases.py` holds the configuration dataclasses (`DelayDist`, `Partition`, `Phase`) and `validate_timeline`; `network.py` holds the `Network` class, which queues `Delivery` events on the T21 `Scheduler` and tracks the active phase via a `_phase_idx` pointer advanced by `PhaseAdvance` events. Test-driven throughout.

**Tech Stack:** Python 3.13, stdlib only (`random`, `hashlib`, `math`, `dataclasses`), `unittest`. Upstream code: `src/scheduler/` (T21), `src/nodes/` (T22).

**Design spec:** `docs/superpowers/specs/2026-05-19-t23-network-design.md` — read it before starting; this plan implements it literally.

**Test commands (no pytest in this environment — `unittest` only):**
- All network tests: `PYTHONPATH=src:tests/network python3 -m unittest discover -s tests/network -v`
- One module: `PYTHONPATH=src:tests/network python3 -m unittest test_delay_dist -v`
- One test: `PYTHONPATH=src:tests/network python3 -m unittest test_delay_dist.TestDelayDist.test_constant_is_exact -v`

**Commit convention:** Each task ends with a **Checkpoint** — the *human* reviews and commits (`task 23: <desc>`). The executing agent does **not** run `git commit`; it stages nothing and stops at the checkpoint for human action.

---

## Task 1: `DelayDist` — five delay distributions

**Files:**
- Create: `src/network/__init__.py` (empty placeholder for now — package marker)
- Create: `src/network/phases.py`
- Create: `tests/network/test_delay_dist.py`

**Step 1: Write the failing test**

Create `tests/network/test_delay_dist.py`:

```python
"""Unit tests for DelayDist (network-model-phases.md §2)."""
import random
import unittest

from network.phases import DelayDist


class TestDelayDistValidation(unittest.TestCase):
    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("triangular", {})

    def test_missing_required_param_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("constant", {})

    def test_constant_non_positive_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("constant", {"delay": 0})

    def test_uniform_non_positive_low_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("uniform", {"low": 0, "high": 5})

    def test_uniform_high_below_low_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("uniform", {"low": 10, "high": 5})

    def test_normal_negative_std_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("normal", {"mean": 10, "std": -1})

    def test_exponential_non_positive_mean_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("exponential", {"mean": 0})

    def test_heavy_tail_non_positive_shape_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("heavy_tail", {"scale": 10, "shape": 0})


class TestDelayDistSample(unittest.TestCase):
    def test_constant_is_exact(self):
        d = DelayDist("constant", {"delay": 12.5})
        self.assertEqual(d.sample(random.Random(0)), 12.5)

    def test_uniform_within_bounds(self):
        d = DelayDist("uniform", {"low": 100, "high": 500})
        rng = random.Random(1)
        for _ in range(200):
            s = d.sample(rng)
            self.assertGreaterEqual(s, 100)
            self.assertLessEqual(s, 500)

    def test_normal_floored_by_clip_low(self):
        # mean far below clip_low so the floor always binds
        d = DelayDist("normal", {"mean": -1000, "std": 1, "clip_low": 3.0})
        rng = random.Random(2)
        for _ in range(50):
            self.assertEqual(d.sample(rng), 3.0)

    def test_all_kinds_strictly_positive(self):
        dists = [
            DelayDist("constant", {"delay": 1}),
            DelayDist("uniform", {"low": 1, "high": 2}),
            DelayDist("normal", {"mean": 5, "std": 2}),
            DelayDist("exponential", {"mean": 5}),
            DelayDist("heavy_tail", {"scale": 1, "shape": 2}),
        ]
        rng = random.Random(3)
        for d in dists:
            for _ in range(200):
                self.assertGreater(d.sample(rng), 0.0)

    def test_sample_is_deterministic(self):
        d = DelayDist("exponential", {"mean": 50})
        a = [d.sample(random.Random(7)) for _ in range(5)]
        b = [d.sample(random.Random(7)) for _ in range(5)]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_delay_dist -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'network.phases'`.

**Step 3: Write minimal implementation**

Create `src/network/__init__.py` as an empty file (package marker; real exports land in Task 4).

Create `src/network/phases.py`:

```python
"""Phase configuration for the honest delivery layer (network-model-phases.md, T15/T23).

Design spec: docs/superpowers/specs/2026-05-19-t23-network-design.md
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

NodeId = int
SimTime = float

# Strictly-positive guard so t_delivered > t_sent (network-model.md §4).
# Only ever binds on the measure-zero exponential edge case.
_LATENCY_FLOOR: float = 1e-9

_DELAY_KINDS = ("constant", "uniform", "normal", "exponential", "heavy_tail")
_REQUIRED_PARAMS = {
    "constant": ("delay",),
    "uniform": ("low", "high"),
    "normal": ("mean", "std"),
    "exponential": ("mean",),
    "heavy_tail": ("scale", "shape"),
}


@dataclass(frozen=True)
class DelayDist:
    """A named delivery-delay distribution (network-model-phases.md §2).

    `sample()` returns strictly-positive SimTime. Bad params raise
    ValueError at construction (fail-fast, before any run).
    """
    kind: str
    params: dict

    def __post_init__(self) -> None:
        if self.kind not in _DELAY_KINDS:
            raise ValueError(f"unknown delay kind: {self.kind!r}")
        for key in _REQUIRED_PARAMS[self.kind]:
            if key not in self.params:
                raise ValueError(
                    f"delay kind {self.kind!r} requires param {key!r}")
        p = self.params
        if self.kind == "constant":
            if p["delay"] <= 0:
                raise ValueError(f"constant delay must be > 0, got {p['delay']}")
        elif self.kind == "uniform":
            if p["low"] <= 0:
                raise ValueError(f"uniform low must be > 0, got {p['low']}")
            if p["high"] < p["low"]:
                raise ValueError(
                    f"uniform high {p['high']} < low {p['low']}")
        elif self.kind == "normal":
            if p["std"] < 0:
                raise ValueError(f"normal std must be >= 0, got {p['std']}")
            if p.get("clip_low", 1.0) <= 0:
                raise ValueError(
                    f"normal clip_low must be > 0, got {p.get('clip_low')}")
        elif self.kind == "exponential":
            if p["mean"] <= 0:
                raise ValueError(
                    f"exponential mean must be > 0, got {p['mean']}")
        else:  # heavy_tail
            if p["scale"] <= 0:
                raise ValueError(
                    f"heavy_tail scale must be > 0, got {p['scale']}")
            if p["shape"] <= 0:
                raise ValueError(
                    f"heavy_tail shape must be > 0, got {p['shape']}")

    def sample(self, rng: random.Random) -> SimTime:
        p = self.params
        if self.kind == "constant":
            raw = p["delay"]
        elif self.kind == "uniform":
            raw = rng.uniform(p["low"], p["high"])
        elif self.kind == "normal":
            raw = max(rng.normalvariate(p["mean"], p["std"]),
                      p.get("clip_low", 1.0))
        elif self.kind == "exponential":
            raw = rng.expovariate(1.0 / p["mean"])
        else:  # heavy_tail — Pareto, paretovariate() >= 1.0
            raw = p["scale"] * rng.paretovariate(p["shape"])
        return max(raw, _LATENCY_FLOOR)
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_delay_dist -v`
Expected: PASS — `OK` (13 tests).

**Step 5: Checkpoint** — human reviews `src/network/phases.py` (DelayDist) + `test_delay_dist.py` and commits `task 23: add DelayDist with five distributions`.

---

## Task 2: `Partition` — cross-group delivery blocking

**Files:**
- Modify: `src/network/phases.py` (append `Partition`)
- Create: `tests/network/test_partition.py`

**Step 1: Write the failing test**

Create `tests/network/test_partition.py`:

```python
"""Unit tests for Partition.blocks (network-model-phases.md §4)."""
import unittest

from network.phases import Partition


class TestPartitionBlocks(unittest.TestCase):
    def setUp(self):
        # two groups: {0,1} | {2,3}; node 4 is unconstrained
        self.part = Partition(groups=((0, 1), (2, 3)))

    def test_same_group_not_blocked(self):
        self.assertFalse(self.part.blocks(0, 1))
        self.assertFalse(self.part.blocks(2, 3))

    def test_cross_group_blocked_both_directions(self):
        self.assertTrue(self.part.blocks(0, 2))
        self.assertTrue(self.part.blocks(2, 0))

    def test_unconstrained_node_reachable(self):
        self.assertFalse(self.part.blocks(4, 0))
        self.assertFalse(self.part.blocks(0, 4))
        self.assertFalse(self.part.blocks(4, 4))

    def test_asymmetric_blocks_all_cross_edges_in_v1(self):
        # v1: symmetric=False behaves identically to symmetric=True
        asym = Partition(groups=((0, 1), (2, 3)), symmetric=False)
        self.assertTrue(asym.blocks(0, 2))
        self.assertTrue(asym.blocks(2, 0))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_partition -v`
Expected: FAIL — `ImportError: cannot import name 'Partition'`.

**Step 3: Write minimal implementation**

Append to `src/network/phases.py`:

```python
@dataclass(frozen=True)
class Partition:
    """A network partition: blocks delivery between disjoint groups
    (network-model-phases.md §4).

    v1 asymmetric (symmetric=False) blocks all directed cross-group edges,
    identically to symmetric. The `symmetric` field is reserved for the
    per-edge allowlisting revision (network-model.md §8); it does not yet
    change `blocks` behaviour.
    """
    groups: tuple[tuple[NodeId, ...], ...]
    symmetric: bool = True

    def _group_of(self, node: NodeId) -> int | None:
        for i, g in enumerate(self.groups):
            if node in g:
                return i
        return None

    def blocks(self, src: NodeId, dst: NodeId) -> bool:
        gs = self._group_of(src)
        gd = self._group_of(dst)
        if gs is None or gd is None:
            return False          # unconstrained validators stay reachable
        return gs != gd
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_partition -v`
Expected: PASS — `OK` (4 tests).

**Step 5: Checkpoint** — human reviews and commits `task 23: add Partition predicate`.

---

## Task 3: `Phase` + `validate_timeline`

**Files:**
- Modify: `src/network/phases.py` (append `Phase`, `validate_timeline`)
- Create: `tests/network/test_phases.py`

**Step 1: Write the failing test**

Create `tests/network/test_phases.py`:

```python
"""Unit tests for Phase and validate_timeline (network-model-phases.md §5)."""
import math
import unittest

from network.phases import DelayDist, Partition, Phase, validate_timeline

D = DelayDist("constant", {"delay": 10})


def _phase(t0, t1, p_drop=0.0, partitions=()):
    return Phase(t_start=t0, t_end=t1, delay=D, p_drop=p_drop,
                 partitions=partitions)


class TestValidateTimeline(unittest.TestCase):
    def test_valid_single_open_phase(self):
        validate_timeline((_phase(0, math.inf),), {0, 1})  # no raise

    def test_valid_multi_phase(self):
        validate_timeline(
            (_phase(0, 100), _phase(100, 250), _phase(250, math.inf)),
            {0, 1})  # no raise

    def test_empty_timeline_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline((), {0})

    def test_first_phase_not_at_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline((_phase(5, math.inf),), {0})

    def test_zero_width_phase_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline((_phase(0, 0), _phase(0, math.inf)), {0})

    def test_non_contiguous_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline((_phase(0, 100), _phase(150, math.inf)), {0})

    def test_infinite_interior_boundary_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline(
                (_phase(0, math.inf), _phase(math.inf, math.inf)), {0})

    def test_p_drop_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_timeline((_phase(0, math.inf, p_drop=1.0),), {0})

    def test_partition_under_two_groups_rejected(self):
        bad = Partition(groups=((0, 1),))
        with self.assertRaises(ValueError):
            validate_timeline((_phase(0, math.inf, partitions=(bad,)),),
                              {0, 1})

    def test_partition_empty_group_rejected(self):
        bad = Partition(groups=((0,), ()))
        with self.assertRaises(ValueError):
            validate_timeline((_phase(0, math.inf, partitions=(bad,)),), {0})

    def test_partition_overlapping_groups_rejected(self):
        bad = Partition(groups=((0, 1), (1, 2)))
        with self.assertRaises(ValueError):
            validate_timeline((_phase(0, math.inf, partitions=(bad,)),),
                              {0, 1, 2})

    def test_partition_undeclared_nodeid_rejected(self):
        bad = Partition(groups=((0,), (9,)))
        with self.assertRaises(ValueError):
            validate_timeline((_phase(0, math.inf, partitions=(bad,)),),
                              {0, 1})


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_phases -v`
Expected: FAIL — `ImportError: cannot import name 'Phase'`.

**Step 3: Write minimal implementation**

Append to `src/network/phases.py`:

```python
@dataclass(frozen=True)
class Phase:
    """One contiguous network-condition interval, half-open [t_start, t_end)
    (network-model-phases.md §1, §5). The final phase may have
    t_end = math.inf; every interior phase has a finite t_end.
    """
    t_start: SimTime
    t_end: SimTime
    delay: DelayDist
    p_drop: float = 0.0
    partitions: tuple[Partition, ...] = ()


def validate_timeline(phases: tuple[Phase, ...],
                      registered_ids: set[NodeId]) -> None:
    """Fail-fast validation of a phase timeline (network-model-phases.md §5).

    Raises ValueError naming the first violation found. Run once by
    Network.start(), before t=0.
    """
    if not phases:
        raise ValueError("phase timeline is empty; need >= 1 phase")
    if phases[0].t_start != 0:
        raise ValueError(
            f"first phase must start at t=0, got {phases[0].t_start}")
    last_idx = len(phases) - 1
    for i, ph in enumerate(phases):
        if ph.t_start >= ph.t_end:
            raise ValueError(
                f"phase {i} has non-positive width: "
                f"[{ph.t_start}, {ph.t_end})")
        if i != last_idx:
            if not math.isfinite(ph.t_end):
                raise ValueError(
                    f"interior phase {i} has non-finite t_end={ph.t_end}")
            if ph.t_end != phases[i + 1].t_start:
                raise ValueError(
                    f"phase {i} t_end={ph.t_end} != phase {i + 1} "
                    f"t_start={phases[i + 1].t_start} (non-contiguous)")
        if not (0.0 <= ph.p_drop < 1.0):
            raise ValueError(
                f"phase {i} p_drop={ph.p_drop} not in [0, 1) "
                f"(1.0 is forbidden — use a covering partition)")
        for j, part in enumerate(ph.partitions):
            if len(part.groups) < 2:
                raise ValueError(
                    f"phase {i} partition {j}: need >= 2 groups, "
                    f"got {len(part.groups)}")
            seen: set[NodeId] = set()
            for g in part.groups:
                if not g:
                    raise ValueError(
                        f"phase {i} partition {j}: empty group")
                for nid in g:
                    if nid in seen:
                        raise ValueError(
                            f"phase {i} partition {j}: NodeId {nid} "
                            f"appears in multiple groups")
                    seen.add(nid)
                    if nid not in registered_ids:
                        raise ValueError(
                            f"phase {i} partition {j}: NodeId {nid} "
                            f"not registered")
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_phases -v`
Expected: PASS — `OK` (12 tests).

**Step 5: Checkpoint** — human reviews and commits `task 23: add Phase and validate_timeline`.

---

## Task 4: `Network` — construction, `register`, `bind`, package exports

**Files:**
- Create: `src/network/network.py`
- Modify: `src/network/__init__.py` (real exports)
- Create: `tests/network/_helpers.py`
- Create: `tests/network/test_network.py`

**Step 1: Write the failing test**

Create `tests/network/_helpers.py`:

```python
"""Test doubles for the Network (T23)."""
from __future__ import annotations

from nodes import HaltReason, Node


class StubNode(Node):
    """Minimal concrete Node: records inbound messages. For unit tests."""

    def __init__(self, node_id, global_seed=0):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.received: list = []

    def _on_start(self, t):
        pass

    def _on_message(self, msg, t):
        self.received.append((msg, t))

    def _on_timer(self, timer_id, payload, t):
        pass


class PingPongNode(Node):
    """Two nodes bounce a token; each halts after `budget` inbound messages."""

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
```

Create `tests/network/test_network.py` (this task adds the construction/wiring class; later tasks append more classes to this same file):

```python
"""Unit tests for the Network class (network-model.md, T23)."""
import math
import unittest

from network import DelayDist, Network, Phase
from scheduler import Scheduler
from _helpers import StubNode

SEED = 42
_D = DelayDist("constant", {"delay": 10.0})


def _single_phase():
    return (Phase(0.0, math.inf, _D),)


class TestNetworkWiring(unittest.TestCase):
    def test_register_populates_registry(self):
        net = Network(Scheduler(), _single_phase(), SEED)
        n = StubNode(3)
        net.register(n)
        self.assertIs(net.registry[3], n)

    def test_bind_wires_send_and_broadcast(self):
        sched = Scheduler()
        net = Network(sched, _single_phase(), SEED)
        n = StubNode(0)
        net.register(n)
        net.bind(n)
        net.start()
        peer = StubNode(1)
        net.register(peer)
        # send now routes through the Network -> schedules a Delivery
        n.send(1, "X", None, 0.0)
        self.assertEqual(len(sched.heap), 1)

    def test_network_rng_is_process_stable(self):
        # blake2b-seeded: identical across constructions, not hash()-randomised
        a = Network(Scheduler(), _single_phase(), SEED)
        b = Network(Scheduler(), _single_phase(), SEED)
        self.assertEqual(a.net_rng.getstate(), b.net_rng.getstate())


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_network -v`
Expected: FAIL — `ImportError: cannot import name 'Network'`.

**Step 3: Write minimal implementation**

Create `src/network/network.py`:

```python
"""The honest inter-node delivery layer (network-model.md, T15/T23).

Design spec: docs/superpowers/specs/2026-05-19-t23-network-design.md
"""
from __future__ import annotations

import hashlib
import random

from nodes import Message, Node
from scheduler import Delivery, PhaseAdvance, Scheduler

from .phases import NodeId, Phase, SimTime, validate_timeline


def _network_seed(global_seed: int) -> int:
    """Process-stable 64-bit seed for the network RNG (design spec Decision D).

    blake2b, not hash() — Python's hash() of a str is process-randomised
    (PYTHONHASHSEED), which would break byte-identical replay. Mirrors the
    node-model.md §8 fix applied to the per-Node RNG.
    """
    digest = hashlib.blake2b(b"network:" + str(global_seed).encode(),
                             digest_size=8).digest()
    return int.from_bytes(digest, "big")


class Network:
    """System-level honest delivery infrastructure shared by every Node.

    Honest infrastructure only — all adversary semantics are owned by T18
    and attach at the Node level (network-model.md §6).
    """

    def __init__(self, scheduler: Scheduler,
                 phases: tuple[Phase, ...], global_seed: int) -> None:
        self.scheduler = scheduler
        self.phases: tuple[Phase, ...] = tuple(phases)
        self.registry: dict[NodeId, Node] = {}
        self.net_rng = random.Random(_network_seed(global_seed))
        self._phase_idx: int = 0
        self._started: bool = False

    def register(self, node: Node) -> None:
        """Bootstrap phase 2: make `node` resolvable as a delivery target."""
        self.registry[node.id] = node

    def bind(self, node: Node) -> None:
        """Bootstrap phase 3: wire the network half of the outbound API.

        The scheduler's bind() wires set_timer/cancel_timer/emit; this wires
        send/broadcast (simulation-design.md §7.2 split bind). `type` shadows
        the builtin to match the node-model.md §7 signature.
        """
        node.send = lambda dst, type, payload, t: self.submit_unicast(
            node.id, dst, type, payload, t)
        node.broadcast = lambda type, payload, t: self.submit_broadcast(
            node.id, type, payload, t)
```

Create/overwrite `src/network/__init__.py`:

```python
"""Honest inter-node delivery layer (network-model.md, T23).

See wiki/concepts/network-model.md + network-model-phases.md for the
design contract.
"""
from .network import Network
from .phases import DelayDist, Partition, Phase, validate_timeline

__all__ = [
    "DelayDist",
    "Network",
    "Partition",
    "Phase",
    "validate_timeline",
]
```

> Note: `test_bind_wires_send_and_broadcast` calls `net.start()` and
> `submit_unicast`, which do not exist yet — that test will still fail after
> this step. That is expected: it passes in Task 6. To keep this task green,
> the executing agent should run only the two tests that this task fully
> satisfies (next step). The full `test_network.py` goes green at Task 6.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_network.TestNetworkWiring.test_register_populates_registry test_network.TestNetworkWiring.test_network_rng_is_process_stable -v`
Expected: PASS — `OK` (2 tests). `test_bind_wires_send_and_broadcast` remains red until Task 6.

**Step 5: Checkpoint** — human reviews `network.py` (construction/register/bind), `__init__.py`, `_helpers.py` and commits `task 23: add Network construction, register, bind`.

---

## Task 5: `Network.start()` + `advance_phase` — the phase pointer (design spec §3a)

**Files:**
- Modify: `src/network/network.py` (append `start`, `advance_phase`, `_guard_started`)
- Modify: `tests/network/test_network.py` (append `TestPhaseAdvance`)

**Step 1: Write the failing test**

Append to `tests/network/test_network.py` (before the `if __name__` block):

```python
class TestPhaseAdvance(unittest.TestCase):
    def _two_phase(self):
        return (Phase(0.0, 100.0, _D), Phase(100.0, math.inf, _D))

    def test_start_schedules_interior_boundary_only(self):
        sched = Scheduler()
        net = Network(sched, self._two_phase(), SEED)
        net.start()
        # exactly one PhaseAdvance, at the single interior boundary t=100
        self.assertEqual(len(sched.heap), 1)
        t, node_id, _seq, ev = sched.heap[0]
        self.assertEqual(t, 100.0)
        self.assertEqual(node_id, Scheduler.PHASE_NODE_ID)
        self.assertEqual(ev.phase_id, 1)

    def test_start_validates_timeline(self):
        # non-contiguous timeline -> ValueError from start()
        bad = (Phase(0.0, 100.0, _D), Phase(150.0, math.inf, _D))
        net = Network(Scheduler(), bad, SEED)
        with self.assertRaises(ValueError):
            net.start()

    def test_advance_phase_moves_pointer(self):
        net = Network(Scheduler(), self._two_phase(), SEED)
        net.start()
        self.assertEqual(net._phase_idx, 0)
        net.advance_phase(1)
        self.assertEqual(net._phase_idx, 1)

    def test_advance_phase_out_of_range_raises(self):
        net = Network(Scheduler(), self._two_phase(), SEED)
        net.start()
        with self.assertRaises(ValueError):
            net.advance_phase(2)
        with self.assertRaises(ValueError):
            net.advance_phase(-1)

    def test_advance_phase_non_monotonic_raises(self):
        net = Network(Scheduler(), self._two_phase(), SEED)
        net.start()
        # skipping (0 -> 2 not possible with 2 phases; use 3-phase) and
        # repeats are non-monotonic; here 0 -> 0 is a repeat
        with self.assertRaises(RuntimeError):
            net.advance_phase(0)

    def test_phase_advances_through_scheduler_run(self):
        # end-to-end pointer move: the PhaseAdvance event drives advance_phase
        sched = Scheduler()
        net = Network(sched, self._two_phase(), SEED)
        sched.bind_network(net)
        net.start()
        sched.run()                       # only the PhaseAdvance is queued
        self.assertEqual(net._phase_idx, 1)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_network.TestPhaseAdvance -v`
Expected: FAIL — `AttributeError: 'Network' object has no attribute 'start'`.

**Step 3: Write minimal implementation**

Append to the `Network` class in `src/network/network.py`:

```python
    def start(self) -> None:
        """Bootstrap phase 5: validate the timeline and arm phase rollover.

        Schedules one PhaseAdvance per *interior* boundary. The final phase's
        t_end (possibly math.inf) is never scheduled — there is no phase after
        it, and Scheduler.schedule rejects non-finite t. validate_timeline's
        finite-interior-boundary check guarantees every scheduled t is finite.
        """
        validate_timeline(self.phases, set(self.registry))
        for i in range(len(self.phases) - 1):
            self.scheduler.schedule(
                PhaseAdvance(i + 1), self.phases[i].t_end,
                Scheduler.PHASE_NODE_ID)
        self._started = True

    def advance_phase(self, phase_id: int) -> None:
        """Scheduler-dispatched PhaseAdvance handler: move the active-phase
        pointer (design spec §3a / Decision C).

        No boundary race: PhaseAdvance carries node_id = -1, which sorts
        before every real NodeId at the same t, so the pointer advances
        before any Delivery/TimerFire at that t — realising the half-open
        [t_start, t_end) convention.
        """
        if not (0 <= phase_id < len(self.phases)):
            raise ValueError(
                f"advance_phase: phase_id={phase_id} out of range "
                f"[0, {len(self.phases)})")
        if phase_id != self._phase_idx + 1:
            raise RuntimeError(
                f"advance_phase: non-monotonic transition "
                f"{self._phase_idx} -> {phase_id} (expected +1)")
        self._phase_idx = phase_id

    def _guard_started(self) -> None:
        if not self._started:
            raise RuntimeError("Network.submit_* called before start()")
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_network.TestPhaseAdvance -v`
Expected: PASS — `OK` (6 tests).

**Step 5: Checkpoint** — human reviews `start`/`advance_phase` and commits `task 23: add Network.start and advance_phase phase pointer`.

---

## Task 6: `submit_unicast` / `submit_broadcast` / `_try_deliver` — the delivery pipeline

**Files:**
- Modify: `src/network/network.py` (append the submit methods)
- Modify: `tests/network/test_network.py` (append `TestDelivery`)

**Step 1: Write the failing test**

Append to `tests/network/test_network.py` (before the `if __name__` block):

```python
from network.network import _network_seed   # noqa: E402  (test-only import)
import random as _random                    # noqa: E402


class TestDelivery(unittest.TestCase):
    def _net(self, phases=None, ids=(0, 1, 2)):
        sched = Scheduler()
        net = Network(sched, phases or _single_phase(), SEED)
        for i in ids:
            net.register(StubNode(i))
        net.start()
        return sched, net

    def test_submit_before_start_raises(self):
        net = Network(Scheduler(), _single_phase(), SEED)
        net.register(StubNode(0))
        net.register(StubNode(1))
        with self.assertRaises(RuntimeError):
            net.submit_unicast(0, 1, "X", None, 0.0)

    def test_unicast_schedules_one_delivery(self):
        sched, net = self._net()
        net.submit_unicast(0, 1, "PING", {"k": 1}, 5.0)
        self.assertEqual(len(sched.heap), 1)
        t, node_id, _seq, ev = sched.heap[0]
        self.assertEqual(t, 15.0)                 # 5.0 + constant 10.0
        self.assertEqual(node_id, 1)              # Delivery node_id = dst
        self.assertEqual((ev.msg.src, ev.msg.dst, ev.msg.type), (0, 1, "PING"))
        self.assertEqual(ev.msg.t_sent, 5.0)

    def test_unknown_dst_raises_keyerror(self):
        _sched, net = self._net()
        with self.assertRaises(KeyError):
            net.submit_unicast(0, 99, "X", None, 0.0)

    def test_broadcast_reaches_registry_minus_sender(self):
        sched, net = self._net(ids=(0, 1, 2))
        net.submit_broadcast(1, "ANN", None, 0.0)
        dsts = sorted(ev.msg.dst for (_t, _n, _s, ev) in sched.heap)
        self.assertEqual(dsts, [0, 2])            # sender 1 excluded

    def test_full_drop_phase_suppresses_delivery(self):
        # p_drop just below 1.0 so every coin lands "drop"
        phases = (Phase(0.0, math.inf, _D, p_drop=0.999999),)
        sched, net = self._net(phases=phases)
        for _ in range(50):
            net.submit_unicast(0, 1, "X", None, 0.0)
        self.assertEqual(len(sched.heap), 0)

    def test_partition_suppresses_delivery(self):
        part = Partition(groups=((0,), (1,)))
        phases = (Phase(0.0, math.inf, _D, partitions=(part,)),)
        sched, net = self._net(phases=phases)
        net.submit_unicast(0, 1, "X", None, 0.0)  # cross-group -> blocked
        self.assertEqual(len(sched.heap), 0)

    def test_partition_drop_consumes_no_delay_sample(self):
        # network-model-phases.md §6.2: a partitioned message consumes the
        # drop coin but NOT a delay sample.
        part = Partition(groups=((0,), (1,)))
        phases = (Phase(0.0, math.inf, _D, partitions=(part,)),)
        _sched, net = self._net(phases=phases)
        net.submit_unicast(0, 1, "X", None, 0.0)
        ref = _random.Random(_network_seed(SEED))
        ref.random()                              # exactly one drop coin
        self.assertEqual(net.net_rng.getstate(), ref.getstate())

    def test_active_phase_governs_delay(self):
        # after advance_phase, sends draw from the second phase's DelayDist
        slow = DelayDist("constant", {"delay": 10.0})
        fast = DelayDist("constant", {"delay": 1.0})
        phases = (Phase(0.0, 100.0, slow), Phase(100.0, math.inf, fast))
        sched, net = self._net(phases=phases)
        net.submit_unicast(0, 1, "X", None, 0.0)
        net.advance_phase(1)
        net.submit_unicast(0, 1, "X", None, 100.0)
        delays = sorted(t - ev.msg.t_sent for (t, _n, _s, ev) in sched.heap)
        self.assertEqual(delays, [1.0, 10.0])
```

Now `Partition` is needed in `test_network.py` — update its import line at the top of the file:

```python
from network import DelayDist, Network, Partition, Phase
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_network.TestDelivery -v`
Expected: FAIL — `AttributeError: 'Network' object has no attribute 'submit_unicast'`.

**Step 3: Write minimal implementation**

Append to the `Network` class in `src/network/network.py`:

```python
    def submit_unicast(self, src: NodeId, dst: NodeId,
                       type: str, payload: object,
                       t_sent: SimTime) -> None:
        """Outbound API: deliver `payload` to one peer (node-model.md §7)."""
        self._guard_started()
        self._try_deliver(src, dst, type, payload, t_sent)

    def submit_broadcast(self, src: NodeId,
                         type: str, payload: object,
                         t_sent: SimTime) -> None:
        """Outbound API: deliver `payload` to the full registry minus sender.

        v1 broadcast set = every registered Node except `src` (design spec
        Decision B; the FSM active-validator-set seam arrives with T28).
        Recipients are iterated in sorted(NodeId) order so per-recipient
        delay samples are consumed deterministically (network-model-phases.md
        §6.3). broadcast is per-recipient independent — not atomic.
        """
        self._guard_started()
        for dst in sorted(self.registry):
            if dst != src:
                self._try_deliver(src, dst, type, payload, t_sent)

    def _try_deliver(self, src: NodeId, dst: NodeId,
                     type: str, payload: object,
                     t_sent: SimTime) -> None:
        """The five-step delivery pipeline (network-model.md §1).

        Sampling order is pinned (network-model-phases.md §6.2): drop coin
        (consumes RNG) -> partition check (no RNG) -> delay sample (consumes
        RNG). A partition-dropped message consumes no delay sample.
        """
        if dst not in self.registry:                       # 1. resolve
            raise KeyError(
                f"submit: dst={dst} not registered (configuration error)")
        phase = self.phases[self._phase_idx]
        if self.net_rng.random() < phase.p_drop:           # 2. drop coin
            return
        if any(p.blocks(src, dst) for p in phase.partitions):  # 3. partition
            return
        delay = phase.delay.sample(self.net_rng)           # 4. delay
        msg = Message(src=src, dst=dst, type=type, payload=payload,
                      t_sent=t_sent)
        self.scheduler.schedule(Delivery(msg), t_sent + delay, dst)  # 5.
```

**Step 4: Run the full network suite to verify it passes**

Run: `PYTHONPATH=src:tests/network python3 -m unittest discover -s tests/network -v`
Expected: PASS — `OK`. All of `test_delay_dist`, `test_partition`, `test_phases`, `test_network` green (including `TestNetworkWiring.test_bind_wires_send_and_broadcast`, red since Task 4, now satisfied).

**Step 5: Checkpoint** — human reviews the submit pipeline and commits `task 23: add Network delivery pipeline (unicast, broadcast, drop, partition)`.

---

## Task 7: End-to-end build verification + experiment baseline page

**Files:**
- Create: `tests/network/test_e2e.py`
- Create: `wiki/experiments/2026-05-19_network-baseline.md`

**Step 1: Write the failing test**

Create `tests/network/test_e2e.py`:

```python
"""End-to-end: the real Network drives Nodes through the six-phase bootstrap.

Replaces the LoopbackNetwork stub (tests/nodes/_helpers.py) with the real
T23 Network. Exercises network-model.md delivery + the network-level
determinism contract (network-model-phases.md §6.4).
"""
import math
import unittest

from network import DelayDist, Network, Phase
from scheduler import Delivery, Scheduler
from _helpers import PingPongNode

_D = DelayDist("constant", {"delay": 10.0})


def _run(global_seed, phases=None, budget=4):
    """Six-phase bootstrap (simulation-design.md §7.2) over the real Network."""
    sched = Scheduler()
    net = Network(sched, phases or (Phase(0.0, math.inf, _D),), global_seed)
    nodes = [
        PingPongNode(0, peer_id=1, budget=budget, global_seed=global_seed),
        PingPongNode(1, peer_id=0, budget=budget, global_seed=global_seed),
    ]
    deliveries: list = []
    sched.event_sink = lambda t, nid, seq, ev: (
        deliveries.append((ev.msg.src, ev.msg.dst, ev.msg.type,
                           ev.msg.t_sent, t))
        if isinstance(ev, Delivery) else None)
    for n in nodes:                       # phase 2: register
        net.register(n)
    sched.bind_network(net)               # phase 3: PhaseAdvance dispatch target
    for n in nodes:                       # phase 3: split bind
        sched.bind(n)
        net.bind(n)
    net.start()                           # phase 5: arm phase rollover
    for n in nodes:                       # phase 5: kickoff
        n.start(0.0)
    result = sched.run()                  # phase 6
    return result, deliveries


class TestNetworkE2E(unittest.TestCase):
    def test_run_reaches_quiescence(self):
        result, _ = _run(global_seed=42)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_deliveries_respect_constant_delay(self):
        _, deliveries = _run(global_seed=42)
        self.assertTrue(deliveries)
        for (_src, _dst, _type, t_sent, t_delivered) in deliveries:
            self.assertEqual(t_delivered - t_sent, 10.0)

    def test_two_seed_identical_runs_are_byte_identical(self):
        _, a = _run(global_seed=42)
        _, b = _run(global_seed=42)
        self.assertEqual(a, b)

    def test_multi_phase_run_reaches_quiescence(self):
        # slow phase then fast phase; advance_phase fires mid-run
        phases = (
            Phase(0.0, 25.0, DelayDist("constant", {"delay": 10.0})),
            Phase(25.0, math.inf, DelayDist("constant", {"delay": 2.0})),
        )
        result, deliveries = _run(global_seed=42, phases=phases)
        self.assertEqual(result.stopped_by, "quiescence")
        # at least one delivery used each phase's delay
        observed = {round(td - ts, 6) for (*_x, ts, td) in deliveries}
        self.assertEqual(observed, {10.0, 2.0})


if __name__ == "__main__":
    unittest.main()
```

> **If `test_multi_phase_run_reaches_quiescence` does not observe both
> delays:** the ping-pong's send times depend on accumulated delay, so the
> exact crossing of `t=25` is timing-sensitive. If the run never sends after
> `t=25`, widen phase 0 (`t_end`) or raise `budget` until both delays appear,
> then pin the values in the test. Do not weaken the determinism test
> (`test_two_seed_identical_runs_are_byte_identical`) to compensate.

**Step 2: Run test to verify it fails / passes**

Run: `PYTHONPATH=src:tests/network python3 -m unittest test_e2e -v`
Expected: PASS — `OK` (4 tests). (The implementation is already complete from Tasks 1–6; this task is the build-verification harness. If a test fails, fix per the note above, not by weakening assertions.)

**Step 3: Write the experiment baseline page**

Create `wiki/experiments/2026-05-19_network-baseline.md`. Follow the structure of `wiki/experiments/2026-05-19_node-baseline.md` exactly — sections: title + intro, `## Configuration`, `## Re-run`, `## Result`, `## Observation`, `## Back-links`. Content:

- **Intro:** First runnable artifact of the delivery layer — the `Network`
  (`network-model.md` / `network-model-phases.md`) driving a 2-node ping-pong
  on the T21 scheduler and T22 nodes. A build-verification baseline, not a
  protocol experiment.
- **Configuration:** component under test `src/network/`; scenario = 2-node
  `PingPongNode` ping-pong, `budget=4`, single phase `[0, ∞)` with
  `DelayDist("constant", {"delay": 10.0})`; full six-phase bootstrap; stub =
  `PingPongNode` (real protocol FSMs are T28/T32/T38); seed `global_seed=42`;
  commit hash = **the commit the human makes at this task's checkpoint**
  (leave a `TODO(human): commit hash` marker — the page is written before
  the commit exists).
- **Re-run:** the two `PYTHONPATH=...` discover commands for `tests/network`
  and (regression) `tests/scheduler`, `tests/nodes`.
- **Result:** total network-suite test count to green; ping-pong reaches
  quiescence at `t=70`; deliveries show the constant 10 ms delay; two
  `global_seed`-identical runs produce byte-identical delivery streams.
- **Observation:** one paragraph — the real `Network` replaces the
  `LoopbackNetwork` stub end-to-end; delay injection, drop, partition, and
  the network-level determinism contract (`network-model-phases.md §6.4`)
  hold; phase rollover via the `_phase_idx` pointer works under a real
  scheduler run.
- **Back-links:** `[[concepts/network-model]]`,
  `[[concepts/network-model-phases]]`, `[[concepts/simulation-design]]`.

**Step 4: Verify the experiment page**

Run: `PYTHONPATH=src:tests/network python3 -m unittest discover -s tests/network -v`
Expected: PASS — `OK`. Confirm the test count quoted in the page matches the actual run.

**Step 5: Checkpoint** — human reviews `test_e2e.py` + the experiment page, commits `task 23: add network e2e build verification + baseline page`, then **fills the `TODO(human): commit hash` marker** with that commit's hash.

---

## Task 8: Regression check + wiki bookkeeping

**Files:**
- Modify: `wiki/concepts/network-model-phases.md` (append a `## Revisions` entry)
- Modify: `wiki/index.md` (add the experiment page under Experiments)
- Modify: `wiki/log.md` (append one `code`-type entry)

**Step 1: Run the full regression suite**

The `Network` imports `Message` from `src/nodes/` and queues events on the
T21 `Scheduler`; confirm no regression in either upstream suite.

Run all three suites:
```
PYTHONPATH=src:tests/network python3 -m unittest discover -s tests/network -v
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v
```
Expected: all three `OK`. Record the per-suite test counts — they go in the
`log.md` entry and the experiment page.

**Step 2: Add the `## Revisions` entry to `network-model-phases.md`**

Append to `wiki/concepts/network-model-phases.md` a `## Revisions` section
(or a dated entry under the existing one if present) recording the
**Decision D** divergence:

- Date `2026-05-19`, T23 implementation.
- §6.1 specifies `Random(seed=hash(("network", global_seed)))`. Python's
  `hash()` of a tuple containing a `str` is process-randomised
  (`PYTHONHASHSEED`), which breaks byte-identical replay across processes.
- T23 diverges: a `blake2b`-derived stable seed (`_network_seed`), identical
  across processes and machines.
- This mirrors the `node-model.md §8` fix applied to the per-Node RNG
  (2026-05-19) and protects the determinism contract this very page (§6)
  promises. The §6.2 sampling order and §6.3 forbidden surfaces are
  unchanged.

Keep it in the register's existing register style; do not silently rewrite
§6.1 (`docs/wiki-spec.md` § Revisions rule).

**Step 3: Update `wiki/index.md`**

Under `## Experiments`, add one line after the `node-baseline` entry:

```
- [[experiments/2026-05-19_network-baseline]] — T23 build-verification baseline: the real `Network` drives a 2-node ping-pong through the six-phase bootstrap to quiescence; delay injection, drop, partition, and the network-level determinism contract hold.
```

**Step 4: Append to `wiki/log.md`**

Append one entry in the `docs/wiki-spec.md` § Log format:

```
## [2026-05-19] code | task 23 — Message passing with configurable delay
- role: Engineer
- touched: src/network/{__init__,phases,network}.py, tests/network/{_helpers,test_delay_dist,test_partition,test_phases,test_network,test_e2e}.py, wiki/experiments/2026-05-19_network-baseline.md, wiki/concepts/network-model-phases.md, wiki/index.md
- notes: <one sentence — built the honest delivery layer (phases, 5 delay distributions, Bernoulli drop, partition predicate, blake2b-seeded RNG); recorded the §6.1 seed divergence as a Revision.>
```

**Step 5: Checkpoint** — human reviews the wiki edits and commits
`wiki: record T23 network-baseline experiment and §6.1 seed Revision` (or
folds it into the task-8 commit per their preference).

---

## Post-plan: verification before In Review

Per the Engineer role, before T23 flips to In Review the executing session
invokes `superpowers:verification-before-completion`: re-run all three test
suites, confirm `OK`, and confirm the test counts quoted in the experiment
page and `log.md` match the actual output. Then the human flips `TASKS.md`
T23 `[~]` → `[?]` and the branch is pushed for review. Agents never
self-complete (`docs/workflow.md`).

## Out of scope (do not implement — see design spec §10)

Adversary semantics (T18); per-protocol message contents (T16); YAML phase
loading / `global_seed` sourcing (T19/T27); the scrambled-call-order
determinism test (T25); bandwidth / region-aware delay / bursty drop /
per-edge partition allowlisting (`network-model.md §8`); repointing
`broadcast` at the FSM validator set (T28). Do not edit `tests/nodes/` — the
`LoopbackNetwork` stub stays as T22's test fixture.
