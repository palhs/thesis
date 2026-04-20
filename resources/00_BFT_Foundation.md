*Phase 1 — Foundation Document*

**The Byzantine Fault Tolerance Problem**

*A Unifying Lens for Layer-1 Consensus Algorithms*

Companion document for: Performance–Security Evaluation of Layer-1 Consensus Algorithms under Network Delay and Adversarial Conditions: A Simulation-Based Comparative Study

# **Purpose of this Document**

This document establishes the Byzantine Fault Tolerance (BFT) problem as the unifying lens through which every consensus family studied in this thesis — PBFT-style, Proof-of-Stake finality, Avalanche-style probabilistic, and DAG-based — is analysed. Each family can be read as a distinct design response to the same fundamental question: how can a set of distributed validators, some of which may be arbitrarily malicious, reach durable agreement on an ordered sequence of transactions despite an unreliable network?

Framing the four families as propagations of the BFT problem provides three concrete benefits for this thesis. First, it yields a common vocabulary for describing safety, liveness, synchrony assumptions, and fault thresholds, which in turn enables an apples-to-apples comparison. Second, it makes each algorithm’s assumptions and tradeoffs visible — what each family concedes in order to gain what it gains. Third, it directly drives the simulator design: if the simulator can vary (i) network synchrony, (ii) message delay distribution, and (iii) adversarial validator behaviour, then every family becomes a fair test subject under a shared experimental harness.

# **1\. The Byzantine Generals Problem**

Lamport, Shostak and Pease formalised the Byzantine Generals Problem (BGP) in 1982 as an abstraction for distributed agreement under arbitrary faults. Generals of a besieged city must coordinate on a single plan — attack or retreat — by sending messengers across enemy territory. Some generals, or their messengers, may be traitors who say anything to disrupt consensus. The problem is to design a protocol such that all loyal generals reach the same decision and, if the commanding general is loyal, that decision is the one the commander ordered.

Two properties must hold simultaneously. Agreement requires that all non-faulty participants decide the same value. Validity requires that, when the proposer is non-faulty, the agreed value equals the proposed value. The classical result is that BGP is solvable with deterministic protocols if and only if at most f out of n participants are faulty and n ≥ 3f \+ 1, and that protocols require at least f \+ 1 rounds of communication in the worst case. The 3f+1 bound recurs throughout modern blockchain consensus; it is the reason Tendermint, PBFT, HotStuff and Casper FFG all fix a two-thirds supermajority as their quorum threshold.

# **2\. Foundational Impossibility Results**

## **2.1 FLP Impossibility**

The FLP impossibility result established that no deterministic protocol can guarantee agreement in an asynchronous network with even a single crash-faulty process. The intuition is that an asynchronous adversary can always delay one message long enough that any decision is premature; thus safety and liveness cannot both be guaranteed under pure asynchrony. Every practical consensus algorithm therefore relaxes one of FLP’s assumptions: it assumes partial synchrony (PBFT, Tendermint, HotStuff), uses randomisation to circumvent the determinism clause (Avalanche, Algorand), or separates the agreement problem into a deterministically-solvable sub-problem layered on top of a reliably-broadcast mempool (Narwhal/Tusk, Bullshark, Mysticeti).

## **2.2 CAP Theorem**

Brewer’s CAP theorem states that a networked system cannot simultaneously provide Consistency, Availability, and Partition-tolerance. Blockchain systems operate over the public internet, where partitions are inevitable, so the choice is between consistency (safety-favouring) and availability (liveness-favouring). PBFT-style and PoS-finality systems sacrifice availability during partitions — blocks stop finalising until a quorum is restored — while Avalanche and probabilistic protocols lean toward availability, accepting temporary inconsistency that resolves as the network heals.

# **3\. Formal Properties of a Consensus Protocol**

Before any protocol can be compared, the properties it is expected to guarantee must be stated precisely. The literature converges on four:

* Agreement (safety). No two non-faulty validators commit conflicting values at the same height.

* Validity. Any committed value was proposed by some validator, and, stronger, was proposed by a non-faulty validator when one exists.

* Termination (liveness). Every non-faulty validator eventually commits a value at every height.

* Integrity. No validator commits the same value twice, and committed history is immutable.

Safety and liveness are often in tension. A protocol that is conservative about committing (good for safety) risks stalling under delay (bad for liveness). Whether a given family prioritises one over the other in the worst case is one of the axes this thesis evaluates empirically.

# **4\. Network Synchrony Models**

Synchrony assumptions govern what a protocol may assume about message delivery. They are the single most important knob in comparing consensus algorithms because they determine what the network can do to the protocol in the worst case. The partial-synchrony model has become the dominant assumption for practical BFT protocols.

