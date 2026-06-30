# Chapter 3 — Methodology

## 3.1 Overview

This chapter describes the simulator that closes the gap of Chapter 2 and answers
the data-generating questions RQ1–RQ4: a single discrete-event system in which the
three families run under one system model (§3.2), one experiment design (§3.4), and
one metric schema (§3.5). RQ5 — whether a consistent performance–security frontier
emerges across the families — is a synthesis over that data rather than a sweep, and
is answered in Chapter 5. The approach extends the instrumented-harness methodology
of Gervais *et al.* [17] from Proof-of-Work to the three BFT families.

## 3.2 System model: one fair harness

The three families differ in leadership, in what one decision commits, and in
layering, and do not even produce the same *kind* of decision — so a fair comparison
cannot be read off each family's own published numbers. The design answers this with
one device: a single fixed engine that runs all three identically, with only the
protocol logic swapped.

The harness builds the runtime machinery (scheduler, network, validators, logger)
identically for every protocol; a run loop drives the simulation and a reducer turns
the event stream into one comparable row per seed and per matrix cell (Figure 3.1).
Ownership is split so that no protocol can reach the shared machinery: the scheduler
owns virtual time and event delivery, the network owns transport (at-most-once,
unordered, under configurable per-phase delay, loss, and partition), and the logger
owns the record. Because every component but the protocol slot is identical across
protocols, **any difference between two rows is attributable to the protocol logic
alone** — the property the whole comparison rests on. An adversary is not a new
component but a per-node interceptor that alters one validator's outgoing messages
(§3.4).

One further property is load-bearing: determinism. Every random draw derives from a
single seed keyed by stream identity, so a configuration paired with a seed
reproduces a byte-identical event stream and every reported number is exactly
reproducible [[wiki/concepts/reproducibility]]; each output row carries its
`commit_hash` and `seed`, so it can be regenerated from the record alone. Making the
three protocols *comparable* is then a separate downstream step the metric schema
performs (§3.5).

**Figure 3.1 ([[diagrams/runtime/architecture]]).** Structural view: one fixed
harness — scheduler, network, validators, logger — in which only the protocol-logic
slot is swapped, turning one experiment-matrix cell and seed into one comparable
per-trial row.

## 3.3 The three protocols

Each family of Chapter 2 is represented by one protocol — PBFT for PBFT-style
[[wiki/algorithms/pbft]], Casper FFG for PoS-finality [[wiki/algorithms/pos]], and
Snowman for Avalanche-style [[wiki/algorithms/avalanche]] — each the canonical or
production form of its family. Table 3.1 distinguishes how the three decide; the full
mechanics belong to the defense presentation, so only the load-bearing behavior is
given here. The *atomic commit unit* (ACU), the row that makes the three
commensurable, is defined in §3.5.

**Table 3.1 — The three implemented protocols at a glance.**

| | PBFT (PBFT-style) | Casper FFG (PoS-finality) | Snowman (Avalanche-style) |
|:--|:--|:--|:--|
| Leader | single rotating primary | slot proposer | leaderless |
| Decision unit (ACU) | one committed block | one finalized checkpoint | one accepted block |
| Decides when | `2f+1` replicas commit a `(view, seq)` | a checkpoint and its child are both justified | a block's confidence counter reaches `β` |
| Agreement | ~2/3 quorum, met twice (`prepare`, `commit`) | ~2/3 of stake, over two epochs | ~80% of a random `K`-peer sample, `β` rounds running |
| Finality | deterministic | deterministic | probabilistic, `ε ≤ (1 − α_c/K)^β` |
| Communication cost | `O(n²)` | `O(n)` aggregated | `O(K·β)` per validator |
| Implemented as | classical PBFT, no signatures | FFG gadget standalone, no LMD-GHOST fork-choice | linearized Snowman, no DAG, no stake-weighted sampling |

Three simplifications carry into the results and are stated once here, so a later
finding can point back rather than re-argue.

1. **PBFT** is the classical variant, which sits at the `O(n²)` worst case of its
   family's message complexity, so the RQ3 overhead verdict is a verdict on classical
   PBFT specifically, not on lighter descendants such as HotStuff (§6.2). No
   cryptographic signatures are modeled, so the adversary catalogue has no
   evidence-forgery capability; messages still carry an authenticated sender identity
   and a content digest, so what classical PBFT lacks under equivocation is an
   *accountability gadget* — a slashing layer that names the faulty replica — not the
   harness's ability to attribute a vote. The same signature-free harness detects
   Casper FFG's slashable offences (below), which fixes the gap as a protocol property
   rather than a modeling artifact. The full three-phase protocol including view-change
   and `NEW-VIEW` leader recovery is implemented; leader-disruption is a catalogued but
   un-swept adversary surface (§6.2), not an absent mechanism.
