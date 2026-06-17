# T51 — Delayed-voters adversary + Family C delay-emission sweep — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bootstrap the simulator's adversary-injection subsystem (the first fill of the opaque `Node.adversary` slot) and run the Week-10 Family C `delay-emission` experiment — a fraction of validators hold every outbound emission by a fixed multiple of their protocol's round cadence — measuring time-to-finality impact across PBFT, Casper FFG, and Snowman at n ∈ {10, 25}.

**Architecture:** A new `src/adversary/` package attaches the delay capability by **re-wrapping a slow node's bound outbound API after `build_run`** — it does NOT edit the network, scheduler, or any protocol FSM (the honest network must stay honest, [[concepts/network-model]] §6). Each slow node's `send`/`broadcast` is wrapped to shift the `t_sent` argument forward by a fixed `m·ref` seconds; because the multiplier is fixed, the shift is a deterministic constant and consumes no adversary RNG. The sweep reuses the T46.1 resumable/parallel `run_grid_tiered`, the T46 `clip_records`, and the T40 reducers verbatim; only scheduling and the new package are added.

**Tech Stack:** Python 3 stdlib only (`dataclasses`, `hashlib`, `multiprocessing`, `csv`, `argparse`), `matplotlib` for plots (already a dependency), `unittest` for tests. No new third-party dependencies.

---

## Background the engineer must know

This codebase is a discrete-event consensus simulator. Read these before starting:

- **The bind seam.** `config.factory.build_run(config, seed, make)` constructs Scheduler + Network + Nodes and returns a `RunHandle` with `.scheduler`, `.network`, `.nodes` (an immutable `MappingProxyType[int, Node]`). During construction, `Network.bind(node)` sets:
  ```python
  node.send      = lambda dst, type, payload, t: self.submit_unicast(node.id, dst, type, payload, t)
  node.broadcast = lambda type, payload, t:      self.submit_broadcast(node.id, type, payload, t)
  ```
  So a bound `send` takes `(dst, type, payload, t)` and a bound `broadcast` takes `(type, payload, t)`. The `t` argument flows through as `t_sent`, and the network schedules delivery at `t_sent + delay`. **Shifting `t` forward delays delivery — this is the entire mechanism.**
- **The honest run sequence** (see `src/delay/runners.py` lines 133-151):
  ```python
  handle = build_run(config, seed, make)        # honest nodes; Network.bind done
  result, logger = run_to_completion(handle, t_max=...)
  return logger.records, result, meta
  ```
  T51 inserts `inject_delay(handle, slow_ids, m, ref)` **between** these two lines.
- **`Node.adversary`** (`src/nodes/node.py:61`) is an `Optional[AdversaryProfile]` slot, currently always `None`. T51 fills it with a `DelayProfile`.
- **The sweep driver.** `common.run_grid_tiered(cells, run_cell, cell_key, *, checkpoint_dir, run_constants, param_fingerprint, is_heavy, jobs, heavy_jobs, fresh, progress_stream)` partitions cells by `is_heavy(cell)`, runs the light tier at `jobs` then the heavy tier at `heavy_jobs`, and returns rows sorted by `cell_key`. **Every function crossing the process boundary (`run_cell`, `cell_key`, `param_fingerprint`) must be module-level; every `cell` a plain picklable tuple — no closures, no NaN-in-tuple.** Study `src/delay/heavy.py` — it is the closest precedent and T51's sweep mirrors it almost exactly.
- **The clip.** `delay.clip.clip_records(records, window_s, one_round_s)` returns `(kept_records, ClipStats)`. `ClipStats.clipped_fraction` is the calibration guard. Reuse unchanged.
- **The reducers.** `pbft.summarise.summarise`, `pos.summarise.summarise`, `snowman.summarise.summarise` each take `(records, result, meta)` and return a dict of metric columns including `commit_latency_ms` (the cross-protocol-comparable latency, [[concepts/output-format]] §13). `output.csv._generic_cols(records, result, meta, commit_hash=...)` produces the identity/workload columns; `_format_row` / `_resolve_commit_hash` are the CSV helpers.
- **The static-baseline network.** Family C fixes the network at a constant low delay. The honest baselines use `DelayDist("constant", {"delay": 1e-9})`; Family C uses a realistic-but-fast constant 10 ms: `DelayDist("constant", {"delay": 0.01})`. `DelayDist` kinds are validated in `src/network/phases.py`; `"constant"` requires param `"delay" > 0`.
- **Determinism contract.** Same `(config, seed)` → byte-identical event log. The delay wrap only shifts `t_sent` by a constant and draws no RNG, so determinism is preserved (spec §8). An `f=0` cell (empty slow set) is byte-identical to a plain honest static-baseline run — this is the validity anchor for the `finality_delay_ratio` denominator.
- **auggie is unavailable** in this environment. The Engineer role mandates `mcp__auggie__codebase-retrieval` pre/post edit; substitute Grep/Glob and log each query + result in the experiment page's **Auggie verification** section (precedent: the T41 page). This is the proof-of-verification artifact.

Design spec (approved 2026-06-15): `docs/superpowers/specs/2026-06-14-t51-delayed-voters-design.md`.

---

## File structure

**New package `src/adversary/`:**
- `src/adversary/__init__.py` — package marker + public exports (`DelayProfile`, `inject_delay`, `slow_node_ids`).
- `src/adversary/profiles.py` — `DelayProfile` frozen dataclass (fills `Node.adversary`).
- `src/adversary/select.py` — `slow_node_ids(n, f)` = highest-id `⌊f·n⌋` nodes.
- `src/adversary/inject.py` — `inject_delay(handle, slow_ids, mult, ref)` = the post-build wrap.
- `src/adversary/config.py` — Family C constants: static-baseline timeline, `N_VALUES`, `F_VALUES`, `M_VALUES`, `SEEDS`, per-protocol cadence refs, window/buffer calibration, PBFT `vc_delay`.
- `src/adversary/runners.py` — `run_{pbft,ffg,snowman}(n, f, m, seed)` + `RUNNERS` dispatch table.
- `src/adversary/sweep.py` — the orchestrator: grid, cell_key, fingerprint, `_run_cell`, `_build_row`, Family-C columns, `_finality_delay_ratios` post-pass, `write_csv`, probe, preflight, CLI.

**New plots module:**
- `src/output/adversary_plots.py` — the dose-response figures (mirrors `src/output/delay_plots.py` STYLE).

**New tests `tests/adversary/`:**
- `tests/adversary/__init__.py`
- `tests/adversary/test_profiles.py`
- `tests/adversary/test_select.py`
- `tests/adversary/test_inject.py`
- `tests/adversary/test_config.py`
- `tests/adversary/test_runners.py` (small e2e + monotone sanity)
- `tests/adversary/test_determinism.py`
- `tests/adversary/test_sweep.py`

**Modified:**
- `Makefile:15` — add `adversary` to `SUITES` so `make test` runs the new suite.

**Wiki (Task 12):** new `wiki/experiments/2026-06-14_delayed-voters.md`; Revisions on `adversary-model`, `adversary-model-runtime`, `node-model`, `experiment-matrix`, `experiment-matrix-runs`; `wiki/index.md` + `wiki/log.md`; `TASKS.md` matrix budget amendment + status flip.

---

## Task 1: Package scaffolding + Makefile wiring

**Files:**
- Create: `src/adversary/__init__.py`
- Create: `tests/adversary/__init__.py`
- Modify: `Makefile:15`

- [ ] **Step 1: Create the package marker with public exports**

Create `src/adversary/__init__.py`:

```python
"""Adversary-injection subsystem (T51).

The first fill of the opaque ``Node.adversary`` slot. Attaches an adversary
capability by re-wrapping a node's bound outbound API AFTER ``build_run`` --
the honest network/scheduler/FSMs are never edited (network-model.md §6).

T51 lands the ``delay-emission`` capability (slow voters). T52 (withhold) and
T53 (equivocate) extend this package.

Design spec: docs/superpowers/specs/2026-06-14-t51-delayed-voters-design.md
"""
from __future__ import annotations

from .inject import inject_delay
from .profiles import DelayProfile
from .select import slow_node_ids

__all__ = ["DelayProfile", "inject_delay", "slow_node_ids"]
```

- [ ] **Step 2: Create the test package marker**

Create `tests/adversary/__init__.py`:

```python
```

(Empty file — it only marks the directory as a package for `unittest discover`.)

- [ ] **Step 3: Add the suite to the Makefile**

In `Makefile`, change line 15 from:

```make
SUITES        = scheduler nodes network event_log config common pbft pos snowman output workload delay integration
```

to (insert `adversary` immediately after `delay`):

```make
SUITES        = scheduler nodes network event_log config common pbft pos snowman output workload delay adversary integration
```

- [ ] **Step 4: Verify the suite is discovered (and currently empty-passes)**

Run: `make test-adversary`
Expected: discovery runs against `tests/adversary`, reports `Ran 0 tests` and `OK` (the package imports fail until later tasks add modules — but step 1's `__init__` imports modules that don't exist yet, so first add a temporary guard).

Because `src/adversary/__init__.py` imports `inject`, `profiles`, `select` which don't exist yet, `make test-adversary` will raise `ModuleNotFoundError` at import. That is expected at this point — the next tasks create those modules. Do **not** add stub files to silence it; just proceed to Task 2. (If you prefer a green checkpoint here, run `make test-config` to confirm the Makefile edit didn't break the existing suites.)

Run: `make test-config`
Expected: PASS (proves the `SUITES` edit is well-formed).

- [ ] **Step 5: Commit**

```bash
git add src/adversary/__init__.py tests/adversary/__init__.py Makefile
git commit -m "task 51: scaffold src/adversary package + Makefile suite"
```

---

## Task 2: `DelayProfile` (fills the `Node.adversary` slot)

**Files:**
- Create: `src/adversary/profiles.py`
- Test: `tests/adversary/test_profiles.py`

- [ ] **Step 1: Write the failing test**

Create `tests/adversary/test_profiles.py`:

```python
"""DelayProfile shape + immutability (T51)."""
from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from adversary.profiles import DelayProfile


class TestDelayProfile(unittest.TestCase):
    def test_fields(self):
        p = DelayProfile(nodes=(8, 9), intensity=0.20, mult=5.0)
        self.assertEqual(p.nodes, (8, 9))
        self.assertEqual(p.intensity, 0.20)
        self.assertEqual(p.mult, 5.0)
        self.assertEqual(p.kind, "delay-emission")

    def test_is_frozen(self):
        p = DelayProfile(nodes=(), intensity=0.0, mult=0.0)
        with self.assertRaises(FrozenInstanceError):
            p.intensity = 0.5            # type: ignore[misc]

    def test_kind_is_fixed_default(self):
        # kind is not a constructor argument the caller varies; it identifies
        # the capability for the (future) adversary dispatch.
        p = DelayProfile(nodes=(9,), intensity=0.1, mult=2.0)
        self.assertEqual(p.kind, "delay-emission")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-adversary`
Expected: FAIL with `ModuleNotFoundError: No module named 'adversary.profiles'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/adversary/profiles.py`:

