# Plan — Replace Swimlanes.io with Mermaid across all diagrams

**Date:** 2026-05-26
**Branch:** (to be created) `task/diagrams-mermaid-migration`
**Scope:** wiki + drafts + docs only. No `src/`. No `raw/`. No TASKS.md
status flips (this is a meta/wiki-maintenance change, not a numbered task —
land it as a single `meta:` + `wiki:` commit sequence).

---

## 1. Motivation

Swimlanes.io has no clean CLI. Every Swimlanes diagram requires a human to
open swimlanes.io, paste the source, and export a PDF — captured in the
project today as the `TODO(human-export)` marker pattern
(`docs/draft-style.md § Figures and diagrams`). Mermaid renders directly
via `mmdc` (already in use for `wiki/diagrams/concepts/bft-families-tree.md`,
landed 2026-05-26). Converting the 10 outstanding Swimlanes diagrams to
Mermaid collapses the figure pipeline to a single agent-rendered route:

- Zero `TODO(human-export)` markers in `drafts/`.
- Every figure PDF rebuildable from source with one command.
- One DSL legend in `wiki/diagrams/index.md` instead of two.
- L-W12 (final lint) check 8 ("every figure reference has a PDF on disk")
  becomes mechanically satisfiable from CI rather than waiting on the human.

## 2. Inventory

### 2.1 Diagrams to convert (10 Swimlanes → Mermaid)

All currently use ```` ```swimlanes ```` fenced blocks. Each is a sequence /
interaction diagram — the natural Mermaid target is `sequenceDiagram`.

| # | Path | Lifelines | Notable constructs |
| :-- | :-- | :-- | :-- |
| 1 | `wiki/diagrams/scheduler/bootstrap.md` | Harness, Scheduler, Network, NodeA, NodeB, Heap | `note`, `=:`, `...:`, `=>` |
| 2 | `wiki/diagrams/scheduler/event-enqueue.md` | three enqueue sources | `note`, `=:` |
| 3 | `wiki/diagrams/scheduler/event-dispatch.md` | Caller, Scheduler, Heap, Registry, EventSink, Node | `if/else/end`, `-:` |
| 4 | `wiki/diagrams/scheduler/timer-lifecycle.md` | timer lifecycle actors | `=:`, `note` |
| 5 | `wiki/diagrams/scheduler/constraints.md` | Harness, Node, Adversary, Network, Scheduler, EventSink, T40Consumer | `if/else/end`, `=:`, many `note` |
| 6 | `wiki/diagrams/runtime/macro.md` | Harness, Config, Builder, Simulator, Logger, Results | `=:`, `...:` |
| 7 | `wiki/diagrams/protocols/pbft.md` | Primary, ReplicaB/C/D | `=:`, `-:`, `if/end` |
| 8 | `wiki/diagrams/protocols/casper-ffg.md` | per-protocol validators | (audit on read) |
| 9 | `wiki/diagrams/protocols/snowman.md` | per-protocol validators | (audit on read) |
| 10 | `wiki/diagrams/protocols/narwhal-tusk.md` | ValidatorA–D | `=:`, `-:`, `if/end` |

### 2.2 Already Mermaid — no change

- `wiki/diagrams/concepts/bft-families-tree.md` (`flowchart TD`, rendered
  `bft-families-tree.pdf` on disk).

### 2.3 Prose files referencing Swimlanes (text edits only)

- `docs/draft-style.md` § Figures and diagrams — collapse the two-DSL
  branch to one (Mermaid). Remove the Swimlanes hand-off subsection.
  Remove the `TODO(human-export)` mechanism and its lint hook (see §6).
- `wiki/diagrams/index.md` — drop the `### Swimlanes.io syntax` legend
  table; keep and expand the `### Mermaid syntax` legend (add
  `sequenceDiagram` primitives — `participant`, `Note over`, `alt/else/end`,
  `loop`, `rect`, `->>`, `-->>`, `autonumber`). Rewrite §Export to drop
  the dual route; one route remains (`mmdc`).
- `wiki/concepts/system-design.md` — replace "Swimlanes.io" mentions
  (lines 33, 103) with "Mermaid".
- `wiki/concepts/system-design-protocols.md` — line 29 idem.
- `wiki/index.md` — lines 44 + 96 idem.
- `drafts/ch3_methodology.md` — remove the three `TODO(human-export)`
  markers (lines 45, 163, 214); the cited PDFs land on disk in this pass.
