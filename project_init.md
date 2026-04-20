# thesis-consensus — Project Init

A single-repo workspace for a 12-week Layer-1 consensus evaluation thesis.
Raw sources, an LLM-maintained wiki, simulator code, experiment results, and
thesis drafts live together. Agents operate one task at a time; you review
every merge.

## Core idea

- **One git repo.** The wiki is the brain. `TASKS.md` is the queue.
- **Agent runs one task** per session under a role (Researcher, Engineer,
  Writer, Linter). Every task must leave durable knowledge in `wiki/`, not
  just artifacts in `src/` or `drafts/`.
- **The wiki is how agents retrieve.** `wiki/index.md` is the catalog;
  wikilinks form the graph. No embeddings, no vector DB — the whole wiki
  fits in context at thesis scale.
- **You review the diff** before merge. You are the bottleneck and the gate.
- **Claude Code auto-loads `CLAUDE.md`** at session start; `CLAUDE.md` uses
  `@docs/*.md` imports to pull in the operating rules.

## Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Pick task   │ → │ Agent works  │ → │ Commit + PR  │ → │ Human review │
│ from TASKS   │   │ reads index  │   │ on branch    │   │ diff + merge │
└──────────────┘   │ reads wiki   │   └──────────────┘   └──────┬───────┘
                   │ files output │                             │
                   │ updates log  │                             ↓
                   └──────────────┘                     TASKS.md → Completed
```

Five layers of the repo, from input to output:

| Layer | Owner | Purpose |
|---|---|---|
| `raw/` | human | immutable source material (PDFs, articles) |
| `wiki/` | agent | knowledge base — summaries, concepts, algorithms, experiments |
| `src/` | agent | simulator code |
| `results/` | agent | CSVs and plots from experiment runs |
| `drafts/` | agent | thesis chapters in markdown (→ LaTeX at the end) |

And three control files:

- `CLAUDE.md` — lean root; imports the rule files.
- `docs/*.md` — workflow, wiki spec, retrieval, role prompts, lint protocol.
- `TASKS.md` — the work queue, the only place task status lives.

## How retrieval works (the wiki-centric part)

This is the mechanic that makes the whole scheme work. It's worth saying
explicitly:

At thesis scale (~100–200 wiki pages by Week 12), the wiki fits in context.
Agents retrieve in three moves:

1. Read `wiki/index.md` — a categorized catalog with one-line summaries per
   page. This is the search engine.
2. Open the pages the catalog points to. Pages are small (<300 lines each).
3. Follow wikilinks (`[[algorithms/pbft]]`, `[[concepts/flp#impossibility]]`)
   out to related pages — the wiki is a graph, not a pile of files.

No embeddings, no vector DB, no chunking. You replace RAG with a
well-maintained index and a handful of page reads.

The rule that makes this stick: **every task starts by reading
`wiki/index.md`.** The full retrieval patterns per role are in
`docs/retrieval.md`.

---

## Bootstrap

Run once in a new empty folder:

```bash
mkdir thesis-consensus && cd thesis-consensus
git init

# top-level folders
mkdir -p raw src results drafts docs
mkdir -p wiki/{algorithms,concepts,sources,experiments,lint}

# seed wiki root files (agents maintain these)
cat > wiki/index.md << 'EOF'
# Wiki index

> Auto-maintained catalog of all wiki pages. One line per page.
> Format: `- [[path/to/page]] — one-line summary`
> Keep under ~500 lines. Revisit retrieval strategy if it grows past that.

## Algorithms
## Concepts
## Sources
## Experiments
## Drafts
EOF

cat > wiki/log.md << 'EOF'
# Wiki log

> Append-only chronological record. Format:
> ## [YYYY-MM-DD] <type> | task <N> — <title>
EOF

# .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.venv/
.env
results/**/*.csv
results/**/*.png
!results/**/.gitkeep
.DS_Store
EOF

