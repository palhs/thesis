# T73 — Narwhal removal + Tier-1 prose condensation (first pass toward ~60pp)

**Role:** Writer (+ meta: this is a scope change, so ledger reconciliation is in-scope — see CLAUDE.md "Scope discipline").
**Goal:** First condensation pass on the markdown drafts. Strip the Narwhal+Tusk / four-family
scaffolding (rescope the *presentation* to three families) and apply the Tier-1 prose cuts.
Figures are **out of scope** (a later pass). Output is markdown edits + a port-checklist; the
human does the `.tex` mirror and the Overleaf push.

> Read this whole file first. It is written for a cold session that did **not** see the planning
> conversation. Don't re-derive the decisions — they're locked in §0.

---

## 0. Locked decisions (do not relitigate)

| # | Decision | Resolution |
|---|---|---|
| 1 | What "remove Narwhal" means | **Strip all body scaffolding**; the thesis already evaluates three families and the contribution is already three. Relocate the DAG acknowledgment to **one** Ch6 §6.3 further-work sentence. |
| 2 | Prose scope | **Full Tier-1 condensation + Narwhal**, in one task. |
| 3 | LaTeX / Overleaf | Agent edits **markdown only** and emits a **port-checklist** (§6). Human mirrors into `chapter*.tex`, compiles, checks page count, pushes Overleaf. **Do not touch `../thesis-tex/`.** |
| 4 | Clean start | **Step-0 commit** the pending clarity edits (ch3/ch4/macro.svg) on the new branch before any new work. |
| 5 | Reframe depth | **Pure three families.** No design-space nod in Ch1. DAG appears in exactly **one** place in the whole thesis: the new Ch6 §6.3 further-work line. |

**Why this is low-risk:** `docs/draft-narrative.md` already records "Three families, Narwhal+Tusk
deferred — stated consistently in Ch1–Ch4" and RQ5 is already closed "over the three families
evaluated." We are removing *descriptive scaffolding*, not rescoping the contribution.

---

## 1. Cold-start context

- **Git drift is real here.** Branch context has moved before. **First action: verify refs**
  (`git branch --show-current`, `git status`). Expect to start from `main`. T62 (figures) and T72
  (LaTeX port → 84pp) are already merged.
- **Source of truth:** markdown `drafts/*.md` are authored first; `../thesis-tex/MIT-thesis-template/chapter*.tex`
  mirrors them. This task edits **only** `drafts/`, `TASKS.md`, `wiki/log.md`, `docs/draft-narrative.md`,
  and this `docs/plans/` folder.
- **Working tree is dirty on arrival:** uncommitted clarity edits in `ch3_methodology.md` +
  `ch4_results.md` (formula fixes, `finality_latency_ms` retired, §4.2.6 deleted) + `macro.svg`, plus
  untracked tooling (`review/`, `tools/`, svgs). The clarity edits are **intentional, keep them** —
  step 0 commits them. Untracked tooling is orthogonal; leave it.
- **Page target:** 84pp (incl. refs) → ~60pp overall. This pass (prose + Narwhal) will not reach 60
  alone; the figure pass closes the rest. Record word-count deltas as the page proxy (no local TeX
  build — `tectonic` is installed but does not compile this template turnkey; page count is verified
  by the human on Overleaf).

---

## 2. Pre-flight (step 0)

```
git branch --show-current          # expect: main
git status --short                 # expect: M ch3, M ch4, M macro.svg + untracked tooling
git checkout -b task/T73-narwhal-condense
# Commit the pending clarity pass FIRST, as its own boundary:
git add drafts/ch3_methodology.md drafts/ch4_results.md wiki/diagrams/runtime/macro.svg
git commit -m "task 73: preserve pending clarity pass (formula fixes, finality_latency_ms retire, §4.2.6 cut)"
```

Then add the TASKS.md entry (paste under the active-tasks section), flip **In Progress**, and commit
`task 73: start` alone:

```
- [ ] **T73** `H` Writer — Narwhal removal + Tier-1 prose condensation (first pass toward ~60pp)
  _Outcome:_ Three-family reframing across Ch1–Ch4 (Narwhal/four-family scaffolding stripped, DAG
  relocated to a single Ch6 §6.3 further-work line) + Tier-1 prose cuts (Ch3 §3.4.4/§3.5/§3.6,
  Ch5 §5.2/§5.3, Ch6 §6.1/§6.3.1, Ch2 variant trim); draft-narrative ledgers reconciled; figures
  deferred. · _Artifact:_ `drafts/ch{1,2,3,4,5,6}.md`, `docs/draft-narrative.md`, port-checklist ·
  _Verify:_ see plan §5; zero residual Narwhal/four-family except the one Ch6 further-work line
```

> **Do not mark Completed** — human only.

---

## 3. Execution method — chapter by chapter, one commit each

Each chapter is one coherent commit that does **both** the Narwhal strip **and** that chapter's
Tier-1 condensation, so overlapping sections (Ch2, Ch3) are touched once. Match by **section number +
quoted anchor phrase** (grep), not line numbers — lines drift. Run the per-chapter grep gate (§5)
before committing each.

