# Draft rework rubric

A self-check checklist for the draft-rework stages. Derived directly from
the supervisor review of the Week-7 drafts (too long; too much meta
"prompting"; the concrete *how do the four algorithms differ*, *how does
the simulation work*, and *why this comparison* are missing; "read 46
pages and found no information").

The Writer self-scores each reworked section against R1–R7 **before**
handing it to human review. A section is not ready for review until every
`pass/fail` item passes and every thresholded item is inside its bound, or
the deviation is named in the handoff with a reason.

This is a quality gate, not a style preference. The two load-bearing items
are **R3** (mechanism concreteness) and **R4** (simulation concreteness):
they are the direct answer to "found no information."

---

## R1 — Purpose stated first

**Check.** A section opens by stating, in ≤2 sentences, the question it
answers or the thing it establishes. It does **not** open by recapping the
previous chapter or previewing its own subsections.

**Score.** Pass / fail.

**Violation example (current draft).** §2.1 "Chapter roadmap" and §3.1
"Chapter roadmap" both open by re-narrating the prior chapter and listing
what each subsection will do. The "The remainder of the chapter is
organized as follows…" paragraph is the canonical anti-pattern.

**Fix shape.** Delete the roadmap. Let the first content sentence carry the
purpose. A one-line "this chapter covers X, Y, Z" is allowed at most once
per chapter, not per section.

---

## R2 — Signal density

**Check.** Count meta sentences — roadmap, recap, forward/backward
self-reference ("as we will see", "Chapter 4 will read", "this shows
that"), and claim-bookkeeping (labeling/relabeling C1/C2/C3 machinery) —
as a fraction of total sentences in the section.

**Score.** Meta fraction **< ~15%**. Report the count.

**Violation example.** §3.2.5 spends a full paragraph on adversary
scope-accounting (18 pairs, 12 scheduled, "catalog vocabulary differs from
RQ4 vocabulary") — almost entirely bookkeeping, near-zero content. This is
the literal "read pages, found no information" experience.

**Fix shape.** Keep one sentence of scope where genuinely load-bearing;
move the rest to a footnote, a table cell, or delete. Bookkeeping that only
the author needs goes to `wiki/` or the task log, not the chapter.

---

## R3 — Mechanism concreteness and direct comparison  **(load-bearing)**

**Check.** Each of the four algorithms is presented with:
1. its **steps** spelled out concretely (not just its design-space
   coordinates),
2. **one small worked instance** (e.g. n=4, f=1 — show the actual quorum
   counts / sample sizes), and
3. placement **side-by-side with the other three** so the *difference* is
   visible, not left for the reader to infer.

There must be **at least one direct-comparison artifact**: a step-by-step
table across the four protocols, or a single block/transaction traced
through all four, showing where they diverge.

**Score.** Pass / fail per algorithm, plus pass/fail on the comparison
artifact.

**Violation example.** §2.4 gives each family four abstract paragraphs
("partial synchrony / 3f+1 / deterministic finality") but never lines them
up to expose the contrast, and carries no worked instance. The supervisor's
"how do the four work *differently*" is exactly this gap.

**Fix shape.** Add the comparison artifact. Trace one block: PBFT collects
a 2f+1 commit quorum; Casper FFG needs two epochs of 2/3-stake
attestations; Snowman needs β consecutive K-sample majorities; Narwhal+Tusk
orders off the DAG with zero extra messages. Same event, four mechanisms,
shown together.

---

## R4 — Simulation concreteness  **(load-bearing)**

**Check.** The methodology contains **at least one fully concrete run
walked end-to-end**: the configuration (n, network phase, adversary,
workload), what actually happens during the run, and how each measured
number is taken. Architecture description (scheduler, heap, invariants)
does **not** satisfy this on its own.

**Score.** Pass / fail.

**Violation example.** §3.2 describes the discrete-event architecture in
detail; §3.4 describes the experiment matrix as a product of axes. Neither
shows one concrete experiment from start to finish. The supervisor's "you
say you simulate — say *how*" lands here.

**Fix shape.** Add a worked scenario: "Experiment B1: 10 validators, a
network phase with heavy-tailed delay (E[delay]=…, drop=…), honest set,
Poisson 100 tx/s. A transaction submitted at t=… enters block… reaches
2f+1 COMMIT at t=…; commit_latency_ms is the difference. Repeated over 20
seeds." One concrete spine the reader can hold onto.

---

## R5 — Motivation in plain terms

**Check.** "Why run this comparison / what do we learn from it" is stated
in plain language, early (Ch1), anchored to at least one concrete instance
(e.g. a real mainnet halt), not buried in abstraction about
"performance–security coupling."

**Score.** Pass / fail.

**Note.** Ch1 §1.2 already has the concrete anchors (Solana/Ethereum/Sui
incidents) — the fix is to lead with them and cut the surrounding abstract
framing, not to invent new material. This item also guards against
over-correcting R3/R4 into a tutorial that loses the research framing.

---

## R6 — Length discipline

**Check.** Delete-test each subsection: if it were removed, would a reader
notice missing information (not missing *framing*)? If removal loses only
scaffolding, cut it.

**Score.** Pass / fail per subsection.

**Target.** Net length should drop materially from the current draft while
R3/R4 content is *added*. Cuts come from R1/R2 scaffolding, not from
mechanism or results.

---

## R7 — Citation noise

**Check.** Wikilinks and numbered references do not interrupt clauses to
the point of breaking the reading line. A sentence should be readable with
the citations mentally removed.

**Score.** Pass / fail per section (judgment call; flag the worst offenders).

**Violation example.** Sentences in §1.1–§1.3 carry two or three
`[[wiki/…]]` links mid-clause. Move citations to clause ends or sentence
ends; one anchor per claim, not per noun.

---

## Per-section scorecard format

When self-checking, the Writer emits one block per section:

```
### <section id> — <title>
- R1 purpose-first: pass | fail (note)
- R2 signal density: <meta>/<total> = NN% (pass if <15%)
- R3 mechanism+comparison: pass | fail (note)   [only where algorithms appear]
- R4 simulation concreteness: pass | fail (note) [only in methodology]
- R5 motivation: pass | fail (note)              [only where motivation appears]
- R6 length discipline: pass | fail (subsections flagged to cut)
- R7 citation noise: pass | fail (worst offenders)
- verdict: ready for human review | not ready (blocking items)
```
