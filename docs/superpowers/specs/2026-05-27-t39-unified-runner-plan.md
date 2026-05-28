# T39 — Unified Runner + Bootstrap-Seam Hardening: Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to
> implement this plan task-by-task. Each task is one TDD cycle (test →
> red → green → commit) and leaves `make test` green.

**Goal:** Land `src/common/runner.py` (one helper, `run_to_completion`)
collapsing the bootstrap tail four callers duplicate; close the two
remaining bootstrap-seam fail-fast holes (`Scheduler.bind` duplicate and
`Network.start` double-call); migrate all four callers; document the new
seam in `wiki/concepts/runner.md` + three `## Revisions` blocks.

**Architecture:** Helper, not a class. `run_to_completion(handle, *,
t_max=None, logger=None) -> tuple[RunResult, EventLogger]` attaches the
logger to `handle.scheduler.event_sink`, runs the scheduler, returns
both. Sits *post-build* (consumes the `RunHandle` from
`config.factory.build_run`). No CSV writing, no multi-seed, no adversary
hook (those are T40 / T41+ / T18).

**Tech Stack:** Python 3 stdlib only. unittest. The existing
`config.factory.build_run` + `RunHandle` seam from T27. The
`EventLogger` from T24. No new dependencies.

---

## 0. Spec → plan drift (read first)

The companion design spec
`docs/superpowers/specs/2026-05-27-t39-unified-runner-design.md` §3 lists
five fail-fast guards as in-scope (A1, A2, B1, B2, B3). On audit, three
already shipped during W3 (T22 / T23) and are covered by existing tests:

| Guard | Code site | Test site | Status |
|---|---|---|---|
| **A1** `node_id < 0` rejected | `src/nodes/node.py:46-49` | `tests/nodes/test_node.py::test_negative_node_id_rejected` (lines 31-37) | ✅ already shipped |
| **A2** non-finite `weight` rejected | `src/nodes/node.py:50-51` | `tests/nodes/test_node.py::test_nan_weight_rejected`, `test_pos_inf_weight_rejected`, `test_neg_inf_weight_rejected` (lines 39-55) | ✅ already shipped |
| **B1** duplicate `Network.register` | `src/network/network.py:46-48` | `tests/network/test_network.py::test_duplicate_register_rejected` (line 306) | ✅ already shipped |
| **B2** duplicate `Scheduler.bind` | — | — | ❌ Task 1 below |
| **B3** double `Network.start` | — | — | ❌ Task 2 below |

**Plan posture:** treat A1 / A2 / B1 as **verify-only** — no code edits;
the existing tests are the evidence — and append-resolve the relevant
TASKS.md backlog item with both halves (W3-shipped + T39-closes-B2/B3).

This is the only departure from the spec's literal task list. The Out
of Scope section (spec §1), the runner contract (spec §2), the
migration plan (spec §4), the wiki touches (spec §6), and the
acceptance criteria (spec §8) are unchanged.

## 0.1 Pre-flight check (no code change)

**Run:**

```bash
make test
PYTHONPATH=src python3 -m pos.baseline
shasum -a 256 results/pos/baseline.csv
```

