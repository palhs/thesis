# Chapter 4 — Results

## 4.1 Chapter roadmap

This chapter answers RQ1–RQ4 against the metric schema of §3.5, organized by the
three run families: §4.2 the baseline scaling sweep (validator-set size the only
variable, clean network), §4.3 the network-delay sweep, and §4.4 the adversarial
sweep. The baseline both establishes honest-path correctness and, with no delay or
faults injected, is the cleanest setting in which to confront the simulator's
measured numbers with each protocol's published asymptotic theory.

## 4.2 Baseline: scaling with validator-set size

The baseline sweeps validator-set size `n ∈ {4, 7, 10, 16, 25}` under a clean network and common Poisson workload (100 tx/s, 512-byte transactions), with twenty seeds per configuration [[wiki/experiments/2026-06-03_scaling-baseline]]. Snowman is excluded at `n = 4`, where its threshold collapses to a degenerate boundary.

On the honest path all three protocols are correct at every validator count — success rate 1.0, fork rate 0.0 — and both latency and goodput are flat in `n`: without network delay, timing is governed by each protocol's round structure, not validator-set size. PBFT and Snowman commit the first unit at ≈ 1000 ms; Casper FFG at ≈ 5000 ms, a consequence of its epoch-granularity finality (§3.3). Goodput is ≈ 95 tx/s for the per-block protocols and ≈ 80 tx/s for Casper FFG, whose shortfall is a fixed end-of-window epoch left uncommitted.

Communication overhead is where the protocols separate most sharply, answering **RQ3**. Messages per committed unit grow with `n` for all three, but the slopes differ by an order of magnitude: PBFT approaches `2n`, Casper FFG `1.2n`, and Snowman `2·K·β`. Each measured trend matches the protocol's published asymptotic cost (Table 3.3, §3.5). Two readings must be kept apart: per committed unit Snowman is the most expensive by an order of magnitude (≈ 24 messages per validator against PBFT's two), the price of repeated subsampling; yet Avalanche's claim — that its *per-validator* cost is independent of `n` — is a statement about per-validator work, not the network aggregate plotted here. At `n = 25` the overhead gap reaches an order of magnitude: ≈ 50 messages per unit for PBFT, ≈ 29 for Casper FFG, and ≈ 601 for Snowman.

**Figure 4.1 — Communication overhead: measured against predicted asymptotic cost.**
`total_msgs_per_acu` for each protocol across the sweep, logarithmic vertical axis;
markers are measured values, dashed lines the per-protocol predictions PBFT `2n`,
Casper FFG `1.2n`, and Snowman `2·K·β` with `K = min(20, n−1)`. Source:
`results/baseline/plots/theory_vs_measured.pdf`
[[wiki/experiments/2026-06-09_baseline-explainers]].

The latency cost of a larger `n` and reliability differences between protocols do not appear in this regime; both surface under the delay and adversarial sweeps that follow.

## 4.3 Network-delay sweep

The delay sweep holds the validator set and workload fixed and varies the network timeline, drawing two regimes from run family B. The moderate regime applies two loss-free timelines of equal mean but different tail shape: `delay-uniform` on [100, 500] ms and `delay-exponential` of
the same 300 ms mean. The heavy regime applies a heavy-tailed Pareto delay of roughly
three-second mean, first without loss as a control and then under per-message drop
probabilities of 5%, 10%, and 20%. Each cell runs at `n ∈ {10, 25}` over twenty seeds with common random numbers. Delay and loss attack different properties and are reported
apart: delay inflates time-to-finality (RQ1, §4.3.1), loss erodes liveness (RQ4,
§4.3.2).

### 4.3.1 Delay and time-to-finality

Under moderate delay the three protocols separate by nearly an order of magnitude, governed by each protocol's round structure rather than the network (Figure 4.2). PBFT and Casper FFG are round-bounded: both stay near-flat in `n` and insensitive to tail shape, differing by at most three percent between the uniform and exponential timelines because a fixed count of rounds averages out the per-message delay. Both slow against their zero-delay baselines — PBFT roughly doubles (×1.9 at `n = 10`, near ×2.0 at `n = 25`) and Casper FFG rises modestly (×1.3) [[wiki/experiments/2026-06-10_delay-moderate]]. Snowman is the exception: it rises by a factor of twelve to fifteen over baseline, and its exponential-timeline latency exceeds its uniform-timeline latency (15.3 against 12.6 s at `n = 10`), because its `β = 15` sequential poll rounds each wait on the slowest of `K` sampled peers and the exponential tail pushes that slowest response higher across every round. Message counts, by contrast, stay near their zero-delay values for the round-bounded protocols (PBFT within a tenth of a percent, Snowman within about two percent), while Casper FFG's messages per committed unit fall by roughly twelve percent under delay.

