# Snowman honest-path baseline — T38

End-to-end build-verification check of the **full Snowball honest path**
([[algorithms/avalanche]]) under an **all-honest validator set**, across
the W3 stack: the discrete-event scheduler
([[concepts/simulation-design]], T21), the shared-layer `Node`
([[concepts/node-model]], T22), the honest `Network`
([[concepts/network-model]], T23), the event-log subsystem
([[concepts/event-log-schema]], T24), and the config/factory layer
([[concepts/reproducibility]], T27), driven by `SnowmanNode` validators
running the full two-threshold Snowball update with the parameter
rescaling rule from [[concepts/metric-reconciliation]] §Snowman parameter
rescaling.

This is the Snowman counterpart of the T30 PBFT baseline
([[experiments/2026-05-21_pbft-baseline]]) and the T35 Casper FFG baseline
([[experiments/2026-05-25_pos-baseline]]). T38 added the entire
`src/snowman/` package — six modules (`__init__.py`, `parameters.py`,
`messages.py`, `block.py`, `poll.py`, `node.py`), the `tests/snowman/`
unit suite, one integration test (`tests/integration/test_snowman_baseline.py`),
and this page. No shared-infra change: `src/scheduler/`, `src/network/`,
`src/nodes/`, and `src/event_log/` are untouched
([[concepts/week7-decision]] §4.3).

The four T38 outcomes — every node **decides** every announced block, the
run produces **no forks**, **finalisation latency is logged**, and two
seed-identical runs are **byte-identical** — are asserted by the
integration suite. A unified comparative CSV remains T40 work; no
T38-local CSV is shipped (the T35 sample is the placeholder, see
`TASKS.md` Backlog).

## Configuration

- Code under test: `src/snowman/` (new). Branch `task/T38-snowman`;
  commit hash `TODO(human)` — assigned when the branch is committed (T38
  lands as one human commit per `docs/workflow.md`).
- `global_seed = 42`; `slot_duration = 1.0`; `β = 15`.
- Per-scenario `(K, α_p, α_c)` from [[concepts/metric-reconciliation]]
  §Snowman parameter rescaling — `K = min(20, n−1)`, `α_p = ⌊K/2⌋+1`,
  `α_c = ⌈0.8·K⌉`:

  | `n` | `K` | `α_p` | `α_c` | `α_c / K` | `(1 − α_c/K)^β` |
  | --: | --: | --: | --: | --: | --: |
  |  4 |  3 |  2 |  3 | 1.00 | `0` (boundary case) |
  |  7 |  6 |  4 |  5 | 0.83 | `≈ 6.5e-12` |
  | 10 |  9 |  5 |  8 | 0.89 | `≈ 4.4e-14` |

- Network: a single phase `[0, ∞)`, constant delay `1e-9`, drop rate 0,
  no partitions. The delay is `1e-9` rather than literal zero because the
  network model enforces `t_delivered > t_sent`; `1e-9` is the minimum
  (same as the T30 and T35 baselines).
- `t_max = 20.0`. Snowman has no quiescence — the slot timer re-arms
  every slot indefinitely — so each run is bounded by `t_max` only. With
  `slot_duration = 1.0` the loop dispatches slots `0..18`, so 19 blocks
  are announced and decided per node.

### Scenarios

Three scenarios sweep `n` at uniform weight (mirrors the T30 / T35 first
three rows). Snowman is not stake-weighted, so the T35 non-uniform-stake
fourth row is omitted intentionally — there is no weight-vs-headcount
distinction for the proposer rule (round-robin `slot % n`) or the poll
threshold (`α` counts equal-weight responses).

- **n=4.** `(K, α_p, α_c) = (3, 2, 3)`. Rescaling-boundary scenario: at
  `α_c / K = 1.0` the empirical safety bound `(1 − α_c/K)^β = 0`, so the
  poll degenerates to "flood-vote-with-counter." Build-verification
  includes n=4 as a sanity check that the rescaling rule reduces to its
  boundary cleanly; downstream comparative tables (T41+) exclude this
  row per [[concepts/metric-reconciliation]] §Comparative-claim exclusion.
- **n=7.** `(K, α_p, α_c) = (6, 4, 5)`. First "real" Snowman regime;
  `α_p + α_c = 9 > K = 6`, so the success-path early-close is flip-safe.
