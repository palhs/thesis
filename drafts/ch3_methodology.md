# Chapter 3 — Methodology

## 3.1 Overview

This chapter describes the simulator that closes the gap of Chapter 2 and answers
the data-generating questions RQ1–RQ4: a single discrete-event system in which the
three families run under one system model (§3.2), one experiment design (§3.4), and
one metric schema (§3.5). RQ5 (whether a consistent performance–security frontier
emerges across the families) is a synthesis over that data rather than a sweep, and
is answered in Chapter 5. The approach extends the instrumented-harness methodology
of Gervais *et al.* [17] from Proof-of-Work to the three BFT families.

## 3.2 System model: one fair harness

The three families reach decisions in very different ways, so their published
numbers cannot be placed side by side. A single harness that runs all three
identically, with only the protocol logic swapped, removes that obstacle.

For every run the harness builds the same infrastructure: a scheduler for virtual
time, a network that delivers messages under configurable delay and loss, and a
logger. The only part that varies between runs is the protocol slot, so any
difference in output is attributable to the protocol rather than to the
infrastructure (Figure 3.1). An adversary is not a separate harness component; it
is a per-node interceptor placed on one validator's outbound messages (§3.4).

The harness is also deterministic: each random draw is keyed by stream identity, so
a configuration paired with a seed always replays the same event sequence. Every
output row records its `commit_hash` and `seed` for later verification. Converting
those rows into a shared measurement unit is a separate step, handled by the metric
schema in §3.5.

**Figure 3.1 ([[diagrams/runtime/architecture]]).** Read left to right: one
configuration enters the fixed harness, the protocol logic is the only part that
changes between runs, and the output is one result row. The loop arrow shows this
repeats for every seed and every experiment cell.

## 3.3 The three protocols

Each family of Chapter 2 is represented by one protocol — PBFT for PBFT-style
[[wiki/algorithms/pbft]], Casper FFG for PoS-finality [[wiki/algorithms/pos]], and
Snowman for Avalanche-style [[wiki/algorithms/avalanche]] — each the canonical or
production form of its family. Table 3.1 distinguishes how the three decide; only the
load-bearing behavior is given here. The *atomic commit unit* (ACU), the row that
makes the three commensurable, is defined in §3.5.

### PBFT — leader-driven two-phase voting

Figure 3.2 shows four validators with Node 3 offline.

A client sends a request to the primary (Node 0), which broadcasts `PRE-PREPARE`
to all validators. Each honest validator then broadcasts `PREPARE` to every other.
Once a validator sees `2f+1` matching `PREPARE` messages, it broadcasts `COMMIT`.
At `2f+1` matching `COMMIT` messages, the block is decided and that validator
replies to the client.

Two all-to-all rounds, hence `O(n²)` messages per block. Node 3's silence cuts
the available votes, but three honest nodes still clear the `2f+1 = 3` threshold
in both phases.

**Figure 3.2 ([[diagrams/concepts/pbft-flow]]).** PBFT message flow, n=4, f=1.
Colours indicate the sender. Node 3 (faulty) receives `PRE-PREPARE` but emits
nothing; the three honest nodes still reach `2f+1` in both phases.

The implementation drops cryptographic signatures but keeps the full view-change
and `NEW-VIEW` recovery path; §6.2 addresses generalizability.

### Casper FFG — checkpoint finality over epochs

Blocks arrive continuously and are grouped into epochs. At each epoch boundary a
checkpoint is created. During an epoch, validators broadcast *attestations*
(signed votes for the link from the previous checkpoint to the current one) to
the entire validator set. The arrows in Figure 3.3 point at checkpoints as
shorthand for "this vote targets that link"; the actual recipients are the other
validators, not the checkpoint.

When attestations worth ≥⅔ of total stake accumulate for a link, the target
checkpoint is *justified*. It becomes *finalized* only once its child checkpoint
is also justified. C3 in the figure is still pending: not enough attestations
yet.

**Figure 3.3 ([[diagrams/concepts/casper-ffg-flow]]).** Casper FFG checkpoint
chain. Green = finalized, amber = justified, white = proposed. Solid arcs are
confirmed supermajority links; the dashed arc shows the next link still
accumulating votes. Validator dots show 5 of 7 attesting (grey = silent or late).

The gadget runs without LMD-GHOST fork-choice, so the results cover the finality
layer only, not a complete Gasper deployment (§6.2).

### Snowman — repeated random subsampling

Each round, validator v picks K peers at random and asks which block they prefer.
If at least `α_c` of the replies agree, the confidence counter increments. The
counter resets on a preference switch. At β consecutive agreeing rounds, v accepts
the block.