# keep empty dirs in git
touch results/.gitkeep src/.gitkeep drafts/.gitkeep raw/.gitkeep wiki/lint/.gitkeep
```

Then create the seven files listed below (or paste this whole doc into
Claude Code and say "create these files at the paths specified"). After
that:

```bash
git add .
git commit -m "meta: scaffold thesis-consensus repo"
git checkout -b task/S1-import-pbft-notes   # first real work: W0 sync
```

---

## File 1 — `CLAUDE.md` (repo root)

````markdown
# CLAUDE.md

Single-source workspace for a Layer-1 consensus evaluation thesis. Holds raw
sources, an LLM-maintained wiki, simulator code, experiment results, and
thesis drafts. Agents operate one task at a time; humans review every merge.

## Repo map

- `raw/` — source papers, PDFs. Immutable. Agents read, never modify.
- `wiki/` — LLM-authored knowledge base.
  - `wiki/index.md` — catalog of every wiki page. First read on every task.
  - `wiki/log.md` — chronological record of ingests/work/lint.
  - `wiki/algorithms/`, `wiki/concepts/`, `wiki/sources/`, `wiki/experiments/`, `wiki/lint/`
- `src/` — simulator code.
- `results/` — CSVs, plots.
- `drafts/` — thesis chapters in markdown. Converted to LaTeX at the end.
- `TASKS.md` — the work queue. Source of truth for status.
- `docs/` — operating rules (imported below).

## Operating rules

@docs/workflow.md
@docs/wiki-spec.md
@docs/retrieval.md
@docs/roles.md
@docs/lint-protocol.md

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
````

---

## File 2 — `docs/workflow.md`

````markdown
# Workflow

## Task lifecycle

Status in `TASKS.md`:

`Not Started` → `In Progress` → `In Review` → `Completed`

`Blocked` is a parallel state set with a short reason when stuck.

- Agent flips to **In Progress** on pickup.
- Agent flips to **In Review** on push.
- Human flips to **Completed** on merge. Agents never self-complete.

## Per-task workflow

1. Read the task entry in `TASKS.md`.
2. Read `wiki/index.md` to orient on what already exists.
3. Flip status to In Progress. Commit alone: `task <N>: start`.
4. Do the work. Stay inside the task's scope.
5. Create/update wiki pages. Update `wiki/index.md` if new pages were added.
6. Append entry to `wiki/log.md` (format in `docs/wiki-spec.md`).
7. Flip status to In Review. Commit: `task <N>: <short description>`.
8. Push branch. Summarize for the human: files touched, wiki pages
   added/updated, decisions made, open questions.

## Branch convention

One branch per task: `task/T<N>-<slug>`. Example: `task/T14-node-model`.

## Commit convention

- `task <N>: <imperative>` — task work.
- `wiki: <description>` — wiki-only maintenance.
- `meta: <description>` — changes to CLAUDE.md, TASKS.md structure, scaffolding.

One logical change per commit.

## Scope discipline

- One task per session.
- Do not edit files outside the task's scope.
- Notice an unrelated issue? Append to `## Backlog` in `TASKS.md`; do not fix.
- If a task is ambiguous, stop and ask. Do not guess.

## Evolution

When a convention here conflicts with reality, update this file as part of
the task and flag the change in the commit message.
````

---

## File 3 — `docs/wiki-spec.md`

````markdown
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
````

---

## File 4 — `docs/retrieval.md`

````markdown
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
````

---

## File 5 — `docs/roles.md`

````markdown
# Role prompts

Paste the matching prompt at the start of a session before handing over a
task. All prompts assume the agent has already read `CLAUDE.md` and the
target task in `TASKS.md`.

## Researcher

