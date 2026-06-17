# [2026-06-12] T46.1 — Resumable + parallel sweep harness

Run-success evidence for the grid-agnostic sweep driver
`common.sweep.run_grid` and `src/delay/sweep.py`'s adoption of it, plus **the
written induction** proving any cell grid runs byte-identically regardless of
`--jobs N`, resume boundary, or cell-completion order — so T47 is known to
run identically *without running T47 to prove it*.

Design contract: [[concepts/sweep-harness]]. Design spec:
`docs/superpowers/specs/2026-06-12-t46-1-sweep-harness-design.md`. Plan:
`docs/plans/2026-06-12-t46-1-sweep-harness.md`. Branch:
`task/T46.1-sweep-harness`.

## What changed

- **New** `src/common/sweep.py` — `run_grid` (resume-skip via fingerprinted
  sidecars, atomic `os.replace` write, collect-sort total order, `jobs>1`
  via a `spawn` `multiprocessing.Pool` with continue-then-report
  `SweepCellError`, `progress_stream`, `estimate_runtime`). Exported from
  `common/__init__.py`.
- **`src/delay/sweep.py`** adopts it: a module-level adapter
  (`_run_cell` / `_cell_key` / `_param_fingerprint`, spawn-picklable), a
  `run_grid`-based `run_sweep`, and `--jobs` / `--fresh` + a stderr progress
  stream and pre-flight estimate on `main`. `_build_row` / `write_csv` /
  `_window_denominator_fix` are unchanged — the single formatting site and
  the per-cell numerics are preserved.
- **`.gitignore`** — `results/**/.sweep/` (sidecars are runtime-only).
- **Tests** — `tests/common/test_sweep.py` (driver, 18 incl. runner) and
  `tests/delay/test_sweep_equivalence.py` (the 4 induction witnesses).
- **T41 baseline untouched** (`src/output/baseline.py`).

## Run-success evidence

```
make test-common   # Ran 18 tests ... OK   (driver: resume / stale-guard /
                   #   atomic-write / fresh / jobs1≡jobsN / worker-exception
                   #   / clamp / progress / no-timing-leak / estimate)
make test-delay    # Ran 36 tests ... OK   (32 existing + 4 witnesses; 165 s)
```

Smoke equivalence (12-cell smoke grid, independent checkpoint dirs):

```
PYTHONPATH=src python3 -m delay.sweep --smoke --jobs 1 --out /tmp/A/delay.csv
PYTHONPATH=src python3 -m delay.sweep --smoke --jobs 4 --out /tmp/B/delay.csv
cmp /tmp/A/delay.csv /tmp/B/delay.csv      # BYTE-IDENTICAL
```

