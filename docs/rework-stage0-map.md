# Rework Stage 0 — section map

Per-section analysis of the current Week-7 drafts (`ch1_intro.md`,
`ch2_litreview.md`, `ch3_methodology.md`), as input to the targeted
rework. For each section: **what it says**, **what it is for**, **how it
connects**, **rubric flags** (R1–R7, see `docs/rework-rubric.md`), and a
**verdict** — KEEP (leave as-is), TRIM (cut scaffolding, keep content),
REWRITE (content stays but must be re-expressed concretely), CUT (remove),
ADD (new material the supervisor demands that no current section carries).

Diagnosis in one line: the *facts* are mostly present and correct; the
chapters spend too many words framing them (R1/R2) and too few making the
four mechanisms and the simulation **concrete and comparable** (R3/R4).
The fix is density + concreteness, not reorganization — the chapter order
(Intro → Lit Review → Methodology) is sound.

---

## Chapter 1 — Introduction

### §1.1 Background
- **Says.** Defines an L1 blockchain as a replicated append-only log;
  recalls the three impossibilities (Byzantine Generals 3f+1, FLP, partial
  synchrony f<n/3); names the four families as four points in that design
  space and gives each a one-paragraph cost summary.
- **For.** Establish the shared theoretical frame all four families relax,
  and the claim that performance and security stop being independent under
  stress.
- **Connects.** Feeds §1.2 (motivation) and is the seed of Ch2 §2.2–§2.3,
  which develop the same material at lit-review depth.
- **Flags.** R7 (2–3 wikilinks mid-clause throughout). The four-family
  cost paragraph is good raw material for the R3 comparison artifact but is
  currently prose-only, no contrast surfaced.
- **Verdict.** TRIM + REWRITE-light. Keep the substance; thin the
  citations; convert the four-family paragraph toward a contrast the reader
  can see (preview of the R3 artifact that lands fully in Ch2).

### §1.2 Motivation
- **Says.** L1 consensus determines finality/liveness/safety; lists which
  production chains use which family; catalogs real mainnet incidents
  (Solana halts, Ethereum reorg + finality stall, Cosmos, Sui); argues
  publication benchmarks don't combine the stress conditions that live
  operation does; states the performance–security coupling.
- **For.** This is the **"why this comparison"** section — exactly what the
  supervisor asked for. The concrete anchors (R5) already live here.
- **Connects.** Sets up the gap that §1.3 problem statement and Ch2 §2.5
  formalize.
- **Flags.** R5 is *almost* satisfied but inverted: the concrete incidents
  are strong, yet they're wrapped in abstract framing ("the
  performance–security coupling is invisible to benign-condition
  benchmarks") that buries the lede. R2 (several meta sentences telling the
  reader what to conclude).
- **Verdict.** REWRITE for ordering. Lead with the concrete failure
  (Solana 17-hour halt), then generalize. Cut the abstract coupling prose
  to one sentence. Highest-leverage section for the "why" — gets the reader
  hooked in the first paragraph.

### §1.3 Problem statement
- **Says.** States the thesis: comparative performance–security behavior of
  the four families under controlled delay + adversary in a unified
  discrete-event simulator; contribution is a reproducible framework, not a
  production benchmark; names the Gervais et al. methodology being extended;
  organizes around a Pareto frontier.
- **For.** The one-paragraph "what this thesis does" anchor.
- **Connects.** Names the metric schema (Ch3 §3.5) and the Gervais
  precedent (Ch2 §2.5.2); frames RQ5 (§1.5).
- **Flags.** R2 (repeats framing already in §1.1–§1.2). "Pareto frontier"
  introduced with no concrete gloss (R5-adjacent — a beginner reader needs
  one anchor).
- **Verdict.** TRIM. Keep it tight — this should be the shortest, sharpest
  paragraph in the chapter. Remove overlap with §1.2.

### §1.4 Scope and assumptions
- **Says.** In scope: configurable delay distributions, packet loss, three
  Byzantine behaviors, sets up to several hundred nodes. Out of scope: PoW
  as subject, L2, testnet/mainnet, economics, crypto-primitive perf. Four
  framing assumptions. Three reasons simulation over testnet.
- **For.** Bound the work honestly; pre-empt "why not measure real chains".
- **Connects.** The "why simulate" reasons here directly answer the
  supervisor's "say how you simulate" at the *motivation* level (the
  *mechanics* are Ch3 §3.2/§3.4).
- **Flags.** Mostly fine. Mild R2. The three reasons-to-simulate are
  valuable and under-emphasized.
