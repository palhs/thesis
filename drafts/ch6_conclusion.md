# Chapter 6 — Conclusions

## 6.1 Summary of findings

This thesis measured, on matched assumptions and in a single harness, how three
representative Layer-1 consensus protocols — PBFT, Casper FFG, and Snowman —
behave under the network and adversarial conditions their guarantees assume away.
Table 6.1 collects the answers to the five research questions; the through-line is
that each answer is set by a structural choice rather than by the fault fraction
alone, and that no protocol is robust to every adversary because each structural
defense is also an exposure.

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

## 6.2 Limitations

The findings hold within boundaries that Chapter 3 fixed.

- **Cost model.** The simulator charges network latency but no
  signature-verification, execution, or bandwidth cost. This flatters the cost and
  per-validator verdicts for the compute-bound equivocation handling of PBFT and
  Casper FFG; it does not bear on the message-count, liveness, or safety results
  [[wiki/concepts/network-model]].
- **No capacity model.** Goodput is reported against an offered load below
  saturation, so the flat-in-`n` goodput is a property of the unsaturated model
  rather than a claim about peak capacity [[wiki/concepts/output-format]].
- **Commensurability by convention.** Thesis-scale committee sizes require
  rescaling protocol parameters (Snowman's `K`, `α_c`, and `β`, and the Casper FFG
  slot-to-delay coherence rule), so the cross-protocol verdicts rest on those
  conventions and are reported as robust only where they survive the governing
  sensitivity check [[wiki/concepts/metric-reconciliation]].
- **Three-family scope.** The comparative verdicts cover only the three protocols
  implemented, and the frontier is traced only over the regimes measured; a
  high-throughput regime outside that span is not represented, so the absence of a
  configuration that is at once cheap, fast, and resilient is a statement about the
  measured plane rather than the whole design space.
- **Snowman safety witnessed by bound.** Snowman's safety is reported through its
  analytical bound `ε ≤ (1 − α_c/K)^β` rather than a measured fork rate, so its
  safety standing is the weakest-witnessed of the three (§3.5)
  [[wiki/concepts/adversarial-degradation-metrics]].
- **Small-n rescaling.** The loss-resilience comparison of the two most resilient
  families at `n = 25` is a statistical tie, their confidence intervals overlapping
  on a reduced seed count (Chapter 5, Table 5.1), so the absence of a dominant
  family there is a non-rejection rather than a measured separation
  [[wiki/concepts/key-findings]].
- **Permanent-loss bound.** Packet loss is modeled as permanent per-message drop
  with no transport retransmission, so the loss-resilience curves are an upper
  bound on fragility rather than a model of a retransmitting transport
  [[wiki/concepts/key-findings]].
- **Leader-sparing coverage.** The sweep exercises the three generic capabilities
  of the adversary catalog and spares the view-0 primary, so the leader-disruption
  surface, plausibly the sharpest attack on the leader-based protocols, is
  catalogued but not measured, and PBFT's liveness standing is established only
  against adversaries that leave its leader honest [[wiki/concepts/adversary-model]].

## 6.3 Directions for further work

### 6.3.1 Production-optimized protocol variants

The communication-overhead comparison of §4.2.4 evaluates each protocol at the
message granularity of its original specification. Production deployments reduce
this cost through signature aggregation: the Ethereum beacon chain aggregates
committee attestations with BLS signatures, collapsing Casper FFG's per-epoch cost
from `O(n²)` to `O(n)` [8], and HotStuff achieves the analogous reduction for the
PBFT family through threshold-signature collection at the leader [5]
[[wiki/algorithms/pbft#communication-complexity]]. Because aggregation is a property
of a family's signature scheme rather than of an individual protocol, a faithful
extension holds the optimization level constant: it either models all
signature-based families at production granularity, or reports the as-specified
and aggregated regimes side by side. Otherwise the per-unit cost contrast that
answers RQ3 is misstated by a comparison of implementations at different
optimization levels.
An implementation plan for the Casper FFG side is recorded as a kickoff
specification in the project repository.

### 6.3.2 Further directions

Five directions remain open beyond §6.3.1. The first is a saturation-throughput
capacity model that drives each protocol to a measured ceiling, which would turn
the flat-goodput baseline into a peak-capacity comparison
[[wiki/concepts/output-format]]. The second is an adaptive-timeout enhancement,
exponential backoff with jitter calibrated to observed round-trip time, evaluated
against the baseline in a regime that stresses timeout calibration directly; the
steady-state sweeps reported here are not such a regime. The third is an empirical
witness of Snowman's analytical safety bound, obtained by driving the protocol at a
weakened confidence depth `ε` at which forks become observable
[[wiki/concepts/adversarial-degradation-metrics]]. The fourth is an extension of the
harness to a DAG-based family (Narwhal+Tusk), whose data-availability-withholding
adversary the present sweep does not cover and which would populate the
high-throughput corner the three-family frontier leaves unmeasured
[[wiki/concepts/adversary-model]]. The fifth is a repetition of the comparison at
larger validator sets and against a transport that models bandwidth and
retransmission, which would test how far the rankings survive outside the
simplifying assumptions that made the controlled comparison possible
[[wiki/concepts/network-model]].

## 6.4 Concluding remarks

The contribution of this thesis is a single harness in which representative
Layer-1 consensus protocols were subjected to the same delay and adversarial
conditions and measured against one schema, together with the comparative reading
it made possible: not a winner, but a map of which structural commitment places
each family where on the performance–security frontier. Because the same
structural choice that places a family on one corner is what exposes it on another,
this is a map of mechanisms rather than an artifact of the comparison set. The
incidents that opened this study (§1.2) — Ethereum's May 2023 finality stall [21]
and the Solana and Cosmos liveness halts — are read here not as interchangeable
faults to be engineered away by one better protocol, but as the separable
consequences of the choices a protocol makes.
