# Output format

Canonical comparative CSV produced by `src/output/csv.py`: one row per
`(protocol, scenario, seed)` simulation run; the derived dataset
downstream of [[concepts/event-log-schema]]; the column-set
implementation of the contract pinned by
[[concepts/metric-reconciliation]] §T40 CSV schema implications.

## 1. Purpose

T40 is the lift from per-protocol event streams to one comparative
table. Four structural asymmetries from
[[concepts/metric-reconciliation]] propagate into the column set: the
linear-chain / DAG **output structure** (resolved via the ACU
denominator on the `*_per_acu` columns); the four **finality regimes**
(resolved into the `commit_latency_ms` / `finality_latency_ms` column
split); the Narwhal+Tusk **mempool / consensus message split**
(resolved into two columns, `mempool_msgs_per_acu` and
`consensus_msgs_per_acu`); and the **Snowman parameter rescaling**
(resolved into five Snowman-only columns plus the `n=4` boundary policy
in §7). The page is the L-W4 M1 forward-reference closer — fifteen
inbound `[[concepts/output-format]]` links across twelve pages
(`wiki/lint/2026-05-21_report.md` §M1) resolve once the file lands.

## 2. Position in the pipeline

```
EventLogger.records  +  RunResult  +  ScenarioMeta
              \              |              /
               \             |             /
              src/<protocol>/summarise.py   ← protocol-specific reducer
                            +
              src/output/csv.py::_generic_cols  ← generic columns
                            ↓
              src/output/csv.py::write_unified_csv
                            ↓
                  results/baseline.csv         ← one row per run
                            ↓
                       T44 aggregation
                            ↓
              results/baseline_aggregated.csv  ← means + 95% CIs
                            ↓
                  Chapter 4 plots (T48–T49)
```

Row granularity is **per-trial / long format** — one row per
`(protocol, scenario, seed)`. T40 writes the per-trial file at the
project default `global_seed=42` (so the `seed` column is constant
today but present). T44 owns the multi-seed sweep, CI computation, and
the aggregated sibling file. The two CSV layouts are sibling consumers
of the same `EventLogger.records` substrate
([[concepts/event-log-schema]]), with different row granularities and
different column sets.

## 3. Canonical schema

The full ~30-column schema implied by
[[concepts/metric-reconciliation]] §T40 CSV schema implications. T40
populates the 18-column subset marked `populated-today? = yes`; the
remaining columns are pending under their owning tasks, each registered
in §11 below.

| column | dtype | unit | populated-today? | extension-register-entry |
| :--- | :--- | :--- | :--- | :--- |
| `run_id` | str | — | yes | — |
| `protocol` | str | — | yes | — |
| `n` | int | validators | yes | — |
| `byzantine_fraction` | float | [0, 1] | no | T51–T54 |
| `adversary_strategy` | str | — | no | T51–T54 |
| `seed` | int | — | yes (=42 today) | T41 sweeps |
| `workload_arrival_process` | str | — | no | T41 |
| `workload_tx_bytes` | int | bytes | no | T41 |
| `workload_conflict_rate` | float | [0, 1] | no | T41 |
| `workload_offered_rate` | float | tx/s | no | T41 |
| `network_phase_id` | str | — | no | T19 + T48 |
| `n_runs` | int | — | no (=1 today) | T44 |
| `commit_hash` | str | — | yes | — |
| `commit_latency_ms` | float | ms | yes (PBFT, FFG, Snowman) | NWT row → T38.1 |
| `finality_latency_ms` | float | ms | yes (PBFT, FFG, Snowman) | NWT row → T38.1 |
| `round_latency_ms` | float | ms | no | T41 + T48 |
| `tps` | float | tx/s | yes (PBFT, FFG, Snowman) | NWT row → T38.1 |
| `goodput` | float | tx/s | no | T41 + T58 |
| `peak_tps` | float | tx/s | no | T41 + T58 |
| `mempool_tps` | float | tx/s | no | T38.1 |
| `consensus_msgs_per_acu` | float | msgs/ACU | yes (PBFT, FFG, Snowman) | NWT row → T38.1 |
| `mempool_msgs_per_acu` | float | msgs/ACU | no | T38.1 |
| `total_msgs_per_acu` | float | msgs/ACU | yes | NWT row → T38.1 |
| `bytes_per_acu` | float | bytes/ACU | no | T41 + T58 |
| `per_validator_state_bytes` | float | bytes | no | T41 + T58 |
| `success_rate` | float | [0, 1] | yes (0/1 indicator) | becomes frequency at T44 |
| `fork_rate` | float | [0, 1] | yes | — |
| `view_change_or_reorg_count` | int | events | no | T54 |
| `empirical_epsilon` | float | [0, 1] | no | T54 |
| `analytical_epsilon_bound` | float | [0, 1] | no | T54 |
| `f_max_count` | int | nodes | no | T54 |
| `f_max_stake` | float | stake | no | T54 |
| `t_max` | float | s | yes | — |
| `K` | int | — | yes (Snowman only) | NaN elsewhere |
| `alpha_p` | int | — | yes (Snowman only) | NaN elsewhere |
| `alpha_c` | int | — | yes (Snowman only) | NaN elsewhere |
| `beta` | int | — | yes (Snowman only) | NaN elsewhere |
| `alpha_c_over_K` | float | [0, 1] | yes (Snowman only) | NaN elsewhere |

