# Sweep harness (resumable + parallel driver)

The grid-agnostic experiment driver `common.sweep.run_grid` (T46.1). It runs
a list of independent **cells** through a pure per-cell function, writing one
fingerprinted **sidecar** per completed cell so a killed sweep resumes and
parallel workers never clobber. Output is **byte-identical across `jobs`,
resume boundary, and cell-completion order** — the property the
induction-over-the-grid relies on ([[experiments/2026-06-12_sweep-harness]]).

It is the shared layer under [[experiments/2026-06-10_delay-moderate]]'s
Family-B sweep and the precursor to T47 (heavy delay + loss) and the T51–T56
adversarial sweeps. It does not replace the per-run pipeline — `runner →
clip → row` stays in the protocol/experiment packages
([[concepts/runner]]); `run_grid` only orchestrates the grid.

## 1. The cell abstraction

A **cell** is the unit of work: a plain, picklable tuple identifying one run
(for delay, `(protocol, timeline_name, n, seed)`). The driver is given three
pure functions over cells:

- `run_cell(cell, run_constants) -> row` — computes one **unformatted**
  native-type row dict. Pure: a deterministic function of its arguments, no
  wallclock, no cross-cell shared state ([[concepts/reproducibility]]).
- `cell_key(cell) -> str` — a stable, total-order, filesystem-safe identity,
  used for **both** the sidecar filename **and** the collect-sort order (one
  function, so the two can never disagree).
- `param_fingerprint(cell) -> str` — `blake2b` over the cell's canonicalized
  config; binds a sidecar to the params that produced it (§3).

```python
def run_grid(cells, run_cell, cell_key, *, checkpoint_dir, run_constants,
             param_fingerprint, jobs=1, fresh=False, progress_stream=None):
    -> list[dict]    # collected UNFORMATTED rows, sorted by cell_key
```

`run_constants` carries values that must be uniform across every row and must
**not** be resolved inside a worker — notably `commit_hash` (§5).

## 2. Single formatting site

`run_cell` returns the unformatted row; `run_grid` stores and returns
unformatted rows. Formatting (floats → strings) happens once, in the caller's
writer (`delay.sweep.write_csv` / `output.csv._format_row`) at write time
([[concepts/output-format]]). Sidecars therefore store native types
(`json.dump(..., allow_nan=True, sort_keys=True)`), so a Snowman-parameter
`NaN` round-trips as `NaN`, not a formatted string.

## 3. Checkpoint / resume contract (sidecar)

One sidecar JSON per completed cell under `<output_dir>/.sweep/`
(gitignored: `results/**/.sweep/`). Filename = `cell_key(cell) + ".json"`.

```json
{ "schema_version": 1,
  "commit_hash": "<the run's single resolved hash>",
  "param_fingerprint": "<blake2b over the cell's canonicalized config>",
  "row": { ...unformatted native-type row dict... } }
```

- **Atomic write.** Write to a temp file **in the same directory**
  (`tempfile.mkstemp(dir=...)`), then `os.replace` — a same-filesystem
  rename, no `EXDEV`, no torn files. A crash leaves a complete sidecar or
  none.
- **`param_fingerprint`** canonicalizes over the cell's network **phase
  tuple** — per phase: `(t_start, t_end, delay.kind, sorted(delay.params),
  p_drop, partitions)` — plus `(protocol, n, t_max, schema_tag)`, where
  `schema_tag` is the full column set. Canonicalizing over phases covers
  single-phase production timelines and multi-phase / `p_drop>0` timelines
  uniformly. Float params use `repr` (shortest round-tripping decimal,
  stable in Python 3) so semantically-equal configs fingerprint equal. A
  column-set change flips `schema_tag`, invalidating every sidecar.
- **Resume validity rule (default on).** A sidecar is reused **only if**
  `schema_version` AND `commit_hash` AND `param_fingerprint` all match the
  current run. Otherwise it is treated as **absent → recompute**. So the
  final CSV always carries a uniform current `commit_hash`; a code or param
  change can never silently mix stale rows.
- **Dirty tree invalidates resume.** `commit_hash` already encodes
  working-tree dirtiness (`<hash>-dirty` via `git status --porcelain`,
  [[concepts/reproducibility]]), so editing tracked code between runs flips
  the hash and forces a full recompute — correctness over convenience. Run a
  long production sweep from a **clean** tree, or every cell recomputes.
- **`fresh=True`** clears `checkpoint_dir` before starting (ignore resumable
  state, recompute every cell).

## 4. Collect — the total-order step

After the grid completes, `run_grid` reads the sidecar of every requested
cell, extracts `row`, and **sorts by `cell_key`**. This filesystem-collect-
then-sort is order-independent: it does not depend on `imap_unordered`
completion order or `os.scandir` order. It is the canonical step the
induction's inductive case turns on — grid size, parallelism, and resume
points cannot perturb a row or its position.

## 5. `commit_hash` resolved once (provenance)

`commit_hash` is resolved **once in the parent** (`_resolve_commit_hash`) and
broadcast via `run_constants`; `run_cell` reads it, never re-resolves it.
Resolving inside a worker would race the writer's own output dirtying the
tree mid-sweep, producing a mix of `<hash>` and `<hash>-dirty` rows. This is
the single provenance input to a row; everything else is a pure function of
the cell.

## 6. Parallelism

- `jobs == 1`: a plain sequential loop — the **provenance default**, the
  documented single-process command.
