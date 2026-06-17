# Simulator Architecture — One Engine, Any Protocol

> The static picture of the simulator for Chapter 3 §3.2: what the system
> is made of, what goes in, what comes out, and where the four protocols
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

```mermaid
flowchart TD
    IN["<b>INPUT — one experiment-matrix cell + seed</b><br/>protocol · n = 4 to 25 validators<br/>network conditions: delay, loss, partitions (configure the NETWORK below)<br/>adversary (behaviour + strength) · workload (transactions) · seed"]

    subgraph HARNESS["THE HARNESS — identical for every protocol; only the protocol logic is swapped"]
        direction TB
        HB["<b>BUILDER</b> — assembles the system and loads the workload"]
        SCH["<b>SCHEDULER</b> — the single run loop and virtual clock<br/><i>one turn of this loop is the event-loop figure</i>"]
        SLOT["<b>PROTOCOL LOGIC</b> — the only swappable part<br/>a state machine for one of the four protocols"]
        NET["<b>NETWORK</b> — delivers messages with delay, loss and partitions<br/>(models timing only — no CPU or signature cost)"]
        LOG["<b>LOGGER</b> — records what happened: decided, halted, messages"]
        HB --- SCH
        SCH --- SLOT
        SLOT --- NET
        SLOT -. "results &amp; messages" .-> LOG
    end

    RED["<b>REDUCE + RECONCILE</b><br/>the four emit different kinds of decision — put them on one common scale<br/>(per ACU for overhead · split Narwhal's two layers · rescale Snowman)"]
    OUT["<b>OUTPUT — one row of results.csv (one comparable data point)</b><br/>time-to-finality &amp; throughput (per transaction)<br/>message &amp; byte overhead (per ACU; mempool / consensus split for the DAG)<br/>reliability: agreement · safety · liveness (defined with the metrics) · run outcome"]
    RQ["comparison plots that answer the research questions (§3.1)"]

    IN -- "build + load workload" --> HARNESS
    HARNESS -- "flush events" --> RED
    RED --> OUT
    OUT --> RQ

    classDef io fill:#eef6ff,stroke:#3366aa,color:#000
    classDef eng fill:#f4f4f4,stroke:#666,color:#000
    classDef proto fill:#eefaee,stroke:#557755,color:#000
    classDef red fill:#f3eefb,stroke:#7755aa,color:#000
    classDef rq fill:#fff4e6,stroke:#bb8833,color:#000
    class IN,OUT io
    class RED red
    class RQ rq
    class HB,SCH,NET,LOG eng
    class SLOT proto
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
behaviour. Making four different decisions *comparable* is the separate
**reduce + reconcile** step, and that is where commensurability is
established — under stated conventions, not by the engine being shared
([[concepts/metric-reconciliation]]). §3.2 prose owns the conventions and
the caveats (task T36.3).

**Only the protocol-logic slot swaps.** The four protocols decide by
genuinely different rules and do not even produce the same *kind* of
decision (a PBFT block, an FFG checkpoint-plus-ancestors, a Snowman block,
a Narwhal anchor-batch). The slot is drawn generic here; the per-protocol
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

None.
