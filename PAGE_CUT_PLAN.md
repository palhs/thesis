# Thesis page-cut plan — 80+ pp → ~41 pp (hard cap 50, incl. appendix)

**Locked decisions (2026-06-29):** medium cut (~40–42 pp body+appendix) · keep all 6
chapters (no Ch5/Ch6 merge) · Appendix A kept lean (~2 pp). Status: PLAN ONLY — no
chapter edited yet.

This plan is the source of truth for the cut. Execute top-to-bottom in the three
priority waves. Re-measure the rendered PDF after Wave 1 before doing Wave 3 prose
cuts, so we cut chars only as far as the page count actually requires.

---

## 0. Target budget (arithmetic)

| Part | Now (pp) | Target (pp) | Lever |
| :-- | --: | --: | :-- |
| Front matter | 5.0 | 4.0 | trim abstract |
| List of Figures | 3.0 | 1.5 | fewer floats (29→~16 figs) |
| List of Tables | 1.0 | 0.5 | fewer tables (10→~7) |
| Ch1 Intro | 2.7 | 2.0 | §1.1/§1.2 nip |
| Ch2 Lit review | 5.0 | 3.5 | merge §2.1+§2.2; §2.4.2→1¶ |
| Ch3 Methodology | 17.0 | 10.0 | ledgers + §3.6 + move §3.4.4 walkthrough → App A |
| Ch4 Results | 25.5 | 12.5 | 21→8 in-body figs; cut table-walking prose |
| Ch5 Synthesis | 7.0 | 4.0 | drop §5.1/§5.2 framing; one no-dominance statement |
| Ch6 Conclusion | 4.5 | 3.0 | §6.1 leans on Table 6.1; trim §6.4 |
| Appendix A (code+contract) | 2.0 | 2.0 | keep config contract + absorb §3.4.4 walkthrough |
| Appendix B (heat-conduction) | 10.0 | 0 | **DELETE — leftover mitthesis.cls example** |
| **Total** | **~80.5** | **~43** | ~2 pp slack to reach 40–42 |

Prose word targets (current → target):
Ch1 1341→1000 · Ch2 1710→1400 · Ch3 6141→4300 · Ch4 7493→5500 · Ch5 2659→1900 ·
Ch6 1672→1300. Total 21,016 → ~15,400 (cut ~5,600 words, ~27%).

---

## INVARIANTS — do not cut, move, or weaken

- All five RQ answers, verbatim-aligned to §1.5 wording (RQ1 §4.3.1; RQ2 §4.4.4
  closing ¶ + Fig 4.21; RQ3 §4.2.4; RQ4 §4.4.4; RQ5 §5.4).
- §3.2 system model (single fixed engine + split-ownership invariant + determinism
  /reproducibility claim) · §3.3 deviation ledgers (compress wording, keep every
  numbered departure + Snowman rescaling + n=4 exclusion) · §3.5 metric schema (ACU,
  commit_latency_ms, goodput-not-tps, reliability semantics) · §3.6 threats.
- §4.2.4 + Fig 4.6 (theory-vs-measured) · all of §4.3 · all of §4.4 + Table 4.2.
- §5.3, §5.4 + Table 5.1 · §6.2 Limitations.
- Reproducibility evidence (commit_hash/seed provenance — claim stays in body even if
  the worked CSV row moves to App A).

Replace every removed cross-reference with an inline section ref `(§3.5)`, **never a
`[[wiki/...]]` link** — concept/experiment wikilinks are stripped on LaTeX export, so
no claim may rest on one. Source-page `[[wiki/sources/...]]` links survive as `\cite`
and stay.

---

## WAVE 1 — zero content lost (~18 pp). Do first, then re-measure.

### 1A. Delete Appendix B
Leftover `mitthesis.cls` example ("One-term coefficients for heat conduction",
"A multipage table of numbers"). Remove from the LaTeX (sibling `../thesis-tex`) and
from the ToC. No markdown source in `drafts/` — this is a tex-side deletion.
Saves ~10 pp.

### 1B. Ch4 figures 21 → 8 in-body (+2 to appendix, 2 deleted)
Merge into multi-panel figures; rewrite captions to match. Re-letter sequentially
on execution. Saves ~6.5 pp + shrinks List of Figures.

| New | Merge / action | Note |
| :-- | :-- | :-- |
| Fig A | 4.1+4.2+4.3+4.4 | baseline metric-vs-n 2×2 panel (goodput-CI, latency, tps, goodput) |
| Fig B | **drop 4.5, keep 4.6** | 4.6 (dashed theory + measured markers, log axis) is a superset of 4.5 — same `total_msgs_per_acu` data, just with the prediction lines overlaid. Keep 4.6; its caption must also carry 4.5's job (the order-of-magnitude separation that answers RQ3). In §4.2.4 collapse the two figure call-outs into one and trim the duplicated explanatory prose accordingly. |
| — | **4.7 DELETE** | success=1.0/fork=0.0 everywhere; state in one sentence |
| Fig C | keep 4.8 | moderate-delay latency (RQ1) |
| Fig D | 4.9+4.10 | finalization-degradation curve + AURC ranking, 2-panel |
| Fig E | 4.11+4.12+4.13 | mechanism panel; 4.13 operator-pareto may drop to prose if tight |
| Fig F | 4.14+4.15 | liveness vs φ (delayed + silent), 2-row panel |
| Fig G | 4.16+4.18 | equivocation: liveness + safety-violation |
| Fig H | keep 4.21 | RQ2 throughput degradation |
| App | 4.19 | Casper slashable stake → appendix |
| App | 4.20 | adversary outcome map (it visualizes Table 4.2) → appendix |
| — | **4.17 DELETE** | view-change counts (10/25) already in text + Table 4.2 |

