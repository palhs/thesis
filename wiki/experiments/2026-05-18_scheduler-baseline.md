# Scheduler baseline — T21

First runnable artifact of the simulator: the discrete-event scheduler
([[concepts/simulation-design]]) executing a minimal end-to-end scenario.
Not a protocol experiment — a build-verification baseline confirming the
scheduler drives a simulation correctly and deterministically.

## Configuration

- Component under test: `src/scheduler/` (`Scheduler`, `RunResult`,
  `Delivery` / `TimerFire` / `PhaseAdvance`).
- Scenario: 2-node ping-pong. Node 0 sets a 5 ms kickoff timer, broadcasts
  `PING`; node 1 echoes `PONG`. Fixed 10 ms link delay; one `PhaseAdvance`
  at 20 ms. Full six-phase bootstrap (simulation-design §7.2).
- Stubs: `EchoNode` / `LoopbackNetwork` (real Node / Network are T22 / T23).
- Seeds: none — the scheduler holds no RNG; determinism is structural
  (unique heap key `(t, node_id, seq)`).
- Commit: d4fff60 (the scheduler + end-to-end test; the state at which this baseline is reproducible).

## Re-run

```
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
```

## Result

`run()` processes 4 events to quiescence at virtual time 25.0 ms, 0
tombstoned. Two fresh runs of the scenario produce byte-identical
`event_sink` streams. Raw result: assertions in
`tests/scheduler/test_e2e.py` (no CSV — pre-T40).

## Observation

The scheduler drives a complete bootstrap-to-quiescence simulation with
the expected event ordering, and the determinism contract holds for a
non-trivial multi-node scenario. Two spec gaps surfaced and were resolved
during implementation — see [[concepts/simulation-design]] §9 Revisions
R1 (dispatch references) and R2 (`schedule()` returns `seq`).
