# [2026-06-13] T48 — Comparative delay/loss resilience: ranking + plots

Synthesizes the two Family-B delay datasets (`results/delay/delay.csv`, T46
moderate; `results/delay/delay_heavy.csv`, T47 heavy-tail + packet loss) into a
**cross-protocol resilience ranking table** plus a **comparison plot set** for
Chapter 4. Descriptive only: this task lands the numbers and figures; the
"which degrades most gracefully and *why*" analysis is T49, and the Ch. 4 prose
is T50.

This page is the methodology contract the `src/output/delay_analysis.py` +
`src/output/delay_plots.py` artifacts reference.

## Locked methodology (human decisions 2026-06-13)

Criteria were selected via a 5-proposal + 1-evaluator design pass; the human
made the final calls. Key revision to the Week-9 plan
([[experiments/2026-06-12_delay-heavy]] §Locked methodology):

- **The 95 %-finalization breakpoint is DROPPED entirely.** Two reasons: (1)
  the 0.95 threshold is an SLA convention with no theoretical backing, and (2)
  it saturates — mean `finalization_rate` is already below 0.95 at the first
  tested loss level (`p_drop = 0.05`) for **all six** protocol × n cells (the
  best cell anywhere is Snowman n=25 at 0.904). As a sort key it declares a
  six-way tie; as a column it prints "<0.05" six times. No `breakpoint_95`
  column, and **no 0.95 reference line on any plot**. This revises the
  Week-9 decision that named the 95 % breakpoint the discriminator.
- **Primary ranking key = AURC** (Area Under the Retention Curve): the area
  under the `finalization_rate`-vs-`p_drop` curve over `[0, 0.20]`, by plain
  trapezoid over the **actual uneven spacing** (`{0, 0.05, 0.10, 0.20}`, so the
  wide 0.10→0.20 gap counts double), normalized by the 0.20 width to land on
  `[0, 1]`. No threshold. Computed **per seed** so its 95 % Student-t CI is
  available for the tie test (`df = n_seeds − 1`).
- **Tiebreak = survival-depth**: the deepest `p_drop` whose mean
  `finalization_rate` is still > 0 — the principled liveness-collapse boundary
  (fr = 0), not a convention.
- **`n = 10` and `n = 25` are reported UNPOOLED** in both table and plots;
  committee size flips the Snowman ordering and that is itself a finding.
- **Statistical-tie rule:** within an `n` block, adjacent rows (sorted by AURC
  desc) whose AURC 95 % CIs overlap **share a rank**. Verified to fire at
  n=25 (Snowman edges PBFT on AURC but the CIs overlap).
- **Cost is displayed, never folded into the rank:** added-latency ratio,
  message overhead, and PBFT view-change churn are Pareto columns the reader
  reads alongside the rank — no hidden weighted scalar.
- **Latency comparisons anchor to each protocol's OWN loss-free heavy-tail
  control**, never to the differently-configured baseline dataset (different
  slot / workload / clip), which would be apples-to-oranges.
- **Comparison latency column:** `commit_latency_ms` (uniform across protocols),
  per [[concepts/output-format]] §13.

## Metric definitions

- **AURC** — see above. Reuses the Student-t machinery from
  [[experiments/2026-06-08_baseline-cis]] (`output.analysis.t_critical_975`).
- **survival-depth `p*`** — deepest loss level with mean fr > 0.
- **added-latency ratio** — `commit_latency_ms` at the worst loss level the
  protocol still finalizes at, ÷ its loss-free control latency. The price of
  staying alive.

## Output artifacts

- **`results/delay/resilience_ranking.csv`** — two blocks (n=10 then n=25),
  ranked by (AURC desc, survival-depth desc), columns: `rank, tie, protocol,
  n, n_seeds, aurc, aurc_ci_lo, aurc_ci_hi, fr_at_0_05, fr_at_0_10, fr_at_0_20,
  survival_depth_p, worst_finalizing_p, added_latency_ratio_worst,
  msgs_per_acu_worst, view_changes_at_0_20, control_commit_latency_ms,
  moderate_delay_latency_ms`. Pure read→compute→write, byte-stable.
- **`results/delay/plots/`** — five figures (PDF tracked, PNG gitignored per
  [[drafts/ch4_results]] figure convention):
  1. `finalization_degradation` — fr vs `p_drop`, faceted n=10/n=25, 95 % CI.
     The headline; no 0.95 line.
  2. `latency_cliff` — `commit_latency_ms` (log) vs `p_drop`, solid while
     finalizing, `×` marker where liveness is lost. Graceful-vs-cliff.
  3. `operator_pareto` — retained finality (y) vs added-latency ratio (x, log);
     dead cells pinned on a "no finality" band. Upper-left is operator-best.
  4. `cost_of_survival` — `total_msgs_per_acu` (log) vs `p_drop`, PBFT
     view-change counts annotated. Displayed cost only.
  5. `moderate_latency` — context: `commit_latency_ms` under the two moderate
     T46 timelines (uniform vs exponential), faceted by n.

