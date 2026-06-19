# T54 — Adversarial liveness & safety degradation metrics — Design

- **Task:** T54 (Engineer) — "Measure liveness and safety degradation."
- **Artifact:** a metrics spec + plots.
- **Status:** design (this doc) → writing-plans → TDD execution.
- **Date:** 2026-06-19.

## 1. Context and scope

T54 is the analysis/spec/plots capstone over the three Family-C adversarial
sweeps already on disk:

- T51 `delay-emission` (delayed voters) — `results/adversary/delayed_voters.csv`
- T52 `withhold-participation` (offline validators) — `results/adversary/offline_validators.csv`
- T53 `equivocate-vote` (equivocating nodes) — `results/adversary/equivocating_nodes.csv`

T54 **derives** liveness and the four per-protocol safety invariants from these
CSVs. It does **not** re-run any sweep, does **not** mutate the raw CSVs, and
does **not** implement new protocols. T55 (downstream) owns the
algorithm × adversary × metric comparison tables and the robustness ranking;
T54 produces the per-metric measurement + the durable metric spec T55 cites.

The four protocols in scope are PBFT, Casper FFG, Snowman. **Narwhal+Tusk is
unimplemented** (T38.1 blocked, sequenced post-T55), so its §5 invariant is
defined in the spec but reported as a documented deferral, not measured. T54
delivers **3 of 4** invariants empirically.

## 2. Locked methodology decisions (user-approved 2026-06-19)

1. **Liveness scope = all three families.** Safety can only come from the
   equivocate sweep (the only one carrying the safety signals); liveness is
   measured across delay, offline, and equivocate.
2. **Liveness metric = "% of seed-runs reaching consensus"** = `mean(success_rate)`
   per `(family, protocol, n, φ)` cell, with a **Wilson** proportion interval.
   Draft-consistent: `ch3_methodology.md` §3.5 defines a liveness failure as the
   complement of `success_rate` and aggregates rate metrics with Wilson. Not a
   per-round fraction (that would contradict the chapter; `success_rate` is a
   per-run 0/1 flag and "round" is non-uniform across protocols).
3. **Snowman ε = witness table from existing β=15 data.** Empirical
   ε = `mean(safety_violation)` (= 0 on every cell) with a Wilson upper bound;
   analytical bound `(1 − α_c/K)^β` derived from the row's `K`/`alpha_c`/`beta`
   columns (≈ 4.9·10⁻¹⁵ at n=10, ≈ 3.3·10⁻¹¹ at n=25). The β ∈ {3,5}
   observability sweep is **deferred** to a separate RQ4 regime (also
   draft-consistent, §3.5). No re-run in T54.
4. **Data approach = derive in a new analysis layer.** Raw CSVs untouched.
   Canonical schema names (`f_max_count`/`f_max_stake`) appear only in the new
   ranking CSV. Honors the standing "no standalone `analytical_epsilon_bound`
   per-row column" decision (`metric-reconciliation.md`).
5. **f_max = interval-censored grid bracket.** Report `[largest φ that holds,
   first φ that breaks]` over the φ grid (`{0,0.10,0.20,0.33,0.40,0.50}` for
   PBFT/FFG; `{0,0.10,0.20,0.33}` for Snowman). The headline **f_max point = the
   hold edge** (largest φ under which the invariant holds), matching the binding
   `evaluation-metrics.md` definition; the break edge is the upper censoring
   bound. This unifies T52's `f*` (= break edge) and `f_max` (= hold edge) as the
   two ends of one bracket. The §3.5 "smallest-that-breaks" gloss is reconciled
   to "largest-that-holds" — a one-line Writer sync flagged for follow-up
   (Backlog item (b) sanctions T54 tightening this).
6. **Metrics-spec deliverable = a new wiki concept page**
   (`wiki/concepts/adversarial-degradation-metrics.md`), not Revisions scattered
   across existing pages.

## 3. Data sources (read by NAME)

All three CSVs share columns 1–24 byte-identically (the T40 comparative prefix +
Snowman params) but their tails diverge in **both membership and order**
(`byzantine_fraction` is col 26 in T51 vs col 27 in T52/T53; T51 lacks
`adversary_node_count`). The loader therefore reads by column name, never by
position.

| file | family | rows | commit | headline / safety columns |
|---|---|---|---|---|
| `delayed_voters.csv` | delay | 1920 | `8b2d0bb0-dirty` | `finality_delay_ratio`, `view_change_count`(=0), `success_rate`; axes `byzantine_fraction`+`delay_mult` |
| `offline_validators.csv` | offline | 560 | `366df826` | `throughput_ratio`, `success_rate`, `view_change_count`; axis `byzantine_fraction` |
| `equivocating_nodes.csv` | equivocate | 640 | `c18587d2` | `safety_violation`, `conflicting_instances`, `max_slashable_stake_fraction`, `view_change_count`, `success_rate`, `K`/`alpha_p`/`alpha_c`/`beta`/`alpha_c_over_K`; axis `byzantine_fraction` |

