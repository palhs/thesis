# Draft narrative — cross-chapter coherence layer

How the Writer keeps the **story** straight across chapters. This sits one level
above `docs/draft-style.md`: that file fixes register, voice, word choice, and
citation form *inside a chapter*; this file fixes the *through-line between
chapters* — the questions each chapter inherits, the promises it must discharge,
and the conventions it must not silently break. Every chapter after Chapter 3
(results, synthesis, conclusion) is written and reviewed against this file.

`CLAUDE.md` does not `@`-import it (it is Writer-only for *loading*, like
`draft-style.md`), so the Writer loads it on pickup — but its ledgers (§2, §3,
§10) are a synchronized artifact maintained by *any* task that changes scope, not
only Writer tasks (see §11). It is also the second rubric the
`prj-review-panel` slice review and any draft self-check run against: the panel
scores a slice in isolation; this layer scores whether the slice *connects*.

The standing rule holds: this is an operating artifact, agent-consumable and
technical. It governs draft prose; it is not draft prose.

---

## 1. The thesis spine

The whole document argues one line. Every chapter is a segment of it, and each
chapter must visibly receive the prior segment and pass the next one on:

> Deployed Layer-1 protocols hold their guarantees *in theory*, yet halt, stall,
> and fork *in deployment* (§1.2 incidents) — because the conditions those
> guarantees assume are routinely exited, and because under combined stress
> performance and security stop being independent (the **coupling**, §1.2–1.3).
> No prior study measures that coupling across families on matched assumptions
> (the **gap**, §2.4–2.5). This thesis builds one simulator that does (the
> **method**, Ch3), reports what each family does under delay and adversary (the
> **data**, RQ1–RQ4, Ch4), synthesizes whether any family dominates (the
> **verdict**, RQ5, Ch5), and returns to the incidents, the limits, and the
> further-work directions (the **close**, Ch6).

The narrative contract for every chapter after Chapter 3:

1. **Inherit.** Open by naming the question the previous chapter left open, not
   as a free-standing topic.
2. **Discharge.** Answer it with data or argument traceable to the wiki, and say
   plainly that it is now answered.
