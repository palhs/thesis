# [7] Buterin & Griffith — Casper the Friendly Finality Gadget (2017)

**Category:** Protocol · **Venue:** arXiv:1710.09437 (not peer-reviewed;
deployed in Ethereum).

## Full citation

V. Buterin and V. Griffith, "Casper the Friendly Finality Gadget,"
arXiv preprint arXiv:1710.09437, 2017.

## Key takeaways

1. **BFT finality gadget overlaid on a chain.** Casper FFG is not a
   standalone total-order protocol — it is a BFT-style finality layer
   sitting on top of an existing chain-selection rule (LMD-GHOST in
   Ethereum's Gasper [8]). Validators *justify* and *finalise* epoch
   boundary blocks; the underlying fork-choice extends the chain.
2. **Two-round justify → finalise.** A block is *justified* when
   `≥ 2/3` of stake attests to a justification link from a previous
   justified ancestor; two consecutive justifications finalise the
   earlier block. Matches the PBFT prepare/commit pattern
   ([[algorithms/pos]] §two-round) but at epoch granularity (epochs are
   `~6.4` minutes on Ethereum), not per-block.
3. **Accountable safety via slashing.** A validator that violates either
   the *no-double-vote* or *no-surround-vote* slashing conditions can be
   cryptographically proven to have misbehaved, and their staked deposit
   is burned. This converts the classical `f < n/3` safety argument into
   an *economic* one: an adversary with `> 1/3` stake can violate safety,
   but must burn `> 1/3` of total stake to do so. Anchors the
   [[algorithms/pos]] fault model.
4. **Stake-weighted `3f+1` threshold.** The `2/3` attestation supermajority
   is stake-weighted rather than node-count weighted. Same theoretical
   bound as [1]; different unit of account. Derived in
   [[concepts/quorum-arithmetic]] §pos.
5. **Does not specify block production.** Casper FFG leaves proposer
   selection to the underlying protocol (in Ethereum, RANDAO-driven
   validator selection). The simulator's PoS module (tasks T32–T35)
   implements finality on top of a simplified round-robin or
   stake-weighted proposer — proposer selection is a separate knob
   (task T33).

## Limitations / gaps

Protocol specification and formal properties only — no implementation
performance numbers. Time-to-finality (epochs) is a theoretical bound;
real-world values are probed by Ethereum production telemetry and by
this thesis's simulator (task T32–T35). Depends on an underlying chain
for block production, which Gasper [8] supplies.

## Links to affected wiki pages

- [[algorithms/pos]] — primary consumer; Casper FFG is the reference
  protocol for the PoS-finality family.
- [[concepts/quorum-arithmetic]] — stake-weighted `3f+1`.
- [[concepts/fault-model]] — accountable Byzantine via slashing.
- [[concepts/consensus-families]] — PoS-finality family anchor.
- [[concepts/synchrony-models]] — partial synchrony for liveness.