| Model | Assumption on message delay | Representative algorithms |
| :---- | :---- | :---- |
| **Synchronous** | A known upper bound Δ on delivery; any message exceeding Δ is treated as lost. | Dolev–Strong; classical signed-message BGP; textbook PoW analyses. |
| **Partial synchrony** | Network alternates between synchronous and asynchronous periods; an unknown Global Stabilisation Time (GST) eventually holds with a bounded Δ thereafter. | PBFT, Tendermint, HotStuff, Casper FFG / Gasper. |
| **Asynchronous** | No bound on delivery; messages may be arbitrarily delayed but eventually arrive. | HoneyBadger-BFT, Dumbo, DAG-based (Narwhal/Tusk, Bullshark, Mysticeti). |
| **Probabilistic** | No timing assumption required; termination holds with overwhelming probability under random sampling. | Avalanche (Snowball/Snowflake/Avalanche), Algorand sortition. |

*For this thesis, the simulator must support at least partial synchrony (to exercise PBFT-family and PoS-finality protocols fairly) and asynchrony (to exercise DAG-based protocols). Avalanche-style protocols remain operable across all models, and their resilience under the same conditions becomes a direct basis for comparison.*

# **5\. Adversarial Models**

The second critical modelling axis is the adversary. A protocol can only be called Byzantine-fault-tolerant if it tolerates arbitrary behaviour from its faulty fraction; weaker fault models (crash, omission) admit simpler protocols that are out of scope for public blockchain settings.

* Crash faults. Faulty validators stop permanently. Tolerated by protocols such as Paxos and Raft; insufficient for adversarial settings.

* Omission faults. Faulty validators selectively drop messages but do not lie. A useful intermediate when modelling censorship or network-level adversaries.

* Byzantine faults. Faulty validators may send arbitrary, conflicting, or protocol-violating messages, possibly colluding. This is the canonical public-blockchain adversary and the focus of this thesis.

* Adaptive vs. static adversary. A static adversary chooses its corruption set once; an adaptive adversary corrupts as the protocol runs, typically after observing randomness. Adaptive corruption is the most demanding case and motivates cryptographic sortition in Algorand and repeated random sampling in Avalanche.

Concrete adversarial behaviours that the simulator will expose as first-class knobs are: (a) silent non-participation, (b) delayed voting, (c) equivocation (double-voting on different proposals at the same height), (d) selective message dropping to specific peers, and (e) surround voting in finality-gadget protocols. These correspond directly to the behaviours that the literature reports as most damaging to each family under evaluation.

# **6\. Why 3f+1? The Quorum Arithmetic Behind BFT**

The recurring 3f+1 validator requirement is not a convention; it falls out of two observations. First, to commit a value safely, a protocol must collect a quorum Q large enough that any two quorums intersect in at least one honest validator — otherwise two conflicting values could each gather a quorum and violate agreement. Since any two quorums of size Q in an n-validator set intersect in at least 2Q − n validators, and at most f of those can be Byzantine, the intersection is guaranteed to contain an honest validator whenever 2Q − n ≥ f \+ 1, i.e. Q ≥ (n \+ f \+ 1\) / 2\. When n \= 3f \+ 1, this yields the familiar Q ≥ 2f \+ 1\.

Second, liveness requires that a quorum be reachable even when f validators are unresponsive, so Q ≤ n − f. Combining Q ≥ (n \+ f \+ 1\) / 2 with Q ≤ n − f gives n ≥ 3f \+ 1\. The two constraints together force the classical threshold: the smallest n for which both agreement and termination are achievable under up to f Byzantine faults is 3f \+ 1, and the corresponding minimum quorum is 2f \+ 1\.

This deterministic quorum argument underpins the PBFT and PoS-finality families directly, and the DAG-based family indirectly (the 2f+1 signature requirement for Narwhal certificates is the same inequality). Avalanche-style probabilistic protocols do not use a quorum at all; their safety threshold is derived from a separate statistical argument about the improbability of a biased random sample, and is parameter-dependent rather than a fixed fraction of n. The 3f+1 bound is therefore a property of three of the four families studied, not all four.

# **7\. Design Space Map**

The table below positions each family evaluated in this thesis along the four axes introduced above. It is the document to return to whenever a design decision in a specific family needs to be justified by reference to what the family concedes and what it gains.

| Family | Synchrony | Finality | Fault threshold | Primary cost concession |
| :---- | :---- | :---- | :---- | :---- |
| **PBFT-style** | Partial | Deterministic, single-slot | f \< n/3 | O(n²) per-block messages; view-change cost on leader failure. |
| **PoS-finality** | Partial | Deterministic, checkpoint-based | f \< n/3 by stake | Latency to finality spans multiple epochs; complex slashing logic. |
| **Avalanche-style** | Asynchronous / probabilistic | Probabilistic (1 − ε) | f \< n/5 for safety under repeated sampling (parameter-dependent) | No hard finality; parameter tuning required; security under adaptive adversary analysed probabilistically. |
| **DAG-based** | Asynchronous | Deterministic, induced by DAG order | f \< n/3 | Higher per-node storage and bandwidth; deeper pipeline before order is fixed. |

