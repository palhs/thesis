# PoS-Finality Consensus

BFT as a finality gadget over a chain of blocks. PoS-finality protocols
split consensus into two layers: a block-proposal layer produces a
constantly-growing chain of candidate blocks, while a BFT gadget
periodically anoints certain blocks as irreversibly final. The canonical
instance is Casper FFG [7] and the full Ethereum integration is Gasper,
combining LMD-GHOST fork choice with Casper-style finality [8]. It sits
between [[algorithms/pbft]] (deterministic, single-slot finality) and
[[algorithms/avalanche]] (probabilistic finality) on the spectrum of how
aggressively a protocol commits — see [[concepts/consensus-families]] for
the full design-space map.

What distinguishes this family from the rest: the fault threshold is
measured in **stake**, not validator count, and deviation is punished
**economically via slashing** rather than only excluded cryptographically.

## Family scope

Two representative protocols share the gadget-over-chain structure but
differ in what the underlying chain looks like:

| Protocol | Source | Role |
| :---- | :---- | :---- |
| **Casper FFG** | Buterin & Griffith, 2017 [7] | Pure finality gadget; agnostic to the block-proposal layer. |
| **Gasper** | Buterin et al., 2020 [8] | Casper FFG + LMD-GHOST fork choice; the deployed Ethereum variant. |

## Model and assumptions

- **Synchrony.** Partial synchrony — see [[concepts/synchrony-models]].
  Asynchrony threatens finality delay, not safety: a stalled gadget simply
  stops justifying new checkpoints.
- **Fault model.** Up to `f < 1/3` of **total stake** may be Byzantine
  ([[concepts/fault-model]]). Collusion, equivocation, and arbitrary
  message forgery are in scope; the threshold is stake-weighted, not
  count-weighted.
- **Economic rationality.** Validators are assumed to value their staked
  deposit more than any profit obtainable from an equivocation strategy
  that survives long enough to cause harm. This is the new axis the
  family introduces and the one slashing operationalises.
- **Weak subjectivity.** New or long-offline nodes must trust a recent
  checkpoint from a social consensus source. No purely on-chain mechanism
  can distinguish a valid long-range history from an adversarial rewrite.
- **Signature aggregation.** Modern implementations use BLS so that
  thousands of attestations fit in a single aggregated vote — the
  enabling mechanism for validator sets in the tens of thousands.
