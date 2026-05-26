# PoS honest-validator correctness baseline — T35

End-to-end correctness check of the **simplified Casper FFG honest path**
([[algorithms/pos]]) under an **all-honest validator set**, across the W3
stack: the discrete-event scheduler ([[concepts/simulation-design]], T21),
the shared-layer `Node` ([[concepts/node-model]], T22), the honest
`Network` ([[concepts/network-model]], T23), the event-log subsystem
([[concepts/event-log-schema]], T24), and the config/factory layer
([[concepts/reproducibility]], T27), driven by `CasperNode` validators
(T32 implementation + T33 stake-weighted proposer + T34 extracted
finality module).

This is the PoS counterpart of the T30 PBFT honest-path correctness
experiment ([[experiments/2026-05-21_pbft-baseline]]). It also re-records
the canonical event-stream snapshot under the T33 stake-weighted proposer
rule, superseding the T32 build-verification page
([[experiments/2026-05-23_casper-baseline]]) whose Revisions note forwards
readers here. T35 added no `src/` protocol code — the protocol is
complete. The four T35 outcomes — every node **finalises**, the run
produces **no forks**, **finalisation latency is logged**, and two
seed-identical runs are **byte-identical** — are asserted by the new
`tests/integration/test_pos_baseline.py`. A sample CSV is regenerated on
demand at `results/pos/baseline.csv` by `python3 -m pos.baseline`; the
`results/**/*.csv` pattern is gitignored by repo convention, so the
artifact is not checked in — the canonical sample content is reproduced
inline below. The schema is a T35-local stand-in for the unified
cross-protocol CSV T40 will define against [[concepts/output-format]]
(Backlog note in `TASKS.md`).

## Configuration

- Code under test: `src/pos/` (unchanged since T34). T35 added one
  integration test (`tests/integration/test_pos_baseline.py`), one
  baseline-CSV runner module (`src/pos/baseline.py`), the sample
  `results/pos/baseline.csv`, and this page; no protocol change. Branch
  `task/T35-pos-baseline`; commit hash `TODO(human)` — assigned when the
  branch is committed (T35 lands as one human commit per
  `docs/workflow.md`).
- `global_seed = 42`; `slot_duration = 1.0`; `slots_per_epoch = 2`;
  `attest_offset = 1` (the constructor default — the mid-epoch slot, so
  the checkpoint block has time to propagate).
- Network: a single phase `[0, ∞)`, constant delay `1e-9`, drop rate 0,
  no partitions. The delay is `1e-9` rather than literal zero because the
  network model enforces `t_delivered > t_sent`; `1e-9` is the minimum
  (same as the T30 and T32 baselines).
- `t_max = 20.0`. Casper FFG has no quiescence — the slot timer re-arms
  every slot indefinitely — so each run is bounded by `t_max` only. With
  `slot_duration = 1.0` and `slots_per_epoch = 2`, epoch `e` finalises
  once epoch `e+1` is justified, which requires reaching slot
  `2·(e+1) + attest_offset`; `t_max = 20.0` covers 19 dispatched slots
  and finalises epochs 1 through 8.

### Scenarios

The first three sweep `n` at uniform stake (mirrors the T30 PBFT sweep);
the fourth preserves the T32 non-uniform-stake coverage so this page
fully supersedes the T32 event-stream snapshot.

- **n=4 uniform stake.** `stake_table = {i: 3.0 for i in range(4)}`;
  `total_stake = 12`; supermajority `≥ 2/3` ⇒ `≥ 8`.
- **n=7 uniform stake.** `stake_table = {i: 3.0 for i in range(7)}`;
  `total_stake = 21`; supermajority `≥ 14`.
- **n=10 uniform stake.** `stake_table = {i: 3.0 for i in range(10)}`;
  `total_stake = 30`; supermajority `≥ 20`.
- **n=4 non-uniform stake.** `stake_table = {0: 5.0, 1: 4.0, 2: 2.0,
  3: 1.0}`; `total_stake = 12`; supermajority `≥ 8`. Justification is on
  stake, not head-count: any pair of `{0, 1}` already clears the
  threshold; node 3 alone is far below it.

