# Retrieval

The wiki is the knowledge base. This file explains how agents find and use
what's in it.

## Mental model

At thesis scale (~100–200 pages by Week 12), the wiki fits in context. No
embeddings, no vector DB, no chunking. Retrieval is three moves:

1. **`wiki/index.md` is the search engine.** A categorized catalog with
   one-line summaries. Every task starts by reading it.
2. **Wikilinks are the graph.** Once on a relevant page, follow
   `[[algorithms/pbft]]` style links to gather related context.
3. **Pages are small and focused** (<300 lines), so pulling a handful into
   context is cheap.

## The index-first rule

Your first read on every task is `wiki/index.md`. It tells you what exists.
Without that scan, you risk duplicating pages, missing prior work, or
writing prose that contradicts established wiki claims.

## Per-role retrieval patterns

### Researcher (ingesting a new source)
1. Read `index.md` to see what already exists in the topic area.
2. Read those existing pages — avoid duplicating, find where new facts should land.
3. Write the new source page; update affected algorithm/concept pages.
4. Scan for pages that referenced this topic weakly or as TODO — strengthen them.
5. Update `index.md`; append to `log.md`.

### Engineer (implementing code)
1. Read `index.md` to find the algorithm/concept pages the task depends on.
2. Read them in full.
3. Follow wikilinks outward — if `pbft.md` links to `[[concepts/message-types]]`, read that too.
4. If the spec is incomplete or ambiguous, stop and ask. Do not guess.
5. Implement; write an experiment page back-linking to the concept pages used.

### Writer (drafting a chapter)
1. Read `index.md`; identify which wiki pages correspond to chapter sections.
2. Read those pages fully.
3. Follow wikilinks to gather supporting concepts.
4. Draft prose with `[[wiki/...]]` citations inline.
5. Missing something? Flag a Researcher task in Backlog instead of inventing.

### Linter
1. Walk the tree recursively.
2. Parse wikilinks to build the graph.
3. Cross-check against `index.md` for drift.
4. Compare `TASKS.md` Completed entries against on-disk artifacts.

## When to revisit

This scheme works up to ~300 wiki pages. Past that, `index.md` stops fitting
comfortably and you'll want proper search (grep for small cases, `qmd` or
similar for bigger). Signal to upgrade: `index.md` crosses ~500 lines, or
the agent starts missing relevant pages because it scanned too fast.
