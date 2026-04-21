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
- **Validator set.** Rotates at epoch boundaries; fixed within an epoch.

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

The implementation is a simplified Casper-FFG-like gadget: a fixed-length
epoch, stake-weighted validator set, per-validator attestation delay, and
configurable slashing penalty. LMD-GHOST fork choice is modelled only to
the degree needed to expose delay-induced reorgs; full Gasper integration
is out of scope.

Knobs exposed to experiments:

- **Epoch length** (slots per epoch) — trades per-epoch finality latency
  against per-slot attestation overhead.
- **Participation threshold** for justification (default `2/3` stake) —
  to probe how close to the threshold the chain can operate before
  finalisation stalls.
- **Attestation delay per validator** — drives the LMD-GHOST reorg
  dynamic and lets the adversarial-delay adversary be parameterised.
- **Slashing penalty magnitude** — drives the safety-cost-budget metric.

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
  liveness. The simulator treats penalty magnitude as an independent
  knob for this reason.

## Sources

Citations `[7]`, `[8]` resolve via [[concepts/annotated-bibliography]]
to the dedicated source pages
[[sources/2026-04-21_buterin-griffith-casper-ffg-2017]] and
[[sources/2026-04-21_buterin-gasper-2020]] respectively.
