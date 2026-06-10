# Chapter 3 — Methodology

## 3.1 Overview

This chapter describes the simulator that closes the gap of Chapter 2 and
operationalizes RQ1–RQ4 [[wiki/concepts/research-questions]]: a single
discrete-event system in which the four families run under one system model
(§3.2), one metric schema (§3.5), and one experiment matrix (§3.4) that
varies each research question's independent variable in isolation. The
approach extends the instrumented-harness methodology of Gervais *et al.*
[17] from Proof-of-Work to the four BFT families.

Three protocols are implemented at this stage — PBFT, Casper FFG, and
Snowman. The fourth, Narwhal+Tusk (§3.3.4), is a deferred placeholder that
task T36.2 fills once its implementation exists in `src/`. The system model
(§3.2), the simulation setup (§3.4), and the family-agnostic metric schema
(§3.5) are written so that they need no revision when that subsection is
filled.

## 3.2 System model

The simulator is a single-process discrete-event system. Control flow is
one-directional: the harness wires the components once and calls
`Scheduler.run()`, after which each validator acts only through its outbound
messaging API, never by calling another component directly, so that protocol
behavior and scheduler infrastructure stay cleanly separated
[[wiki/concepts/system-design]]. Figure 3.1 gives the static structure — one
experiment-matrix cell and a seed enter a fixed engine and leave as one
comparable row of results — and Figure 3.2 the engine's run loop; Table 3.1
lists the components both exercise. This fixed engine isolates protocol
behavior: any difference between two rows is attributable to the protocol
logic alone, since the builder, scheduler, network, and logger are identical
across protocols. Isolation is not the same as commensurability, however. The
four protocols do not produce the same kind of decision, so putting them on a
single scale is a separate step, performed downstream by the metric schema
under stated conventions (§3.5) rather than secured by the engine being
shared.

**Figure 3.1 ([[diagrams/runtime/architecture]]).** Structural view: a single
fixed harness in which only the protocol-logic slot is swapped, turning one
experiment-matrix cell and seed into one comparable `results.csv` row.

**Figure 3.2 ([[diagrams/runtime/event-loop]]).** One turn of the scheduler's
event loop — pop the next event, advance the virtual clock to it, let a node
react, enqueue what it produces — with the three termination paths.

**Table 3.1 — Simulator components.**

| Component | Role | Key design property |
|:--|:--|:--|
| Harness | Builds the system, drives the run, and reduces events to metrics | Wires the components once, then hands control to the scheduler |
| Scheduler | Owns the single run loop and the virtual clock | Orders events deterministically, so any run replays identically from its seed |
| Network | Delivers messages between validators | Latency only — configurable per-phase delay, loss, and partition; at-most-once and unordered |
| Node | Executes one validator's protocol logic | A shared lifecycle, plus a protocol-specific state machine |
| Message | Carries protocol data on the wire | A uniform envelope with a per-protocol type catalog (Table 3.2) |
| Adversary profile | Applies an optional Byzantine deviation to one validator | Intercepts that validator's outgoing messages; adds no new component |

Two properties of this model carry the methodology. First, determinism:
virtual time and every random draw derive from a single global seed, so a
configuration paired with a seed reproduces a byte-identical event stream and
any reported number is exactly reproducible [[wiki/concepts/reproducibility]].
Second, network phases are scheduled in advance, so a single seeded run can
cross a partial-synchronous Global Stabilization Time without intervention
[[wiki/concepts/network-model-phases]]. The four Byzantine strategies a profile
can apply are catalogued in [[wiki/concepts/adversary-model]]; §3.4 names the
three the RQ4 sweep exercises.

## 3.3 Algorithms

Table 3.2 fixes how the three implemented protocols are realized in the
simulator: the message types each carries, the event that signals a commit,
the knobs exposed to experiments, and the principal simplification each makes
relative to its family. The mechanism of each family is established in
Chapter 2 (§2.3, Table 2.1) and is not repeated here; the subsections below
add only the implementation-specific detail Table 3.2 cannot carry. The
Narwhal+Tusk column is reserved for T36.2.

**Table 3.2 — The implemented protocols in the simulator.**

| | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
|:--|:--|:--|:--|:--|
| Message types | `PRE-PREPARE`, `PREPARE`, `COMMIT`, `VIEW-CHANGE`, `NEW-VIEW` | `BLOCK-PROPOSAL`, `ATTESTATION`, `SLASHING-EVIDENCE` | `BLOCK-ANNOUNCEMENT`, `QUERY`, `QUERY-RESPONSE` | `TODO(T36.2)` |
| `decided` fires when | `2f+1` `COMMIT` collected for one `(view, seq)` | a checkpoint and its direct child are both justified | the confidence counter reaches `β` | `TODO(T36.2)` |
| Knobs exposed | view-change timeout (`3·E[round_latency]`, `×2^view` backoff); Byzantine fraction | `slots_per_epoch` (4); `slot_duration` (100 ms); justification threshold | `(K, α_p, α_c, β)` via the rescaling rule; sampling seed | `TODO(T36.2)` |
| Principal simplification | classical variant only — no HotStuff/Tendermint, no signatures | no LMD-GHOST fork choice; attest once per epoch; slashing modeled as a halt | linearized Snowman only — no DAG-Avalanche; no stake-weighted sampling | `TODO(T36.2)` |

### 3.3.1 PBFT

Only the classical variant is implemented: a single primary, no HotStuff
threshold-signature linearization, no Tendermint rotation. The view-change
timeout uses an exponential per-view backoff `vc_delay·2^view`, which is
required for view-change recovery to terminate deterministically — a flat
timeout that has fired once fires again in the same delay regime. The
simulator carries no cryptographic signatures; message digests serve
integrity and deterministic replay only, so a `VIEW-CHANGE` message's
prepared evidence is an assertion rather than a cryptographic certificate, and
the adversary catalog deliberately carries no evidence-forgery capability.
This boundary affects no honest-path result and no equivocating-primary
result; within-threshold safety against forged view-change evidence is assumed
by construction [[wiki/algorithms/pbft]]. The classical variant sits at the
worst-case end of the family's `O(n) → O(n²)` message-complexity range, so the
RQ3 verdict reported for "PBFT-style" is a verdict on classical PBFT
specifically.

**Figure 3.3 ([[diagrams/protocols/pbft]]).** PBFT three-phase commit for one
`(view, seq)` instance with the view-change branch.

### 3.3.2 Casper FFG

The implementation is a simplified Casper FFG gadget with stake-weighted
proposer selection: proposer assignment is a pure function of
`(global_seed, slot)` through blake2b, verified for fairness at four stake
distributions in [[experiments/2026-05-23_pos-selection-fairness]]. Two
calibration defaults diverge from Ethereum's deployed values:
`slots_per_epoch = 4` (against 32) and `slot_duration = 100 ms` (against
12 s), both pinned in [[wiki/concepts/metric-reconciliation]]. The first
preserves FFG's epoch character at the smallest value that still admits a
multi-slot epoch; the second keeps FFG finality at the same order of magnitude
as the other protocols' commit latency, so cross-protocol plots remain
readable on one axis. The `{16, 32}` and `{500 ms}` ends of a sensitivity
sweep defend the comparative ordering at production scale. LMD-GHOST fork
choice is not implemented — `Chain.head` is the block at the greatest known
slot under an honest-path linear chain — and slashing is modeled as a halt
event with the offending deposit logged as burned, consistent with the
economic-design exclusion of §1.4.

**Figure 3.4 ([[diagrams/protocols/casper-ffg]]).** Casper FFG
justify→finalize for one epoch with the slashing branch.

### 3.3.3 Snowman

Only the linearized Snowman variant is implemented; full DAG-Avalanche is out
of scope, which keeps the chain structure directly comparable to PBFT and
Casper FFG under the shared `Node` interface [[wiki/algorithms/avalanche]].
Production Snowman runs on validator sets in the thousands with
`(K, α_p, α_c, β) = (20, 11, 16, 15)`, so the thesis-scale sweep
`n ∈ {4, 7, 10, 16, 25}` requires a rescaling rule that keeps the protocol
comparable across `n`: `K = min(20, n−1)`, `α_p = ⌊K/2⌋ + 1`,
`α_c = ⌈0.8·K⌉`, with `β = 15` held fixed [[wiki/concepts/metric-reconciliation]].
Holding `α_c/K ≈ 0.8` preserves the shape of the safety bound and holding `β`
fixed keeps the probabilistic-finality semantics invariant in `n`, so the
rescaled protocol is one Snowman tracked across the sweep rather than a
distinct parametrization at each `n` [[wiki/concepts/metric-reconciliation]]. Proposer
assignment is round-robin `slot % n`; Snowman is not stake-weighted. The
rescaling degenerates at `n = 4`, where it yields `α_c = K = 3` so a poll
demands unanimity and the bound `(1 − α_c/K)^β` collapses to zero; the `n = 4`
Snowman row is therefore excluded from the comparative tables of Chapters 4
and 5 and reported once as a rescaling sanity check, leaving PBFT and Casper
FFG at `n = 4` unaffected. The honest path is verified at `n ∈ {4, 7, 10}` by
the T38 baseline, in which every validator decides every announced block with
no forks and byte-identical replay [[experiments/2026-05-27_snowman-baseline]].

