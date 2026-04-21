# Wiki index

> Auto-maintained catalog of all wiki pages. One line per page.
> Format: `- [[path/to/page]] — one-line summary`
> Keep under ~500 lines. Revisit retrieval strategy if it grows past that.

## Algorithms

- [[algorithms/pbft]] — PBFT-family (Castro–Liskov, HotStuff, Tendermint): three-phase commit under partial synchrony; `3f+1` replicas; view change as liveness recovery.
- [[algorithms/pos]] — PoS-finality (Casper FFG, Gasper): BFT finality gadget over a chain; two-round justify→finalise at epoch granularity; stake-weighted `3f+1` with slashing-based accountable safety.
- [[algorithms/avalanche]] — Avalanche family (Slush → Snowflake → Snowball → DAG-Avalanche; production: Snowman): BFT via repeated random `k`-peer subsampling; probabilistic finality `1 − ε` with `ε < (1 − α_c/K)^β`; per-validator cost `O(K·β)` independent of `n`.
- [[algorithms/dag-based]] — DAG-based BFT (Narwhal+Tusk, Bullshark, Mysticeti): decouple data availability (DAG mempool) from ordering (anchor commit over DAG); `3f+1` threshold, async-safe, `O(n)` per-block messages, trades messages for per-node storage.

## Concepts

- [[concepts/byzantine-generals]] — Lamport–Shostak–Pease BGP formulation; `n ≥ 3f+1` solvability bound; origin of the two-thirds supermajority.
- [[concepts/flp-impossibility]] — Fischer–Lynch–Paterson: no deterministic async consensus with even one crash fault; motivates partial-sync, randomization, and layered relaxations.
- [[concepts/cap-theorem]] — Under partition, blockchains choose Consistency (PBFT, PoS-finality) or Availability (Avalanche); `P` is non-negotiable.
- [[concepts/consensus-properties]] — The four properties (Agreement, Validity, Termination, Integrity) and the safety/liveness tension.
- [[concepts/synchrony-models]] — Synchronous / partial-sync / async / probabilistic; which family assumes which.
- [[concepts/fault-model]] — Crash / omission / Byzantine classes; static vs adaptive adversary timing. Theoretical taxonomy only; operational simulator adversary is T18.
- [[concepts/quorum-arithmetic]] — Derivation of `n ≥ 3f+1` from safety (quorum intersection) + liveness (unresponsive tolerance) constraints. Applies to 3 of 4 families.
- [[concepts/consensus-families]] — Design-space table + BGP propagation tree; one-line framing per family. Central navigation hub for comparative work.
- [[concepts/problem-statement]] — Thesis title, the three-gap motivation, four objectives, scope (in/out), assumptions/limitations, success criteria. Entry point for Chapter 1 framing.
- [[concepts/research-questions]] — RQ1–RQ5 with primary metrics and independent variables; maps each RQ to the family axis it stresses and to the downstream tasks that consume it.
- [[concepts/annotated-bibliography]] — Consolidated IEEE bibliography `[1]–[17]`; citation policy (unified numbering across chapters; surveys for framing only); resolver to `wiki/sources/` pages.

## Sources

- [[sources/2026-04-21_lamport-shostak-pease-bgp-1982]] — [1] BGP formulation; deterministic agreement iff `n ≥ 3f+1`, round floor `f+1`; signatures relax to `f+1`.
- [[sources/2026-04-21_flp-impossibility-1985]] — [2] FLP: no deterministic async consensus with even one crash fault; motivates the four families' relaxations.
- [[sources/2026-04-21_dwork-lynch-stockmeyer-partial-sync-1988]] — [3] Partial-synchrony model; consensus under `f < n/3`; safety-always / liveness-after-GST separation.
- [[sources/2026-04-21_castro-liskov-pbft-1999]] — [4] PBFT: first practical BFT SMR; three-phase commit + view change; `O(n²)` normal / `O(n³)` view change.
- [[sources/2026-04-21_yin-hotstuff-2019]] — [5] HotStuff: linearises view change to `O(n)` via threshold signatures; responsive leader rotation.
- [[sources/2026-04-21_buchman-tendermint-2018]] — [6] Tendermint: round-robin leader BFT with locking rule; Cosmos SDK deployment basis.
- [[sources/2026-04-21_buterin-griffith-casper-ffg-2017]] — [7] Casper FFG: BFT finality gadget; two-round justify→finalise; accountable safety via slashing.
- [[sources/2026-04-21_team-rocket-avalanche-2019]] — [9] Avalanche: subsampled-voting cascade Slush→Snowflake→Snowball→Avalanche; probabilistic `1 − ε` finality; per-node `O(K·β)`.
- [[sources/2026-04-21_danezis-narwhal-tusk-2022]] — [11] Narwhal+Tusk: DAG mempool + zero-overhead consensus; decouples data availability from ordering; `O(n)` messages.
- [[sources/2026-04-21_spiegelman-bullshark-2022]] — [12] Bullshark: partial-sync fast path + async fallback DAG BFT; simplifies Narwhal+Tusk in ~200 LoC.
- [[sources/2026-04-21_babel-mysticeti-2023]] — [13] Mysticeti: uncertified DAG at the 3-round BFT latency lower bound; deployed in Sui.
- [[sources/2026-04-21_bano-sok-consensus-2019]] — [14] SoK taxonomy of blockchain consensus families; taxonomic anchor for Ch. 2 and for [[concepts/consensus-families]].

## Experiments

## Drafts
