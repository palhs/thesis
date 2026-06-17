# T46.1 — Resumable + Parallel Sweep Harness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. For each non-trivial task use superpowers:test-driven-development.

**Goal:** Make the experiment sweep harness resumable (per-cell checkpointing) and parallel (`--jobs N`) via a shared, grid-agnostic `src/common/sweep.py` driver, and prove via an induction-over-the-grid (mechanized witnesses + written argument) that any grid — including T47's — runs byte-identically regardless of jobs / resume / order.

**Architecture:** A new `run_grid(cells, run_cell, cell_key, *, checkpoint_dir, run_constants, param_fingerprint, jobs, fresh)` driver writes one fingerprinted sidecar per completed cell (atomic `os.replace`), skips cells whose valid sidecar exists on resume, runs cells sequentially (`jobs=1`, provenance default) or via `multiprocessing.Pool` (`jobs>1`), then collects by scanning the dir and sorting on `cell_key`. `src/delay/sweep.py` adopts it; `commit_hash` is resolved once in the parent and threaded as a constant. T41 baseline is untouched.

**Tech Stack:** Python 3 stdlib only (`multiprocessing`, `hashlib.blake2b`, `json`, `tempfile`, `os.replace`), `PYTHONPATH=src`, `unittest`. Determinism is sacred.

**Design spec:** `docs/superpowers/specs/2026-06-12-t46-1-sweep-harness-design.md`

**Commits:** This repo's humans commit and manage the `task/T46.1-sweep-harness` branch. Each task below ends with a **Commit checkpoint (human)** — STOP, summarize what changed, and let the human commit. Do NOT run `git commit`.

**Test commands (unittest, per-suite):**
- Whole suite: `make test-common` / `make test-delay`
- One test: `PYTHONPATH=src:tests/common python3 -m unittest test_sweep.TestName.test_method -v`
- Full gate before In Review: `make test`

---

## Task 0: Prep — checkpoint location + gitignore

**Files:**
- Modify: `.gitignore` (add `results/**/.sweep/`)

**Step 1:** Add `results/**/.sweep/` to `.gitignore`. Verify it does not collide with the existing `results/delay/*.csv` re-include (sidecars are `.json`, not `.csv`).

**Step 2:** Verify: `git check-ignore results/delay/.sweep/x.json` prints the path (ignored); `git check-ignore results/delay/delay.csv` prints nothing (still tracked).

**Commit checkpoint (human).**

---

## Task 1: `run_grid` driver — sequential core + sidecar + collect

The driver is developed against a **fake pure `run_cell`** (no protocol code), so the driver's determinism/resume logic is tested in isolation.

**Files:**
- Create: `src/common/sweep.py`
- Modify: `src/common/__init__.py` (export `run_grid`)
- Test: `tests/common/test_sweep.py`

**Step 1 — Write failing test: collect is sorted by `cell_key`, jobs=1.**

```python
# tests/common/test_sweep.py
import unittest, tempfile, json, os
from pathlib import Path
from common.sweep import run_grid

def _fake_run_cell(cell, run_constants):
    # pure: row is a deterministic function of the cell + constants
    proto, n, seed = cell
    return {"protocol": proto, "n": n, "seed": seed,
            "val": f"{proto}-{n}-{seed}", "hash": run_constants["commit_hash"]}

def _key(cell):
    proto, n, seed = cell
    return f"{proto}__n{n}__seed{seed:02d}"

def _fp(cell):
    return "fp-v1"  # constant fingerprint for the fake

class TestCollectOrder(unittest.TestCase):
    def test_rows_sorted_by_cell_key_regardless_of_input_order(self):
        cells = [("b", 7, 1), ("a", 4, 0), ("b", 7, 0)]
        with tempfile.TemporaryDirectory() as d:
            rows = run_grid(cells, _fake_run_cell, _key,
                            checkpoint_dir=Path(d)/".sweep",
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=1)
        keys = [_key((r["protocol"], r["n"], r["seed"])) for r in rows]
        self.assertEqual(keys, sorted(keys))
```

