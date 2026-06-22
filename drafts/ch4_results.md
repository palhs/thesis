# Chapter 4 — Results

## 4.1 Chapter roadmap

Chapter 3 fixed the simulator, the metric schema, and the experiment matrix but
left their purpose untested: what each protocol does once the conditions those
metrics are built to stress — network delay and Byzantine validators — are
applied. This chapter reports that evaluation, prescribed by the experiment
matrix [[wiki/concepts/experiment-matrix]], and answers research
questions RQ1–RQ4 against the metric schema fixed in §3.5. It proceeds in
three movements that mirror the three run families. Section 4.2 reports the
baseline scaling sweep, in which validator-set size is the only independent
variable and the network carries no injected delay or adversary. Section 4.3
reports the network-delay sweep, in which the network timeline is varied while
the validator set and workload are held fixed, and Section 4.4 reports the
adversarial sweep, in which a fraction of the honest validators is replaced by
each of the adversarial strategies of the fault model. Three protocols are
evaluated throughout — PBFT, Casper FFG, and Snowman — with the Narwhal+Tusk
column reserved until that implementation lands, consistent with the chapter
scope set in §3.6.

The baseline serves two purposes. It establishes that each implemented
protocol is correct on the honest path at every validator count, and it
isolates the cost that scales with the validator set from the cost that the
later sweeps will attribute to delay and to adversarial behavior. Because the
baseline injects no delay and no faults, it is also the cleanest setting in
which to confront the simulator's measured numbers with each protocol's
published asymptotic theory.

## 4.2 Baseline: scaling with validator-set size

The baseline dataset sweeps validator-set size `n ∈ {4, 7, 10, 16, 25}` at
twenty seeds per configuration, driven by a common deterministic Poisson
transaction workload (`offered_rate = 100` tx/s, `tx_bytes = 512`,
`conflict_rate = 0`), with common random numbers across protocols so that
seed `k` presents the same arrival stream to every protocol
[[wiki/experiments/2026-06-03_scaling-baseline]]. The result is 300 trials —
fifteen scenarios of twenty seeds — aggregated to per-scenario means with
95% confidence intervals [[wiki/experiments/2026-06-08_baseline-cis]].
Snowman is evaluated from `n = 7` upward: at `n = 4` its parameter rescaling
collapses to the degenerate unanimity boundary `α_c = K` and is excluded from
the comparison by the schema [[wiki/concepts/output-format]]. Confidence
intervals use a Student-t critical value at nineteen degrees of freedom
rather than the Gaussian value named in §3.5; for a twenty-sample mean the
distinction is small, and for the deterministic metrics discussed in §4.2.1
the interval is degenerate regardless of which critical value is used.

### 4.2.1 Statistical reliability

The dominant statistical fact of the baseline is that the seed has almost no
effect. Across the twenty seeds of every scenario, commit latency, decision
rate, message overhead, success rate, and fork rate each show a coefficient
of variation of zero: their 95% confidence intervals are degenerate, of zero
width. This is not an artifact of too few seeds but a property of the model.
At the zero-delay honest baseline a protocol's round structure and message
counts are fixed once `(protocol, n)` is fixed; the only seeded randomness is
the workload arrival process, and it perturbs only goodput, the rate of
committed transaction bytes. Goodput accordingly carries the sole
non-degenerate interval, with a coefficient of variation near 2.2% and a
confidence half-width near 1% of its mean (Figure 4.5). Twenty seeds are
therefore more than adequate: no larger seed set would narrow a deterministic
metric's interval, and the one stochastic metric is already estimated to
within a percent. The confidence-interval exercise thus does double duty — it
confirms determinism for the structural metrics and bounds workload noise for
goodput.

### 4.2.2 Latency

