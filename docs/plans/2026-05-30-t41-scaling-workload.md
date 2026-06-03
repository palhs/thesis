# T41 — Scaling Baseline + Workload Axis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the single-seed T40 baseline into a multi-seed scaling sweep (`n ∈ {4,7,10,16,25}` × seeds `0–19`, common random numbers) driven by a real deterministic transaction workload, landing the `workload_*`, `goodput`, and `bytes_per_acu` CSV columns.

**Architecture:** A new seeded `src/workload/` generator produces a deterministic list of per-proposal transaction batches from `global_seed`; every node receives the identical list and the proposer at opportunity `k` indexes `batches[k]`. Protocol mechanics and instance/block counts are preserved (PBFT moves to a `t_max` window so its throughput is comparable). New columns are added to the existing pure-reducer CSV pipeline; output moves to `results/baseline/`.

**Tech Stack:** Python 3 stdlib only (`random`, `hashlib`, `statistics`, `csv`, `dataclasses`), `unittest`, Makefile suites. No new external dependencies.

**Spec:** `docs/superpowers/specs/2026-05-30-t41-scaling-workload-design.md` (read it first).

**Branch:** `task/T41-scaling-workload`. **The human commits every step — do NOT run `git commit`.** Where a step says "Commit", stage the listed files and *propose* the commit message to the human; they run it.

---

## Conventions for the executor

- Run tests with: `make test-<suite>` (e.g. `make test-workload`), or directly
  `PYTHONPATH=src:tests/<suite> python3 -m unittest discover -s tests/<suite> -v`.
- All simulator code assumes `PYTHONPATH=src`.
- Determinism is the cardinal contract: the only randomness source is an RNG
  seeded off `global_seed` via `hashlib.blake2b`. Never use `random` module-level
  functions, `Date`, or wallclock.
- Keep reducers **pure** (no I/O, no clock, no RNG, no side effects).
- Match the surrounding code's register: module docstring naming the task +
  design contract, `from __future__ import annotations`, frozen dataclasses.

---

## Phase 0 — Scaffolding

### Task 0.1: Register the `workload` test suite + results dir

**Files:**
- Modify: `Makefile` (the `SUITES = ...` line)
- Create: `tests/workload/__init__.py` (empty)
- Create: `results/baseline/.gitkeep` (empty)