**Step 2 — Run, expect FAIL** (`ModuleNotFoundError: common.sweep`):
`PYTHONPATH=src:tests/common python3 -m unittest test_sweep.TestCollectOrder -v`

**Step 3 — Minimal implementation (sequential + sidecar + collect).**

```python
# src/common/sweep.py
"""Grid-agnostic, resumable, parallel sweep driver (T46.1).

run_grid runs a list of independent `cells` through a pure `run_cell`,
writing one fingerprinted sidecar per completed cell so a killed sweep
resumes and parallel workers never clobber. Output is byte-identical
across jobs / resume / completion order. Determinism contract:
wiki/concepts/sweep-harness.md. Design spec:
docs/superpowers/specs/2026-06-12-t46-1-sweep-harness-design.md
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

_SCHEMA_VERSION = 1


def _sidecar_path(checkpoint_dir: Path, key: str) -> Path:
    return checkpoint_dir / f"{key}.json"


def _write_sidecar(path: Path, payload: dict) -> None:
    """Atomic write: temp file in the SAME dir, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(payload, fh, allow_nan=True, sort_keys=True)
        os.replace(tmp, path)          # same-fs rename, atomic
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _valid_sidecar(path: Path, commit_hash: str, fingerprint: str) -> dict | None:
    """Return the stored payload iff it matches the current run, else None
    (treat as absent -> recompute). Guards against stale sidecars from a
    different commit or params (design spec §4, review B2)."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (ValueError, OSError):
        return None
    if (payload.get("schema_version") == _SCHEMA_VERSION
            and payload.get("commit_hash") == commit_hash
            and payload.get("param_fingerprint") == fingerprint):
        return payload
    return None


def run_grid(cells, run_cell, cell_key, *, checkpoint_dir, run_constants,
             param_fingerprint, jobs=1, fresh=False):
    checkpoint_dir = Path(checkpoint_dir)
    commit_hash = run_constants["commit_hash"]
    if fresh and checkpoint_dir.exists():
        for p in checkpoint_dir.glob("*.json"):
            p.unlink()
    # Determine pending cells (resume-skip valid sidecars).
    pending = []
    for cell in cells:
        key = cell_key(cell)
        if _valid_sidecar(_sidecar_path(checkpoint_dir, key),
                          commit_hash, param_fingerprint(cell)) is None:
            pending.append(cell)
    # Run pending cells (sequential for now; Task 2 adds jobs>1).
    for cell in pending:
        _run_one(cell, run_cell, cell_key, checkpoint_dir,
                 run_constants, param_fingerprint)
    return _collect(cells, cell_key, checkpoint_dir)


def _run_one(cell, run_cell, cell_key, checkpoint_dir, run_constants,
             param_fingerprint) -> str:
    row = run_cell(cell, run_constants)
    payload = {"schema_version": _SCHEMA_VERSION,
               "commit_hash": run_constants["commit_hash"],
               "param_fingerprint": param_fingerprint(cell),
               "row": row}
    key = cell_key(cell)
    _write_sidecar(_sidecar_path(checkpoint_dir, key), payload)
    return key


def _collect(cells, cell_key, checkpoint_dir) -> list[dict]:
    """Scan sidecars for the requested cells, sort by cell_key (total
    order), return unformatted rows. Order-independent of run order."""
    keyed = []
    for cell in cells:
        key = cell_key(cell)
        payload = json.loads(_sidecar_path(checkpoint_dir, key).read_text())
        keyed.append((key, payload["row"]))
    keyed.sort(key=lambda kr: kr[0])
    return [row for _, row in keyed]
```

Export in `src/common/__init__.py`: add `from .sweep import run_grid` and append `"run_grid"` to `__all__`.

**Step 4 — Run, expect PASS.**

**Step 5 — Add resume-skip test.** Pre-write a valid sidecar, then call `run_grid` with a `run_cell` that raises if invoked for that cell; assert it is NOT invoked (skipped) and its row still appears in output.