**Figure 3.5 ([[diagrams/protocols/snowman]]).** Snowman subsampled `K`-peer
poll loop for one block, accepting at counter `≥ β`.

### 3.3.4 Narwhal+Tusk

`TODO(T36.2).` Narwhal+Tusk is the DAG-based representative, decoupling data
availability (the Narwhal mempool) from ordering (the Tusk anchor commit)
[11]. The simulator's implementation does not yet exist; T36.2 fills this
subsection and the reserved column of Table 3.2 once it does. The
mempool-versus-consensus message split the family forces on the metric schema
is pinned in [[wiki/concepts/metric-reconciliation]] and surfaces in §3.5 as
two message columns rather than one.

## 3.4 Simulation setup

### 3.4.1 Reproducibility and the run lifecycle

The harness drives a fixed six-phase bootstrap to wire the system —
construct the scheduler, network, and validators; register each validator
with the network; bind each to the scheduler and the network under a
split-ownership invariant (the scheduler owns `set_timer`, `cancel_timer`,
and `emit`; the network owns `send` and `broadcast`); attach the event logger;
call `Network.start()` and `Node.start(t=0)` to seed the heap; and call
`Scheduler.run(t_max, stop_when)` [[wiki/concepts/simulation-design]]. The
same configuration file paired with the same global seed produces a
byte-identical event stream: virtual time is owned by the scheduler alone, and
all randomness is centralized in scheduler-, node-, and network-scoped RNG
streams derived deterministically from the global seed
[[wiki/concepts/reproducibility]]. A run terminates under any of three
OR-composed predicates — `quiescence` (the heap is empty), `deadline` (the
clock reaches `t_max`), or `predicate` (a caller-supplied `stop_when()`
returns true). Time-bounded runs use a buffer beyond the measurement window,
and the analysis step clips out-of-window events so that in-window events are
not truncated by the deadline. A `deadline` stop is therefore not in itself a
liveness failure: each run records which predicate stopped it, and a run is
scored as a liveness failure only when no honest validator commits inside the
measurement window — the condition the `success_rate` column reports against
`t_max` — not merely because the clock reached the deadline
[[wiki/concepts/output-format]]. This keeps the RQ4 success-rate column free
of runs that were healthy but truncated.

### 3.4.2 The experiment matrix

An experiment is one point in the product of six axes — validator-set size
`n`, network timeline, adversary, protocol knobs, workload, and seed
[[wiki/concepts/experiment-matrix]]. The sweep `n ∈ {4, 7, 10, 16, 25}` is
`3f+1` at `f ∈ {1, 2, 3, 5, 8}`, giving a clean Byzantine-threshold instance
at each point. Experiments group into three run families, each fixing five
axes and sweeping one:

- **Family A (Scaling)** sweeps `n` under an honest validator set on the
  `static-baseline` network, for RQ3.
- **Family B (Delay)** sweeps the network timeline at `n = 10`, for RQ1.
- **Family C (Adversarial)** sweeps the `(adversary, intensity)` pair at
  `n = 10`, for RQ2 and RQ4 jointly — the sub-threshold grid `f ∈ {1, 2, 3}`
  plus the above-threshold points `f ∈ {4, 5}` reserved for the T53
  safety-cliff sweep on PBFT and Casper FFG [[wiki/concepts/experiment-matrix-runs]].

