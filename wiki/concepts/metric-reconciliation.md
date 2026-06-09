# Cross-Protocol Metric Reconciliation

Companion to [[concepts/evaluation-metrics]]. The unified metric schema on
that page is defined family-agnostically; this page resolves the four
structural asymmetries that arise when the schema is instantiated against
the thesis's four-protocol scope — **PBFT** [4], **Casper FFG** [7],
**Snowman** [9] / [ava-docs], and **Narwhal+Tusk** [11].

The asymmetries are not avoidable by a clever metric choice. They follow
from the protocols' own designs. The job of this page is to make the
per-protocol instantiation of each metric explicit so that

- the comparative CSV produced by [[concepts/output-format]] (T40) has
  one well-defined column per metric, computed from a protocol-specific
  formula stated here, and
- no metric in [[concepts/evaluation-metrics]] is left with an implicit
  "behaves like PBFT" reading.

## The four asymmetries

1. **Output structure.** PBFT, Casper FFG, and Snowman produce a totally
   ordered *chain* of blocks; Narwhal+Tusk produces a *DAG* of certificates
   from which Tusk derives a total order [11]. "Per-block" is well defined
   only for the first three; for Narwhal+Tusk the analogous unit is the
   sub-DAG of ancestors committed atomically at an anchor certificate.

2. **Finality regime.** Finality is per-block deterministic in PBFT [4],
   per-epoch deterministic in Casper FFG (two-epoch justify→finalise) [7],
   per-block probabilistic in Snowman (counter `β` with operational
   `ε ≤ (1 − α_c/K)^β`) [9] / [ava-docs], and per-anchor-batch
   deterministic in Narwhal+Tusk (anchor commits a DAG sub-graph) [11]. A
   single "time-to-finality" metric must dispatch on the regime.

3. **Mempool–consensus message split.** PBFT, Casper FFG (FFG vote layer),
   and Snowman have one logical message class per phase. Narwhal+Tusk
   structurally separates the *mempool layer* (data availability — every
   `2f+1`-signed certificate) from the *consensus layer* (Tusk anchor
   commit, which costs **zero additional messages** because order is
   derived from existing DAG references) [11]. Reporting Narwhal's
   "messages per block" without that split conflates two layers with
   different scaling behaviour.

4. **Snowman parameter rescaling.** Production Snowman uses `K=20`,
   `α_c ≈ 0.8·K = 16`, `α_p = ⌊K/2⌋+1 = 11`, `β = 15` on a validator
   set in the thousands [ava-docs]. The thesis sweeps `n ∈ {4, 7, 10,
   16, 25}` (T41), so production `K=20` is incoherent below `n=21`. The
   rescaling rule is defined in §Snowman parameter rescaling below and
   is the only legitimate way to put Snowman on the same axes as the
   other three protocols at thesis-scale `n`.

## Unit of progress

Every metric in [[concepts/evaluation-metrics]] that ends in
"…per block" needs a per-protocol unit. Define the *atomic commit unit*
(ACU) as the smallest contiguous set of transactions that the protocol
commits indivisibly. Then "per block" is read as "per ACU" everywhere
downstream of this page.

| Protocol | ACU | Cardinality per protocol round | Source |
| :---- | :---- | :---- | :---- |
| PBFT | one block | 1 per three-phase commit | [4] |
| Casper FFG | one finalised checkpoint (= 1 block at the slot the checkpoint pins, plus its ancestors back to the previous finalised checkpoint) | 1 every 2 epochs (justify → finalise) | [7] |
| Snowman | one block | 1 per Snowball decision (counter `β` reached) | [9], [ava-docs] |
| Narwhal+Tusk | one anchor-batch (the anchor certificate plus all its DAG ancestors not committed by a prior anchor) | 1 per anchor period of `r` DAG rounds | [11] |

ACU is the denominator used by all of `messages_per_block`,
`bytes_per_block`, and the throughput metrics' "per block" variants in
[[concepts/evaluation-metrics]].