**Step 6 — Add stale-guard tests (two):** (a) sidecar with a different `commit_hash` → recomputed; (b) sidecar with a different `param_fingerprint` → recomputed. Use a `run_cell` that tags rows so you can tell recompute from reuse.

**Step 7 — Add atomic-write test:** assert no `*.tmp` file remains in `checkpoint_dir` after a run; assert a sidecar is valid JSON with the four required keys.

**Step 8 — Add `fresh=True` test:** pre-write a sidecar, call with `fresh=True` + a tagging `run_cell`, assert the row is recomputed (old sidecar cleared).

**Step 9 — Run `make test-common`, expect PASS.**

**Commit checkpoint (human).**

---

## Task 2: Parallel execution (`jobs > 1`)

**Files:**
- Modify: `src/common/sweep.py`
- Test: `tests/common/test_sweep.py`

**Step 1 — Failing test: `jobs=1` ≡ `jobs=4` byte-identical.**

```python
class TestJobsEquivalence(unittest.TestCase):
    def test_jobs1_equals_jobsN(self):
        cells = [("a", n, s) for n in (4, 7) for s in range(6)]
        def run(jobs, d):
            return run_grid(cells, _fake_run_cell, _key,
                            checkpoint_dir=Path(d)/".sweep",
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=jobs)
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            self.assertEqual(run(1, d1), run(4, d2))
```

> `_fake_run_cell` and `_key`/`_fp` are module-level (already) → picklable under the macOS `spawn` start method. Keep all test fixtures module-level.

**Step 2 — Run, expect FAIL** (sequential ignores `jobs`).

**Step 3 — Implement the parallel branch.** Replace the "Run pending cells" loop in `run_grid`:

```python
    n_jobs = max(1, min(int(jobs), os.cpu_count() or 1, len(pending) or 1))
    if n_jobs == 1 or len(pending) <= 1:
        for cell in pending:
            _run_one(cell, run_cell, cell_key, checkpoint_dir,
                     run_constants, param_fingerprint)
    else:
        _run_parallel(pending, run_cell, cell_key, checkpoint_dir,
                      run_constants, param_fingerprint, n_jobs)
```

Add a module-level worker (picklable) and the pool driver. Workers receive everything they need as arguments — no closures:

```python
import multiprocessing as mp

_WORKER_CTX = {}

def _worker_init(run_cell, cell_key, checkpoint_dir, run_constants, param_fingerprint):
    _WORKER_CTX.update(run_cell=run_cell, cell_key=cell_key,
                       checkpoint_dir=checkpoint_dir,
                       run_constants=run_constants,
                       param_fingerprint=param_fingerprint)

def _worker(cell):
    c = _WORKER_CTX
    try:
        key = _run_one(cell, c["run_cell"], c["cell_key"], c["checkpoint_dir"],
                       c["run_constants"], c["param_fingerprint"])
        return (cell, key, None)
    except Exception as exc:                       # continue-then-report
        return (cell, None, f"{type(exc).__name__}: {exc}")

def _run_parallel(pending, run_cell, cell_key, checkpoint_dir, run_constants,
                  param_fingerprint, n_jobs):
    failures = []
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(n_jobs, initializer=_worker_init,
                    initargs=(run_cell, cell_key, checkpoint_dir,
                              run_constants, param_fingerprint))
    try:
        for cell, key, err in pool.imap_unordered(_worker, pending, chunksize=1):
            if err is not None:
                failures.append((cell, err))
        pool.close()
        pool.join()
    finally:
        pool.terminate()                            # clean Ctrl-C teardown
    if failures:
        raise SweepCellError(failures)
```

Define `class SweepCellError(RuntimeError)` carrying `.failures` (list of `(cell, msg)`).

> NOTE on picklability: `run_cell`, `cell_key`, `param_fingerprint` must be module-level functions in the *caller's* module (delay adapter), not closures. The delay adapter (Task 4) satisfies this. Document it in the driver docstring.

**Step 4 — Run, expect PASS** (`make test-common`).

