# [2026-06-03] T41 — Scaling baseline + workload axis

The first multi-seed comparative dataset: three honest-path protocols
(PBFT, Casper FFG, Snowman) swept across validator-set size
`n ∈ {4, 7, 10, 16, 25}` at 20 seeds each, driven by a real deterministic
transaction workload. Lands Run family A (Scaling) of
[[concepts/experiment-matrix]] §3 and the workload axis of
[[concepts/output-format]] §13. Narwhal+Tusk is out of scope (T38.1).

## Configuration

- **Sweep:** `n ∈ {4,7,10,16,25} × seed ∈ {0…19}`, common random numbers
  (same seed set across protocols, [[concepts/experiment-matrix]] §7).
- **Workload:** `poisson` arrival, `offered_rate = 100` tx/s,
  `tx_bytes = 512`, `conflict_rate = 0.0` (the committed §6 defaults).
  Generated deterministically per run from `global_seed` by
  `src/workload/generator.py`; the proposer at opportunity `k` (PBFT `seq`,
  FFG/Snowman `slot`) carries `batches[k]`.
- **Network:** minimal constant delay (honest `static-baseline`-equivalent).
- **Run shape:** PBFT windowed over `t_max = 20 s` (continuous proposing);
  Casper FFG `t_max = 20 s`, `slot_duration = 1 s`, `slots_per_epoch = 2`;
  Snowman `t_max = 20 s`, `slot_duration = 1 s`, `β = 15`, `(K, α_p, α_c)`
  rescaled per [[concepts/metric-reconciliation]].
- **Rows:** 300 in `results/baseline/baseline.csv` (PBFT 100 + Casper FFG
  120 [100 uniform + 20 `n=4` nonuniform] + Snowman 80 [`n=4` excluded]);
  20 in `results/baseline/snowman_n4_sanity.csv` (Snowman `n=4`, the
  degenerate `α_c = K` boundary, excluded from comparison per
  [[concepts/output-format]] §7).
- **Commit hash:** `1348a5da-dirty` (generated from the uncommitted T41
  working tree). **Regenerate after the code is committed** for a clean
  provenance hash — `PYTHONPATH=src python3 -m output.baseline`.

## Re-run

```
PYTHONPATH=src python3 -m output.baseline
# writes results/baseline/baseline.csv + results/baseline/snowman_n4_sanity.csv
```
Byte-identical on re-run (determinism gated by
`tests/output/test_baseline_e2e.py`).

## Results (means over seeds)

| protocol | n | seeds | commit_ms | tps | goodput | msgs/ACU | bytes/ACU |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| casper-ffg | 4 | 40 | 5000.0 | 1.6 | 79.6 | 5.2 | 92 125 |
| casper-ffg | 7 | 20 | 5000.0 | 2.8 | 79.6 | 8.8 | 105 853 |
| casper-ffg | 10 | 20 | 5000.0 | 4.0 | 79.6 | 12.3 | 111 741 |
| casper-ffg | 16 | 20 | 5000.0 | 6.4 | 79.6 | 19.1 | 117 637 |
| casper-ffg | 25 | 20 | 5000.0 | 10.0 | 79.6 | 29.3 | 122 365 |
| pbft | 4 | 20 | 1000.0 | 3.8 | 94.8 | 6.8 | 38 724 |
| pbft | 7 | 20 | 1000.0 | 6.7 | 94.8 | 12.9 | 44 503 |
| pbft | 10 | 20 | 1000.0 | 9.5 | 94.8 | 18.9 | 46 987 |
| pbft | 16 | 20 | 1000.0 | 15.2 | 94.8 | 30.9 | 49 485 |
| pbft | 25 | 20 | 1000.0 | 23.8 | 94.8 | 49.0 | 51 502 |
| snowman | 7 | 20 | 1000.0 | 6.7 | 94.8 | 180.9 | 51 144 |
| snowman | 10 | 20 | 1000.0 | 9.5 | 94.8 | 270.9 | 56 941 |
| snowman | 16 | 20 | 1000.0 | 15.2 | 94.8 | 450.9 | 66 064 |
| snowman | 25 | 20 | 1000.0 | 23.8 | 94.8 | 601.0 | 73 217 |

