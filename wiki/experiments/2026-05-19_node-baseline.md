# Node baseline — T22

First runnable artifact of the validator abstraction: the shared-layer
`Node` ABC ([[concepts/node-model]]) driving a minimal end-to-end scenario
on the T21 scheduler. Not a protocol experiment — a build-verification
baseline confirming the shared lifecycle layer bootstraps, emits events,
and runs deterministically.

## Configuration

- Component under test: `src/nodes/` (abstract `Node`: lifecycle FSM,
  per-Node RNG, template-method inbound hooks, outbound-API placeholders,
  opaque adversary slot, `Message` envelope).
- Scenario: 2-node ping-pong. Two `PingPongNode`s with `budget=4`,
  bounced over a `LoopbackNetwork` with `LINK_DELAY=10.0`. Full six-phase
  bootstrap (simulation-design §7.2).
- Stubs: `PingPongNode` / `LoopbackNetwork` (real protocol FSMs are
  T28 / T32 / T38; real Network is T23).
- Seeds: `global_seed=42` — the harness seed; each `Node` derives its own
  RNG stream from it (node-model §8 determinism contract).
- Commit: 7ebe72a (the shared-layer `Node` + nodes-suite tests; the state
  at which this baseline is reproducible).

## Re-run

```
PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
```

## Result

The nodes suite runs 41 tests (including 3 end-to-end tests) to green;
the scheduler suite (40 tests) is unaffected. The ping-pong scenario
reaches quiescence at virtual time t=70.0, with `decided` and `halted`
events emitted. Two `global_seed`-identical runs produce byte-identical
event captures. Raw result: assertions in `tests/nodes/test_e2e.py` (no
CSV — pre-T40).

## Observation

The shared-layer `Node` drives a 2-node ping-pong through the full
six-phase bootstrap to `quiescence` at virtual time t=70; `decided` and
`halted` events emit as expected; two `global_seed`-identical runs produce
byte-identical event captures, so the §8 determinism contract holds. Note
the structural asymmetry: node 1 reaches `budget` first and halts, while
node 0 ends un-halted at budget-1 hops — exactly one node completes a full
`decided`→`halted` lifecycle. This is the intended build-verification
scope: the shared lifecycle layer is exercised end-to-end without a real
protocol FSM, which arrives with T28 / T32 / T38.

## Back-links

- [[concepts/node-model]] — the W3 design contract this build verifies.
- [[concepts/simulation-design]] — the discrete-event scheduler driving
  §6 inbound and providing §7 outbound.
