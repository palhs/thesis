# 2026-06-19 — Adversarial liveness & safety degradation (T54)

Derived-analysis capstone over the three Family-C adversarial sweeps. No new
simulation runs: T54 reduces the committed T51/T52/T53 datasets into comparable
liveness and per-protocol safety numbers, the interval-censored `f_max`
brackets, and the figures. Measurement spec:
[[concepts/adversarial-degradation-metrics]]. Scope: PBFT, Casper FFG, Snowman
(Narwhal+Tusk unimplemented — its invariant is defined but deferred with T38.1).

## Inputs (source datasets + provenance)

| family | file | rows | commit_hash |
|---|---|---|---|
| delay (T51) | `results/adversary/delayed_voters.csv` | 1920 | `8b2d0bb0-dirty` |
| offline (T52) | `results/adversary/offline_validators.csv` | 560 | `366df826` |
| equivocate (T53) | `results/adversary/equivocating_nodes.csv` | 640 | `c18587d2` |

Each: protocols `{pbft, casper-ffg, snowman}`, `n ∈ {10, 25}`, 20 seeds (common
random numbers). The equivocate φ-grid is `{0, .10, .20, .33, .40, .50}`
(Snowman stops at `.33`). **Provenance caveat:** the T51 dataset was generated
off a dirty working tree (`8b2d0bb0-dirty`); any figure/number quoting T51 (the
delay-family liveness curve) carries that flag.

## Code + artifacts

- `src/output/adversary_analysis.py` — pure-stdlib reducers + the `f_max`
  bracket estimator (reuses `wilson_interval` in `src/output/analysis.py` and
  `mean_ci` in `src/output/delay_analysis.py`; no matplotlib).
- `src/output/adversary_degradation_plots.py` — the figures (matplotlib, Agg).
- `tests/output/test_adversary_analysis.py` — synthetic reducer/bracket cases +
  real-dataset locked-number regression + ranking-CSV byte-stability.
- `tests/output/test_adversary_degradation_plots.py` — render smoke test.
- `results/adversary/degradation_ranking.csv` — 26 rows (18 liveness across the
  three families + 6 equivocate safety + 2 NWT deferred). **Consumed by T55.**
- `results/adversary/snowman_epsilon_witness.csv` — the ε witness (2 rows).
- `results/adversary/plots/*.{pdf,png}` — 6 figures (PDF tracked, PNG ignored).

## Commands to re-derive

```
PYTHONPATH=src python3 -m output.adversary_analysis          # the two CSVs
PYTHONPATH=src python3 -m output.adversary_degradation_plots # the 6 figures
make test-output                                             # 145 tests
```

The ranking CSV is byte-stable (a pure function of the input CSVs; gated by
`test_ranking_csv_is_byte_stable`).

## Observation

The three protocols separate cleanly under equivocation. **PBFT** holds safety
through φ=0.33 via view-change leader rotation (10 view-changes at n=10, 25 at
n=25), then crosses a deterministic **fork cliff** at φ=0.40 (`safety_violation`
1, `conflicting_instances` 229 at both n) — `f_max` safety bracket `[0.33, 0.40]`.
Its liveness is non-monotone (live → stalled at φ∈{0.10,0.20}, a view-change
window artifact → live-but-*forked* at φ≥0.40), so the equivocate-PBFT liveness
rows are flagged `safety_broken`. **Casper FFG** never forks in-model; its
accountable-safety signal (`max_slashable_stake_fraction`) rises with φ and
first reaches ≥1/3 at φ=0.40 (0.30/0.32 at φ=0.33), bracket `[0.33, 0.40]` on
the stake axis. **Snowman** resists entirely — empirical safety-violation rate
0 on every cell (right-censored, `f_max ≥ 0.33`), reported as a witness against
the analytical bound `(1−α_c/K)^β` ≈ 4.9·10⁻¹⁵ (n=10) / 3.3·10⁻¹¹ (n=25) at
β=15. Liveness degrades by family in the expected shapes (FFG most fragile to
delay/offline; PBFT/Snowman robust to delay; the offline cliff at the quorum
boundary). The `f_max` bracket replaces T48's AURC because the equivocate axis
is a discrete cliff, not a smooth retention curve.

## Deferrals / follow-ups (flagged, not done here)