- `docs/superpowers/specs/2026-05-13-t17-scheduler-design.md` — §8 prose
  ("five Swimlanes.io diagrams … the legend for the Swimlanes.io syntax")
  reworded; no DSL embedded inline, so wikilinks to the five scheduler
  diagrams stay valid as-is.
- `docs/plans/2026-05-18-t20-system-design-design.md` — historical record
  of T20's design decision; leave unchanged (it documents *what was chosen
  at the time*) and let this plan supersede it.
- `wiki/log.md` — historical entries left untouched per the wiki
  contract (no silent overwrites); a new entry is appended at the end of
  this migration.

### 2.4 Artifacts to render

Ten new `<slug>.pdf` files, one per converted diagram, committed beside
their `.md` source under `wiki/diagrams/`.

## 3. Mermaid translation cheat-sheet

The authoritative Mermaid syntax reference for the project is
[`docs/mermaid-syntax.md`](../mermaid-syntax.md) — curated from the
upstream Mermaid `develop`-branch docs and limited to the constructs
this thesis uses. Read it before translating the first diagram. The
table below is the Swimlanes → Mermaid mapping; the upstream syntax for
each Mermaid target is pinned in `mermaid-syntax.md` §1.

The mapping is mechanical. Every Swimlanes construct in the inventory has
a direct Mermaid `sequenceDiagram` equivalent.

| Swimlanes | Mermaid `sequenceDiagram` |
| :-- | :-- |
| `title: T` | `%%{init: {'theme':'neutral'}}%%` + first-line comment `%% T` (Mermaid sequence diagrams have no title primitive; the wiki page H1 carries it) |
| `order: A, B, C` | `participant A`<br>`participant B`<br>`participant C` (declared in that order) |
| `autonumber` | `autonumber` |
| `A -> B: msg` | `A->>B: msg` |
| `A => B: msg` (emphasised) | `A->>B: <b>msg</b>` or `Note right of A: msg` — pick once and apply consistently (decision: bold the message text with `<b>…</b>`) |
| `A --> B: msg` (return) | `A-->>B: msg` |
| `note A, B: text` | `Note over A,B: text` |
| `=: text` (bold divider) | `rect rgb(240,240,240)` block wrapping the section, with `Note over <leftmost>,<rightmost>: <b>text</b>` as the first line inside the rect |
| `-: text` (regular divider) | `Note over <leftmost>,<rightmost>: text` |
| `...: text` (delay) | `Note over <leftmost>,<rightmost>: … text` |
| `if: cond` / `else` / `end` | `alt cond` / `else` / `end` |
| `group: label` / `end` | `opt label` / `end` |

**Rationale for the divider mapping.** Swimlanes `=:` is a heavy section
break; Mermaid's `rect` (background-shaded block) is the closest analogue
because it visually groups a span of messages. `Note over` alone (used for
`-:`) handles lightweight breaks without the block visual. This keeps
visual hierarchy intact.

**Markdown in labels.** Mermaid sequence labels accept HTML; `<b>…</b>`
maps the Swimlanes-implied bold of `=>` arrows and `=:` dividers.

**No primitive for `order:` as a lock.** Mermaid orders participants by
declaration. The plan: declare participants up-front in the same order the
Swimlanes `order:` line had them.

## 4. Per-diagram conversion procedure

For each of the 10 diagrams, apply this loop (single agent, one diagram at
a time, one commit per diagram is too noisy — batch into two commits, one
per subdirectory group: scheduler + runtime, then protocols):

1. Open the `.md` file. Replace the ```` ```swimlanes ```` block with a
   ```` ```mermaid ```` block carrying `sequenceDiagram` and the rewritten
   body per §3.
2. Keep the prose ("What this pins", "Cross-links", "Source", "Revisions")
   untouched. Only the fenced diagram block changes.
3. Render the PDF:
   ```bash
   PUPPETEER_SKIP_DOWNLOAD=true \
     npx --yes @mermaid-js/mermaid-cli@latest \
     -p <puppeteer-config.json> \
     -i wiki/diagrams/<group>/<slug>.md \
     -o wiki/diagrams/<group>/<slug>.pdf \
     -b transparent -t neutral
   ```
   (`mmdc` reads Mermaid blocks directly from Markdown; no `.mmd` extraction
   step needed. `puppeteer-config.json` already in repo from the
   bft-families-tree pass.)
4. Open the PDF; sanity-check that:
   - Every Swimlanes message appears as a Mermaid message (line count
     matches modulo divider blocks).
   - `alt` / `else` / `end` boundaries map onto the original `if` /
     `else` / `end` boundaries.
   - Lifeline order matches the original `order:` line.
   - No lifeline introduced or removed.