```python
"""Adversary strategy profiles (T51).

``DelayProfile`` is the first concrete fill of the opaque ``Node.adversary``
slot (node-model.md §9). It mirrors the adversary-model-runtime.md §4
``DelayProfile`` reference sketch, trimmed to exactly what the
``delay-emission`` capability needs: the slow-node set, the nominal intensity
(fraction f), and the fixed delay multiple (m). ``kind`` tags the capability.

Stored on the node for observability/provenance; the actual late-emission
behaviour is realised by ``adversary.inject.inject_delay`` (the bind-seam
wrap), not by the FSM reading this object (spec §3.2 / the node-model.md §9
Revision).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DelayProfile:
    """The ``delay-emission`` adversary profile for one run.

    - ``nodes``     -- the slow-node ids (highest-id ⌊f·n⌋; select.py).
    - ``intensity`` -- nominal fraction f of slow nodes.
    - ``mult``      -- m, the fixed delay multiple of the protocol round
                       cadence applied to every outbound emission.
    - ``kind``      -- capability tag ("delay-emission").
    """
    nodes: tuple[int, ...]
    intensity: float
    mult: float
    kind: str = "delay-emission"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `make test-adversary`
Expected: PASS (3 tests in `test_profiles`).

- [ ] **Step 5: Commit**

```bash
git add src/adversary/profiles.py tests/adversary/test_profiles.py
git commit -m "task 51: DelayProfile (fills Node.adversary slot)"
```

---

## Task 3: `slow_node_ids` (slow-node selection)

**Files:**
- Create: `src/adversary/select.py`
- Test: `tests/adversary/test_select.py`

Rationale (spec §3.3): the slow set is the **highest-id `⌊f·n⌋`** nodes. PBFT's view-0 primary is node 0, so highest-id selection keeps the attack on backups (delayed votes), not the leader — keeping this `delay-emission`, not `disrupt-leader`.

- [ ] **Step 1: Write the failing test**

Create `tests/adversary/test_select.py`:

```python
"""slow_node_ids: highest-id ⌊f·n⌋ selection (T51, spec §3.3)."""
from __future__ import annotations

import unittest

from adversary.select import slow_node_ids


class TestSlowNodeIds(unittest.TestCase):
    def test_floor_count_n10(self):
        # n=10: f=0.10 -> 1, f=0.20 -> 2, f=0.30 -> 3.
        self.assertEqual(slow_node_ids(10, 0.10), (9,))
        self.assertEqual(slow_node_ids(10, 0.20), (8, 9))
        self.assertEqual(slow_node_ids(10, 0.30), (7, 8, 9))

    def test_floor_count_n25(self):
        # n=25: f=0.10 -> 2 (floor 2.5), f=0.20 -> 5, f=0.30 -> 7 (floor 7.5).
        self.assertEqual(slow_node_ids(25, 0.10), (23, 24))
        self.assertEqual(slow_node_ids(25, 0.20), (20, 21, 22, 23, 24))
        self.assertEqual(slow_node_ids(25, 0.30), (18, 19, 20, 21, 22, 23, 24))

    def test_zero_fraction_is_empty(self):
        self.assertEqual(slow_node_ids(10, 0.0), ())
        self.assertEqual(slow_node_ids(25, 0.0), ())

    def test_excludes_primary_for_all_f_below_one(self):
        # Node 0 (PBFT view-0 primary) must never be slow while f < 1.
        for n in (10, 25):
            for f in (0.10, 0.20, 0.30):
                self.assertNotIn(0, slow_node_ids(n, f),
                                 msg=f"n={n} f={f}")

    def test_returns_sorted_ascending(self):
        ids = slow_node_ids(25, 0.30)
        self.assertEqual(list(ids), sorted(ids))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-adversary`
Expected: FAIL with `ModuleNotFoundError: No module named 'adversary.select'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/adversary/select.py`:

```python
"""Slow-node selection for the delay-emission adversary (T51, spec §3.3).

The slow set is the highest-id ⌊f·n⌋ nodes. PBFT's view-0 primary is node 0,
so selecting from the top keeps the attack on backups (delayed PREPARE/COMMIT
votes), not the leader -- this is delay-emission, not disrupt-leader. Snowman
is leaderless and Casper FFG rotates its proposer by slot, so the occasional
proposer overlap in FFG is reported (spec §3.3), not engineered away.
"""
from __future__ import annotations

import math


def slow_node_ids(n: int, f: float) -> tuple[int, ...]:
    """Return the ⌊f·n⌋ highest node ids, ascending. Empty when f == 0.

    For every f < 1 the count is < n, so node 0 (the PBFT primary) is never
    included -- the invariant the experiment relies on.
    """
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"f must be in [0, 1], got {f}")
    k = math.floor(f * n)
    if k <= 0:
        return ()
    return tuple(range(n - k, n))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `make test-adversary`
Expected: PASS (`test_profiles` + `test_select`).

- [ ] **Step 5: Commit**

```bash
git add src/adversary/select.py tests/adversary/test_select.py
git commit -m "task 51: slow_node_ids highest-id floor selection"
```

---

## Task 4: `inject_delay` (the bind-seam wrap — the heart of the subsystem)

**Files:**
- Create: `src/adversary/inject.py`
- Test: `tests/adversary/test_inject.py`

The wrap captures each slow node's honest bound `send`/`broadcast`, and replaces them with versions that shift the `t` argument forward by `shift = mult·ref`. It must avoid the Python closure late-binding trap (use a factory function, not a loop-body lambda). It is a **no-op when `slow_ids` is empty** (the f=0 control path).

- [ ] **Step 1: Write the failing test**

Create `tests/adversary/test_inject.py`:

```python
"""inject_delay: the post-build outbound-API wrap (T51, spec §3.1).

Unit-tested against stub nodes (no full simulator run): inject_delay only
touches handle.nodes[*].send / .broadcast / .adversary, so a SimpleNamespace
handle with recording stub nodes exercises the wrap in isolation.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from adversary.inject import inject_delay
from adversary.profiles import DelayProfile


def _stub_node(node_id: int):
    """A node whose send/broadcast record (args) into .sent / .bcast."""
    node = SimpleNamespace(id=node_id, adversary=None, sent=[], bcast=[])
    node.send = lambda dst, type, payload, t, _n=node: _n.sent.append(
        (dst, type, payload, t))
    node.broadcast = lambda type, payload, t, _n=node: _n.bcast.append(
        (type, payload, t))
    return node


def _stub_handle(n: int):
    nodes = {i: _stub_node(i) for i in range(n)}
    return SimpleNamespace(nodes=nodes), nodes


class TestInjectDelay(unittest.TestCase):
    def test_slow_node_send_shifted(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(3,), mult=5.0, ref=1.0)   # shift = 5.0
        nodes[3].send(dst=0, type="VOTE", payload=b"x", t=2.0)
        # delivered as if emitted at t + 5.0 = 7.0
        self.assertEqual(nodes[3].sent, [(0, "VOTE", b"x", 7.0)])

    def test_slow_node_broadcast_shifted(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(3,), mult=2.0, ref=1.0)   # shift = 2.0
        nodes[3].broadcast(type="PREPARE", payload=b"p", t=10.0)
        self.assertEqual(nodes[3].bcast, [("PREPARE", b"p", 12.0)])

    def test_non_slow_nodes_untouched(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(3,), mult=5.0, ref=1.0)
        nodes[0].send(dst=1, type="VOTE", payload=b"y", t=2.0)
        nodes[0].broadcast(type="PRE", payload=b"q", t=3.0)
        # honest node 0: no shift.
        self.assertEqual(nodes[0].sent, [(1, "VOTE", b"y", 2.0)])
        self.assertEqual(nodes[0].bcast, [("PRE", b"q", 3.0)])

    def test_empty_slow_set_is_noop(self):
        handle, nodes = _stub_handle(4)
        before_send = {i: nodes[i].send for i in range(4)}
        before_bcast = {i: nodes[i].broadcast for i in range(4)}
        inject_delay(handle, slow_ids=(), mult=5.0, ref=1.0)
        # identity unchanged: no wrapping happened.
        for i in range(4):
            self.assertIs(nodes[i].send, before_send[i])
            self.assertIs(nodes[i].broadcast, before_bcast[i])
            self.assertIsNone(nodes[i].adversary)

    def test_multiple_slow_nodes_independent_shift(self):
        # Closure-correctness: each wrapped node keeps ITS OWN honest fn +
        # shift, not the last loop iteration's.
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(2, 3), mult=3.0, ref=1.0)  # shift = 3.0
        nodes[2].send(dst=0, type="V", payload=b"a", t=1.0)
        nodes[3].send(dst=0, type="V", payload=b"b", t=1.0)
        self.assertEqual(nodes[2].sent, [(0, "V", b"a", 4.0)])
        self.assertEqual(nodes[3].sent, [(0, "V", b"b", 4.0)])

    def test_adversary_profile_recorded(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(2, 3), mult=5.0, ref=1.0)
        for i in (2, 3):
            self.assertIsInstance(nodes[i].adversary, DelayProfile)
            self.assertEqual(nodes[i].adversary.nodes, (2, 3))
            self.assertEqual(nodes[i].adversary.mult, 5.0)
        self.assertIsNone(nodes[0].adversary)
        self.assertIsNone(nodes[1].adversary)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-adversary`
Expected: FAIL with `ModuleNotFoundError: No module named 'adversary.inject'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/adversary/inject.py`:

```python
"""The delay-emission injection seam (T51, spec §3.1).

``inject_delay`` re-wraps each slow node's honest bound ``send`` / ``broadcast``
(set by ``Network.bind`` during ``build_run``) so that every outbound emission
is delivered ``mult·ref`` seconds late. The honest network adds its normal
delivery delay on top. Because ``mult`` is FIXED, the shift is a deterministic
constant -- no adversary RNG is consumed, so each slow node's protocol RNG
stream is byte-identical to honest; the node is only *late* (spec §8).

This realises the node-model.md §9 ``delayer`` cell (gate ``broadcast`` /
``send``). Intercepting at the bound outbound API is behaviourally identical to
FSM-level dispatch for delay -- which neither changes payloads nor drops/forks
messages -- and far less invasive (spec §3.2 / the node-model.md §9 Revision).
T52/T53 will need deeper FSM hooks; T51 does not.

Empty ``slow_ids`` is a strict no-op: the f=0 control is byte-identical to a
plain honest static-baseline run (the finality_delay_ratio denominator anchor).
"""
from __future__ import annotations

from config.schema import RunHandle

from .profiles import DelayProfile


def _delayed_send(honest_send, shift):
    """A send that shifts t_sent forward by `shift` (factory avoids the
    closure late-binding trap in the inject loop)."""
    def send(dst, type, payload, t):
        honest_send(dst, type, payload, t + shift)
    return send


def _delayed_broadcast(honest_broadcast, shift):
    """A broadcast that shifts t_sent forward by `shift`."""
    def broadcast(type, payload, t):
        honest_broadcast(type, payload, t + shift)
    return broadcast


def inject_delay(handle: RunHandle, slow_ids: tuple[int, ...],
                 mult: float, ref: float) -> None:
    """Re-wrap the slow nodes' outbound API to emit `mult·ref` s late.

    Call AFTER ``build_run`` and BEFORE ``run_to_completion``. Mutates the
    nodes in place. A no-op when ``slow_ids`` is empty.

    - ``handle``   -- the RunHandle from build_run (honest, fully bound).
    - ``slow_ids`` -- the slow-node ids (from ``select.slow_node_ids``).
    - ``mult``     -- m, the delay multiple.
    - ``ref``      -- the protocol round cadence in seconds (shift = mult·ref).
    """
    if not slow_ids:
        return
    shift = mult * ref
    profile = DelayProfile(nodes=tuple(slow_ids), intensity=0.0, mult=mult)
    # intensity is recorded by the runner via the profile it builds; here we
    # only need the slow set + mult for provenance. (The runner overwrites
    # nothing -- it passes the realized fraction into the CSV separately.)
    for nid in slow_ids:
        node = handle.nodes[nid]
        node.adversary = profile
        node.send = _delayed_send(node.send, shift)
        node.broadcast = _delayed_broadcast(node.broadcast, shift)
```