2. **Casper FFG** runs as a standalone finality gadget — its real LMD-GHOST
   fork-choice and block-production layer (Ethereum's Gasper [8]) are removed, so the
   measured latency, throughput, and liveness are properties of the gadget as modeled,
   not of a full Gasper deployment. Its slot cadence is compressed (`slots_per_epoch =
   2`, `slot_duration = 1 s`, against Ethereum's 32 and 12 s); `2` is the smallest
   value that preserves FFG's epoch structure (a multi-block epoch plus the
   two-epoch justify→finalize dependency, both of which collapse onto a single
   block at `slots_per_epoch = 1`) [[wiki/concepts/metric-reconciliation]]. The
   cadence is a configurable parameter, not a hard-coded constant, and a sensitivity sweep over
   `slot_duration ∈ {0.5, 1, 2} s` confirms finality latency scales linearly with it,
   so the resulting ≈ 5 s epoch-granularity finality is reported as a *finding* in §4.2
   — a transparent function of the calibration, not an artifact absorbed into it.
   Slashing is modeled as detection: the gadget identifies both double-vote and
   surround-vote offences and reports the slashable stake fraction, then halts — the
   economic penalty itself is out of scope (§1.4).
3. **Snowman** is the linearized variant (no DAG), rescaled for thesis-scale validator
   sets: `K = min(20, n−1)`, `α_c = ⌈0.8·K⌉`, `β = 15` held fixed. Holding the ratio
   `α_c/K ≈ 0.8` preserves the *form* of Snowman's safety bound `ε ≤ (1 − α_c/K)^β`
   rather than its production value. The `β`-round confidence accumulation itself is the
   complete Snowball rule, not a reduced form. The rescaling degenerates at `n = 4` (where
   `α_c = K` forces unanimity), so the `n = 4` Snowman row is excluded from the
   comparative tables of Chapters 4–5 [[experiments/2026-05-27_snowman-baseline]]; at the
   smaller sizes `K = n − 1` also makes each poll a near-complete canvass rather than a
   sparse subsample, so Snowman's distinguishing subsampling is only fully exercised at
   `n = 25` (§6.2).

## 3.4 Experiment design

An experiment is one point in the product of validator-set size `n`, network timeline,
adversary, workload, and seed. The sweep `n ∈ {4, 7, 10, 16, 25}` is `n = 3f + 1` at
`f ∈ {1, 2, 3, 5, 8}`, a clean Byzantine-threshold instance at each size. Two fault
symbols are kept distinct: `f` is the threshold a configuration tolerates; `φ` is the
adversarial fraction injected in Family C, independent of the `3f+1` relation.
Experiments group into three families, each fixing the other axes and sweeping one.

**Table 3.2 — The three run families.**

| Family | Axis swept | `n` | Answers | Key values |
|:--|:--|:--|:--|:--|
| A — Scaling | `n` | `{4, 7, 10, 16, 25}` | RQ3 | honest set, clean network |
| B — Delay | network timeline | `{10, 25}` | RQ1 | baseline → `uniform` 100–500 ms → `heavy_tail` 1–5 s; with and without packet loss |
| C — Adversarial | adversary | `{10, 25}` | RQ2, RQ4 | `φ ∈ {0, 0.10, 0.20, 0.30}`; `φ ∈ {0.40, 0.50}` above threshold for equivocation |

`n = 10` is the shared anchor for Families B and C (small enough to afford many seeds);
both also run at `n = 25` to amplify the delay and adversarial effects. Family B's
timeline draws each phase from a fixed catalogue (`constant`, `uniform`, `normal`,
`exponential`, `heavy_tail`) plus optional loss and partition; partial synchrony is the
two-phase case that crosses the Global Stabilization Time. Family C fixes the network at
baseline and sweeps the adversary — the per-node interceptor of §3.2 — exercising three
Byzantine behaviors, each injected at fraction `φ` in the protocol's natural unit
(replicas, validators, or stake):

- **delayed voting** — hold an outbound vote past the protocol's timing tolerance;
- **silent non-participation** — a validator that still runs its state machine but emits
  nothing (the crash-faulty case);
- **equivocation** — sign two conflicting messages where one is expected; swept above the
  `1/3` bound (`φ ∈ {0.40, 0.50}`) to expose the safety cliff. Snowman cannot fork below
  threshold, so equivocation against it reduces to the silent case and is not swept above
  threshold.

The workload is a Poisson stream of fixed 512-byte transactions at 100 tx/s, below
saturation. Because the latency-only network makes block-commit time independent of
block size, the model has no saturation point; sustained throughput is therefore
measured as goodput at this fixed rate rather than a peak-capacity figure. All three
protocols share the same seeds at every point and, because randomness is keyed by stream
identity, draw the same network and arrival randomness — so the cross-protocol comparison
is paired under common random numbers. Each cell runs over 20 seeds, raised to 30 at the
near-threshold Family C points. Time-bounded runs use a buffer beyond the measurement
window and clip out-of-window events, so reaching the deadline is not itself a liveness
failure: a run fails liveness only if no honest validator commits within the window.

## 3.5 Metric schema

The schema places every quantity on one axis: each metric has one definition, one unit,
and one fixed instrumentation point, the family differences appearing only as
per-protocol formulas for the same column [[wiki/concepts/evaluation-metrics]]. The
device that makes the three commensurable is the *atomic commit unit* (ACU): the smallest
contiguous set of transactions a protocol commits indivisibly — one block for PBFT, one
finalized checkpoint for Casper FFG, one accepted block for Snowman. Every "per-block"
metric is rewritten "per ACU", so one denominator serves all three. Because the ACU
denominator, the Snowman rescaling, and the Casper FFG calibration are modeling
conventions, a verdict is reported robust only when it survives the sensitivity sweep that
varies the convention's governing knob.

Two definitions are load-bearing. `commit_latency_ms` is the canonical time-to-finality
axis: the `decided` event fires at each protocol's irreversibility milestone — PBFT's
`2f+1` `COMMIT`, the finalized Casper FFG checkpoint, Snowman's counter-`β` acceptance —
so every finality-latency claim is read from it. Cross-protocol throughput uses `goodput`,
the committed-transaction rate, not a raw decided-event rate, whose granularity is
protocol-dependent (per block for PBFT and Snowman, per finalized epoch for Casper FFG)
and so not like-for-like.

**Table 3.3 — Per-protocol metric schema.** Adapted from
[[wiki/concepts/metric-reconciliation]].

| Metric | PBFT | Casper FFG | Snowman |
| :-- | :-- | :-- | :-- |
| `commit_latency_ms` | time to the first `decided` instance (`2f+1` `COMMIT`) | time to the first finalized checkpoint (justify→finalize, `≥ 2` epochs) | time to counter-`β` acceptance of the first block |
| `goodput` | committed transactions per window | committed transactions per window over finalized epochs | committed transactions per window |
| `total_msgs_per_acu` | all deliveries per ACU; evaluates to `(2n²−2)/n`, i.e. `O(n²)` traffic over an `n`-scaled denominator | `≈ 1.125n` (un-aggregated all-to-all votes; production BLS aggregation to `O(n)` not modeled) | `O(K·β)` query/response deliveries per validator, independent of `n` |
| `success_rate` | `0/1` per run (`1` iff an instance decided); a frequency after aggregation | `0/1` per run (iff an epoch finalized) | `0/1` per run (iff a block reaches counter `β`) |
| safety (`fork_rate`) | `0` below threshold by construction; `> 0` only above `1/3` under equivocation | `0` below threshold; `> 0` only above `1/3` (a conflicting finalized checkpoint, not a reorg) | N/A — probabilistic safety, reported via `ε` against `(1 − α_c/K)^β` |

The reliability metrics operationalize the §2.1 properties. A *safety violation* is an
observed breach of Agreement (two honest validators commit conflicting values at one
height), recorded in `fork_rate`; for the deterministic-finality families it is `0` below
threshold by construction and measured only above it. A *liveness failure* is a breach of
Termination (no honest validator commits within the window), measured by the complement of
`success_rate`. Validity holds by construction and is not instrumented. Snowman is the
exception: its finality is probabilistic, so its safety is reported via the analytical
bound `ε ≤ (1 − α_c/K)^β` rather than a measured fork rate — the weakest-witnessed safety
of the three, a limitation taken up with the others in §6.2.

The deliberate exclusions that bound these metrics — no compute or bandwidth cost, a
synthetic open-loop workload, sub-production scale, and an uncovered leader-disruption
surface — are consolidated with the full reflective limitations in §6.2. Chapter 4 reports
the baseline, delay, and adversarial sweeps the matrix prescribes and answers RQ1–RQ4
against the schema fixed here.
