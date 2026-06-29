# Chapter 3 — Methodology

## 3.1 Overview

This chapter describes the simulator that closes the gap of Chapter 2 and
operationalizes the data-generating research questions RQ1–RQ4
[[wiki/concepts/research-questions]]: a single discrete-event system in which
the three families run under one system model (§3.2), one metric schema
(§3.5), and one experiment matrix (§3.4) that varies each research question's
independent variable in isolation. The fifth question, RQ5 (whether a
consistent performance–security Pareto frontier emerges across the families),
is a synthesis over the RQ1–RQ4 data rather than a sweep this matrix
prescribes, and is answered in Chapter 5. The approach extends the
instrumented-harness methodology of Gervais *et al.* [17] from Proof-of-Work
to the three BFT families.

## 3.2 System model

The three consensus families differ in leadership, in what one decision commits,
and in layering (established in §2.2, catalogued per protocol in §3.3, Table 3.2),
and do not even produce the same *kind* of decision, so a fair comparison cannot
be read off raw numbers. It needs two things: a single fixed engine that runs all
three identically, and a downstream step that reconciles their differing output
onto one scale.

The engine is short (Figure 3.1). The harness builds the runtime machinery —
scheduler, network, validators, logger — identically for every protocol, swapping
only the protocol-logic slot; a run loop drives the run and a reducer turns the
event stream into one comparable row, once per seed and per cell of the
experiment matrix (§3.4), so the only thing that varies between two rows is the
quantity under study.

**Figure 3.1 ([[diagrams/runtime/architecture]]).** Structural view: a single
fixed harness in which only the protocol-logic slot is swapped, turning one
experiment-matrix cell and seed into one comparable per-trial row.

A run is fully described by its configuration, whose input contract is in
Appendix A. Each validator is granted exactly three capabilities, each owned by a
different component: under this split-ownership invariant the scheduler owns time
and event delivery, the network owns transport (at-most-once and unordered, under
per-phase delay, loss, and partition), and the logger owns the record
[[wiki/concepts/system-design]]. Because every component but the protocol slot is
identical across protocols, any difference between two rows is attributable to the
protocol logic alone. The run loop (Figure 3.2) is identical across all three
protocols; only the validator state machine differs.

**Figure 3.2 ([[diagrams/runtime/event-loop]]).** One turn of the scheduler's
event loop — pop the next event, advance the virtual clock to it, let a node
react, enqueue what it produces — with the three termination paths.

One further property is load-bearing: determinism. Every random draw derives from
a single global seed keyed by stream identity rather than construction order, so a
configuration paired with a seed reproduces a byte-identical event stream and any
reported number is exactly reproducible [[wiki/concepts/reproducibility]].

Finally, an adversary is not a new component but a per-node interceptor that
alters a single validator's outgoing messages
[[wiki/concepts/adversary-model]]; §3.4 names the three the RQ4 sweep exercises.
Making the three protocols *comparable* is then a separate downstream step the
metric schema performs (§3.5).

## 3.3 Algorithms

Each family surveyed in Chapter 2 (§2.2) is represented by a single protocol
[[wiki/algorithms/pbft]], [[wiki/algorithms/pos]], [[wiki/algorithms/avalanche]];
Table 3.1 fixes that correspondence and states why each is a faithful
representative. The protocol names are used from here onward.

**Table 3.1 — Family-to-protocol mapping.**

| Family (Chapter 2) | Implemented protocol | Why it represents the family |
|:--|:--|:--|
| PBFT-style | PBFT | The canonical leader-driven, multi-phase BFT protocol the family is named for; its `3f+1` quorum and view-change are the mechanism every later variant refines. |
| PoS-finality | Casper FFG | The finality gadget Ethereum deploys; it carries the family's defining stake-weighted, two-checkpoint justification rule. |
| Avalanche-style | Snowman | The production linear-chain form of the Avalanche family; it exercises the family's defining repeated random-subsample voting. |

Chapter 2 (§2.2, Table 2.1) establishes the *mechanism* of each protocol family;
this section audits only where the simulator *departs* from the textbook family,
and why each departure leaves the comparative results valid. Table 3.2 summarizes
the three protocols at a glance; its "Main simplification" column headlines each
protocol's departures, and the subsections below carry only the load-bearing ones
that later chapters cite. The per-protocol sequence diagrams are in Appendix A.
The *atomic commit unit* (ACU) named in the table is defined in §3.5. Throughout,
`n` is the validator-set size and
`f` the Byzantine-fault threshold it tolerates (`n = 3f + 1`, §3.4.2); the
Snowman tuple `(K, α_p, α_c, β)` is defined where it is set, in §3.3.3.