You are acting as **Researcher** on task <ID>. Your job is to extract
durable knowledge from sources and file it in the wiki. Prioritize:
accuracy over fluency, mechanism over narrative, weaknesses over marketing
claims. Write for a reader (future-me) who will need to rederive the
algorithm under exam pressure. Every claim needs a source. When sources
conflict, record both and note which you trust and why. Do not draft thesis
prose — that is the Writer's job. Follow the Researcher retrieval pattern
in `docs/retrieval.md`. Output: wiki pages + `index.md` update + `log.md`
entry.

## Engineer

You are acting as **Engineer** on task <ID>. Your job is to produce code or
experimental results that another person could reproduce from the wiki
alone. Prioritize: correctness, reproducibility, minimal dependencies.
Before implementing, follow the Engineer retrieval pattern in
`docs/retrieval.md` — read the relevant `wiki/concepts/` and
`wiki/algorithms/` pages and confirm the spec matches. If it doesn't, stop
and ask. Every experiment run gets a
`wiki/experiments/<date>_<slug>.md` page with: config used, seeds, commit
hash, commands to re-run, raw result location, one-paragraph observation.
Code goes in `src/`, artifacts in `results/`, understanding in `wiki/`.
Do not run new experiments to "see what happens" without a task — add
those to Backlog instead.

## Writer

You are acting as **Writer** on task <ID>. Your job is to synthesize the
wiki into thesis prose. Prioritize: an argument the reader can follow,
claims backed by wiki citations, honest about limitations. Follow the
Writer retrieval pattern in `docs/retrieval.md`. Do not introduce claims
that aren't in the wiki — if the wiki is missing something you need, stop
and flag it as a Researcher task in Backlog instead of inventing. Use
`[[wiki/...]]` citations. Mark any missing external citation
`TODO(cite)`. Register: academic, neutral, concrete. No hype.

## Linter

You are acting as **Linter**. Your job is to produce a report, not edits.
Walk the wiki with the checks in `docs/lint-protocol.md`. Output one
markdown file to `wiki/lint/<date>_report.md`, grouped by severity. Do not
touch any other file. Do not assume what should be fixed — surface
findings and let the human decide.
````

---

## File 6 — `docs/lint-protocol.md`

````markdown
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
````

---

## File 7 — `TASKS.md`

````markdown
# TASKS.md — thesis-consensus work queue

Source of truth for all work. Agents pick one task, flip status, do the
work, push for review. Humans mark Completed on merge.

## Dashboard

- Total tasks: 66 · Sync tasks: 9 · Lint checkpoints: 5
- Completed: 10 · In Review: 0 · In Progress: 0 · Not Started: 56 · Blocked: 0

## Legend

Status: `[ ]` Not Started · `[~]` In Progress · `[?]` In Review · `[x]` Completed · `[!]` Blocked
Priority: `H` High · `M` Medium · `L` Low

---

## Week 0 — Sync existing work into repo

Bring completed Week 1–2 work into the repo structure. Each sync task pulls
one resource into the appropriate wiki page. Not counted in the 66.

- `[ ]` **S1** `H` Researcher — Import PBFT deep-dive notes
  _Source:_ <path> · _Target:_ `wiki/algorithms/pbft.md` · _Verify:_ T2 outcomes covered
- `[ ]` **S2** `H` Researcher — Import PoS finality deep-dive notes
  _Source:_ <path> · _Target:_ `wiki/algorithms/pos.md` · _Verify:_ T3 outcomes covered
- `[ ]` **S3** `H` Researcher — Import Avalanche deep-dive notes
  _Source:_ <path> · _Target:_ `wiki/algorithms/avalanche.md` · _Verify:_ T4 outcomes covered
- `[ ]` **S4** `H` Researcher — Import DAG-based deep-dive notes
  _Source:_ <path> · _Target:_ `wiki/algorithms/dag-based.md` · _Verify:_ T5 outcomes covered
- `[ ]` **S5** `H` Researcher — Import problem statement + research questions
  _Source:_ <path> · _Target:_ `wiki/concepts/problem-statement.md`, `wiki/concepts/research-questions.md` · _Verify:_ T7, T10
