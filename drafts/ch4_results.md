# Chapter 4 — Results

## 4.1 Chapter roadmap

This chapter reports the evaluation and answers research questions RQ1–RQ4
against the metric schema of §3.5, organized by the three run families: §4.2 the
baseline scaling sweep (validator-set size the only variable, clean network),
§4.3 the network-delay sweep, and §4.4 the adversarial sweep, with the three
protocols PBFT, Casper FFG, and Snowman evaluated throughout (§3.6). The baseline
both establishes honest-path correctness and, with no delay or faults injected,
is the cleanest setting in which to confront the simulator's measured numbers
with each protocol's published asymptotic theory.

## 4.2 Baseline: scaling with validator-set size

The baseline dataset sweeps validator-set size `n ∈ {4, 7, 10, 16, 25}` at
twenty seeds per configuration under a common deterministic Poisson workload
(100 tx/s, 512-byte transactions, zero conflict rate), with common
random numbers so that seed `k` presents the same arrival stream to every
protocol [[wiki/experiments/2026-06-03_scaling-baseline]]. The 300 trials,
fifteen scenarios of twenty seeds, are aggregated to per-scenario means with
95% confidence intervals [[wiki/experiments/2026-06-08_baseline-cis]]. Snowman
is evaluated from `n = 7` upward: at `n = 4` its parameter rescaling collapses
to the degenerate unanimity boundary `α_c = K` and is excluded by the schema
[[wiki/concepts/output-format]].

### 4.2.1 Statistical reliability

The seed perturbs only goodput — every structural metric is degenerate once
`(protocol, n)` is fixed — so goodput carries the sole non-degenerate interval
(Figure 4.1a).

### 4.2.2 Latency