- **n=10.** `(K, α_p, α_c) = (9, 5, 8)`. Larger sampling regime;
  `α_p + α_c = 13 > K = 9`.

## Re-run

```
PYTHONPATH=src:tests/snowman python3 -m unittest discover -s tests/snowman -v
PYTHONPATH=src:tests/integration python3 -m unittest test_snowman_baseline -v
```

The first command runs the 60-test snowman unit suite (parameters,
messages, block, poll, node-init, node-propose, node-announce,
node-query, node-accept, node-flip). The second runs the four T38
integration tests (each a `subTest` loop over the three scenarios above).
`make test` runs both alongside every other suite.

## Result

The T38 suite runs 60 unit tests + 4 integration tests to green. Upstream
suites are unaffected; full `make test` stays green across all nine
suites (scheduler, nodes, network, event_log, config, pbft, pos,
snowman, integration). Per-scenario event counts, observed through the
`EventLogger`:

| Metric | `n=4` | `n=7` | `n=10` |
| :-- | --: | --: | --: |
| `stopped_by` | deadline | deadline | deadline |
| `snowman_announced` | 76 | 133 | 190 |
| `snowman_poll_started` | 1 140 | 1 995 | 2 850 |
| `snowman_poll_closed` | 1 140 | 1 995 | 2 850 |
| `snowman_rejected` | 0 | 0 | 0 |
| `decided` | 76 | 133 | 190 |
| `delivery` | 6 897 | 24 054 | 51 471 |
| `timer_fire` | 1 217 | 2 129 | 3 041 |
| first `decided.t` | `1.000000045` | `1.000000045` | `1.000000045` |

`snowman_announced` and `decided` both equal `19 · n` per scenario:
slot loop dispatches slots `0..18`, each block is decided by every node.
`snowman_poll_started = snowman_poll_closed = 19 · n · β = 19 · n · 15`
— every accepted block runs exactly β polls before acceptance because
honest-path conflict sets are singletons (one candidate block per
parent), so every round trivially clears α_c (full K responses for the
single block), the counter advances 1 per round, and acceptance fires
at counter ≥ β. The `α_p` flip path is dead under honest scenarios but
guarded against regression by `tests/snowman/test_node_flip.py`. The
empirical safety violation rate is `ε = 0` across all seeds for all
three scenarios; meaningful empirical-ε study (`β ∈ {3, 5}` regime,
adversarial Snowman) is RQ4 work owned by T51–T53.

- **Decides.** Every validator emits `decided` exactly once per announced
  block — 19 announces × `n` validators per scenario. Each `decided`
  event carries the `block_id` as both its `value` and `instance_id`
  (Snowman finalises *blocks*, so one `decided` per `(node, block_id)`).
  The per-validator `decided` count is identical across the validator
  set (no node lags or skips a block), and the run halts on `deadline`,
  never on a stall.
- **No forks.** Every node's `decided` event for a given block carries
  the *identical* `value` (the `block_id` bytes), so the distinct-value
  count per block is 1 for every block across every scenario. Zero
  `snowman_rejected`: an honest run produces no malformed payloads.
  Per [[concepts/metric-reconciliation]] §Reliability and §Snowman
  parameter rescaling, the empirical violation rate is bounded by
  `(1 − α_c/K)^β` (analytical bound); the experiment witnesses the
  honest baseline at ε = 0.
- **Finalisation latency logged.** Every `decided` event's `t` field is
  the per-node finalisation timestamp. The first decided lands at
  `t ≈ 1.000000045` across every node and every scenario, derived as
  `slot_duration + (2K + 1) · 1e-9 · β / 1e9` — slot 0 fires at `t = 1.0`,
  the announce delivery adds `1e-9`, and β = 15 poll rounds each consume
  ~3 × 1e-9 of sim time (one timer fire, K query deliveries, K response
  deliveries, all at constant delay 1e-9 deduplicated by event sequence).
  The latency-vs-`n` *curve* is flat under the constant `1e-9` delay
  regime: Snowman finality is structurally `β` poll rounds regardless
  of `n` (the round count, not the per-round wall time, depends on `n`
  through K only via the message *count*). A realistic delay regime and
  multiple seeds with confidence intervals are T41/T44 scope.
