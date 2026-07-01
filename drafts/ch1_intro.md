# Chapter 1 — Introduction

## 1.1 Background

A Layer-1 (L1) blockchain maintains a replicated, append-only log of
transactions across a set of mutually distrusting validators
[[wiki/concepts/consensus-overview#what-a-blockchain-is]]. At each block
height the validator set must agree on a single block; the protocol that
produces that agreement is the consensus protocol.

Three foundational results bound any such protocol. Deterministic Byzantine
agreement requires `n ≥ 3f+1` replicas [1] [[wiki/concepts/byzantine-generals]].
Under pure asynchrony no deterministic protocol guarantees both safety and
liveness against even one crash fault, by the FLP impossibility [2]
[[wiki/concepts/flp-impossibility]]. Under partial synchrony consensus
becomes solvable for `f < n/3` [3] [[wiki/concepts/synchrony-models]]. Every
deployed L1 protocol sits at some point in the design space these results
define.

Three families occupy distinct points in
that space [[wiki/concepts/consensus-families]], each trading a different
cost for its guarantees:

- **PBFT-style** [4] [[wiki/algorithms/pbft]] — leader-driven multi-phase
  voting; deterministic finality at commit; cost: `O(n²)` messages, which
  bounds the validator-set size.
- **PoS-finality** [7], [8] [[wiki/algorithms/pos]] — a stake-weighted finality
  gadget over epoch checkpoints; deterministic finality; cost: finality
  latency on the order of minutes.
- **Avalanche-style** [9] [[wiki/algorithms/avalanche]] — repeated random
  subsampling; probabilistic finality with tunable confidence; cost: no
  deterministic safety.

How these mechanisms differ in operation is developed in Chapters 2 and 3;
quantifying the cost differences is the task of this thesis.

## 1.2 Motivation

In September 2021 the Solana mainnet stopped producing blocks for seventeen
hours after a flood of bot transactions overwhelmed the network [19]. The
halt was not an isolated event. Solana stalled again in April 2022 from
validator memory exhaustion compounded by insufficient finalization votes,
in February 2023 from block-propagation saturation, and in February 2024
from a five-hour finalization stall [19]. Ethereum, secured by a
PoS-finality protocol [8], experienced a seven-block reorganization in May
2022 and a multi-epoch finality stall in May 2023 driven by
attestation-processing pressure [20], [21]. The Cosmos Hub, secured by a
PBFT-style protocol [6], halted after its v17.1 upgrade in June 2024 [22].
Sui suffered a crash-loop network halt in November 2024 [23]. The Avalanche
mainnet runs the protocol from which its family takes its name [9].

These incidents do not invalidate the protocols' theoretical guarantees.
They demonstrate that the conditions under which those guarantees hold
(bounded delay, a sufficiently honest validator set) are routinely exited
in deployment. Isolating which condition triggers which failure requires
controlled measurement that live networks do not afford. The
primary literature does not supply it: each study fixes its own network
model, fault assumptions, and workload, and varies one disturbance at a
time [14], [16]. Live operation combines those disturbances. Validators are
geographically distributed; messages are delayed, reordered, and dropped;
and a fraction of the active set is, at any moment, slow, offline, or
adversarial.

Under those combined conditions, performance and security cease to be
independent. A protocol that only *slows* under load may also miss
finality, fork, or admit conflicting commits across honest validators. This
coupling is invisible to the benign-condition benchmarks each family publishes
[14], [16] [[wiki/concepts/problem-statement#the-gap]]. The motivation for this
thesis lies in that coupling, and in the absence of a unified harness in which
it can be measured across the three families on matched assumptions.

## 1.3 Problem statement

This thesis investigates the comparative performance–security behavior of
the three L1 consensus families — PBFT-style [[wiki/algorithms/pbft]],
PoS-finality [[wiki/algorithms/pos]], and Avalanche-style
[[wiki/algorithms/avalanche]] — under controlled network delay and
adversarial conditions, using a single discrete-event simulator. The
contribution is not a benchmark of production systems. It is a reproducible
cross-family evaluation framework in which the three families are measured
under matched assumptions. Performance is measured as commit latency,
sustained throughput, and communication overhead; security, as safety and
liveness under adversarial pressure. Chapter 3 defines the metric schema
common to both [[wiki/concepts/evaluation-metrics]]. The framework extends the
simulation-based, metrics-instrumented methodology of Gervais *et al.* [17],
first applied to Proof-of-Work, to the three implemented BFT families
[[wiki/concepts/problem-statement#intended-contributions]]. Each family traces
a Pareto frontier under matched conditions; whether any family dominates across
all operating regimes is answered from experimental data.

## 1.4 Scope and assumptions

Evaluation is conducted at the message-passing level inside a
discrete-event simulator [[wiki/concepts/problem-statement#scope]]. In scope
are configurable network delay (constant, uniform, normal, exponential,
heavy-tailed), configurable packet loss, three Byzantine validator
behaviors drawn from the primary literature — silent non-participation,
delayed voting, and equivocation [[wiki/concepts/adversary-model]] — and
validator sets of n ∈ {4, 7, 10, 16, 25} nodes. Extrapolation to the
several-hundred-node production scale rests on the sensitivity sweeps rather
than on direct measurement at that scale. Out of scope are Proof-of-Work
as a subject of comparison (it appears only as the methodological precedent
[17]), Layer-2 protocols, deployment on testnet or mainnet, economic and
incentive design, and the performance of cryptographic primitives.

Simulation is chosen over testnet or live-network measurement for
reproducibility of seeded runs, controlled isolation of one variable at a time,
and a matched harness across the three families. The choice carries four framing
assumptions [[wiki/concepts/problem-statement#assumptions-and-limitations]]: each
family is a deliberately simplified implementation (the aim is fair like-for-like
comparison, not reproduction of a production codebase's throughput); the network is
idealized (delay and loss are configurable, but TCP congestion control, kernel
scheduling, and physical-layer jitter are not modeled); the adversarial strategies
are those most discussed in the primary literature, attacks needing specialized
cryptographic or economic modeling being left to future work; and published
production figures are treated as order-of-magnitude sanity checks, not validation
targets — the simulator's contribution is internal consistency across families
under matched assumptions, not the reproduction of production throughput.

The three protocols are representatives chosen to occupy separable regions of
this design space. PBFT is the reference construction for the PBFT-style family:
leader-driven quorum voting with deterministic single-slot finality, from which
later partially synchronous protocols such as Tendermint and HotStuff inherit
their two-thirds quorum structure [[wiki/algorithms/pbft]]. Casper FFG stands for
the PoS-finality family, where a stake-weighted finality gadget finalizes epoch
checkpoints rather than individual blocks and renders a safety violation
attributable to specific validators through slashing [[wiki/algorithms/pos]].
Snowman stands for the Avalanche-style family, reaching agreement by repeated
random subsampling and offering probabilistic finality in place of a
deterministic commit [[wiki/algorithms/avalanche]]. The three differ on exactly
the axes the evaluation measures: the finality mechanism, the communication
structure that sets message cost, and whether a safety failure is accountable.
That separation is what makes the cross-family comparison informative, rather
than a contrast between near-identical designs
[[wiki/concepts/consensus-families]].

Selecting one representative per family, rather than several protocols drawn
from a single family, keeps every protocol inside one simulator and one metric
schema while still spanning the range of finality guarantees from deterministic
to probabilistic. A different representative of the same family would exercise
the same design axes; substituting HotStuff or Tendermint for PBFT, for
instance, would test the same deterministic quorum-voting regime and leave the
family-level tradeoff under study unchanged.

## 1.5 Research questions

Five research questions structure the evaluation
[[wiki/concepts/research-questions]]. RQ1–RQ4 generate the data; RQ5
synthesizes it.

- **RQ1.** How does end-to-end commit latency scale, for each family, as
  the variance of the network-delay distribution increases from nominal to
  heavy-tailed? This tests the synchrony assumption each family makes.
- **RQ2.** How does sustained throughput degrade, for each family, as the
  Byzantine fraction approaches the theoretical fault threshold from below?
  This describes how each family approaches its fault bound, not only
  whether it reaches it.
- **RQ3.** What is the relative communication overhead of each family,
  measured in messages per agreed unit, under a fixed workload and
  identical network assumptions? This quantifies the asymptotic scaling each
  family claims.
- **RQ4.** Under which adversarial strategies — silent non-participation,
  delayed voting, equivocation — does each family show liveness
  degradation, safety violation, or neither? This maps each adversary onto
  the property each family claims to preserve.
- **RQ5.** Does a consistent Pareto frontier of the performance–security
  tradeoff exist across the three families evaluated, and does any family
  dominate across all operating regimes? This is the comparative synthesis
  and the primary contribution.

Each question is paired with a defined subset of the metric schema
[[wiki/concepts/evaluation-metrics]] and a defined independent variable in
the experiment matrix [[wiki/concepts/experiment-matrix]].

## 1.6 Contributions and thesis roadmap

The thesis makes four contributions
[[wiki/concepts/problem-statement#intended-contributions]]:

1. **Artifact.** A discrete-event simulator for L1 consensus evaluation
   under configurable network delay and adversarial conditions, with a
   shared metric schema and a pluggable protocol interface.
2. **Implementations.** Simplified reference implementations of one
   representative protocol from each of the three families within a single
   harness — PBFT-style, PoS-finality, and Avalanche-style — enabling
   reproducible like-for-like comparison.
3. **Dataset and analysis.** An experimental dataset and comparative
   analysis quantifying the performance–security tradeoff across the three
   implemented families under matched conditions, answering RQ1–RQ4 and
   supporting the RQ5 synthesis over those three.
4. **Methodological framing.** The simulation-based, metrics-instrumented
   approach of Gervais *et al.* [17], extended from Proof-of-Work to the
   three implemented BFT families on a single harness with matched assumptions.

Chapter 2 reviews the three families and the prior comparative evaluations
that motivate a unified harness. Chapter 3 describes the methodology: the
system model, the three protocol implementations, the metric schema, and the
experimental design. Chapter 4 presents the baseline, network-delay, and
adversarial results that answer RQ1–RQ4. Chapter 5 presents the
cross-family Pareto synthesis that answers RQ5. Chapter 6 concludes with
the findings, their limitations, and directions for further work.
