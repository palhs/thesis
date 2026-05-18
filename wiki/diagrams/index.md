# Diagrams

> Standalone folder for thesis diagrams. Each diagram lives in its own
> Markdown file containing a Swimlanes.io source block plus per-step
> elaboration. Swimlanes.io blocks render via
> [swimlanes.io](https://swimlanes.io) paste-and-render or the CLI.
>
> This page is the navigation entry point. Wiki pages that need a
> diagram link here via `[[diagrams/<group>/<slug>]]`. New diagram
> groups append a new catalogue section below.

## Legend

Notation conventions used across the diagram set.

### Swimlanes.io syntax

| Symbol | Meaning |
| :-- | :-- |
| `A -> B: msg` | Solid arrow — synchronous call from `A` to `B`. |
| `A => B: msg` | **Bold** arrow — emphasised invocation (handler dispatch, `RunResult` return, key API calls). |
| `A --> B: msg` | Dashed arrow — return value, data flowing back rather than a new action. |
| `note A, B: text` | Multi-actor note spanning from `A` to `B`; carries semantic content. |
| `if: cond` / `else` / `end` | Conditional branch (up to one level of nesting per the Swimlanes spec). |
| `group: label` / `end` | Non-conditional grouping. |
| `=: text` | Bold divider — major section break inside the diagram. |
| `-: text` | Regular divider — minor section break. |
| `...: text` | Delay marker — "time passes, other events run." |
| `autonumber` | Auto-numbers every message line. |
| `order: A, B, C` | Locks lifeline order left-to-right. |

### Lifeline glossary

The same role can appear under different names depending on the
diagram-set abstraction level.

| Class/code name | Runtime role label | Owning wiki page |
| :-- | :-- | :-- |
| `Node` | Validator | [[concepts/node-model]] |
| `Network` | Network | [[concepts/network-model]] |
| `Scheduler` | Scheduler | [[concepts/simulation-design]] |
| `Harness` | Harness | T19 / T27 (forthcoming) |
| `Logger` / `EventSink` | Logger | T24 (forthcoming) |
| `AdversaryProfile` | Adversary | T18 (forthcoming) |
| `Heap`, `Registry`, `SeqPer` | (internal scheduler state) | [[concepts/simulation-design]] §4 |

`Heap`, `Registry`, and `SeqPer` are not separate classes — they are
the scheduler's internal data fields. They appear as lifelines in the
T17 diagrams to make state mutations visible at the message-sequence
level. Read them as "the scheduler talking to its own fields."

## Catalogue

### Scheduler contract — T17 ([[concepts/simulation-design]])

The five diagrams below together compress the scheduler design
contract. A reader who reads only these diagrams should be able to
reconstruct the API surface, the determinism guarantees, the cancel
semantics, the stop conditions, and the failure modes — without
reading the wiki page.

- [[diagrams/scheduler/bootstrap]] — the cast and how the harness
  wires them. Six phases from construction to run. Establishes the
  split-bind invariant (Scheduler owns `set_timer` / `cancel_timer` /
  `emit`; Network owns `send` / `broadcast`).
- [[diagrams/scheduler/event-enqueue]] — how events get onto the
  heap. Three sources (Node `set_timer`, Network delivery, Network
  phase advance) funnel through `Scheduler.schedule()`. Pins seq
  assignment and validation gates.
- [[diagrams/scheduler/event-dispatch]] — one iteration of `run()`.
  Pop, advance virtual time, deadline check, tombstone check, event
  sink, dispatch, predicate check. Three exit paths drawn explicitly.
- [[diagrams/scheduler/timer-lifecycle]] — one timer's full life
  cycle through set / cancel / overwrite / fire. Shows the lazy
  tombstone pattern: registry is the source of truth, heap is
  append-only from the cancel side.
- [[diagrams/scheduler/constraints]] — the negative space. Adversary
  boundary, RNG ownership, metric-computation ownership, wallclock
  prohibition, four fail-fast validation gates.

### Simulator runtime — T20 ([[concepts/system-design]])

One macro-level diagram, one abstraction above the T17 contract set.

- [[diagrams/runtime/macro]] — one experiment-matrix cell + seed to
  one row of `results.csv`. Six phases: init, workload, run loop,
  stop, flush, output. The run-loop phase zooms into the five
  scheduler diagrams above; `build()` zooms into
  [[diagrams/scheduler/bootstrap]].

### Protocol main loops — T20 ([[concepts/system-design-protocols]])

One sequence diagram per protocol, all at a matched abstraction
level: one consensus decision instance from first message to
`decided`.

- [[diagrams/protocols/pbft]] — three-phase commit for one
  `(view, seq)` instance; view-change branch.
- [[diagrams/protocols/casper-ffg]] — justify→finalise for one
  epoch; accountable-safety (slashing) branch.
- [[diagrams/protocols/snowman]] — subsampled `K`-peer poll loop for
  one block; accept at `counter ≥ β`.
- [[diagrams/protocols/narwhal-tusk]] — one DAG round (header → vote
  → certificate) plus the zero-message Tusk anchor commit.

## How to read them

Read the five T17 diagrams in order: bootstrap → enqueue → dispatch →
timer-lifecycle → constraints. The first three together cover the
API surface and the run loop. The fourth covers a subtle internal
pattern. The fifth pins what is *not* in the scheduler.

## What is *not* drawn (yet)

- **Adversary catalogue.** [[diagrams/scheduler/constraints]] pins
  *where* adversaries attach. The catalogue of *which* adversaries
  exist and how each one distorts the four Node outbound calls is T18
  ([[concepts/adversary-model]]).
- **Experiment matrix.** The harness-level cell × seed iteration
  shape is T19 ([[concepts/experiment-matrix]]).
## Status

The five T17 contract diagrams (Swimlanes.io) were authored during
T17 ([[concepts/simulation-design]], In Review as of 2026-05-13). When
T17 merges, they become permanent reference material for
[[concepts/simulation-design]] and the implementation work in T21.

The five T20 diagrams (one `runtime/`, four `protocols/`) were
authored during T20 ([[concepts/system-design]] /
[[concepts/system-design-protocols]], In Review as of 2026-05-18).
They close the "protocol-internal sequences" and "simulator-runtime
macro view" gaps this section previously listed.

Forward wikilinks to unwritten pages
([[concepts/adversary-model]], [[concepts/reproducibility]],
[[concepts/output-format]], [[concepts/experiment-matrix]]) are
deliberately left dead and will resolve when T18, T27, T40, and T19
land — same pattern S5 and S7 used during the Week 2 imports.
