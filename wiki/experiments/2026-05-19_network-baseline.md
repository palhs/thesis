# Network baseline — T23

First runnable artifact of the delivery layer: the `Network`
([[concepts/network-model]] / [[concepts/network-model-phases]]) driving a
2-node ping-pong on the T21 scheduler and T22 nodes. Not a protocol
experiment — a build-verification baseline confirming the honest delivery
layer bootstraps, injects delay, and runs deterministically.

## Configuration

- Component under test: `src/network/` (the `Network` class: phase
  timeline, five delay distributions, Bernoulli drop, partition predicate,
  network-scoped `blake2b`-seeded RNG).
- Scenario: 2-node ping-pong. Two `PingPongNode`s with `budget=4`, bounced
  over the real `Network` with a single phase `[0, ∞)` carrying
  `DelayDist("constant", {"delay": 10.0})`. Full six-phase bootstrap
  (simulation-design §7.2).
- Stubs: `PingPongNode` only (real protocol FSMs are T28 / T32 / T38). The
  `LoopbackNetwork` stub used by the T22 baseline is now replaced by the
  real `Network`.
- Seeds: `global_seed=42` — the harness seed; the `Network` derives its own
  RNG stream from it (network-model-phases §6 determinism contract).
- Commit: 552e579 (the `src/network/` delivery layer + network-suite tests;
  the state at which this baseline is reproducible).

## Re-run

```
PYTHONPATH=src:tests/network python3 -m unittest discover -s tests/network -v
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v
```

## Result

The network suite runs 57 tests (including 5 end-to-end tests) to green;
the upstream scheduler and nodes suites are unaffected. The ping-pong
scenario reaches quiescence at virtual time t=70.0. Every delivery shows
the constant 10 ms delay (`t_delivered − t_sent == 10.0`). Two
`global_seed`-identical runs produce byte-identical delivery streams. Raw
result: assertions in `tests/network/test_e2e.py` (no CSV — pre-T40).

## Observation

The real `Network` replaces the `LoopbackNetwork` stub end-to-end: it
drives a 2-node ping-pong through the full six-phase bootstrap to
`quiescence` at virtual time t=70, with the constant 10 ms delay injected
on every hop. Delay injection and the network-level determinism contract
(`network-model-phases.md §6.4`) hold end-to-end — two
`global_seed`-identical runs produce byte-identical delivery streams.
Bernoulli drop and the partition predicate are not exercised by this
baseline scenario; they are verified at the unit level
(`tests/network/test_network.py`). Phase rollover via the `_phase_idx`
pointer works under a real
scheduler run: the multi-phase e2e test crosses an interior boundary
mid-run and observes both phases' delay distributions. This is the intended
build-verification scope: the honest delivery layer is exercised end-to-end
without a real protocol FSM, which arrives with T28 / T32 / T38.

## Back-links

- [[concepts/network-model]] — the W3 design contract this build verifies.
- [[concepts/network-model-phases]] — the phase timeline, delay
  distributions, and §6 determinism contract.
- [[concepts/simulation-design]] — the discrete-event scheduler driving
  delivery and the six-phase bootstrap.
