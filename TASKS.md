# TASKS.md — thesis-consensus work queue

Source of truth for all work. Agents pick one task, flip status, do the
work, push for review. Humans mark Completed on merge.

## Dashboard

- Total tasks: 68 · Sync tasks: 10 · Lint checkpoints: 5 · Lint follow-ups: 2
- Completed: 35 · In Review: 1 · In Progress: 0 · Not Started: 49 · Blocked: 0

## Legend

Status: `[ ]` Not Started · `[~]` In Progress · `[?]` In Review · `[x]` Completed · `[!]` Blocked
Priority: `H` High · `M` Medium · `L` Low

---

## Week 0 — Sync existing work into repo

Bring completed Week 1–2 work into the repo structure. Each sync task pulls
one resource into the appropriate wiki page. Not counted in the 66.

- `[x]` **S0** `H` Researcher — Import BFT Foundation concepts
  _Source:_ `resources/00_BFT_Foundation.md` · _Target:_ `wiki/concepts/{byzantine-generals,flp-impossibility,cap-theorem,consensus-properties,synchrony-models,fault-model,quorum-arithmetic,consensus-families}.md` · _Verify:_ S1–S4 wikilink targets resolve
- `[x]` **S1** `H` Researcher — Import PBFT deep-dive notes
  _Source:_ `resources/01_PBFT_DeepDive.md` · _Target:_ `wiki/algorithms/pbft.md` · _Verify:_ T2 outcomes covered
- `[x]` **S2** `H` Researcher — Import PoS finality deep-dive notes
  _Source:_ `resources/02_PoS_Finality_DeepDive.md` · _Target:_ `wiki/algorithms/pos.md` · _Verify:_ T3 outcomes covered
- `[x]` **S3** `H` Researcher — Import Avalanche deep-dive notes
  _Source:_ `resources/03_Avalanche_DeepDive.md` · _Target:_ `wiki/algorithms/avalanche.md` · _Verify:_ T4 outcomes covered
- `[x]` **S4** `H` Researcher — Import DAG-based deep-dive notes
  _Source:_ `resources/04_DAG_Based_DeepDive.md` · _Target:_ `wiki/algorithms/dag-based.md` · _Verify:_ T5 outcomes covered
- `[x]` **S5** `H` Researcher — Import problem statement + research questions
  _Source:_ <path> · _Target:_ `wiki/concepts/problem-statement.md`, `wiki/concepts/research-questions.md` · _Verify:_ T7, T10
- `[x]` **S6** `H` Researcher — Import annotated bibliography + 8–12 source pages
  _Source:_ <path + raw PDFs> · _Target:_ `wiki/sources/*.md`, `wiki/concepts/annotated-bibliography.md` · _Verify:_ T8
- `[x]` **S7** `H` Researcher — Import evaluation metrics notes
  _Source:_ `resources/Evaluation_Metrics.md` · _Target:_ `wiki/concepts/evaluation-metrics.md` · _Verify:_ T9
- `[x]` **S8** `M` Researcher — Generate initial `wiki/index.md` and `wiki/log.md`
  _Outcome:_ Index reflects S1–S7 pages; log has one retroactive entry per import · _Artifact:_ `wiki/index.md`, `wiki/log.md`
- `[x]` **S9** `M` Linter — Sync completeness check
  _Outcome:_ Confirm every W1–W2 completed task (T1–T10) has a corresponding wiki artifact · _Artifact:_ `wiki/lint/<date>_sync-report.md`

---

## Week 1 — Foundations (reading)

- `[x]` **T1** `H` Researcher — Read introductory materials on blockchain & L1 consensus
  _Outcome:_ Notes on blockchain structure, block creation, why consensus is needed · _Artifact:_ `wiki/concepts/consensus-overview.md`
- `[x]` **T1.1** `H` Researcher — Produce missing T1 artifact `consensus-overview.md`
  _Outcome:_ Introductory page covering blockchain structure, block creation, and why consensus is needed; links outward to the S0 foundation pages (`byzantine-generals`, `fault-model`, `consensus-properties`, etc.) for deeper treatment. New authorship, not a re-do of T1. · _Artifact:_ `wiki/concepts/consensus-overview.md` + update `wiki/index.md` · _Verify:_ S9 lint H1 resolved — file exists on disk, listed under Concepts in `wiki/index.md`, and at least one inbound wikilink from an algorithm or foundation page so it isn't born an orphan