No leader is involved. Each validator runs this loop on its own, touching only K
peers per round, so the per-validator cost does not grow with network size. The
price of dropping the quorum requirement is probabilistic finality:
`ε ≤ (1 − α_c/K)^β`, shrinking exponentially in β. Figure 3.4 traces one such
sequence of sampling rounds.

**Figure 3.4 ([[diagrams/concepts/snowman-flow]]).** Snowman sampling rounds for
validator v. Blue peers prefer the same block; red peers prefer a competing one.
The counter grows each round the sample clears α_c, and resets if v switches
preference.

The simulator uses the linearized (no-DAG) variant with parameters rescaled for
small validator sets; DAG routing and stake-weighted sampling are not modeled
(§6.2).

Table 3.1 summarises the three protocols side by side.

**Table 3.1 — The three implemented protocols at a glance.**

| | PBFT (PBFT-style) | Casper FFG (PoS-finality) | Snowman (Avalanche-style) |
|:--|:--|:--|:--|
| Leader | single rotating primary | slot proposer | leaderless |
| Decision unit (ACU) | one committed block | one finalized checkpoint | one accepted block |
| Decides when | `2f+1` replicas commit a `(view, seq)` | a checkpoint and its child are both justified | a block's confidence counter reaches `β` |
| Agreement | ~2/3 quorum, met twice (`prepare`, `commit`) | ~2/3 of stake, over two epochs | ~80% of a random `K`-peer sample, `β` rounds running |
| Finality | deterministic | deterministic | probabilistic, `ε ≤ (1 − α_c/K)^β` |
| Communication cost | `O(n²)` | `O(n²)` un-aggregated (prod. BLS → `O(n)` not modeled) | `O(K·β)` per validator |
| Implemented as | classical PBFT, no signatures | FFG gadget standalone, no LMD-GHOST fork-choice | linearized Snowman, no DAG, no stake-weighted sampling |

## 3.4 Experiment design

The experiment space has five axes: validator-set size `n`, network timeline, adversary
type, workload, and seed. Sweeping all five at once is impractical, so the runs are
grouped into three families, each fixing four axes and varying one (Table 3.2).

`n` takes values in `{4, 7, 10, 16, 25}`, each satisfying `n = 3f + 1` for
`f ∈ {1, 2, 3, 5, 8}`, a clean Byzantine-threshold instance at every size. Two fault
symbols stay distinct: `f` is the fault threshold a configuration tolerates; `φ` is the
adversarial fraction actually injected in Family C, swept independently of the `3f+1`
relation.

**Table 3.2 — The three run families.**

| Family | Axis swept | `n` | Answers | Key values |
|:--|:--|:--|:--|:--|
| A — Scaling | `n` | `{4, 7, 10, 16, 25}` | RQ3 | honest set, clean network |
| B — Delay | network timeline | `{10, 25}` | RQ1 | baseline → `uniform` 100–500 ms → `heavy_tail` 1–5 s; with and without packet loss |
| C — Adversarial | adversary | `{10, 25}` | RQ2, RQ4 | `φ ∈ {0, 0.10, 0.20, 0.30}`; `φ ∈ {0.40, 0.50}` above threshold for equivocation |

Family A sweeps `n` over an honest, clean-network baseline to isolate scaling effects.
Families B and C fix `n ∈ {10, 25}`: `n = 10` keeps seed counts affordable; `n = 25`
lets the delay and adversarial effects show up more clearly.

The grid stops at `n = 25` rather than extending to production-scale validator
sets. The comparison targets the relative scaling trend across families, not
absolute latency at deployment scale, and that trend is already separated by
`n = 25`. Past that size the `O(n²)` message growth of the leader-based family
dominates simulation cost and raises the sweep's expense without
changing the qualitative ordering, so behavior at several-hundred-node scale
rests on the sensitivity argument rather than on direct measurement (§6.2).

Family B varies the network timeline. Message delays are drawn from a fixed catalogue
(`constant`, `uniform`, `normal`, `exponential`, `heavy_tail`), with optional packet loss
or partition. Partial synchrony is the two-phase case that crosses the Global
Stabilization Time, the point after which message delivery stops being adversarially
delayed.

Family C holds the network at baseline and sweeps the adversary, injecting Byzantine
behavior at fraction `φ` of each protocol's natural unit (replicas, validators, or
stake). Three behaviors are tested:

- **Delayed voting** — hold an outbound vote past the protocol's timing tolerance.
- **Silent non-participation** — run the state machine but send nothing; the crash-faulty
  case.
- **Equivocation** — sign two conflicting messages where one is expected. The sweep goes
  above the `1/3` threshold (`φ ∈ {0.40, 0.50}`) to expose the safety cliff. Snowman
  cannot fork below threshold, so equivocation against it collapses to the silent case
  and is not swept above threshold.