**Expected:** every suite green; `results/pos/baseline.csv` written; one
sha256 line. **Capture both** the pre-migration `make test` line counts
(every suite's "Ran N tests in ..." footer) and the pre-migration
sha256 — they are the byte-identical evidence in §M-verify and §8.

A clean tree is mandatory before Task 1. Confirm with `git status`.

---

## Task 1: B2 guard — `Scheduler.bind` rejects duplicate `node.id`

**Why:** symmetric with the unregistered-`dst` `KeyError` paths in
`Scheduler._dispatch._node` and `Network._try_deliver`. The current
`self.nodes[node.id] = node` (`src/scheduler/scheduler.py:105`)
silently clobbers — a duplicate-`id` config would drop a validator.

**Files:**
- Modify: `src/scheduler/scheduler.py:101-117` (the `bind()` method)
- Test:   `tests/scheduler/test_scheduler.py` (append to `class TestBind`)

### Step 1: Write the failing test

Append inside `class TestBind` in `tests/scheduler/test_scheduler.py`
(after `test_bind_network_sets_network_handle`, before
`test_emit_with_no_sink_is_silent`):

```python
    def test_bind_rejects_duplicate_node_id(self):
        s = Scheduler()
        a = RecordingNode(7)
        b = RecordingNode(7)   # same id; should fail loud, not clobber
        s.bind(a)
        with self.assertRaises(ValueError) as cm:
            s.bind(b)
        self.assertIn("duplicate", str(cm.exception))
        self.assertIs(s.nodes[7], a)   # original still wired
```

### Step 2: Run the test, confirm it fails

```bash
PYTHONPATH=src:tests/scheduler python3 -m unittest \
    tests.scheduler.test_scheduler.TestBind.test_bind_rejects_duplicate_node_id -v
```

Expected: **FAIL** — `AssertionError: ValueError not raised` (current
code clobbers silently).

### Step 3: Add the guard

Edit `src/scheduler/scheduler.py`, in `Scheduler.bind` (line 101), add
the check as the first line of the method body, before `self.nodes[...]`:

```python
    def bind(self, node: Any) -> None:
        """Wire a Node's scheduler-owned outbound API and register it for
        dispatch. Does NOT wire send/broadcast — that is Network.bind's half.
        """
        if node.id in self.nodes:
            raise ValueError(
                f"Scheduler.bind: NodeId {node.id} already bound")
        self.nodes[node.id] = node   # DD3 / Revision R1: dispatch target.
        # ... (rest unchanged)
```

### Step 4: Re-run, confirm green

```bash
PYTHONPATH=src:tests/scheduler python3 -m unittest \
    tests.scheduler.test_scheduler.TestBind.test_bind_rejects_duplicate_node_id -v
make test-scheduler
```

Expected: **PASS**; `test-scheduler` suite green.

### Step 5: Commit

`git add src/scheduler/scheduler.py tests/scheduler/test_scheduler.py`

Commit message (per `docs/workflow.md` § Commit convention):

```
task 39: scheduler.bind fail-fast on duplicate node_id
```

---

## Task 2: B3 guard — `Network.start` rejects second call

**Why:** `Network.start()` already sets `self._started = True`
(`src/network/network.py:76`) but never checks it on entry; a second
call re-runs `validate_timeline` *and* re-schedules every interior
`PhaseAdvance`, double-firing phase rollovers — a heap-poisoning bug
that would corrupt determinism the moment a future harness layer
called `start` twice. `RuntimeError`, not `ValueError`, because the
fault is a wrong call sequence, not a bad value.

**Files:**
- Modify: `src/network/network.py:63-76` (the `start()` method)
- Test:   `tests/network/test_network.py` (append to an existing
  `class` near `test_start_*`)

### Step 1: Write the failing test

Append inside the same test class as `test_start_validates_timeline`
(`tests/network/test_network.py`, around line 79):

```python
    def test_start_rejects_double_call(self):
        # Second start would re-schedule every interior PhaseAdvance,
        # double-firing rollovers and corrupting the heap.
        net = _net_one_phase()
        net.start()
        with self.assertRaises(RuntimeError) as cm:
            net.start()
        self.assertIn("twice", str(cm.exception))
```

If the file does not already expose a `_net_one_phase()` helper, mirror
the construction used in `test_start_schedules_interior_boundary_only`
(check `tests/network/test_network.py` ~lines 68-79; the suite already
has a single-phase fixture). If there is no shared helper, inline the
construction:

```python
        sched = Scheduler()
        phases = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)
        net = Network(sched, phases, global_seed=42)
        net.start()
        with self.assertRaises(RuntimeError) as cm:
            net.start()
        self.assertIn("twice", str(cm.exception))
```

(Imports already present in this test file; do not duplicate.)

### Step 2: Run, confirm fail

```bash
PYTHONPATH=src:tests/network python3 -m unittest \
    tests.network.test_network -v -k test_start_rejects_double_call
```

Expected: **FAIL** — second `start()` returns silently.

### Step 3: Add the guard

Edit `src/network/network.py`, prepend to `Network.start` body
(line 71, before `validate_timeline(...)`):

```python
    def start(self) -> None:
        """..."""
        if self._started:
            raise RuntimeError("Network.start() called twice")
        validate_timeline(self.phases, set(self.registry))
        # ... (rest unchanged)
```

### Step 4: Re-run, confirm green

```bash
PYTHONPATH=src:tests/network python3 -m unittest \
    tests.network.test_network -v -k test_start_rejects_double_call
make test-network
```

Expected: **PASS**; full network suite green.

### Step 5: Commit

```
task 39: network.start fail-fast on second call
```

---

## Task 3: Land `src/common/` package and the runner helper

**Files (all new):**
- Create: `src/common/__init__.py`
- Create: `src/common/runner.py`
- Create: `tests/common/test_runner.py`

The design spec §2.2 pins the signature; §2.3 pins the four decisions;
§5.2 pins the six runner tests. Reproduce verbatim.

### Step 1: Create `src/common/__init__.py`

```python
"""Cross-protocol simulator helpers (T39).

Today: one helper, `run_to_completion`, that pairs with
`config.factory.build_run` to collapse the bootstrap tail every caller
otherwise duplicates. See wiki/concepts/runner.md for the contract.
"""
from .runner import run_to_completion

__all__ = ["run_to_completion"]
```

### Step 2: Create `src/common/runner.py`

```python
"""Post-build half of the six-phase bootstrap (T39).

`run_to_completion` attaches an EventLogger to the scheduler's
event_sink, runs the scheduler to its stop condition, and returns
(RunResult, EventLogger). Pass-through over `RunHandle`; no scheduler-
layer adversary hook (that surface belongs to T18); no CSV output
(that surface belongs to T40).

Design contract: wiki/concepts/runner.md
Design spec:    docs/superpowers/specs/2026-05-27-t39-unified-runner-design.md
"""
from __future__ import annotations

from config.schema import RunHandle
from event_log import EventLogger
from scheduler import RunResult


def run_to_completion(
    handle: RunHandle,
    *,
    t_max: float | None = None,
    logger: EventLogger | None = None,
) -> tuple[RunResult, EventLogger]:
    """Attach a logger, run the scheduler, return (RunResult, EventLogger).

    `t_max=None` runs to quiescence (matches PBFT honest path).
    `t_max=<float>` runs to deadline (matches Casper / Snowman, which
    have no natural quiescence).

    A freshly-constructed `EventLogger` is used if `logger is None`;
    callers that want to share or pre-seed a logger may pass one. The
    same logger object is returned, so callers can introspect
    `logger.records` after the run.
    """
    if logger is None:
        logger = EventLogger()
    handle.scheduler.event_sink = logger.sink
    if t_max is None:
        result = handle.scheduler.run()
    else:
        result = handle.scheduler.run(t_max=t_max)
    return result, logger
```

### Step 3: Create `tests/common/test_runner.py` — six cases

The runner reuses `BroadcastNode` (a quiescent workload) and
`TimerNode` (re-arming workload) from `tests/integration/_helpers.py`;
copying the minimal nodes locally avoids cross-suite PYTHONPATH
collisions (each test suite lives behind its own helper, per the
Makefile note about colliding `_helpers.py` modules).

```python
"""Unit tests for run_to_completion (T39, wiki/concepts/runner.md)."""
from __future__ import annotations

import math
import unittest
from types import MappingProxyType

from common import run_to_completion
from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from nodes import Node


_MIN_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)


class _QuiescentNode(Node):
    """Broadcasts one TOKEN on start; recipients do not re-broadcast,
    so the run reaches quiescence after one round of n*(n-1) deliveries."""

    def __init__(self, node_id, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)

    def _on_start(self, t):
        self.broadcast("TOKEN", {"from": self.id}, t)

    def _on_message(self, msg, t):
        pass

    def _on_timer(self, timer_id, payload, t):
        pass


class _ReArmingNode(Node):
    """Re-arms a 0.1-second timer indefinitely; no quiescence — only a
    deadline can stop the run."""

    def __init__(self, node_id, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)

    def _on_start(self, t):
        self.set_timer("tick", 0.1, None, t)

    def _on_message(self, msg, t):
        pass

    def _on_timer(self, timer_id, payload, t):
        self.set_timer("tick", 0.1, None, t)


def _config(n):
    return Config(
        n=n, t_max=math.inf, seeds=SeedsConfig(n_runs=1),
        network=_MIN_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _quiescent_factory():
    def make(node_id, global_seed):
        return _QuiescentNode(node_id=node_id, global_seed=global_seed)
    return make


def _rearming_factory():
    def make(node_id, global_seed):
        return _ReArmingNode(node_id=node_id, global_seed=global_seed)
    return make


class TestRunToCompletion(unittest.TestCase):

    def test_returns_run_result_and_logger(self):
        handle = build_run(_config(2), 42, _quiescent_factory())
        result, logger = run_to_completion(handle)
        self.assertIsInstance(logger, EventLogger)
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertGreater(len(logger.records), 0)

    def test_default_logger_constructed_when_omitted(self):
        handle = build_run(_config(2), 42, _quiescent_factory())
        _, logger = run_to_completion(handle)
        # Fresh logger captured the run.
        self.assertGreater(len(logger.records), 0)

    def test_caller_supplied_logger_used(self):
        pre = EventLogger()
        handle = build_run(_config(2), 42, _quiescent_factory())
        _, logger = run_to_completion(handle, logger=pre)
        self.assertIs(logger, pre)
        self.assertGreater(len(logger.records), 0)

    def test_t_max_none_runs_to_quiescence(self):
        handle = build_run(_config(2), 42, _quiescent_factory())
        result, _ = run_to_completion(handle, t_max=None)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_t_max_float_runs_to_deadline(self):
        handle = build_run(_config(2), 42, _rearming_factory())
        result, _ = run_to_completion(handle, t_max=1.0)
        self.assertEqual(result.stopped_by, "deadline")
        self.assertGreaterEqual(result.now, 1.0)

    def test_two_runs_byte_identical(self):
        h1 = build_run(_config(2), 42, _quiescent_factory())
        _, a = run_to_completion(h1)
        h2 = build_run(_config(2), 42, _quiescent_factory())
        _, b = run_to_completion(h2)
        self.assertEqual(list(a.records), list(b.records))


if __name__ == "__main__":
    unittest.main()
```

### Step 4: Run the new suite, confirm green

The `common` suite is not yet in the Makefile (Task 4 below adds it),
so run it directly first:

```bash
PYTHONPATH=src:tests/common python3 -m unittest discover -s tests/common -v
```

Expected: 6 tests, all PASS.

### Step 5: Commit

```
task 39: src/common/runner.py — run_to_completion helper
```

Stage: `src/common/__init__.py src/common/runner.py
tests/common/test_runner.py`.

---

## Task 4: Register the `common` suite in the Makefile

**Why:** `make test` iterates `SUITES`; without registration the new
suite never runs. T38 set the precedent (added `snowman`).

**Files:**
- Modify: `Makefile:15`

### Step 1: Edit

Change line 15 from:

```
SUITES        = scheduler nodes network event_log config pbft pos snowman integration
```

to (alphabetical between `config` and `event_log`):

```
SUITES        = scheduler nodes network event_log config common pbft pos snowman integration
```

### Step 2: Verify the new suite runs from `make test`

```bash
make test-common
```

Expected: 6 tests PASS, same as Task 3 Step 4.

```bash
make test
```

Expected: every suite green, **including** `common`. Capture the
per-suite "Ran N tests" footer in the verification record (§M-verify
below references this).

### Step 3: Commit

```
task 39: register common suite in Makefile
```

---

## Task 5: Pre-migration determinism baseline (no code change)

**Why:** the migration's correctness proof is byte-identical event
streams pre/post — for the integration tests via
`test_determinism*`, and for `src/pos/baseline.py` via
`results/pos/baseline.csv`. Capture the pre-migration evidence *now*
so post-migration verification is a single `diff` / `shasum -c`.

**Files:** none modified — verification capture only.

### Steps

```bash
make test 2>&1 | tee /tmp/t39-pre.log
PYTHONPATH=src python3 -m pos.baseline
shasum -a 256 results/pos/baseline.csv > /tmp/t39-pos-baseline.sha
cat /tmp/t39-pos-baseline.sha
```

Expected: `make test` green; `results/pos/baseline.csv` exists; sha256
captured. **Do not commit** `/tmp/*` artifacts — they are
verification scratch. Note the sha256 line in the handoff summary.

No commit for this task.

---

## Task 6: Migrate M1 — `tests/integration/test_pbft_baseline.py`

**Files:**
- Modify: `tests/integration/test_pbft_baseline.py:23-78`

### Step 1: Edit imports

Change line 25 from:

```python
from event_log import EventLogger
```

to:

```python
from common import run_to_completion
```

(`event_log` becomes unused in this file post-migration.)

### Step 2: Replace `_run`

Replace lines 72-78 (the `_run` function) with:

```python
def _run(n: int, global_seed: int = 42):
    """Build, run to quiescence, return (logger, result)."""
    handle = build_run(_config(n), global_seed, _factory(n))
    result, logger = run_to_completion(handle)
    return logger, result
```

Return-tuple shape `(logger, result)` is preserved — call-sites
(`test_every_node_finalizes`, `test_no_forks`,
`test_finalization_latency_logged`, `test_determinism`) unchanged.

### Step 3: Run the suite

```bash
make test-integration
```

Expected: every PBFT-baseline test PASS, including `test_determinism`
(byte-identical event streams from the migration).

### Step 4: Commit

```
task 39: migrate test_pbft_baseline to run_to_completion
```

---

## Task 7: Migrate M2 — `tests/integration/test_pos_baseline.py`

**Files:**
- Modify: `tests/integration/test_pos_baseline.py:23-110`

### Step 1: Edit imports

Change line 29 from:

```python
from event_log import EventLogger
```

to:

```python
from common import run_to_completion
```

### Step 2: Replace `_run`

Replace lines 97-109 (the `_run` function) with:

```python
def _run(n: int, stake_table: dict[int, float], global_seed: int = 42):
    """Build, run to t_max, return (logger, result).

    Casper has no quiescence — the slot timer re-arms indefinitely —
    so every run is bounded by t_max only. config.factory.build_run
    does not pipe Config.t_max into scheduler.run(), so pass it
    through here (same pattern as test_casper_baseline.py)."""
    handle = build_run(_config(n), global_seed, _factory(n, stake_table))
    result, logger = run_to_completion(handle, t_max=_T_MAX)
    return logger, result
```

### Step 3: Run

```bash
make test-integration
```

Expected: PoS-baseline tests PASS, `test_determinism` byte-identical.

### Step 4: Commit

```
task 39: migrate test_pos_baseline to run_to_completion
```

---

## Task 8: Migrate M3 — `tests/integration/test_snowman_baseline.py`

**Files:**
- Modify: `tests/integration/test_snowman_baseline.py:1-65`

### Step 1: Edit imports

Change line 17 from:

```python
from event_log import EventLogger
```

to:

```python
from common import run_to_completion
```

### Step 2: Replace `_run`

Replace lines 59-64 with:

```python
def _run(n: int, global_seed: int = 42):
    handle = build_run(_config(n), global_seed, _factory(n))
    result, logger = run_to_completion(handle, t_max=_T_MAX)
    return logger, result, dict(handle.nodes)
```

`handle.nodes` extraction stays at the caller — protocol-specific
introspection is deliberately not the runner's job (spec §2.4).
`handle.nodes` is the `MappingProxyType` view `build_run` provides.

### Step 3: Run

```bash
make test-integration
```

Expected: Snowman-baseline tests PASS; the (newly-added in T38)
`test_determinism` case stays byte-identical.

### Step 4: Commit

```
task 39: migrate test_snowman_baseline to run_to_completion
```

---

## Task 9: Migrate M4 — `src/pos/baseline.py`

**Files:**
- Modify: `src/pos/baseline.py:22-79`

### Step 1: Edit imports

Change line 32 from:

```python
from event_log import EventLogger
```

to:

```python
from common import run_to_completion
```

### Step 2: Replace `_run_scenario`

Replace lines 75-79 (the bottom of `_run_scenario`):

```python
    logger = EventLogger()
    handle = build_run(config, _GLOBAL_SEED, factory)
    handle.scheduler.event_sink = logger.sink
    handle.scheduler.run(t_max=_T_MAX)
    return logger
```

with:

```python
    handle = build_run(config, _GLOBAL_SEED, factory)
    _, logger = run_to_completion(handle, t_max=_T_MAX)
    return logger
```

### Step 3: Verify byte-identical CSV

```bash
PYTHONPATH=src python3 -m pos.baseline
shasum -a 256 -c /tmp/t39-pos-baseline.sha
```

Expected: `results/pos/baseline.csv: OK`. If it does **not** verify,
stop — the migration changed event-stream order, which violates the
contract (spec §7 latent risk). Diagnose before continuing.

### Step 4: Commit

```
task 39: migrate src/pos/baseline.py to run_to_completion
```

---

## §M-verify: full-suite verification before wiki / TASKS edits

Before the documentation tasks (10–12), gate on a clean full-suite run
(per the Engineer role prompt's
`superpowers:verification-before-completion` requirement):

```bash
make test
```

Expected: every suite green; per-suite pass counts ≥ the pre-migration
counts captured in Task 5 (`/tmp/t39-pre.log`). Specifically:

- `tests/common`: 6 (new, all from Task 3).
- `tests/scheduler`: pre + 1 (B2 guard test from Task 1).
- `tests/network`: pre + 1 (B3 guard test from Task 2).
- `tests/integration`: pre (unchanged — Tasks 6–8 replace bodies, not
  add tests).
- All other suites: identical to pre.

Capture the post-migration totals for the handoff summary. If any
`test_determinism*` case fails byte-identical, stop and diagnose.

---

## Task 10: New wiki page `wiki/concepts/runner.md`

**Files:**
- Create: `wiki/concepts/runner.md`

Follow the design spec §6.1 (six sections, ~120 lines, mirrors
`event-log-schema.md`'s tone). Outline:

1. **Purpose.** `run_to_completion` is the post-build half of the
   six-phase bootstrap; pairs with `build_run` (build half) and the
   bootstrap from `[[concepts/simulation-design#bootstrap]]`.
2. **Contract.** The signature from spec §2.2 + the four decisions
   R1–R4 from spec §2.3 (table).
3. **Stop modes.** `t_max=None` ⇒ quiescence; `t_max=<float>` ⇒
   deadline. Explicit non-introduction of overshoot-and-clip
   (forwards to `[[concepts/experiment-matrix]]` Backlog item).
4. **Determinism.** Runner is pass-through; the seven determinism
   mechanisms in `[[concepts/simulation-design-runtime]]` are
   unaffected.
5. **Adversary boundary.** Explicit non-slot — same posture as
   `[[concepts/simulation-design-runtime#adversary-boundary]]`. T18
   attaches at the `Node` layer.
6. **What it does NOT own.** CSV columns → T40
   (`[[concepts/output-format]]`); multi-seed sweeps → T41+; adversary
   wiring → T18. One bullet each.

Wikilink style: `[[concepts/...]]` per `docs/wiki-spec.md` § Cross-
references. No `TODO(cite)` (no external claims). Stay under 300 lines
per `docs/wiki-spec.md` § Page size.

No commit yet — bundle with Task 11.

---

## Task 11: Three `## Revisions` blocks + index + log

**Files:**
- Modify: `wiki/concepts/node-model.md` (append a Revisions block —
  scoped to A1/A2 as W3-shipped, recorded retroactively in T39)
- Modify: `wiki/concepts/network-model.md` (Revisions block for
  B1 W3-shipped + B3 new in T39)
- Modify: `wiki/concepts/simulation-design.md` (Revisions block for
  B2 new in T39, plus inbound `[[concepts/runner]]` link in the
  Bootstrap section)
- Modify: `wiki/concepts/reproducibility.md` (one bullet adding
  `[[concepts/runner]]` to the harness-level contract list)
- Modify: `wiki/index.md` (add one `Concepts` entry for
  `[[concepts/runner]]`)
- Modify: `wiki/log.md` (append one entry per `docs/wiki-spec.md`
  § Log format)

### Step 1: Revisions blocks

Per `docs/wiki-spec.md` § Revisions rule — append, do not silently
overwrite. Date each block `2026-05-27`.

**`wiki/concepts/node-model.md`** Revisions block:

```markdown
## Revisions

- **2026-05-27 (T39, retroactive):** `Node.__init__` rejects
  `node_id < 0` with `ValueError` (A1; `node_id = -1` is the
  `PhaseAdvance` sentinel — would scramble `(t, node_id, seq)`
  ordering) and non-finite `weight` with `ValueError` (A2;
  `float('nan') < 0` is `False`, so the existing `weight < 0` check
  let `NaN` / `±inf` slip past). Both guards shipped with T22; T39
  records them here against the backlog closure. Test surface:
  `tests/nodes/test_node.py::test_negative_node_id_rejected`,
  `test_nan_weight_rejected`, `test_pos_inf_weight_rejected`,
  `test_neg_inf_weight_rejected`.
```

**`wiki/concepts/network-model.md`** Revisions block:

```markdown
## Revisions

- **2026-05-27 (T39):** `Network.register(node)` rejects duplicate
  `node.id` with `ValueError` (B1; shipped with T23, recorded here
  against the backlog closure — symmetric with the unregistered-`dst`
  `KeyError` in `_try_deliver`). `Network.start()` rejects a second
  call with `RuntimeError` (B3; new in T39 — re-running `start` would
  re-schedule every interior `PhaseAdvance` boundary, double-firing
  phase rollovers). Test surface:
  `tests/network/test_network.py::test_duplicate_register_rejected`,
  `test_start_rejects_double_call`.
```

**`wiki/concepts/simulation-design.md`** Revisions block:

```markdown
## Revisions

- **2026-05-27 (T39):** `Scheduler.bind(node)` rejects duplicate
  `node.id` with `ValueError` (B2; symmetric with the
  unregistered-`node_id` `KeyError` path in `_dispatch._node`). The
  post-build half of the six-phase bootstrap is now
  `[[concepts/runner]]` — `run_to_completion(handle, *, t_max,
  logger) -> (RunResult, EventLogger)`. Test surface:
  `tests/scheduler/test_scheduler.py::test_bind_rejects_duplicate_node_id`,
  `tests/common/test_runner.py`.
```

Insert the inbound link inside the Bootstrap section of
`simulation-design.md` — one sentence, locating the appropriate
paragraph (the one describing post-`start` execution): `Post-build
execution is owned by [[concepts/runner]].`

### Step 2: Reproducibility inbound link

In `wiki/concepts/reproducibility.md`, locate the harness-level
contract list (the section listing the per-component determinism
contracts — `[[concepts/node-model]] §8`,
`[[concepts/network-model-phases]] §6`,
`[[concepts/simulation-design-runtime]] §1`). Append one bullet:

```markdown
- `[[concepts/runner]]` — pass-through runner contract: attaching the
  logger and entering `scheduler.run()` introduces no new RNG, no
  reordering, no scheduler-layer adversary surface.
```

### Step 3: `wiki/index.md` entry

Under `## Concepts`, insert (alphabetically — between
`[[concepts/reproducibility]]` and any later `r` entries; if none,
after `reproducibility`):

```markdown
- [[concepts/runner]] — Post-build half of the six-phase bootstrap:
  `run_to_completion(handle, *, t_max, logger)` attaches an
  EventLogger, runs the scheduler to its stop condition, returns
  `(RunResult, EventLogger)`. Pairs with
  `[[concepts/simulation-design]]` (build half); pass-through
  determinism (no new RNG, no scheduler-layer adversary); T40 owns
  CSV columns, T41+ owns sweeps, T18 owns adversary wiring.
```

### Step 4: `wiki/log.md` entry

Append (per `docs/wiki-spec.md` § Log format):

```markdown
## [2026-05-27] code | task 39 — unified runner + fail-fast seam hardening

- role: Engineer
- touched: src/common/runner.py, src/common/__init__.py,
    src/scheduler/scheduler.py, src/network/network.py,
    tests/common/test_runner.py, tests/scheduler/test_scheduler.py,
    tests/network/test_network.py,
    tests/integration/test_pbft_baseline.py,
    tests/integration/test_pos_baseline.py,
    tests/integration/test_snowman_baseline.py,
    src/pos/baseline.py, Makefile,
    wiki/concepts/runner.md,
    wiki/concepts/node-model.md, wiki/concepts/network-model.md,
    wiki/concepts/simulation-design.md, wiki/concepts/reproducibility.md,
    wiki/index.md, TASKS.md
- notes: Lands the post-build run helper run_to_completion(handle, *,
    t_max, logger) → (RunResult, EventLogger), collapsing ~12 LoC of
    duplicated bootstrap-tail boilerplate across four callers. Closes
    two bootstrap-seam fail-fast holes new in T39 (Scheduler.bind on
    duplicate node_id; Network.start on second call); records the
    three already-shipped W3 guards (A1/A2/B1) against the backlog
    closure. T35-local CSV schema in src/pos/baseline.py untouched —
    T40 owns reconciliation per [[concepts/output-format]] when it
    lands. T39 entry rewritten to drop the W7-buffer counterfactual
    framing.
```

### Step 5: Commit

Stage all the wiki edits as one logical change:

```
git add wiki/concepts/runner.md wiki/concepts/node-model.md \
        wiki/concepts/network-model.md wiki/concepts/simulation-design.md \
        wiki/concepts/reproducibility.md wiki/index.md wiki/log.md
```

Commit message (wiki-only convention per `docs/workflow.md`):

```
wiki: T39 runner concept + 3 Revisions blocks + index/log
```

---

## Task 12: TASKS.md edits — T39 entry rewrite + append-resolves

**Files:**
- Modify: `TASKS.md` (Dashboard line, T39 entry, two Backlog items)

### Step 1: Rewrite T39 entry (line 203)

Current:

```
- `[~]` **T39** `H` Engineer — If buffer: stabilize PBFT & PoS, fix bugs, unify interface
  _Outcome:_ Known bugs fixed, edge cases handled, unified `run()` interface · _Artifact:_ `src/common/runner.py`
```

Replace with (mirroring T29's 2026-05-21 rewrite pattern):

```
- `[?]` **T39** `H` Engineer — Unified `run()` interface (run_to_completion) + bootstrap-seam fail-fast hardening (superseded 2026-05-27 by W7 decision; original framing assumed the buffer branch the T37 decision did not take)
  _Outcome:_ One helper `run_to_completion(handle, *, t_max, logger) -> (RunResult, EventLogger)` in `src/common/runner.py` collapses the bootstrap tail four callers duplicate (three integration baselines + `src/pos/baseline.py`); five fail-fast guards close the bootstrap seam (A1 `node_id < 0`, A2 non-finite `weight`, B1 duplicate `Network.register`, B2 duplicate `Scheduler.bind`, B3 double `Network.start` — A1/A2/B1 shipped with T22/T23, B2/B3 new in T39); byte-identical determinism and byte-identical `results/pos/baseline.csv` pre/post migration; CSV columns deliberately untouched (T40 owns `[[concepts/output-format]]`); no adversary hook (T18); no multi-seed sweep (T41+). · _Artifact:_ `src/common/runner.py`, `src/common/__init__.py`, `tests/common/test_runner.py`, `wiki/concepts/runner.md`, `## Revisions` blocks on `[[concepts/node-model]]` / `[[concepts/network-model]]` / `[[concepts/simulation-design]]`
```

Status flips `[~]` → `[?]`.

### Step 2: Append-resolve backlog item 304

Locate the backlog bullet starting with **`Node.__init__` accepts
non-finite `weight`** (line 304). Append at the end of that bullet:

```
**Resolved 2026-05-27 by T39:** A2 guard in `Node.__init__` (shipped
with T22; recorded in T39's `[[concepts/node-model]]` ## Revisions);
covered by `tests/nodes/test_node.py::test_nan_weight_rejected` +
`test_pos_inf_weight_rejected` + `test_neg_inf_weight_rejected`.
```

### Step 3: Append-resolve backlog item 305

Locate the bullet starting with **`Network.register` / `Scheduler.bind`
/ `Network.start` lack fail-fast collision-or-repeat checks** (line
305). Append:

```
**Resolved 2026-05-27 by T39:** all four guards land — A1
(`Node.__init__` rejects `node_id < 0`, shipped with T22), B1
(`Network.register` rejects duplicate `node.id`, shipped with T23),
B2 (`Scheduler.bind` rejects duplicate `node.id`, new in T39), B3
(`Network.start` rejects second call, new in T39). Recorded in
T39's `[[concepts/node-model]]` / `[[concepts/network-model]]` /
`[[concepts/simulation-design]]` ## Revisions blocks. Covered by
the corresponding one-test-per-guard suite.
```

### Step 4: Recompute Dashboard arithmetic (line 9)

Current:

```
- Completed: 56 · In Review: 2 · In Progress: 1 · Not Started: 31 · Blocked: 3
```

T39 flips `[~]` → `[?]`: In Progress −1, In Review +1.

Replace with:

```
- Completed: 56 · In Review: 3 · In Progress: 0 · Not Started: 31 · Blocked: 3
```

(Confirm by `/usr/bin/grep -c '^- `\[[ ~?x!]\]' TASKS.md` if any
discrepancy is suspected; the dashboard backlog item at line 296 notes
"Watch for re-drift during future flips.")

### Step 5: Commit

```
task 39: implement run_to_completion + B2/B3 guards; close W3 backlog
```

Stage:

```
git add src/common/__init__.py src/common/runner.py \
        src/scheduler/scheduler.py src/network/network.py \
        src/pos/baseline.py \
        tests/common/test_runner.py \
        tests/scheduler/test_scheduler.py \
        tests/network/test_network.py \
        tests/integration/test_pbft_baseline.py \
        tests/integration/test_pos_baseline.py \
        tests/integration/test_snowman_baseline.py \
        Makefile TASKS.md
```

> **Note:** if Tasks 1–9 each committed independently, this final commit
> is TASKS.md-only (the source/test files are already in earlier
> commits). Adjust the `git add` accordingly. The workflow doc allows
> either grouping — one logical change per commit, scope-disciplined.

### Step 6: Run `superpowers:verification-before-completion`

Per the Engineer role prompt — invoke that skill before announcing
ready-for-review. The acceptance checklist below is the input.

---

## 8. Acceptance criteria (mirror of spec §8)

T39 is ready to flip to In Review (Engineer hands off to human merge)
when **all** of the following hold. Tick each in the handoff summary.

- [ ] `src/common/runner.py` exists with the spec §2.2 signature
  (verified by Task 3 + Task 4 `make test-common`).
- [ ] All five guards (A1, A2, B1, B2, B3) are in place with the
  corresponding tests:
  - A1/A2: pre-existing in `tests/nodes/test_node.py`.
  - B1: pre-existing in `tests/network/test_network.py`.
  - B2: new in `tests/scheduler/test_scheduler.py` (Task 1).
  - B3: new in `tests/network/test_network.py` (Task 2).
- [ ] All four callers (M1, M2, M3, M4) use `run_to_completion`; the
  `EventLogger` import is removed from any caller that no longer uses
  it directly (Tasks 6–9).
- [ ] `make test` green from a clean checkout (§M-verify); every
  existing `test_determinism*` case still passes byte-identical.
- [ ] `src/pos/baseline.py`'s `results/pos/baseline.csv` output is
  byte-identical pre/post (Task 9 Step 3 — `shasum -c` against
  `/tmp/t39-pos-baseline.sha`).
- [ ] `wiki/concepts/runner.md` exists; three `## Revisions` blocks
  added to `node-model.md` / `network-model.md` /
  `simulation-design.md`; one inbound bullet on `reproducibility.md`;
  `wiki/index.md` updated; `wiki/log.md` appended (Tasks 10–11).
- [ ] `TASKS.md`: T39 entry rewritten, two backlog items append-
  resolved, dashboard recomputed (Task 12).
- [ ] `superpowers:verification-before-completion` invoked; the
  handoff summary records pre/post test counts (from `/tmp/t39-pre.log`
  vs the §M-verify capture), the `results/pos/baseline.csv` sha256
  match, and any deferred observations.

---

## Handoff summary template (for the In-Review post)

```markdown
T39 — In Review.

Files touched:
- src/common/__init__.py (new)
- src/common/runner.py (new)
- src/scheduler/scheduler.py (B2 guard)
- src/network/network.py (B3 guard)
- src/pos/baseline.py (M4 migration)
- tests/common/test_runner.py (new; 6 tests)
- tests/scheduler/test_scheduler.py (B2 test)
- tests/network/test_network.py (B3 test)
- tests/integration/test_pbft_baseline.py (M1 migration)
- tests/integration/test_pos_baseline.py (M2 migration)
- tests/integration/test_snowman_baseline.py (M3 migration)
- Makefile (`common` suite registered)
- wiki/concepts/runner.md (new)
- wiki/concepts/node-model.md (Revisions)
- wiki/concepts/network-model.md (Revisions)
- wiki/concepts/simulation-design.md (Revisions + inbound link)
- wiki/concepts/reproducibility.md (inbound bullet)
- wiki/index.md (one entry)
- wiki/log.md (one entry)
- TASKS.md (T39 entry rewrite + two backlog append-resolves + dashboard)

Wiki pages added/updated: runner (new); node-model, network-model,
simulation-design, reproducibility, index, log (updated).

Decisions made:
- A1/A2/B1 found already shipped with T22/T23 — treated as verify-only
  and recorded retroactively in the new Revisions blocks (no
  duplicate-implementation churn). B2 and B3 are the only new guards.
- T35-local CSV schema in src/pos/baseline.py left untouched per the
  scope agreement; T40 owns the reconciliation.
- Approach 2 one-shot `run(config, seed, factory, …)` deliberately
  deferred (YAGNI; spec §2.4).

Open questions: none.

Verification:
- make test: <pre-count> → <post-count> tests, all green.
- results/pos/baseline.csv sha256 byte-identical pre/post: <hash>.
- every test_determinism* case passes byte-identical pre/post.
```
