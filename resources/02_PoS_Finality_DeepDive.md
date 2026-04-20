*Phase 1 — Deep Dive 2 of 4*

**Proof-of-Stake Finality Consensus**

*BFT as a Finality Gadget over a Chain of Blocks*

# **1\. Overview**

Proof-of-Stake finality protocols split the consensus problem into two layers. A block-proposal layer produces a constantly-growing chain of candidate blocks, while a BFT finality gadget periodically anoints certain blocks as irreversibly final. The canonical instance is Casper FFG — the Friendly Finality Gadget proposed by Buterin and Griffith \[1\] — and its full integration with Ethereum is the Gasper protocol combining LMD-GHOST fork choice with Casper FFG finality \[2\]. Unlike PBFT-family protocols, the fault threshold is measured in stake rather than validator count, and deviation is punished economically via slashing rather than only excluded cryptographically.

For this thesis, PoS-finality sits between PBFT (deterministic, single-slot finality) and Avalanche (probabilistic finality) on the spectrum of how aggressively a protocol commits. It introduces a new axis — economic security — that the simulator will model explicitly via a stake-weighted validator set and configurable slashing penalties.

# **2\. Protocol Mechanics**

## **2.1 Epochs, checkpoints and supermajority links**

Time is partitioned into fixed-length epochs, each containing many slots. The first block of each epoch is designated a checkpoint. Validators cast FFG votes of the form \<source, target\>, attesting that a source checkpoint should justify a target checkpoint. A supermajority link exists between source S and target T when FFG votes representing at least two-thirds of total stake have been cast for \<S, T\>.

A checkpoint T is justified when a supermajority link exists from any justified ancestor to T. A checkpoint T is finalised when T is justified and a supermajority link exists from T to its direct child T'. The two-round justification-then-finalisation mirrors the prepare-then-commit structure of PBFT, but operates at epoch granularity rather than per-block.

## **2.2 Finality flow**

   epoch n      epoch n+1     epoch n+2     epoch n+3

 \+----------+  \+----------+  \+----------+  \+----------+

 | block A  |  | block B  |  | block C  |  | block D  |     slots / blocks

 | (cp)     |  |          |  | (cp)     |  |          |     (cp \= checkpoint)

 \+----------+  \+----------+  \+----------+  \+----------+

     |   \<===== supermajority link (FFG votes, \>= 2/3 stake) \===\>  |

     |                                                             |

  justified \---\> justified \---\> finalised (two consecutive supermajority links)

## **2.3 The two slashing conditions**

Safety relies on two provable misbehaviours being economically punishable. Any validator that signs FFG votes violating either condition loses its staked deposit.

* Double voting: signing two distinct FFG votes with the same target epoch.

* Surround voting: signing a vote \<S1, T1\> that surrounds another of the validator’s own votes \<S2, T2\>, i.e. S1 \< S2 and T2 \< T1.

Casper’s accountable-safety theorem \[1\] shows that, if two conflicting checkpoints are ever finalised, at least one-third of total stake must have signed a slashable message, making the culprits identifiable and economically penalised. This is the property that distinguishes PoS-finality from unaccountable BFT: safety violations are not only infeasible under the threshold but also attributable above it.

# **3\. Assumptions**

* Partial synchrony for liveness; asynchrony only threatens finality delay, not safety.

* Fault threshold of one-third of total stake, not one-third of validators by count.

* Economically-motivated validators: the value of staked deposits exceeds the profit from any equivocation strategy that survives long enough to cause harm.

* Weak subjectivity: new or long-offline nodes must trust a recent checkpoint from a social consensus source, because no purely on-chain mechanism can distinguish a valid long-range history from an adversarial rewrite.

* Synchronous signature aggregation: modern implementations use BLS signatures so that thousands of attestations fit in a single aggregated vote.

# **4\. Behaviour under Network Delay**