Note on `intensity`: `inject_delay` does not know `f` (it only receives the slow-id set), so the `DelayProfile.intensity` stored on the node is `0.0` as a placeholder; the realized fraction is reported into the CSV by the sweep (`slow_node_count` / `byzantine_fraction` columns, Task 6). The profile on the node is provenance only — nothing reads `intensity` back. If you prefer the stored profile to carry the true `f`, thread `f` through `inject_delay` as an extra arg; the spec keeps the seam minimal, so this plan does not.

- [ ] **Step 4: Run test to verify it passes**

Run: `make test-adversary`
Expected: PASS (`test_profiles` + `test_select` + `test_inject`, 6 tests in `test_inject`).

- [ ] **Step 5: Commit**

```bash
git add src/adversary/inject.py tests/adversary/test_inject.py
git commit -m "task 51: inject_delay bind-seam wrap (delay-emission)"
```

---

## Task 5: Family C configuration (`config.py`)

**Files:**
- Create: `src/adversary/config.py`
- Test: `tests/adversary/test_config.py`

This pins the Family C fixed axes and the (probe-set) calibration. The window/buffer/`vc_delay` values here are **placeholders to be confirmed by the probe in Task 9** — they are typed in now so the runners/sweep compile and the smoke tests run; Task 9 edits these three constants after reading the probe output.

- [ ] **Step 1: Write the failing test**

Create `tests/adversary/test_config.py`:

```python
"""Family C config: axes, static-baseline timeline, cadence refs (T51)."""
from __future__ import annotations

import math
import unittest

from adversary import config as cfg


class TestAxes(unittest.TestCase):
    def test_n_values(self):
        self.assertEqual(cfg.N_VALUES, (10, 25))

    def test_f_values_include_zero_control(self):
        self.assertEqual(cfg.F_VALUES, (0.0, 0.10, 0.20, 0.30))

    def test_m_values(self):
        self.assertEqual(cfg.M_VALUES, (2.0, 5.0, 10.0))

    def test_seeds(self):
        self.assertEqual(cfg.SEEDS, tuple(range(20)))


class TestStaticBaseline(unittest.TestCase):
    def test_single_phase_constant_10ms(self):
        phases = cfg.STATIC_BASELINE.phases()
        self.assertEqual(len(phases), 1)
        ph = phases[0]
        self.assertEqual(ph.t_start, 0.0)
        self.assertTrue(math.isinf(ph.t_end))
        self.assertEqual(ph.delay.kind, "constant")
        self.assertAlmostEqual(ph.delay.params["delay"], 0.01)
        self.assertEqual(ph.p_drop, 0.0)


class TestCadenceRefs(unittest.TestCase):
    def test_refs_per_protocol(self):
        self.assertAlmostEqual(cfg.REF_S["pbft"], 1.0)
        self.assertAlmostEqual(cfg.REF_S["snowman"], 1.0)
        self.assertAlmostEqual(cfg.REF_S["casper-ffg"], 0.1)

    def test_ffg_slot_satisfies_coherence(self):
        # static-baseline E[delay] = 10 ms; slot >= 4·E[delay] = 40 ms.
        self.assertGreaterEqual(cfg.FFG_SLOT_DURATION_S, 4 * 0.01)


class TestCalibration(unittest.TestCase):
    def test_horizon_is_window_plus_buffer(self):
        self.assertAlmostEqual(cfg.T_MAX, cfg.WINDOW_S + cfg.BUFFER_S)

    def test_one_round_keys(self):
        self.assertEqual(set(cfg.ONE_ROUND_S),
                         {"pbft", "casper-ffg", "snowman"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-adversary`
Expected: FAIL with `ModuleNotFoundError: No module named 'adversary.config'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/adversary/config.py`:

```python
"""Family C delay-emission (delayed-voters) configuration (T51).

Family C fixes the network at a constant low delay (the "static-baseline"
timeline) and sweeps the ADVERSARY axes: intensity f (fraction of slow nodes)
and magnitude m (the fixed delay multiple of each protocol's round cadence).
All delay values are SECONDS of simulator model time (the unit the baselines
use: slot_duration = 1.0 s ⇒ commit_latency ≈ 1000 ms).

The WINDOW_S / BUFFER_S / PBFT_VC_DELAY_S constants are PROBE-SET: Task 9's
`sweep.py --probe` prints first-decision latency, clip fraction, and PBFT
view-change count, after which these three are finalised. The values below are
the pre-probe defaults; the experiment page records the confirmed numbers.

Design contract: docs/superpowers/specs/2026-06-14-t51-delayed-voters-design.md
                 wiki/experiments/2026-06-14_delayed-voters.md
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from network import DelayDist, Phase

# --- Swept adversary axes (human 2026-06-14). ----------------------------
# f = 0.00 is the honest CONTROL (0 slow nodes, no magnitude). m applies only
# to f > 0 cells. n=10 → {0,1,2,3} slow; n=25 → {0,2,5,7} slow (floor).
N_VALUES: tuple[int, ...] = (10, 25)
F_VALUES: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)
M_VALUES: tuple[float, ...] = (2.0, 5.0, 10.0)
SEEDS: tuple[int, ...] = tuple(range(20))

# --- Per-protocol round cadence ref (shift = m·ref). ---------------------
# PBFT propose cadence and Snowman slot cadence are the native 1.0 s. Casper
# FFG's slot is 0.1 s (default); static-baseline E[delay]=10 ms satisfies the
# §5 coherence rule slot ≥ 4·E[delay] = 40 ms. The FFG cadence asymmetry
# (shorter ref ⇒ smaller absolute shift) is a real finding, reported (spec §5).
REF_S: dict[str, float] = {
    "pbft":       1.0,
    "snowman":    1.0,
    "casper-ffg": 0.1,
}

# --- Per-protocol protocol knobs. ----------------------------------------
PBFT_PROPOSE_DELAY_S: float = 1.0
SNOWMAN_SLOT_DURATION_S: float = 1.0
SNOWMAN_BETA: int = 15
FFG_SLOT_DURATION_S: float = 0.1
FFG_SLOTS_PER_EPOCH: int = 2

# --- Window / buffer / view-change calibration (PROBE-SET; Task 9). ------
# Family C runs on the fast static-baseline (10 ms delay), so the window is
# far shorter than the Family B delay sweeps. WINDOW_S must hold ≥ 25
# in-window-started decisions for every protocol with clip < 5 %; the worst
# attack cell (m=10) holds emissions by up to 10·ref = 10 s (PBFT/Snowman),
# so the buffer must clear one such delayed round. Confirm via --probe.
WINDOW_S: float = 120.0
BUFFER_S: float = 24.0
T_MAX: float = WINDOW_S + BUFFER_S

# PBFT view-change timeout: realistic (≈ 3× honest round) so a slow backup that
# pushes a vote past it trips an OBSERVABLE view-change (the §3 invariant),
# while honest (f=0) cells never rotate. Probe-confirmed (view_change_count
# = 0 at f=0, > 0 under attack at large m). PROBE-SET.
PBFT_VC_DELAY_S: float = 3.0

# Per-protocol one-round latency (the "started in [0,W]" scope bound for the
# clip). PROBE-SET from the worst-magnitude probe cell.
ONE_ROUND_S: dict[str, float] = {
    "pbft":       12.0,
    "casper-ffg": 4.0,
    "snowman":   12.0,
}

# --- Workload axis (experiment-matrix §6 committed defaults). ------------
ARRIVAL_PROCESS: str = "poisson"
OFFERED_RATE: float = 100.0
TX_BYTES: int = 512
CONFLICT_RATE: float = 0.0


@dataclass(frozen=True)
class Timeline:
    """The single fixed Family C network timeline (one network_phase_id).

    Mirrors delay.config.Timeline's surface (`name`, `e_delay_s`,
    `ffg_slot_duration_s`, `phases()`) so the runners read it identically.
    """
    name: str
    delay: DelayDist
    e_delay_s: float
    ffg_slot_duration_s: float

    def phases(self) -> tuple[Phase, ...]:
        return (Phase(0.0, math.inf, self.delay),)


# The Family C fixed network: constant 10 ms delivery delay, loss-free.
STATIC_BASELINE: Timeline = Timeline(
    name="static-baseline",
    delay=DelayDist("constant", {"delay": 0.01}),
    e_delay_s=0.01,
    ffg_slot_duration_s=FFG_SLOT_DURATION_S,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `make test-adversary`
Expected: PASS (`test_config` added).

- [ ] **Step 5: Commit**

```bash
git add src/adversary/config.py tests/adversary/test_config.py
git commit -m "task 51: Family C config + static-baseline timeline"
```

---

## Task 6: Per-protocol runners (`runners.py`)

**Files:**
- Create: `src/adversary/runners.py`
- Test: `tests/adversary/test_runners.py`

Each `run_<proto>(n, f, m, seed)` builds the honest run on the static-baseline timeline (mirroring `src/delay/runners.py`), then applies `inject_delay` on the slow set, then runs to completion. Returns the `(records, result, meta)` triple the reducers consume.

- [ ] **Step 1: Write the failing test**

Create `tests/adversary/test_runners.py`:

```python
"""Per-protocol Family C runners: run success + monotone delay sanity (T51)."""
from __future__ import annotations

import unittest

from adversary import config as cfg
from adversary.runners import RUNNERS


def _decided(records):
    return [r for r in records if r.event_type == "decided"]


def _first_latency_ms(records):
    """First decided event's commit time, ms (a coarse cross-run proxy)."""
    dec = _decided(records)
    return min(r.t for r in dec) * 1000.0 if dec else float("nan")


class TestRunSuccess(unittest.TestCase):
    def test_every_protocol_control_finalizes(self):
        # f=0 control at small n finalizes for every protocol.
        for proto, runner in RUNNERS.items():
            records, result, meta = runner(n=7, f=0.0, m=0.0, seed=0)
            self.assertTrue(_decided(records), msg=f"{proto} produced no decisions")
            self.assertEqual(meta.protocol, proto)


