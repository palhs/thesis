# Chapter 1 — Introduction

## 1.1 Background

A Layer-1 (L1) blockchain maintains a replicated, append-only log of
transactions across a set of mutually distrusting validators
[[wiki/concepts/consensus-overview#what-a-blockchain-is]]. At each height
the validator set must agree on a single block; the protocol that produces
that agreement is the consensus protocol, and the four families evaluated
in this thesis differ in how they produce it.

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
obstacle to honest cross-family comparison.

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

The working title is *Performance–Security Evaluation of Layer-1 Consensus
Algorithms under Network Delay and Adversarial Conditions: A
Simulation-Based Comparative Study*
[[wiki/concepts/problem-statement#thesis-title]].[^1]

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

Two operational definitions follow the metric schema of
[[wiki/concepts/evaluation-metrics]]. *Performance* denotes the observable
cost of executing the protocol: commit latency, sustained throughput, and
communication overhead in messages and bytes per agreed unit. *Security*
denotes whether the protocol still holds its two correctness properties
under adversarial pressure: *safety*, measured as the absence of conflicting
commits across honest validators (fork rate and empirical safety-violation
probability `ε`), and *liveness*, measured as the fraction of rounds
reaching commit together with the frequency of view-change or reorg events
[[wiki/concepts/evaluation-metrics#reliability-metrics]]. The matching
of these definitions across the linear-chain, epoch-based,
probabilistic-finality, and DAG-anchored output structures of the four
families is set out in [[wiki/concepts/metric-reconciliation]].

The contribution sits between two existing bodies of work. On one
side, the primary papers [4]–[13] report performance for individual
protocols under harness-specific conditions; the main surveys [14],
[15] explicitly note that those numbers do not cross family boundaries. On
the other side, the taxonomic surveys [14]–[16] place the families in
qualitative terms but do not measure them. This thesis sits in the middle
layer by extending the simulation-based, metrics-instrumented methodology
of Gervais *et al.* [17], originally applied to Proof-of-Work, to
PBFT-style, PoS-finality, Avalanche-style, and DAG-based protocols
[[wiki/concepts/problem-statement#intended-contributions]]. The comparison
is organized around the Pareto frontier of the performance–security
tradeoff that each family traces under matched conditions, so that the
question of whether any family dominates across all operating regimes can
be asked from data rather than claimed.

[^1]: The title is working, pending supervisor sign-off as part of the
Week 2 milestone (see [[wiki/concepts/problem-statement#status]]).

## 1.4 Scope and assumptions

Evaluation is conducted at the message-passing level inside a
discrete-event simulator [[wiki/concepts/problem-statement#scope]]. Within
scope: configurable network delay (constant, uniform, exponential,
heavy-tailed); configurable packet loss; the four Byzantine validator
behaviors documented in the primary literature, namely silent
non-participation, delayed voting, equivocation, and selective dropping
[[wiki/concepts/adversary-model]]; and validator sets up to several
hundred nodes. Out of scope: Proof-of-Work as a subject of comparison
(it appears only as a methodological precedent through [17]); Layer-2
protocols; deployment on testnet or mainnet; economic and incentive design;
and the performance of cryptographic primitives.

Four assumptions frame the results
[[wiki/concepts/problem-statement#assumptions-and-limitations]]. First,
each family is represented by a deliberately simplified implementation; the
simplification is intentional, since the aim is fair like-for-like
comparison across families rather than the reproduction of any particular
production codebase's throughput. Second, the network is idealized: delay
and loss are configurable parameters, but TCP congestion control, kernel
scheduling, and physical-layer jitter are not modeled. The abstraction
level matches that of prior simulation studies [17]. Third, the adversarial
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
families. This is the same reasoning behind the unified
Proof-of-Work simulator of Gervais *et al.* [17].

## 1.5 Research questions

Five research questions structure the empirical evaluation
[[wiki/concepts/research-questions]]. RQ1–RQ4 generate the data; RQ5
synthesizes it.

- **RQ1.** How does end-to-end commit latency scale, for each of the four
  families, as the variance of the network-delay distribution increases
  from nominal to heavy-tailed? *The question tests the synchrony
  assumption each family makes.*
- **RQ2.** How does sustained throughput degrade, for each family, as the
  Byzantine fraction increases below and toward the theoretical fault
  threshold? *The question describes how each family
  approaches its fault bound, not only whether it reaches it.*
- **RQ3.** What is the relative communication overhead of each family,
  measured in messages and bytes per agreed unit, under a fixed workload
  and identical network assumptions? *The question shows the different
  scaling exponents (`O(n²)` for PBFT, `O(n)` for DAG-based, per-validator
  `O(K·β)` independent of `n` for Avalanche) in a single measurement.*
- **RQ4.** Under which adversarial strategies (silent non-participation,
  delayed voting, equivocation, selective dropping) does each family
  show liveness degradation, safety violation, or neither? *The question
  maps each adversary onto the property each family claims to preserve.*
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

1. A discrete-event simulator for Layer-1 consensus evaluation under
   configurable network delay and adversarial conditions, with a shared
   metric schema and a pluggable protocol interface.
2. Simplified reference implementations of one protocol from each of the
   four families within a single harness, so that reproducible
   like-for-like comparison is possible.
3. An experimental dataset and comparative analysis quantifying the
   performance–security tradeoff across the four families under matched
   conditions, answering RQ1–RQ5.
4. A methodological extension of the simulation-based,
   metrics-instrumented evaluation approach of Gervais *et al.* [17],
   which they originally applied to Proof-of-Work, to PBFT-style,
   PoS-finality, Avalanche-style, and DAG-based protocols.

The remainder of the thesis is organized as follows. **Chapter 2** reviews
the literature on Layer-1 consensus families and prior comparative
evaluations. **Chapter 3** describes the methodology: the system model, the
four protocol implementations, the metric schema, and the experimental
design. **Chapter 4** presents the empirical results — baseline,
network-delay, and adversarial experiments — answering RQ1–RQ4.
**Chapter 5** presents the cross-family Pareto synthesis that answers RQ5
and shows the simulator's design value through a targeted enhancement
experiment (an adaptive timeout) compared against the baseline.
**Chapter 6** concludes with the findings, their limitations, and
directions for further work.
