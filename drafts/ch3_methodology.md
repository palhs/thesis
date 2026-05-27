# Chapter 3 — Methodology

## 3.1 Chapter roadmap

Chapter 1 stated the research questions that drive this thesis and
Chapter 2 documented the unified-harness gap in the existing comparative
literature. The present chapter describes the methodology that closes
that gap and operationalizes RQ1–RQ4 [[wiki/concepts/research-questions]].
The methodology rests on three claims about how the simulator is built:
a single system model serves all four families without protocol-specific
concessions [[wiki/concepts/system-design]]; a uniform metric schema
admits the structural asymmetries between linear-chain and DAG output,
between per-block and per-epoch finality, and between layered and
single-layer message structure without redefining any metric per family
[[wiki/concepts/metric-reconciliation]]; and the experiment matrix is
constructed so the independent variable of each research question is
varied in isolation [[wiki/concepts/experiment-matrix]].

This first pass establishes the framework end-to-end on the two
protocols implemented through Week 6: PBFT and Casper FFG. The remaining
two protocols, Snowman (§3.3.3) and Narwhal+Tusk (§3.3.4), are present
as deferred subsections; their detailed treatment lands with tasks
T36.1 and T36.2 once the corresponding implementations exist in `src/`.
The system model (§3.2), the simulation setup (§3.4), and the
family-agnostic half of the metric schema (§3.5) are written so that
they require no revision when the deferred subsections are filled.

## 3.2 System model

The simulator is a single-process discrete-event system in which five
component types are layered into one run [[wiki/concepts/system-design]].
The harness builds the wired system from a configuration cell and drives
the run; the scheduler owns the single run loop and the virtual clock;
the network delivers messages with configurable delay and loss; the
validators execute protocol logic; the event logger captures the event
stream that the metric reduction consumes. Control flow is
one-directional: the harness wires the system once and calls
`Scheduler.run()`; from that point onward, validators act only through
their outbound API, never by calling another component directly
[[wiki/concepts/node-model]].

**Figure 3.1 ([[diagrams/runtime/macro]]).** Macro runtime view of one
seeded run.

### 3.2.1 Discrete-event execution

The scheduler is custom rather than SimPy-based, built on a binary
min-heap over the tuple `(t, node_id, seq, event)`
[[wiki/concepts/simulation-design]]. Three event classes pin the
contract — `Delivery`, `TimerFire`, and `PhaseAdvance` — and the
dispatch routes each class to a fixed handler. The `(t, node_id, seq)`
tie-break is uniquely valued by construction, which together with the
centralization of randomness in scheduler- and node-owned RNG streams
forces byte-identical replay of any run from the same global seed
[[wiki/concepts/simulation-design-runtime]]. The simulator never reads
wall-clock time; virtual time is advanced only by events popped from
the heap.

### 3.2.2 Node model

A validator is a shared lifecycle and a per-protocol finite-state
machine. The shared lifecycle exposes three inbound entry points
(`start(t)` at bootstrap, `on_message(msg, t)` per delivery,
`on_timer(timer_id, payload, t)` per fired timer) and five outbound
calls (`send`, `broadcast`, `set_timer`, `cancel_timer`, `emit`), with
a node-scoped RNG for any non-determinism the protocol needs
[[wiki/concepts/node-model]]. The two-layer split keeps scheduler
infrastructure uniform across protocols while the per-protocol
finite-state machine carries all family-specific behavior. Each
protocol implemented under `src/` subclasses the shared `Node` and
overrides only the inbound entry points and the state transitions; the
outbound API is identical across protocols.

### 3.2.3 Network model

The network is a latency-only full mesh with phase-driven mechanics
[[wiki/concepts/network-model]]. Delivery is at-most-once with no order
guarantee and no retries, matching the assumption every protocol in
scope makes about the layer it sits on. Each network phase declares a
delay distribution (constant, uniform, exponential, or heavy-tailed),
an independent Bernoulli drop probability, and an optional partition
map [[wiki/concepts/network-model-phases]]. Phase boundaries are
scheduled as `PhaseAdvance` events at the start of the run, so a single
seeded run can traverse a partial-synchronous narrative that crosses
Global Stabilization Time. The model carries no link-capacity
dimension; the saturation ramp in §3.4 therefore probes the protocol
rather than the link.

### 3.2.4 Message envelope and protocol vocabulary

