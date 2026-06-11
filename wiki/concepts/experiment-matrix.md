# Experiment Matrix

Design contract for the simulator's experiment parameter space. Turns the
five research questions ([[concepts/research-questions]]) into an
enumerable set of seeded simulator runs.

This page (T19) owns the **design** — the parameter axes, the run
families, the per-RQ mapping, and the policies (workload, seeds,
FFG–network coherence). The **enumerated catalog** — concrete
network-timeline parameter tables, adversary triple tables, and the
run-count budget — is the companion [[concepts/experiment-matrix-runs]].
The split follows `docs/wiki-spec.md` § Page size; precedent:
[[concepts/network-model]] / [[concepts/network-model-phases]].

## 1. Scope

**T19 owns** — and this page or its companion pins:

- the parameter axes and their value sets (§2);
- the synchrony-narrative → network-phase-timeline mapping that
  [[concepts/network-model-phases]] §1 / §5 delegates here;
- the FFG `slot_duration` ↔ `E[delay]` coherence pairing that
  [[concepts/metric-reconciliation]] § Calibration defaults assigns to
  T19 (§5);
- the four `workload_*` columns [[concepts/metric-reconciliation]]
  § T40 CSV schema labels "T19 contract", and the offered-load ramp grid
  and hold-window `W` [[concepts/evaluation-metrics]] § Throughput
  leaves for "T19 to pin" (§6);
- the seed and replication policy (§7).

**T19 consumes** — does not re-derive: per-protocol calibration defaults
([[concepts/metric-reconciliation]] § Calibration defaults); phase
mechanics ([[concepts/network-model-phases]]); the adversary catalog
([[concepts/adversary-model]]) and per-protocol intensity unit
([[concepts/adversary-model-runtime]] §2); metric definitions and time
anchors ([[concepts/evaluation-metrics]]).

**Out of scope:** metric definitions (T9 / T9.1); CSV column finalisation
(T40, [[concepts/output-format]]); the YAML config loader and
`global_seed` injection (T27, [[concepts/reproducibility]]); per-protocol
implementation (T22, T28+).

## 2. The six axes

An experiment configuration is a point in the product of six axes. Every
row of the T40 comparative CSV is one such point, run `n_runs` times.

| Axis | CSV column(s) | Value set | Values owned by |
| :-- | :-- | :-- | :-- |
| Validator-set size | `n` | `{4, 7, 10, 16, 25}` | T41, carried on [[concepts/metric-reconciliation]] § Snowman rescaling |
| Network timeline | `network_phase_id` | named timelines — [[concepts/experiment-matrix-runs]] §2 | T19 (this page) |
| Adversary | `adversary_strategy`, `byzantine_fraction` | catalog §§3–5 × intensity grid — [[concepts/experiment-matrix-runs]] §3 | T18 catalog; T19 picks the grid |
| Protocol knobs / timeouts | (per-protocol) | calibration defaults + sensitivity sweeps | [[concepts/metric-reconciliation]] § Calibration defaults |
| Workload | `workload_*` (4 columns) | §6 below | T19 (this page) |
| Seeds / replication | `seed`, `n_runs` | `seed ∈ 0 … n_runs−1`; `n_runs` per §7 | T19 (this page) |

`n ∈ {4, 7, 10, 16, 25}` is exactly `3f+1` at `f ∈ {1, 2, 3, 5, 8}`, so
every point is a clean Byzantine-threshold instance for the three
`f < n/3` families. The Snowman row at `n = 4` is excluded from
cross-protocol comparison tables ([[concepts/metric-reconciliation]]
§ Snowman parameter rescaling — the rescaling collapses Snowman to
flood-vote-with-counter there); `n = 7` is included but margin-flagged.

### Protocol knobs and timeouts

The "timeouts" axis named in the T19 task outcome is **not** re-derived
here. [[concepts/metric-reconciliation]] § Calibration defaults already
pins, before any baseline run, the PBFT view-change timeout
(`3 · E[round_latency]`), Casper FFG `slots_per_epoch` (4) and
`slot_duration` (100 ms), the Snowman `(K, α_p, α_c)` rescaling rule and
`β` (15), and the Narwhal+Tusk anchor period `r` (2). The experiment
matrix uses these as the **baseline configuration** and consumes the
per-RQ sensitivity sweeps from the same page's § Sensitivity-sweep
policy. The single knob T19 actively varies is the FFG `slot_duration`,
and only to keep FFG coherent with the network delay regime (§5).

