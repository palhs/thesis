# Wiki specification

## File naming

- Source ingests: `wiki/sources/YYYY-MM-DD_<slug>.md`
- Algorithms: `wiki/algorithms/<slug>.md` (e.g., `pbft.md`, `narwhal-tusk.md`)
- Concepts: `wiki/concepts/<slug>.md`
- Experiments: `wiki/experiments/YYYY-MM-DD_<slug>.md`
- Lint reports: `wiki/lint/YYYY-MM-DD_report.md`
- Chapter drafts: `drafts/ch<N>_<slug>.md`

Lowercase kebab-case slugs. No spaces.

## Page size

Keep wiki pages under ~300 lines. If a page grows past that, split it along
natural boundaries (e.g., `pbft.md` → `pbft.md` + `pbft-view-change.md`) and
update inbound wikilinks.

## Cross-references

Obsidian-style wikilinks: `[[algorithms/pbft]]` or
`[[concepts/flp#impossibility]]`. These are both citation syntax AND the
retrieval graph — see `docs/retrieval.md`.

## Index structure

`wiki/index.md` is the retrieval entry point. Rules:

- Organized by category: Algorithms, Concepts, Sources, Experiments, Drafts.
- One line per page: `- [[path/to/page]] — one-line summary`.
- Updated on every task that creates a page.
- Keep under ~500 lines total. If it grows past that, revisit — split by
  category into sub-indexes, or adopt proper search (grep, `qmd`, etc.).

## Mandatory updates per task

- Every new wiki page is added to `wiki/index.md` under its category.
- Every task appends an entry to `wiki/log.md`.

## Revisions rule

When new data contradicts an existing claim, do NOT silently overwrite. Add
a `## Revisions` section to the page noting the contradiction and the date.

## Source page requirements

Each `wiki/sources/` page must include:
- Full citation
- 3–5 key takeaways
- Links to affected wiki pages

## Log format

Append to `wiki/log.md`. One entry per task. Greppable prefix:

```
## [YYYY-MM-DD] <type> | task <N> — <short title>
- role: <Researcher|Engineer|Writer|Linter>
- touched: <comma-separated file list>
- notes: <1–3 sentences on what changed and why>
```

`<type>` ∈ { `ingest`, `code`, `experiment`, `draft`, `lint`, `sync` }.

Example grep: `grep "^## \[" wiki/log.md | tail -10` shows the last 10 entries.

## Citations in drafts

Inside `drafts/ch*.md`, claims cite wiki pages, not raw sources directly:

```
PBFT tolerates up to f Byzantine faults with 3f+1 replicas
[[wiki/algorithms/pbft#fault-model]].
```

If a claim relies on a raw source not yet in the wiki, ingest that source
into `wiki/sources/` first.

## What NOT to do

- Do not write thesis prose into wiki pages. Wiki organizes and synthesizes;
  `drafts/` holds chapter text.
- Do not invent citations. Use `TODO(cite)`.
