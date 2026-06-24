---
description: Dispatch a 3-reviewer examiner panel that scores any draft chapter/section on a shared rubric and proposes analysis/figure improvements
argument-hint: <chapter|section|file> e.g. "ch4 §4.4", "ch3", "drafts/ch2_litreview.md §2.3"
---

You are convening a three-reviewer examination panel on a slice of the thesis
draft named by the argument, scoring it on a fixed rubric so results are
comparable across runs and chapters. This command is **read-only**: do not edit
`drafts/`, `wiki/`, `src/`, `TASKS.md`, or any file, and do not commit. Produce a
report in chat. (If the user explicitly asks to save it, write to
`wiki/lint/<date>_review-panel_<slug>.md` — otherwise write nothing.)

The argument is: `$ARGUMENTS`

## Step 0 — Resolve the target

Parse the argument into a **draft file** and an optional **section**:

1. **Draft file.**
   - If the argument contains an explicit `.md` path, use it.
   - Else if it contains a `chN` token (e.g. `ch4`), resolve `drafts/chN_*.md`
     (glob; e.g. `ch4` → `drafts/ch4_results.md`). Front/back matter:
     `abstract`/`acknowledgments`/`conclusion` → `drafts/front_*.md` /
     `drafts/ch*_*.md` by name.
   - If nothing resolves, list the files in `drafts/` and stop, asking which.
2. **Section.** Look for a `§X.Y`, `X.Y`, or `§X` / `X` token (e.g. `§4.4`,
   `4.4`, `§3`). If present, the target is that heading (`## X.Y` or `### X.Y`)
   and its body, up to the next heading of the same or higher level. If absent,
   the target is the **whole file**.
3. Read the target slice in full. Also skim the rest of the file (≈1 screen
   before and after) so the panel can judge continuity and signposting, not just
   the slice in isolation.

State the resolved file + section + line range before dispatching.

## Step 1 — Discover what the section rests on (do not hardcode)

From the target slice, gather the grounding the reviewers must read. This is what
makes the command chapter-agnostic — discover, never assume Chapter 4's figures.

1. **Figures / tables.** Grep the slice for `Figure \d`, `Table \d`, and for
   asset paths: `results/**/plots/*.pdf`, `wiki/diagrams/**/*.pdf`, and any
   `.png`/`.pdf` reference. For each figure asset, the reviewers must **inspect
   the image**: prefer the `.png` sibling (same basename) when it exists on disk
   (screen-preview companion); otherwise Read the `.pdf` directly. List the
   resolved image paths. If the slice references no figures, say so — the panel
   then judges presentation on prose structure, tables, and signposting instead.
2. **Wiki citations.** Collect every `[[wiki/...]]`, `[[concepts/...]]`,
   `[[algorithms/...]]`, `[[experiments/...]]`, `[[diagrams/...]]` target in the
   slice — these are the claims' backing and the reviewers should sample the
   load-bearing ones (the RQ/concept pages especially) to check the prose against
   them.
3. **Research questions.** Grep the slice for `RQ\d`. If it answers any RQ,
   include `wiki/concepts/research-questions.md` so reviewers check the answer
   against the question as written.
4. **Style contract.** Always include `docs/draft-style.md` — every chapter is
   written against it (audience = examination committee; formal register;
   `[[wiki/...]]` citation discipline; no internal task IDs in prose). Reviewers
   judge register and citation hygiene against it.

## Step 2 — Dispatch the panel (three reviewers, in parallel)

Launch **three reviewer agents at once** — a single message with three parallel
agents (a Workflow with a per-reviewer output schema is preferred when available,
for structured, comparable scores; otherwise three parallel `Agent` calls). Give
every reviewer: the resolved draft slice, the discovered grounding from Step 1
(they must READ the chapter slice, INSPECT every discovered figure image, and
sample the cited wiki pages + `docs/draft-style.md`), and the shared rubric
below. Each grounds every judgement in something actually read — a quoted phrase,
a number, or a figure detail — and neither invents shortcomings nor credits
strengths that are not there.

### Shared rubric (identical for every reviewer)