Keep Table 4.2 in body (load-bearing). Fold Table 4.1 (3-row baseline means) into the
§4.2.6 sentence.

### 1C. Table merges (10 → ~7)
- Ch3: keep Table 3.1 + 3.2; consider folding Table 3.3+3.4 (latency/throughput +
  overhead/reliability schema) into one wide schema table.
- Ch4: drop Table 4.1 into prose (above).

---

## WAVE 2 — redundancy removal (~4,000 words). No argument/number lost.

R1. **No-dominance verdict** — canonical home **§5.4 only**. Delete the full
restatements in: §4.4.4 ¶ "This no-dominance result is not an artifact…" (keep the
mechanism map + inversions; end by handing to Ch5), §5.1, §5.5 (keep implications,
drop the re-verdict), §6.1 prose (Table 6.1 carries it), §6.4 (collapse to 3–4
sentences). ~600 w + ~400 w.

R2. **Per-protocol findings narrated 3×** → canonical **§5.3**. Ch4 §4.4.1–§4.4.3 keep
their numbers (report-once); cut §4.4.4 ¶1 (lines ~706–725) to a ~5-sentence
pointer at Table 4.2/Fig 4.20. Ch6 §6.1 prose ¶2–3 (re-narrates Table 6.1 rows) →
~6 sentences. ~600 w.

R3. **Standing caveats** — define once, then bare `(§x)` ref:
- ε "reported not witnessed": define §3.5 + one restatement §4.4.3; strip from §4.3.4,
  §5.3.3, §5.4 table note, §6.2.
- latency-only "flatters PBFT/FFG, no compute cost": define §3.6; strip from §1.4,
  §3.2, §4.4.4, §5.2, §6.2.
- "spares the view-0 primary / leader-disruption uncovered": keep §4.4.4 + §6.2; drop
  §4.4.1, §5.3.1.
- ε bound `5e-15 / 3e-11` + "rounding lifts ratio above 0.8 only at small K": derive
  once §3.3.3 ④; elsewhere cite the two numbers without re-deriving.
- "no protocol forks / loss erodes liveness not safety": once per sweep, not 3× inside
  §4.4. ~700 w total.

R4. **§1.2 incident callback** — canonical **§5.5**; keep one earned instance in §4.3.4
(Casper mechanism). Delete from §5.3.2 and §6.1. ~200 w.

R5. **Roadmap/scaffolding paragraphs** — §4.1 and §5.1 to 2–3 sentences each; §5.2
"common frame" framing (re-defines Pareto dominance + re-lists §3.5 conventions) → one
cross-ref sentence. ~550 w.

R6. **Hedging** — "the contribution is not the bare statement… which a reader might
anticipate" appears in §4.4.4, §5.1, §5.4 → keep once. ~120 w.

R7. **Ch2 — cut the tutorial half + the per-family subsections, protect the gap**
(promoted from Wave 3 per author request; these read as "excessive / skippable" and
should go early).
- Cut/merge **§2.1 (blockchains, consensus problem) + §2.2 (CAP, "fork in the road")**
  into one short framing section — textbook for a BFT-fluent committee.
- **Cut §2.3.1 + §2.3.2 + §2.3.3** (the three per-family weakness paragraphs) and the
  bridging sentence at the end of §2.3 that introduces them. Their headlines already
  live in Table 2.1's "Adversarial pressure point" row, and Ch4 §4.4 measures each
  weakness directly. §2.3 keeps its intro prose + **Table 2.1** + the Notation table +
  the "At n=7" example (Table 2.1 is the load-bearing part).
- §2.4.2 (three surveys + Gervais) → one paragraph.

