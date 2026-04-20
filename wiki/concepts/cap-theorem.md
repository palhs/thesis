# CAP Theorem

A networked system cannot simultaneously provide **Consistency**,
**Availability**, and **Partition-tolerance**. Under a network partition the
system must choose between remaining consistent (C) or remaining available (A).

## Application to blockchain systems

Blockchain protocols operate over the public internet, where partitions are
inevitable, so `P` is non-negotiable. The design choice reduces to C vs A:

| Choice | Behaviour during partition | Families |
| :---- | :---- | :---- |
| **CP (safety-favouring)** | Finality halts until a quorum is restored; no conflicting commits. | [[algorithms/pbft]] family, PoS-finality (Casper FFG / Gasper) |
| **AP (liveness-favouring)** | Protocol keeps making progress; temporary inconsistency resolves as the network heals. | [[algorithms/avalanche]] and other probabilistic protocols |

## Nuance

Real blockchain protocols are not pure C or pure A. Avalanche converges to
consistency with probability `1 − ε` but accepts a window of divergence; PBFT
tolerates partition-induced stalls but guarantees safety during them. CAP
states the tradeoff exists, not where each system sits on it.

## Relation to this thesis

The CAP choice determines what metric matters under delay: for CP families,
it is finality latency and the size of the stall; for AP families, it is the
reconvergence time and the probability of a still-divergent commit.

## Source

- Brewer, E. A. "Towards Robust Distributed Systems." PODC 2000 keynote.
  `TODO(cite)` — add Gilbert & Lynch's 2002 proof of the conjecture.