Every wire message is a `Message(src, dst, type, payload, t_sent)`
envelope; the per-protocol type-and-payload catalog is fixed in
[[wiki/concepts/message-types]]. PBFT carries five types
(`PRE-PREPARE`, `PREPARE`, `COMMIT`, `VIEW-CHANGE`, `NEW-VIEW`); Casper
FFG carries three (`BLOCK-PROPOSAL`, `ATTESTATION`,
`SLASHING-EVIDENCE`). The per-type byte budget feeds the
`bytes_per_acu` metric in §3.5.

### 3.2.5 Adversary surface

Byzantine behavior attaches as an optional per-validator
`AdversaryProfile` slot, not as a scheduler-layer hook
[[wiki/concepts/adversary-model]]. A profile intercepts the host
validator's outbound calls — for example, suppressing a vote,
duplicating it to two recipients with disjoint payloads, or delaying
its emission — but adds no component and no event class
[[wiki/concepts/adversary-model-runtime]]. The catalog contains four
generic capabilities (silent non-participation, delayed voting,
equivocation, leader disruption) and three protocol-specific surfaces,
giving eighteen valid `(adversary, protocol)` pairs. Twelve of those
are exercised by the Week-10 experiments T51–T53; the remaining six are
catalogued design space, retained for reference but deliberately out of
experimental scope.

## 3.3 Algorithms

Each protocol subsection follows the same four-part skeleton —
mechanism, simulator mapping, simplifications, and event-handler shape
— paralleling the per-family layout of Chapter 2 §2.4 but narrowed to
the concrete implementations under `src/`.

### 3.3.1 PBFT

*Mechanism.* PBFT [4] is a leader-driven three-phase commit protocol
over `3f+1` replicas under partial synchrony [3]. The designated
primary broadcasts a `PRE-PREPARE`; each replica that validates it
broadcasts a `PREPARE`; once a replica collects a `2f+1`
prepare-quorum, it broadcasts `COMMIT`; the accumulation of a `2f+1`
commit-quorum finalizes the block [[wiki/algorithms/pbft]]. Liveness is
recovered after Global Stabilization Time through a view change in
which `2f+1` `VIEW-CHANGE` messages drive a `NEW-VIEW` that re-anchors
prepared-but-uncommitted requests.

*Simulator mapping.* Only the classical variant is implemented: single
primary, no HotStuff threshold-signature linearization, no Tendermint
round-robin rotation. Two knobs are exposed to experiments: the
view-change timeout, which defaults to `3·E[round_latency]` and uses an
exponential per-view backoff `vc_delay·2^view`, and the Byzantine
fraction. The exponential backoff is required for view-change recovery
to terminate deterministically: a flat timeout that has fired once will
fire again in the same delay regime.

*Simplifications.* The simulator carries no cryptographic signatures;
message digests serve integrity and deterministic replay only. The
`VIEW-CHANGE` evidence a replica attaches is therefore an assertion
rather than a cryptographic prepared certificate, and the adversary
catalog deliberately carries no evidence-forgery capability. The
boundary affects no honest-path result and no equivocating-primary
result; within-threshold safety against forged view-change evidence is
assumed by construction [[wiki/algorithms/pbft]].

*Event-handler shape.* Three inbound entry points dispatch the
three-phase commit and the view-change recovery; the `decided` event
fires on commit-quorum collection. Figure 3.2 gives the
handler-dispatch shape.

**Figure 3.2 ([[diagrams/protocols/pbft]]).** PBFT three-phase commit
for one `(view, seq)` instance with the view-change branch.

### 3.3.2 Casper FFG

*Mechanism.* Casper FFG [7] is a two-round BFT finality gadget over a
chain of blocks. Time is partitioned into fixed-length epochs of
`slots_per_epoch` slots, and the first block of each epoch is
designated a checkpoint. Validators attest to `<source, target>`
checkpoint pairs; a checkpoint `T` is justified once attestations
representing at least two-thirds of total stake support a link from a
justified ancestor; `T` is finalized once it is justified and its
direct child is also justified [[wiki/algorithms/pos]]. Safety is
accountable: a validator that signs two FFG votes with the same target
or surrounds one of its own votes can be cryptographically convicted
and its stake slashed.

