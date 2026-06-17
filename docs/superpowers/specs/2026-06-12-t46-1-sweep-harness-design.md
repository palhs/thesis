# T46.1 — Resumable + parallel sweep harness (design spec)

- **Task:** T46.1 (Engineer, H). Infra precursor to T47.
- **Date:** 2026-06-12
- **Status:** approved (brainstorming → this spec → writing-plans → TDD)
- **Reviewed by:** system-architect subagent (adversarial design review, 2026-06-12) —
  two BLOCKERs + four MAJORs incorporated below; verdict revise-then-ship.

## 1. Motivation

The Family-B delay sweep (`src/delay/sweep.py`, T46) is single-process,
all-or-nothing, and silent. The T46 run took ~2.4 h sequential and had to be
hand-parallelized into 5 throwaway monkey-patched processes; a kill at any
point lost everything. T47 (heavy delay + packet loss, more timelines) and
the Week-10 adversarial sweeps (T51–T56) are larger. This task lands the two
H-priority improvements from the 2026-06-11 sweep-harness backlog item —
**(a) incremental/resumable checkpointing** and **(b) native `--jobs N`
parallelism** — on a *shared* driver, plus the cheap wins (c) per-cell
progress and (d) pre-flight wall-clock estimate. Item (e) Snowman n=25 cost
reduction is deferred to a separate M task.

The deliverable closes with an **equivalence argument structured as an
induction over the sweep grid**, proving any cell grid runs byte-identically
on the new harness regardless of `--jobs N`, resume boundary, or
cell-completion order — so T47 is known to run identically *without running
T47 to prove it*.

## 2. Scope

- **In:** new shared `src/common/sweep.py` driver; `src/delay/sweep.py`
  adopts it; checkpoint + parallel + progress + estimate; the induction
  witnesses (tests) + the written induction (wiki experiment page);
  `wiki/concepts/sweep-harness.md` contract page.
- **Out:** the T41 baseline sweep (`src/output/baseline.py`) stays untouched
  (completed/merged work; re-touching it is a separate decision). T47's
  production timelines (heavy-tail / loss / partial-sync-GST) are T47's to
  define — T46.1 uses *test-local* witness timelines only. Item (e) Snowman
  n=25 cost reduction → separate M task. The adversarial-family adoption of
  the driver is T51–T56's.

## 3. Architecture — the grid-agnostic driver

New `src/common/sweep.py`:

```python
def run_grid(
    cells,            # list[Cell]  — plain picklable tuples, the unit of work
    run_cell,         # module-level PURE fn: (cell, run_constants) -> row dict (native types)
    cell_key,         # fn: cell -> str  — stable, total-order, filesystem-safe identity
    *,
    checkpoint_dir,   # Path  — where sidecars live
    run_constants,    # dict  — resolved ONCE in parent (e.g. commit_hash); broadcast to every cell
    param_fingerprint,# fn: cell -> str — blake2b over the cell's canonicalized config
    jobs=1,           # 1 = sequential (provenance default); >1 = multiprocessing.Pool
    fresh=False,      # True clears checkpoint_dir first
) -> list[dict]:      # collected UNFORMATTED rows, sorted by cell_key
```

- `cell_key` is **one function** used for *both* the sidecar filename and the
  collect-sort order (review M3/n1): it must be a total order over the grid.
  For delay: `f"{protocol}__{timeline_name}__n{n}__seed{seed:02d}"`.
- `run_cell` returns the **unformatted** native-type row (review M1).
  Formatting (`_format_row` + the Family-B branch) happens once, in the
  caller, at collect/write time — single formatting site.
- `run_constants` carries values that must be uniform across all rows and
  must NOT be resolved inside a worker — notably `commit_hash` (review B1).

`src/delay/sweep.py` adopts it: builds the cell list of plain tuples
`(protocol, timeline_name, n, seed)`, supplies a module-level `run_cell`
adapter that reconstructs the `Timeline` by name from `cfg.TIMELINES`
(closures/lambdas must not cross the process boundary — required for the
macOS-default `spawn` start method), runs `runner → clip → _build_row`, and
returns the unformatted row. The existing `write_csv` formats + writes the
collected rows.

## 4. Checkpoint / resume contract (sidecar)