## Finality semantics

`time_to_finality` is wall-clock from transaction submission to the
*protocol-specific finality event* below. Reporting time-to-finality
without naming the event is the chief vocabulary fragmentation flagged
in [15] and [16]; this table closes it.

| Protocol | Finality event | Regime | Source |
| :---- | :---- | :---- | :---- |
| PBFT | `2f+1` `COMMIT` messages collected for the block containing the transaction | per-block deterministic | [4] |
| Casper FFG | the checkpoint that pins the block containing the transaction becomes finalised (= it is justified *and* its direct-child checkpoint is justified) | per-epoch deterministic; latency `≥ 2 epochs` | [7] |
| Snowman | the Snowball counter reaches `β` on the block containing the transaction at the operational `α_c, K, β` | per-block probabilistic; report `ε ≤ (1 − α_c/K)^β` alongside | [9], [ava-docs] |
| Narwhal+Tusk | the certificate containing the transaction is a DAG ancestor of a committed anchor certificate | per-anchor-batch deterministic | [11] |

**Reporting rule for Snowman.** Every Snowman run logs both the empirical
`ε` (count of conflicting decisions across seeds) and the analytical
`ε ≤ (1 − α_c/K)^β` for the run's parameters. Comparative tables that
suppress one of the two are ambiguous: an empirical zero at low Byzantine
fraction is compatible with `ε`-bounds that range over many decades.

**End-to-end commit latency** (§Latency in [[concepts/evaluation-metrics]])
is *separately* defined per protocol as wall-clock from transaction
submission to the transaction's first inclusion in any committed-or-to-be-
committed block. For PBFT this coincides with finality; for the other three
it does not. The gap between commit and finality is itself an RQ1-relevant
quantity.

## Narwhal mempool-consensus message split

[[concepts/evaluation-metrics]] §Overhead defines `messages_per_block`
and `bytes_per_block`. For Narwhal+Tusk these decompose into two layers
with different scaling behaviour [11].

| Layer | Role | Per-ACU cost |
| :---- | :---- | :---- |
| **Mempool** (Narwhal) | Each validator publishes one certificate per DAG round; certificate completion requires `2f+1` signatures attesting availability of contents. Carries transaction payload bytes. | `r · n` certificates × `(1 broadcast + 2f+1 signature replies)` ≈ `O(r · n²)` messages per anchor-batch. Bytes dominated by transaction payload. |
| **Consensus** (Tusk) | Anchor commit deterministically derives total order from existing DAG references — no new messages. | `0` additional messages per anchor-batch. |

Reporting rule:

- `messages_per_block` for Narwhal+Tusk is reported as **two CSV
  columns**: `mempool_msgs_per_acu` and `consensus_msgs_per_acu`. The
  combined total is also reported as `total_msgs_per_acu` for
  cross-protocol comparison.
- The other three protocols populate `mempool_msgs_per_acu = 0` and put
  the entire cost in `consensus_msgs_per_acu`. This is not double
  counting: it is the convention that lets the schema admit either
  layered or single-layer protocols without conditional formulae.
- `bytes_per_block` follows the same split. Mempool bytes carry payload;
  consensus bytes do not. PBFT/Casper FFG/Snowman put payload bytes in
  `consensus_bytes_per_acu` because no separate mempool exists.

Without this split, Narwhal's reported "messages per block" is either
overstated (counting all mempool traffic as consensus) or understated
(reporting only the zero-cost Tusk layer). Both are seen in the
literature; survey [15] explicitly calls this out.

## Snowman parameter rescaling

Production Snowman runs on a validator set in the thousands with
`(K, α_p, α_c, β) = (20, 11, 16, 15)` [ava-docs]. The thesis sweeps
`n ∈ {4, 7, 10, 16, 25}` (T41). The first four points violate `K ≤ n−1`
at production parameters, so the simulator must rescale. The rule below
is the only rescaling used; it is deterministic in `n` and reproducible
across seeds.