- `[x]` **T2** `H` Researcher — Study PBFT-style consensus in depth
  _Outcome:_ Notes on PBFT phases, 3f+1, view change · _Artifact:_ `wiki/algorithms/pbft.md`
- `[x]` **T3** `H` Researcher — Study simplified PoS voting/finality
  _Outcome:_ Notes on validator voting, attestation, supermajority finality, slashing · _Artifact:_ `wiki/algorithms/pos.md`
- `[x]` **T4** `M` Researcher — Study Avalanche-style probabilistic consensus
  _Outcome:_ Notes on Snowball/Snowflake, subsampled voting, convergence · _Artifact:_ `wiki/algorithms/avalanche.md`
- `[x]` **T5** `M` Researcher — Study DAG-based consensus (Narwhal/Tusk, Mysticeti)
  _Outcome:_ Notes on DAG construction, parallel proposals, ordering · _Artifact:_ `wiki/algorithms/dag-based.md`
- `[x]` **T6** `H` Researcher — Summarize each algorithm in 1–2 pages
  _Outcome:_ 4 summaries covering mechanism, guarantees, assumptions, weaknesses · _Artifact:_ collective: `wiki/algorithms/{pbft,pos,avalanche,dag-based}.md` (Mechanism / Safety / Weaknesses-to-foreground sections on each)
- `[x]` **T7** `H` Researcher — Draft initial problem statement
  _Outcome:_ 1-page statement identifying the gap · _Artifact:_ `wiki/concepts/problem-statement.md`

## Week 2 — Lit review & framing

- `[x]` **T8** `H` Researcher — Review 8–12 papers/surveys on consensus performance & security
  _Outcome:_ Annotated bibliography with contribution/method/limitations · _Artifact:_ `wiki/sources/`, `wiki/concepts/annotated-bibliography.md`
- `[x]` **T9** `H` Researcher — Identify common evaluation metrics from literature
  _Outcome:_ Metric list: latency, throughput, communication overhead, fault tolerance, finality time, fork rate · _Artifact:_ `wiki/concepts/evaluation-metrics.md`
- `[x]` **T9.1** `H` Researcher — Cross-protocol metric reconciliation
  _Outcome:_ Extend `evaluation-metrics.md` to handle the asymmetries introduced by the four-protocol scope (PBFT / Casper FFG / Snowman / Narwhal+Tusk): (i) linear-chain vs DAG output structure; (ii) per-block (PBFT, Snowman) vs per-epoch (Casper FFG) vs per-anchor-batch (Tusk) finality semantics; (iii) mempool-vs-consensus message-count split for Narwhal; (iv) Snowman parameter rescaling rule (`K`, `α_c`, `β`) at thesis-scale `n`. Defines the unified metric schema T40 will implement in code. · _Artifact:_ updated `wiki/concepts/evaluation-metrics.md`; new `wiki/concepts/metric-reconciliation.md` if needed; update `wiki/index.md` · _Verify:_ T40 CSV schema can be expressed in terms defined here; every metric in `evaluation-metrics.md` carries an explicit per-protocol definition or an explicit "not applicable" note; protocol-scope decisions captured here trace back to `[7]`/`[9]`/`[11]` in the bibliography
- `[x]` **T10** `H` Researcher — Define research questions and thesis objectives
  _Outcome:_ RQ1–RQ5 finalized, measurable scope · _Artifact:_ `wiki/concepts/research-questions.md`
- `[x]` **T11** `H` Writer — Write Chapter 1 draft (Introduction)
  _Outcome:_ 3–5 pages: background, motivation, problem statement, objectives, RQs · _Artifact:_ `drafts/ch1_intro.md`
- `[x]` **T12** `H` Writer — Write initial Chapter 2 draft (Literature Review)
  _Outcome:_ 3–5 pages on blockchain basics, consensus families, existing evaluations · _Artifact:_ `drafts/ch2_litreview.md`