class TestMonotoneSanity(unittest.TestCase):
    def test_slow_voters_do_not_speed_up_finality(self):
        # A delay-emission attack cell finalizes no EARLIER than its f=0
        # control at the same (n, seed). (Latency inflates or holds; never
        # improves.) Uses the largest magnitude for a clear signal.
        for proto, runner in RUNNERS.items():
            ctrl, _, _ = runner(n=7, f=0.0, m=0.0, seed=1)
            atk, _, _ = runner(n=7, f=0.30, m=10.0, seed=1)
            c = _first_latency_ms(ctrl)
            a = _first_latency_ms(atk)
            self.assertGreaterEqual(
                a + 1e-6, c,
                msg=f"{proto}: attack {a:.3f}ms < control {c:.3f}ms")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-adversary`
Expected: FAIL with `ModuleNotFoundError: No module named 'adversary.runners'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/adversary/runners.py`:

```python
"""Per-protocol run builders for the Family C delay-emission sweep (T51).

Each ``run_<proto>(n, f, m, seed)`` mirrors the honest baseline factory
(src/{pbft,pos,snowman}/baseline.py) on the Family C static-baseline timeline,
then applies the delay-emission adversary: the highest-id ⌊f·n⌋ nodes hold every
outbound emission by ``m·ref`` seconds (``adversary.inject.inject_delay``). The
f=0 control applies no wrap (byte-identical to honest static-baseline).

Same ``RunTriple`` shape and ``meta`` discipline as src/delay/runners.py:
``meta.t_max`` is the measurement WINDOW (the reducers' throughput denominator),
while the scheduler runs to the full ``T_MAX = WINDOW_S + BUFFER_S`` horizon.

No shared infrastructure is modified -- the adversary attaches entirely at the
Node outbound API, post-build (spec §3.2).

Design contract: wiki/experiments/2026-06-14_delayed-voters.md
"""
from __future__ import annotations

import math

from common import run_to_completion
from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult
from workload import WorkloadConfig, generate_batches

from pbft import PBFTNode
from pos.node import CasperNode
from snowman import SnowmanNode

from . import config as cfg
from .inject import inject_delay
from .select import slow_node_ids

RunTriple = tuple[list[EventRecord], RunResult, ScenarioMeta]


def _config(n: int) -> Config:
    """One Config point on the static-baseline timeline, horizon T_MAX."""
    return Config(
        n=n,
        t_max=cfg.T_MAX,
        seeds=SeedsConfig(n_runs=1),
        network=cfg.STATIC_BASELINE.phases(),
        adversary={},
        protocol_knobs={},
        workload={},
    )


def _batches(seed: int, interval: float):
    """Deterministic batch stream covering the full horizon plus margin."""
    n_opportunities = math.ceil(cfg.T_MAX / interval) + 2
    return generate_batches(
        WorkloadConfig(cfg.ARRIVAL_PROCESS, cfg.OFFERED_RATE,
                       cfg.TX_BYTES, cfg.CONFLICT_RATE),
        seed, n_opportunities=n_opportunities, interval=interval,
    )


def _meta(protocol: str, run_id: str, n: int, seed: int,
          interval: float, slots_per_epoch: int | None) -> ScenarioMeta:
    """ScenarioMeta with t_max = WINDOW_S (the measurement window)."""
    return ScenarioMeta(
        run_id=run_id, protocol=protocol, n=n, variant=None, seed=seed,
        t_max=cfg.WINDOW_S,
        arrival_process=cfg.ARRIVAL_PROCESS, tx_bytes=cfg.TX_BYTES,
        conflict_rate=cfg.CONFLICT_RATE, offered_rate=cfg.OFFERED_RATE,
        interval=interval, slots_per_epoch=slots_per_epoch,
    )


# --- PBFT ---------------------------------------------------------------

def run_pbft(n: int, f: float, m: float, seed: int) -> RunTriple:
    propose = cfg.PBFT_PROPOSE_DELAY_S
    batches = [b"".join(b) for b in _batches(seed, propose)]

    def make(node_id: int, global_seed: int) -> PBFTNode:
        workload = batches if node_id == 0 else None
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n, workload=workload,
                        propose_delay=propose, initial_view=0,
                        vc_delay=cfg.PBFT_VC_DELAY_S)

    meta = _meta("pbft", f"pbft-n{n}", n, seed, propose, None)
    handle = build_run(_config(n), seed, make)
    inject_delay(handle, slow_node_ids(n, f), m, cfg.REF_S["pbft"], f)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# --- Casper FFG ---------------------------------------------------------

def run_ffg(n: int, f: float, m: float, seed: int) -> RunTriple:
    slot = cfg.FFG_SLOT_DURATION_S
    spe = cfg.FFG_SLOTS_PER_EPOCH
    stake = {i: 3.0 for i in range(n)}
    batches = [b for b in _batches(seed, slot)]

    def make(node_id: int, global_seed: int) -> CasperNode:
        return CasperNode(node_id=node_id, weight=stake[node_id],
                          endpoint=None, global_seed=global_seed, n=n,
                          stake_table=stake, slot_duration=slot,
                          slots_per_epoch=spe, workload=batches)

    meta = _meta("casper-ffg", f"casper-ffg-n{n}", n, seed, slot, spe)
    handle = build_run(_config(n), seed, make)
    inject_delay(handle, slow_node_ids(n, f), m, cfg.REF_S["casper-ffg"], f)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# --- Snowman ------------------------------------------------------------

def run_snowman(n: int, f: float, m: float, seed: int) -> RunTriple:
    slot = cfg.SNOWMAN_SLOT_DURATION_S
    batches = [b for b in _batches(seed, slot)]

    def make(node_id: int, global_seed: int) -> SnowmanNode:
        return SnowmanNode(node_id=node_id, weight=1.0, endpoint=None,
                           global_seed=global_seed, n=n, slot_duration=slot,
                           beta=cfg.SNOWMAN_BETA, workload=batches)

    meta = _meta("snowman", f"snowman-n{n}", n, seed, slot, None)
    handle = build_run(_config(n), seed, make)
    inject_delay(handle, slow_node_ids(n, f), m, cfg.REF_S["snowman"], f)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# Dispatch table: protocol_id -> run builder.
RUNNERS = {
    "pbft":       run_pbft,
    "casper-ffg": run_ffg,
    "snowman":    run_snowman,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `make test-adversary`
Expected: PASS. (If a protocol's control does not finalize within the placeholder `WINDOW_S`, this surfaces here — adjust `WINDOW_S` upward in `config.py`; Task 9's probe finalises it. The monotone test should hold regardless.)

- [ ] **Step 5: Commit**

```bash
git add src/adversary/runners.py tests/adversary/test_runners.py
git commit -m "task 51: Family C per-protocol runners + inject"
```

---

## Task 7: Determinism tests (the §8 contract)

**Files:**
- Test: `tests/adversary/test_determinism.py`

No new source — this task asserts the determinism contract on the existing runners: same `(n,f,m,seed)` → byte-identical records, and `f=0 ≡ honest static-baseline`.

- [ ] **Step 1: Write the failing test**

Create `tests/adversary/test_determinism.py`:

```python
"""Determinism contract for the delay-emission runners (T51, spec §8)."""
from __future__ import annotations

import unittest

from adversary.runners import RUNNERS


def _key(records):
    """A hashable, comparable projection of the event stream."""
    return [(r.t, r.event_type,
             tuple(sorted((k, repr(v)) for k, v in r.fields.items())))
            for r in records]


class TestDeterminism(unittest.TestCase):
    def test_attack_cell_byte_identical_rerun(self):
        # Same (n,f,m,seed) twice -> identical event stream (fixed shift
        # consumes no RNG; spec §8).
        for proto, runner in RUNNERS.items():
            a, _, _ = runner(n=7, f=0.30, m=10.0, seed=3)
            b, _, _ = runner(n=7, f=0.30, m=10.0, seed=3)
            self.assertEqual(_key(a), _key(b), msg=proto)

    def test_f0_equals_honest_static_baseline(self):
        # The f=0 control is byte-identical to a run with m varied: since
        # slow_ids is empty for f=0, inject_delay is a no-op regardless of m.
        for proto, runner in RUNNERS.items():
            a, _, _ = runner(n=7, f=0.0, m=2.0, seed=4)
            b, _, _ = runner(n=7, f=0.0, m=10.0, seed=4)
            self.assertEqual(_key(a), _key(b),
                             msg=f"{proto}: f=0 must ignore m")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails (or passes immediately)**

Run: `make test-adversary`
Expected: PASS (the runners from Task 6 already satisfy this). If it FAILS on `test_attack_cell_byte_identical_rerun`, the wrap is leaking RNG or capturing a closure variable wrong — revisit Task 4. If `test_f0_equals_honest_static_baseline` fails, `inject_delay` is not a strict no-op for empty `slow_ids` — revisit Task 4 step 3.

This is a TDD checkpoint that confirms the §8 contract holds across the runner layer; it has no separate "implement" step because the contract is a property of code already written.

- [ ] **Step 3: Commit**

```bash
git add tests/adversary/test_determinism.py
git commit -m "task 51: determinism contract tests (fixed-shift, f=0≡honest)"
```

---

## Task 8: Sweep orchestrator (`sweep.py`)

**Files:**
- Create: `src/adversary/sweep.py`
- Test: `tests/adversary/test_sweep.py`

The orchestrator mirrors `src/delay/heavy.py`: a grid of plain tuples driven through `run_grid_tiered`, with module-level `_run_cell` / `_cell_key` / `_param_fingerprint`, a `_build_row` projecting the T40 columns + a Family-C annotation block, a post-grid `_finality_delay_ratios` pass, `write_csv`, a `--probe`, a preflight estimate, and a CLI.

The cell tuple is `(proto, n, f, m, seed)`. The control is `(proto, n, 0.0, 0.0, seed)`; attack cells carry `f ∈ {0.10,0.20,0.30}`, `m ∈ {2,5,10}`. No NaN in the tuple (NaN breaks fingerprint repr-equality and dict identity) — control uses `m=0.0` and is recognised by `f == 0.0`.

- [ ] **Step 1: Write the failing test**

Create `tests/adversary/test_sweep.py`:

```python
"""Family C sweep: cell grid, jobs-equivalence, ratio post-pass (T51)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adversary import sweep
from adversary import config as cfg


class TestGrid(unittest.TestCase):
    def test_cells_per_proto_n_seed(self):
        # 1 control (f=0) + 3 f × 3 m attack = 10 cells per (proto, n, seed).
        cells = sweep._build_cells((0,))
        per = [c for c in cells if c[0] == "pbft" and c[1] == 10 and c[4] == 0]
        self.assertEqual(len(per), 10)
        controls = [c for c in per if c[2] == 0.0]
        self.assertEqual(len(controls), 1)
        self.assertEqual(controls[0][3], 0.0)            # control m == 0.0

    def test_cell_key_stable_and_safe(self):
        k = sweep._cell_key(("snowman", 25, 0.10, 5.0, 7))
        self.assertNotIn("/", k)
        self.assertNotIn(" ", k)
        # deterministic: same cell -> same key.
        self.assertEqual(k, sweep._cell_key(("snowman", 25, 0.10, 5.0, 7)))

    def test_distinct_cells_distinct_fingerprints(self):
        a = sweep._param_fingerprint(("pbft", 10, 0.10, 2.0, 0))
        b = sweep._param_fingerprint(("pbft", 10, 0.10, 5.0, 0))
        c = sweep._param_fingerprint(("pbft", 10, 0.20, 2.0, 0))
        self.assertNotEqual(a, b)        # m differs
        self.assertNotEqual(a, c)        # f differs


class TestFinalityRatioPostPass(unittest.TestCase):
    def test_control_is_one_attacks_are_ratio(self):
        rows = [
            {"protocol": "pbft", "n": 10, "seed": 0, "byzantine_fraction": 0.0,
             "delay_mult": 0.0, "commit_latency_ms": 100.0},
            {"protocol": "pbft", "n": 10, "seed": 0, "byzantine_fraction": 0.20,
             "delay_mult": 5.0, "commit_latency_ms": 250.0},
        ]
        sweep._finality_delay_ratios(rows)
        self.assertEqual(rows[0]["finality_delay_ratio"], 1.0)
        self.assertAlmostEqual(rows[1]["finality_delay_ratio"], 2.5)

    def test_nan_when_control_absent_or_zero(self):
        import math
        rows = [
            {"protocol": "snowman", "n": 25, "seed": 9,
             "byzantine_fraction": 0.30, "delay_mult": 10.0,
             "commit_latency_ms": 5000.0},   # no control sibling in this set
        ]
        sweep._finality_delay_ratios(rows)
        self.assertTrue(math.isnan(rows[0]["finality_delay_ratio"]))


class TestJobsEquivalence(unittest.TestCase):
    def test_jobs1_equals_jobs2_smoke(self):
        # 1-seed smoke grid byte-identical across jobs=1 and jobs=2.
        with tempfile.TemporaryDirectory() as d:
            out1 = Path(d) / "a.csv"
            out2 = Path(d) / "b.csv"
            rows1, _ = sweep.run_sweep(seeds=(0,), out=out1, jobs=1, fresh=True)
            sweep.write_csv(rows1, out1)
            rows2, _ = sweep.run_sweep(seeds=(0,), out=out2, jobs=2, fresh=True)
            sweep.write_csv(rows2, out2)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-adversary`
Expected: FAIL with `ModuleNotFoundError: No module named 'adversary.sweep'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/adversary/sweep.py`:

```python
"""Family C delay-emission (delayed-voters) sweep orchestrator (T51).

Drives protocols × N_VALUES × (1 control + F×M attack cells) × seeds through
the resumable/parallel memory-aware ``common.run_grid_tiered`` (the Snowman
n=25 class runs at ``--heavy-jobs``, default 1), applies the T46 window/buffer
clip, runs the T40 reducers, and writes one results/adversary/delayed_voters.csv.

The per-cell pipeline mirrors src/delay/heavy.py:

    run_<proto>(n, f, m, seed)            # full W+buffer horizon, slow voters
        -> clip_records(records, W, one_round)
        -> reducer(kept, ...)             # the existing T40 reducer
        -> row + Family-C annotation columns

The headline ``finality_delay_ratio`` is filled by a POST-grid pass (mirroring
heavy.py::_finalization_rates), so each ``_run_cell`` stays a pure per-cell
function -- the property the T46.1 induction relies on.

Run from repo root:
    PYTHONPATH=src python3 -m adversary.sweep                 # full sweep
    PYTHONPATH=src python3 -m adversary.sweep --smoke         # 1 seed sanity
    PYTHONPATH=src python3 -m adversary.sweep --probe         # calibration only
    PYTHONPATH=src python3 -m adversary.sweep --jobs 8 --heavy-jobs 1

Design contract: wiki/experiments/2026-06-14_delayed-voters.md
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

from common import run_grid_tiered
from common.sweep import estimate_runtime
from event_log import EventRecord
from output.csv import _generic_cols, _format_row, _resolve_commit_hash
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult

from pbft import PBFT_VIEW_CHANGE
from pbft.summarise import summarise as _pbft_summarise
from pos.summarise import summarise as _pos_summarise
from snowman.summarise import summarise as _snowman_summarise

from delay.clip import clip_records
from delay.sweep import _window_denominator_fix

from . import config as cfg
from .runners import RUNNERS


_OUT = Path("results/adversary/delayed_voters.csv")

_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}

