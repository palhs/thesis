# Readability pass

A find-and-simplify protocol for thesis draft prose (`drafts/ch*.md`). It
targets one failure mode: a sentence that is hard to read not because its
content is hard, but because it packs three or four ideas into one clause
chain joined by em-dashes and semicolons, burying the causal order.

This is a Writer-role pass. It sits below `draft-style.md` (which fixes
register, voice, citation discipline) and is gated, like any chapter change,
by the `/humanizer` step and the ledgers of `draft-narrative.md`. It changes
sentence *structure*, never claims, numbers, citations, or rigor.

## Core principle

**One sentence, one idea, one straight causal chain.** When a sentence states
a cause, an effect, and a consequence, order them linearly and front-load the
cause. Do not bury a link inside a dash-aside or a trailing `rather than X`.

## Step 1 — Find candidates

Mostly mechanical. Flag a sentence carrying ≥2 of:

- **≥2 em-dashes** in one sentence (stacked appositives).
- **A semicolon joining two independent clauses**, each a complete idea.
- **Length > ~45 words.**
- **A buried causal chain**: the cause sits inside a dash-aside, or the payload
  hangs off a trailing `rather than …` / `so that …`.
- **Scaffolding phrases** that announce structure instead of delivering it:
  "The first governs…", "Two features of this…", "It is worth noting that…".
- **A coined abstraction with no concrete anchor** ("configuration artifact",
  used where "the chosen input rate" is what is meant).

The first two are greppable: counting `—` and `;` per sentence is an effective
coarse filter. Run it per chapter to produce a candidate list.

## Step 2 — Transform

1. **Split at semicolons and dash-appositions** into separate sentences — one
   idea each.
2. **Linearize the causal chain, cause first** (e.g. latency-only model → no
   saturation point → peak-throughput figure is meaningless → measure goodput).
3. **Promote content out of the dash-aside; cut or demote scaffolding.**
4. **Replace a coined abstraction with the concrete thing it denotes.**
5. **Cut restatement** — when two clauses say one thing, keep the sharper.

## Step 3 — Guardrails (do not lose)

The most important step. Structure simplifies; evidence and rigor do not.

- **Keep every citation, wikilink, and cross-reference.** A claim must still
  stand on its inline evidence (number, formula, figure) — wiki concept and
  experiment links are stripped on LaTeX export and never carry the evidence.
- **Never delete a qualification that bounds a claim.** The thesis voice
  depends on honest hedging; `draft-narrative.md` gates on it. A tail like
  "reported as robust only when it survives the sensitivity sweep" is
  load-bearing and stays. A tail that merely restates the prior sentence can go.
- **Distinguish "vestigial → delete" from "load-bearing → keep or gloss".**
  Verify against the wiki before deleting a term or passage. A genuinely
  unused column and the section explaining its non-use can be cut outright; a
  term that carries a real distinction must be glossed, not removed.
- **Define notation before use.** A symbol or coined term in a live formula
  gets a one-clause gloss at first use (or a forward pointer to where it is
  defined), not deletion.
- **Hold the technical register.** This pass improves readability of structure,
  not by softening precision or swapping technical terms for loose ones.

## Worked examples

Before → after, from the pass that produced this protocol.

- **Split + linearize.** "Because the network is latency-only, the simulator
  has no saturation point — a block of one and one of a thousand commit at the
  same latency — so throughput is measured as goodput …; a peak measurement is
  deferred … rather than reported as a configuration artifact." → two sentences:
  one establishing latency-only → no saturation → peak reflects only the input
  rate; one stating goodput is used and peak is deferred.

- **One idea per sentence.** "A deadline stop is therefore not in itself a
  liveness failure — a run is scored as a failure only when no honest validator
  commits inside the window, the condition the `success_rate` column reports
  against `t_max`." → three short sentences: deadline ≠ failure; the definition
  of failure; what `success_rate` records.

- **Cut redundancy.** The Casper FFG coherence passage lost "The first governs
  Casper FFG slot timing" (absorbed into the opening) and "the matrix owns the
  per-timeline pairing" (overlapping with "the runner refuses"), ~40% shorter
  with no lost content.

- **Delete vs gloss.** `finality_latency_ms` — an unused column whose section
  existed only to explain its non-use — was deleted outright. `result.now`,
  `E[round_latency]`, and `attest_offset` — terms inside live formulas — were
  glossed or harmonized, not deleted.

## How to run it across the thesis

1. Per chapter, run the mechanical scan (Step 1) to get a candidate list.
2. For each candidate, apply the Step 2 decision: split / cut-redundancy /
   gloss-term / leave-as-is.
3. A reviewer pass checks the Step 3 guardrails — every citation still present,
   no bounding qualification lost.
4. Run the `/humanizer` gate before flipping to In Review.

Commit per chapter or per batch, following the per-task workflow.
