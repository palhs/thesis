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

**Simulator note (2026-06-14).** For **Casper FFG and Snowman** the
commit↔finality gap is *unpopulated*: `finality_latency_ms == commit_latency_ms`
on every FFG and Snowman row of `results/{baseline,delay}/*.csv`. This is a
**modelling choice, not a defect** — the FFG and Snowman reducers
(`src/pos/summarise.py`, `src/snowman/summarise.py`) emit a single finalisation
`decided` event and model no distinct pre-final "commit" state, so the two
latencies coincide by construction. **PBFT is the exception:** its reducer
(`src/pbft/summarise.py`, T70) emits a distinct `pbft_client_finalized` event,
so `finality_latency_ms` (the `f+1` client `REPLY`) is strictly greater than
`commit_latency_ms` (the `2f+1` `COMMIT` quorum) on every PBFT row — a
near-instant hop at the zero-delay baseline (≈ 10⁻⁶ ms) that grows to
tens–hundreds of ms under network delay (`delay.csv`). The genuine multi-epoch
(FFG, ≥ 2 epochs) and multi-`β` (Snowman, `β` poll rounds) finality lag this
section describes is therefore **not yet measured for FFG or Snowman** — any
Chapter 4 commit-vs-finality comparison must treat their `finality_latency_ms`
as a commit-time proxy until a distinct finality event is implemented (standing
Backlog item, 2026-06-14). **[Superseded — see Relabel (T71, 2026-06-15)
immediately below: finality IS already measured by `commit_latency_ms`; the
unmeasured quantity is the *earlier reversible* inclusion milestone, not
finality.]** See §Revisions [2026-06-14]. [4], [7], [9]

**Relabel (T71, 2026-06-15) — what is mislabelled, and which direction the gap
points.** The framing above is correct that a commit↔finality gap exists at the
*metric* level, but it mislocates which column is the proxy. The simulator's
`decided` event fires at each protocol's **irreversibility (finality)**
milestone, not at reversible inclusion: PBFT `2f+1` `COMMIT`, FFG the
**finalised** checkpoint (`src/pos/node.py::_finalise`, justify→finalise,
`≥ 2` epochs — *not* block inclusion), Snowman counter-`β` acceptance. So
`commit_latency_ms` (median time-to-first-`decided`) already **is**
time-to-finality for all three; it is the column that is misnamed, and it is
the canonical cross-protocol *time-to-finality* axis (the basis of the valid
T48/T49 comparison). `finality_latency_ms` is **not** an upgradeable
commit-proxy: for FFG/Snowman it is a structural duplicate of
`commit_latency_ms`, and it is retracted to PBFT-only client-observed finality.
The quantity genuinely *unmeasured* for FFG/Snowman is the **earlier,
reversible** commit/inclusion milestone (FFG block inclusion before
finalisation, Snowman pre-`β` first-poll preference) — it lies *before*
`decided`, not after, and is the deferred Path A enrichment, **not** a finality
event to be added after `decided` (that would double-count). The
nature-of-milestone caveat stands: FFG finality is accountable-deterministic,
Snowman finality is probabilistic-with-`ε ≤ (1 − α_c/K)^β`; the `ε` columns
remain the Family-C (T51+) deferral. Binding contract: [[concepts/output-format]]
§13 Revisions [2026-06-15]. See §Revisions [2026-06-15] below. [4], [7], [9]

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
| 7 | 6 | 4 | 5 | 0.833 | ≈ 2.1·10⁻¹² |
| 10 | 9 | 5 | 8 | 0.889 | ≈ 4.9·10⁻¹⁵ |
| 16 | 15 | 8 | 12 | 0.800 | ≈ 3.3·10⁻¹¹ |
| 25 | 20 | 11 | 16 | 0.800 | ≈ 3.3·10⁻¹¹ |

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
| **Casper FFG** | slots per epoch | 32 [8] | **2** | `{2, 4, 8, 16}` |
| **Casper FFG** | slot duration | 12 s [8] | **1 s** | `{0.5, 1, 2} s` |
| **Snowman** | `K`, `α_p`, `α_c` | (20, 11, 16) [ava-docs] | rescaling rule per `n` — see §Snowman parameter rescaling | — |
| **Snowman** | `β` | 15 [ava-docs] | **15** (production-parity; the cross-protocol comparison baseline) | RQ4-only safety regime: `{3, 5}` (see constraint below) |
| **Narwhal+Tusk** | anchor period `r` | 2 [11] | **2** | `{2, 4, 8}` |

