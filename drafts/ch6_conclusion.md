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

Table 6.1 carries the detail; the through-line is that each answer is set by a
structural choice rather than by the fault fraction alone. Latency is flat in `n`
but carried differently under delay, Snowman alone paying an order of magnitude
(RQ1); throughput degrades in three quorum-set modes, with Casper FFG tracking
`1 − φ` and Snowman starving earliest (RQ2); and per-unit overhead is linear for
PBFT and Casper FFG but roughly fourteenfold heavier for Snowman's subsampled
polling at `n = 16` (RQ3) [[wiki/concepts/key-findings]]. No protocol is robust to
every adversary, because each structural defense is also an exposure: PBFT is
immune to the liveness adversaries exercised here yet is the only unaccountable
fork, Snowman leads on equivocation safety yet is the most delay- and
silence-exposed, and Casper FFG is never first yet holds the only accountable
failure (RQ4). From that mechanism map follows the RQ5 verdict: a consistent
frontier exists and no family dominates, the verdict surviving even when the one
axis only a slashing-based protocol can hold is set aside
[[wiki/concepts/research-questions]].

## 6.2 Limitations

The findings hold within boundaries that Chapter 3 fixed and the analysis honored
throughout.

**The cost model.** The simulator charges network latency but no
signature-verification, execution, or bandwidth cost. This boundary bears on cost
and per-validator verdicts, which it flatters for the compute-bound equivocation
handling of PBFT and Casper FFG. It does not bear on the message-count,
liveness, or safety results [[wiki/concepts/network-model]]. The throughput model
has no saturation ceiling: goodput is reported against an offered load below any
saturation point, so the flat-in-`n` goodput is a property of the unsaturated
model rather than a claim about peak capacity [[wiki/concepts/output-format]].

**Commensurability.** Thesis-scale committee sizes require rescaling protocol
parameters (Snowman's `K`, `α_c`, and `β`, and the Casper FFG slot-to-delay
coherence rule), so the cross-protocol verdicts rest on those conventions. They
are reported as robust only where they survive the governing sensitivity check
[[wiki/concepts/metric-reconciliation]]. The evaluation covers the three protocols
implemented in the harness, and the comparative verdicts are scoped to them. The
frontier is likewise traced only over the regimes measured, and a high-throughput
regime outside that span is not represented. The absence of a configuration
that is at once cheap, fast, and resilient is therefore a statement about the measured plane
rather than the whole design space. Snowman's safety is reported through its
analytical bound `ε ≤ (1 − α_c/K)^β` rather than a measured fork rate, so its
safety standing is the weakest-witnessed of the three (§3.5)
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
surface is catalogued but not measured. That surface is plausibly the sharpest
attack on the leader-based protocols. PBFT's liveness standing is therefore
established only against adversaries that leave its leader honest
[[wiki/concepts/adversary-model]].

## 6.3 Directions for further work

### 6.3.1 Production-optimized protocol variants

The communication-overhead comparison of §4.2.4 evaluates each protocol at the
message granularity of its original specification — classical PBFT with all-to-all
prepare and commit phases [4], Casper FFG with individually signed attestations [7]
[[wiki/algorithms/pos#communication-complexity]]. Production deployments reduce this
cost through signature aggregation: the Ethereum beacon chain aggregates committee
attestations with BLS signatures, collapsing Casper FFG's per-epoch cost from
`O(n²)` to `O(n)` [8], and HotStuff achieves the analogous reduction for the PBFT
family with threshold-signature collection at the leader [5]
[[wiki/algorithms/pbft#communication-complexity]]. Modeling these aggregated
variants would establish whether the per-unit cost ordering observed at the
as-specified granularity survives at the granularity of deployed systems.

The extension carries one methodological requirement. Because signature aggregation
is a property of a family's signature scheme rather than of an individual protocol,
aggregating one family while leaving another at its un-aggregated specification
would compare implementations at different optimization levels and so misstate the
per-unit cost contrast that answers RQ3 [[wiki/concepts/research-questions]]. A
faithful extension therefore holds the optimization level constant — either
modeling all signature-based families at production granularity (aggregated Casper
FFG against a HotStuff-style PBFT), or reporting the as-specified and aggregated
regimes side by side. The side-by-side form is the more conservative, preserving
the present baseline as a point of comparison; the choice between the two is left
to the supervisor, and an implementation plan for the Casper FFG side is recorded
as a kickoff specification in the project repository.

### 6.3.2 Further directions

Five directions remain open beyond the production-optimized variants of §6.3.1.
The first is a saturation-throughput capacity model: the
present baseline reports goodput against an offered load below saturation, so
throughput reads as flat in the validator set, and replacing the unsaturated model
with one that drives each protocol to a measured ceiling would turn the
flat-goodput baseline into a peak-capacity comparison
[[wiki/concepts/output-format]]. The second is an adaptive-timeout enhancement:
exponential backoff with jitter, calibrated to observed round-trip time, which
the simulator is positioned to evaluate against the baseline. A meaningful
comparison would require a regime that stresses timeout calibration directly, such
as a tight view-change budget under high-jitter delay or a post-GST recovery
scenario. The steady-state sweeps reported here are not such a regime: in them the
view-change budget was set generously enough that recovery timers seldom fired
[[wiki/experiments/2026-06-10_delay-moderate]]. The
third is to witness Snowman's analytical safety bound empirically by driving the
protocol at a weakened confidence depth where forks become observable, closing the
gap between the reported bound and a measured rate
[[wiki/concepts/adversarial-degradation-metrics]]. The fourth is to extend the harness
to a DAG-based family (Narwhal+Tusk), whose data-availability-withholding adversary
the present sweep does not cover; adding it would populate the high-throughput
corner that the three-family frontier leaves unmeasured
[[wiki/concepts/adversary-model]]. The fifth is to repeat the
comparison at larger validator sets and against a transport that models bandwidth
and retransmission, testing how far the rankings reported here survive outside
the simplifying assumptions that made the controlled comparison possible
[[wiki/concepts/network-model]].

## 6.4 Concluding remarks

The contribution of this thesis is a single harness in which representative
Layer-1 consensus protocols could be subjected to the same delay and adversarial
conditions and measured against one schema. The comparative reading it made
possible has a single headline: not a winner, but a map of which structural
commitment places each family where on the performance–security frontier. Because
the same structural choice that places a family on one corner is what exposes it
on another, this is a map of mechanisms rather than an artifact of the comparison
set. The incidents that opened this study (§1.2) — Ethereum's May 2023 finality
stall [21] and the Solana and Cosmos liveness halts — are read here not as
interchangeable faults to be engineered away by one better protocol, but as the
separable consequences of the choices a protocol makes, consequences an evaluation
on matched assumptions can name.