3. **Hand off.** Close by opening the next chapter's question.
4. **No silent drops.** A promise made upstream (an RQ, a "deferred to Chapter
   X", a caveat handed to Chapter 6) is a debt. Pay it, or restate why it is
   still carried — never let it disappear.

The payload of a coherent thesis is not that the questions get answers; it is
that *the answers surprise*. Surface the non-obvious findings as headlines (§4).

---

## 2. The RQ-closure ledger (central instrument)

The five research questions are the thesis's load-bearing promises. RQ1–RQ4
generate data; RQ5 synthesizes. **Every RQ a chapter owns must have an explicit,
locatable answer that matches the question as written in §1.5** — not an implied
one a reader must assemble. Check the answer against the exact wording, including
the independent variable named in the question.

| RQ | Question (as written, §1.5) | Independent variable | Answered where | Status |
|:--|:--|:--|:--|:--|
| RQ1 | commit-latency scaling as network-delay variance rises nominal→heavy-tailed | network timeline (Family B) | §4.3.1 | **closed** — stated as the delay/time-to-finality result |
| RQ2 | **sustained throughput** degradation as Byzantine fraction approaches the threshold from below | adversarial fraction φ (Family C) | §4.4 (evidence in §4.4.2 throughput ≈ 1−φ) | **closed** (2026-06-22) — §4.4 now states the explicit closure, naming sustained throughput (≈ 1−φ) as the measured quantity |
| RQ3 | relative communication overhead (msgs + bytes per agreed unit) | n (Family A) | §4.2.4 | **closed** — "answers RQ3" stated |
| RQ4 | which adversary → liveness loss / safety violation / neither | adversary (Family C) | §4.4 | **closed** — per-strategy, with the mechanism map in §4.4.4 |
| RQ5 | does a consistent perf–security Pareto frontier exist; does any family dominate | synthesis over RQ1–RQ4 | §5.3 (was §5.4 pre-Wave-3) | **closed** (2026-06-23; relocated by the Wave-3 Ch5 restructure 2026-06-29) — the first of §5.3's three drawn conclusions states a consistent frontier over the three families evaluated and that no family dominates; Table 5.1 and the cross-family frontier radar Fig 5.1 (both now anchored in §5.2) and the operator-tradeoff figure (Fig 4.5c) carry the evidence |

A Writer touching a results or synthesis chapter updates this table and satisfies
every row it owns. RQ2 was the live trap and is now closed: the §4.4 pass added
the explicit closure sentence, naming throughput (not success rate) as the
measured quantity. **RQ5 is closed by the Ch5 draft (in §5.3 after the Wave-3
restructure; in review); all five research questions have explicit, located
answers.**

---

## 3. The forward-reference ledger

Every "deferred to Chapter X", "taken up in Chapter Y", and "left to future work"
is tracked here until discharged. Adding a new forward reference requires naming
the chapter that owns it; closing one requires the owning chapter to actually
deliver, or to restate the reason it is carried.

**Discharged by Chapter 5 (drafted 2026-06-23, in review):**

- the RQ5 Pareto-frontier synthesis (was deferred from §4.3.4, §4.4.4, §1.5–1.6,
  §3.1) — delivered in §5.3 (post-Wave-3; was §5.4) over the three families
  evaluated, and given its own native figure in the W12 figure pass (the
  cross-family frontier radar, Figure 5.1, 2026-06-24, now anchored in §5.2);
- the explicit "does any family dominate" verdict — delivered as *no* (§5.3,
  with Table 5.1 in §5.2), established over the three families evaluated.

**Discharged by Chapter 6 (drafted 2026-06-23, in review):**

- the consolidated **Limitations** section — delivered §6.2 (latency-only model,
  no-capacity-model, small-n rescaling, three-family scope,
  commensurability-by-convention, permanent-loss bound, leader-sparing coverage);
- the RQ1–RQ5 summary of findings — delivered §6.1;
- future directions — delivered §6.3 (6.3.1 signature-aggregation variants kept;
  6.3.2 capacity model, adaptive-timeout enhancement, Snowman `ε` confidence
  depth, larger-scale/real-network validation).

**Descoped, restated as future work (no silent drop):**

- the adaptive-timeout enhancement *measured against the baseline* — was promised
  in the §1.6 roadmap; descoped 2026-06-22 by human decision (T57/T58 not
  implemented). It is **not** delivered as a measured result; it is restated as a
  further-work direction in Ch6 §6.3.2, gated on a future timeout-stressing
  experiment. Ch1 §1.6 no longer promises it as a chapter deliverable, so no
  upstream roadmap debt remains.

**Carried (consciously deferred, owner = future implementation, not a chapter):**

- the Narwhal+Tusk / DAG-based family and its data-availability-withholding
  adversary. **Rescoped by T73 (2026-06-24):** the three-of-four scaffolding is
  stripped from Ch1–Ch4 — the family is no longer named anywhere in the body —
  and the DAG acknowledgment is consolidated into a single Ch6 §6.3.2 further-work
  line that names Narwhal+Tusk, its uncovered data-availability-withholding
  adversary, and the high-throughput frontier corner left unmeasured
  [[wiki/concepts/adversary-model]]. The thesis now presents and evaluates three
  families throughout; the DAG family remains future work owned by a future
  implementation, not by any chapter, and the prior §5 "state it once per chapter"
  exception (Ch5/Ch6 neutral, Ch1–Ch4 named) is retired — DAG now appears in
  exactly one place in the whole document;
- the empirical/analytical Snowman `ε` columns at weakened confidence depth;
- the saturation/capacity throughput model.

Rule (post-T73): the thesis evaluates three families throughout; no chapter body
softens this into "we evaluate four" or names the deferred DAG family except the
single Ch6 §6.3.2 further-work line.

---

## 4. Narrative tension — open, fill, close

What makes the document read as one argument rather than five reports:

- **Inherited roadmaps.** A chapter's opening frames its sections as the next
  questions raised by the prior chapter. Section openings state the question the
  section answers before the numbers arrive.
- **Surface the inversions.** The thesis's non-obvious results are the
  contribution; lead with them, do not bury them under expected ones:
  - the same subsampling makes Snowman the *most* delay-tolerant protocol when
    peers are merely slow and the *least* tolerant when they fall silent;
  - PBFT's leader-based commit rule is at once the source of its liveness
    robustness and of its unaccountable fork;
  - the protocols that survive loss are exactly the ones that pay the most
    latency to do so (no cheap-and-resilient configuration exists);
  - no family dominates — and the value is the *mechanism map* of which
    structural choice causes which failure, not the bare no-dominance statement.
  A finding a reader of the design space could have guessed is worth one
  sentence; a finding that inverts the expectation is worth the spotlight.
- **Close the loop to the hook.** The §1.2 incidents (Solana halts, Ethereum's
  May-2023 finality stall, the Cosmos and Sui halts) open the document and must
  be *returned to* — at least once in the Ch4/Ch5 synthesis and once in Ch6 —
  so the measured failure modes are tied back to the real ones that motivated
  them (e.g. Casper FFG's first-step loss collapse as the measured analogue of an
  attestation-pressure finality stall; PBFT's view-change storm as the
  leader-disruption halt class). **Discipline:** a callback is an honest
  *mechanism analogy* traceable to the wiki, never an invented causal claim that
  the simulator reproduced a specific incident — frame it as "the same class of
  failure", and cite, or mark the bridge as interpretive.
- **Explicit transitions.** Between sections and chapters, name what was just
  isolated and what is isolated next ("§4.3 varied the network and held the
  validators honest; §4.4 holds the network fixed and varies the adversary").

---

## 5. Inherited-convention gates (from Chapter 3 — never break downstream)

Chapter 3 fixes measurement conventions that later prose silently violates if
unwatched. A downstream chapter that needs to deviate must say so and cite the
wiki page that authorizes the deviation.

- Cross-protocol **latency** is read from `commit_latency_ms` (the canonical
  time-to-finality column), never `finality_latency_ms` (§4.2.6).
- Cross-protocol **throughput** uses `goodput`, never `tps` (`tps` is a
  protocol-granularity decision-event rate, not like-for-like).
- All per-unit metrics use the **ACU** denominator.
- **Snowman `n = 4`** is excluded from comparative tables (rescaling degenerates
  to unanimity); report it once as a sanity check at most.
- **Commensurability by convention:** every comparative verdict is qualified by
  the convention it rests on, and is reported as *robust* only when it survives
  the governing sensitivity sweep.
- **Latency-only model:** the no-compute/no-bandwidth-cost caveat attaches to
  *cost and per-validator* verdicts (it flatters PBFT and Casper FFG); it does
  **not** qualify the message-count, byte-count, liveness, or safety verdicts.
- **Snowman safety** is probabilistic — reported via the `ε ≤ (1−α_c/K)^β` bound,
  not a fork count; an empirical zero is a non-witness of the bound, not a
  confirmation of it.
- A **`deadline` stop is not a liveness failure**; only a run in which no honest
  validator commits within the window is.
- **Three families evaluated; the DAG family is future work only** — as of T73
  (2026-06-24) the Narwhal+Tusk / DAG-based scaffolding is stripped from the body
  (see §3). The thesis presents and evaluates three families — PBFT, Casper FFG,
  Snowman — uniformly across Ch1–Ch6, and the DAG family appears in exactly one
  place: the Ch6 §6.3.2 further-work line. The prior "stated in Ch1–Ch4 /
  neutral in Ch5–Ch6" asymmetry and its "state it once per chapter" exception are
  retired.

---

## 6. Inherited style/discipline gates (from draft-style.md — the ones most missed)

- **No project-internal task IDs** in prose, tables, or captions. Name the
  *work* or the *mechanism*, never the ticket. *(Status 2026-06-23: the
  `T38.1`/`T51` leaks were stripped from `ch4_results.md`; the `T38.1` leak in
  `ch6_conclusion.md` §6.3.2 is now resolved — the DAG-completion clause that
  carried it was removed in the Ch6 pass. No task-ID leaks remain in the drafted
  chapters.)*
- Every claim cites a wiki page inline as `[[wiki/...]]`; missing external
  citations are `TODO(cite)`; no invented citations.
- **No fabricated statistics.** Every number in prose, a table, or a caption —
  a mean, a confidence interval, a ratio, a count, a threshold, a percentage —
  must trace to a wiki experiment page, the aggregated CSV that page cites, or a
  §3 schema definition. If a number is needed but is not in the wiki, do not
  invent, round-guess, or interpolate it: stop and flag a Researcher/Engineer
  task in Backlog, or mark `TODO(cite)`. This is the quantitative case of the
  no-invented-citations rule and the single largest hallucination risk in a
  results chapter — retrieve the figure through a subagent (§9), with its source
  line, rather than recalling it from context.
- Data-plot figures cite the **experiment page** and reference a vector PDF that
  exists on disk; diagram figures cite `[[diagrams/...]]`.
- Formal, impersonal, US English, no contractions, general vocabulary held to the
  IELTS-7 band.

---

## 7. The evaluation rubric

Two parts. The **gates** are pass/fail and block In Review. The **scored
dimensions** extend the six the `prj-review-panel` already applies, so a slice
gets one comparable set of numbers covering both intra-chapter quality and
cross-chapter coherence.

### 7a. Pre-flight gates (pass/fail — any FAIL is not ready for In Review)

Each is a grounded binary (cite a line, number, or figure for the verdict):

- **G1 — RQ closure.** Every RQ this chapter owns has an explicit, locatable
  answer matching the §1.5 wording, including the named independent variable.
- **G2 — Forward references.** Every "deferred to Chapter X" the chapter owns is
  discharged, or restated as consciously carried with its owner named (§3).
- **G3 — Inherited conventions.** No §5 convention is violated; any deviation is
  declared and wiki-authorized.
- **G4 — Style/discipline.** No task IDs in prose; every claim cited; **every
  number traces to a wiki / experiment / CSV source — no fabricated statistics**;
  every figure backed by an on-disk PDF and an experiment/diagram back-reference;
  register and word choice per `draft-style.md`.
- **G5 — Loop closure.** Synthesis and conclusion return to at least one §1.2
  motivating thread, as an honest mechanism analogy, cited.
- **G6 — Signposting.** The chapter opens by inheriting the prior question and
  closes by opening the next; section transitions are explicit.
- **G7 — Humanizer.** The `/humanizer` pass has been run and re-verified (§8).

### 7b. Scored narrative dimensions (1–10, alongside the panel's six)

10 = exemplary; 5 = adequate but unremarkable; ≤3 = a defense liability. Each
scored with a one-line justification grounded in the text.

- **N1 — continuity.** Does the slice receive the prior chapter's open question
  and hand off the next, rather than starting and ending in isolation?
  *(10: inheritance and hand-off are explicit and natural; ≤3: reads as a
  stand-alone report with no thread in or out.)*
- **N2 — promise-closure.** Are owned RQ answers and forward references
  *discharged and announced*, not left for the reader to infer?
  *(10: every promise paid and named; ≤3: an RQ or deferral silently dropped or
  only implied — the RQ2 trap.)*
- **N3 — narrative payload.** Are the non-obvious findings and the inversions of
  §4 surfaced as headlines, and is the §1.2 hook closed?
  *(10: the surprises lead and the loop closes; ≤3: findings buried under
  expected ones, hook never revisited.)*
- **N4 — convention fidelity.** Does the slice honor the Chapter-3 measurement
  conventions of §5 exactly?
  *(10: every convention held, deviations declared; ≤3: a silent
  `finality_latency_ms`/`tps`/ACU/`n=4` slip that misstates a comparison.)*

The panel's six (significance, soundness, rq_contribution, rigor_honesty,
clarity, presentation) still apply unchanged. N1–N4 are the cross-chapter layer
the per-slice panel cannot see on its own.

---

## 8. The humanizer gate (mandatory, last step before In Review)

AI-pattern detection (Turnitin and similar) is a real risk for generated prose.
After the draft is written and the §7 gates are addressed, run `/humanizer` over
the new or changed prose. Then **re-verify**, because the humanizer optimizes for
natural human rhythm and can collide with the thesis's formal contract:

- citations `[[wiki/...]]` are intact, correctly placed, none dropped or mangled;
- every number, symbol, and unit is unchanged;
- no task ID was reintroduced;
- register held: no first person ("we"/"I"), no contractions, no rhetorical
  questions, no informal synonym swapped in for a precise technical term;
- every claim is still traceable to its wiki page.

Reconcile the two pressures at the level the humanizer works best — sentence
rhythm, varied openings, fewer formulaic constructions — and **revert any
humanizer edit that lowers the register, breaks a citation, or changes a
measured value**. The humanizer serves the prose's surface; it never overrides
`draft-style.md` or the claim discipline.

---

## 9. Execution hygiene — offload small tasks to subagents

A results or synthesis chapter is verification-heavy: every number checked
against its source, every citation resolved, every figure inspected, every §5
convention re-checked. Doing all of that inline floods the drafting context with
raw CSVs, full experiment pages, and figure binaries — and a flooded context
degrades the prose the main flow exists to write. Keep the main flow lean: it
holds the spine, the two ledgers (§2–§3), the wiki pages backing the section in
hand, and the prose itself. Push everything else out.

**Offload mechanical, self-contained subtasks to subagents** — a single `Agent`
for one lookup, parallel `Agent`s or a `Workflow` for checks that fan out —
running on **Sonnet 4.6 (`model: sonnet`)**, which is fast and cheap enough for
retrieval and checking and leaves the heavier model for drafting and synthesis
judgment. A subagent reads the bulky source and returns only the distilled
result — the number plus the line it came from, a pass/fail verdict, a list of
hits — never the raw file. Natural offloads:

- **Number retrieval and verification (the anti-hallucination workhorse).** Fetch
  the exact mean / CI / ratio / count from the experiment page or aggregated CSV
  and hand it back *with its source line*. This is how §6's
  no-fabricated-statistics rule is met in practice: the number comes back
  sourced, never guessed.
- **Citation and figure checks.** Confirm each `[[wiki/...]]` resolves and each
  figure's PDF exists on disk; sample a figure image and report what it shows.
- **Gate sweeps.** Run the §7a pass/fail gates, or grep a slice for task-ID leaks
  and uncited numbers, as parallel checks that return only verdicts.
- **The slice review.** `prj-review-panel` already fans out three reviewers; it
  is the same pattern, and its scores feed the §7b rubric.

Use a `Workflow` for structured, multi-stage fan-out (verify every number in a
section against its source, then re-check the survivors); use a lone `Agent` for
a single self-contained lookup. Either way the rule is the same: **bulk reading
happens in a subagent's context, not the drafting flow's** — so the context that
writes the prose stays clean and the answer stays sharp.

---

## 10. Per-chapter cheat-sheet (what each remaining chapter inherits and owes)

- **Ch4 — Results (narrative-layer debts discharged 2026-06-22).** Owns RQ1
  (§4.3.1 ✓), RQ3 (§4.2.4 ✓), RQ4 (§4.4 ✓), and RQ2 (§4.4 ✓ — explicit
  throughput-axis closure added; the ≈ 1−φ decay of §4.4.2 is the evidence). §5
  conventions honored with declared deviations; `T38.1`/`T51` task-ID leaks
  stripped; §1.2 hook callback present (Ethereum May-2023 finality stall). All
  caveats handed to Ch6. Remaining cross-chapter work lives in Ch5/Ch6 below.
  *(T73, 2026-06-24: the §4.4 "survey covers three families / Narwhal
  data-availability-withholding absent" qualification trimmed to the honest
  three-family scope statement; the DA-withholding point relocated to Ch6 §6.3.2.)*
  *(Page-cut Wave 1, 2026-06-29: Ch4 in-body figures consolidated 21 → 8
  multi-panel figures (4.1–4.8); old single figures merged — operator tradeoff is
  now Fig 4.5c (was 4.13), referenced from Ch5 §5.4 and the §2 RQ5 row; the Casper
  slashable-stake and adversary outcome-map figures relocated to Appendix A as
  Figs A.1/A.2; Table 4.1 baseline means folded into §4.2.6 prose; success/fork and
  PBFT view-change-count figures dropped to one prose sentence each. Leftover
  `mitthesis.cls` Appendix B (heat-conduction example) deleted from the LaTeX
  back matter. No RQ answer, number, or caveat changed.)*
  *(Page-cut Wave 2, 2026-06-29 — redundancy removal, no argument/number/source-cite
  lost: no-dominance verdict kept canonical in §5.4 (restatements trimmed in §4.4.4,
  §5.1, §5.5, §6.1, §6.4); per-protocol findings canonical in §5.3 (§4.4.4 ¶1 and
  §6.1 prose reduced to pointers); standing caveats defined once in Ch3 (ε §3.5,
  latency-only §3.6, ε-bound derivation §3.3.3) and cited as bare `(§x)` elsewhere;
  §1.2 incident callback kept in §5.5 (canonical), §4.3.4, §5.3.2, and §6.4 (Ch6
  instance retained with [21]), removed from §6.1; §3.6 compressed to a bullet list,
  §6.2 keeps the full reflective limitations. **Ch2 was renumbered** — old §2.1+§2.2
  merged into §2.1, so the families/Table-2.1 section is now §2.2 (Ch3's three "§2.3"
  cross-refs repointed to §2.2; the gap is now §2.4). Ch2's three per-family weakness
  paragraphs (§2.3.x) cut, their headlines carried by Table 2.1; the Amores-Sesar [10]
  Snowman-stall sentence preserved.)*
  *(Page-cut Wave 3, 2026-06-29 — deep cut, deletes prose; no RQ answer, result
  number, caveat, or source-cite lost. Ch4 6930→~5540 w: range-over-points rule
  (per-cell `n=10/25`/`φ` recitations dropped, trends + thresholds/anomalies kept)
  across §4.3.1/§4.3.2/§4.4.1–§4.4.3; §4.4.4 four caveats → one-line pointers, hedge
  kept once; the tex-only "A note on the latency measurement point" subsection removed,
  the `commit_latency_ms` clause folded into §4.2.2 so md/tex converge; §4.2.1 retained
  as a one-sentence subsection so numbering stays §4.2.1–§4.2.6 and §4.2.4 remains the
  RQ3 home. Ch3 5893→~4310 w: §3.4.4 walkthrough deleted (Figure 3.6 + commit_hash/seed
  kept), §3.3 deviation ledgers → 3 body sentences, §3.5 → Table 3.3 + invariant metric
  defs, §3.4.2 → a Family A/B/C matrix table, four §3.6 threats verbatim; the seven-key
  input config contract relocated from an inline chapter3.tex `verbatim` block into
  Appendix A (matching the §3.2 reference), and the leftover mitthesis-template Lua code
  listing removed from Appendix A.)*
- **Ch5 — Synthesis (drafted 2026-06-23, in review).** Owns RQ5: traced the
  Pareto frontier over the three families evaluated and answered "does any family
  dominate" = *no* (§5.4, Table 5.1 and the native cross-family frontier radar
  Figure 5.1 added in the W12 figure pass 2026-06-24), discharging the
  §4.3.4 / §4.4.4 deferrals.
  §1.2 hook callback present (§5.5). Hands off to Ch6. The adaptive-timeout
  enhancement is no longer in Ch5 scope (descoped 2026-06-22; now a Ch6 §6.3.2
  further-work direction). Three-family scoping — now uniform across the whole
  thesis (T73, 2026-06-24); the deferred DAG family is named only in Ch6 §6.3.2.
  *(T73 also compressed §5.2 convention restatement to a Ch3 cross-reference and
  trimmed the §5.3 magnitude enumerations that Table 5.1 carries.)*
  *(Page-cut Wave 3, 2026-06-29 — Ch5 RESTRUCTURED, 2285→~1560 w. New section map:
  §5.1 the joint reading (merges old §5.1+§5.2); §5.2 the cross-regime frontier
  (Table 5.1 + Fig 5.1 moved up as the anchor — all per-family numbers now live in the
  table/captions, not prose); §5.3 three drawn conclusions written as insights
  (no-dominance — **the RQ5 answer now lives here**, was §5.4; structural inversions /
  mechanism map naming Casper FFG's accountable-failure corner, the "map not the bare
  statement" hedge kept once; the empty corner); §5.4 implications + hand-off (old §5.5,
  **the §1.2 incident callback's canonical home moved §5.5→§5.4**). Per-family
  non-domination evidence is not lost — it lives in Table 5.1, honoring the
  §5.3/§5.4/Table-5.1 invariant: the evidence survives, the prose narration changed.)*
- **Ch6 — Conclusion (drafted 2026-06-23, in review).** §6.1 RQ1–RQ5 summary
  (per-RQ prose walk condensed to one paragraph by T73, 2026-06-24; Table 6.1
  carries the detail); §6.2 consolidated limitations; §6.3 further work (6.3.1
  signature-aggregation variants kept, BLS caveat condensed by T73; 6.3.2 —
  capacity model, adaptive-timeout enhancement, Snowman `ε` depth, **the
  DAG-family extension (Narwhal+Tusk — the single DAG mention in the thesis,
  added by T73)**, and larger-scale validation; the earlier DAG-*completion*
  clause and its `T38.1` leak remain removed); §6.4 returns to the §1.2
  incidents. Three-family scoping, DAG named only here.
  *(Page-cut Wave 3, 2026-06-29 — deep compress, 1478→~1090 w. §6.1 prose to ~3
  sentences (Table 6.1 carries the per-RQ detail); §6.2 keeps every limitation as
  tight bullets (integrity gate — none dropped); §6.3.1 to ~4 sentences; §6.3.2 five
  directions to one clause each — **all five kept, including the adaptive-timeout
  enhancement and the single Narwhal+Tusk/DAG further-work line**; §6.4 to the
  contribution statement + the §1.2 May-2023 callback [21]. No RQ summary row, limitation,
  further-work direction, or callback lost.)*

---

## 11. Maintenance contract — this file is a synchronized ledger

The §2 RQ-closure ledger, the §3 forward-reference ledger, the §10 per-chapter
cheat-sheet, and the §1 spine sentence are **derived state**: they restate, in
cross-chapter form, scope decisions whose authoritative record lives in
`TASKS.md` (and, for RQ wording, `wiki/concepts/research-questions.md`). Derived
state drifts unless something forces it to move with its source — which is exactly
how a descoped deliverable can sit in the ledger as still "owed by Chapter X"
until a downstream Writer discovers the contradiction by chance.

The rule, modelled on the `wiki/index.md` update obligation (every task that
creates a page updates the index):

> **Any task that changes thesis scope updates §1, §2, §3, and §10 in the same
> change — regardless of role.** A scope change is: descoping or rescoping a task;
> rewording, adding, or retiring a research question; adding, discharging, or
> re-owning a forward reference ("deferred to Chapter X", "left to future work");
> or changing what a chapter owns or hands off.

This obligation is **not Writer-only.** Most scope changes are recorded by `meta:`
commits or by Engineer/Researcher tasks whose authors never open a draft; they
must still reconcile these ledgers, or the next Writer inherits a contradiction.
The reciprocal Writer obligation already stands: a Writer touching a results or
synthesis chapter updates §2 and satisfies every row it owns (§2; gate §7a-G2).

When a row cannot be fully reconciled in the moment, do not leave it silently
wrong: restate it as consciously carried, with the date and the pending decision,
per the no-silent-drops rule (§1, item 4). The lint pass cross-checks these
ledgers against `TASKS.md` (`docs/lint-protocol.md` check 9 — narrative-ledger
drift) and the pickup flow loads this file for post-Chapter-3 Writer tasks so a
residual divergence surfaces at pickup, not mid-draft. A divergence is a finding,
not a convention.
</content>
</invoke>