Common keys for joining: `{protocol, n, seed, byzantine_fraction}` (+ per-family
axes: delay also has `delay_mult`). Grids: protocols `{pbft, casper-ffg, snowman}`,
`n ∈ {10,25}`, 20 seeds. **Provenance flag:** T51's dataset was generated off a
dirty tree (`8b2d0bb0-dirty`); any T54 figure/table citing T51 numbers carries
that caveat.

## 4. The four per-protocol safety invariants (adversary-model §5/§7)

| protocol | invariant (verbatim §5/§7) | operationalization | data status |
|---|---|---|---|
| PBFT | "no two-honest commit conflict at same (view, seq)"; operational invariant "view-change frequency tracks equivocator rate" (§5) | within-threshold: `view_change_count / run_horizon_s`; above-threshold: the fork cliff (`safety_violation`, `conflicting_instances`) | already in CSV. φ≤0.33: 10(n=10)/25(n=25) view-changes, safe; φ≥0.40: cliff (`safety_violation`=1, `conflicting_instances`=229, view-change→0) |
| Casper FFG | "any two-conflicting-finalised → ≥1/3 stake slashable" (§7.3) | does `max_slashable_stake_fraction` reach ≥1/3? = realized ⌊φ·n⌋/n | already in CSV; crosses ⅓ at φ=0.40. FFG never forks in-model (`EpochState.links` ignores `target_hash`) → frame as "economically-possible violation crosses the slashing threshold," not "fork observed" |
| Snowman | "empirical safety-violation rate ≤ (1 − α_c/K)^β" (§5/§7.1) | empirical = `mean(safety_violation)` (=0) + Wilson UB; analytical = `(1 − α_c/K)^β` from row cols | empirical derivable (=0); analytical = 1-line calc. Witness table (Q3) |
| Narwhal+Tusk | "no conflicting header reaches 2f+1 signatures" (§5) | `conflicting_header_reaches_2f1` (bool) — spec only | **unmeasurable** (NWT unimplemented). Documented deferral, not silent NaN |

## 5. Liveness metric

Per `(family, protocol, n, φ)` cell: `liveness_rate = mean(success_rate)` over
the 20 seeds, with a Wilson interval on the `k`-of-`n_seeds` proportion.

**PBFT non-monotone caveat (must be honored):** in the equivocate data PBFT
`success_rate` is 1.0 at φ=0/0.33, 0.0 at φ∈{0.10,0.20} (in-window view-change
miss at `PBFT_VC_DELAY_S=3.0`), and 1.0 again at φ≥0.40 where the **fork**
decides (consensus "reached" but *unsafely*). Liveness is therefore always
reported **jointly** with the safety column, and equivocate φ≥0.40 PBFT cells
carry a `safety_broken=True` flag so the "live" reading is never mistaken for
resilience.

## 6. f_max estimator

`bracket(phi_grid, holds_at)` walks the sorted φ grid and returns
`(hold_edge, break_edge)` = (largest φ with `holds_at(φ)` true, first φ with it
false). Right-censored (never breaks in grid) → `(max φ, None)` reported as
"≥ max φ, no break observed". Left-censored (broken at φ=0) → `(None, 0.0)`.

- **Headline f_max = hold_edge.** Bracket reported as the censoring interval.
- **Per-protocol column routing** (`output-format.md` §6 mutually-exclusive
  rule): `f_max_count` for PBFT/Snowman (and NWT when it lands), `f_max_stake`
  for Casper FFG; the other is `NaN`.
- **No CI on safety brackets.** The equivocate safety signals are
  **seed-invariant** (deterministic parity partition, no adversary RNG — every
  cell has exactly one safety tuple across its 20 seeds), so a per-seed CI is
  zero-width. Only the **liveness** bracket carries a Wilson band.
- **Departure from T48's AURC** (documented in the spec page): the equivocate
  axis is a discrete safety **cliff** (step function), not a smooth retention
  curve, so AURC is the wrong scalar — the robustness key is the f_max bracket
  (a survival-depth analogue: deepest φ with the invariant intact).

Worked brackets (from the data): PBFT safety = `[0.33, 0.40]` (point 0.33);
FFG slashing-threshold = `[0.33, 0.40]` (0.32<⅓ at 0.33, 0.40≥⅓ at 0.40);
Snowman safety = `≥0.33` (no break observed); liveness f* edges reuse T52
(PBFT 0.40, FFG 0.10, Snowman 0.20@n=10 / 0.33@n=25).

## 7. Module layout & signatures

**`src/output/adversary_analysis.py`** (pure-stdlib, no matplotlib):

- `load_adversary_rows(paths) -> list[AdvRow]` — read each CSV by name, tag
  `family`, expose a uniform record (join keys + per-family axes + metric cols).
- `liveness_rate(rows, family, protocol, n) -> dict[float, WilsonRate]` —
  `mean(success_rate)` + Wilson per φ.
- `pbft_view_change_rate(rows, n) -> dict[float, float]` —
  `view_change_count / run_horizon_s` per φ (equivocate).
- `ffg_slashable(rows, n) -> dict[float, float]` — `max_slashable_stake_fraction`
  per φ, with the ⅓ reference (equivocate).
