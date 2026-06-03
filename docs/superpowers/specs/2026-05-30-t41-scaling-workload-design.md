# T41 — Scaling baseline + workload axis (design spec)

Status: approved 2026-05-30 (human). Role: Engineer. Supersedes the
single-seed T40 baseline (`results/baseline.csv`) with a multi-seed
scaling sweep under `results/baseline/`, and lands the workload axis the
T40 extension register ([[concepts/output-format]] §11) assigns to T41.

## 1. Goal

Two coupled deliverables:

1. **Scaling sweep.** Run the three honest-path protocols (PBFT, Casper
   FFG, Snowman) across `n ∈ {4, 7, 10, 16, 25}` with **20 seeded runs**
   per configuration (seeds `0…19`), reusing the same seed set across
   protocols (common random numbers, [[concepts/experiment-matrix]] §7).
   Emit one CSV row per `(protocol, n, seed[, variant])` trial.
2. **Workload axis.** Drive every run from a real, deterministic
   transaction stream so the four `workload_*` columns, `goodput`, and
   `bytes_per_acu` become genuine measurements rather than absent
   columns. Flip the corresponding [[concepts/output-format]] §11
   register entries from `pending` to `live`.

Narwhal+Tusk is out of scope (blocked under T38.1). The NWT row stays
unpopulated per the existing register.

## 2. Scope decisions (human-confirmed 2026-05-30)

| Decision | Choice |
| :-- | :-- |
| Seeds per cell | **20** (seeds `0…19`), common random numbers across protocols |
| Workload axis | **Build it** — real arrival-process stream |
| Output layout | **`results/baseline/`** directory; retire flat `results/baseline.csv` |
| FFG stake variant | **Uniform across all `n`**; retain `nonuniform-n4` as a labeled extra row |
| PBFT run shape | **Windowed** — give PBFT a fixed `t_max` and a continuous arrival stream so it proposes across the window like FFG/Snowman, making `tps`/`goodput`/`bytes_per_acu` comparable. First-instance latency columns stay identical to T40; PBFT throughput/overhead columns intentionally re-baseline (human-confirmed 2026-05-30). |
| `peak_tps` | **Deferred** — the latency-only model has no capacity ceiling, so a saturation ramp would fabricate numbers. Recorded as a Revision. |
| `bytes_per_acu` | **Included** — derived from message-types byte budgets |
| `round_latency_ms`, `per_validator_state_bytes` | Deferred (T48 / T58) |

## 3. The model constraint that bounds this task

All three protocols are **cadence-driven, not load-driven**: PBFT
re-arms its propose timer every `propose_delay` (one instance per
interval, pipelined — `src/pbft/node.py:139`); Snowman and Casper FFG
produce one block per `slot_duration`. The simulator is **latency-only**
([[concepts/network-model]] §1): no link-bandwidth model, no per-node CPU
cost, and message *counts* are per-instance, not per-transaction. A block
carrying 1 transaction and a block carrying 1,000 commit at identical
simulated latency.

Consequence: **offered load above the cadence rate cannot saturate the
protocol** — there is no queue and no capacity ceiling to hit. Therefore
`peak_tps` and the offered-load ramp ([[concepts/experiment-matrix]] §6)
are **not honestly measurable on the current model** and are deferred,
not faked. What *is* measurable: the protocol's behaviour under a fixed
sub-saturation offered rate, with the transaction stream materialising
in the `workload_*`, `goodput`, and `bytes_per_acu` columns.

## 4. Architecture

### 4.1 Workload generator — new `src/workload/` package

A deterministic transaction-stream generator. Inputs: arrival process,
offered rate, transaction size, conflict rate, time horizon, and a seed
derived from `global_seed`. Output: a reproducible sequence of
`(arrival_time, tx_bytes_payload)` transactions over `[0, t_max]`.

- **Arrival processes:** `poisson` (memoryless inter-arrival,
  exponential gaps at rate `λ = offered_rate`) and `constant`
  (deterministic `1/offered_rate` spacing, the variance-free control).
- **Determinism:** draws come only from an RNG seeded off `global_seed`
  via the established per-component derivation
  ([[concepts/reproducibility]]); no wallclock, no global RNG. Same
  `(config, global_seed)` → identical stream. This is the byte-identical
  contract the whole pipeline already inherits
  ([[concepts/output-format]] §10).
- **Payload:** each transaction is an opaque `workload_tx_bytes`-length
  byte string (default 512, [[concepts/experiment-matrix]] §6, grounded
  in [11]). `workload_conflict_rate` is held at `0.0` (all transactions
  independently valid); the conflict mechanism is a documented stub for
  a later task.
