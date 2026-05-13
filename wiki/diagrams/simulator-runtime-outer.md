# Simulator Runtime — Outer View

> One experiment run, end to end. Answers: *from `python run.py
> config.yaml` to one row in `results.csv`, what calls what, in what
> order?* The full survey is many of these runs — the outer matrix loop
> is described at the bottom of this page.
>
> Companion: [[diagrams/simulator-runtime-tick]] zooms into one event
> tick — the loop that runs millions of times inside Phase 3 below.
> Both diagrams live in `wiki/diagrams/`; navigation entry point is
> [[diagrams/index]].

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant H as Harness
    participant C as Config
    participant S as Scheduler
    participant N as Network
    participant V as Validator(s)
    participant F as Protocol FSM
    participant L as Logger

    Note over H,L: Phase 1 — INIT
    H->>C: load(config.yaml)
    C-->>H: cfg + seed
    H->>S: new Scheduler(seed)
    H->>N: new Network(cfg.delay, cfg.loss, seed)
    H->>V: new Validator(id, weight) ×N
    V->>F: attach Protocol FSM
    Note right of V: Adversary hook attached here<br/>to Byzantine subset (hidden;<br/>see node-model.md §7)
    H->>L: register four log streams

    Note over H,L: Phase 2 — WORKLOAD START
    H->>S: schedule tx_submit events at rate r

    Note over H,L: Phase 3 — RUN LOOP (repeats O(10^6) times)
    loop until stop condition
        S->>S: pop next event, advance clock
        S->>V: deliver(msg) or fire_timer()
        V->>F: handle(event)
        F-->>V: actions (send / broadcast / set_timer / emit)
        V->>N: send(to, msg)
        N->>S: schedule deliver(to, msg, t+delay)
        V->>S: set_timer(t+Δ)
        V->>L: emit(event)
    end

    Note over H,L: Phase 4 — STOP
    S->>V: halt(reason = run_end)

    Note over H,L: Phase 5 — FLUSH
    L-->>H: per-tx, per-block, per-round, per-validator streams

    Note over H,L: Phase 6 — OUTPUT
    H->>H: derive metrics per evaluation-metrics.md
    H->>H: append CSV row per metric-reconciliation.md §T40
```

## Lifelines

The eight roles in the diagram, each tied to the wiki page that owns
the contract. Forward wikilinks (T17, T18, T19, T27, T40) resolve when
those tasks land.

| Lifeline | Role | Owner |
| :-- | :-- | :-- |
| **Harness** | Top-level runner. Drives the matrix, writes CSV. | T19 + T40 (forward) |
| **Config** | YAML knobs + RNG seed. | T27 → [[concepts/reproducibility]] (forward) |
| **Scheduler** | Event queue + model clock. Single source of "what happens next". | T17 → [[concepts/simulation-design]] (forward) |
| **Network** | Delivers messages with delay / drop / partition. | [[concepts/network-model]], [[concepts/network-model-phases]] |
| **Validator** | One per node. Identity, lifecycle, outbound API. | [[concepts/node-model]] |
| **Protocol FSM** | Per-protocol state machine inside the Validator. | [[algorithms/pbft]] · [[algorithms/pos]] · [[algorithms/avalanche]] · [[algorithms/dag-based]] · [[concepts/message-types]] |
| **Logger** | Four log streams per [[concepts/evaluation-metrics#simulator-instrumentation]]. | T24 (forward) |
| **Adversary** *(not drawn)* | Init-time attachment on the Validator outbound API. Distorts `send` / `broadcast` / `set_timer` / `emit` in place. | T18 → [[concepts/adversary-model]] (forward) |

## The six phases

### 1. Init (steps 1–6 in the diagram)

Harness reads `config.yaml` plus a seed. With those, it materialises
the Scheduler, the Network, N Validators (each with its Protocol FSM),
and the Logger sinks. The Adversary hook is wrapped around the
outbound API of every Validator in the Byzantine subset specified by
`cfg.byzantine_fraction` — that subset is fixed at init and does not
change during the run.

The Adversary is not drawn as a lifeline. It is an *attachment*, not
a peer (per [[concepts/node-model]] §"T18 adversary attachment
surface"). When you see a compromised Validator misbehave during
Phase 3, the Adversary is the reason — it lives inside that
Validator's outbound calls.

### 2. Workload start (step 7)

A workload generator (folded into Harness at this zoom) schedules
`tx_submit` events into the Scheduler at the configured offered-load
rate. From step 8 onward the simulator clock advances.

### 3. Run loop (steps 8–14, repeated)

The dense part. Drill down: [[diagrams/simulator-runtime-tick]].

Key property: **all time flows through the Scheduler.** No model
advances its own clock; the Validator and Network only schedule
*future* events. This is what makes the simulator deterministic for a
given seed — the seed pins event ordering, delay sampling, and any
per-Validator randomness.

### 4. Stop (step 15)

The Scheduler hits the configured stop condition (`max_time`,
`max_committed_blocks`, or `max_rounds` — set in Config). It issues
a `halt(reason = run_end)` to every Validator; each transitions to
`halted{run_end}` per [[concepts/node-model]] §"Shared lifecycle".

### 5. Flush (step 16)

The Logger releases its four streams to the Harness:

- per-tx timestamp log → latency, time-to-finality, goodput
- per-block message-count + byte-size log → messages per block, bytes per block, peak throughput
- per-round event log → view changes, reorgs, safety-check failures
- per-validator state-size sample → per-validator state size

The contract is in [[concepts/evaluation-metrics#simulator-instrumentation]].

### 6. Output (steps 17–18)

The Harness derives the metric schema from the streams and writes one
CSV row whose columns are pinned by
[[concepts/metric-reconciliation#t40-csv-schema-implications]]. One
row = one (cell, seed) combination.

## What this picture pins

- **The Validator outbound API is the seam.** `send`, `broadcast`,
  `set_timer`, `emit` are the only ways a Validator affects the world.
  Adversary strategies (silent / delayed / equivocator / dropper from
  RQ4) all reduce to overrides on these four calls.
- **Two RNG streams.** Network samples delay/drop from a
  network-scoped RNG; Validators use per-`NodeId` RNGs for sampling
  (Snowman) and leader rotation. Both seeded deterministically by
  Config. Pinned in [[concepts/network-model-phases]] for the network
  half and [[concepts/node-model]] §"Determinism" for the Validator
  half.
- **No retries, no application-layer guarantees.** The Network is
  at-most-once; reliability is the protocol's job, not the
  infrastructure's. This is what makes the simulator a fair test of
  protocol resilience.

## From one run to the whole survey

The diagram above is one row of `results.csv`. The survey is the
matrix — one extra outer loop covers it.

```
for cell in T19_matrix:                   # delay × adversary × n × workload
    for seed in cell.seeds:               # 10–30 per cell, per T44
        run(config=cell, seed=seed)       # ← the diagram above
        append row to CSV
aggregate → plots → drafts/ch4_results.md
```

T19 (experiment matrix) defines the cells; T44 defines the seed count
per cell. Both are Not Started in `TASKS.md` — the outer-loop shape
above is correct, but specific cell counts fill in when those tasks
land.

## Source

Drafted as scaffolding for T17 ([[concepts/simulation-design]],
Not Started). The diagram is the centerpiece T17 will absorb when it
picks up — for now it lives standalone in `wiki/diagrams/` and is
discovered via [[diagrams/index]]. No `wiki/log.md` entry and no
`TASKS.md` status change at this stage.

## Revisions

None.
