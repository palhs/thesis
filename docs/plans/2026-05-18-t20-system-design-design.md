# T20 — System design diagram + per-protocol pseudocode (design)

Date: 2026-05-18 · Task: T20 · Role: Engineer

## Goal

Consolidate the Week-3 design set (node / network / message / scheduler /
adversary models) into one protocol-execution view: a system architecture
expressed as a runtime sequence, plus per-protocol main-loop pseudocode for
PBFT, Casper FFG, Snowman, and Narwhal+Tusk.

## Decisions (brainstorming, 2026-05-18)

1. **Diagram set** — produce both unbuilt families the `diagrams/index.md`
   "What is not drawn (yet)" section reserved: one macro-runtime diagram +
   four per-protocol main-loop sequence diagrams. 5 swimlanes.io diagrams.
2. **Diagram storage** — standalone files under `wiki/diagrams/<group>/`
   (T17 precedent), each with a swimlanes block + per-step elaboration.
   New groups: `runtime/` (macro) and `protocols/` (the four).
3. **Pseudocode form** — event-handler-structured (`on_message` / `on_timer`
   / `start`), not a textbook `while` loop. The Scheduler owns the only run
   loop; each Node is a set of handlers + a per-protocol FSM. "Main loop" is
   read as "handler dispatch logic."
4. **Diagram syntax** — swimlanes.io throughout, per the legend already
   codified in `wiki/diagrams/index.md` §Legend.

## Deliverables

- `wiki/concepts/system-design.md` — architecture prose + component table +
  macro-runtime walkthrough + four event-handler pseudocode sketches +
  open-to-revision register.
- `wiki/diagrams/runtime/macro.md` — config → one `results.csv` row, six
  phases (init → workload → run loop → stop → flush → output).
- `wiki/diagrams/protocols/{pbft,casper-ffg,snowman,narwhal-tusk}.md` —
  one main-loop sequence diagram per protocol.
- Updates: `wiki/diagrams/index.md` (two catalogue sections + status),
  `wiki/index.md` (system-design under Concepts), `wiki/log.md` (T20 entry).

## Notes

- Pseudocode is an explicitly non-binding reference sketch, consistent with
  the W3 design-contract style (`node-model` §10, `message-types` §8). T28–
  T39 implementations may revise it; revisions land per wiki-spec §Revisions.
- TASKS.md lists only `system-design.md` as the artifact; storing diagrams
  as standalone files expands the touched-file set to ~9. This matches the
  T17 convention and the slots `diagrams/index.md` pre-reserved; inlining
  would breach the ~300-line wiki-spec page limit. Flagged for the human in
  the In-Review summary.
- Deliverable is documentation, not code — no `writing-plans` / TDD step.

## Verification

- All five swimlanes blocks parse against the syntax in `diagrams/index.md`.
- Every wikilink in the new pages resolves on disk.
- `system-design.md` stays under the ~300-line wiki-spec limit.
- Pseudocode handler signatures match `node-model` §6/§7 exactly.
