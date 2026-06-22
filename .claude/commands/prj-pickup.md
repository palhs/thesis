---
description: Pick up the next actionable task from TASKS.md with role context auto-filled
argument-hint: [task-id]
---

You are picking up a task from the thesis-consensus work queue. Follow this flow exactly. Do not skip steps.

## Step 1 — Identify the task

Argument (may be empty): $ARGUMENTS

- If the argument is **empty**, scan `TASKS.md` top-to-bottom and pick the first actionable task by this rule:
  1. First `[~]` In Progress task (resume) — preferred.
  2. Otherwise, first `[ ]` Not Started task from the top of the queue.
  3. Skip `[x]` Completed, `[?]` In Review, `[!]` Blocked.
- If an argument is given (e.g. `T14`, `S3`, `L-W4`), use that exact task ID. If its status is `[x]` Completed or `[?]` In Review, stop and warn the user before doing anything else.
- If nothing actionable remains (everything is `[x]`, `[?]`, or `[!]`), stop and report that — suggest running `/prj-status` for a full picture.

## Step 2 — Load context

In order:

1. Read the full task entry from `TASKS.md`. Capture: ID, role, priority, outcome, artifact paths, any verify/source/target fields.
2. Read the matching role prompt from `docs/roles.md` (Researcher / Engineer / Writer / Linter). This is your operating mode for this task — follow its flow (including any superpowers skill invocations) once execution begins.
3. Read `wiki/index.md`. Per `docs/retrieval.md`, this is always the first read of every task. Note which existing pages relate to this task.
4. **Writer tasks only — load the prose-coherence layer now, not at draft time.** If the task's role is Writer, also read `docs/draft-style.md`. If the chapter is *after* Chapter 3 (any results / synthesis / conclusion chapter), additionally read `docs/draft-narrative.md` and cross-check its ledgers (§2 RQ-closure, §3 forward-reference, §10 cheat-sheet) against the `TASKS.md` scope notes you captured in step 1. Loading these at pickup — rather than after go-ahead — surfaces any ledger-vs-`TASKS.md` contradiction (a descoped deliverable still "owed", a closed RQ still "open") while it is cheap to raise, instead of mid-draft. Reading `docs/` files is allowed here; this step does not touch `drafts/`.

## Step 3 — Report and stop

Post a short summary back:

- **Task**: `<ID>` — one-line goal
- **Role**: Researcher / Engineer / Writer / Linter
- **Artifacts to produce**: from the task entry
- **Relevant existing wiki pages** (from your `index.md` scan): 3–5 links
- **Ledger consistency** (Writer tasks on post-Chapter-3 chapters only): one line — either "`draft-narrative.md` ledgers consistent with `TASKS.md`" or the specific contradiction found and how the task will reconcile it.
- **First concrete action** you intend to take

Then **stop and wait for the human's explicit go-ahead**. Do not:

- Flip the task status in `TASKS.md` yet.
- Make any git commit.
- Read raw sources, touch `src/`, `wiki/`, or `drafts/` yet.

Once the human confirms, proceed per the role prompt's flow. The human commits; you do not run `git commit`.