**Figure 4.2 — Commit latency under moderate delay.** Mean per-validator
`commit_latency_ms` under the two equal-mean moderate timelines (`delay-uniform` and
`delay-exponential`), grouped by protocol and faceted by validator count; logarithmic
vertical axis. Source: `results/delay/plots/moderate_latency.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

This answers **RQ1**: commit latency scales by a factor fixed by each family's round structure, not by validator-set size. The round-bounded protocols are insensitive to tail shape; Snowman, whose polls each wait on the slowest sampled peer, is sharply sensitive to it.

### 4.3.2 Packet loss and the resilience ranking

Under packet loss the question shifts from how long finalization takes to whether it happens at all, measured by the finalization rate against the matched loss-free control (Figure 4.3).

At `n = 10`, the three protocols separate clearly. PBFT's finalization rate declines gradually, staying above zero at 20% loss. Casper FFG collapses at the first loss step, dropping to near zero at 5%. Snowman falls between the two: it holds partially at 5% loss but cliffs to near zero by 10%. Ranked by AURC with survival depth as the tiebreak, the order is strict: PBFT, Snowman, Casper FFG.

At `n = 25` the picture changes for Snowman. Its finalization rate stays high through 5% loss — near the PBFT level — before cliffing to near zero at 10%, a clear plateau-then-cliff shape absent at `n = 10`. PBFT keeps its shallow tail to 20% loss; Casper FFG collapses as before. PBFT and Snowman tie at the top by AURC while Casper FFG remains last.

Across both committee sizes, PBFT is the only protocol still finalizing at 20% loss. No protocol forks throughout: loss erodes liveness, not safety.

Each position in the ranking reflects what the protocol can do when messages are lost. PBFT has a genuine recovery path: a per-instance timer fires and rotates the leader through a view-change, reissuing the stalled instance, so retries eventually succeed even under heavy loss (its view-change count climbs into the tens at `n = 10` and toward the seventies at `n = 25`). Snowman has in-round redundancy but no cross-round recovery: a poll round tolerates losses past its `α_c` threshold yet has no timeout, so once the committee's margin is exhausted the `β` rounds compound into a cliff. At `n = 10` that margin is small enough that 5% loss exhausts it; at `n = 25` the larger committee absorbs light loss before the cliff hits at 10%. Casper FFG has neither, collapsing at the first 5% drop with no leader to rotate and no resampling to fall back on.

PBFT's recovery is not free (Figure A.3): its per-unit message cost rises with loss at both committee sizes, more steeply at `n = 25` where view-change traffic is heavier. The other two protocols degrade faster still — their per-unit cost inflates even more sharply as finalized instances collapse with no recovery path — and Snowman's cost spike tracks where its cliff falls, arriving earlier at `n = 10` than at `n = 25`. At 20% loss only PBFT still commits, and it is the cheapest of the three at that depth. The clean-path cost ordering of §4.2 does not survive: PBFT overtakes Casper FFG while Snowman stays most expensive throughout.

**Figure 4.3 — Packet-loss resilience.** Faceted by validator count, 95% confidence
intervals. (a) Finalization rate against per-message drop probability, one curve per
protocol. (b) Loss-resilience ranking by area under the finalization-rate curve
(AURC), labelled with each cell's survival depth `p*`. Source:
`results/delay/plots/loss_resilience_panel.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

### 4.3.3 The latency–liveness tradeoff

The two stress axes converge on one result: the protocols that survive loss pay for it in latency. PBFT and Snowman both inflate their time-to-finality by factors of roughly two to three-and-a-half at the worst loss they survive; Casper FFG does not make the trade, inflating latency by only three to ten percent over the few seeds that still finalize, to no benefit. No configuration is both cheap and resilient: protecting liveness against a lossy network costs latency, and the only variable is how much.

PBFT degrades most gracefully, alive at the deepest tested loss at both committee sizes; Snowman is strong but brittle, best at light loss with a large committee but prone to sudden collapse; Casper FFG is fragile, never establishing a resilient plateau. The `n = 25` PBFT–Snowman result is a non-rejection: the two AURC values sit inside overlapping intervals.

## 4.4 Adversarial sweep