All three protocols share the same workload — a Poisson stream of 512-byte transactions
at 100 tx/s, below saturation — and the same seeds at each experiment point. Because
randomness is keyed by stream identity, all three see identical network delays and
arrival patterns; cross-protocol comparisons are paired under common random numbers.
Each cell runs for 20 seeds, raised to 30 at near-threshold Family C points. A run
fails liveness only if no honest validator commits within the measurement window.

## 3.5 Metric schema

Each metric has one definition, one unit, and one fixed instrumentation point. Protocol differences appear only as per-protocol formulas within the same column [[wiki/concepts/evaluation-metrics]]; Table 3.3 collects those formulas. The device that makes the three comparable is the *atomic commit unit* (ACU): the smallest set of transactions a protocol commits indivisibly, whether one block for PBFT, one finalized checkpoint for Casper FFG, or one accepted block for Snowman. Every "per-block" metric is recast as "per ACU", giving all three protocols the same denominator.

Some of these denominators are modeling conventions: the ACU definition, the Snowman rescaling, the Casper FFG slot calibration. A verdict is only reported as robust when it survives the sensitivity sweep that varies the convention's governing parameter.

Cross-protocol comparisons use *Pareto dominance*: protocol A dominates B when A is no worse on every metric and strictly better on at least one. A protocol is *non-dominated* when nothing dominates it. Chapter 5 applies this to test whether any family dominates the rest.

`commit_latency_ms` measures time to finality, recorded when each protocol hits its irreversibility point: `2f+1` `COMMIT` for PBFT, a finalized checkpoint for Casper FFG, and counter-`β` acceptance for Snowman.

Cross-protocol `goodput` is the committed-transaction rate, not a raw decided-event rate. The raw rate is protocol-dependent in granularity — per block for PBFT and Snowman, per finalized epoch for Casper FFG — and is not like-for-like.

**Table 3.3 — Per-protocol metric schema.** Adapted from
[[wiki/concepts/metric-reconciliation]].

| Metric | PBFT | Casper FFG | Snowman |
| :-- | :-- | :-- | :-- |
| `commit_latency_ms` | time to the first `decided` instance (`2f+1` `COMMIT`) | time to the first finalized checkpoint (justify→finalize, `≥ 2` epochs) | time to counter-`β` acceptance of the first block |
| `goodput` | committed transactions per window | committed transactions per window over finalized epochs | committed transactions per window |
| `total_msgs_per_acu` | all deliveries per ACU; evaluates to `(2n²−2)/n`, i.e. `O(n²)` traffic over an `n`-scaled denominator | `≈ 1.125n` (un-aggregated all-to-all votes; production BLS aggregation to `O(n)` not modeled) | `O(K·β)` query/response deliveries per validator, independent of `n` |
| `success_rate` | `0/1` per run (`1` iff an instance decided); a frequency after aggregation | `0/1` per run (iff an epoch finalized) | `0/1` per run (iff a block reaches counter `β`) |
| safety (`fork_rate`) | `0` below threshold by construction; `> 0` only above `1/3` under equivocation | `0` below threshold; `> 0` only above `1/3` (a conflicting finalized checkpoint, not a reorg) | N/A — probabilistic safety, reported via `ε` against `(1 − α_c/K)^β` |

The reliability metrics connect back to the §2.1 properties. A *safety violation* is an observed breach of Agreement (two honest validators commit conflicting values at one height), recorded in `fork_rate`. For the deterministic-finality protocols this is `0` below threshold by construction; it is only measured above it. A *liveness failure* is a breach of Termination: no honest validator commits within the window, measured by the complement of `success_rate`. Validity holds by construction and is not instrumented.

Snowman is the exception. Its finality is probabilistic, so safety is reported via the analytical bound `ε ≤ (1 − α_c/K)^β` rather than a measured fork rate — the weakest safety guarantee of the three, a limitation taken up in §6.2.

Continuous metrics are aggregated with a 95% Student-t interval across seeds. Rate metrics (`success_rate`, `fork_rate`) use a 95% Wilson score interval, which handles zero-observation cells correctly: a run with no violations is reported as `0/n_runs` with an upper confidence bound rather than a flat 0%. Near-threshold safety and liveness figures are read as bounds, not exact values.

The deliberate exclusions that bound these metrics — no compute or bandwidth cost, a synthetic open-loop workload, sub-production scale, and an uncovered leader-disruption surface — are consolidated with the full limitations in §6.2. Chapter 4 reports the baseline, delay, and adversarial sweeps and answers RQ1–RQ4 against this schema.
