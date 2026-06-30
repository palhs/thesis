# Whitespace / print-representation fix plan (post-Wave-4)

**State (2026-06-30):** thesis compiles at **48 pp total / 36 content** after the Wave-4
examinability cut (T76, merged to Overleaf). Remaining problem: ugly vertical whitespace
that wastes pages and prints badly. **Constraint from the author:** do NOT solve this by
changing the `[H]` float specifier to `[h]/[ht]` — that risks figures landing mid-paragraph,
which is rejected.

This file is a PLAN ONLY. Execute in a fresh session. Sibling tex lives in
`../thesis-tex/MIT-thesis-template/`; markdown drafts in `drafts/` are source of truth, tex
is the port (mirror any prose-affecting change both ways). Overleaf push is the author's.

---

## Diagnosis (already done — don't re-investigate from scratch)

- `\documentclass[oneside]{mitthesis}`; mitthesis `\LoadClass[12pt,openright]{report}`.
  - `report` + `oneside` ⇒ already `\raggedbottom`, no blank verso pages, single-spaced
    (setspace commented out). **So the whitespace is NOT spacing/flushbottom** — it is float
    placement.
- **19 floats are forced `[H]`** (11 figures + 8 tables). `[H]` = "exactly here, never
  float." When a `[H]` float is taller than the space left on the current page, it is pushed
  to the next page and the current page ends short → the page-bottom gap the author sees.
- Aggravators: several **multi-panel figures at `width=\linewidth`** are tall
  (`loss_resilience_panel`, `liveness_delay_offline_panel`, `equivocation_panel`,
  `theory_vs_measured`, `throughput_degradation_vs_phi`, `adversary_tradeoff_matrix`); the
  **8 tables carry 36 `\addlinespace`** rows, inflating their height. Taller floats bump more
  often.
- No explicit `\clearpage/\newpage` in the chapters (good — gaps are not forced by hand).

**First execution step:** recompile, then walk the PDF and list the ~6–10 pages with the
worst bottom gaps and which float immediately follows each gap. All Tier-2 work is targeted
at those pages; do not guess.

---

## Fixes — all keep `[H]` (floats stay anchored, no mid-prose risk)

### Tier 1 — global, cheap, shrink floats so they fit more often (do first, recompile)

1. **Strip table row-padding.** Remove the 36 `\addlinespace` (or replace the lot with one
   `\renewcommand{\arraystretch}{1.1}` in `mydesign.tex`). The 8 tables get materially
   shorter → fit the space left on their page → far fewer bumps. Biggest easy win. Verify no
   table now looks cramped.
2. **Tighten caption footprint.** In `mydesign.tex` add
   `\captionsetup{font=small,skip=4pt}` (caption package is already loaded there). Smaller
   caption font + less skip shortens every float.
3. **Recompile, re-measure.** Tier 1 alone may reclaim several pages.

### Tier 2 — per-float sizing + surgical nudges (after Tier 1, target the listed gap pages)

4. **Cap the tall panel figures.** For each multi-panel figure still bumping, add
   `height=0.42\textheight,keepaspectratio` (or drop `width` to `0.85\linewidth`) so it is
   short enough to share its page with text. Tradeoff: slightly smaller plots — they are
   panels and stay legible; check each after.
5. **`\enlargethispage`.** On a page where a float *just* misses fitting, put
   `\enlargethispage{2\baselineskip}` near the top of that page to pull 1–2 extra lines on so
   the float fits and the gap closes. Safe, local, per-page.
6. **Local reflow.** Move a float's source position by a paragraph (still adjacent to its
   first `\ref`), or let two short floats share one page, so floats land at natural page
   positions. No semantic change; keep each float within a paragraph or two of its reference.

### Tier 3 — OPTIONAL, author's call (the constraint, clarified)

7. **`[tbp]` for FIGURES only** (never `[h]`/`[ht]`). Important clarification of the rejected
   approach: `[t]`/`[b]`/`[p]` place a figure at the page **top**, **bottom**, or on a
   float-only page — they do **not** put a figure mid-paragraph. Mid-prose placement comes
   from `[h]` (here), which this plan does NOT use. `\ref{}` keeps every "Figure 4.x" text
   reference correct wherever the figure floats. This is the textbook fix and the most
   effective single lever; the only cost is a figure may not sit exactly at its mention
   (it appears at the nearest page top/bottom). Leave tables as `[H]`. **Decision needed from
   the author before applying** — they were previously burned by `[h]`, which is a different
   specifier.

### Tier 4 — optional, requirements permitting

8. **11pt instead of 12pt** (change the `\LoadClass` point size or the documentclass option).
   Large page-count drop, but **confirm the program does not mandate 12pt** before doing this.
9. **Front-matter polish.** Inspect ToC / List of Figures / List of Tables for sparse pages;
   optionally reduce the large vertical drop above chapter titles via `titlesec` (already
   referenced, commented, in `mydesign.tex`).

---

## Order, goal, guardrails

- **Order:** Tier 1 → recompile/measure → Tier 2 on remaining gap pages → ask author about
  Tier 3 → Tier 4 only if still over target.
- **Goal:** reclaim the gaps for clean print; 48 pp likely falls to ~42–44 as a side effect.
- **Guardrails:** keep `[H]` (no mid-prose figures); keep each float within ~1–2 paragraphs
  of its first reference; verify every `\ref`/`Table~`/`Figure~` still resolves after each
  tier; recompile and eyeball after each change; mirror any caption/prose edit into the
  `drafts/ch*.md` source. Do not touch `raw/`.
