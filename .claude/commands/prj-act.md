---
description: Approve or deny an In Review task — flips status in TASKS.md; does not merge, commit, or push
argument-hint: <task-id> <approve|deny> [reason]
---

You are acting on a reviewed task. Arguments: $ARGUMENTS

## Step 1 — Parse arguments

- **First token** = task ID (e.g. `S1`, `T14`, `L-W4`).
- **Second token** = action: must be exactly `approve` or `deny`. Any other value → stop with an error.
- **Remaining tokens** (optional) = free-text reason. Only used for `deny`; ignored for `approve`.

If fewer than 2 tokens are provided, stop with:

```
Usage: /prj-act <task-id> <approve|deny> [reason]
```

## Step 2 — Verify the task is In Review

Read `TASKS.md` and locate the row for the given task ID. The row looks like:

```
- `[?]` **<ID>** `<priority>` <role> — <title>
```

- If no row matches the given ID → stop with: `Task <ID> not found in TASKS.md.`
- If the row's status symbol is not `` `[?]` `` → stop with: `Task <ID> is not In Review (status: <actual>). Not acting.`

## Step 3 — Act

Use the Edit tool with enough surrounding context to match the task line uniquely — for example, include `` **<ID>** `` in the `old_string`. The Legend line also contains `` `[?]` ``, so never edit `` `[?]` `` alone.

### If action is `approve`

1. On the matched line, change `` `[?]` `` to `` `[x]` ``. Change nothing else on the line. Do not touch any other file.
2. Determine the base branch (for the merge hint):
   - Try `git symbolic-ref --quiet refs/remotes/origin/HEAD` and strip the `refs/remotes/origin/` prefix.
   - If that fails (no `origin` remote), fall back: whichever of `main`, `master` exists as a local branch (`git show-ref --verify --quiet refs/heads/<name>`).
   - Call the result `<base>`. If neither works, use the literal string `<base>` in the hint and note `(could not detect base branch)`.
3. Determine the task branch: `git branch --list 'task/<ID>-*'`. Capture the first match. If none match, use `<branch-name-unknown>` in the hint below.
4. Print (substitute `<base>` and `<branch-name>` with the actual values):

```
Approved <ID>. Status flipped to [x] Completed in TASKS.md.

Merge from your IDE:

  git switch <base>
  git merge --no-ff <branch-name>
```

Do NOT run `git merge`, `git commit`, or `git push`. The human commits and merges from the IDE.

### If action is `deny`

1. On the matched line, change `` `[?]` `` to `` `[~]` ``.
2. Append a silent HTML comment to the end of that same line. Use today's date from the system context. Format:
   - With reason: ` <!-- denied YYYY-MM-DD: <reason> -->`
   - Without reason: ` <!-- denied YYYY-MM-DD -->`
   Note the leading space before `<!--`. The comment goes after the existing title text, still on the same line.
3. Do **not** add an entry to `wiki/log.md`. Denials are silent per project convention.
4. Print:

```
Denied <ID>. Status returned to [~] In Progress; silent denial comment appended to the task line. Branch untouched.
```

Do NOT run any git command. The human commits the TASKS.md change from the IDE.

## Step 4 — Stop

Do not run `git commit`, `git merge`, or `git push`. Your only mutation is the single-line edit to `TASKS.md`.