_PROTOCOLS: tuple[str, ...] = ("pbft", "casper-ffg", "snowman")

# Family-C annotation columns appended after the 18-column T40 projection.
_ADV_COLUMNS: tuple[str, ...] = (
    "adversary_strategy",     # "delay-emission" (or "none" for f=0)
    "byzantine_fraction",     # nominal f
    "slow_node_count",        # realized ⌊f·n⌋
    "delay_mult",             # m (0.0 for the f=0 control)
    "view_change_count",      # PBFT view-changes in [0, W] (0 for FFG/Snowman)
    "clipped_fraction",       # tail past W / in-scope (reported)
    "run_horizon_s",          # W + buffer
    "finality_delay_ratio",   # headline (post-pass)
)

_ALL_COLUMNS = list(COLUMN_ORDER) + list(_ADV_COLUMNS)

# A control cell is identified by f == 0.0 (m is 0.0 and ignored there).
_CONTROL_F = 0.0


def _strategy(f: float) -> str:
    return "none" if f == _CONTROL_F else "delay-emission"


def _build_row(records: list[EventRecord], result: RunResult,
               meta: ScenarioMeta, n: int, f: float, m: float,
               clipped_fraction: float, commit_hash: str) -> dict[str, object]:
    """Project one clipped run to a CSV row: T40 generic + reducer columns,
    plus the Family-C annotation block. finality_delay_ratio is NaN here and
    filled by the post-grid pass."""
    import math

    row = _generic_cols(records, result, meta, commit_hash=commit_hash)
    row.update(_REDUCERS[meta.protocol](records, result, meta))
    _window_denominator_fix(row, records, meta)

    view_changes = sum(1 for r in records
                       if r.event_type == PBFT_VIEW_CHANGE)
    slow_count = math.floor(f * n)
    row["adversary_strategy"] = _strategy(f)
    row["byzantine_fraction"] = f
    row["slow_node_count"] = slow_count
    row["delay_mult"] = m
    row["view_change_count"] = view_changes
    row["clipped_fraction"] = clipped_fraction
    row["run_horizon_s"] = cfg.T_MAX
    row["finality_delay_ratio"] = float("nan")     # post-pass fills this
    return row


# --- Driver adapter (module-level for the `spawn` Pool). -----------------

_SCHEMA_TAG = (tuple(COLUMN_ORDER), _ADV_COLUMNS)


def _cell_key(cell: tuple) -> str:
    """Stable, total-order, filesystem-safe identity (filename + sort key)."""
    proto, n, f, m, seed = cell
    return (f"{proto}__n{n}__f{f:.2f}__m{m:04.1f}__seed{seed:02d}")


def _phase_canon(ph) -> tuple:
    return (ph.t_start, ph.t_end, ph.delay.kind,
            tuple(sorted(ph.delay.params.items())), ph.p_drop,
            repr(ph.partitions))


def _param_fingerprint(cell: tuple) -> str:
    """blake2b over the cell's canonicalized config: (proto, n, f, m, the
    static-baseline phase tuple, T_MAX, schema_tag). f and m both enter the
    hash, so every (f, m) point fingerprints distinctly. `seed` is the cell
    identity (in the filename), not a param, so it is excluded."""
    proto, n, f, m, seed = cell
    canon = repr((proto, n, f, m, cfg.STATIC_BASELINE.name,
                  tuple(_phase_canon(ph)
                        for ph in cfg.STATIC_BASELINE.phases()),
                  cfg.T_MAX, _SCHEMA_TAG))
    return hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()


def _run_cell(cell: tuple, run_constants: dict) -> dict[str, object]:
    """Pure per-cell row builder: runner -> clip -> _build_row. commit_hash is
    threaded in from run_constants (resolved once in the parent)."""
    proto, n, f, m, seed = cell
    records, result, meta = RUNNERS[proto](n, f, m, seed)
    kept, stats = clip_records(records, cfg.WINDOW_S, cfg.ONE_ROUND_S[proto])
    return _build_row(kept, result, meta, n, f, m,
                      stats.clipped_fraction, run_constants["commit_hash"])


def _finality_delay_ratios(rows: list[dict[str, object]]) -> None:
    """Fill each row's finality_delay_ratio IN PLACE (post-grid pass).

    Control (f=0) rows are 1.0 by definition. For an attack row, the ratio is
    commit_latency_ms(cell) / commit_latency_ms(control) at the same
    (protocol, n, seed); NaN if the control is absent from this collection or
    did not finalize (commit_latency_ms NaN or <= 0)."""
    import math

    control: dict[tuple, float] = {}
    for r in rows:
        if r["byzantine_fraction"] == _CONTROL_F:
            control[(r["protocol"], r["n"], r["seed"])] = r["commit_latency_ms"]
    for r in rows:
        if r["byzantine_fraction"] == _CONTROL_F:
            r["finality_delay_ratio"] = 1.0
            continue
        denom = control.get((r["protocol"], r["n"], r["seed"]))
        num = r["commit_latency_ms"]
        if (denom is None or not isinstance(denom, (int, float))
                or math.isnan(denom) or denom <= 0
                or not isinstance(num, (int, float)) or math.isnan(num)):
            r["finality_delay_ratio"] = float("nan")
        else:
            r["finality_delay_ratio"] = num / denom


def _is_heavy_cell(cell: tuple) -> bool:
    """The memory-heavy class: Snowman n>=25 (one cell materializes a large
    EventRecord stream; run it at --heavy-jobs, default 1). Mirrors
    delay.heavy._is_heavy_cell."""
    proto, n, _f, _m, _seed = cell
    return proto == "snowman" and int(n) >= 25


def _build_cells(seeds: tuple[int, ...]) -> list[tuple]:
    """The full cell list. Per (proto, n, seed): 1 control (f=0, m=0) + the
    F×M attack grid (f>0)."""
    attack_f = tuple(f for f in cfg.F_VALUES if f != _CONTROL_F)
    cells = []
    for p in _PROTOCOLS:
        for n in cfg.N_VALUES:
            for s in seeds:
                cells.append((p, n, _CONTROL_F, 0.0, s))      # control
                for f in attack_f:
                    for m in cfg.M_VALUES:
                        cells.append((p, n, f, m, s))
    return cells


def run_sweep(seeds: tuple[int, ...] | None = None, *,
              out: Path = _OUT, jobs: int = 1, heavy_jobs: int = 1,
              fresh: bool = False, progress_stream=None,
              ) -> tuple[list[dict[str, object]], float]:
    """Execute the Family C sweep via the memory-aware resumable/parallel
    driver. Returns (rows, worst_clipped_fraction); finality_delay_ratio is
    filled by the post-grid pass before return. Checkpoints live under
    <out_dir>/.sweep_adversary; commit_hash is resolved once in the parent."""
    seeds = cfg.SEEDS if seeds is None else seeds
    commit_hash = _resolve_commit_hash()
    cells = _build_cells(seeds)
    rows = run_grid_tiered(cells, _run_cell, _cell_key,
                           checkpoint_dir=Path(out).parent / ".sweep_adversary",
                           run_constants={"commit_hash": commit_hash},
                           param_fingerprint=_param_fingerprint,
                           is_heavy=_is_heavy_cell,
                           jobs=jobs, heavy_jobs=heavy_jobs,
                           fresh=fresh, progress_stream=progress_stream)
    _finality_delay_ratios(rows)
    worst = max((r["clipped_fraction"] for r in rows), default=0.0)
    return rows, worst


