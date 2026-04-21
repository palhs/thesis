# [8] Buterin et al. — Combining GHOST and Casper (Gasper, 2020)

**Category:** Protocol · **Venue:** arXiv:2003.03052 (Ethereum 2 spec;
not peer-reviewed; deployed in Ethereum).

## Full citation

V. Buterin, D. Hernandez, T. Kamphefner, K. Pham, Z. Qiao, D. Ryan,
J. Sin, Y. Wang, and Y. X. Zhang, "Combining GHOST and Casper," arXiv
preprint arXiv:2003.03052, 2020.

## Key takeaways

1. **Gasper = LMD-GHOST fork choice + Casper FFG finality.** Two layers
   composed into a single deployable PoS protocol. LMD-GHOST chooses the
   head of the chain using each validator's **latest** message, while
   Casper FFG [7] justifies and finalises epoch-boundary checkpoints on
   top of that chain. The thesis cites Gasper wherever fork choice and
   finality interact — see [[algorithms/pos]] §behaviour-under-delay.
2. **Latest-message fork choice is delay-sensitive.** Under network
   delay, stale attestations can survive long enough to bias the fork
   head toward a chain that FFG ultimately refuses to finalise. This is
   the mechanism behind short-lived reorgs under delay that the
   simulator must reproduce for PoS experiments (T51, T54).
3. **Epoch granularity for finality.** Ethereum epochs are ~6.4 minutes
   (32 slots × 12 s). Finality therefore lags block production by at
   least two epochs under honest conditions; under delay the lag grows
   unbounded, but safety is never violated — only time-to-finality
   degrades. This is the long-finality weakness called out on
   [[algorithms/pos]] §weaknesses-to-foreground.
4. **Reorg depth under attestation delay.** The paper analyses how late
   attestations can cause reorgs deeper than one slot, which informs the
   thesis's "fork rate under delay" metric axis on
   [[concepts/evaluation-metrics]] §reliability.
5. **Specification, not evaluation.** The paper is a protocol
   specification with partial analytical treatment. It does not report
   implementation performance; those numbers come from Ethereum
   production telemetry and, for this thesis, from the simulator
   modules produced under T32–T35 and T51.

## Limitations / gaps

No standalone empirical evaluation; the analyses provided are partial.
Reorg-depth bounds are conditional on specific attestation-delay
distributions. Validator-selection/randomness (RANDAO) is specified
elsewhere and interacts with Gasper in ways the paper does not fully
formalise.

## Links to affected wiki pages

- [[algorithms/pos]] — primary consumer; fork-choice-with-finality
  interaction, LMD-GHOST delay sensitivity, epoch finality granularity.
- [[concepts/evaluation-metrics]] — supplies the reorg-depth and
  time-to-finality metric dimensions for PoS experiments.
- [[concepts/fault-model]] — stake-weighted Byzantine thresholds under
  the combined protocol.
- [[concepts/annotated-bibliography]] — companion to [7] Casper FFG.
