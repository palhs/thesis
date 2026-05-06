---
description: Morning review — list all [?] In Review tasks with commits, diff stats, and log entries waiting for approval
---

You are producing a review dashboard for tasks waiting on the human's approval. Read-only. Do not modify any files. Do not run `git merge`, `git commit`, or `git push`.

## Step 0 — Detect the base branch

Determine the repo's default branch once and reuse it as `<base>` for the rest of this command:

1. Try `git symbolic-ref --quiet refs/remotes/origin/HEAD` and strip the `refs/remotes/origin/` prefix. If that yields a name, use it.
2. Otherwise, fall back in order: `main`, then `master`. Pick the first that exists as a local branch (`git show-ref --verify --quiet refs/heads/<name>`).
3. If neither check yields a branch, stop with: `Could not determine base branch (no origin/HEAD, no local main/master).`

## Step 1 — Scan TASKS.md for In Review tasks

Grep `TASKS.md` for rows starting with `` - `[?]` ``. For each match, extract:

- Task ID (e.g., `T14`, `S3`, `L-W4`)
- Role and priority
- One-line title / outcome

If zero `[?]` tasks are found, print exactly:

```
No tasks waiting for review. Go make coffee.
```

and stop.

## Step 2 — For each task, gather branch and log context

Per task, in order:

1. **Branch name.** Run `git branch --list 'task/<ID>-*'` (e.g. `git branch --list 'task/S1-*'`). Capture the first match. If none match, note `(no matching branch)`.
2. **Commits since diverging from base.** If a branch was found: `git log <base>..<branch> --oneline --no-decorate`. Capture the list. If empty: `(no commits)`.
3. **Diff stats.** If a branch was found: `git diff --stat <base>...<branch>`. Capture the output.
4. **Log entry.** Grep `wiki/log.md` for the task ID. The log format is `## [YYYY-MM-DD] <type> | task <N> — <title>` followed by a few bullet lines. Capture the most recent matching block (the task ID may appear once; take the block from its header line through the last bullet before the next `## [` or EOF).

## Step 3 — Output

Print one block per task, separated by a horizontal rule. Use the actual `<base>` branch name in the commits heading (e.g. `Commits since master:`):

```
---

## <ID> — <role> · <priority> · <one-line title>

**Branch:** `<branch name or "(no matching branch)">`

**Commits since <base>:**
<commit list, one per line, or "(no commits)">

**Diff stats:**
<git diff --stat output, or "(no diff)">

**Log entry:**
<the matching wiki/log.md block, or "(no log entry found)">
```

After all tasks, print this footer:

```
---

Run `/prj-act <ID> approve` to approve, or `/prj-act <ID> deny [reason]` to deny.
Merging is your job — the approve command prints the git merge hint but does not run it.
```

Do not edit any files. Do not run `git merge`, `git commit`, or `git push`. This command is observation only.
