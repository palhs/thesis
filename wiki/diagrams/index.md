# Diagrams

> Standalone folder for thesis diagrams. Each diagram lives in its own
> Markdown file containing a Mermaid source block plus per-step
> elaboration. Mermaid blocks render via
> [`mmdc`](https://github.com/mermaid-js/mermaid-cli).
>
> This page is the navigation entry point. Wiki pages that need a
> diagram link here via `[[diagrams/<group>/<slug>]]`. New diagram
> groups append a new catalogue section below.
>
> Authoritative Mermaid syntax reference for this project:
> [`docs/mermaid-syntax.md`](../../docs/mermaid-syntax.md). The legend
> below is a tour-sized summary; the syntax doc has the upstream-pinned
> details and the project conventions.

## Legend

Notation conventions used across the diagram set. Two Mermaid diagram
types are in use — `sequenceDiagram` for every protocol main loop,
scheduler-contract, and runtime view; `flowchart` for taxonomy and
component diagrams where there is no time axis.

### Mermaid `sequenceDiagram`

| Symbol | Meaning |
| :-- | :-- |
| `sequenceDiagram` | First line — declares the chart type. |
| `participant A` | Declares a lifeline. Declaration order locks left-to-right order on the page. |
| `autonumber` | Auto-numbers every arrow line. |
| `A->>B: msg` | Solid arrow with arrowhead — synchronous call or network send. |
| `A-->>B: msg` | Dotted arrow with arrowhead — return value or response to a prior call. |
| `Note over A: text` | Annotation tied to one lifeline. |
| `Note over A,B: text` | Multi-actor note spanning from `A` to `B`. The workhorse for cross-lifeline annotations. |
| `alt cond` / `else cond'` / `end` | `n`-way branch (at least one `alt`, zero or more `else`, one `end`). |
| `opt cond` / `end` | Single-arm optional branch (no `else`). |
| `loop label` / `end` | Repeated section — used for protocol main-loop iterations. |
| `rect rgb(r,g,b)` / `end` | Visually shaded background block. Project convention: `rect rgb(240,240,240)` (light gray) wraps a heavy section, with `Note over <leftmost>,<rightmost>: <phase>` as the first line inside. |
| `%% text` | Line-level comment — stripped before render. Used to pin the source spec a diagram traces to. |

**Authoring notes.** Mermaid parses `;` as a statement separator —
avoid it inside note/message text (use `,` or `—`). The literal
characters `<` and `>` are arrow markers — keep them out of note text
(use words or parentheses); they are safe inside `alt`/`opt` labels.
The CLI does not render `<b>...</b>` in sequence-diagram labels; bold
emphasis is decorative-only and dropped from the source.

### Mermaid `flowchart`

Used for taxonomy and component diagrams where there is no time axis —
just parent/child or containment relationships. Currently one diagram:
[[diagrams/concepts/bft-families-tree]].

| Symbol | Meaning |
| :-- | :-- |
| `flowchart TD` | Top-down flowchart layout. Used for taxonomy trees. |
| `A["label"]` | Node `A` with a display label. `<br/>` is a line break, `<b>...</b>` is bold (HTML works in flowchart labels). |
| `A --> B` | Directed edge from `A` to `B` (parent → child in a tree). |
| `classDef name fill:#...,stroke:#...` | Define a visual class. |
| `class A,B name` | Apply a class to one or more nodes. |

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

**One route — Mermaid CLI (`mmdc`) agent export.** Every diagram is
Mermaid; the agent that authors the diagram also produces the PDF in
the same pass. No `TODO(human-export)` marker is needed — the draft
cites the rendered figure straight away. Invocation:

```
PUPPETEER_SKIP_DOWNLOAD=true \
  npx --yes @mermaid-js/mermaid-cli@latest \
  -p puppeteer-config.json \
  -c mermaid-config.json \
  -i wiki/diagrams/<group>/<slug>.md \
  -o wiki/diagrams/<group>/<slug>.pdf \
  -b transparent -t neutral
mv wiki/diagrams/<group>/<slug>-1.pdf wiki/diagrams/<group>/<slug>.pdf
```

`puppeteer-config.json` (repo root) points `executablePath` at the
system Chrome to skip the bundled Chromium download.
`mermaid-config.json` (repo root) sets `securityLevel: loose` for
HTML rendering in flowchart labels. The `mv` step renames mmdc's
`<slug>-1.pdf` Markdown-input output to the canonical `<slug>.pdf`.

The PDF filename must match the diagram's wiki slug exactly; agents
never invent a PDF path that does not.

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

The five T17 contract diagrams and the five T20 diagrams (one
`runtime/`, four `protocols/`) were originally authored in
Swimlanes.io and migrated to Mermaid `sequenceDiagram` on 2026-05-26
(see § Revisions). The concept diagram
[[diagrams/concepts/bft-families-tree]] was authored directly in
Mermaid `flowchart`.

Forward wikilinks to unwritten pages
([[concepts/adversary-model]], [[concepts/reproducibility]],
[[concepts/output-format]], [[concepts/experiment-matrix]]) are
deliberately left dead and will resolve when T18, T27, T40, and T19
land — same pattern S5 and S7 used during the Week 2 imports.

## Revisions

- **2026-05-26 — Swimlanes.io → Mermaid migration.** All 10 outstanding
  Swimlanes.io diagrams converted to Mermaid `sequenceDiagram`. The
  figure pipeline collapsed to one DSL and one agent-driven render
  route (`mmdc`); the `TODO(human-export)` marker mechanism is retired
  in this same pass. Plan:
  [`docs/plans/2026-05-26-swimlanes-to-mermaid.md`](../../docs/plans/2026-05-26-swimlanes-to-mermaid.md).