PoS-finality degrades gracefully under delay because its unit of progress is an epoch, not a block. When delay spikes, the block-proposal layer continues operating but FFG supermajority links fail to form, and finalisation simply stalls. Crucially, safety is not at risk during a stall — only the time-to-finality lengthens. In Ethereum’s parameterisation with 32-slot epochs, a one-epoch delay in finalisation already adds roughly 6.4 minutes to time-to-finality, which is observable in periods of high adversarial delay or low participation.

Gasper \[2\] adds a second subtlety: the LMD-GHOST fork-choice rule operates on the latest attestation from each validator. Under delay, stale attestations can survive long enough to bias fork choice toward a chain that FFG will ultimately refuse to finalise, producing short-lived forks that reorg when attestations catch up. The simulator will exercise this by injecting per-validator attestation delay and observing reorg depth.

# **5\. Behaviour under Adversarial Conditions**

Three adversarial strategies are directly relevant and will be implemented as simulator behaviours.

* Non-participation. Byzantine validators abstain from attesting. Below one-third of stake, the only effect is higher finality latency; at or above one-third the chain stops finalising entirely (a liveness attack).

* Equivocation. Byzantine validators attempt to double-vote or surround-vote. Under the slashing conditions, each violating validator forfeits its stake and is ejected. Under a sufficiently large colluding fraction (\> 1/3 stake), safety can be violated, but at the cost of at least one-third of total stake being destroyed — the economic deterrent that supplements the cryptographic threshold.

* Delayed attestation. Byzantine validators attest at the last possible slot to maximise uncertainty in fork choice. This is a throughput/latency attack rather than a safety attack, and it is specifically the behaviour Gasper’s LMD-GHOST rule is sensitive to.

Because slashing is a first-class economic mechanism, PoS-finality protocols also expose a safety-cost budget that PBFT-family protocols do not: for an attacker of stake α, a successful safety attack costs approximately α/3 of total stake burned. The simulator can therefore report not only whether an attack succeeded but how expensive the attack was, a metric that is meaningful only in the PoS setting.

# **6\. Communication Complexity**

| Aspect | Per-slot cost | Per-epoch cost | Finality latency |
| :---- | :---- | :---- | :---- |
| **Attestations** | n per slot (aggregated via BLS to \~1) | n total | — |
| **FFG votes** | — | O(n) aggregated | 2 epochs (justify \+ finalise) |
| **Slashing evidence** | rare; carried in blocks | rare | — |

*Aggregated BLS signatures reduce the per-slot communication from O(n) distinct messages to a single aggregated attestation per committee, which is the enabling mechanism for validator sets in the tens of thousands. The simulator will model aggregation as a fixed cost per committee to keep per-validator instrumentation comparable across families.*

# **7\. Relevance to this Thesis**

PoS-finality occupies a distinctive position in the design space: it preserves PBFT’s deterministic finality while trading per-block latency for epoch-level finality latency, in return for validator-set sizes and economic accountability that PBFT cannot match. In the simulator we will implement a simplified Casper-FFG-like gadget with configurable epoch length, stake distribution, and slashing penalty. The knobs exposed to experiments are: (i) epoch length (slots), (ii) participation threshold for justification, (iii) attestation delay per validator, (iv) slashing penalty magnitude.

Expected findings — to be evaluated in Chapter 5 — include: time-to-finality degrades non-linearly once adversarial stake approaches one-third, reorg depth scales with attestation delay variance, and the economic cost of a successful safety break is a meaningful secondary security metric that is absent from PBFT-family analyses.

# **References**

**\[1\]** V. Buterin and V. Griffith, “Casper the Friendly Finality Gadget,” arXiv preprint arXiv:1710.09437, 2017\.

**\[2\]** V. Buterin, D. Hernandez, T. Kamphefner, K. Pham, Z. Qiao, D. Ryan, J. Sin, Y. Wang, and Y. X. Zhang, “Combining GHOST and Casper,” arXiv preprint arXiv:2003.03052, 2020\.