**Step 1:** Add `workload` to the `SUITES` variable in `Makefile` (alphabetical
or appended — match existing style). Confirm `make test-workload` resolves
(it will find no tests yet — that's fine).

**Step 2:** `touch tests/workload/__init__.py results/baseline/.gitkeep`.

**Step 3:** Run `make test-workload` — expect "Ran 0 tests" (suite discovered, empty).

**Step 4 (Commit):** propose `task 41: register workload test suite + results/baseline dir`.

### Task 0.2: .gitignore — retire flat baseline CSVs, admit results/baseline/

**Files:** Modify: `.gitignore` (lines ~19–20)

**Step 1:** Remove the two negations `!results/baseline.csv` and
`!results/snowman_n4_sanity.csv`. Add:
```
!results/baseline/
!results/baseline/*.csv
```
(so the committed canonical CSVs live under `results/baseline/`, consistent
with the prior force-include-the-baseline convention).

**Step 2:** `git rm --cached results/baseline.csv results/snowman_n4_sanity.csv`
will be proposed to the human at the orchestrator step (Phase 5), not here —
the files are still produced by the old orchestrator until then.

**Step 3 (Commit):** propose `task 41: point .gitignore at results/baseline/`.

---

## Phase 1 — Workload generator (`src/workload/`)

The generator is a pure function of `(params, global_seed)` returning a
deterministic list of transaction batches, one per proposal opportunity.

### Task 1.1: WorkloadConfig + seed derivation

**Files:**
- Create: `src/workload/__init__.py`
- Create: `src/workload/generator.py`
- Test: `tests/workload/test_generator.py`

**Step 1: Write failing test** (`tests/workload/test_generator.py`):
```python
import math, unittest
from workload import WorkloadConfig, generate_batches

class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_stream(self):
        cfg = WorkloadConfig(arrival_process="poisson", offered_rate=100.0,
                             tx_bytes=512, conflict_rate=0.0)
        a = generate_batches(cfg, global_seed=42, n_opportunities=20,
                             interval=1.0)
        b = generate_batches(cfg, global_seed=42, n_opportunities=20,
                             interval=1.0)
        self.assertEqual(a, b)

    def test_different_seed_differs(self):
        cfg = WorkloadConfig("poisson", 100.0, 512, 0.0)
        a = generate_batches(cfg, 42, 20, 1.0)
        b = generate_batches(cfg, 7, 20, 1.0)
        self.assertNotEqual(a, b)
```

**Step 2:** Run `make test-workload` — expect FAIL (`ImportError`).

**Step 3: Implement** (`src/workload/generator.py`):
```python
"""T41 — deterministic transaction-workload generator.

A pure function of (WorkloadConfig, global_seed) producing a list of
per-proposal transaction batches. The same list is handed to every node;
the proposer at opportunity k uses batches[k] (spec §4.2), so batch
content is independent of which node proposes.

Design spec: docs/superpowers/specs/2026-05-30-t41-scaling-workload-design.md
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkloadConfig:
    arrival_process: str   # "poisson" | "constant"
    offered_rate: float    # tx/s
    tx_bytes: int          # payload width per tx
    conflict_rate: float   # held 0.0 in T41


def _workload_seed(global_seed: int) -> int:
    digest = hashlib.blake2b(b"workload:" + str(global_seed).encode(),
                             digest_size=8).digest()
    return int.from_bytes(digest, "big")


def _tx(opportunity: int, idx: int, tx_bytes: int) -> bytes:
    """A distinct tx payload of exactly tx_bytes, content-stable per
    (opportunity, idx). conflict_rate=0 ⇒ every tx is unique/independent."""
    seed = f"{opportunity}:{idx}".encode()
    return hashlib.blake2b(seed, digest_size=tx_bytes).digest() if tx_bytes <= 64 \
        else (seed * (tx_bytes // len(seed) + 1))[:tx_bytes]


def _batch_size(rng: random.Random, cfg: WorkloadConfig,
                interval: float) -> int:
    expected = cfg.offered_rate * interval
    if cfg.arrival_process == "constant":
        return round(expected)
    if cfg.arrival_process == "poisson":
        # Knuth Poisson sampler — pure, RNG-driven.
        import math
        L, k, p = math.exp(-expected), 0, 1.0
        while True:
            k += 1
            p *= rng.random()
            if p <= L:
                return k - 1
    raise ValueError(f"unknown arrival_process {cfg.arrival_process!r}")


def generate_batches(cfg: WorkloadConfig, global_seed: int,
                     n_opportunities: int, interval: float
                     ) -> tuple[tuple[bytes, ...], ...]:
    """Return n_opportunities batches; batch k holds the tx that arrive in
    the k-th proposal interval (size ~ arrival process over `interval`)."""
    rng = random.Random(_workload_seed(global_seed))
    batches = []
    for k in range(n_opportunities):
        size = _batch_size(rng, cfg, interval)
        batches.append(tuple(_tx(k, i, cfg.tx_bytes) for i in range(size)))
    return tuple(batches)
```
`src/workload/__init__.py`:
```python
from .generator import WorkloadConfig, generate_batches
__all__ = ["WorkloadConfig", "generate_batches"]
```

**Step 4:** Run `make test-workload` — expect PASS.

**Step 5 (Commit):** propose `task 41: deterministic workload generator`.

### Task 1.2: Arrival-rate / distribution check

**Files:** Test: `tests/workload/test_generator.py` (extend)

**Step 1: Write failing test** — over many seeds, the mean batch size lands
near `offered_rate × interval`, and `constant` is exact:
```python
class TestRate(unittest.TestCase):
    def test_constant_is_exact(self):
        cfg = WorkloadConfig("constant", 100.0, 512, 0.0)
        batches = generate_batches(cfg, 0, 20, 1.0)
        self.assertTrue(all(len(b) == 100 for b in batches))

    def test_poisson_mean_in_tolerance(self):
        cfg = WorkloadConfig("poisson", 100.0, 512, 0.0)
        sizes = [len(b) for s in range(40)
                 for b in generate_batches(cfg, s, 20, 1.0)]
        mean = sum(sizes) / len(sizes)
        self.assertAlmostEqual(mean, 100.0, delta=5.0)  # ~800 samples
```

**Step 2:** Run — expect PASS (generator already correct). If the Poisson mean
test is flaky at the chosen delta, widen delta or sample count; do **not**
re-seed with wallclock.

**Step 3 (Commit):** propose `task 41: workload arrival-rate distribution test`.

---

## Phase 2 — CSV schema extension

### Task 2.1: Add workload fields to ScenarioMeta + columns to COLUMN_ORDER

**Files:**
- Modify: `src/output/schema.py`
- Test: `tests/output/test_schema.py` (create if absent; else extend)

**Step 1: Write failing test:**
```python
from output.schema import COLUMN_ORDER, ScenarioMeta
def test_new_columns_present():
    for c in ("workload_arrival_process","workload_tx_bytes",
              "workload_conflict_rate","workload_offered_rate",
              "goodput","bytes_per_acu"):
        assert c in COLUMN_ORDER
def test_meta_carries_workload():
    m = ScenarioMeta(run_id="x",protocol="pbft",n=4,variant=None,seed=0,
                     t_max=20.0,arrival_process="poisson",tx_bytes=512,
                     conflict_rate=0.0,offered_rate=100.0)
    assert m.offered_rate == 100.0
```

**Step 2:** Run `make test-output` — expect FAIL.

**Step 3: Implement.** In `src/output/schema.py`:
- Add four fields to `ScenarioMeta` (frozen dataclass), **with defaults** so
  existing constructions stay valid during migration:
  `arrival_process: str = "poisson"`, `tx_bytes: int = 512`,
  `conflict_rate: float = 0.0`, `offered_rate: float = 100.0`.
- Extend `COLUMN_ORDER`. Insert the four `workload_*` columns in the identity/
  reproducibility region (after `t_max`), and `goodput` next to `tps`,
  `bytes_per_acu` next to the `*_per_acu` columns — mirror the §3 schema
  grouping in `output-format.md`. Keep it a single tuple.

**Step 4:** Run `make test-output` — expect PASS.

**Step 5 (Commit):** propose `task 41: extend CSV schema with workload + goodput + bytes_per_acu columns`.

### Task 2.2: Generic columns emit workload_* ; float formatting

**Files:** Modify: `src/output/csv.py`; Test: `tests/output/` (extend)

**Step 1: Write failing test** asserting a built row carries
`workload_offered_rate` and that `_format_row` renders `goodput`,
`bytes_per_acu` at `.6f`.

**Step 2:** Run — expect FAIL.

**Step 3: Implement:**
- In `_generic_cols`, add the four `workload_*` keys read from `meta`
  (they are generic — identical column for all protocols). Add them to
  `_GENERIC_COLUMNS`.
- In `_format_row`, add `goodput` and `bytes_per_acu` to the `.6f` set;
  `workload_arrival_process` is a str (passthrough), the numeric workload
  cols use `str()` (int/float passthrough as today's non-special cols).

**Step 4:** Run `make test-output` — expect PASS.

**Step 5 (Commit):** propose `task 41: emit workload columns from generic cols`.

---

## Phase 3 — goodput + bytes_per_acu in the reducers

`goodput` and `bytes_per_acu` are per-protocol (they live in each
`summarise.py`), computed purely from `(records, result, meta)`. They share
two helpers placed in a new `src/output/metrics.py` so the three reducers
stay DRY.

### Task 3.1: Shared metric helpers

**Files:**
- Create: `src/output/metrics.py`
- Test: `tests/output/test_metrics.py`

**Definitions (spec §4.3):**
- `goodput = committed_tx / time_denom`, where
  `committed_tx = Σ len(batches[k]) for k in range(n_decided_instances)`
  regenerated deterministically from `(meta.seed, meta workload params,
  per-protocol interval, n_decided)`; `time_denom` matches the protocol's
  `tps` rule — `result.now` for PBFT, `meta.t_max` for FFG/Snowman.
- `bytes_per_acu = Σ_{delivery} base_budget[msg_type] / decided_count`, where
  `base_budget` is the fixed per-type width from `message-types.md` §3–§7,
  and transaction-carrying types (`PRE-PREPARE`, `BLOCK-PROPOSAL`,
  `BLOCK-ANNOUNCEMENT`) add `expected_batch × tx_bytes` with
  `expected_batch = offered_rate × interval`. **Honest order-of-magnitude
  estimate** (budgets non-binding, message-types §7); label as such on the
  experiment page.

**Step 1: Write failing tests** for both helpers with hand-built
`EventRecord` lists and a known batch stream (assert exact values).

**Step 2:** Run `make test-output` — expect FAIL.

**Step 3: Implement `src/output/metrics.py`:**
```python
"""T41 — shared workload-derived metric helpers (goodput, bytes_per_acu).

Pure functions over (records, result, meta) + the deterministic batch
stream. Used by the three per-protocol reducers. See output-format.md §5
and the T41 spec §4.3.
"""
from __future__ import annotations
from event_log import EventRecord
from scheduler import RunResult
from output.schema import ScenarioMeta
from workload import WorkloadConfig, generate_batches

# Fixed per-message-type byte budgets from wiki/concepts/message-types.md
# §3–§7 (non-binding order-of-magnitude). TX-carrying types get the tx
# payload added at call time. Fill exact values by reading the message-types
# Size(bytes) columns during implementation.
_BASE_BUDGET = {
    # "PRE-PREPARE": ..., "PREPARE": ..., "COMMIT": ...,
    # "BLOCK-PROPOSAL": ..., "ATTESTATION": ...,
    # "BLOCK-ANNOUNCEMENT": ..., "QUERY": ..., "QUERY-RESPONSE": ...,
}
_TX_CARRYING = {"PRE-PREPARE", "BLOCK-PROPOSAL", "BLOCK-ANNOUNCEMENT"}

def _decided(records): return [r for r in records if r.event_type == "decided"]

def goodput(records, result, meta, *, interval, time_denom) -> float:
    decided = _decided(records)
    n_inst = len({r.fields.get("instance_id") for r in decided})
    if n_inst == 0 or time_denom <= 0:
        return float("nan")
    cfg = WorkloadConfig(meta.arrival_process, meta.offered_rate,
                         meta.tx_bytes, meta.conflict_rate)
    batches = generate_batches(cfg, meta.seed, n_inst, interval)
    committed_tx = sum(len(b) for b in batches)
    return committed_tx / time_denom

def bytes_per_acu(records, result, meta, *, interval) -> float:
    decided = _decided(records)
    if not decided:
        return float("nan")
    expected_batch = meta.offered_rate * interval
    total = 0.0
    for r in records:
        if r.event_type != "delivery":
            continue
        mt = r.fields.get("msg_type")
        b = _BASE_BUDGET.get(mt, 0)
        if mt in _TX_CARRYING:
            b += expected_batch * meta.tx_bytes
        total += b
    return total / len(decided)
```
Read `wiki/concepts/message-types.md` §3–§7 and fill `_BASE_BUDGET` with the
documented `Size (bytes)` per type. Add a test that every msg_type the three
protocols actually emit (grep `broadcast(`/`send(` in `src/{pbft,pos,snowman}`)
has a `_BASE_BUDGET` entry, so an unbudgeted type fails fast rather than
silently scoring 0.

**Step 4:** Run `make test-output` — expect PASS.

**Step 5 (Commit):** propose `task 41: shared goodput + bytes_per_acu helpers`.

### Task 3.2: Wire helpers into the three reducers

**Files:** Modify `src/pbft/summarise.py`, `src/pos/summarise.py`,
`src/snowman/summarise.py`; Tests: extend each `tests/<p>/test_summarise.py`.

Each reducer adds two keys, `goodput` and `bytes_per_acu`, passing its own
`interval` (PBFT `propose_delay`; FFG/Snowman `slot_duration`) and `time_denom`
(PBFT `result.now`; FFG/Snowman `meta.t_max`). The interval constants live in
the protocol's `baseline.py` — import or pass via `meta`. Simplest: add a
`interval: float` field to `ScenarioMeta` (default matching each protocol),
set per scenario, so the reducer reads `meta.interval`. (Update Task 2.1 test
accordingly if you take this route — decide before implementing and keep one
source of truth.)

**TDD per reducer:** failing test asserting the two new keys with known inputs
→ implement → pass → commit (`task 41: <protocol> reducer goodput + bytes_per_acu`).

---

## Phase 4 — Wire batches into baselines + scenario expansion

### Task 4.1: PBFT — windowed run + batch workload

**Files:** Modify `src/pbft/baseline.py`; Test: `tests/pbft/` + `tests/integration/test_pbft_baseline.py`.

**Changes:**
- `_config(n)`: set `t_max = _T_MAX` (new constant, **20.0** to match FFG/Snowman)
  instead of `math.inf`; `ScenarioMeta.t_max = _T_MAX`.
- `_factory`: build `batches = generate_batches(WorkloadConfig(...), global_seed,
  n_opportunities=ceil(_T_MAX/PROPOSE_DELAY)+2, interval=PROPOSE_DELAY)`. The
  primary's `workload` becomes `[<batch> for batch in batches]` — i.e. one
  *request per instance is a batch tuple*. Non-primaries get `None` (they don't
  propose). `PROPOSE_DELAY` stays 1.0.
- The PBFT request payload is now a batch (`tuple[bytes,...]`); confirm
  `digest()` / `PrePreparePayload.request` accept it (they treat the request as
  opaque bytes-ish — verify; if `digest` needs bytes, join or hash the tuple).
- `SCENARIOS`: expand to `n ∈ {4,7,10,16,25} × seed ∈ range(20)`; `run_id`
  is `pbft-n{n}` (seed disambiguates rows, output-format §8). Set workload
  fields on each `ScenarioMeta`.

**TDD:** test that PBFT now decides **multiple** instances within the window
(not 1), first-instance latency unchanged, determinism holds. Then commit
(`task 41: PBFT windowed batch workload + scenario sweep`).

### Task 4.2: Casper FFG — batch workload + sweep

**Files:** Modify `src/pos/baseline.py`; Tests: `tests/pos/` + integration.

**Changes:**
- `_factory`: every node receives the identical `batches` list
  (`generate_batches(..., interval=_SLOT_DURATION, n_opportunities=
  ceil(_T_MAX/_SLOT_DURATION)+2)`); the round-robin proposer at `slot` uses
  `batches[slot]`. Pass `workload=[list(b) for b in batches]` (the node pops
  per slot via `_workload_cursor`; confirm cursor indexes by slot — if it pops
  sequentially per proposal, the proposer only advances on its own slots, so
  index explicitly by slot instead of popping). **Resolve the cursor-vs-slot
  indexing by reading `pos/node.py` `_propose`** and pick the slot-indexed form.
- `SCENARIOS`: `n ∈ {4,7,10,16,25} × seed ∈ range(20)` with `variant="uniform"`,
  **plus** the retained `casper-ffg-n4-nonuniform × seed ∈ range(20)`.

**TDD:** epoch/decided counts unchanged vs T40 at seed=42; determinism. Commit
(`task 41: Casper FFG batch workload + scenario sweep`).

### Task 4.3: Snowman — batch workload + sweep

**Files:** Modify `src/snowman/baseline.py`; Tests: `tests/snowman/` + integration.

**Changes:** same batch-by-slot wiring (`interval=_SLOT_DURATION`); confirm
whether each node announces its own block per slot or a single per-slot
proposer (read `snowman/node.py` `_propose`) and index `batches[slot]`
accordingly so all announcers at slot k carry identical batch content.
`SCENARIOS`: `n ∈ {4,7,10,16,25} × seed ∈ range(20)` (n=4 stays in SCENARIOS;
the writer routes it to the sanity file).

**TDD:** block/decided counts unchanged vs T40 at seed=42; determinism. Commit
(`task 41: Snowman batch workload + scenario sweep`).

---

## Phase 5 — Orchestrator + output layout

### Task 5.1: Multi-seed orchestrator → results/baseline/

**Files:** Modify `src/output/baseline.py`, `src/output/csv.py` (sanity path);
Tests: `tests/output/test_baseline_e2e.py`.

**Changes:**
- `_OUT = Path("results/baseline/baseline.csv")`,
  `_SANE = Path("results/baseline/snowman_n4_sanity.csv")`.
- `_collect_runs` already iterates each protocol's `SCENARIOS`; with the
  expanded tuples it now yields ~320 runs. No structural change needed beyond
  the larger iteration. Keep the single commit-hash snapshot.
- The Snowman n=4 sanity emission: with 20 seeds there are 20 n=4 runs; write
  **all** to the sanity file (loop, not `break`). Update `sanity_row` /
  the writer to append multiple rows (or collect n=4 runs and write once).
- Confirm `write_unified_csv` still skips Snowman n=4 from the main file.

**Step — propose to human:** `git rm --cached results/baseline.csv
results/snowman_n4_sanity.csv` (retire flat files) alongside this commit.

**TDD:** e2e test — two orchestrator runs (commit hash monkeypatched) produce
byte-identical `results/baseline/baseline.csv`; row count == expected
(280 main); sanity file has 20 rows. Commit (`task 41: multi-seed orchestrator to results/baseline/`).

---

## Phase 6 — Regression + determinism guards

### Task 6.1: Latency-column stability regression

**Files:** Test: `tests/output/test_t40_stability.py` (new)

**Step 1:** Capture the T40 latency values (`commit_latency_ms`,
`finality_latency_ms`) for the seed=42 rows of all three protocols (from the
prior `results/baseline.csv` committed in git history, or recompute by running
each protocol's `run_scenario` at seed=42). Assert the post-workload pipeline
reproduces them **byte-identically** for PBFT/FFG/Snowman, and that **all**
FFG/Snowman landed columns (not just latency) are unchanged at seed=42.

**Step 2–4:** Run; expect PASS (the batch wiring must not move these). If PBFT
latency moved, the windowing broke the first-instance definition — STOP and
debug (spec §4.2 says it must not move).

**Step 5 (Commit):** propose `task 41: T40 latency-stability regression guard`.

---

## Phase 7 — Generate the dataset

### Task 7.1: Run the sweep

**Step 1:** `PYTHONPATH=src python3 -m output.baseline`.
**Step 2:** Verify `results/baseline/baseline.csv` (280 rows + header) and
`results/baseline/snowman_n4_sanity.csv` (20 rows + header) exist and parse.
**Step 3:** Re-run; confirm byte-identical (determinism).
**Step 4 (Commit):** propose `task 41: generate scaling-baseline dataset` (stage
the two CSVs under results/baseline/).

---

## Phase 8 — Wiki + verification

### Task 8.1: Revisions on output-format + experiment-matrix

**Files:** Modify `wiki/concepts/output-format.md`, `wiki/concepts/experiment-matrix.md`.

- `output-format.md`: §11 register — flip `workload_*`, `goodput`,
  `bytes_per_acu` to `live`; add `## Revisions` (2026-05-30, T41) noting PBFT
  `tps`/overhead re-baselined to windowed values (§5.1), and that `peak_tps`
  stays pending pending a capacity model.
- `experiment-matrix.md`: `## Revisions` (2026-05-30, T41) — `peak_tps` /
  offered-load ramp deferred: latency-only model cannot saturate; needs a
  capacity/cost model. `offered_rate = 100` tx/s used, not recalibrated.

Commit: `task 41: wiki revisions for workload axis + peak_tps deferral`.

### Task 8.2: Experiment page

**Files:** Create `wiki/experiments/2026-05-30_scaling-baseline.md`.

Include (Engineer role + wiki-spec): config (n-set, seeds 0–19, CRN, workload
defaults, per-protocol interval/t_max), commit hash, exact re-run command
(`PYTHONPATH=src python3 -m output.baseline`), raw-result location
(`results/baseline/`), a one-paragraph observation (e.g. all protocols sustain
100 tx/s at all n — no saturation, as the model predicts; latency-vs-n trend;
bytes_per_acu growth with batch), the `bytes_per_acu` honest-estimate caveat,
and an **Auggie verification** subsection: log that `mcp__auggie__codebase-
retrieval` is unavailable in this environment and `augment_code_search` returns
`REPO_NOT_FOUND` for `palhs/thesis`; structural search used local grep/Read
(per spec §11). Back-link `[[concepts/output-format]]`,
`[[concepts/experiment-matrix]]`, `[[concepts/metric-reconciliation]]`,
`[[concepts/runner]]`.

Commit: `task 41: scaling-baseline experiment page`.

### Task 8.3: Index + log + verification-before-completion

**Files:** Modify `wiki/index.md` (add the experiment page under Experiments),
`wiki/log.md` (append the T41 entry per wiki-spec format).

**Step — verification:** invoke `superpowers:verification-before-completion`;
run `make test` (full suite) and paste the actual pass/fail output into the
handoff. Only then propose flipping `TASKS.md` T41 → `[?]` In Review and
recomputing the Dashboard counts.

Commit: `task 41: index + log + In Review`.

---

## Done criteria

- `make test` green (all suites, incl. `workload`).
- `results/baseline/baseline.csv`: 280 rows; `snowman_n4_sanity.csv`: 20 rows;
  both byte-identical on re-run.
- T40 latency columns reproduced byte-identically; FFG/Snowman all-column stable;
  PBFT throughput/overhead re-baselined (documented).
- `workload_*`, `goodput`, `bytes_per_acu` populated for all rows; register `live`.
- `peak_tps` deferral + PBFT re-baseline recorded as Revisions.
- Experiment page (with Auggie verification subsection), index, log updated.
- TASKS.md T41 → In Review; dashboard recomputed. **Human commits throughout.**
