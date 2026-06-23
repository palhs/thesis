# Chapter 6 — Conclusions

## 6.1 Summary of findings

This thesis set out to measure, on matched assumptions and in a single harness,
how representative Layer-1 consensus protocols behave under the network and
adversarial conditions their guarantees assume away. The simulator, its metric
schema, and its experiment matrix were built in Chapter 3; the campaign ran in
Chapter 4 and was synthesized in Chapter 5. The five research questions are now
answered over the three protocols evaluated — PBFT, Casper FFG, and Snowman. The
five answers are collected in Table 6.1 and developed below.

**Table 6.1 — The five research questions and their answers over the three
protocols evaluated.** Source: [[wiki/concepts/research-questions]],
[[wiki/concepts/key-findings]].

| RQ | Question | Answer | Governing mechanism |
| :-- | :-- | :-- | :-- |
| RQ1 | latency under rising network-delay variance | flat in `n`; PBFT +≈ 0.9 s, Casper FFG +≈ 27%, Snowman ×12–13 | round structure vs. `β` sequential polls |
| RQ2 | sustained throughput as `φ` rises to the threshold | three modes: PBFT holds then cliffs, Casper FFG ≈ `1 − φ`, Snowman starves earliest | quorum structure |
| RQ3 | communication overhead per committed unit | PBFT ≈ `2n`, Casper FFG ≈ `1.2n` (cheapest), Snowman ≈ `2Kβ` (≈ 14× PBFT at `n = 16`) | all-to-all / attestation vs. `K`-poll |
| RQ4 | which adversary causes liveness or safety loss | no protocol robust to all three; the mechanism map | each structural defense is also an exposure |
| RQ5 | consistent Pareto frontier; any dominance | a frontier exists; no family dominates | each family non-dominated on ≥ 1 axis |

RQ1 asked how commit latency scales as network-delay variance rises. The three
families carry delay very differently: PBFT adds under a second under moderate
delay, Casper FFG roughly twenty-seven percent — an increase dominated by its
slot-clock rescaling rather than by attestation propagation — and Snowman an order
of magnitude, the last being the only protocol sensitive to the shape of the delay
distribution. Commit latency is otherwise flat in the validator set. The
network timeline, not the committee size, governs time-to-finality
[[wiki/concepts/key-findings]]. RQ2 asked how sustained throughput degrades as
the Byzantine fraction approaches the fault threshold. Throughput degrades in
three distinct modes — PBFT undegraded until a hard quorum cliff, Casper FFG
decaying in proportion to the participating stake at approximately `1 − φ`, and
Snowman starving earliest — so the rate of throughput loss is set by each
family's quorum structure rather than by the fault fraction alone
[[wiki/concepts/key-findings]]. RQ3 asked after relative communication overhead.
Per committed unit, PBFT and Casper FFG grow linearly in the validator set, while
Snowman's subsampled polling costs an order of magnitude more at thesis scale,
roughly fourteenfold at `n = 16` [[wiki/concepts/key-findings]].

RQ4 asked which adversary drives which protocol to a liveness loss, a safety
violation, or neither. No protocol is robust to every adversary. The structural
choice that defends a family against one strategy is the same that exposes it to
another, and the contribution is the resulting mechanism map. PBFT is immune to
the liveness adversaries exercised here — those that spare the view-0 primary —
but is the source of the only unaccountable fork. Snowman is the equivocation-safety
leader on its analytical bound, reported rather than empirically witnessed, yet
the most delay- and silence-exposed of the three. Casper FFG is never first against
any single adversary but holds the only accountable failure
[[wiki/concepts/key-findings]].
RQ5 asked whether a consistent performance–security frontier exists and whether
any family dominates [[wiki/concepts/research-questions]]. A consistent frontier
exists across the three families. No family dominates: each is the strict best
on at least one axis, and the frontier admits no configuration that is at once
cheap, fast, and resilient [[wiki/concepts/key-findings]]. The verdict does not
turn on the one axis only a slashing-based protocol can hold: even setting
accountable safety aside, each family remains non-dominated on a measured axis
[[wiki/concepts/key-findings]].

Returning to the incidents that motivated the study (§1.2), the measured failure
modes are the controlled analogues of the deployment ones. An attestation quorum
lost to a lossy network reproduces the class of finality stall observed on
Ethereum in May 2023 [21], and a leader-based protocol's view-change behavior under
stress reproduces the class of liveness halt observed when block production stalls
[[wiki/concepts/key-findings]]. The synthesis is that these are not symptoms of
one immature technology but the consequences of distinct structural
commitments, which is why no single protocol resolves all of them.

## 6.2 Limitations

The findings hold within boundaries that Chapter 3 fixed and the analysis honored
throughout, drawn together here under three headings.

**The cost model.** The simulator charges network latency but no
signature-verification, execution, or bandwidth cost; this boundary bears on cost
and per-validator verdicts, which it flatters for the compute-bound equivocation
handling of PBFT and Casper FFG, and it does not bear on the message-count,
liveness, or safety results [[wiki/concepts/network-model]]. The throughput model
has no saturation ceiling: goodput is reported against an offered load below any
saturation point, so the flat-in-`n` goodput is a property of the unsaturated
model rather than a claim about peak capacity [[wiki/concepts/output-format]].

