# [1] Lamport, Shostak & Pease — The Byzantine Generals Problem (1982)

**Category:** Foundational · **Venue:** ACM TOPLAS.

## Full citation

L. Lamport, R. Shostak, and M. Pease, "The Byzantine Generals Problem,"
*ACM Transactions on Programming Languages and Systems*, vol. 4, no. 3,
pp. 382–401, 1982.

## Key takeaways

1. **Formalises the Byzantine Generals Problem.** A commanding general
   and `n-1` lieutenants must reach agreement on an order, in the
   presence of up to `f` traitors who may send arbitrary (including
   inconsistent) messages. Abstracts malicious-fault consensus away from
   specific protocols.
2. **Proves the `n ≥ 3f+1` lower bound.** With oral messages (no
   authentication), deterministic agreement is impossible when
   `n ≤ 3f`; achievable and optimal at `n = 3f+1`. This bound is
   inherited by every BFT family in the thesis — see
   [[concepts/quorum-arithmetic]] for the derivation and
   [[concepts/byzantine-generals]] for the propagation tree.
3. **Round-complexity floor of `f+1`.** Even with optimal replica count,
   `f+1` synchronous rounds are necessary in the worst case. Informs the
   `3`-phase (`O(1)`-round) structure of practical BFT under
   partial-synchrony (PBFT, HotStuff) and the `3`-round lower bound
   [[algorithms/dag-based]] Mysticeti claims to reach.
4. **Signatures relax the bound to `f+1`.** With unforgeable signed
   messages, agreement is possible with any `n > f`. Motivates
   threshold-signature designs in [[algorithms/pbft]] (HotStuff) and the
   slashing-backed signatures in [[algorithms/pos]] (Casper FFG).
5. **Abstracts the adversary, not the network.** The paper is silent on
   network delay — it assumes synchronous rounds. Real-world
   degradations under delay/packet-loss are out of scope and motivate
   this thesis's simulator work (see [[concepts/problem-statement]] §gap).

## Limitations / gaps

Abstract and message-combinatorial; no implementation, no network model,
no performance measurement. Synchrony assumption does not hold on the
open Internet — relaxed by [3] (partial synchrony) and [2] (FLP).

## Links to affected wiki pages

- [[concepts/byzantine-generals]] — primary consumer; BGP formulation
  and propagation tree.
- [[concepts/quorum-arithmetic]] — derivation of `3f+1`.
- [[concepts/consensus-properties]] — agreement/validity definitions.
- [[concepts/fault-model]] — Byzantine fault class.
- [[algorithms/pbft]], [[algorithms/pos]], [[algorithms/dag-based]] —
  inherit the `3f+1` threshold.
- [[algorithms/avalanche]] — deliberately departs from the deterministic
  setting; [9] trades deterministic agreement for probabilistic
  `1 − ε` safety.
