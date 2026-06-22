# Chapter 4 — Results

## 4.1 Chapter roadmap

Chapter 3 fixed the simulator, the metric schema, and the experiment matrix
[[wiki/concepts/experiment-matrix]] but left their purpose untested: what each
protocol does once the conditions those metrics stress — network delay and
Byzantine validators — are applied. This chapter reports that evaluation and
answers research questions RQ1–RQ4 against the metric schema of §3.5, in three
movements mirroring the three run families. Section 4.2 reports the baseline
scaling sweep, where validator-set size is the only independent variable and the
network is clean; §4.3 the network-delay sweep, where the timeline varies while
the validator set and workload hold fixed; and §4.4 the adversarial sweep, where
a fraction of the honest validators is replaced by each strategy of the fault
model. Three protocols are evaluated throughout — PBFT, Casper FFG, and Snowman —
with the Narwhal+Tusk column reserved until that implementation lands, consistent
with the chapter scope set in §3.6.

The baseline serves two purposes: it establishes that each protocol is correct
on the honest path at every validator count, and it isolates the cost that
scales with the validator set from the cost the later sweeps attribute to delay
and adversarial behavior. Injecting no delay and no faults, it is also the
cleanest setting in which to confront the simulator's measured numbers with each
protocol's published asymptotic theory.

## 4.2 Baseline: scaling with validator-set size

The baseline dataset sweeps validator-set size `n ∈ {4, 7, 10, 16, 25}` at
twenty seeds per configuration under a common deterministic Poisson workload
(`offered_rate = 100` tx/s, `tx_bytes = 512`, `conflict_rate = 0`), with common
random numbers so that seed `k` presents the same arrival stream to every
protocol [[wiki/experiments/2026-06-03_scaling-baseline]]. The 300 trials —
fifteen scenarios of twenty seeds — are aggregated to per-scenario means with
95% confidence intervals [[wiki/experiments/2026-06-08_baseline-cis]]. Snowman
is evaluated from `n = 7` upward: at `n = 4` its parameter rescaling collapses
to the degenerate unanimity boundary `α_c = K` and is excluded by the schema
[[wiki/concepts/output-format]]. The intervals use a Student-t critical value at
nineteen degrees of freedom rather than the Gaussian value named in §3.5; for a
twenty-sample mean the difference is small, and for the deterministic metrics of
§4.2.1 the interval is degenerate regardless.

### 4.2.1 Statistical reliability

The seed has almost no effect at the baseline: every structural metric —
commit latency, decision rate, message overhead, success rate, and fork rate —
has a coefficient of variation of zero across the twenty seeds, so its 95%
confidence interval is degenerate. This is a property of the model, not too
few seeds: at zero delay a protocol's round structure and message counts are
fixed once `(protocol, n)` is fixed, and the only seeded randomness, the
workload arrival process, perturbs goodput alone. Goodput therefore carries
the sole non-degenerate interval — a coefficient of variation near 2.2% and a
half-width near 1% of its mean (Figure 4.5) — so twenty seeds are more than
adequate: a larger set cannot narrow a degenerate interval, and goodput is
already bounded to within a percent of its mean.

**Figure 4.5 — Goodput with 95% confidence intervals (baseline).** Per-protocol
goodput across `n ∈ {4, 7, 10, 16, 25}`; the sole non-degenerate interval
(coefficient of variation ≈ 2.2%), every structural metric being deterministic
across seeds. Source: `results/baseline/plots/goodput_ci_vs_n.pdf`
[[wiki/experiments/2026-06-08_baseline-cis]].

### 4.2.2 Latency