The simulator's two Casper FFG defaults diverge from paper values.
`slots_per_epoch = 2` (vs Ethereum's 32 [8]) is the smallest value
preserving FFG's epoch character — a multi-slot epoch, the two-epoch
justify→finalise structure, the LMD-GHOST-vs-FFG-layer separation.
`slot_duration = 1 s` (vs Ethereum's 12 s [8]) is a round, legible
wall-clock cadence about an order of magnitude below production while
keeping the epoch structure intact. The resulting per-epoch finality is
`(2·slots_per_epoch + attest_offset)·slot_duration = (4 + 1)·1 s ≈ 5 s`
(`attest_offset = slots_per_epoch // 2 = 1`) — roughly 5× the per-block
protocols' ≈1 s commit. That gap is **not** calibrated away: it is
reported as a genuine RQ1 finding (Chapter 4 §4.2.2) about FFG's coarser
epoch-granularity finality, the coupling Ethereum's 12 s slot reflects in
the extreme. The `{8, 16}`-slot and `{2 s}` ends of the sensitivity sweep
test whether the comparative ordering survives the trip toward production
scale (32 slots / 12 s). (The original design pinned `4`/`100 ms` for a
~1 s FFG finality readable on a single axis with the other protocols; the
implementation and every run instead used `2`/`1 s` — see
[[#revisions]].)

**Coherence constraint on FFG experiments.** The `slot_duration = 1 s`
default is incoherent with a network phase where `E[delay] ≫ 1 s`:
under such a phase, FFG attestations from distant validators arrive
*after* the slot boundary and the protocol is perpetually in a
degraded-finality regime that is not Casper FFG. **Any T19 experiment
matrix that pairs FFG with the `1 s` default must use a network phase
([[concepts/network-model-phases]]) where `E[delay] ≪ slot_duration`**
— operationally `E[delay] ≤ slot_duration / 4`, so the `1 s` default is
coherent up to `E[delay] ≈ 250 ms` (covering Families A and C and the
`static-baseline` network). FFG experiments at larger delays rescale the
slot upward by `slot_duration ≥ 4·E[delay]` (the per-timeline pairing in
[[concepts/experiment-matrix-runs]] §2), not the baseline value. T19 owns
this pairing decision; the simulator runner must refuse to start an FFG
run with an incoherent pairing rather than silently produce
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

**Column ↔ metric mapping (T71, 2026-06-15) — read this before cloning the
table into a draft.** This table is the *metric* taxonomy: "End-to-end commit
latency" (reversible inclusion) and "Time-to-finality" (irreversibility) are
genuinely distinct rows. But the **implemented CSV columns do not map to them
by name.** The `commit_latency_ms` column implements the **Time-to-finality**
row, *not* End-to-end commit latency — the simulator's `decided` event (which
the column keys on) fires at each protocol's irreversibility milestone (PBFT
`2f+1` `COMMIT`, FFG the finalised checkpoint, Snowman counter-`β`; see
§Finality semantics §Relabel). The `finality_latency_ms` column is retracted to
**PBFT-only** client-observed finality and is a structural duplicate of
`commit_latency_ms` for FFG/Snowman. The **End-to-end commit latency** row above
(the *earlier, reversible* inclusion milestone) is **not implemented as any CSV
column today** — it is the deferred Path A enrichment. Do not infer
"`commit_latency_ms` = inclusion" from the column name. Binding contract:
[[concepts/output-format]] §13 Revisions [2026-06-15].

### Throughput

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :---- | :---- | :---- | :---- | :---- |
| Transactions per second (`tps`) | committed-tx count / wall-clock window | finalised-tx count / wall-clock window | counter-`β`-accepted tx count / wall-clock window | anchor-committed tx count / wall-clock window |
| Goodput | identical to `tps` (no reorg-before-finality) | `tps` restricted to tx whose containing checkpoint *survives to finalisation* (LMD-GHOST reorgs subtract) [8] | `tps` (reorg post-`β` bounded by `ε`; reported separately) | `tps` restricted to tx whose certificate appears in a committed anchor-batch (orphan certificates subtract) |
| Peak throughput | sustained `tps` before queueing diverges | sustained `tps` before attestation backlog stalls finalisation | sustained `tps` before per-validator `O(K·β)` cost saturates the round budget | sustained `tps` before DAG retention or `2f+1`-signature collection stalls |
| Mempool throughput (`mempool_tps`) | `0` (no separate mempool layer) | `0` | `0` | certificate-included tx count / wall-clock window [11] |

**Simulator note (2026-06-14) — `tps` and `goodput` are on different bases.**
As implemented, `tps = len(decided) / window` (`src/{pbft,pos,snowman}/
summarise.py`): a *decided-event rate*, not a committed-application-tx rate.
Its granularity is protocol-dependent — PBFT and Snowman decide per block,
Casper FFG decides per finalised epoch — so in `results/baseline/baseline.csv`
`tps` is exactly `0.95·n` for PBFT and Snowman but `0.40·n` for Casper FFG, an
artefact of per-block vs per-epoch crediting, not a like-for-like throughput.
`goodput`, by contrast, is the committed-application-tx rate (`committed_tx /
window`, `src/output/metrics.py`), flat in `n` (workload-driven), with mean
`94.82` tx/s for PBFT/Snowman and `79.635` tx/s for Casper FFG (×1.19). Two
consequences for the rows above: (i) `goodput ≫ tps` numerically (e.g. FFG at
`n=10`: `tps=4.0` vs `goodput≈79.6`), so the "Goodput = `tps` restricted to
surviving tx" framing does not describe the implemented metrics — they measure
different quantities, not subsets; (ii) the Casper FFG goodput shortfall is
**not** "LMD-GHOST reorgs subtracting": LMD-GHOST fork choice and reorgs are
*not implemented* and `fork_rate = 0` on every row
([[algorithms/pos#simulator-mapping]]). The FFG shortfall traces instead to
its epoch-paced finalisation accounting (`n_opportunities = n_epochs ×
slots_per_epoch` over *finalised* epochs only, `src/pos/summarise.py`) — FFG
finalises fewer application-tx opportunities inside the window, which is partly
legitimate (slower finality), not reorg loss. **Any cross-protocol throughput
axis must use `goodput`, never `tps`.** See §Revisions [2026-06-14]. [7], [8]

### Overhead

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :---- | :---- | :---- | :---- | :---- |
| `consensus_msgs_per_acu` | per-instance `2(n²−1)` deliveries — all-to-all PREPARE + COMMIT `2n(n−1)` plus PRE-PREPARE + client `REPLY` `2(n−1)`, primary self-excluded; per-ACU `(2n²−2)/n = 2n − 2/n` after dividing by the `I·n` decided events (CSV-exact: 7.5 / 13.71 / 19.8 / 31.88 / 49.92 at `n = 4/7/10/16/25`). Traffic is `O(n²)` *per committed instance*; the `≈2n` per-ACU figure is that quadratic traffic normalised by an `n`-scaled decided-event denominator, **not** linear scaling — see §Revisions [2026-06-14] [4] | simulator (per FFG paper [1]): `O(n²)` — `n` individually-signed votes broadcast all-to-all per epoch; analytical `≈1.125n` per-ACU, measured slope `≈1.15n` (fit `1.145n + 0.7`; see §Revisions [2026-07-02]). Production (BLS-aggregated): `O(n)`. Aggregation not modelled — see [[algorithms/pos#communication-complexity]] | `O(K·β)` per validator (queries + replies); independent of `n` [9], [ava-docs] | `0` (Tusk derives order from existing DAG references) [11] |
| `mempool_msgs_per_acu` | `0` (no separate mempool layer) | `0` (block-proposal layer carries payload; not a separate mempool) | `0` | `O(r · n²)` over `r` rounds × `n` certificates × `2f+1` signatures [11] |
| `bytes_per_block` | dominated by signatures × `O(n²)` | simulator: per-validator (un-aggregated) attestation + payload per slot, `O(n²)`; production BLS would amortise to one aggregate per committee | `O(K·β)` query/reply bytes per validator | dominated by mempool payload bytes; consensus layer adds none |
| `per_validator_state` | vote caches + view-change log; `O(n)` per recent block | attestation buffers per slot + finalised-checkpoint chain | Snowball preference + counter per pending block; independent of `n` | full DAG retention until pruned at anchor commit — **largest of the four** |

**Simulator note (2026-06-14) — `bytes_per_acu` is payload-dominated, not
signature/`O(n²)`-dominated.** The `bytes_per_block` row predicts the byte axis
tracks each protocol's message-complexity law. In the measured data it does
not: `bytes_per_acu` includes the 512-byte transaction payload
(`workload_tx_bytes = 512`) on every tx-carrying delivery
(`src/output/metrics.py::bytes_per_acu`), and at the thesis workload this
payload term dominates and amortises. So `bytes_per_acu / n²` *falls* with `n`
for PBFT (2423 → 82 across `n = 4..25`) and Casper FFG (5758 → 196), and
`bytes_per_acu / (K·β)` falls for Snowman (568 → 244) — the opposite of the
protocol-overhead scaling RQ3 is built to test. The scaling-exponent contrast
(PBFT/FFG `O(n²)` vs Snowman `O(K·β)`) is visible in `consensus_msgs_per_acu`
(message *count*) but **not** in `bytes_per_acu`. RQ3 byte-overhead claims
should therefore use `consensus_msgs_per_acu`, or report a payload-subtracted
protocol-byte figure (`bytes − payload·ACU`). No published claim currently
asserts a `bytes_per_acu` scaling law, so this is a gap to close, not an error
to retract. See §Revisions [2026-06-14].

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
populate via the per-protocol formulas in §Finality semantics — **except that
under T71 (2026-06-15) `finality_latency_ms` is retracted to PBFT-only
client-observed finality and is a structural duplicate of `commit_latency_ms`
for FFG/Snowman, not an independent per-protocol value** (§Finality semantics
§Relabel; [[concepts/output-format]] §13 Revisions [2026-06-15]). The Snowman
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

**Status note (2026-06-14) — several mandated columns are not yet populated.**
The schema above lists `empirical_epsilon`, `analytical_epsilon_bound`,
`f_max_count`, and `f_max_stake`, but no `results/*.csv` produced through
Family B (baseline + delay) carries them: the honest-only Family-A/B runs have
no Byzantine axis, so `f_max_*` is untestable and `empirical_epsilon` is
structurally zero. These columns are deferred to the **Family C adversarial
sweep (T51+)**, where empirical `ε` can be non-zero and `f_max_*` is
measurable. `analytical_epsilon_bound` is a deterministic per-`n` constant
already tabulated in §Snowman parameter rescaling (corrected this revision), so
it is **not** added as a standalone per-row column now — as a per-row value it
would be redundant; it lands alongside `empirical_epsilon` with Family C, where
it is the comparison baseline. The absence is recorded here rather than left
silent. See §Revisions [2026-06-14].

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

**2026-06-14 (T49.1) — reconcile metric docs against the T49 theory-vs-data
validation.** A 29-agent adversarial pass over `results/{baseline,delay}/*.csv`
(the T49 validation, [[experiments/2026-06-13_delay-analysis]] §"Issues outside
T49 scope") surfaced five framework discrepancies between this page and the
data. A read-only code investigation confirmed each and revised two severities
down (the finality and `tps` items are documentation gaps, not bugs). All
corrected numbers re-derive in Python and match the CSV to the quoted
precision. The companion page [[concepts/evaluation-metrics]] carries the
aligned definition-level edits; `[[algorithms/pos]]` was already correct (it
states LMD-GHOST is not implemented) and is unchanged — the other two pages are
aligned *to it*.

1. **PBFT `consensus_msgs_per_acu` formula (§Overhead) was wrong.** The body
   read `1 + 2·n + 2·n²` (≈ 41/113/221/545/1301 at `n = 4/7/10/16/25`), which
   does not match the data. Corrected to per-instance `2(n²−1)` deliveries
   (= all-to-all PREPARE + COMMIT `2n(n−1)` + PRE-PREPARE + client `REPLY`
   `2(n−1)`, primary self-excluded) and per-ACU `(2n²−2)/n = 2n − 2/n`
   (7.5/13.71/19.8/31.88/49.92) — CSV-exact. Added the caveat that the `≈2n`
   per-ACU figure is `O(n²)` traffic-per-instance normalised by an `n`-scaled
   decided-event denominator, **not** linear scaling, so Chapter 4 must not read
   "2n" as "PBFT scales linearly".

2. **Snowman analytical `ε` table (§Snowman parameter rescaling) was off.**
   Recomputing `(1 − α_c/K)^β` with `β = 15`: `n=7` `6.5·10⁻¹² → 2.1·10⁻¹²`,
   `n=10` `4.4·10⁻¹⁴ → 4.9·10⁻¹⁵` (one order of magnitude), `n=16`/`n=25`
   `3.0·10⁻¹¹ → 3.3·10⁻¹¹`. The `K/α_p/α_c/(α_c/K)` columns were already
   correct; only the `ε` column changed.

3. **`finality_latency_ms ≡ commit_latency_ms` for FFG/Snowman is a modelling
   choice, not a bug (§Finality semantics).** The FFG/Snowman reducers emit a
   single finalisation `decided` event and model no separate pre-final commit
   state, so the equality holds by construction. PBFT is the exception: it emits
   a distinct `pbft_client_finalized` event (T70), so its `finality_latency_ms`
   exceeds `commit_latency_ms` on every row — ≈ 10⁻⁶ ms at the zero-delay
   baseline, growing to tens–hundreds of ms under delay. Added a simulator note:
   the FFG/Snowman commit↔finality gap the schema reserves is unpopulated, so it
   is a commit-time proxy until a distinct finality event is implemented
   (standing Backlog item).

4. **`tps` and `goodput` are on protocol-dependent bases (§Throughput).** `tps`
   as implemented is a *decided-event* rate (per-block PBFT/Snowman ⇒ `0.95·n`;
   per-epoch FFG ⇒ `0.40·n`), not a committed-tx count, so it is not a
   cross-protocol common basis. `goodput` is the committed-application-tx rate
   and is the correct cross-protocol axis. Corrected the false attribution of
   the FFG goodput shortfall (`79.635` vs `94.82`) to "LMD-GHOST reorgs": reorgs
   are not implemented (`fork_rate = 0`, [[algorithms/pos#simulator-mapping]]);
   the shortfall is epoch-paced finalisation accounting and is partly legitimate.

5. **`bytes_per_acu` is payload-dominated (§Overhead).** It does not follow the
   `O(n²)` / `O(K·β)` law the `bytes_per_block` row predicts — the 512-byte
   payload dominates and `bytes_per_acu / n²` (and `/(K·β)`) *falls* with `n`.
   Steered RQ3 byte claims to `consensus_msgs_per_acu`. Gap to close, not a
   published error.

6. **Mandated reliability columns absent from every CSV (§T40 CSV schema).**
   `empirical_epsilon` / `analytical_epsilon_bound` / `f_max_count` /
   `f_max_stake` are unpopulated through Family B (no Byzantine axis). Flagged
   the deferral to the Family C adversarial sweep (T51+); `analytical_epsilon_bound`
   is the deterministic per-`n` constant already in the corrected ε table and is
   **not** added as a standalone column now (decision recorded in the 2026-06-14
   Backlog plan).

**2026-06-15 (T71) — `commit_latency_ms` is the canonical time-to-finality
column; `finality_latency_ms` retracted to PBFT-only.** Refines item #3 above.
The 2026-06-14 item correctly classed `finality_latency_ms ≡ commit_latency_ms`
(FFG/Snowman) as a modelling choice rather than a bug, but framed
`commit_latency_ms` as a *commit-time proxy* awaiting a finality event. The
chosen path (eval-methodology decision, Path B) inverts that framing: the
`decided` event each protocol emits already fires at its **irreversibility
(finality)** milestone — PBFT `2f+1` `COMMIT`, FFG the **finalised** checkpoint
(`src/pos/node.py::_finalise`, justify→finalise, `≥ 2` epochs, **not** block
inclusion), Snowman counter-`β` — so `commit_latency_ms` *already* measures
time-to-finality and is the canonical cross-protocol latency axis (which is why
the T48/T49 comparison on it is valid). The label is the only defect, and it is
fixed at the binding contract page, [[concepts/output-format]] §13 Revisions
[2026-06-15]:

1. `commit_latency_ms` = canonical cross-protocol **time-to-finality
   (irreversibility)** for PBFT, FFG, Snowman; read all "finality latency"
   claims off it.
2. `finality_latency_ms` is retracted from cross-protocol use and scoped to
   PBFT-only client-observed finality (`f+1` client `REPLY`). For FFG/Snowman
   it is a structural duplicate, not a measurement, and must not go on a
   cross-protocol axis. Retained physically (CSVs byte-identical).
3. The quantity §Finality-semantics above calls "not yet measured for
   FFG/Snowman" is the **earlier, reversible** commit/inclusion milestone
   (before `decided`) — the deferred Path A enrichment — **not** finality. Do
   not add a finality event *after* `decided`; that would double-count.
4. Nature-of-milestone caveat unchanged: FFG accountable-deterministic, Snowman
   probabilistic-with-`ε`; the `ε` columns stay the Family-C (T51+) deferral.

Documentation/label edit only — no reducer/schema/CSV change, no re-run;
supersedes the two `TASKS.md` Backlog finality items. `[[algorithms/pos]]` and
[[experiments/2026-06-13_delay-analysis]] are unaffected and unchanged.

### [2026-06-22] Casper FFG slot calibration corrected to the as-run config (L-W10 finding H2)

The §Calibration table previously pinned Casper FFG `slots_per_epoch = 4`
and `slot_duration = 100 ms`, with the rationale that this keeps FFG
finality at ~1 s "readable on a single axis" with the per-block
protocols. **That was the design; it is not what ran.** The
implementation (`src/pos/node.py` defaults `slots_per_epoch = 2`,
`slot_duration = 1.0`) and **every** experiment — baseline (T41,
[[experiments/2026-06-03_scaling-baseline]] `slot_duration = 1 s`,
`slots_per_epoch = 2`), delay (T46/T47), and adversarial (T51–T55) —
used `2`/`1 s`, giving per-epoch finality
`(2·slots_per_epoch + attest_offset)·slot_duration = (4 + 1)·1 s ≈ 5 s`,
the ≈5000 ms FFG figure Chapter 4 §4.2.2 reports and explains. The table,
its rationale, and the §Coherence-constraint default were corrected to
the as-run `2`/`1 s`; the sensitivity-sweep ranges were re-centred on the
new defaults. The delay-rescale rule (`slot_duration ≥ 4·E[delay]`) and
the per-timeline rescaled values (`1200 ms` at `E[delay] = 300 ms`,
`12000 ms` at ≈3 s — see [[concepts/experiment-matrix-runs]] §2) are
unchanged: they equal `4·E[delay]` and never depended on the baseline
default. Mirror corrections landed on [[concepts/experiment-matrix]] §5,
[[concepts/experiment-matrix-runs]] §2, and `drafts/ch3_methodology.md`
§3.3.2/§3.4.3. **Documentation reconciliation only — no code, CSV, or
re-run; the data already reflects `2`/`1 s`.** The alternative resolution
(treat `4`/`100 ms` as the intended pin and re-run the entire dataset at
that calibration) was rejected: it would contradict an existing Chapter 4
finding and invalidate every committed result.

**2026-07-02 — Casper FFG `total_msgs_per_acu` relabelled: analytical `≈1.125n`,
measured `≈1.15n`.** The §Overhead table (`total_msgs_per_acu` row) previously
called `≈1.125n` the *measured* value; it is the *analytical* prediction. A
least-squares fit of `results/baseline/aggregated.csv` gives the measured slope
`1.145n + 0.7` (≈ `1.15n`, within two percent of the prediction); the per-`n`
ratio is 1.29 → 1.17 over `n = 4 → 25` as the fixed additive term (block
proposals + finite-window boundary epochs) dilutes. The row now states both
values. This also corrected the opposite over-round in [[concepts/key-findings]]
(which reported `≈1.2n`); drafts Ch4/Ch5/Ch6 and the `theory_vs_measured` figure
theory line (`src/output/explain.py::_theory_line`, previously `1.2·n`, now the
analytical `1.125·n`) were aligned the same day. No CSV or re-run — the data was
always correct; only the labels were.
