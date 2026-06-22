# Draft narrative — cross-chapter coherence layer

How the Writer keeps the **story** straight across chapters. This sits one level
above `docs/draft-style.md`: that file fixes register, voice, word choice, and
citation form *inside a chapter*; this file fixes the *through-line between
chapters* — the questions each chapter inherits, the promises it must discharge,
and the conventions it must not silently break. Every chapter after Chapter 3
(results, synthesis, conclusion) is written and reviewed against this file.

`CLAUDE.md` does not `@`-import it (it is Writer-only, like `draft-style.md`), so
the Writer loads it on pickup. It is also the second rubric the
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
> **verdict**, RQ5 + the enhancement, Ch5), and returns to the incidents and the
> limits (the **close**, Ch6).

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
| RQ5 | does a consistent perf–security Pareto frontier exist; does any family dominate | synthesis over RQ1–RQ4 | Ch5 | **open** — owed by Ch5; foreshadowed by the no-dominance result of §4.4.4 and the latency–liveness trade of §4.3.4 |

A Writer touching a results or synthesis chapter updates this table and satisfies
every row it owns. RQ2 was the live trap and is now closed: the §4.4 pass added
the explicit closure sentence, naming throughput (not success rate) as the
measured quantity. **RQ5 is the remaining open promise, owed by Ch5.**

---

## 3. The forward-reference ledger

Every "deferred to Chapter X", "taken up in Chapter Y", and "left to future work"
is tracked here until discharged. Adding a new forward reference requires naming
the chapter that owns it; closing one requires the owning chapter to actually
deliver, or to restate the reason it is carried.

**Owed by Chapter 5:**

- the RQ5 Pareto-frontier synthesis (deferred from §4.3.4, §4.4.4, §1.5–1.6, §3.1);
- the explicit "does any family dominate" verdict (the answer is foreshadowed as
  *no*; Ch5 must establish it over the three implemented families, with the
  high-throughput corner the DAG family would occupy stated as unmeasured);
- the adaptive-timeout enhancement, measured against the baseline (promised in
  the §1.6 roadmap as the demonstration of the simulator's utility).

**Owed by Chapter 6:**

- the consolidated **Limitations** section (§3.6 threats + every per-chapter
  caveat drawn together — the latency-only baseline, the no-capacity-model, the
  small-n rescaling, the three-family scope, commensurability-by-convention);
- the RQ1–RQ5 summary of findings;
- future directions (§6.3 already seeds signature-aggregation variants and the
  capacity/Narwhal+Tusk lines — keep, do not duplicate).

**Carried (consciously deferred, owner = future implementation, not a chapter):**

- the Narwhal+Tusk / DAG-based family and its data-availability-withholding
  adversary — stated consistently as three-of-four throughout;
- the empirical/analytical Snowman `ε` columns at weakened confidence depth;
- the saturation/capacity throughput model.

Rule: the three-family deferral must read the same way in every chapter — neither
softened into "we evaluate four" nor over-apologized. State it once per chapter at
the scope boundary and move on.

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
- **Three families, Narwhal+Tusk deferred** — stated consistently (see §3).

---

## 6. Inherited style/discipline gates (from draft-style.md — the ones most missed)

- **No project-internal task IDs** in prose, tables, or captions. Name the
  *work* or the *mechanism*, never the ticket. *(Status 2026-06-22: the
  `T38.1`/`T51` leaks have been stripped from `ch4_results.md`; `T38.1` still
  leaks into `ch6_conclusion.md` §6.3.2 — the next Writer pass on Ch6 must strip
  it; see `draft-style.md` for the ticket→mechanism rewrite pattern.)*
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
- **Ch5 — Synthesis (to write).** Owns RQ5: trace the Pareto frontier over the
  three implemented families, answer "does any family dominate" (discharge the
  deferrals from §4.3.4 and §4.4.4 — the answer the data points to is *no*), and
  deliver the adaptive-timeout enhancement measured against the baseline. The
  strongest site for the §1.2 hook callback. Open Ch6's summary-and-limits
  question on the way out.
- **Ch6 — Conclusion (stub).** Consolidate Limitations from §3.6 + the
  per-chapter caveats; summarize RQ1–RQ5; keep the §6.3 future-work directions
  (do not duplicate the seeded ones). Close the loop to the §1.2 incidents.
  Strip the `T38.1` leak in §6.3.2.
</content>
</invoke>
