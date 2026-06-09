# TASKS.md — thesis-consensus work queue

Source of truth for all work. Agents pick one task, flip status, do the
work, push for review. Humans mark Completed on merge.

## Dashboard

- Total tasks: 76 · Sync tasks: 10 · Lint checkpoints: 5 · Lint follow-ups: 4
- Completed: 68 · In Review: 0 · In Progress: 0 · Not Started: 24 · Blocked: 2

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

## Thesis assembly — parallel track (front & back matter)

Front- and back-matter tasks required by the MIT thesis layout but absent
from the weekly Writer queue. **Not bound to the weekly sequence** — safe to
pick up alongside any in-flight task: they touch only `drafts/`, `wiki/`,
and the sibling `../thesis-tex/` repo, never `src/`, so they never conflict
with an Engineer task in progress.

Biography front matter is intentionally omitted (optional under MIT thesis
specs); the `\include{biography}` line has been removed from the template.

- `[x]` **T67** `H` Writer — Draft acknowledgments front matter
  _Outcome:_ Brief acknowledgments page (~half page) for the thesis front
  matter. The agent supplies structure and neutral phrasing only; specific
  names and personal thanks are left as `TODO(human)` for the author. Front
  matter is not wiki knowledge — create no wiki page; append a `log.md`
  entry only. · _Artifact:_ `drafts/front_acknowledgments.md` · _Verify:_
  file exists; every name or personal detail is either author-supplied or
  marked `TODO(human)`; content ports cleanly into
  `../thesis-tex/MIT-thesis-template/acknowledgments.tex`
- `[x]` **T68** `H` Writer — Build the biblatex `.bib` from the wiki bibliography
  _Outcome:_ Convert the consolidated annotated bibliography (`[1]`–`[18]`
  in `wiki/concepts/annotated-bibliography.md`) and the `wiki/sources/*.md`
  pages into a biblatex `.bib` file the MIT template compiles against.
  Define a stable citation-key convention (e.g. `lamport1982bgp`) and record
  the `[N]` ↔ bibkey ↔ source-page mapping so draft citations port
  deterministically. Repoint the template's `\addbibresource` at the new
  file. The `.bib` grows as later chapters cite more — this task lands the
  initial build from the 18 known entries, not the final set. · _Artifact:_
  `../thesis-tex/MIT-thesis-template/references.bib`; updated
  `\addbibresource` in `../thesis-tex/MIT-thesis-template/MIT-Thesis.tex`;
  new `wiki/concepts/citation-keys.md` holding the mapping; update
  `wiki/index.md` · _Verify:_ every `[1]`–`[18]` entry has a matching
  `.bib` record; each record is well-formed biblatex with the required
  fields for its entry type; the mapping page resolves every
  `wiki/sources/*.md` page to exactly one bibkey

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

- `[x]` **T21** `H` Engineer — Implement event scheduler (SimPy or custom)
  _Outcome:_ Working scheduler passing 3+ unit tests · _Design:_ `wiki/concepts/simulation-design.md`, `wiki/concepts/simulation-design-runtime.md` · _Spec:_ `docs/superpowers/specs/2026-05-13-t17-scheduler-design.md` · _Artifact:_ `src/scheduler/` + `wiki/experiments/<date>_scheduler-baseline.md`
- `[x]` **T22** `H` Engineer — Implement node objects with state management
  _Outcome:_ Node class with transitions, message handling, honest/adversarial hooks · _Artifact:_ `src/nodes/`
- `[x]` **T23** `H` Engineer — Implement message passing with configurable delay
  _Outcome:_ Delivery system with delay injection and drop simulation · _Artifact:_ `src/network/`
- `[x]` **T24** `M` Engineer — Add logging for consensus events
  _Outcome:_ Structured event log — core columns `t, node_id, event_type, seq` plus an open `fields` dict — exportable to CSV (Decision A: `round` / `msg_id` have no source in the current event stream; they are `fields` keys populated by protocol code in T28+, not columns) · _Artifact:_ `src/event_log/` (renamed from `src/logging/` — Decision E: a `logging` package on `PYTHONPATH=src` shadows the stdlib module)
- `[x]` **T25** `H` Engineer — Test basic message exchange among nodes
  _Outcome:_ Integration test with 4 nodes; delay distribution matches config · _Artifact:_ `tests/` + experiment page
- `[x]` **T26** `H` Engineer — Set up repo scaffolding: /src, /tests, /configs, /results
  _Outcome:_ Clean structure, README, .gitignore, initial commit · _Artifact:_ repo root
- `[x]` **T27** `M` Engineer — Set up reproducibility: seed control, YAML configs
  _Outcome:_ YAML loader, seed injection; same seed → same output · _Artifact:_ `src/config/` + `wiki/concepts/reproducibility.md`
- `[x]` **L-W4** `M` Linter — Wiki lint pass (end of Week 4)
  _Outcome:_ Report on wiki health before implementation phase · _Artifact:_ `wiki/lint/<date>_report.md`
- `[x]` **L-W4.1** `M` Researcher — Catalog the Diagrams subtree and admit it as an index category (M3a + M3b from L-W4)
  _Outcome:_ Two related edits, landed together because they are the same kind of index-curation work. (i) Amend `docs/wiki-spec.md § Index structure` to add `Diagrams` to the closed category list ("Algorithms, Concepts, Sources, Experiments, Drafts" → "Algorithms, Concepts, Sources, Experiments, Drafts, Diagrams"); the subtree was introduced in W3 (T17/T18/T20) after S8 wrote the original list. (ii) Add a `## Diagrams` section to `wiki/index.md` listing all 11 on-disk pages — `diagrams/index`, `diagrams/runtime/macro`, `diagrams/protocols/{pbft,casper-ffg,snowman,narwhal-tusk}`, `diagrams/scheduler/{bootstrap,event-enqueue,event-dispatch,timer-lifecycle,constraints}` — each with a one-line summary in the same `- [[path]] — summary` style as the other categories. (iii) Add the missing `[[drafts/front_acknowledgments]]` entry under `## Drafts` (T67 artifact present on disk but uncatalogued). · _Artifact:_ updated `docs/wiki-spec.md`, `wiki/index.md` · _Verify:_ M3a and M3b in `wiki/lint/2026-05-21_report.md` resolved — every `wiki/diagrams/*.md` file on disk has exactly one index entry under `## Diagrams`; `drafts/front_acknowledgments` appears under `## Drafts`; `docs/wiki-spec.md § Index structure` category list reads six categories