All scenarios: `success_rate = 1.0`, `fork_rate = 0.0`. (Casper FFG `n=4`
carries 40 rows because the uniform and `nonuniform` stake variants both
sit at `n=4`.)

## Observations

- **Finality latency is flat in `n`.** PBFT and Snowman finalise the first
  unit at ≈ 1 s (one `propose_delay` / `slot_duration`); Casper FFG at ≈ 5 s
  (justify→finalise spans epochs). None grows with `n` over this range —
  latency is set by the protocol's round structure, not the validator count.
- **Goodput is constant in `n` — no saturation.** Every protocol sustains
  the offered load at every `n` (≈ 95 tx/s for the per-instance protocols
  PBFT/Snowman, ≈ 80 tx/s for Casper FFG). This is the *expected* and
  honest result on a latency-only model with no capacity ceiling
  ([[concepts/experiment-matrix]] §9 Revision): offered load below the
  cadence rate is always absorbed. The Casper FFG shortfall is the
  **finality-tail effect** — its per-epoch finality leaves the window's
  last unfinalised epoch's slots uncommitted, so in-window goodput sits
  ~20 % below offered, vs ~5 % for the per-block PBFT/Snowman protocols.
- **Communication overhead per ACU grows with `n`, and Snowman dominates.**
  PBFT and Casper FFG scale ≈ `O(n)` messages per committed unit (6.8→49
  and 5.2→29 over `n=4→25`); Snowman is an order of magnitude higher
  (181→601) — the `O(K·β)` repeated-subsampling poll cost, which at
  thesis-scale `n` is the price of its `n`-independent *per-validator* cost.
  This is the central performance/structure contrast Chapter 4 (RQ3) draws.
- **`bytes_per_acu` is an honest order-of-magnitude estimate.** It sums the
  fixed per-message-type byte budgets from [[concepts/message-types]] §3–§7
  (declared non-binding there) plus `offered_rate · interval · tx_bytes`
  for transaction-carrying messages; treat the absolute values as
  indicative, the cross-protocol/`n` trend as the signal.

## Scope and deferrals

- **`peak_tps` deferred** — the model cannot saturate (no per-tx/byte cost,
  no queue), so an offered-load ramp would report a config artifact. Moved
  to a capacity-model task ([[concepts/experiment-matrix]] §9 Revision,
  [[concepts/output-format]] §13).
- **CIs and aggregation** (means ± 95 % CI, aggregated sibling file) are
  T44; this task lands the raw per-trial long-format rows.
- **Narwhal+Tusk** is T38.1.

## Auggie verification

