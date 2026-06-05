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
| `seed` | int | — | yes (sweeps 0–19 at T41) | — |
| `workload_arrival_process` | str | — | yes (T41) | — |
| `workload_tx_bytes` | int | bytes | yes (T41) | — |
| `workload_conflict_rate` | float | [0, 1] | yes (T41, =0.0) | — |
| `workload_offered_rate` | float | tx/s | yes (T41) | — |
| `network_phase_id` | str | — | no | T19 + T48 |
| `n_runs` | int | — | no (=1 today) | T44 |
| `commit_hash` | str | — | yes | — |
| `commit_latency_ms` | float | ms | yes (PBFT, FFG, Snowman) | NWT row → T38.1 |
| `finality_latency_ms` | float | ms | yes (PBFT, FFG, Snowman) | NWT row → T38.1 |
| `round_latency_ms` | float | ms | no | T48 |
| `tps` | float | tx/s | yes (PBFT, FFG, Snowman) | NWT row → T38.1 |
| `goodput` | float | tx/s | yes (T41; PBFT/FFG/Snowman) | — |
| `peak_tps` | float | tx/s | no | T58 + capacity model (T41-deferred, §13) |
| `mempool_tps` | float | tx/s | no | T38.1 |
| `consensus_msgs_per_acu` | float | msgs/ACU | yes (PBFT, FFG, Snowman) | NWT row → T38.1 |
| `mempool_msgs_per_acu` | float | msgs/ACU | no | T38.1 |
| `total_msgs_per_acu` | float | msgs/ACU | yes | NWT row → T38.1 |
| `bytes_per_acu` | float | bytes/ACU | yes (T41; est., §13) | — |
| `per_validator_state_bytes` | float | bytes | no | T58 |
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

24 columns, ordered as `COLUMN_ORDER` (T41 added the four `workload_*`
columns plus `goodput` and `bytes_per_acu` to the original 18 — §13):