The source of truth for the ordering of the today subset is
`src/output/schema.py:COLUMN_ORDER`. Adding a future column is a
one-line edit there plus an extension-register entry on this page.

## 4. Today's writer subset

18 columns, ordered as `COLUMN_ORDER`:

```
run_id, protocol, n, seed,
commit_hash, t_max,
commit_latency_ms, finality_latency_ms,
tps,
consensus_msgs_per_acu, total_msgs_per_acu,
success_rate, fork_rate,
K, alpha_p, alpha_c, beta, alpha_c_over_K
```

Columns absent from `COLUMN_ORDER` are not written as `NaN` — they are
absent rows on the schema, picked up by their owning task per §11. This
distinguishes *structurally not applicable to this protocol* (a present
column with `NaN`) from *not yet implemented anywhere* (absent column).

## 5. Per-protocol derivation rules

### 5.1 PBFT

Per-block deterministic finality: every `decided` event at a given
`instance_id=(view, seq)` is final on receipt.

- `commit_latency_ms = finality_latency_ms` — both are the median
  per-node decision time for the first decided instance,
  `1000 · median{r.t : r.event_type == "decided"
  ∧ r.fields["instance_id"] == first}`.
- `tps = decided_count / result.now` (quiescence-stopped run; deciding
  the throughput denominator from the stop time, not `t_max`).
- `consensus_msgs_per_acu = delivery_count / decided_count` (the ACU is
  one decided instance; PBFT consensus messages dominate the message
  total at the honest baseline).
- `success_rate = 1.0` iff any instance decided, else `0.0`.
- `fork_rate = 0.0` by construction — PBFT cannot fork below `f`
  ([[algorithms/pbft]]).
- Snowman parameter columns = `NaN`.

### 5.2 Casper FFG

Slot-vote-aggregation finality at epoch granularity. The first
finalised epoch is epoch 1 in every honest-baseline scenario at the
calibration delay regime.

- `commit_latency_ms = finality_latency_ms` at the honest baseline
  (block-included latency and epoch-finalised latency coincide when no
  reorg occurs; the column split is reserved for the T54
  pre-finality-reorg case where they diverge).
- `latency_ms = 1000 · median{r.t : r.event_type == "decided"
  ∧ r.fields["instance_id"] == 1}` — per-node first-epoch finalisation
  time.
- `tps = decided_count / meta.t_max` (deadline-stopped run).
- `consensus_msgs_per_acu = delivery_count / decided_count` (the ACU
  is one finalised checkpoint, which corresponds to one `decided`
  event per node per epoch).
- `success_rate = 1.0` iff any epoch finalised, else `0.0`.
- `fork_rate = 0.0` at the honest baseline (pre-finality reorg accounting
  belongs to T54).
- Snowman parameter columns = `NaN`.

### 5.3 Snowman

Per-block probabilistic finality at counter `β`. The first announced
block reaches `decided` in every honest-baseline scenario.

- `commit_latency_ms = finality_latency_ms` — Snowman has no separate
  pre-finality state in the implemented model; counter-`β` IS finality.
- `latency_ms = 1000 · median{r.t : r.event_type == "decided"
  ∧ r.fields["instance_id"] == first_block}` (Snowman emits the block
  identity under the `instance_id` field — same key as PBFT/FFG, with
  the value being the block hash).
