# [6] Buchman, Kwon & Milosevic — The Latest Gossip on BFT Consensus (Tendermint, 2018)

**Category:** Protocol · **Venue:** arXiv:1807.04938 (not peer-reviewed).

## Full citation

E. Buchman, J. Kwon, and Z. Milosevic, "The Latest Gossip on BFT
Consensus," arXiv preprint arXiv:1807.04938, 2018.

## Key takeaways

1. **Round-robin leader BFT.** Primary rotates deterministically by
   round number — no view change, no primary-suspicion machinery. Every
   round has a scheduled leader; failed leaders time out and the next
   round begins immediately under the next validator in the rotation.
   No replica is structurally privileged, which simplifies the threat
   model at the cost of forcing every leader rotation to pay a timeout.
2. **Locking rule for safety.** A validator that pre-commits to a value
   in round `r` "locks" on that value and will only unlock on a polka
   (`2f+1` prevotes) for a different value in a later round. This is
   the mechanism that preserves safety across round transitions — the
   analogue of PBFT's [4] view-change certificate.
3. **Same `3f+1` threshold, same partial synchrony.** Derived from
   [1]–[3] without modification. Tendermint is a structural
   simplification of PBFT, not a weakening of its guarantees — see
   [[algorithms/pbft]] §variants for the head-to-head table.
4. **Cosmos SDK deployment basis.** Operationally the most widely
   deployed BFT protocol as of 2026 (Cosmos Hub, Osmosis, Binance
   Chain's early era, and dozens of application chains). Commit latencies
   are seconds-scale on WAN due to the round-robin timeout cost, not
   hundreds of ms as in LAN PBFT [4].
5. **Reference for the thesis PBFT simulator.** The round-robin leader +
   prevote/precommit structure is simpler to implement than PBFT's
   view-change, so the simulator's PBFT-family module (task T28–T31)
   adopts Tendermint's control flow while keeping Castro–Liskov's
   three-phase names.

## Limitations / gaps

Not peer-reviewed; claims about fairness and leader-rotation overhead
are operational rather than analytical. Production performance data is
anecdotal; there is no systematic evaluation under delay or adversarial
conditions (the gap this thesis's simulator is designed to close — see
[[concepts/problem-statement]]).

## Links to affected wiki pages

- [[algorithms/pbft]] — primary consumer; Tendermint variant.
- [[concepts/quorum-arithmetic]] — `2f+1` prevote/precommit quorums.
- [[concepts/synchrony-models]] — partial sync.
- [[concepts/consensus-families]] — classical-BFT family, round-robin
  flavour.
