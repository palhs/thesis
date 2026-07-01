# Research Questions

Five research questions (RQ1–RQ5) structure the empirical evaluation. Each
is stated with a measurable scope so its answer is empirical rather than
speculative. The questions map one-to-one onto the metric schema in
`wiki/concepts/evaluation-metrics.md` (landing under S7/T9) and define the
experimental matrix driven by RQ1–RQ4.

Problem statement, objectives, and scope: [[concepts/problem-statement]].

## The five questions

| ID | Research question | Primary metric(s) | Independent variable |
| :---- | :---- | :---- | :---- |
| **RQ1** | How does end-to-end commit latency scale, for each of the four consensus families, as network delay variance increases from nominal to heavy-tailed? | Commit latency, round latency, time-to-finality | Delay distribution (constant, uniform, exponential, heavy-tailed) |
| **RQ2** | How does sustained throughput of each family degrade under increasing Byzantine fraction, below and approaching the theoretical threshold? | Throughput (tps), goodput, peak throughput | Byzantine fraction `0 → f_max` |
| **RQ3** | What is the relative communication overhead of each family, measured in messages per agreed unit, under a fixed workload and identical network assumptions? | Messages per agreed unit, per-validator state size | Validator-set size `n` |
| **RQ4** | Under which adversarial strategies (silent non-participation, delayed voting, equivocation) does each family experience liveness degradation, safety violations, or neither? | Consensus success rate, view-change/reorg frequency, safety-violation probability `ε` | Adversarial strategy × Byzantine fraction |
| **RQ5** | Is there a consistent Pareto frontier of the performance–security tradeoff across families, and does any family dominate the others across all operating regimes? | All four metric families jointly | Combined (delay, adversary, `n`, workload) |

**Role split.** RQ1–RQ4 generate the data. RQ5 is the synthesis question;
its answer is the headline contribution of the comparative analysis in
Chapter 5.

## What each RQ tests about each family

- **RQ1 (delay scaling).** Stresses the synchrony column of
  [[concepts/consensus-families]]. Partial-sync families ([[algorithms/pbft]],
  [[algorithms/pos]]) hinge on GST; asynchronous families
  ([[algorithms/avalanche]], [[algorithms/dag-based]]) should degrade more
  gracefully. See [[concepts/synchrony-models]] for the model taxonomy.

- **RQ2 (Byzantine load).** Stresses the fault-threshold column. Three of
  the four families share `f < n/3`; Avalanche-style tolerance under
  repeated sampling is parameter-dependent and tighter (see
  [[concepts/quorum-arithmetic]] and [[algorithms/avalanche]]). The
  question targets *how* degradation approaches the break point, not only
  whether it breaks.

- **RQ3 (message cost).** Stresses the cost-concession column:
  `O(n²)` per block for PBFT, `O(n)` per block for DAG-based, per-validator
  `O(K·β)` (independent of `n`) for Avalanche. The independent variable is
  `n` precisely to expose these scaling exponents.

- **RQ4 (adversarial strategies).** Maps adversary strategies onto the axes
  of [[concepts/consensus-properties]]: which strategy threatens Agreement
  (safety), Termination (liveness), or both, per family. The theoretical
  fault taxonomy lives in [[concepts/fault-model]]; the simulator's
  operational adversary catalogue lands under T18
  (`wiki/concepts/adversary-model.md`).

- **RQ5 (Pareto synthesis).** Integrates RQ1–RQ4. The question is whether
  any family dominates across all operating regimes, or whether every family
  occupies a distinct region of the tradeoff space. Prior comparative work
  ([16], [14]) is either qualitative or partial — RQ5 is positioned
  specifically to exceed that baseline.

## Where this plugs into downstream work

- **Experimental matrix (T19).** The (IV, primary metric) columns above
  define the axes of `wiki/concepts/experiment-matrix.md`.
- **Metric definitions (T9 / S7).** Metric definitions, units, and
  computation live in `wiki/concepts/evaluation-metrics.md`.
- **Adversary operationalisation (T18).** RQ4's four strategies become four
  adversary classes in `wiki/concepts/adversary-model.md`.
- **Chapter 4 (T41–T55).** Weeks 8–10 produce the RQ1–RQ4 data.
- **Chapter 5 (T59–T60).** Week 11 synthesises across experiments and
  answers RQ5.

## Source

Imported from `resources/Problem_Statement_and_RQs.md` §3 (Phase 3 — Thesis
Framing). Bracketed numbers `[N]` follow the annotated-bibliography
numbering carried forward from Phase 2; dedicated `wiki/sources/` pages for
[1]–[17] land under S6/T8.

## Revisions

None.
