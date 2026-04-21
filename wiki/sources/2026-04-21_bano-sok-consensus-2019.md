# [14] Bano et al. — SoK: Consensus in the Age of Blockchains (2019)

**Category:** Survey · **Venue:** AFT (1st ACM Conf. on Advances in
Financial Technologies).

## Full citation

S. Bano, A. Sonnino, M. Al-Bassam, S. Azouvi, P. McCorry, S. Meiklejohn,
and G. Danezis, "SoK: Consensus in the Age of Blockchains," in *Proc.
1st ACM Conf. Advances in Financial Technologies (AFT)*, 2019,
pp. 183–198.

## Key takeaways

1. **Taxonomy used by the thesis.** Bano et al. organise blockchain
   consensus into Nakamoto-style PoW, proof-of-X (including PoS), and
   hybrid/classical BFT families, with evaluation axes for security
   (fault model, trust assumptions) and performance (throughput,
   latency, scalability). This is the taxonomic spine of
   [[concepts/consensus-families]] and the framing for Ch. 2.
2. **Explicit separation of BFT and Nakamoto lineages.** Makes the
   distinction this thesis relies on: BFT-style protocols (PBFT, PoS-
   finality, DAG-based, and — less comfortably — Avalanche) share a
   `3f+1`-style threshold and deterministic-or-probabilistic finality,
   whereas Nakamoto's probabilistic longest-chain rule is architecturally
   different. This motivates the thesis's scope exclusion of pure
   longest-chain PoW — see [[concepts/problem-statement]] §scope.
3. **Methodological caveat: heterogeneous reported performance.** The
   survey flags that reported throughput/latency numbers across papers
   are not directly comparable due to differing hardware, workloads, and
   batching. This is the same comparability gap restated in
   [[concepts/problem-statement]] §heterogeneous-harnesses and is the
   headline motivation for the simulator-based approach this thesis adopts.
4. **Cited only for taxonomy.** Per the citation policy (see
   [[concepts/annotated-bibliography]] §citation-policy), surveys are
   cited for framing and classification only; never as the source of a
   quantitative claim. The thesis's performance figures all resolve to
   the primary papers [4]–[13], [17].
5. **Pre-dates DAG-based family.** Published 2019; does not cover
   Narwhal+Tusk [11], Bullshark [12], or Mysticeti [13]. Coverage of
   Avalanche [9] is brief. Ch. 2's DAG-based section therefore cannot
   rely on [14] and must cite primary sources directly.

## Limitations / gaps

Survey-level treatment; no new experimental data; coverage frozen at
2019. Pre-dates DAG-based BFT and the formal Avalanche-analysis line of
work ([10], 2024). Thesis uses it as the literature-framing anchor, not
as a source of performance evidence.

## Links to affected wiki pages

- [[concepts/consensus-families]] — primary consumer; taxonomic spine.
- [[concepts/problem-statement]] — heterogeneous-harnesses gap framing.
- [[concepts/annotated-bibliography]] — citation-policy exemplar.
- [[algorithms/pbft]], [[algorithms/pos]], [[algorithms/avalanche]] —
  coverage present (Avalanche brief).
- [[algorithms/dag-based]] — coverage *absent*; DAG-based citations
  must go to primary sources [11]–[13] instead.