**Table 3.2 — The implemented protocols in the simulator.**

| | PBFT | Casper FFG | Snowman |
|:--|:--|:--|:--|
| Leader? | Yes — single rotating primary | Yes — slot proposer | No — leaderless |
| Decision unit (ACU) | one committed block | one finalized checkpoint (+ its ancestors) | one accepted block |
| Message types | `PRE-PREPARE`, `PREPARE`, `COMMIT`, `VIEW-CHANGE`, `NEW-VIEW` | `BLOCK-PROPOSAL`, `ATTESTATION`, `SLASHING-EVIDENCE` | `BLOCK-ANNOUNCEMENT`, `QUERY`, `QUERY-RESPONSE` |
| `decided` fires when | `2f+1` `COMMIT` collected for one `(view, seq)` | a checkpoint and its direct child are both justified | the confidence counter reaches `β` |
| Knobs exposed | view-change timeout (`3·E[round_latency]`, `×2^view` backoff); Byzantine fraction | `slots_per_epoch` (2); `slot_duration` (1 s); justification threshold | `(K, α_p, α_c, β)` via the rescaling rule; sampling seed |
| Main simplification | classical variant only — no HotStuff/Tendermint, no signatures | no LMD-GHOST fork choice; attest once per epoch; slashing modeled as a halt | linearized Snowman only — no DAG-Avalanche; no stake-weighted sampling |

### 3.3.1 PBFT

Only the classical variant is implemented [[wiki/algorithms/pbft]] (three-phase
commit with a view-change branch; sequence diagram in Appendix A). The simulator
carries no cryptographic signatures, so the adversary catalog has no
evidence-forgery capability. Classical PBFT sits at the worst-case `O(n²)` end of
the family's message-complexity range, so the RQ3 verdict reported for
"PBFT-style" is a verdict on classical PBFT specifically.

### 3.3.2 Casper FFG

