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

## WAVE 3 — DEEP CUT (~6,300 words). Per-chapter, aligned with author 2026-06-29.

Supersedes the prior C2–C7 frame-compression sketch (folded in below). Wave 2 removed
redundancy (~1,400 w) but fell short of the 4,000 w goal; because the hard constraint is
**total page count** (50 pp incl. appendix), this wave **deletes content, does not relocate
it** — moving prose to App A does not help the cap. **Ch1 and Ch2 are left untouched**
(Ch2 already at target after Wave 2). Execute **Ch3 → Ch4 → Ch5 → Ch6**.

Projected: Ch3 5,893→~3,150 · Ch4 6,930→~5,200 · Ch5 2,285→~1,150 · Ch6 1,478→~780.
Total 19,397 → **~13,090** (cut ~6,300; below the 15,400 prose target).

**Cross-cutting editorial rule (Ch4, Ch5): summarize over ranges, spot anomalies.**
Stop reciting per-cell numbers (`n = 10 / 25`, each `φ`) — the reader sees those in the
figures. Describe the *trend over the whole range* and keep a number only when it is
(a) an RQ answer, (b) a threshold/cliff (a `φ*` where a protocol dies), or (c) an
anomaly/inversion worth spotting. Figure captions are tightened to "describe the panel +
source", never re-narrate the result.

### Ch3 — Methodology (cut ~2,740 w → ~3,150)
1. **§3.4.4** — keep Figure 3.6 (6-phase diagram); delete the walkthrough prose + CSV-row
   narration behind it. Keep 2 sentences of the reproducibility claim (commit_hash/seed).
   ~550 w.
2. **§3.2** — remove duplicate framing: network-phases-cross-GST stated twice (≈ll.50–54 &
   96–98), determinism restated in §3.4.1, "isolation ≠ commensurability" recurs in §3.5/§3.6.
   Keep each once. ~250 w.
3. **§3.5** — keep Table 3.3 + 2–3 lead sentences + definitions of key fields not in the
   table (ACU, `commit_latency_ms`, goodput-not-tps, safety/liveness semantics — invariants).
   Delete the "Byte overhead" note and the "Throughput basis" note (duplicate the table);
   compress the CI/CRN prose. ~500 w.
4. **§3.3 deviation ledgers** — delete all three bulleted ledgers (PBFT ①–④, Casper ①–⑤,
   Snowman ①–④); headline of each already lives in Table 3.2 "Main simplification". Keep
   only 3 load-bearing notes as short body sentences (Ch4/Ch5 cite them): Snowman rescaling
   (`K=min(20,n−1)`, `α_c=⌈0.8K⌉`, `β=15`, ratio≈0.8, ε `10⁻¹¹…10⁻¹⁵`); n=4 degeneracy
   exclusion (shortened to the main point); Casper `slot_duration`→≈5 s finality (one clause,
   §4.2 reports it as a finding). Do NOT annotate the diagrams (avoids a figure-regen task).
   ~830 w.
5. **§3.6** — compress intro + the two caveat-properties to one line each; keep all four
   threats verbatim (integrity gate). ~150 w.
6. **§3.4.1** — reduce to the two genuinely new points (config-by-code, buffer/clip window).
   ~100 w.
7. **§3.4.2** — generalize: replace number-dense prose with a compact Family A/B/C matrix
   table (axis swept, `n`, RQ, key values) + overview prose. Keep the values Ch4 needs
   (`n∈{4,7,10,16,25}`, `φ` bands) but in the table. ~400 w.

### Ch4 — Results (cut ~1,730 w → ~5,200). Numbers are load-bearing — do not cut results.
- §4.1 roadmap → 2 sentences (~80). §4.2.1 statistical-reliability → fold to 1 sentence in
  §4.2 intro (~90). §4.2.2 Casper calibration para → drop formula re-derivation +
  2500/5000/10000 enumeration (in §3.3.2 ③), keep the intrinsic "epoch-granularity, coarser
  at any realistic slot" (~150). §4.2.5 reliability → 1 sentence (~60). §4.2.4 "two readings"
  → tighten, keep RQ3 verdict + Fig 4.2 (~80). §4.3.4 caveat para → drop ε `5e-15/3e-11` +
  finality-kind restatement (§3.3.3, repeats §4.4.3); keep loss=upper-bound caveat + May-2023
  callback (~100). §4.4 setup → trim Wilson-width explanation that repeats §3.5 (~100).
  §4.4.4 "two qualifications" → consolidate the 4 caveats to short pointers, B(i): keep them
  next to the verdict but as pointers (leader-disruption pointer to §3.6) (~180). Hedge
  "contribution is not the bare statement…" → keep once (~40). Captions Fig 4.4/4.5/4.6/4.7/A.2
  → cut hard to panel-description + source (~150).