- `[ ]` **S6** `H` Researcher — Import annotated bibliography + 8–12 source pages
  _Source:_ <path + raw PDFs> · _Target:_ `wiki/sources/*.md`, `wiki/concepts/annotated-bibliography.md` · _Verify:_ T8
- `[ ]` **S7** `H` Researcher — Import evaluation metrics notes
  _Source:_ <path> · _Target:_ `wiki/concepts/evaluation-metrics.md` · _Verify:_ T9
- `[ ]` **S8** `M` Researcher — Generate initial `wiki/index.md` and `wiki/log.md`
  _Outcome:_ Index reflects S1–S7 pages; log has one retroactive entry per import · _Artifact:_ `wiki/index.md`, `wiki/log.md`
- `[ ]` **S9** `M` Linter — Sync completeness check
  _Outcome:_ Confirm every W1–W2 completed task (T1–T10) has a corresponding wiki artifact · _Artifact:_ `wiki/lint/<date>_sync-report.md`

---

## Week 1 — Foundations (reading)

- `[x]` **T1** `H` Researcher — Read introductory materials on blockchain & L1 consensus
  _Outcome:_ Notes on blockchain structure, block creation, why consensus is needed · _Artifact:_ `wiki/concepts/consensus-overview.md`
- `[x]` **T2** `H` Researcher — Study PBFT-style consensus in depth
  _Outcome:_ Notes on PBFT phases, 3f+1, view change · _Artifact:_ `wiki/algorithms/pbft.md`
- `[x]` **T3** `H` Researcher — Study simplified PoS voting/finality
  _Outcome:_ Notes on validator voting, attestation, supermajority finality, slashing · _Artifact:_ `wiki/algorithms/pos.md`
- `[x]` **T4** `M` Researcher — Study Avalanche-style probabilistic consensus
  _Outcome:_ Notes on Snowball/Snowflake, subsampled voting, convergence · _Artifact:_ `wiki/algorithms/avalanche.md`
- `[x]` **T5** `M` Researcher — Study DAG-based consensus (Narwhal/Tusk, Mysticeti)
  _Outcome:_ Notes on DAG construction, parallel proposals, ordering · _Artifact:_ `wiki/algorithms/dag-based.md`
- `[x]` **T6** `H` Researcher — Summarize each algorithm in 1–2 pages
  _Outcome:_ 4 summaries covering mechanism, guarantees, assumptions, weaknesses
- `[x]` **T7** `H` Researcher — Draft initial problem statement
  _Outcome:_ 1-page statement identifying the gap · _Artifact:_ `wiki/concepts/problem-statement.md`

## Week 2 — Lit review & framing

- `[x]` **T8** `H` Researcher — Review 8–12 papers/surveys on consensus performance & security
  _Outcome:_ Annotated bibliography with contribution/method/limitations · _Artifact:_ `wiki/sources/`, `wiki/concepts/annotated-bibliography.md`
- `[x]` **T9** `H` Researcher — Identify common evaluation metrics from literature
  _Outcome:_ Metric list: latency, throughput, communication overhead, fault tolerance, finality time, fork rate · _Artifact:_ `wiki/concepts/evaluation-metrics.md`
- `[x]` **T10** `H` Researcher — Define research questions and thesis objectives
  _Outcome:_ RQ1–RQ5 finalized, measurable scope · _Artifact:_ `wiki/concepts/research-questions.md`
- `[ ]` **T11** `H` Writer — Write Chapter 1 draft (Introduction)
  _Outcome:_ 3–5 pages: background, motivation, problem statement, objectives, RQs · _Artifact:_ `drafts/ch1_intro.md`
- `[ ]` **T12** `H` Writer — Write initial Chapter 2 draft (Literature Review)
  _Outcome:_ 3–5 pages on blockchain basics, consensus families, existing evaluations · _Artifact:_ `drafts/ch2_litreview.md`
