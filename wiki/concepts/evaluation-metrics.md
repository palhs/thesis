# Evaluation Metrics

A unified metric schema applied to all four consensus families evaluated in
this thesis. Every protocol implemented under `src/` exports the metrics
below in identical units, so the comparative tables and plots in Ch. 4–5
operate on a single definition per quantity.

Rationale: the four families have historically been evaluated with their
own vocabulary — PBFT reports operations/s and view-change cost [4], [5];
Casper FFG reports time-to-finality in epochs [7]; Avalanche reports
probabilistic `ε` and per-transaction confirmation latency [9]; DAG-based
protocols report ktps and commit latency at the WAN [11]–[13]. Survey [15]
and methodological critique [16] both identify this vocabulary
fragmentation as the principal obstacle to comparative evaluation. A unified
schema is the obstacle-removal step; see [[concepts/problem-statement]].

## Four-protocol scope

The thesis instantiates the schema against four concrete protocols, one
per family:

- **PBFT** ([[algorithms/pbft]], [4]) — partial-sync, per-block
  deterministic finality.
- **Casper FFG** ([[algorithms/pos]], [7]) — partial-sync, per-epoch
  deterministic finality with accountable safety.
- **Snowman** ([[algorithms/avalanche]], [9] / [ava-docs]) — async-tolerant,
  per-block probabilistic finality on a totally-ordered chain.
- **Narwhal+Tusk** ([[algorithms/dag-based]], [11]) — async-safe,
  per-anchor-batch deterministic finality over a DAG mempool.

This page states the canonical metric definitions in family-agnostic
form. Concrete per-protocol formulas — including the four structural
asymmetries (linear-chain vs DAG output, per-block vs per-epoch vs
per-anchor-batch finality, Narwhal mempool/consensus split, Snowman
parameter rescaling at thesis-scale `n`) — live in the companion page
[[concepts/metric-reconciliation]]. That page is normative for the T40
CSV schema and for cross-protocol comparison; this page is normative for
metric *names, units, and meaning*.

## Schema structure

Four metric families. Each family contains 2–5 metrics; each metric has a
fixed definition, a set of primary sources, and a fixed instrumentation
point in `src/` (see §Simulator instrumentation).

| Family | What it measures |
| :---- | :---- |
| **Latency** | How quickly a transaction or block reaches commit or finality. |
| **Throughput** | How many transactions/blocks the protocol commits per unit time. |
| **Overhead** | Messages, bytes, and per-validator state required to operate the protocol. |
| **Reliability** | Whether the protocol preserves safety and liveness under delay and adversary. |

## Time anchors

