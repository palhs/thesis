# Key findings

Synthesis of the empirical campaign (run families A — scaling, B — network
delay/loss, C — adversarial) into the ten load-bearing findings, each with
verified evidence and a research-question mapping. This page is the upstream
feeder for the RQ5 Pareto synthesis (Chapter 5), the Chapter 6 summary of
findings, the traceability matrix, and the abstract. It organises and ranks;
it does not hold thesis prose.

Scope: three of the four families — PBFT, Casper FFG, Snowman — are
implemented and measured. Narwhal+Tusk is deferred, so every cross-family
ranking below is over three of four. Research questions:
[[concepts/research-questions]]; metric definitions:
[[concepts/evaluation-metrics]] and [[concepts/metric-reconciliation]].

## Measurement conventions these findings rest on

Every finding is stated against the conventions fixed in
[[concepts/metric-reconciliation]]. Three are load-bearing:

- **Latency** is read from `commit_latency_ms`, the canonical cross-protocol
  time-to-finality column (PBFT 2f+1 COMMIT, Casper FFG the finalised
  checkpoint after justify→finalise, Snowman counter-β acceptance) — never
  `finality_latency_ms`, which after the fidelity pass denotes PBFT-only
  client-observed finality one hop past COMMIT.
- **Throughput** is `goodput` (committed application-tx rate), never `tps`.
  `tps` counts decided events per node and grows ≈ `0.95·n` (PBFT, Snowman)
  or `0.40·n` (Casper FFG) by construction, so it is not a like-for-like
  system rate [[experiments/2026-06-08_baseline-cis]].
- **Per-unit** metrics use the ACU (agreed-consensus-unit) denominator;
  Snowman is evaluated from `n = 7` upward (at `n = 4` the parameter
  rescaling degenerates to unanimity).

## Findings

### Family A — honest scaling baseline

**F1 (RQ3) — Communication overhead splits into two scaling regimes.**
PBFT (≈ `2n`) and Casper FFG (≈ `1.15n` measured, ≈ `1.125n` analytical) both
grow linearly in messages per ACU, because each protocol's `O(n²)` per-instance
all-to-all cost is divided by `n` decisions per instance; Snowman sits an order of magnitude above both
at ≈ `2·K·β`. Measured total messages per ACU run PBFT 7.5 → 49.9 (per-n ratio
1.875 → 1.997) and Casper FFG 5.2 → 29.3 over `n = 4 → 25`, against Snowman
180.9 → 601.0 over `n = 7 → 25`
[[experiments/2026-06-03_scaling-baseline]], [[experiments/2026-06-08_baseline-cis]]. At `n = 16`
Snowman's 450.9 ≈ `2·15·15` is ≈ 14.1× PBFT's per-ACU cost
[[experiments/2026-06-09_baseline-explainers]]. The apparent Snowman growth
is `K`-rescaling (`K = min(20, n−1)`) masking the published per-validator
`O(K·β)` `n`-independence, which only emerges once `K` caps above `n ≈ 21`
[[experiments/2026-06-08_baseline-cis]].
*Caveat:* zero-delay honest baseline; Casper FFG uses individually-signed
attestations (the paper protocol), not BLS aggregation, so the ≈ `1.15n`
slope is un-aggregated all-to-all, not an aggregated `O(n)` deployment. A
least-squares fit of the CSV gives `1.145n + 0.7`; the per-`n` ratio runs
1.29 → 1.17 over `n = 4 → 25` as the fixed additive term dilutes.

**F2 (RQ1, RQ3) — Latency and throughput are flat in `n`, and the baseline
is deterministic except goodput.** Commit latency holds at ≈ 1000 ms (PBFT,
Snowman) and ≈ 5000 ms (Casper FFG) across all `n`, and goodput holds at
≈ 94.8 tx/s (PBFT, Snowman) and ≈ 79.6 tx/s (Casper FFG)
[[experiments/2026-06-03_scaling-baseline]]. Casper FFG's ≈ 20%-below-offered
goodput is the finality-tail (per-epoch finality leaves the window's last
unfinalised epoch uncommitted), not a communication penalty. Every
structural metric carries CV = 0 across 20 seeds; only goodput shows real
seed-to-seed variance (CV ≈ 2.2%, 95% CI half-width ≈ 1.0% of mean)
[[experiments/2026-06-08_baseline-cis]].
*Caveat:* flat latency is a zero-delay artifact (round/timer-bounded, not
network-bounded), and flat goodput reflects a latency-only model below
saturation — `peak_tps` needs a capacity model and is deferred.

### Family B — network delay and loss

