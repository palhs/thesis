# [2026-06-09] Explanatory baseline illustrations

A **read-only view** over the frozen Week-8 baseline artifacts
([[experiments/2026-06-08_baseline-cis]], provenance `24a491a4`). Renders six
human-legible charts that surface the *meaning* of the CSV columns rather than
re-plotting them. **Touches no existing logic**: `analysis.py`, `aggregate.py`,
and `plots.py` are unchanged; the new `src/output/explain.py` only reads
`aggregated.csv` / `metrics.csv` and writes to a fresh `results/baseline/explain/`
(plus one promoted thesis PDF, `theory_vs_measured`, into `results/baseline/plots/`).

## Re-run

```
PYTHONPATH=src python3 -m output.explain   # -> results/baseline/explain/*.png
make test-output                           # 102/102 (9 new explain data-layer tests)
```

matplotlib only (already a plotting-only dep, `requirements-dev.txt`); inputs
are the committed CSVs, so nothing in the simulator core is invoked. The
data-layer functions (`load_agg`/`load_trials`/`_theory_line`) carry unit
tests (`tests/output/test_explain.py`); the matplotlib render layer is
untested, matching the `plots.py` convention.

## The six figures and what each one makes visible

1. **`cost_per_commit_bar`** — messages to commit one unit at `n = 16`, log-scale
   bars. The RQ3 headline as a single contrast: PBFT 31.9 (baseline), Casper FFG
   19.1 (0.6×), Snowman 450.9 (**14.1× PBFT**). The order-of-magnitude gap a
   log-line plot buries is unmissable here.
2. **`theory_vs_measured`** — measured `total_msgs_per_acu` markers over each
   protocol's *predicted* slope (dashed): PBFT `2n`, Casper `1.2n`, Snowman
   `2·K·β` with `K=min(20,n−1), β≈15`. Markers sit on the dashed lines →
   visual check the simulator tracks published complexity (largest gaps
   ≈6–7% at n=4; see [[experiments/2026-06-08_baseline-cis]])
   ([[algorithms/pbft#communication-complexity]],
   [[algorithms/pos#communication-complexity]],
   [[algorithms/avalanche#parameters-and-communication-complexity]]).
   **Promoted to a thesis figure (Chapter 4, Figure 4.7):** additionally
   rendered as a tracked vector PDF to `results/baseline/plots/theory_vs_measured.pdf`
   beside the canonical `plots.py` figures, and cited from [[drafts/ch4_results]]
   §4.2.4 as the visual form of the RQ3 theory-match claim. (The data-plot
   figure convention is still Mermaid-only in `draft-style.md`; extending it is
   the open L-W8 lint item M2, to settle at T62.)
3. **`variance_heatmap`** — coefficient of variation per metric × protocol.
   Everything is `0` (deterministic) except `goodput` (≈2.2–2.3%). Makes the
   T44 dominant finding — *the baseline is deterministic except for workload
   noise* — readable at a glance.
4. **`goodput_spread`** — the 20 per-seed `goodput` samples per protocol
   (box + strip) with the mean ± 95% CI diamond. The one metric that truly
   varies, shown honestly; PBFT and Snowman overlap exactly (same per-block
   workload), Casper sits lower (per-epoch finality tail).
5. **`profile_panel`** — ratio-to-best tradeoff shape at `n = 16` across speed
   (low latency), throughput, and frugality (low msg cost). Each protocol's
   give-and-take in one frame: PBFT balanced, Casper cheap-but-slow (0.20
   speed), Snowman fast-but-expensive (0.04 frugality).
6. **`overview`** — 2×2 dashboard (latency, goodput, msg-cost, decision-rate
   vs `n`) for a one-screen read of all four trends.
7. **`pbft_2n_validation`** — derives PBFT's `≈2n` per-unit cost from its
   message phases: (a) one all-to-all phase = `n(n−1)` (n×n send matrix at
   n=4), (b) per instance the two all-to-all phases (PREPARE, COMMIT)
   dominate → `2(n²−1)` total, (c) ÷ `n` decisions/instance gives
   `2n − 2/n → 2n`, with measured points on the closed form. Phase counts
   confirmed exact against the simulator (`tests/output/test_explain.py`).

## Interpretation guards carried into the charts

The charts inherit the T44 caveats so a reader cannot misread them:

- Panel (d) of `overview` is **`tps` (decision events/s)**, labeled "scales
  with `n` by construction" — `tps/n` is constant (PBFT/Snowman 0.95, Casper
  0.40), so it is an event count, not system throughput. The honest throughput
  is `goodput` (panel b), flat in `n`.
- Flat `goodput` = **no saturation in the latency-only model**, not a measured
  capacity ceiling (`peak_tps` needs a capacity model, deferred).
- Flat latency = **zero-delay artifact**; the `n`/delay latency story is W9.
- `success_rate`/`fork_rate` are uninformative here (all 1.0 / 0.0) — they
  discriminate only under the W10 adversary, so they are not given a headline
  chart.
- Latency uses `commit_latency_ms` only (never the PBFT-only
  `finality_latency_ms`), per [[concepts/output-format]] §13.
- `profile_panel` is **ratio-to-best within this 3-protocol set**, an explicitly
  relative shape, not absolute performance.

## Theory reconciliation (per protocol)

| protocol | predicted per-unit cost | measured (n=16) | match |
| :-- | :-- | :-- | :-- |
| PBFT | `2n` (O(n²)/instance ÷ n decisions) | 31.9 ≈ 2·16 | ✓ |
| Casper FFG | `≈1.2n` (one attestation round) | 19.1 ≈ 1.2·16 | ✓ |
| Snowman | `2·K·β`, `K=min(20,n−1)`, `β≈15` | 450.9 ≈ 2·15·15 | ✓ (ratio 1.00) |

Snowman's growth across `n∈{7…25}` is **K-rescaling** (`K` tracks `n−1` below
`n≈21`), not a true `n`-dependence — the published per-validator
`n`-independence is masked at thesis scale. Stated so the contrast is not
misread (full treatment in [[experiments/2026-06-08_baseline-cis]] / Ch. 4).

## Verification

All six charts were independently recomputed from the frozen CSVs by a
parallel adversarial pass (one auditor per chart). Every *rendered numeric
value* reconciled to displayed precision, and all three cost curves matched
their theory slope within ~7% (Snowman <0.5%). The pass caught one real
defect, now fixed: `goodput_spread` originally pooled samples across all `n`,
which (a) inflated each box from 20 to 80–120 points, (b) double-counted
Casper's `n=4` uniform/nonuniform pair, and (c) overlaid an `n=16`-only CI on
the pooled box. Fixed by restricting the chart to `n=16` — a true 20-sample
distribution whose CI diamond sits on exactly the points it summarizes. Two
cosmetic fixes followed (a docstring "≈26×" → the reproducible ≈14× Snowman/
PBFT gap; a legend entry naming the theory line). No new simulation; charts
are a pure function of the committed data.

## Scope / deferrals

Delay-axis and adversarial illustrations follow the W9/W10 datasets. These are
explanatory companions to the Chapter-4 figures, not replacements — the
thesis figures remain the `plots.py` PDFs.
