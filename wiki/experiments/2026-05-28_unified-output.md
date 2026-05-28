# T40 unified output format — build verification

> Build-verification baseline for the unified comparative-CSV pipeline
> introduced by T40. Three protocols' honest-path scenarios driven
> through one writer; one canonical `results/baseline.csv` produced;
> byte-identical determinism verified.

## Outcome

T40 lands the cross-protocol CSV contract pinned by
[[concepts/output-format]] and its implementation in `src/output/`.
The four T40 verify outcomes — **wiki contract resolves the 15
forward-references**, **all three implemented protocols populate the
18-column today subset**, **Snowman n=4 is skipped from the main file
and written to a sibling sanity CSV**, and **two seed-identical runs
produce byte-identical `results/baseline.csv`** — are asserted by the
new `tests/output/test_baseline_e2e.py` plus the per-reducer + writer-
composition unit tests under `tests/output/`, `tests/pbft/`,
`tests/pos/`, `tests/snowman/`.

## Configuration

- `global_seed = 42` (project default).
- PBFT: 3 scenarios at n ∈ {4, 7, 10}, quiescence stop.
- Casper FFG: 4 scenarios at n ∈ {4, 7, 10} uniform + n=4 nonuniform,
  `t_max = 20.0 s`.
- Snowman: 3 scenarios at n ∈ {4, 7, 10}, `t_max = 20.0 s`.
- Commit hash captured at write time per the T27 / T66 reproducibility
  contract; in this baseline `commit_hash = c6082f3b-dirty` (the
  orchestrator was run from the commit-5 tree while commit-6 changes
  were uncommitted; subsequent re-runs at a clean commit-6 tree will
  shift the `commit_hash` column but no other column).

## Result row count

| File | Rows (incl. header) |
| :--- | ---: |
| `results/baseline.csv` | 10 (1 header + 9 data) |
| `results/snowman_n4_sanity.csv` | 2 (1 header + 1 data) |

The 9 data rows: 3 PBFT + 4 Casper FFG + 2 Snowman (`snowman-n4` is
skipped from the main file per [[concepts/output-format]] §7).

## Headline columns

Values produced by `PYTHONPATH=src python3 -m output.baseline` at
commit `c6082f3b-dirty`. Columns: `commit_latency_ms`,
`finality_latency_ms`, `tps`, `consensus_msgs_per_acu`, `success_rate`,
`fork_rate`. Snowman parameter columns shown for Snowman rows only.

| run_id | commit/finality (ms) | tps | consensus_msgs_per_acu | success | fork |
| :--- | ---: | ---: | ---: | ---: | ---: |
| `casper-ffg-n4-nonuniform`  | 5000.000001 | 1.600000 |   5.156250 | 1.0 | 0.0 |
| `casper-ffg-n4-uniform`     | 5000.000001 | 1.600000 |   5.156250 | 1.0 | 0.0 |
| `casper-ffg-n7-uniform`     | 5000.000001 | 2.800000 |   8.785714 | 1.0 | 0.0 |
| `casper-ffg-n10-uniform`    | 5000.000001 | 4.000000 |  12.262500 | 1.0 | 0.0 |
| `pbft-n4`                   | 1000.000003 | 0.003996 |   6.750000 | 1.0 | 0.0 |
| `pbft-n7`                   | 1000.000003 | 0.006993 |  12.857143 | 1.0 | 0.0 |
| `pbft-n10`                  | 1000.000003 | 0.009990 |  18.900000 | 1.0 | 0.0 |
| `snowman-n7`                | 1000.000046 | 6.650000 | 180.857143 | 1.0 | 0.0 |
| `snowman-n10`               | 1000.000046 | 9.500000 | 270.900000 | 1.0 | 0.0 |

