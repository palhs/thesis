# PBFT honest-node correctness baseline — T30

End-to-end correctness check of the **full PBFT three-phase commit**
([[algorithms/pbft]]) under an **all-honest validator set**, across the W3
stack: the discrete-event scheduler ([[concepts/simulation-design]], T21),
the shared-layer `Node` ([[concepts/node-model]], T22), the honest
`Network` ([[concepts/network-model]], T23), the event-log subsystem
([[concepts/event-log-schema]], T24), and the config/factory layer
([[concepts/reproducibility]], T27), driven by `PBFTNode` validators
(T28 pre-prepare + T29 voting/commit/view-change).

This is a **correctness experiment**, not a build-verification baseline.
The T29 baseline ([[experiments/2026-05-21_pbft-consensus-baseline]])
confirmed the protocol *composes* across the stack at n=4/7 plus a
view-change scenario. T30 instead asserts the three honest-path
correctness outcomes — every node **finalizes**, the run produces **no
forks**, and **finalization latency is logged** — across the validator-set
sweep n ∈ {4, 7, 10}. T30 added no `src/` code; the protocol is complete.

## Configuration

- Code under test: `src/pbft/` (unchanged since T29). T30 added one test
  file, `tests/integration/test_pbft_baseline.py`, and this page; no
  `src/` change. Branch `task/T30-pbft-honest-correctness`; commit hash
  `TODO(human)` — assigned when the branch is committed (T30 lands as one
  human commit per `docs/workflow.md`).
- `global_seed = 42`; `initial_view = 0`; `propose_delay = 1.0`;
  `vc_delay = 1000.0` — generous, so no instance's view-change timer fires
  before its commit quorum forms.
- Validator-set sizes `n ∈ {4, 7, 10}`, run separately. Fault threshold
  `f = ⌊(n−1)/3⌋` and commit quorum `2f+1`: n=4 → f=1, quorum 3; n=7 →
  f=2, quorum 5; n=10 → f=3, quorum 7.
- Workload: a single request `[b"X"]` placed on node 0 only; the run
  commits exactly `(view 0, seq 0)`.
- Network: a single phase `[0, ∞)`, constant delay `1e-9`, drop rate 0, no
  partitions. The delay is `1e-9` rather than literal zero because the
  network model enforces `t_delivered > t_sent`; `1e-9` is the minimum
  (same as the T29 Scenario A baseline).
- `t_max = ∞` — the honest run quiesces on its own.

## Re-run

```
PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_baseline -v
```

Four tests: `test_every_node_finalizes`, `test_no_forks`,
`test_finalization_latency_logged`, `test_determinism`, each a `subTest`
loop over n ∈ {4, 7, 10}. Results are observed through the in-test
`EventLogger` — no CSV is persisted (the unified comparative CSV is T40
work).

## Result

The T30 suite runs 4 tests to green. Per-n event counts, observed through
the `EventLogger`:

| Metric | `n=4` | `n=7` | `n=10` |
| :-- | --: | --: | --: |
| `stopped_by` | quiescence | quiescence | quiescence |
| `pbft_pre_prepared` | 4 | 7 | 10 |
| `pbft_prepared` | 4 | 7 | 10 |
| `pbft_committed` | 4 | 7 | 10 |
| `decided` | 4 | 7 | 10 |
| `pbft_rejected` | 0 | 0 | 0 |
| `pbft_view_change` | 0 | 0 | 0 |
| `PRE-PREPARE` deliveries | 3 | 6 | 9 |
| `PREPARE` deliveries | 12 | 42 | 90 |
| `COMMIT` deliveries | 12 | 42 | 90 |
| `events_processed` | 29 | 92 | 191 |
| distinct `decided` values (seq 0) | 1 | 1 | 1 |
| finalization latency `decided.t` | 1.000000003 | 1.000000003 | 1.000000003 |

- **Finalizes.** Every validator `0…n−1` runs the full
  `pre_prepared → prepared → committed → decided` pipeline exactly once
  for `(view 0, seq 0)` — `n` of each event — and the run halts on
  `quiescence`, never on `t_max` or a stall.
- **No forks.** Every node's `decided` event for seq 0 carries the
  *identical* value — the digest of the request `b"X"` — so the distinct
  value count is 1 at every n. Zero `pbft_rejected`, zero
  `pbft_view_change`, and zero `VIEW-CHANGE` / `NEW-VIEW` deliveries: an
  honest run reaches agreement with no recovery machinery engaged. This is
  the `fork_rate = 0` "by construction" property recorded for PBFT in
  [[concepts/metric-reconciliation]] §Reliability — categorical finality,
  no equivocation below the `f` threshold.
- **Finalization latency logged.** The `decided` event's `t` field is the
  per-node finalization timestamp; measured from run start (`t = 0`) it is
  `1.000000003` for every node at every n. It decomposes as
  `1.0` (the `propose_delay` timer offset before the primary proposes seq
  0) `+ 3·1e-9` (three delivery hops on the commit critical path:
  `PRE-PREPARE → PREPARE → COMMIT`). Two seed-identical runs produce
  byte-identical event-record streams at every n.

## Observation

Honest PBFT is correct across the validator-set sweep: at n = 4, 7, and
10 every replica reaches `decided` on the uniform `2f+1` quorum, all
replicas decide the same value, and no replica rejects a message or
initiates a view-change. The finalization latency is flat at
`≈1.000000003` across all three sizes because the network delay is the
minimal constant `1e-9`: message *fan-out* grows as `O(n²)` — `PREPARE`
and `COMMIT` deliveries go `12 → 42 → 90` and `events_processed`
`29 → 92 → 191` — but the commit *critical path* is a fixed three-hop
chain independent of n, so under a constant per-hop delay the latency
does not move. The latency-vs-n *curve* — the quantity RQ3 actually asks
for — requires a realistic delay regime, multiple seeds, and confidence
intervals; that is T41/T44 scope, not this correctness check. Each node's
per-instance view-change timer, armed on `PRE_PREPARED` and cancelled on
`COMMITTED`, leaves one lazy heap tombstone (`n` total), far below the
`heap/2` compaction threshold flagged in the `TASKS.md` Backlog — the
virtual clock advances cosmetically to `t ≈ 1001` as those tombstones are
popped and skipped, exactly the T29 baseline behaviour. The
above-threshold `f > 1/3` safety cliff is deliberately out of scope here:
T30 fixes the honest baseline; equivocation and the safety-invariant
measurement are T53/T54.

## Back-links

- [[algorithms/pbft]] — the protocol under test: three-phase commit, the
  `2f+1` quorum-intersection safety argument, categorical finality.
- [[concepts/metric-reconciliation]] — §Finality semantics (PBFT
  time-to-finality = `2f+1` `COMMIT` collected) and §Reliability
  (`fork_rate = 0` by construction) — the definitions this run checks.
- [[concepts/evaluation-metrics]] — the canonical latency / reliability
  metric definitions instantiated here.
- [[concepts/event-log-schema]] — the `EventRecord` / `decided` event the
  finalization latency is read from.
- [[concepts/node-model]] — the shared-layer `Node`; the `decided` event
  contract (`_emit_decided`).
- [[experiments/2026-05-21_pbft-consensus-baseline]] — the T29
  build-verification baseline this correctness experiment extends.