**Commensurability.** Thesis-scale committee sizes require rescaling protocol
parameters — Snowman's `K`, `α_c`, and `β`, and the Casper FFG slot-to-delay
coherence rule — so the cross-protocol verdicts rest on those conventions and are
reported as robust only where they survive the governing sensitivity check
[[wiki/concepts/metric-reconciliation]]. The evaluation covers the three protocols
implemented in the harness, and the comparative verdicts are scoped to them. The
frontier is likewise traced only over the regimes measured; a high-throughput
regime outside that span is not represented, so the absence of a configuration
that is at once cheap, fast, and resilient is a statement about the measured plane
rather than the whole design space. Snowman's safety is reported through its
analytical bound `ε ≤ (1 − α_c/K)^β` rather than a fork count, and an empirical
zero is a non-witness of that bound, not a confirmation of it
[[wiki/concepts/adversarial-degradation-metrics]]. Several rankings also rest on
narrow support: the loss-resilience comparison of the two most resilient families
at `n = 25` is a statistical tie, their confidence intervals overlapping on a
reduced seed count (Chapter 5, Table 5.1), so the absence of a dominant family
there is a non-rejection rather than a measured separation
[[wiki/concepts/key-findings]].

**The adversarial sweep.** Packet loss is modeled as permanent per-message drop
with no transport retransmission, so the loss-resilience curves are an upper bound
on fragility rather than a model of a retransmitting transport
[[wiki/concepts/key-findings]]. The sweep exercises the three generic capabilities
of the adversary catalog and spares the view-0 primary, so the leader-disruption
surface — plausibly the sharpest attack on the leader-based protocols — is
catalogued but not measured, and PBFT's liveness standing is established only
against adversaries that leave its leader honest [[wiki/concepts/adversary-model]].

## 6.3 Directions for further work

### 6.3.1 Production-optimized protocol variants

The communication-overhead comparison of §4.2.4 evaluates each protocol at the
message granularity of its original specification: classical PBFT with
all-to-all prepare and commit phases [4], and Casper FFG with individually signed
attestations counted toward a supermajority [7]
[[wiki/algorithms/pos#communication-complexity]]. Production deployments of both
families reduce this cost through signature aggregation. The Ethereum beacon
chain aggregates committee attestations with BLS signatures, which collapses
Casper FFG's per-epoch attestation cost from the `O(n²)` of propagated
individual votes to `O(n)` [8] [[wiki/algorithms/pos#communication-complexity]];
HotStuff achieves the analogous reduction for the PBFT family, replacing the
quadratic vote phases with threshold-signature collection at the leader to
obtain linear normal-case and view-change communication [5]
[[wiki/algorithms/pbft#communication-complexity]]. Modeling these aggregated
variants is the most direct extension of the present communication-overhead
results, and would establish whether the per-unit cost ordering observed at the
as-specified granularity survives at the granularity of deployed systems.

This extension carries a methodological requirement that constrains how it must
be undertaken. Signature aggregation is a property of a protocol family's
signature scheme rather than of an individual protocol; introducing it for one
family while leaving another at its un-aggregated specification would compare
implementations at different levels of optimization and would therefore
misstate the per-unit cost contrast that answers RQ3
[[wiki/concepts/research-questions]]. A faithful extension consequently either
models all signature-based families at their production-optimized message
granularity — aggregated Casper FFG against a HotStuff-style PBFT — or reports
the as-specified and the aggregated regimes side by side, so that the level of
optimization is held constant across the comparison. Of the two, side-by-side
reporting is the more conservative: it preserves the present as-specified baseline
as a point of comparison rather than replacing it, so the per-unit ordering
reported here remains legible alongside the optimized one. The final choice between
side-by-side reporting and a uniformly aggregated comparison is a methodological
decision left to the supervisor. An implementation plan for the Casper FFG side — the aggregation topology, the
message-counting convention, and the comparability decision described here — is
recorded as a kickoff specification in the project repository.

### 6.3.2 Further directions

Beyond the production-optimized variants of §6.3.1, the evaluation leaves several
directions open. The most direct is a saturation-throughput capacity model: the
present baseline reports goodput against an offered load below saturation, so
throughput reads as flat in the validator set, and replacing the unsaturated model
with one that drives each protocol to a measured ceiling would turn the
flat-goodput baseline into a peak-capacity comparison
[[wiki/concepts/output-format]]. A second is an adaptive-timeout enhancement —
exponential backoff with jitter, calibrated to observed round-trip time — which
the simulator is positioned to evaluate against the baseline; a meaningful
comparison would require a regime that stresses timeout calibration directly, such
as a tight view-change budget under high-jitter delay or a post-GST recovery
scenario, rather than the steady-state sweeps reported here, in which the view-change
budget was set generously enough that recovery timers seldom fired
[[wiki/experiments/2026-06-10_delay-moderate]]. A
third is to witness Snowman's analytical safety bound empirically by driving the
protocol at a weakened confidence depth where forks become observable, closing the
gap between the reported bound and a measured rate
[[wiki/concepts/adversarial-degradation-metrics]]. Finally, the campaign runs at
thesis-scale committee sizes under a latency-only network; repeating the
comparison at larger validator sets and against a transport that models bandwidth
and retransmission would test how far the rankings reported here survive outside
the simplifying assumptions that made the controlled comparison possible
[[wiki/concepts/network-model]].

## 6.4 Concluding remarks

The contribution of this thesis is a single harness in which representative
Layer-1 consensus protocols could be subjected to the same delay and adversarial
conditions and measured against one schema. Across the three protocols evaluated,
the comparative reading that harness made possible has a single headline: not a
winner, but a map. No family dominates. The value of the result is the account of
which structural commitment places each family where on the performance–security
frontier.

This is more than the truism that three differently optimized protocols each win
their own axis. The same structural choice that places a family on one corner is
what exposes it on another, so the result is a map of mechanisms rather than an
artifact of the comparison set. The deployment failures that opened the study were
the motivation for asking, and the synthesis answers them in their own terms:
liveness halts and finality stalls are not interchangeable faults to be engineered
away by a single better protocol, but the separable consequences of the choices a
protocol makes, consequences that an evaluation on matched assumptions can name.
