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

## Latency metrics

- **End-to-end commit latency.** Wall-clock time from transaction
  submission to first inclusion in a committed block, averaged over a
  stable-state measurement window. Sources: [4], [11], [17].
- **Time-to-finality.** Wall-clock time from transaction submission to
  *finality*. "Finality" resolves differently per family: deterministic
  `2f+1` commit acknowledgments in [[algorithms/pbft]], epoch-granularity
  justify → finalise in [[algorithms/pos]], or a probabilistic confidence
  threshold `β` being reached in [[algorithms/avalanche]]. Sources: [4],
  [7], [9], [13].
- **Round latency.** Time to complete one protocol round — one PBFT phase,
  one FFG epoch boundary, or one Avalanche sampling round. Sources: [4],
  [5], [9].

## Throughput metrics

- **Transactions per second (tps).** Count of *committed* transactions per
  unit wall-clock time, averaged over a stable-state window. Sources:
  [11]–[13], [15], [17].
- **Goodput.** tps restricted to transactions that survive to finality;
  excludes transactions in reorganised forks. Distinct from tps for
  families that can reorg before finality ([[algorithms/pos]]) or admit
  fork races ([[algorithms/dag-based]] orphan DAG vertices). Sources: [8],
  [17].
- **Peak throughput.** Maximum sustained tps before queueing delay
  diverges — the per-family saturation point. Sources: [11], [13], [15].

## Overhead metrics

- **Messages per block.** Protocol messages transmitted per committed
  block. Exposes the scaling-exponent difference the thesis tests under
  RQ3: `O(n²)` for [[algorithms/pbft]], `O(n)` for [[algorithms/dag-based]],
  per-validator `O(K·β)` independent of `n` for [[algorithms/avalanche]].
  Sources: [4], [5], [11].
- **Bytes per block.** Total byte footprint of protocol messages per
  block — absolute bandwidth, not just message count. Signature bytes
  dominate in [[algorithms/pbft]] and [[algorithms/pos]]; payload bytes
  dominate in the DAG mempool of [[algorithms/dag-based]]. Sources: [15],
  [17].
- **Per-validator state size.** Storage required per validator to operate
  the protocol: DAG retention window in [[algorithms/dag-based]],
  attestation buffers in [[algorithms/pos]], vote caches in
  [[algorithms/pbft]]. Sources: [11], [13].

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
  Sources: [4], [5], [8].
- **Safety-violation probability (`ε`).** Empirical probability that two
  honest validators commit conflicting values. Primary metric for
  [[algorithms/avalanche]] (parameter-dependent:
  `ε < (1 − α_c/K)^β`); detected but expected to be zero for the `3f+1`
  deterministic-finality families. Sources: [9], [10].
- **Fault-tolerance threshold (`f_max`).** Empirically largest adversarial
  fraction (by count or stake) under which the protocol preserves safety
  *in the simulator*. Compared against the theoretical bound in
  [[concepts/quorum-arithmetic]]. Sources: [1], [3], [7], [14].

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
(`wiki/concepts/output-format.md`, forward link).

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

## Revisions

None.