**Rescaling rule.**

```
K   = min(20, n − 1)            # sample size; exclude self
α_p = ⌊K / 2⌋ + 1               # preference-flip threshold
α_c = ⌈0.8 · K⌉                 # confidence-counter threshold
β   = 15                        # consecutive-agreement threshold (unchanged)
```

**Rationale.**

- `K ≤ n − 1` is structural: a validator cannot sample more peers than
  exist (and does not sample itself).
- Holding `α_c/K ≈ 0.8` preserves the *shape* of the safety bound
  `ε ≤ (1 − α_c/K)^β`. At small `n` the ratio is forced higher than 0.8
  by ceiling — `α_c = ⌈0.8·K⌉` rounds up — so empirical `ε` will be at
  least as small as production.
- Holding `β = 15` keeps the safety-probability exponent fixed across `n`
  so that Snowman's probabilistic-finality semantics stay comparable to
  the production reference [ava-docs].

**Resulting parameter table for the T41 sweep.**

| `n` | `K` | `α_p` | `α_c` | `α_c/K` | `ε ≤ (1 − α_c/K)^β` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 4 | 3 | 2 | 3 | 1.000 | 0 (degenerate — unanimous) |
| 7 | 6 | 4 | 5 | 0.833 | ≈ 6.5·10⁻¹² |
| 10 | 9 | 5 | 8 | 0.889 | ≈ 4.4·10⁻¹⁴ |
| 16 | 15 | 8 | 12 | 0.800 | ≈ 3.0·10⁻¹¹ |
| 25 | 20 | 11 | 16 | 0.800 | ≈ 3.0·10⁻¹¹ |

**Comparative-claim exclusion at `n = 4`.** At `n = 4` the rescaling
collapses Snowman to flood-vote-with-counter — every poll queries every
peer, `α_c = K` demands unanimity, and the analytical `ε` is zero. This
parametrisation is **not** Snowman; it is the degenerate boundary of
the rescaling rule. Comparative tables under RQ1–RQ5 **exclude** the
Snowman row at `n = 4`. The point is reported once, in a dedicated
"rescaling sanity check" appendix subsection, to confirm the rule
reduces to its boundary cleanly. PBFT, Casper FFG, and Narwhal+Tusk are
reported at `n = 4` as usual; the per-`n` plots simply carry no Snowman
data point at that abscissa.

**Adjacent margin at `n = 7`.** The risk re-emerges weakly: at `n = 7`,
`α_c/K = 5/6 ≈ 0.833 > 0.8`, so Snowman is *near* the unanimity
boundary but not at it. The `n = 7` Snowman row is **included** in
comparative tables but flagged in Chapter 4 with a margin note
surfacing its `α_c/K` against the production `0.8`. From `n ≥ 10`
onward `α_c/K ≤ 0.889` and the rescaling is in its normal regime.

The simulator must emit `α_c/K` on every Snowman row in the CSV (column
already pinned in §T40 CSV schema implications) so the comparative
plotting code can drop or annotate rows automatically rather than
relying on the analyst to remember.

## Calibration defaults

Per-protocol knobs — Casper FFG slot length, Narwhal+Tusk anchor period
`r`, Snowman `β`, PBFT view-change timeout — move per-ACU costs and
time-to-finality by orders of magnitude *within a single protocol*.
Without committed defaults the cross-protocol comparison is
parameter-engineered: pick a different `r` or `slots_per_epoch` and the
verdict changes. This section pins the simulator's defaults and the
per-RQ sensitivity sweep that defends each verdict against the
criticism "your numbers depend on knob choice".

**Discipline.** Defaults are committed *at the metric-reconciliation
layer*, before any baseline experiment runs. T19
([[concepts/experiment-matrix]], forward link) consumes them as the
baseline configuration. Sensitivity sweeps execute *after* baseline;
they never feed back into default selection.