**Step 5 — Worker-exception test:** a `run_cell` that raises for one specific cell; assert `SweepCellError` is raised, `.failures` names that cell, the other cells' sidecars exist, and a follow-up resume run (with a non-raising `run_cell`) completes the grid.

**Step 6 — `jobs` clamp test:** `jobs=999` on a 3-cell grid does not error; result equals `jobs=1`.

**Step 7 — Run `make test-common`, expect PASS.**

**Commit checkpoint (human).**

---

## Task 3: Progress (c) + pre-flight estimate (d)

**Files:**
- Modify: `src/common/sweep.py`
- Test: `tests/common/test_sweep.py`

**Step 1 — Failing test:** `run_grid(..., progress=True)` writes one line per completed cell to a passed `stream` (inject a `io.StringIO` to avoid touching real stderr); the machine-readable return value is unchanged.

**Step 2 — Implement** an optional `progress_stream=None` param; when set, after each completed cell print `f"{cell_key(cell)}  [t={dt:.1f}s]  ({done}/{total})"`. Time each cell with `time.perf_counter()` (a *duration*, never written into a row/sidecar). In the parallel branch, emit from the consumer loop as futures resolve.

**Step 3 — Implement pre-flight estimate** as a separate helper `estimate_runtime(sample_cells, run_cell, run_constants) -> dict[str,float]` that times one cell per sample and returns per-sample seconds; the delay CLI (Task 4) multiplies by pending counts and prints to stderr. Keep it out of `run_grid` (single responsibility).

**Step 4 — Leak test:** run a small grid, assert no value in any returned row nor any sidecar JSON equals/contains a `perf_counter`-style float field (assert the row key set is exactly the expected columns — no timing key).

**Step 5 — Run `make test-common`, expect PASS.**

**Commit checkpoint (human).**

---

## Task 4: `src/delay/sweep.py` adopts the driver

**Files:**
- Modify: `src/delay/sweep.py`
- Test: `tests/delay/test_e2e.py` (existing determinism test must still pass)

**Step 1 — Add the module-level adapter + helpers** (picklable; no closures):

```python
# cells are plain tuples: (protocol, timeline_name, n, seed)
def _cell_key(cell) -> str:
    proto, tl_name, n, seed = cell
    return f"{proto}__{tl_name}__n{n}__seed{seed:02d}"

def _timeline_by_name(tl_name):
    return next(t for t in cfg.TIMELINES if t.name == tl_name)

def _param_fingerprint(cell) -> str:
    proto, tl_name, n, seed = cell
    tl = _timeline_by_name(tl_name)
    canon = repr((proto, n, tl.name, tl.delay_kind, sorted(tl.delay_params.items()),
                  tl.p_drop, cfg.T_MAX, _SCHEMA_TAG))   # stable canonical form
    return hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()

def _run_cell(cell, run_constants) -> dict:
    proto, tl_name, n, seed = cell
    timeline = _timeline_by_name(tl_name)
    records, result, meta = RUNNERS[proto](timeline, n, seed)
    kept, stats = clip_records(records, cfg.WINDOW_S, cfg.ONE_ROUND_S[proto])
    return _build_row(kept, result, meta, timeline, stats.clipped_fraction,
                      run_constants["commit_hash"])   # hash threaded in, not resolved here
```

> `_build_row` currently takes `commit_hash` — keep that. The point is the hash is resolved ONCE in `main`/`run_sweep` and passed via `run_constants`, never via `_resolve_commit_hash()` inside `_run_cell` (review B1). `_param_fingerprint` needs stable access to the timeline's delay kind/params/p_drop — expose them on the `Timeline` dataclass if not already (small accessor, no behavior change).

**Step 2 — Rewrite `run_sweep`** to build the cell list and call `run_grid`:

