# PBFT proposal baseline — T28

First end-to-end run of the PBFT pre-prepare phase across the W3 stack:
the discrete-event scheduler ([[concepts/simulation-design]], T21), the
shared-layer `Node` ([[concepts/node-model]], T22), the honest `Network`
(T23), the event-log subsystem (T24), and the config/factory layer (T27),
all wired together and driven by a `PBFTNode` validator. Not a protocol
experiment — a build-verification baseline. It confirms the pre-prepare
phase reaches a self-consistent `PRE_PREPARED` state and that the T28/T29
cut at the `IDLE → PRE_PREPARED` transition holds: voting (PREPARE/COMMIT),
finalisation, and view-change are T29 work, and this run verifies none of
that machinery has been wired prematurely.

## Configuration

- Code under test: `src/pbft/` (the new PBFT package). T28 modified no
  upstream `src/` — only new files were added. Commit `957ca44`.
- Two scenarios, otherwise identical config:
  - *Scenario A* — `n = 4` (`3f+1`, `f = 1`); workload `[b"A", b"B", b"C"]`
    placed on node 0 only.
  - *Scenario B* — `n = 7` (`f = 2`); workload `[b"X"]` placed on node 0
    only.
- `propose_delay = 1.0`; `initial_view = 0`.
- Network: a single phase `[0, ∞)`, constant delay `1e-9`, drop rate 0, no
  partitions. The delay is `1e-9` rather than a literal zero because the
  network model enforces `t_delivered > t_sent` — a strictly positive
  delivery time — so a zero delay is unrepresentable; `1e-9` is the model's
  minimum.
- `global_seed = 42`.

## Re-run

```
PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_proposal -v
PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v
```

The first command runs the 12-test T28 integration suite; the second runs
the 38-test `src/pbft/` unit suite. As a convenience `make test-integration`
runs the whole `tests/integration/` directory (39 tests including the 12
T28 tests); the raw commands above are the authoritative re-run path.

## Result

The T28 integration suite runs 12 tests to green; the `src/pbft/` unit
suite 38. Upstream suites are unaffected — event_log 30, network 62,
scheduler 46, nodes 46, config 39.

- **Scenario A (n = 4).** The run reaches quiescence. 12
  `pbft_pre_prepared` events fire — 4 nodes × 3 sequence numbers: 3 from
  the primary's self-loop, 9 from deliveries. 0 `pbft_rejected`. 9
  `PRE-PREPARE` deliveries; 0 voting-message deliveries. Emitted digests
  match `blake2b` of the workload. Two seed-identical runs produce
  byte-identical event-record streams.
- **Scenario B (n = 7).** The run reaches quiescence. 7 `pbft_pre_prepared`
  events; 0 `pbft_rejected`; 6 `PRE-PREPARE` deliveries; determinism holds
  byte-identically.

No CSV is persisted — CSV export is pre-T40 work; results are observed
through the in-test `EventLogger`.

## Observation

The pre-prepare phase composes across the W3 stack: a `PBFTNode` primary
drains its stub workload, broadcasts `PRE-PREPARE` over the real honest
`Network`, and recipients validate and transition to `PRE_PREPARED`, with
the run halting at quiescence under a reproducible `RunResult`. The primary's
self-loop produces exactly one `pbft_pre_prepared` per `seq`: the `Network`
broadcast excludes the sender, so the primary's own transition to
`PRE_PREPARED` is an explicit in-process self-transition, not a delivery.
This is why the n = 4 count is 12 (3 self + 9 delivered) and the n = 7
count is 7 (1 self + 6 delivered). Zero voting-message deliveries confirm
the skeleton-cut holds — the FSM declares `PREPARED` and `COMMITTED` but
T28 wires no transition into them. The T28/T29 cut sits at
`_accept_pre_prepare`: T29 can grow the FSM (the `PREPARED`/`COMMITTED`
transitions, quorum counting, view-change) without upstream rework.

## Back-links

- [[algorithms/pbft]] — the protocol whose pre-prepare phase this run
  verifies; the five `PRE-PREPARE` validation rules under test.
- [[concepts/message-types]] — the `PRE-PREPARE` message and the
  voting-message vocabulary the skeleton-cut leaves unwired.
- [[concepts/system-design-protocols]] — the protocol-FSM contract the
  `PBFTNode` validator implements.
- [[concepts/node-model]] — the shared-layer `Node` the `PBFTNode`
  subclasses; the broadcast / event-emission API exercised.
- [[concepts/simulation-design]] — the discrete-event scheduler and the
  six-phase bootstrap this run drives to quiescence.