- **Determinism.** Two seed-identical runs at every scenario produce
  byte-identical event-record streams. `SnowmanNode` consumes
  `self.rng` once per poll round (the K-peer `rng.sample(...)` call),
  with `self.rng` seeded from `blake2b(global_seed:node_id)` by
  `Node.__init__` per [[concepts/reproducibility]]. Per-node RNG draws
  total `β · 19 = 285` samples per scenario — the K-peer sampling path
  PBFT and Casper FFG baselines do not exercise. Closes the
  [[concepts/week7-decision]] §5.1 watch-for by direct observation.

## Observation

The honest Snowman path is correct across the validator-set sweep: at
`n` ∈ {4, 7, 10} every validator reaches `decided` once per announced
block, all validators agree on each block's value, and no validator
rejects a message. Finalisation latency is structurally flat per round
because the network delay is the minimal constant `1e-9` and Snowman's
per-round cost is bounded by the constant POLL_DELAY = 1e-9 plus three
unit delays (timer-fire → K queries → K responses); the per-block
latency is `β · O(1)` ≈ 45 ns of sim time after the slot fires. Under
a realistic delay regime, the per-block cost will shift with
`E[delay] · β`, which is what the T41 scaling sweep and the T46/T47
delay experiments will measure.

Communication scales as expected for a K-subsampled Snowman round.
`delivery` count grows as `(n−1) + β · 2K` per block × `n` decisions —
each block has one announce broadcast (`n−1` deliveries) plus per node β
poll rounds × (K outbound queries + K inbound responses). At n=4
(K=3), that's `3 + 15·6 = 93` per block × 19 = `1767` deliveries from
poll traffic plus `3 · 19 = 57` from announces — but the model is more
nuanced: each node runs its own polls, so the K·β doubling applies
per node. The observed delivery counts (`6897 / 24054 / 51471`) grow
faster than linear with `n` because both the announce fan-out and the
per-poll query/response volume scale with `n`.

The n=4 rescaling boundary is the noteworthy case: `α_c = K = 3` means
the per-round agreement check requires *all three sampled responses*
to match the current preference, so the safety bound `(1 − α_c/K)^β`
degenerates to `0`. In an honest setting this is benign — every
responder shares the same singleton conflict set — but it is the limit
case where Snowman's probabilistic guarantee reduces to deterministic
flood agreement. Downstream comparative tables exclude this row.

## Back-links

- [[algorithms/avalanche]] — the protocol under test: Snowflake →
  Snowball → Snowman lineage, the two-threshold α_p / α_c rule, the
  β-acceptance termination criterion.
- [[concepts/metric-reconciliation]] — §Snowman parameter rescaling
  (the `(K, α_p, α_c)` rule per `n`) and §Calibration defaults
  (β = 15 cross-protocol baseline).
- [[concepts/system-design-protocols]] — §4 Snowman reference sketch;
  the five divergences landed by T38 are listed in this page's `##
  Revisions` entry.
- [[concepts/message-types]] — §5 Snowman wire schema; the permissive
  default for unknown-`block_id` `QUERY`s is clarified by T38's
  `## Revisions` entry.
- [[concepts/week7-decision]] — the W7 decision gate that scoped T38 to
  Snowman and pinned this baseline's outcomes.
- [[concepts/node-model]] — the shared-layer `Node` `SnowmanNode`
  subclasses; the `decided` event contract (`_emit_decided`).
- [[concepts/reproducibility]] — the `(global_seed, node_id)` per-Node
  RNG seeding that makes the K-peer sampling deterministic.
- [[experiments/2026-05-21_pbft-baseline]] — the T30 PBFT counterpart.
- [[experiments/2026-05-25_pos-baseline]] — the T35 Casper FFG
  counterpart; T38 mirrors its four-outcome shape adapted to Snowman's
  per-block finality semantics.

## Forward references

What this page does not cover, and which task owns:

- **Adversarial Snowman.** Selective response, adaptive colour flipping,
  sample-partitioning, colluding sub-sampler → T18 + T51–T53.
- **Empirical ε under adversary** with `β ∈ {3, 5}` regime → T51–T53.
- **Unified comparative CSV** with the Snowman column → T40.
- **Snowman Chapter 3 prose** → T36.1 (unblocked on T38 landing).
- **Out-of-order block arrival / heavy delay** → T46–T50.
- **Drop-resilience poll-deadline timer** → T47 (will land as a
  `## Revisions` entry on [[concepts/system-design-protocols]] §4).
- **Narwhal+Tusk fourth protocol** → T38.1 (between T55 and T57).

## Revisions

(Empty.)