`n = 10` anchors Families B and C: it is the middle of the scaling sweep and
`3f+1` at `f = 3`, enough Byzantine budget for a graded intensity sweep while
small enough to afford many seeds. Workload defaults are a Poisson arrival
process, 512-byte transactions matching the Narwhal benchmark [11], a zero
conflict rate, and an offered rate of 100 transactions per second in the
sub-saturation latency regime. The four protocols share the same seed set at
every configuration point, so the cross-protocol comparison is paired under
common random numbers — a variance-reduction technique that allows verdicts to
be drawn at `n_runs = 20` (`30` near threshold) with 95% confidence intervals
[[wiki/concepts/experiment-matrix-runs]].

Two coherence constraints keep each protocol in its own regime while it sits
on the shared axes. The FFG runner refuses any pairing of
`slot_duration = 100 ms` with a network phase whose `E[delay]` is not far
below the slot duration — attestations from distant validators would arrive
after the slot boundary, producing a degraded regime that is not Casper FFG —
so Family B rescales `slot_duration` upward with the delay regime, by the rule
`slot_duration ≥ 4·E[delay]` [[wiki/concepts/metric-reconciliation]]; the
matrix owns the per-timeline pairing and the runner refuses to start an
incoherent pairing rather than report degraded-finality numbers labeled as
Casper FFG [[wiki/concepts/experiment-matrix]].
Likewise, Snowman's `(K, α_p, α_c)` are not free axes but functions of `n`
fixed by the §3.3.3 rescaling rule, and the `n = 4` point carries no Snowman
comparative data because the rescaling degenerates there.

### 3.4.3 One run, end to end

To make the matrix concrete, consider one cell: PBFT at `n = 10` (so `f = 3`
and the quorum is `2f+1 = 7`), the `static-baseline` network, an honest
validator set, Poisson arrivals at 100 tx/s, and seed 0. The six phases run as
follows; Figure 3.6 gives the same run as a temporal sequence.

**Figure 3.6 ([[diagrams/runtime/macro]]).** One seeded run as a temporal
sequence of the six phases — init, workload, run loop, stop, flush, output —
producing one `results.csv` row.

1. **Init.** The harness builds and wires the scheduler, network, and ten
   validators, and designates one the primary.
2. **Workload.** The harness seeds the primary's mempool with transactions
   drawn from the Poisson process; each transaction `τ` is stamped with its
   submit time `t_submit`.
3. **Run loop.** At its propose timer the primary batches `τ` into a block and
   broadcasts `PRE-PREPARE`. Each validator that accepts it broadcasts
   `PREPARE`; once a validator has collected `7` matching prepares it
   broadcasts `COMMIT`; once it has collected `7` matching commits it emits a
   `decided` event for the block at time `t_decided`. The network applies the
   `static-baseline` delay to every delivery, and the scheduler advances
   virtual time only as it pops events.
4. **Stop.** The run ends at `quiescence` or `t_max`.
5. **Flush and reduce.** The harness reduces the event stream to metrics: the
   commit latency of `τ` is `t_decided − t_submit`; throughput is the
   committed-transaction count over the measurement window; and
   `consensus_msgs_per_acu` is the count of `PRE-PREPARE`, `PREPARE`, and
   `COMMIT` messages for the block — `1 + 2n + 2n² = O(n²)` at this `n`.
6. **Output.** One row, tagged with `(protocol, n, seed)`, is appended to the
   comparative CSV.

Repeating over seeds `0 … 19` under common random numbers yields the cell's
mean and 95% confidence interval. Family B replaces the network phase, Family
C attaches an `AdversaryProfile` to `f` of the validators, and the other three
protocols substitute their own proposer, message types, and `decided`
condition (Table 3.2) — but the six-phase lifecycle is identical for all four.

### 3.4.4 Throughput and the absence of a capacity ceiling

Because the network is latency-only — no link-capacity model, and no
per-transaction or per-byte processing cost — the simulator has no saturation
point: a block carrying one transaction and one carrying a thousand commit at
the same simulated latency [[wiki/concepts/experiment-matrix]]. Sustained
throughput is therefore measured as goodput at the fixed sub-saturation
offered rate, and a peak-throughput measurement is deferred to a task that
first adds a capacity or cost model, rather than reported as a configuration
artifact [[experiments/2026-06-03_scaling-baseline]]. This is a limitation of
the model, recorded here and revisited in Chapter 6.

## 3.5 Metric schema

