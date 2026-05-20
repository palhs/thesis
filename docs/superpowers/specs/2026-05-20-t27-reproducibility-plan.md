# T27 — Reproducibility (seed control + YAML configs): Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build `src/config/` — the YAML configuration loader and reproducibility harness — plus the four "Watch for T27" boundary-seam fail-fast gates pre-flagged in `TASKS.md` § Backlog, plus the consolidating `wiki/concepts/reproducibility.md` page.

**Architecture:** A `src/config/` package with three modules: `schema.py` (frozen dataclasses), `loader.py` (PyYAML `safe_load` → required-key check → type coercion → leaf construction → cross-field validation), `factory.py` (`build_run(config, global_seed, node_factory) -> RunHandle` orchestrates the existing six-phase bootstrap). The four backlog gates are precondition checks added at the offended boundary (`Node.__init__`, `Network.register`, `Network.start`, `Scheduler.bind`), not in the loader — so tests bypassing `build_run` still fail fast. Reproducibility is end-to-end: same YAML + same `global_seed` → byte-identical `event_sink` stream.

**Tech Stack:** Python 3.13. **New runtime dependency:** PyYAML (the simulator's first non-stdlib runtime dep). Stdlib otherwise (`hashlib` and `random` already used by Node and Network for seed derivation via `blake2b`). `unittest` for tests. Upstream code: `src/scheduler/` (T21), `src/nodes/` (T22), `src/network/` (T23), `src/event_log/` (T24).

**Design spec:** `docs/superpowers/specs/2026-05-20-t27-reproducibility-design.md` — read it before starting; this plan implements it literally.

**Test commands (no pytest in this environment — `unittest` only):**
- All suites: `make test`
- One suite: `make test-config` (added in Task 6) — or for the existing suites: `make test-nodes`, `make test-network`, `make test-scheduler`, `make test-event_log`, `make test-integration`
- One module: `PYTHONPATH=src:tests/config python3 -m unittest test_schema -v`
- One test: `PYTHONPATH=src:tests/config python3 -m unittest test_schema.TestConfig.test_frozen -v`
- Coverage: `make coverage`

**Commit convention:** Each task ends with a **Checkpoint** — the *human* reviews and commits (`task 27: <desc>`). The executing agent does **not** run `git commit`; it stages nothing and stops at the checkpoint for human action.

**Wiki discipline:** Per `docs/wiki-spec.md`, the wiki page goes in last — it documents what the code already does. `wiki/index.md` and `wiki/log.md` updates land in the same task.

---

## Task 1: Pin PyYAML in `requirements.txt`

**Files:**
- Modify: `requirements.txt`

**Step 1: Inspect current contents**

Run: `cat requirements.txt`

Expected (current state):
```
# Runtime dependencies for the thesis simulator.
#
# The simulator (src/) currently uses the Python standard library only.
# T27 introduces YAML configuration; the loader will pin its dependency
# here when it lands.
```

**Step 2: Update the file**

Replace the entire file with:

```
# Runtime dependencies for the thesis simulator.
#
# PyYAML is the simulator's first non-stdlib runtime dependency, pinned by
# T27 (src/config/) for the YAML loader. Use `safe_load` only — never
# `yaml.load` with an unsafe loader (reproducibility.md § Forbidden surfaces).

PyYAML>=6.0
```

**Step 3: Verify install (optional in this sandbox; required on the human's machine)**

The executing agent does not run pip; the human installs after merge:

```bash
pip install -r requirements.txt
```

**Step 4: Checkpoint**

Stop. Human reviews and commits as `task 27: pin PyYAML runtime dep`.

---

## Task 2: Gate 1 — `Node.__init__` rejects `node_id < 0` and non-finite `weight`

Pre-flagged in `TASKS.md` § Backlog (entry: "Node.__init__ accepts non-finite weight (NaN, ±inf)" and "Node.__init__ accepts node_id = -1 (the PhaseAdvance sentinel)").

**Files:**
- Modify: `src/nodes/node.py` (extend `Node.__init__` validation block, ~lines 43–54)
- Modify: `tests/nodes/test_node.py` (extend the existing `TestConstruction` class)

**Step 1: Write the failing tests**

Append to `tests/nodes/test_node.py` inside class `TestConstruction`:

```python
    def test_negative_node_id_rejected(self):
        # node_id = -1 is the PhaseAdvance sentinel; -2 etc. would still
        # silently sort before every real NodeId at the same t.
        with self.assertRaises(ValueError):
            FakeNode(node_id=-1)
        with self.assertRaises(ValueError):
            FakeNode(node_id=-7)

    def test_nan_weight_rejected(self):
        import math
        with self.assertRaises(ValueError):
            FakeNode(weight=math.nan)

    def test_pos_inf_weight_rejected(self):
        import math
        with self.assertRaises(ValueError):
            FakeNode(weight=math.inf)

    def test_neg_inf_weight_rejected(self):
        import math
        # `weight < 0` already rejects -inf, but the explicit guard names
        # `weight must be finite` in the error rather than `must be non-negative`.
        with self.assertRaises(ValueError) as cm:
            FakeNode(weight=-math.inf)
        self.assertIn("finite", str(cm.exception))
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest tests.nodes.test_node.TestConstruction -v`

Expected: four new tests FAIL (Node accepts the bad values today). The existing `test_negative_weight_rejected` still passes.

**Step 3: Implement the guards**

Edit `src/nodes/node.py`. Add `import math` to the existing import block (line 8 area). Replace the existing validation block in `Node.__init__` (currently just `if weight < 0:`) with:

```python
        if node_id < 0:
            raise ValueError(
                f"node_id must be non-negative, got {node_id} "
                f"(values < 0 collide with the PhaseAdvance sentinel)")
        if not math.isfinite(weight):
            raise ValueError(f"weight must be finite, got {weight}")
        if weight < 0:
            raise ValueError(f"weight must be non-negative, got {weight}")
```

The order matters: `node_id` first, `isfinite(weight)` before `weight < 0` so a `weight = -math.inf` raises with the "finite" message (matches `test_neg_inf_weight_rejected`).

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src:tests/nodes python3 -m unittest tests.nodes.test_node -v`

Expected: all `TestConstruction` cases PASS, including the four new ones. Other test classes (`TestRng`, `TestOutboundUnbound`, etc.) still pass — `import math` is the only added module-level change.

**Step 5: Run the full suite to confirm no upstream regressions**

Run: `make test-nodes`

Expected: PASS.

**Step 6: Checkpoint**

Stop. Human commits as `task 27: Node fail-fast on negative node_id and non-finite weight`.

---

## Task 3: Gate 2 — `Network.register` rejects duplicate `node.id`

Pre-flagged in `TASKS.md` § Backlog.

**Files:**
- Modify: `src/network/network.py` (`Network.register`, ~line 44)
- Modify: `tests/network/test_network.py` (extend existing test class)

**Step 1: Write the failing test**

Append to `tests/network/test_network.py` (in whichever test class hosts `register` tests; if none, add a new `TestRegister` class):

```python
class TestRegisterCollision(unittest.TestCase):
    def test_duplicate_register_rejected(self):
        # A duplicate register silently clobbers today; the gate makes it loud.
        scheduler = Scheduler()
        network = Network(scheduler, _ONE_PHASE, global_seed=0)
        a = FakeNode(node_id=5)
        b = FakeNode(node_id=5)
        network.register(a)
        with self.assertRaises(ValueError) as cm:
            network.register(b)
        self.assertIn("5", str(cm.exception))
        # First registration still resolvable.
        self.assertIs(network.registry[5], a)
```

If `_ONE_PHASE` and `FakeNode` are not already importable in this test file, copy the helper imports from a sibling test file in the same suite (typically `from _helpers import ...` plus the standard `Scheduler` / `Network` imports). `_ONE_PHASE` should be a `tuple[Phase, ...]` constant exposed in `tests/network/_helpers.py`; if it does not exist, define it locally in the test file as:

```python
_ONE_PHASE = (Phase(t_start=0.0, t_end=math.inf,
                    delay=DelayDist("constant", {"delay": 1.0})),)
```

(matching the existing test fixtures' phase shape).

**Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src:tests/network python3 -m unittest tests.network.test_network.TestRegisterCollision -v`

Expected: FAIL — current `register` silently overwrites.

**Step 3: Implement the guard**

Edit `src/network/network.py`. In `Network.register`:

```python
    def register(self, node: Node) -> None:
        """Bootstrap phase 2: make `node` resolvable as a delivery target."""
        if node.id in self.registry:
            raise ValueError(
                f"Network.register: NodeId {node.id} already registered")
        self.registry[node.id] = node
```

**Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=src:tests/network python3 -m unittest tests.network.test_network.TestRegisterCollision -v`

Expected: PASS.

**Step 5: Run the full network suite**

Run: `make test-network`

Expected: PASS — no existing test re-registers a node, so no regressions.

**Step 6: Checkpoint**

Stop. Human commits as `task 27: Network.register fail-fast on duplicate node`.

---

## Task 4: Gate 3 — `Scheduler.bind` rejects duplicate `node.id`

Pre-flagged in `TASKS.md` § Backlog.

**Files:**
- Modify: `src/scheduler/scheduler.py` (`Scheduler.bind`, ~line 101)
- Modify: `tests/scheduler/test_scheduler.py` (extend existing test class)

**Step 1: Write the failing test**

Append to `tests/scheduler/test_scheduler.py`:

```python
class TestBindCollision(unittest.TestCase):
    def test_duplicate_bind_rejected(self):
        # Symmetric to Network.register's collision guard; both seams need
        # the check because build_run() calls them independently.
        sched = Scheduler()
        a = StubNode(node_id=3)
        b = StubNode(node_id=3)
        sched.bind(a)
        with self.assertRaises(ValueError) as cm:
            sched.bind(b)
        self.assertIn("3", str(cm.exception))
        # First binding still in place.
        self.assertIs(sched.nodes[3], a)
```

`StubNode` is presumably already defined in `tests/scheduler/_stubs.py`; reuse it. If not, look at the existing `Scheduler.bind` tests and reuse whatever local fake they use.

**Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest tests.scheduler.test_scheduler.TestBindCollision -v`

Expected: FAIL — current `bind` silently overwrites.

**Step 3: Implement the guard**

Edit `src/scheduler/scheduler.py`. In `Scheduler.bind`:

```python
    def bind(self, node: Any) -> None:
        """Wire a Node's scheduler-owned outbound API and register it for
        dispatch. Does NOT wire send/broadcast — that is Network.bind's half.
        """
        if node.id in self.nodes:
            raise ValueError(
                f"Scheduler.bind: NodeId {node.id} already bound")
        self.nodes[node.id] = node   # DD3 / Revision R1: dispatch target.
        node.set_timer = lambda timer_id, delay, payload, t: self.set_timer(
            node.id, timer_id, delay, payload, t
        )
        node.cancel_timer = lambda timer_id: self.cancel_timer(
            node.id, timer_id
        )
        node.emit = lambda event_type, fields, t: (
            self.event_sink(t, node.id, self.EMIT_SEQ,
                            ("emit", event_type, fields))
            if self.event_sink is not None
            else None
        )
```

**Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=src:tests/scheduler python3 -m unittest tests.scheduler.test_scheduler.TestBindCollision -v`

Expected: PASS.

**Step 5: Run the full scheduler suite**

Run: `make test-scheduler`

Expected: PASS — no existing test re-binds a node.

**Step 6: Checkpoint**

Stop. Human commits as `task 27: Scheduler.bind fail-fast on duplicate node`.

---

## Task 5: Gate 4 — `Network.start` is idempotent

Pre-flagged in `TASKS.md` § Backlog ("`Network.start` is not idempotent — calling it twice ... doubles phase-rollover events on the heap").

**Files:**
- Modify: `src/network/network.py` (`Network.start`, ~line 60)
- Modify: `tests/network/test_network.py`

**Step 1: Write the failing test**

Append to `tests/network/test_network.py`:

```python
class TestStartIdempotency(unittest.TestCase):
    def test_double_start_rejected(self):
        scheduler = Scheduler()
        network = Network(scheduler, _ONE_PHASE, global_seed=0)
        network.register(FakeNode(node_id=0))
        network.start()
        with self.assertRaises(RuntimeError) as cm:
            network.start()
        self.assertIn("already started", str(cm.exception))

    def test_double_start_does_not_double_phase_rollovers(self):
        # Two-phase timeline: a duplicate start would push a duplicate
        # PhaseAdvance and double the heap entries. The guard prevents it.
        two_phase = (
            Phase(0.0, 50.0, DelayDist("constant", {"delay": 1.0})),
            Phase(50.0, math.inf, DelayDist("constant", {"delay": 1.0})),
        )
        scheduler = Scheduler()
        network = Network(scheduler, two_phase, global_seed=0)
        network.register(FakeNode(node_id=0))
        network.start()
        heap_size_after_one_start = len(scheduler.heap)
        with self.assertRaises(RuntimeError):
            network.start()
        # heap unchanged by the rejected second call:
        self.assertEqual(len(scheduler.heap), heap_size_after_one_start)
```

**Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=src:tests/network python3 -m unittest tests.network.test_network.TestStartIdempotency -v`

Expected: both FAIL — current `start()` silently re-arms the timeline.

**Step 3: Implement the guard**

Edit `src/network/network.py`. In `Network.start`:

```python
    def start(self) -> None:
        """Bootstrap phase 5: validate the timeline and arm phase rollover.
        ...
        """
        if self._started:
            raise RuntimeError("Network.start: already started")
        validate_timeline(self.phases, set(self.registry))
        for i in range(len(self.phases) - 1):
            self.scheduler.schedule(
                PhaseAdvance(i + 1), self.phases[i].t_end,
                Scheduler.PHASE_NODE_ID)
        self._started = True
```

**Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=src:tests/network python3 -m unittest tests.network.test_network.TestStartIdempotency -v`

Expected: both PASS.

**Step 5: Run the full network suite**

Run: `make test-network`

Expected: PASS — no existing test calls `start()` twice.

**Step 6: Checkpoint**

Stop. Human commits as `task 27: Network.start idempotency`.

---

## Task 6: `src/config/` scaffold + schema dataclasses

Creates the package skeleton, the `SeedsConfig` / `Config` / `RunHandle` dataclasses, and the `tests/config/` suite layout. The `Makefile` `SUITES` list gains `config`.

**Files:**
- Create: `src/config/__init__.py`
- Create: `src/config/schema.py`
- Create: `tests/config/__init__.py` (empty package marker — match the existing suite convention)
- Create: `tests/config/test_schema.py`
- Modify: `Makefile` (add `config` to `SUITES`)

**Step 1: Write the failing tests**

Create `tests/config/test_schema.py`:

```python
"""Unit tests for src/config/schema.py — Config, SeedsConfig, RunHandle."""
from __future__ import annotations

import math
import unittest
from dataclasses import FrozenInstanceError
from types import MappingProxyType

from config.schema import Config, RunHandle, SeedsConfig
from network.phases import DelayDist, Phase


class TestSeedsConfig(unittest.TestCase):
    def test_construction(self):
        s = SeedsConfig(n_runs=20)
        self.assertEqual(s.n_runs, 20)

    def test_frozen(self):
        s = SeedsConfig(n_runs=20)
        with self.assertRaises(FrozenInstanceError):
            s.n_runs = 21          # type: ignore[misc]

    def test_structural_equality(self):
        self.assertEqual(SeedsConfig(n_runs=5), SeedsConfig(n_runs=5))
        self.assertNotEqual(SeedsConfig(n_runs=5), SeedsConfig(n_runs=6))


_PHASES = (
    Phase(t_start=0.0, t_end=math.inf,
          delay=DelayDist("constant", {"delay": 50.0})),
)


class TestConfig(unittest.TestCase):
    def _make(self, **kw):
        defaults = dict(
            n=4,
            t_max=1000.0,
            seeds=SeedsConfig(n_runs=20),
            network=_PHASES,
            adversary={},
            protocol_knobs={},
            workload={},
        )
        defaults.update(kw)
        return Config(**defaults)

    def test_construction(self):
        c = self._make()
        self.assertEqual(c.n, 4)
        self.assertEqual(c.t_max, 1000.0)
        self.assertEqual(c.seeds.n_runs, 20)
        self.assertEqual(c.network, _PHASES)
        self.assertEqual(c.adversary, {})
        self.assertEqual(c.protocol_knobs, {})
        self.assertEqual(c.workload, {})

    def test_frozen(self):
        c = self._make()
        with self.assertRaises(FrozenInstanceError):
            c.n = 7                # type: ignore[misc]

    def test_structural_equality_same_inputs(self):
        # Two loads of the same YAML must produce equal Configs.
        self.assertEqual(self._make(), self._make())

    def test_inequality_when_seed_block_differs(self):
        self.assertNotEqual(self._make(seeds=SeedsConfig(n_runs=20)),
                            self._make(seeds=SeedsConfig(n_runs=30)))


class TestRunHandle(unittest.TestCase):
    def test_nodes_field_is_immutable_mapping(self):
        # Pure shape test — no Scheduler/Network construction here; that's
        # covered in test_factory.py.
        nodes_view = MappingProxyType({0: object(), 1: object()})
        handle = RunHandle(
            scheduler=object(),  # type: ignore[arg-type]
            network=object(),    # type: ignore[arg-type]
            nodes=nodes_view,
        )
        with self.assertRaises(TypeError):
            handle.nodes[2] = object()    # type: ignore[index]
        self.assertEqual(set(handle.nodes), {0, 1})


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Add the `config` suite to the Makefile**

Edit `Makefile`. Change the `SUITES` line from:

```
SUITES        = scheduler nodes network event_log integration
```

to:

```
SUITES        = scheduler nodes network event_log config integration
```

`config` is inserted before `integration` so the cross-component integration suite runs last.

**Step 3: Run the tests to verify they fail**

Run: `PYTHONPATH=src:tests/config python3 -m unittest discover -s tests/config -v`

Expected: FAIL — `config.schema` does not exist yet.

**Step 4: Write the schema module**

Create `src/config/__init__.py`:

```python
"""Reproducibility harness: YAML configs + seed control (T27).

Spec: docs/superpowers/specs/2026-05-20-t27-reproducibility-design.md
"""
from .schema import Config, RunHandle, SeedsConfig

__all__ = ["Config", "RunHandle", "SeedsConfig"]
```

(Re-exports for `ConfigError`, `load_config`, `build_run` are added by later tasks as those names land.)

Create `src/config/schema.py`:

```python
"""Frozen dataclasses for the YAML config schema (T27 spec § 3).

Three sections (`adversary`, `protocol_knobs`, `workload`) are opaque
`Mapping[str, Any]` blobs by design — their upstream wiki contracts are
open-to-revision (adversary-model-runtime §4, node-model §11). When the
tasks that own those contracts (T18 binding, T28+, T41) land, each replaces
its `dict` with a typed dataclass.

Network sub-types are reused from src/network/phases.py — do not mirror
them as *Config types.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from network.phases import Phase
from nodes import Node
from scheduler import Scheduler


@dataclass(frozen=True)
class SeedsConfig:
    """Seeds / replication axis (experiment-matrix.md §7).

    `n_runs` is the only field today; the harness enumerates seeds
    0 … n_runs-1 externally. A future SeedsConfig revision may add a
    seed_seq override; deferred to T41.
    """
    n_runs: int


@dataclass(frozen=True)
class Config:
    """One configuration point — one row of the future T40 comparative CSV.

    Six axes (experiment-matrix.md §2) plus the operational t_max scalar.
    Three opaque sections are loaded round-trip but not introspected by
    build_run.
    """
    n: int
    t_max: float
    seeds: SeedsConfig
    network: tuple[Phase, ...]
    adversary: Mapping[str, Any]       # opaque — T18
    protocol_knobs: Mapping[str, Any]  # opaque — T28+
    workload: Mapping[str, Any]        # opaque — T41


@dataclass(frozen=True)
class RunHandle:
    """Three handles returned by build_run(): the Scheduler, the Network,
    and an immutable Mapping[NodeId, Node] view of the registered Nodes.
    """
    scheduler: Scheduler
    # `network` is forward-declared as Any to avoid a circular import; T27
    # does not depend on Network's type for any narrowing.
    network: Any
    nodes: Mapping[int, Node]
```

(Note the `network: Any` field type — typing it as `Network` would force `from network import Network` here, which is fine in this direction but adds an import. `Any` is safe; the factory test in Task 10 type-checks the constructed object structurally.)

**Step 5: Run the tests to verify they pass**

Run: `PYTHONPATH=src:tests/config python3 -m unittest discover -s tests/config -v`

Expected: PASS — all five schema tests.

**Step 6: Run `make test-config` to confirm the Makefile target works**

Run: `make test-config`

Expected: PASS.

**Step 7: Run the full suite to confirm no regressions**

Run: `make test`

Expected: PASS — `config` suite passes; all other suites unaffected.

**Step 8: Checkpoint**

Stop. Human commits as `task 27: src/config/ scaffold + schema dataclasses`.

---

## Task 7: `ConfigError` + `load_config` — parse + required-key check

First of three loader tasks. Builds steps 4.1 and 4.2 of the spec (parse and required-key enforcement).

**Files:**
- Modify: `src/config/__init__.py` (add `ConfigError`, `load_config` re-exports)
- Create: `src/config/loader.py`
- Create: `tests/config/test_loader.py`
- Create: `tests/config/_helpers.py` (canonical-YAML constant, reused by Tasks 7–11)

**Step 1: Write the test helper**

Create `tests/config/_helpers.py`:

```python
"""Test helpers for the T27 config suite."""
from __future__ import annotations

import textwrap

# Canonical minimal valid YAML — used by every loader / factory / e2e test.
# 4 nodes, single-phase constant-delay network, t_max=1000, n_runs=1, all
# three opaque sections empty.
MINIMAL_YAML = textwrap.dedent("""\
    n: 4
    t_max: 1000.0
    seeds:
      n_runs: 1
    network:
      phases:
        - t_start: 0
          t_end: .inf
          delay:
            kind: constant
            params: { delay: 50.0 }
          p_drop: 0.0
          partitions: []
    adversary: {}
    protocol_knobs: {}
    workload: {}
""")


def write_yaml(tmp_path, body: str = MINIMAL_YAML):
    """Materialise `body` as a temp YAML file and return its path."""
    p = tmp_path / "cfg.yaml"
    p.write_text(body)
    return p
```

The `tmp_path` fixture-style parameter is just a `pathlib.Path` — each test constructs its own with `pathlib.Path(self.tmpdir.name)` via the standard `unittest.TestCase.setUp` pattern.

**Step 2: Write the failing tests**

Create `tests/config/test_loader.py`:

```python
"""Unit tests for src/config/loader.py — ConfigError + load_config."""
from __future__ import annotations

import pathlib
import tempfile
import textwrap
import unittest

from config.loader import ConfigError, load_config
from _helpers import MINIMAL_YAML, write_yaml


class _LoaderTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class TestParse(_LoaderTestBase):
    def test_canonical_minimal_yaml_loads(self):
        path = write_yaml(self.tmp_path, MINIMAL_YAML)
        cfg = load_config(path)
        self.assertEqual(cfg.n, 4)
        self.assertEqual(cfg.t_max, 1000.0)

    def test_yaml_parse_error_wraps(self):
        path = write_yaml(self.tmp_path, "n: 4\n  bad indent: oops\n")
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("parse failed", str(cm.exception).lower())

    def test_top_level_must_be_dict(self):
        path = write_yaml(self.tmp_path, "- 1\n- 2\n- 3\n")
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_yaml_tags_rejected_by_safe_load(self):
        # safe_load refuses Python-object tags. The loader's parse-step
        # wraps the resulting yaml.YAMLError as ConfigError.
        path = write_yaml(self.tmp_path,
                          "n: !!python/object/apply:os.system ['echo']\n")
        with self.assertRaises(ConfigError):
            load_config(path)


class TestRequiredKeys(_LoaderTestBase):
    REQUIRED_TOP_LEVEL = (
        "n", "t_max", "seeds", "network",
        "adversary", "protocol_knobs", "workload",
    )

    def _yaml_without(self, key):
        # Build a YAML missing exactly one required top-level key.
        lines = []
        skip = False
        for line in MINIMAL_YAML.splitlines(keepends=True):
            stripped = line.split(":", 1)[0].strip()
            if not line.startswith((" ", "-")) and stripped == key:
                skip = True
                continue
            if skip and (line.startswith(" ") or line.startswith("-")):
                continue           # consume the value block of the removed key
            skip = False
            lines.append(line)
        return "".join(lines)

    def test_each_top_level_key_required(self):
        for key in self.REQUIRED_TOP_LEVEL:
            with self.subTest(missing=key):
                path = write_yaml(self.tmp_path, self._yaml_without(key))
                with self.assertRaises(ConfigError) as cm:
                    load_config(path)
                self.assertIn(key, str(cm.exception))

    def test_unknown_top_level_key_rejected(self):
        body = MINIMAL_YAML + "n_run: 99\n"     # typo of n_runs at top level
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("n_run", str(cm.exception))

    def test_seeds_n_runs_required(self):
        body = MINIMAL_YAML.replace("seeds:\n  n_runs: 1\n", "seeds: {}\n")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("n_runs", str(cm.exception))

    def test_network_phases_required(self):
        body = MINIMAL_YAML.replace(
            "network:\n  phases:\n    - t_start: 0",
            "network: {}\n# stripped phases\n#    - t_start: 0",
        )
        # Crude string surgery; just make sure the resulting YAML loads.
        path = write_yaml(self.tmp_path,
                          "n: 4\nt_max: 1000.0\nseeds:\n  n_runs: 1\n"
                          "network: {}\nadversary: {}\n"
                          "protocol_knobs: {}\nworkload: {}\n")
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("phases", str(cm.exception))


class TestErrorFormat(_LoaderTestBase):
    def test_str_contains_path_key_and_reason(self):
        body = MINIMAL_YAML.replace("n: 4\n", "")    # drop required n
        path = write_yaml(self.tmp_path, body)
        try:
            load_config(path)
        except ConfigError as e:
            s = str(e)
            self.assertIn(str(path), s)
            self.assertIn("n", s)
            return
        self.fail("ConfigError not raised")


if __name__ == "__main__":
    unittest.main()
```

**Step 3: Run the tests to verify they fail**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_loader -v`

Expected: FAIL — `config.loader` does not exist yet.

**Step 4: Implement the loader (parse + required-keys only — Tasks 8 and 9 add coercion + cross-field)**

Create `src/config/loader.py`:

```python
"""YAML config loader (T27 spec § 4).

Five-step pipeline: parse → required-keys → type-coercion → leaf-construct →
cross-field. This module owns steps 4.1 + 4.2 today; Task 8 fills 4.3 + 4.4
and Task 9 fills 4.5.

Every failure is funneled into ConfigError(path, key_path, message). No
other exception type escapes load_config — yaml.YAMLError and ValueError
from leaf __post_init__ validators are caught and re-raised.
"""
from __future__ import annotations

import pathlib
from typing import Any

import yaml

from .schema import Config, SeedsConfig
from network.phases import DelayDist, Partition, Phase


class ConfigError(ValueError):
    """Loader / cross-field validation failure.

    `__str__` returns `f"{path}: {key_path}: {message}"` — a caller printing
    the exception gets a one-line locator. Subclass of ValueError so
    pytest.raises(ValueError) catches it.
    """
    def __init__(self, path: pathlib.Path | str, key_path: str, message: str):
        self.path = pathlib.Path(path)
        self.key_path = key_path
        self.message = message
        super().__init__(f"{self.path}: {self.key_path}: {self.message}")


_REQUIRED_TOP_LEVEL = frozenset((
    "n", "t_max", "seeds", "network",
    "adversary", "protocol_knobs", "workload",
))


def load_config(path: str | pathlib.Path) -> Config:
    """Load and fully validate a YAML config file. Returns a frozen Config.

    Raises ConfigError on any malformed input.
    """
    path = pathlib.Path(path)

    # --- 4.1 Parse -----------------------------------------------------
    try:
        with open(path, "r") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(path, "<root>",
                          f"YAML parse failed: {e}") from None
    if not isinstance(raw, dict):
        raise ConfigError(path, "<root>",
                          f"top level must be a mapping, got "
                          f"{type(raw).__name__}")

    # --- 4.2 Required-key check ----------------------------------------
    keys = set(raw)
    missing = _REQUIRED_TOP_LEVEL - keys
    if missing:
        # Stable error: name the alphabetically-first missing key.
        first = sorted(missing)[0]
        raise ConfigError(path, first, "missing required top-level key")
    unknown = keys - _REQUIRED_TOP_LEVEL
    if unknown:
        first = sorted(unknown)[0]
        raise ConfigError(path, first, "unknown top-level key")

    # Seeds sub-keys.
    seeds_raw = raw["seeds"]
    if not isinstance(seeds_raw, dict):
        raise ConfigError(path, "seeds",
                          f"must be a mapping, got {type(seeds_raw).__name__}")
    if "n_runs" not in seeds_raw:
        raise ConfigError(path, "seeds.n_runs",
                          "missing required key")
    extra_seeds = set(seeds_raw) - {"n_runs"}
    if extra_seeds:
        first = sorted(extra_seeds)[0]
        raise ConfigError(path, f"seeds.{first}", "unknown key")

    # Network sub-keys.
    network_raw = raw["network"]
    if not isinstance(network_raw, dict):
        raise ConfigError(path, "network",
                          f"must be a mapping, got "
                          f"{type(network_raw).__name__}")
    if "phases" not in network_raw:
        raise ConfigError(path, "network.phases",
                          "missing required key")
    extra_net = set(network_raw) - {"phases"}
    if extra_net:
        first = sorted(extra_net)[0]
        raise ConfigError(path, f"network.{first}", "unknown key")

    # Each phase entry requires t_start, t_end, delay.
    phases_raw = network_raw["phases"]
    if not isinstance(phases_raw, list):
        raise ConfigError(path, "network.phases",
                          f"must be a list, got {type(phases_raw).__name__}")
    for i, ph in enumerate(phases_raw):
        if not isinstance(ph, dict):
            raise ConfigError(path, f"network.phases[{i}]",
                              f"must be a mapping, got {type(ph).__name__}")
        for req in ("t_start", "t_end", "delay"):
            if req not in ph:
                raise ConfigError(path,
                                  f"network.phases[{i}].{req}",
                                  "missing required key")
        # delay sub-keys.
        dly = ph["delay"]
        if not isinstance(dly, dict):
            raise ConfigError(path,
                              f"network.phases[{i}].delay",
                              f"must be a mapping, got "
                              f"{type(dly).__name__}")
        for req in ("kind", "params"):
            if req not in dly:
                raise ConfigError(path,
                                  f"network.phases[{i}].delay.{req}",
                                  "missing required key")

    # Opaque sections: must be dicts.
    for opaque in ("adversary", "protocol_knobs", "workload"):
        v = raw[opaque]
        if not isinstance(v, dict):
            raise ConfigError(path, opaque,
                              f"must be a mapping, got {type(v).__name__}")

    # Tasks 8 + 9 fill in:
    #   - 4.3 type coercion
    #   - 4.4 leaf construction (DelayDist / Partition / Phase / SeedsConfig)
    #   - 4.5 cross-field validation
    # For now, return a placeholder — this stub is overwritten in Task 8.
    raise NotImplementedError("Task 8 implements type coercion + leaf "
                              "construction; Task 9 the cross-field pass.")
```

**Step 5: Update `src/config/__init__.py`**

Replace `src/config/__init__.py` with:

```python
"""Reproducibility harness: YAML configs + seed control (T27).

Spec: docs/superpowers/specs/2026-05-20-t27-reproducibility-design.md
"""
from .loader import ConfigError, load_config
from .schema import Config, RunHandle, SeedsConfig

__all__ = ["Config", "ConfigError", "RunHandle", "SeedsConfig",
           "load_config"]
```

**Step 6: Run the tests to confirm the parse + required-key behaviour**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_loader -v`

Expected: **`TestRequiredKeys` and `TestErrorFormat` cases PASS** (they trigger errors before reaching the unfinished step 4.3 region). **`TestParse.test_canonical_minimal_yaml_loads` FAILS** with `NotImplementedError` — that is by design; Task 8 makes it pass. The other `TestParse` cases pass (their error paths still funnel before the placeholder raise).

Mark the canonical-load test as expected-fail with a comment pointing at Task 8, or simply leave the failure documented in the checkpoint summary — Task 8's first verification step is "this test now passes."

**Step 7: Checkpoint**

Stop. Human commits as `task 27: config loader — parse + required-key check`.

---

## Task 8: `load_config` — type coercion + leaf construction

Adds steps 4.3 (type coercion) and 4.4 (leaf construction: `DelayDist` / `Partition` / `Phase` / `SeedsConfig` / `Config`). At the end of this task the canonical-minimal-YAML test from Task 7 must pass.

**Files:**
- Modify: `src/config/loader.py` (replace the `NotImplementedError` block with the coercion + construction logic)
- Modify: `tests/config/test_loader.py` (add `TestCoercion` and `TestLeafConstructionErrors` classes)

**Step 1: Write the new failing tests**

Append to `tests/config/test_loader.py`:

```python
class TestCoercion(_LoaderTestBase):
    def test_t_max_string_is_coerced(self):
        body = MINIMAL_YAML.replace("t_max: 1000.0", 't_max: "1000"')
        path = write_yaml(self.tmp_path, body)
        cfg = load_config(path)
        self.assertEqual(cfg.t_max, 1000.0)
        self.assertIsInstance(cfg.t_max, float)

    def test_t_max_list_rejected(self):
        body = MINIMAL_YAML.replace("t_max: 1000.0", "t_max: [1000]")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("t_max", str(cm.exception))

    def test_n_int_coerced_from_string(self):
        body = MINIMAL_YAML.replace("n: 4", 'n: "4"')
        path = write_yaml(self.tmp_path, body)
        cfg = load_config(path)
        self.assertEqual(cfg.n, 4)
        self.assertIsInstance(cfg.n, int)

    def test_inf_t_end_loads(self):
        # YAML `.inf` parses as math.inf; the loader passes it through to
        # Phase, which accepts non-finite t_end only on the final phase
        # (validate_timeline enforces; the loader does not).
        path = write_yaml(self.tmp_path, MINIMAL_YAML)
        cfg = load_config(path)
        import math
        self.assertEqual(cfg.network[0].t_end, math.inf)


class TestLeafConstructionErrors(_LoaderTestBase):
    def test_unknown_delay_kind_surfaced(self):
        body = MINIMAL_YAML.replace("kind: constant", "kind: triangular")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("delay", str(cm.exception))
        self.assertIn("triangular", str(cm.exception))

    def test_constant_zero_delay_surfaced(self):
        body = MINIMAL_YAML.replace("delay: 50.0", "delay: 0")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("constant delay", str(cm.exception).lower())

    def test_opaque_sections_round_trip(self):
        body = MINIMAL_YAML.replace(
            "adversary: {}",
            "adversary: { strategy: delay-emission, fraction: 0.1 }",
        )
        path = write_yaml(self.tmp_path, body)
        cfg = load_config(path)
        # Opaque, but contents survive verbatim:
        self.assertEqual(cfg.adversary,
                         {"strategy": "delay-emission", "fraction": 0.1})
```

**Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_loader -v`

Expected: the new tests FAIL (NotImplementedError); the existing Task 7 tests still pass-or-not as documented.

**Step 3: Replace the placeholder in `src/config/loader.py`**

Edit `src/config/loader.py`. Remove the trailing `raise NotImplementedError(...)` and the comment above it, and append:

```python
    # --- 4.3 + 4.4 Type coercion + leaf construction --------------------
    try:
        n = int(raw["n"])
    except (TypeError, ValueError) as e:
        raise ConfigError(path, "n", f"must coerce to int: {e}") from None

    try:
        t_max = float(raw["t_max"])
    except (TypeError, ValueError) as e:
        raise ConfigError(path, "t_max",
                          f"must coerce to float: {e}") from None

    try:
        n_runs = int(seeds_raw["n_runs"])
    except (TypeError, ValueError) as e:
        raise ConfigError(path, "seeds.n_runs",
                          f"must coerce to int: {e}") from None
    seeds = SeedsConfig(n_runs=n_runs)

    phases: list[Phase] = []
    for i, ph_raw in enumerate(phases_raw):
        key_prefix = f"network.phases[{i}]"
        try:
            t_start = float(ph_raw["t_start"])
            t_end = float(ph_raw["t_end"])
        except (TypeError, ValueError) as e:
            raise ConfigError(path, f"{key_prefix}.t_start/t_end",
                              f"must coerce to float: {e}") from None

        # Build DelayDist (leaf __post_init__ does its own validation).
        dly_raw = ph_raw["delay"]
        if not isinstance(dly_raw["params"], dict):
            raise ConfigError(path, f"{key_prefix}.delay.params",
                              f"must be a mapping, got "
                              f"{type(dly_raw['params']).__name__}")
        try:
            delay = DelayDist(kind=str(dly_raw["kind"]),
                              params=dict(dly_raw["params"]))
        except ValueError as e:
            raise ConfigError(path, f"{key_prefix}.delay",
                              str(e)) from None

        # p_drop default 0.0; coerce if present.
        if "p_drop" in ph_raw:
            try:
                p_drop = float(ph_raw["p_drop"])
            except (TypeError, ValueError) as e:
                raise ConfigError(path, f"{key_prefix}.p_drop",
                                  f"must coerce to float: {e}") from None
        else:
            p_drop = 0.0

        # partitions default empty; build Partition leaves.
        partitions_raw = ph_raw.get("partitions", [])
        if not isinstance(partitions_raw, list):
            raise ConfigError(path, f"{key_prefix}.partitions",
                              f"must be a list, got "
                              f"{type(partitions_raw).__name__}")
        parts: list[Partition] = []
        for j, part_raw in enumerate(partitions_raw):
            ppref = f"{key_prefix}.partitions[{j}]"
            if not isinstance(part_raw, dict):
                raise ConfigError(path, ppref,
                                  f"must be a mapping, got "
                                  f"{type(part_raw).__name__}")
            if "groups" not in part_raw:
                raise ConfigError(path, f"{ppref}.groups",
                                  "missing required key")
            groups_raw = part_raw["groups"]
            if not isinstance(groups_raw, list):
                raise ConfigError(path, f"{ppref}.groups",
                                  f"must be a list, got "
                                  f"{type(groups_raw).__name__}")
            try:
                groups = tuple(tuple(int(nid) for nid in g) for g in groups_raw)
            except (TypeError, ValueError) as e:
                raise ConfigError(path, f"{ppref}.groups",
                                  f"NodeIds must be ints: {e}") from None
            sym = bool(part_raw.get("symmetric", True))
            parts.append(Partition(groups=groups, symmetric=sym))

        try:
            phases.append(Phase(t_start=t_start, t_end=t_end,
                                delay=delay, p_drop=p_drop,
                                partitions=tuple(parts)))
        except ValueError as e:
            raise ConfigError(path, key_prefix, str(e)) from None

    # Build Config (frozen — __post_init__ is none for now).
    config = Config(
        n=n,
        t_max=t_max,
        seeds=seeds,
        network=tuple(phases),
        adversary=dict(raw["adversary"]),
        protocol_knobs=dict(raw["protocol_knobs"]),
        workload=dict(raw["workload"]),
    )

    # Task 9 adds the cross-field validation pass before this return.
    return config
```

**Step 4: Run the loader suite**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_loader -v`

Expected: every test in `TestParse`, `TestRequiredKeys`, `TestErrorFormat`, `TestCoercion`, `TestLeafConstructionErrors` PASS. The canonical-minimal-YAML test from Task 7 now passes.

**Step 5: Run the full suite**

Run: `make test`

Expected: PASS.

**Step 6: Checkpoint**

Stop. Human commits as `task 27: config loader — type coercion + leaf construction`.

---

## Task 9: `load_config` — cross-field validation (step 4.5)

Adds the final pre-return validation pass: `n` bounds, `t_max` bounds, partition-NodeId-in-range.

**Files:**
- Modify: `src/config/loader.py` (insert `_validate_config(config, path)` and call it before `return config`)
- Modify: `tests/config/test_loader.py` (add `TestCrossField`)

**Step 1: Write the failing tests**

Append to `tests/config/test_loader.py`:

```python
class TestCrossField(_LoaderTestBase):
    def test_zero_n_rejected(self):
        body = MINIMAL_YAML.replace("n: 4", "n: 0")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("n", str(cm.exception))

    def test_huge_n_rejected(self):
        # The sanity ceiling is 10_000 (spec § 4.5).
        body = MINIMAL_YAML.replace("n: 4", "n: 100000")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_zero_t_max_rejected(self):
        body = MINIMAL_YAML.replace("t_max: 1000.0", "t_max: 0")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("t_max", str(cm.exception))

    def test_nan_t_max_rejected(self):
        body = MINIMAL_YAML.replace("t_max: 1000.0", "t_max: .nan")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("t_max", str(cm.exception))

    def test_zero_n_runs_rejected(self):
        body = MINIMAL_YAML.replace("n_runs: 1", "n_runs: 0")
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("n_runs", str(cm.exception))

    def test_partition_nodeid_out_of_range_rejected(self):
        # n = 4, so valid NodeIds are 0..3. NodeId 99 must be rejected.
        body = MINIMAL_YAML.replace(
            "partitions: []",
            "partitions:\n        - groups: [[0, 1], [99]]\n",
        )
        path = write_yaml(self.tmp_path, body)
        with self.assertRaises(ConfigError) as cm:
            load_config(path)
        self.assertIn("99", str(cm.exception))
```

**Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_loader.TestCrossField -v`

Expected: FAIL.

**Step 3: Add the cross-field validation pass**

Edit `src/config/loader.py`. At the bottom of the module, add:

```python
import math


def _validate_config(config: Config, path: pathlib.Path) -> None:
    """Step 4.5: cross-field checks.

    Raises ConfigError naming the first violation found.
    """
    if not (1 <= config.n <= 10_000):
        raise ConfigError(
            path, "n",
            f"must be in [1, 10000], got {config.n}")
    if not math.isfinite(config.t_max) or config.t_max <= 0:
        raise ConfigError(
            path, "t_max",
            f"must be a positive finite float, got {config.t_max}")
    if config.seeds.n_runs < 1:
        raise ConfigError(
            path, "seeds.n_runs",
            f"must be >= 1, got {config.seeds.n_runs}")

    valid_ids = set(range(config.n))
    for i, ph in enumerate(config.network):
        for j, part in enumerate(ph.partitions):
            for nid in (nid for g in part.groups for nid in g):
                if nid not in valid_ids:
                    raise ConfigError(
                        path,
                        f"network.phases[{i}].partitions[{j}]",
                        f"NodeId {nid} not in range(n)={config.n}")
```

In the `load_config` body, replace the final `return config` with:

```python
    _validate_config(config, path)
    return config
```

**Step 4: Run the loader suite**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_loader -v`

Expected: every test PASSES, including the six new `TestCrossField` cases.

**Step 5: Run the full suite**

Run: `make test`

Expected: PASS.

**Step 6: Checkpoint**

Stop. Human commits as `task 27: config loader — cross-field validation`.

---

## Task 10: `build_run` factory

The factory orchestrates the six-phase bootstrap, returns a `RunHandle`. Reuses the four boundary gates landed in Tasks 2–5.

**Files:**
- Create: `src/config/factory.py`
- Modify: `src/config/__init__.py` (re-export `build_run`, `NodeFactory`)
- Create: `tests/config/test_factory.py`
- Modify: `tests/config/_helpers.py` (add `MinimalNode`)

**Step 1: Add `MinimalNode` to the test helpers**

Append to `tests/config/_helpers.py`:

```python
from nodes import HaltReason, Message, Node


class MinimalNode(Node):
    """Concrete Node used by T27 factory + e2e tests. Tiny by design — its
    sole job is to produce observable events so the determinism contract
    can be exercised without binding to T28+ protocol semantics.

    Behaviour: on _on_start, broadcast a single "PING" carrying a random
    draw from self.rng. On _on_message, halt(RUN_END). _on_timer is
    defensive — never fired by this scenario.
    """

    def __init__(self, node_id, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)

    def _on_start(self, t):
        self.broadcast("PING", {"r": self.rng.random()}, t)

    def _on_message(self, msg, t):
        self.halt(HaltReason.RUN_END, t)

    def _on_timer(self, timer_id, payload, t):
        raise AssertionError("MinimalNode never sets a timer")
```

**Step 2: Write the failing tests**

Create `tests/config/test_factory.py`:

```python
"""Unit tests for src/config/factory.py — build_run."""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from config import RunHandle, build_run, load_config
from network import Network
from scheduler import Scheduler

from _helpers import MINIMAL_YAML, MinimalNode, write_yaml


class _FactoryTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self._tmp.name)
        self.path = write_yaml(self.tmp_path, MINIMAL_YAML)
        self.config = load_config(self.path)

    def tearDown(self):
        self._tmp.cleanup()


class TestReturn(_FactoryTestBase):
    def test_returns_run_handle(self):
        handle = build_run(self.config, global_seed=0,
                           node_factory=MinimalNode)
        self.assertIsInstance(handle, RunHandle)
        self.assertIsInstance(handle.scheduler, Scheduler)
        self.assertIsInstance(handle.network, Network)
        self.assertEqual(set(handle.nodes), {0, 1, 2, 3})

    def test_nodes_view_is_immutable(self):
        handle = build_run(self.config, global_seed=0,
                           node_factory=MinimalNode)
        with self.assertRaises(TypeError):
            handle.nodes[42] = object()        # type: ignore[index]


class TestFactoryContract(_FactoryTestBase):
    def test_node_factory_called_with_global_seed(self):
        seen: list[tuple[int, int]] = []

        def factory(nid, seed):
            seen.append((nid, seed))
            return MinimalNode(nid, seed)

        build_run(self.config, global_seed=99, node_factory=factory)
        self.assertEqual(seen,
                         [(0, 99), (1, 99), (2, 99), (3, 99)])

    def test_mismatched_node_id_fails_fast(self):
        def bad_factory(nid, seed):
            # Return a Node whose id differs from the requested nid.
            return MinimalNode(node_id=nid + 100, global_seed=seed)

        with self.assertRaises(AssertionError) as cm:
            build_run(self.config, global_seed=0, node_factory=bad_factory)
        self.assertIn("node.id", str(cm.exception).lower())


class TestBootstrapOrder(_FactoryTestBase):
    def test_network_started_before_any_node_started(self):
        # MinimalNode._on_start calls broadcast(), which raises if Network
        # is not started. The factory must therefore call Network.start
        # before any Node.start — proven by the construction succeeding
        # (a regression would raise "Network.submit_* called before start()").
        try:
            build_run(self.config, global_seed=0, node_factory=MinimalNode)
        except RuntimeError as e:
            self.fail(f"build_run raised {e!r}; "
                      "Network.start was not called before Node.start")

    def test_nodes_started_in_sorted_node_id_order(self):
        order: list[int] = []

        class OrderRecordingNode(MinimalNode):
            def _on_start(self, t):
                order.append(self.id)
                super()._on_start(t)

        build_run(self.config, global_seed=0,
                  node_factory=OrderRecordingNode)
        self.assertEqual(order, sorted(order))
        self.assertEqual(order, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
```

**Step 3: Run the tests to verify they fail**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_factory -v`

Expected: FAIL — `build_run` does not exist.

**Step 4: Implement the factory**

Create `src/config/factory.py`:

```python
"""Six-phase bootstrap from a Config + global_seed (T27 spec § 5).

build_run() composes Scheduler + Network + Nodes in the canonical order
pinned by simulation-design.md (the wiki six-phase bootstrap) and by spec
§ 5. Returns a RunHandle. The caller calls handle.scheduler.run() and
optionally wires handle.scheduler.event_sink before that.
"""
from __future__ import annotations

from types import MappingProxyType
from typing import Callable

from network import Network
from nodes import Node
from scheduler import Scheduler

from .schema import Config, RunHandle

NodeId = int
NodeFactory = Callable[[NodeId, int], Node]
#               (node_id, global_seed) -> Node


def build_run(config: Config,
              global_seed: int,
              node_factory: NodeFactory) -> RunHandle:
    """Construct one run from `config` and `global_seed`.

    Construction order (matches simulation-design.md six-phase bootstrap):
      1. Scheduler()
      2. Network(scheduler, config.network, global_seed)
      3. For each NodeId in range(config.n):
           node = node_factory(nid, global_seed)
           assert node.id == nid
           network.register(node); scheduler.bind(node); network.bind(node)
      4. scheduler.bind_network(network)
      5. network.start()
      6. For each NodeId in sorted order: node.start(t=0.0)

    Returns a RunHandle whose `nodes` field is an immutable mapping view.
    """
    # Phase 1: Scheduler.
    scheduler = Scheduler()

    # Phase 2: Network. _network_seed(global_seed) seeds net_rng inside.
    network = Network(scheduler, config.network, global_seed)

    # Phase 3: Nodes.
    nodes: dict[NodeId, Node] = {}
    for nid in range(config.n):
        node = node_factory(nid, global_seed)
        assert node.id == nid, (
            f"node_factory returned node.id={node.id} for requested nid={nid}"
        )
        network.register(node)
        scheduler.bind(node)
        network.bind(node)
        nodes[nid] = node

    # Phase 4: PhaseAdvance dispatch target.
    scheduler.bind_network(network)

    # Phase 5: Validate timeline and arm interior PhaseAdvance events.
    network.start()

    # Phase 6: Kick off Node._on_start in sorted NodeId order.
    for nid in sorted(nodes):
        nodes[nid].start(t=0.0)

    return RunHandle(scheduler=scheduler, network=network,
                     nodes=MappingProxyType(nodes))
```

**Step 5: Update `src/config/__init__.py`**

Replace `src/config/__init__.py` with:

```python
"""Reproducibility harness: YAML configs + seed control (T27).

Spec: docs/superpowers/specs/2026-05-20-t27-reproducibility-design.md
"""
from .factory import NodeFactory, build_run
from .loader import ConfigError, load_config
from .schema import Config, RunHandle, SeedsConfig

__all__ = [
    "Config", "ConfigError", "NodeFactory", "RunHandle", "SeedsConfig",
    "build_run", "load_config",
]
```

**Step 6: Run the tests to confirm everything passes**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_factory -v`

Expected: every test in `TestReturn`, `TestFactoryContract`, `TestBootstrapOrder` PASSES.

**Step 7: Run the full suite**

Run: `make test`

Expected: PASS.

**Step 8: Checkpoint**

Stop. Human commits as `task 27: build_run factory`.

---

## Task 11: E2E determinism tests

Three end-to-end tests asserting the central T27 contract: same `(YAML, global_seed)` → byte-identical `event_sink` stream.

**Files:**
- Create: `tests/config/test_e2e_determinism.py`

**Step 1: Write the failing tests**

Create `tests/config/test_e2e_determinism.py`:

```python
"""End-to-end determinism tests for T27.

Three claims, one test each:
  (a) Two builds with the same (YAML, global_seed) produce byte-identical
      event_sink capture streams.
  (b) Two builds with different global_seed values produce different
      capture streams — proving the seed actually flows.
  (c) Two load_config calls on the same file produce equal Configs —
      isolated check on the loader's own determinism.

The MinimalNode test fixture lives in tests/config/_helpers.py.
"""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from config import build_run, load_config

from _helpers import MINIMAL_YAML, MinimalNode, write_yaml


class _E2EBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self._tmp.name)
        self.path = write_yaml(self.tmp_path, MINIMAL_YAML)

    def tearDown(self):
        self._tmp.cleanup()

    def _capture_run(self, global_seed: int) -> list[tuple]:
        capture: list[tuple] = []
        config = load_config(self.path)
        handle = build_run(config, global_seed=global_seed,
                           node_factory=MinimalNode)
        handle.scheduler.event_sink = (
            lambda *args: capture.append(tuple(args)))
        handle.scheduler.run(t_max=config.t_max)
        return capture


class TestSameSeedByteIdentical(_E2EBase):
    def test_two_runs_byte_identical(self):
        cap_a = self._capture_run(global_seed=42)
        cap_b = self._capture_run(global_seed=42)
        self.assertEqual(cap_a, cap_b)
        self.assertGreater(len(cap_a), 0,
                           "capture should not be empty — MinimalNode "
                           "broadcasts on start, halts on first message")


class TestSeedDivergence(_E2EBase):
    def test_different_seeds_diverge(self):
        cap_a = self._capture_run(global_seed=42)
        cap_b = self._capture_run(global_seed=43)
        self.assertNotEqual(cap_a, cap_b,
                            "different global_seed must produce different "
                            "event streams — otherwise the seed is not "
                            "flowing through the random draws")


class TestLoadDeterminism(_E2EBase):
    def test_two_loads_equal(self):
        a = load_config(self.path)
        b = load_config(self.path)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests to verify they pass**

Run: `PYTHONPATH=src:tests/config python3 -m unittest tests.config.test_e2e_determinism -v`

Expected: all three tests PASS. This is the "same seed → same output" verification line from `TASKS.md` T27.

Note: this is a TDD pass-on-first-run because every upstream piece (Tasks 2–10) is already in place. If a test fails here, suspect a regression in one of:
  - Per-Node `_stable_seed` (Task 2 / `node-model.md` §8 Revision)
  - Per-Network `_network_seed` (`network-model-phases.md` §6.1 Revision)
  - Sorted iteration in broadcast (Task 3 / `network.py:117`)
  - Construction order in `build_run` (Task 10)

**Step 3: Run the full suite**

Run: `make test`

Expected: PASS.

**Step 4: Run coverage to check branch coverage on `src/config/*`**

Run: `make coverage`

Expected: the report shows `src/config/{schema.py, loader.py, factory.py}` with high coverage. Spot-check that loader.py's error paths are exercised — the per-required-key parameterised tests in `TestRequiredKeys.test_each_top_level_key_required` should cover most.

**Step 5: Checkpoint**

Stop. Human commits as `task 27: E2E determinism tests`.

---

## Task 12: `wiki/concepts/reproducibility.md` + index + log

The wiki artifact pinning the consolidation layer. Per `docs/wiki-spec.md`, every new wiki page goes in `wiki/index.md`, and every task appends a `wiki/log.md` entry.

**Files:**
- Create: `wiki/concepts/reproducibility.md`
- Modify: `wiki/index.md` (add one line under `## Concepts`)
- Modify: `wiki/log.md` (append one entry)

**Step 1: Write `wiki/concepts/reproducibility.md`**

Create `wiki/concepts/reproducibility.md`. Target length ≤ ~200 lines. Follow the W3 design-contract style (prose + tables + Revisions section); NO "reference sketch" section since the implementation already exists — pointers to source files instead.

Outline (matches spec § 7):

```markdown
# Reproducibility

Harness-level reproducibility contract for the thesis simulator. Pins the
end-to-end claim: same `(YAML config, global_seed)` produces a byte-identical
`event_sink` stream. Consolidates three per-component determinism contracts
already in place — [[concepts/node-model]] §8, [[concepts/network-model-phases]]
§6, [[concepts/simulation-design-runtime]] §1 — and adds the harness layer
(`src/config/`) that injects `global_seed` and constructs configurations
from YAML.

## 1. Framing

Three claims:
- (a) Same YAML file → same `Config` (deterministic load).
- (b) Same `Config` + same `global_seed` → same `RunHandle` behaviour.
- (c) Captured `event_sink` stream end-to-end is byte-identical under (a) ∧ (b).

[Two-paragraph framing on why reproducibility matters for the thesis: the
central artifact is comparative numbers across four protocols; if a run is
not byte-identical for the same input, every reported metric inherits the
hidden noise and no cross-protocol verdict is defensible. The contract is
strict (byte-identical, not "statistically equivalent") because the cost
is small — `blake2b` seeds + sorted iteration — and the value is high.]

## 2. The three pre-existing contracts

| Contract | Source | Test | Commits to |
| :-- | :-- | :-- | :-- |
| Per-Node RNG seeding via stable hash | `src/nodes/node.py:19, 51`; [[concepts/node-model]] §8 | `tests/nodes/test_node.py::TestRng` | identical `Node.rng` streams across processes |
| Per-Network RNG seeding via stable hash | `src/network/network.py:16, 40`; [[concepts/network-model-phases]] §6 | `tests/network/test_network.py` (delay-sampling determinism) | identical `net_rng` stream across processes |
| Scheduler heap ordering by `(t, node_id, seq)` | `src/scheduler/scheduler.py`; [[concepts/simulation-design-runtime]] §1 | `tests/scheduler/test_scheduler.py::TestOrdering` | unambiguous dispatch order at any `t` |

T27 adds the layer that drives `global_seed` into the first two contracts
and orchestrates the bootstrap in a fixed order.

## 3. The single seed surface

`global_seed: int` is the sole randomness input to the simulator. Two
derivations:

- `_stable_seed(global_seed, node_id)` → `Node.rng` (`src/nodes/node.py:19`),
  one per Node.
- `_network_seed(global_seed)` → `Network.net_rng`
  (`src/network/network.py:16`), one for the whole run.

Both derivations are `blake2b`-based, fixed-size, and process-stable —
Python's built-in `hash()` is randomised per process, which would break
byte-identical replay across machines. The scheduler holds no RNG.

`global_seed` is NOT in the YAML. The harness enumerates seeds externally
(see [[concepts/experiment-matrix]] §7 — common random numbers across
protocols).

## 4. Config materialization

`load_config(path) -> Config` is itself deterministic:
- YAML parsing is `yaml.safe_load` only — no Python-object tags.
- Required-key, type-coercion, leaf-construction, and cross-field checks
  run in a fixed sequence (`src/config/loader.py` § 4.1–4.5).
- `Config` is a frozen dataclass — post-load mutation raises
  `FrozenInstanceError`.
- The three opaque sections (`adversary`, `protocol_knobs`, `workload`)
  are round-tripped as `dict[str, Any]`; their insertion order matches
  PyYAML's parse order, which itself is document-order under
  `safe_load`.

## 5. `build_run` determinism

`build_run(config, global_seed, node_factory)` orchestrates the canonical
six-phase bootstrap with no randomness of its own (full sequence in
`src/config/factory.py:build_run`):

1. `Scheduler()` — no RNG.
2. `Network(scheduler, config.network, global_seed)` — seeds `net_rng`.
3. For `nid in range(config.n)`: `node_factory(nid, global_seed)`;
   `network.register(node)`; `scheduler.bind(node)`; `network.bind(node)`.
4. `scheduler.bind_network(network)`.
5. `network.start()` — runs `validate_timeline`, arms phase-advance.
6. For `nid in sorted(nodes)`: `nodes[nid].start(t=0.0)`.

The factory consumes no global state. `random.seed()`, `os.urandom`,
`time.time()` are not called. Iteration is `range(n)` (already sorted)
and `sorted(nodes)`.

## 6. Forbidden surfaces

Inside `src/config/`:
- `yaml.load` with any unsafe loader. `safe_load` only.
- `random.seed()`, `random.random()` at module scope.
- `os.urandom`, `secrets.*` for any randomness.
- `time.time()`, `time.monotonic()`, or any wallclock read.
- Iteration over unordered containers (raw `set`, `dict.keys()` without
  `sorted`) where the iteration order is observable in the event stream.

These are greppable invariants — a `grep -nE` of the listed APIs across
`src/config/` should produce zero hits.

## 7. Test surface

| Test | Asserts |
| :-- | :-- |
| `tests/config/test_e2e_determinism.py::TestSameSeedByteIdentical` | Two `build_run` invocations with the same `(YAML, global_seed)` produce byte-identical `event_sink` capture streams. |
| `tests/config/test_e2e_determinism.py::TestSeedDivergence` | Different `global_seed` values produce different capture streams — proves the seed actually flows through per-Node RNG draws. |
| `tests/config/test_e2e_determinism.py::TestLoadDeterminism` | Two `load_config` calls on the same file produce equal `Config`s. |
| Per-component contracts | Each upstream test from § 2 above. |

## 8. Open to revision

- **Cross-process replay tested only on CPython.** The `blake2b`-based
  seed derivations are process-stable by construction, but the e2e test
  runs in a single Python process. If the thesis adds a distributed
  harness (T41+), spawn a subprocess with the same `(YAML, global_seed)`
  and `diff` the captured streams.
- **Thread-safety contract is single-threaded.** The simulator is
  intentionally single-threaded; the determinism contract does not extend
  to a multi-threaded harness. T41+ if multi-threading lands.
- **Opaque-section preservation depends on dict insertion order.** Python
  3.7+ preserves dict insertion order; PyYAML `safe_load` returns dicts
  in document order. If PyYAML's parse order changes, the byte view of
  `Config.adversary` could differ — irrelevant today because the loader
  does not introspect these.

## 9. Sources

Design contract; no primary-literature citations.

**Inbound:**
- [[concepts/node-model]] §8 — per-Node RNG seeding contract.
- [[concepts/network-model-phases]] §6 — network-scoped RNG and sampling
  order.
- [[concepts/simulation-design-runtime]] §1 — scheduler determinism
  mechanisms.
- [[concepts/experiment-matrix]] §7 — seed enumeration policy and
  common-random-numbers across protocols.

**Source files:**
- `src/config/schema.py`, `src/config/loader.py`, `src/config/factory.py`
- `src/nodes/node.py:19` (`_stable_seed`)
- `src/network/network.py:16` (`_network_seed`)

## 10. Revisions

None.
```

(The bracketed paragraph in § 1 is to be expanded with the framing prose the executing agent writes at file-creation time; treat the rest of the page as final.)

**Step 2: Update `wiki/index.md`**

Find the `## Concepts` section. Add the new line, keeping the section alphabetical-ish by topic adjacency (place it just after `[[concepts/simulation-design-runtime]]` so the three pre-existing-contract pages plus reproducibility cluster):

```markdown
- [[concepts/reproducibility]] — Harness-level reproducibility contract: same `(YAML config, global_seed)` → byte-identical event stream. Consolidates the three per-component determinism contracts (node-model §8, network-model-phases §6, simulation-design-runtime §1); pins the `src/config/` package (loader + factory) and the four "Watch for T27" boundary-seam fail-fast gates.
```

**Step 3: Append a `wiki/log.md` entry**

Per `docs/wiki-spec.md` § Log format:

```markdown
## [2026-05-20] code | task 27 — Reproducibility: seed control + YAML configs
- role: Engineer
- touched: src/config/{__init__,schema,loader,factory}.py, src/nodes/node.py, src/network/network.py, src/scheduler/scheduler.py, tests/config/*, wiki/concepts/reproducibility.md, wiki/index.md, requirements.txt
- notes: Landed src/config/ — YAML loader, Config dataclass with opaque sections for the un-wired adversary / protocol / workload axes, and the six-phase build_run factory taking a node_factory supplied by the caller. Four boundary-seam fail-fast gates added at the offended boundaries (Node.__init__ rejects negative node_id and non-finite weight; Network.register / Scheduler.bind reject duplicates; Network.start is idempotent). PyYAML pinned as the simulator's first non-stdlib runtime dependency. E2E determinism test asserts byte-identical event_sink streams across two same-seed builds.
```

**Step 4: Verify no broken wikilinks**

Open `wiki/concepts/reproducibility.md`, `wiki/index.md`, and visit each `[[...]]` link's target file to confirm it exists:

```bash
ls wiki/concepts/node-model.md wiki/concepts/network-model-phases.md \
   wiki/concepts/simulation-design-runtime.md wiki/concepts/experiment-matrix.md
```

Expected: all four exist.

**Step 5: Run the full test suite one final time**

Run: `make test`

Expected: PASS — no wiki edit affects code.

**Step 6: Checkpoint**

Stop. Human reviews `wiki/concepts/reproducibility.md` for prose quality and commits as `task 27: reproducibility.md + index + log`.

---

## Plan complete

Twelve tasks, structured for TDD execution by `superpowers:executing-plans`.

**Implementation order:** 1 (PyYAML) → 2–5 (four boundary gates, any order) → 6 (config scaffold) → 7–9 (loader, sequential) → 10 (factory) → 11 (e2e) → 12 (wiki).

**Verification gates between tasks:**
- After Tasks 2–5: `make test` passes (the four gates do not break anything upstream).
- After Task 6: `make test-config` exists and passes; `make test` still passes.
- After Task 10: `make test-config` passes incl. factory tests.
- After Task 11: e2e determinism asserts the central T27 contract.
- After Task 12: wiki page exists, index updated, log entry appended.

**Final verification (before flipping T27 to In Review):**
1. `make test` — all suites pass.
2. `make coverage` — `src/config/{schema,loader,factory}.py` covered with no obvious dead branches.
3. `grep -nE "random\.seed|os\.urandom|time\.time|yaml\.load[^_]" src/config/` — empty (forbidden-surface check).
4. `wiki/concepts/reproducibility.md` exists, ≤ 250 lines, linked from `wiki/index.md`, `wiki/log.md` has the T27 entry.
5. `docs/superpowers/specs/2026-05-20-t27-reproducibility-{design,plan}.md` both committed.

**Out of scope** (deferred per spec § 9): protocol-specific Nodes (T28+); adversary attachment binding (post-T18); workload generation (T41+); CLI entry point (T41); sample YAML files in `configs/`; multi-process / cross-machine determinism tests.