Both wrote 12 rows at worst clipped-fraction 3.81 % (PASS). The `--jobs 4`
run completed cells **out of order** (n=10 first, n=25 interleaved across
protocols), confirming real parallelism; the collected CSV is byte-identical
to `--jobs 1` regardless. The stderr progress stream and pre-flight estimate
rendered correctly (the estimate flagged Snowman as the cost driver:
~29 s/cell at n=10; the n=25 cells then ran ~200–256 s — the "rough,
smallest-n sample" caveat is honest).

Re-run (production):

```
PYTHONPATH=src python3 -m delay.sweep            # full 240-row sweep, jobs=1
PYTHONPATH=src python3 -m delay.sweep --jobs 8   # parallel, byte-identical
PYTHONPATH=src python3 -m delay.sweep --fresh    # ignore resumable sidecars
```

## The induction (witnesses + written argument)

Per the human decision (2026-06-12) the conclusion is carried by mechanized
**witnesses** (`tests/delay/test_sweep_equivalence.py`) plus this written
generalization — **no full-grid regeneration**.

**Witness grid (T47's param shapes, test-local timelines).** Three cells
exercising the parameter shapes T47 introduces, all expressible on today's
determinism substrate ([[concepts/network-model-phases]]):

- `w-heavy-tail` — single-phase `heavy_tail` (Pareto `scale=0.2, shape=2.0`).
- `w-loss` — single-phase `uniform` delay with `p_drop=0.1` packet loss.
- `w-2phase` — phase A `[0, 240)` `uniform` + `p_drop=0.05`, phase B
  `[240, ∞)` `heavy_tail`; crosses a `PhaseAdvance` rollover inside the
  528 s horizon (T47's partial-sync-GST timeline is inherently multi-phase,
  so the witness **must** cross a phase boundary or the induction has a
  hole).

**Per-cell invariant (precondition).** Each cell maps to its row by a pure
deterministic `f(cell, run_constants)`: no wallclock, no cross-cell shared
state, every RNG seeded from the cell's `seed`/`global_seed`; `commit_hash`
is the only provenance input and a broadcast constant, not worker-resolved
([[concepts/reproducibility]]). *Witnessed:* each of the three witness cells
run twice → byte-identical CSV (`TestPerCellInvariant`).

**Base case.** *Witnessed (`TestBaseCase`):* (1) the `w-2phase` cell's row is
byte-identical across `{jobs=1, jobs=2-parallel, forced-resume}` (delete the
sidecar mid-grid → recompute). (2) the **committed anchor** — the real T46
cell `("pbft", "delay-uniform", 10, 0)` recomputed on the new harness equals
the committed `results/delay/delay.csv` row on **all 28 data columns**,
differing only in `commit_hash` (the committed rows carry T46's `2ef410f7`;
the recompute carries the current run's hash, asserted well-formed
separately). Honest statement: *reproduces the committed T46 rows modulo the
provenance hash.* This is the load-bearing no-regression check — the refactor
changed orchestration, not numbers.

**Inductive step.** *Witnessed (`TestInductiveStep`):* a 5-cell grid mixing
two real protocols (PBFT, Casper FFG) + the three witness cells is
byte-identical across `{jobs=1, jobs=4, kill-and-resume}`. Adding cells /
parallelism / resume points cannot perturb a row, because cells are
independent and the collect-sort imposes a total order (§4 of
[[concepts/sweep-harness]]).

**Conclusion (written).** By induction over the grid, **any** finite cell
grid — T46's full 240-cell grid and T47's larger heavy-tail / loss /
multi-phase grid — produces byte-identical output on this harness regardless
of `jobs`, resume boundary, or completion order, **without running them**.
The base case fixes one cell's invariance across execution modes; the
inductive step shows a grid's invariance is preserved under adding an
independent cell; every T46/T47 cell is of the same independent form,
differing only in parameter values already covered by the witnesses.

**Honest caveat.** The precondition is "pure `run_cell`". `heavy_tail`,
`p_drop`, and multi-phase rollovers are already in the determinism substrate
(`network/phases.py` `_DELAY_KINDS`) and covered by the witnesses, so T47 is
covered. A **brand-new `DelayDist` kind** added later (outside `_DELAY_KINDS`)
would reopen the precondition and require its own determinism witness before
the induction extends to it.

## Decisions / deviations from the plan

- **`_param_fingerprint` canonicalizes over `tl.phases()`** (delay kind +
  params + phase boundaries + `p_drop` + partitions per phase) rather than
  the plan's `tl.delay_kind` / `tl.p_drop` accessors, which `cfg.Timeline`
  does not expose. One fingerprint function now covers single-phase
  production timelines and the multi-phase / `p_drop>0` witnesses uniformly.
- **Checkpoint dir derives from the `--out` path** (`<out_dir>/.sweep`), not
  a hardcoded `results/delay/.sweep` — so distinct output paths checkpoint
  independently (which is what makes the two-dir smoke equivalence a genuine
  independent recompute, not a resume-reuse).
- **`estimate_runtime` keys its dict by the cell tuple** (the generic helper
  has no protocol-aware key fn; the CLI holds the sample cells).

## Scope / deferrals

- **T47** owns its production timelines (heavy-tail 1–5 s, packet loss
  5–20 %, partial-sync-GST). T46.1 ships only the harness + test-local
  witnesses.
- **Item (e)** Snowman n=25 cost reduction (streaming reducer / hot path) —
  a separate M task. `chunksize=1` bounds memory to `jobs` concurrent runs
  but does not reduce per-cell cost.
- **T51–T56** adversarial-family adoption of the driver is their task.

## Auggie verification

Per the Engineer protocol, every `mcp__auggie__codebase-retrieval` call made
during the task (query, one-line result, phase):

- **pickup-index** — query: *"Implementing `run_grid` in `src/common/sweep.py`
  and adopting it in `src/delay/sweep.py`. Map the surface: `_build_row` /
  `run_sweep` / `write_csv` / `main` and how `_resolve_commit_hash` is
  called; `runners.RUNNERS` + `run_pbft/ffg/snowman(timeline, n, seed)`
  returns; `clip.clip_records` signature; `config.Timeline` fields + phases()
  + TIMELINES/N_VALUES/SEEDS/T_MAX/WINDOW_S/ONE_ROUND_S; network DelayDist
  (kind/params/sample) + Phase (t_start/t_end/delay/p_drop); `output.csv`
  `_format_row`/`_generic_cols`/`_resolve_commit_hash` + `output.schema`
  COLUMN_ORDER; `common/__init__.py` exports; confirm nothing else imports
  delay.sweep besides tests."* Result: confirmed the full surface — runners
  return `(records, result, meta)`, `_build_row(records, result, meta,
  timeline, clipped_fraction, commit_hash)` is the single row builder, the
  PBFT reducer needs the unchanged `_window_denominator_fix`, `Timeline`
  exposes `phases()` (single `Phase(0, inf, delay, p_drop=0)`) but **no**
  `delay_kind`/`p_drop` accessors (→ fingerprint over `phases()`), and only
  `tests/delay/{test_e2e,test_window_denominator}` import `delay.sweep` (the
  `_build_row`/`write_csv`/`_window_denominator_fix` names, all preserved).

- **post-edit re-query** — query: *"Post-edit verification of the new T46.1
  sweep harness: describe `common.sweep.run_grid` and its helpers
  (`_run_one`/`_collect`/`_valid_sidecar`/`_write_sidecar`/`_run_parallel`/
  `_worker`/`_worker_init`/`estimate_runtime`/`SweepCellError`), their
  determinism guarantees, and parallelism/resume; locate ALL callers of
  `run_grid` and the delay adapter; flag any stale callsite, any
  worker-resolved `commit_hash`, any closure/lambda crossing the
  multiprocessing boundary, or any timing/wallclock written into a row or
  sidecar."* Result: confirmed the production caller is `src/delay/sweep.py`
  (`run_sweep → run_grid`) and the only test exercisers are
  `tests/common/test_sweep.py` and `tests/delay/test_sweep_equivalence.py`;
  the live `_run_cell` threads `commit_hash` in from `run_constants` (not
  worker-resolved), the adapter functions (`_run_cell`/`_cell_key`/
  `_param_fingerprint`) and the driver's `_worker`/`_worker_init` are all
  module-level (no closure/lambda crosses the `spawn` Pool boundary), and
  timing stays a `perf_counter` duration on the progress/estimate path —
  never written into a row or sidecar. **No stale or broken callsite, no
  worker-resolved hash, no boundary closure, no timing leak.**