- `jobs > 1`: `multiprocessing.Pool` over the pending cells with
  `imap_unordered(chunksize=1)`. Each worker runs `run_cell` and writes its
  **own** sidecar — no shared writer, no lock. Byte-identical to sequential
  because every cell is a pure function writing a private file, and collect
  re-imposes the total order.
- **`spawn` start method** (macOS default) is mandatory: every function
  crossing the Pool boundary (`run_cell`, `cell_key`, `param_fingerprint`,
  the worker) must be a **module-level** function, and cells plain tuples —
  no closures/lambdas. The delay adapter satisfies this.
- **`jobs` clamp:** `max(1, min(jobs, os.cpu_count() or 1, len(pending)))` —
  a huge `--jobs` on a tiny grid does not over-subscribe.
- **Memory ceiling:** each in-flight cell holds its full `EventLogger`
  records (Snowman `n=25` ≈ millions). `chunksize=1` bounds residency to
  `jobs` concurrent runs; it does not *reduce* per-cell cost (deferred item
  (e), a separate M task).
- **Continue-then-report failure policy:** a worker exception is caught,
  attached to its cell, and collected; the sweep finishes the rest, then
  raises `SweepCellError` listing the failures. A failed cell simply has no
  sidecar, so a later resume retries it. `pool.terminate()` in a `finally`
  tears workers down cleanly on Ctrl-C; durable sidecars make
  interrupt-then-resume safe.

## 7. Progress + pre-flight estimate (stderr only)

- `progress_stream` (e.g. `sys.stderr`) gets one line per completed cell:
  `cell_key  [t=4.1s]  (132/240)`. The `t=` is a `perf_counter` **duration**.
- `estimate_runtime(sample_cells, run_cell, run_constants)` times one cell
  per protocol at the smallest `n` and returns `{cell: seconds}`; the CLI
  projects wall-clock to stderr.
- **Timing never enters a row or a sidecar.** Durations are stderr-only — a
  test asserts the returned rows and every sidecar carry exactly their data
  columns, no timing field (the determinism contract forbids wallclock in
  output, [[concepts/reproducibility]]).

## 8. What the driver does NOT own

Per-run mechanics — the `runner → clip → row` pipeline, the window/buffer
clip, the CSV column set and formatting — stay in the experiment package
([[experiments/2026-06-10_delay-moderate]], [[concepts/output-format]]). The
network-layer determinism that makes a cell pure (seeded delay sampling,
drop coin, phase advance) is [[concepts/network-model-phases]]. The T41
baseline sweep (`src/output/baseline.py`) is untouched — adoption there is a
separate decision.

## 9. Memory-aware tiered scheduling (`run_grid_tiered`, T47)

`run_grid`'s §6 memory ceiling — "`chunksize=1` bounds residency to `jobs`
concurrent runs" — bounds the *count* of in-flight cells, not their *size*.
When the heaviest cell is large, `jobs × heaviest-cell` can still exceed RAM:
the T47 Snowman n=25 heavy sweep OOM'd at `jobs=2` because two cells each
materialize ~20–30 M `EventRecord`s (~5 GB) and `2 × 5 GB` + the OS pushed a
16 GB machine into swap-death (a worker was OS-killed and the `Pool` hung).

`run_grid_tiered(cells, …, is_heavy, jobs, heavy_jobs)` fixes this at the
scheduling layer: it partitions cells by `is_heavy(cell)` and runs the LIGHT
tier at `jobs`, then the HEAVY tier at `heavy_jobs` (default 1, one at a
time). Peak memory is bounded by `max(jobs × light-footprint, heavy_jobs ×
heavy-footprint)` instead of `jobs × heaviest`.

- **Byte-identical to `run_grid`.** Both tiers write into the same
  `checkpoint_dir`, and the function ends with a full `run_grid(cells)` —
  every sidecar is then present, so that final call computes nothing and just
  collects, globally sorted by `cell_key`. Tiering changes only *scheduling*;
  the §4 total order and the induction (§1, [[experiments/2026-06-12_sweep-harness]])
  are untouched. A driver-level test asserts `tiered == plain run_grid`.
- **`is_heavy` runs only in the parent** (partitioning), so it need not be
  picklable — unlike `run_cell`/`cell_key`/`param_fingerprint` (§6).
- **Mitigation, not cure.** It bounds memory but not per-cell wall-clock; the
  heavy class still runs ~serially. The O(1)-memory cure is the streaming
  reducer (TASKS.md Backlog 2026-06-12, supersedes deferred item (e)) — fold
  metrics as events emit instead of materializing the full list — which would
  let `heavy_jobs` rise. Land it before the larger T51–T56 sweeps.

## Revisions

### [2026-06-12] T47 — `run_grid_tiered` added (memory-aware scheduling)

The §6 "Memory ceiling" bullet claimed `chunksize=1` bounds residency to
`jobs` concurrent runs — true for cell *count* but not cell *size*. T47 hit
the gap (Snowman n=25 heavy, ~5 GB/cell, OOM at `jobs=2`). `run_grid_tiered`
(§9) is the scheduling-layer mitigation: heavy cells run at `heavy_jobs`.
Additive (a new function; `run_grid` itself is unchanged), so no prior claim
is contradicted — recorded here per the new-capability convention. The deep
O(1)-memory fix (streaming reducer) is a filed follow-up.
