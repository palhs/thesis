# Adversarial degradation metrics

The measurement spec for T54: how the Family-C adversarial experiments
(T51 delay / T52 offline / T53 equivocate) are turned into comparable
**liveness** and per-protocol **safety** numbers. The run record is
[[experiments/2026-06-19_adversarial-degradation]]; the binding column contract
is [[concepts/output-format]]; the invariant catalog is
[[concepts/adversary-model]]. Scope: PBFT, Casper FFG, Snowman —
Narwhal+Tusk is unimplemented (see §Narwhal+Tusk).

## Inputs

Three committed per-trial CSVs under `results/adversary/`, loaded **by column
name** (their tails diverge in membership and order, so positional reads
misalign):

| family | file | adversary | per-family headline |
|---|---|---|---|
| delay | `delayed_voters.csv` | delay-emission (T51) | `finality_delay_ratio` |
| offline | `offline_validators.csv` | withhold-participation (T52) | `throughput_ratio` |
| equivocate | `equivocating_nodes.csv` | equivocate-vote (T53) | safety triple |

`φ` is the `byzantine_fraction` column — the injected adversarial fraction
(the §3.4.2 `φ` symbol, distinct from the `n = 3f+1` tolerated threshold `f`).
All three families sweep `n ∈ {10, 25}` at 20 seeds; the equivocate φ-grid is
`{0, .10, .20, .33, .40, .50}` (Snowman stops at `.33`, where its equivocation
is liveness-only).

## Liveness — % of seed-runs reaching consensus

Per `(family, protocol, n, φ)` cell:
`liveness = mean(success_rate)` over the cell's runs (`success_rate` is the
per-run 0/1 finalization flag), reported with a **Wilson** score interval —
honest at the 0/1 boundary, so a 0-of-20 cell bounds the true rate below
`≈ 0.16` and a 0-of-30 cell below `≈ 0.11`. This is the operational dual of
the Termination property and matches the Chapter-3 §3.5 definition (a liveness
failure is the complement of `success_rate`; rate metrics get Wilson). The
delay family pools over the magnitude axis `delay_mult` at each φ — the
liveness pattern is `m`-invariant, so pooling is representative and tightens
the band.

**PBFT non-monotone caveat (load-bearing).** Under equivocation PBFT's
`success_rate` is `1.0` at φ=0, `0.0` at φ∈{0.10, 0.20} (view-change recovery
pushes finalization past the measurement window — a window artifact at
`PBFT_VC_DELAY = 3 s`, not a true liveness loss), then `1.0` again at φ≥0.40
where the **fork** decides — consensus "reached" but *unsafely*. Liveness is
therefore always reported jointly with safety: the equivocate-PBFT liveness
rows carry `safety_broken = True`, and the headline liveness `f_max` reports
only the first dip (bracket `[0.0, 0.10]`); the high-φ recovery is an unsafe
fork, not resilience.

## Safety — four per-protocol invariants

