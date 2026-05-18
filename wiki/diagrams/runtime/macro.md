# Simulator Runtime — Macro View

> The whole simulator at one abstraction level above the T17 scheduler
> contract: from one experiment-cell YAML config to one row of
> `results.csv`. Six phases — init, workload, run loop, stop, flush,
> output. The `run loop` phase zooms into the five scheduler contract
> diagrams catalogued in [[diagrams/index]]; the bootstrap inside
> `build()` zooms into [[diagrams/scheduler/bootstrap]].
>
> Navigation entry point: [[diagrams/index]]. Owning page:
> [[concepts/system-design]] §3.

## Diagram

```swimlanes
title: Simulator runtime — one config cell to one results.csv row

order: Harness, Config, Builder, Simulator, Logger, Results
autonumber

note Harness, Results: **phase 1 — init**: resolve one experiment-matrix cell + seed

Harness -> Config: load(experiment.yaml)
Config --> Harness: `{protocol, n, network_phases, adversary, workload, seed}`
Harness => Builder: build(config)
note Builder: constructs Scheduler + Network + n Nodes, then runs the six-phase bootstrap (construct, register, bind, observability, kickoff, run)
Builder --> Harness: Simulator (Scheduler + Network + Nodes, wired)

note Harness, Simulator: **phase 2 — workload**: seed proposer mempools

Harness -> Simulator: load_workload(transactions)

=: phase 3 — run loop

Harness => Simulator: run(t_max, stop_when)
note Simulator: scheduler pops events; Nodes run protocol FSMs (pop, advance virtual time, dispatch, repeat)
...: {fas-spinner} virtual time advances event-to-event
Simulator -> Logger: emit(decided / halted / message events)

note Harness, Simulator: **phase 4 — stop**: one of three exit paths fires

Simulator => Harness: RunResult(stopped_by, now, events_processed)

note Harness, Results: **phase 5 — flush + reduce**

Harness -> Logger: flush()
Logger --> Harness: per-event records
Harness -> Harness: reduce events to metrics (latency, throughput, msg_count, success)

=: phase 6 — output

Harness => Results: append one row `{run_id, protocol, n, adversary, metrics...}`
```

## What this pins

**One config cell → one CSV row.** The diagram is the unit of work the
experiment harness ([[concepts/experiment-matrix]], T19) iterates. A
full experiment is this sequence run once per `(cell, seed)` pair; the
matrix page owns the iteration, this diagram owns one iteration's shape.

**`build()` collapses the T17 bootstrap.** Phase 1's `Builder.build()`
is the six-phase construct → register → bind → observability → kickoff
→ run setup from [[diagrams/scheduler/bootstrap]]. It is one step here
because the macro view's grain is the run, not the wiring.

**The run loop is a delay marker, not a step.** Phase 3 is a single
`run()` call; everything inside — pop, dispatch, protocol message
exchange — is the T17 contract set ([[diagrams/scheduler/event-dispatch]]
and the rest of the [[diagrams/index]] scheduler diagrams). The
`{fas-spinner}` delay marker stands for "thousands of events processed."

**Logging is a side channel, not a return path.** Nodes `emit` events
to the Logger throughout the run (the `event_sink` of
[[concepts/simulation-design]] §4); the Logger is read only in phase 5.
The `RunResult` (phase 4) plus the flushed event stream (phase 5) are
the harness's complete picture of the run — exactly what T40 needs.

**Metric reduction is harness-side, not scheduler-side.** Phase 5's
`reduce` step is where raw `decided` / `halted` / message events become
the latency / throughput / message-count columns. The scheduler never
computes a metric ([[diagrams/scheduler/constraints]]); the harness does.

**Three stop paths feed one column.** `RunResult.stopped_by ∈
{quiescence, deadline, predicate}` is carried into the CSV row so a
failed (deadline) run is distinguishable from a completed (predicate)
or natural-end (quiescence) run.

## Cross-links

- Bootstrap inside `build()`: [[diagrams/scheduler/bootstrap]].
- The run loop interior: [[diagrams/scheduler/event-dispatch]] and the
  rest of the scheduler set under [[diagrams/index]].
- Per-protocol message exchange inside the run loop:
  [[diagrams/protocols/pbft]], [[diagrams/protocols/casper-ffg]],
  [[diagrams/protocols/snowman]], [[diagrams/protocols/narwhal-tusk]].
- Owning page and architecture prose: [[concepts/system-design]].
- Config cell and iteration: [[concepts/experiment-matrix]] (T19).
- `RunResult` and the run loop API: [[concepts/simulation-design]] §6.

## Source

Authored as part of T20 ([[concepts/system-design]]).

## Revisions

None.