- **Defaults:** `arrival_process = poisson`, `offered_rate = 100` tx/s,
  `tx_bytes = 512`, `conflict_rate = 0.0` — exactly the
  [[concepts/experiment-matrix]] §6 committed defaults.

### 4.2 Batch model — wiring the stream into proposers

Each proposal opportunity (a PBFT primary propose-timer fire, a Snowman /
FFG slot proposer) includes the **batch** of transactions that arrived
since the previous proposal opportunity. This is the only model that
keeps instance/block/epoch counts *unchanged* while making block contents
real:

- Instance/block/epoch count stays **cadence-driven over `t_max`** — the
  generator does not add or remove consensus instances.
- Each instance/block carries a batch ≈ `offered_rate × cadence_interval`
  transactions.
- Existing protocols already pop from a `workload` list
  (`pbft/node.py:80`, `pos/node.py:57`, `snowman/node.py:67`); the change
  is to supply a list of **batches** (one batch consumed per proposal)
  instead of the current trivial single-request / empty workload.

Per-protocol proposer identification (PBFT primary only; FFG round-robin
`slot mod n`; Snowman's per-slot announcer) is resolved against each
node's propose path during implementation, preserving determinism. The
**same** deterministic batch list (generated once per run from
`global_seed`) is handed to every node; the proposer at opportunity `k`
(PBFT `seq`, FFG/Snowman `slot`) indexes `batches[k]`, so batch content is
independent of which node proposes — no per-node stream divergence.

**PBFT windowing.** PBFT moves from quiescence (single instance) to a
fixed `t_max` window matching FFG/Snowman, fed enough batches to keep the
primary proposing across the window (`_propose` re-arms while its workload
is non-empty — `pbft/node.py:139`). Effect on landed columns:
`commit_latency_ms` / `finality_latency_ms` are defined on the *first*
decided instance ([[concepts/output-format]] §5.1) and stay **identical**
to T40; `tps`, `consensus_msgs_per_acu`, `total_msgs_per_acu` intentionally
re-baseline to honest windowed values (an improvement over T40's
single-shot quiescence-tail figures). FFG and Snowman block/epoch counts
are unchanged.

**Stability invariant (revised):** the workload wiring must not change any
*latency* column on any protocol, nor any FFG/Snowman landed column —
enforced by a regression test (§7). PBFT throughput/overhead columns are
expected to change and are re-baselined deliberately.

### 4.3 Metrics — new columns

Added to `src/output/schema.py:COLUMN_ORDER` and the
[[concepts/output-format]] §3 schema, with §11 register entries flipped to
`live`:

| column | derivation |
| :-- | :-- |
| `workload_arrival_process` | config string (`poisson` / `constant`) |
| `workload_tx_bytes` | config int (512) |
| `workload_conflict_rate` | config float (0.0) |
| `workload_offered_rate` | config float (100) |
| `goodput` | committed valid transactions ÷ run time. With `conflict_rate = 0` every committed tx is valid, so `goodput` is the tx-level throughput; the per-protocol time denominator matches that protocol's `tps` rule ([[concepts/output-format]] §5 — `result.now` for PBFT quiescence, `meta.t_max` for FFG/Snowman). |
| `bytes_per_acu` | Σ over delivery events of `byte_budget[msg_type]` ÷ decided-event count, where `byte_budget` is the per-message-type width table from [[concepts/message-types]] §3–§7, and proposal/announcement/header messages add `batch_size × tx_bytes` for their `transactions` component. Honest order-of-magnitude estimate (the byte budgets are explicitly non-binding, [[concepts/message-types]] §7); labeled as such on the experiment page. |

`tps` keeps its T40-pinned per-ACU meaning ([[concepts/output-format]]
§5); `goodput` is the distinct tx-level measure. The float-formatting
rules in `csv.py:_format_row` extend to the new float columns
(`goodput`, `bytes_per_acu` at `.6f`; `workload_*` per dtype).

### 4.4 Scenario enumeration & output

- Each protocol's `baseline.py` `SCENARIOS` expands from the hardcoded
  `seed=42` tuple to the cross product `n ∈ {4,7,10,16,25} × seed ∈
  0…19`, plus the retained `casper-ffg-n4-nonuniform` variant × seeds.
  `run_id` carries `n` but **not** seed (the `seed` column disambiguates
  rows; row identity is `(protocol, n, run_id, seed)` per
  [[concepts/output-format]] §8).
- Snowman `n=4` rows are still skipped from the main file
  ([[concepts/output-format]] §7) and written to the sanity sibling — now
  multi-seed (20 rows) for consistency.
- Orchestrator `src/output/baseline.py` writes
  `results/baseline/baseline.csv` and
  `results/baseline/snowman_n4_sanity.csv`; the flat
  `results/baseline.csv` and `results/snowman_n4_sanity.csv` are retired
  (removed). Commit-hash threading (§10 of output-format) is preserved.

## 5. Run volume

`(PBFT 5 n + FFG 5 n uniform + Snowman 4 n in-main [n=4 excluded]) × 20
seeds` = `(5 + 5 + 4) × 20 = 280` main rows, + Snowman `n=4` sanity
(20 rows) + FFG `nonuniform-n4` (20 rows). ≈ **320 runs total**. Honest
baselines are fast (quiescence or `t_max ≤ 20 s` simulated); the sweep is
a single orchestrator invocation.

## 6. Determinism contract

Inherited end-to-end ([[concepts/output-format]] §10): same
`(config, global_seed)` → byte-identical CSV. The generator is the one
new RNG consumer; it must seed off `global_seed` through the existing
derivation and draw in a fixed order. The reducer stays a pure function.
Row ordering stays total over `(protocol, n, run_id, seed)`. The only
impurity surface remains `_resolve_commit_hash`, monkeypatched in tests.

## 7. Test plan (TDD)

1. **Generator determinism** — same `(params, seed)` → identical stream;
   different seed → different stream.
2. **Arrival-rate / distribution** — over many seeds, empirical mean rate
   and inter-arrival distribution land within tolerance of the configured
   `offered_rate` and process (the [[concepts/experiment-matrix-runs]]-
   style distribution check; analogue of the T25 delay-distribution test).
3. **Batch wiring (per protocol)** — a proposed block/instance carries the
   batch of transactions that arrived in its interval; empty interval →
   empty batch; counts unchanged.
4. **Existing-column stability (regression)** — the 9 T40 rows' landed
   columns are byte-identical before/after the workload wiring at
   `seed=42` (locks §4.2's invariant).
5. **Multi-seed CSV byte-identical determinism** — two full orchestrator
   runs (commit hash monkeypatched) produce byte-identical
   `results/baseline/baseline.csv`.
6. **Schema guards** — new columns pass the `_GENERIC_COLUMNS` collision
   and `COLUMN_ORDER` membership guards; sanity-file schema check holds.

Each protocol's `tests/<protocol>/` suite and `tests/output/` extend;
`tests/workload/` is the new suite, registered as a Makefile target.

## 8. Honest deferrals — recorded as Revisions

Append `## Revisions` entries (dated 2026-05-30, task T41), not silent
overwrites:

- [[concepts/experiment-matrix]] §6 / [[concepts/output-format]] §11 —
  `peak_tps` and the offered-load ramp are **not realizable** on the
  latency-only, no-CPU-cost model: nothing saturates as offered load
  rises, so a sustained-rate ramp would report a config artifact, not a
  protocol property. Deferred to a task that first adds a capacity/cost
  model (candidate: T58 enhancement, or a dedicated task). The
  `offered_rate = 100` tx/s sub-saturation operating point is used; it is
  not recalibrated down (no protocol saturates).
- `round_latency_ms` remains T48-coupled; `per_validator_state_bytes`
  remains T58-coupled — unchanged from the register.

## 9. Artifacts

- `src/workload/` (generator + `__init__`).
- `src/output/schema.py`, `src/output/csv.py`, `src/output/baseline.py`
  (new columns, formatting, output paths).
- `src/pbft/baseline.py`, `src/pos/baseline.py`, `src/snowman/baseline.py`
  (scenario expansion + batch wiring).
- `tests/workload/`, extended `tests/output/` + `tests/{pbft,pos,snowman}/`.
- `results/baseline/baseline.csv`, `results/baseline/snowman_n4_sanity.csv`
  (gitignored runtime artifacts per repo convention; verify against
  `.gitignore`).
- `wiki/experiments/2026-05-30_scaling-baseline.md` (config, seeds, commit
  hash, re-run command, raw-result location, observation; Auggie
  verification subsection).
- Revisions on [[concepts/output-format]] and
  [[concepts/experiment-matrix]]; `wiki/index.md` + `wiki/log.md` updates.

## 10. Out of scope

Capacity/cost model and `peak_tps`; conflict-rate sweeps; adversarial and
delay axes (Families B/C); CI computation and aggregated file (T44);
Narwhal+Tusk (T38.1); plotting (T43). No changes to `src/scheduler/`,
`src/network/`, `src/nodes/`, `src/event_log/` beyond read-only use.

## 11. Auggie note

The Engineer role mandates `mcp__auggie__codebase-retrieval`; that tool
is not present in this environment. The available auggie tool
(`augment_code_search`) requires the GitHub repo to be indexed, and
`palhs/thesis` returns `REPO_NOT_FOUND`. Structural search fell back to
local `grep` / `Read`; this is logged in the experiment page's Auggie
verification subsection per the role's verification-log requirement.
