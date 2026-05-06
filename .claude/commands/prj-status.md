---
description: Dashboard of in-progress, in-review, and blocked tasks plus recent log activity
---

You are producing a status dashboard for the thesis-consensus repo. Read-only. Do not modify any files.

## Step 1 — Scan TASKS.md

Grep `TASKS.md` for rows with status `[~]` In Progress, `[?]` In Review, or `[!]` Blocked. For each match, extract:

- Task ID (e.g., `T14`, `S3`, `L-W4`)
- Status symbol → human-readable status
- Role (Researcher / Engineer / Writer / Linter)
- Priority (H / M / L)
- One-line outcome or goal (from the task entry)

## Step 2 — Gather context

- Current git branch: `git branch --show-current`
- Last 3 log entries: grep `wiki/log.md` for lines starting with `## [` and take the last 3.

## Step 3 — Output

Print exactly one compact report in this shape (markdown):

```
## Active tasks

| ID | Status | Role | Prio | Outcome |
|----|--------|------|------|---------|
| T14 | In Progress | Engineer | H | Define node model (validator states, roles) |
| ... | ... | ... | ... | ... |

## Current branch

<branch name, or `(no git repo / detached)` if unavailable>

## Recent log entries

- [YYYY-MM-DD] <type> | task <N> — <title>
- [YYYY-MM-DD] <type> | task <N> — <title>
- [YYYY-MM-DD] <type> | task <N> — <title>
```

If there are zero `[~]` / `[?]` / `[!]` tasks, replace the table with a single line: `No active tasks. Run /prj-pickup to start the next one.`

Do not flip statuses. Do not edit any files. Do not run `git commit`. This command is observation only.