## 3. Three run families

Experiments group into three families. Each fixes most axes and sweeps
one, so a family's runs answer one primary RQ without confounds.

| Family | Sweeps | Holds fixed | Network | Primary RQ | Feeds tasks |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **A — Scaling** | `n ∈ {4,7,10,16,25}` | honest, baseline workload | `static-baseline` | RQ3 | T41–T45 |
| **B — Delay** | network timeline | `n = 10`, honest, baseline workload | swept (constant → heavy-tail) | RQ1 | T46–T50 |
| **C — Adversarial** | `(adversary, intensity)` | `n = 10`, baseline workload | `static-baseline` | RQ2 + RQ4 | T51–T56 |

**Why `n = 10` for Families B and C.** It is the middle of the scaling
sweep and `3f+1` at `f = 3` — enough Byzantine budget for a graded
intensity sweep (`1, 2, 3` faulty, plus above-threshold `4, 5` for T53)
while small enough to afford many seeds. Snowman at `n = 10` sits in its
normal rescaling regime (`α_c/K = 0.889`), so no margin caveat applies.
Family A supplies the honest reference point at every other `n`.

**RQ5** ([[concepts/research-questions]]) runs no experiments of its
own; it is the Pareto synthesis across the Family A/B/C data and is
answered in Chapter 5 (T59–T60).

## 4. Per-RQ experiment design

| RQ | Family | Swept axis (independent variable) | Knob sensitivity sweep | Feeds |
| :-- | :-- | :-- | :-- | :-- |
| RQ1 | B | network delay distribution: `constant`, `uniform`, `exponential`, `heavy_tail` | none — the axis *is* the sweep ([[concepts/metric-reconciliation]] § Sensitivity-sweep policy) | T46–T50 |
| RQ2 | C | Byzantine fraction `0 → f_max` | inherits RQ4 | T51–T55 |
| RQ3 | A | `n ∈ {4,7,10,16,25}` | FFG `slots_per_epoch ∈ {4,8,16,32}`; Narwhal `r ∈ {2,4,8}` | T41–T44 |
| RQ4 | C | adversary strategy × Byzantine fraction | Snowman `β ∈ {3,5}` (RQ4-only safety regime) | T51–T56 |
| RQ5 | — | combined (delay, adversary, `n`, workload) | inherits RQ3 sweep data | T59–T60 |

RQ2 and RQ4 are answered from the **same** Family C run set: RQ2 reads
the throughput columns, RQ4 reads the liveness and per-protocol safety
columns. They share the Byzantine-fraction axis, so they are not run
twice. The Snowman `β ∈ {3,5}` sweep is RQ4-only and its rows **must
not** appear on cross-protocol throughput axes — [[concepts/metric-reconciliation]]
§ Calibration defaults pins `β = 15` as the throughput-comparison
baseline.

## 5. FFG slot-duration ↔ network coherence

[[concepts/metric-reconciliation]] § Coherence constraint on FFG forbids
pairing the Casper FFG `slot_duration = 100 ms` default with a network
phase where `E[delay]` is not `≪ slot_duration` — operationally the
matrix requires

```
slot_duration ≥ 4 · E[delay]
```

for every FFG run. Below that ratio, attestations from distant
validators arrive after the slot boundary and the protocol sits
permanently in a degraded-finality regime that is *not* Casper FFG; the
simulator runner must refuse such a pairing rather than emit mislabelled
numbers.

**T19's resolution: FFG `slot_duration` rescales with the delay regime.**
This is the direct analogue of the Snowman `K` rescaling with `n`
([[concepts/metric-reconciliation]] § Snowman parameter rescaling) —
both are the only legitimate way to keep a protocol *in its own regime*
while it is placed on a shared comparative axis. Families A and C use
the low-delay `static-baseline` network, so FFG runs there at its
default `slot_duration = 100 ms` and all four protocols are coherent.
Family B sweeps delay, so each delay timeline carries an FFG
`slot_duration` chosen by the rule above; the per-timeline pairing table
is in [[concepts/experiment-matrix-runs]] §2.

**Consequence, reported not hidden.** Because FFG's `slot_duration`
grows with `E[delay]` in Family B, FFG's time-to-finality there is
slot-dominated and *necessarily* increases with delay — an honest RQ1
finding about Casper FFG's delay coupling (the coupling Ethereum's 12 s
slot reflects). Chapter 4 surfaces the per-timeline `slot_duration` on
the plot rather than burying it.