- `[ ]` **T13** `H` Researcher — Finalize thesis title and scope
  _Outcome:_ Confirmed title, included/excluded scope, supervisor sign-off · _Artifact:_ update `wiki/concepts/problem-statement.md` · _KPI checkpoint_
- `[ ]` **L-W2** `M` Linter — Wiki lint pass (end of Week 2)
  _Outcome:_ Triaged report of orphans, missing pages, contradictions, index drift · _Artifact:_ `wiki/lint/<date>_report.md`

## Week 3 — System modeling

- `[ ]` **T14** `H` Engineer — Define node model (validator states, roles)
  _Outcome:_ Node class design; states (idle, proposing, voting, committed); role assignment · _Artifact:_ `wiki/concepts/node-model.md`
- `[ ]` **T15** `H` Engineer — Define network model (delays, packet loss)
  _Outcome:_ Uniform/normal/exponential delay, configurable drop rate, jitter params · _Artifact:_ `wiki/concepts/network-model.md`
- `[ ]` **T16** `H` Engineer — Define message types and protocol rounds
  _Outcome:_ Catalog: Propose, Vote, Commit, Finalize, Query with fields/sizes · _Artifact:_ `wiki/concepts/message-types.md`
- `[ ]` **T17** `H` Engineer — Define event-driven simulation logic
  _Outcome:_ Event scheduler design: queue, time advancement, callback registration · _Artifact:_ `wiki/concepts/simulation-design.md`
- `[ ]` **T18** `M` Engineer — Define adversarial behavior categories
  _Outcome:_ 4 adversary types: delayer, equivocator, non-participant, leader disruptor · _Artifact:_ `wiki/concepts/adversary-model.md`
- `[ ]` **T19** `M` Engineer — Design experiment parameter space
  _Outcome:_ Matrix: validator counts, delay ranges, adversary fractions, timeouts, seeds · _Artifact:_ `wiki/concepts/experiment-matrix.md`
- `[ ]` **T20** `H` Engineer — Produce system design diagram + pseudocode
  _Outcome:_ Architecture diagram + pseudocode for each protocol main loop · _Artifact:_ `wiki/concepts/system-design.md`

## Week 4 — Simulator skeleton

- `[ ]` **T21** `H` Engineer — Implement event scheduler (SimPy or custom)
  _Outcome:_ Working scheduler passing 3+ unit tests · _Artifact:_ `src/scheduler/` + `wiki/experiments/<date>_scheduler-baseline.md`
- `[ ]` **T22** `H` Engineer — Implement node objects with state management
  _Outcome:_ Node class with transitions, message handling, honest/adversarial hooks · _Artifact:_ `src/nodes/`
- `[ ]` **T23** `H` Engineer — Implement message passing with configurable delay
  _Outcome:_ Delivery system with delay injection and drop simulation · _Artifact:_ `src/network/`
- `[ ]` **T24** `M` Engineer — Add logging for consensus events
  _Outcome:_ Structured logs (timestamp, node_id, event_type, round, msg_id) exportable to CSV · _Artifact:_ `src/logging/`
- `[ ]` **T25** `H` Engineer — Test basic message exchange among nodes
  _Outcome:_ Integration test with 4 nodes; delay distribution matches config · _Artifact:_ `src/tests/` + experiment page
- `[ ]` **T26** `H` Engineer — Set up repo scaffolding: /src, /tests, /configs, /results
  _Outcome:_ Clean structure, README, .gitignore, initial commit · _Artifact:_ repo root
- `[ ]` **T27** `M` Engineer — Set up reproducibility: seed control, YAML configs
  _Outcome:_ YAML loader, seed injection; same seed → same output · _Artifact:_ `src/config/` + `wiki/concepts/reproducibility.md`