- `[x]` **T13** `H` Researcher — Finalize thesis title and scope
  _Outcome:_ Confirmed title, included/excluded scope, supervisor sign-off · _Artifact:_ update `wiki/concepts/problem-statement.md` · _KPI checkpoint_
- `[x]` **L-W2** `M` Linter — Wiki lint pass (end of Week 2)
  _Outcome:_ Triaged report of orphans, missing pages, contradictions, index drift · _Artifact:_ `wiki/lint/<date>_report.md`
- `[x]` **L-W2.1** `M` Researcher — Resolve stale `TODO(cite)` markers superseded by S6/S9 (M2 from L-W2)
  _Outcome:_ Three foundation pages carry `TODO(cite)` markers asking for source-page resolution that S6/S9 already completed. Replace each with the appropriate `[[sources/...]]` wikilink (or rewrite as a pointer to `[[concepts/annotated-bibliography]]`): (i) `wiki/concepts/byzantine-generals.md:36` → `[[sources/2026-04-21_lamport-shostak-pease-bgp-1982]]` ([1]); (ii) `wiki/concepts/flp-impossibility.md:38` → `[[sources/2026-04-21_flp-impossibility-1985]]` ([2]); (iii) `wiki/concepts/problem-statement.md:167` — the "once S6 lands" sentence is now factual; rewrite as a pointer to the bibliography page or delete. · _Artifact:_ updated `wiki/concepts/{byzantine-generals,flp-impossibility,problem-statement}.md` · _Verify:_ M2 in `wiki/lint/2026-05-06_report.md` resolved — zero `TODO(cite)` markers remain on the three pages; replacement wikilinks resolve on disk
- `[x]` **L-W2.2** `L` Researcher — Ingest Gilbert–Lynch 2002 CAP proof as `[18]` (L1 from L-W2)
  _Outcome:_ Add Gilbert & Lynch's 2002 formal proof of the CAP conjecture to the consolidated bibliography as new entry `[18]`; create the dedicated source page following the S6 template; replace the `TODO(cite)` on `wiki/concepts/cap-theorem.md:33` with the new `[[sources/...]]` wikilink. Sweep for any places that hard-code `[1]–[17]` as a closed range and update to `[1]–[18]`. · _Artifact:_ `wiki/sources/<date>_gilbert-lynch-cap-2002.md`, updated `wiki/concepts/{annotated-bibliography,cap-theorem}.md`, `wiki/index.md` · _Verify:_ L1 in `wiki/lint/2026-05-06_report.md` resolved — `[18]` resolves to a source page; `cap-theorem.md` cites the formal proof; bibliography upper-bound text reads `[1]–[18]`

## Week 3 — System modeling

- `[x]` **T14** `H` Engineer — Define node model (validator states, roles)
  _Outcome:_ Node class design; states (idle, proposing, voting, committed); role assignment · _Artifact:_ `wiki/concepts/node-model.md`
- `[x]` **T15** `H` Engineer — Define network model (delays, packet loss)
  _Outcome:_ Uniform/normal/exponential delay, configurable drop rate, jitter params · _Artifact:_ `wiki/concepts/network-model.md` (split: also `wiki/concepts/network-model-phases.md` per `docs/wiki-spec.md` § Page size)
- `[x]` **T16** `H` Engineer — Define message types and protocol rounds
  _Outcome:_ Catalog: Propose, Vote, Commit, Finalize, Query with fields/sizes · _Artifact:_ `wiki/concepts/message-types.md`
- `[x]` **T17** `H` Engineer — Define event-driven simulation logic
  _Outcome:_ Event scheduler design: queue, time advancement, callback registration · _Artifact:_ `wiki/concepts/simulation-design.md`