| Protocol | Knob | Paper value | Simulator default | Sensitivity sweep |
| :---- | :---- | :---- | :---- | :---- |
| **PBFT** | view-change timeout | adaptive [4] | `3 · E[round_latency]` | `{2, 3, 5, 10} · E[round_latency]` |
| **Casper FFG** | slots per epoch | 32 [8] | **4** | `{4, 8, 16, 32}` |
| **Casper FFG** | slot duration | 12 s [8] | **100 ms** | `{50, 100, 500} ms` |
| **Snowman** | `K`, `α_p`, `α_c` | (20, 11, 16) [ava-docs] | rescaling rule per `n` — see §Snowman parameter rescaling | — |
| **Snowman** | `β` | 15 [ava-docs] | **15** (production-parity; the cross-protocol comparison baseline) | RQ4-only safety regime: `{3, 5}` (see constraint below) |
| **Narwhal+Tusk** | anchor period `r` | 2 [11] | **2** | `{2, 4, 8}` |

Two defaults deliberately diverge from paper values, both on Casper
FFG. `slots_per_epoch = 4` (vs Ethereum's 32 [8]) is the smallest value
preserving FFG's epoch character — multiple slots per epoch, the
two-epoch justify→finalise structure, the LMD-GHOST-vs-FFG-layer
separation. `slot_duration = 100 ms` (vs Ethereum's 12 s [8]) keeps FFG
finality at ~800 ms — the same order of magnitude as Snowman `β` rounds
and Narwhal+Tusk `r` rounds — so cross-protocol latency plots are
readable on a single axis. The divergence is **for comparison fairness,
not tractability**: the four protocols must occupy comparable per-ACU
and wall-clock scales for the Chapter 4 verdicts to be defendable. The
`{16, 32}` and `{500 ms}` ends of the sensitivity sweep confirm whether
the comparative ordering survives the trip to production scale.

**Coherence constraint on FFG experiments.** The `slot_duration = 100
ms` default is incoherent with a network phase where `E[delay] ≫ 100
ms`: under such a phase, FFG attestations from distant validators
arrive *after* the slot boundary and the protocol is perpetually in a
degraded-finality regime that is not Casper FFG. **Any T19 experiment
matrix that pairs FFG with the `100 ms` default must use a network
phase ([[concepts/network-model-phases]]) where `E[delay] ≪
slot_duration`** — operationally `E[delay] ≤ slot_duration / 4`. FFG
experiments at WAN-scale delays must use the `slot_duration = 500 ms`
sensitivity-sweep point (or larger), not the baseline. T19 owns this
pairing decision; the simulator runner must refuse to start an FFG run
with an incoherent pairing rather than silently produce
degraded-finality numbers labelled as FFG.

The Snowman `β ∈ {3, 5}` regime is included **only** to make empirical
`ε` observable for RQ4 (safety degradation under adversary). At
production `β = 15` the analytical bound `(1 − α_c/K)^15` makes safety
violations unobservable in thesis-feasible trial counts; the RQ4-only
regime exists to give RQ4 a measurable Snowman safety column. `β = 15`
remains the cross-protocol comparison baseline.

**Constraint on cross-protocol throughput comparison.** Snowman `tps`,
`goodput`, `peak_tps`, and `mempool_tps` rows used in cross-protocol
comparison tables (RQ1, RQ2, RQ3, RQ5) **must** carry `β = 15`. At
`β = 3` Snowman's per-validator consensus cost is `O(K·3)` not
`O(K·15)`, so a ~5× apparent throughput advantage opens against PBFT
that disappears at the safety-equivalent `β`. Chapter 4 reports
`β ∈ {3, 5}` Snowman numbers *separately* under RQ4 and **never**
combines them with other protocols on a throughput axis. The CSV column
`beta` (per §T40 CSV schema implications) makes this auditable on every
row.

### Sensitivity-sweep policy

Sweep the one or two knobs most likely to bias each RQ's verdict, not
every knob in every experiment.

| RQ | Sweep knob(s) | Why |
| :---- | :---- | :---- |
| RQ1 (delay scaling) | network delay distribution (IS the RQ axis) | No additional knob sweep. |
| RQ2 (Byzantine load) | Byzantine fraction (IS the RQ axis) | No additional knob sweep. |
| RQ3 (validator-set `n`) | FFG `slots_per_epoch`; Narwhal+Tusk `r` | Per-ACU costs are most sensitive to these knobs along the `n` axis. |
| RQ4 (adversarial strategy) | Snowman `β ∈ {3, 5, 10, 15}` | Makes empirical `ε` observable; closes the safety-unobservability gap. |
| RQ5 (Pareto synthesis) | inherits RQ3 sensitivity data | Verdict is reported as a Pareto *region* across the sweep, not a single point. |

A comparative verdict is reported as **robust** iff the protocol
ordering on the primary metric is preserved across the full sensitivity
sweep for that RQ. Verdicts that flip across the sweep are reported as
**knob-sensitive** and the Chapter 4 discussion surfaces the crossover
point rather than picking a winner.

## Per-protocol applicability matrix

For every metric in [[concepts/evaluation-metrics]], the following four
tables give either an explicit per-protocol formula or an explicit
`N/A (reason)` entry. The CSV column names referenced in §T40 CSV schema
below are the ones a downstream implementation can use unchanged.

### Latency

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :---- | :---- | :---- | :---- | :---- |
| End-to-end commit latency | tx submit → containing block enters `PRE-PREPARE` and persists through commit | tx submit → containing block proposed at next slot | tx submit → containing block enters the protocol's preference set | tx submit → containing batch enters a `2f+1`-signed certificate |
| Time-to-finality | tx submit → `COMMIT` quorum (same block) | tx submit → checkpoint containing tx finalised (`≥ 2 epochs` later) | tx submit → counter `β` reached on containing block (report with `ε`) | tx submit → containing certificate is a DAG ancestor of a committed anchor |
| Round latency | one of three phases | one slot | one Snowball poll of `K` peers | one DAG round (publish + collect `2f+1` parents) |

### Throughput

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :---- | :---- | :---- | :---- | :---- |
| Transactions per second (`tps`) | committed-tx count / wall-clock window | finalised-tx count / wall-clock window | counter-`β`-accepted tx count / wall-clock window | anchor-committed tx count / wall-clock window |
| Goodput | identical to `tps` (no reorg-before-finality) | `tps` restricted to tx whose containing checkpoint *survives to finalisation* (LMD-GHOST reorgs subtract) [8] | `tps` (reorg post-`β` bounded by `ε`; reported separately) | `tps` restricted to tx whose certificate appears in a committed anchor-batch (orphan certificates subtract) |
| Peak throughput | sustained `tps` before queueing diverges | sustained `tps` before attestation backlog stalls finalisation | sustained `tps` before per-validator `O(K·β)` cost saturates the round budget | sustained `tps` before DAG retention or `2f+1`-signature collection stalls |
| Mempool throughput (`mempool_tps`) | `0` (no separate mempool layer) | `0` | `0` | certificate-included tx count / wall-clock window [11] |

### Overhead

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :---- | :---- | :---- | :---- | :---- |
| `consensus_msgs_per_acu` | `1 + 2·n + 2·n² ≈ O(n²)` (PRE-PREPARE + PREPARE + COMMIT) [4] | simulator (per FFG paper [1]): `O(n²)` — `n` individually-signed votes broadcast all-to-all per epoch; measured `≈1.125n` per-ACU. Production (BLS-aggregated): `O(n)`. Aggregation not modelled — see [[algorithms/pos#communication-complexity]] | `O(K·β)` per validator (queries + replies); independent of `n` [9], [ava-docs] | `0` (Tusk derives order from existing DAG references) [11] |
| `mempool_msgs_per_acu` | `0` (no separate mempool layer) | `0` (block-proposal layer carries payload; not a separate mempool) | `0` | `O(r · n²)` over `r` rounds × `n` certificates × `2f+1` signatures [11] |
| `bytes_per_block` | dominated by signatures × `O(n²)` | simulator: per-validator (un-aggregated) attestation + payload per slot, `O(n²)`; production BLS would amortise to one aggregate per committee | `O(K·β)` query/reply bytes per validator | dominated by mempool payload bytes; consensus layer adds none |
| `per_validator_state` | vote caches + view-change log; `O(n)` per recent block | attestation buffers per slot + finalised-checkpoint chain | Snowball preference + counter per pending block; independent of `n` | full DAG retention until pruned at anchor commit — **largest of the four** |

### Reliability

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :---- | :---- | :---- | :---- | :---- |
| Consensus success rate | fraction of rounds reaching `COMMIT` quorum; spurious view changes count as failures | fraction of epoch boundaries producing a justified→finalised pair | fraction of pending blocks reaching counter `β` within a time budget | fraction of anchor rounds where the anchor certificate commits |
| Fork rate | `0` by construction (categorical finality) | fraction of proposed blocks reorged in the block-proposal layer before their checkpoint is finalised — meaningful and central [8] | pre-`β` preference-switch rate (post-`β` reorg bounded by `ε`, reported separately) | certificate orphan rate (certificates produced but never appearing in a committed anchor-batch) |
| View-change / reorg frequency | view-change count per unit wall-clock | LMD-GHOST reorg count per epoch, depth-attributed [8] | `N/A` (no view changes; no post-finality reorgs — pre-`β` preference flips logged separately) | `N/A` (no view changes; failed-anchor-commit count logged separately as pipeline-extension events) |
| Safety-violation probability `ε` | `0` below threshold; measured above | `0` below `1/3` stake; measured above; slashing cost recorded separately | both analytical `ε ≤ (1 − α_c/K)^β` and empirical violation rate; *primary* metric for this family [9], [10], [ava-docs] | `0` below threshold; measured above |
| Fault-tolerance threshold (`f_max`) | empirical `f_max_count`; theoretical `< n/3`; `f_max_stake = NaN` | empirical `f_max_stake`; theoretical `< 1/3` of stake [7]; `f_max_count = NaN` | empirical `f_max_count`; parameter-dependent on `α_c/K` and `β`; no fixed `1/3` analogue [9], [10]; `f_max_stake = NaN` | empirical `f_max_count`; theoretical `< n/3` [11]; `f_max_stake = NaN` |

## T40 CSV schema implications

T40 ([[concepts/output-format]], forward link) defines the comparative
CSV. This page fixes the per-protocol formulas it must compute. The
schema implied by the matrix above is:

```
run_id, protocol, n, byzantine_fraction, adversary_strategy, seed,
  # workload (T19 contract; required, no NaN allowed)
  workload_arrival_process, workload_tx_bytes,
  workload_conflict_rate, workload_offered_rate,
  # network phase (T15 + T19 contract; references the phase active
  # for this row in the experiment's phase timeline)
  network_phase_id,
  # reproducibility (T27 + T66 contract; required)
  n_runs, commit_hash,
  # latency (ms; mean over n_runs)
  commit_latency_ms, finality_latency_ms, round_latency_ms,
  # throughput (tx/s; mean over n_runs)
  tps, goodput, peak_tps, mempool_tps,
  # overhead (per ACU; mean over n_runs)
  consensus_msgs_per_acu, mempool_msgs_per_acu, total_msgs_per_acu,
  bytes_per_acu, per_validator_state_bytes,
  # reliability (mean over n_runs)
  success_rate, fork_rate, view_change_or_reorg_count,
  empirical_epsilon, analytical_epsilon_bound,
  f_max_count, f_max_stake,
  # snowman-specific (NaN for other protocols)
  K, alpha_p, alpha_c, beta, alpha_c_over_K
```

`finality_latency_ms`, `empirical_epsilon`, and `analytical_epsilon_bound`
populate via the per-protocol formulas in §Finality semantics. The Snowman
parameter columns are required by §Snowman parameter rescaling and are
left `NaN` for the other three protocols. Exactly one of `f_max_count`
and `f_max_stake` is populated per row; the other is `NaN`. The choice
is determined by the protocol's fault-attribution model (count for
PBFT/Snowman/Narwhal+Tusk; stake for Casper FFG).

The `workload_*` columns are T19's contract
([[concepts/experiment-matrix]] — forward link); every row **must**
populate all four (no `NaN`). Throughput and goodput metrics are
undefined without them. `network_phase_id` references a phase declared
in the T15 phase timeline ([[concepts/network-model-phases]]) so a
row's network regime can be reconstructed without duplicating the full
delay/drop/partition config on every row.

Every metric column above is the **mean over `n_runs` seeded trials**
at the row's full configuration. Confidence intervals are **required**
for cross-protocol comparison and **must** be surfaced — either as
per-metric `*_ci_lo` / `*_ci_hi` columns added by T40 alongside the
means, or as a sibling per-trial CSV consumed by the Chapter 4
plotting layer. T40 chooses the layout; T44 pins the CI computation
method (default 95% CI via the `t`-distribution; non-parametric
bootstrap permitted for metrics whose empirical distribution is
non-normal). `commit_hash` is the simulator-source git hash at the
time of the run — T27 + T66 reproducibility contract.

This is the minimum column set that satisfies the verify gate of T9.1
("T40 CSV schema can be expressed in terms defined here"). T40 may add
columns (e.g., adversary intensity, network-delay distribution
parameters) but must not drop any column above without re-opening the
reconciliation.

## Cross-references

- Canonical metric definitions: [[concepts/evaluation-metrics]].
- Per-family protocol detail: [[algorithms/pbft]], [[algorithms/pos]],
  [[algorithms/avalanche]], [[algorithms/dag-based]].
- RQ↔metric map (unchanged by this page): [[concepts/research-questions]].
- Downstream CSV schema: [[concepts/output-format]] (T40, forward link).
- Downstream adversary catalogue (T18 will use the per-protocol semantics
  rows in §Reliability and §Finality semantics): forward link.

## Sources

Primary citations in this reconciliation:

- [4] [[sources/2026-04-21_castro-liskov-pbft-1999]] — PBFT three-phase
  commit; per-block deterministic finality; `O(n²)` per-block messaging.
- [7] [[sources/2026-04-21_buterin-griffith-casper-ffg-2017]] — Casper
  FFG; two-round justify→finalise at epoch granularity; finality regime
  source.
- [8] [[sources/2026-04-21_buterin-gasper-2020]] — Gasper; LMD-GHOST
  fork choice and the reorg-before-finality regime that makes goodput
  distinct from `tps` for this family.
- [9] [[sources/2026-04-21_team-rocket-avalanche-2019]] — Avalanche;
  `(K, α, β)` parameters and the `ε ≤ (1 − α_c/K)^β` safety bound.
- [10] [[sources/2026-04-21_amores-sesar-avalanche-analysis-2024]] —
  Formal re-analysis; sharper threshold conditions used in the
  `f_max` row.
- [11] [[sources/2026-04-21_danezis-narwhal-tusk-2022]] — Narwhal+Tusk;
  mempool/consensus split; anchor-batch atomic commit unit.
- `[ava-docs]` — Ava Labs documentation; production Snowman parameters
  used as the rescaling target. Per
  [[concepts/annotated-bibliography]] §citation-policy this is a
  weaker citation pending primary-source corroboration, but it is the
  only documented source for production `(K, α_p, α_c, β)`.

`[15]`, `[16]` provide framing for the asymmetries this page reconciles
and are catalogued in [[concepts/annotated-bibliography]].

## Revisions

None.