Commit message pattern: `task 73: <chapter> — narwhal strip + condense`.

### Ch1 — `drafts/ch1_intro.md`  (commit 1)
**Narwhal / four→three:**
- §1.1 opening: `"Four families occupy four distinct points in that space"` → reframe to three families.
  **Delete the DAG-based bullet** from the family list. Keep PBFT-style, PoS-finality, Avalanche-style.
- RQ5: `"across the four families"` → `"across the families evaluated"` (or "the three families").
- Contribution-2: `"one protocol from each of the four families"` + `"Three of the four are implemented"`
  → `"one representative protocol from each of three families … all three implemented"`.
- Roadmap: `"Chapter 2 reviews the four families"` → "three families".
- Sweep the rest of the file for any remaining `four`/`DAG`/`Narwhal`; none should survive.

**Condensation:** Ch1 is already lean (1,428 w) — only trim the now-dangling DAG cost-detail clauses.
**Protect:** the RQ block, the §1.2 deployment-incident motivation (callbacks in Ch4/Ch5/Ch6).

### Ch2 — `drafts/ch2_litreview.md`  (commit 2)
**Narwhal / four→three:**
- §2.3 intro `"four families"` → three; remove the **DAG-based family bullet**.
- Remove the **§2.3.4 DAG-based** subsection entirely.
- **Table 2.1:** drop the DAG column. **Table 2.2:** drop the Narwhal+Tusk / Bullshark / Mysticeti rows.

**Condensation (Tier-1 variant trim):** compress the per-family paragraphs to the
weakness→adversary mapping each (the part RQ4 consumes); drop HotStuff/Tendermint/Gasper variant
name-drops except where a variant is the implemented representative (Snowman, Casper FFG).
**Protect:** the §2.4–2.5 **gap argument** — do not weaken it; its antecedents are the per-family
weakness claims you keep.

### Ch3 — `drafts/ch3_methodology.md`  (commit 3 — the big one)
**Narwhal / four→three:**
- §3.1: remove the `"written so that they need no revision when that subsection is [filled]"` /
  family-agnostic-for-the-4th framing.
- **Remove the §3.3.4 Narwhal+Tusk subsection.**
- **Table 3.1:** drop the `DAG-based | Narwhal+Tusk — deferred` row.
- **Tables 3.2 / 3.3 / 3.4:** drop the reserved `Narwhal+Tusk` column (the `—` cells).
- Remove the `"reserved column … filled once the implementation lands"` sentence(s).
- §3.5 ACU: `"Running four kinds of decision"` → three; `"The four protocols do not emit commensurable
  events … Narwhal+Tusk commits an anchor-batch over a DAG"` → three protocols, **remove the
  anchor-batch example**; `"The device that makes the four commensurable … anchor-batch for
  Narwhal+Tusk"` → three. Drop the Narwhal `—` column from the **ACU table** and the **tps table**.
  (The ACU argument stands on three incommensurable events.)
- §3.6: `"family-agnostic: the four … written to need no revision when the [4th]"` → three; drop the
  4th-family framing.

**Condensation (Tier-1):**
- §3.4.4 walkthrough: compress the six-step prose, **keep** the `commit_hash`/seed reproducibility
  sentence and the per-trial-vs-aggregated two-file distinction (Ch4 §4.2.1 leans on the latter).
- §3.2 YAML config block + the capability table: cut from the body, leave a one-sentence pointer
  `"(full run schema in Appendix A)"`. **→ add to port-checklist: user moves these into `appendixa.tex`.**
- §3.5 sub-notes (throughput-basis / byte-overhead / Snowman exception): state once, consolidate.
- §3.6 threats-to-validity: tighten prose only.
**Protect (do NOT cut content):** the deviation ledgers (§3.3.1–3.3.3 entries), the §3.5 ACU
commensurability argument, the §3.6 three exclusions + three coverage bounds. Compress prose, keep
every distinct entry/threat.

### Ch4 — `drafts/ch4_results.md`  (commit 4 — light; figures deferred)
**Narwhal / four→three only:**
- Intro: remove `"with the Narwhal+Tusk column reserved until that implementation lands"`; keep
  `"Three protocols are evaluated throughout — PBFT, Casper FFG, and Snowman"`.
- §4.4 qualification: `"the survey covers three families: Narwhal+Tusk is unimplemented, so its
  catalogued weakness — data-availability[-withholding] — is absent …"` → trim to the honest scope
  statement `"the adversarial verdict is scoped to the three families evaluated"`. The DA-withholding
  point **moves to** the new Ch6 §6.3 further-work line (commit 6).
- The "three protocols / three families" honest-scope phrasings elsewhere are fine — keep them.
- **Figures: untouched this pass.** §4.2.6 is already cut (captured in the step-0 commit).

### Ch5 — `drafts/ch5_synthesis.md`  (commit 5 — Tier-1 only; zero Narwhal)
- §5.2: cut the convention-restatement paragraphs → one cross-reference to Ch3 §3.5/§3.6. **Keep** the
  Pareto-dominance definition.
- §5.3.1–5.3.3: compress; push re-quoted Ch4 magnitudes into **Table 5.1**. **Keep every mechanism /
  inversion sentence** (those are the RQ5 contribution) and **Figure 5.1**.

