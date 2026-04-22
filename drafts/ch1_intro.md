# Chapter 1 — Introduction

## 1.1 Background

A **Layer-1 (L1) blockchain** is a replicated, append-only log of
transactions maintained across a set of mutually distrusting validators
[[wiki/concepts/consensus-overview#what-a-blockchain-is]]. At each height,
one new block must be produced, and every honest validator must agree on
which block it is. The step that makes that agreement happen — **consensus**
— is where the four protocol families evaluated in this thesis differ, and
it is what this thesis evaluates.

Consensus is hard for three connected reasons that every deployed protocol
has to answer. Some validators may be **Byzantine** — that is, arbitrary:
they may crash, lie, collude, or send conflicting messages to different
peers [1]. The network is not synchronous either: messages are delayed,
reordered, and dropped, and a validator cannot distinguish a slow peer from
an offline peer from a lying peer [3]. Under pure asynchrony, the FLP
impossibility result then proves that no deterministic protocol can
guarantee both **safety** (all honest validators agree on the same history)
and **liveness** (the protocol keeps making progress) with even one
crash-faulty process [2].

Every deployed L1 protocol relaxes one of these constraints. The four
families evaluated in this thesis — PBFT-style, PoS-finality,
Avalanche-style, and DAG-based — correspond to four different relaxations
[[wiki/concepts/consensus-families]].

## 1.2 Motivation

Layer-1 blockchains now hold real assets and settle real transactions. The
consensus protocol underneath them is what decides whether a transaction is
final, whether the chain keeps moving, and whether two honest validators
can ever end up holding conflicting histories. When that protocol works,
nobody notices. When it doesn't, the cost is borne by everyone using the
chain. Ethereum runs a PoS-finality protocol [8]; Sui runs a DAG-based
protocol [13]; Cosmos runs a PBFT-style protocol [6]; Avalanche mainnet
runs the Avalanche-style protocol it gave its name to [9]. The choice of
consensus family governs, in each case, availability and finality for the
users of the chain.

Most consensus protocols are analysed under ideal assumptions — honest
participants, stable networks, one variable stressed at a time. Real
Layer-1 networks offer none of that. Validators span continents, messages
arrive late or are lost, and some of the participants are slow, offline, or
hostile. The conditions that test a protocol hardest are exactly the ones
its original benchmarks never combine. Surveys [14] and methodological
critiques [16] identify this absence of comparable stress-condition
evaluation as the principal obstacle to honest cross-family comparison.

That gap would be only an academic concern if performance and security
stayed separate. They do not. Under delay and adversarial pressure, the two
become coupled: a protocol that merely *slows* under load may also miss
finality, fork, or let honest validators commit different blocks.
Benign-condition benchmarks never expose this coupling. This thesis is
motivated by that coupling — and by the limited availability, in the
current literature, of comparable cross-family evaluation under unified
stress conditions.

## 1.3 Problem statement

The working title of this thesis is *Performance–Security Evaluation of
Layer-1 Consensus Algorithms under Network Delay and Adversarial Conditions:
A Simulation-Based Comparative Study*
[[wiki/concepts/problem-statement#thesis-title]].[^1]

This thesis investigates the comparative performance–security behaviour of
four Layer-1 consensus families — PBFT-style [[wiki/algorithms/pbft]],
PoS-finality [[wiki/algorithms/pos]], Avalanche-style
[[wiki/algorithms/avalanche]], and DAG-based [[wiki/algorithms/dag-based]]
— under controlled network delay and adversarial conditions using a unified
simulation harness. Rather than benchmarking production systems directly,
it provides a reproducible cross-family evaluation framework in which
latency, throughput, communication cost, safety, and liveness can be
measured under matched assumptions.

In this thesis, **performance** refers to the observable cost of running
the protocol — commit latency, sustained throughput, and communication
overhead — and **security** refers to the preservation of the protocol's
two core correctness guarantees under adversarial pressure: *safety*,
measured as the absence of conflicting commits across honest validators
(fork rate and empirical safety-violation probability ε), and *liveness*,
measured as the fraction of rounds that reach commit and the frequency of
view-change or reorg events
[[wiki/concepts/evaluation-metrics#reliability-metrics]].

The contribution sits between two bodies of existing work. On one side, the
primary papers [4]–[13] report performance for individual protocols on
harness-specific conditions; their numbers are not directly comparable
across families, a limitation explicitly noted in the principal surveys
[14], [15]. On the other side, taxonomic surveys [14]–[16] position the
families qualitatively but do not measure them. This thesis contributes to
that middle layer by extending the simulation-based methodology of Gervais
*et al.* [17] — originally applied to Proof-of-Work — to BFT-style,
PoS-finality, Avalanche-style, and DAG-based protocols.

[^1]: The title is working, pending supervisor sign-off as part of the
Week 2 milestone.

## 1.4 Scope and assumptions

The thesis evaluates four Layer-1 consensus families at the message-passing
level inside a discrete-event simulator
[[wiki/concepts/problem-statement#scope]]. Within scope: configurable
network delay (constant, uniform, exponential, heavy-tailed), configurable
packet loss, four Byzantine validator behaviours (silent non-participation,
delayed voting, equivocation, selective dropping), and validator sets up to
a few hundred nodes. Out of scope: Proof-of-Work as a subject of comparison
(covered only as a methodological baseline [17]), Layer-2 protocols,
testnet or mainnet deployment, economic and incentive design, and
cryptographic primitive performance.

Four assumptions frame the results
[[wiki/concepts/problem-statement#assumptions-and-limitations]]. First,
the per-family implementations are deliberately simplified. Each protocol
is treated as a *family representative* for controlled comparative
experimentation, not as a complete proxy for every production variant in
that family; the aim is fair comparison across families, not matching any
specific production codebase's throughput. Second, the network model is
idealised — delay and loss are configurable, but TCP congestion control,
kernel scheduling, and physical-layer jitter are not modelled. Third, the
adversarial strategies evaluated are those documented in the primary
literature; attacks requiring specialised cryptographic or economic
modelling are left to future work. Fourth, literature-reported numbers are
treated as order-of-magnitude sanity checks, not as validation targets —
the simulator's contribution is internal consistency across families, not
matching production throughput.

Simulation, rather than testnet or live-network measurement, is the chosen
method for three reasons: reproducibility, controlled conditions, and a
matched harness across all four families. This is the same rationale that
motivated the PoW simulation framework of [17].

## 1.5 Research questions

Five research questions structure the empirical evaluation
[[wiki/concepts/research-questions]]. RQ1–RQ4 generate the data; RQ5
synthesises it.

- **RQ1.** How does end-to-end commit latency scale, for each of the four
  families, as network delay variance increases from nominal to
  heavy-tailed? *This tests the synchrony assumption each family makes.*
- **RQ2.** How does sustained throughput of each family degrade under
  increasing Byzantine fraction, below and approaching the theoretical
  threshold? *This tests how gracefully each family approaches its fault
  bound.*
- **RQ3.** What is the relative communication overhead of each family,
  measured in messages and bytes per block, under a fixed workload and
  identical network assumptions? *This exposes the different scaling
  exponents — `O(n²)` for PBFT, `O(n)` for DAG-based, per-validator `O(K·β)`
  independent of `n` for Avalanche — in a single measurement.*
- **RQ4.** Under which adversarial strategies (silent non-participation,
  delayed voting, equivocation, selective dropping) does each family
  experience liveness degradation, safety violations, or neither? *This
  maps adversarial behaviour to the properties each family claims to
  preserve.*
- **RQ5.** Is there a consistent Pareto frontier of the performance–security
  tradeoff across the four families, and does any family dominate across all
  operating regimes? *This is the comparative synthesis question and the
  headline contribution of the thesis.*

Each question pairs with a defined subset of the unified metric schema in
[[wiki/concepts/evaluation-metrics]] and with a defined independent
variable in the experimental matrix.

## 1.6 Contributions and thesis roadmap

The thesis makes four contributions
[[wiki/concepts/problem-statement#intended-contributions]]:

1. A discrete-event simulator for Layer-1 consensus evaluation under
   configurable network delay and adversarial conditions, with a shared
   metric schema and a pluggable protocol interface.
2. Simplified reference implementations of one protocol from each of the
   four families within a single harness, enabling reproducible like-for-like
   comparison.
3. An experimental dataset and comparative analysis quantifying the
   performance–security tradeoff across the four families under matched
   conditions, answering RQ1–RQ5.
4. A methodological extension of the simulation-based,
   metrics-instrumented evaluation approach of Gervais *et al.* [17] —
   originally applied to Proof-of-Work — to BFT-style, PoS-finality,
   Avalanche-style, and DAG-based protocols.

The remainder of the thesis is organised as follows. **Chapter 2** reviews
the literature on blockchain consensus families and prior comparative
evaluations. **Chapter 3** describes the methodology: the system model, the
four protocol implementations, the metric schema, and the experimental
design. **Chapter 4** presents the empirical results — baseline,
network-delay, and adversarial experiments — answering RQ1–RQ4.
**Chapter 5** presents the cross-family Pareto synthesis that answers RQ5,
and illustrates the simulator's design utility with one targeted
enhancement experiment (an adaptive timeout) compared against the baseline. **Chapter 6** concludes with the findings, their limitations, and
directions for further work.