Score each dimension **1–10** (10 = exemplary thesis quality; 5 = adequate but
unremarkable; ≤3 = a defense liability), each with a one-line justification
grounded in the text/figure:

1. **significance** — is the content non-obvious and worth reporting, or
   expected/trivial?
2. **soundness** — are the claims technically correct and do the numbers /
   mechanisms hang together?
3. **rq_contribution** — does the slice do its job in the thesis (answer its RQ,
   or serve its chapter's purpose)? If it answers an RQ, check against the
   question as written.
4. **rigor_honesty** — are caveats, scope limits, and statistics adequate? Any
   overclaim or unstated assumption a committee would seize on?
5. **clarity** — is it well-structured and followable for an examination
   committee; is the narrative effective?
6. **presentation** — do the figures and tables make the case compellingly
   (inspect them)? If the slice has no figures, judge prose structure,
   signposting, and typography instead.

Then return: **overall** (holistic, not an average), **verdict** (`accept` |
`minor_revisions` | `major_revisions` | `reject`), an explicit read on whether
the content is **interesting**, **attractive**, and **beneficial** to the thesis,
plus **top_strengths**, **top_weaknesses**, **analysis_improvements** (each with a
priority), **plot_improvements** (name the figure; each with a priority; omit or
note "no figures" if none), and **likely_defense_questions**.

### The three reviewers (distinct lenses — keep verbatim for reproducibility)

- **R1 — Domain expert / advisor.** The thesis advisor and a subject expert in
  the slice's topic (for consensus chapters: PBFT `3f+1`/view-change, Casper FFG
  accountable safety/slashing, Snowman/Avalanche `K`-subsampling/`α_c`/`β`/`ε`,
  DAG-BFT). Supportive but rigorous; wants a strong, defensible contribution.
  Weights **soundness, significance, rq_contribution**. Checks figures for
  technical accuracy and the comparison for commensurability (fair metrics).

- **R2 — Skeptical external examiner.** No stake, defaults critical. Hunts
  overclaims, unsupported generalizations, and viva traps: incomplete scope,
  small parameter ranges, comparisons that are asymmetric or partly definitional
  by construction, unobservable or unwitnessed quantities, model artifacts
  presented as findings, and headline claims that are tautological given the
  setup. Asks "what would falsify this?" Credits caveats that are already stated
  honestly. Weights **rigor_honesty, significance**.

- **R3 — Reader-experience / presentation reviewer.** Copy-editor plus the viva
  audience following slides live. Judges narrative pull, structure, and whether
  the **figures and tables** land the findings at a glance — inspect every image:
  axis labels, legends, color/encoding, whether the threshold/cliff/trend story
  is visible, whether faceting helps or clutters, whether a ranking or verdict can
  be read off the figure, whether any figure is redundant or a key number appears
  on no figure, and whether a summary figure is missing. Most generative about
  making the analysis and visuals **more tempting**. For figure-less sections,
  judges signposting, paragraph focus, table design, and register against
  `docs/draft-style.md`. Weights **clarity, presentation** (but scores every
  dimension).

## Step 3 — Synthesize

After the three return, print:

1. **Consensus score table** — rows = the six dimensions + overall; columns = R1,
   R2, R3, mean. Flag the lowest-mean dimension.
2. **Verdicts** — each reviewer's verdict, and the panel's effective call.
3. **Interesting / attractive / beneficial** — the straight, honest read,
   reconciling agreement and disagreement across the three.
4. **Prioritized "what still needs work"** — merge the analysis_improvements and
   plot_improvements, deduplicated, High→Low. For each, note whether it is a
   prose fix (in-scope for a Writer pass on this slice) or a code/figure fix
   (belongs to a regeneration/`T62`-style pass), so the user can route it.
5. **Likely defense questions** — the union, deduplicated.
6. If a prior panel run on the same slice is in the conversation (or the user
   names a baseline), compare the new dimension means against it — especially
   whether **presentation** moved.

Keep the synthesis tight. Do not edit any file. This command observes and scores;
acting on the findings is a separate, user-initiated step.
