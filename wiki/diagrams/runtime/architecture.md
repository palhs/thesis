# Simulator Architecture — One Engine, Any Protocol

> The static picture of the simulator for Chapter 3 §3.2: what the system
> is made of, what goes in, what comes out, and where the three protocols
> differ. One experiment-matrix cell plus a seed enters a fixed engine and
> leaves as one comparable row of `results.csv`. The engine is identical
> for every protocol — the only swappable part is the protocol logic.
>
> This is the **structural** companion to [[diagrams/runtime/macro]] (which
> tells the same "cell → row" story as a *temporal* sequence) and to
> [[diagrams/runtime/event-loop]] (which zooms into the Scheduler's run
> loop). The per-protocol decide rules this figure points at are catalogued
> in [[concepts/system-design-protocols]] and normalised in
> [[concepts/metric-reconciliation]].
>
> Navigation entry point: [[diagrams/index]]. Owning page:
> [[concepts/system-design]] §2.

## Diagram

> **Render source (2026-07-01):** the thesis/LaTeX figure is now the
> hand-authored `architecture.svg` in this directory, rendered to
> `architecture.pdf` (via `cairosvg`) and copied to
> `thesis-tex/.../figures/runtime-architecture.pdf`. The Mermaid block below
> is retained as the textual **structural reference** — it is no longer the
> render source, so edit `architecture.svg` for anything that must reach the
> PDF, and keep the two in step (see Revisions 2026-07-01).

```mermaid
flowchart LR
    CFG["<b>One run</b><br/>protocol · n validators · seed<br/>network timeline · adversary · workload"]

    subgraph HARNESS["Fixed harness — identical for every protocol"]
        direction TB
        SCH["<b>Scheduler</b><br/>virtual clock + event delivery"]
        SLOT["<b>Protocol logic</b><br/>PBFT · Casper FFG · Snowman<br/><i>(the only swappable part)</i>"]
        NET["<b>Network</b><br/>delay, loss, partition<br/><i>phase-varying · timing only</i>"]
        ADV["<b>Adversary</b><br/>per-node interceptor<br/>delay · silent · equivocation"]
        LOG["<b>Logger</b><br/>records decisions, halts, messages"]
        SCH --> SLOT
        SLOT --> NET
        SLOT --> ADV
        SLOT -.-> LOG
    end

    RED["<b>Normalise</b><br/>three decision types →<br/>one shared scale"]
    OUT["<b>One result row</b><br/>latency · throughput<br/>message overhead · reliability"]
    AGG["<b>Aggregate</b><br/>N seeds →<br/>aggregated mean row"]

    CFG --> HARNESS
    HARNESS --> RED
    RED --> OUT
    OUT -- "next seed / next cell" --> CFG
    OUT --> AGG

    classDef io fill:#eef6ff,stroke:#3366aa,color:#000
    classDef eng fill:#f4f4f4,stroke:#666,color:#000
    classDef proto fill:#eefaee,stroke:#557755,color:#000
    classDef red fill:#f3eefb,stroke:#7755aa,color:#000
    classDef agg fill:#fff4e6,stroke:#bb8833,color:#000
    class CFG,OUT io
    class RED red
    class SCH,NET,LOG eng
    class SLOT proto
    class ADV eng
    class AGG agg
```

## What this pins

**One config cell → one comparable data point.** The input is a single
cell of the experiment matrix plus a seed — protocol, validator count `n`,
network conditions, adversary, workload, seed. These are the independent
variables the research questions sweep ([[concepts/experiment-matrix]],
[[concepts/research-questions]]). The output is one row of `results.csv`.
The harness iterates this figure once per `(cell, seed)`.

**The engine is fixed — but that alone is not "fairness."** Builder,
Scheduler, Network and Logger are identical for every protocol, so any
difference in the results comes from the protocol logic, not the harness
(its RNG, scheduling, or network model). That *isolates* protocol
behaviour. Making three different decisions *comparable* is the separate
**reduce + reconcile** step, and that is where commensurability is
established — under stated conventions, not by the engine being shared
([[concepts/metric-reconciliation]]). §3.2 prose owns the conventions and
the caveats (task T36.3).

**Only the protocol-logic slot swaps.** The three protocols decide by
genuinely different rules and do not even produce the same *kind* of
decision (a PBFT block, an FFG checkpoint-plus-ancestors, a Snowman block).
The slot is drawn generic here; the per-protocol
control spines and decide rules live in
[[concepts/system-design-protocols]], and their atomic-commit-unit (ACU)
definitions in [[concepts/metric-reconciliation]].