def write_csv(rows: list[dict[str, object]], path: Path = _OUT) -> None:
    """Write rows in COLUMN_ORDER + the Family-C columns, sorted by
    (protocol, n, byzantine_fraction, delay_mult, seed)."""
    rows = sorted(rows, key=lambda r: (r["protocol"], r["n"],
                                       r["byzantine_fraction"],
                                       r["delay_mult"], r["seed"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_ALL_COLUMNS,
                                extrasaction="raise")
        writer.writeheader()
        for row in rows:
            formatted = _format_row({k: row[k] for k in COLUMN_ORDER})
            formatted["adversary_strategy"] = str(row["adversary_strategy"])
            formatted["byzantine_fraction"] = f"{row['byzantine_fraction']:.6f}"
            formatted["slow_node_count"] = str(row["slow_node_count"])
            formatted["delay_mult"] = f"{row['delay_mult']:.6f}"
            formatted["view_change_count"] = str(row["view_change_count"])
            formatted["clipped_fraction"] = f"{row['clipped_fraction']:.6f}"
            formatted["run_horizon_s"] = f"{row['run_horizon_s']:.3f}"
            formatted["finality_delay_ratio"] = \
                f"{row['finality_delay_ratio']:.6f}"
            writer.writerow(formatted)


def _preflight_estimate(seeds: tuple[int, ...], jobs: int, stream) -> None:
    """Pre-flight wall-clock estimate: time one worst-magnitude cell per
    protocol at the smallest n, project to the full grid. Rough (smallest-n
    sample under-counts Snowman n=25); stderr only, never persisted."""
    commit_hash = _resolve_commit_hash()
    n0 = min(cfg.N_VALUES)
    m_max = max(cfg.M_VALUES)
    f_max = max(cfg.F_VALUES)
    samples = [(p, n0, f_max, m_max, seeds[0]) for p in _PROTOCOLS]
    timings = estimate_runtime(samples, _run_cell,
                               {"commit_hash": commit_hash})
    cells = _build_cells(seeds)
    total = 0.0
    for (proto, _, _, _, _), sec in timings.items():
        n_cells = sum(1 for c in cells if c[0] == proto)
        proj = n_cells * sec
        total += proj
        stream.write(f"[estimate] {proto}: ~{sec:.1f}s/cell (n={n0}, worst m) "
                     f"× {n_cells} cells ≈ {proj / 60:.1f} min "
                     f"(rough — Snowman n=25 is far costlier than n={n0})\n")
    eff = total / max(1, jobs)
    stream.write(f"[estimate] total ≈ {total / 60:.1f} min sequential, "
                 f"~{eff / 60:.1f} min at jobs={jobs} "
                 f"(rough, smallest-n sample, from scratch)\n")
    stream.flush()


def _probe(stream) -> None:
    """Calibration probe: one seed per (protocol, n=10) at the worst magnitude
    (m=max, slowest), printing first-decision latency, clip fraction, PBFT
    view-change count, and in-window finalizations, so WINDOW_S / BUFFER_S /
    ONE_ROUND_S / PBFT_VC_DELAY_S can be finalised before the full sweep
    commits. Does not write the dataset."""
    n0 = min(cfg.N_VALUES)
    m_max = max(cfg.M_VALUES)
    f_max = max(cfg.F_VALUES)
    stream.write(f"[probe] static-baseline, n={n0}, seed 0, worst attack "
                 f"(f={f_max}, m={m_max}); W={cfg.WINDOW_S:.0f}s, "
                 f"horizon={cfg.T_MAX:.0f}s:\n")
    for proto in _PROTOCOLS:
        records, result, meta = RUNNERS[proto](n0, f_max, m_max, 0)
        decided = [r for r in records if r.event_type == "decided"]
        first = min((r.t for r in decided), default=float("nan"))
        kept, stats = clip_records(records, cfg.WINDOW_S,
                                   cfg.ONE_ROUND_S[proto])
        vc = sum(1 for r in records if r.event_type == PBFT_VIEW_CHANGE)
        kept_dec = len({r.fields.get("instance_id") for r in kept
                        if r.event_type == "decided"})
        stream.write(
            f"  {proto:11s} first_decision={first:8.3f}s  "
            f"clipped={stats.clipped_fraction * 100:5.2f}%  "
            f"in_window_finalized={kept_dec:4d}  view_changes={vc}\n")
    stream.flush()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Family C delay-emission (delayed-voters) sweep (T51).")
    ap.add_argument("--smoke", action="store_true",
                    help="1 seed only (fast sanity, not the real dataset).")
    ap.add_argument("--probe", action="store_true",
                    help="calibration probe only (no dataset written).")
    ap.add_argument("--out", default=str(_OUT), help="output CSV path.")
    ap.add_argument("--jobs", type=int, default=1,
                    help="parallel workers for the light cell class (default 1).")
    ap.add_argument("--heavy-jobs", type=int, default=1,
                    help="parallel workers for the Snowman n>=25 class "
                         "(default 1; each cell is memory-heavy).")
    ap.add_argument("--fresh", action="store_true",
                    help="clear the checkpoint dir first (recompute all).")
    args = ap.parse_args()

    if args.probe:
        _probe(sys.stderr)
        return

    seeds = (0,) if args.smoke else cfg.SEEDS
    out = Path(args.out)
    _preflight_estimate(seeds, args.jobs, sys.stderr)
    rows, worst = run_sweep(seeds=seeds, out=out, jobs=args.jobs,
                            heavy_jobs=args.heavy_jobs, fresh=args.fresh,
                            progress_stream=sys.stderr)
    write_csv(rows, out)
    guard = "PASS" if worst < 0.05 else "FAIL (> 5% — see calibration)"
    print(f"wrote {len(rows)} rows -> {out}")
    print(f"worst clipped_fraction = {worst*100:.2f}%  [{guard}]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `make test-adversary`
Expected: PASS (all suites). The `test_jobs1_equals_jobs2_smoke` exercises the real `run_grid_tiered` on a 1-seed grid (30 cells/proto × 3 = 90 cells) — it may take a minute; that is fine.

- [ ] **Step 5: Run the full adversary suite + confirm no regressions elsewhere**

Run: `make test-adversary`
Expected: PASS.

Run: `make test-delay && make test-common`
Expected: PASS — proves the shared infra (`clip`, `run_grid_tiered`) was reused, not changed.

- [ ] **Step 6: Commit**

```bash
git add src/adversary/sweep.py tests/adversary/test_sweep.py
git commit -m "task 51: Family C sweep orchestrator + finality-delay-ratio post-pass"
```

---

## Task 9: Calibration probe + finalize the window/buffer/vc constants

**Files:**
- Modify: `src/adversary/config.py` (the four PROBE-SET constants only)

This task runs the probe, reads the real numbers, and edits `config.py` so the full sweep's clip guard holds. No new code.

- [ ] **Step 1: Run the probe**

Run: `PYTHONPATH=src python3 -m adversary.sweep --probe`
Expected: three lines (one per protocol) printing `first_decision`, `clipped`, `in_window_finalized`, `view_changes` for the worst attack cell (f=0.30, m=10) at n=10. Record this output verbatim for the experiment page §Calibration.

- [ ] **Step 2: Set `WINDOW_S` so every protocol finalizes ≥ 25 in-window decisions with clip < 5%**

From the probe's `in_window_finalized` and `clipped` columns: if any protocol shows `in_window_finalized < 25` or `clipped >= 5%`, raise `WINDOW_S` in `src/adversary/config.py` and re-probe. The binding constraint is whichever protocol has the largest `first_decision` under the worst attack (likely Snowman or PBFT-with-view-change at m=10). Set `WINDOW_S` to comfortably exceed `25 × (per-decision cadence under attack)` and keep the slowest protocol's clip under 5%.

- [ ] **Step 3: Set `BUFFER_S ≥` the slowest settling time**

`BUFFER_S` must clear one fully-delayed round: `≈ m_max·ref + one honest round`. For PBFT/Snowman `m_max·ref = 10·1.0 = 10 s`; set `BUFFER_S` to at least that plus margin (e.g. 24 s is the default — confirm it exceeds the slowest tail seen in the probe).

- [ ] **Step 4: Set `ONE_ROUND_S` per protocol from the probe**

Set each `ONE_ROUND_S[proto]` to the probe's `first_decision` for that protocol under the worst attack, rounded up — this is the clip's "started in [0, W]" scope bound.

- [ ] **Step 5: Confirm `PBFT_VC_DELAY_S` gives observable-but-not-spurious view-changes**

The probe prints `view_changes` for the worst PBFT attack cell — it should be `> 0` (a slow backup tripped rotation). Separately confirm the honest control does not rotate:

Run: `PYTHONPATH=src python3 -c "import sys; sys.path.insert(0,'src'); from adversary.runners import run_pbft; from pbft import PBFT_VIEW_CHANGE; recs,_,_ = run_pbft(10, 0.0, 0.0, 0); print('control view_changes =', sum(1 for r in recs if r.event_type==PBFT_VIEW_CHANGE))"`
Expected: `control view_changes = 0`. If it is `> 0`, raise `PBFT_VC_DELAY_S` until honest cells stop rotating; if the worst attack cell shows `0`, lower it until the attack trips rotation. Record the final value.

- [ ] **Step 6: Re-run the affected tests with the finalized constants**

Run: `make test-adversary`
Expected: PASS (Task 6's run-success test and Task 8's smoke now run against the calibrated window).

- [ ] **Step 7: Commit**

```bash
git add src/adversary/config.py
git commit -m "task 51: finalize Family C window/buffer/vc-delay from probe"
```

---

## Task 10: Run the full sweep → results CSV

**Files:**
- Create (artifact): `results/adversary/delayed_voters.csv`

- [ ] **Step 1: Print the preflight estimate and decide on a seed cap**

Run: `PYTHONPATH=src python3 -m adversary.sweep --smoke 2>&1 | tail -5`
This prints the per-protocol `[estimate]` lines and writes a 1-seed dataset. Read the projected total wall-clock at the bottom. Per the human decision (memory + spec §11): if the full 20-seed projection exceeds ~3 h, cap Snowman n=25 to ~8 seeds. The estimate is smallest-n and under-counts Snowman n=25, so be conservative.

- [ ] **Step 2 (conditional): Add a Snowman n=25 seed cap if the estimate is large**

If a cap is needed, add a `_seeds_for(protocol, n, seeds)` helper to `src/adversary/sweep.py` exactly mirroring `src/delay/heavy.py:175-183`, plus a module constant `SNOWMAN_N25_SEEDS = tuple(range(8))`, and use it in `_build_cells`:

```python
SNOWMAN_N25_SEEDS: tuple[int, ...] = tuple(range(8))


def _seeds_for(protocol: str, n: int, seeds: tuple[int, ...]) -> tuple[int, ...]:
    """Snowman n=25 capped at SNOWMAN_N25_SEEDS; everything else full set.
    Intersecting with `seeds` keeps --smoke coherent."""
    if protocol == "snowman" and n == 25:
        cap = set(SNOWMAN_N25_SEEDS)
        return tuple(s for s in seeds if s in cap)
    return seeds
```

Then in `_build_cells`, replace the `for s in seeds:` loop with `for s in _seeds_for(p, n, seeds):`. Re-run `make test-adversary` (the grid-count test counts the pbft/n10 cell which is unaffected, so it still passes). Add a one-line `log()`-style note to the experiment page that the cap was applied and which cells it touched (no silent truncation). Commit:

```bash
git add src/adversary/sweep.py
git commit -m "task 51: cap Snowman n=25 seeds (probe wall-clock)"
```

If no cap is needed, skip this step and note in the experiment page that the full 20-seed set ran for every (protocol, n).

- [ ] **Step 3: Run the full sweep**

Run: `PYTHONPATH=src python3 -m adversary.sweep --jobs 8 --heavy-jobs 1 2>sweep.log`
Expected: terminates with `wrote <N> rows -> results/adversary/delayed_voters.csv` and `worst clipped_fraction = X%  [PASS]`. If it shows `[FAIL (> 5%)]`, the window is too short — return to Task 9. The run is resumable: if interrupted, re-run the same command and it resumes from the checkpoints under `results/adversary/.sweep_adversary`.

- [ ] **Step 4: Sanity-check the dataset**

Run: `PYTHONPATH=src python3 -c "import sys,csv; rows=list(csv.DictReader(open('results/adversary/delayed_voters.csv'))); print('rows:', len(rows)); print('controls fdr==1:', all(abs(float(r['finality_delay_ratio'])-1.0)<1e-9 for r in rows if float(r['byzantine_fraction'])==0.0)); print('protocols:', sorted({r['protocol'] for r in rows}))"`
Expected: row count matches the grid (3 protocols × 2 n × 10 cells × seeds, minus any Snowman n=25 cap); every control row has `finality_delay_ratio == 1.0`; all three protocols present.

- [ ] **Step 5: Commit the dataset**

```bash
git add results/adversary/delayed_voters.csv
git commit -m "task 51: Family C delayed-voters dataset"
```

(The checkpoint dir `results/adversary/.sweep_adversary` is a runtime artifact — confirm it is gitignored like `results/delay/.sweep*`; if `results/` has a `.gitignore` entry for `.sweep*`, nothing to do. Otherwise add `results/adversary/.sweep_adversary/` to `.gitignore` in this commit.)

---

## Task 11: Dose-response plots (`adversary_plots.py`)

**Files:**
- Create: `src/output/adversary_plots.py`
- Test: `tests/output/test_adversary_plots.py`

Mirrors `src/output/delay_plots.py`: headless matplotlib (`Agg`), reuse `output.plots.STYLE` + `PROTO_ORDER`, save PNG + PDF to `results/adversary/plots/`. Two figure families (spec §6): finality_delay_ratio vs m at fixed f (dose-response), and vs f at fixed m, faceted by n.

- [ ] **Step 1: Write the failing test**

Create `tests/output/test_adversary_plots.py`:

```python
"""Smoke test for the Family C dose-response plots (T51)."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from output import adversary_plots as ap


def _tiny_csv(path: Path) -> None:
    cols = ["protocol", "n", "seed", "byzantine_fraction", "delay_mult",
            "finality_delay_ratio"]
    rows = []
    for proto in ("pbft", "casper-ffg", "snowman"):
        for n in (10, 25):
            for f in (0.0, 0.10, 0.20, 0.30):
                for m in ((0.0,) if f == 0.0 else (2.0, 5.0, 10.0)):
                    ratio = 1.0 if f == 0.0 else 1.0 + f * m
                    rows.append({"protocol": proto, "n": n, "seed": 0,
                                 "byzantine_fraction": f, "delay_mult": m,
                                 "finality_delay_ratio": ratio})
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


class TestPlots(unittest.TestCase):
    def test_render_all_figures(self):
        with tempfile.TemporaryDirectory() as d:
            csv_path = Path(d) / "delayed_voters.csv"
            plot_dir = Path(d) / "plots"
            _tiny_csv(csv_path)
            names = ap.render_all(str(csv_path), str(plot_dir))
            self.assertTrue(names)
            for name in names:
                self.assertTrue((plot_dir / f"{name}.pdf").exists(), name)
                self.assertTrue((plot_dir / f"{name}.png").exists(), name)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `make test-output`
Expected: FAIL with `ModuleNotFoundError: No module named 'output.adversary_plots'`.

- [ ] **Step 3: Write minimal implementation**

Create `src/output/adversary_plots.py`:

```python
"""T51 — delayed-voters (Family C delay-emission) dose-response figures.

Renders the Chapter-4 figures from results/adversary/delayed_voters.csv to
results/adversary/plots/ as PNG (screen) + PDF (vector, thesis import). The
headline is the dose-response of finality_delay_ratio (commit latency under
attack ÷ the f=0 control's latency) against the two swept adversary axes:
magnitude m and intensity f, faceted by committee size n.

Reuses output.plots STYLE + PROTO_ORDER and the output.analysis Student-t CI.

Re-run:
    PYTHONPATH=src python3 -m output.adversary_plots
"""
from __future__ import annotations

import csv
import math
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # headless / deterministic.
import matplotlib.pyplot as plt

from output.delay_analysis import mean_ci
from output.plots import STYLE, PROTO_ORDER

CSV_PATH = "results/adversary/delayed_voters.csv"
PLOT_DIR = "results/adversary/plots"

NS = (10, 25)
F_ATTACK = (0.10, 0.20, 0.30)
M_VALUES = (2.0, 5.0, 10.0)


def _fnum(x: str) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _load(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _save(fig, plot_dir: str, fname: str) -> str:
    fig.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(plot_dir, f"{fname}.{ext}"),
                    dpi=150 if ext == "png" else None)
    plt.close(fig)
    return fname


def _grid(ax):
    ax.grid(True, which="both", linestyle=":", linewidth=0.6, alpha=0.7)


def _ratio_means(rows, key_fields):
    """Map key_fields-tuple -> MeanCI of finality_delay_ratio over seeds."""
    buckets = defaultdict(list)
    for r in rows:
        key = tuple(r[k] if isinstance(k, str) else k for k in key_fields)
        buckets[key].append(_fnum(r["finality_delay_ratio"]))
    return {k: mean_ci(v) for k, v in buckets.items()}


def fig_ratio_vs_m(rows, plot_dir: str) -> list[str]:
    """Dose-response: finality_delay_ratio vs magnitude m, one panel per
    fixed intensity f, faceted by n. One figure per n."""
    means = _ratio_means(
        [r for r in rows if _fnum(r["byzantine_fraction"]) != 0.0],
        ("protocol", "n", "byzantine_fraction", "delay_mult"))
    names = []
    for n in NS:
        fig, axes = plt.subplots(1, len(F_ATTACK),
                                 figsize=(4.0 * len(F_ATTACK), 4.0),
                                 sharey=True)
        for ax, f in zip(axes, F_ATTACK):
            for proto in PROTO_ORDER:
                pts = [(m, means[(proto, str(n), f"{f:.6f}", f"{m:.6f}")])
                       for m in M_VALUES
                       if (proto, str(n), f"{f:.6f}", f"{m:.6f}") in means]
                if not pts:
                    continue
                xs = [m for m, _ in pts]
                ys = [c.mean for _, c in pts]
                errs = [c.ci_half for _, c in pts]
                ax.errorbar(xs, ys, yerr=errs, capsize=3, linewidth=1.6,
                            markersize=6, **STYLE[proto])
            ax.set_title(f"$f = {f:.2f}$")
            ax.set_xlabel("delay magnitude $m$ (× round cadence)")
            ax.set_xticks(M_VALUES)
            ax.axhline(1.0, color="grey", linewidth=0.8, linestyle="--")
            _grid(ax)
        axes[0].set_ylabel("finality delay ratio (vs f=0 control)")
        axes[0].legend(frameon=False)
        fig.suptitle(f"Finality delay vs slow-voter magnitude "
                     f"($n = {n}$, mean ± 95% CI)")
        names.append(_save(fig, plot_dir, f"ratio_vs_m_n{n}"))
    return names


def fig_ratio_vs_f(rows, plot_dir: str) -> list[str]:
    """finality_delay_ratio vs intensity f, one panel per fixed magnitude m,
    faceted by n. One figure per n."""
    means = _ratio_means(
        [r for r in rows if _fnum(r["byzantine_fraction"]) != 0.0],
        ("protocol", "n", "delay_mult", "byzantine_fraction"))
    names = []
    for n in NS:
        fig, axes = plt.subplots(1, len(M_VALUES),
                                 figsize=(4.0 * len(M_VALUES), 4.0),
                                 sharey=True)
        for ax, m in zip(axes, M_VALUES):
            for proto in PROTO_ORDER:
                pts = [(f, means[(proto, str(n), f"{m:.6f}", f"{f:.6f}")])
                       for f in F_ATTACK
                       if (proto, str(n), f"{m:.6f}", f"{f:.6f}") in means]
                if not pts:
                    continue
                xs = [f for f, _ in pts]
                ys = [c.mean for _, c in pts]
                errs = [c.ci_half for _, c in pts]
                ax.errorbar(xs, ys, yerr=errs, capsize=3, linewidth=1.6,
                            markersize=6, **STYLE[proto])
            ax.set_title(f"$m = {m:.0f}$")
            ax.set_xlabel("slow-voter fraction $f$")
            ax.set_xticks(F_ATTACK)
            ax.axhline(1.0, color="grey", linewidth=0.8, linestyle="--")
            _grid(ax)
        axes[0].set_ylabel("finality delay ratio (vs f=0 control)")
        axes[0].legend(frameon=False)
        fig.suptitle(f"Finality delay vs slow-voter fraction "
                     f"($n = {n}$, mean ± 95% CI)")
        names.append(_save(fig, plot_dir, f"ratio_vs_f_n{n}"))
    return names


def render_all(csv_path: str = CSV_PATH, plot_dir: str = PLOT_DIR) -> list[str]:
    rows = _load(csv_path)
    names = []
    names += fig_ratio_vs_m(rows, plot_dir)
    names += fig_ratio_vs_f(rows, plot_dir)
    return names


def main() -> None:
    names = render_all()
    print(f"wrote {len(names)} figures -> {PLOT_DIR}: {', '.join(names)}")


if __name__ == "__main__":
    main()
```

Before implementing, **verify two reused symbols exist** (Grep substitute for auggie): `output.plots.STYLE`, `output.plots.PROTO_ORDER`, and `output.analysis.mean_ci`. If `mean_ci` lives in `output.delay_analysis` instead of `output.analysis` (it is re-exported in `delay_analysis`), import it from wherever it is defined — `grep -n "def mean_ci\|^STYLE\|^PROTO_ORDER" src/output/*.py` resolves this. Adjust the import line accordingly.

- [ ] **Step 4: Run test to verify it passes**

Run: `make test-output`
Expected: PASS (`test_adversary_plots` renders 4 figures into a temp dir).

- [ ] **Step 5: Render the real figures from the committed dataset**

Run: `PYTHONPATH=src python3 -m output.adversary_plots`
Expected: `wrote 4 figures -> results/adversary/plots: ratio_vs_m_n10, ratio_vs_m_n25, ratio_vs_f_n10, ratio_vs_f_n25`.

- [ ] **Step 6: Commit (code + PDFs; PNGs are regenerable)**

```bash
git add src/output/adversary_plots.py tests/output/test_adversary_plots.py
git add results/adversary/plots/*.pdf
git commit -m "task 51: dose-response plots for delayed-voters"
```

(Match the T48 figure-tracking convention: PDFs tracked, PNGs regenerable. Confirm `results/**/plots/*.png` is gitignored as in `results/delay/plots`; if not, do not `git add` the PNGs.)

---

## Task 12: Wiki deliverables, experiment-matrix amendments, status flip

**Files:**
- Create: `wiki/experiments/2026-06-14_delayed-voters.md`
- Modify: `wiki/concepts/adversary-model.md` (Revision §3)
- Modify: `wiki/concepts/adversary-model-runtime.md` (Revision §4/§5)
- Modify: `wiki/concepts/node-model.md` (Revision §9)
- Modify: `wiki/concepts/experiment-matrix.md` (Revision §3)
- Modify: `wiki/concepts/experiment-matrix-runs.md` (Revision §3/§4)
- Modify: `wiki/index.md` (add the experiment page)
- Modify: `wiki/log.md` (append the task entry)
- Modify: `TASKS.md` (status flip to In Review)

- [ ] **Step 1: Write the experiment page**

Create `wiki/experiments/2026-06-14_delayed-voters.md` with these sections (fill the bracketed values from the actual run — do not leave brackets in the committed file):

```markdown
# [2026-06-14] Delayed voters — Family C delay-emission (T51)

Bootstraps the adversary-injection subsystem (`src/adversary/`) and runs the
Week-10 Family C `delay-emission` experiment: the highest-id ⌊f·n⌋ validators
hold every outbound emission by a fixed `m·ref` seconds; impact on
time-to-finality across PBFT, Casper FFG, Snowman at n ∈ {10, 25}.

Backlinks: [[concepts/adversary-model#3]], [[concepts/adversary-model-runtime#4]],
[[concepts/node-model#9]], [[concepts/experiment-matrix#3]],
[[concepts/experiment-matrix-runs#3]], [[concepts/sweep-harness]],
[[experiments/2026-06-12_delay-heavy]] (the heavy.py orchestrator precedent).

## Subsystem (the seam)
[2-3 sentences: post-build outbound-API wrap, honest network preserved,
fixed-shift determinism, fills Node.adversary. Cite spec §3.]

## Config
- Static-baseline network: constant 10 ms, loss-free.
- Axes: f ∈ {0, 0.10, 0.20, 0.30}; m ∈ {2, 5, 10} (m on f>0 only).
- n ∈ {10, 25}; seeds [range(20); Snowman n=25 capped to range(8) if applied].
- Per-protocol ref: PBFT 1.0 s, Snowman 1.0 s, Casper FFG 0.1 s.
- Window/buffer/vc (probe-set): W=[..], buffer=[..], PBFT vc_delay=[..].

## Calibration (probe numbers)
[Paste the `--probe` output table: first_decision / clipped / in_window_finalized
/ view_changes per protocol. State the resulting WINDOW_S / BUFFER_S /
ONE_ROUND_S / PBFT_VC_DELAY_S and why.]

## Seeds, commit, re-run
- Commit hash: [git rev-parse HEAD at run time].
- Raw result: `results/adversary/delayed_voters.csv` ([N] rows).
- Re-run: `PYTHONPATH=src python3 -m adversary.sweep --jobs 8 --heavy-jobs 1`
- Probe: `PYTHONPATH=src python3 -m adversary.sweep --probe`
- Plots: `PYTHONPATH=src python3 -m output.adversary_plots`

## Observation (one paragraph)
[Findings: dose-response shape per protocol; FFG cadence asymmetry (shorter ref
⇒ smaller absolute shift); PBFT view-change behaviour under attack; the Casper
proposer-overlap caveat (§3.3); whether liveness held at f < 1/3.]

## Auggie verification
auggie MCP (`mcp__auggie__codebase-retrieval`) is unavailable in this
environment; per the Engineer role this gap is logged with the Grep/Glob
substitutes used (precedent: the T41 page).

- pickup-index: [query string] -> [one-line result]
- plan: [query string] -> [one-line result]
- post-edit re-query: [query string] -> [one-line result]
```

- [ ] **Step 2: Add the four concept-page Revisions**

To each of `adversary-model.md`, `adversary-model-runtime.md`, `node-model.md`, append (or extend) a `## Revisions` section dated 2026-06-14 per `docs/wiki-spec.md` (do NOT overwrite existing claims):
- `adversary-model.md` §3 — `delay-emission` now has a runtime realization (the bind-seam wrap); record the bind-seam-vs-FSM-dispatch decision for the delay capability.
- `adversary-model-runtime.md` §4/§5 — `DelayProfile` implemented in `src/adversary/profiles.py`; fixed-magnitude delay needs no adversary RNG (the §5 per-node RNG deferred to randomized capabilities, e.g. T53).
- `node-model.md` §9 — delay realized at the bound outbound API via post-build wrap, not FSM dispatch (pragmatic for the delay capability).

- [ ] **Step 3: Amend the experiment-matrix pages**

To `experiment-matrix.md` §3 and `experiment-matrix-runs.md` §3/§4, add a Revision recording: Family C gains `n ∈ {10, 25}` (the approved 2026-06-14 extension), the magnitude axis `m ∈ {2,5,10}` for delay-emission (refines the matrix's "2–10×" band into a swept axis), the `f=0` control point, and the bumped run budget. This resolves the 2026-06-10 Backlog item that named T51.

- [ ] **Step 4: Update the index**

In `wiki/index.md` under `## Experiments`, add one line (keep the existing alphabetical-by-date ordering near the other 2026-06 entries):

```markdown
- [[experiments/2026-06-14_delayed-voters]] — T51 Family C delay-emission: bootstraps `src/adversary/` (post-build outbound-API wrap filling `Node.adversary`, fixed-shift ⇒ no adversary RNG); slow voters hold emissions by `m·ref` over PBFT/Casper FFG/Snowman, n∈{10,25}, f∈{0,.1,.2,.3}×m∈{2,5,10}; headline `finality_delay_ratio` vs the f=0 control. Reuses `run_grid_tiered` + `clip_records`.
```

- [ ] **Step 5: Append the log entry**

Append to `wiki/log.md`:

```markdown
## [2026-06-14] experiment | task 51 — delayed voters (Family C delay-emission)
- role: Engineer
- touched: src/adversary/{__init__,profiles,select,inject,config,runners,sweep}.py, src/output/adversary_plots.py, tests/adversary/*, tests/output/test_adversary_plots.py, Makefile, results/adversary/delayed_voters.csv, results/adversary/plots/*.pdf, wiki/experiments/2026-06-14_delayed-voters.md, wiki/concepts/{adversary-model,adversary-model-runtime,node-model,experiment-matrix,experiment-matrix-runs}.md, wiki/index.md
- notes: Bootstrapped the adversary-injection subsystem (post-build outbound-API wrap, honest network preserved, fixed-shift determinism) and ran the delay-emission sweep; reused T46.1 run_grid_tiered + T46 clip. auggie unavailable — Grep/Glob substitute logged in the experiment page.
```

- [ ] **Step 6: Flip the task status**

In `TASKS.md`, change the T51 line from `[~]` (In Progress) to `[?]` (In Review). Do NOT mark it Completed — that is the human's call (CLAUDE.md hard rule). Recompute the Dashboard counts if `TASKS.md` carries them.

- [ ] **Step 7: Run the verification skill, then commit**

Invoke `superpowers:verification-before-completion` and run the full gate:

Run: `make test`
Expected: every suite PASS (including the new `adversary` suite), and the existing baselines unchanged (no shared-infra edits).

```bash
git add wiki/ TASKS.md
git commit -m "task 51: wiki experiment page + matrix amendments + In Review"
```

- [ ] **Step 8: Push and hand off**

Push `worktree-T51-delayed-voters`. Summarize for the human: files touched, wiki pages added/updated, the calibration decisions (window/buffer/vc, any Snowman seed cap), the headline findings, and the open questions (magnitude granularity `{2,5,10}` vs `{2,4,6,8,10}`; Casper proposer overlap; FFG cadence asymmetry). The human commits the merge and flips to Completed.

---

## Self-Review

**1. Spec coverage** (against `2026-06-14-t51-delayed-voters-design.md`):
- §1 goal / scope → Tasks 1–11 build exactly the in-scope items (delay-emission, 3 protocols, n∈{10,25}, static-baseline, `src/adversary/`, one CSV + plots, experiment page, wiki amendments). Out-of-scope (T52/T53, Narwhal+Tusk, streaming reducer) untouched. ✓
- §3 architecture (bind-seam wrap, no source edits, slow-node selection) → Task 4 (`inject_delay`), Task 3 (`slow_node_ids` highest-id). ✓
- §4 components → `profiles.py` (T2), `inject.py` (T4), `select.py` (T3), `config.py` (T5), `runners.py` (T6), `sweep.py` (T8). ✓
- §5 experiment design (f/m axes, 10 cells/(proto,n,seed), 1200-run grid, cadence refs) → Task 5 constants + Task 8 `_build_cells`. ✓
- §6 metrics/output (18-col T40 projection + Family-C block, `finality_delay_ratio` post-pass) → Task 8 `_build_row` + `_finality_delay_ratios`; plots → Task 11. ✓
- §7 calibration/window/tiered scheduler (probe-first, `run_grid_tiered`, `--heavy-jobs 1`) → Task 9 (probe) + Task 8 (`run_grid_tiered`, `_is_heavy_cell`). ✓
- §8 determinism (fixed shift ⇒ no RNG; f=0 ≡ honest; jobs=1 ≡ jobs=N) → Task 7 tests + Task 8 `test_jobs1_equals_jobs2_smoke`. ✓
- §9 testing (test_select / test_inject / test_profiles / test_determinism / test_e2e / test_sweep) → Tasks 2,3,4,6,7,8 (test_runners covers the §9 e2e monotone case). ✓
- §10 wiki deliverables (experiment page + 4 Revisions + matrix amendment + index + log) → Task 12. ✓
- §11 risks (magnitude granularity, Snowman cost cap, proposer overlap, FFG asymmetry) → Task 10 step 2 (seed cap), Task 12 step 8 (handoff flags). ✓
- §12 auggie gap → Task 12 step 1 (Auggie verification section). ✓

**2. Placeholder scan:** the probe-set constants in `config.py` are explicitly real values with a finalize-in-Task-9 protocol (not "TBD"); the experiment-page brackets in Task 12 are instructions-to-fill-from-the-run with a "do not leave brackets" directive, not code placeholders. No `TODO`/"add error handling"/"similar to" in any code step.

**3. Type consistency:** `inject_delay(handle, slow_ids, mult, ref)` signature is identical in `inject.py` (T4), the runners (T6), and the tests (T4). `DelayProfile(nodes, intensity, mult, kind=)` identical across T2/T4. The cell tuple `(proto, n, f, m, seed)` is consistent across `_build_cells`, `_cell_key`, `_param_fingerprint`, `_run_cell` (T8). `RUNNERS[proto](n, f, m, seed)` signature matches runners (T6) and sweep `_run_cell` (T8). `finality_delay_ratio` column name identical in `_build_row`, `_finality_delay_ratios`, `write_csv`, and the plots. ✓
```