- **Validator set.** In real Gasper the active set rotates at epoch
  boundaries (activations, exits, slashings) and is fixed within an epoch.
  *Simulator note:* the simulator does **not** model rotation — the
  `stake_table` is supplied once at `CasperNode.__init__` and is fixed for
  the entire run (see [[#simulator-mapping]]).

## Two-round finalisation

Time is partitioned into fixed-length **epochs**, each containing many
**slots**. The first block of each epoch is designated a **checkpoint**.
Validators cast FFG votes of the form `<source, target>` attesting that a
source checkpoint should justify a target checkpoint.

- A **supermajority link** from `S` to `T` exists when FFG votes
  representing `≥ 2/3` of total stake have been cast for `<S, T>`.
- A checkpoint `T` is **justified** when a supermajority link exists from
  any justified ancestor to `T`.
- A checkpoint `T` is **finalised** when `T` is justified *and* a
  supermajority link exists from `T` to its direct child `T'`.

The two-round justify-then-finalise structure is the PoS analogue of
PBFT's prepare-then-commit (see [[algorithms/pbft#three-phase-commit]]) —
but it operates at epoch granularity rather than per-block.

### Finality flow

```
  epoch n      epoch n+1    epoch n+2    epoch n+3
 +---------+  +---------+  +---------+  +---------+
 | block A |  | block B |  | block C |  | block D |   slots / blocks
 |  (cp)   |  |         |  |  (cp)   |  |         |   (cp = checkpoint)
 +---------+  +---------+  +---------+  +---------+
     |                         |
     |<== supermajority link (FFG votes, >= 2/3 stake) ==>|
     |                                                    |
   justified  ---->   justified   ---->   finalised
                   (two consecutive supermajority links)
```

## Slashing conditions

Safety rests on two provable misbehaviours being economically punishable.
Any validator that signs FFG votes violating either condition loses its
staked deposit.

- **Double voting.** Signing two distinct FFG votes with the same target
  epoch.
- **Surround voting.** Signing a vote `<S1, T1>` that surrounds another
  of the validator's own votes `<S2, T2>` — i.e. `S1 < S2` and
  `T2 < T1`.

## Accountable safety

The two-round structure gives the same quorum-intersection guarantee as
PBFT (see [[concepts/quorum-arithmetic]]) — applied to stake rather than
replica count. What PoS-finality adds on top is **accountable safety**:

Casper's accountable-safety theorem [7] shows that, if two conflicting
checkpoints are ever finalised, at least one-third of total stake must
have signed a slashable message. The culprits are identifiable, and
their deposits are destroyed. Safety violations are therefore not only
infeasible below the threshold but also **attributable** above it — the
property that distinguishes PoS-finality from unaccountable BFT.

This promotes Agreement (see [[concepts/consensus-properties]]) from a
threshold-only guarantee to a threshold-plus-economic-deterrent
guarantee.

## Behaviour under network delay

PoS-finality degrades gracefully under delay because its unit of progress
is an epoch, not a block.

- **Stalled finalisation.** When delay spikes, the block-proposal layer
  keeps running but FFG supermajority links fail to form, and
  finalisation simply stalls. Safety is not at risk during a stall; only
  time-to-finality lengthens. In Ethereum's 32-slot epochs, a one-epoch
  delay in finalisation already adds ~6.4 minutes to time-to-finality.
- **LMD-GHOST reorgs.** Gasper's fork choice operates on the latest
  attestation from each validator [8]. Under delay, stale attestations
  can survive long enough to bias fork choice toward a chain that FFG
  will ultimately refuse to finalise — producing short-lived forks that
  reorg when attestations catch up.

## Behaviour under adversarial conditions

Three adversarial strategies are directly relevant and concretised as
simulator behaviours (the operational taxonomy lives in
[[concepts/adversary-model]], pending T18).

- **Non-participation.** Byzantine validators abstain from attesting.
  Below `1/3` of stake the only effect is higher finality latency; at or
  above `1/3` the chain stops finalising entirely — a pure liveness
  attack.
- **Equivocation.** Byzantine validators attempt to double-vote or
  surround-vote. Each violator forfeits its stake. Above `1/3`
  colluding stake, safety can be violated — but at the cost of at least
  one-third of total stake being destroyed. This is the economic
  deterrent that supplements the cryptographic threshold.
- **Delayed attestation.** Byzantine validators attest at the last
  possible slot to maximise uncertainty in fork choice. This is a
  throughput/latency attack rather than a safety attack, and it is
  specifically the behaviour Gasper's LMD-GHOST rule is sensitive to.

**Safety-cost budget.** Because slashing is a first-class mechanism,
PoS-finality exposes a metric PBFT-family protocols do not: for an
attacker controlling stake `α`, a successful safety attack costs
approximately `α/3` of total stake burned. The simulator can therefore
report not only whether an attack succeeded but how expensive it was —
meaningful only in the PoS setting.

## Communication complexity

| Aspect | Per-slot cost | Per-epoch cost | Finality latency |
| :---- | :---- | :---- | :---- |
| **Attestations** | `n` per slot (BLS-aggregated to ~1) | `n` total | — |
| **FFG votes** | — | `O(n)` aggregated | 2 epochs (justify + finalise) |
| **Slashing evidence** | rare; carried in blocks | rare | — |

BLS aggregation reduces the per-slot communication from `O(n)` distinct
messages to a single aggregated attestation per committee — the enabling
mechanism for the large validator sets that PBFT-family protocols cannot
reach. The simulator models aggregation as a fixed cost per committee to
keep per-validator instrumentation comparable across families.

## Simulator mapping

The implementation in `src/pos/` is a deliberately partial Casper-FFG
gadget. This section separates **what real Gasper / the paper specify**
(described in the sections above) from **what this simulator actually
implements**. Several mechanisms described above as Gasper theory are
*not* built; they are listed under "Not implemented" so the gap between
model and code is explicit. (Revised 2026-06-04 — see
[[#revisions]] — the earlier version of this section claimed features
that do not exist in the code.)

### Implemented

- **Stake-weighted two-round FFG.** Fixed-length epochs over a chain of
  blocks; the `<source, target>` justify→finalise rule with a
  stake-weighted `≥ 2/3` supermajority link (`src/pos/finality.py`,
  `src/pos/epoch.py`, `src/pos/node.py`). The supermajority test is
  division-free (`3·stake ≥ 2·total`) so whole-number stakes compare
  exactly.
- **Stake-weighted proposer selection** (T33) — see the next subsection.
- **Slashing-condition *detection*** (T70). The simulator detects the two
  provable misbehaviours defined under [[#slashing-conditions]]:
  - **Double voting** — two distinct FFG votes by the same validator with
    the same target epoch.
  - **Surround voting** — a validator's vote `<S1, T1>` that surrounds one
    of its own earlier votes `<S2, T2>` (`S1 < S2` and `T2 < T1`).
  Detection identifies and records the offending validators.
- **Slashable-stake-fraction metric** (T70) — reports the fraction of
  total stake that has signed a slashable (double- or surround-vote)
  message, the operational handle on [[#accountable-safety]].

### Not implemented (deferred)

These exist in real Gasper / Casper FFG but are absent from `src/pos/`.
Treat any experiment claim that depends on them as out of scope until the
corresponding code lands:

- **Slashing *penalty* application / stake burn.** Detection records
  offenders, but no deposit is destroyed and no stake is removed from the
  active set. There is no penalty-magnitude knob.
- **Safety-cost budget.** Because no stake is burned, the simulator does
  *not* report the `~α/3`-of-stake economic cost of a safety attack
  described under [[#behaviour-under-adversarial-conditions]]. That metric
  is deferred until penalty application exists.
- **LMD-GHOST fork choice and delay-induced reorgs.** The chain selects
  the proposer's parent on a single known head; there is no
  latest-message fork choice and no reorg dynamic (`src/pos/chain.py`
  notes fork choice is deferred to T46–T50).
- **Per-validator attestation delay.** Every node attests at a fixed
  `attest_offset` within the epoch; there is no per-validator delay knob
  driving fork-choice bias.
- **Epoch-boundary validator-set rotation.** The `stake_table` is fixed
  at `CasperNode.__init__` and never rotates (see [[#model-and-assumptions]]).
- **Checkpoint tree across forks.** Finality is tracked on a single
  justify chain; conflicting-checkpoint trees across forks are not
  represented.

### Knobs exposed to experiments

- **Epoch length** (`slots_per_epoch`) — trades per-epoch finality latency
  against per-slot attestation overhead.
- **Participation / supermajority threshold** for justification (fixed at
  `2/3` stake) — combined with adversarial non-participation, lets
  experiments probe how close to the threshold the chain can operate
  before finalisation stalls.

(The earlier "attestation delay per validator" and "slashing penalty
magnitude" knobs were never implemented and have been removed from this
list.)

**Proposer selection (T33).** The slot proposer is drawn by
stake-weighted random sampling: `src/pos/selection.py`'s
`stake_weighted_proposer(slot, stake_table, global_seed)` is a pure
function seeded from `(global_seed, slot)` via blake2b, so every
validator computes the same proposer for any given slot (`CasperNode`
rejects any `BLOCK-PROPOSAL` whose `msg.src` disagrees). The
probability of selecting validator `v` equals its share of total stake;
zero-stake validators are never selected. The 100-round empirical
fairness check is `tests/pos/test_selection.py`; the broader sweep over
seeds and stake distributions is the T33 experiment page
[[experiments/2026-05-23_pos-selection-fairness]]. The earlier T32 rule
(`slot mod n`, round-robin) is retained as `round_robin_proposer` for
reference and direct testing.

These feed T32–T35 (PoS implementation and correctness tests) and the
baseline/delay/adversarial experiment batteries in Weeks 8–10.

## Expected findings

Hypotheses to evaluate in the results chapter:

- Time-to-finality degrades non-linearly once adversarial stake
  approaches `1/3`; below it, only latency grows.
- Reorg depth scales with attestation delay variance, not mean delay —
  mirroring the variance-sensitivity seen in PBFT view changes.
- Economic cost of a successful safety break (`~α/3` of stake) is a
  meaningful secondary security metric absent from PBFT-family analyses.

## Weaknesses to foreground

- **Long finality latency.** Two-epoch finalisation means time-to-finality
  is measured in minutes, not the sub-second latency PBFT can achieve.
- **Weak subjectivity.** New or offline-for-long nodes cannot bootstrap
  purely from the chain; they must trust a recent checkpoint from a
  social source. No purely on-chain mechanism closes this gap.
- **Attestation-delay sensitivity.** LMD-GHOST fork choice is biased by
  stale attestations under delay, producing reorgs that finalisation
  ultimately reconciles — but which are visible to applications as
  short-lived forks.
- **Slashing calibration is load-bearing.** Penalties too small → the
  economic deterrent collapses; too large → honest validators fear
  equipment failure more than dishonesty and under-attest, eroding
  liveness. *(In real Gasper this calibration is load-bearing; the
  simulator does not yet apply penalties, so penalty magnitude is not a
  knob — see [[#simulator-mapping]].)*

## Revisions

- **2026-06-04 (T70, finding #4).** The previous "Simulator mapping"
  section presented unbuilt machinery as implemented. Corrected to
  separate paper/Gasper theory from what `src/pos/` actually does:
  - **Removed false simulator claims:** per-validator attestation delay,
    configurable slashing penalty / stake burn, LMD-GHOST fork choice and
    delay-induced reorgs, a safety-cost budget, and checkpoint trees
    across forks. None of these exist in `src/pos/`. The two corresponding
    experiment knobs (attestation-delay-per-validator, slashing-penalty
    magnitude) were removed from the knobs list, and the trailing
    "simulator treats penalty magnitude as a knob" clause under
    [[#weaknesses-to-foreground]] was corrected.
  - **Corrected validator-set claim** under [[#model-and-assumptions]]:
    epoch-boundary rotation is real-Gasper theory only; the simulator's
    `stake_table` is fixed at `CasperNode.__init__` for the whole run.
  - **Added the newly implemented T70 features:** double-vote and
    surround-vote slashing *detection* and the slashable-stake-fraction
    metric, landing alongside as finding #3. These are detection-only —
    no penalty is applied.
  - **Still-open overclaim flagged for the human:** the safety-cost-budget
    paragraph under [[#behaviour-under-adversarial-conditions]] and the
    reorg-depth / economic-cost items under [[#expected-findings]] still
    read as achievable simulator outputs. Left in place as paper-theory /
    future-work hypotheses; they depend on penalty application and
    LMD-GHOST, both deferred.

## Sources

Citations `[7]`, `[8]` resolve via [[concepts/annotated-bibliography]]
to the dedicated source pages
[[sources/2026-04-21_buterin-griffith-casper-ffg-2017]] and
[[sources/2026-04-21_buterin-gasper-2020]] respectively.