One sidecar file per completed cell under `results/delay/.sweep/`
(gitignored: add `results/**/.sweep/`). Filename = `cell_key(cell) + ".json"`.

Sidecar content (review B2, M1, M2):

```json
{
  "schema_version": 1,
  "commit_hash": "<the run's single resolved hash>",
  "param_fingerprint": "<blake2b over the cell's canonicalized config>",
  "row": { ...unformatted native-type row dict... }
}
```

- **Atomic write:** write to a temp file created **in `checkpoint_dir`**
  (`tempfile.NamedTemporaryFile(dir=checkpoint_dir, delete=False)`), then
  `os.replace` → same-filesystem rename, no `EXDEV`, no torn files (review
  m5). A crash leaves a complete sidecar or none.
- **`param_fingerprint`** = blake2b over the canonicalized cell config:
  `(n, timeline_name, delay.kind, sorted(delay.params), p_drop, protocol
  knobs, t_max, schema_version, COLUMN_ORDER + delay columns)`. Binds the
  sidecar to the params that produced it.
- **Resume (default on):** for each cell, read its sidecar if present; reuse
  **only if** `commit_hash == current` AND `param_fingerprint == current`
  AND `schema_version == current`. Otherwise treat as absent → recompute
  (review B2). `commit_hash` already encodes working-tree dirtiness
  (`git status --porcelain`), so a changed tree invalidates resume —
  correctness over convenience. Net effect: the final CSV always carries a
  **uniform current `commit_hash`**; a code/param change cannot silently mix
  stale rows.
- **`--fresh`** clears `checkpoint_dir` before starting.

### Collect

After the grid completes: scan `checkpoint_dir`, read every sidecar, extract
`row`, **sort by `cell_key`** (the total order), hand to the caller's
formatter/writer. This filesystem-collect-then-sort is the canonical,
order-independent step the induction relies on — it does not depend on
`imap_unordered` completion order or `os.scandir` order.

## 5. Parallelism

- `jobs == 1`: plain sequential loop (the provenance default — the documented
  single-process command).
- `jobs > 1`: `multiprocessing.Pool(jobs)` + `imap_unordered(chunksize=1)`
  over the cells. Each worker runs `run_cell`, writes its own sidecar,
  returns `cell_key` (for progress). No shared writer, no lock. Because every
  cell is a pure function of `(cell, run_constants)` and writes a private
  file, the result is byte-identical to sequential.
- **`jobs` clamp:** `jobs = max(1, min(jobs, os.cpu_count() or 1, len(pending_cells)))`.
- **Memory ceiling (review m2):** each in-flight cell holds its full
  `EventLogger.records` (Snowman n=25 ≈ 8M records). `chunksize=1` bounds
  residency to `jobs` concurrent runs; document the ceiling and warn when the
  grid includes the Snowman n=25 tier. (Real cost reduction is deferred item
  (e).)
- **Worker exceptions (review m3):** wrap `run_cell` so any exception is
  re-raised with the `cell_key` attached; policy is **continue-then-report** —
  failed cells are collected into a manifest, the sweep finishes the rest,
  and `main` exits non-zero listing the failures. (A failed cell simply has
  no sidecar, so a later resume retries it.)
- **Interrupt (review m4):** run the pool inside a context manager /
  `try…finally` with `pool.terminate()` so Ctrl-C tears workers down
  cleanly; durably-written sidecars make interrupt-then-resume safe. `spawn`
  start method (macOS default) is satisfied by the module-level-fn +
  plain-tuple-cells design.

## 6. Progress (c) + pre-flight estimate (d)

- **(c)** one line per completed cell to **stderr** (stdout stays the
  machine-readable summary):
  `snowman n=25 delay-exponential seed7  [t=4.1s]  (132/240)`.
- **(d)** before the full grid, time one cell per protocol at the smallest
  `n`, multiply by the per-protocol *pending* cell counts, print a projected
  wall-clock + per-protocol breakdown to stderr, then proceed. Distinct from
  the static `ONE_ROUND_S` window-sizing constants — this is the wall-clock
  estimate the T46 run lacked. Timing is stderr-only; it must never enter a
  row or sidecar (asserted by a test that greps output for wall-clock fields).

## 7. The induction (witnesses-only)

