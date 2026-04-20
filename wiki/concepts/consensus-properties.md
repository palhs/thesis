# Formal Properties of a Consensus Protocol

The four properties every consensus protocol in the literature is expected to
state explicitly. They are the vocabulary used to compare families fairly.

## The four properties

- **Agreement (safety).** No two non-faulty validators commit conflicting
  values at the same height.
- **Validity.** Any committed value was proposed by some validator. A stronger
  form: the value was proposed by a non-faulty validator when one exists.
- **Termination (liveness).** Every non-faulty validator eventually commits a
  value at every height.
- **Integrity.** No validator commits the same value twice; committed history
  is immutable.

## Safety vs liveness tension

These are two failure modes, not one. A protocol that is conservative about
committing (good for safety) risks stalling under delay (bad for liveness).
A protocol that is aggressive about committing (good for liveness) risks
forking (bad for safety).

Which side of this tension a family prioritises in the worst case is one of
the axes this thesis evaluates empirically. See [[concepts/cap-theorem]] for
the partition-time specialisation of the same tradeoff, and
[[concepts/consensus-families]] for per-family positioning.

## Relation to adjacent concepts

- The `f < n/3` threshold in [[concepts/quorum-arithmetic]] is precisely what
  makes Agreement and Termination simultaneously achievable under Byzantine
  faults.
- Under pure asynchrony, [[concepts/flp-impossibility]] rules out
  deterministic satisfaction of all four properties with even one crash
  fault — hence the synchrony relaxations in [[concepts/synchrony-models]].