*Simulator mapping.* The implementation is a simplified Casper FFG
gadget with stake-weighted proposer selection. Proposer assignment is
a pure function of `(global_seed, slot)` through blake2b, and the
100-round fairness check at four stake distributions is recorded in
[[experiments/2026-05-23_pos-selection-fairness]]. Two calibration
defaults diverge from Ethereum's deployed values:
`slots_per_epoch = 4` (against Ethereum's 32) and
`slot_duration = 100 ms` (against Ethereum's 12 s), both pinned in
[[wiki/concepts/metric-reconciliation]]. The first preserves FFG's
epoch character at the smallest value that still admits a meaningful
multi-slot epoch; the second keeps FFG finality at the same order of
magnitude as the other three protocols' commit latency, so that
cross-protocol plots remain readable on a single axis. The `{16, 32}`
and `{500 ms}` sensitivity-sweep points defend the comparative ordering
at production scale.

*Simplifications.* LMD-GHOST fork choice is not implemented;
`Chain.head` is the block at the greatest known slot under an
honest-path linear chain [[wiki/concepts/system-design-protocols]].
Delay-induced reorgs are out of scope until the delay sweep of Week 9.
Attestation cadence is once per epoch at a configurable offset rather
than once per slot; the per-slot head vote belongs to LMD-GHOST and
contributes no extra information to the FFG gadget once fork choice is
honest-path-linear.

*Event-handler shape.* The slot loop drives proposer selection and
attestation emission; FFG vote aggregation transitions epoch state
through unjustified → justified → finalized; the `decided` event fires
on finalization.

**Figure 3.3 ([[diagrams/protocols/casper-ffg]]).** Casper FFG
justify→finalize for one epoch with the slashing branch on detected
double or surround votes.

### 3.3.3 Snowman

`TODO(T36.1).` Snowman is the deterministically-ordered linearization
of the Avalanche family deployed on Avalanche's C-Chain and Subnet
stack [9]. The simulator's Snowman implementation does not yet exist;
T36.1 picks up this subsection once it does. The parameter-rescaling
rule that holds Snowman comparable to the other three protocols at
thesis-scale `n` is pinned in
[[wiki/concepts/metric-reconciliation]], and the empirical
safety-violation invariant `ε ≤ (1 − α_c/K)^β` carries through to §3.5.

### 3.3.4 Narwhal+Tusk

`TODO(T36.2).` Narwhal+Tusk is the DAG-based representative of the
fourth family, decoupling data availability (the Narwhal mempool) from
ordering (the Tusk anchor commit) [11]. The simulator's Narwhal+Tusk
implementation does not yet exist; T36.2 picks up this subsection once
it does. The mempool-versus-consensus message split that the family
forces on the metric schema is pinned in
[[wiki/concepts/metric-reconciliation]] and surfaces in §3.5 as two CSV
columns rather than one.

## 3.4 Simulation setup

Four mechanisms together make one experiment-matrix cell reproducible
from a configuration file paired with a global seed.

*Six-phase bootstrap.* The harness drives a fixed six-phase bootstrap
to wire the system: construct the scheduler, network, and validators;
register each validator with the network; bind each validator to both
the scheduler and the network under a split-ownership invariant (the
scheduler owns `set_timer`, `cancel_timer`, and `emit`; the network
owns `send` and `broadcast`); attach the event logger sink; call
`Network.start()` and `Node.start(t=0)` to populate the heap with the
first events; call `Scheduler.run(t_max, stop_when)`
[[wiki/concepts/simulation-design]]. The split-ownership invariant
prevents a scheduler–network reference cycle and is the reason the run
loop is the single canonical run loop in the system.

*Reproducibility.* The same configuration file paired with the same
global seed produces a byte-identical event stream. Virtual time is
owned exclusively by the scheduler, all randomness is centralized in
scheduler- and node-owned RNG streams derived deterministically from
the global seed, and the network draws its stochastic delivery paths
from a network-scoped RNG seeded from the same source. The
harness-level reproducibility contract that consolidates the three
component-level contracts is set out in
[[wiki/concepts/reproducibility]].

*Experiment matrix.* An experiment is one point in the product of six
axes — validator-set size `n`, network timeline, adversary, protocol
knobs, workload, seed [[wiki/concepts/experiment-matrix]]. The
simulator sweeps `n ∈ {4, 7, 10, 16, 25}`, which is `3f+1` at
`f ∈ {1, 2, 3, 5, 8}` and gives a clean Byzantine-threshold instance at
each point. Experiments group into three run families that fix five
axes and sweep one: Family A (Scaling) sweeps `n` under an honest
validator set on the `static-baseline` network for RQ3; Family B
(Delay) sweeps the network timeline at `n = 10` for RQ1; Family C
(Adversarial) sweeps the `(adversary, intensity)` pair at `n = 10` for
RQ2 and RQ4 jointly. Workload defaults are pinned at a Poisson arrival
process, 512-byte transactions matching the Narwhal benchmark [11], a
zero conflict rate, and an offered rate of 100 transactions per second
under the sub-saturation latency regime. Peak throughput is measured
by a separate offered-load ramp through the geometric grid
`{25, 50, 100, 200, 400, 800, 1600} tx/s`, holding each rate for
`W = 10` simulator-seconds and declaring a rate sustained when its
`commit_latency_p99` stays within a factor of `1.5` of the previous
rate's value. The four protocols share the same seed set at every
configuration point so the cross-protocol comparison is paired under
common random numbers — a standard variance-reduction technique that
allows cross-protocol verdicts to be drawn at modest `n_runs = 20`
(`30` near-threshold) with 95% confidence intervals
[[wiki/concepts/experiment-matrix-runs]].

*FFG coherence constraint.* Pairing the Casper FFG
`slot_duration = 100 ms` baseline with a network phase in which
`E[delay]` is not far below the slot duration produces a
degraded-finality regime that is not Casper FFG, because attestations
from distant validators arrive after the slot boundary. The matrix
therefore enforces `slot_duration ≥ 4·E[delay]` on every FFG run and
rescales `slot_duration` upward through the `{50, 100, 500} ms`
sensitivity sweep when the delay sweep of Family B demands it. The
simulator runner refuses an incoherent pairing rather than silently
producing mislabelled numbers [[wiki/concepts/metric-reconciliation]].

A run terminates under any of three OR-composed predicates:
`quiescence` (the heap is empty), `deadline` (the virtual clock has
reached `t_max`), or `predicate` (a caller-supplied `stop_when()`
returns `True`) [[wiki/concepts/simulation-design]]. Time-bounded
experiments deliberately run with a buffer beyond the measurement
window, and the analysis step clips events whose timestamps lie outside
the window; this protects in-window events from truncation by the
deadline tie-break.

## 3.5 Metric schema

The metric schema is uniform across families. Each metric has one
definition, one unit, and one fixed instrumentation point in `src/`;
family-specific differences appear only as different per-protocol
formulas that compute the same column
[[wiki/concepts/evaluation-metrics]].

*Four metric families.* Latency measures how quickly a transaction
reaches commit or finality; throughput measures how many transactions
the protocol commits per unit time; overhead measures the messages,
bytes, and per-validator state the protocol consumes; reliability
measures whether the protocol preserves safety and liveness under
delay and adversary. Safety and liveness here are the operational
counterparts of the foundational properties defined in §2.2: a *safety
violation* is an observed breach of Agreement — two honest validators
commit different values at the same height within one simulator run —
and is counted directly by `fork_rate` and, where applicable, by the
`view_change_or_reorg_count` instrumentation; a *liveness failure* is
an observed breach of Termination — at least one honest validator
fails to commit within the run's measurement window — and is counted
by the complement of `success_rate`. Validity is preserved by
construction in the simulator (the workload generator emits only
well-formed transactions and no protocol module commits a value it did
not receive) and is therefore not instrumented as a separate column.
Every latency metric is anchored at "tx submit,"
the wall-clock moment the workload generator emits the transaction
before it reaches any validator, so end-to-end latency is comparable
across protocols whether or not they carry a separate mempool.
Wall-clock throughout means the simulator's model time, advanced only
by events popped from the scheduler heap; no simulator number is a
real-hardware claim.

*Four structural asymmetries.* Four asymmetries arise when the schema
is instantiated against the four-protocol scope, and a single companion
page resolves each one [[wiki/concepts/metric-reconciliation]]:
linear-chain versus DAG output structure; per-block versus per-epoch
versus per-block-probabilistic versus per-anchor-batch finality regime;
the Narwhal mempool-versus-consensus message split; and Snowman
parameter rescaling at thesis-scale `n`. The reconciliation defines an
*atomic commit unit* (ACU) as the smallest contiguous set of
transactions the protocol commits indivisibly, and rewrites every
"per-block" metric as "per ACU". The ACU is one block for PBFT, one
finalized checkpoint for Casper FFG, one block for Snowman, and one
anchor-batch for Narwhal+Tusk; the same denominator therefore admits
both layered and single-layer protocols without a conditional formula.

*Per-protocol instantiation.* Table 3.1 collects the latency and
throughput formulas for the two protocols implemented at this stage;
Table 3.2 collects the overhead and reliability formulas. Snowman and
Narwhal+Tusk rows are reserved for T36.1 and T36.2; the table
structure is fixed now so the deferred subsections fill rows rather
than restructure columns.

**Table 3.1 — Latency and throughput per protocol.** Adapted from
[[wiki/concepts/metric-reconciliation]].

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :-- | :-- | :-- | :-- | :-- |
| `commit_latency_ms` | tx submit → containing block enters `PRE-PREPARE` and persists through commit | tx submit → containing block proposed at next slot | `TODO(T36.1)` | `TODO(T36.2)` |
| `finality_latency_ms` | tx submit → `2f+1` `COMMIT` collected for same block | tx submit → checkpoint containing tx is finalized (≥ 2 epochs later) | `TODO(T36.1)` | `TODO(T36.2)` |
| `round_latency_ms` | one of three phases | one slot | `TODO(T36.1)` | `TODO(T36.2)` |
| `tps` | committed-tx count / window | finalized-tx count / window | `TODO(T36.1)` | `TODO(T36.2)` |
| `goodput` | identical to `tps` (no reorg-before-finality) | `tps` restricted to checkpoints that survive to finalization | `TODO(T36.1)` | `TODO(T36.2)` |
| `mempool_tps` | `0` (no separate mempool) | `0` | `TODO(T36.1)` | `TODO(T36.2)` |

**Table 3.2 — Overhead and reliability per protocol.** Adapted from
[[wiki/concepts/metric-reconciliation]].

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :-- | :-- | :-- | :-- | :-- |
| `consensus_msgs_per_acu` | `1 + 2n + 2n² = O(n²)` | `O(n)` FFG attestations per epoch, BLS-aggregated | `TODO(T36.1)` | `TODO(T36.2)` |
| `mempool_msgs_per_acu` | `0` | `0` | `TODO(T36.1)` | `TODO(T36.2)` |
| `bytes_per_acu` | dominated by signatures × `O(n²)` | dominated by aggregated attestation + payload per slot | `TODO(T36.1)` | `TODO(T36.2)` |
| `success_rate` | fraction of rounds reaching `COMMIT` quorum | fraction of epoch boundaries producing a justified→finalized pair | `TODO(T36.1)` | `TODO(T36.2)` |
| `fork_rate` | `0` by construction | fraction of proposed blocks reorged before their checkpoint finalizes | `TODO(T36.1)` | `TODO(T36.2)` |
| `f_max` | empirical `f_max_count`; theoretical `f < n/3` | empirical `f_max_stake`; theoretical `f < 1/3` of stake | `TODO(T36.1)` | `TODO(T36.2)` |

*Calibration defaults and sensitivity sweeps.* Calibration defaults are
committed at the metric-reconciliation layer before any baseline
experiment runs, and sensitivity sweeps never feed back into default
selection. The two Casper FFG defaults that diverge from Ethereum's
deployed values (§3.3.2) are the only departures from published
parameters; the `{16, 32}` and `{500 ms}` ends of the sensitivity sweep
confirm whether the cross-protocol ordering on the primary metric of
each research question survives the trip to production scale. A
verdict is reported as *robust* when the ordering is preserved across
the full sweep and as *knob-sensitive* when it is not; in the second
case Chapter 4 surfaces the crossover point rather than picking a
winner [[wiki/concepts/metric-reconciliation]].

*The output row.* One row of the comparative CSV is produced per
`(config, seed)` after `n_runs` aggregation; every metric column is the
mean over `n_runs` seeded trials at the row's full configuration, and
95% confidence intervals are surfaced alongside each mean. The columns
Chapter 4 will read are `commit_latency_ms`, `finality_latency_ms`,
`tps`, `goodput`, `peak_tps`, `consensus_msgs_per_acu`,
`mempool_msgs_per_acu`, `bytes_per_acu`, `success_rate`, `fork_rate`,
`view_change_or_reorg_count`, and the two mutually exclusive
`f_max_count` and `f_max_stake` columns, of which exactly one is
populated per row. The finalized CSV layout is `TODO(cite)` —
`wiki/concepts/output-format` is the open T40 deliverable.

## 3.6 Chapter summary

The system model (§3.2) and metric schema (§3.5) are family-agnostic;
the four families' structural asymmetries are absorbed upstream of any
experiment by the ACU denominator, the layered-versus-single-layer
message split, and the per-protocol finality semantics. Two protocols
are implemented at this stage — PBFT and Casper FFG — and the deferred
subsections §3.3.3 and §3.3.4 are explicit placeholders for the
Snowman and Narwhal+Tusk implementations that T36.1 and T36.2 will
fill. Chapter 4 reports the baseline, delay, and adversarial sweeps the
matrix prescribes and answers RQ1–RQ4 against the metric schema fixed
here.