- `[x]` **T18** `H` Engineer — Define adversarial behavior categories (per-protocol)
  _Outcome:_ Adversary catalog spanning the four-protocol scope (PBFT / Casper FFG / Snowman / Narwhal+Tusk), in two layers. **(1) Four generic categories** — delayer, equivocator, non-participant, leader-disruptor — each given an explicit per-protocol semantics row or marked `N/A` with justification (leader-disruptor is `N/A` for Snowman; Snowman equivocation reduces to a weaker "lying responder" form and must be flagged as such). **(2) Protocol-specific adversaries** — at minimum: Snowman colluding sub-sampler (coordinated query responses biasing `α_c` counts); Narwhal+Tusk data-availability withholding (worker certifies header but withholds batch contents); Casper FFG slashable equivocation refinements (surround vote, double vote with explicit slashing semantics). Each entry specifies: adversary action, victim protocol(s), measurable effect on safety vs liveness, configuration knobs (% of stake/nodes affected, intensity), and the invariant to be verified by simulator instrumentation. · _Artifact:_ `wiki/concepts/adversary-model.md` + update `wiki/index.md` · _Verify:_ every generic adversary has a per-protocol semantics row or an `N/A` justification; every protocol-specific adversary traces to its source paper (`[4]` / `[7]` / `[9]` / `[11]`); T51–T53 (Week 10 adversarial experiments) can be expressed as `(adversary_id, protocol_id, intensity)` triples drawn from this catalog — exercising the 12 generic-capability pairs under §§3–5; the 6 pairs under §6 (disrupt-leader) and §7 (protocol-specific surfaces) are catalogued design space deliberately out of experimental scope (human decision 2026-05-18, see § Backlog)
- `[x]` **T19** `M` Engineer — Design experiment parameter space
  _Outcome:_ Matrix: validator counts, delay ranges, adversary fractions, timeouts, seeds · _Artifact:_ `wiki/concepts/experiment-matrix.md`
- `[x]` **T20** `H` Engineer — Produce system design diagram + pseudocode
  _Outcome:_ Architecture diagram + pseudocode for each protocol main loop · _Artifact:_ `wiki/concepts/system-design.md`

## Week 4 — Simulator skeleton

- `[?]` **T21** `H` Engineer — Implement event scheduler (SimPy or custom)
  _Outcome:_ Working scheduler passing 3+ unit tests · _Design:_ `wiki/concepts/simulation-design.md`, `wiki/concepts/simulation-design-runtime.md` · _Spec:_ `docs/superpowers/specs/2026-05-13-t17-scheduler-design.md` · _Artifact:_ `src/scheduler/` + `wiki/experiments/<date>_scheduler-baseline.md`
- `[ ]` **T22** `H` Engineer — Implement node objects with state management
  _Outcome:_ Node class with transitions, message handling, honest/adversarial hooks · _Artifact:_ `src/nodes/`
- `[ ]` **T23** `H` Engineer — Implement message passing with configurable delay
  _Outcome:_ Delivery system with delay injection and drop simulation · _Artifact:_ `src/network/`
- `[ ]` **T24** `M` Engineer — Add logging for consensus events
  _Outcome:_ Structured logs (timestamp, node_id, event_type, round, msg_id) exportable to CSV · _Artifact:_ `src/logging/`
- `[ ]` **T25** `H` Engineer — Test basic message exchange among nodes
  _Outcome:_ Integration test with 4 nodes; delay distribution matches config · _Artifact:_ `src/tests/` + experiment page
- `[ ]` **T26** `H` Engineer — Set up repo scaffolding: /src, /tests, /configs, /results
  _Outcome:_ Clean structure, README, .gitignore, initial commit · _Artifact:_ repo root
- `[ ]` **T27** `M` Engineer — Set up reproducibility: seed control, YAML configs
  _Outcome:_ YAML loader, seed injection; same seed → same output · _Artifact:_ `src/config/` + `wiki/concepts/reproducibility.md`
- `[ ]` **L-W4** `M` Linter — Wiki lint pass (end of Week 4)
  _Outcome:_ Report on wiki health before implementation phase · _Artifact:_ `wiki/lint/<date>_report.md`

## Week 5 — PBFT implementation

- `[ ]` **T28** `H` Engineer — Implement simplified PBFT proposal logic
  _Outcome:_ Leader proposes, broadcasts pre-prepare, nodes validate · _Artifact:_ `src/pbft/`
- `[ ]` **T29** `H` Engineer — Implement PBFT voting and commit/finalization
  _Outcome:_ Full round: pre-prepare → prepare (2f+1) → commit (2f+1) → finalize; view change stub · _Artifact:_ `src/pbft/`
