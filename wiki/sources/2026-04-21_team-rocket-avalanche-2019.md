# [9] Team Rocket, Yin, Sekniqi, van Renesse & Sirer — Scalable and Probabilistic Leaderless BFT Consensus through Metastability (2019)

**Category:** Protocol · **Venue:** arXiv:1906.08936 (widely cited; basis
of the Avalanche network).

## Full citation

Team Rocket, M. Yin, K. Sekniqi, R. van Renesse, and E. G. Sirer,
"Scalable and Probabilistic Leaderless BFT Consensus through
Metastability," arXiv preprint arXiv:1906.08936, 2019.

## Key takeaways

1. **Subsampled-voting cascade.** Protocol family Slush → Snowflake →
   Snowball → Avalanche, each adding a property to the last: Slush is
   stateless biased-random-walk agreement; Snowflake adds a *confidence
   counter* that reaches `β` before commit; Snowball adds preference-
   stickiness per colour; Avalanche lifts the single-decision protocol
   into a DAG-wide ordering. Production Avalanche uses Snowman — the
   linearised chain variant — not the DAG form. Full cascade in
   [[algorithms/avalanche]] §cascade.
2. **Per-validator `O(K·β)` cost, independent of `n`.** Each validator
   samples `K` peers per round and commits after `β` consecutive
   matching rounds. This bounds the *per-node* message cost to a
   constant — the scalability argument for thousand-validator networks
   that distinguishes Avalanche from quadratic-cost PBFT-style BFT.
3. **Probabilistic finality `1 − ε`.** Safety is not absolute. For
   honest-majority parameters `α_c/K` above a threshold, safety holds
   with probability `1 − ε` where
   `ε < (1 − α_c/K)^β`. Finality is achieved in expectation in `~1.35s`
   on the Avalanche testnet; throughput `~3.4 ktps` reported. These are
   the canonical numbers cited in Ch. 4 (all subject to verification via
   the simulator).
4. **Leaderless.** No primary, no view change, no leader rotation — every
   node queries random peers. Eliminates the leader-is-bottleneck and
   leader-can-be-targeted failure modes of PBFT-family protocols at the
   cost of probabilistic (not deterministic) finality.
5. **Production `α_p` vs `α_c` split.** The production network distinguishes
   a preference-flip threshold `α_p` from a commit threshold `α_c`
   (α_c ≥ α_p); the original paper's informal treatment conflates them.
   Flagged as a fidelity gap — the simulator follows the production split
   (per [[algorithms/avalanche]] §parameters).

## Limitations / gaps

Original analysis is informal. The formal follow-up [10] identifies
conditions under which liveness degrades more than [9] claims — [10] is a
required companion for balanced treatment in Ch. 2. Testnet numbers
([9] §eval) depend on workload and geography; the simulator must not
re-cite them as measured facts without qualification.

## Links to affected wiki pages

- [[algorithms/avalanche]] — primary consumer; canonical reference for
  the subsampling cascade.
- [[concepts/consensus-families]] — Avalanche family anchor.
- [[concepts/synchrony-models]] — probabilistic-synchrony regime.
- [[concepts/fault-model]] — probabilistic safety vs Byzantine.
- [[concepts/flp-impossibility]] — randomisation is the FLP relaxation.
- [[concepts/quorum-arithmetic]] — Avalanche does *not* use a
  deterministic quorum; treated in that page's §non-quorum-families.
