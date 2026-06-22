# Lint protocol

Run at KPI checkpoints (W2, W4, W8, W10, W12) or on human request. The
Linter produces a report, not edits. Edits happen only after you triage
the report.

## Checks

1. **Orphans** — pages with zero inbound links.
2. **Missing pages** — entities/concepts referenced in 3+ pages but lacking
   their own page.
3. **Contradictions** — claims newer sources undermine without a
   `## Revisions` note.
4. **Stale status** — tasks marked Completed whose artifacts don't exist
   on disk.
5. **Index drift** — pages not listed in `wiki/index.md`, or listed but
   missing from disk.
6. **Citation gaps** — `TODO(cite)` markers in `drafts/`.
7. **Dead links** — wikilinks pointing to non-existent pages.
8. **Figure-export gaps** — the thesis has two figure families (Mermaid
   *diagram figures* under `wiki/diagrams/`, matplotlib *data-plot
   figures* under `results/**/plots/`; see `docs/draft-style.md`
   § Figures). Four checks:
   - `TODO(human-export)` markers anywhere in `drafts/` or `wiki/`
     (legacy from the retired Swimlanes pipeline; the 2026-05-26
     Mermaid migration cleared them and no new ones should appear).
   - `drafts/` figure references whose
     `wiki/diagrams/<group>/<slug>.pdf` sibling is missing on disk.
   - For every `wiki/diagrams/**/*.md` carrying a ```` ```mermaid ````
     block, a sibling `.pdf` exists with mtime ≥ the `.md`'s mtime
     (PDF is stale if older than its source).
   - **Data plots:** for every `drafts/` data-plot figure reference —
     resolved via the experiment page named in its
     `Figure N.M ([[experiments/<page>]])` citation, which maps figure
     number → plot slug — the tracked `results/**/plots/<slug>.pdf`
     exists on disk. A data-plot PDF is stale if older than the results
     CSV it was rendered from (the CSV is the provenance anchor); flag,
     but treat a CSV-newer-than-PDF as Low unless the CSV's data
     actually changed.
9. **Narrative-ledger drift** — the cross-chapter ledgers in
   `docs/draft-narrative.md` (§1 spine sentence, §2 RQ-closure ledger, §3
   forward-reference ledger, §10 per-chapter cheat-sheet) are derived from scope
   decisions recorded in `TASKS.md` and the RQ wording in
   `wiki/concepts/research-questions.md`. Cross-check each row against its source
   and flag:
   - an RQ whose `TASKS.md`/on-disk-draft status disagrees with its §2 ledger row
     (a chapter present on disk but the RQ still "open", or vice versa);
   - a §3 forward reference whose owning task has been descoped, retired, or
     completed without the ledger discharging or explicitly re-carrying it (e.g.
     an enhancement "owed by Chapter X" whose task carries a `DESCOPED` note in
     `TASKS.md`);
   - a §10 cheat-sheet entry naming a deliverable that a `TASKS.md` scope note has
     moved, dropped, or reassigned.
   Report each divergence with both the ledger line and the conflicting
   `TASKS.md` line. This guards the `docs/draft-narrative.md` §11 maintenance
   contract.

## Output

Single file: `wiki/lint/YYYY-MM-DD_report.md`, grouped by severity
(High / Medium / Low). Include file paths and specific findings. No silent
fixes.