- `[x]` **L-W4.2** `L` Researcher — Repoint three dead protocol-page wikilinks in `concepts/reproducibility.md` (M2 from L-W4)
  _Outcome:_ `wiki/concepts/reproducibility.md` links to three non-existent pages — `[[algorithms/casper-ffg]]`, `[[algorithms/snowman]]`, `[[algorithms/narwhal-tusk]]` — authored against a protocol-page layout the wiki does not use. The wiki organizes consensus by family page: Casper FFG lives in `wiki/algorithms/pos.md`, Snowman in `wiki/algorithms/avalanche.md`, Narwhal+Tusk in `wiki/algorithms/dag-based.md`. Repoint each link to its family page (with `#section` anchors where an exact section exists; otherwise plain page link is fine). Do not split the family pages — option (b) was explicitly rejected during L-W4 triage. · _Artifact:_ updated `wiki/concepts/reproducibility.md` · _Verify:_ M2 in `wiki/lint/2026-05-21_report.md` resolved — zero dead `[[algorithms/...]]` wikilinks remain in `reproducibility.md`; the three replacement targets each resolve to a real `wiki/algorithms/*.md` file on disk

## Week 5 — PBFT implementation

- `[x]` **T28** `H` Engineer — Implement simplified PBFT proposal logic
  _Outcome:_ Leader proposes, broadcasts pre-prepare, nodes validate · _Artifact:_ `src/pbft/`
- `[x]` **T29** `H` Engineer — Implement PBFT voting and commit/finalization
  _Outcome:_ Full round: pre-prepare → prepare (2f+1) → commit (2f+1) → finalize; full view-change recovery (`VIEW-CHANGE` → `NEW-VIEW` → reissue) — human decision 2026-05-21 supersedes the original "view change stub" scope, reconciling with `wiki/concepts/system-design-protocols.md` §6 ("T29 implements the full recovery path") · _Artifact:_ `src/pbft/`
- `[x]` **T30** `H` Engineer — Test PBFT correctness under honest nodes
  _Outcome:_ Finalizes with 4/7/10 nodes; no forks; latency logged · _Artifact:_ `wiki/experiments/<date>_pbft-baseline.md`
- `[x]` **T31** `M` Engineer — Write unit tests for PBFT
  _Outcome:_ 5+ tests: happy path, insufficient votes, timeout, message loss, multi-round · _Artifact:_ `tests/pbft/`

## Week 6 — PoS implementation + start Ch. 3

- `[x]` **T32** `H` Engineer — Implement simplified PoS-inspired consensus
  _Outcome:_ Validator-based voting; proposer by stake/turn; threshold finality · _Artifact:_ `src/pos/`
- `[x]` **T33** `H` Engineer — Define validator selection / turn-based proposal
  _Outcome:_ Round-robin or weighted random; fairness verified over 100 rounds · _Artifact:_ `src/pos/selection.py` + wiki update
- `[x]` **T34** `H` Engineer — Define voting/finality rule (threshold participation)
  _Outcome:_ Finality when ≥2/3 attest; edge cases tested · _Artifact:_ `src/pos/finality.py`
- `[x]` **T35** `H` Engineer — Test PoS correctness and comparison-ready output
  _Outcome:_ Same CSV format as PBFT · _Artifact:_ `wiki/experiments/<date>_pos-baseline.md`
- `[x]` **T36** `M` Writer — Begin drafting Chapter 3 (Methodology)
  _Outcome:_ 2–3 pages: system model, algorithm descriptions, simulation setup, metrics. First pass covers the two protocols implemented by end of W6 (PBFT, Casper FFG); the remaining two protocols land via T36.1 and T36.2 so Ch. 3 stays consistent with `src/` as it grows. · _Artifact:_ `drafts/ch3_methodology.md`
- `[x]` **T36.1** `M` Writer — Extend Ch. 3 methodology to cover Snowman (unblocked 2026-05-30: T38 Snowman baseline landed)
  _Outcome:_ Pick up once Snowman is implemented in `src/` (currently unscheduled; W7 T38 may absorb it). Add a Snowman subsection to the algorithm-descriptions section of `drafts/ch3_methodology.md`: mechanism (Snowflake → Snowball → Snowman lineage), safety/liveness posture, and how Snowman's parameter rescaling at thesis-scale `n` (`K`, `α_c`, `β`) is handled per [[concepts/metric-reconciliation]]. Update the simulation-setup and metrics sections to reflect Snowman's per-block finality semantics and the empirical safety-violation invariant `(1−α_c/K)^β`. Front matter is not wiki knowledge — append a `log.md` entry only; create no new wiki page. · _Artifact:_ updated `drafts/ch3_methodology.md` · _Verify:_ Ch. 3 covers three protocols (PBFT, Casper FFG, Snowman); the Snowman subsection cites [[algorithms/avalanche]] and the metric-reconciliation page; no `TODO(cite)` left dangling for content that exists in the wiki
- `[!]` **T36.2** `M` Writer — Extend Ch. 3 methodology to cover Narwhal+Tusk (blocked: pending T38.1)
  _Outcome:_ Pick up once Narwhal+Tusk is implemented in `src/`. Add a Narwhal+Tusk subsection to the algorithm-descriptions section of `drafts/ch3_methodology.md`: DAG construction (Narwhal mempool), ordering (Tusk anchor commit), and how the mempool-vs-consensus message-count split and per-anchor-batch finality semantics defined in [[concepts/metric-reconciliation]] are surfaced in the metrics section. Update the system-model section if DAG-output structure forces any model changes beyond the linear-chain assumptions used by the first three protocols. Front matter is not wiki knowledge — append a `log.md` entry only; create no new wiki page. · _Artifact:_ updated `drafts/ch3_methodology.md` · _Verify:_ Ch. 3 covers all four protocols (PBFT, Casper FFG, Snowman, Narwhal+Tusk); the Narwhal+Tusk subsection cites [[algorithms/dag-based]] and the metric-reconciliation page; the metrics section explicitly handles the linear-vs-DAG output asymmetry from T9.1