- **Apply the range-over-points rule** to §4.3.1, §4.3.2, §4.4.1–§4.4.3 — biggest single
  lever. Guardrail: numbers in **Table 4.2** and RQ answers (Fig 4.2 RQ3, 229-conflict fork,
  ε bound, `φ*` cliffs) stay.
- **Tex-drift fix:** subsection "A note on the latency measurement point" exists only in
  `chapter4.tex:177`, not in the markdown. Delete it tex-side, replace with one clause in
  §4.2.2 ("latency read from `commit_latency_ms`, the canonical time-to-finality column,
  §3.5") and add the same clause to the markdown so the two converge.
- Keep (invariants): all result numbers; RQ1 (§4.3.1), RQ2+RQ4 (§4.4.4 close), RQ3 (§4.2.4
  + Fig 4.2), all of §4.3 and §4.4, Table 4.2, May-2023 callback.

### Ch5 — Synthesis (RESTRUCTURE → ~1,150, cut ~1,135). Anchor everything on Table 5.1 + Fig 5.1.
The §5.3.1–§5.3.3 per-family number-walk is replaced. New structure:
- **§5.1 The joint reading** (~3 sentences) — merge old §5.1 + §5.2: Ch4 isolated each axis,
  RQ5 asks the joint question, read off Table 5.1 + Fig 5.1, "adds a reading not a measurement".
- **§5.2 The cross-regime frontier** — move Table 5.1 + Figure 5.1 up to here as the anchor;
  all exact per-family numbers (`2n`, `1.2n`, 229, ε, ×62, 0.904, AURC…) live in the table /
  Fig 5.1 caption only.
- **§5.3 Conclusions drawn from the frontier** — three drawn conclusions, written as insights,
  not number-walks:
  1. **No-dominance** — each family non-dominated on ≥1 axis; survives removing the
     definitional accountable-safety row → answers RQ5.
  2. **Structural inversions (mechanism map)** — each defense is also an exposure. Spot the
     sharpest result (Snowman: most delay-tolerant when peers are slow ↔ least tolerant when
     they go silent) and PBFT (liveness-robust ↔ unaccountable fork). **Name Casper FFG
     explicitly**: never first on any axis yet never catastrophic, holding the accountable-
     failure corner only a slashing-based protocol can occupy. Keep the "contribution is the
     map, not the bare no-winner statement" hedge once.
  3. **The empty corner** — resilience is bought with latency; the cheap+fast+resilient corner
     is empty.
- **§5.4 Implications and hand-off** (old §5.5) — select by dominant threat; §1.2 incident
  callback (canonical home); hand to Ch6.
- Per-family non-domination evidence is NOT lost — it moves into Table 5.1. (Honors the
  §5.3/§5.4/Table 5.1 invariant: the evidence survives, the prose narration is what changes.)

### Ch6 — Conclusions (DEEP COMPRESS → ~780, cut ~700). A summary, not a re-narration.
- §6.1 → keep Table 6.1; prose to 2–3 sentences (the structural-choice through-line + table
  pointer) (~150). §6.2 Limitations → keep every limitation (integrity gate) but as tight
  prose/bullets, drop the long lead-ins (~130). §6.3.1 → 3–4 sentences (aggregation cuts
  `O(n²)→O(n)`; faithful extension holds optimization level constant; plan recorded in repo)
  (~200). §6.3.2 → five directions, one clause each, keep all five incl. adaptive-timeout
  (~120). §6.4 → 3–4 sentences (contribution = one harness + a map-of-mechanisms; §1.2
  callback one sentence) (~100).

---

### Folded-in prior sketch (C2–C7), for traceability
- C2 → Ch3 item 4 (ledgers, deepened to full deletion). C3 → Ch3 item 2. C4 → Ch3 item 1
  (changed from *relocate* to *delete walkthrough, keep diagram* — relocation does not help
  the cap). C5 (Ch1) → **dropped**, Ch1 left untouched. C6 → done in Wave 2 R7. C7 → Ch4
  §4.2 items above.

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