The adversarial sweep holds the network at a constant baseline delay and replaces a fraction `φ` of the honest validators with a single Byzantine strategy, isolating adversarial behavior from the network effects of §4.3. It draws run family C and exercises three generic capabilities — delayed voting, silent non-participation, and equivocation (defined in §3.4) — each swept from an honest control through a band of fractions `φ` at `n ∈ {10, 25}`, twenty seeds per cell; `φ` is denominated in each protocol's natural unit (replicas for PBFT and Snowman, stake for Casper FFG). The sweep extends past the one-third threshold where a safety failure is possible. It reports two outcome families: liveness (success rate, §3.5) and safety, a per-protocol safety-violation rate — except for Snowman, whose probabilistic finality is reported through its analytical bound `ε` rather than a fork count.

### 4.4.1 Delayed voting

Under delayed voting the three protocols separate by failure mode, driven by protocol structure rather than the size of the delayed set (Figure 4.4a,b). PBFT is immune: its delayed validators are backups, the honest remainder still meets the `2f+1` quorum, so the success rate holds at 1.0. Casper FFG loses liveness instead, because its single rotating proposer is periodically the delayed node and the block it owes stalls for that slot, dropping the success rate to a worst pooled 0.60–0.65. Snowman keeps liveness, but its time-to-finality explodes by a factor of roughly 62 at `n = 10` and 49 at `n = 25`, severe near `φ = 0.20`, because each of its `β` sequential poll rounds waits on the slowest sampled peer. None of the three forks: delayed voting threatens liveness and latency, never agreement.

### 4.4.2 Silent non-participation

When the adversarial validators go silent rather than slow, the result inverts the
delayed-voting verdict for Snowman: the protocol that best tolerated slow peers is the
least tolerant of silent ones, because a sampled supermajority can wait out a slow
peer but cannot complete a poll around an absent one (Figure 4.4c). PBFT shows a clean
quorum cliff, finalizing with no goodput loss up to `φ = 0.33` and dying at
`φ = 0.40` where the silent set drops the honest remainder below the `2f+1` quorum;
Casper FFG degrades gracefully over the same range and still finalizes at `φ = 0.33`,
its goodput decaying with the participating stake but somewhat faster than the `1 − φ`
line, which it stays below because lost proposer slots forfeit whole finalization
rounds (Figure 4.6); and Snowman cliffs earliest, at `φ = 0.10` for `n = 10` and `φ = 0.20` for `n = 25`. The ordering is therefore PBFT and
Casper FFG ahead of Snowman.

**Figure 4.4 — Liveness under delayed voting and silent non-participation.** Each row
faceted by validator count, against the injected adversarial fraction `φ` with 95%
Wilson intervals. (a) Delayed-voting success rate. (b) Delayed-voting time-to-finality
ratio against the honest control (logarithmic). (c) Silent-participation success rate,
each protocol's survival depth `φ*` boxed. Source:
`results/adversary/plots/liveness_delay_offline_panel.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

### 4.4.3 Equivocation

Equivocation is the only one of the three strategies that can break safety: all three hold agreement to `φ = 0.33` and differ entirely above it, in the *kind* of failure rather than its onset (Figure 4.5). PBFT fails with a deterministic, unaccountable fork: at `φ = 0.40` the safety-violation indicator steps from zero to one in every seed-run — 229 conflicting instances at both committee sizes — a breach PBFT cannot attribute to its cause. Casper FFG never forks but fails accountably, the failure surfacing as slashable stake that crosses the one-third line at `φ = 0.40` (Figure A.1), so a safety violation costs at least one-third of the stake, provably slashable [[wiki/sources/2026-04-21_buterin-griffith-casper-ffg-2017]]. Snowman presents no fork surface at all, since equivocation against a subsampling protocol reduces to a lying responder (§3.4), so its safety is reported through the analytical bound `ε ≤ (1 − α_c/K)^β`, ≈ `5 × 10⁻¹⁵` at `n = 10` and a looser `3 × 10⁻¹¹` at `n = 25`, which the empirical zero on every cell cannot witness.

**Figure 4.5 — Liveness and safety under equivocation.** Each row faceted by validator
count, against the equivocator fraction `φ`. (a) Finalization success rate, one curve
per protocol. (b) Cross-protocol safety-violation rate, drawn as steps. Source:
`results/adversary/plots/equivocation_panel.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

The safety order is therefore Snowman, Casper FFG, PBFT, set by what failure occurs
above `φ = 0.33` rather than which fraction each tolerates. Two cautions: the three
failures sit on incommensurable scales (a conflicting-commit rate, a slashable-stake
fraction, an analytical bound), so the ranking compares kinds of failure, not
magnitudes; and Snowman's first place is in part structural, ranked first for having
no fork-inducing surface to expose.

### 4.4.4 The performance–security tradeoff

