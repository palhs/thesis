# Diagrams

> Standalone folder for thesis diagrams. Each diagram lives in its own
> Markdown file containing a diagram source block plus per-step
> elaboration. Two source languages are used:
>
> - **Mermaid** — renders natively in Obsidian and GitHub. Used by the
>   simulator-runtime diagrams (the macro view).
> - **Swimlanes.io** — renders via [swimlanes.io](https://swimlanes.io)
>   paste-and-render or the swimlanes CLI. Used by the T17
>   scheduler-contract diagrams (the contract view).
>
> Both are sequence-diagram families; choice is per-diagram and noted
> in the catalogue line below.
>
> This page is the navigation entry point. Wiki pages that need a
> diagram link here via `[[diagrams/<slug>]]`. New diagrams append to
> the appropriate catalogue section.

## Legend

Notation conventions used across the diagram set.

### Swimlanes.io conventions (T17 scheduler diagrams)

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

### Mermaid conventions (simulator-runtime diagrams)

| Symbol | Meaning |
| :-- | :-- |
| `A->>B: msg` | Solid arrow. |
| `A-->>B: msg` | Dashed arrow / return. |
| `Note over A,B: text` | Multi-actor note. |
| `loop ... end` | Iteration. |
| `alt ... else ... end` | Alternation. |

### Lifeline glossary

The same role can appear under different names depending on the
diagram-set abstraction level.

| Class/code name | Runtime role label | Owning wiki page |
| :-- | :-- | :-- |
| `Node` | Validator | [[concepts/node-model]] |
| `Network` | Network | [[concepts/network-model]] |
| `Scheduler` | Scheduler | [[concepts/simulation-design]] (forthcoming) |
| `Harness` | Harness | T19 / T27 (forthcoming) |
| `Logger` / `EventSink` | Logger | T24 (forthcoming) |
| `AdversaryProfile` | Adversary | T18 (forthcoming) |
| `Heap`, `Registry`, `SeqPer` | (internal scheduler state) | this diagram set |

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
reading the wiki page. Source language: **Swimlanes.io**.

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

### Simulator runtime — how the models work together

These two diagrams sit one abstraction level above the T17 contract.
They answer: *what calls what, in what order, to take a YAML config
and produce one row of `results.csv`?* The T17 set zooms into the
Scheduler lifeline of these two. Source language: **Mermaid**.

- [[diagrams/simulator-runtime-outer]] — **outer view.** One
  experiment run, end to end. Six phases (init → workload → run loop
  → stop → flush → output). Lifelines: Harness, Config, Scheduler,
  Network, Validator, Protocol FSM, Logger.
- [[diagrams/simulator-runtime-tick]] — **inner view.** One event
  tick — what happens between two `Scheduler.pop()` calls. Shows the
  four-verb Validator outbound API.

## How to read them

Two reading paths depending on what you want.

**Path A — "what is the simulator?"** Start with
[[diagrams/simulator-runtime-outer]] for the experiment-level view,
then drill into [[diagrams/simulator-runtime-tick]] for the per-tick
mechanics. These two were drafted before T17 and operate at the
"runtime" abstraction level.

**Path B — "what is the scheduler contract?"** Read the five T17
diagrams in order: bootstrap → enqueue → dispatch → timer-lifecycle →
constraints. The first three together cover the API surface and the
run loop. The fourth covers a subtle internal pattern. The fifth pins
what is *not* in the scheduler.

If you read both paths, the relationship is: the T17 set is a zoom-in
on the `S` (Scheduler) lifeline of the runtime set. They do not
overlap; they compose.

## What is *not* drawn (yet)

- **Protocol-internal sequences.** PBFT three-phase commit, Casper FFG
  justify→finalise, Snowman `K`-peer poll, Narwhal+Tusk DAG walk.
  These belong to a future `protocols/` heading; one sequence diagram
  per protocol at matched abstraction level.
- **Adversary catalogue.** [[diagrams/scheduler/constraints]] pins
  *where* adversaries attach. The catalogue of *which* adversaries
  exist and how each one distorts the four Node outbound calls is T18
  ([[concepts/adversary-model]]).
- **Experiment matrix.** The outer-loop sketch in
  [[diagrams/simulator-runtime-outer]] gestures at it; full coverage
  is T19 ([[concepts/experiment-matrix]]).

## Status

The two simulator-runtime diagrams (Mermaid) were drafted as
scaffolding before T17 picked up. The five T17 contract diagrams
(Swimlanes.io) were authored during T17
([[concepts/simulation-design]], In Progress as of 2026-05-13). When
T17 lands and is approved, the contract diagrams become permanent
reference material for [[concepts/simulation-design]] and the
implementation work in T21.

Forward wikilinks to unwritten pages
([[concepts/simulation-design]], [[concepts/adversary-model]],
[[concepts/reproducibility]], [[concepts/output-format]]) are
deliberately left dead and will resolve when T17, T18, T27, and T40
land — same pattern S5 and S7 used during the Week 2 imports.