# **8\. Propagation of the BFT Problem Across Consensus Families**

Each family can be read as answering a slightly different question, even though the underlying BGP is the same. The following ASCII diagram captures the propagation; each subsequent deep-dive document expands one branch.

                     \+-------------------------------+

                     |  Byzantine Generals Problem   |

                     |  n \>= 3f+1, safety \+ liveness |

                     \+---------------+---------------+

                                     |

         \+---------------------------+---------------------------+

         |                           |                           |

 Deterministic, quorum      Deterministic, stake-       Probabilistic,

 under partial sync         weighted \+ economic        random subsampling

         |                           |                           |

  \+------+------+          \+---------+---------+         \+-------+-------+

  | PBFT-family |          |  PoS-finality     |         |  Avalanche    |

  | PBFT, HS, TM|          |  Casper FFG /     |         |  Snowball \-\>  |

  |             |          |  Gasper / LMD     |         |  Avalanche    |

  \+------+------+          \+---------+---------+         \+-------+-------+

         |                           |                           |

         \+-----------+---------------+---------------------------+

                     |

           Separate data-availability  \----\> \+---------------+

           from ordering (DAG layer)         |  DAG-based    |

                                             | Narwhal/Tusk, |

                                             | Bullshark,    |

                                             | Mysticeti     |

                                             \+---------------+

## **8.1 PBFT-family — BFT under partial synchrony**

PBFT is the canonical deterministic answer: a designated leader drives a three-phase commit (pre-prepare, prepare, commit) among 3f+1 replicas; safety is preserved at all times and liveness is restored after GST through view changes. HotStuff and Tendermint streamline message complexity and leader rotation while preserving the same skeleton.

## **8.2 PoS-finality — BFT layered on a chain of blocks**

Casper FFG and Ethereum’s Gasper keep a conventional blockchain as the substrate and overlay a BFT finality gadget: validators cast supermajority votes on checkpoints, and two sequential supermajority votes finalise a checkpoint irreversibly. The BFT kernel is recognisably PBFT-like, but it operates at epoch granularity rather than per-block, and the fault threshold is expressed as one-third of stake rather than one-third of validator count. Slashing replaces the classical impossibility of identifying equivocators: because stake is at risk, the adversary is economically as well as cryptographically deterred.

## **8.3 Avalanche-style — BFT as a probabilistic process**

Avalanche abandons quorums in favour of repeated random subsampling. Each validator repeatedly polls a small random subset of peers; if a supermajority of the sample agrees on a value, the validator increments its confidence counter. After sufficiently many rounds of agreement the value is accepted. No validator ever collects a deterministic quorum, yet the protocol converges to agreement with probability (1 − ε) for arbitrarily small ε. The cost is that finality is probabilistic rather than absolute, and security analysis becomes a statement about the statistical indistinguishability of adversarial samples from honest ones.

## **8.4 DAG-based — BFT with data-availability split from ordering**

Narwhal, and its successors Bullshark and Mysticeti, observe that much of the latency and bandwidth cost of traditional BFT stems from entangling two concerns: disseminating transactions and ordering them. Narwhal reliably broadcasts transaction batches and records a DAG of causal dependencies; Tusk/Bullshark/Mysticeti then derive a total order from the DAG with zero extra messages in the common case. The BFT kernel is unchanged — still 3f+1, still quorum-based — but it now operates on DAG vertices rather than raw transactions, enabling far higher sustained throughput and graceful behaviour under delay.

# **9\. Implications for This Thesis**

The framing above dictates four concrete requirements for the simulator and the experimental protocol.

* Synchrony knob. The simulator must parameterise message delay as a configurable distribution (constant, uniform, exponential, heavy-tailed) and must allow a GST-style transition from asynchronous to synchronous regimes within a single run.

* Adversary knob. Validator behaviour must be pluggable so that silent non-participation, delayed voting, equivocation and selective dropping can be switched on per-validator without touching protocol code.

* Metric harness. Latency, throughput, per-block message count, finality time and fork rate must be instrumented uniformly across all four families so that the comparative analysis in Chapter 5 operates on a single schema.

* Shared abstractions. The simulator exposes a Validator, a Network and a Messaging API; each family is a plug-in that consumes the same API. This enforces fairness in comparison and makes the contribution reusable beyond this thesis.

# **10\. What Comes Next**

The four companion documents that follow this one each expand a single branch of the propagation diagram in Section 8\. Each is structured identically — Overview, Protocol mechanics, Assumptions, Behaviour under delay, Behaviour under adversarial conditions, Communication complexity, and Relevance to this thesis — so that the deep-dives themselves form the substrate of the Chapter 2 literature review. Full IEEE-style references to the canonical papers will accompany each deep-dive, where protocol-specific claims are made and attribution is required.