Per human decision 2026-06-12, the conclusion is carried by mechanized
**witnesses** + a **written** generalization on the experiment page — no
full-grid regeneration.

**Per-cell invariant (precondition).** Each cell maps to its row by a pure
deterministic `f(cell, run_constants)`: no wallclock, no cross-cell shared
state, every RNG seeded via blake2b from the cell's `seed`/`global_seed`
(verified across `network.py`, `nodes/node.py`, `workload/generator.py`,
`pos/selection.py`). `commit_hash` is the only provenance input and is a
broadcast constant, not worker-resolved.

**Witness grid (test-local timelines — T47's param shapes, expressible
today):**
- a single-phase `heavy_tail` (Pareto) cell;
- a single-phase `p_drop > 0` (packet-loss) cell;
- a **2-phase** cell (e.g. loss-phase → heavy_tail-phase) that exercises a
  `PhaseAdvance` rollover (review M4 — T47's partial-sync-GST timeline is
  inherently multi-phase, so the witness must cross a phase boundary or the
  induction has a hole).

**Base case.** One cell's row is identical across `{jobs=1, jobs=N,
forced-resume-midway}`. Additionally, for cells present in the committed T46
grid (n=10 uniform/exp × 3 protocols), the recomputed row equals the
committed `results/delay/delay.csv` row on **all columns except
`commit_hash`** (the committed rows carry the T46 commit's hash; honest
statement: "reproduces the committed T46 rows modulo the provenance hash"),
with `commit_hash` asserted well-formed separately.

**Inductive step.** A small k-cell grid (mixed protocols + the three witness
cells) run three ways → the collected, sorted, formatted CSV is byte-identical
across all three modes. Adding cells / parallelism / resume points cannot
perturb a row, because cells are independent and the collect-sort imposes a
total order.

**Conclusion (written, on the experiment page).** By induction over the grid,
any finite cell grid — T46's full 240-cell grid and T47's larger
heavy-tail / loss / multi-phase grid — produces byte-identical output on this
harness regardless of jobs / resume / order, without running them. **Honest
caveat:** the precondition is "pure `run_cell`". `heavy_tail`, `p_drop`, and
multi-phase rollovers are already in the determinism substrate and covered by
the witnesses, so T47 is covered. A *brand-new* `DelayDist` kind added later
(outside `_DELAY_KINDS`) would reopen the precondition and require its own
determinism witness.

## 8. Tests (TDD)

- `tests/common/test_sweep.py` (driver, against a fake pure `run_cell`):
  resume-skip; atomic-write/no-torn-file; stale-fingerprint → recompute;
  stale-commit_hash → recompute; collect-sort order-independence;
  `jobs=1 ≡ jobs=N`; worker-exception → continue-then-report manifest;
  `--fresh` clears.
- `tests/delay/test_sweep_equivalence.py` (the induction witnesses):
  per-cell invariant; base case (3-mode + committed-row anchor modulo
  `commit_hash`); inductive step (3-mode byte-identical collected CSV);
  the `heavy_tail`, `p_drop>0`, and 2-phase witness cells.
- estimate/progress: assert no wall-clock field leaks into CSV/sidecar.
- Register a `make test` suite entry if needed; existing suites stay green.

## 9. Artifacts

- **Code:** `src/common/sweep.py` (new) + `src/common/__init__.py` export;
  `src/delay/sweep.py` (adopts `run_grid`, adds `--jobs / --fresh / --out`,
  composes with `--smoke`); `.gitignore` `results/**/.sweep/`.
- **Wiki:** new `wiki/concepts/sweep-harness.md` (resumable/parallel +
  determinism contract); `wiki/experiments/2026-06-12_sweep-harness.md`
  (run-success evidence + the written induction + the **Auggie
  verification** log: every auggie query, its one-line result, and its phase
  — pickup-index / plan / post-edit re-query); update `wiki/index.md`;
  append `wiki/log.md`.

## 10. Risks / open items

- A dirty working tree invalidates resume (by design). Documented in the
  contract page so a long production sweep is run from a clean tree.
- Memory under high `jobs` with the Snowman n=25 tier — bounded to `jobs`
  concurrent but not reduced (deferred item (e)).
- `param_fingerprint` must canonicalize float params stably (use the same
  formatting discipline as the CSV) so semantically-equal configs fingerprint
  equal across runs.
