# [16] Cachin & Vukolić — Blockchain Consensus Protocols in the Wild (2017)

**Category:** Survey (DISC keynote / arXiv review) · **Venue:**
arXiv:1707.01873; presented at DISC 2017.

## Full citation

C. Cachin and M. Vukolić, "Blockchain Consensus Protocols in the Wild,"
arXiv preprint arXiv:1707.01873, 2017.

## Key takeaways

1. **Methodological anchor for this thesis.** The paper's central
   argument is that permissioned-blockchain BFT claims in industry and
   whitepapers were being made without formal models or public review,
   and that the discipline should demand both. The thesis's
   simulation-based, metrics-instrumented comparative approach is a
   direct response to this argument — see [[concepts/problem-statement]]
   §method.
2. **Qualitative taxonomy.** Organises permissioned-chain consensus
   around fault model, trust model, and safety/liveness rather than
   around specific algorithms. Complements the quantitative framings in
   [14] (SoK-style taxonomy) and [15] (metric ranges) but stays purely
   qualitative.
3. **Cited for methodology, not numbers.** Per the citation policy on
   [[concepts/annotated-bibliography]] §citation-policy, [16] is invoked
   wherever the thesis defends its choice of a formal-model /
   reproducible-simulator approach. It is **never** cited as a source of
   a throughput, latency, or fault-threshold figure — it contains none.
4. **Permissioned-chain focus.** The paper's lens is permissioned BFT
   (Hyperledger-era projects), but its arguments about evaluation rigor
   apply to permissionless BFT families equally. The thesis inherits the
   rigor argument while applying it to the permissionless-chain BFT
   families on [[concepts/consensus-families]].
5. **Historical context for Ch. 1.** Cited in Ch. 1 (motivation) as
   evidence that the rigor gap predates the current DAG/Avalanche
   generation — the same concerns recur, updated, in [10]'s re-analysis
   of Avalanche safety claims.

## Limitations / gaps

Qualitative review only; no quantitative benchmark, no protocol
comparison beyond structural taxonomy. Permissioned-chain focus means
some of the specific concerns do not map cleanly onto the
permissionless-BFT families this thesis evaluates. Pre-dates HotStuff
[5], Casper FFG [7], Gasper [8], Avalanche [9], and the DAG-based family
[11]–[13].

## Links to affected wiki pages

- [[concepts/problem-statement]] — primary consumer; methodological
  motivation for the simulator-based approach.
- [[concepts/annotated-bibliography]] — exemplar of methodology-only
  survey citation.
- [[concepts/consensus-families]] — qualitative-taxonomy companion to
  [14].