- `[ ]` **L-W4** `M` Linter — Wiki lint pass (end of Week 4)
  _Outcome:_ Report on wiki health before implementation phase · _Artifact:_ `wiki/lint/<date>_report.md`

## Week 5 — PBFT implementation

- `[ ]` **T28** `H` Engineer — Implement simplified PBFT proposal logic
  _Outcome:_ Leader proposes, broadcasts pre-prepare, nodes validate · _Artifact:_ `src/pbft/`
- `[ ]` **T29** `H` Engineer — Implement PBFT voting and commit/finalization
  _Outcome:_ Full round: pre-prepare → prepare (2f+1) → commit (2f+1) → finalize; view change stub · _Artifact:_ `src/pbft/`
- `[ ]` **T30** `H` Engineer — Test PBFT correctness under honest nodes
  _Outcome:_ Finalizes with 4/7/10 nodes; no forks; latency logged · _Artifact:_ `wiki/experiments/<date>_pbft-baseline.md`
- `[ ]` **T31** `M` Engineer — Write unit tests for PBFT
  _Outcome:_ 5+ tests: happy path, insufficient votes, timeout, message loss, multi-round · _Artifact:_ `src/tests/pbft/`

## Week 6 — PoS implementation + start Ch. 3

- `[ ]` **T32** `H` Engineer — Implement simplified PoS-inspired consensus
  _Outcome:_ Validator-based voting; proposer by stake/turn; threshold finality · _Artifact:_ `src/pos/`
- `[ ]` **T33** `H` Engineer — Define validator selection / turn-based proposal
  _Outcome:_ Round-robin or weighted random; fairness verified over 100 rounds · _Artifact:_ `src/pos/selection.py` + wiki update
- `[ ]` **T34** `H` Engineer — Define voting/finality rule (threshold participation)
  _Outcome:_ Finality when ≥2/3 attest; edge cases tested · _Artifact:_ `src/pos/finality.py`
- `[ ]` **T35** `H` Engineer — Test PoS correctness and comparison-ready output
  _Outcome:_ Same CSV format as PBFT · _Artifact:_ `wiki/experiments/<date>_pos-baseline.md`
- `[ ]` **T36** `M` Writer — Begin drafting Chapter 3 (Methodology)
  _Outcome:_ 2–3 pages: system model, algorithm descriptions, simulation setup, metrics · _Artifact:_ `drafts/ch3_methodology.md`

## Week 7 — Buffer / third algorithm

- `[ ]` **T37** `H` Engineer — Assess status: ready for Algorithm 3 or need buffer?
  _Outcome:_ Written assessment; decision gate · _Artifact:_ `wiki/concepts/week7-decision.md`
- `[ ]` **T38** `M` Engineer — If ready: implement DAG-based or Avalanche-style consensus
  _Outcome:_ Third algorithm producing same output format · _Artifact:_ `src/<alg3>/`
- `[ ]` **T39** `H` Engineer — If buffer: stabilize PBFT & PoS, fix bugs, unify interface
  _Outcome:_ Known bugs fixed, edge cases handled, unified `run()` interface · _Artifact:_ `src/common/runner.py`
- `[ ]` **T40** `H` Engineer — Unify output format across all algorithms
  _Outcome:_ Common CSV: run_id, algorithm, n_validators, latency_ms, throughput, msg_count, success · _Artifact:_ `wiki/concepts/output-format.md`

## Week 8 — Baseline experiments

- `[ ]` **T41** `H` Engineer — Run baseline: vary number of validators
  _Outcome:_ Results for n=4,7,10,16,25 per algorithm; 10+ seeded runs each · _Artifact:_ `results/baseline/` + experiment page
- `[ ]` **T42** `H` Engineer — Collect latency, throughput, communication overhead
  _Outcome:_ Full CSV dataset verified for completeness · _Artifact:_ `results/baseline/metrics.csv`