- `[ ]` **T30** `H` Engineer — Test PBFT correctness under honest nodes
  _Outcome:_ Finalizes with 4/7/10 nodes; no forks; latency logged · _Artifact:_ `wiki/experiments/<date>_pbft-baseline.md`
- `[ ]` **T31** `M` Engineer — Write unit tests for PBFT
  _Outcome:_ 5+ tests: happy path, insufficient votes, timeout, message loss, multi-round · _Artifact:_ `src/tests/pbft/`

## Week 6 — PoS implementation + start Ch. 3

- `[ ]` **T32** `H` Engineer — Implement simplified PoS-inspired consensus
  _Outcome:_ Validator-based voting; proposer by stake/turn; threshold finality · _Artifact:_ `src/pos/`
- `[ ]` **T33** `H` Engineer — Define validator selection / turn-based proposal
  _Outcome:_ Round-robin or weighted random; fairness verified over 100 rounds · _Artifact:_ `src/pos/selection.py` + wiki update
- `[ ]` **T34** `H` Engineer — Define voting/finality rule (threshold participation)
  _Outcome:_ Finality when ≥2/3 attest; edge cases tested · _Artifact:_ `src/pos/finality.py`
- `[ ]` **T35** `H` Engineer — Test PoS correctness and comparison-ready output
  _Outcome:_ Same CSV format as PBFT · _Artifact:_ `wiki/experiments/<date>_pos-baseline.md`
- `[ ]` **T36** `M` Writer — Begin drafting Chapter 3 (Methodology)
  _Outcome:_ 2–3 pages: system model, algorithm descriptions, simulation setup, metrics · _Artifact:_ `drafts/ch3_methodology.md`

## Week 7 — Buffer / third algorithm

- `[ ]` **T37** `H` Engineer — Assess status: ready for Algorithm 3 or need buffer?
  _Outcome:_ Written assessment; decision gate · _Artifact:_ `wiki/concepts/week7-decision.md`
- `[ ]` **T38** `M` Engineer — If ready: implement DAG-based or Avalanche-style consensus
  _Outcome:_ Third algorithm producing same output format · _Artifact:_ `src/<alg3>/`
- `[ ]` **T39** `H` Engineer — If buffer: stabilize PBFT & PoS, fix bugs, unify interface
  _Outcome:_ Known bugs fixed, edge cases handled, unified `run()` interface · _Artifact:_ `src/common/runner.py`
- `[ ]` **T40** `H` Engineer — Unify output format across all algorithms
  _Outcome:_ Common CSV: run_id, algorithm, n_validators, latency_ms, throughput, msg_count, success · _Artifact:_ `wiki/concepts/output-format.md`

## Week 8 — Baseline experiments

- `[ ]` **T41** `H` Engineer — Run baseline: vary number of validators
  _Outcome:_ Results for n=4,7,10,16,25 per algorithm; 10+ seeded runs each · _Artifact:_ `results/baseline/` + experiment page
- `[ ]` **T42** `H` Engineer — Collect latency, throughput, communication overhead
  _Outcome:_ Full CSV dataset verified for completeness · _Artifact:_ `results/baseline/metrics.csv`
- `[ ]` **T43** `H` Engineer — Generate baseline comparison plots
  _Outcome:_ 4+ plots: latency vs n, throughput vs n, msgs vs n, success rate vs n · _Artifact:_ `results/baseline/plots/`
- `[ ]` **T44** `H` Engineer — Multiple seeds; compute 95% CIs
  _Outcome:_ 20–30 runs per config; mean ± CI on all plots · _Artifact:_ updated plots + stats notes
- `[ ]` **T45** `H` Writer — Draft Chapter 4 baseline section
  _Outcome:_ 3–4 pages with plots and initial observations · _Artifact:_ `drafts/ch4_results.md` · _KPI checkpoint_
- `[ ]` **L-W8** `M` Linter — Wiki lint pass (end of Week 8)
  _Outcome:_ Report before testing phase begins · _Artifact:_ `wiki/lint/<date>_report.md`

## Week 9 — Network delay experiments

