# [2026-06-04] T42 — Metrics collection + completeness verification

T42's outcome is "Full CSV dataset verified for completeness" plus the
named deliverable `results/baseline/metrics.csv`. The latency, throughput,
and communication-overhead metric families were already collected and
shipped by [[experiments/2026-06-03_scaling-baseline]] (T41) and
regenerated under T70 (PR #8) at clean provenance `commit_hash = 24a491a4`.
T42 therefore does **not** collect anything new. It does two things:

1. **Verifies completeness** of the existing
   `results/baseline/baseline.csv` (300 per-trial rows) and its Snowman
   `n=4` sanity sibling, codified as the checked-in objective gate
   `tests/output/test_dataset_completeness.py`.
2. **Materialises `results/baseline/metrics.csv`** as a thin DERIVED metrics
   view over `baseline.csv` — identity columns plus the three metric
   families — built by `src/output/metrics_view.py` and gated by
   `tests/output/test_metrics_view.py`.

`baseline.csv` stays the canonical authoritative per-trial file
([[concepts/output-format]] §2); `metrics.csv` is derived and
non-authoritative. This is NOT a rename (that would orphan the 15+ inbound
`[[concepts/output-format]]` wikilinks and break the e2e determinism gate)
and NOT new collection (the model is latency-only; `peak_tps` /
`mempool_*` / Narwhal+Tusk rows are deferred to T58 / T38.1 per
[[concepts/output-format]] §11, §13).

## Configuration

- **Source dataset:** the T41 sweep — `n ∈ {4,7,10,16,25} × seed ∈ {0…19}`,
  `poisson` arrival, `offered_rate = 100` tx/s, `tx_bytes = 512`,
  `conflict_rate = 0.0`. Full config: [[experiments/2026-06-03_scaling-baseline]].
- **Seeds:** 0…19 (20 per configuration).
- **Provenance commit:** `24a491a4` (single distinct `commit_hash` across
  all 300 rows; carried through unchanged into the metrics view — the view
  does not re-resolve the git hash).
- **metrics.csv projection (12 columns):**
  - identity: `run_id, protocol, n, seed, commit_hash`
  - latency: `commit_latency_ms, finality_latency_ms`
  - throughput: `tps, goodput`
  - communication overhead: `consensus_msgs_per_acu, total_msgs_per_acu,
    bytes_per_acu`
- **Rows in metrics.csv:** 300 (main-file rows only; the Snowman `n=4`
  sanity rows are excluded to preserve the cross-protocol-comparison
  invariant, [[concepts/output-format]] §7).

## Row-arithmetic reconciliation

300 main rows are **not** a clean `3 × 5 × 20` grid:

```
300  =  PBFT 100      (5 n × 20 seeds)
     +  Casper FFG 120 (6 run_ids × 20 seeds: 5 uniform n + 1 nonuniform n=4)
     +  Snowman 80      (4 n × 20 seeds; n=4 routed to the sanity file)
```

Casper FFG gains 20 rows from the extra `n=4` nonuniform-stake variant;
Snowman loses 20 rows because the degenerate `n=4` (`α_c = K`) boundary is
excluded from the main file and lives in
`results/baseline/snowman_n4_sanity.csv` (20 rows, `snowman_degenerate_n4 =
True`). Documented here so 300 is never mistaken for a uniform grid.

## Re-run

```
# 1. Source dataset (only if regenerating from scratch; already shipped):
PYTHONPATH=src python3 -m output.baseline
#    -> results/baseline/baseline.csv + results/baseline/snowman_n4_sanity.csv

# 2. Derived metrics view:
PYTHONPATH=src python3 -m output.metrics_view
#    -> results/baseline/metrics.csv

# 3. Verification gates:
PYTHONPATH=src:tests/output python3 -m unittest discover -s tests/output
```

`metrics.csv` is byte-identical on re-run: `build_metrics_view` is a pure
read → project → write that copies each cell through verbatim as a string.
Because `baseline.csv` was already written with the
[[concepts/output-format]] §9 float formats (`*_ms` at `.9f`; `tps` /
`*_per_acu` / rates at `.6f`), pass-through guarantees the view's metric
cells are byte-identical to their source without re-formatting. Row order is
inherited from `baseline.csv` (the total `(protocol, n, run_id, seed)` sort,
§8), so output is input-order-independent. Determinism asserted by
`tests/output/test_metrics_view.py::test_regenerable_and_byte_identical`.

## Raw result location

- `results/baseline/baseline.csv` — canonical per-trial source (300 rows).
- `results/baseline/snowman_n4_sanity.csv` — Snowman `n=4` boundary (20 rows).
- `results/baseline/metrics.csv` — derived metrics view (300 rows), T42.

## Verification (what the gates assert)

`tests/output/test_dataset_completeness.py` (over the existing source):
- exactly 300 data rows; the 15 expected `run_id`s, each at all 20 seeds;
- no empty / non-finite cell in any of the 7 metric columns on any row;
- Snowman parameter columns NaN on every PBFT/FFG row and populated on every
  Snowman row ([[concepts/output-format]] §6);
- `success_rate = 1.0`, `fork_rate = 0.0` on every row (honest-path invariant);
- a single distinct `commit_hash = 24a491a4`;
- the row-arithmetic split (100 / 120 / 80); `snowman-n4` absent from the
  main file; the sanity file carries 20 degenerate-`n4` rows.

`tests/output/test_metrics_view.py` (over the derived view):
- `metrics.csv` exists, regenerates byte-identically across two builds, and
  the rebuild matches the committed artifact byte-for-byte;
- row count matches the source (300); every metric cell present and finite;
- **round-trip fidelity** — each view cell equals the corresponding
  `baseline.csv` cell (string compare, keyed by `(run_id, seed)`);
- `commit_hash = 24a491a4` carried through.

Full `tests/output` suite: **75 tests pass**, including the unchanged e2e
determinism gate `test_baseline_e2e.py`. `baseline.csv` is byte-unchanged by
T42 (verified via `git status` — no working-tree modification).

## Observation

The shipped T41/T70 dataset is complete by every objective criterion the
task demands: 300 fully-populated per-trial rows across three protocols,
single clean provenance hash, correct NaN dispatch, honest-path invariants
held. The metrics view is a faithful, deterministic, downstream-friendly
slice of that source. No metric was missing and none needed re-collection;
T42 is verification + a derived deliverable, not a measurement task.

## Scope and deferrals

- **PBFT measurement-point methodology note → T45 (Writer).** The
  commit-vs-client-observed PBFT finality distinction (T70 added an `f+1`
  REPLY round, so `finality_latency_ms` is now client-observed, one hop past
  the `2f+1` COMMIT quorum — [[experiments/2026-06-03_scaling-baseline]]
  §Revisions) needs a Chapter 4 methodology note. That is Writer scope
  (TASKS.md Backlog RX.2: "Remaining for T42/T45"); T42 only flags it. Do
  not write the prose here or in `drafts/`.
- **metrics.csv is documented as derived here, not elevated to a
  contract-level artifact** in [[concepts/output-format]]. Keeping it on the
  experiment page avoids creating a second "canonical" file that could
  confuse the T44 aggregation consumer (which reads `baseline.csv`).
- **CIs / aggregation** are T44; **`peak_tps` / capacity model** T58;
  **Narwhal+Tusk** T38.1.

## Auggie verification

The Engineer role mandates `mcp__auggie__codebase-retrieval`. During the
implementation phases the auggie MCP tool was unavailable (same finding as
[[experiments/2026-06-03_scaling-baseline]] §Auggie verification — it
returned `[REPO_NOT_FOUND]` for this repo), so the pickup-index and plan
structural search fell back to local `grep` / `Read`. The mandatory
post-edit re-query was run later in the documentation pass with the auggie
tool available, against the repo on disk; it succeeded and confirmed the
local-grep finding independently.

- *pickup-index* (auggie unavailable; fell back to local `grep`/`Read`.
  Query intent: "metrics CSV writer, schema, baseline orchestrator,
  float-format conventions, output test gates"): located
  `src/output/{schema,csv,baseline}.py` and `tests/output/test_baseline_e2e.py`;
  confirmed `COLUMN_ORDER` is the per-trial projection, the §9 float formats
  live in `csv.py::_format_row` (`.9f` / `.6f`), and the e2e gate patches
  `base._OUT` to a file literally named `baseline.csv` (so a rename would
  break it).
- *plan* (auggie unavailable; fell back to local `grep`/`Read`. Query
  intent: "how baseline.csv cells are formatted on disk; whether
  pass-through preserves bytes"): confirmed metric cells in `baseline.csv`
  are already formatted strings, so a verbatim string pass-through is
  byte-stable and needs no re-formatting in the view.
- *post-edit re-query* (auggie available; `mcp__auggie__codebase-retrieval`,
  `directory_path = repo root`. Query string: "Describe the new/changed
  behavior for results/baseline/metrics.csv: what module produces it
  (src/output/metrics_view.py), how it derives from baseline.csv, and locate
  all callers/references to metrics_view and metrics.csv across src and
  tests. Surface any stale callsites or references to a renamed/moved
  file."): auggie returned the `metrics_view`/`metrics.csv` source set —
  `src/output/metrics_view.py` (`build_metrics_view`, `_DEFAULT_OUT`, its
  `__main__`) and `tests/output/test_metrics_view.py` — and confirmed
  `src/output/baseline.py` still writes `baseline.csv` to `_OUT`
  unchanged. One-line result: the derived view has no caller other than its
  own `__main__` and its dedicated test; no stale callsite, no inbound
  reference to a renamed/moved file, `baseline.csv` and the e2e gate
  untouched. A cross-check `grep -rn 'metrics_view\|metrics.csv' src tests`
  agreed line-for-line.

## Cross-references

- [[experiments/2026-06-03_scaling-baseline]] — the T41/T70 source dataset.
- [[concepts/output-format]] §2 (canonical file), §6 (NaN dispatch),
  §7 (`n=4` exclusion), §8 (row order), §9 (float formats), §13 (Revisions).
- [[concepts/metric-reconciliation]] — per-protocol metric formulas.
