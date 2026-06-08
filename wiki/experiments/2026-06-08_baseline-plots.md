# [2026-06-08] T43 — Baseline comparison plots

Renders the Chapter-4 baseline figures from the T41/T70 scaling dataset
(`results/baseline/baseline.csv`, 300 rows, provenance `24a491a4`). One
figure per metric vs. validator-set size `n ∈ {4,7,10,16,25}`, one curve
per protocol (PBFT, Casper FFG, Snowman). No new simulation — pure view
over the committed CSV. CIs are added by T44; this task lands the trend
plots (`--no-ci`).

## Artifacts

- `src/output/analysis.py` — stdlib aggregation (mean / std / SEM / 95% CI
  via Student-t; grouping per `run_id`). Shared with T44.
- `src/output/plots.py` — matplotlib renderer → `results/baseline/plots/`.
- `tests/output/test_analysis.py` — 11 unit tests (CI math, grouping, NaN
  handling, real-dataset smoke). `make test-output` 86/86 green.
- Figures (PDF tracked in git; PNG regenerable, `.gitignore`d):
  `latency_vs_n`, `throughput_vs_n`, `msgs_vs_n`, `success_rate_vs_n`,
  `decision_rate_vs_n`, `goodput_ci_vs_n`.

## Re-run

```
pip install -r requirements-dev.txt        # matplotlib (plotting-only dep)
PYTHONPATH=src python3 -m output.plots --no-ci   # T43 trend curves
PYTHONPATH=src python3 -m output.plots           # T44 with 95% CI bars
```

matplotlib is a plotting-only dependency (`requirements-dev.txt`); the
simulator and `analysis.py` stay stdlib-only, so the dataset regenerates
and aggregates without it.

## Comparable-column discipline

The latency figure plots **`commit_latency_ms`**, not `finality_latency_ms`,
per [[concepts/output-format]] §13 Revisions [2026-06-05]: T70 added a
PBFT-only `f+1` client-REPLY hop, so `finality_latency_ms` is PBFT-internal
and not apples-to-apples. `commit_latency_ms` (median per-node time to the
first internal `decided` instance) is the only uniformly-defined latency
column across the three protocols.

## Figures and what they show

- **`latency_vs_n`** — `commit_latency_ms`. Flat in `n`: PBFT and Snowman at
  ≈ 1000 ms (one `propose_delay` / `slot_duration`), Casper FFG at ≈ 5000 ms
  (justify→finalise spans epochs). Latency is set by round structure, not
  validator count, at the zero-delay baseline.
- **`throughput_vs_n`** — `goodput` (committed tx/s). Flat in `n`: ≈ 95 for
  the per-block protocols PBFT/Snowman, ≈ 80 for Casper FFG (per-epoch
  finality-tail leaves the window's last epoch uncommitted). No saturation.
- **`msgs_vs_n`** — `total_msgs_per_acu` (log y). All three grow with `n`;
  Snowman is an order of magnitude above PBFT > Casper FFG. The central
  performance/structure contrast for RQ3 ([[concepts/research-questions]]).
- **`success_rate_vs_n`** — constant 1.0 everywhere (honest baseline; no
  faults). Carries no comparative signal until the W10 adversarial runs.
- **`decision_rate_vs_n`** — `tps` (decided events/s). Grows ≈ linearly in
  `n` — a decision-event count, not a system tx rate (see T44 stats notes).
- **`goodput_ci_vs_n`** — goodput with visible 95% CI bars: the one metric
  with real seed-to-seed variance (workload-driven, CV ≈ 2.2%).

## Theory anchors (full comparison in [[experiments/2026-06-08_baseline-cis]] / Ch. 4)

- PBFT `O(n²)` per block, 3-round latency [[algorithms/pbft#communication-complexity]].
- Casper FFG `O(n)` aggregated per epoch, 2-epoch finality
  [[algorithms/pos#communication-complexity]].
- Snowman per-validator `O(K·β)`, latency invariant to `n`
  [[algorithms/avalanche#parameters-and-communication-complexity]].

## Scope / deferrals

- CIs, the aggregated CSV, and the full statistical-meaning analysis are
  T44 ([[experiments/2026-06-08_baseline-cis]]).
- Delay-axis plots → T48–T50; adversarial → T55–T56. Narwhal+Tusk → T38.1.

## Auggie verification

`mcp__auggie__codebase-retrieval` is unavailable in this environment (same
as [[experiments/2026-06-03_scaling-baseline]]); the GitHub-indexing
fallback returns `[REPO_NOT_FOUND]` for `palhs/thesis`. Structural search
used local `grep`/`Read`: confirmed `src/output/` houses the T40 writer
(`csv.py`, `schema.py`, `baseline.py`) and `metrics_view.py`; the new
`analysis.py` / `plots.py` add the read-only view layer with no caller into
the simulator core, and `analysis.py` has no non-stdlib import.