## 6. Workload axis

[[concepts/metric-reconciliation]] § T40 CSV schema requires every row
to populate four `workload_*` columns with no `NaN`: throughput and
goodput are undefined without them. No prior page pinned their values;
that pinning is T19's contract. The committed defaults:

| Column | Default | Rationale |
| :-- | :-- | :-- |
| `workload_arrival_process` | `poisson` (`constant` for control runs) | Open-loop, memoryless arrivals — the standard offered-load model; a deterministic `constant` process is kept for variance-free control runs. |
| `workload_tx_bytes` | `512` | Application-payload size of one transaction. Matches the 512-byte transaction size used in the Narwhal+Tusk benchmarks [11]; distinct from the protocol-message overhead owned by T16 ([[concepts/message-types]]). |
| `workload_conflict_rate` | `0.0` | All transactions independently valid. Isolates protocol-level reorg / orphan behaviour (the goodput-vs-tps gap) from workload-level double-spends. Sweeping it is deferred (§9). |
| `workload_offered_rate` | `100` tx/s for the latency runs of Families A and B; the ramp grid below for peak-throughput measurement | See below. |

**Sub-saturation latency runs.** Families A and B measure latency and
per-ACU cost, meaningful only below saturation — above it queueing
dominates and the number stops being a protocol property. The fixed
`offered_rate = 100` tx/s is the sub-saturation operating point;
recalibrated down via `## Revisions` if T41 / T42 finds any protocol
saturates below it (§9).

**Peak-throughput ramp** (the `peak_tps` metric of
[[concepts/evaluation-metrics]] § Throughput, measured within Families A
and C). The offered-load rate ramps monotonically through the grid

```
{25, 50, 100, 200, 400, 800, 1600} tx/s   (geometric)
```

holding each rate for `W = 10` simulator-seconds; a rate is *sustained*
iff `commit_latency_p99` over the window stays within `×1.5` of the
previous rate's value. `peak_tps` is the highest sustained rate. The
grid and `W` are T19's to pin; the `×1.5` factor is inherited from
[[concepts/evaluation-metrics]]; all three are sensitivity-sweep
candidates ([[concepts/metric-reconciliation]] § Sensitivity-sweep
policy).

The simulator network is **latency-only** ([[concepts/network-model]]
§1 — no link-capacity model), so the ramp saturates the *protocol* (the
per-validator `O(K·β)` / `O(n²)` cost, vote-queue divergence), never a
network link. There is deliberately no bandwidth axis.

`network_phase_id` (the fifth axis) references a phase declared in the
timeline catalog of [[concepts/experiment-matrix-runs]] §2, so a row's
network regime is reconstructable from the CSV without duplicating the
full delay / drop / partition config on every row.

## 7. Seed and replication policy

- **`n_runs` per configuration.** Default **20** seeded trials per
  configuration point — satisfies the "10+ seeded runs" floor of T41 and
  supplies the 20–30-run band T44 needs for 95% confidence intervals.
  Near-threshold Family C configurations (Byzantine fraction at or above
  `f_max`, where outcome variance is highest) use **30**.
- **Seed enumeration.** The seeds are the integers `0 … n_runs−1`, each
  passed as the run's `global_seed`. Derivation of per-`Node` and
  per-`Network` RNG seeds from `global_seed` is owned by T27
  ([[concepts/reproducibility]]) and T14/T15
  ([[concepts/node-model]] §8, [[concepts/network-model-phases]] §6).
- **Common random numbers.** The same seed set is reused across all four
  protocols at a given configuration point. The four protocols then see
  the same network delay draws and adversary placements, which pairs the
  cross-protocol comparison and reduces the variance of the *difference*
  between protocols — a standard variance-reduction technique, and the
  reason cross-protocol verdicts can be drawn at modest `n_runs`.

`n_runs` and `commit_hash` are required CSV columns
([[concepts/metric-reconciliation]] § T40 CSV schema); every metric is
reported as the mean over `n_runs` with confidence intervals (CI method
pinned by T44).

## 8. Adversary-catalog coverage

[[concepts/adversary-model]] defines **18 valid `(adversary, protocol)`
pairs**. Family C exercises the three generic capabilities that have a
Week-10 experiment task:

- §3 `delay-emission` → T51 (delayed voters);
- §4 `withhold-participation` → T52 (non-participating validators);
- §5 `equivocate-vote` → T53 (equivocating nodes).

