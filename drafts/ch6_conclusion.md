# Chapter 6 — Conclusions

## 6.1 Summary of findings

This thesis measured, on matched assumptions and in a single harness, how three
representative Layer-1 consensus protocols, as implemented here — classical all-to-all
PBFT, the Casper FFG finality gadget without its LMD-GHOST fork-choice, and a
linearized small-`n` Snowman — behave under the network and adversarial conditions
their guarantees assume away. Table 6.1 collects the answers to the five research
questions; each is a claim about the representative implementation evaluated, not about
its whole protocol family. Each answer is set by a structural choice rather than by the
fault fraction alone, and no protocol is robust to every adversary because each
structural defense is also an exposure.

**Table 6.1 — The five research questions and their answers over the three protocols
evaluated.** Source: [[wiki/concepts/research-questions]], [[wiki/concepts/key-findings]].

| RQ | Question | Answer | Governing mechanism |
| :-- | :-- | :-- | :-- |
| RQ1 | latency under rising network-delay variance | flat in `n`; finality slows least for Casper FFG (×1.3, slot-bound), then PBFT (×1.9), then Snowman (×12–13) | round structure vs. `β` sequential polls |
| RQ2 | sustained throughput as `φ` rises to the threshold | three modes: PBFT holds then cliffs, Casper FFG ≈ `1 − φ`, Snowman starves earliest | quorum structure |
| RQ3 | communication overhead per committed unit | PBFT ≈ `2n`, Casper FFG ≈ `1.2n` (cheapest), Snowman ≈ `2Kβ` (≈ 14× PBFT at `n = 16`) | all-to-all / attestation vs. `K`-poll |
| RQ4 | which adversary causes liveness or safety loss | no protocol robust to all three; only PBFT's fork is measured, Snowman's safety rests on an unwitnessed analytical bound, Casper FFG alone is accountable by construction | each structural defense is also an exposure; safety differs in kind, not rank |
| RQ5 | consistent Pareto frontier; any dominance | a frontier exists; no family dominates across the measured axes plus the definitional safety ones | each family non-dominated on ≥ 1 axis |

## 6.2 Limitations

The findings hold within boundaries the methodology fixed; the deliberate exclusions
introduced in Chapter 3 are collected here in full.

- **Cost model.** The simulator charges network latency but no signature-verification,
  execution, or bandwidth cost. This flatters the cost and per-validator verdicts for
  the compute-bound equivocation handling of PBFT and Casper FFG; it does not bear on
  the message-count, liveness, or safety results. Communication overhead is reported as
  message count per agreed unit only; the byte-per-unit figure the harness also computes
  is payload-dominated at the synthetic workload — it tracks transaction payload
  amortized over committed units rather than protocol message structure — so the
  asymptotic-scaling contrast RQ3 examines is read from the message-count axis.
- **Synthetic workload, no capacity model.** Goodput is reported against a Poisson
  stream of fixed-size transactions at a zero conflict rate, below saturation — so the
  flat-in-`n` goodput is a property of the unsaturated model rather than a claim about
  peak capacity, and real-traffic burstiness and conflict-driven reorganization lie
  outside the measured range.
- **Commensurability by convention.** Thesis-scale committee sizes require rescaling
  protocol parameters (Snowman's `K`, `α_c`, `β`, and the Casper FFG slot-to-delay
  coherence rule), so the cross-protocol verdicts rest on those conventions and are
  reported robust only where they survive the governing sensitivity check.
- **Sub-production scale, and a collapsed subsample for Snowman.** The sweep
  `n ∈ {4, …, 25}` sits well below the deployed scale, Snowman's in particular: the
  rescaling `K = min(20, n−1)` sets `K ≈ n`, so at `n = 10` it samples 9 of 10 peers
  and is barely *subsampling*. Avalanche-style security is asymptotic in the sampled
  population, so at small `n` the distinguishing mechanism is largely collapsed, and
  Snowman's measured delay, loss, and silence fragility may be partly a small-`n`
  artifact rather than a property of the family at scale.