```
run_id, protocol, n, seed,
workload_arrival_process, workload_tx_bytes, workload_conflict_rate, workload_offered_rate,
commit_hash, t_max,
commit_latency_ms, finality_latency_ms,
tps, goodput,
consensus_msgs_per_acu, total_msgs_per_acu, bytes_per_acu,
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
  **[Superseded post-T70 — see §13 Revisions [2026-06-05].** The two columns
  no longer coincide: T70 finding #1 moved `finality_latency_ms` to the
  `f+1` client `REPLY` round (`pbft_client_finalized`), one network hop past
  the `decided` COMMIT quorum that still defines `commit_latency_ms`. The
  PBFT-only split makes `finality_latency_ms` non-comparable across
  protocols; cross-protocol latency uses `commit_latency_ms`.]**
- `tps = decided_count / result.now`. **T41 re-baseline (§13):** PBFT now
  runs windowed over a fixed `t_max` (fed a continuous arrival stream)
  instead of quiescing after one instance, so `tps` / `consensus_msgs_per_acu`
  / `total_msgs_per_acu` reflect honest windowed values rather than the
  single-shot quiescence-tail figure. `commit_latency_ms` /
  `finality_latency_ms` are unchanged (defined on the *first* decided
  instance).
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
| `workload_arrival_process`, `workload_tx_bytes`, `workload_conflict_rate`, `workload_offered_rate` | T41 | **live** (T41 — §13 Revision) |
| `goodput` | T41 | **live** (T41 — §13 Revision) |
| `bytes_per_acu` | T41 | **live** (T41 — §13 Revision, honest order-of-magnitude estimate) |
| `view_change_or_reorg_count` | T54 | pending |
| `f_max_count`, `f_max_stake` (mutually exclusive per §6 rule 2) | T54 | pending |
| `peak_tps`, `per_validator_state_bytes` | T58 (+ capacity model) | pending — **`peak_tps` deferred at T41**, see §13 |
| `n_runs` (becomes >1 once T44 sweeps; `success_rate` becomes a frequency, schema unchanged) | T44 | pending |
| `round_latency_ms` | T48 | pending |

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

### [2026-06-03] T41 — workload axis lands; PBFT throughput re-baselined; peak_tps deferred

- **`COLUMN_ORDER` grows 18 → 24.** T41 adds the four `workload_*`
  config columns plus `goodput` (committed tx/s) and `bytes_per_acu`
  (honest order-of-magnitude wire-byte budget per ACU, from the
  [[concepts/message-types]] §3–§7 size tables × delivery counts, with
  transaction-carrying types adding `offered_rate · interval · tx_bytes`).
  §3, §4, and the §11 register entries are flipped to `live`. The
  `seed` column now sweeps `0…19` (20 trials per configuration,
  [[concepts/experiment-matrix]] §7) instead of the constant `42`; the
  per-trial file lives at `results/baseline/baseline.csv` and the Snowman
  `n=4` sanity sibling at `results/baseline/snowman_n4_sanity.csv` (one
  row per seed). The flat `results/baseline.csv` is retired.
- **PBFT throughput/overhead re-baselined (§5.1).** PBFT moved from
  single-instance quiescence to a windowed run over a fixed `t_max` fed by
  the arrival stream, so `tps` / `consensus_msgs_per_acu` /
  `total_msgs_per_acu` are now honest windowed values. `commit_latency_ms`
  / `finality_latency_ms` are byte-unchanged (first-decided-instance
  definition). FFG and Snowman landed columns are fully unchanged (block
  content does not perturb their consensus timing).
- **`peak_tps` deferred (was T41 + T58).** The offered-load saturation
  ramp ([[concepts/experiment-matrix]] §6) is **not realizable** on the
  current latency-only model: there is no per-tx/per-byte cost or queue,
  so throughput never saturates as offered load rises and a ramp would
  report a config artifact, not a protocol property. `peak_tps` and
  `per_validator_state_bytes` move to T58 (the former gated on first
  adding a capacity/cost model); `round_latency_ms` stays T48. The fixed
  sub-saturation `offered_rate = 100` tx/s is used and not recalibrated
  (no protocol saturates). See [[concepts/experiment-matrix]] §9 Revision.
- **`bytes_per_acu` is an estimate.** Per [[concepts/message-types]] §7
  the byte budgets are explicitly non-binding order-of-magnitude figures;
  the column is labelled as such on [[experiments/2026-06-03_scaling-baseline]].

### [2026-06-05] Measurement-point split — `commit_latency_ms` is the cross-protocol latency column; `finality_latency_ms` is no longer apples-to-apples

**The contradiction.** T70 finding #1 (PBFT client-observed finality,
[[experiments/2026-06-04_t70-fidelity-fixes]] R1.*) added an `f+1`-matching
`REPLY` round to PBFT only. As a result `finality_latency_ms` is now measured
at the client-reply collector's `pbft_client_finalized` event — one network
hop past the internal `2f+1` COMMIT quorum — while `commit_latency_ms` stays
at the COMMIT quorum (`src/pbft/summarise.py`). §5.1 above was written pre-T70
and still asserts `commit_latency_ms = finality_latency_ms` for PBFT; that
equality is **false in the current dataset**. Every PBFT row in
`results/baseline/baseline.csv` now has `commit_latency_ms` (1000.000003 ms) ≠
`finality_latency_ms` (1000.000004 ms); the per-row magnitudes are tabulated
in [[experiments/2026-06-03_scaling-baseline]] §Revisions. This entry records
the contradiction per the `docs/wiki-spec.md` Revisions rule (new data
contradicts a claim → Revisions, do not silently overwrite); the §5.1 bullet
carries an inline supersession flag pointing here.

**The asymmetry.** Only PBFT carries the client-observation hop. Casper FFG
(§5.2) and Snowman (§5.3) still satisfy `commit_latency_ms =
finality_latency_ms` — neither has an implemented post-commit client round, so
their `finality_latency_ms` is the *internal* finalisation time. Putting all
three protocols' `finality_latency_ms` on one axis therefore compares PBFT's
client-observed timestamp against the other two protocols' internal
timestamps — not apples-to-apples.

**The contract (binding on downstream consumers).**

1. **Cross-protocol latency comparisons use `commit_latency_ms`.** It is the
   only latency column uniformly defined for all three protocols today —
   median per-node time to the first internal `decided` instance — so it is
   the apples-to-apples axis post-T70. This binds the T43 plots and the
   T45/T56 Chapter 4 latency prose: the cross-protocol latency figure and any
   "protocol X is faster than Y" claim are built from `commit_latency_ms`, not
   `finality_latency_ms`.
2. **`finality_latency_ms` is a PBFT-internal refinement only.** Its valid use
   is *within* PBFT — compared against PBFT's own `commit_latency_ms`, where it
   shows the client-observation hop costs exactly one network delay (one
   `decided`→`pbft_client_finalized` tick). It must **not** appear on a
   cross-protocol latency axis until the hop is uniform across protocols (see
   the structural-fix follow-up below).
3. **The fix is structural, not a Chapter 4 footnote.** A committee review
   noted that prose caveats get skipped, so the comparable-column choice lives
   here in the binding schema page that governs figure construction, not as a
   methodology aside in Chapter 4. Chapter 4 still *states* the
   measurement-point difference, but correctness does not depend on the reader
   noticing that sentence.

**Corrected PBFT formulas (supersede the §5.1 bullet).**

- `commit_latency_ms = 1000 · median{r.t : r.event_type == "decided"
  ∧ r.fields["instance_id"] == first}` (the `2f+1` COMMIT quorum) — unchanged.
- `finality_latency_ms = 1000 · median{r.t : r.event_type ==
  "pbft_client_finalized" ∧ r.fields["instance_id"] == first}` (the `f+1`
  client `REPLY` round), falling back to `commit_latency_ms` if a run decided
  but logged no client-finalize (`src/pbft/summarise.py`).

**Making `finality_latency_ms` genuinely uniform** — i.e. adding an
equivalent client-observation hop to Casper FFG and Snowman so the column
becomes cross-protocol comparable — is real code work, scoped as a separate
follow-up in the `TASKS.md` Backlog. Until that lands, contract item 2 holds.
