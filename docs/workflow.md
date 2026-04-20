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