**F3 (RQ1) — Snowman is by far the most delay-exposed protocol, and the only
one sensitive to delay-distribution shape.** Under moderate delay
(uniform[100,500] ms, E[delay] = 300 ms) Snowman degrades from its 1000 ms
baseline to 12,200–12,600 ms (≈ 12–13×), versus PBFT 1,895–2,006 ms (≈ +0.9 s)
and Casper FFG 6,282–6,359 ms (≈ +27%), because its `β = 15` sequential poll
rounds each pay a slowest-of-`K` round-trip that compounds additively. Holding
the mean fixed and switching uniform → exponential inflates Snowman a further
+9.9% (`n = 25`) to +21.5% (`n = 10`), while PBFT and Casper FFG move ≤ 3%
[[experiments/2026-06-10_delay-moderate]]. Casper FFG's increase is
slot-clock-dominated — the coherence rule rescales the slot 1.0 → 1.2 s, so
5-slot finality becomes ≈ 6.0 s and only ≈ 0.3 s is attestation propagation.
*Caveat:* all control rows finalize (finalization_rate = 1.0), so this is a
pure latency axis with no liveness confound.

**F4 (RQ4) — Loss-resilience ranking is PBFT ≥ Snowman > Casper FFG, with a
verified `n = 25` virtue-crossover tie.** PBFT is the only protocol retaining
any finalization at 20% per-message loss (fr = 0.104 at `n = 10`, 0.056 at
`n = 25`); Casper FFG is the most fragile, already at fr ≈ 0.05–0.07 by 5%
loss [[experiments/2026-06-12_delay-heavy]]. At `n = 25` PBFT and Snowman are
a statistical tie at rank #1 — AURC CIs overlap (Snowman 0.369 [0.366, 0.372]
vs PBFT 0.351 [0.327, 0.376]) — concealing a genuine crossover: Snowman wins
area-under-curve (fr = 0.904 at 5% loss vs PBFT 0.533) while PBFT wins
survival-depth (sole survivor at 20%) [[experiments/2026-06-13_delay-comparison]].
Committee size is a sharp Snowman lever: raising `n` 10 → 25 lifts fr@5% from
0.195 to 0.904 as per-round loss-slack `K − α_c` grows 1 → 4
[[experiments/2026-06-13_delay-analysis]].
*Caveat:* loss is permanent per-message Bernoulli drop with no transport
retransmission, so the curves upper-bound fragility; Snowman `n = 25` rests
on 8 seeds (the cost wall).

**F5 (RQ4 → RQ5) — Loss resilience is bought with latency; no
cheap-and-resilient configuration exists. [Inversion]** The protocols that
survive loss are exactly the ones that pay the most latency to do so. At the
worst loss level they survive, PBFT and Snowman pay 2.16–3.57× added latency,
while Casper FFG pays only ≈ 1.03–1.10× and is the first to die
[[experiments/2026-06-13_delay-analysis]]. PBFT's view-change count tracks
loss exactly (0 → 30 at `n = 10`, 0 → 75 at `n = 25` over p = 0 → 0.20),
confirming leader rotation as the active liveness-recovery mechanism — and
the cost of that recovery is the latency inflation
[[experiments/2026-06-12_delay-heavy]]. The cheap-and-resilient corner of the
operator frontier is empty.
*Caveat:* Snowman's added-latency ratios are survivorship-biased (computed
over surviving seeds at that loss level).

### Family C — adversarial

**F6 (RQ2) — Sustained throughput degrades in three distinct modes as the
Byzantine/offline fraction φ rises.** PBFT holds throughput undegraded up to
its 1/3 quorum cliff (`f* = 0.40`); Casper FFG decays gracefully ≈ `(1−φ)`
with participating stake (finalization success 1.00 → 0.85 → 0.75 → 0.60 at
`n = 10`, 1.00 → 0.90 → 0.75 → 0.60 at `n = 25`, for f = 0 → 0.33, then
collapse at 0.40); Snowman starves earliest, cliffing at an `α_c`-driven
boundary *below* 1/3 (`f* = 0.20` at `n = 10`, `0.33` at `n = 25`)
[[experiments/2026-06-17_offline-validators]]. Snowman's sub-1/3 cliff
contradicts the catalogued proportional-degradation expectation
[[experiments/2026-06-19_adversary-comparison]]. This closes RQ2 on the
sustained-throughput-versus-φ axis.
*Caveat:* the throughput signal is the `throughput_ratio` /
finalization-success proxy, not a saturation `tps`; Snowman required an
opt-in 15 s query timeout to produce a measurable cliff rather than an
infinite stall.

**F7 (RQ4) — One structural fork-handling choice yields three distinct
outcomes at φ = 0.40.** Under equivocation, PBFT produces a deterministic
*unaccountable* fork — `safety_violation` flips 0 → 1 between φ = 0.33 and
0.40, with `conflicting_instances = 229` at both `n = 10` and `n = 25`, and
view-change recovery holding safety below the threshold. Casper FFG holds
*accountable* safety — every Byzantine attester is slashable, the slashable
stake fraction reaches ≥ 1/3 at φ = 0.40 (peaking 0.50 at `n = 10`, 0.48 at
`n = 25`), and no in-model fork forms. Snowman presents *no fork surface* —
empirical `safety_violation = 0` across the grid, bounded analytically by
ε ≈ 4.9×10⁻¹⁵ (`n = 10`) / 3.3×10⁻¹¹ (`n = 25`)
[[experiments/2026-06-18_equivocating-nodes]], [[experiments/2026-06-19_adversarial-degradation]].
*Caveat:* PBFT's fork is only observable under the node-parity partition
split; Snowman safety is the probabilistic ε-bound (an empirical zero is a
non-witness, not a confirmation), and the strategy is not swept above
φ = 0.33 for Snowman.