- `tps = decided_count / meta.t_max`.
- `consensus_msgs_per_acu = delivery_count / decided_count` (the ACU
  is one decided block; deliveries are the K-peer query / response
  pairs that drove the counter).
- `success_rate = 1.0` iff any block decided, else `0.0`.
- `fork_rate = 0.0` at the honest baseline (pre-`β` preference-flip
  accounting belongs to T54; see §10 risk 3).
- `(K, α_p, α_c, β, α_c/K)` from
  [[concepts/metric-reconciliation#snowman-parameter-rescaling]]:
  `K = min(20, n−1); α_p = ⌊K/2⌋+1; α_c = ⌈0.8·K⌉; β = 15`. The
  reducer mirrors the rescaling rule as the canonical Python source.

### 5.4 Narwhal+Tusk

Lands with T38.1. The reducer is the open-to-revision surface; its
addition is one new `src/narwhal_tusk/summarise.py` + one entry in the
`_REDUCERS` dispatch table.

## 6. NaN dispatch policy

1. **Snowman parameter columns** (`K`, `alpha_p`, `alpha_c`, `beta`,
   `alpha_c_over_K`) carry `NaN` on rows where `protocol ≠ "snowman"`.
2. **`f_max_count` and `f_max_stake` are mutually exclusive** — exactly
   one is populated per row when the f_max family lands; the other is
   `NaN`. Dispatch by protocol fault-attribution model: count for
   PBFT / Snowman / Narwhal+Tusk, stake for Casper FFG.
3. **Pending vs structurally N/A** — a column whose extension-register
   entry (§11) is unresolved is absent from the CSV header today
   (empty distinguishes "not implemented yet" from "structurally not
   applicable to this protocol"). The `NaN` policy applies only once a
   column lands.

## 7. Snowman n=4 row policy

At `n=4` Snowman's parameter rescaling collapses to the degenerate
boundary `α_c = K` (unanimity) — see
[[concepts/metric-reconciliation#snowman-parameter-rescaling]]
§Comparative-claim exclusion at n=4. The writer **skips** the
`snowman-n4` row from `results/baseline.csv` so downstream consumers
(T44 aggregation, T48 plots, Chapter 4 tables) do not have to
re-implement the exclusion.

`snowman.summarise` exports a separate `sanity_row()` function the
orchestrator calls to write the row to a sibling
`results/snowman_n4_sanity.csv` file. The sanity file's schema is the
same 18-column `COLUMN_ORDER` plus one extra `snowman_degenerate_n4`
boolean flag column (always `True` in the sanity file; the column
does not exist in the main file). Header row + one data row.

## 8. Row identity & ordering

**`run_id`** uniquely names a scenario: `<protocol>-n<n>[-<variant>]`.
Examples: `pbft-n4`, `casper-ffg-n4-nonuniform`, `snowman-n7`. The
`variant` suffix is omitted when the scenario has no variant axis.

**Row order** is the lexicographic sort of
`(protocol, n, run_id, seed)`. This is total: the four-tuple uniquely
identifies a row in the per-trial schema, so the sort is independent of
the input iterable's order. Grep-friendliness is the primary
requirement, not human-reading order — `casper-ffg-n4-nonuniform`
sorts before `casper-ffg-n4-uniform` because `nonuniform < uniform`
alphabetically.

**`seed`** is the integer `global_seed` from
`build_run(config, global_seed, factory)`. Today every scenario runs at
the project default `global_seed=42`, so the column is constant but
present. T41 sweeps it.

## 9. CSV mechanics

Stdlib `csv.DictWriter`, header row, `newline=""`,
`extrasaction="raise"`, parent directories created on write,
overwrite-on-write (no append; T41 owns the multi-file aggregator
pattern). Float formatting:

- `*_ms` columns at `.9f` (nanosecond resolution preserved).
- `tps`, `*_per_acu`, `success_rate`, `fork_rate`, `alpha_c_over_K`
  at `.6f`.
- Snowman parameters `K`, `alpha_p`, `alpha_c`, `beta` as integers.

Empty `runs` iterable → header-only file. The two-guard schema check
(explicit pre-write `_GENERIC_COLUMNS` collision detection +
`extrasaction="raise"`) catches reducer drift early. A reducer that
returns a key in `_GENERIC_COLUMNS` raises `ValueError` at row-build
time; a reducer that returns a key not in `COLUMN_ORDER` raises
`ValueError` too. An unknown `protocol` raises `KeyError` from
`_REDUCERS`.

## 10. Determinism contract

Same `(YAML config, global_seed)` → byte-identical
`results/baseline.csv`. Inherited from upstream layers — `build_run`
([[concepts/reproducibility]]), `run_to_completion`
([[concepts/runner]]), the scheduler's canonical `(t, node_id, seq)`
dispatch order ([[concepts/simulation-design]]), and the append-in-
dispatch-order `EventLogger.records` ([[concepts/event-log-schema]]).
Three local properties reinforce it:

1. **Reducer is a pure function.** Each `summarise(records, result,
   meta)` has no I/O, no clock reads, no RNG draws, no side effects.
2. **Row ordering is total.** Sort by `(protocol, n, run_id, seed)`
   resolves a unique row regardless of input order.
3. **Float formatting is order-stable.** `f"{v:.9f}"` and `f"{v:.6f}"`
   are CPython-deterministic; no locale-aware formatting.

The one impurity surface is `_resolve_commit_hash`'s `subprocess` call
to `git rev-parse`. Tests monkeypatch it to a fixed value to keep CSVs
byte-identical across the test's two runs;
`tests/output/test_baseline_e2e.py` is the gate.

## 11. Extension register

Every column on the canonical schema (§3) not in the today subset (§4)
is registered here with its owning task. Adding a column means: ship
the reducer change, add one row to `COLUMN_ORDER`, and flip the entry
below from `pending` to `live`.

| column(s) | depends-on task | status |
| :--- | :--- | :--- |
| `*_ci_lo`, `*_ci_hi` for every metric | T44 | pending |
| `mempool_msgs_per_acu`, `mempool_tps`, NWT row population on `commit_latency_ms` / `finality_latency_ms` / `tps` / `consensus_msgs_per_acu` / `total_msgs_per_acu` | T38.1 | pending |
| `empirical_epsilon` (Snowman observed ε) | T54 | pending |
| `analytical_epsilon_bound` (Snowman `(1 − α_c/K)^β`) | T54 | pending |
| `byzantine_fraction`, `adversary_strategy` | T51–T54 | pending |
| `network_phase_id` | T19 + T48 | pending |
| `workload_arrival_process`, `workload_tx_bytes`, `workload_conflict_rate`, `workload_offered_rate` | T41 | pending |
| `view_change_or_reorg_count` | T54 | pending |
| `f_max_count`, `f_max_stake` (mutually exclusive per §6 rule 2) | T54 | pending |
| `peak_tps`, `goodput`, `bytes_per_acu`, `per_validator_state_bytes` | T41 + T58 | pending |
| `n_runs` (becomes >1 once T44 sweeps; `success_rate` becomes a frequency, schema unchanged) | T44 | pending |
| `round_latency_ms` | T41 + T48 | pending |

T44 will choose the aggregated-file layout: either `*_ci_lo` /
`*_ci_hi` columns rewritten in place, or a sibling
`baseline_aggregated.csv`. T40 leaves the choice open.

## 12. Cross-references

- [[concepts/metric-reconciliation]] — the binding schema and per-protocol
  formulas.
- [[concepts/evaluation-metrics]] — canonical metric vocabulary.
- [[concepts/event-log-schema]] — raw substrate the writer consumes.
- [[concepts/runner]] — upstream `run_to_completion` seam that returns
  the `(EventLogger, RunResult)` pair the reducer consumes.
- [[concepts/experiment-matrix]] — the parameter space; T41 lifts the
  Python-tuple `SCENARIOS` into YAML configs.
- [[concepts/experiment-matrix-runs]] — the ~2,700-run combinatorial
  budget; the per-trial schema here is the row shape it consumes.
- [[concepts/reproducibility]] — the `(YAML, global_seed) →
  byte-identical` contract this page inherits.
- Inbound expectations from
  [[concepts/adversary-model]] §8 (column-set cross-link),
  [[concepts/adversary-model-runtime]] §6 (register cross-link),
  Chapter 4 plots referenced from [[drafts/ch3_methodology]] §3.5.

## 13. Revisions

(none yet)