The metric schema is uniform across families: each metric has one definition,
one unit, and one fixed instrumentation point in `src/`; family-specific
differences appear only as different per-protocol formulas computing the same
column [[wiki/concepts/evaluation-metrics]]. Four metric families cover the
evaluation. *Latency* measures how quickly a transaction reaches commit or
finality; *throughput* measures how many transactions the protocol commits per
unit time; *overhead* measures the messages, bytes, and per-validator state it
consumes; *reliability* measures whether it preserves safety and liveness
under delay and adversary.

Safety and liveness are the operational counterparts of the §2.1 properties. A
*safety violation* is an observed breach of Agreement — two honest validators
commit different values at the same height in one run — counted by `fork_rate`.
A *liveness failure* is an observed breach of Termination — at least one honest
validator fails to commit within the measurement window — counted by the
complement of `success_rate`. Validity holds by construction (the workload
generator emits only well-formed transactions, and no module commits a value
it did not receive) and is not instrumented. For Snowman, whose finality is
probabilistic rather than categorical, the safety-violation rate is reported as
both the analytical bound `(1 − α_c/K)^β` and the empirical conflicting-decision
rate across seeds, in place of the zero that the deterministic-finality
protocols carry below threshold [[wiki/concepts/evaluation-metrics]]. Every latency metric is anchored
at the transaction's submit time, so end-to-end latency is comparable across
protocols whether or not they carry a separate mempool. Throughout, time is
the simulator's model time; no number is a real-hardware claim, and published
production figures serve as order-of-magnitude sanity checks (§1.4), not
validation targets.

The four families differ structurally in four ways — linear-chain versus DAG
output, per-block versus per-epoch versus per-anchor-batch finality, the
Narwhal mempool-versus-consensus message split, and Snowman parameter
rescaling — and a single companion page reconciles each
[[wiki/concepts/metric-reconciliation]]. The key device is the *atomic commit
unit* (ACU): the smallest contiguous set of transactions the protocol commits
indivisibly. Every "per-block" metric is rewritten as "per ACU", where the ACU
is one block for PBFT, one finalized checkpoint for Casper FFG, one block for
Snowman, and one anchor-batch for Narwhal+Tusk — so one denominator admits both
layered and single-layer protocols without a conditional formula. The four
protocols are thereby plottable on one scale under these stated conventions —
the ACU denominator, the Narwhal mempool-versus-consensus split, the Snowman
parameter rescaling, and the Casper FFG calibration of §3.3.2 — and not because
they measure the same physical event. The conventions, not the shared engine,
are what make the comparison commensurable, and a verdict is reported as robust
only when it survives the sensitivity sweep that varies the convention's
governing knob [[wiki/concepts/metric-reconciliation]]. Tables 3.3 and 3.4 give
the per-protocol latency/throughput and overhead/reliability formulas; the
Narwhal+Tusk column is reserved for T36.2.

**Table 3.3 — Latency and throughput per protocol.** Adapted from
[[wiki/concepts/metric-reconciliation]].

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :-- | :-- | :-- | :-- | :-- |
| `commit_latency_ms` | submit → containing block enters `PRE-PREPARE` and persists through commit | submit → containing block proposed at next slot | submit → containing block enters the preference set | `TODO(T36.2)` |
| `finality_latency_ms` | submit → `2f+1` `COMMIT` collected | submit → containing checkpoint finalized (≥ 2 epochs later) | submit → counter reaches `β` (reported with `ε`) | `TODO(T36.2)` |
| `tps` | committed-tx count / window | finalized-tx count / window | decided-block tx count / window | `TODO(T36.2)` |
| `goodput` | identical to `tps` | `tps` restricted to checkpoints that reach finalization | `tps` (post-`β` reorg bounded by `ε`, reported separately) | `TODO(T36.2)` |
| `mempool_tps` | `0` (no separate mempool) | `0` | `0` | `TODO(T36.2)` |

**Table 3.4 — Overhead and reliability per protocol.** Adapted from
[[wiki/concepts/metric-reconciliation]].