## Week 7 — Buffer / third algorithm

- `[x]` **T37** `H` Engineer — Assess status: ready for Algorithm 3 or need buffer?
  _Outcome:_ Written assessment; decision gate · _Artifact:_ `wiki/concepts/week7-decision.md`
- `[x]` **T38** `M` Engineer — If ready: implement DAG-based or Avalanche-style consensus
  _Outcome:_ Third algorithm producing same output format. **Scoped by T37 to Snowman**: honest-path build-verification baseline at n=4/7/10 with byte-identical determinism (analogous to T30 / T35); implementation against [[concepts/system-design-protocols]] §4 as the non-binding reference sketch with expected divergences landing as `## Revisions` entries on that page; knobs from [[concepts/metric-reconciliation]] §Snowman parameter rescaling + §Calibration defaults; new `src/snowman/` package + `tests/snowman/` registered as a new Makefile suite; no changes to shared infrastructure (`src/scheduler/`, `src/network/`, `src/nodes/`, `src/event_log/`). Adversarial Snowman → T18 / T51–T53; unified CSV → T40; Ch.3 Snowman extension → T36.1 (unblocks on T38 landing). · _Artifact:_ `src/snowman/`, `tests/snowman/`, `wiki/experiments/<date>_snowman-baseline.md`
- `[!]` **T38.1** `H` Engineer — Implement Narwhal+Tusk (DAG-based fourth protocol) (blocked: pending T55 / scheduled W10→W11 bridge)
  _Outcome:_ Honest-path Narwhal+Tusk build-verification baseline at n=4/7/10 with byte-identical determinism, analogous to T30 (PBFT) / T35 (Casper FFG) / the T38 Snowman baseline. Scheduled between T55 (W10 adversarial summary) and T57 (W11 enhancement), so the three-protocol comparative adversarial evidence ([[concepts/problem-statement]] §Contributions) lands before NWT competes for implementation time. New `src/narwhal_tusk/` package + `tests/narwhal_tusk/` registered as a new Makefile suite; implementation against [[concepts/system-design-protocols]] §5 as the non-binding reference sketch with expected divergences (mempool/consensus split, anchor commit, certificate `2f+1` collection) landing as `## Revisions` entries on that page; knobs from [[concepts/metric-reconciliation]] §Calibration defaults (anchor period `r = 2`). On landing: unblocks T36.2; rewrites [[concepts/adversary-model]] §8 and [[concepts/experiment-matrix-runs]] §8 coverage count from "9 in-scope / 3 deferred-with-T38.1 / 6 catalogued" to "12 in-scope / 6 catalogued"; T40 unified CSV gains the NWT column; seeds the three NWT-adversary follow-on experiments (T51/T52/T53 NWT extensions; §§3–5 generic capabilities only — §6 disrupt-leader and §7.2 data-availability withholding remain catalogued design space). · _Artifact:_ `src/narwhal_tusk/`, `tests/narwhal_tusk/`, `wiki/experiments/<date>_narwhal-tusk-baseline.md`, `## Revisions` entries on [[concepts/system-design-protocols]] / [[concepts/adversary-model]] / [[concepts/experiment-matrix-runs]] · _Verify:_ honest-path baseline reproduces the T30 / T35 / T38 outcome triple (every node decides every committed anchor, no forks, latency logged) at n=4/7/10; byte-identical determinism with the DAG-mempool sampling path exercised; T36.2 status flips from `[!]` Blocked to `[ ]` Not Started
- `[x]` **T39** `H` Engineer — Unified `run()` interface (run_to_completion) + bootstrap-seam fail-fast hardening (superseded 2026-05-27 by W7 decision; original framing assumed the buffer branch the T37 decision did not take)
  _Outcome:_ One helper `run_to_completion(handle, *, t_max, logger) -> (RunResult, EventLogger)` in `src/common/runner.py` collapses the bootstrap tail four callers duplicate (three integration baselines + `src/pos/baseline.py`); five fail-fast guards close the bootstrap seam (A1 `node_id < 0`, A2 non-finite `weight`, B1 duplicate `Network.register`, B2 duplicate `Scheduler.bind`, B3 double `Network.start` — A1/A2/B1 shipped with T22/T23, B2/B3 new in T39); byte-identical determinism and byte-identical `results/pos/baseline.csv` pre/post migration; CSV columns deliberately untouched (T40 owns `[[concepts/output-format]]`); no adversary hook (T18); no multi-seed sweep (T41+). · _Artifact:_ `src/common/runner.py`, `src/common/__init__.py`, `tests/common/test_runner.py`, `wiki/concepts/runner.md`, `## Revisions` blocks on `[[concepts/node-model]]` / `[[concepts/network-model]]` / `[[concepts/simulation-design]]`
