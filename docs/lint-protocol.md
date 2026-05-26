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
8. **Figure-export gaps** — three checks:
   - `TODO(human-export)` markers anywhere in `drafts/` or `wiki/`
     (legacy from the retired Swimlanes pipeline; the 2026-05-26
     Mermaid migration cleared them and no new ones should appear).
   - `drafts/` figure references whose
     `wiki/diagrams/<group>/<slug>.pdf` sibling is missing on disk.
   - For every `wiki/diagrams/**/*.md` carrying a ```` ```mermaid ````
     block, a sibling `.pdf` exists with mtime ≥ the `.md`'s mtime
     (PDF is stale if older than its source).

## Output

Single file: `wiki/lint/YYYY-MM-DD_report.md`, grouped by severity
(High / Medium / Low). Include file paths and specific findings. No silent
fixes.