## Results — resilience ranking

`AURC` is the normalized area under the retention curve; `surv` is
survival-depth (deepest `p_drop` with fr > 0); `lat×` is the added-latency
ratio at the worst finalizing loss level. CIs are 95 % Student-t over seeds.

**n = 10** (20 seeds; strict order, no tie):

| rank | protocol | AURC [95 % CI] | surv `p*` | lat× | fr@.05 | fr@.10 | fr@.20 |
| :-- | :-- | :-- | --: | --: | --: | --: | --: |
| 1 | PBFT       | 0.253 [0.246, 0.261] | 0.20 | 2.84 | 0.169 | 0.161 | 0.104 |
| 2 | Snowman    | 0.174 [0.172, 0.176] | 0.05 | 2.16 | 0.195 | 0.000 | 0.000 |
| 3 | Casper FFG | 0.149 [0.142, 0.156] | 0.10 | 1.03 | 0.070 | 0.018 | 0.000 |

**n = 25** (20 seeds, Snowman 8; PBFT/Snowman a statistical tie at #1):

| rank | protocol | AURC [95 % CI] | surv `p*` | lat× | fr@.05 | fr@.10 | fr@.20 |
| :-- | :-- | :-- | --: | --: | --: | --: | --: |
| 1 (tie) | Snowman | 0.369 [0.366, 0.372] | 0.10 | 3.11 | 0.904 | 0.047 | 0.000 |
| 1 (tie) | PBFT    | 0.351 [0.327, 0.376] | 0.20 | 3.57 | 0.533 | 0.211 | 0.056 |
| 3 | Casper FFG | 0.140 [0.135, 0.146] | 0.10 | 1.10 | 0.051 | 0.006 | 0.000 |

## Observations (descriptive — mechanism analysis is T49)

- **Overall resilience ranking: PBFT ≥ Snowman > Casper FFG**, but it is
  committee-size-dependent. At n=10 PBFT leads cleanly; at n=25 PBFT and
  Snowman are a **statistical tie** at the top (their AURC CIs overlap) and
  Casper FFG is last at both sizes.
- **The n=25 tie is a genuine crossover, not noise.** Snowman wins on
  area-under-curve (it retains 0.90 finality at 5 % loss, far above PBFT's
  0.53) but dies by 10 %; PBFT retains less at light loss yet is the **only**
  protocol still finalizing anything at 20 % loss (survival-depth 0.20 vs
  0.10). The two metrics reward different virtues, so neither is crowned alone.
- **The arbitrary 95 % breakpoint would have hidden all of this** — every cell
  is below 0.95 by the first loss step, so the dropped metric resolves to a
  flat six-way tie. AURC + survival-depth separate the field cleanly.
- **Cost asymmetry is visible in the Pareto view.** Casper FFG barely inflates
  latency (≈1.0–1.1×) but dies first; PBFT and Snowman pay 2.8–3.6× latency,
  and only PBFT converts that cost into tail survival.
- **Committee size is a resilience lever**, sharply for Snowman (fr@.05 0.195→
  0.904 from n=10 to n=25) and for PBFT (0.169→0.533), but a mild liability for
  Casper FFG (0.070→0.051) — hence the unpooled reporting.

## Scope and deferrals

- **Descriptive only.** Why view-change buys PBFT its tail survival, why
  Snowman's redundancy scales with `K`, why Casper FFG has no recovery path —
  all reserved for **T49** ([[experiments/2026-06-12_delay-heavy]] §Observations
  sketches these but the graded analysis is T49's deliverable).
- **Ch. 4 delay section** (≥6 plots + 2-page write-up) is **T50**.
- **Narwhal+Tusk** absent (T38.1 blocked); **`partial-sync-gst`** timeline is a
  separate backlog task, not part of the delay/loss degradation story.

## Re-run

```
PYTHONPATH=src python3 -m output.delay_analysis   # writes resilience_ranking.csv + prints ranking
PYTHONPATH=src python3 -m output.delay_plots      # writes results/delay/plots/*.{png,pdf}
make test-output                                  # tests/output/test_delay_analysis.py (+ suite)
```

## Auggie verification

Per the Engineer protocol, every `mcp__auggie__codebase-retrieval` call made
during the task (query, one-line result, phase):

- **pickup-index** — query: *"where is the code that reads
  results/delay/delay*.csv and the existing plotting/analysis/aggregation code
  (analysis.py CSV load + Student-t CI + METRICS; plots.py matplotlib STYLE +
  faceting + PDF/PNG conventions; explain.py / aggregate.py reusable helpers;
  how delay CSVs are consumed in src/delay/)?"* Result: mapped the
  `EventLogger → summarise → csv.write_unified_csv → results CSV → aggregate →
  Chapter-4 plots` pipeline; confirmed `output.analysis` exposes
  `load_rows` / `aggregate` / `t_critical_975` / the `Agg` dataclass and that
  `plots.py` owns the `STYLE` palette + `_fig` PNG+PDF writer — establishing
  "add a sibling `delay_analysis.py` + `delay_plots.py` pair reusing
  `t_critical_975` and `STYLE`" rather than overloading the baseline modules.
- **post-edit re-query** — query: *"describe the new `output.delay_analysis`
  (aurc / survival_depth / ranking_for_n / write_ranking_csv) and
  `output.delay_plots`, locate their callers and confirm the imports from
  output.analysis (t_critical_975) and output.plots (STYLE, PROTO_ORDER)
  resolve."* Result: confirmed `delay_analysis` imports `t_critical_975` from
  `output.analysis` (present) and `delay_plots` imports `STYLE` + `PROTO_ORDER`
  from `output.plots` (both present); the two are leaf modules with no callers
  other than their own `main()` and `tests/output/test_delay_analysis.py`
  (which imports `from output import delay_analysis as da` correctly); no stale
  or broken references. `make test` 869 tests across 13 suites all green.

## Cross-references

- [[experiments/2026-06-12_delay-heavy]] — T47, the heavy-tail + loss dataset
  (`delay_heavy.csv`) this ranks; source of the `finalization_rate` column.
- [[experiments/2026-06-10_delay-moderate]] — T46, the moderate dataset
  (`delay.csv`) used as latency-growth context.
- [[experiments/2026-06-08_baseline-cis]] — the Student-t CI method reused here.
- [[experiments/2026-06-08_baseline-plots]] — the `plots.py` house style
  (`STYLE`, faceting, PDF/PNG split) this builds on.
- [[concepts/output-format]] §13 — `commit_latency_ms` as the cross-protocol
  latency column.
- [[concepts/research-questions]] — RQ4 (resilience under adverse networks),
  which this ranking answers descriptively.

## Revisions

### [2026-06-15] T50 — sixth Chapter-4 figure added (`resilience_ranking`)

The Chapter-4 delay write-up (T50) added a sixth figure to
`src/output/delay_plots.py`, `fig_resilience_ranking(heavy, moderate)` →
`results/delay/plots/resilience_ranking.{pdf,png}`: an AURC bar chart with 95%
Student-t CIs, faceted by `n` (10 / 25), each bar annotated with its
survival-depth `p*`. It reads the same `ranking_for_n` that
`resilience_ranking.csv` is written from, so figure and table cannot drift
(verified: bar values reproduce the CSV to 6 decimals). Rationale: §Output
artifacts lists five figures, none of which renders the AURC scalar with its
CI, so the `n=25` PBFT/Snowman statistical tie (the overlapping AURC intervals)
was visible only indirectly through the `finalization_degradation` curve
crossover. The bar chart makes the overlap — and the survival-depth tiebreak —
directly legible. Pure read of the frozen `resilience_ranking.csv`: no new runs
and no data change. Re-running `PYTHONPATH=src python3 -m output.delay_plots`
now emits six figures; the five pre-existing PDFs were left untouched
(re-rendered only on demand) to avoid churning their committed blobs. Cited as
Figure 4.10 in [[drafts/ch4_results]] §4.3.2.

### [2026-07-01] `msgs_per_acu`-under-loss finding surfaced in §4.3.2 (Figure A.3)

Closes a gap flagged in a Ch4 read-through: the clean-path `total_msgs_per_acu`
RQ3 result (§4.2) was never confronted with the loss sweep, even though the
`cost_of_survival` figure (§Output artifacts #4) already plotted it. That figure
had been cut from the Ch4 body during the W1 condensation wave and left
unreferenced. It is now restored as **Figure A.3** (Appendix A) with a new
§4.3.2 paragraph reporting the numbers. No new runs and no data change — the
values are the committed `delay_heavy.csv` means (per-seed, `finalized_instances
> 0` only), reproduced from `heavy_metric_means`:

- **PBFT `total_msgs_per_acu` (n=25)** inflates 50.0 → 84.6 → 134.8 → 678.2 across
  `p_drop ∈ {0, .05, .10, .20}` (≈13.5×; worst seed 1368), driven by two fronts:
  view-change retransmits (numerator, mean vc 0 → 75) **and** the collapsing ACU
  denominator (`finalized_instances` 993 → 55).
- **The clean-path cost order does not survive loss.** Casper FFG, cheapest on
  the control (25.5), craters to 328.5 (p05) / 1666.2 (p10) as its denominator
  collapses with no recovery path, **overtaking PBFT**. Snowman reaches 5.0×10⁴
  at p10 (n=25, 8-seed heavy cell). At p20 only PBFT still finalizes.
- **RQ3 headline (Snowman ≫ deterministic) holds and widens**, but PBFT — not
  Casper FFG — is the cheapest per committed unit at every loss level it clears.

This is consistent with, and quantifies, the §Observations note that "only PBFT
converts [latency] cost into tail survival": that survival is bought with an
order-of-magnitude message-overhead rise. `results/delay/plots/cost_of_survival.pdf`
regenerated (byte-refreshed, content identical) and copied into the tex repo's
`figures/`. §6.2 unchanged: the residual caveat (permanent-loss, no
retransmission → upper bound) already covers the overhead inflation.
