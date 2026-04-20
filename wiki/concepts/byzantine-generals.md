# Byzantine Generals Problem

Formalized by Lamport, Shostak, and Pease (1982) as the canonical abstraction for
distributed agreement under arbitrary faults. Generals of a besieged city must
coordinate on a single plan — attack or retreat — by sending messengers across
enemy territory. Some generals, or their messengers, may be traitors who say
anything to disrupt consensus.

## Properties that must hold

- **Agreement.** All non-faulty participants decide the same value.
- **Validity.** If the proposer (commanding general) is non-faulty, the agreed
  value equals the proposed value.

## Classical results

- BGP is solvable with deterministic protocols iff at most `f` out of `n`
  participants are faulty and `n ≥ 3f+1`.
- Protocols require at least `f+1` rounds of communication in the worst case.

The `3f+1` bound recurs throughout modern blockchain consensus — it is the
reason Tendermint, PBFT, HotStuff, and Casper FFG all fix a two-thirds
supermajority as their quorum threshold. Derivation lives in
[[concepts/quorum-arithmetic]].

## Relation to this thesis

BGP is the single problem all four families studied here respond to. Each
family is a distinct design tradeoff against BGP's solvability constraints —
see [[concepts/consensus-families]] for the propagation map.

## Source

- Lamport, L., Shostak, R., and Pease, M. "The Byzantine Generals Problem."
  *ACM Transactions on Programming Languages and Systems*, 4(3): 382–401, 1982.
  `TODO(cite)` — confirm exact DOI/pagination for thesis bibliography.
