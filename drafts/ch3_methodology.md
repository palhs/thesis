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

Three protocols are implemented: PBFT, Casper FFG, and Snowman. One system
model (§3.2), one simulation setup (§3.4), and one metric schema (§3.5) apply
uniformly across them.

## 3.2 System model

The three consensus families decide in genuinely different ways, and that
diversity is the comparison problem this chapter must solve. They are not one
protocol run with different constants. They differ in leadership, in what one
decision commits, and in layering (established in §2.2, catalogued per protocol
in §3.3, Table 3.2). The three do not even produce the same *kind* of decision,
so a fair comparison cannot be read off raw numbers. It needs two things: a
single fixed engine that runs all three identically, and a downstream step that
reconciles their differing output onto one scale.

The spine of that engine is short (Figure 3.1). One seed and one configuration
enter. The harness builds the runtime machinery — scheduler, network,
validators, logger — identically for every protocol, swapping only the
protocol-logic slot. A single run loop (detailed below) drives the run, and a
reducer turns the recorded event stream into one comparable row. The same
machinery runs once per seed and once per cell of the experiment matrix (§3.4),
so the only thing that varies between two rows is the quantity under study.

**Figure 3.1 ([[diagrams/runtime/architecture]]).** Structural view: a single
fixed harness in which only the protocol-logic slot is swapped, turning one
experiment-matrix cell and seed into one comparable per-trial row.

A run is fully described by the configuration that enters it. The configuration
loader requires seven top-level keys — `n`, `t_max`, `seeds`, `network`,
`adversary`, `protocol_knobs`, and `workload` — reproduced in full as the input
contract in Appendix A.

This contract has two features that carry weight later: the `network` key is not a
static setting but a time-stamped sequence of phases, each fixing a delay regime
and optional message loss and partition over a stated interval. Scheduling the
regime change in advance is what lets one seeded run cross a partial-synchronous
Global Stabilization Time without mid-run intervention
[[wiki/concepts/network-model-phases]]. The `adversary`,
`protocol_knobs`, and `workload` blocks are deliberately opaque. The loader
admits each whole and leaves interpretation to the protocol or adversary that
consumes it, which is how one harness admits three protocols that need not share
a knob schema [[wiki/concepts/system-design]].

When wired, each validator is granted exactly three capabilities, the only ways
it affects anything outside itself. Each is owned by a different component, and
the full capability contract is tabulated in Appendix A. This three-capability
contract is the split-ownership invariant: the scheduler owns time and event
delivery, the network owns transport, the logger owns the record. Because the
builder, scheduler, network, and logger are identical across protocols, any
difference between two rows is attributable to the protocol logic alone
[[wiki/concepts/system-design]]. The network models timing only: it delivers
each message at most once, unordered, under per-phase delay, loss, and partition.
Every protocol's messages travel in one uniform envelope distinguished
only by a per-protocol type (Table 3.2).

The engine's mechanism is one run loop (Figure 3.2) — the scheduler box of
Figure 3.1 seen up close. One turn proceeds as follows. If the virtual clock
has reached the deadline `t_max`, the run stops. If no events remain, the run
stops on quiescence. Otherwise the scheduler pops the soonest event, identified
by the triple `(t, node, seq)`, and advances the virtual clock to `t`. If that
event is a timer that has since been cancelled, it is skipped. Otherwise the
logger records it and the scheduler hands it to the target validator, which
reacts and may schedule new events. The loop then checks the caller's stop
predicate before taking the next turn. A run therefore ends on one of three
termination paths — `quiescence` (the heap is empty), `deadline` (the clock
reached `t_max`), or `predicate` (a caller-supplied condition became true). The
loop is identical for all three protocols; only the state machine inside the
validator differs.

**Figure 3.2 ([[diagrams/runtime/event-loop]]).** One turn of the scheduler's
event loop — pop the next event, advance the virtual clock to it, let a node
react, enqueue what it produces — with the three termination paths.

Two properties of this model are load-bearing. First, determinism: the
event queue breaks ties among same-time events by a fixed total order, and every
random draw derives from a single global seed keyed by stream identity rather
than by construction order [[wiki/concepts/simulation-design]]. A configuration
paired with a seed therefore reproduces a byte-identical event stream, so any
reported number is exactly reproducible [[wiki/concepts/reproducibility]].
Second, network phases are scheduled in advance, so a single seeded run can cross
a partial-synchronous Global Stabilization Time without intervention
[[wiki/concepts/network-model-phases]].