- `[ ]` **T46** `H` Engineer — Inject moderate delay (100–500ms)
  _Outcome:_ Per-algorithm latency/throughput changes · _Artifact:_ `wiki/experiments/<date>_delay-moderate.md`
- `[ ]` **T47** `H` Engineer — Inject heavy delay (1–5s) + packet loss
  _Outcome:_ Degradation under 5–20% loss; success rate measured · _Artifact:_ `wiki/experiments/<date>_delay-heavy.md`
- `[ ]` **T48** `H` Engineer — Compare latency growth and success rate across algorithms
  _Outcome:_ Comparative plot + resilience ranking table · _Artifact:_ `results/delay/`
- `[ ]` **T49** `H` Engineer — Analyze which algorithm degrades most gracefully
  _Outcome:_ 1–2 page analysis: breakpoints, which is most robust and why · _Artifact:_ `wiki/experiments/<date>_delay-analysis.md`
- `[ ]` **T50** `H` Writer — Produce delay plots and written observations in Ch. 4
  _Outcome:_ 6+ plots, 2-page observations integrated · _Artifact:_ `drafts/ch4_results.md`

## Week 10 — Adversarial experiments

- `[ ]` **T51** `H` Engineer — Simulate delayed voters (intentionally slow nodes)
  _Outcome:_ 10–30% slow nodes (2–10× normal delay); impact on finality time · _Artifact:_ experiment page
- `[ ]` **T52** `H` Engineer — Simulate non-participating validators (offline)
  _Outcome:_ 10–33% offline; success/failure boundary identified · _Artifact:_ experiment page
- `[ ]` **T53** `H` Engineer — Simulate equivocating nodes
  _Outcome:_ Conflicting votes across the four-protocol scope; per-protocol safety invariant measured (see T54); intensity sweep includes above-threshold f > 1/3 runs (at least PBFT and Casper FFG) to expose the safety cliff that the catalog documents (`wiki/concepts/adversary-model.md` §5, §7.1, §7.3) · _Artifact:_ experiment page
- `[ ]` **T54** `H` Engineer — Measure liveness and safety degradation
  _Outcome:_ Liveness = % rounds reaching consensus. Safety = four per-protocol invariants from `wiki/concepts/adversary-model.md` "Invariant checked" columns — Casper FFG: slashable stake fraction (§7.3); Snowman: empirical violation rate vs. bound `(1−α_c/K)^β` (§7.1); PBFT: view-change rate, since equivocation converts to leader rotation (§5); Narwhal+Tusk: whether a conflicting header reaches `2f+1` signatures (§5). A universal fork/inconsistency count is insufficient — PBFT and Narwhal+Tusk cannot fork below the 1/3 threshold, so a fork counter reads zero and measures nothing. · _Artifact:_ metrics spec + plots
- `[ ]` **T55** `H` Engineer — Produce adversarial comparison tables
  _Outcome:_ Summary: algorithm × adversary × metric; robustness ranking · _Artifact:_ `results/adversarial/` · _KPI checkpoint_
- `[ ]` **T56** `H` Writer — Draft performance–security tradeoff discussion
  _Outcome:_ 2–3 page analysis answering RQ4 · _Artifact:_ `drafts/ch4_results.md`
- `[ ]` **L-W10** `M` Linter — Wiki lint pass (end of Week 10)
  _Outcome:_ Report before writing crunch · _Artifact:_ `wiki/lint/<date>_report.md`

## Week 11 — Enhancement + findings

- `[ ]` **T57** `M` Engineer — Implement adaptive timeout (exp backoff + jitter)
  _Outcome:_ `base × 2^(failures) + jitter`, calibrated to observed RTT · _Artifact:_ `src/common/timeout.py` + wiki page
- `[ ]` **T58** `M` Engineer — Compare baseline vs enhanced
  _Outcome:_ Side-by-side latency + success rate under delay/adversary · _Artifact:_ experiment page + plots
- `[ ]` **T59** `H` Writer — Summarize key findings across experiments
  _Outcome:_ Top 5–10 findings with evidence and RQ mapping · _Artifact:_ `wiki/concepts/key-findings.md`