The three strategies together answer **RQ4**. No protocol is robust to every adversary: the structural choice that defends one strategy is the choice that exposes another (Table 4.1, mapped in Figure A.2): PBFT first against delay and silence but last against equivocation, Snowman first against equivocation but last against silence, Casper FFG never first but never catastrophic. The mechanism map shows which structural feature produces which failure: the subsampling that keeps Snowman live under slow peers — finalizing, merely far slower — makes it the least tolerant when they fall silent, and PBFT's leader-based commit rule is at once the source of its liveness robustness and of its unaccountable fork. Whether this is an artifact of the adversary choice, and the broader joint-regime synthesis, are taken up in Chapter 5.

**Table 4.1 — Adversarial outcomes by protocol and strategy (`n = 10 / 25`, 20
seeds).** Values pair the two committee sizes where they differ. Robustness order is
per strategy, ranked on the liveness held for the two liveness adversaries and on the
safety invariant for equivocation. Source:
[[wiki/experiments/2026-06-19_adversary-comparison]].

| Adversarial strategy | PBFT | Casper FFG | Snowman | Robustness order |
| :-- | :-- | :-- | :-- | :-- |
| Delayed voting | success 1.0; finality 1.0× (immune, no view-changes) | success → 0.60 / 0.65; finality 1.0× (liveness dips) | success 1.0; finality ×62 / ×49 (full liveness, crawls) | PBFT ≈ Snowman ≫ FFG |
| Silent non-participation | clean quorum cliff at `φ = 0.40`; no decay below it | graceful decay, survives to `φ = 0.33` (goodput below `1 − φ`) | early cliff at `φ = 0.10 / 0.20`; starves | PBFT ≈ FFG > Snowman |
| Equivocation | deterministic unaccountable fork at `φ = 0.40` (229 conflicts) | accountable: ≥ ⅓ stake slashable at `φ = 0.40`, no fork | no fork surface; `ε ≈ 5 × 10⁻¹⁵ / 3 × 10⁻¹¹` | Snowman > FFG > PBFT |

Three qualifications bound the verdict: the leader-disruption surface is catalogued but not exercised, so PBFT's standing against the liveness adversaries holds only against an adversary that spares its view-0 primary (§6.2); Snowman's analytical `ε` is not empirically witnessed at the baseline depth (§4.4.3); and the latency-only network understates the detection and recovery cost borne by PBFT and Casper FFG (§6.2).

On the goodput axis, the same sweep answers
**RQ2**: as the injected Byzantine fraction `φ` rises toward the fault threshold,
sustained goodput degrades in three distinct modes (PBFT undegraded until its
quorum cliff, Casper FFG decaying with the participating stake but somewhat faster than `1 − φ`,
and Snowman starving earliest), so the rate of decay is governed by each family's
quorum structure rather than by `φ` alone (Figure 4.6).

Whether any one family occupies a dominant position once the baseline, delay, and
adversarial regimes are considered jointly (the Pareto-frontier synthesis of RQ5) is
taken up in Chapter 5.

**Figure 4.6 — Goodput degradation versus adversarial fraction (silent
non-participation).** Committed-unit goodput against the injected silent fraction
`φ` for each protocol, faceted by validator count, with the `y = 1 − φ`
participating-stake invariant marked. Source:
`results/adversary/plots/throughput_degradation_vs_phi.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

<!-- Appendix figures: the three detail figures below are referenced from §4.3.2,
§4.4.3, and §4.4.4 but rendered in Appendix A to keep the chapter's figure budget on
the load-bearing results. On LaTeX export their figure environments live in
appendixa.tex; the body keeps only the cross-references (Figure A.1, Figure A.2,
Figure A.3). -->

**Figure A.1 — Casper FFG slashable stake under equivocation.** Maximum slashable
stake fraction against the equivocator fraction `φ`, faceted by validator count, with
the one-third accountability line marked. Source:
`results/adversary/plots/ffg_slashable_vs_phi.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

**Figure A.2 — Adversarial outcomes by protocol and strategy.** The nine
protocol–strategy cells of Table 4.1 as an outcome map: cell colour encodes the
outcome kind and each label its governing magnitude. Source:
`results/adversary/plots/adversary_tradeoff_matrix.pdf`
[[wiki/experiments/2026-06-19_adversary-comparison]].

**Figure A.3 — Communication cost under packet loss.** `total_msgs_per_acu` for each
protocol against per-message drop probability, faceted by validator count, on a
logarithmic axis, with PBFT's mean view-change count annotated at each loss level.
Shows the two compounding inflation fronts of §4.3.2 (view-change numerator, collapsing
ACU denominator) and the clean-path cost order breaking under loss as Casper FFG
crosses above PBFT. Source: `results/delay/plots/cost_of_survival.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].
