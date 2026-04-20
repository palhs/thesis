*Phase 1 — Deep Dive 3 of 4*

**Avalanche-Style Probabilistic Consensus**

*BFT via Repeated Random Subsampling*

# **1\. Overview**

Avalanche-style consensus departs radically from the quorum-based reasoning of PBFT and PoS-finality. Rather than collecting a supermajority vote, each validator repeatedly polls a small random sample of peers, and accumulates confidence in a value through many short rounds of agreement. The protocol family — Slush, Snowflake, Snowball, and the full Avalanche protocol — was introduced by Rocket et al. in a paper originally published anonymously under the “Team Rocket” pseudonym and later formalised by researchers at Cornell \[1\]. The protocol is deployed in production as the Avalanche network’s consensus layer, and a linearised variant called Snowman has replaced the original DAG-based variant on all three production chains (C-Chain, P-Chain, and — since the Cortina upgrade in April 2023 — the X-Chain) \[3\]. Subsequent formal security analyses have examined the protocol’s resilience and its assumptions more critically \[2\].

For this thesis, Avalanche represents the probabilistic-finality corner of the design space. Its defining tradeoff is well-defined: no single round of messages ever forms a quorum, but the probability that all honest validators converge on the same value grows exponentially with the number of sampling rounds. Finality becomes a statistical guarantee — any desired probability 1 − ε is reachable by tuning a small set of parameters rather than by waiting for deterministic events. The official Avalanche documentation describes finality as “sub-second” and “immutable” on the production network, reflecting a parameter choice that drives the safety-violation probability well below any operationally observable threshold \[3\].

# **2\. Protocol Mechanics**

## **2.1 Slush: the subsampling primitive**

The simplest member of the family, Slush, works as follows. Each validator holds a colour (e.g. red or blue). In each round, the validator picks k peers uniformly at random, queries their colour, and if α out of k responses agree on a colour different from its own, it flips to that colour. After m rounds every honest validator outputs its current colour as the decision.

## **2.2 Snowflake: adding confidence counters**

Snowflake extends Slush with a counter: a validator only decides a colour once it has seen β consecutive rounds with α agreement on that colour. Each time the validator flips, the counter resets. The consecutive-agreement requirement makes Snowflake robust to transient noise: brief minority clusters of disagreement cannot push the system into premature commitment.

## **2.3 Snowball: preference tracking**

Snowball augments Snowflake with a preference that reflects all historical α-supermajority observations, not just the consecutive streak. The preference is updated whenever a round produces an α-majority, independently of the consecutive counter. Preference tracking improves bias toward the true majority colour by exploiting information that Snowflake discards on every flip.

## **2.4 Avalanche: DAG-ordered Snowball**

Avalanche generalises Snowball from binary colours to an arbitrary DAG of conflicting transactions. Each validator maintains a DAG of transactions; when polled about a transaction T, a validator replies with the consistent subset of its DAG that includes T. The confidence of T grows whenever it is included in an α-majority reply, and T is accepted when its confidence exceeds β. Conflicting transactions are resolved by Snowball on the vertex whose inclusion is being voted on. The DAG plus Snowball voting is the full protocol.

## **2.5 Snowman: the linearised production variant**

Snowman is the linear-chain variant of Avalanche consensus used in production on the Avalanche network’s C-Chain, P-Chain and (post-Cortina, April 2023\) X-Chain \[3\]. It applies the same Snowball sub-sampling engine, but operates on a totally-ordered chain of blocks rather than a DAG of transactions. For this thesis, Snowman is the appropriate production reference point when making latency and throughput comparisons, because it is the deployed protocol and its chain-structured behaviour is directly comparable to PBFT-family and PoS-finality protocols. The full DAG-based Avalanche described in Section 2.4 remains the canonical theoretical object and is the one analysed in \[1\] and \[2\].

The official documentation distinguishes two thresholds within what the original paper called α: AlphaPreference (the sample-majority threshold that causes the validator to switch its preference) and AlphaConfidence (the sample-majority threshold that increments the decision counter) \[3\]. In the original Snowball these were the same; the production parameterisation decouples them to tune preference volatility and finality probability independently.

## **2.6 Sampling round diagram**

                     validator v

                         |

      random sample of k peers (k small, e.g. 20\)

     /    /    /    \\    \\    \\

    p1   p2   p3   ...  pk-1   pk

     \\    \\    \\    /    /    /

         count votes for colour c

              |

      if count \>= α → update preference, increment counter

      if counter \>= β → ACCEPT c

# **3\. Assumptions**

* Adversary bound. A fixed fraction of validators may be Byzantine. The safe fraction depends on parameter choices; for production parameters (K \= 20, α\_c ≈ 0.8K, β ≈ 15\) \[3\], the safety-violation probability is bounded by (1 − α\_c/K)^β and remains negligible while the Byzantine fraction stays well below the critical threshold. Formal analyses in \[1\] and \[2\] refine these bounds under different adversary models.

* Random peer sampling. Each validator has a reasonably uniform view of the peer set and samples without persistent bias. Sybil resistance is assumed to be provided externally (e.g. by stake-based sampling weights on AVAX).

* No timing assumptions. Unlike PBFT, Avalanche does not require partial synchrony for safety; the statistical argument holds under adversarial message delays, at the cost of extended time to accumulate β consecutive agreements.

* Probabilistic finality. A transaction is accepted when its confidence exceeds a threshold, and the probability of a later reversal decays exponentially with additional rounds. There is no hard finality — only a tunable ε.

# **4\. Behaviour under Network Delay**

