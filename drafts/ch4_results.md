# Chapter 4 — Results

## 4.1 Chapter roadmap

This chapter reports the experimental evaluation prescribed by the
experiment matrix [[wiki/concepts/experiment-matrix]] and answers research
questions RQ1–RQ4 against the metric schema fixed in §3.5. It proceeds in
three movements that mirror the three run families. Section 4.2 reports the
baseline scaling sweep, in which validator-set size is the only independent
variable and the network carries no injected delay or adversary. Section 4.3
reports the network-delay sweep and Section 4.4 the adversarial sweep; both
are reserved for the experiments of Weeks 9 and 10 and are populated by tasks
T50 and T56 respectively. Three protocols are evaluated at this stage — PBFT,
Casper FFG, and Snowman — with the Narwhal+Tusk column reserved for its
implementation (T38.1), consistent with the chapter scope set in §3.6.

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
slot and two-slot epoch [[wiki/algorithms/pos#communication-complexity]]. The
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
approaches `2n` messages per committed unit; Casper FFG's approaches `1.2n`;
and Snowman's tracks `2·K·β`, where `K` is the poll sample size and `β` the
confidence threshold. Each measured trend matches the protocol's published
asymptotic cost. PBFT's normal-case cost is `O(n²)` messages per block
[[wiki/algorithms/pbft#communication-complexity]]; the per-unit metric reads
`O(n)` because the atomic-commit-unit denominator counts one decision per
validator per instance, absorbing exactly one factor of `n` from the
all-to-all prepare and commit phases. Casper FFG's single attestation round
per epoch is the cheaper `O(n)` aggregated cost
[[wiki/algorithms/pos#communication-complexity]], which is why its slope sits
below PBFT's. Snowman's measured overhead matches `2·K·β` to within half a
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

The cross-protocol latency comparison of §4.2.2 is built from
`commit_latency_ms`, the median per-validator time to a protocol's first
internal decision, and not from `finality_latency_ms`. The two columns
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

`TODO(T50)` — reserved for the Week 9 delay experiments (T46–T49).

## 4.4 Adversarial sweep

`TODO(T56)` — reserved for the Week 10 adversarial experiments (T51–T55).