- `snowman_epsilon_witness(rows, n) -> EpsilonWitness` — empirical
  `mean(safety_violation)` + Wilson UB, analytical `(1 − α_c/K)^β` from row cols.
- `nwt_invariant() -> dict` — documented "deferred — T38.1" stub.
- `bracket(phi_grid, holds_at) -> (hold_edge, break_edge)` — the f_max estimator.
- `f_max_for(invariant_curve, protocol) -> FMaxRow` — bracket + `f_max_count`
  vs `f_max_stake` routing + theoretical-bound comparison.
- `write_ranking_csv(rows, path) -> None` — byte-stable, mirrors
  `delay_analysis.write_ranking_csv`.

**`src/output/analysis.py`** (shared CI primitive home): add
`wilson_interval(k, n, z=1.96) -> (lo, hi)` next to `t_critical_975`. Reuse
`mean_ci`/`t_critical_975` from `analysis.py`/`delay_analysis.py` — do not
re-implement.

**`src/output/adversary_degradation_plots.py`** (matplotlib; imports
`STYLE`/`PROTO_ORDER` from `output.plots`, dual PNG@150dpi + PDF, `PLOT_DIR =
results/adversary/plots`):

- `fig_liveness_vs_phi` — `mean(success_rate)` + Wilson band vs φ, faceted 1×2 by
  n, one figure per family (delay/offline/equivocate); PBFT non-monotone caveat
  in the caption.
- `fig_pbft_viewchange_rate_vs_phi` — view-change rate vs φ, faceted by n
  (equivocate).
- `fig_ffg_slashable_vs_phi` — `max_slashable_stake_fraction` vs φ with a ⅓
  reference line, faceted by n (equivocate).
- `fig_safety_cliff_vs_phi` — `safety_violation` (or `conflicting_instances`) vs
  φ, all three protocols, faceted by n (equivocate).
- Snowman ε and the f_max bracket summary are **tables** (in the ranking CSV +
  the spec/experiment pages), not figures.

Exact faceting is finalized in the implementation plan.

## 8. Outputs

- `results/adversary/degradation_ranking.csv` — one row per
  `(family/invariant, protocol, n)`: `f_max_hold`, `f_max_break`,
  `f_max_count`/`f_max_stake` (one populated, the other NaN), the theoretical
  bound (`< n/3`, `< 1/3 stake`, parameter-dependent, or deferred-NWT), the
  liveness rate at the breakpoint, and `safety_broken`. Byte-stable.
- Figures under `results/adversary/plots/` — **PDF tracked, PNG gitignored**
  (Ch4 figure convention).

## 9. Testing

- `tests/output/test_adversary_analysis.py` — synthetic-case reducer tests
  (bracket edges, Wilson, censoring cases, the PBFT non-monotone flag) +
  **locked-number regression** against the three real CSVs + **byte-stability**
  of `degradation_ranking.csv`. Clone `test_delay_analysis.py`.
- `tests/output/test_adversary_degradation_plots.py` — tiny synthetic CSV →
  `render_all` → assert each `name.pdf`/`name.png` exists. Clone
  `test_adversary_plots.py`.

Both run under the existing `output` Make suite — no new target needed.

## 10. Wiki & provenance

- **New** `wiki/concepts/adversarial-degradation-metrics.md` — the durable
  metrics spec: liveness definition, the four invariant operationalizations, the
  f_max bracket estimator + interval + the hold/break-edge reconciliation, the
  AURC-departure rationale, the seed-invariance-of-safety note.
- `wiki/experiments/2026-06-19_adversarial-degradation.md` — run record:
  source CSVs + commits (T51 dirty flag), commands to re-derive, raw-result
  locations, one-paragraph observation, and the mandatory **Auggie verification**
  subsection (pickup-index + plan + post-edit queries).
- `wiki/index.md` (Concepts + Experiments) and `wiki/log.md` updates.
- Naming: concept name "safety-violation rate" throughout; the literal
  `fork_rate` column referenced only as a column name (the rename is a separate
  pending task). Directory `results/adversary/` (the task/T55 `results/adversarial/`
  spelling is a typo, flagged in the handoff).

## 11. Determinism & verification

- The analysis layer is a pure function of the input CSVs; `degradation_ranking.csv`
  is byte-stable (sorted, fixed formatting), gated by a test.
- Pre-edit auggie pickup-index already done; a plan-phase and a post-edit
  re-query are mandatory before In Review, logged in the experiment page's
  Auggie verification subsection.
- A verification subagent runs at each commit boundary (per-commit verification
  discipline), and `superpowers:verification-before-completion` runs before the
  In Review flip.

## 12. Deferrals & follow-ups (flagged, not done here)

- §3.5 `f_max` gloss sync ("smallest-that-breaks" → "largest-that-holds") — a
  one-line Writer edit (Backlog item (b)); flagged for a Writer pass.
- Snowman β ∈ {3,5} ε-observability sweep — deferred to a separate RQ4 regime.
- Narwhal+Tusk §5 invariant — deferred with T38.1.
- Standing Snowman n=4 exclusion note carries into any cross-protocol table
  (equivocate runs Snowman only at n∈{10,25}, so n=4 does not arise here).