Commit latency is flat in the validator count for all three protocols: absent
network delay, latency is set by each protocol's round and timer structure, not
by the size of the validator set (Figure 4.1b). PBFT and Snowman commit the first
unit at approximately 1000 ms and Casper FFG at approximately 5000 ms, none
changing measurably as `n` grows from 4 to 25. Latency throughout is read from
`commit_latency_ms`, the canonical cross-protocol time-to-finality column (§3.5).
Casper FFG's absolute ≈5000 ms is slot-calibrated — a fixed multiple of the
chosen one-second slot, not a protocol property
[[wiki/concepts/metric-reconciliation#calibration-defaults]]; its
protocol-intrinsic result is finality at epoch granularity, coarser than
per-block or per-poll commit at any realistic slot. The flatness is a property of
the zero-delay model; the latency cost that grows with the validator set and
separates the protocols surfaces only under the delay sweep of §4.3.

### 4.2.3 Throughput and goodput

Throughput is reported as goodput (§3.5), the rate of committed transactions, and
is flat in `n`: approximately 95 tx/s for the per-block protocols PBFT and Snowman
and approximately 80 tx/s for Casper FFG, whose shortfall is a finality-tail
effect — its per-epoch finality leaves the window's last unfinalized epoch
uncommitted, a fixed end-of-window loss the per-block protocols avoid (Figure 4.1a).
Flat goodput is the expected result on a latency-only model with no per-transaction
cost and no queue, not a measured capacity ceiling
[[wiki/experiments/2026-06-03_scaling-baseline]].

**Figure 4.1 — Baseline scaling with validator-set size.** Per-protocol metrics
across `n ∈ {4, 7, 10, 16, 25}` at zero injected delay, twenty seeds per cell:
(a) goodput with 95% confidence intervals, the sole non-degenerate interval;
(b) median commit latency. Source:
`results/baseline/plots/baseline_panel.pdf`
[[wiki/experiments/2026-06-08_baseline-cis]]
[[wiki/experiments/2026-06-03_scaling-baseline]].

### 4.2.4 Communication overhead

Communication overhead is the metric on which the protocols separate most
sharply, and the one that answers RQ3 [[wiki/concepts/research-questions]].
Messages per committed unit grow with `n` for all three, but the slopes differ by
an order of magnitude (Figure 4.2, logarithmic axis): PBFT approaches `2n`, Casper
FFG `1.2n`, and Snowman `2·K·β`, where `K` is the poll sample size and `β` the
confidence threshold. Each trend matches the protocol's published asymptotic cost, the markers falling
on the prediction across the sweep, the largest departures confined to `n = 4`.
The slopes trace to each protocol's all-to-all structure: PBFT's PREPARE and
COMMIT phases [[wiki/sources/2026-04-21_castro-liskov-pbft-1999]], Casper FFG's
individually-signed attestation phase
[[wiki/sources/2026-04-21_buterin-griffith-casper-ffg-2017]], and Snowman's
`K`-peer query-and-response polls (the factor of two being the query–response
pair) [[wiki/sources/2026-04-21_team-rocket-avalanche-2019]], the last matched to
within half a percent. Casper FFG's per-unit slope sits below PBFT's because one
attestation phase serves more committed decisions than PBFT's two broadcast
phases; the production BLS aggregation that would cut both protocols' cost is not
in the original specification and is identified as future work (§6.3).

The overhead admits two readings that must be kept apart. Per committed unit,
Snowman is the most expensive protocol by an order of magnitude, roughly
twenty-four messages per validator against PBFT's two, the price of repeated
subsampling at thesis scale. Yet the property for which Avalanche is known is that
its *per-validator* cost is independent of `n`, a statement about per-validator
work, not about the network-aggregate `total_msgs_per_acu` plotted here, which
necessarily grows with `n` as each of `n` validators performs that constant work.
The independence is further masked over this range because the thesis rescales
`K = min(20, n−1)` (§3.3.3), so `K` tracks `n` until it saturates at the
production value of 20 near `n = 21`. The result is therefore reported as a
per-unit cost contrast, with the per-validator scalability stated separately so
the figure is not misread.

**Figure 4.2 — Communication overhead: measured against predicted asymptotic
cost.** `total_msgs_per_acu` for each protocol across the sweep, logarithmic
vertical axis; markers are measured values, dashed lines the per-protocol
predictions PBFT `2n`, Casper FFG `1.2n`, and Snowman `2·K·β` with
`K = min(20, n−1)`. Source: `results/baseline/plots/theory_vs_measured.pdf`,
generated by `src/output/explain.py`
[[wiki/experiments/2026-06-09_baseline-explainers]].

### 4.2.5 Reliability

Every scenario commits and none forks — success rate 1.0 and fork rate 0.0 at
every `n` for all three protocols — confirming honest-path correctness; these
metrics discriminate only under the adversarial sweep (§4.4).

### 4.2.6 Baseline summary

At the production-scale end of the sweep (`n = 25`) the overhead gap spans an
order of magnitude — ≈50 messages per committed unit for PBFT and ≈29 for Casper
FFG against ≈601 for Snowman — the performance–structure contrast RQ3 asks about
[[wiki/experiments/2026-06-08_baseline-cis]]. Two results carry forward: all three
protocols are correct on the honest path at every validator count, and at zero
delay latency and goodput are flat in `n`, so the protocols separate only along
the delay and adversarial axes of §4.3 and §4.4.

## 4.3 Network-delay sweep

The delay sweep holds the validator set and workload fixed and varies the
network timeline, isolating the latency and loss the baseline of §4.2 excluded.
It draws two regimes from run family B [[wiki/concepts/experiment-matrix]]. The
moderate regime applies two loss-free timelines of equal mean but different tail
shape: `delay-uniform` on [100, 500] ms and `delay-exponential` of the same
300 ms mean [[wiki/experiments/2026-06-10_delay-moderate]]. The heavy regime
applies a heavy-tailed Pareto delay of roughly three-second mean, first without
loss as a control and then under per-message drop probabilities of 5%, 10%, and
20% [[wiki/experiments/2026-06-12_delay-heavy]]. Each cell runs at `n ∈ {10, 25}`
over twenty seeds with common random numbers, except the most expensive,
Snowman at `n = 25` under heavy delay, over eight.

Delay and loss attack different properties and are reported apart: delay inflates
time-to-finality (RQ1, §4.3.1) and loss erodes liveness (RQ4, §4.3.2)
[[wiki/concepts/research-questions]].

### 4.3.1 Delay and time-to-finality

Under moderate delay the three protocols separate by nearly an order of
magnitude, governed by each protocol's round structure rather than the network
(Figure 4.3). PBFT and Casper FFG are round-bounded: both stay near-flat in `n`
and nearly tail-insensitive, differing by at most three percent between the
uniform and exponential timelines because a fixed count of rounds or slots
averages out the per-message delay. Casper FFG's modest ≈27% rise is
slot-mediated, not network-driven — the coherence rule of §3.3.2 rescales its
slot with the delay regime [[wiki/concepts/experiment-matrix]]. Snowman is the
exception, acutely tail-sensitive: it rises by a factor of twelve to fifteen over
baseline, and its exponential-timeline latency exceeds its uniform-timeline
latency (15.3 against 12.6 s at `n = 10`), because its `β = 15` sequential poll
rounds (§3.3.3) each wait on the slowest of `K` sampled peers and the memoryless
tail inflates that slowest response across the rounds
[[wiki/experiments/2026-06-10_delay-moderate]]. Message counts, by contrast, hold
within about two percent of their zero-delay values (§4.2.4).

These results answer RQ1: as the network-delay distribution widens from the
nominal baseline toward heavier tails, commit latency scales by a factor fixed by
each family's round structure rather than by the validator-set size — the
round-bounded protocols stay near-insensitive to the tail, while Snowman, whose
`β` sequential polls each wait on the slowest sampled peer, is acutely sensitive
to it [[wiki/experiments/2026-06-10_delay-moderate]].

**Figure 4.3 — Commit latency under moderate delay.** Median per-validator
`commit_latency_ms` under the two equal-mean moderate timelines
(`delay-uniform` and `delay-exponential`), grouped by protocol and faceted by
validator count; logarithmic vertical axis. Source:
`results/delay/plots/moderate_latency.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

### 4.3.2 Packet loss and the resilience ranking

Under packet loss the question shifts from how long finalization takes to
whether it happens at all, measured by the finalization rate: instances finalized
under loss as a fraction of those finalized on the matched loss-free control
[[wiki/experiments/2026-06-12_delay-heavy]]. Figure 4.4a shows three degradation
shapes: PBFT's shallow tail staying above zero to the deepest tested loss,
Snowman's high plateau then single-step cliff, and Casper FFG's collapse at the
first loss step. A fixed 95%-finalization breakpoint was rejected as a resilience
score, every protocol already falling below it at the lightest tested loss
[[wiki/experiments/2026-06-13_delay-comparison]].

The protocols are therefore ranked by the area under the finalization-rate curve
(AURC), with survival depth as the tiebreak, the two committee sizes reported
separately (Figure 4.4b). At `n = 10` the order is strict — PBFT, then Snowman,
then Casper FFG — but at `n = 25` PBFT and Snowman tie at the top, 0.351 and 0.369
with overlapping intervals, while Casper FFG remains last
[[wiki/experiments/2026-06-13_delay-comparison]]. Two findings stand out. PBFT is
the only protocol still finalizing at 20% loss at both committee sizes, whereas
neither other survives past 10%. And committee size is a sharp resilience lever
for Snowman: its 5%-loss finalization rate rises from 0.195 at `n = 10` to 0.904
at `n = 25`, making the larger committee the strongest of the three at light loss,
even as it still cliffs to near-zero by 10%. Throughout the loss sweep no protocol
forks: loss erodes liveness, not safety [[wiki/experiments/2026-06-12_delay-heavy]].

**Figure 4.4 — Packet-loss resilience.** Faceted by validator count, 95%
confidence intervals. (a) Finalization rate against per-message drop probability,
one curve per protocol. (b) Loss-resilience ranking by area under the
finalization-rate curve (AURC), labelled with each cell's survival depth `p*`. Source: `results/delay/plots/loss_resilience_panel.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

The ranking follows from what each protocol can do when messages are lost
(Figure 4.5, panels a and b). PBFT has a genuine recovery path: a per-instance
timer fires and rotates the leader through a view-change, reissuing the stalled
instance as a fresh round, so enough retries eventually succeed even under heavy
loss — visible in the view-change count, which climbs into the tens at `n = 10`
and toward the seventies at `n = 25` (Figure 4.5b)
[[wiki/experiments/2026-06-13_delay-analysis]]. Snowman has in-round redundancy
but no cross-round recovery: a poll round tolerates losses past its `α_c`
threshold yet has no timeout, so once the larger committee's margin is exhausted
the `β` rounds compound into a cliff rather than a slope. Casper FFG has neither,
collapsing at the first 5% drop with no leader to rotate and no resampling to fall
back on [[wiki/experiments/2026-06-12_delay-heavy]].

### 4.3.3 The latency–liveness tradeoff

The two stress axes converge on one result: the protocols that survive loss are
the ones that pay the most latency to do so (Figure 4.5c). PBFT and Snowman both
inflate their time-to-finality by factors of roughly two to three-and-a-half at
the worst loss they survive, converting that cost into survival: a long tail to
20% loss for PBFT, a high but brittle plateau for Snowman
[[wiki/experiments/2026-06-13_delay-analysis]]. Casper FFG does not make the trade:
it inflates latency by only about three to ten percent, but over the few seeds
that still finalize and to no benefit, since it no longer finalizes by 10% loss.
No configuration is both cheap and resilient; protecting liveness against a lossy
network is a choice of how much latency to spend, not whether to spend it.

The delay-family verdict follows. PBFT degrades most gracefully, alive at the
deepest tested loss at both committee sizes; Snowman is strong but brittle, best
in class at light loss with a large committee but prone to sudden collapse; Casper
FFG is fragile, never establishing a resilient plateau. The `n = 25` PBFT–Snowman
tie is a genuine crossover: the two win on different virtues, Snowman on area
under the curve (retaining 0.90 finality at 5% loss) and PBFT on survival depth
(alone alive at 20%) [[wiki/experiments/2026-06-13_delay-comparison]]. Casper FFG's
fragility is, in mechanism, the failure that motivated this study (§1.2):
attestations that fail to reach a quorum — dropped by a lossy network here, delayed
under attestation-processing pressure in Ethereum's multi-epoch finality stall of
May 2023 there — leave the epoch unjustified and finality stalled
[[wiki/algorithms/pos]].

One caveat governs the loss results: loss is modeled as permanent per-message
drop with no transport-layer retransmission, so the finalization-rate curves are
an upper bound on fragility [[wiki/experiments/2026-06-13_delay-analysis]]. The
ordering, PBFT most robust and Casper FFG most fragile, is a property of the
protocols' recovery mechanisms and would survive a retransmitting transport, but
the absolute collapse levels of 5% to 20% would shift higher beneath one. The
kinds of finality being timed differ (deterministic for PBFT and Casper FFG,
the latter additionally accountable; probabilistic for Snowman), a distinction
returned to in §4.4.3.

**Figure 4.5 — Mechanisms of degradation under packet loss.** Three rows faceted
by validator count. (a) Commit latency against drop probability (logarithmic), a
cross marking lost liveness. (b) Messages per committed unit against drop
probability (logarithmic), PBFT view-changes annotated. (c) Finalization rate
retained against added-latency ratio (logarithmic), non-finalizing cells pinned
on a no-finality band. Source:
`results/delay/plots/degradation_mechanism_panel.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

## 4.4 Adversarial sweep

The adversarial sweep holds the network at a constant baseline delay and replaces
a fraction of the honest validators with a single Byzantine strategy, isolating
adversarial behavior from the network effects of §4.3. It draws run family C from
the experiment matrix [[wiki/concepts/experiment-matrix]] and exercises the three
generic capabilities of the adversary catalog in turn: delayed voting, silent
non-participation, and equivocation (defined in §3.4.2). Each is swept from an
honest control through a band of injected adversarial fractions `φ` at `n ∈ {10,
25}`, twenty seeds per cell under common random numbers; `φ` is the swept variable,
distinct from the tolerated threshold `f`, denominated in each protocol's natural
unit (replicas for PBFT and Snowman, stake for Casper FFG, §3.4.2). The sweep is
extended past the one-third threshold where a safety failure is possible, namely
equivocation against PBFT and Casper FFG, and the paired committee sizes separate
size-invariant results from size-dependent ones such as Snowman's silence cliff
(§3.3.3).

The sweep reports the two outcome families RQ4 separates: liveness, the success
rate of seed-runs that finalize within the measurement window (§3.5), and safety,
a per-protocol safety-violation rate, except for Snowman, whose probabilistic
finality is reported through its analytical bound `ε` rather than a fork count
[[wiki/concepts/evaluation-metrics]].

The liveness intervals throughout are 95% Wilson bands on the success rate (§3.5).
The delayed-voting figure pools each point over all five delay magnitudes
(invariant to magnitude [[wiki/experiments/2026-06-14_delayed-voters]]).

### 4.4.1 Delayed voting

Under delayed voting the three protocols separate by failure mode, and the
split follows protocol structure rather than the size of the delayed set
(Figure 4.6, panels a and b). PBFT is immune: its delayed validators are
backups, the honest remainder already meets the `2f+1` quorum, and the view-0
primary commits without rotation, so the success rate holds at 1.0 with zero
view-changes [[wiki/experiments/2026-06-14_delayed-voters]]. Casper FFG loses
liveness instead, because its single rotating proposer is periodically the
delayed node and the block it owes stalls for that slot, dropping the success
rate to a worst pooled 0.60–0.65
[[wiki/experiments/2026-06-19_adversary-comparison]]. Snowman keeps liveness, but
its time-to-finality explodes by a factor of roughly 62 at `n = 10` and 49 at
`n = 25`, severe near `φ = 0.20`, because each of its `β` sequential poll rounds
waits on the slowest sampled peer
[[wiki/experiments/2026-06-19_adversary-comparison]]. None of the three forks:
delayed voting threatens liveness and latency, never agreement
[[wiki/experiments/2026-06-19_adversarial-degradation]].

### 4.4.2 Silent non-participation

When the adversarial validators go silent rather than slow, the result inverts
the delayed-voting verdict for Snowman: the protocol that best tolerated slow
peers is the least tolerant of silent ones, because a sampled supermajority can
wait out a slow peer but cannot complete a poll around an absent one (Figure
4.6c). PBFT shows a clean quorum cliff, finalizing with no throughput loss up to
`φ = 0.33` and dying at `φ = 0.40` where the silent set drops the honest
remainder below the `2f+1` quorum; Casper FFG degrades gracefully over the same
range and still finalizes at `φ = 0.33`, its throughput decaying in proportion to
the participating stake, approximately `1 − φ` (Figure 4.8); and Snowman cliffs
earliest and committee-size-dependent, surviving only to `φ = 0.10` at `n = 10`
and `φ = 0.20` at `n = 25` [[wiki/experiments/2026-06-17_offline-validators]].
The ordering is therefore PBFT and Casper FFG ahead of Snowman
[[wiki/experiments/2026-06-19_adversary-comparison]].

**Figure 4.6 — Liveness under delayed voting and silent non-participation.** Each
row faceted by validator count, against the injected adversarial fraction `φ`
with 95% Wilson intervals. (a) Delayed-voting success rate. (b) Delayed-voting
time-to-finality ratio against the honest control (logarithmic). (c)
Silent-participation success rate, each protocol's survival depth `φ*` boxed. Source:
`results/adversary/plots/liveness_delay_offline_panel.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

### 4.4.3 Equivocation

Equivocation is the only one of the three strategies that can break safety: all
three hold agreement to `φ = 0.33` and differ entirely above it, in the kind of
failure rather than its onset (Figure 4.7). PBFT fails with a deterministic,
unaccountable fork: at `φ = 0.40` two honest replicas commit conflicting values at
the same height and the safety-violation rate steps from zero to 229 conflicting
instances, identical at both committee sizes, a breach PBFT cannot attribute to
its cause [[wiki/experiments/2026-06-18_equivocating-nodes]]. Casper FFG never
forks but fails accountably, the failure surfacing as slashable stake that crosses
the one-third line at `φ = 0.40` (Figure A.1), so a safety violation costs at least
one-third of the stake, provably slashable
[[wiki/sources/2026-04-21_buterin-griffith-casper-ffg-2017]]. Snowman presents no
fork surface at all, since equivocation against a subsampling protocol reduces to a
lying responder (§3.4.2), so its safety is probabilistic, reported through the
analytical bound `ε ≤ (1 − α_c/K)^β`, approximately `5 × 10⁻¹⁵` at `n = 10` and a
looser `3 × 10⁻¹¹` at `n = 25` (§3.3.3), and the empirical zero on every cell
cannot witness a bound this small
[[wiki/experiments/2026-06-19_adversarial-degradation]].

The safety order is therefore Snowman, Casper FFG, PBFT, set by what failure occurs
above `φ = 0.33` rather than which fraction each tolerates. Two cautions: the three
failures sit on incommensurable scales (a conflicting-commit rate, a
slashable-stake fraction, an analytical bound), so the ranking compares kinds of
failure, not magnitudes; and Snowman's first place is in part structural, ranked
first for having no fork-inducing surface to expose (§3.4.2).

**Figure 4.7 — Liveness and safety under equivocation.** Each row faceted by
validator count, against the equivocator fraction `φ`. (a) Finalization success
rate, one curve per protocol. (b) Cross-protocol safety-violation rate, drawn as
steps.
Source: `results/adversary/plots/equivocation_panel.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

### 4.4.4 The performance–security tradeoff

The three strategies together answer RQ4. No protocol is robust to every
adversary: the structural choice that defends one strategy is the choice that
exposes another, so the protocol best on one axis is last on another in every case
(Table 4.1, mapped in Figure A.2): PBFT first against delay and silence but last
against equivocation, Snowman first against equivocation but last against silence,
Casper FFG never first but never catastrophic. The contribution is not that bare
statement but the mechanism-level map of which structural feature produces which
failure under which adversary: the subsampling that makes Snowman the most
delay-tolerant protocol when peers are slow makes it the least tolerant when they
fall silent, and PBFT's leader-based commit rule is at once the source of its
liveness robustness and of its unaccountable fork
[[wiki/concepts/adversary-model]]. Whether this is an artifact of the adversary
choice (the three are the generic capabilities of the catalog, defined
independently of any protocol) and the broader joint-regime synthesis are taken up
in Chapter 5.

**Table 4.1 — Adversarial outcomes by protocol and strategy (`n = 10 / 25`, 20
seeds).** Values pair the two committee sizes where they differ. Robustness order
is per strategy, ranked on the liveness held for the two liveness adversaries and
on the safety invariant for equivocation. Source:
[[wiki/experiments/2026-06-19_adversary-comparison]].

| Adversarial strategy | PBFT | Casper FFG | Snowman | Robustness order |
| :-- | :-- | :-- | :-- | :-- |
| Delayed voting | immune; finality 1.0×, no view-changes | liveness dips (success → 0.60 / 0.65) | survives; finality ×62 / ×49 | PBFT ≈ Snowman ≫ FFG |
| Silent non-participation | clean quorum cliff at `φ = 0.40`; no decay below it | graceful decay, survives to `φ = 0.33` (throughput ≈ `1 − φ`) | early cliff at `φ = 0.10 / 0.20`; starves | PBFT ≈ FFG > Snowman |
| Equivocation | deterministic unaccountable fork at `φ = 0.40` (229 conflicts) | accountable: ≥ ⅓ stake slashable at `φ = 0.40`, no fork | no fork surface; `ε ≈ 5 × 10⁻¹⁵ / 3 × 10⁻¹¹` | Snowman > FFG > PBFT |

Four qualifications, each fixed elsewhere, bound the verdict: the leader-disruption
surface is catalogued but not exercised, so PBFT's standing against the liveness
adversaries holds only against an adversary that spares its view-0 primary (§3.6);
safety results are seed-invariant, so those columns carry no seed variance while
the success-rate columns carry all of it; Snowman's analytical `ε` is not
empirically witnessed at the baseline depth (§4.4.3); and the latency-only network
understates the detection and recovery cost borne by PBFT and Casper FFG, without
bearing on the message-count, liveness, or safety verdicts drawn here (§3.6).

Read on the throughput axis rather than the liveness one, the same sweep answers
RQ2: as the injected Byzantine fraction `φ` rises toward the fault threshold,
sustained throughput degrades in three distinct modes (PBFT undegraded until its
quorum cliff, Casper FFG decaying in proportion to the participating stake,
≈ `1 − φ`, and Snowman starving earliest), so the rate of decay is governed by
each family's quorum structure rather than by `φ` alone (Figure 4.8)
[[wiki/experiments/2026-06-19_adversary-comparison]].

**Figure 4.8 — Throughput degradation versus adversarial fraction (silent
non-participation).** Committed-unit throughput against the injected silent
fraction `φ` for each protocol, faceted by validator count, with the `y = 1 − φ`
participating-stake invariant marked. Source:
`results/adversary/plots/throughput_degradation_vs_phi.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

Whether any one family occupies a dominant position once the baseline, delay, and
adversarial regimes are considered jointly, the Pareto-frontier synthesis of RQ5,
is taken up in Chapter 5 [[wiki/concepts/research-questions]].

<!-- Appendix figures: the two detail figures below are referenced from §4.4.3
and §4.4.4 but rendered in Appendix A to keep the chapter's figure budget on the
load-bearing results. On LaTeX export their figure environments live in
appendixa.tex; the body keeps only the cross-references (Figure A.1, Figure A.2). -->

**Figure A.1 — Casper FFG slashable stake under equivocation.** Maximum
slashable stake fraction against the equivocator fraction `φ`, faceted by
validator count, with the one-third accountability line marked. Source:
`results/adversary/plots/ffg_slashable_vs_phi.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

**Figure A.2 — Adversarial outcomes by protocol and strategy.** The nine
protocol–strategy cells of Table 4.1 as an outcome map: cell colour encodes the
outcome kind and each label its governing magnitude. Source:
`results/adversary/plots/adversary_tradeoff_matrix.pdf`
[[wiki/experiments/2026-06-19_adversary-comparison]].