## Re-run

```
PYTHONPATH=src:tests/integration python3 -m unittest test_pos_baseline -v
PYTHONPATH=src python3 -m pos.baseline
```

The first command runs the four T35 integration tests (each a `subTest`
loop over the four scenarios above). The second writes
`results/pos/baseline.csv` — one row per scenario. Results are also
observed through the in-test `EventLogger`; the unified cross-protocol
CSV remains T40 work.

## Result

The T35 suite runs 4 tests to green. Upstream suites are unaffected; full
`make test` stays green. Per-scenario event counts, observed through the
`EventLogger`:

| Metric | `n=4 uniform` | `n=7 uniform` | `n=10 uniform` | `n=4 non-uniform` |
| :-- | --: | --: | --: | --: |
| `stopped_by` | deadline | deadline | deadline | deadline |
| `casper_block_accepted` | 76 | 133 | 190 | 76 |
| `casper_attested` | 36 | 63 | 90 | 36 |
| `casper_justified` | 36 | 63 | 90 | 36 |
| `casper_finalised` | 32 | 56 | 80 | 32 |
| `decided` | 32 | 56 | 80 | 32 |
| `casper_rejected` | 0 | 0 | 0 | 0 |
| `BLOCK-PROPOSAL` deliveries | 57 | 114 | 171 | 57 |
| `ATTESTATION` deliveries | 108 | 378 | 810 | 108 |
| epoch-1 `decided.t` | 5.000000001 | 5.000000001 | 5.000000001 | 5.000000001 |

Sample `results/pos/baseline.csv`:

```
run_id,algorithm,n_validators,latency_ms,throughput,msg_count,success
pos-n4-uniform,casper-ffg,4,5000.000001000,1.600000,165,True
pos-n7-uniform,casper-ffg,7,5000.000001000,2.800000,492,True
pos-n10-uniform,casper-ffg,10,5000.000001000,4.000000,981,True
pos-n4-nonuniform,casper-ffg,4,5000.000001000,1.600000,165,True
```

The `latency_ms` column is the median per-node finalisation time of
epoch 1, in milliseconds; `throughput` is `decided` events per simulated
second over the `t_max = 20.0` window; `msg_count` is total deliveries
(BLOCK-PROPOSAL + ATTESTATION); `success` is True when at least one
epoch finalised. The schema is T35-local; T40 will reconcile it against
[[concepts/output-format]].

- **Finalises.** Every validator emits `casper_finalised` and `decided`
  exactly once per finalised epoch — 8 epochs × `n` validators —
  matching the predicted finalisation window for `t_max = 20.0`. Each
  `decided` event carries the epoch as its `instance_id` (Decision G:
  Casper finalises *epochs*, so one `decided` per `(node, epoch)`). The
  per-validator `decided` count is identical across the validator set
  (no node lags or skips an epoch), and the run halts on `deadline`,
  never on a stall.
- **No forks.** Every node's `decided` event for a given epoch carries
  the *identical* `value` (the hex `checkpoint_hash` of the epoch's
  checkpoint block), so the distinct-value count per epoch is 1 for
  every epoch in `{1..8}` at every scenario. Zero `casper_rejected`: an
  honest run produces no malformed payloads, no non-proposer blocks, no
  out-of-range attesters, and no checkpoint-unavailable attestations.
  Per [[concepts/metric-reconciliation]] §Reliability, FFG categorical
  finality holds `fork_rate = 0` below the `1/3`-stake threshold; this
  experiment is the honest baseline witness.