- `[ ]` **T43** `H` Engineer — Generate baseline comparison plots
  _Outcome:_ 4+ plots: latency vs n, throughput vs n, msgs vs n, success rate vs n · _Artifact:_ `results/baseline/plots/`
- `[ ]` **T44** `H` Engineer — Multiple seeds; compute 95% CIs
  _Outcome:_ 20–30 runs per config; mean ± CI on all plots · _Artifact:_ updated plots + stats notes
- `[ ]` **T45** `H` Writer — Draft Chapter 4 baseline section
  _Outcome:_ 3–4 pages with plots and initial observations · _Artifact:_ `drafts/ch4_results.md` · _KPI checkpoint_
- `[ ]` **L-W8** `M` Linter — Wiki lint pass (end of Week 8)
  _Outcome:_ Report before testing phase begins · _Artifact:_ `wiki/lint/<date>_report.md`

## Week 9 — Network delay experiments

- `[ ]` **T46** `H` Engineer — Inject moderate delay (100–500ms)
  _Outcome:_ Per-algorithm latency/throughput changes · _Artifact:_ `wiki/experiments/<date>_delay-moderate.md`
- `[ ]` **T47** `H` Engineer — Inject heavy delay (1–5s) + packet loss
  _Outcome:_ Degradation under 5–20% loss; success rate measured · _Artifact:_ `wiki/experiments/<date>_delay-heavy.md`
- `[ ]` **T48** `H` Engineer — Compare latency growth and success rate across algorithms
  _Outcome:_ Comparative plot + resilience ranking table · _Artifact:_ `results/delay/`
- `[ ]` **T49** `H` Engineer — Analyze which algorithm degrades most gracefully
  _Outcome:_ 1–2 page analysis: breakpoints, which is most robust and why · _Artifact:_ `wiki/experiments/<date>_delay-analysis.md`
- `[ ]` **T50** `H` Writer — Produce delay plots and written observations in Ch. 4
  _Outcome:_ 6+ plots, 2-page observations integrated · _Artifact:_ `drafts/ch4_results.md`

## Week 10 — Adversarial experiments

- `[ ]` **T51** `H` Engineer — Simulate delayed voters (intentionally slow nodes)
  _Outcome:_ 10–30% slow nodes (2–10× normal delay); impact on finality time · _Artifact:_ experiment page
- `[ ]` **T52** `H` Engineer — Simulate non-participating validators (offline)
  _Outcome:_ 10–33% offline; success/failure boundary identified · _Artifact:_ experiment page
- `[ ]` **T53** `M` Engineer — Simulate equivocating nodes if feasible
  _Outcome:_ Conflicting votes; fork rate measured · _Artifact:_ experiment page
- `[ ]` **T54** `H` Engineer — Measure liveness and safety degradation
  _Outcome:_ Liveness = % rounds reaching consensus; Safety = fork/inconsistency count · _Artifact:_ metrics spec + plots
- `[ ]` **T55** `H` Engineer — Produce adversarial comparison tables
  _Outcome:_ Summary: algorithm × adversary × metric; robustness ranking · _Artifact:_ `results/adversarial/` · _KPI checkpoint_
- `[ ]` **T56** `H` Writer — Draft performance–security tradeoff discussion
  _Outcome:_ 2–3 page analysis answering RQ4 · _Artifact:_ `drafts/ch4_results.md`
- `[ ]` **L-W10** `M` Linter — Wiki lint pass (end of Week 10)
  _Outcome:_ Report before writing crunch · _Artifact:_ `wiki/lint/<date>_report.md`

## Week 11 — Enhancement + findings

- `[ ]` **T57** `M` Engineer — Implement adaptive timeout (exp backoff + jitter)
  _Outcome:_ `base × 2^(failures) + jitter`, calibrated to observed RTT · _Artifact:_ `src/common/timeout.py` + wiki page
- `[ ]` **T58** `M` Engineer — Compare baseline vs enhanced
  _Outcome:_ Side-by-side latency + success rate under delay/adversary · _Artifact:_ experiment page + plots
