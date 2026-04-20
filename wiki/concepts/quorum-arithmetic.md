# Quorum Arithmetic: Why 3f+1

The recurring `3f+1` validator requirement in BFT protocols is not a
convention; it falls out of two independent constraints on quorum size `Q`.

## Constraint 1 — Safety via quorum intersection

To commit a value safely, any two quorums must intersect in at least one
honest validator — otherwise two conflicting values could each gather a
quorum and violate Agreement ([[concepts/consensus-properties]]).

- Any two quorums of size `Q` in an `n`-validator set intersect in at least
  `2Q − n` validators.
- Of those, at most `f` can be Byzantine.
- Intersection contains an honest validator iff `2Q − n ≥ f + 1`, i.e.
  `Q ≥ (n + f + 1) / 2`.

## Constraint 2 — Liveness under unresponsive validators

A quorum must be reachable even when `f` validators are silent:

- `Q ≤ n − f`.

## Combined

`(n + f + 1) / 2 ≤ Q ≤ n − f`  forces  `n ≥ 3f + 1`.

The smallest `n` for which both Agreement and Termination are simultaneously
achievable under up to `f` Byzantine faults is `3f + 1`; the corresponding
minimum quorum is `Q = 2f + 1`.

## Applicability

This deterministic argument underpins:

- [[algorithms/pbft]] family (explicit `2f+1` quorums in Prepare and Commit).
- PoS-finality (`2f+1` by stake on checkpoint votes in Casper FFG / Gasper).
- [[algorithms/dag-based]] (the `2f+1` signature requirement for Narwhal
  certificates is the same inequality applied to vertex certification).

[[algorithms/avalanche]] does **not** use a quorum: its safety threshold is
derived from a separate statistical argument about the improbability of a
biased random sample. The Avalanche safety threshold (commonly `f < n/5`
under repeated sampling) is parameter-dependent rather than a fixed fraction
of `n`. The `3f+1` bound is therefore a property of three of the four
families studied, not all four.