**The adversary is a `Node`-local slot, not a layer.** It attaches to a
node and alters that node's outbound messages; its effect is
protocol-specific (there is no leader to disrupt in Snowman). Drawn as an
input knob for brevity; it lives inside the swappable region
([[concepts/adversary-model]], [[concepts/node-model]] §9).

**The Network models timing only.** Delay, loss and partitions — no CPU or
cryptographic cost. This is a stated threat to validity (it favours
signature-heavy protocols); §3.2 prose names it (T36.3).

**Metric reduction is harness-side.** The Scheduler never computes a
metric; the Logger's `decided` / `halted` / message events are reduced and
reconciled by the harness ([[concepts/simulation-design-runtime]] §2,
[[concepts/output-format]]). Rates are *not* uniformly per-ACU: overhead is
per ACU, throughput and time-to-finality are per transaction
([[concepts/evaluation-metrics]]).

## Cross-links

- The same run as a temporal sequence: [[diagrams/runtime/macro]].
- One turn of the Scheduler's run loop: [[diagrams/runtime/event-loop]].
- Per-protocol control spines and decide rules (the swappable slot):
  [[concepts/system-design-protocols]], [[diagrams/protocols/pbft]],
  [[diagrams/protocols/casper-ffg]], [[diagrams/protocols/snowman]],
  [[diagrams/protocols/narwhal-tusk]].
- Input axes and iteration: [[concepts/experiment-matrix]].
- Output schema and per-ACU normalisation:
  [[concepts/output-format]], [[concepts/metric-reconciliation]],
  [[concepts/evaluation-metrics]].
- Architecture prose and component table: [[concepts/system-design]] §2.

## Source

Authored for Chapter 3 §3.2 (2026-06-09), as the structural-architecture
companion to the macro sequence view, after a three-reviewer design pass.
The §3.2 prose obligations this figure defers (commensurability
conventions, no-compute-cost threat, FFG↔network coherence guard, workload
realism, scaling-range limit, Snowman rescaling validity, deadline-vs-
liveness detection, reliability-family definitions) are tracked as task
T36.3.

## Revisions

- **2026-06-19 — relaid-out for LaTeX (layout only, no content change).**
  The figure was a top-down column (`flowchart TD`, harness `direction TB`)
  with a ~1:3 aspect ratio (656×2028), which forced a dedicated full-page
  float (`\begin{figure}[p]` bounded by `height=0.92\textheight`) and left
  whitespace around it. Reflowed to a left-to-right macro pipeline
  (`flowchart LR`) with the harness components as an internal top-down spine
  (`direction TB`), giving a landscape ~2.4:1 render (PDF MediaBox 600×254).
  It now takes a plain `width=\linewidth` and sits inline. The component
  labels were rewrapped with `<br/>` to keep box widths bounded; node set,
  edges, classes, and wording are otherwise unchanged. `chapter3.tex`
  switched the float from a dedicated page (`[p]`, `height=0.92\textheight`)
  to inline placement (`[tbp]`, plain `width=\linewidth`).

- **2026-07-01 — replaced Mermaid render with a hand-authored SVG; dropped
  the "95% CI" wording from the figure (content).** The rendered figure is
  now `architecture.svg` → `architecture.pdf` (`cairosvg`, page 1080×780 pt,
  aspect ~1.39:1) rather than a Mermaid render; it adds a title, a colour
  legend, and three labelled zone containers (input / engine / output) but
  keeps the same node set and pipeline. Per an explicit human decision, the
  Aggregate box now reads **"N seeds → aggregated mean row"** (was "95% CI
  row") and the final-table caption reads "each metric reported as the mean
  across N seeds" (was "±95% confidence interval") — the aggregation step is
  retained (it is real: `src/output/aggregate.py`), only the statistical-
  reporting claim is dropped *from the diagram*. The CI method itself is
  unchanged and still owned by §3.5 prose (Student-t for continuous, Wilson
  for rate metrics) and relied on by Ch4 §4.4, so this is a figure-scoping
  change, not a methodology change. The Mermaid AGG node above was aligned to
  match. `chapter3.tex` include is unchanged (`[H]`, `width=\linewidth`);
  the new landscape aspect sits inline without a height cap. Font-family
  leads with `Arial Unicode MS` so `cairosvg` on macOS resolves the `→` and
  `①②③` glyphs (DejaVu Sans, the design font, is not installed locally).