Isolation is not commensurability. Running three kinds of decision through one
identical engine secures only that the engine adds no difference of its own.
Making them comparable is a separate downstream step: the reconciliation step the
metric schema performs under stated conventions when the per-trial rows are read
back (§3.5). Finally, an adversary is not a new component but a per-node interceptor
that alters a single validator's outgoing messages; the Byzantine strategies a
profile can apply are catalogued in [[wiki/concepts/adversary-model]], and §3.4
names the three exercised by the RQ4 sweep.

## 3.3 Algorithms

Each family surveyed in Chapter 2 (§2.2) is represented in the simulator by a
single protocol [[wiki/algorithms/pbft]], [[wiki/algorithms/pos]],
[[wiki/algorithms/avalanche]]; Table 3.1 fixes that correspondence, and its
rightmost column states why each protocol is a faithful representative of its
family. The family labels are those of Chapter 2; the protocol names are used
from here onward.

**Table 3.1 — Family-to-protocol mapping.**

| Family (Chapter 2) | Implemented protocol | Why it represents the family |
|:--|:--|:--|
| PBFT-style | PBFT | The canonical leader-driven, multi-phase BFT protocol the family is named for; its `3f+1` quorum and view-change are the mechanism every later variant refines. |
| PoS-finality | Casper FFG | The finality gadget Ethereum deploys; it carries the family's defining stake-weighted, two-checkpoint justification rule. |
| Avalanche-style | Snowman | The production linear-chain form of the Avalanche family; it exercises the family's defining repeated random-subsample voting. |

Chapter 2 (§2.2, Table 2.1) establishes the *mechanism* of each protocol
family; this section does not revisit it. It audits where the simulator's
implementation *departs* from the textbook family, and why each departure
leaves the comparative results valid. Table 3.2 summarizes the three protocols
at a glance — whether each elects a leader, what one decision commits (its
*atomic commit unit*, or ACU; defined in §3.5), the message types each carries,
the event that signals a commit, the knobs exposed to experiments, and the main
simplification each makes. Each subsection then pairs the protocol's decide-path figure (the
honest path from first message to `decided`) with a *deviation ledger* whose
numbered entries name every point at which the implementation departs from the
family and the validity boundary each departure introduces.

In this table and the subsections that follow, `n` is the validator-set size and
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

Only the classical variant is implemented. Figure 3.3 traces its honest
three-phase commit and the view-change branch; the deviation ledger records
where the implementation departs from classical PBFT.

**Figure 3.3 ([[diagrams/protocols/pbft]]).** PBFT three-phase commit for one
`(view, seq)` instance with the view-change branch.

**Deviation ledger.**

- **① Single primary — classical variant only.** No HotStuff
  threshold-signature linearization and no Tendermint rotation
  [[wiki/algorithms/pbft]].
- **② Exponential view-change backoff.** The view-change timeout uses a
  per-view backoff `(3·E[round_latency])·2^view` (where `E[round_latency]` is
  the expected per-round message latency in the current network phase), required
  so recovery terminates deterministically: a flat timeout that has fired once
  fires again in the same delay regime.
- **③ Digests, not certificates.** The simulator carries no cryptographic
  signatures; message digests serve integrity and deterministic replay only, so
  a `VIEW-CHANGE` message's prepared evidence is an assertion rather than a
  cryptographic certificate, and the adversary catalog deliberately carries no
  evidence-forgery capability. *Validity boundary:* this affects no honest-path
  result and no equivocating-primary result; within-threshold safety against
  forged view-change evidence is assumed by construction.
- **④ Worst-case message complexity.** Classical PBFT sits at the
  `O(n) → O(n²)` end of the family's message-complexity range, so the RQ3
  verdict reported for "PBFT-style" is a verdict on classical PBFT
  specifically.

### 3.3.2 Casper FFG

The implementation is a simplified Casper FFG gadget. Figure 3.4 traces one
epoch's justify→finalize path and its slashing branch; the deviation ledger
records the departures from deployed Ethereum FFG.

**Figure 3.4 ([[diagrams/protocols/casper-ffg]]).** Casper FFG
justify→finalize for one epoch with the slashing branch.

**Deviation ledger.**

- **① Deterministic stake-weighted proposer.** Proposer assignment is a pure
  function of `(global_seed, slot)` through blake2b, verified for fairness at
  four stake distributions (each validator's selection frequency within 0.10
  of its stake share over 100 slots under a fixed seed)
  [[experiments/2026-05-23_pos-selection-fairness]].