**Boundaries — preserve when cutting §2.3.x:**
- Keep ONE sentence carrying the Amores-Sesar/Cachin/Schneider **[10]** result (two
  undecided validators stall Snowman's counter beyond poly(β) rounds) — the literature
  grounding for Snowman's measured delay/silence fragility; it appears nowhere else as
  a finding. Fold it into §2.3 intro prose or §2.4. ([7] accountable safety is safe —
  re-cited in Ch5/Ch6.)
- Do NOT cut §2.4 / §2.5 (the gap) or Table 2.1 / Table 2.2 — these justify the
  contribution and carry the gap evidence.
~700 w (§2.1/§2.2 merge ~350 + §2.3.x ~350).

R8. **§3.6 — compress recap, consolidate limitations into §6.2** (promoted from Wave 3
per author request). §3.6 reads as excessive because it is ~90% recap of §1.4 / §3.5 /
§3.4.3, and it overlaps §6.2 Limitations. Move:
- §3.6 → a tight **bullet list** naming only the four deliberate exclusions
  (no compute/bandwidth cost · synthetic open-loop workload · sub-production scale ·
  leader-disruption surface uncovered) + the two caveat-type properties
  (commensurability-by-convention, regime-coherence rules). Drop all prose that re-tells
  §1.4/§3.5.
- §6.2 **keeps the full reflective limitations**; de-duplicate so the two sections do
  not narrate the same exclusions twice.
**Boundary — do NOT delete the threats themselves.** Threats-to-validity is the
integrity gate the examiner checks; only the *recap padding* goes, not the substance.
~400 w.

---

## WAVE 3 — frame compression (only as far as page count needs)

> Ch2 (§2.1/§2.2) and §3.6 moved up to Wave 2 (R7, R8) at author request — they read
> as the most skippable / excessive parts, so they are cut early rather than last.

C2. **Ch3 §3.3 deviation ledgers** — compress each numbered entry to one line; drop
prose duplicating Table 3.2; collapse the triple-stated exponential-bound gloss in
§3.3.3 ③④. Keep every departure + validity boundary. ~400 w.

C3. **Ch3 §3.2** — keep determinism + split-ownership once; drop the repeated
"isolation is not commensurability" framing (recurs in §3.5/§3.6 openings). ~150 w.

C4. **Move §3.4.4 "One run, end to end"** (PBFT walkthrough + CSV-row example) → App A,
beside the config/input contract. Body keeps a 2–3 sentence pointer. Frees Ch3 body
without losing the illustration.

C5. **Ch1 §1.1/§1.2** — three foundational results to ~3 sentences; incident catalog
(Solana×4, Eth×2, Cosmos, Sui) → 2–3 representative incidents (the Ch4/5/6 callbacks
only need Eth-May-2023 + one liveness halt). ~300 w.

C6. *(moved to Wave 2 R7 — Ch2 tutorial-half compression.)*

C7. **Ch4 §4.2 baseline** — compress §4.2.1 (degenerate-CI) to one sentence; §4.2.2 /
§4.2.3 ("flat in n") to a paragraph each; keep §4.2.4 (RQ3) intact. ~400 w.

---

## Per-wave execution mechanism (stale-snapshot + port + push)

Each wave runs as a self-contained cycle so the rendered PDF can be re-measured
between waves and the pre-cut text stays available for side-by-side review:

1. **Snapshot.** Copy every chapter this wave will edit into
   `drafts/stale/ch<N>_<slug>.preW<k>.md` (k = wave number). These are archival diffs
   only — kept out of `wiki/index.md` and excluded from the lint walk, deleted after
   human merge. (Git history already covers this; the stale copies are a reviewer
   convenience for in-tree before/after diffing.)
2. **Rewrite.** Write the cut chapter back to its canonical name
   `drafts/ch<N>_<slug>.md` (full-file Write for heavy cuts).
3. **Port.** Mirror the changes into `../thesis-tex/*.tex` (sibling repo, outside this
   repo). drafts/ is source of truth; tex is the port.
4. **Build & measure.** Rebuild the PDF, count pages against the §0 budget. If already
   under budget, later waves cut only as far as needed (preserve prose).
5. **Commit & push.** Commit this repo (`task <N>: …`) and commit `thesis-tex`
   separately. **Overleaf push is left to the human** — pushing to the external
   Overleaf remote needs the user's auth; the agent stops after the local tex commit
   and hands off (per the standing sibling-repo convention).

> drafts-side vs tex-side split: prose/structure/figure-callouts/captions/§3.4.4-move =
> **drafts/ then port**. tex-only = **delete Appendix B**, **regenerate plot PDFs +
> multi-panel `\includegraphics`**, front matter + auto-generated List of
> Figures/Tables.

## Execution & process notes

- This is a **Writer** task spanning all chapters → one **new branch dedicated to the
  cut** (do not reuse `task/sentence-density-pass`), In Review, human merge
  (per `docs/workflow.md`). Add a task ID to `TASKS.md`, flip In Progress on pickup.
- **Ledger debt:** moving §3.4.4 to App A, deleting figures, and any RQ-answer
  relocation are scope/forward-reference changes → reconcile `docs/draft-narrative.md`
  §1 spine / §2 RQ-closure / §3 forward-ref / §10 cheat-sheet in the same pass
  (`draft-narrative.md` §11). The lint pass cross-checks these.
- Run the mandatory `/humanizer` gate before In Review (draft-narrative requirement for
  post-Ch3 chapters).
- After Wave 1, rebuild the PDF and re-measure. If already ≤44 pp, Wave 3 can be
  partial — cut only to the budget, preserving prose where possible.
