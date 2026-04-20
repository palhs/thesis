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

## Output

Single file: `wiki/lint/YYYY-MM-DD_report.md`, grouped by severity
(High / Medium / Low). Include file paths and specific findings. No silent
fixes.
