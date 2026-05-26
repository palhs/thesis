# Diagrams

> Standalone folder for thesis diagrams. Each diagram lives in its own
> Markdown file containing a source block (Swimlanes.io for
> sequence/interaction diagrams, Mermaid for taxonomy/component
> diagrams) plus per-step elaboration. Swimlanes.io blocks render via
> [swimlanes.io](https://swimlanes.io) paste-and-render; Mermaid blocks
> render via [`mmdc`](https://github.com/mermaid-js/mermaid-cli).
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

### Mermaid syntax

Used for taxonomy and component diagrams where a sequence-flow
notation is the wrong fit (no time axis, no message exchange — just
parent/child or containment relationships). Primitives used in this
diagram set:

| Symbol | Meaning |
| :-- | :-- |
| `flowchart TD` | Top-down flowchart layout. Used for taxonomy trees. |
| `A["label"]` | Node `A` with a display label. `<br/>` inside the label is a line break; `<b>...</b>` is bold. |
| `A --> B` | Directed edge from `A` to `B` (parent → child in a tree). |
| `classDef name fill:#...,stroke:#...` | Define a visual class. |
| `class A,B name` | Apply a class to one or more nodes. |

Render with `mmdc -i <slug>.mmd -o <slug>.pdf -b transparent -t neutral`
(see § Export for thesis figures below).

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

### Concept diagrams — Chapter 2 ([[concepts/consensus-families]])

Taxonomy/component figures consumed by Chapter 2. Rendered in Mermaid
(see § Mermaid syntax above) because Swimlanes.io has no idiomatic
representation for a containment tree.

- [[diagrams/concepts/bft-families-tree]] — propagation of the
  Byzantine Generals Problem [1] into the four families this thesis
  evaluates. Three layers, four sibling branches. Consumed by
  `drafts/ch2_litreview.md` §2.3 (Figure 2.1).

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

## Export for thesis figures

Each diagram is also a thesis figure. Rendered PDFs are co-located with
their source: `wiki/diagrams/<group>/<slug>.pdf` sits beside the matching
`.md`. The PDF is committed to git and is the authoritative render — a
diagram and its PDF travel together.

The export route depends on the DSL:

- **Swimlanes.io (sequence diagrams) — human export.** No clean CLI;
  the human opens the diagram's `.md` on swimlanes.io, exports the PDF
  (not PNG — vector keeps it crisp and text-selectable), and saves it
  as the sibling `<slug>.pdf`. The Writer drops a `TODO(human-export)`
  marker in the draft per `docs/draft-style.md § Figures and diagrams`
  until the PDF lands.
- **Mermaid (taxonomy/component diagrams) — agent export.** The
  Mermaid CLI (`mmdc`) renders directly from the command line, so the
  agent that authors the diagram also produces the PDF in the same
  pass. No `TODO(human-export)` marker; the draft cites the rendered
  figure straight away. Invocation:
  ```
  PUPPETEER_SKIP_DOWNLOAD=true \
    npx --yes @mermaid-js/mermaid-cli@latest \
    -p <puppeteer-config.json> \
    -i <slug>.mmd -o <group>/<slug>.pdf \
    -b transparent -t neutral
  ```
  where `puppeteer-config.json` points `executablePath` at the system
  Chrome to skip the bundled Chromium download.

In both routes, the PDF filename must match the diagram's wiki slug
exactly; agents never invent a PDF path that does not.

T62 (W12 figure polish) copies `wiki/diagrams/**/*.pdf` into
`../thesis-tex/MIT-thesis-template/figures/` and finalises captions,
labels, and the list-of-figures. L-W12 verifies every figure
reference in `drafts/` has a PDF on disk (lint check 8).

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
