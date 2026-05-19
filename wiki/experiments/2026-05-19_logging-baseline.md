# Logging baseline — T24

First runnable artifact of the structured event-logging subsystem: the
`EventLogger` ([[concepts/event-log-schema]]) wired as `Scheduler.event_sink`
over a real 2-node run. Not a protocol experiment — a build-verification
baseline confirming the logger captures both `event_sink` payload shapes,
exports a well-formed CSV, and preserves the determinism contract.

## Configuration

- Component under test: `src/event_log/` (`EventLogger`, `EventRecord`, the
  `event_types.py` constant vocabulary).
- Scenario: 2-node ping-pong (`tests/event_log/test_e2e.py`). Two
  `PingPongNode`s with `budget=4` bounce a token over the **real** `Network`
  ([[concepts/network-model]]) through the full six-phase bootstrap
  ([[concepts/simulation-design]] §7.2). The logger is wired as
  `scheduler.event_sink = logger.sink` at bootstrap phase 4.
- Network: a single infinite phase, `DelayDist("constant", {"delay": 10.0})`
  — every link delivers after 10.0 of virtual time, no drop, no partition.
- Seeds: `global_seed=42` — the harness seed; each `Node` and the `Network`
  derive their own RNG streams from it.
- Commit: `2ffca38` — the state at which this baseline is reproducible
  (`src/event_log/`, the `node.py` constant adoption, and the event_log
  test suite all present).

## Re-run

```
PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v
PYTHONPATH=src:tests/event_log python3 -m unittest test_logger -v
PYTHONPATH=src:tests/event_log python3 -m unittest test_e2e -v
```

## Raw result location

None persisted. The e2e test writes its CSV to a `tempfile.TemporaryDirectory`
and asserts against it in-process — the logger buffers records in memory and
exports only on an explicit `to_csv` call (event-log-schema design Decision B).
No CSV is committed to `results/`; the persisted-output harness is T27 / T41.

## Observation

The event_log suite runs 23 tests to green (3 `test_event_types`, 16
`test_logger`, 4 `test_e2e`); the `node.py` constant adoption left the
regression suites unchanged (`tests/nodes` 41, `tests/scheduler` 40). The
e2e run reaches `quiescence` and the logger captures records spanning both
`event_sink` shapes — emit events (`decided`, `halted`) and transport events
(`delivery`). `to_csv` produces a well-formed file: header
`t,node_id,event_type,seq,fields` plus one row per buffered record. Two
`global_seed`-identical full runs produce byte-identical CSV, so the
determinism contract ([[concepts/node-model]] §8) holds end-to-end: the
logger appends in dispatch order and serialises `fields` with sorted keys,
introducing no order of its own.

## Decision E note

The subsystem is `src/event_log/`, not the `TASKS.md` T24 entry's literal
`src/logging/`. With `src` on `PYTHONPATH` (the project test convention),
every directory beneath `src/` is a *top-level* package; a `src/logging/`
directory would import as `logging` and shadow the standard-library `logging`
module for the whole process. The deviation is documented per
`docs/workflow.md` § Evolution and flagged in the T24 handoff summary.

## Back-links

- [[concepts/event-log-schema]] — the design contract this build verifies.
- [[concepts/simulation-design]] — the `Scheduler` and `event_sink` seam the
  logger consumes.
- [[concepts/node-model]] — the `Node.emit` API producing the emit-shape
  events and the §8 determinism contract.
