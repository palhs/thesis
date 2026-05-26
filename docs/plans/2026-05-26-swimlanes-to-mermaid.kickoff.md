# Kickoff prompt — Swimlanes → Mermaid migration

Paste the block below into a fresh Claude Code session opened in this
repository. It briefs a cold agent (no prior conversation history) and
points it at the persisted plan + syntax reference.

---

## Prompt

You are picking up a documentation-pipeline migration that has already
been designed. Your job is to execute it. **Read first, do not
improvise** — every decision is already pinned in the persisted docs.

**Read on pickup, in this order:**

1. `CLAUDE.md` — repo orientation and hard rules. The relevant
   constraints for this task: do not flip TASKS.md to Completed, one
   logical change per commit, do not modify `raw/`.
2. `docs/workflow.md` — branch convention, commit convention, scope
   discipline. This task uses a non-numbered branch
   (`task/diagrams-mermaid-migration`); it is meta-maintenance, not a
   T-task.
3. `docs/plans/2026-05-26-swimlanes-to-mermaid.md` — **the binding
   plan**. Eleven sections covering motivation, the 10-diagram
   inventory, the Swimlanes-→-Mermaid translation cheat-sheet, the
   per-diagram conversion procedure, prose-file edits, drafts cleanup,
   verification checklist, the 7-commit sequence, out-of-scope items,
   risks, and the done-definition. Treat §8 (commit plan) and §11
   (done definition) as the contract.
4. `docs/mermaid-syntax.md` — the authoritative Mermaid syntax
   reference for this project, curated from the upstream `develop`
   branch. Read §1 (`sequenceDiagram`) in full before touching any of
   the 10 diagrams; §2 (`flowchart`) is not exercised by this
   migration but is the reference if you hit anything taxonomic.

**Then execute the plan:**

- Record the **starting branch name** at pickup with `git rev-parse
  --abbrev-ref HEAD` and remember it. You will merge back to it at
  the end (this is the user's active development branch — at the time
  of writing, `task/T36-ch3-methodology`).
- Create the branch `task/diagrams-mermaid-migration` **from the
  starting branch's HEAD** (`git checkout -b
  task/diagrams-mermaid-migration`). This is meta-maintenance and does
  not flow through `TASKS.md` status flips.
- Work the seven commits in `2026-05-26-swimlanes-to-mermaid.md` §8 in
  order. The 10 diagram conversions land as two batched commits
  (scheduler group, then runtime + protocols group); each batch
  commits the converted `.md` files and the rendered `.pdf` files
  together.
- Use the `mmdc` invocation pinned in `docs/mermaid-syntax.md` § Render
  path. The `puppeteer-config.json` from the prior
  `bft-families-tree.pdf` render is already in the repo; reuse it.
- Render `wiki/diagrams/scheduler/constraints.md` first (7 lifelines
  — the widest in the set) as the worst-case layout check before
  committing to the conversion style for the other nine. If layout is
  unacceptable, fall back to the per-section split documented in §10
  Risks.
- Run the §7 verification checklist on the migration branch before the
  merge-back. The four greppable checks (`grep -rE '\`\`\`swimlanes'`,
  `grep -r 'TODO(human-export)'`, PDF freshness loop, wikilink
  resolution) are the gate.

**Then merge back into the starting branch so the user can continue
their in-flight work:**

- Push the migration branch first: `git push -u origin
  task/diagrams-mermaid-migration`. This preserves it as a reviewable
  standalone unit — the human may still want to open a PR from it to
  `main` later, independent of whatever else lands on the starting
  branch.
- Switch back: `git checkout <starting-branch>`.
- Merge: `git merge --no-ff task/diagrams-mermaid-migration -m
  "Merge branch 'task/diagrams-mermaid-migration' into
  <starting-branch>"`. Use `--no-ff` so the merge is a visible commit
  in the history of the starting branch (not silently fast-forwarded
  away) — this makes it easy to revert if needed and keeps the audit
  trail honest.
- If the merge has conflicts (the user's in-flight work on the
  starting branch touched a file the migration also touched —
  realistically only `drafts/ch3_methodology.md` is at risk, where
  the migration strips three `TODO(human-export)` lines), **stop and
  surface the conflict**. Do not auto-resolve. The user is the
  authority on which side wins for in-flight prose edits.
- **Do not push the starting branch.** Leave the merge commit local
  so the user can inspect it and push when they are ready. The
  migration branch is already on origin; that is enough for review.
- Re-run the §7 verification checks on the merged starting-branch
  HEAD as well, to confirm the merge did not reintroduce a stale
  `TODO(human-export)` line or a missing PDF.

**Do not, in this session:**

- Touch `src/`, `tests/`, `raw/`, `results/`, or `TASKS.md`. None of
  these are in scope (`2026-05-26-swimlanes-to-mermaid.md` §9).
- Re-design the diagram conventions. The Swimlanes-→-Mermaid mapping
  in plan §3 is mechanical; if you find a Swimlanes construct that
  the cheat-sheet does not cover, stop and ask — do not invent.
- Rewrite historical entries in `wiki/log.md` or
  `docs/plans/2026-05-18-…md`. History is not silently overwritten
  (`docs/wiki-spec.md` § Revisions rule).
- Self-complete or self-merge. Per `CLAUDE.md` hard rules, the agent
  pushes the branch and the human reviews + merges.

**Handoff format when done:** the migration branch is pushed and
merged locally into the starting branch. Summarise for the human in
this shape:

- Migration branch name + commit count + the pushed remote URL.
- Starting branch name + the SHA of the merge commit (local only,
  not pushed).
- Files touched (grouped by the seven migration commits, plus the
  merge commit on the starting branch).
- Whether the merge was clean or required conflict resolution; if
  resolution happened, which file(s) and which side won.
- Verification output: paste the four greppable checks and their
  results, run on **the starting-branch HEAD after merge** (not just
  on the migration tip).
- Any §10 risks that actually fired during execution, and how you
  resolved them.
- One open question, if any. Otherwise: "none."

If anything in the plan turns out to be wrong or under-specified
mid-execution, stop and surface the conflict — do not paper over it.
The plan is binding for design decisions; an unexpected blocker is a
reason to pause, not to improvise.

---

## Notes for the human pasting this

- The prompt is intentionally self-contained. The fresh agent does not
  need the prior conversation that produced the plan — everything
  load-bearing is in the linked files.
- If you want the agent to also clear `drafts/review.html` (the
  auto-generated review render that mirrors `drafts/ch3_methodology.md`
  and currently carries the three `TODO(human-export)` lines), say so
  explicitly when pasting — the plan §6 flags it as "leave to its next
  regenerator" by default.
- The agent should ask before running `npx --yes @mermaid-js/mermaid-cli@latest`
  the first time (it pulls a network dependency); approve it once and
  it will reuse the cached install for the remaining nine diagrams.
- The merge-back to the starting branch is done locally and **not
  pushed**, so you can inspect the merge commit before publishing. If
  you would rather the agent push the starting branch too, say so when
  pasting — otherwise the default is "migration branch pushed,
  starting-branch merge commit local."
- If you have done parallel work on the starting branch in another
  session while the migration was running, the merge may need conflict
  resolution. The agent is instructed to stop and ask in that case
  rather than auto-resolving.
