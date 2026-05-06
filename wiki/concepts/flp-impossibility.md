# FLP Impossibility

Fischer, Lynch, and Paterson (1985) `[2]` proved that no deterministic
protocol can guarantee agreement in an asynchronous network with even a
single crash-faulty process.

## Intuition

An asynchronous adversary can always delay one message long enough that any
decision is premature: if the protocol commits before seeing the delayed
message, the delayed process could flip the decision; if the protocol waits,
it may wait forever. Thus safety and liveness cannot both be guaranteed under
pure asynchrony.

## How practical protocols circumvent FLP

Every deployed consensus algorithm relaxes one of FLP's assumptions:

- **Partial synchrony assumption.** Protocol may assume an eventual bound on
  message delay. Used by PBFT, Tendermint, HotStuff, Casper FFG/Gasper. See
  [[concepts/synchrony-models]].
- **Randomization.** Drop determinism; safety/liveness hold with probability
  `1 − ε`. Used by Avalanche (Snowball/Snowflake/Avalanche) and Algorand
  sortition.
- **Layered decomposition.** Separate the agreement problem into a
  deterministically-solvable sub-problem layered on top of a reliably
  broadcast mempool. Used by Narwhal/Tusk, Bullshark, Mysticeti.

## Relation to this thesis

FLP is the reason the simulator must vary network synchrony as an independent
axis: the boundary between "progress" and "stall" is where each family's
relaxation strategy earns or loses its guarantees.

## Sources

Citation `[2]` resolves via [[concepts/annotated-bibliography]] to the
dedicated source page [[sources/2026-04-21_flp-impossibility-1985]].
