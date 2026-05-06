# [18] Gilbert & Lynch — Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services (2002)

**Category:** Foundational · **Venue:** ACM SIGACT News.

## Full citation

S. Gilbert and N. Lynch, "Brewer's Conjecture and the Feasibility of
Consistent, Available, Partition-Tolerant Web Services," *ACM SIGACT
News*, vol. 33, no. 2, pp. 51–59, 2002.

## Key takeaways

1. **Formal proof of the CAP conjecture (asynchronous model).** No
   distributed read/write register implementation can simultaneously
   guarantee atomic consistency (linearizability), availability (every
   request to a non-failing node terminates), and partition tolerance
   when the network may drop arbitrary messages. The proof is a
   short indistinguishability argument: partition the nodes into two
   sets `G₁`, `G₂`; a write completes in `G₁` (availability); a
   subsequent read in `G₂` cannot observe it (partition); availability
   forces the read to return some value, which violates linearizability.
   Promotes Brewer's PODC 2000 conjecture to a theorem and pins down the
   CAP triangle that [[concepts/cap-theorem]] frames.
2. **Operational definitions matter.** Atomic consistency is defined as
   linearizability over a single read/write register; availability is
   defined per non-failing node, not system-wide; a partition is
   modelled as arbitrary message loss between the two halves. Reading
   the result outside these definitions ("CAP says you can only pick
   two of three") is the source of most folk misuses; the paper itself
   is narrower and stronger.
3. **Partial-synchrony refinement.** §4 considers a model in which
   nodes have access to local clocks and message-delay bounds hold when
   the network is connected. Even here, atomic consistency plus
   availability remains impossible during a partition; what becomes
   possible is *t-eventual consistency* — atomicity restored within `t`
   time after the partition heals. This is the formal anchor for the
   "AP families converge after the partition resolves" reading of
   [[algorithms/avalanche]] used on [[concepts/cap-theorem]].
4. **Maps onto the thesis's CP/AP families.** The CP families
   ([[algorithms/pbft]], [[algorithms/pos]]) preserve atomic
   consistency by sacrificing availability — finality halts under
   partition. The AP family ([[algorithms/avalanche]]) preserves
   availability by sacrificing instantaneous consistency, accepting a
   `1 − ε` finality and a bounded reconvergence window. Gilbert &
   Lynch make explicit what [[concepts/cap-theorem]] frames informally:
   `P` is non-negotiable for blockchains, so the design choice is
   genuinely binary modulo the relaxations [9]–[10] formalise.
5. **Relation to FLP.** Distinct from [2]: FLP forbids deterministic
   async consensus with one crash fault even with reliable channels;
   CAP forbids consistent + available service when the channel itself
   may drop messages. They are complementary impossibilities — FLP
   constrains agreement under failure, CAP constrains read/write
   registers under partition — and both motivate the partial-synchrony
   relaxation [3] that the thesis's CP families adopt.

## Limitations / gaps

The paper proves an impossibility for read/write registers; it does
not directly target consensus, BFT replication, or blockchain finality.
Mapping CAP onto consensus algorithms requires the additional step that
[[concepts/cap-theorem]] makes (a stalled BFT quorum is "unavailable"
in the CAP sense; a `1 − ε`-finality protocol is "consistent" only in
the limit). The 2002 paper does not quantify the partition-recovery
window for any specific protocol; per-family numbers come from the
primary protocol papers ([4]–[13]).

## Links to affected wiki pages

- [[concepts/cap-theorem]] — primary consumer; opening attribution and
  the CP/AP partition behaviour table.
- [[concepts/flp-impossibility]] — companion impossibility; the
  relationship between FLP (async + crash) and CAP (partition + atomic
  register) is laid out in takeaway 5 above.
- [[concepts/synchrony-models]] — the partial-synchrony refinement in
  §4 of the paper underpins the CP-family timing assumption.
- [[concepts/consensus-properties]] — safety/liveness reading of CAP's
  C/A choice during partition.
- [[concepts/problem-statement]] — three-gap motivation references the
  CP/AP split that this paper formalises.
- [[algorithms/avalanche]] — AP-family relaxation; `t-eventual`
  consistency is the formal anchor for "converges with probability
  `1 − ε` after the partition heals."
- [[algorithms/pbft]], [[algorithms/pos]] — CP-family choice;
  finality halts during partition rather than risk a divergent commit.
