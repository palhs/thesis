# CLAUDE.md

Single-source workspace for a Layer-1 consensus evaluation thesis. Holds raw
sources, an LLM-maintained wiki, simulator code, experiment results, and
thesis drafts. Agents operate one task at a time; humans review every merge.
Always use 'auggie' mcp to search and index codebase.

## Repo map

- `raw/` — source papers, PDFs. Immutable. Agents read, never modify.
- `wiki/` — LLM-authored knowledge base.
  - `wiki/index.md` — catalog of every wiki page. First read on every task.
  - `wiki/log.md` — chronological record of ingests/work/lint.
  - `wiki/algorithms/`, `wiki/concepts/`, `wiki/sources/`, `wiki/experiments/`, `wiki/lint/`
- `src/` — simulator code.
- `results/` — CSVs, plots.
- `drafts/` — thesis chapters in markdown. Ported into LaTeX in
  `../thesis-tex/` (sibling Overleaf clone; outside this repo).
- `TASKS.md` — the work queue. Source of truth for status.
- `docs/` — operating rules (imported below).

## Operating rules

@docs/workflow.md
@docs/wiki-spec.md
@docs/retrieval.md
@docs/roles.md
@docs/chat-style.md

Role-specific docs are not loaded here. The matching role section in
`docs/roles.md` names the style/protocol doc to read on pickup:

- Writer → `docs/draft-style.md`
- Linter → `docs/lint-protocol.md`

## Orientation

12-week thesis comparing L1 consensus algorithms via simulation. Pull one
task from TASKS.md per session. Each task has a role: Researcher, Engineer,
Writer, Linter. Every task must leave durable knowledge in `wiki/`, not just
artifacts in `src/` or `drafts/`. Humans review all merges.

The wiki is how you retrieve knowledge. First read on every task is
`wiki/index.md` (see `docs/retrieval.md` for the full pattern).

## Hard rules

- Do not modify `raw/`.
- Do not mark tasks Completed — human only.
- Do not guess scope. Ask if ambiguous.
- Do not invent citations. Use `TODO(cite)`.
- One task per session. No opportunistic edits.
- Do not sync to Google Sheet. `TASKS.md` is authoritative.