| Metric | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :-- | :-- | :-- | :-- | :-- |
| `consensus_msgs_per_acu` | `1 + 2n + 2n² = O(n²)` | `O(n)` attestations per epoch, BLS-aggregated | `O(K·β)` per validator; independent of `n` | `TODO(T36.2)` |
| `bytes_per_acu` | dominated by `O(n²)` votes | aggregated attestation + payload per slot | `O(K·β)` query/response payloads | `TODO(T36.2)` |
| `success_rate` | fraction of rounds reaching a commit quorum | fraction of epoch boundaries producing a justify→finalize pair | fraction of announced blocks reaching counter `β` | `TODO(T36.2)` |
| `fork_rate` | `0` by construction | fraction of blocks reorged before their checkpoint finalizes | pre-`β` preference-switch rate (post-`β` bounded by `ε`) | `TODO(T36.2)` |
| `f_max` | empirical `f_max_count`; theoretical `f < n/3` | empirical `f_max_stake`; theoretical `f < 1/3` stake | empirical `f_max_count`; parameter-dependent | `TODO(T36.2)` |

One row of the comparative CSV is produced per configuration after `n_runs`
aggregation. Continuous metrics are reported as the mean over the seed set
with a 95% Gaussian confidence interval; rate metrics (`fork_rate`,
`success_rate`) as the observed proportion with a 95% Wilson interval, so a
zero-violation outcome is stated as `0/n_runs` rather than a degenerate mean;
and the threshold metric `f_max` as the smallest adversary fraction at which
the row's safety or liveness invariant first breaks. Snowman's probabilistic
finality adds the four rescaled parameters and the derived ratio `α_c/K` as
protocol-specific columns that carry `NaN` on every non-Snowman row, with the
empirical and analytical sides of `(1 − α_c/K)^β` reserved for the RQ4
adversarial sweep. The finalized CSV layout is fixed in
[[wiki/concepts/output-format]].

## 3.6 Summary and threats to validity

The system model (§3.2) and metric schema (§3.5) are family-agnostic: the four
families' structural asymmetries are absorbed upstream of any experiment by
the ACU denominator, the layered-versus-single-layer message split, and the
per-protocol finality semantics. Three protocols are implemented at this stage
— PBFT, Casper FFG, and Snowman — and §3.3.4 is the explicit placeholder for
the Narwhal+Tusk implementation T36.2 will fill.

Three deliberate exclusions in the model bound the claims the chapter can
support, and are stated here rather than left implicit. First, the network
models timing only — delay, loss, and partitions — with no per-byte,
processing, or signature-verification cost [[wiki/concepts/experiment-matrix]].
This favors the protocols whose dominant real-world cost is precisely what the
model omits: PBFT's `O(n²)` signature verification and Narwhal's
data-availability mempool are charged for the messages and bytes they emit,
which the simulator counts directly, but not for the computation those messages
imply. The bias is therefore confined to the latency and per-validator-cost
verdicts; the message-count and byte-count comparisons are unaffected
[[wiki/concepts/evaluation-metrics]]. Second, the workload is a synthetic
open-loop offered load — Poisson arrivals of fixed-size transactions at a
conflict rate of zero (§3.4.2) — which isolates protocol behavior from
workload-induced contention at the cost of not modeling real-traffic
burstiness or double-spends, so conflict-driven reorganization lies outside the
measured range [[wiki/concepts/experiment-matrix]]. Third, the validator-set
sweep `n ∈ {4, …, 25}` sits well below the production scale of the deployed
protocols, Snowman's in particular, so the RQ3 scaling verdicts are stated
within this range and their extrapolation to production `n` rests on the
sensitivity sweeps of §3.3.2 and §3.3.3 rather than on the sweep itself; the
Snowman `n = 4` point, where the rescaling rule degenerates to unanimity, is
excluded outright [[wiki/concepts/output-format]].

Two further properties of the methodology are sources of caveat rather than
exclusion. The cross-protocol comparison is commensurable by convention, not by
identity of the measured event (§3.5), so every comparative verdict is
qualified by the conventions it rests on and is reported as robust only when it
survives the governing sensitivity sweep [[wiki/concepts/metric-reconciliation]].
And the protocols are held in their own regimes on the shared axes by two
coherence rules — the Casper FFG slot-duration-to-delay pairing the runner
enforces (§3.4.2) and the Snowman parameter rescaling that keeps one protocol
across the sweep (§3.3.3) — rather than by freezing knobs that would place a
protocol outside its design point. A `deadline` stop, finally, is scored as a
liveness failure only against the in-window commit condition of §3.4.1, not by
the clock alone. The model's absence of a capacity ceiling (§3.4.4) and the
threats named here are revisited in Chapter 6.

Chapter 4 reports the baseline, delay, and adversarial sweeps the matrix
prescribes and answers RQ1–RQ4 against the schema fixed here.