Commit latency is flat in the validator count for all three protocols: absent
network delay, latency is set by each protocol's round and timer structure, not
by the size of the validator set (Figure 4.1). PBFT and Snowman commit the first
unit at approximately 1000 ms and Casper FFG at approximately 5000 ms, and none
changes measurably as `n` grows from 4 to 25. PBFT's figure is one proposal
interval ahead of its three-phase commit; Snowman's is one slot driving its
repeated-poll counter; Casper FFG's is the justify-then-finalize rule spanning
roughly two epochs at the configured one-second slot and two-slot epoch
[[wiki/algorithms/pos#communication-complexity]].

Only the Casper FFG figure carries a calibration qualification. Its finality
interval is a fixed multiple of the slot — `(2·slots_per_epoch +
attest_offset)·slot_duration`, five slot durations at the configured two-slot
epoch — so the absolute ≈5000 ms is set by the chosen one-second slot, not
fixed by the protocol, and the cross-protocol comparison of *absolute* latency
is conditional on that choice
[[wiki/concepts/metric-reconciliation#calibration-defaults]]. What is intrinsic
is the *qualitative* ordering, and it follows from the same formula: finality is
exactly linear in the slot — 2500, 5000, and 10000 ms at 0.5, 1, and 2 s by the
formula — so it stays above the per-block protocols' ≈1000 ms commit for every
slot above a 0.2 s crossover (where five slot durations equal 1000 ms), far
below the 12 s slot a deployed finality gadget such as Ethereum runs
[[wiki/sources/2026-04-21_buterin-gasper-2020]]. A slot-duration sensitivity
sweep confirms the prediction
[[wiki/experiments/2026-06-22_ffg-slot-sensitivity]]. The
protocol-intrinsic result is therefore that Casper FFG finalizes at epoch
granularity, coarser than per-block or per-poll commit at any realistic slot —
not the specific fivefold gap, which moves with the calibration.

This flatness is a property of the zero-delay model; the latency cost that grows
with the validator set and separates the protocols surfaces only under the delay
sweep of §4.3.

**Figure 4.1 — Commit latency versus validator-set size (baseline).** Median
per-validator `commit_latency_ms` for each protocol across the sweep at zero
injected delay; flat in `n` (PBFT and Snowman ≈ 1000 ms, Casper FFG ≈ 5000 ms).
Source: `results/baseline/plots/latency_vs_n.pdf`
[[wiki/experiments/2026-06-03_scaling-baseline]].

### 4.2.3 Throughput and goodput

The schema's two throughput columns are not interchangeable. The decision rate
`tps` grows linearly in `n` — per-validator constant at 0.95 for PBFT and Snowman
and 0.40 for Casper FFG (Figure 4.4) — confirming that it is a decision-event rate
scaling with the validator set, not a measure of system throughput; the
comparable measure is goodput (§3.5), the rate of committed transaction bytes,
flat in `n`:
approximately 95 tx/s for the per-block protocols PBFT and Snowman and
approximately 80 tx/s for Casper FFG (Figure 4.2). The Casper FFG shortfall is a
finality-tail effect — its per-epoch finality leaves the window's last
unfinalized epoch uncommitted, a fixed end-of-window loss the per-block protocols
avoid. Flat goodput is the expected result on a latency-only model with no
per-transaction cost and no queue, where offered load below the protocol's
cadence is always absorbed [[wiki/experiments/2026-06-03_scaling-baseline]]; it
is not a measured capacity ceiling, which would require a capacity model and is
deferred [[wiki/concepts/output-format]].

**Figure 4.2 — Goodput versus validator-set size (baseline).** Committed-
transaction rate (tx/s) for each protocol across the sweep; flat in `n`
(≈ 95 tx/s for PBFT and Snowman, ≈ 80 tx/s for Casper FFG). Source:
`results/baseline/plots/throughput_vs_n.pdf`
[[wiki/experiments/2026-06-03_scaling-baseline]].

**Figure 4.4 — Decision rate (`tps`) versus validator-set size (baseline).**
Per-protocol `tps` (decision events per window), growing linearly in `n` by
construction — not a system-throughput measure (contrast Figure 4.2). Source:
`results/baseline/plots/decision_rate_vs_n.pdf`
[[wiki/experiments/2026-06-03_scaling-baseline]].

### 4.2.4 Communication overhead

Communication overhead is the metric on which the protocols separate most
sharply, and it answers RQ3 [[wiki/concepts/research-questions]]. Messages per
committed unit grow with `n` for all three, but the slopes differ by an order of
magnitude (Figure 4.3, logarithmic axis): PBFT approaches `2n`, Casper FFG
`1.2n`, and Snowman `2·K·β`, where `K` is the poll sample size and `β` the
confidence threshold. Each trend matches the protocol's published asymptotic
cost — Figure 4.7 overlays the measured `total_msgs_per_acu` on the prediction,
and the markers fall on it across the sweep, the largest departures (six to seven
percent) confined to `n = 4`. PBFT's `2n` is its `O(n²)`-per-block cost — the all-to-all PREPARE and COMMIT
phases [[wiki/sources/2026-04-21_castro-liskov-pbft-1999]] — normalized by the
atomic-commit-unit denominator (§3.5), which counts one decision per validator per
instance and so absorbs one factor of `n`, leaving a per-unit cost of `O(n)`
[[wiki/concepts/metric-reconciliation]].
Casper FFG's attestation phase is likewise all-to-all under the
individually-signed-vote model that the original protocol specifies
[[wiki/sources/2026-04-21_buterin-griffith-casper-ffg-2017]] and the simulator
implements — and so `O(n²)` per epoch; its
per-unit slope sits below PBFT's not through aggregation but because one
attestation phase serves more committed decisions than PBFT's two broadcast
phases. The production BLS aggregation that would cut this to `O(n)` is not in
the original specification and is not modelled; introducing it, with the
corresponding threshold-signature PBFT variant, is identified as future work in
§6.3. Snowman's overhead matches `2·K·β` to within half a percent across its
`n = 7`–`25` sweep — the factor of two being the query-and-response pair of each
poll — confirming the per-validator `O(K·β)` cost the Avalanche family is built
around [[wiki/sources/2026-04-21_team-rocket-avalanche-2019]].

Two readings must be kept apart. Per committed unit, Snowman is the most
expensive protocol by an order of magnitude — roughly twenty-four messages per
validator against PBFT's two — the price of repeated subsampling at thesis scale.
Yet the property for which Avalanche is celebrated is that its *per-validator*
cost is independent of `n`, a statement about per-validator work, not about the
network-aggregate `total_msgs_per_acu` plotted here, which necessarily grows with
`n` as each of `n` validators performs that constant work. The independence is
further masked over this range because the thesis rescales `K = min(20, n−1)` (§3.3.3), so `K` still tracks `n`
until it saturates at the production value of 20 near `n = 21`. The result is therefore
reported as a per-unit cost contrast, with the per-validator scalability stated
separately so the figure is not misread.

**Figure 4.3 — Communication overhead versus validator-set size (baseline).**
`total_msgs_per_acu` for each protocol across the sweep, logarithmic vertical
axis; the order-of-magnitude separation that answers RQ3. Source:
`results/baseline/plots/msgs_vs_n.pdf`
[[wiki/experiments/2026-06-03_scaling-baseline]].

**Figure 4.7 — Measured message overhead against predicted asymptotic cost.**
Markers are the measured `total_msgs_per_acu`; dashed lines the per-protocol
predictions — PBFT `2n`, Casper FFG `1.2n`, and Snowman `2·K·β` with
`K = min(20, n−1)`; logarithmic vertical axis. The residual gaps at `n = 4` are
finite-`n` corrections [[wiki/experiments/2026-06-08_baseline-cis]]. Source:
`results/baseline/plots/theory_vs_measured.pdf`, generated by
`src/output/explain.py` [[wiki/experiments/2026-06-09_baseline-explainers]].

### 4.2.5 Reliability

Every scenario commits and none forks: success rate is 1.0 and fork rate 0.0 at
every validator count for all three protocols (Figure 4.6). This confirms
honest-path correctness — each protocol terminates and preserves agreement when
no validator deviates — but carries no comparative information, the three being
indistinguishable on both columns. These metrics become discriminating only once
the adversarial sweep drives validators past their fault thresholds, where the
per-protocol safety invariants of §3.5 diverge; that analysis is §4.4.

**Figure 4.6 — Success and fork rate versus validator-set size (baseline).**
Per-protocol success rate across the sweep; success rate 1.0 and fork rate 0.0
at every `n`, confirming honest-path correctness. Source:
`results/baseline/plots/success_rate_vs_n.pdf`
[[wiki/experiments/2026-06-03_scaling-baseline]].

### 4.2.6 A note on the latency measurement point

The cross-protocol latency comparison of §4.2.2 — and of the delay sweep in
§4.3 — is built from `commit_latency_ms`, not `finality_latency_ms`. Despite its
name, `commit_latency_ms` is the canonical cross-protocol *time-to-finality*
column: the median per-validator time to each protocol's irreversibility
milestone — the `2f+1` commit quorum for PBFT, the finalized checkpoint after the
justify-then-finalize rule for Casper FFG, and counter-`β` acceptance for
Snowman. Aligning these three milestones on one axis is what makes the comparison
meaningful [[wiki/concepts/output-format]]. The two columns coincide for Casper
FFG and Snowman but diverge for PBFT, whose implementation adds a client-reply
round, so its `finality_latency_ms` sits one network hop past the internal commit
quorum at client-observed finality; placing all three protocols'
`finality_latency_ms` on one axis would compare PBFT's client-observed timestamp
against the others' internal ones — not like for like. This column choice is fixed
in the schema that governs figure construction, so the comparison's correctness
does not depend on the reader noticing this paragraph
[[wiki/concepts/output-format]].

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

The baseline establishes three results the later sweeps build on. First, all
three protocols are correct on the honest path at every validator count. Second,
at zero delay both latency and goodput are flat in `n`, so neither separates the
protocols here — that separation comes from the delay and adversarial axes.
Third, communication overhead already separates them by an order of magnitude in
a direction matching their published asymptotic costs, establishing the
performance–structure contrast RQ3 asks about and that §4.3 will stress further.

## 4.3 Network-delay sweep

The delay sweep holds the validator set and workload fixed and varies the
network timeline, isolating the latency and loss the baseline of §4.2 excluded.
It draws two regimes from run family B [[wiki/concepts/experiment-matrix]]. The
moderate regime applies two loss-free timelines of equal mean but different tail
shape — `delay-uniform` on [100, 500] ms and `delay-exponential` of the same
300 ms mean [[wiki/experiments/2026-06-10_delay-moderate]]. The heavy regime
applies a heavy-tailed Pareto delay of roughly three-second mean, first without
loss as a control and then under per-message drop probabilities of 5%, 10%, and
20% [[wiki/experiments/2026-06-12_delay-heavy]]. Each cell runs at `n ∈ {10, 25}`
over twenty seeds with common random numbers, except the most expensive —
Snowman at `n = 25` under heavy delay — over eight. As in §4.2, three of the four
families are covered; Narwhal+Tusk awaits its implementation.

Two measurement properties frame the results. All cross-protocol latency is read
from `commit_latency_ms`, the canonical time-to-finality column of §4.2.6, so
each protocol's irreversibility milestone is compared like for like
[[wiki/concepts/output-format]]. And delay and loss attack different properties,
reported apart: delay inflates time-to-finality (RQ1), loss erodes liveness
(RQ4) [[wiki/concepts/research-questions]]. The section follows that order —
latency, then the loss-resilience ranking, then its mechanisms, then the tradeoff
tying the two together.

### 4.3.1 Delay and time-to-finality

Under moderate delay the three protocols separate by nearly an order of
magnitude, governed by each protocol's round structure rather than the network
(Figure 4.8). PBFT rises from its ≈1000 ms zero-delay baseline to approximately
1.95 s — about 0.9 s, one network round-trip absorbed into each of its three
phases — and is near-flat in `n` because those phases overlap across the
validator set [[wiki/experiments/2026-06-10_delay-moderate]]. Casper FFG rises
from approximately 5.0 to 6.3 s, about 27%, but this is slot-dominated, not
network-dominated: the coherence rule `slot ≥ 4·E[delay]` (§3.4.3) rescales the
finality-gadget slot from one second to 1.2 s, and the same 20% scales the
slot-bound finality interval, lengthening FFG's roughly five-second finality to
about six and leaving only some 0.3 s to attestation propagation
[[wiki/concepts/experiment-matrix]]. Casper FFG's delay sensitivity is therefore
indirect, mediated by its slot clock.

Snowman is by far the most delay-exposed, rising from approximately 1000 ms to
between 12 and 15 s, a factor of twelve to fifteen
[[wiki/experiments/2026-06-10_delay-moderate]]. Its confidence counter requires
`β = 15` poll rounds in sequence (§3.3.3), each a query-and-response exchange
costing about two network delays, so the fifteen rounds accumulate roughly twelve
seconds. Its latency too is near-flat — indeed slightly lower — in `n`, because
the poll sample size `K` rescales with the committee rather than the first
block's finality time growing with it (§3.3.3).

The two timelines share a mean but differ in tail shape, separating the
protocols a second way. PBFT and Casper FFG are nearly tail-insensitive,
differing by at most three percent between the uniform and exponential
timelines, because a fixed count of rounds or slots averages out the per-message
delay [[wiki/experiments/2026-06-10_delay-moderate]]. Snowman is the exception:
its exponential-timeline latency exceeds its uniform-timeline latency at both
committee sizes — approximately 15.3 against 12.6 s at `n = 10` — because each
poll round waits on the slowest of its `K` sampled peers, and the memoryless tail
inflates that slowest response across the fifteen sequential rounds. Communication
overhead, by contrast, does not move with delay: PBFT's messages per committed
unit hold the same `2n` measured at zero delay and Snowman's stay within about
two percent, confirming that message count is fixed by protocol structure, not
network timing (§4.2.4).

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
whether it happens at all. The measure is the finalization rate: instances
finalized under loss as a fraction of those finalized on the matched loss-free
control [[wiki/experiments/2026-06-12_delay-heavy]]. Figure 4.9 plots it against
drop probability per protocol and committee size, showing three degradation
shapes: PBFT declines along a shallow tail that stays above zero to the deepest
tested loss, Snowman holds a high plateau then falls to near-zero within a single
step, and Casper FFG collapses at the first loss step. A fixed 95%-finalization
breakpoint was rejected as a resilience score: every protocol is already below it
at the lightest tested loss, collapsing the field to an uninformative tie
[[wiki/experiments/2026-06-13_delay-comparison]].

The protocols are therefore ranked by the area under the finalization-rate curve
(AURC), with survival depth — the deepest loss at which a protocol still
finalizes anything — as the tiebreak, the two committee sizes reported separately
[[wiki/experiments/2026-06-13_delay-comparison]]. At `n = 10` the order is strict
(Figure 4.10): PBFT leads with an AURC of 0.253 and survives to 20% loss, Snowman
follows at 0.174, Casper FFG trails at 0.149. At `n = 25` PBFT and Snowman tie at
the top — Snowman's point estimate of 0.369 and PBFT's of 0.351 carry overlapping
intervals, [0.366, 0.372] against [0.327, 0.376], so neither outranks the other —
while Casper FFG remains last at 0.140. Unlike the deterministic baseline of
§4.2.1, the finalization rate genuinely varies with the seed, since which
messages drop depends on it; the intervals in Figures 4.9 and 4.10 are
accordingly non-degenerate. They are Wilson-score intervals, the schema's form
for rate metrics (§3.5); Snowman's at `n = 25` is widest, that cell being
estimated from eight seeds rather than twenty
[[wiki/experiments/2026-06-12_delay-heavy]].

Two findings stand out. First, PBFT is the only protocol still finalizing at 20%
loss, at both committee sizes — 10% of its control rate at `n = 10`, 6% at
`n = 25` — whereas neither other survives past 10% loss, each fallen to zero by
the 20% step [[wiki/experiments/2026-06-13_delay-comparison]]. Second, committee
size is a sharp resilience lever for Snowman: its finalization rate at 5% loss
rises from 0.195 at `n = 10` to 0.904 at `n = 25`, so at light loss the larger
committee makes Snowman the strongest of the three, even as it still cliffs to
near-zero by 10% [[wiki/experiments/2026-06-12_delay-heavy]]. The same enlargement
is a mild liability for Casper FFG, whose 5%-loss rate falls slightly, 0.070 to
0.051. Throughout the loss sweep no protocol forks: loss degrades liveness, not
safety [[wiki/experiments/2026-06-12_delay-heavy]].

**Figure 4.9 — Finalization rate under packet loss.** Finalization rate against
per-message drop probability, one curve per protocol, faceted by validator
count, with 95% confidence intervals. Source:
`results/delay/plots/finalization_degradation.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

**Figure 4.10 — Loss-resilience ranking.** Area under the finalization-rate
curve (AURC) with 95% confidence intervals, annotated with each cell's survival
depth `p*`, faceted by validator count; overlapping intervals share a rank (the
`n = 25` PBFT–Snowman tie). Source:
`results/delay/plots/resilience_ranking.pdf`
[[wiki/experiments/2026-06-13_delay-comparison]].

### 4.3.3 Mechanisms of degradation

The ranking follows from what each protocol can do when messages are lost
(Figures 4.11 and 4.12) [[wiki/experiments/2026-06-13_delay-analysis]]. PBFT is
the most robust because it has a genuine recovery path: when dropped prepare or
commit messages stall an instance below its quorum, a per-instance timer fires,
the replicas rotate the leader through a view-change, and the instance is
reissued under the new leader. This is a retry, not a retransmission — a fresh
round with fresh messages, and so a fresh chance to assemble the quorum — and
enough retries eventually succeed even under heavy loss. The recovery is visible
in the view-change count, climbing with loss from zero to sixteen and then thirty
at `n = 10`, and from zero through twenty-eight and sixty-three to seventy-five at
`n = 25` (Figure 4.12).

Snowman's robustness is of a different kind: redundancy within a single poll
round, not recovery across rounds. A round closes once `α_c` agreeing responses
arrive, tolerating the loss of peers beyond that threshold, but there is no poll
timeout and no retransmission — a round that never collects `α_c` responses
simply stalls. Because a response survives only if both its query and reply
survive, the expected usable responses per round is `K·(1−p)²`, and the round
closes only while this exceeds `α_c`; the slack `K − α_c` is one at `n = 10` but
four at `n = 25`, which is why the larger committee tolerates so much more loss
(§3.3.3). Once that margin is exhausted the `β = 15` rounds compound, the
probability of completing all fifteen falling away sharply and turning the
degradation into a cliff rather than a slope — an argument that predicts the
cliff's location and the committee-size ordering, used qualitatively
[[wiki/experiments/2026-06-13_delay-analysis]].

Casper FFG is the most fragile, having neither recovery nor in-round redundancy.
Finalization requires a two-thirds-stake supermajority to attest the same
checkpoint and then two such justifications in consecutive epochs; attestations
are broadcast once per epoch, so when enough are lost the epoch never justifies,
with no leader to rotate and no resampling to fall back on. A 5% drop already
collapses it, and a larger committee is a slight liability, adding attestation
links that can be lost without adding redundancy
[[wiki/experiments/2026-06-12_delay-heavy]]. Under heavy delay a node may justify
an epoch before its checkpoint block arrives locally; a guard added during the
heavy-delay experiments converts what would have been a crash into an honest
stall, the node skipping the attestation and retrying at a later slot
[[wiki/experiments/2026-06-12_delay-heavy]].

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

The two stress axes meet in one conclusion: the protocols that survive loss are
the ones that pay the most latency to do so (Figure 4.13). PBFT and Snowman both
inflate their time-to-finality by factors of roughly two to three-and-a-half at
the worst loss they survive, converting that cost into survival — PBFT a long
tail to 20% loss, Snowman a high but brittle plateau
[[wiki/experiments/2026-06-13_delay-analysis]]. Casper FFG does not make the
trade: it inflates latency by only about three to ten percent, but that
near-constant cost is measured over the few seeds that still finalize and buys
almost nothing, since it no longer finalizes by 10% loss. No configuration in the dataset is
both cheap and resilient; for an operator, protecting liveness against a lossy
network is a choice of how much latency to spend, not whether to spend it.

The delay-family verdict follows. PBFT degrades most gracefully, alive at the
deepest tested loss at both committee sizes; Snowman is strong but brittle, best
in class at light loss with a large committee but prone to sudden collapse;
Casper FFG is fragile, never establishing a resilient plateau. The `n = 25`
PBFT–Snowman tie is a genuine crossover, not noise: the two win on different
virtues — Snowman on area under the curve, retaining 0.90 finality at 5% loss,
PBFT on survival depth, alone alive at 20% — so neither ranks first outright
[[wiki/experiments/2026-06-13_delay-comparison]]. Casper FFG's fragility is, in
mechanism, the same class of failure that motivated this study (§1.2):
attestations that fail to reach a quorum — dropped by a lossy network here,
delayed under attestation-processing pressure in Ethereum's multi-epoch finality
stall of May 2023 there — leave the epoch unjustified and finality stalled
[[wiki/algorithms/pos]]. Whether any one family dominates across the baseline,
delay, and adversarial regimes jointly — RQ5 — is taken up in the synthesis of
Chapter 5 [[wiki/concepts/research-questions]].

Two caveats qualify these results. First, the aligned milestones of §4.2.6 differ
in kind: PBFT and Casper FFG offer deterministic finality, Casper FFG's
additionally accountable — reverting a finalized checkpoint requires at least
one-third of the stake to be slashed
[[wiki/sources/2026-04-21_buterin-griffith-casper-ffg-2017]] — whereas Snowman's
is probabilistic, a residual reversion probability bounded by `(1 − α_c/K)^β`,
approximately `5 × 10⁻¹⁵` at `n = 10` and a looser `3 × 10⁻¹¹` at `n = 25` (the
bound loosens at the larger committee because the rounding in `α_c = ⌈0.8K⌉`
raises the ratio above 0.8 only at small `K`) (§3.3.3). The empirical and
analytical `ε` columns recording this residual per run are deferred to a separate
sweep at a deliberately weakened confidence depth, as §4.4.3 details
[[wiki/concepts/output-format]]. Second, and more important for the loss results:
loss is modeled as permanent per-message drop with no transport-layer
retransmission, so the finalization-rate curves are an upper bound on fragility
[[wiki/experiments/2026-06-13_delay-analysis]]. The ordering — PBFT most robust,
Casper FFG most fragile — is a property of the protocols' recovery mechanisms and
would survive a retransmitting transport, but the absolute collapse levels of 5%
to 20% would shift higher beneath one.

**Figure 4.13 — The operator tradeoff.** Finalization rate retained against the
added-latency ratio (loss latency over control latency, logarithmic), faceted by
validator count; cells that no longer finalize are pinned on a "no finality"
band; the operator-best region is the upper left. Source:
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
approximately `1 − φ` (Figure 4.20), to a worst surviving ratio near 0.49 at `n = 10` and 0.47
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
quorum structure rather than by `φ` alone (Figure 4.20)
[[wiki/experiments/2026-06-19_adversary-comparison]].

**Figure 4.20 — Throughput degradation versus adversarial fraction (silent
non-participation).** Committed-unit throughput against the injected silent
fraction `φ` for each protocol, one panel per committee size (`n = 10`,
`n = 25`); the three RQ2 degradation modes read off the curves directly — PBFT
undegraded to its quorum cliff, Casper FFG decaying in proportion to the
participating stake (≈ `1 − φ`), and Snowman starving earliest. Source:
`results/adversary/plots/throughput_vs_f_n10.pdf` and
`results/adversary/plots/throughput_vs_f_n25.pdf`
[[wiki/experiments/2026-06-17_offline-validators]].

The question of whether any one family occupies a dominant position once the
baseline, delay, and adversarial regimes are considered jointly — the
Pareto-frontier synthesis of RQ5 — is taken up in Chapter 5
[[wiki/concepts/research-questions]].