**F8 (RQ4) — Snowman is the most delay-tolerant protocol when peers are slow
and the least tolerant when they fall silent. [Inversion]** The same `K`-peer
subsampling drives both extremes. When adversarial validators merely delay,
Snowman survives — finality only becomes expensive, up to ≈ 62× the control at
`n = 10` and ≈ 49× at `n = 25` under the strongest delay (m = 10)
[[experiments/2026-06-14_delayed-voters]]. When the
same fraction falls silent, polls can never collect `α_c` responses, so
Snowman cliffs earliest of the three protocols
[[experiments/2026-06-17_offline-validators]],
[[experiments/2026-06-19_adversary-comparison]].
*Caveat:* the delayed and silent sets spare the view-0 primary, so these are
adversaries that do not target a bootstrap proposer.

**F9 (RQ4) — PBFT's leader-based commit is at once the source of its liveness
robustness and of its unaccountable fork. [Inversion]** The view-change
mechanism that rotates past slow or silent leaders to recover liveness is the
same mechanism whose absence above threshold yields the fork of F7. The metric
itself is context-sensitive: `view_change_count` is 10 (`n = 10`) / 25
(`n = 25`) as *successful* safety-preserving recovery under equivocation at
φ ≤ 0.33, but 50 (`n = 10`) / 125 (`n = 25`) as *failed* thrashing under the
insoluble offline quorum failure at φ = 0.40
[[experiments/2026-06-18_equivocating-nodes]],
[[experiments/2026-06-17_offline-validators]].

### Synthesis seed (RQ5)

**F10 (RQ4 → RQ5) — No family dominates; the contribution is the mechanism
map. [Inversion]** Across the three adversarial strategies the rankings
invert: PBFT is first under delayed voting and silence but last under
equivocation; Snowman is first under equivocation but last under silence;
Casper FFG is never first but never catastrophic (accountable rather than
unaccountable). The protocol best on one axis is last on another in every
case [[experiments/2026-06-19_adversary-comparison]],
[[experiments/2026-06-19_adversarial-degradation]]. The value is therefore
the map of which structural choice causes which failure, not a bare
no-dominance verdict. The cross-regime Pareto-frontier synthesis over
baseline, delay, and adversarial conditions is deferred to Chapter 5 (RQ5);
this page foreshadows it but does not close it.
*Caveat:* the survey covers three of four families (Narwhal+Tusk deferred),
and the leader-disruption adversary is catalogued but not exercised.

## RQ → finding map

For the Week-12 traceability matrix. RQ1–RQ4 are answered by the data below;
RQ5 is foreshadowed here and owed by Chapter 5.

| RQ | Question (independent variable) | Findings | Status |
| :-- | :-- | :-- | :-- |
| RQ1 | Commit-latency scaling as delay variance rises (network timeline, Family B) | F2 (flat at baseline), F3 (delay scaling) | answered |
| RQ2 | Sustained throughput degradation vs Byzantine fraction φ (Family C) | F6 | answered |
| RQ3 | Relative communication overhead per ACU (validator-set size `n`, Family A) | F1, F2 | answered |
| RQ4 | Which adversary → liveness loss / safety violation / neither (Family C) | F4, F5, F7, F8, F9 | answered |
| RQ5 | Consistent Pareto frontier; does any family dominate (synthesis) | F5, F10 | foreshadowed — deferred to Chapter 5 |

## Revisions

**2026-07-02 — Casper FFG overhead slope corrected from ≈ `1.2n` to ≈ `1.15n`
(measured).** F1 previously reported the Casper FFG per-ACU message slope as
≈ `1.2n`. A least-squares fit of `results/baseline/aggregated.csv`
(`total_msgs_per_acu_mean`) gives `1.145n + 0.7` (residual < 0.14 at every `n`),
i.e. a measured slope of ≈ `1.15n`, within two percent of the ≈ `1.125n`
un-aggregated analytical prediction. The earlier `1.2n` was an over-round of the
small-`n` per-validator ratio (1.29 at `n = 4`, falling to 1.17 at `n = 25` as
the fixed additive term dilutes), which overstated the analytical gap. Drafts
(Ch4/Ch5/Ch6), the `theory_vs_measured` figure theory line, and
[[concepts/metric-reconciliation]] were aligned the same day.

Cross-protocol context (measured − analytical, `results/baseline/aggregated.csv`):
PBFT is exact (0.00% at every `n`, its `(2n²−2)/n` law is closed-form); Snowman
runs +0.16%–0.48% above `2Kβ`, a near-constant additive of ≈ +0.9 messages per
unit; Casper FFG's residual is the same absolute size (+0.66 → +1.16 messages,
`n = 4 → 25`) but sits on a base of only 5–29 messages, so the identical finite-run
overhead (block proposals + boundary epochs) shows as +4% (n=25) to +14.6% (n=4).
Casper FFG's larger *percentage* gap is thus a small-base artifact of its being the
cheapest protocol, not a break from the all-to-all message law.