- **Verdict.** KEEP + light TRIM. Promote the three reasons-to-simulate so
  they're not lost; they're part of the answer the supervisor wants.

### §1.5 Research questions
- **Says.** RQ1 (latency vs delay variance), RQ2 (throughput vs Byzantine
  fraction), RQ3 (communication overhead / scaling exponent), RQ4
  (adversary → property), RQ5 (Pareto synthesis). Each with an italic gloss.
- **For.** The empirical backbone; every Ch4 result maps to one RQ.
- **Connects.** Each RQ binds to a metric subset (§3.5) and an experiment
  axis (§3.4); RQ5 is the headline (§1.3, Ch5).
- **Flags.** Minor R2 (the "RQ1–RQ4 generate the data; RQ5 synthesizes it"
  line is fine; the per-RQ italic meta-glosses are borderline). Otherwise
  this is concrete and should stay.
- **Verdict.** KEEP. This is one of the most information-dense sections —
  the model for the rest.

### §1.6 Contributions and roadmap
- **Says.** Four contributions (artifact, implementations, dataset, method
  framing); chapter-by-chapter roadmap.
- **For.** Standard thesis closing of an intro.
- **Flags.** R1/R2 — the roadmap paragraph is pure preview.
- **Verdict.** TRIM. Keep the four contributions (concrete). Compress the
  roadmap to 2–3 sentences.

---

## Chapter 2 — Literature Review

### §2.1 Chapter roadmap
- **Says.** Recaps Ch1; states three claims C1/C2/C3; lists what each
  subsection will do.
- **For.** Frame the chapter.
- **Flags.** R1 + R2, heaviest offender in the chapter. Entirely preview
  and recap.
- **Verdict.** CUT to ~3 sentences. Keep C1/C2/C3 only if they earn their
  keep as a one-line thesis-of-the-chapter; drop the per-section preview
  and the Ch1 recap entirely. The C1/C2/C3 labels are then referenced once,
  not threaded through every later paragraph.

### §2.2 Blockchains and the consensus problem
- **Says.** Replicated-log framing; the three foundational results
  (Lamport 3f+1, FLP, DLS partial synchrony); the concession axes; CAP
  projected onto chains; the three consensus properties (Agreement,
  Validity, Termination).
- **For.** Establish the shared frame (claim C1) at depth.
- **Connects.** Overlaps §1.1 by design (Ch1 previews, Ch2 develops);
  feeds §2.3.
- **Flags.** R2 (some "the next section maps…" connective tissue). Content
  is solid and appropriately concrete for a lit review.
- **Verdict.** TRIM. Cut the inter-section connective sentences; keep the
  theory. This section is mostly doing its job.

### §2.3 The design space the impossibilities create
- **Says.** PBFT sits at 3f+1/partial-synchrony; the other three branches
  are "which assumption to loosen next" — PoS adds economics, Avalanche
  drops quorums for sampling, DAG splits availability from ordering.
  References Figure 2.1 (family tree).
- **For.** Show the four families as principled relaxations (C1), not
  arbitrary — the conceptual setup for the R3 contrast.
- **Connects.** Directly into §2.4; Figure 2.1 is the visual spine.
- **Flags.** This is the *right place* to begin the R3 comparison but it
  currently describes the branches abstractly. Good bones, needs
  concreteness.
- **Verdict.** REWRITE toward R3. This paragraph + Figure 2.1 should carry
  the "here is the fork in the road" contrast that §2.4 then fills in
  per-family.

### §2.4 The four families (Table 2.1 + §2.4.1–§2.4.4)
- **Says.** Table 2.1 = design-space scorecard (synchrony / finality /
  fault threshold / cost). Each subsection: mechanism, guarantees+
  assumption, documented adversarial weakness, simulator role.
- **For.** The core of the chapter and the **primary R3 battleground** —
  this is where "how do the four differ" must be answered.
- **Connects.** Table 2.1 ↔ Ch3 §3.3 (implementation-level mirror of the
  same four); adversarial-weakness paragraphs ↔ RQ4.
- **Flags.** **R3 fail.** Each family gets competent abstract prose but
  (a) no worked instance (n=4, actual quorum/sample numbers), and (b) the
  four are never lined up to expose the *difference* — the reader must
  hold four separate descriptions in their head and diff them manually.
  This is the supervisor's single biggest complaint.