```python
def run_sweep(seeds=None, *, jobs=1, fresh=False, progress_stream=None):
    seeds = cfg.SEEDS if seeds is None else seeds
    commit_hash = _resolve_commit_hash()             # ONCE, in the parent
    cells = [(p, tl.name, n, s)
             for p in _PROTOCOLS for tl in cfg.TIMELINES
             for n in cfg.N_VALUES for s in seeds]
    rows = run_grid(cells, _run_cell, _cell_key,
                    checkpoint_dir=_OUT.parent / ".sweep",
                    run_constants={"commit_hash": commit_hash},
                    param_fingerprint=_param_fingerprint,
                    jobs=jobs, fresh=fresh, progress_stream=progress_stream)
    worst = max((r["clipped_fraction"] for r in rows), default=0.0)
    return rows, worst
```

`write_csv` is unchanged (it formats the collected unformatted rows). Confirm `_build_row` returns native types and `write_csv`'s formatting is the single formatting site.

**Step 3 — Update `main`** argparse: add `--jobs` (int, default 1), `--fresh` (store_true), keep `--smoke` and `--out`. Compose: `--smoke` → `seeds=(0,)`. Print the pre-flight estimate (Task 3 helper) to stderr before running; pass `progress_stream=sys.stderr`.

**Step 4 — Run the existing determinism test, expect PASS:**
`make test-delay` — `TestDeterminism.test_byte_identical_rerun` and the pipeline tests must stay green (they call `_build_row`/`write_csv` directly, which are unchanged in contract).

**Step 5 — Smoke-run equivalence (manual, fast):**
`PYTHONPATH=src python3 -m delay.sweep --smoke --jobs 1 --out /tmp/a.csv` then `--jobs 4 --out /tmp/b.csv` (fresh dirs); assert `/tmp/a.csv` and `/tmp/b.csv` are byte-identical (`cmp`). This is the smoke equivalence; the formal witnesses are Task 5.

**Commit checkpoint (human).**

---

## Task 5: The induction witnesses

**Files:**
- Create: `tests/delay/test_sweep_equivalence.py`