- **Finalisation latency logged.** Every `decided` event's `t` field is
  the per-node finalisation timestamp. Epoch 1's `decided.t` lands at
  `5.000000001` across every node in every scenario, derived as
  `slot_duration × (2·slots_per_epoch + attest_offset) + epsilon`
  `= 1.0 × 5 + 1e-9` — the slot-5 attestation at `t = 5.0` self-records
  on each node, and the second peer ATTESTATION delivery at
  `t = 5.0 + 1e-9` completes the supermajority link that justifies
  epoch 2 and finalises epoch 1. Subsequent epochs finalise on the same
  two-slot cadence (≈ `5 + 2(e−1)` seconds), out to epoch 8 at
  `t ≈ 19.0`. The latency-vs-`n` *curve* is flat under the constant
  `1e-9` delay regime: FFG finality is structurally `2·slot_duration`
  per epoch regardless of `n`. A realistic delay regime and multiple
  seeds with confidence intervals are T41/T44 scope.
- **Determinism.** Two seed-identical runs at every scenario produce
  byte-identical event-record streams. T33's `stake_weighted_proposer`
  draws from a per-slot deterministic RNG seeded by
  `blake2b("<global_seed>:<slot>")`, so the proposer schedule is fixed
  across re-runs; the FFG aggregation is order-stable; and the network
  layer's per-Message `t_delivered` is fully determined by
  `(t_sent, delay_dist, global_seed)`.

The non-uniform-stake scenario produces event counts identical to the
n=4 uniform case — under the honest path every validator attests every
epoch, each link sums to `total_stake = 12`, and the `≥ 2/3` threshold
is met identically regardless of how the stake is partitioned. The
non-uniform scenario stresses the *wiring* (that `EpochState.link_stake`
weights each vote by `stake_table[attester_idx]` rather than by
head-count) and the proposer selection (that `stake_weighted_proposer`
favours higher-stake validators), not the threshold arithmetic; the
adversarial setting where a stake subset is withheld is T18/T53 work.

## Observation

The honest Casper FFG path is correct across the validator-set sweep:
at `n` ∈ {4, 7, 10} (and under non-uniform stake at `n = 4`) every
validator reaches `decided` once per finalised epoch, all validators
agree on each epoch's checkpoint, and no validator rejects a message.
Finalisation latency is flat at `≈ 5.000000001` seconds for epoch 1
across every scenario because the network delay is the minimal constant
`1e-9` and FFG's structural per-epoch cost is `2·slot_duration`
independent of `n`; under a realistic delay regime, the per-epoch cost
will shift with `E[delay]`, which is what the T41 scaling sweep and the
T46/T47 delay experiments will measure.

Communication scales as expected for an all-to-all FFG round.
BLOCK-PROPOSAL deliveries grow as `(n−1)·slots_dispatched = 19(n−1)` —
`57 → 114 → 171` from n=4 to n=10. ATTESTATION deliveries grow as
`9·n·(n−1)` — `108 → 378 → 810` — the `O(n²)` term that dominates the
honest-path message budget and that drives the per-protocol
`consensus_msgs_per_acu` column [[concepts/metric-reconciliation]] §3
will eventually report.

## Back-links

- [[algorithms/pos]] — the protocol under test: simplified Casper FFG,
  the two-round justify→finalise gadget, the `≥ 2/3` stake-weighted
  supermajority, epoch-granular `decided`.
- [[concepts/metric-reconciliation]] — §Finality semantics (FFG
  per-epoch finalisation) and §Reliability (`fork_rate = 0` below the
  `1/3`-stake threshold).
- [[concepts/evaluation-metrics]] — the canonical latency / reliability
  metric definitions instantiated here.
- [[concepts/event-log-schema]] — the `EventRecord` / `decided` event
  the finalisation latency is read from.
- [[concepts/node-model]] — the shared-layer `Node` the `CasperNode`
  subclasses; the `decided` event contract (`_emit_decided`).
- [[experiments/2026-05-23_casper-baseline]] — the T32 build-verification
  baseline this correctness experiment supersedes; its `## Revisions`
  note forwards readers here.
- [[experiments/2026-05-23_pos-selection-fairness]] — the T33 fairness
  check on `stake_weighted_proposer`; the proposer rule whose
  event-stream snapshot this page records.
- [[experiments/2026-05-21_pbft-baseline]] — the T30 PBFT counterpart;
  T35 mirrors its four-outcome shape adapted to FFG finality semantics.