Across all four protocols these are **12 of the 18 pairs**. The triple
enumeration and intensity grids are in [[concepts/experiment-matrix-runs]]
§3.

**Uncovered: 6 pairs.** §6 `disrupt-leader` (3 pairs — Snowman is `N/A`)
and the §7 protocol-specific surfaces (Snowman colluding sub-sampler,
Narwhal+Tusk data-availability withholding, Casper FFG slashable-
equivocation refinements — 3 pairs) have **no Week-10 experiment task**.
T18's verify clause originally asserted "T51–T53 … without gaps"; a
human scope decision (2026-05-18) resolved the mismatch by **narrowing
the coverage claim** — T18's verify clause and
[[concepts/adversary-model]] §1 / §8 now state that T51–T53 exercise 12
of the 18 catalog pairs.

Per scope discipline (`CLAUDE.md` § Hard rules — adding experiment tasks
is a roadmap change, human-only), this matrix documents only the
surfaces the existing tasks cover. The 6 uncovered pairs remain
catalogued design space with no experiment task; the decision is
recorded in `TASKS.md` § Backlog.

## 9. Open to revision

Per the W3 design-contract precedent, the following are expected to be
re-examined; each promotes to a `## Revisions` entry rather than a
silent overwrite.

- **Workload default values** (§6). `arrival_process`, `tx_bytes`, and
  `conflict_rate` are Engineer-chosen simulator-setup values; a
  Researcher pass against the benchmark workloads in [9], [11], [13] may
  revise them. `tx_bytes = 512` is the only one grounded in a source.
- **`offered_rate = 100` tx/s** (§6). Provisional sub-saturation point;
  T41 / T42 recalibrates it down if any protocol saturates below it.
- **`workload_conflict_rate` sweep** (§6). Held at `0.0`; a sweep is
  added if a goodput RQ needs workload-induced conflicts.
- **Adversary-coverage gap** (§8). 6 of 18 catalog pairs have no
  experiment task — a human roadmap decision per the `TASKS.md` Backlog.
- **Peak-throughput `W` and `×1.5`** (§6). Sensitivity-sweep candidates;
  `W = 10 s` may move if the hold window misses steady state.
- **FFG `slot_duration` rescaling grid** (§5,
  [[concepts/experiment-matrix-runs]] §2). Extends the
  `{50, 100, 500} ms` sweep upward; if the heaviest timeline forces an
  impractical slot, that FFG row is dropped and reported as a gap.

## 10. Sources

Design contract; no primary-literature citations of its own. The one
external value committed here — `workload_tx_bytes = 512` — traces to:

- [11] [[sources/2026-04-21_danezis-narwhal-tusk-2022]] — Narwhal+Tusk
  benchmark transaction size.

**Companion page:**

- [[concepts/experiment-matrix-runs]] — the enumerated run catalog:
  network-timeline parameter tables, the FFG slot-duration pairing
  table, adversary triple tables, and the run-count budget.

**Inbound (existing wiki pages):**

- [[concepts/research-questions]] — RQ1–RQ5; the `(IV, primary metric)` columns this matrix instantiates.
- [[concepts/metric-reconciliation]] — calibration defaults, FFG coherence constraint, Snowman rescaling precedent, the T40 CSV `workload_*` contract.
- [[concepts/evaluation-metrics]] — metric definitions, time anchors, the peak-throughput ramp §6 parameterises.
- [[concepts/adversary-model]] / [[concepts/adversary-model-runtime]] — the adversary catalog and per-protocol intensity unit Family C draws from.
- [[concepts/network-model]] / [[concepts/network-model-phases]] — the honest-network delivery contract and phase mechanics; the latency-only richness level §6 relies on.
- [[concepts/node-model]] — per-`Node` RNG seeding consumed by §7.
- [[concepts/synchrony-models]] — the partial-sync / asynchronous / GST narratives the Family B timelines realise.

**Forward references (not yet authored):** [[concepts/reproducibility]]
(T27) consumes the §7 policy; [[concepts/output-format]] (T40) finalises
the CSV schema whose axes this page pins.

## Revisions

### [2026-06-03] T41 — peak-throughput ramp deferred (model cannot saturate)

