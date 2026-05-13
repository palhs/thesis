# Adversary Model — Runtime

## 1. Framing — relationship to main page

Runtime companion to [[concepts/adversary-model]] (T18). The main page
pins the catalog — generic capability × protocol matrix, per-capability
bindings, protocol-specific attack surfaces. This page pins the runtime
obligations the implementation (T22) must hold: per-protocol intensity
normalization (§2), uniform effect schema (§3), `AdversaryProfile`
reference sketch (§4), T27 determinism interaction (§5), and the
open-to-revision register (§6). The split from
[[concepts/adversary-model]] follows `docs/wiki-spec.md` § Page size;
precedent: [[concepts/network-model]] / [[concepts/network-model-phases]]
and [[concepts/simulation-design]] / [[concepts/simulation-design-runtime]].
Read the main page first for the catalog surface; this page assumes
that catalog as given.

## 2. Intensity normalization

Each `(adversary_id, protocol_id, intensity)` triple consumed by T51–T53
carries an intensity `f ∈ [0, 1]` whose unit is the protocol's *natural*
fault-threshold denominator. The unit is fixed per protocol; the catalog
([[concepts/adversary-model]] §§3–7) reports ranges and invariants in
this unit.

| Protocol | `f` unit | Why this unit |
| :-- | :-- | :-- |
| PBFT | fraction of `n` replicas | Simulator scope uses equal-weight validators; replicas = nodes. The native fault threshold is `f < n/3` by count ([[algorithms/pbft#model-and-assumptions]]). |
| Casper FFG | fraction of total stake | Casper's threshold is stake-weighted; the accountable-safety cost (≈ α/3 stake burned per [[algorithms/pos#accountable-safety]]) is stake-denominated by definition. |
| Snowman | fraction of validators | Snowman's sub-sampling is node-uniform (modulo external sybil resistance) per [[algorithms/avalanche#model-and-assumptions]]; biasing stake without biasing validator count does not perturb the sampler. |
| Narwhal+Tusk | fraction of `n` replicas | Same as PBFT in the simulator scope; the quorum threshold over header certificates is by count ([[algorithms/dag-based#model-and-assumptions]]). |

The triple shape for T51–T53 is therefore

`(adversary_id: AdversaryKind, protocol_id: ProtocolId, f: float)`

with the meaning of `f` resolved by `protocol_id` via the table above.
`AdversaryKind` is sketched in §4; `ProtocolId` is the four-protocol
enumeration consumed by the experiment matrix
([[concepts/experiment-matrix]] — forward link).

**Cross-protocol plot policy.** Plots that span more than one protocol
on the x-axis must caption which unit they report. The default is to
plot each protocol on its own panel; a single-panel comparison requires
either (a) restricting to PBFT + Narwhal+Tusk (where the unit is
identical), or (b) explicitly captioning "stake-fraction for Casper;
validator-fraction for Snowman; replica-fraction for PBFT and
Narwhal+Tusk." Per-protocol re-mapping happens at plot-generation time,
not in the catalog; the catalog stores intensities in the natural unit
only.

**Why per-protocol natural rather than a single forced unit.** A single
stake-fraction unit would force Snowman's sample-bias mechanism through
an indirection (bias x% of stake → bias x% of sampling pool under
equal-weight) that has no semantic content in the simulator and loses
the natural threshold framing for PBFT and Narwhal+Tusk. A single
node-count unit would erase Casper's stake-burn cost reporting and
collapse the accountable-safety story
([[algorithms/pos#accountable-safety]]). The per-protocol-natural
choice respects each family's native fault model; the cost is the
per-plot re-mapping step described above, surfaced explicitly rather
than buried in the catalog row.

## 3. Effect schema

Every adversary run populates the same CSV column set. Column names
match [[concepts/evaluation-metrics]] and
[[concepts/metric-reconciliation]]; T18 does not introduce new metric
definitions. T40 (CSV finalisation) is the normative source for the
exact column list and unit; this page only pins which columns each
capability is *expected* to perturb.

**Per-capability expected perturbation.** Each capability is bound to
the columns it is expected to shift relative to an honest-baseline row.
Rows where no expected column moves are a signal that either the
adversary did not engage (mis-configured cell) or the protocol absorbed
the attack within the invariant — both are reportable outcomes.

| Capability | Columns expected to perturb |
| :-- | :-- |
| `delay-emission` | `time_to_finality_p50`, `time_to_finality_p95`, `consensus_msgs_per_acu` |
| `withhold-participation` | `liveness_failures`, `finality_lag_epochs` (Casper only), `throughput_per_validator` |
| `equivocate-vote` | `safety_violations`, `slashing_events` (Casper only), `view_changes` (PBFT only), `equivocations_blocked` (Narwhal only) |
| `disrupt-leader` | `view_changes` (PBFT), `anchor_commit_lag` (Narwhal), `block_proposal_failures` (Casper) |
| `snowman-collusion` (cf. [[concepts/adversary-model#7-protocol-specific-surfaces]] §7.1) | `safety_violations`, `accept_time_p95` |
| `narwhal-data-withhold` (cf. §7.2) | `batch_availability_rate`, `consensus_stall_events` |
| `casper-slashing` (cf. §7.3) | `slashing_events`, `safety_violations`, `safety_cost_stake_burned` |

**Invariant vs effect.** [[concepts/adversary-model]] §§3–7 carry the
*invariant* column per cell — the pass/fail predicate the run must
satisfy (e.g. "view-change rate ≤ baseline + 3σ", "safety violations =
0"). The effect-schema table above carries the *effect* — which metric
column moves. The two are related but distinct: T55 (detection logic)
reads invariants; T40 (CSV finalisation) reads effects. An effect that
moves without breaching its invariant is a reportable result, not a
failure.

## 4. AdversaryProfile reference sketch

Per the W3 design-contract style established for this thesis's hand-off
to W4 code (precedent: [[concepts/node-model]] §Reference sketch,
[[concepts/network-model]] §7, [[concepts/simulation-design-runtime]]
§4), this sketch is **not a specification**. It exists so T22 (`src/nodes/`)
has a starting shape and so a reader scanning this page cold can
picture the artifact. T22 may diverge; divergences land as
`## Revisions` entries per `docs/wiki-spec.md` §revisions-rule.

```python
# Reference sketch — illustrative, non-binding.
# Implementation (T22) may diverge; document via Revisions register.

from dataclasses import dataclass, field
from typing import Protocol, Optional
from enum import Enum

class AdversaryKind(Enum):
    DELAY = 0
    WITHHOLD = 1
    EQUIVOCATE = 2
    DISRUPT_LEADER = 3
    SNOWMAN_COLLUSION = 4
    NARWHAL_DATA_WITHHOLD = 5
    CASPER_SLASHING = 6

class AdversaryProfile(Protocol):
    kind: AdversaryKind
    nodes: tuple[int, ...]      # NodeIds; fixed at sim-start
    intensity: float            # per-protocol natural unit (see §2)

@dataclass(frozen=True)
class DelayProfile:
    nodes: tuple[int, ...]
    intensity: float
    delay_ms_min: float
    delay_ms_max: float
    kind: AdversaryKind = AdversaryKind.DELAY

@dataclass(frozen=True)
class WithholdProfile:
    nodes: tuple[int, ...]
    intensity: float
    kind: AdversaryKind = AdversaryKind.WITHHOLD

@dataclass(frozen=True)
class EquivocateProfile:
    nodes: tuple[int, ...]
    intensity: float
    target_phase: str           # protocol-specific: 'pre-prepare', 'attest', 'header'
    partition_strategy: str     # 'half-half', 'one-vs-rest'
    kind: AdversaryKind = AdversaryKind.EQUIVOCATE

@dataclass(frozen=True)
class DisruptLeaderProfile:
    nodes: tuple[int, ...]
    intensity: float
    action: str                 # 'silent', 'equivocate-proposal', 'anchor-withhold'
    kind: AdversaryKind = AdversaryKind.DISRUPT_LEADER

@dataclass(frozen=True)
class SnowmanCollusionProfile:
    nodes: tuple[int, ...]
    intensity: float
    target_colour: int          # the colour the collusion biases toward
    shared_rng_seed: int        # derived from sim seed; pins coordination
    kind: AdversaryKind = AdversaryKind.SNOWMAN_COLLUSION

@dataclass(frozen=True)
class NarwhalDataWithholdProfile:
    nodes: tuple[int, ...]
    intensity: float
    kind: AdversaryKind = AdversaryKind.NARWHAL_DATA_WITHHOLD

@dataclass(frozen=True)
class CasperSlashingProfile:
    nodes: tuple[int, ...]
    intensity: float
    violation: str              # 'double-vote' | 'surround-vote'
    kind: AdversaryKind = AdversaryKind.CASPER_SLASHING
```

**Attachment.** [[concepts/node-model#node-level-slot]] declares the
`self.adversary: Optional[AdversaryProfile]` slot. When non-`None`, the
FSM module routes outbound emissions and state-mutation decisions
through the profile before honest behaviour. The
per-protocol attachment matrix lives at
[[concepts/node-model#generic-adversary-attachment-matrix]]; the
protocol-specific slots (Snowman colluding sub-sampler, Narwhal+Tusk
data-availability withholding, Casper FFG slashable equivocation) are
pinned at [[concepts/node-model#protocol-specific-adversary-slots]].

**Static-only contract.** Profile fields are read once at relevant
emission points; there is no `on_observe()` callback (per the catalog's
static-only contract — see [[concepts/adversary-model#1-framing-and-scope]]
and design-spec §3 D2). T22 implements `self.adversary` as an opaque
strategy slot reading these fields; T18 fills the slot.

## 5. Determinism interaction with T27

The static-only profile contract (§4) gives the determinism rule for
free: identical `(config, seed)` produces byte-identical
adversary-injected events at byte-identical times.

**Per-Node adversary RNG.** Each `Node`'s RNG is seeded from the sim
seed per [[concepts/node-model#per-node-rng-seeding]]
(`seed = hash((global_seed, node_id))`). When the FSM dispatches
through `self.adversary`, any randomness (e.g. choosing which subset
to send equivocating messages to, sampling a delay from
`(delay_ms_min, delay_ms_max)`) draws from this per-Node RNG, not from
a global source. The forbidden-surfaces list at
[[concepts/node-model#forbidden-surfaces]] binds the adversary path
identically to the honest path.

**Colluding-group seed derivation.** Adversaries that coordinate
across multiple `Node`s (e.g. `SnowmanCollusionProfile`) derive a
shared RNG seed from `hash(sim_seed, group_id)`, where `group_id` is
fixed at sim-start. Two colluding nodes drawing from the same derived
seed in the same order make identical decisions without runtime
coordination, so the static-only contract holds.

**Replay invariant.** A run with `(config, seed)` produces an event
log byte-identical to any other run with the same `(config, seed)`.
Adversary-injected events are part of the log; the invariant covers
them. Cross-links: [[concepts/node-model#determinism-and-reproducibility]],
[[concepts/simulation-design-runtime]] §1.

## 6. Open to revision

The catalog deliberately leaves the following items open for
downstream tasks. Each promotes to a `## Revisions` entry on this
page (or on [[concepts/adversary-model]]) when resolved.

- **Adversary timing.** Static-only for T18. Promote to
  bounded-adaptive only if T22 implementation or T51 results expose a
  specific gap (an attack class with no static analogue). Revisions
  discipline applies.
- **Coordination protocol for Snowman colluding sub-sampler.**
  Currently "shared params + derived RNG seed" (§5). If T51 surfaces
  stale-state attacks (e.g. coordinated lag in adopting a new round
  number), the coordination model may need a richer shared-state
  surface.
- **Intensity range bounds per cell.** All cells in
  [[concepts/adversary-model]] §§3–7 carry `f ∈ [0, 0.33]` as a
  placeholder. T51–T53 calibration will tighten per-cell ranges; some
  attacks may have tighter or wider operational ranges than the naive
  Byzantine threshold.
- **`AdversaryProfile` final type.** `typing.Protocol` now (§4). T22
  may promote to `abc.ABC` if dispatch needs concrete inheritance —
  but the static-only contract makes this unlikely.
- **Safety-cost-budget column.** Currently lives in
  [[concepts/evaluation-metrics]]. T40 (CSV finalisation) may move it
  to a dedicated effect-schema slot; defer to T40.
- **LMD-GHOST reorg-inducer.** The brainstorm audit subsumed it under
  `delay-emission` ([[concepts/adversary-model#3-delay-emission]]).
  If W10 Casper results show structurally-distinct reorg dynamics,
  promote to a fourth protocol-specific entry under
  [[concepts/adversary-model#7-protocol-specific-surfaces]] §7.4.
- **Bullshark / Mysticeti out-of-scope.** Reaffirmed by spec §3 D5.
  Revisit only if family scope widens past Narwhal+Tusk (no current
  plan).
- **Snowman `α_p` vs `α_c` boundary exploit.** Audit subsumed under
  colluding-sub-sampler. If T51 results expose a distinct attack at
  the preference-flip threshold, promote to
  [[concepts/adversary-model#7-protocol-specific-surfaces]] §7.4.
- **Undefined metric column names in §3 effect schema.** The §3
  per-capability table references column names that are not yet
  defined in [[concepts/evaluation-metrics]] or
  [[concepts/metric-reconciliation]] (current CSV header lists
  `commit_latency_ms`, `finality_latency_ms`, `view_change_or_reorg_count`,
  `success_rate`, `fork_rate`, `empirical_epsilon`, `f_max_count`,
  `f_max_stake`, etc., but not these). T40 (CSV finalisation) must
  either define them or remap §3 onto the existing schema. The
  unresolved names: `time_to_finality_p50`, `time_to_finality_p95`,
  `liveness_failures`, `finality_lag_epochs`, `throughput_per_validator`,
  `safety_violations`, `slashing_events`, `view_changes`,
  `equivocations_blocked`, `anchor_commit_lag`,
  `block_proposal_failures`, `accept_time_p95`,
  `batch_availability_rate`, `consensus_stall_events`,
  `safety_cost_stake_burned`.

## 7. Sources

Inherits the bibliography of [[concepts/adversary-model#9-sources]].
No additional sources are introduced on this page.