- **Family-vs-protocol generalization.** Each verdict is established for one
  representative implementation and does not transfer automatically to the rest of its
  family. A family-mate with a different structural choice can invert a verdict —
  HotStuff replaces PBFT's all-to-all round with a leader-collected threshold-signature
  pipeline that lowers overhead from `O(n²)` to `O(n)`, so PBFT's RQ3 cost standing is a
  property of the classical construction measured here, not of the leader-based family
  as such [[wiki/algorithms/pbft#communication-complexity]].
- **Snowman safety witnessed by bound.** Snowman's safety is reported through its
  analytical bound `ε ≤ (1 − α_c/K)^β` rather than a measured fork rate, so its safety
  standing is the weakest-witnessed of the three. The `n = 25` loss-resilience tie with
  PBFT likewise rests on overlapping confidence intervals at a reduced seed count, so
  the absence of a dominant family there is a non-rejection, not a measured separation.
- **Permanent-loss bound.** Packet loss is modeled as permanent per-message drop with
  no transport retransmission, so the loss-resilience curves are an upper bound on
  fragility rather than a model of a retransmitting transport.
- **Leader-sparing coverage.** The sweep exercises the three generic capabilities of
  the adversary catalog and spares the view-0 primary, so the leader-disruption surface
  — plausibly the sharpest attack on the leader-based protocols — is catalogued but not
  measured, and PBFT's liveness standing is established only against adversaries that
  leave its leader honest.

## 6.3 Directions for further work

### 6.3.1 Production-optimized protocol variants

The communication-overhead comparison of §4.2 evaluates each protocol at the message
granularity of its original specification. Production deployments reduce this cost
through signature aggregation: the Ethereum beacon chain aggregates committee
attestations with BLS signatures, collapsing Casper FFG's per-epoch cost from `O(n²)`
to `O(n)` [8], and HotStuff achieves the analogous reduction for the PBFT family
through threshold-signature collection at the leader [5]. Because aggregation is a
property of a family's signature scheme rather than of an individual protocol, a
faithful extension holds the optimization level constant — modeling all signature-based
families at production granularity, or reporting the as-specified and aggregated regimes
side by side — otherwise the per-unit cost contrast that answers RQ3 is misstated by a
comparison of implementations at different optimization levels. An implementation plan
for the Casper FFG side is recorded as a kickoff specification in the project repository.

### 6.3.2 Further directions

Five directions remain open beyond §6.3.1. The first is a saturation-throughput capacity
model that drives each protocol to a measured ceiling, turning the flat-goodput baseline
into a peak-capacity comparison. The second is an adaptive-timeout enhancement —
exponential backoff with jitter calibrated to observed round-trip time — evaluated in a
regime that stresses timeout calibration directly, which the steady-state sweeps here are
not. The third is an empirical witness of Snowman's analytical safety bound, obtained by
driving the protocol at a weakened confidence depth at which forks become observable. The
fourth is an extension of the harness to a DAG-based family (Narwhal+Tusk), whose
data-availability-withholding adversary the present sweep does not cover and which would
populate the high-throughput corner the three-family frontier leaves unmeasured. The
fifth is a repetition at larger validator sets and against a transport that models
bandwidth and retransmission, which would test how far the rankings survive outside the
simplifying assumptions that made the controlled comparison possible.

## 6.4 Concluding remarks

This thesis contributes a single harness in which representative Layer-1 consensus
protocols were subjected to the same delay and adversarial conditions and measured
against one schema, and the comparative reading that harness made possible: not a
winner, but a map of which structural commitment places each representative
implementation where on the performance–security frontier. No one of the three
dominates — a verdict resting on the measured axes plus two safety axes that are
definitional rather than measured (§5.3). Because the same structural choice that places
a family on one corner is what exposes it on another, the map records mechanisms rather
than an artifact of the comparison set. The incidents that opened this study (§1.2) —
Ethereum's May 2023 finality stall [21] and the Solana and Cosmos liveness halts — are
read here not as interchangeable faults to be engineered away by one better protocol,
but as the separable consequences of the choices a protocol makes.
