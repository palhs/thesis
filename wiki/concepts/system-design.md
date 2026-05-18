# System Design

Consolidated protocol-execution view of the thesis simulator: how the
Week-3 design contracts — [[concepts/node-model]] (T14),
[[concepts/network-model]] + [[concepts/network-model-phases]] (T15),
[[concepts/message-types]] (T16), [[concepts/simulation-design]] +
[[concepts/simulation-design-runtime]] (T17), [[concepts/adversary-model]]
(T18) — fit together into one running system.

This page is a **synthesis**, not a new contract. It introduces no
mechanism the W3 pages do not already own; it draws the architecture as
a runtime sequence. Consumed by the W4 implementation (T21–T27) and the
per-protocol implementations (T28, T32, T38). The page is split per
`docs/wiki-spec.md` § Page size:

- **This page.** Architecture (§2) and one run end-to-end (§3).
- **[[concepts/system-design-protocols]] (the companion).** The four
  protocols' main loops as event-handler pseudocode, and the
  open-to-revision register spanning both pages.

## 1. Scope and relation to the W3 set

The W3 pages each specify one component in isolation. This page and its
companion answer the cross-cutting questions none of them owns alone:

- **What runs the system?** §2 — the architecture and component
  layering.
- **What is one run?** §3 — the macro walkthrough, config to one
  `results.csv` row.
- **What does each protocol *do*?** [[concepts/system-design-protocols]]
  — the four main loops as pseudocode.

Every diagram across both pages uses Swimlanes.io syntax per the legend
in [[diagrams/index]]; the diagrams themselves live as standalone files
([[diagrams/runtime/macro]] and the four under `diagrams/protocols/`)
per the T17 precedent.

## 2. Architecture

The simulator is a single-process discrete-event system. Five
component types, layered: the **Harness** builds and drives; the
**Scheduler** owns the only run loop and the virtual clock; the
**Network** delivers messages with delay and loss; the **Nodes** run
protocol logic; the **Logger** captures the event stream.

| Component | Role | Owning page |
| :-- | :-- | :-- |
| `Harness` | Builds the system, iterates the experiment matrix, seeds workload, reduces events to metrics | T19 / T27 |
| `Scheduler` | The only run loop; virtual clock; typed-event min-heap; determinism contract | [[concepts/simulation-design]] |
| `Network` | Full-mesh delivery; per-phase delay / drop; envelope routing | [[concepts/network-model]] |
| `Node` | Validator: shared lifecycle + inbound/outbound API + per-protocol FSM | [[concepts/node-model]] |
| `Message` | Wire envelope + per-protocol type/payload catalog | [[concepts/message-types]] |
| `AdversaryProfile` | Optional per-`Node` deviation strategy | [[concepts/adversary-model]] |
| `Logger` / `EventSink` | Captures `decided` / `halted` / message events for metric reduction | T24 |

**Control flow is one-directional.** The Harness wires the system once
([[diagrams/scheduler/bootstrap]]), then calls `Scheduler.run()`. From
there the Scheduler pops events and dispatches to `Node` handlers; a
`Node` acts only through its outbound API (`send` / `broadcast` /
`set_timer` / `emit`), never by calling another component directly
([[concepts/node-model]] §7). The Scheduler never inspects message
contents or FSM state — protocol behaviour and scheduler infrastructure
are the two-layer split every W3 page commits to.

**The adversary is a `Node`-local slot, not a layer.** An
`AdversaryProfile` attaches at `Node.adversary` and intercepts that
node's outbound calls ([[concepts/node-model]] §9); it adds no
component and no scheduler hook ([[diagrams/scheduler/constraints]]).

## 3. One run, end to end

Visual: [[diagrams/runtime/macro]]. One experiment-matrix cell plus one
seed produces one row of `results.csv`, in six phases:

1. **Init.** The Harness loads one config cell — protocol, validator
   count `n`, network phase timeline, adversary, workload, seed — and
   builds the wired system (the six-phase bootstrap of
   [[diagrams/scheduler/bootstrap]], collapsed to one `build()` step).
2. **Workload.** The Harness seeds the proposers' local mempools with
   transactions; the simulator has no external client
   ([[concepts/message-types]] §1).
3. **Run loop.** `Scheduler.run(t_max, stop_when)` pops events and
   dispatches them until a stop condition fires. All protocol message
   exchange happens here ([[diagrams/scheduler/event-dispatch]]).
4. **Stop.** `run()` returns a `RunResult` labelled with which of the
   three stop conditions fired — `quiescence`, `deadline`, `predicate`.
5. **Flush + reduce.** The Harness flushes the Logger's event stream
   and reduces it to metrics — latency, throughput, message count,
   success — per [[concepts/evaluation-metrics]].
6. **Output.** One row is appended to `results.csv`.

Metric computation is harness-side; the Scheduler never computes a
metric ([[concepts/simulation-design-runtime]] §2).

## 4. Per-protocol main loops

The simulator is event-driven: the **Scheduler owns the only run
loop**, and a `Node` is a set of handlers — `start`, `on_message`,
`on_timer` ([[concepts/node-model]] §6) — over a per-protocol FSM.
There is no textbook "main loop" per protocol; each protocol's
handler-dispatch logic is given as event-handler pseudocode in the
companion page, [[concepts/system-design-protocols]], one section per
protocol, each paired with its Swimlanes.io diagram:

- PBFT — [[concepts/system-design-protocols]] §2,
  [[diagrams/protocols/pbft]].
- Casper FFG — [[concepts/system-design-protocols]] §3,
  [[diagrams/protocols/casper-ffg]].
- Snowman — [[concepts/system-design-protocols]] §4,
  [[diagrams/protocols/snowman]].
- Narwhal+Tusk — [[concepts/system-design-protocols]] §5,
  [[diagrams/protocols/narwhal-tusk]].

## 5. Sources

Synthesis page; no primary-literature citations. Mechanism semantics
and the bibliography live on the algorithm pages.

**Inbound (existing wiki pages):**

- [[concepts/node-model]] (T14) — lifecycle, inbound/outbound API,
  FSM table, adversary slot; §2 builds directly on it.
- [[concepts/network-model]] / [[concepts/network-model-phases]] (T15)
  — delivery layer in §2.
- [[concepts/message-types]] (T16) — the wire vocabulary §3 references.
- [[concepts/simulation-design]] / [[concepts/simulation-design-runtime]]
  (T17) — the Scheduler and run loop §3 walks through.
- [[concepts/adversary-model]] (T18) — the §2 adversary slot.
- [[concepts/evaluation-metrics]] — metric reduction in §3 phase 5.

**Companion:** [[concepts/system-design-protocols]] — the §4 main
loops in full, plus the open-to-revision register spanning both pages.

**Visual contract:** [[diagrams/runtime/macro]] and the four
[[diagrams/index]] `protocols/` diagrams.

**Forward references (sibling pages, not yet authored):**
[[concepts/experiment-matrix]] (T19) drives the §3 run; T21–T27
implement the §2 components; [[concepts/output-format]] (T40) fixes the
§3 phase-6 CSV row.

## Revisions

None.
