# Wiki index

> Auto-maintained catalog of all wiki pages. One line per page.
> Format: `- [[path/to/page]] — one-line summary`
> Keep under ~500 lines. Revisit retrieval strategy if it grows past that.

## Algorithms

- [[algorithms/pbft]] — PBFT-family (Castro–Liskov, HotStuff, Tendermint): three-phase commit under partial synchrony; `3f+1` replicas; view change as liveness recovery.

## Concepts

- [[concepts/byzantine-generals]] — Lamport–Shostak–Pease BGP formulation; `n ≥ 3f+1` solvability bound; origin of the two-thirds supermajority.
- [[concepts/flp-impossibility]] — Fischer–Lynch–Paterson: no deterministic async consensus with even one crash fault; motivates partial-sync, randomization, and layered relaxations.
- [[concepts/cap-theorem]] — Under partition, blockchains choose Consistency (PBFT, PoS-finality) or Availability (Avalanche); `P` is non-negotiable.
- [[concepts/consensus-properties]] — The four properties (Agreement, Validity, Termination, Integrity) and the safety/liveness tension.
- [[concepts/synchrony-models]] — Synchronous / partial-sync / async / probabilistic; which family assumes which.
- [[concepts/fault-model]] — Crash / omission / Byzantine classes; static vs adaptive adversary timing. Theoretical taxonomy only; operational simulator adversary is T18.
- [[concepts/quorum-arithmetic]] — Derivation of `n ≥ 3f+1` from safety (quorum intersection) + liveness (unresponsive tolerance) constraints. Applies to 3 of 4 families.
- [[concepts/consensus-families]] — Design-space table + BGP propagation tree; one-line framing per family. Central navigation hub for comparative work.

## Sources

## Experiments

## Drafts