The implementation is a simplified Casper FFG gadget [[wiki/algorithms/pos#simulator-mapping]]
(justify→finalize over one epoch with a slashing branch; sequence diagram in
Appendix A). Proposer assignment is a deterministic stake-weighted function of the global
seed and slot, verified for fairness at four stake distributions
[[experiments/2026-05-23_pos-selection-fairness]]; slashing is modeled as
detection-and-halt only, so the economic penalty lies outside scope per §1.4. The one load-bearing departure is the slot cadence, calibrated against
production: `slots_per_epoch = 2` (against Ethereum's 32, the smallest value that
still admits a multi-slot epoch) and `slot_duration = 1 s` (against 12 s). The
resulting per-epoch finality is ≈ 5 s, roughly 5× the per-block protocols'
≈ 1 s commit. This gap reflects FFG's coarser
epoch-granularity finality and is reported as a finding in §4.2 rather than
absorbed into the calibration. A sensitivity sweep toward production scale (larger
`slots_per_epoch` and `slot_duration`) tests whether the comparative ordering is
preserved. Family B holds Casper in its own regime by rescaling the slot,
`slot_duration ≥ 4·E[delay]`, and the runner refuses an incoherent pairing rather
than label degraded numbers as Casper FFG [[wiki/concepts/metric-reconciliation]].
Because the slot then grows with the delay regime, Casper's Family B
time-to-finality is slot-dominated and its RQ1 curve reports the protocol's
*delay coupling*.

### 3.3.3 Snowman

Only the linearized Snowman variant is implemented; full DAG-Avalanche is out of
scope, keeping the chain structure comparable to PBFT and Casper FFG under the
shared `Node` interface [[wiki/algorithms/avalanche]]. Proposer assignment is
round-robin (`slot % n`). Production Snowman runs validator sets in the thousands
with `(K, α_p, α_c, β) = (20, 11, 16, 15)`, so the thesis-scale sweep
`n ∈ {4, 7, 10, 16, 25}` requires a rescaling rule (the subsampled `K`-peer poll
loop, accepting at counter `≥ β`, is shown in Appendix A).

The rescaling sets `K = min(20, n−1)`, `α_p = ⌊K/2⌋ + 1`, and `α_c = ⌈0.8·K⌉`,
with `β = 15` held fixed [[wiki/concepts/metric-reconciliation]]. Holding the
ratio `α_c/K ≈ 0.8` and the exponent `β` fixed preserves the *form* of Snowman's
safety bound `ε ≤ (1 − α_c/K)^β` — the analytical ceiling on the probability `ε`
that two honest validators accept conflicting blocks, exponentially small in the
confirmation depth `β` [9] — rather than its numerical value, which varies
non-monotonically with `n` from `≈ 10⁻¹¹` at `n ∈ {16, 25}` to `≈ 10⁻¹⁵` at
`n = 10`. This rescaling is the coherence analogue of the §3.3.2 slot rule,
holding Snowman in its own regime on the shared axes.

The rescaling degenerates at `n = 4`, where `α_c = K = 3` forces unanimity and
drives the bound to zero; the `n = 4` Snowman row is therefore excluded from the
comparative tables of Chapters 4 and 5 and reported once as a rescaling sanity
check, leaving PBFT and Casper FFG at `n = 4` unaffected. The honest path is
verified at `n ∈ {4, 7, 10}` by the Snowman baseline experiment, with no forks
and byte-identical replay [[experiments/2026-05-27_snowman-baseline]].

## 3.4 Simulation setup

### 3.4.1 Reproducibility and the run lifecycle

The baseline experiments build the configuration in code rather than from a
per-run file. Time-bounded runs use a buffer beyond the measurement window and
clip out-of-window events, so reaching the deadline is not itself a liveness
failure: a run fails liveness only if no honest validator committed within the
window, which `success_rate` records [[wiki/concepts/output-format]].

### 3.4.2 The experiment matrix

An experiment is one point in the product of six axes — validator-set size `n`,
network timeline, adversary, protocol knobs, workload, and seed
[[wiki/concepts/experiment-matrix]]. The sweep `n ∈ {4, 7, 10, 16, 25}` is `3f+1`
at `f ∈ {1, 2, 3, 5, 8}`, a clean Byzantine-threshold instance at each point. Two
fault symbols are kept distinct: `f` is the integer threshold a configuration
tolerates (`n = 3f + 1`), while `φ` is the adversarial fraction injected in
Family C, independent of the `3f+1` relation. Experiments group into three run
families, each fixing five axes and sweeping one (Table 3.2a).

**Table 3.2a — The three run families.**

| Family | Axis swept | `n` | RQ | Key values |
|:--|:--|:--|:--|:--|
| A — Scaling | `n` | `{4, 7, 10, 16, 25}` | RQ3 | honest set on `static-baseline` |
| B — Delay | network timeline | `{10, 25}` | RQ1 | `static-baseline` → `uniform` 100–500 ms → `heavy_tail` 1–5 s; partial-synchrony two-phase case crosses GST |
| C — Adversarial | adversary | `{10, 25}` | RQ2, RQ4 | `φ ∈ {0.10, 0.20, 0.30}` (band), `φ = 0` control; `φ ∈ {0.40, 0.50}` above-threshold for equivocation |

`n = 10` is the shared anchor for Families B and C (`3f+1` at `f = 3`, small
enough to afford many seeds) and both also run at `n = 25` (`f = 8`) to amplify
the delay and adversarial effects [[wiki/concepts/experiment-matrix]]. Family B's
timeline is built from the per-phase delay model of §3.2, each phase drawing from
a fixed catalogue (`constant`, `uniform`, `normal`, `exponential`, `heavy_tail`)
plus optional loss and partition; partial synchrony is the two-phase case
crossing GST recorded in Table 3.2a [[wiki/concepts/network-model-phases]].

Family C fixes the network at `static-baseline` and sweeps the adversary (the
per-node interceptor of §3.2 [[wiki/concepts/adversary-model]]), the mirror of
Family B. An `AdversaryProfile` is static data: its capability, intensity, and bound node
set are fixed at sim-start and do not adapt mid-run. Three capabilities are exercised, one per Byzantine behavior of
RQ4, each at intensity `φ` denominated in each protocol's natural unit (replicas
for PBFT, validators for Snowman, stake for Casper FFG):

- **`delay-emission`** (delayed voting) — hold an outbound vote past the
  protocol's timing tolerance; adds a magnitude axis `m ∈ {2, 4, 6, 8, 10}`, the
  forced delay as a multiple of each protocol's round cadence.
- **`withhold-participation`** (silent non-participation) — a silent validator
  that still runs its state machine but emits nothing, the crash-faulty case.
- **`equivocate-vote`** (equivocation) — sign two conflicting messages where one
  is expected. This safety-relevant sweep also drives PBFT and Casper FFG above
  the `1/3` bound (`φ ∈ {0.40, 0.50}`) to expose the safety cliff; Snowman cannot
  fork below threshold and is not swept above it, the capability reducing to a
  "lying responder" that coincides with `withhold-participation`
  [[wiki/concepts/adversary-model#5-equivocate-vote]].

The workload defaults to a Poisson arrival process of fixed 512-byte
transactions at a zero conflict rate and 100 transactions per second, a
sub-saturation rate. Because the latency-only network (§3.2) makes block-commit
time independent of block size, the simulator has no saturation point and a
peak-throughput figure would reflect only the chosen input rate; sustained
throughput is therefore measured as goodput at this fixed rate, with
peak-throughput deferred to a task that first adds a capacity or cost model
[[experiments/2026-06-03_scaling-baseline]].

The three protocols share the same seed set at every configuration point, and
because randomness is keyed by stream identity (§3.2), all three draw the same
network and arrival randomness. The cross-protocol comparison is therefore paired
under common random numbers, a variance-reduction technique on the paired
differences whose seed count and interval machinery are set out in §3.5
[[wiki/concepts/experiment-matrix]].

### 3.4.3 One run, end to end

Figure 3.3 traces one cell end to end — PBFT at `n = 10`, the `static-baseline`
network, an honest validator set, Poisson arrivals at 100 tx/s, seed 0 — as the
six phases from init through the run loop to the flush that writes one per-trial
CSV row tagged `(protocol, n, seed)`, with each metric computed per the §3.5
definitions.

**Figure 3.3 ([[diagrams/runtime/macro]]).** One seeded run as a temporal
sequence of the six phases — init, workload, run loop, stop, flush, output —
producing one `results.csv` row, with the run-loop branch showing where the
delay (Family B) and adversarial (Family C) sweeps diverge from the honest
baseline (Family A).

Every appended row embeds a `commit_hash` and `seed` column, pinning the exact
code and random draws that produced it, so any number can be regenerated from the
record alone — the hard evidence of reproducibility. Results land in a per-trial
CSV that is aggregated to per-configuration means with 95% confidence intervals,
feeding the Chapter 4 plots. Family B replaces the network phase, Family C
attaches an `AdversaryProfile` to `φ` of the validators, and the other protocols
substitute their own proposer, message types, and `decided` condition (Table 3.2);
the lifecycle is identical for all three.

## 3.5 Metric schema

The schema places every quantity on one axis: each metric has one definition, one
unit, and one fixed instrumentation point, the family differences appearing only
as per-protocol formulas for the same column, across four metric families —
latency, throughput, overhead, and reliability
[[wiki/concepts/evaluation-metrics]].

The device that makes the three commensurable is the *atomic commit unit* (ACU):
the smallest contiguous set of transactions a protocol commits indivisibly — one
block for PBFT, one finalized checkpoint for Casper FFG, one accepted block for
Snowman. Every "per-block" metric is rewritten "per ACU", so one denominator
serves all three. Because the ACU denominator, the Snowman rescaling, and the
Casper FFG calibration of §3.3.2 are each modeling conventions, a verdict is
reported robust only when it survives the sensitivity sweep that varies the
convention's governing knob [[wiki/concepts/metric-reconciliation]].

`commit_latency_ms` is the canonical cross-protocol time-to-finality axis: the
`decided` event fires at each protocol's irreversibility milestone — PBFT's
`2f+1` `COMMIT`, the finalized Casper FFG checkpoint, Snowman's counter-`β`
acceptance — so every finality-latency claim is read from it. Cross-protocol
throughput comparison uses `goodput`, the committed-transaction rate, rather than
a raw decided-event rate, whose granularity is protocol-dependent (per block for
PBFT and Snowman, per finalized epoch for Casper FFG) and is therefore not a
like-for-like quantity.

Table 3.3 gives the per-protocol metric schema across all four metric families.

**Table 3.3 — Per-protocol metric schema.** Adapted from
[[wiki/concepts/metric-reconciliation]].

| Metric | PBFT | Casper FFG | Snowman |
| :-- | :-- | :-- | :-- |
| `commit_latency_ms` | median per-node time to the first `decided` instance (`2f+1` `COMMIT`) | median per-node time to the first finalized checkpoint (justify→finalize, `≥ 2` epochs) | median per-node time to counter-`β` acceptance of the first block |
| `goodput` | committed transactions per window (`committed_tx / time`) | committed transactions per window over finalized epochs | committed transactions per window |
| `consensus_msgs_per_acu` | `delivery_count / decided_count`, which evaluates to `(2n²−2)/n = 2n − 2/n`; this is `O(n²)` per-instance traffic over an `n`-scaled decided-event denominator, *not* linear scaling | `delivery_count / decided_count`, measured `≈ 1.125n` (un-aggregated all-to-all votes, `O(n²)` traffic; production BLS aggregation to `O(n)` is not modeled) | `delivery_count / decided_count` (`O(K·β)` query/response deliveries per validator, independent of `n`) |
| `total_msgs_per_acu` | all deliveries per ACU; equals `consensus_msgs_per_acu`, as none of the three carries a separate mempool layer | as PBFT | as PBFT |
| `bytes_per_acu` | wire-byte budget per ACU; payload-dominated at the thesis workload | attestation + payload bytes per slot; payload-dominated | `O(K·β)` query/response bytes plus payload; payload-dominated |
| `success_rate` | `0/1` indicator per run (`1.0` iff an instance decided); becomes a frequency after `n_runs` aggregation | `0/1` per run (iff an epoch finalized) | `0/1` per run (iff a block reaches counter `β`) |
| safety-violation rate (`fork_rate`) | `0` below threshold by construction; measured `> 0` only above the `1/3` bound under equivocation | `0` below threshold by construction; measured `> 0` only above `1/3` under equivocation — a conflicting finalized checkpoint, not a reorg (LMD-GHOST is not modeled, §3.3.2) | N/A — Snowman's safety is probabilistic, reported via `ε` (empirical conflicting-decision rate against `(1 − α_c/K)^β`); pre-`β` preference switches are convergence transients, not violations |

The reliability family operationalizes the §2.1 properties. A *safety violation*
is an observed breach of Agreement (two honest validators commit conflicting
values at the same height in one run), recorded in the `fork_rate` column; for the
deterministic-finality families it is `0` below threshold by construction and
measured only above it. A *liveness failure* is an observed breach of Termination
(at least one honest validator fails to commit within the window), measured by the
complement of `success_rate`. Validity holds by construction and is not
instrumented.

Snowman is the exception: its finality is probabilistic, so its safety is
reported via the analytical bound `(1 − α_c/K)^β` of §3.3.3 — below feasible seed
counts at the comparison `β = 15` — plus an empirical conflicting-decision rate
collected only in a separate RQ4 safety regime at `β ∈ {3, 5}`, never placed on a
cross-protocol throughput axis since lowering `β` cuts the `O(K·β)` cost
[[wiki/concepts/evaluation-metrics]].

Protocols are compared under the common random numbers of §3.4.2: sharing the
network, arrival, and adversary-placement streams makes each cell measure the
variance of the cross-protocol *difference*, which is what makes a modest
`n_runs = 20` per cell sufficient, raised to `30` at the near-threshold Family C
points. Because even 30 runs bound the true rate only below `≈ 0.11`,
near-threshold safety verdicts are read as bounds, not point estimates.

## 3.6 Summary and threats to validity

Four deliberate exclusions bound the claims this chapter can support; Chapter 6
takes up the full reflective limitations.

- **No compute or bandwidth cost.** The latency-only network (§3.2) charges no
  per-byte, processing, or signature-verification cost, which flatters the
  protocols whose dominant real-world cost is precisely what the model omits —
  PBFT's and Casper FFG's `O(n²)` signature verification is charged for the
  messages and bytes it emits but not for the computation they imply. The bias is
  confined to the latency and per-validator-cost verdicts; the message-count and
  byte-count comparisons are unaffected [[wiki/concepts/evaluation-metrics]].
- **Synthetic open-loop workload.** Poisson arrivals of fixed-size transactions
  at a zero conflict rate (§3.4.2), so real-traffic burstiness and
  conflict-driven reorganization lie outside the measured range.
- **Sub-production scale.** The sweep `n ∈ {4, …, 25}` sits well below the
  deployed scale, Snowman's in particular, so the RQ3 verdicts hold within this
  range and extrapolate only through the sensitivity sweeps of §3.3.2 and §3.3.3;
  the degenerate Snowman `n = 4` point is excluded (§3.3.3).
- **Leader-disruption surface uncovered.** The adversary grid exercises the three
  generic capabilities across the protocols — twelve of the eighteen
  (capability, protocol) pairs the catalogue defines — leaving six unexercised,
  among them the entire leader-disruption surface, the documented pressure point
  of the leader-driven families where a faulty primary or proposer forces leader
  rotation [[wiki/concepts/experiment-matrix-runs#uncovered-catalog-surfaces]].

Two further properties are caveats rather than exclusions: commensurability is by
convention, not by identity of the measured event (§3.5), so each verdict is
reported robust only when it survives the governing sensitivity sweep; and the
protocols are held in their own regimes by the coherence rules of §3.3.2 and
§3.3.3, not by freezing knobs outside a protocol's design point.

Chapter 4 reports the baseline, delay, and adversarial sweeps the matrix
prescribes and answers RQ1–RQ4 against the schema fixed here.