- `[ ]` **T59** `H` Writer — Summarize key findings across experiments
  _Outcome:_ Top 5–10 findings with evidence and RQ mapping · _Artifact:_ `wiki/concepts/key-findings.md`
- `[ ]` **T60** `H` Writer — Write Chapter 5 (Enhancement) and Chapter 6 (Conclusion)
  _Outcome:_ Ch5 3–4 pages; Ch6 2–3 pages summary + future work · _Artifact:_ `drafts/ch5_enhancement.md`, `drafts/ch6_conclusion.md`

## Week 12 — Polish & defense

- `[ ]` **T61** `H` Writer — Revise all chapters for consistency
  _Outcome:_ Terminology consistent, no contradictions, references complete · _Artifact:_ `drafts/`
- `[ ]` **T62** `H` Writer — Improve all figures, tables, captions
  _Outcome:_ Publication-quality: labeled axes, legends, consistent colors · _Artifact:_ `results/` + `drafts/`
- `[ ]` **T63** `H` Writer — Verify objectives ↔ experiments ↔ conclusions alignment
  _Outcome:_ Traceability matrix: RQ → experiment → conclusion · _Artifact:_ `wiki/concepts/traceability-matrix.md`
- `[ ]` **T64** `H` Writer — Prepare presentation slides
  _Outcome:_ 15–20 Marp slides: title, problem, methodology, results, demo, Q&A · _Artifact:_ `drafts/defense.md` (Marp)
- `[ ]` **T65** `H` Writer — Rehearse oral defense
  _Outcome:_ 2+ rehearsals; 15–20 min; answers to 10 expected questions · _Artifact:_ rehearsal notes in `wiki/log.md`
- `[ ]` **T66** `H` Engineer — Final code package + README + reproducibility check
  _Outcome:_ Zip archive: code, configs, seeds, README, sample output verified · _Artifact:_ `results/release/` · _KPI checkpoint_
- `[ ]` **L-W12** `M` Linter — Final wiki lint pass
  _Outcome:_ Final report; any remaining `TODO(cite)` or dead links resolved before submission · _Artifact:_ `wiki/lint/<date>_report.md`

---

## Backlog

Agents append here when they notice out-of-scope issues during a task.
````

---

## First session kickoff

Once the seven files are in place, open Claude Code in the repo root. Your
first session handles the W0 sync: pull in the Week 1–2 work you already
have. Sample opening message:

```
I am starting W0 sync. Begin with task S1: import my PBFT deep-dive notes
into wiki/algorithms/pbft.md. My existing notes are at <path>. Follow the
Researcher role prompt in docs/roles.md and the per-task workflow in
docs/workflow.md. Stop after step 7 so I can review the diff.
```

After S1–S9 merge cleanly, move on to **T11** (Chapter 1 draft) — the
first task where a Writer runs against a newly-synced wiki.

## A note on multi-agent parallelism

You asked earlier whether multiple agents can share a role. Short answer:
no. The recommended pattern is **cross-role parallelism when file scopes
are disjoint** — e.g., a Writer on T11 (touches `drafts/`) running at the
same time as an Engineer on T21 (touches `src/`). Same role, same subtree,
concurrent agents → merge conflicts and subtle context drift. Keep it
serial within a role.

## A note on sub-agents and slash commands

Deferred on purpose. Build them only after running 5–10 tasks manually and
noticing which friction is real (probably: keeping `wiki/index.md` in
sync, remembering to append to `log.md`). Designing tools before running
the workflow codifies untested assumptions.

## Evolving this doc

`PROJECT_INIT.md` is a one-shot bootstrap doc — it's not read by Claude
Code at session time (`CLAUDE.md` is). Once you've scaffolded, the live
operating manual is `CLAUDE.md` + `docs/*.md`. Changes to conventions go
there, not here.