A universal fork counter is insufficient: PBFT and Narwhal+Tusk cannot fork
below the 1/3 threshold, so a fork counter reads zero and measures nothing
([[concepts/adversary-model#5-equivocate-vote]]). Each protocol gets the
invariant its design actually exposes. The signals are already in the T53
data (`src/adversary/safety.py`); T54 reduces and brackets them.

### PBFT — view-change rate + fork cliff (§5)
Equivocation converts to leader rotation, so the operational invariant is
"view-change frequency tracks the equivocator rate"
([[concepts/adversary-model#5-equivocate-vote]]). Measured as
`view_change_count / run_horizon_s`. Within φ≤0.33 the rate is positive
(10 view-changes at n=10, 25 at n=25; safety holds); at φ≥0.40 it collapses to
0 as the deterministic **fork cliff** opens (`safety_violation = 1`,
`conflicting_instances = 229` at both n). Theoretical threshold `f < n/3`.

### Casper FFG — slashable stake fraction (§7.3)
FFG never forks in-model (`EpochState.links` aggregates by source epoch and
ignores `target_hash`), so the faithful safety signal is accountable safety:
does `max_slashable_stake_fraction` reach `≥ 1/3`?
([[concepts/adversary-model#73-casper-ffg-slashable-equivocation-refinements]]).
It equals the realized `⌊φ·n⌋ / n` and first crosses 1/3 at φ=0.40 (0.30 at
n=10 / 0.32 at n=25 at φ=0.33, just below). Framed as "economically-possible
violation crosses the slashing threshold," **not** "fork observed."

### Snowman — empirical ε vs analytical bound (§7.1)
Equivocation reduces to a lying responder with no fork-induction surface, so
the empirical safety-violation rate is **0 on every cell**. Reported as a
witness table against the analytical bound `ε ≤ (1 − α_c/K)^β`
([[concepts/adversary-model#71-snowman-colluding-sub-sampler]],
[[algorithms/avalanche#probabilistic-safety]]):

| n | K | α_c | β | empirical ε | Wilson UB | analytical bound |
|---|---|---|---|---|---|---|
| 10 | 9 | 8 | 15 | 0 / 80 | ≈ 0.046 | ≈ 4.9·10⁻¹⁵ |
| 25 | 20 | 16 | 15 | 0 / 80 | ≈ 0.046 | ≈ 3.3·10⁻¹¹ |

The invariant holds trivially at the production `β = 15`. Making ε *observable*
(non-zero) needs the low-`β ∈ {3, 5}` regime, deferred to a separate RQ4 sweep
([[concepts/metric-reconciliation]]). The witness lives in
`results/adversary/snowman_epsilon_witness.csv`.

### Narwhal+Tusk — deferred (§5)
The invariant ("no conflicting header reaches `2f+1` signatures") is **defined
but not measured**: Narwhal+Tusk is unimplemented (T38.1, sequenced post-T55).
The ranking table carries an explicit deferral row, not a silent NaN
([[concepts/output-format]] §4 absent-vs-NaN distinction). T54 delivers 3 of 4
invariants empirically.

**Seed-invariance.** The equivocate safety signals are deterministic (a parity
partition with no adversary RNG), so every cell has exactly one safety value
across its 20 seeds. Confidence intervals therefore apply to **liveness only**;
safety is reported as exact per-cell values (no zero-width-CI theatre).

## f_max — the interval-censored fault threshold

`f_max` is the fault fraction at which an invariant first fails. The φ-grid is
coarse, so `f_max` is interval-censored and is reported as the **bracket**
`[largest φ that holds, first φ that breaks]`. The headline point is the
**hold edge** (largest-φ-that-holds), matching the binding
[[concepts/evaluation-metrics]] definition; the break edge is the upper
censoring bound. This unifies the T52 `f*` (the break edge) and `f_max` (the
hold edge) as the two ends of one bracket, reconciling §3.5's
"smallest-that-breaks" wording with evaluation-metrics' "largest-that-holds"
wording (a one-line Writer sync of §3.5 is flagged as follow-up).

Column routing ([[concepts/output-format]] §6 mutual exclusion):
`f_max_count` for PBFT / Snowman / Narwhal+Tusk, `f_max_stake` for Casper FFG;
the other column is `NaN`.

Measured safety brackets: **PBFT** `[0.33, 0.40]`; **Casper FFG** `[0.33, 0.40]`
(stake); **Snowman** `≥ 0.33` (right-censored — no break in the grid).

**Departure from the T48 ranking.** T48 ranked delay/loss resilience by AURC
(area under a smooth retention curve). The equivocate axis is a discrete safety
**cliff** (a step function), so an area integral is the wrong scalar — the
robustness key here is the f_max bracket (a survival-depth analogue: the
deepest φ at which the invariant is still intact).

## Outputs

- `src/output/adversary_analysis.py` — reducers + the f_max bracket estimator
  (pure-stdlib; reuses the `mean_ci` / Wilson primitives in
  `src/output/analysis.py` + `src/output/delay_analysis.py`).
- `src/output/adversary_degradation_plots.py` — the figures.
- `results/adversary/degradation_ranking.csv` — one row per
  `(family/invariant, protocol, n)`: the f_max bracket, count/stake routing,
  theoretical bound, and `safety_broken`. **Consumed by T55** (join
  `safety_broken` from the safety row, not the liveness row).
- `results/adversary/snowman_epsilon_witness.csv` — the ε witness (2 rows).
- `results/adversary/plots/*.{pdf,png}` — liveness-vs-φ per family, the PBFT
  view-change rate, the FFG slashable-stake curve (with the 1/3 line), and the
  cross-protocol safety cliff.

See [[experiments/2026-06-19_adversarial-degradation]] for the run record,
config, seeds, and commands.