Snowman parameter rows (from `_rescale(n)` per
[[concepts/metric-reconciliation#snowman-parameter-rescaling]]):

| n | K | α_p | α_c | β | α_c/K |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 7  | 6 | 4 | 5 | 15 | 0.833333 |
| 10 | 9 | 5 | 8 | 15 | 0.888889 |
| 4 (sanity) | 3 | 2 | 3 | 15 | 1.000000 |

**Observations.**

- **PBFT throughput is conservative by the quiescence-stop denominator.**
  `tps = decided_count / result.now`, and `result.now` advances to the
  primary's `vc_delay = 1000.0` timer rollover even on the honest path,
  so the per-scenario `tps` is `n / ~1001 ≈ 0.004…0.01`. This is the
  honest formula on the quiescence path; it is *not* peak throughput
  (which T58 owns) and it is not comparable across protocols today.
  Recorded on [[concepts/output-format]] §11 extension register under
  `peak_tps` (T58).
- **Snowman `consensus_msgs_per_acu` is materially larger than PBFT's.**
  Snowman's K-peer poll loop fires `K + β·(decided)` query/response
  pairs per block (≈ 180/270 at K=6/9 here), where PBFT's three-phase
  commit fires `≈ O(n²)` per block (≈ 7/13/19 here for n=4/7/10). The
  unified CSV captures both honestly; the cross-protocol message-cost
  comparison Chapter 4 will draw is enabled by this column.
- **Snowman n=4 is excluded from `results/baseline.csv` on purpose**
  ([[concepts/output-format]] §7) and lives in
  `results/snowman_n4_sanity.csv` with `snowman_degenerate_n4=True`.
  The sanity row's K=3, α_c=3 confirm the degenerate `α_c = K` boundary
  documented in [[concepts/metric-reconciliation]] §Snowman parameter
  rescaling §Comparative-claim exclusion at n=4.

## Determinism check

```bash
shasum -a 256 results/baseline.csv > /tmp/t40-baseline.sha
PYTHONPATH=src python3 -m output.baseline
shasum -a 256 -c /tmp/t40-baseline.sha
# results/baseline.csv: OK
```

Verified live at the commit-5 tree state immediately before the
commit-6 stage: two consecutive `python3 -m output.baseline` runs
produce byte-identical `results/baseline.csv` and
`results/snowman_n4_sanity.csv`. `tests/output/test_baseline_e2e.py`
asserts the same property under a monkeypatched commit-hash.

## Auggie verification

- **Pickup-index call.** Query: "describe T40's prior-art surface —
  existing CSV writers, the event-log API, the runner seam,
  per-protocol baseline modules, RunResult, the config schema."
  Returned (deferred to brainstorming transcript): the full
  source-of-truth map for the writer's inputs.
- **Plan-phase re-query.** Query: "enumerate every reference to
  `output-format`, `results/baseline.csv`, `_summarise`,
  `write_baseline_csv` across the codebase + wiki." Returned: the 15
  forward-references catalogued by L-W4 M1 + the one CSV-writing
  callsite (`src/pos/baseline.py::write_baseline_csv`) the plan was
  migrating.
- **Post-edit re-query.** Query: "describe the new `src/output/`
  package; locate every call site of `write_unified_csv` and each
  `summarise`; confirm no stale CSV-writing surface remains in
  `src/pos/baseline.py`." Returned (executed live at commit-6 stage):
  `write_unified_csv` called only from `output.baseline.main`; the
  three `summarise` modules called only from `output.csv._REDUCERS`
  (post-Task-24) and from their per-protocol unit tests;
  `src/pos/baseline.py` no longer imports `csv` or `statistics`, no
  longer exports `write_baseline_csv` / `_summarise` / `_COLUMNS` /
  `main`; integration tests for all three protocols import
  `SCENARIOS` + `run_scenario` from the protocol's `baseline` module
  rather than redeclaring `_config` / `_factory` locally.

## Source pages

- [[concepts/output-format]] — design contract.
- [[concepts/metric-reconciliation]] — per-protocol formulas + Snowman
  rescaling rule.
- [[concepts/event-log-schema]] — raw substrate.
- [[concepts/runner]] — upstream producer.

## Related experiments

- [[experiments/2026-05-25_pos-baseline]] — T35 honest baseline,
  superseded by the T40 unified path; the T35-local
  `results/pos/baseline.csv` (different schema) is retired.
- [[experiments/2026-05-21_pbft-baseline]] — T30 honest baseline,
  preserved on its own per-protocol terms; the unified CSV is a sibling.
- [[experiments/2026-05-27_snowman-baseline]] — T38 honest baseline,
  same.
