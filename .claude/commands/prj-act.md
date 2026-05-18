---
description: Approve or deny an In Review task — flips status and recomputes the Dashboard counts in TASKS.md; does not merge, commit, or push
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

1. On the matched line, change `` `[?]` `` to `` `[x]` ``. Change nothing else on that line.
2. Recompute the Dashboard status-count line — see **Step 4**.
3. Determine the base branch (for the merge hint):
   - Try `git symbolic-ref --quiet refs/remotes/origin/HEAD` and strip the `refs/remotes/origin/` prefix.
   - If that fails (no `origin` remote), fall back: whichever of `main`, `master` exists as a local branch (`git show-ref --verify --quiet refs/heads/<name>`).
   - Call the result `<base>`. If neither works, use the literal string `<base>` in the hint and note `(could not detect base branch)`.
4. Determine the task branch: `git branch --list 'task/<ID>-*'`. Capture the first match. If none match, use `<branch-name-unknown>` in the hint below.
5. Print (substitute `<base>` and `<branch-name>` with the actual values):

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
3. Recompute the Dashboard status-count line — see **Step 4**.
4. Do **not** add an entry to `wiki/log.md`. Denials are silent per project convention.
5. Print:

```
Denied <ID>. Status returned to [~] In Progress; silent denial comment appended to the task line. Branch untouched.
```

Do NOT run any git command. The human commits the TASKS.md change from the IDE.

## Step 4 — Recompute the Dashboard status-count line

After the status flip in Step 3, the task row in `TASKS.md` already carries its
new status symbol. Now rewrite the Dashboard status-count line so its tallies
match the file's current state. Recompute every count from scratch — do not
adjust the old numbers by ±1. A full recompute is self-healing: it corrects any
pre-existing drift, not just the change you just made.

1. Count task rows by status symbol. A task row is any line matching one of the
   five regex patterns below — one per status. Use these patterns exactly as
   written; do not mentally substitute a raw symbol into a template:

   - Not Started — `` ^- `\[ \]` \*\* ``
   - In Progress — `` ^- `\[~\]` \*\* ``
   - In Review — `` ^- `\[\?\]` \*\* `` (note the escaped `\?`)
   - Completed — `` ^- `\[x\]` \*\* ``
   - Blocked — `` ^- `\[!\]` \*\* ``

   Note: in the In Review pattern the `?` is regex-escaped as `\?` because `?`
   is a regex metacharacter (a quantifier). An unescaped `[?]` would parse as an
   optional `[` followed by `]` and match (almost) nothing — do not "simplify"
   `\?` back to `?`.

   The Legend line lists all five symbols but is NOT a task row (it has no
   `` - `[..]` ** `` prefix), so it must not be counted. Sub-task rows like
   `T1.1` and `L-W2.2` DO match and must be counted. The Grep tool with
   `output_mode: "count"` is a reliable way to tally each symbol — but any
   counting method that applies the same regex works.
2. Locate the status-count Dashboard line — the one starting with `- Completed:`
   (not the `- Total tasks:` line).
3. Rewrite that line in full, preserving its exact format — the ` · `
   separators and this field order:

```
- Completed: <x> · In Review: <?> · In Progress: <~> · Not Started: < > · Blocked: <!>
```

   where each `<…>` is the count for that status symbol. Leave the
   `- Total tasks:` line completely untouched.

## Step 5 — Stop

Do not run `git commit`, `git merge`, or `git push`. Your only mutations are the
two edits within `TASKS.md` — the task row's status symbol and the Dashboard
status-count line. Do not touch any other line of `TASKS.md`, and do not touch
any other file.