- `[x]` **T40** `H` Engineer — Unify output format across all algorithms
  _Outcome:_ (superseded 2026-05-28 by [[concepts/output-format]] §4) Unified per-trial CSV at `results/baseline.csv` with the 18-column subset of the binding ~30-column schema pinned by [[concepts/metric-reconciliation]] §T40; per-protocol reducers in `src/<protocol>/summarise.py`; orchestrator at `src/output/baseline.py`; T35-local CSV writer retired (the seven T35-sketched columns are a strict subset of today's 18). Snowman n=4 skipped from the main CSV and written to a sibling `results/snowman_n4_sanity.csv` per [[concepts/output-format]] §7 and [[concepts/metric-reconciliation]] §Snowman parameter rescaling §Comparative-claim exclusion at n=4. Multi-seed sweeps + 95% CIs + NWT row population + adversarial / delay / workload columns on the wiki extension register, deferred to T41 / T44 / T38.1 / T48–T49 / T51–T54 / T58 respectively. · _Artifact:_ `wiki/concepts/output-format.md`, `src/output/{csv,baseline,schema}.py`, `src/pbft/{baseline,summarise}.py`, `src/pos/{baseline,summarise}.py`, `src/snowman/{baseline,summarise}.py`, `tests/output/`, `tests/{pbft,pos,snowman}/test_summarise.py`, `results/baseline.csv`, `results/snowman_n4_sanity.csv`, `wiki/experiments/2026-05-28_unified-output.md`

## Week 8 — Baseline experiments

- `[x]` **T41** `H` Engineer — Run baseline: vary number of validators
  _Outcome:_ Results for n=4,7,10,16,25 per algorithm; 10+ seeded runs each · _Artifact:_ `results/baseline/` + experiment page
- `[x]` **T42** `H` Engineer — Collect latency, throughput, communication overhead
  _Outcome:_ Full CSV dataset verified for completeness · _Artifact:_ `results/baseline/metrics.csv`
- `[x]` **T43** `H` Engineer — Generate baseline comparison plots
  _Outcome:_ 4+ plots: latency vs n, throughput vs n, msgs vs n, success rate vs n · _Artifact:_ `results/baseline/plots/` · _Done 2026-06-08:_ 6 figures (PNG+PDF) via `src/output/{analysis,plots}.py` from the T41/T70 dataset; latency on the comparable `commit_latency_ms` column (output-format §13); see [[experiments/2026-06-08_baseline-plots]]
- `[x]` **T44** `H` Engineer — Multiple seeds; compute 95% CIs
  _Outcome:_ 20–30 runs per config; mean ± CI on all plots · _Artifact:_ updated plots + stats notes · _Done 2026-06-08:_ 20 seeds/config aggregated to `results/baseline/aggregated.csv` (Student-t df=19) via `src/output/aggregate.py`; plots regenerated with CI bars; statistical-accuracy/meaning audit + base-theory comparison in [[experiments/2026-06-08_baseline-cis]]; structural metrics are deterministic (zero-width CI), only goodput varies (CV≈2.2%)
- `[x]` **T45** `H` Writer — Draft Chapter 4 baseline section
  _Outcome:_ 3–4 pages with plots and initial observations · _Artifact:_ `drafts/ch4_results.md` · _KPI checkpoint_ · _Done 2026-06-08:_ §4.1 roadmap + §4.2 baseline (statistical reliability, latency, throughput/goodput, overhead-vs-base-theory for RQ3, reliability, measurement-point note, Table 4.1); cites Figures 4.1–4.6 + the T43/T44 experiment pages; §4.3/§4.4 reserved for T50/T56
- `[x]` **L-W8** `M` Linter — Wiki lint pass (end of Week 8)
  _Outcome:_ Report before testing phase begins · _Artifact:_ `wiki/lint/<date>_report.md` · _Done 2026-06-09:_ [[lint/2026-06-09_report]] — no High; M1 stale protocol-diagram PDFs, M2 data-plot figure convention/lint gap; 3 Low; all other checks clean

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
- `[ ]` **T69** `H` Writer — Draft the abstract
  _Outcome:_ ~500-word abstract for the MIT front matter, written from the
  finished and revised chapters: problem, method (four-protocol simulation
  study), headline results, contribution. No formulas or special characters
  (MIT thesis spec). Front matter is not wiki knowledge — create no wiki
  page; append a `log.md` entry only. · _Artifact:_ `drafts/front_abstract.md`
  · _Verify:_ ≤500 words; states problem, method, key results, and
  contribution; no math mode or special characters; ports cleanly into
  `../thesis-tex/MIT-thesis-template/abstract.tex`
- `[ ]` **L-W12** `M` Linter — Final wiki lint pass
  _Outcome:_ Final report; any remaining `TODO(cite)` or dead links resolved before submission · _Artifact:_ `wiki/lint/<date>_report.md`

---

## Audit follow-up — fidelity fixes

Cross-cutting follow-up from the 2026-06-04 multi-agent fidelity audit
(implementation vs published-paper coverage). The audit surfaced six MAJOR
findings; this task bundles them into one Engineer pass: three
code-fidelity fixes (each with a step-logged demonstration on a simulated
case) plus three wiki-overclaim corrections. Each fix is gated by a
pre-defined rubric (eval set) recorded on the experiment page. Scope and
the double+surround slashing decision were human-approved 2026-06-04.

- `[x]` **T70** `H` Engineer — Close the six major impl-vs-paper fidelity gaps
  _Outcome:_ Address the six MAJOR findings from the 2026-06-04 audit, each
  gated by a rubric and demonstrated with step-logging on a simulated case.
  **Code fixes** — (1) *Casper FFG accountable safety* (audit #3): detect
  both double-vote and surround-vote slashing in `src/pos/`, emit a
  `casper_slashing` event, surface a slashable-stake fraction; stop
  `EpochState.record_vote` from silently swallowing a conflicting second
  vote by an attester while preserving idempotent-duplicate handling. (2)
  *Snowman genuine Snowball* (audit #5): drive `ConflictSet.preference`
  from the accumulated confidence (argmax over `confidence`), not the last
  sample majority (Snowflake), in `src/snowman/poll.py`; correct the
  `close_round` / `ConflictSet` docstrings. (3) *PBFT client-observed
  finality* (audit #1): add an f+1-matching `REPLY` round so
  `finality_latency_ms` is measured at client-observed finality (one hop
  after the internal `COMMIT` quorum), distinct from `commit_latency_ms`.
  **Wiki corrections** — (4) `message-types.md` watermark contradiction
  (audit #2): the body claims the simulator "caps it at the configured
  high-water mark", which the code never enforces. (5) `pos.md`
  Simulator-mapping overclaims (audit #4): slashing penalty, per-validator
  attestation delay, LMD-GHOST reorgs, safety-cost budget, and validator
  rotation are presented as implemented — rewrite to state what T70 now
  implements (double/surround detection + slashable-stake metric) vs what
  stays deferred (penalty application, LMD-GHOST, attestation delay). Add
  `## Revisions` entries. Determinism preserved (step-logging gated; RNG
  untouched); honest baselines unchanged; new unit + e2e tests per fix.
  · _Artifact:_ `src/pos/`, `src/snowman/`, `src/pbft/`,
  `tests/{pos,snowman,pbft}/`, updated `wiki/concepts/message-types.md`,
  `wiki/algorithms/pos.md`, new
  `wiki/experiments/2026-06-04_t70-fidelity-fixes.md`, `wiki/index.md`,
  `wiki/log.md` · _Verify:_ rubric-coverage table all-green on the
  experiment page; every pre-existing protocol suite still passes
  (`make test`); byte-identical determinism re-run per protocol; each code
  fix carries a logged simulated-case demonstration on the experiment page
  that a reader can re-run from the documented command

---

## Backlog

Agents append here when they notice out-of-scope issues during a task.

- **Make `finality_latency_ms` cross-protocol uniform — add a client-observation hop to Casper FFG and Snowman** (introduced 2026-06-05 by `task/measurement-point-fix`; the structural follow-up flagged in [[concepts/output-format]] §13 Revisions [2026-06-05]). T70 finding #1 added an `f+1` client `REPLY` round to **PBFT only**, so `finality_latency_ms` now measures client-observed finality for PBFT but internal finalisation for Casper FFG and Snowman — not apples-to-apples. The interim contract (output-format §13) routes all cross-protocol latency comparisons through `commit_latency_ms` and forbids cross-protocol `finality_latency_ms`. This task would *restore* `finality_latency_ms` as a comparable column by implementing an equivalent client-observation hop for Casper FFG (post-finalisation client confirmation) and Snowman (post-`β`-acceptance client confirmation), then regenerating the baseline so all three protocols carry the hop. **Real code work — scope deliberately:** decide whether a client-observation hop is even semantically meaningful for epoch-granular FFG finality and counter-`β` Snowman acceptance (it may be a PBFT-specific notion, in which case the right answer is to *keep* `commit_latency_ms` as the canonical cross-protocol column and document why finality is not uniformly comparable — not to force-fit a hop). Touches `src/pos/`, `src/snowman/`, `src/output/`, the baseline dataset, and the output-format contract. Consult the user on measurement methodology before implementing (eval-methodology decision). Priority: M; gates clean cross-protocol *finality* comparisons but not the thesis's latency story, which `commit_latency_ms` already covers. Human to assign a task ID.

- **PBFT baseline numbers shift after T70 client-finality fix — re-run T41/T42** (introduced by T70, 2026-06-04, rubric criterion RX.2). T70 finding #1 added the f+1-`REPLY` round so `finality_latency_ms` is now measured at client-observed finality (one network hop past the internal `COMMIT` quorum) instead of at the COMMIT quorum. The extra `REPLY` deliveries also feed `consensus_msgs_per_acu` and `bytes_per_acu`. So the PBFT rows in the T41 scaling dataset (`results/baseline/baseline.csv`) and the T42 metrics collection are now stale for PBFT (Casper FFG / Snowman rows unaffected). The honest-path *decided* behaviour and fork_rate=0 are unchanged; only the latency/overhead magnitudes move, and only for PBFT. Flagged in `src/pbft/baseline.py` docstring. Priority: M. **When T42** (collect latency/throughput/overhead) is picked up — or sooner if a comparison plot is drafted — regenerate the PBFT rows and note the measurement-point change (commit vs client-observed finality) in the Chapter 4 methodology so the cross-protocol latency comparison is on aligned semantics. **Partially resolved 2026-06-04 (under T70, PR #8):** the dataset was regenerated (`results/baseline/baseline.csv`, provenance `24a491a4`) — PBFT finality now client-observed, overhead includes the REPLY round (`consensus_msgs_per_acu` +0.75→+0.96, `bytes_per_acu` +0.1%; latency unchanged at the T41 zero-delay baseline, so the hop's latency effect surfaces only under the T46/T47 delay regimes); Casper FFG / Snowman value columns unchanged; deltas recorded in [[experiments/2026-06-03_scaling-baseline]] §Revisions. **Remaining for T42/T45:** surface the measurement-point change in the Chapter 4 methodology / latency table. **Structural fix landed 2026-06-05 (branch `task/measurement-point-fix`):** a committee role-play (T42 teaching session) found this was a *data + canonical-doc* defect, not just prose — [[concepts/output-format]] §5.1 still claimed `commit_latency_ms = finality_latency_ms` for PBFT while the dataset has them split. Fixed at the binding schema page (governs figure construction, so the fix is structural not a Ch4 footnote): §13 `## Revisions [2026-06-05]` pins the contract — cross-protocol latency uses `commit_latency_ms` (uniformly defined for all three); `finality_latency_ms` is PBFT-internal only and must not go on a cross-protocol axis until the hop is uniform; §5.1's false bullet flagged superseded. So T43 plots / T45/T56 prose now have a binding comparable-column rule to cite; the remaining Ch4 work is to *state* the measurement-point difference, no longer to *carry* the correctness of the comparison.

- **Dashboard arithmetic.** `TASKS.md` dashboard line previously read "Not Started: 66" when the actual sum was 65 after S0–S5 and T1–T10 completions (total 81 slots across T-tasks + S-tasks + L-tasks, minus 16 completed = 65). Fixed incidentally as part of the S6 flip (now 65 Not Started, 1 In Progress). Watch for re-drift during future flips.
- **Ava Labs documentation as a non-bibliography citation** (introduced by S9 reconciliation). [[algorithms/avalanche]] uses a `[ava-docs]` marker for production-variant details (Snowman, C-Chain / P-Chain / X-Chain, production parameters `K=20, α_c≈0.8K, β≈15`, "sub-second" finality). Per the citation policy, any quantitative claim should ultimately cite a primary paper; the Ava Labs URL is currently the only available source for some production details. Priority: L — watch for Writer tasks quoting `[ava-docs]`-backed performance numbers and flag them; ideally replace with primary-paper corroboration from [9] or [10] when possible.
- **Time-bounded experiments: run-past-`t_max`-then-clip.** The scheduler's `run(t_max)` deadline is overshoot-by-one — it exits when `now >= t_max` *after* a pop (`wiki/concepts/simulation-design.md` §3 D5 / §9), stopping on the first event that reaches `t_max`, so a sibling event scheduled at exactly `t_max` but later in `(t, node_id, seq)` tie-break order can be left unprocessed. **Decision 2026-05-18 (human, reviewing T21):** any time-bounded run (T46/T47 delay experiments, and every `run()` call with a `t_max`) deliberately uses a buffer — `run(t_max = window + buffer)` — so the real measurement boundary is interior to the run and no in-window event is ever truncated; the analysis/output step then *clips* events with `t > window` so reported metrics cover exactly `[0, window]`. Two parameters to pin when the harness (T27/T41) and delay experiments (T46/T47) are designed: (1) buffer size — must exceed the maximum settling time of any in-window action (≥ max network delay; one round/timeout duration is safer); (2) boundary metric semantics — whether an outcome started in-window but completed in the buffer (e.g. a block proposed at `t<window`, committed at `t>window`) counts toward the window's metrics, since clipping alone would drop it. Record in `wiki/concepts/experiment-matrix.md` when T46/T47 are planned.
- **Scheduler heap growth under high timer churn** (noticed in the 2026-05-19 T21 code review). D4 lazy-tombstone cancellation leaves a dead heap entry per `cancel_timer`; D4's rationale bounds garbage by "cancel frequency, which is small at thesis scale." That holds for the baseline, but protocols that reset timers every round across every validator — PBFT view-change timers (T28/T29), and any adaptive-timeout work (T57) — can accumulate a large stale fraction, degrading `heappush`/`heappop` from live-set to cumulative-set size. No test currently asserts tombstones are ever shed. Priority: L. **Watch for** T28/T29/T57: if a run's `RunResult.events_tombstoned` approaches or exceeds `events_processed`, add periodic heap compaction (rebuild when `tombstone_count > len(heap)/2`). Pure optimization — correctness is unaffected.
- **e2e determinism test scope** (noticed in the 2026-05-19 T21 code review). `tests/scheduler/test_e2e.py` `test_two_runs_are_byte_identical` reuses one `LoopbackNetwork` whose broadcast iterates members in dict-insertion order, so it proves "this scenario reproduces," not "the scheduler forces a deterministic order on unordered inputs." The scheduler's own ordering guarantee *is* covered by `test_heap_orders_by_time_then_node_then_seq`. Priority: L. **When T25** (basic message-exchange integration test) is picked up, add a case that schedules a node's downstream events in a deliberately scrambled call order and asserts dispatch still follows `(t, node_id, seq)` — or soften the e2e page's determinism claim to match what the test actually shows.
- **§6 disrupt-leader and §7 protocol-specific adversaries have no experiment task** (noticed reviewing `wiki/concepts/adversary-model.md` against the Week 10 experiment matrix; sibling scope fixes for T53/T54 already folded into those task entries). T51–T53 cover delay / offline / equivocate (catalog §§3–5 only). The catalog defines 21 adversary surfaces; T51–T53 reach roughly half. Uncovered: §6 disrupt-leader (all protocols), §7.1 Snowman colluding sub-sampler, §7.2 Narwhal+Tusk data-availability withholding. Note T18's verify clause asserts "T51–T53 can be expressed as triples drawn from this catalog without gaps" — that claim appears already unmet. **Resolved 2026-05-18 (during T19):** human chose path (b) — narrow the coverage claim, add no new experiment tasks. The catalog stays at 18 valid pairs (superseding the "21 surfaces" figure above — `wiki/concepts/adversary-model.md` §1 is authoritative; the covered subset is 12, not "roughly half"); the 6 §6/§7 pairs are catalogued design space out of experimental scope. T18's verify clause, `adversary-model.md` §1 + §8, `wiki/index.md`, and `wiki/concepts/experiment-matrix.md` §8 all amended to state T51–T53 exercise 12 of 18 pairs.
- **Node event stream: `event_sink` emit-tuple shape + bare event-name strings** (noticed in the 2026-05-19 T22 code review). `Scheduler.bind` routes `Node.emit(event_type, fields, t)` into `event_sink` as the tuple `(t, node_id, EMIT_SEQ, ("emit", event_type, fields))`. That `("emit", event_type, fields)` payload shape is a cross-component seam — `Node.emit` → `Scheduler.event_sink` → T24 `src/logging/` — that no wiki page currently pins. Separately, event-type names are bare string literals (`"halted"` in `src/nodes/node.py`, `"decided"` via `_emit_decided`; protocol-specific events arrive in T28+). Priority: L. **When T24** (logging / structured event schema) is picked up: document the emit-tuple shape as part of the event schema, and consider promoting event-type names to a shared constant/enum so a rename fails fast instead of silently.
- **No public read accessor for `Node._halt_reason`** (noticed in the 2026-05-19 T22 code review). `Node.halt(reason, t)` stores `self._halt_reason` privately and surfaces it only inside the emitted `halted` event; there is no getter. `wiki/concepts/node-model.md` exposes the halt reason solely via that event, so the current state is contract-faithful. Priority: L. **Watch for T32**: if the Casper FFG FSM needs to branch on `SLASHED` vs `EXITED` post-halt without parsing the event stream, add a read-only `halt_reason` property to `Node` (and register it as a `node-model.md` Revision).
- **`Node.__init__` accepts non-finite `weight` (`NaN`, `±inf`)** (noticed in the 2026-05-20 T25 walkthrough Module 2). `Node.__init__` validates `weight < 0`, but `NaN` slips past because `float('nan') < 0` is `False`; `+inf` and `-inf` would also pass or fail unhelpfully. No protocol uses `weight` yet, so the current state is contract-faithful for T22. **Watch for T32** (Casper FFG): `weight` becomes staked balance there, and a `NaN`/`inf` weight from a malformed config would corrupt the FSM's threshold arithmetic silently rather than fail at construction. Fix at `Node.__init__`: reject any non-finite weight with `ValueError` (`math.isfinite(weight)` is the one-liner). Priority: L — pure config-hygiene; precondition for T32. **Resolved 2026-05-27 by T39:** A2 guard in `Node.__init__` (shipped with T22; recorded in T39's `[[concepts/node-model]]` ## Revisions); covered by `tests/nodes/test_node.py::test_nan_weight_rejected` + `test_pos_inf_weight_rejected` + `test_neg_inf_weight_rejected`.
- **`Network.register` / `Scheduler.bind` / `Network.start` lack fail-fast collision-or-repeat checks; `Node.__init__` accepts `node_id = -1` (the `PhaseAdvance` sentinel)** (Network noticed in the 2026-05-19 T23 code review; symmetric scheduler-side issue noticed in the 2026-05-20 T25 walkthrough; the sentinel-collision sub-issue noticed in the same walkthrough's Module 2; `Network.start` idempotency added 2026-05-20 from the same walkthrough's Module 3). Three boundary-seam holes that should be hardened together as a single fail-fast pass: **(a)** `Network.register(node)` — `registry[node.id] = node` — performs no collision check; registering two nodes with the same `id`, or re-registering one, silently clobbers. **(b)** `Scheduler.bind(node)` — `self.nodes[node.id] = node` — has the same hole. **(c)** `Network.start()` is not idempotent — calling it twice re-runs `validate_timeline` (cheap) and re-schedules every interior `PhaseAdvance` boundary, doubling phase-rollover events on the heap; the `_started` flag is set but never checked. All three are asymmetric with the unregistered-`dst` paths in `Network._try_deliver` and `Scheduler._dispatch._node`, which both fail fast with `KeyError`. Separately, `Node.__init__` accepts any `int` as `node_id`, including `-1` — the value the scheduler reserves as the `PhaseAdvance` sentinel for the heap's `(t, node_id, seq)` tie-break (`scheduler.py`); a misconfigured Node with `id = -1` would silently sort with `PhaseAdvance` rather than after it. Fix-together rationale: fail-fast at the `Node.__init__` boundary if `node_id < 0`, at the `bind` / `register` seam if `node.id` is already present, and at `start()` if `self._started` is already true — rather than piecemeal. Priority: L. **Watch for** the T19/T27 experiment harness: when node construction and bootstrap are driven from config, a duplicate/negative `NodeId` or a double-bootstrap should fail fast rather than silently drop a validator, scramble heap ordering, or double-fire phase rollovers. Pure robustness — a well-formed run is unaffected. **Resolved 2026-05-27 by T39:** all four guards land — A1 (`Node.__init__` rejects `node_id < 0`, shipped with T22), B1 (`Network.register` rejects duplicate `node.id`, shipped with T23), B2 (`Scheduler.bind` rejects duplicate `node.id`, new in T39), B3 (`Network.start` rejects second call, new in T39). Recorded in T39's `[[concepts/node-model]]` / `[[concepts/network-model]]` / `[[concepts/simulation-design]]` ## Revisions blocks. Covered by the corresponding one-test-per-guard suite.
- **PBFT-specific network-drop integration test** (raised during T31; human-approved deferral, 2026-05-21). T31's message-loss coverage is unit-level (`tests/pbft/test_message_loss.py`): a lost message is modelled as an `on_message` call that never happens, covering loss within the `2f+1` quorum's `f`-fault tolerance and the view-change recovery past it. End-to-end network *drop* is exercised only generically by `tests/integration/test_drop_rate.py`. A PBFT-specific integration test driving the full W3 stack under a non-zero `drop_rate` — confirming the protocol commits while loss stays within tolerance and recovers via view-change once it exceeds `f` — would de-risk the heavy-loss experiments. Priority: L. **When T47** (heavy delay + packet loss) is picked up, add it to `tests/integration/`.
- **Network e2e tests: stochastic-delay distribution check + full-`RunResult` determinism** (noticed in the 2026-05-19 T23 Task-7 code review). Two follow-ups for **T25** ("Test basic message exchange among nodes; delay distribution matches config"). **(M1)** `tests/network/test_e2e.py` now drives a stochastic (`uniform`) delay end-to-end in two determinism tests, so the RNG-driven delay-sampling path *is* exercised — but no e2e test asserts the delay *distribution shape* matches config (e.g. mean/spread over many seeded runs land within the configured `[low, high]`). T25's "delay distribution matches config" outcome is exactly that check; make sure its plan includes it, not just "a random delay was drawn." **(L1)** the e2e determinism tests compare only the captured delivery stream (`network-model-phases.md §6.4` tuple), not the full `RunResult` (`events_processed`, final `now`, `stopped_by`). Comparing `result` too would catch divergence the stream-only check misses. Priority: L — optional hardening; the delivery stream is the §6.4 contract unit, so the current check is contract-faithful.
- **No coverage tooling — fold a `make coverage` target into T26 scaffolding** (raised during the 2026-05-19 T25 review; human decision to defer rather than widen T25 scope). The repo has no coverage measurement and no dependency manifest. An ad-hoc measurement during the T25 review (stdlib `trace`) put the full suite at 99.8% line coverage of `src/` — 491/492 executable lines; the sole uncovered line is `src/scheduler/scheduler.py:179`, the unreachable defensive `raise` in `_dispatch`'s `else` (`Event` is a closed three-member union, so a coverage gate set at 100% would fail on intentionally-unreachable code). The T25 integration suite alone covers ~64%, by design — it is a cross-component build-verification test, not a coverage test. **When T26** (repo scaffolding) is picked up: add a standing `make coverage` target alongside the `make test` Makefile T25 introduced, and (i) decide the mechanism — stdlib `trace` (no dependency, line coverage only) vs `coverage.py` (branch coverage, accurate, but the repo's first external dependency, requiring the `requirements-dev.txt` / `pyproject.toml` manifest T26 should create anyway); (ii) measure **branch coverage**, not just line coverage — line coverage is already 99.8%, so untaken branches are where real test gaps would surface; (iii) decide whether the target is report-only or enforces a floor. Priority: M.
- **T35 sample CSV needs schema reconciliation in T40** (introduced by T35 itself, 2026-05-25). T35's verify clause asks for "same CSV format as PBFT," but T30 deliberately persisted no CSV (the unified comparative CSV is T40 work, owned by the forward-referenced [[concepts/output-format]] page). To honour the T35 verify clause without anticipating T40's column set, T35 lands a sample `results/pos/baseline.csv` with a T35-local schema — `run_id, algorithm, n_validators, latency_ms, throughput, msg_count, success` (matching the column list `TASKS.md` T40 currently sketches) — written by `src/pos/baseline.py` via `PYTHONPATH=src python3 -m pos.baseline`. Open semantic questions left for T40: (i) `latency_ms` is *median per-node finalisation time of epoch 1*, picked as the first finalised epoch in every scenario; T40 should decide whether the canonical latency is first-epoch, median-across-finalised-epochs, or per-`(run, epoch)` rows; (ii) `throughput` is `decided`-events / `t_max`, but T30 has no per-block `t_max` budget — T40 must pin the throughput definition reconciling PBFT (per-block) vs FFG (per-epoch) finality semantics per [[concepts/metric-reconciliation]] §3; (iii) the row granularity (one row per `(run_id, scenario)` here) may need to expand to `(run_id, scenario, seed)` once T44's CI sweeps land. **When T40** is picked up: reconcile the T35 sample columns against [[concepts/output-format]], decide whether to keep or supersede `results/pos/baseline.csv`, and either retire `src/pos/baseline.py` or fold it into the unified runner. Priority: M. **Resolved 2026-05-28 by T40 (wiki contract):** [[concepts/output-format]] landed with the binding column set + Snowman n=4 policy + extension register. T35's three open semantic questions resolved: (i) `commit_latency_ms` and `finality_latency_ms` are distinct columns with explicit per-protocol formulas (§5 Per-protocol derivation rules); (ii) `tps` is per-protocol per [[concepts/metric-reconciliation]] §Throughput; (iii) row granularity is per-trial — `(run_id, scenario, seed)` — with T44 owning the aggregated sibling file. Code-side reconciliation (retiring `src/pos/baseline.py`'s CSV writer + `results/pos/baseline.csv`) follows in Commit 3 of this task.
- **T32 baseline page reports `casper_block_accepted = 77` for n=4; the code measures 76** (noticed in the 2026-05-25 T35 wiki write-up). Re-running the T32 integration suite under the current code prints `casper_block_accepted: 76` for both the n=4 uniform and n=4 non-uniform scenarios, but the T32 page's result table reports `77`. The n=7 column (`133`) matches the code; the formula `(slots dispatched) × n` gives `19 × 4 = 76`, consistent with the n=7 `19 × 7 = 133` and the T35-measured n=10 `19 × 10 = 190`. Looks like a transcription error during the T32 write-up (the page's `timer_fire` count is 77 for n=4, possibly conflated). Priority: L. **When the next Linter pass** (or a follow-up Researcher edit on the PoS pages) is picked up, correct the two `77` entries on [[experiments/2026-05-23_casper-baseline]] to `76` and adjust the surrounding narrative — no code change needed; the T32 build-verification claim itself is unaffected.
- **Adversary catalogue coverage count temporarily reads 9-of-18, not 12-of-18** (introduced by T37, 2026-05-27). [[concepts/adversary-model]] §8 and [[concepts/experiment-matrix-runs]] §8 currently describe T51–T53 as exercising 12 of 18 valid `(adversary × protocol)` pairs (the §§3–5 capability rows across all four protocols). Under the T37 sequencing decision (Narwhal+Tusk implementation moved to T38.1 between T55 and T57), the W10 adversarial sweep exercises **9** pairs (PBFT + Casper FFG + Snowman × 3 capabilities); the **3** NWT pairs in §§3–5 land as a post-T38.1 follow-on. The catalogue itself is unchanged — the 18-pair design space stays valid; the four-protocol scope is preserved. The §8 wording in both pages will be rewritten to "9 in-scope / 3 deferred-with-T38.1 / 6 catalogued design space" as a `## Revisions` entry **when T38.1 lands**, and back to "12 in-scope / 6 catalogued design space" when the post-T38.1 NWT-adversary follow-on (T51/T52/T53 NWT extensions) lands. Priority: L — pure catalogue-wording drift; no impact on simulator code or in-flight experiments. **Watch for T38.1.**
- **PBFT proposal-phase review follow-ups** (noticed in the 2026-05-21 T28 reviews). Two seams the T28 pre-prepare implementation deliberately leaves for T29/T18, plus minor polish. **(a) Payload-shape validation gap.** `PBFTNode._handle_pre_prepare` binds `pp = msg.payload` and immediately reads `pp.view` with no shape check; a `PRE-PREPARE` envelope carrying `None` or a non-`PrePreparePayload` object would raise `AttributeError` and crash `Node.on_message`, defeating the design's log-and-drop intent (`docs/superpowers/specs/2026-05-21-t28-pbft-proposal-design.md` §7.4 — recipients must not crash on malformed input, because T18 will inject malformed PRE-PREPAREs). Unreachable in T28: only the honest primary produces `PRE-PREPARE` traffic, always with a correct payload. Priority: L. **Watch for T18 / T29:** when adversarial or cross-view messages can carry malformed payloads, add a payload-type guard at the top of `_handle_pre_prepare` that emits `pbft_rejected` (reason `malformed_payload`) instead of letting the `AttributeError` escape. **(b) Propose-side `view_changing` quiescence is unenforced.** `PBFTNode._propose` guards on `_is_primary(self.view)` but not on `self.view_changing`; a node still primary of its current view while `view_changing` is true keeps emitting `PRE-PREPARE`s that every honest recipient rejects under validation Rule 3. Dead in T28 (the view never changes; `view_changing` is never set true outside a hand-set unit test). Priority: L. **When T29** wires view-change: have `_propose` also return early (or cancel the propose timer) while `view_changing` is true, symmetric with the recipient-side Rule 3. **(c) Minor polish, none blocking:** `_reject(**fields)` is loosely typed (a mistyped field name silently lands in the event payload); `PBFTNode.__init__`'s `list(workload or [])` treats an explicit empty-list workload identically to `None`; the `pbft_rejected` event payload schema is non-uniform across emit sites (`unknown_type` carries `msg_type`, the five validation rejections carry `view`/`seq`); no test exercises a non-zero `initial_view` end-to-end; `TestScenarioB_n7` omits the no-voting-messages assertion that `TestScenarioA_n4` carries.