The Engineer role mandates `mcp__auggie__codebase-retrieval`; that tool is
absent in this environment. The available auggie tool
(`mcp__auggie__augment_code_search`) indexes GitHub repos only, and
`palhs/thesis` returns `[REPO_NOT_FOUND]` on both the pickup-index and
post-edit re-queries. Structural search fell back to local `grep`/`Read`
throughout (recorded per the role's verification-log requirement):

- *pickup-index:* mapped the T40 pipeline (`src/output/{schema,csv,baseline}.py`),
  the three `*/baseline.py` + `*/summarise.py`, and the config/runner/RNG
  seams — confirmed `Config.workload` is the opaque T41 slot and the
  blake2b seed-derivation idiom.
- *post-edit re-query:* confirmed no stale callers of the changed
  `SCENARIOS`/`run_scenario` (only `src/output/baseline.py` + tests), the
  removed Snowman `_workload_cursor` has zero references, and the slot-indexed
  `_propose` change is the only node-layer edit per protocol.

## Revisions

**[2026-06-04] PBFT rows regenerated after the T70 client-finality fix.**
The dataset was re-run with `PYTHONPATH=src python3 -m output.baseline` on
the T70 branch (provenance `commit_hash` now `24a491a4`, was
`1348a5da-dirty`). T70 finding #1 added an `f+1` REPLY round to PBFT, so
`finality_latency_ms` is now measured at **client-observed** finality — one
network hop past the internal `2f+1` COMMIT quorum — and the REPLY messages
are counted in PBFT's overhead columns. The original PBFT rows above were
generated with the pre-T70 code and are superseded by the regenerated CSV.

PBFT before/after (means over 20 seeds; deltas hold per-seed — the
per-protocol metrics carry zero variance across seeds at fixed `n`):

| metric | n=4 | n=7 | n=10 | n=16 | n=25 |
| :-- | --: | --: | --: | --: | --: |
| commit_latency_ms (old=new) | 1000.000003 | 1000.000003 | 1000.000003 | 1000.000003 | 1000.000003 |
| finality_latency_ms old | 1000.000003 | 1000.000003 | 1000.000003 | 1000.000003 | 1000.000003 |
| finality_latency_ms new | 1000.000004 | 1000.000004 | 1000.000004 | 1000.000004 | 1000.000004 |
| consensus_msgs/ACU old | 6.750 | 12.857 | 18.900 | 30.938 | 48.960 |
| consensus_msgs/ACU new | 7.500 | 13.714 | 19.800 | 31.875 | 49.920 |
| Δ consensus_msgs/ACU | +0.750 | +0.857 | +0.900 | +0.938 | +0.960 |
| bytes/ACU old | 38 724 | 44 502.9 | 46 987.2 | 49 485 | 51 502.1 |
| bytes/ACU new | 38 763 | 44 547.4 | 47 034 | 49 533.8 | 51 552 |
| Δ bytes/ACU (≈+0.10 %) | +39 | +44.6 | +46.8 | +48.8 | +49.9 |
| tps (old=new) | 3.800 | 6.650 | 9.500 | 15.200 | 23.750 |
| goodput (old=new) | 94.820 | 94.820 | 94.820 | 94.820 | 94.820 |

Direction confirmed:
- `finality_latency_ms` increases by one network-hop tick (`+1e-6` ms in the
  model's time units) and now **strictly exceeds** `commit_latency_ms`
  (1000.000004 > 1000.000003) — finality is the client-observed event, one
  hop past COMMIT. The absolute increment is tiny because the honest-path
  network model encodes the extra REPLY hop as a minimal delay tick.
- `consensus_msgs_per_acu` increases (+0.75 → +0.96 per ACU over
  n=4→25). Cause: every replica now sends a REPLY on COMMITTED-local — all
  `n` replicas reply and the collector self-records, so each committed
  instance adds ≈`n−1` REPLY *deliveries* (`f+1`=2,3,4,6,9 is the
  *finalization threshold*, i.e. how many matching replies the collector
  waits for, not the message volume). Normalized per ACU the addition is
  well under one message and its relative share shrinks as `n` grows and
  the all-to-all PREPARE/COMMIT traffic dominates.
- `bytes_per_acu` increases ≈0.10 % uniformly (REPLY messages are small).
- `commit_latency_ms`, `tps`, `goodput` are unchanged — the COMMIT-quorum
  timing and committed-throughput are unaffected by the added client round.

Casper FFG and Snowman rows are **unchanged in every value column** (only
`commit_hash` moved, since HEAD advanced from the T41 commit to the T70
commit `24a491a4`); their node code was untouched by T70. Determinism
re-verified: two independent clean-tree regenerations are byte-identical.
The "Results" and "Observations" sections above retain the original PBFT
numbers as the pre-T70 record; use the regenerated CSV for current values.

## Cross-references

- [[concepts/output-format]] §13 — schema/register lift this dataset realises.
- [[concepts/experiment-matrix]] §3 (Family A), §6 (workload), §7 (seeds),
  §9 Revision (peak_tps deferral).
- [[concepts/metric-reconciliation]] — per-protocol metric formulas + Snowman
  rescaling / `n=4` exclusion.
- [[concepts/runner]] — `run_to_completion` seam each baseline drives.
- [[experiments/2026-05-28_unified-output]] — the single-seed T40 baseline
  this dataset supersedes.