- **Verdict.** REWRITE + ADD. Keep the four mechanism paragraphs as source
  material. ADD the R3 comparison artifact: a step-by-step table or a
  one-block trace across all four (PBFT 2f+1 commit quorum / Casper two-
  epoch 2/3-stake / Snowman β consecutive K-majorities / Narwhal+Tusk
  DAG-order). Add a small worked instance to each. This is where the most
  *new* writing goes.

### §2.5 Existing comparative evaluations (§2.5.1, §2.5.2, Table 2.2)
- **Says.** §2.5.1: each family reported in its own vocabulary (ops/s,
  epochs, ε, ktps); Table 2.2 collects headline numbers and argues they're
  incomparable. §2.5.2: three surveys (Bano, Xiao, Cachin–Vukolić) measure
  nothing; Gervais et al. is the one quantitative precedent but on PoW.
- **For.** Establish C2 (vocabulary fragmentation) and C3 (no unified
  harness exists) — the gap the thesis fills.
- **Connects.** C3 → §1.3 problem statement and §2.6; Table 2.2 is the
  evidence for "why a unified harness is needed."
- **Flags.** R2 (some "this incomparability is precisely the obstacle"
  editorializing — show via the table, don't narrate). Table 2.2 is strong,
  concrete, and exactly the kind of artifact the supervisor wants more of.
- **Verdict.** TRIM. Keep Table 2.2 and the gap argument; cut the
  telling-the-reader-what-to-conclude sentences. Let the table do the work.

### §2.6 The unified-harness gap and the methodology it calls for
- **Says.** Restates C1+C2+C3; previews Ch3's simulator, schema, and
  experiment axes; previews Ch4/Ch5/Ch6.
- **For.** Hand-off to Ch3.
- **Flags.** R1/R2 — largely recap of C1/C2/C3 + preview of later chapters.
- **Verdict.** CUT to a short bridge (3–4 sentences). The C1/C2/C3 restate
  is redundant if §2.1 already stated them once.

---

## Chapter 3 — Methodology

### §3.1 Chapter roadmap
- **Says.** Recaps Ch1/Ch2; states three claims about the simulator;
  flags that only 3 of 4 protocols are implemented (Narwhal+Tusk deferred).
- **For.** Frame the chapter + record the deferral.
- **Flags.** R1/R2. The deferral note is the only load-bearing content.
- **Verdict.** CUT to a few sentences. Keep the "three protocols
  implemented, Narwhal+Tusk deferred" fact; drop the recap and the
  three-claims preamble.

### §3.2 System model (§3.2.1–§3.2.5)
- **Says.** §3.2.1 discrete-event scheduler (min-heap, three event
  classes, deterministic replay). §3.2.2 node model (inbound/outbound API,
  per-protocol FSM). §3.2.3 network model (latency-only mesh, delay
  distributions, drop, partitions, phases). §3.2.4 message envelope +
  per-protocol type catalog. §3.2.5 adversary surface (AdversaryProfile,
  the 18-pair design space).
- **For.** Describe **how the simulator works** — the supervisor's "say how
  you simulate" at the architecture level.
- **Connects.** §3.2.3 phases ↔ RQ1 delay sweep; §3.2.5 ↔ RQ4; envelope
  §3.2.4 ↔ bytes_per_acu in §3.5.
- **Flags.** **R4 partial.** This describes the *machine* accurately but
  never runs it — no concrete trace. §3.2.5 is the chapter's worst R2
  offender (the 18-pair / scheduled-vs-deferred / catalog-vs-RQ4-vocabulary
  accounting). §3.2.1–§3.2.4 are decent but architecture-only.
- **Verdict.** TRIM hard on §3.2.5 (collapse the scope-accounting to a
  table or footnote; keep the AdversaryProfile mechanism). KEEP §3.2.1–
  §3.2.4 as the architecture spine, but they are *not sufficient* for R4 —
  see §3.4 verdict for where the concrete run must be added.

### §3.3 Algorithms (§3.3.1 PBFT, §3.3.2 Casper FFG, §3.3.3 Snowman, §3.3.4 Narwhal+Tusk)
- **Says.** Each implemented protocol: mechanism, simulator mapping (knobs,
  defaults, rescaling rules), simplifications, event-handler shape, with a
  figure. §3.3.4 is a `TODO(T36.2)` placeholder.
- **For.** The implementation-level mirror of Ch2 §2.4 — **the second R3
  battleground**, narrowed to what's actually in `src/`.
- **Connects.** §3.3 ↔ §2.4 (same four families, now concrete);
  simplifications ↔ §1.4 scope; rescaling rules ↔ §3.4 / metric
  reconciliation.
- **Flags.** Better than §2.4 on concreteness (real knobs, real defaults,
  e.g. Snowman K=min(20,n−1), α_c=⌈0.8K⌉, β=15; Casper slots_per_epoch=4).
  But still **no side-by-side contrast** and **no worked run** (R3/R4).
  The Snowman n=4 degeneracy discussion is concrete and good. Lots of
  forward references to T36.2 / Week-9 / Week-10 (R2).
- **Verdict.** REWRITE-light + ADD. Keep the per-protocol concreteness
  (it's the chapter's strongest material). ADD the cross-protocol contrast
  here too — ideally the same one-block trace as §2.4 but at
  implementation granularity (which handler fires, which message types,
  how many). Trim the week/task forward-references.

### §3.4 Simulation setup
- **Says.** Six-phase bootstrap; reproducibility contract; experiment
  matrix (six axes; n∈{4,7,10,16,25}; Families A/B/C); workload defaults
  (Poisson, 512-byte tx, 100 tx/s, ramp grid); FFG coherence constraint;
  Snowman rescaling constraint; termination predicates.
- **For.** **The primary R4 section** — "what is the concrete evaluation
  scenario." All the ingredients of a concrete run are here.
- **Connects.** Families A/B/C ↔ RQ3/RQ1/(RQ2+RQ4); workload ↔ §3.5
  metrics; constraints ↔ §3.3 rescaling.
- **Flags.** **R4 fail despite having all the parts.** The matrix is
  described as a *product of axes*, never instantiated as one runnable
  scenario the reader can follow from config → events → measured number.
  Everything needed is present; it just isn't walked once.
- **Verdict.** REWRITE + ADD. Keep the axes/constraints as reference. ADD
  one fully worked experiment (e.g. "B1: n=10, heavy-tailed delay phase,
  honest, 100 tx/s, 20 seeds — a tx at t=… commits at t=…, here is how
  commit_latency_ms is read"). This single concrete spine is the highest-
  leverage addition in the whole chapter for the supervisor's "say how."

### §3.5 Metric schema (Tables 3.1, 3.2)
- **Says.** Uniform schema; four metric families (latency, throughput,
  overhead, reliability); operational defs of safety/liveness violations;
  four structural asymmetries + the ACU (atomic commit unit) device;
  per-protocol formula tables; aggregation rules; output CSV columns.
- **For.** Make the four families measurable on one yardstick — the
  technical core of the contribution.
- **Connects.** Tables 3.1/3.2 ↔ Ch4 columns; ACU ↔ §2.4 finality
  differences; safety/liveness defs ↔ §2.2 properties and RQ4.
- **Flags.** Dense but mostly load-bearing. Tables 3.1/3.2 are exactly the
  concrete artifacts to keep. Some R2 in the prose around the tables
  (forward refs to T54, output-format page). The ACU explanation is good
  and concrete.
- **Verdict.** KEEP tables; TRIM surrounding prose. Cut the
  reserved-column / future-task forward references to a single note.

### §3.6 Chapter summary
- **Says.** Recaps family-agnostic model + schema; restates 3 implemented /
  1 deferred; previews Ch4.
- **Flags.** R1/R2 — recap + preview.
- **Verdict.** CUT to a short bridge or remove.

---

## Cross-cutting actions (not tied to one section)

1. **The R3 comparison artifact is the centerpiece of the rework.** One
   well-built "trace one block through all four protocols" table/figure,
   referenced from both §2.4 and §3.3, answers the supervisor's #1 question
   more than any prose edit. Build it once, cite it twice.
2. **The R4 worked scenario is the second centerpiece.** One concrete
   experiment walked end-to-end in §3.4 answers "say how you simulate."
3. **Kill the roadmaps.** §2.1, §3.1, §2.6, §3.6 are ~80% scaffolding.
   Cutting them is pure signal gain and a big chunk of the length the
   supervisor flagged.
4. **Demote the bookkeeping.** §3.2.5's 18-pair accounting and the
   scattered week/task forward-references belong in `wiki/` or the task
   log, not the chapter body.
5. **Citations to clause/sentence ends** (R7) throughout.

## Suggested stage order after Stage 0 approval
- **Stage 1 (pilot):** Ch1 — recalibrate voice + rubric on the shortest
  chapter; nails the "why" (§1.2 lead-with-the-failure rewrite).
- **Stage 2:** Ch2 — the R3 mechanism contrast (the supervisor's #1).
- **Stage 3:** Ch3 — the R4 concrete run + trim the architecture/bookkeeping.

The R3 artifact spans Stage 2–3; build it in Stage 2 and reuse in Stage 3.