- **Narwhal+Tusk** §5 invariant — defined in the spec, measured when T38.1
  lands (post-T55). Carried as an explicit deferral row, not a silent NaN.
- **Snowman β ∈ {3,5}** ε-observability regime — separate RQ4 sweep; at β=15 ε
  is structurally unobservable.
- **§3.5 `f_max` gloss** — a one-line Writer sync from "smallest-that-breaks"
  to "largest-that-holds" (Backlog item (b)); not edited here (Engineer task).
- **`results/adversarial/` (with `-al`)** — the T54/T55 task text spelling; all
  on-disk artifacts use `results/adversary/`. Flagged for the human.
- **`fork_rate` → `safety_violation_rate`** column rename — a separate schema
  task; this analysis uses the concept name "safety-violation rate" and never
  introduces `fork_rate` as a concept.

## Auggie verification

| phase | query (abridged) | one-line result |
|---|---|---|
| pickup-index | structural map of `src/adversary/`, the per-protocol `summarise.py` safety/liveness columns, the T48/T49 `delay_analysis`/`delay_plots` template, the sweep harness, and where adversarial CSVs are written | located the T51/T52/T53 sweep orchestrators + `src/adversary/safety.py` (safety triple), the reducers, the T48 analysis/plot pair to mirror, and `results/adversary/` as the output dir |
| understand (sub-agents) | the 10-agent understand workflow's code-location readers queried auggie for the safety/liveness producers and the analysis template | confirmed `safety_violation`/`max_slashable_stake_fraction`/`view_change_count` producers + the `mean_ci`/`t_critical_975` CI primitives |
| post-edit re-query | describe the new `adversary_analysis.py` / `adversary_degradation_plots.py` behavior; locate every importer/caller of them + `wilson_interval`; confirm no existing output module changed | the two modules are self-contained additions — only the two new test files import them, `wilson_interval` is called only by `adversary_analysis` + its test, and `analysis.py`/`delay_analysis.py`/`plots.py`/`offline_plots.py`/`adversary_plots.py` behavior is unchanged (no broken references, no stale callsites) |

## Revisions

### [2026-06-24] — §4.4 figure-impact pass (T62 figure slice)

A presentation-only pass over the §4.4 adversarial figures (the "regenerate §4.4
figures for impact + fix the rate/count seam" backlog item, folded into T62).
**No data change** — the three Family-C CSVs and every derived CSV
(`degradation_ranking`, `snowman_epsilon_witness`, `adversary_comparison`,
`robustness_ranking`) are byte-identical (writers re-run, `git diff` clean). The
figure set is now **7** (was 6); the "6 figures" lines under `## Code +
artifacts` and `## Commands to re-derive` predate this pass.

- `adversary_degradation_plots.py` rewritten (render layer): **Fig 4.14** is now a
  2×2 — success rate on top, log-scale time-to-finality ratio below with the
  Snowman ×62 / ×49 blow-up annotated — so PBFT and Snowman no longer read as
  identically immune; **Fig 4.15** (offline) drawn as step cliffs with each
  protocol's survival depth `φ*` boxed and the `n=25` Snowman "alive but
  starved" cell labelled by its surviving throughput; **Fig 4.17** re-expressed
  from view-change *rate* to *count* (shared y-axis across `n`, the `φ=0.40`
  collapse marked) — file renamed `pbft_viewchange_rate_vs_phi` →
  `pbft_viewchange_count_vs_phi`, resolving the L-W10 lint M2 rate/count seam;
  **Fig 4.18** annotates the 229-conflict fork magnitude on PBFT's step; liveness
  panels (4.14–4.16) share a 0–0.50 `φ` axis with a `1/3` reference line; the
  editorializing in-image titles were neutralised (interpretation lives in the
  chapter captions). New **Fig 4.21** `adversary_tradeoff_matrix` renders Table
  4.2 as a 3×3 protocol×adversary outcome map (colour = outcome class, label =
  magnitude).
- `adversary_analysis.py` gained four pure read-only reducers feeding the overlays
  (`delay_finality_ratio_by_phi`, `offline_throughput_ratio`,
  `pbft_view_change_count`, `pbft_conflicting_instances`); no CSV-writer or
  existing reducer changed. Unit tests added (`TestMagnitudeReducers`); the render
  smoke-test fixture was extended to the real column schema. `make test` green.