The §6 peak-throughput offered-load ramp (`{25,50,…,1600}` tx/s, hold
`W=10 s`, sustained-until-`commit_latency_p99`-×1.5) assumes the protocol
**saturates** as offered load rises. T41 found this is not realizable on
the current simulator: the network is latency-only ([[concepts/network-model]]
§1, no link-capacity model), nodes have no per-transaction or per-byte CPU
cost, and message *counts* are per-instance, not per-transaction — so a
block carrying 1 tx and one carrying 1 000 commit at identical simulated
latency. Nothing saturates; a measured `peak_tps` would be a configuration
artifact (the proposer cadence ceiling), not a protocol-performance
property. **`peak_tps` is therefore deferred** to a task that first adds a
capacity/cost model (candidate: T58 enhancement, or a dedicated task);
[[concepts/output-format]] §13 records the matching column-register move.

What T41 *did* land from §6: a real arrival-process workload
([[concepts/output-format]] §13 — `poisson`/`constant`, `tx_bytes=512`,
`conflict_rate=0.0`), the fixed sub-saturation `offered_rate = 100` tx/s
operating point (Family A scaling runs), and the `goodput` measurement.
The `offered_rate` was **not** recalibrated down (the §6 "Open to revision"
clause): no protocol saturated below it — at sub-saturation `goodput`
tracks `offered_rate` modulo the finality-tail effect (Casper FFG's
per-epoch finality leaves the window's trailing slots unfinalized, so its
in-window `goodput` sits ~20 % below offered, vs ~5 % for the per-instance
PBFT/Snowman protocols). Evidence: [[experiments/2026-06-03_scaling-baseline]].

### [2026-06-10] T46 — Family B locked methodology (n-axis, buffer/clip, comparison column)

Human decision 2026-06-10 (Week 9) fixes the Family B (Delay) plan. This
amends §3 and pins the buffer/clip and comparison-column rules the §3 table
left to the delay tasks. Evidence: [[experiments/2026-06-10_delay-moderate]].

- **`n` axis for Family B (amends §3).** Family B is no longer the fixed
  `n = 10` of the §3 table; it sweeps **`n ∈ {10, 25}`**. `n = 10` is the
  shared anchor with Family C; `n = 25` (`3f+1`, `f = 8`) amplifies delay
  degradation. So Family B plots/aggregates gain an `n` dimension
  (protocol × timeline × `n`). Snowman `(K, α_c, β)` rescale with `n`
  (§ Snowman parameter rescaling, [[concepts/metric-reconciliation]]) — at
  `n = 25`, `K = 20`, `α_c = 16`, `β = 15`; `n = 25` is a normal input, not
  a margin case. The §3 "Why `n = 10` for Families B and C" paragraph now
  applies to **Family C only**; Family C (adversarial, T51–T56) **stays at
  `n = 10`** — the symmetric Family-C-at-`n=25` extension is parked in
  `TASKS.md` Backlog (2026-06-10) and is not part of this Revision.
- **Six-timeline Family B plan; T46 lands two.** Family B is the six
  timelines of [[concepts/experiment-matrix-runs]] §2 (`delay-uniform`,
  `delay-exponential`, `delay-heavy-tail`, `delay-heavy-tail-loss`,
  `partial-sync-gst`, plus the `static-baseline` `constant` RQ1 point). T46
  lands exactly **two**: `delay-uniform` (uniform[100, 500] ms, mean
  300 ms) and `delay-exponential` (exponential mean 300 ms), both
  `E[delay] = 300 ms` ⇒ FFG `slot_duration = 1200 ms` (§5). T47 owns the
  heavy-tail / loss / partial-sync-gst timelines.
- **Buffer/clip rule (pins the 2026-05-18 Backlog decision).** Time-bounded
  delay runs run to `W + buffer` with `buffer ≥` one full protocol round;
  metrics cover every instance that **started** in `[0, W]` even if it
  finalizes in the buffer; events with `t > W` are clipped. Calibration is a
  per-task self-check: probe one seed/regime → measure one-round latency →
  set `buffer` to that, `W` large enough for `≥ 25` decisions, assert
  clipped-fraction `< 5 %` (else flag Blocked). T46's calibration:
  `W = 480 s`, `buffer = 48 s` (Snowman's ≈ 16 s `β`-poll tail is binding);
  guard PASS.
- **Cross-protocol latency column = `commit_latency_ms`** (uniformly defined
  for all three protocols), **not** `finality_latency_ms` — see
  [[concepts/output-format]] §13. Each timeline's `slot_duration` is recorded
  on the output so plots can annotate it (§5 "reported not hidden").