Every latency metric below uses a single protocol-agnostic start-of-clock:
**"tx submit"** is the wall-clock moment the workload generator emits the
transaction, *before* it reaches any validator. End-of-clock is
protocol-specific and pinned per metric below (and per protocol in
[[concepts/metric-reconciliation#latency]]).

For protocols with a separate mempool layer (Narwhal+Tusk in scope here),
the time the transaction spends traversing the mempool is **counted in**
`commit_latency_ms` and `finality_latency_ms` — not stripped out.
Treating mempool admission as "free" would hide the cost of Narwhal's
data-availability layer and bias the latency comparison.

**Wall-clock** throughout this page and its companion refers to the
simulator's *model time* as advanced by the event scheduler
([[concepts/simulation-design]] — T17, forward link); no simulator number
is a real-hardware claim. The literature numbers in §"Reported ranges in
the literature" below are real-hardware and are not directly comparable
to simulator output — see §Caveat.

## Latency metrics

- **End-to-end commit latency.** Wall-clock time from transaction
  submission to first inclusion in a committed block, averaged over a
  stable-state measurement window. Sources: [4], [11], [17].
- **Time-to-finality.** Wall-clock time from transaction submission to
  *finality*. "Finality" resolves to four distinct events across the
  scoped protocols — `2f+1` `COMMIT` quorum in PBFT [4], epoch-granularity
  justify → finalise in Casper FFG [7], counter `β` reached with
  operational `ε` in Snowman [9] / [ava-docs], anchor-commit of a DAG
  sub-graph in Narwhal+Tusk [11]. Per-protocol formulas in
  [[concepts/metric-reconciliation#finality-semantics]]. Sources: [4],
  [7], [9], [11], [13].
- **Round latency.** Time to complete one protocol round. The "round"
  unit dispatches per protocol: one of three PBFT phases, one slot in
  Casper FFG, one Snowball poll of `K` peers in Snowman, one DAG round
  in Narwhal+Tusk. Per-protocol rows in
  [[concepts/metric-reconciliation#latency]]. Sources: [4], [5], [7],
  [9], [11].

→ Per-protocol formulas for every latency metric:
[[concepts/metric-reconciliation#latency]].

**Implementation note (T71, 2026-06-15) — column ↔ metric mapping.** Despite
its name, the `commit_latency_ms` CSV column implements **Time-to-finality**
above, *not* End-to-end commit latency. Its end-of-clock is each protocol's
`decided` event, which fires at the **irreversibility** milestone: PBFT `2f+1`
`COMMIT`, Casper FFG the *finalised* checkpoint (justify→finalise, `≥ 2`
epochs, **not** block inclusion), Snowman counter-`β` acceptance. It is the
canonical cross-protocol time-to-finality axis (basis of the T48/T49
comparison). The `finality_latency_ms` column is **retracted** from
cross-protocol finality use and scoped to PBFT-only client-observed finality
(`f+1` client `REPLY`); for Casper FFG / Snowman it is a structural duplicate
of `commit_latency_ms`, carrying no independent measurement. The **End-to-end
commit latency** metric above — the *earlier, reversible* inclusion milestone,
before finality — is **not implemented as a distinct column** for Casper FFG /
Snowman; populating it is the deferred Path A enrichment. PBFT has no
reversible-inclusion stage (COMMIT is immediately final), so its inclusion ≈
finality. Binding contract: [[concepts/output-format]] §13 Revisions
[2026-06-15]; companion reconciliation:
[[concepts/metric-reconciliation#finality-semantics]] §Revisions [2026-06-15].
See §Revisions below.

## Throughput metrics

- **Transactions per second (tps).** Count of *committed* transactions per
  unit wall-clock time, averaged over a stable-state window. Sources:
  [11]–[13], [15], [17]. **Implementation caveat (2026-06-14):** as built,
  `tps` is a *decided-event* rate (`len(decided) / window`,
  `src/{pbft,pos,snowman}/summarise.py`), whose granularity is per-block for
  PBFT/Snowman and per-epoch for Casper FFG — so cross-protocol `tps` is **not**
  on a common basis (`0.95·n` vs `0.40·n` in the baseline). The
  committed-transaction quantity this bullet defines is carried by `goodput`.
  See [[concepts/metric-reconciliation#revisions]].
- **Goodput.** tps restricted to transactions that survive to finality;
  excludes transactions in reorganised forks. Identical to tps for PBFT
  (no reorg-before-finality) and Snowman (post-`β` reorgs bounded by
  `ε`, reported separately); distinct from tps for Casper FFG (LMD-GHOST
  reorgs before checkpoint finalisation [8]) and Narwhal+Tusk (orphan
  certificates not referenced by any committed anchor). Sources: [8],
  [17]. **Implementation caveat (2026-06-14):** the *implemented* `goodput`
  is computed directly as `committed_tx / window` (committed-application-tx
  rate, `src/output/metrics.py`), **not** as `tps` minus reorged tx — in the
  data `goodput ≫ tps` because the implemented `tps` is a decided-event rate
  (see above). The Casper FFG goodput shortfall (`79.635` vs `94.82` tx/s) is
  **not** LMD-GHOST reorg loss: LMD-GHOST fork choice and reorgs are *not
  implemented* and `fork_rate = 0` ([[algorithms/pos#simulator-mapping]]); it
  reflects FFG's epoch-paced finalisation accounting. Full reconciliation:
  [[concepts/metric-reconciliation#revisions]].
- **Peak throughput.** Maximum sustained tps before commit-latency
  diverges — the per-family saturation point. Operational definition:
  run an offered-load rate ramp where the workload generator's
  submission rate increases monotonically through a configured grid
  (T19 to pin the grid); at each rate, hold for a measurement window of
  ≥ `W` simulator seconds; declare the rate "sustained" iff
  `commit_latency_p99` over the window stays within a factor of `1.5`
  of its value at the previous rate. Peak throughput is the highest
  sustained rate. The `1.5` factor and the holding window `W` are
  sensitivity-sweep candidates (see
  [[concepts/metric-reconciliation#sensitivity-sweep-policy]]). Sources:
  [11], [13], [15].
- **Mempool throughput (`mempool_tps`).** For protocols with a separate
  mempool layer that commits transactions for *availability* before
  consensus orders them, the count of mempool-admitted transactions per
  unit wall-clock time. Defined for Narwhal+Tusk (certificate-included
  tx count / window); **zero by construction** for PBFT, Casper FFG, and
  Snowman, which have no separate mempool. Asymmetric counterpart to
  `mempool_msgs_per_acu` under §Overhead; reporting only consensus tps
  hides Narwhal's central architectural claim that mempool capacity
  decouples from consensus capacity. Sources: [11].

→ Per-protocol formulas for every throughput metric:
[[concepts/metric-reconciliation#throughput]].

## Overhead metrics

- **Messages per block.** Protocol messages transmitted per committed
  unit. The unit is "block" for PBFT/Casper FFG/Snowman and "anchor-batch"
  for Narwhal+Tusk — the per-protocol *atomic commit unit* is defined in
  [[concepts/metric-reconciliation#unit-of-progress]]. Exposes the
  scaling-exponent difference RQ3 tests: `O(n²)` for [[algorithms/pbft]],
  per-validator `O(K·β)` independent of `n` for Snowman, and a *two-layer
  split* for [[algorithms/dag-based]] — `O(n²)` mempool messages per round
  plus zero additional consensus messages at anchor commit
  ([[concepts/metric-reconciliation#narwhal-mempool-consensus-message-split]]).
  Sources: [4], [5], [11].
- **Bytes per block.** Total byte footprint of protocol messages per
  block — absolute bandwidth, not just message count. Signature bytes
  dominate in [[algorithms/pbft]] and [[algorithms/pos]]; payload bytes
  dominate in the DAG mempool of [[algorithms/dag-based]]. The signature
  scheme and aggregation model (ECDSA vs BLS, individual vs aggregated
  attestations) is **T16's contract** ([[concepts/message-types]] —
  forward link); `bytes_per_acu` is computed against the T16-pinned
  scheme and is undefined without it. This matters specifically for the
  FFG-vs-PBFT bytes comparison: BLS aggregation collapses Casper FFG's
  per-epoch attestation cost from `O(n)` individual signatures to one
  aggregate signature + bit-vector, a factor-of-`n` swing depending on
  T16's choice. Sources: [15], [17]. **Implementation caveat (2026-06-14):**
  the measured `bytes_per_acu` includes the 512-byte transaction payload and is
  payload-dominated at the thesis workload, so it does *not* exhibit the
  `O(n²)` / `O(K·β)` scaling this bullet describes; RQ3 byte-overhead claims
  should use `consensus_msgs_per_acu` (message count) or a payload-subtracted
  figure. See [[concepts/metric-reconciliation#revisions]].
- **Per-validator state size.** Storage required per validator to operate
  the protocol: full DAG retention in Narwhal+Tusk (the largest of the
  four — the structural tradeoff against PBFT's per-block message cost),
  attestation buffers per slot in Casper FFG, vote caches in PBFT,
  Snowball preference + counter (independent of `n`) in Snowman. Sources:
  [11], [13].

→ Per-protocol formulas for every overhead metric, including the
Narwhal mempool/consensus message split:
[[concepts/metric-reconciliation#overhead]].

## Reliability metrics

- **Consensus success rate.** Fraction of protocol rounds that
  successfully commit a value under a given adversary/delay scenario.
  Operationalises the Termination property from
  [[concepts/consensus-properties]]. Sources: [4], [5], [9], [17].
- **Fork rate.** Fraction of proposed blocks/rounds that do not survive
  to finality — the BFT analogue of the PoW stale-block rate. Meaningful
  for families with a reorg-before-finality regime ([[algorithms/pos]]);
  nil by construction for pure BFT finality ([[algorithms/pbft]]).
  Sources: [8], [17].
- **View-change / reorg frequency.** Count of view changes
  ([[algorithms/pbft]]) or reorgs ([[algorithms/pos]]) per unit wall-clock
  time. Tracks liveness disruption invisible to success rate alone.
  `N/A` for Snowman (no view changes; pre-`β` preference flips logged
  separately) and Narwhal+Tusk (no view changes; failed-anchor-commit
  events logged separately as pipeline-extension events). Sources: [4],
  [5], [8].
- **Safety-violation probability (`ε`).** Empirical probability that two
  honest validators commit conflicting values. *Primary* metric for
  Snowman (parameter-dependent: `ε ≤ (1 − α_c/K)^β` [9]; report both
  analytical bound and empirical rate); zero by construction below
  threshold for PBFT, Casper FFG, and Narwhal+Tusk (measured above
  threshold). Sources: [9], [10]. **Status (2026-06-14):** `empirical_epsilon`
  and `analytical_epsilon_bound` are not populated in the honest-only
  baseline/delay CSVs (empirical `ε` is structurally zero with no Byzantine
  axis); they are deferred to the Family C adversarial sweep (T51+). See
  [[concepts/metric-reconciliation#revisions]].
- **Fault-tolerance threshold (`f_max`).** Empirically largest adversarial
  fraction under which the protocol preserves safety *in the simulator*.
  Reported as **two CSV columns**: `f_max_count` (PBFT, Snowman,
  Narwhal+Tusk — by validator count) and `f_max_stake` (Casper FFG — by
  stake fraction). Exactly one column is populated per row; the other
  is `NaN`. Compared against the theoretical bound in
  [[concepts/quorum-arithmetic]] — `< n/3` for PBFT and Narwhal+Tusk,
  `< 1/3` of stake for Casper FFG, parameter-dependent (driven by
  `α_c/K` and `β`) for Snowman. Sources: [1], [3], [7], [14].

→ Per-protocol formulas for every reliability metric:
[[concepts/metric-reconciliation#reliability]].

## Reported ranges in the literature

Baselines for qualitative comparison with the simulator's own measurements;
not treated as ground truth. See caveat below.

| Family | Throughput (reported) | Latency (reported) | `f_max` | Source |
| :---- | :---- | :---- | :---- | :---- |
| [[algorithms/pbft]] (LAN) | Thousands of ops/s | Sub-10 ms | `< n/3` | [4] |
| HotStuff | Linear with `n` after optimisations | 3-round commit | `< n/3` | [5] |
| [[algorithms/pos]] (Casper FFG / Gasper) | Block-proposal rate of underlying chain | Two-epoch finality (≤12.8 min for 32-slot epochs on Ethereum) | `< 1/3` of stake | [7], [8] |
| [[algorithms/avalanche]] | ~3.4 ktps (testnet) | ~1.35 s | Parameter-dependent (~`< 1/5` typical) | [9], [10] |
| Narwhal + Tusk | ~140 ktps (WAN) | ~2–3 s | `< n/3` | [11] |
| Bullshark | ~125 ktps | 2-round fast path under synchrony | `< n/3` | [12] |
| Mysticeti | >200 ktps | ~0.5 s (WAN, consensus commit) | `< n/3` | [13] |
| PoW baseline (Bitcoin-style) | Tens of tps max, block-interval dependent | ~10–60 min confirmation | `< ~1/4` hashrate (selfish-mining bound) | [17] |

**Caveat.** These numbers come from different experimental harnesses —
hardware, workload, batching, and geography all differ. Survey [15]
explicitly flags this as the primary obstacle to accurate comparative
evaluation, and it is the obstacle this thesis's simulator is designed to
remove (see [[concepts/problem-statement]]).

## Adversarial and delay axes

Independent variables swept against each metric family. Operational
catalogue of adversary strategies lands under T18
(`wiki/concepts/adversary-model.md`, forward link); the experimental
matrix that combines these axes lands under T19
(`wiki/concepts/experiment-matrix.md`, forward link).

- **Byzantine fraction.** `0 → f_max` per family; sources [1], [3], [14].
- **Network delay distribution.** Constant / uniform / exponential /
  heavy-tailed. Materially changes [[algorithms/pbft]] behaviour via
  view-change frequency [4], [5] and [[algorithms/avalanche]] behaviour
  via round-time variance [9], [10].
- **Packet loss rate.** Independent Bernoulli per message; probes the
  reliable-broadcast assumptions in [[algorithms/dag-based]] [11], [13].
- **Partitions and GST.** Bounded async intervals; required to exercise
  the partial-synchrony assumption from [[concepts/synchrony-models]]
  faithfully [3].
- **Adversarial strategies.** Silent non-participation, delayed voting,
  equivocation, selective message dropping. Each maps to documented
  behaviour in [4], [7], [9]. Theoretical fault taxonomy in
  [[concepts/fault-model]].

## Metric-to-RQ map

Each [[concepts/research-questions|research question]] drives a subset of
the schema.

| RQ | Primary metrics | Axis swept |
| :---- | :---- | :---- |
| RQ1 | Commit latency, round latency, time-to-finality | Delay distribution |
| RQ2 | tps, goodput, peak throughput | Byzantine fraction |
| RQ3 | Messages per block, bytes per block, per-validator state size | Validator-set size `n` |
| RQ4 | Consensus success rate, view-change / reorg frequency, safety-violation `ε` | Adversarial strategy × Byzantine fraction |
| RQ5 | All four families jointly | Combined |

## Simulator instrumentation

The schema is enforced as a `Metric` interface every protocol
implementation under `src/` must populate. Concretely:

- **Per-transaction timestamp log** → commit latency, time-to-finality,
  goodput.
- **Per-block message-count and byte-size log** → messages per block,
  bytes per block, peak throughput.
- **Per-round event log** → view changes, reorgs, safety-check failures;
  drives consensus success rate, fork rate, view-change / reorg
  frequency, safety-violation `ε`.
- **Per-validator state-size sample** → per-validator state size.

The simulator runner aggregates these across trials and writes one
comparative CSV per scenario, whose columns match the metric names above.
The concrete CSV schema lands under T40
(`wiki/concepts/output-format.md`, forward link); the per-protocol
formulas it must compute, plus the column set derived from this schema,
are pinned in
[[concepts/metric-reconciliation#t40-csv-schema-implications]].

This is the methodological practice recommended by [14] and critiqued as
missing in [16] — applied uniformly to all four families.

## Primary sources cited here

Dedicated source pages exist for:

- [1] [[sources/2026-04-21_lamport-shostak-pease-bgp-1982]]
- [3] [[sources/2026-04-21_dwork-lynch-stockmeyer-partial-sync-1988]]
- [4] [[sources/2026-04-21_castro-liskov-pbft-1999]]
- [5] [[sources/2026-04-21_yin-hotstuff-2019]]
- [7] [[sources/2026-04-21_buterin-griffith-casper-ffg-2017]]
- [9] [[sources/2026-04-21_team-rocket-avalanche-2019]]
- [11] [[sources/2026-04-21_danezis-narwhal-tusk-2022]]
- [12] [[sources/2026-04-21_spiegelman-bullshark-2022]]
- [13] [[sources/2026-04-21_babel-mysticeti-2023]]
- [14] [[sources/2026-04-21_bano-sok-consensus-2019]]

`[8]`, `[10]`, `[15]`, `[16]`, `[17]` are catalogued on
[[concepts/annotated-bibliography]] with full IEEE entries; dedicated
source pages are deferred (Backlog in `TASKS.md`). Numbering follows the
consolidated `[N]` convention pinned at the top of
[[concepts/annotated-bibliography]].

## Source

Imported from `resources/Evaluation_Metrics.md` (Phase 2 — Literature
Synthesis). T9 outcomes covered: the six metric categories required by
T9 (latency, throughput, communication overhead, fault tolerance, finality
time, fork rate) are all represented — communication overhead spans the
three metrics under §Overhead; finality time is the time-to-finality
metric under §Latency; fault tolerance is `f_max` under §Reliability;
fork rate is its own reliability metric.

T9.1 extension: §Four-protocol scope added; the time-to-finality,
round-latency, messages-per-block, goodput, per-validator-state-size,
view-change/reorg-frequency, safety-violation `ε`, and `f_max` bullets
tightened to instantiate against PBFT, Casper FFG, Snowman, and
Narwhal+Tusk explicitly. Per-protocol formulas (and `N/A` notes where
applicable) live on the companion page
[[concepts/metric-reconciliation]]; this page remains the canonical
metric-definition source. Reported-ranges table left intact for Chapter 2
breadth; the four scoped rows are PBFT (LAN), PoS (Casper FFG / Gasper),
Avalanche (Snowman is the deployed linearised variant of this family),
and Narwhal + Tusk.

## Revisions

**2026-06-14 (T49.1) — align definition-level metric prose with the T49
theory-vs-data validation.** The companion page
[[concepts/metric-reconciliation#revisions]] carries the full reconciliation
and the corrected per-protocol formulas/numbers; this page holds the
canonical *definitions*, so the edits here are caveats that keep the
definition prose honest about what the simulator actually measures:

- **`tps`** — flagged that the implemented metric is a decided-event rate with
  protocol-dependent granularity (per-block vs per-epoch), not a cross-protocol
  common basis; the committed-tx quantity is `goodput`.
- **Goodput** — corrected the false implication that the Casper FFG `goodput <
  tps` gap is LMD-GHOST reorg loss. LMD-GHOST and reorgs are *not implemented*
  (`fork_rate = 0`, [[algorithms/pos#simulator-mapping]]); the implemented
  `goodput` is `committed_tx / window` and `goodput ≫ tps` in the data.
- **Bytes per block** — flagged that measured `bytes_per_acu` is
  payload-dominated and does not show the `O(n²)`/`O(K·β)` scaling; RQ3 byte
  claims should use `consensus_msgs_per_acu`.
- **Safety-violation `ε`** — flagged that `empirical_epsilon` /
  `analytical_epsilon_bound` are unpopulated in the honest-only Family-A/B CSVs
  and are deferred to the Family C adversarial sweep (T51+).

No metric was renamed or removed; `[[algorithms/pos]]` was already correct and
is unchanged.

**2026-06-15 (T71) — `commit_latency_ms` is the canonical time-to-finality
column; `finality_latency_ms` retracted to PBFT-only.** Added the
column ↔ metric mapping note under §Latency metrics. The `commit_latency_ms`
CSV column implements the **Time-to-finality** metric defined here (each
protocol's `decided` event marks its irreversibility milestone — PBFT `2f+1`
`COMMIT`, FFG the finalised checkpoint, Snowman counter-`β`), *not*
End-to-end commit latency despite its name; it is the canonical cross-protocol
latency axis. `finality_latency_ms` is retracted from cross-protocol use and
scoped to PBFT-only client-observed finality (structural duplicate for
FFG/Snowman). The **End-to-end commit latency** metric (the earlier reversible
inclusion milestone) is not implemented as a distinct column for FFG/Snowman —
the deferred Path A enrichment. No metric renamed or removed; documentation
edit only, CSVs byte-identical. Binding contract: [[concepts/output-format]]
§13 Revisions [2026-06-15].
