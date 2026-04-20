# Fault Model

A protocol can only be called Byzantine-fault-tolerant if it tolerates
arbitrary behaviour from its faulty fraction. Weaker fault models admit
simpler protocols that are out of scope for public blockchain settings.

## Fault classes (strongest tolerance last)

- **Crash faults.** Faulty validators stop permanently. Tolerated by
  protocols such as Paxos and Raft. Insufficient for adversarial settings.
- **Omission faults.** Faulty validators selectively drop messages but do
  not lie. Useful intermediate model when reasoning about censorship or
  network-level adversaries.
- **Byzantine faults.** Faulty validators may send arbitrary, conflicting,
  or protocol-violating messages, possibly colluding. This is the canonical
  public-blockchain adversary and the focus of this thesis.

## Adversary timing

- **Static adversary.** Chooses its corruption set once, at protocol start.
- **Adaptive adversary.** Corrupts validators as the protocol runs, typically
  after observing randomness. Strictly harder to defend against; motivates
  cryptographic sortition (Algorand) and repeated random sampling
  ([[algorithms/avalanche]]).

## Relation to operational adversary model

This page defines the *theoretical* fault taxonomy from the literature. The
*operational* adversary used by the simulator — concrete misbehaviours
parameterised per-validator — is defined separately in
[[concepts/adversary-model]] (task T18, pending).