Commit latency is flat in the validator count for all three protocols
(Figure 4.1). PBFT and Snowman commit the first unit at approximately
1000 ms, and Casper FFG at approximately 5000 ms; none of the three changes
measurably as `n` grows from 4 to 25. The explanation is that, absent network
delay, latency is set by each protocol's round and timer structure rather
than by the size of the validator set. PBFT's figure reflects one proposal
interval ahead of its three-phase commit; Snowman's reflects one slot driving
its repeated-poll counter; and Casper FFG's reflects the justify-then-finalize
rule, whose finality spans roughly two epochs at the configured one-second
slot and two-slot epoch [[wiki/algorithms/pos#communication-complexity]]. This
last figure must be read with one qualification that the round-bounded PBFT and
Snowman figures do not require. Casper FFG's finality interval is
`(2·slots_per_epoch + attest_offset)·slot_duration`, which at the configured
two-slot epoch equals five slot durations; the absolute ≈5000 ms is therefore
set by the chosen one-second slot rather than fixed by the protocol, and the
cross-protocol comparison of *absolute* latency is conditional on that
calibration choice [[wiki/concepts/metric-reconciliation#calibration-defaults]].
What the comparison establishes intrinsically is the *qualitative* ordering, and
that ordering is robust to the slot. A slot-duration sensitivity sweep confirms
that Casper FFG finality is exactly linear in the slot — 2500, 5000, and
10000 ms at slots of 0.5, 1, and 2 s — and so remains above the per-block
protocols' ≈1000 ms commit across the realistic range, crossing it only at a
sub-realistic slot of 0.2 s or below, far shorter than any deployed cadence
[[wiki/experiments/2026-06-22_ffg-slot-sensitivity]]. The protocol-intrinsic
result is thus that Casper FFG finalizes at epoch granularity, roughly two
epochs of slot timers, which is coarser than per-block or per-poll commit at any
realistic slot — not the specific fivefold gap, which moves with the
calibration. The
flatness is consistent with the theory that these protocols' latency is
round-bounded, but it must be read as a property of the zero-delay model: the
latency cost that grows with the validator set, and that separates the
protocols, surfaces only under the delay sweep of §4.3.

### 4.2.3 Throughput and goodput

The schema carries two throughput columns, and the baseline shows why the
distinction matters. The decision rate `tps` grows linearly in `n` for every
protocol — its per-validator value is constant at 0.95 for PBFT and Snowman
and 0.40 for Casper FFG (Figure 4.4) — because `tps` counts decision events,
of which each committed unit produces one per validator. It is therefore a
decision-event rate that scales with the validator set by construction, not a
measure of system transaction throughput. The honest throughput measure is
goodput, the rate of committed transaction bytes, which is flat in `n`:
approximately 95 tx/s for the per-block protocols PBFT and Snowman and
approximately 80 tx/s for Casper FFG (Figure 4.2). The Casper FFG shortfall is
a finality-tail effect: its per-epoch finality leaves the measurement window's
last unfinalized epoch uncommitted, a fixed end-of-window loss that the
per-block protocols do not incur. The flat goodput is the expected result on a
latency-only model with no per-transaction cost and no queue: offered load
below the protocol's cadence is always absorbed
[[wiki/experiments/2026-06-03_scaling-baseline]]. It must not be read as a
measured capacity ceiling; saturation throughput requires a capacity model and
is deferred [[wiki/concepts/output-format]].

### 4.2.4 Communication overhead

Communication overhead is the metric on which the protocols separate most
sharply, and it answers RQ3 [[wiki/concepts/research-questions]]. Messages per
committed unit grow with `n` for all three protocols, but the slopes differ by
an order of magnitude (Figure 4.3, logarithmic axis). PBFT's overhead
approaches `2n` messages per committed unit — `O(n²)` per-instance traffic
normalized by the `n`-scaled atomic-commit-unit denominator, not a linear
protocol cost [[wiki/concepts/metric-reconciliation]]; Casper FFG's approaches
`1.2n`; and Snowman's tracks `2·K·β`, where `K` is the poll sample size and `β`
the confidence threshold. Each measured trend matches the protocol's published
asymptotic cost: Figure 4.7 overlays the measured `total_msgs_per_acu` of each
protocol on its predicted slope, and the markers fall on the prediction across
the sweep, with the largest departures — near six to seven percent — confined to
`n = 4`. PBFT's normal-case cost is `O(n²)` messages per block
[[wiki/algorithms/pbft#communication-complexity]]; the per-unit metric reads
`O(n)` because the atomic-commit-unit denominator counts one decision per
validator per instance, absorbing exactly one factor of `n` from the
all-to-all prepare and commit phases. Casper FFG's attestation phase is also
all-to-all, and therefore `O(n²)` per epoch under the individually-signed-vote
model that the original protocol specifies and that the simulator implements
[[wiki/algorithms/pos#communication-complexity]]; its per-unit slope sits below
PBFT's not because of aggregation but because a single attestation phase serves
more committed decisions per round than PBFT's two broadcast phases. The
production BLS aggregation that would reduce this cost to `O(n)` is not part of
the original Casper FFG specification and is not modelled here; introducing it,
together with the corresponding threshold-signature variant of PBFT, is
identified as future work in §6.3. Snowman's measured overhead matches `2·K·β` to within half a
percent across the sweep — the factor of two is the query-and-response pair of
each poll — confirming the per-validator `O(K·β)` cost that the Avalanche
family is built around [[wiki/algorithms/avalanche#parameters-and-communication-complexity]].

Two readings of this result must be kept apart. Per committed unit, Snowman is
the most expensive protocol by an order of magnitude — roughly twenty-six
messages per validator against PBFT's two — which is the price of repeated
subsampling at thesis scale. Yet the property for which Avalanche is celebrated
is that its per-validator cost is independent of `n`, and that is a statement
about per-validator work, not about the network-aggregate `total_msgs_per_acu`
plotted here. The aggregate necessarily grows with `n` because each of `n`
validators performs the constant-per-validator work. The independence is
further masked over this range because the thesis rescales `K = min(20, n−1)`
to keep the protocol meaningful at small `n`, so `K` still tracks `n` until it
saturates at the production value of 20 near `n = 21`. The comparison is
therefore reported as a per-unit cost contrast, with the per-validator
scalability stated separately so the figure is not misread.

**Figure 4.7 — Measured message overhead against predicted asymptotic cost.**
Markers are the simulator's measured `total_msgs_per_acu`; dashed lines are the
per-protocol predictions — PBFT `2n`, Casper FFG `1.2n`, and Snowman `2·K·β`
with `K = min(20, n−1)`. Vertical axis logarithmic. The overlay is the visual
form of the theory-match claim made in this section; the residual gaps at
`n = 4` are the finite-`n` corrections discussed in
[[wiki/experiments/2026-06-08_baseline-cis]]. Source:
`results/baseline/plots/theory_vs_measured.pdf`, generated by
`src/output/explain.py` [[wiki/experiments/2026-06-09_baseline-explainers]].

### 4.2.5 Reliability

Every scenario commits successfully and none forks: success rate is 1.0 and
fork rate is 0.0 at every validator count for all three protocols
(Figure 4.6). This confirms honest-path correctness — each protocol terminates
and preserves agreement when no validator deviates — but carries no
comparative information, since the three protocols are indistinguishable on
both columns. The reliability metrics become discriminating only once the
adversarial sweep drives validators past their fault thresholds, where the
per-protocol safety invariants of §3.5 diverge; that analysis is §4.4.

### 4.2.6 A note on the latency measurement point

The cross-protocol latency comparison of §4.2.2 — and of the delay sweep in
§4.3 — is built from `commit_latency_ms`, and not from `finality_latency_ms`.
Despite its name, `commit_latency_ms` is the canonical cross-protocol
*time-to-finality* column: the median per-validator time to each protocol's
irreversibility milestone, its point of no return — the `2f+1` commit quorum
for PBFT, the finalized checkpoint after the justify-then-finalize rule for
Casper FFG, and counter-`β` acceptance for Snowman. Aligning these three
irreversibility milestones on one axis is what makes the comparison meaningful
[[wiki/concepts/output-format]]. The two columns
coincide for Casper FFG and Snowman but diverge for PBFT, whose
implementation adds a client-reply round so that its `finality_latency_ms` is
measured one network hop past the internal commit quorum, at client-observed
finality. Placing all three protocols' `finality_latency_ms` on one axis would
compare PBFT's client-observed timestamp against the others' internal
timestamps, which is not a like-for-like comparison. The comparable-column
choice is fixed in the schema page that governs figure construction rather
than left to this prose, so the correctness of the comparison does not depend
on the reader noticing this paragraph [[wiki/concepts/output-format]].

### 4.2.7 Baseline summary

**Table 4.1 — Baseline means at `n = 25` (production-scale end of the sweep),
20 seeds.** Latency and overhead are deterministic across seeds; goodput
carries a 95% confidence interval. Source:
[[wiki/experiments/2026-06-08_baseline-cis]].

| Protocol | `commit_latency_ms` | goodput (tx/s) | `total_msgs_per_acu` | success | fork |
| :-- | --: | --: | --: | --: | --: |
| PBFT | 1000.0 | 94.82 ± 1.01 | 49.9 | 1.0 | 0.0 |
| Casper FFG | 5000.0 | 79.64 ± 0.82 | 29.3 | 1.0 | 0.0 |
| Snowman | 1000.0 | 94.82 ± 1.01 | 601.0 | 1.0 | 0.0 |

The baseline establishes three results that the later sweeps build on. First,
all three protocols are correct on the honest path at every validator count.
Second, at zero delay both latency and goodput are flat in `n`, so neither
metric separates the protocols here; the separation will come from the delay
and adversarial axes. Third, communication overhead already separates the
protocols by an order of magnitude in a direction that matches their published
asymptotic costs, establishing the performance–structure contrast that RQ3
asks about and that the delay sweep of §4.3 will stress further.

## 4.3 Network-delay sweep

The delay sweep holds the validator set and the workload fixed and varies the
network timeline, isolating the latency and message loss that the baseline of
§4.2 deliberately excluded. It draws two regimes from run family B of the
experiment matrix [[wiki/concepts/experiment-matrix]]. The moderate regime
applies two loss-free timelines of equal mean delay but different tail shape —
`delay-uniform`, uniform on [100, 500] ms, and `delay-exponential`,
exponential with the same 300 ms mean
[[wiki/experiments/2026-06-10_delay-moderate]]. The heavy regime applies a
heavy-tailed Pareto delay of roughly three-second mean, first without loss as a
control and then under per-message drop probabilities of 5%, 10%, and 20%
[[wiki/experiments/2026-06-12_delay-heavy]]. Each cell is run at validator
counts `n ∈ {10, 25}` over twenty seeds with common random numbers across
protocols, except the most expensive cell — Snowman at `n = 25` under heavy
delay — which is run over eight. As in §4.2, the evaluation covers three of the
four families; Narwhal+Tusk awaits its implementation.

Two properties of the measurement must be stated before the results. First, all
cross-protocol latency figures are read from `commit_latency_ms`, the canonical
time-to-finality column established in §4.2.6, so that each protocol's
irreversibility milestone is compared like for like
[[wiki/concepts/output-format]]. Second, delay and loss attack different
properties and are reported apart: delay inflates time-to-finality and bears on
RQ1, whereas loss erodes liveness and bears on RQ4
[[wiki/concepts/research-questions]]. The section follows that division —
latency first, then the loss-resilience ranking, then the mechanisms behind it,
and finally the tradeoff that ties the two axes together.

### 4.3.1 Delay and time-to-finality

Under moderate delay the three protocols separate by more than an order of
magnitude, and the separation is governed by each protocol's round structure
rather than by the network (Figure 4.8). PBFT rises from its zero-delay
baseline of approximately 1000 ms [[wiki/experiments/2026-06-03_scaling-baseline]]
to approximately 1.95 s, an increase of about 0.9 s that corresponds to one
network round-trip absorbed into each of its three communication phases; the
figure is near-flat in `n` because those phases overlap across the validator
set [[wiki/experiments/2026-06-10_delay-moderate]]. Casper FFG rises from
approximately 5.0 s to approximately 6.3 s, an increase of about 27%. This rise
is slot-dominated rather than network-dominated: the experiment matrix couples
the finality-gadget slot to the delay regime through the coherence rule
`slot ≥ 4·E[delay]`, rescaling the slot from one second to 1.2 s; the same 20%
scales the slot-bound finality interval, lengthening FFG's roughly five-second
finality to about six seconds and leaving only some 0.3 s to attestation
propagation [[wiki/concepts/experiment-matrix]]. Casper FFG's sensitivity to delay is
therefore indirect, mediated by its slot clock.

Snowman is by far the most delay-exposed protocol, rising from approximately
1000 ms to between 12 and 15 s, a factor of twelve to fifteen
[[wiki/experiments/2026-06-10_delay-moderate]]. Its confidence counter requires
`β = 15` successful poll rounds in sequence, and each round is a
query-and-response exchange that costs about two network delays, so the fifteen
rounds accumulate roughly twelve seconds [[wiki/algorithms/avalanche]]. Like
the other two protocols its latency is near-flat — indeed slightly lower — in
`n`, because the poll sample size `K` rescales with the committee rather than
the first block's finality time growing with it
[[wiki/concepts/metric-reconciliation]].

The two moderate timelines share a mean but differ in tail shape, and this
distinguishes the protocols a second way. PBFT and Casper FFG are nearly
insensitive to the tail, differing by at most three percent between the uniform
and exponential timelines, because a fixed count of rounds or slots averages
the per-message delay and washes out its distribution
[[wiki/experiments/2026-06-10_delay-moderate]]. Snowman is the exception: its
exponential-timeline latency exceeds its uniform-timeline latency at both
committee sizes — approximately 15.3 against 12.6 s at `n = 10` — because each
poll round waits on the slowest of its `K` sampled peers, and the memoryless
tail inflates that slowest response and compounds the penalty across the
fifteen sequential rounds. Communication overhead, by contrast, does not move
with delay at all: PBFT's messages per committed unit land on the same `2n`
value measured at zero delay and Snowman's within about two percent, confirming
that message count is fixed by protocol structure and not by network timing,
consistent with the overhead analysis of §4.2.4
[[wiki/experiments/2026-06-10_delay-moderate]].

These results answer RQ1: as the network-delay distribution widens from the
nominal baseline toward heavier tails, commit latency scales by a factor fixed by
each family's round structure rather than by the validator-set size — the
round-bounded protocols stay near-insensitive to the tail, while Snowman, whose
`β` sequential polls each wait on the slowest sampled peer, is acutely sensitive
to it [[wiki/experiments/2026-06-10_delay-moderate]].

**Figure 4.8 — Commit latency under moderate delay.** Median per-validator
`commit_latency_ms` under the two equal-mean moderate timelines
(`delay-uniform` and `delay-exponential`), grouped by protocol and faceted by
validator count; logarithmic vertical axis. Source:
`results/delay/plots/moderate_latency.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

### 4.3.2 Packet loss and the resilience ranking

Under packet loss the question shifts from how long finalization takes to
whether it happens at all. The measure is the finalization rate: the number of
instances a protocol finalizes under loss as a fraction of the number it
finalizes on the matched loss-free control
[[wiki/experiments/2026-06-12_delay-heavy]]. Figure 4.9 plots this rate against
the drop probability for each protocol and committee size, and three distinct
degradation shapes are visible: PBFT declines along a shallow tail that stays
above zero to the deepest tested loss, Snowman holds a high plateau and then
falls to near-zero within a single loss step, and Casper FFG collapses at the
first loss step. A fixed 95%-finalization breakpoint was considered as a resilience
score and rejected, because every protocol is already below that threshold at
the lightest tested loss, so the threshold collapses the field to an
uninformative tie [[wiki/experiments/2026-06-13_delay-comparison]].

The protocols are therefore ranked by the area under the finalization-rate
curve (AURC), with survival depth — the deepest loss at which a protocol still
finalizes anything — as the tiebreak, and the two committee sizes reported
separately [[wiki/experiments/2026-06-13_delay-comparison]]. Figure 4.10 shows
the ranking directly. At `n = 10` the order is strict: PBFT leads with an AURC
of 0.253 and survives to 20% loss, Snowman follows at 0.174, and Casper FFG
trails at 0.149. At `n = 25` PBFT and Snowman are a statistical tie at the top:
Snowman's higher point estimate of 0.369 and PBFT's of 0.351 carry confidence
intervals that overlap — [0.366, 0.372] against [0.327, 0.376] — so neither can
be ranked above the other, while Casper FFG remains last at 0.140. Unlike the
baseline of §4.2.1, where every structural metric was deterministic across
seeds and its interval degenerate, the finalization rate genuinely varies with
the seed, because which messages are dropped depends on it; the intervals in
Figures 4.9 and 4.10 are accordingly non-degenerate and carry information. The
finalization-rate intervals are Wilson-score intervals, the form the schema fixes
for rate metrics, with Student-t reserved for continuous metrics (§3.5). The
interval for Snowman at `n = 25` is the widest, as that cell is estimated from
eight seeds rather than twenty [[wiki/experiments/2026-06-12_delay-heavy]].

Two findings stand out from the ranking. The first is that PBFT is the only
protocol still finalizing at 20% loss, at both committee sizes — 10% of its
control rate at `n = 10` and 6% at `n = 25` — whereas neither other protocol
survives past 10% loss, each having fallen to zero by the 20% step
[[wiki/experiments/2026-06-13_delay-comparison]]. The
second is that committee size is a sharp resilience lever for Snowman: its
finalization rate at 5% loss rises from 0.195 at `n = 10` to 0.904 at
`n = 25`, so that at light loss the larger committee makes Snowman the
strongest of the three, even as it still cliffs to near-zero by 10%
[[wiki/experiments/2026-06-12_delay-heavy]]. The same enlargement is a mild
liability for Casper FFG, whose rate at 5% loss falls slightly, from 0.070 to
0.051. Throughout the loss sweep no protocol ever forks: the fork rate is zero
on every row, so what loss degrades is liveness — the ability to finalize — and
not safety [[wiki/experiments/2026-06-12_delay-heavy]].

**Figure 4.9 — Finalization rate under packet loss.** Finalization rate against
per-message drop probability, one curve per protocol, faceted by validator
count, with 95% confidence intervals. Source:
`results/delay/plots/finalization_degradation.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

**Figure 4.10 — Loss-resilience ranking.** Area under the finalization-rate
curve (AURC) with 95% confidence intervals, annotated with each cell's survival
depth `p*`, faceted by validator count; protocols whose intervals overlap share
a rank. Source: `results/delay/plots/resilience_ranking.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

### 4.3.3 Mechanisms of degradation

The ranking is explained by what each protocol can do when messages are lost
(Figures 4.11 and 4.12) [[wiki/experiments/2026-06-13_delay-analysis]]. PBFT is
the most robust because it has a genuine recovery path. When dropped prepare or
commit messages stall an instance below its quorum, a per-instance timer fires,
the replicas rotate the leader through a view-change, and the instance is
reissued under the new leader [[wiki/algorithms/pbft]]. This is a retry rather
than a retransmission — a fresh round with fresh messages, and so a fresh
opportunity to assemble the quorum — and enough retries eventually succeed even
under heavy loss. The recovery work is visible in the view-change count, which
climbs with the loss level from zero to sixteen and then thirty at `n = 10`,
and from zero through twenty-eight and sixty-three to seventy-five at `n = 25`
(Figure 4.12) [[wiki/experiments/2026-06-13_delay-analysis]].

Snowman's robustness is of a different kind: redundancy within a single poll
round rather than recovery across rounds. A round closes once `α_c` agreeing
responses arrive, so it tolerates the loss of peers beyond that threshold, but
there is no poll timeout and no retransmission, and a round that never collects
`α_c` responses simply stalls [[wiki/experiments/2026-06-13_delay-analysis]].
Because a response survives only if both its query and its reply survive, the
expected number of usable responses per round is `K·(1−p)²`, and the round
closes only while this exceeds `α_c`. The slack `K − α_c` is one at `n = 10`
but four at `n = 25`, which is why the larger committee tolerates so much more
loss [[wiki/concepts/metric-reconciliation]]. Once the per-round margin is
exhausted, however, the `β = 15` rounds compound: the probability of completing
all fifteen falls away sharply, turning the degradation into a cliff rather
than a slope. This compounding argument predicts the location of the cliff and
the committee-size ordering but not the exact rate, and is used qualitatively
[[wiki/experiments/2026-06-13_delay-analysis]].

Casper FFG is the most fragile because it has neither recovery nor in-round
redundancy. Finalization requires a supermajority of at least two-thirds of
stake to attest the same checkpoint, and then two such justifications in
consecutive epochs; attestations are broadcast once per epoch, so when enough
are lost the epoch never justifies, and there is no leader to rotate and no
resampling to fall back on [[wiki/experiments/2026-06-13_delay-analysis]]. A 5%
drop already collapses it, and a larger committee is a slight liability because
it adds attestation links that can be lost without adding redundancy
[[wiki/experiments/2026-06-12_delay-heavy]]. Under heavy delay a node may
justify an epoch before its checkpoint block arrives locally; a guard added
during the heavy-delay experiments converts what would have been a crash into
an honest stall, in which the node skips the attestation and retries at a later
slot [[wiki/algorithms/pos]].

**Figure 4.11 — Commit-latency growth under loss.** `commit_latency_ms` against
drop probability on a logarithmic axis; a solid line marks the levels at which
a protocol still finalizes and a cross marks the level at which liveness is
lost. Source: `results/delay/plots/latency_cliff.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

**Figure 4.12 — Communication cost of survival.** Messages per committed unit
against drop probability on a logarithmic axis, with PBFT's view-change counts
annotated. Source: `results/delay/plots/cost_of_survival.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

### 4.3.4 The latency–liveness tradeoff

The two stress axes meet in a single conclusion: the protocols that survive
loss are the ones that pay the most latency to do so (Figure 4.13). PBFT and
Snowman both inflate their time-to-finality by factors of roughly two to
three-and-a-half at the worst loss they survive, and they convert that cost
into survival — PBFT into a long tail to 20% loss, Snowman into a high but
brittle plateau [[wiki/experiments/2026-06-13_delay-analysis]]. Casper FFG
does not make this trade: it inflates latency by only about three to ten
percent, but that near-constant cost is measured over the few seeds that still
finalize at all, and it buys almost nothing, since the protocol no longer
finalizes by 10% loss. No configuration in the dataset is both cheap and resilient; the
operator-facing reading is that protecting liveness against a lossy network is a
choice of how much latency to spend, not whether to spend it.

The verdict for the delay family follows. PBFT degrades most gracefully,
declining smoothly and remaining alive at the deepest tested loss at both
committee sizes; Snowman is strong but brittle, best in class at light loss when
the committee is large but prone to sudden collapse; and Casper FFG is fragile,
never establishing a resilient plateau. The `n = 25` tie between PBFT and
Snowman is a genuine crossover rather than measurement noise: the two protocols
win on different virtues — Snowman on the area under the curve, having retained
0.90 finality at 5% loss, and PBFT on survival depth, being alone alive at 20% —
so neither ranks first outright [[wiki/experiments/2026-06-13_delay-comparison]].
Casper FFG's fragility is, in mechanism, the same class of failure that motivated
this study (§1.2): attestations that fail to reach a quorum — dropped by a lossy
network here, delayed under attestation-processing pressure in Ethereum's
multi-epoch finality stall of May 2023 there — leave the epoch unjustified and
finality stalled [[wiki/algorithms/pos]].
The cross-regime question of whether any one family dominates across baseline,
delay, and adversarial conditions is deferred to the synthesis of Chapter 5
(RQ5) [[wiki/concepts/research-questions]].

Two caveats qualify these results. The first concerns the nature of the
finality being timed. The aligned milestones of §4.2.6 differ in kind: PBFT and
Casper FFG offer deterministic finality, and Casper FFG's is additionally
accountable, in that reverting a finalized checkpoint requires at least
one-third of the stake to be slashed [[wiki/algorithms/pos]]; Snowman's finality
is probabilistic, with a residual reversion probability bounded by
`(1 − α_c/K)^β` — approximately `5 × 10⁻¹⁵` at `n = 10` and a looser
`3 × 10⁻¹¹` at `n = 25`, the bound loosening at the larger committee because the
rounding in `α_c = ⌈0.8K⌉` raises the ratio above 0.8 only at small `K`
[[wiki/concepts/metric-reconciliation]]. The empirical and analytical `ε`
columns that would record this residual per run are deferred to a separate
sweep at a deliberately weakened confidence depth, as §4.4.3 details
[[wiki/concepts/output-format]]. The second caveat is the
more important for interpreting the loss results: loss is modeled as permanent
per-message drop with no transport-layer retransmission, so the
finalization-rate curves are an upper bound on fragility
[[wiki/experiments/2026-06-13_delay-analysis]]. The ordering — PBFT most
robust, Casper FFG most fragile — is a property of the protocols' recovery
mechanisms and would survive a retransmitting transport, but the absolute
collapse levels of 5% to 20% would shift higher beneath one.

**Figure 4.13 — The operator tradeoff.** Finalization rate retained against the
added-latency ratio (loss latency divided by control latency, logarithmic),
faceted by validator count; cells that no longer finalize are pinned on a "no
finality" band, and the operator-best region is the upper left. Source:
`results/delay/plots/operator_pareto.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

## 4.4 Adversarial sweep

The adversarial sweep holds the network at a constant baseline delay and
replaces a fraction of the honest validators with a single adversarial
strategy, isolating the effect of Byzantine behavior from the network effects
of §4.3. It draws run family C from the experiment matrix
[[wiki/concepts/experiment-matrix]]. Three strategies are exercised — the three
generic capabilities of the adversary catalog [[wiki/concepts/adversary-model]]:
delay-emission, in which a validator holds its messages (the delayed-voting
case); withhold-participation, in which a validator stays silent (the
silent-non-participation, or crash-faulty, case); and equivocate-vote, in which
a validator signs two conflicting messages where the protocol expects one (the
equivocation case). Each strategy is swept from an honest control through a band
of injected adversarial fractions at validator counts `n ∈ {10, 25}`, twenty
seeds per cell with common random numbers, and is extended past the one-third
threshold for the protocols and strategy that admit a safety failure —
equivocation against PBFT and Casper FFG [[wiki/concepts/experiment-matrix]].
The two committee sizes are a deliberate pair rather than a convenience sample —
`n = 10` is `3f+1` at `f = 3` and `n = 25` at `f = 8` — so that a result holding
at both is size-invariant, while one that moves between them, such as Snowman's
silence cliff, marks a committee-size dependence the section can name
[[wiki/concepts/experiment-matrix]]. As
in §4.2 and §4.3, the survey covers three of the four families; the Narwhal+Tusk
family awaits its implementation, and with it the data-availability-withholding
adversary that is its catalogued weakness is absent from this survey
[[wiki/concepts/adversary-model]].

Two distinctions must be fixed before the results. First, `φ` denotes the
adversarial fraction injected in this sweep — the swept independent variable —
and is kept distinct from `f`, the fault threshold a configuration tolerates
under `n = 3f+1`. The fraction `φ` is denominated in each protocol's natural
fault unit: replicas for PBFT and Snowman, stake for Casper FFG, so a given `φ`
is a replica share for the first two protocols and a stake share for the third
[[wiki/concepts/adversary-model-runtime]]. Second, the sweep reports two outcome
families that RQ4 separates: liveness, measured as the consensus success rate —
the fraction of seed-runs that finalize within the measurement window — and
safety, measured by a per-protocol invariant and reported as the
safety-violation rate, except for Snowman, whose probabilistic finality is
reported through its analytical bound `ε` rather than a fork count
[[wiki/concepts/evaluation-metrics]]. The section takes the three strategies in
turn — delayed voting, then silent non-participation, then equivocation — and
closes by drawing the cross-adversary tradeoff that answers RQ4.

### 4.4.1 Delayed voting

Under delayed voting the three protocols separate by failure mode, and the
split follows protocol structure rather than the size of the delayed set
(Figure 4.14). PBFT is immune. Its delayed validators are backups, the honest
remainder already meets the `2f+1` prepare and commit quorums, and the primary
commits without rotation, so time-to-finality stays at its baseline — a ratio of
1.0 against the honest control — and the success rate holds at 1.0 to the
deepest injected fraction tested, `φ = 0.30`, with zero view-changes across the
sweep [[wiki/experiments/2026-06-14_delayed-voters]]. This immunity is the
honest-leader case: the delayed set is chosen to spare the view-0 primary, so a
leader-targeting adversary is a separate surface, catalogued but outside the
swept strategies [[wiki/concepts/adversary-model]]. Casper FFG keeps its
finality latency unchanged when it finalizes, because finality is gated on a
stake supermajority that the honest validators still form, but its liveness
degrades: the per-slot proposer rotates, a delayed validator is periodically the
proposer, and the block it should propose stalls for that slot, so a fraction of
runs fail to finalize within the window — the success rate falls to a worst
pooled value of 0.60 at `n = 10` and 0.65 at `n = 25`
[[wiki/experiments/2026-06-19_adversary-comparison]]. Snowman is the costliest
case. It neither forks nor stalls, so the success rate holds, but its
time-to-finality explodes by a factor of roughly 62 at `n = 10` and 49 at
`n = 25` against the honest control, because each of its `β` sequential poll
rounds waits on the slowest sampled peer and a delayed peer inflates every round
into which it is sampled; the blow-up becomes severe near `φ = 0.20`
[[wiki/experiments/2026-06-19_adversary-comparison]].

The three outcomes are the performance–security tradeoff in miniature. The two
protocols that finalize without liveness loss do so for opposite reasons and at
opposite costs: PBFT because its fixed quorum tolerates slow backups for free,
Snowman because its sampled supermajority also tolerates them but only by
waiting, paying an order-of-magnitude latency penalty for the same survival.
Casper FFG pays no latency penalty but loses liveness instead, because its single
rotating proposer has no redundancy when the proposer is the slow node. Ranked
by the liveness held against the adversary, PBFT and Snowman are tied and ahead
of Casper FFG, with PBFT first on the finality-cost tiebreak
[[wiki/experiments/2026-06-19_adversary-comparison]]. None of the three suffers a
safety violation: delayed voting threatens liveness and latency, never agreement
[[wiki/experiments/2026-06-19_adversarial-degradation]].

**Figure 4.14 — Liveness under delayed voting.** Finalization success rate
against the injected adversarial fraction `φ`, one curve per protocol, faceted by
validator count. Source: `results/adversary/plots/liveness_vs_phi_delay.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

### 4.4.2 Silent non-participation

When the adversarial validators go silent rather than slow, the question becomes
how deep a fraction each protocol can lose and still finalize (Figure 4.15). The
protocols are ranked here by survival depth — the deepest `φ` at which a protocol
still finalizes anything — rather than by the onset of degradation, because the
two keys give opposite orderings for Casper FFG and Snowman, and survival is the
faithful measure of where liveness fails
[[wiki/experiments/2026-06-19_adversary-comparison]]. PBFT exhibits a clean
quorum cliff: it finalizes without any throughput loss up to `φ = 0.33` and dies
at `φ = 0.40`, the point at which the silent set drops the honest remainder below
the `2f+1` quorum [[wiki/experiments/2026-06-17_offline-validators]]. Casper FFG
degrades gracefully over the same range, still finalizing at `φ = 0.33`; its
throughput — the rate of committed units, a separate magnitude from the success
rate that Figure 4.15 plots — decays in proportion to the participating stake,
approximately `1 − φ`, to a worst surviving ratio near 0.49 at `n = 10` and 0.47
at `n = 25` [[wiki/experiments/2026-06-19_adversary-comparison]]. Snowman cliffs earliest, and
its cliff is committee-size-dependent: it survives only to `φ = 0.10` at `n = 10`
and `φ = 0.20` at `n = 25`, because a poll round closes only once `α_c` sampled
peers respond, and when too many peers are silent the round never completes and
the protocol stalls [[wiki/experiments/2026-06-17_offline-validators]]. At
`n = 25` the `φ = 0.20` cell is technically alive but starved, finalizing at
roughly half a percent of its control throughput
[[wiki/experiments/2026-06-19_adversary-comparison]].

The ordering is therefore PBFT and Casper FFG ahead of Snowman, the two leaders
tied on survival depth and separated only by PBFT's undegraded throughput below
its cliff [[wiki/experiments/2026-06-19_adversary-comparison]]. As under delayed
voting, no protocol forks: silence erodes liveness, not safety
[[wiki/experiments/2026-06-19_adversarial-degradation]]. The result inverts the
delayed-voting verdict for Snowman in particular: the protocol that best
tolerated slow validators, albeit at a latency cost, is the least tolerant of
silent ones, because a sampled supermajority can wait out a slow peer but cannot
complete a poll around an absent one.

**Figure 4.15 — Liveness under silent non-participation.** Finalization success
rate against the injected adversarial fraction `φ`, one curve per protocol,
faceted by validator count. Source:
`results/adversary/plots/liveness_vs_phi_offline.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

### 4.4.3 Equivocation

Equivocation is the only one of the three strategies that can break safety, and
it is the axis on which PBFT and Casper FFG are driven past the one-third
threshold to expose the breaking point. Below the threshold all three protocols
preserve agreement, and, with one exception, liveness (Figure 4.16): Casper FFG's
success rate holds across the full swept range to `φ = 0.50`, Snowman's to the
top of its grid at `φ = 0.33`, while PBFT's dips through a view-change window
before an apparent recovery above the threshold — a recovery that is the safety
failure itself, not restored liveness
[[wiki/experiments/2026-06-19_adversarial-degradation]]. Each protocol holds its
safety invariant to `φ = 0.33`; they differ entirely in what happens above it,
and the difference is the kind of failure, not its onset
[[wiki/experiments/2026-06-19_adversary-comparison]].

PBFT fails catastrophically and without accountability. Below the threshold its
view-change mechanism absorbs the equivocation — an equivocating primary is
detected and the replicas rotate to a new leader — and the view-changes
multiply with the equivocator fraction (Figure 4.17), reaching 10 rotations at
`n = 10` and 25 at `n = 25` at the last safe fraction
[[wiki/experiments/2026-06-19_adversarial-degradation]]. At `φ = 0.40` the
equivocating set exceeds what rotation can contain, and two honest replicas
commit conflicting values at the same height: the safety-violation rate steps
from zero to a deterministic breach, with 229 conflicting instances at both
committee sizes (Figure 4.18)
[[wiki/experiments/2026-06-19_adversary-comparison]]. The fork is deterministic —
invariant across seeds because the equivocating set is fixed rather than sampled,
and identical in count at both committee sizes because the number of conflicting
`(view, seq)` instances inside the measurement window is set by the proposer's
round cadence and the window length, not by the validator-set size
[[wiki/experiments/2026-06-18_equivocating-nodes]] — and it is unaccountable: PBFT
carries no mechanism to attribute the conflicting commit to the validators that
caused it [[wiki/experiments/2026-06-19_adversarial-degradation]].

Casper FFG never forks in the model, and when it fails it fails accountably. Its
finality rule admits no two conflicting finalized checkpoints below the
threshold, and above it the failure surfaces not as a fork but as slashable
stake: the stake an adversary would have to expose to slashing in order to force
a conflicting checkpoint rises with the equivocator fraction and crosses the
one-third accountability line at `φ = 0.40`, peaking at 0.50 of stake at `n = 10`
and 0.48 at `n = 25` (Figure 4.19)
[[wiki/experiments/2026-06-19_adversary-comparison]]. This is the
accountable-safety property of the finality gadget: a safety violation is
possible only at the cost of at least one-third of the stake being provably
slashable [[wiki/algorithms/pos]]. Casper FFG is also the most liveness-robust of
the three to equivocation, its success rate holding across the full swept range
to `φ = 0.50` [[wiki/experiments/2026-06-19_adversarial-degradation]].

Snowman presents no fork surface at all. Equivocation against a subsampling
protocol reduces to a lying responder — a validator that answers different
queries inconsistently — which has no more effect than withholding a response,
so the strategy is not swept above the threshold for Snowman
[[wiki/concepts/adversary-model]]. The empirical safety-violation rate is zero on
every cell of the grid [[wiki/experiments/2026-06-19_adversarial-degradation]].
Snowman's safety is probabilistic rather than categorical and is reported through
its analytical bound `ε ≤ (1 − α_c/K)^β`, approximately `5 × 10⁻¹⁵` at `n = 10`
and a looser `3 × 10⁻¹¹` at `n = 25`, the bound loosening at the larger committee
because the rounding in `α_c = ⌈0.8K⌉` lifts the ratio `α_c/K` above 0.8 only at
small `K` [[wiki/concepts/metric-reconciliation]]. An empirical zero cannot
confirm a bound this small: with eighty observations per cell the data bounds the
violation rate only below a few percent, many orders of magnitude above the
analytical `ε`, so the measured zero records that no violation occurred at the
baseline confidence depth `β = 15`, not that the bound has been observed.
Witnessing `ε` directly would require a separate sweep at a deliberately weakened
confidence depth [[wiki/experiments/2026-06-19_adversarial-degradation]].

Ranked by safety, then, the order is Snowman, Casper FFG, PBFT — not because the
protocols tolerate different fractions, since all three hold to `φ = 0.33`, but
because their failures above it differ in kind: Snowman has no fork to suffer,
Casper FFG forks only at a provable cost of one-third of the stake, and PBFT
forks deterministically and silently
[[wiki/experiments/2026-06-19_adversary-comparison]]. Two cautions attach to this
ordering. The three failures are measured on incommensurable scales — a
conflicting-commit rate for PBFT, a slashable-stake fraction for Casper FFG, and
an analytical bound for Snowman — so the ranking compares kinds of failure, not
magnitudes on a single axis. And Snowman's first place is in part structural:
equivocation presents no fork-inducing surface to a subsampling protocol to begin
with, which is why the strategy is swept only to `φ = 0.33` for Snowman rather
than past it. Snowman is therefore ranked first for having no safety failure mode
to expose, not for surviving a fraction at which the others break
[[wiki/concepts/adversary-model]].

**Figure 4.16 — Liveness under equivocation.** Finalization success rate against
the equivocator fraction `φ`, one curve per protocol, faceted by validator count;
PBFT's curve is non-monotone, its apparent recovery above `φ = 0.33` coinciding
with the safety failure of Figure 4.18. Source:
`results/adversary/plots/liveness_vs_phi_equivocate.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

**Figure 4.17 — PBFT view-change activity under equivocation.** View-change
events per second against the equivocator fraction `φ`, faceted by validator
count; the rate is a monotone indicator of the leader-rotation mechanism that
absorbs equivocation below the one-third threshold, while the absolute
view-change counts at the last safe fraction are the ones reported in the text.
Source: `results/adversary/plots/pbft_viewchange_rate_vs_phi.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

**Figure 4.18 — Cross-protocol safety-violation rate under equivocation.**
Safety-violation rate against the equivocator fraction `φ`, one curve per
protocol, faceted by validator count; only PBFT leaves zero, stepping to a
deterministic fork at `φ = 0.40`, while Casper FFG and Snowman remain at zero —
their failures, where they exist, are reported on the stake axis of Figure 4.19
and through `ε` respectively. Source:
`results/adversary/plots/safety_cliff_vs_phi.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

**Figure 4.19 — Casper FFG slashable stake under equivocation.** Maximum
slashable stake fraction against the equivocator fraction `φ`, faceted by
validator count, with the one-third accountability line marked; the
accountable-safety signal that replaces a fork count for the finality gadget.
Source: `results/adversary/plots/ffg_slashable_vs_phi.pdf`
[[wiki/experiments/2026-06-19_adversarial-degradation]].

### 4.4.4 The performance–security tradeoff

The three strategies together answer RQ4, and their headline is that no protocol
is robust to every adversary, because the structural choice that defends a
protocol against one strategy is the same choice that exposes it to another
(Table 4.2). PBFT's exact quorum and view-change recovery make it the strongest
protocol against the two liveness adversaries — immune to delayed voting and
undegraded under silence up to its quorum cliff — but the same leader-based,
non-accountable commit rule makes it the worst under equivocation, the only
protocol whose safety failure is both deterministic and unattributable. Snowman's
subsampling inverts this profile: it is the strongest against equivocation,
presenting no fork surface and a vanishing probabilistic bound, but it is the
most fragile to silence, its polls starving earliest, and the costliest under
delay, paying an order-of-magnitude latency blow-up. Casper FFG wins no single
adversary outright, yet it is the only protocol with an accountable safety
failure and the most liveness-robust to equivocation, while paying for its single
rotating proposer with the earliest liveness loss under delay and a graceful but
real throughput decay under silence. The protocol best on one axis is last on
another in every case: PBFT first against delay and silence but last against
equivocation, Snowman first against equivocation but last against silence, Casper
FFG never first but never catastrophic
[[wiki/experiments/2026-06-19_adversary-comparison]].

This no-dominance result is not an artifact of how the adversaries were chosen.
The three strategies are the generic capabilities of the adversary catalog,
defined independently of any protocol rather than reverse-engineered to strike
each protocol's known weakness, and every protocol is exposed to all three
[[wiki/concepts/adversary-model]]. The contribution of the section is therefore
not the bare statement that no protocol wins everywhere — which a reader of the
design space might anticipate — but the mechanism-level mapping of which
structural feature produces which failure under which adversary, and the
inversions that mapping reveals: that the same subsampling which makes Snowman
the most delay-tolerant protocol when peers are merely slow makes it the least
tolerant when they fall silent, and that PBFT's leader-based commit rule is at
once the source of its liveness robustness and of its unaccountable fork.

**Table 4.2 — Adversarial outcomes by protocol and strategy (`n = 10 / 25`, 20
seeds).** Values pair the two committee sizes where they differ. Robustness order
is per strategy, ranked on the liveness held for the two liveness adversaries and
on the safety invariant for equivocation. Source:
[[wiki/experiments/2026-06-19_adversary-comparison]].

| Adversarial strategy | PBFT | Casper FFG | Snowman | Robustness order |
| :-- | :-- | :-- | :-- | :-- |
| Delayed voting | immune; finality 1.0×, no view-changes | liveness dips (success → 0.60 / 0.65) | survives; finality ×62 / ×49 | PBFT ≈ Snowman ≫ FFG |
| Silent non-participation | clean quorum cliff at `φ = 0.40`; no decay below it | graceful decay, survives to `φ = 0.33` (throughput ≈ `1 − φ`) | early cliff at `φ = 0.10 / 0.20`; starves | PBFT ≈ FFG > Snowman |
| Equivocation | deterministic unaccountable fork at `φ = 0.40` (229 conflicts) | accountable: ≥ ⅓ stake slashable at `φ = 0.40`, no fork | no fork surface; `ε ≈ 5 × 10⁻¹⁵ / 3 × 10⁻¹¹` | Snowman > FFG > PBFT |

Two qualifications bound this verdict. First, the survey covers three families.
Narwhal+Tusk is unimplemented, so its catalogued weakness — data-availability
withholding, in which a validator certifies a header yet refuses to serve its
contents — is absent, and the adversarial verdict is scoped to the three families
measured [[wiki/concepts/adversary-model]]. The swept strategies are also the
three generic capabilities of the catalog; the leader-disruption surface,
plausibly the sharpest attack on the leader-based protocols, is catalogued but
not exercised. Because the delayed and silent sets are moreover chosen to spare
the view-0 primary, PBFT's standing as the strongest protocol against the two
liveness adversaries is established only against adversaries that leave its leader
honest — a leader-targeting adversary is precisely the case this sweep does not
measure [[wiki/concepts/experiment-matrix]]. Second, several measurement
boundaries
qualify how the numbers should be read. Safety results are seed-invariant, since
the equivocating set is fixed rather than sampled, so the safety columns carry no
seed variance while the success-rate columns carry all of it
[[wiki/experiments/2026-06-19_adversarial-degradation]]; Snowman's analytical `ε`
is not empirically witnessed at the baseline confidence depth, as noted in
§4.4.3; a run truncated at the measurement deadline is not scored a liveness
failure, only a run in which no honest validator commits within the window
[[wiki/concepts/output-format]]; and the latency-only network charges no
signature-verification or other compute cost, so the work of detecting and
recovering from equivocation — view-change rounds for PBFT, slashing-evidence
processing for Casper FFG — is counted in messages but not in computation. This
omission understates the cost borne by precisely PBFT and Casper FFG, whose
equivocation handling is compute-bound, and so flatters those two protocols on
any cost comparison; it does not bear on the message-count, liveness, or safety
verdicts that this section actually draws [[wiki/concepts/network-model]].

Read on the throughput axis rather than the liveness one, the same sweep answers
RQ2: as the injected Byzantine fraction `φ` rises toward the fault threshold,
sustained throughput degrades in three distinct modes — PBFT holds undegraded
until its quorum cliff, Casper FFG decays gracefully in proportion to the
participating stake (≈ `1 − φ`), and Snowman starves earliest as its polls fail
to close — so the rate at which throughput falls is governed by each family's
quorum structure rather than by `φ` alone
[[wiki/experiments/2026-06-19_adversary-comparison]].

The question of whether any one family occupies a dominant position once the
baseline, delay, and adversarial regimes are considered jointly — the
Pareto-frontier synthesis of RQ5 — is taken up in Chapter 5
[[wiki/concepts/research-questions]].