### Ch6 — `drafts/ch6_conclusion.md`  (commit 6 — Tier-1 + the one DAG line)
- **ADD** one further-work sentence in §6.3.2, e.g.: *"Extending the harness to DAG-based protocols
  (Narwhal+Tusk) — whose data-availability-withholding adversary the present sweep does not cover — is
  a natural further direction."* This is the **only** DAG mention left in the thesis.
- §6.1: keep **Table 6.1** + the incidents-revisited closing paragraph; compress the per-RQ prose walk
  to one paragraph.
- §6.3.1: compress the BLS / signature-aggregation caveat (it makes one point ~4×).
**Protect:** §6.2 limitations.

---

## 4. Ledger reconciliation — `docs/draft-narrative.md`  (commit 7, mandatory)

Scope change ⇒ this is in-scope, not optional (CLAUDE.md). Update:
- **§1 spine** — ensure the three-family framing reads consistently.
- **§2 RQ-closure** — RQ5 wording must match the reworded Ch1 RQ5 ("three families" / "families
  evaluated"); already closed-over-three, just align phrasing.
- **§3 forward-reference ledger** — the Narwhal/DAG item (the "data-availability-withholding" forward
  ref) is now **discharged in Ch6 §6.3**, not scattered through Ch1–Ch4. Update the line that reads
  "Three families, Narwhal+Tusk deferred — stated consistently in Ch1–Ch4" to reflect that DAG is now
  acknowledged **only** as Ch6 further work.
- **§10 cheat-sheet** — update the Ch1/Ch2/Ch3/Ch4/Ch6 rows for the removed scaffolding.

---

## 5. Validation ("validate ra sao")

Run after each chapter (per-chapter gate) and once globally at the end.

**A. Residual-scaffolding sweep (global, must be exact):**
```
grep -rniE 'narwhal|tusk|bullshark|mysticeti' drafts/        # expect: exactly ONE hit (Ch6 §6.3)
grep -rniE 'four famil|four distinct|each of the four|four protocols' drafts/   # expect: ZERO
grep -rniE 'reserved column|needs? no revision|family-agnostic' drafts/ch3_methodology.md  # expect: ZERO (or reworded)
```
**B. Cross-reference integrity:** no dangling `§` refs to deleted subsections (esp. removed §3.3.4
and §4.2.6→§4.2.7 renumber already handled); no `[[wikilinks]]` left pointing at an anchor you
deleted. `grep -rn 'algorithms/dag-based' drafts/` should be ZERO (citation removed with the prose;
the wiki page itself stays, just uncited — harmless).
**C. Ledger consistency:** `docs/draft-narrative.md` updated (§4 above); mentally run lint-protocol
check 9 (cross-chapter ledger cross-check).
**D. Protected content present:** confirm the §3.5 ACU argument, §3.6 threats, deviation ledgers,
Table 5.1 + Fig 5.1 mechanism sentences, Table 6.1, and the §1.2 incident callbacks all survive.
**E. Page proxy:** record `wc -w` per chapter before (from `git show main:drafts/…`) and after; report
the word delta per chapter (the only page signal available locally).
**F. Mandatory gates before In Review** (per `docs/draft-narrative.md`): the §7 pre-flight rubric, the
§8 `/humanizer` gate, and a `/prj-review-panel` pass on the most-changed chapters (Ch2, Ch3).

---

## 6. Port-checklist (deliverable for the human's `.tex` work)

Write `docs/plans/T73-port-checklist.md` as you go. For every change, one row:
`chapter*.tex` target → section/table/figure → action (delete / reword / add). Group by `.tex` file
(`chapter1`–`chapter6`, `appendixa`). Call out specifically:
- the table column/row deletions (Tables 2.1, 2.2, 3.1, 3.2, 3.3, 3.4, ACU table, tps table),
- the §3.3.4 subsection deletion,
- the §3.2 YAML block + capability table **moving into `appendixa.tex`**,
- the new Ch6 §6.3 DAG further-work sentence.
This is what the human applies to Overleaf; the agent does **not** edit `.tex`.

---

## 7. Wrap-up

1. `wiki/log.md` entry (format in `docs/wiki-spec.md`): type `draft`, task 73, files touched, what
   changed and why.
2. Flip TASKS.md T73 → **In Review**; commit `task 73: narwhal removal + Tier-1 condensation`.
3. Push `task/T73-narwhal-condense`.
4. Hand-off summary: files touched, word-count deltas per chapter, the port-checklist path, residual-
   sweep result, and the explicit note that **figures + the `.tex` port + Overleaf page-count are the
   human's / a later pass's** work.

## 8. Guardrails recap
- Markdown only; never touch `../thesis-tex/`.
- Match by section + quoted phrase, not line numbers.
- Compress prose, never delete a protected entry/threat/mechanism sentence.
- DAG ends up in exactly one place (Ch6 §6.3). If the residual sweep (5A) returns ≠1 Narwhal hit, stop.
- This is a scope change ⇒ the ledger reconciliation (§4) is part of the task, not an extra.
