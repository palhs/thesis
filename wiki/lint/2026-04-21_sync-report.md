---
type: lint
scope: sync-completeness
date: 2026-04-21
task: S9
---

# Sync completeness report — 2026-04-21

Narrow sync-completeness pass per task S9. For each `[x]` Completed task in
Weeks 1–2 (T1–T10) and the Week 0 sync tasks (S0–S8), verify:

1. The artifact declared in `TASKS.md` exists on disk.
2. The artifact is catalogued in `wiki/index.md`.

Broader wiki-health checks (orphans, contradictions, dead wikilinks,
`TODO(cite)` inventory) are out of scope; those belong to the L-W2 lint
pass. This report is findings-only — no edits are proposed or applied, per
the Linter role in `docs/roles.md`.

## Method

- Enumerated `wiki/**/*.md` via glob: 30 files total — 4 algorithms, 12
  concepts, 12 sources, plus `index.md` and `log.md`.
- Cross-checked disk contents against (a) T1–T10 / S0–S8 rows in `TASKS.md`
  and (b) the catalog in `wiki/index.md`.
- For T6 (whose outcome is "4 summaries" without a single path), confirmed
  that each `wiki/algorithms/*.md` page exposes mechanism / safety /
  weaknesses structure by grepping `^## ` anchors.

## Findings — High

### H1. T1 artifact missing on disk and absent from index

- **Task row (TASKS.md:48–49):**

  > `[x]` **T1** `H` Researcher — Read introductory materials on blockchain
  > & L1 consensus
  > _Artifact:_ `wiki/concepts/consensus-overview.md`

- **On-disk status:** `wiki/concepts/consensus-overview.md` does **not**
  exist. `wiki/concepts/` contains 12 pages; this is not one of them.
- **Index status:** `wiki/index.md` has no `[[concepts/consensus-overview]]`
  entry. Nothing else in `wiki/` appears to substitute for it (the eight
  S0-generated concept pages collectively cover foundation material, but
  none of them carries the T1-scoped "blockchain structure, block creation,
  why consensus is needed" introductory framing).
- **Severity:** High. T1 is marked `[x]` Completed, but its declared
  artifact is absent from the tree — this is the stale-status condition
  defined in `docs/lint-protocol.md` §4, and simultaneously index drift in
  the declared→disk direction (§5).
- **Suggested triage (for human, not applied):** either (i) downgrade T1
  to `[ ]` Not Started or `[~]` In Progress and schedule authorship of
  `wiki/concepts/consensus-overview.md`, or (ii) if the T1 material was
  folded into the S0 foundation pages by design, amend the T1 row to point
  at the correct artifact(s) and append a note to `wiki/log.md`
  documenting the remap.

## Findings — Medium

None inside the sync-completeness scope. Two prior Medium-severity issues
are already logged in `TASKS.md` under `## Backlog` (algorithm-page local
`[1]–[3]` footnote numbering; five missing `wiki/sources/` pages for
bibliography entries [8], [10], [15]–[17]); they are citation-policy and
bibliography-coverage drifts, not sync-completeness drifts, and are out of
scope here.

## Findings — Low

### L1. T6 has no single declared artifact; outcome is served collectively

- **Task row (TASKS.md:58–59):**

  > `[x]` **T6** `H` Researcher — Summarize each algorithm in 1–2 pages
  > _Outcome:_ 4 summaries covering mechanism, guarantees, assumptions,
  > weaknesses

- T6 is the only `[x]` T-task in W1–W2 whose row lacks an `_Artifact:_`
  field. Its outcome is satisfied collectively by
  `wiki/algorithms/{pbft,pos,avalanche,dag-based}.md`, each of which exposes
  Mechanism / Safety / Assumptions / Weaknesses-to-foreground sections
  (confirmed by `^## ` grep: every algorithm page has a `Weaknesses to
  foreground` heading; `pbft.md` and `dag-based.md` also carry a `Safety
  argument`). This is not a drift — it is a convention gap. For future
  grep-ability of T→artifact traceability, consider appending `_Artifact:_
  wiki/algorithms/{pbft,pos,avalanche,dag-based}.md` to the T6 row.

### L2. Dead forward wikilinks to deferred pages (expected, not drift)

- `wiki/log.md` flags several deliberate-dead wikilinks awaiting future
  tasks: `concepts/adversary-model` (T18), `concepts/experiment-matrix`
  (T19), `concepts/output-format` (T40), and `concepts/message-types` (T16,
  referenced inside `wiki/sources/2026-04-21_yin-hotstuff-2019.md` per the
  S6 log entry).
- These are not sync-completeness failures — they are planned forward
  references. Flagged here for pickup by the L-W2 dead-link scan, where
  they should either be verified as still-pending or reclassified if their
  target tasks slip.

## Confirmed coverage — summary

All Week 0 sync tasks (S0–S8) and all `[x]` T-tasks in Weeks 1–2 except T1
pass both existence and index checks:

| Task   | Artifact(s)                                                                  | On disk | In index |
| ------ | ---------------------------------------------------------------------------- | :-----: | :------: |
| S0     | `concepts/{byzantine-generals,flp-impossibility,cap-theorem,consensus-properties,synchrony-models,fault-model,quorum-arithmetic,consensus-families}.md` (8) | yes     | yes      |
| S1 / T2 | `algorithms/pbft.md`                                                        | yes     | yes      |
| S2 / T3 | `algorithms/pos.md`                                                         | yes     | yes      |
| S3 / T4 | `algorithms/avalanche.md`                                                   | yes     | yes      |
| S4 / T5 | `algorithms/dag-based.md`                                                   | yes     | yes      |
| S5 / T7, T10 | `concepts/problem-statement.md`, `concepts/research-questions.md`      | yes     | yes      |
| S6 / T8 | `concepts/annotated-bibliography.md` + 12 `sources/2026-04-21_*.md` pages   | yes     | yes      |
| S7 / T9 | `concepts/evaluation-metrics.md`                                            | yes     | yes      |
| S8     | `index.md`, `log.md`                                                         | yes     | n/a      |
| T1     | `concepts/consensus-overview.md`                                             | **no**  | **no**   |
| T6     | (collective: 4 algorithm pages — see L1)                                     | yes     | yes      |

Index-vs-disk reverse check: all 28 page entries in `wiki/index.md`
(Algorithms 4 + Concepts 12 + Sources 12) resolve to on-disk files. No
index-listed-but-missing drift.

## Out of scope (for L-W2 or later)

- Orphan scan (pages with zero inbound wikilinks).
- Missing-page scan (concepts referenced in ≥3 pages but lacking their own
  page).
- Contradiction scan across algorithm pages vs newer source ingests.
- `TODO(cite)` inventory in wiki and drafts (drafts do not yet exist).
- Dead-wikilink sweep (partial note in L2; full pass belongs at L-W2).
- Backlog items already captured in `TASKS.md`.

---

_Linter report per `docs/lint-protocol.md`. No files outside this report
were touched. Human triage decides which findings become tasks._