- **② `slots_per_epoch = 2`** (against Ethereum's 32), pinned in
  [[wiki/concepts/metric-reconciliation]] — the smallest value that still
  admits a multi-slot epoch, which preserves FFG's epoch character.
- **③ `slot_duration = 1 s`** (against 12 s), pinned in
  [[wiki/concepts/metric-reconciliation]] — a round, legible cadence an order
  of magnitude below production. The resulting per-epoch finality,
  `(2·slots_per_epoch + attest_offset)·slot_duration ≈ 5 s` (where
  `attest_offset` is the one-slot delay before attestations are aggregated), is
  roughly 5× the per-block protocols' ≈1 s commit; this gap is reported as a finding in §4.2,
  not compressed away, and reflects FFG's coarser epoch-granularity finality.
  *Defence:* a sensitivity sweep toward production scale (larger
  `slots_per_epoch` and `slot_duration`) tests whether the comparative ordering
  is preserved.
- **④ No LMD-GHOST fork choice.** `Chain.head` is the block at the greatest
  known slot under an honest-path linear chain.
- **⑤ Slashing modeled as a halt, detection only.** A provable double- or
  surround-vote halts the run with the offending validators recorded; no deposit
  is destroyed and no stake is removed from the active set, so the economic penalty
  — and the safety-cost budget it would yield — lies outside scope, consistent with
  the economic-design exclusion of §1.4 [[wiki/algorithms/pos#simulator-mapping]].

### 3.3.3 Snowman

Only the linearized Snowman variant is implemented. Full DAG-Avalanche is out
of scope, which keeps the chain structure directly comparable to PBFT and
Casper FFG under the shared `Node` interface [[wiki/algorithms/avalanche]].
Production Snowman runs on validator sets in the thousands with
`(K, α_p, α_c, β) = (20, 11, 16, 15)` — respectively the poll sample size, the
preference and confidence thresholds, and the decision threshold. The
thesis-scale sweep
`n ∈ {4, 7, 10, 16, 25}` therefore requires the rescaling rule the deviation ledger
records. Figure 3.5 traces the poll loop.

**Figure 3.5 ([[diagrams/protocols/snowman]]).** Snowman subsampled `K`-peer
poll loop for one block, accepting at counter `≥ β`.

**Deviation ledger.**

- **① Round-robin proposer.** Proposer assignment is `slot % n`; Snowman is not
  stake-weighted.
- **② Sample size rescaled.** `K = min(20, n−1)`, `α_p = ⌊K/2⌋ + 1`, so the
  poll fits a thesis-scale validator set [[wiki/concepts/metric-reconciliation]].
- **③ Confidence threshold rescaled, shape held.** `α_c = ⌈0.8·K⌉`. Snowman's
  safety bound is `ε ≤ (1 − α_c/K)^β` — the analytical ceiling on the
  probability `ε` that two honest validators accept conflicting blocks,
  exponentially small in the confirmation depth `β` [9]. Holding the ratio `α_c/K ≈ 0.8` across the
  sweep preserves the *shape* of that bound rather than its numerical value,
  because the exponential form is what carries the probabilistic-finality
  semantics. The ceiling rounds `α_c` up, so the realized ratio never falls below
  `0.8` and the rescaled bound is at least as tight as production
  [[wiki/concepts/metric-reconciliation]].
- **④ `β = 15` held fixed.** Holding `β` fixed keeps the *exponent* of the safety
  bound `(1 − α_c/K)^β` constant across the sweep, preserving the exponential form
  that carries the probabilistic-finality semantics. It does not hold the
  *realized* bound constant. The base `(1 − α_c/K)` tracks the ceiling-rounded
  ratio of ③, so the analytical ceiling `ε` varies non-monotonically with `n`,
  from `≈ 10⁻¹¹` at `n ∈ {16, 25}` down to `≈ 10⁻¹⁵` at `n = 10`, several orders
  of magnitude. The smallest sets sit nearest unanimity (`n = 7` gives
  `α_c/K = 5/6 ≈ 0.833`) [[wiki/concepts/metric-reconciliation]]. Together with
  ②–③, the rescaled protocol is therefore one Snowman in *form* across the sweep
  (the same exponential semantics tracked at fixed `β`) rather than an identical
  numerical guarantee at each `n`.

**Degeneracy (excluded).** The rescaling degenerates at `n = 4`, where it
yields `α_c = K = 3`: every poll then queries all peers and demands unanimity,
collapsing Snowman to flood-voting and driving the bound `(1 − α_c/K)^β` to
zero. This is not because finality is genuinely perfect, but because this
parametrization is no longer Snowman, only the degenerate boundary of the
rescaling rule [[wiki/concepts/metric-reconciliation]]. The `n = 4` Snowman row
is therefore excluded from the comparative tables of Chapters 4 and 5 and
reported once as a rescaling sanity check, leaving PBFT and Casper FFG at
`n = 4` unaffected.

**Honest-path check.** The honest path is verified at `n ∈ {4, 7, 10}` by the
Snowman baseline experiment, in which every validator decides every announced
block with no forks and byte-identical replay
[[experiments/2026-05-27_snowman-baseline]].

## 3.4 Simulation setup

### 3.4.1 Reproducibility and the run lifecycle

The harness wires and runs the system by the bootstrap and run loop of §3.2, and
the same configuration paired with the same global seed produces a byte-identical
event stream, since the bootstrap adds no randomness of its own
[[wiki/concepts/reproducibility]]. Two points specific to these experiments follow.

First, the baseline experiments do not load a YAML file per run: they build the
configuration programmatically, as scenario definitions in code that produce the
same `Config` object the loader would, so the seven-key schema of §3.2 is the
documented contract rather than an on-disk artifact for every cell
[[wiki/concepts/simulation-design]].

Second, the three termination predicates of §3.2 (`quiescence`, `deadline`,
`predicate`) interact with the measurement window: time-bounded runs use a buffer
beyond the window, and the analysis step clips out-of-window events. Hitting `t_max` is not itself a liveness failure: a run fails liveness only if
no honest validator committed within the measurement window. `success_rate`
records whether at least one did [[wiki/concepts/output-format]], keeping the
RQ4 column free of runs that were healthy but truncated.

### 3.4.2 The experiment matrix

An experiment is one point in the product of six axes — validator-set size
`n`, network timeline, adversary, protocol knobs, workload, and seed
[[wiki/concepts/experiment-matrix]]. The sweep `n ∈ {4, 7, 10, 16, 25}` is
`3f+1` at `f ∈ {1, 2, 3, 5, 8}`, giving a clean Byzantine-threshold instance
at each point. Throughout, two fault symbols recur and are kept distinct: `f` is
the integer fault threshold a configuration tolerates (`n = 3f + 1`), while `φ`
is the adversarial fraction actually injected in Family C — a real fraction of
the validator set, independent of the `n = 3f + 1` relation. Experiments group
into three run families, each fixing five axes and sweeping one:

- **Family A (Scaling)** sweeps `n` under an honest validator set on the
  `static-baseline` network, for RQ3.
- **Family B (Delay)** sweeps the network timeline at `n ∈ {10, 25}`, for RQ1.
- **Family C (Adversarial)** sweeps the adversary at `n ∈ {10, 25}`, for RQ2 and
  RQ4 jointly; the capability set, intensity grid, and magnitude axis are
  detailed below [[wiki/concepts/experiment-matrix-runs]].

`n = 10` is the shared anchor for Families B and C — the middle of the scaling
sweep, `3f+1` at `f = 3`, small enough to afford many seeds — and both families
also run at `n = 25` (`3f+1` at `f = 8`) to amplify the delay and adversarial
effects [[wiki/concepts/experiment-matrix]].

The network timeline Family B sweeps is built from the per-phase delay model of
§3.2 [[wiki/concepts/network-model-phases]]. Each phase fixes a delay
distribution from a fixed catalogue — `constant`, `uniform`, `normal`,
`exponential`, and `heavy_tail` (Pareto) — plus an optional message-loss
probability and an optional partition. The sweep moves from the
`static-baseline` network (one `constant` phase over `[0, t_max)`) through a
moderate regime (`uniform`, 100–500 ms) to a heavy-tailed regime (1–5 s with a
long tail); partial synchrony is the two-phase case — an asynchronous,
heavy-tailed phase, optionally partitioned, before the Global Stabilization Time,
then a bounded-delay phase after it — so one seeded run crosses GST without
intervention.

Family C fixes the network at `static-baseline` (a constant 10 ms delay) and
sweeps the adversary (the per-node interceptor of §3.2
[[wiki/concepts/adversary-model]]), the mirror of Family B. An `AdversaryProfile`
is static data: its capability, intensity, and bound node set are fixed at
sim-start and never adapt mid-run [[wiki/concepts/adversary-model]]. Three
capabilities are exercised, one per Byzantine behavior of RQ4
[[wiki/concepts/research-questions]], each at an intensity given by the
adversarial fraction `φ` — denominated in each protocol's natural unit (replicas
for PBFT, validators for Snowman, stake for Casper FFG) and swept over a
sub-threshold band `φ ∈ {0.10, 0.20, 0.30}` against a `φ = 0` honest control:

- **`delay-emission`** (delayed voting) — hold an outbound vote past the
  protocol's timing tolerance; adds a magnitude axis `m ∈ {2, 4, 6, 8, 10}`, the
  forced delay as a multiple of each protocol's round cadence.
- **`withhold-participation`** (silent non-participation) — a silent validator
  that still runs its state machine but emits nothing, the crash-faulty case.
- **`equivocate-vote`** (equivocation) — sign two conflicting messages where the
  protocol expects one. This safety-relevant sweep also drives PBFT and
  Casper FFG above the `1/3` bound (`φ ∈ {0.40, 0.50}`) to expose the safety
  cliff. Snowman cannot fork below threshold and is not swept
  above it [[wiki/concepts/experiment-matrix-runs]]. For Snowman the capability
  has no distinct realization and reduces to a "lying responder" that coincides
  in effect with `withhold-participation`
  [[wiki/concepts/adversary-model#5-equivocate-vote]].

Workload defaults are:

- a Poisson arrival process;
- fixed 512-byte transactions;
- a zero conflict rate;
- an offered rate of 100 transactions per second in the sub-saturation latency
  regime.

The latency-only network (§3.2) removes the simulator's saturation point: block-commit
time is independent of block size, so any offered load commits at the same rate and a
peak-throughput figure would reflect only the chosen input rate rather than a protocol
limit. Sustained throughput is therefore measured as goodput at the fixed sub-saturation
rate; peak-throughput measurement is deferred to a task that first adds a capacity or cost
model [[wiki/concepts/experiment-matrix]]
[[experiments/2026-06-03_scaling-baseline]].

The three protocols share the same seed set at every configuration point, and
because randomness is keyed by stream identity (§3.2), all three draw from the
same network and arrival randomness. The cross-protocol comparison is
therefore paired under common random numbers, a variance-reduction technique on the
paired differences [[wiki/concepts/experiment-matrix]]. The seed count this
pairing affords, and the interval machinery that reads it, are set out with the
metric schema (§3.5).

### 3.4.3 Regime-coherence constraints

Each protocol is held in its own regime on the shared axes by two coherence
constraints: the FFG runner
refuses any pairing of the baseline `slot_duration = 1 s` (§3.3.2 ③) with a
network phase whose `E[delay]`, the mean delay of the phase's distribution, is
not far below the slot duration. When `E[delay]` approaches `slot_duration`,
attestations from distant validators arrive after the slot boundary, producing a
degraded regime that is not Casper FFG. Family B therefore rescales
`slot_duration` upward with the delay regime, by the rule
`slot_duration ≥ 4·E[delay]` [[wiki/concepts/metric-reconciliation]]. The matrix
owns the per-timeline pairing, and the runner refuses to start an incoherent
pairing rather than report degraded-finality numbers labeled as Casper FFG
[[wiki/concepts/experiment-matrix]]. Because the slot duration grows with the
delay regime, Casper FFG's time-to-finality in Family B is slot-dominated and
necessarily rises with delay. The RQ1 curve for Casper FFG therefore reports the
protocol's *delay coupling*, the same coupling Ethereum's 12 s slot reflects,
rather than a free-running delay-sensitivity measurement. It is read as such
rather than hidden. The second constraint is the analogous one for Snowman: its
`(K, α_p, α_c)` are not free axes but functions of `n` fixed by the §3.3.3
rescaling rule (which also fixes the `n = 4` Snowman exclusion recorded there).

### 3.4.4 One run, end to end

To make the matrix concrete, consider one cell: PBFT at `n = 10` (so `f = 3`
and the quorum is `2f+1 = 7`), the `static-baseline` network, an honest
validator set, Poisson arrivals at 100 tx/s, and seed 0. The six phases run as
follows; Figure 3.6 gives the same run as a temporal sequence.

**Figure 3.6 ([[diagrams/runtime/macro]]).** One seeded run as a temporal
sequence of the six phases — init, workload, run loop, stop, flush, output —
producing one `results.csv` row, with the run-loop branch showing where the
delay (Family B) and adversarial (Family C) sweeps diverge from the honest
baseline (Family A). The adversary is drawn inside the Validator lane, not as
a separate component: it is the per-node interceptor of §3.2 that alters a
bound validator's outgoing messages.

1. **Init.** The harness builds and wires the scheduler, network, and ten
   validators, and names one of them the primary.
2. **Workload.** The harness seeds the primary's mempool with transactions
   drawn from the Poisson process; each transaction `τ` is stamped with its
   submit time `t_submit`.
3. **Run loop.** At its propose timer the primary batches `τ` into a block and
   broadcasts `PRE-PREPARE`. Each validator that accepts it broadcasts
   `PREPARE`. Once a validator has collected `7` matching prepares it
   broadcasts `COMMIT`. Once it has collected `7` matching commits it emits a
   `decided` event for the block at time `t_decided`, under the
   `static-baseline` delay on every delivery.
4. **Stop.** The run ends at `quiescence` or `t_max`.
5. **Flush and reduce.** The harness reduces the event stream to metrics. The
   commit latency of `τ` is `t_decided − t_submit`, and throughput is the
   committed-transaction count over the measurement window.
   `consensus_msgs_per_acu` is the per-ACU message cost: the `PRE-PREPARE`
   broadcast, the all-to-all `PREPARE` and `COMMIT` rounds, and the client
   `REPLY`s total `2(n²−1)` deliveries (`O(n²)` traffic), which over the `n`
   `decided` events is `(2n²−2)/n = 2n − 2/n` (≈ 19.8 at this `n`).
6. **Output.** One per-trial row, tagged with `(protocol, n, seed)`, is
   appended to the per-trial CSV.

The row this run appends has the following shape, shown with a few salient
columns and the remainder elided:

```text
run_id,  protocol, n,  seed, …, commit_hash, t_max, commit_latency_ms, …, success_rate, fork_rate, …
pbft-n10, pbft,    10, 0,    …, 24a491a4,    20.0,  1000.000003,       …, 1.0,          0.0,       …
```

The `commit_hash` (`24a491a4`) and `seed` columns embedded in every row are the
hard evidence of reproducibility: together they pin the exact code and the exact
random draws that produced the row, so any number can be regenerated from the
record alone. The full 24-column schema is defined in §3.5 and is not repeated
here.

The walkthrough above produces one row of a single file, but the comparison
rests on two files [[wiki/concepts/output-format]]. The first is a per-trial,
long-format CSV carrying one row per
`(protocol, scenario, seed)`, the file step 6 appends to. The second is produced
by a separate downstream aggregation step: a wide CSV carrying one row per
configuration with the
mean and 95% confidence interval of each metric across the seed set, and it is
this aggregated file that feeds the Chapter 4 plots. The mean and interval are
therefore properties of the aggregation, not of any single per-trial row.
Repeating the run over seeds `0 … 19` under common random numbers supplies the
sample it reduces. Family B replaces the network phase, Family C attaches an
`AdversaryProfile` to `φ` of the validators, and the other two protocols
substitute their own proposer, message types, and `decided` condition (Table
3.1). The six-phase lifecycle is identical for all three.

## 3.5 Metric schema

The three protocols do not emit commensurable events: PBFT commits a block,
Casper FFG finalizes a checkpoint, and Snowman accepts a block once its counter
reaches `β`. They differ structurally — PBFT's and Snowman's per-block finality
against Casper FFG's per-epoch finality, and Snowman's parameter rescaling.
No quantity can therefore be read off the raw event stream and compared across families
until it is first placed on a common axis [[wiki/concepts/metric-reconciliation]]. Building that axis is the
work of the metric schema, and the schema is uniform across families: each metric
has one definition, one unit, and one fixed instrumentation point in the
simulator, and
the family-specific differences appear only as different per-protocol formulas
computing the same column [[wiki/concepts/evaluation-metrics]]. The evaluation
spans four metric families:

- *latency* measures how quickly a transaction reaches commit or finality;
- *throughput* measures how many transactions the protocol commits per unit
  time;
- *overhead* measures the messages, bytes, and per-validator state it consumes;
- *reliability* measures whether it preserves safety and liveness under delay
  and adversary.

The device that makes the three commensurable is the *atomic commit unit* (ACU):
the smallest contiguous set of transactions a protocol commits indivisibly.
Every "per-block" metric is rewritten as "per ACU", where the ACU is one block
for PBFT, one finalized checkpoint for Casper FFG, and one block for Snowman. One
denominator therefore serves all three without a conditional formula. The three
protocols are thereby plottable on one scale under three stated conventions — the
ACU denominator, the Snowman parameter rescaling, and the Casper FFG calibration
of §3.3.2. Because each convention is a modeling choice rather than a neutral
fact, a verdict is reported as robust only when it survives the sensitivity sweep
that varies the convention's governing knob [[wiki/concepts/metric-reconciliation]].

Latency carries one further convention. Every latency metric is anchored at the
transaction's submit time, so end-to-end latency is comparable across protocols
whether or not they carry a separate mempool. `commit_latency_ms` is the
canonical cross-protocol time-to-finality axis: the simulator's `decided` event
fires at each protocol's irreversibility milestone — PBFT's `2f+1` `COMMIT`, the
finalized Casper FFG checkpoint, Snowman's counter-`β` acceptance — so every
cross-protocol finality-latency claim is read from it
[[wiki/concepts/metric-reconciliation]]. Throughout, time is the simulator's
model time; no number is a real-hardware claim, and published production figures
are order-of-magnitude sanity checks (§1.4), not validation targets.

Table 3.3 gives the per-protocol metric schema across all four metric families —
latency, throughput, overhead, and reliability.

**Table 3.3 — Per-protocol metric schema.** Adapted from
[[wiki/concepts/metric-reconciliation]].

| Metric | PBFT | Casper FFG | Snowman |
| :-- | :-- | :-- | :-- |
| `commit_latency_ms` | median per-node time to the first `decided` instance (`2f+1` `COMMIT`) | median per-node time to the first finalized checkpoint (justify→finalize, `≥ 2` epochs) | median per-node time to counter-`β` acceptance of the first block |
| `tps` | decided ACUs per window (`decided_count / t_max`) | decided epochs per window (`decided_count / t_max`) | decided blocks per window (`decided_count / t_max`) |
| `goodput` | committed transactions per window (`committed_tx / time`) | committed transactions per window over finalized epochs | committed transactions per window |
| `consensus_msgs_per_acu` | `delivery_count / decided_count`, which evaluates to `(2n²−2)/n = 2n − 2/n`; this is `O(n²)` per-instance traffic over an `n`-scaled decided-event denominator, **not** linear scaling | `delivery_count / decided_count`, measured `≈ 1.125n` (un-aggregated all-to-all votes, `O(n²)` traffic; production BLS aggregation to `O(n)` is not modeled) | `delivery_count / decided_count` (`O(K·β)` query/response deliveries per validator, independent of `n`) |
| `total_msgs_per_acu` | all deliveries per ACU; equals `consensus_msgs_per_acu`, as none of the three carries a separate mempool layer | as PBFT | as PBFT |
| `bytes_per_acu` | wire-byte budget per ACU; payload-dominated at the thesis workload — see note below | attestation + payload bytes per slot; payload-dominated | `O(K·β)` query/response bytes plus payload; payload-dominated |
| `success_rate` | `0/1` indicator per run (`1.0` iff an instance decided); becomes a frequency after `n_runs` aggregation | `0/1` per run (iff an epoch finalized) | `0/1` per run (iff a block reaches counter `β`) |
| safety-violation rate (`fork_rate`) | `0` below threshold by construction; measured `> 0` only above the `1/3` bound under equivocation | `0` below threshold by construction; measured `> 0` only above `1/3` under equivocation — a conflicting finalized checkpoint, not a reorg (LMD-GHOST is not modeled, §3.3.2 ④) | N/A — Snowman's safety is probabilistic, reported via `ε` (empirical conflicting-decision rate against `(1 − α_c/K)^β`); pre-`β` preference switches are convergence transients, not violations |

**Throughput basis.** As implemented, `tps` is a decided-event rate whose
granularity is protocol-dependent — per block for PBFT and Snowman, per finalized
epoch for Casper FFG — so it is not a like-for-like cross-protocol quantity.
Cross-protocol throughput comparison therefore uses `goodput`, the committed-
transaction rate, and never `tps` [[wiki/concepts/metric-reconciliation]].

**Byte overhead.** `bytes_per_acu` includes the 512-byte transaction payload on
every transaction-carrying delivery; at the thesis workload this payload term
dominates and amortizes, so `bytes_per_acu / n²` *falls* with `n` rather than
tracking each protocol's message-complexity law. The RQ3 byte-overhead contrast
is therefore read from `consensus_msgs_per_acu` (message count) or a
payload-subtracted byte figure, not from raw `bytes_per_acu`
[[wiki/concepts/metric-reconciliation]].

The reliability family operationalizes the §2.1 properties. A *safety violation*
is an observed breach of Agreement (two honest validators commit conflicting
values at the same height in one run), measured by the safety-violation rate
(recorded in the `fork_rate` column). For the deterministic-finality families it
is `0` below threshold by construction and measured only above it. A *liveness
failure* is an observed breach of Termination (at least one honest validator
fails to commit within the measurement window), measured by the complement of
`success_rate`. Validity holds by construction and is not instrumented: the
workload generator emits only well-formed transactions, and no module commits a
value it did not receive.

Snowman is the exception to the zero-by-construction safety-violation rate: its
finality is probabilistic rather than categorical, so the rate is reported
instead as both the analytical bound `(1 − α_c/K)^β` (§3.3.3) and the empirical
conflicting-decision rate across seeds [[wiki/concepts/evaluation-metrics]]. At
the comparison baseline `β = 15` that analytical bound ranges from ~10⁻¹⁵ at `n = 10` to ~10⁻¹¹ at `n = 25`.
The empirical rate is therefore unobservable in feasible seed counts. The empirical side is
therefore collected only in a separate RQ4 safety regime at `β ∈ {3, 5}`,
reported on its own and never placed on a cross-protocol throughput axis.
Lowering `β` cuts Snowman's `O(K·β)` cost and would otherwise manufacture a
throughput advantage [[wiki/concepts/metric-reconciliation]].

Protocols are compared under the common random numbers of §3.4.2. They share the
network, arrival, and adversary-placement streams, so each cell measures the
variance of the cross-protocol *difference*, not of either protocol alone. This
is what makes a modest `n_runs = 20` per cell sufficient, raised to `30` at the
near-threshold Family C points where outcomes are most variable. Snowman's
internal poll sub-sampling has no cross-protocol counterpart, so its variance
reduction is only partial [[wiki/concepts/experiment-matrix]],
[[wiki/concepts/experiment-matrix-runs]], [[wiki/algorithms/avalanche]].

Each trial writes one CSV row per `(protocol, scenario, seed)`, aggregated
downstream to one row per configuration with the mean and a 95% confidence
interval: Student-t for continuous metrics (small-sample, one degree of freedom
below the seed count) and Wilson for rate metrics (`fork_rate`, `success_rate`),
so a zero-violation cell is reported as `0/n_runs` rather than a degenerate mean.
Wilson stays honest at the boundary but does not narrow: even at 30 runs a
zero-violation cell bounds the true rate only below `≈ 0.11`, so near-threshold
safety verdicts are read as bounds, not point estimates.

Tables 3.3 and 3.4 list the columns populated at the honest baseline. Two
column groups are defined in the schema but written only when the RQ4 adversarial
sweep runs [[wiki/concepts/output-format]]: the adversarial-threshold columns —
`f_max_count` for PBFT and Snowman or the mutually exclusive `f_max_stake` for
Casper FFG (the smallest adversary fraction at which a run's safety or liveness
invariant first breaks) — and the empirical and analytical Snowman safety columns
discussed above. The finalized CSV layout is fixed in
[[wiki/concepts/output-format]].

## 3.6 Summary and threats to validity

The system model (§3.2) and metric schema (§3.5) absorb the three families'
structural asymmetries upstream of any experiment, so no experiment sees them.
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

Two further properties are sources of caveat rather than exclusion:

- **Commensurability by convention.** The comparison is commensurable by
  convention, not by identity of the measured event (§3.5), so every comparative
  verdict is qualified by the conventions it rests on and is reported as robust
  only when it survives the governing sensitivity sweep
  [[wiki/concepts/metric-reconciliation]].
- **Regime-coherence rules, not frozen knobs.** The protocols are held in their
  own regimes by two coherence rules — the Casper FFG slot-duration-to-delay
  pairing (§3.4.3) and the Snowman parameter rescaling (§3.3.3) — rather than by
  freezing knobs that would place a protocol outside its design point.

Chapter 4 reports the baseline, delay, and adversarial sweeps the matrix
prescribes and answers RQ1–RQ4 against the schema fixed here.