This file mechanizes the base case + inductive step + per-cell invariant, including the `heavy_tail`, `p_drop>0`, and 2-phase witness cells (T47's param shapes). Witness timelines are **test-local** (do not touch `cfg.TIMELINES`).

**Step 1 — Define test-local witness timelines** mirroring `cfg.Timeline` but with: (w1) `DelayDist("heavy_tail", {"scale": 0.2, "shape": 2.0})`, single phase; (w2) `DelayDist("uniform", {"low":0.1,"high":0.5})` with `p_drop=0.1`, single phase; (w3) a 2-phase timeline: phase A `[0, 240)` with `p_drop=0.05`, phase B `[240, inf)` `heavy_tail` — exercises a `PhaseAdvance` rollover. Keep `n=10`, a couple of seeds, for speed. If the delay package's `Timeline` cannot express `p_drop`/multi-phase directly, build the `tuple[Phase,...]` and drive `RUNNERS` through a thin local config — the runners already accept a timeline whose `.phases()` returns the phase tuple.

**Step 2 — Per-cell invariant test:** for each witness cell, run it twice via the driver in separate temp dirs; assert the formatted CSV bytes are identical (use `write_csv` to a temp file, compare bytes — inherit the existing "serialize, don't dict-compare" discipline for NaN).

**Step 3 — Base case, 3-mode:** for one witness cell, produce its row via (i) `jobs=1`, (ii) `jobs=4`, (iii) a forced-resume (run a 2-cell grid, delete one sidecar, re-run). Assert all three formatted single-row CSVs are byte-identical.

**Step 4 — Base case, committed-row anchor:** pick a real T46 cell (e.g. `("pbft","delay-uniform",10,0)`), recompute via the driver, and compare against the matching row parsed from the committed `results/delay/delay.csv` on **all columns except `commit_hash`** (assert `commit_hash` is a non-empty well-formed token separately). Honest statement: reproduces modulo provenance hash.

**Step 5 — Inductive step:** a small k-cell grid mixing two real protocols + the three witness cells; run via `{jobs=1, jobs=4, kill-and-resume}`; collect → `write_csv` → assert all three full CSVs byte-identical.

**Step 6 — Run `make test-delay`, expect PASS.**

**Commit checkpoint (human).**

---

## Task 6: Wiki — contract page + experiment page + index/log

**Files:**
- Create: `wiki/concepts/sweep-harness.md`
- Create: `wiki/experiments/2026-06-12_sweep-harness.md`
- Modify: `wiki/index.md` (add both pages under Concepts / Experiments)
- Modify: `wiki/log.md` (append one entry)

**Step 1 — `wiki/concepts/sweep-harness.md`:** the resumable/parallel + determinism contract. Cover: the cell abstraction, `run_grid` signature, the fingerprinted-sidecar format + the resume validity rule, atomic write, the collect-sort total-order rule, the `commit_hash`-resolved-once invariant, the `jobs` clamp + memory ceiling, the continue-then-report failure policy, and the "dirty tree invalidates resume" rule. Wikilink `[[concepts/reproducibility]]`, `[[concepts/runner]]`, `[[concepts/network-model-phases]]`, `[[concepts/output-format]]`. Reference-sketch + Revisions discipline per the wiki contract style.

**Step 2 — `wiki/experiments/2026-06-12_sweep-harness.md`:** run-success evidence (commands to re-run, `make test-common`/`test-delay` green, the smoke equivalence) PLUS **the written induction** (per-cell invariant → base case → inductive step → conclusion reaching T46's full grid and T47's heavy-tail/loss/multi-phase grid, with the new-`DelayDist`-kind caveat). Include the **Auggie verification** subsection: each auggie query string, a one-line result summary, and its phase (pickup-index / plan / post-edit re-query).

**Step 3 — Update `wiki/index.md`** (add the two pages, one line each) and **append `wiki/log.md`** (type `code`, role Engineer, touched-files list, 1–3 sentence note).

**Commit checkpoint (human).**

---

## Task 7: Verification + flip to In Review

**Files:**
- Modify: `TASKS.md` (flip `[~]` T46.1 → `[?]`, update Dashboard In Progress/In Review counts)

**Step 1 — Full gate:** `make test` — every suite green. Capture the output.

**Step 2 — Post-edit auggie re-query (mandatory):** call `mcp__auggie__codebase-retrieval` asking it to describe `run_grid`'s new behavior and locate its callers (`src/delay/sweep.py`), to surface any broken/stale callsite. Record the query + result in the experiment page's Auggie verification subsection (phase: post-edit re-query).

**Step 3 — `superpowers:verification-before-completion`:** run it; confirm evidence (test output, byte-equivalence) before any success claim.

**Step 4 — Determinism re-run evidence:** re-run the smoke equivalence (`--jobs 1` vs `--jobs 4`, byte-identical) and the witness suite; paste results into the experiment page.

**Step 5 — Flip status** in `TASKS.md`: `[~]` → `[?]` for T46.1; Dashboard In Progress `1 → 0`, In Review `0 → 1`.

**Step 6 — Handoff summary** for the human: files touched, wiki pages added/updated, decisions, open questions (e.g. deferred item (e) Snowman n=25 cost; whether T51–T56 adopt the driver now or later).

**Commit checkpoint (human)** — `task 46.1: <description>`, then push the branch for review.

---

## Notes for the executing engineer

- **Determinism is sacred.** Never introduce `hash()` of a str (PYTHONHASHSEED-randomized), `random.Random()` with no seed, `time.*`/`datetime.now()`/`os.getpid()` into any value that lands in a row or sidecar. Timing is stderr-only.
- **Picklability (spawn).** All functions crossing the `Pool` boundary (`run_cell`, `cell_key`, `param_fingerprint`, the worker) are module-level; cells are plain tuples. No lambdas/closures.
- **Single formatting site.** Sidecars store unformatted native rows; `write_csv`/`_format_row` is the only place floats become strings.
- **T41 untouched.** Do not modify `src/output/baseline.py`.
- **YAGNI.** Do not generalize beyond `run_grid` + the delay adapter. T51–T56 adoption is their task.
