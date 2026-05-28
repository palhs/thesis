# Chapter 1 — Introduction

## 1.1 Background

A Layer-1 (L1) blockchain maintains a replicated, append-only log of
transactions across a set of mutually distrusting validators
[[wiki/concepts/consensus-overview#what-a-blockchain-is]]. Such systems
are typically evaluated on two largely separate axes — throughput in
their whitepapers and safety bounds in their proofs — but under network
delay and adversarial pressure the two axes cease to be independent. At
each height the validator set must agree on a single block; the protocol
that produces that agreement is the consensus protocol, and the four
families evaluated in this thesis differ in how they produce it.

Three foundational results bound what any such protocol can achieve.
The Byzantine Generals Problem [1] establishes that deterministic agreement
among `n` processes tolerating `f` arbitrarily-faulty participants requires
`n ≥ 3f+1` [[wiki/concepts/byzantine-generals]]. The Fischer–Lynch–Paterson
impossibility [2] establishes that, under pure asynchrony, no deterministic
protocol guarantees both safety and liveness in the presence of even one
crash fault [[wiki/concepts/flp-impossibility]]. Dwork, Lynch and Stockmeyer
[3] supply the most influential relaxation: under partial synchrony,
consensus is solvable for `f < n/3` [[wiki/concepts/synchrony-models]].
Together these results define the design space in which every deployed L1
protocol must sit.

The four families evaluated in this thesis correspond to four distinct
points in that design space [[wiki/concepts/consensus-families]]:
PBFT-style [[wiki/algorithms/pbft]], PoS-finality
[[wiki/algorithms/pos]], Avalanche-style [[wiki/algorithms/avalanche]],
and DAG-based [[wiki/algorithms/dag-based]]. Each family selects
a different combination of synchrony assumption, fault threshold, and
finality regime; each pays a different primary cost.

PBFT-style protocols reach agreement through leader-driven, multi-phase
voting among a fixed validator set, delivering deterministic finality at
commit time at the cost of `O(n²)` message complexity that bounds the
practical validator-set size. PoS-finality protocols separate block
production from a stake-weighted finality gadget that confirms checkpoints
across epochs, achieving deterministic finality at the cost of finality
latency on the order of minutes. Avalanche-style protocols reach agreement
through repeated random subsampling and metastable voting, achieving
probabilistic finality with tunable confidence at the cost of giving up
deterministic safety. DAG-based protocols decouple message dissemination
from ordering by having validators continuously reference earlier vertices
in a directed acyclic graph, achieving high throughput under good
conditions at the cost of additional ordering-layer complexity and a
higher per-validator memory footprint.

## 1.2 Motivation

Layer-1 blockchains provide the settlement guarantees on which their
users depend: the consensus protocol determines whether a transaction is
final, whether the chain continues to advance, and whether two honest
validators can ever commit incompatible histories at the same height
[[wiki/concepts/consensus-overview#why-consensus-is-needed]]. The choice of
family is important in production. Ethereum is secured by a PoS-finality
protocol [8]; Sui is secured by a DAG-based protocol [13]; Cosmos chains
are secured by a PBFT-style protocol [6]; the Avalanche mainnet is secured
by the Avalanche-style protocol from which the family takes its name [9].

These protocols have demonstrably exited their operating envelopes in
production. Solana's mainnet has halted on multiple occasions — most
visibly in September 2021 (a 17-hour stall under a flood of bot
transactions), April 2022 (a 7-hour halt from validator memory exhaustion
compounded by insufficient finalization votes), February 2023
(block-propagation saturation in the Turbine layer), and February 2024
(a 5-hour finalization stall) [18]. Ethereum's beacon chain experienced
a 7-block reorganization in May 2022, attributed to a late block proposal
that split validator views around the proposer-boost fork-choice rule
[19], and a multi-epoch finality stall in May 2023 caused by
attestation-processing pressure on consensus clients [20]. Cosmos Hub
halted following its v17.1 upgrade in June 2024 [21]; Sui suffered a
complete crash-loop network halt in November 2024 and a six-hour
consensus divergence in January 2026 traced to an edge-case bug in
commit processing [22]. These incidents do not invalidate the protocols'
theoretical guarantees — they demonstrate that the conditions under which
those guarantees hold are routinely exited in deployment. Isolating which
condition triggers which failure, however, requires controlled measurement
that live networks do not afford.

The primary literature evaluates each protocol under scattered,
harness-specific conditions: each study fixes its own network model, fault
assumptions, and workload, and varies one disturbance at a time. Live operation
combines those disturbances rather than isolating them.
Validators are geographically distributed; messages are delayed, reordered,
and dropped; a sizable fraction of the active set is, at any given
moment, slow, offline, or adversarial. The conditions under which a
consensus protocol is tested most severely are exactly the conditions its
publication benchmarks do not combine. Both the canonical taxonomic survey
[14] and the methodological critique of Cachin and Vukolić [16] identify
the absence of comparable stress-condition evaluation as the main
obstacle to honest cross-family comparison. Combining those disturbances
is exactly the condition under which performance and security cease to
be independent variables.

The gap would be of academic interest only if performance and security
remained separate. They do not. Under combined network delay and
adversarial pressure the two become linked: a protocol that only
*slows* under load may also miss finality, fork, or allow conflicting
commits across honest validators. The performance–security coupling is
invisible to benign-condition benchmarks. This thesis is motivated by that
coupling, and by the absence of a unified harness in which it can be
measured across the four families on matched assumptions
[[wiki/concepts/problem-statement#the-gap]].

## 1.3 Problem statement

This thesis investigates the comparative performance–security behavior of
the four Layer-1 consensus families — PBFT-style [[wiki/algorithms/pbft]],
PoS-finality [[wiki/algorithms/pos]], Avalanche-style
[[wiki/algorithms/avalanche]], and DAG-based [[wiki/algorithms/dag-based]]
— under controlled network delay and adversarial conditions, using a
unified discrete-event simulator. The contribution is not a benchmark of
production systems; it is a reproducible cross-family evaluation framework
in which latency, throughput, communication cost, and the safety and
liveness response to adversarial pressure are measured under matched
assumptions [[wiki/concepts/problem-statement#thesis-contribution]].
Performance is measured as commit latency, sustained throughput, and
communication overhead; security as safety and liveness under adversarial
pressure. The unified metric schema is defined in Chapter 3
[[wiki/concepts/evaluation-metrics]] [[wiki/concepts/metric-reconciliation]].

Concretely, this thesis extends the simulation-based,
metrics-instrumented methodology of Gervais *et al.* [17], originally
applied to Proof-of-Work, to PBFT-style, PoS-finality, Avalanche-style,
and DAG-based protocols
[[wiki/concepts/problem-statement#intended-contributions]]. The comparison
is organized around the Pareto frontier of the performance–security
tradeoff that each family traces under matched conditions, so that the
question of whether any family dominates across all operating regimes can
be answered from data rather than claimed from theory.

## 1.4 Scope and assumptions

Evaluation is conducted at the message-passing level inside a
discrete-event simulator [[wiki/concepts/problem-statement#scope]].

Within scope are configurable network delay (constant, uniform,
exponential, heavy-tailed); configurable packet loss; three Byzantine
validator behaviors representative of those discussed in the primary
literature, namely silent non-participation, delayed voting, and
equivocation [[wiki/concepts/adversary-model]]; and validator
sets up to several hundred nodes.

Out of scope are Proof-of-Work as a subject of comparison (it appears
only as a methodological precedent through [17]); Layer-2 protocols;
deployment on testnet or mainnet; economic and incentive design; and the
performance of cryptographic primitives.

Four assumptions frame the results
[[wiki/concepts/problem-statement#assumptions-and-limitations]]. First,
each family is represented by a deliberately simplified implementation; the
simplification is intentional, since the aim is fair like-for-like
comparison across families rather than the reproduction of any particular
production codebase's throughput. Second, the network is idealized: delay
and loss are configurable parameters, but TCP congestion control, kernel
scheduling, and physical-layer jitter are not modeled. The abstraction
level matches that of prior simulation studies of consensus. Third, the adversarial
strategies evaluated are those most frequently discussed in the primary
literature; attacks requiring specialized cryptographic or economic
modeling are left to future work. Fourth, literature-reported figures
are treated as order-of-magnitude sanity checks rather than as validation
targets; the simulator's contribution is internal consistency across
families under matched assumptions, not the reproduction of production
throughput.

Simulation is chosen over testnet or live-network measurement for three
reasons: reproducibility of seeded runs, the controlled isolation of one
independent variable at a time, and a matched harness across all four
families.

## 1.5 Research questions

Five research questions structure the empirical evaluation
[[wiki/concepts/research-questions]]. RQ1–RQ4 generate the data; RQ5
synthesizes it.

- **RQ1.** How does end-to-end commit latency scale, for each of the four
  families, as the variance of the network-delay distribution increases
  from nominal to heavy-tailed? *The question tests the synchrony
  assumption each family makes.*
- **RQ2.** How does sustained throughput degrade, for each family, as the
  Byzantine fraction approaches the theoretical fault threshold from
  below? *The question describes how each family
  approaches its fault bound, not only whether it reaches it.*
- **RQ3.** What is the relative communication overhead of each family,
  measured in messages and bytes per agreed unit, under a fixed workload
  and identical network assumptions? *The question quantifies the
  asymptotic scaling each family claims, in a single measurement.*
- **RQ4.** Under which adversarial strategies (silent non-participation,
  delayed voting, equivocation) does each family show liveness
  degradation, safety violation, or neither? *The question maps each
  adversary onto the property each family claims to preserve.*
- **RQ5.** Does a consistent Pareto frontier of the performance–security
  tradeoff exist across the four families, and does any family dominate
  across all operating regimes? *The question is the comparative synthesis
  and the headline contribution.*

Each question is paired with a defined subset of the unified metric schema
in [[wiki/concepts/evaluation-metrics]] and with a defined independent
variable in the experiment matrix [[wiki/concepts/experiment-matrix]].

## 1.6 Contributions and thesis roadmap

The thesis makes four contributions
[[wiki/concepts/problem-statement#intended-contributions]]:

1. **Artifact.** A discrete-event simulator for Layer-1 consensus
   evaluation under configurable network delay and adversarial conditions,
   with a shared metric schema and a pluggable protocol interface.
2. **Implementations.** Simplified reference implementations of one
   protocol from each of the four families within a single harness, so
   that reproducible like-for-like comparison is possible.
3. **Dataset and analysis.** An experimental dataset and comparative
   analysis quantifying the performance–security tradeoff across the four
   families under matched conditions, answering RQ1–RQ4 and underwriting
   the RQ5 synthesis.
4. **Methodological framing.** The simulation-based,
   metrics-instrumented evaluation approach of Gervais *et al.* [17],
   originally applied to Proof-of-Work, is here extended to PBFT-style,
   PoS-finality, Avalanche-style, and DAG-based protocols on a single
   harness with matched assumptions.

The remainder of the thesis is organized as follows. **Chapter 2** reviews
the literature on Layer-1 consensus families and prior comparative
evaluations. **Chapter 3** describes the methodology: the system model, the
four protocol implementations, the metric schema, and the experimental
design. **Chapter 4** presents the empirical results — baseline,
network-delay, and adversarial experiments — answering RQ1–RQ4.
**Chapter 5** presents the cross-family Pareto synthesis that answers RQ5
and demonstrates the simulator's utility for protocol-level experimentation
through a targeted enhancement (an adaptive timeout) compared against the
baseline.
**Chapter 6** concludes with the findings, their limitations, and
directions for further work.