5. Commit the `.md` + `.pdf` together (one commit per directory:
   `wiki: convert scheduler diagrams to Mermaid`,
   `wiki: convert runtime + protocol diagrams to Mermaid`).

## 5. Prose-file edits

After all 10 diagrams are converted and rendered:

1. **`wiki/diagrams/index.md`** — single largest prose edit.
   - Top blurb: drop "Swimlanes.io for sequence/interaction diagrams, Mermaid
     for taxonomy/component diagrams" → "Mermaid for all diagrams; renders
     via `mmdc`."
   - § Legend: delete the `### Swimlanes.io syntax` subsection entirely.
     Expand `### Mermaid syntax` with the `sequenceDiagram` primitives
     enumerated in §3 above (currently the legend only covers `flowchart`
     primitives).
   - § Export for thesis figures: drop the dual route; one bullet
     ("Mermaid — agent export via `mmdc`").
   - § Status: append a Revisions-style note dating the migration.
2. **`docs/draft-style.md`** § Figures and diagrams — collapse to one DSL.
   Delete the `TODO(human-export)` mechanism paragraph. Mention in passing
   that historical drafts may carry `TODO(human-export)` markers which
   this migration retired.
3. **`docs/lint-protocol.md`** — check 8 currently looks for
   `TODO(human-export)`; this can stay (it now reads as "no historical
   marker should survive") or be replaced with "every Mermaid diagram has
   a sibling PDF newer than its source `.md`." Plan: keep the marker check
   and add the freshness check as an *additional* check item rather than a
   replacement — backward-compatible.
4. **Three single-line text replacements:**
   `wiki/index.md:44`, `wiki/index.md:96`,
   `wiki/concepts/system-design.md:33`, `:103`,
   `wiki/concepts/system-design-protocols.md:29` —
   `Swimlanes.io` → `Mermaid` (or "diagrams" where the phrasing reads cleaner).
5. **`drafts/ch3_methodology.md`** — delete the three
   `TODO(human-export)` lines (45, 163, 214). The figure citations on the
   preceding paragraphs already use the `Figure N.M ([[diagrams/...]])`
   pattern that survives without the marker.
6. **`docs/superpowers/specs/2026-05-13-t17-scheduler-design.md`** §8 —
   single-line text edits ("five Swimlanes.io diagrams" → "five Mermaid
   diagrams"; "legend for the Swimlanes.io syntax" → "legend for the
   Mermaid syntax"). Spec is otherwise historical — do not rewrite.

## 6. Drafts cleanup

The conversion produces real PDFs on disk for every figure
Chapter 3 references, so the `TODO(human-export)` mechanism becomes dead
weight. Three follow-up edits in this same pass:

- `drafts/ch3_methodology.md` — strip the three `TODO(human-export)`
  lines (above).
- `drafts/review.html` — regenerated downstream of `ch3_methodology.md`;
  not edited by hand. If review.html is auto-generated, leave it to its
  next regenerator. If hand-maintained, strip the corresponding three
  lines.
- Greppable proof of completion:
  `grep -r "TODO(human-export)" drafts/ wiki/` returns zero hits after
  this pass.

## 7. Lint + verification

Before flipping to In Review:

1. `grep -r "swimlanes" wiki/ drafts/` returns hits **only** in
   `wiki/log.md` (historical entries) and in the prose-files we updated in
   §5 if they intentionally reference the migration in past tense.
2. `grep -rE "\`\`\`swimlanes" wiki/ drafts/ docs/` returns **zero** hits
   — no fenced Swimlanes blocks survive.
3. `grep -r "TODO(human-export)" drafts/ wiki/` returns zero hits (per §6).
4. For each `.md` containing a ```` ```mermaid ```` block under
   `wiki/diagrams/`, a sibling `.pdf` with a `mtime` ≥ the `.md`'s `mtime`
   exists on disk. Script:
   ```bash
   for f in $(find wiki/diagrams -name '*.md' -not -name 'index.md'); do
     pdf="${f%.md}.pdf"
     [ -f "$pdf" ] && [ "$pdf" -nt "$f" ] || echo "missing/stale: $pdf"
   done
   ```
5. Every wikilink `[[diagrams/...]]` still resolves to a real file
   on disk (no slug renamed during the migration — file names are
   stable).
6. Open the rendered PDFs side-by-side with screenshots of the original
   Swimlanes renders (if cached anywhere) for a visual diff. If not
   cached, the visual-equivalence check is best-effort by reading the new
   PDFs against the prose under "What this pins" on each page.

## 8. Commit + branch plan

Working branch: `task/diagrams-mermaid-migration` (not numbered; this is
meta-maintenance, not a T-task). Cut from the **starting branch's HEAD**
at pickup — whichever feature branch the agent inherits from the
session's worktree, typically the currently-active T-task branch.

Commit sequence on the migration branch:

1. `wiki: convert scheduler diagrams to Mermaid` — 5 `.md` + 5 `.pdf` under
   `wiki/diagrams/scheduler/`.
2. `wiki: convert runtime + protocol diagrams to Mermaid` — 5 `.md` + 5
   `.pdf` under `wiki/diagrams/{runtime,protocols}/`.
3. `wiki: update diagrams/index.md legend and export route for Mermaid`.
4. `meta: collapse draft-style.md figure pipeline to single Mermaid route`.
5. `wiki: text-edit Swimlanes references in concept + index pages`.
6. `task 36: drop TODO(human-export) markers from ch3_methodology.md` —
   touches only `drafts/`, scoped to the in-progress T36 work.
7. `wiki: log the Swimlanes → Mermaid migration` — single `wiki/log.md`
   entry summarising the pass.

After verification (§7) passes on the migration branch tip:

8. Push the migration branch to origin so it remains a reviewable
   standalone unit (the human may later open a PR from it to `main`
   independent of whatever else lands on the starting branch).
9. Switch back to the starting branch and merge with `git merge --no-ff
   task/diagrams-mermaid-migration` so the merge is a visible commit
   on the starting branch's history (no silent fast-forward). Conflicts
   are surfaced to the human, not auto-resolved.
10. Leave the starting-branch merge commit **local** (not pushed) so
    the human can inspect before publishing. Re-run §7 verification on
    the merged starting-branch HEAD to confirm the merge did not
    reintroduce a stale `TODO(human-export)` line or a missing PDF.

The kickoff prompt for a fresh session is in
[`2026-05-26-swimlanes-to-mermaid.kickoff.md`](2026-05-26-swimlanes-to-mermaid.kickoff.md).

## 9. Out of scope

- The `wiki/diagrams/concepts/bft-families-tree.md` Mermaid `flowchart` —
  already Mermaid, untouched.
- The `../thesis-tex/` LaTeX template — figure inclusion is T62 (W12);
  this plan only ensures the PDFs exist on disk under
  `wiki/diagrams/**/*.pdf`. T62 copies them into the template later.
- Any change to T-task numbering, status, or scope in `TASKS.md`. This
  plan deliberately does not flip statuses or add a new T-task.
- Historical entries in `wiki/log.md` and `docs/plans/2026-05-18-…md`.
  Per the wiki contract, history is not silently rewritten.

## 10. Risks

- **Mermaid sequence-diagram rendering of `Note over` with 6+ participants
  can wrap awkwardly.** Mitigation: the `constraints.md` diagram has 7
  lifelines, the widest in the set; render it first, before any prose
  edits, and use it as the worst-case visual check. If layout is
  unacceptable, split the diagram by section (one `rect` per `=:`
  divider becomes its own mini-diagram) — but this is a fallback, not
  the planned path.
- **`<b>…</b>` inside Mermaid message labels is renderer-dependent.** The
  `mmdc` CLI honours HTML in sequence-diagram labels; if a target renderer
  in the future does not, the bold semantics degrade silently to plain
  text. Acceptable: the emphasis is decorative, not load-bearing.
- **Visual diff against the original Swimlanes renders is best-effort.**
  No reference PDFs of the original Swimlanes diagrams are on disk (none
  were ever exported because of the human-export bottleneck this plan
  removes). The check is "does the new PDF say what the prose says it
  should." Documented as a deliberate gap.

## 11. Done definition

- Zero ```` ```swimlanes ```` blocks survive under `wiki/`.
- Ten new `.pdf` files exist under `wiki/diagrams/{scheduler,runtime,
  protocols}/` with mtimes ≥ their source `.md`.
- Zero `TODO(human-export)` markers survive under `drafts/` or `wiki/`.
- `docs/draft-style.md` and `wiki/diagrams/index.md` describe a single,
  Mermaid-only figure pipeline.
- `wiki/log.md` carries one new entry dated the day of the migration.
- All wikilinks `[[diagrams/...]]` resolve.