Avalanche degrades gracefully under delay. Because each round samples only k peers (typically ≤10% of the network), a round completes as soon as the first k responses return — slow peers simply do not influence the round. Network delay therefore lengthens inter-round time but not the computation per round. End-to-end latency grows approximately linearly with delay, not super-linearly as in quorum-based protocols.

The more subtle effect is that delay increases the variance of individual round outcomes: if sampled peers have not yet received the latest transaction, their reply is “don’t know”, which cannot contribute to the α-majority. Under heavy delay this can stall finality without violating safety. The recent formal analysis of Avalanche \[2\] showed that in worst-case asynchrony the protocol can experience extended periods of liveness degradation that had been underestimated in the original informal treatment.

# **5\. Behaviour under Adversarial Conditions**

Because every round is a fresh random sample, the adversary cannot persistently bias a single validator’s view. The strongest adversarial strategies in simulation are therefore statistical rather than structural.

* Selective response. Byzantine validators reply to queries with whichever colour is opposite the honest majority. The effect is to subtract roughly the Byzantine fraction from the α-majority signal. Safety holds as long as the honest fraction of any sample exceeds α with high probability.

* Adaptive colour flipping. Byzantine validators coordinate to flip their reported colour each round to maximise variance in honest validators’ preferences. This delays but does not prevent convergence.

* Sample-partitioning. The adversary attempts to split the honest set into two preference clusters that each see only their own preference in sampled replies. The statistical argument in \[1\] bounds the probability of this succeeding, and recent work in \[2\] refines these bounds under stronger network adversaries.

Unlike PBFT, safety in Avalanche is probabilistic rather than categorical: there exists a non-zero probability that an adversarial coincidence produces a safety violation, but this probability is driven below any target ε by sufficiently many rounds. The simulator can measure empirical ε by running many trials and counting safety violations under a given adversarial strategy.

# **6\. Parameters, Safety Bound, and Communication Complexity**

The official Avalanche documentation specifies four production parameters and a closed-form upper bound on the probability of a safety violation \[3\]. These are reproduced below and serve as the ground truth for the simulator’s Avalanche/Snowman implementation.

| Parameter | Role | Typical value | Cost impact |
| :---- | :---- | :---- | :---- |
| **K (sample size)** | Peers queried per poll | 20 \[3\] | O(K) msgs/round/validator |
| **AlphaPreference (α\_p)** | Sample-majority threshold that flips the validator’s preference \[3\] | \~ ⌊K/2⌋ \+ 1 | Lower value accelerates convergence, higher stabilises preference |
| **AlphaConfidence (α\_c)** | Sample-majority threshold that increments the confidence counter \[3\] | \~0.8 · K | Directly controls safety-violation probability (see bound below) |
| **Beta (β)** | Consecutive α\_c-majorities required before a value is finalised \[3\] | 15–20 | Linear impact on latency; exponential impact on safety |

## **6.1 Safety bound**

The official Avalanche documentation states the probability of a safety violation (two honest validators accepting conflicting blocks) as \[3\]:

   P(safety violation)  \<  ( 1 − α\_c / K ) ^ β

The bound is exponential in β and drives finality probability toward 1 − ε for an arbitrarily small ε as β grows. For the default production parameters the exponent drives ε well below operationally observable thresholds, which is the basis for the documentation’s claim of “immutable” finality \[3\]. Unlike PBFT, which derives safety deterministically from the 3f+1 quorum arithmetic, Avalanche’s safety is a parameterised statistical property; the thesis’s simulator will empirically sample ε by counting violations over many seeds, and will compare empirical ε against this theoretical bound.

## **6.2 Communication complexity**

Per-validator message complexity is O(K·β) in the common case, independent of n. This is the architectural reason Avalanche scales to thousands of validators without per-block traffic blow-up, and it is a direct contrast to the O(n²) per-block cost of classical PBFT. The official documentation notes that parameters are network-wide and cannot be changed per node; heterogeneous parameters would cause consensus failures \[3\] — a constraint the simulator will respect.

# **7\. Relevance to this Thesis**

Avalanche represents the probabilistic, no-quorum corner of the design space and provides the cleanest comparison point for the fundamental tradeoff of this thesis: surrender of deterministic finality in exchange for scalability and resilience under delay. In the simulator we will implement a simplified Snowman variant (the linearised form deployed in production \[3\]) exposing K, AlphaPreference, AlphaConfidence, Beta, and the random-sampling seed as first-class experiment parameters. This keeps the thesis’s Avalanche implementation directly comparable to the production protocol, while remaining simple enough to coexist with the PBFT, PoS-finality, and DAG-based implementations under the same Validator interface.

Expected findings — to be confirmed in Chapter 5 — are: (i) time-to-finality is essentially invariant to validator count n, holding K and β fixed, matching the official sub-second claim \[3\]; (ii) empirical safety-violation rates align with the theoretical bound (1 − α\_c/K)^β for low Byzantine fractions and diverge predictably as the adversary approaches the critical threshold; (iii) under high delay, the protocol maintains correctness but finality latency grows, while quorum-based protocols stall outright. Together these position Snowman/Avalanche as the strongest performance baseline under adversarial delay in the comparative analysis.

# **References**

**\[1\]** Team Rocket, M. Yin, K. Sekniqi, R. van Renesse, and E. G. Sirer, “Scalable and Probabilistic Leaderless BFT Consensus through Metastability,” arXiv preprint arXiv:1906.08936, 2019\.

**\[2\]** I. Amores-Sesar, C. Cachin, and P. Schneider, “An Analysis of Avalanche Consensus,” arXiv preprint arXiv:2401.02811, 2024\.

**\[3\]** Ava Labs, “Consensus Protocols — Avalanche Builder Hub,” official documentation, https://build.avax.network/docs/nodes/architecture/consensus (accessed Apr. 2026).