- `[ ]` **T60** `H` Writer — Write Chapter 5 (Enhancement) and Chapter 6 (Conclusion)
  _Outcome:_ Ch5 3–4 pages; Ch6 2–3 pages summary + future work · _Artifact:_ `drafts/ch5_enhancement.md`, `drafts/ch6_conclusion.md`

## Week 12 — Polish & defense

- `[ ]` **T61** `H` Writer — Revise all chapters for consistency
  _Outcome:_ Terminology consistent, no contradictions, references complete · _Artifact:_ `drafts/`
- `[ ]` **T62** `H` Writer — Improve all figures, tables, captions
  _Outcome:_ Publication-quality: labeled axes, legends, consistent colors · _Artifact:_ `results/` + `drafts/`
- `[ ]` **T63** `H` Writer — Verify objectives ↔ experiments ↔ conclusions alignment
  _Outcome:_ Traceability matrix: RQ → experiment → conclusion · _Artifact:_ `wiki/concepts/traceability-matrix.md`
- `[ ]` **T64** `H` Writer — Prepare presentation slides
  _Outcome:_ 15–20 Marp slides: title, problem, methodology, results, demo, Q&A · _Artifact:_ `drafts/defense.md` (Marp)
- `[ ]` **T65** `H` Writer — Rehearse oral defense
  _Outcome:_ 2+ rehearsals; 15–20 min; answers to 10 expected questions · _Artifact:_ rehearsal notes in `wiki/log.md`
- `[ ]` **T66** `H` Engineer — Final code package + README + reproducibility check
  _Outcome:_ Zip archive: code, configs, seeds, README, sample output verified · _Artifact:_ `results/release/` · _KPI checkpoint_
- `[ ]` **L-W12** `M` Linter — Final wiki lint pass
  _Outcome:_ Final report; any remaining `TODO(cite)` or dead links resolved before submission · _Artifact:_ `wiki/lint/<date>_report.md`

---

## Backlog

Agents append here when they notice out-of-scope issues during a task.

- **Dashboard arithmetic.** `TASKS.md` dashboard line previously read "Not Started: 66" when the actual sum was 65 after S0–S5 and T1–T10 completions (total 81 slots across T-tasks + S-tasks + L-tasks, minus 16 completed = 65). Fixed incidentally as part of the S6 flip (now 65 Not Started, 1 In Progress). Watch for re-drift during future flips.
- **Ava Labs documentation as a non-bibliography citation** (introduced by S9 reconciliation). [[algorithms/avalanche]] uses a `[ava-docs]` marker for production-variant details (Snowman, C-Chain / P-Chain / X-Chain, production parameters `K=20, α_c≈0.8K, β≈15`, "sub-second" finality). Per the citation policy, any quantitative claim should ultimately cite a primary paper; the Ava Labs URL is currently the only available source for some production details. Priority: L — watch for Writer tasks quoting `[ava-docs]`-backed performance numbers and flag them; ideally replace with primary-paper corroboration from [9] or [10] when possible.
- **§6 disrupt-leader and §7 protocol-specific adversaries have no experiment task** (noticed reviewing `wiki/concepts/adversary-model.md` against the Week 10 experiment matrix; sibling scope fixes for T53/T54 already folded into those task entries). T51–T53 cover delay / offline / equivocate (catalog §§3–5 only). The catalog defines 21 adversary surfaces; T51–T53 reach roughly half. Uncovered: §6 disrupt-leader (all protocols), §7.1 Snowman colluding sub-sampler, §7.2 Narwhal+Tusk data-availability withholding. Note T18's verify clause asserts "T51–T53 can be expressed as triples drawn from this catalog without gaps" — that claim appears already unmet. **Resolved 2026-05-18 (during T19):** human chose path (b) — narrow the coverage claim, add no new experiment tasks. The catalog stays at 18 valid pairs (superseding the "21 surfaces" figure above — `wiki/concepts/adversary-model.md` §1 is authoritative; the covered subset is 12, not "roughly half"); the 6 §6/§7 pairs are catalogued design space out of experimental scope. T18's verify clause, `adversary-model.md` §1 + §8, `wiki/index.md`, and `wiki/concepts/experiment-matrix.md` §8 all amended to state T51–T53 exercise 12 of 18 pairs.
