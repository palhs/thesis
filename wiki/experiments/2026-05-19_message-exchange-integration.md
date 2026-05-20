# Message-exchange integration — T25

First cross-component integration test of the W4 simulator skeleton: the
discrete-event scheduler ([[concepts/simulation-design]], T21), the
shared-layer `Node` ([[concepts/node-model]], T22), and the honest
`Network` ([[concepts/network-model]] / [[concepts/network-model-phases]],
T23) wired together and driven by 4/7/10-node scenarios. The
per-subsystem suites each drive only a 2-node ping-pong; this is the first
test exercising the three subsystems jointly above the minimum BFT
committee size. Not a protocol experiment — a build-verification baseline
confirming message exchange, the delay-distribution contract, and the
scheduler's dispatch-ordering contract hold end-to-end.

## Configuration

- Components under test: `src/scheduler/`, `src/nodes/`, `src/network/`
  (no changes to any — T25 adds test code only).
- Node counts: `n ∈ {4, 7, 10}` for message exchange and dispatch
  ordering. `n = 4` is the minimum BFT committee (`3f+1`, `f = 1`); 7 and
  10 confirm broadcast fan-out and determinism hold as the validator set
  grows. The delay-distribution check runs at a single `n = 7` — delay
  sampling is per-message and `n`-independent, so sweeping `n` there would
  re-test identical RNG code (node-sweep decision, human, 2026-05-19).
- Scenarios:
  - *Message exchange* — `n` `BroadcastNode`s; each broadcasts one `TOKEN`
    on start, no re-broadcast. One round of `n*(n-1)` deliveries, then
    quiescence.
  - *Delay distribution* — the `n = 7` broadcast scenario over 60 seeds,
    `uniform(low=100, high=500)` delay; 2,520 pooled end-to-end delay
    samples.
  - *Dispatch ordering* — `n` `TimerNode`s, each submitting three timers
    in non-canonical order (LATE at t=200 before two EARLY at t=100),
    nodes started in reverse id order.
- Stubs: `BroadcastNode`, `TimerNode` (`tests/integration/_helpers.py`) —
  minimal `Node` subclasses standing in for real protocol FSMs
  (PBFT = T28, etc.). The real `Scheduler` and `Network` are used.
- Seeds: message exchange / ordering `global_seed = 42` (and `7` for the
  seed-divergence check); delay distribution pools `global_seed ∈ 0..59`.
- Commit: `src/` under test at `1606dfe`; the T25 integration suite
  itself lands in this task's review commit.

## Re-run

```
make test-integration      # the T25 suite (11 tests)
make test                  # full regression — all five suites
```

## Result

The integration suite runs 11 tests to green; the upstream scheduler (40),
nodes (41), network (57), and event_log (23) suites are unaffected — 172
tests total.

- **Message exchange.** At `n = 4, 7, 10` every node receives exactly one
  `TOKEN` from every peer; `events_processed == n*(n-1)`; the run reaches
  `quiescence`. A seed-identical re-run reproduces byte-identically across
  the *full* `RunResult` (`stopped_by`, `now`, `events_processed`,
  `events_tombstoned`) and the delivery stream; two distinct seeds produce
  distinct delivery timings under a stochastic delay.
- **Delay distribution.** Over 2,520 pooled samples the observed
  end-to-end delay has mean 296.81 ms (configured uniform mean 300) and
  population standard deviation 115.98 ms (configured 115.47); every
  sample lies in `[100, 500]`. The configured distribution's shape is
  recovered, not merely its bounds.
- **Dispatch ordering.** Under deliberately scrambled submission (LATE
  timer submitted first, nodes started in reverse id order) the scheduler
  dispatches in canonical `(t, node_id, seq)` order: handlers fire
  t-major, then node_id, then per-Node `seq`; the dispatch-key stream is
  strictly increasing; handler-observed order matches dispatch order.

Raw result: assertions in `tests/integration/test_message_exchange.py`,
`test_delay_distribution.py`, `test_ordering.py` (no CSV — pre-T40).

## Observation

The three W4 subsystems compose: a 4/7/10-node scenario bootstraps through
the six-phase sequence (simulation-design §7.2), exchanges messages over
the real honest `Network`, and halts at quiescence with a reproducible
`RunResult`. Two contracts the per-subsystem suites could not fully
exercise are now closed. First, the delay-distribution check moves beyond
"a random delay was drawn" (network e2e) and "samples stay in bounds"
(delay-dist unit) to "the observed mean and spread match the configured
`uniform`" — the [[concepts/network-model-phases]] §2 distribution
contract verified at the integration level. Second, the dispatch-ordering
check feeds the scheduler events in scrambled submission order and
confirms it still imposes the [[concepts/simulation-design]] §3
`(t, node_id, seq)` order — answering the open question of whether the
network e2e determinism test proved ordering or merely scenario replay
(it proved replay; this proves ordering). Bernoulli drop and partition
are not exercised here — they are honest-network features verified at the
unit level (`tests/network/`) — and no protocol FSM is involved; that
arrives with T28 / T32 / T38. This is the intended build-verification
scope for the simulator skeleton.

## Back-links

- [[concepts/simulation-design]] — the discrete-event scheduler and the
  `(t, node_id, seq)` dispatch order this test exercises under scrambled
  submission.
- [[concepts/node-model]] — the shared-layer `Node` the test doubles
  subclass; the outbound `broadcast` / `set_timer` API under test.
- [[concepts/network-model]] — the honest delivery layer carrying the
  4/7/10-node message exchange.
- [[concepts/network-model-phases]] — §2 delay-distribution contract
  verified by the distribution check; §6.4 determinism contract hardened
  to a full-`RunResult` comparison.
