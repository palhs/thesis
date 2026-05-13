# T18 — Adversary Model Design

**Task:** T18 (Engineer)
**Date:** 2026-05-13
**Outcome:** Design contract for the adversary catalog covering the four-
protocol scope (PBFT, Casper FFG, Snowman, Narwhal+Tusk), filed as a split-
pair of wiki concept pages.
**Consumed by:** `superpowers:writing-plans` (next), then the wiki page
write that produces `wiki/concepts/adversary-model.md` and
`wiki/concepts/adversary-model-runtime.md`, then T22 (adversary dispatch in
`src/nodes/`), then T51–T53 (Week 10 adversarial experiments), then T55
(safety/liveness invariant detectors).

---

## 1. Goal

Define the design contract for the adversary catalog: the durable
specification of *what attacks the simulator can mount, against which
protocol, at what intensity, with what expected effect, and against what
invariant*. The artifact is a pair of wiki concept pages following the
W3 design-contract precedent established by [[concepts/node-model]],
[[concepts/network-model]], and [[concepts/simulation-design]].

**In scope.** The four-row generic capability × protocol matrix; the three
protocol-specific attack surfaces; the per-protocol intensity-normalization
scheme; the uniform effect schema; the `AdversaryProfile` reference sketch;
the determinism interaction with T27; the catalog-frozen invariant that
makes T51–T53 well-defined.

**Out of scope.** Implementation of `AdversaryProfile` dispatch (T22),
exact intensity sweep ranges (T51–T53 calibration), safety/liveness
detector implementation (T55), CSV column finalisation (T40), and any
adversary timing model stronger than static profiles (deferred — see §7).

---

## 2. Context — upstream contracts taken as given

This spec composes with five upstream contracts already on the wiki. The
decisions in §3 take their content as given and do not re-debate them.

| Upstream contract | Role |
| :-- | :-- |
| [[concepts/node-model]] §9 (T14) | Declares the `Node`-level `self.adversary` slot, the generic-adversary attachment matrix (per-protocol FSM/outbound touchpoint per capability), and the protocol-specific adversary slot list. T18 fills the binding *semantics*; T14 owns the attachment *surface*. |
| [[concepts/network-model]] §6 (T15) | Pins the honest-infrastructure adversary boundary: the network does not equivocate, drop selectively, or partition adversarially. All adversarial behaviour originates at `Node`-level dispatch through `self.adversary`. |
| [[concepts/evaluation-metrics]] + [[concepts/metric-reconciliation]] | Canonical metric definitions and per-protocol formulas. The effect schema (Page B §3) reuses this column vocabulary; no new metric is introduced. |
| [[concepts/fault-model]] | Theoretical fault-class taxonomy (crash/omission/Byzantine; static/adaptive timing). T18 commits to the static slice. |
| [[algorithms/pbft]] §Behaviour-under-adversarial-conditions, [[algorithms/pos]] §Behaviour-under-adversarial-conditions, [[algorithms/avalanche]] §Behaviour-under-adversarial-conditions, [[algorithms/dag-based]] §Behaviour-under-adversarial-conditions | The four protocol pages each enumerate adversarial strategies relevant to that protocol. T18's catalog bindings are rooted in those sections; this spec's prior row-by-row audit reconciled them into the matrix. |

---

## 3. Decisions

Seven structural decisions taken during the brainstorm phase. Each carries
a one-line statement and the rationale that locked it in.

### D1. Intensity unit: per-protocol natural

**Decision.** Each `(adversary_id, protocol_id, intensity)` triple
consumed by T51–T53 carries an intensity `f ∈ [0, 1]` whose unit is the
protocol's *natural* fault-threshold denominator:

- PBFT, Narwhal+Tusk: `f` = fraction of `n` replicas (sim uses equal-
  weight validators; replicas = nodes).
- Casper FFG: `f` = fraction of total stake.
- Snowman: `f` = fraction of validators (per [[algorithms/avalanche]]
  random peer sampling, sampling is node-uniform modulo external sybil
  resistance; the simulator scope is internal sampling only).

**Rationale.** Respects each protocol's native fault threshold; preserves
the Casper safety-cost-budget metric (~α/3 of stake burned per
[[algorithms/pos#accountable-safety]]) which is stake-denominated by
definition; avoids forcing Snowman's sample-mechanism into a stake idiom
where it does not bind. Cost: cross-protocol plots require a per-protocol
re-mapping step at plot-generation time — surfaced explicitly in Page B
§2 and flagged in any results page that reports across the four families.

### D2. Adversary timing: static only

**Decision.** `AdversaryProfile` is *data*, not *behavior*. All adversary
parameters — kind, intensity, node set, per-kind config — are fixed at
sim-start. There is no `on_observe()` hook, no mid-run reaction to
protocol state, no observation surface.

**Rationale.** Matches the simpler half of [[concepts/fault-model]]'s
static/adaptive split; collapses the [[concepts/node-model]] §8
determinism contract to "seed + config → byte-identical events" with no
extra clauses; makes T22 dispatch trivially type-checkable. Cost: rules
out genuinely targeted attacks (e.g. "equivocate exactly when own vote
would tip the quorum past `2f+1`"). The bounded-adaptive escalation
remains available behind a Revisions entry if T22/T51 surface a
specific gap (see §7 item 1).

### D3. Page layout: split-pair (catalog + runtime)

**Decision.** Two wiki pages, mirroring the [[concepts/network-model]] /
[[concepts/network-model-phases]] split:

- `wiki/concepts/adversary-model.md` (~280 lines) — catalog. Framing,
  capability × protocol matrix, per-capability bindings, protocol-
  specific surfaces, sources.
- `wiki/concepts/adversary-model-runtime.md` (~250 lines) — runtime
  contract. Intensity normalization, effect schema, `AdversaryProfile`
  reference sketch, T27 determinism interaction, open-to-revision
  register.

**Rationale.** Hits the [[docs/wiki-spec]] ~300-line page-size guideline
without aggressively trimming per-cell prose. Reader scanning the matrix
isn't forced through the runtime sketch; reader implementing T22 isn't
forced through Chapter-4-facing comparison prose. Established precedent
on the same project.

### D4. Per-cell depth: hybrid table + prose

**Decision.** Each per-capability section in Page A (§§3–6) opens with a
6-column 4-row table (one row per protocol) carrying:

`| Protocol | Mechanism | Intensity range | Safety/Liveness | Invariant checked | Source |`

Below the table, ~80 words of prose covers reductions, N/A
justifications, near-threshold behavior, and cross-protocol contrasts the
table can't carry.

**Rationale.** Best skim-ability for the matrix-as-comparison-surface use
case; still carries the mini-schema (mechanism / intensity / S/L /
invariant / source) the T18 verify clauses require for T51–T53 and T55
consumption. Mirrors the [[concepts/message-types]] §§3–6 per-protocol
section layout.

### D5. Protocol-specific scope: 3, closed

**Decision.** Page A §7 commits to exactly three protocol-specific
adversaries:

- §7.1 Snowman colluding sub-sampler [9]
- §7.2 Narwhal+Tusk data-availability withholding [11]
- §7.3 Casper FFG slashable-equivocation refinements [7]

The row-by-row audit conducted in the brainstorm phase found no other
structurally-unique surfaces across the four-protocol scope. Future
additions go through wiki Revisions discipline.

**Rationale.** Pins the T51–T53 catalog-frozen invariant:
**4 generic capabilities × 4 protocols (1 N/A, 1 reduction) +
3 protocol-specific = 17 valid `(adversary_id, protocol_id, f)` shapes.**
Without this number, T19 (experiment matrix) and T51–T53 cannot size
themselves. Cost: if W10 results expose a missing surface, it costs a
Revisions cycle to add it.

### D6. node-model §9 / adversary-model.md boundary

**Decision.** [[concepts/node-model]] §9 retains ownership of the
*attachment surface* — the `Node`-level `self.adversary` slot, the
per-protocol FSM-state / outbound-API touchpoint matrix (which `Node`
method each capability gates), and the protocol-specific adversary slot
list. `adversary-model.md` owns *binding semantics* — mechanism prose,
intensity range, safety/liveness classification, invariant, source. Zero
content duplication; the two pages compose.

**Rationale.** §9's existing matrix encodes information T14 owns (FSM
hook points), which is genuinely a node-model concern. Moving it would
conflate ownership. Duplicating it would create a synchronisation
hazard the [[docs/wiki-spec]] Revisions rule exists to prevent.

**Side effect.** node-model.md gains a `## Revisions` entry on the
write of adversary-model.md (see §8).

### D7. `AdversaryProfile` shape: `typing.Protocol` + concrete dataclasses

**Decision.** The reference sketch in Page B §4 declares:

- An abstract `class AdversaryProfile(Protocol)` — structural-typing
  surface, extends the skeleton node-model §9 already sketches.
- One concrete `@dataclass` per static-profile kind:
  `DelayProfile`, `WithholdProfile`, `EquivocateProfile`,
  `DisruptLeaderProfile`, plus three protocol-specific dataclasses
  (`SnowmanCollusionProfile`, `NarwhalDataWithholdProfile`,
  `CasperSlashingProfile`).

The reference sketch is illustrative and non-binding per the W3
design-contract precedent; T22 may diverge, with divergences landing as
Revisions entries.

**Rationale.** D2 (static-only) means profiles carry *fields*, not
methods — and fields belong in dataclasses. `Protocol` keeps T22's
dispatch site type-checkable. ABC was rejected because it implies
inheritable behavior, which D2 explicitly forbids.

---

## 4. Page A agenda — `wiki/concepts/adversary-model.md`

Target: ~280 lines. Section list with what each carries.

### §1 Framing & scope (~25 lines)
Two-layer organisation statement (generic × protocol matrix, then
protocol-specific surfaces). Static-only profile contract. Per-protocol
natural intensity unit. Forward pointer to
[[concepts/adversary-model-runtime]] for intensity / effect / sketch /
determinism content. Cross-links to [[concepts/node-model#adversary-attachment]]
(attachment surface), [[concepts/fault-model]] (taxonomy framing),
[[concepts/evaluation-metrics]] (effect schema column source).

### §2 Generic capability × protocol matrix (~30 lines)
The 4×4 audit matrix. Rows: `delay-emission`, `withhold-participation`,
`equivocate-vote`, `disrupt-leader`. Columns: PBFT, Casper FFG, Snowman,
Narwhal+Tusk. Cells: terse mechanism phrase. One structural `N/A`
(Snowman × `disrupt-leader`). One noted reduction (Snowman ×
`equivocate-vote` → "lying responder"). Caption pins the matrix as the
Chapter 4 comparison surface and explains the asymmetric cells as
encoding structural property differences (Snowman's leaderlessness;
Snowman's lack of message-intersection in vote-counting).

### §3 `delay-emission` (~40 lines)
Capability statement (one line). 6-column table (per D4) with rows for
all four protocols; S/L = Liveness for all four. Prose (~80 words)
covers: α-threshold near-miss behaviour where Snowman's preference
oscillates without accepting; Snowman tail "don't-know" reply
interaction at the asynchrony boundary; PBFT view-change-rate as the
operationalisation of the liveness invariant.

### §4 `withhold-participation` (~40 lines)
Same shape as §3. Prose covers: `halted{crashed}` lifecycle encoding
([[concepts/node-model#halt-reasons]]); the skip-vs-slow distinction
between this capability and `delay-emission`; the Casper ≥1/3-stake
finalisation-stall threshold per [[algorithms/pos#behaviour-under-adversarial-conditions]];
Narwhal's throughput-proportional degradation per [[algorithms/dag-based#behaviour-under-adversarial-conditions]].

### §5 `equivocate-vote` (~45 lines, longest of §§3–6)
Same shape as §3, but the Snowman row carries the reduction text rather
than a fresh mechanism. Prose covers: the reduction (Snowman has no
inter-message intersection step, so signing incompatible messages is
mechanically indistinguishable from selective response; cf.
[[concepts/node-model]] §9 ll. 470–473); Casper accountable-safety cost
(~α/3 of stake burned per [[algorithms/pos#accountable-safety]]);
Narwhal certificate-step block per [[algorithms/dag-based#safety-argument]];
PBFT view-change-as-detector per [[algorithms/pbft#behaviour-under-adversarial-conditions]].

### §6 `disrupt-leader` (~40 lines)
Same shape as §3, but the Snowman row carries the `N/A` with the
structural reason. Prose covers: Snowman's leaderlessness per
[[concepts/node-model]] §5; Bullshark/Mysticeti anchor-leader caveat
(out-of-scope per [[algorithms/dag-based#family-scope]] but flagged for
forward compatibility if family scope ever widens).

### §7 Protocol-specific surfaces (~45 lines)
Three subsections, each carrying: action, victim protocol, S/L
classification, intensity range, invariant checked, source citation.

- §7.1 Snowman colluding sub-sampler [9] — coordinated lying responders
  biasing `α_c` per [[algorithms/avalanche#behaviour-under-adversarial-conditions]].
- §7.2 Narwhal+Tusk data-availability withholding [11] — worker
  certifies header but withholds batch contents per
  [[algorithms/dag-based#behaviour-under-adversarial-conditions]] and
  [[concepts/node-model]] §9 ll. 483–485.
- §7.3 Casper FFG slashable-equivocation refinements [7] — surround /
  double vote with explicit slashing payload per
  [[algorithms/pos#slashing-conditions]].

Caption pins the structural-uniqueness reasoning: each exploits a
property the other three families don't share (sampled quorum, two-layer
availability/ordering split, on-chain slashing).

### §8 Revisions (~5 lines)
Reserved stub per W3 design-contract precedent.

### §9 Sources (~10 lines)
Resolve `[4]`, `[7]`, `[9]`, `[11]` via [[concepts/annotated-bibliography]].

---

## 5. Page B agenda — `wiki/concepts/adversary-model-runtime.md`

Target: ~250 lines. Section list with what each carries.

### §1 Framing — relationship to main page (~15 lines)
Catalog ↔ runtime split statement; same precedent as
[[concepts/network-model]] / [[concepts/network-model-phases]] and
[[concepts/simulation-design]] / [[concepts/simulation-design-runtime]].

### §2 Intensity normalization (~50 lines)
Per-protocol unit mapping table (per D1): PBFT/Narwhal in *replicas*;
Casper in *stake fraction*; Snowman in *validator-count fraction*.
T51–T53 triple shape `(adversary_id, protocol_id, f)` with per-protocol
meaning of `f`. Cross-protocol plot policy: per-protocol re-mapping at
plot-generation time; results pages must caption which axis is reported.
Rationale recap (~80 words on why per-protocol natural rather than a
forced single axis).

### §3 Effect schema (~40 lines)
Uniform CSV column set every adversary's runs populate; column names
match [[concepts/evaluation-metrics]] and [[concepts/metric-reconciliation]].
Per-capability expected-perturbation table (which columns each
capability is *expected* to shift):

- `delay-emission` → `time_to_finality_p95`, `consensus_msgs_per_acu`
- `withhold-participation` → `liveness_failures`, `finality_lag_epochs`
  (Casper), `throughput_per_validator`
- `equivocate-vote` → `safety_violations`, `slashing_events` (Casper
  only), `view_changes` (PBFT only)
- `disrupt-leader` → `view_changes` (PBFT), `anchor_commit_lag` (Narwhal),
  `block_proposal_failures` (Casper)

Pin the *invariant* (what passes/fails per cell) vs *effect* (which
metric column moves) distinction.

### §4 `AdversaryProfile` reference sketch (~70 lines, illustrative non-binding)
Per D7:

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

Attachment via [[concepts/node-model#node-level-slot]] `self.adversary`
(typed as `Optional[AdversaryProfile]`). FSM dispatch contract: when
`self.adversary is not None`, the FSM module routes outbound emissions
and state-mutation decisions through the profile before honest
behaviour. Static-only contract reaffirmed: profile fields are read
once at relevant emission points; no `on_observe` callback.

### §5 Determinism interaction with T27 (~25 lines)
Per-Node adversary RNG: each `Node`'s RNG is seeded from the sim seed
per [[concepts/node-model#determinism-and-reproducibility]] §8.1.
Colluding-group seed derivation: groups with shared coordination
(`SnowmanCollusionProfile.shared_rng_seed`) derive their seed from
`hash(sim_seed, group_id)` so that the seed is reproducible without
serialising into config. Replay invariant: identical `(config, seed)` →
identical adversary-injected events at byte-identical times.
Cross-links: [[concepts/node-model#determinism-and-reproducibility]],
[[concepts/simulation-design-runtime#determinism-contract]].

### §6 Open to revision (~35 lines)
Mirrors §7 of this spec — every entry in §7 lands as a §6 bullet on the
runtime page.

### §7 Sources (~10 lines)
Inherits Page A's bibliography.

---

## 6. Constraints

### 6.1 T18 verify clauses (TASKS.md)

The TASKS.md T18 entry specifies three verify clauses. This spec
satisfies them as follows.

| Clause | Satisfied by |
| :-- | :-- |
| Every generic adversary has a per-protocol semantics row or an `N/A` justification | Page A §§3–6 hybrid table layout (D4); the one `N/A` (Snowman × `disrupt-leader`) carries structural reason in prose; the one reduction (Snowman × `equivocate-vote`) carries reduction prose. |
| Every protocol-specific adversary traces to its source paper | Page A §7 sources column carries `[9]`, `[11]`, `[7]` respectively; Page A §9 resolves via [[concepts/annotated-bibliography]]. |
| T51–T53 can be expressed as `(adversary_id, protocol_id, intensity)` triples drawn from this catalog without gaps | D5 pins the catalog-frozen count at **17 valid triples**. Page B §2 specifies the intensity unit per triple. |

### 6.2 Catalog-frozen invariant

The catalog admits exactly the following `(adversary_id, protocol_id)`
pairs:

- **14 generic pairs** = (4 capabilities × 4 protocols) − 1 N/A − 1 reduction-not-a-fresh-binding... but the reduction *is* still a valid pair (selective-response is a real attack); only the N/A is excluded. So **15 generic pairs** are valid (16 cells − 1 N/A).

  Correction: the matrix has 16 cells; 1 is `N/A` (Snowman ×
  `disrupt-leader`); 15 are valid bindings. The Snowman ×
  `equivocate-vote` cell is a noted *reduction* but still a runnable
  binding (it just reduces to selective-response semantics).

- **3 protocol-specific pairs** (D5).

- **Total: 18 valid `(adversary_id, protocol_id)` pairs.** Each pair
  parameterises with intensity `f ∈ [0, 1]` in the protocol's natural
  unit (D1).

Revising the catalog-frozen number from 17 (cited during brainstorm) to
**18** based on this audit. T51–T53 sizes itself against this number.

### 6.3 Determinism contract

Per D2 + D7, the determinism contract is:

1. `AdversaryProfile` is a frozen dataclass; no mutation after sim-start.
2. The set of `Node`s with `self.adversary is not None` is fixed at
   sim-start.
3. Any RNG drawn by the FSM under adversarial dispatch uses the per-
   `Node` RNG seeded per [[concepts/node-model]] §8.1, or a colluding-
   group RNG derived deterministically from `(sim_seed, group_id)`.
4. Replay invariant: identical `(config, seed)` produces byte-identical
   adversary-injected events.

### 6.4 Adversary boundary

Per [[concepts/network-model]] §6 (honest-infrastructure) and
[[concepts/node-model]] §9, the boundary is:

- Network is honest. No adversarial drop, reorder, partition, or
  equivocation originates at the network layer.
- All adversarial behaviour originates at `Node`-level dispatch through
  `self.adversary`.
- The scheduler ([[concepts/simulation-design]]) has no adversary slot;
  adversarial timing manifests only via `Node` outbound-API gating, not
  via direct event-queue manipulation.

---

## 7. Open to revision

Items the spec deliberately leaves open for downstream tasks to resolve.

1. **Adversary timing.** Static-only for T18. Promote to bounded-
   adaptive only if T22 implementation or T51 results expose a specific
   gap (e.g. an attack class that has no static analogue). Revisions
   discipline.

2. **Coordination protocol for Snowman colluding sub-sampler.**
   Currently "shared params + derived RNG seed." If T51 surfaces stale-
   state attacks (e.g. coordinated lag in adopting a new round number),
   the coordination model may need a richer shared-state surface.

3. **Intensity range bounds per cell.** All cells currently carry
   `f ∈ [0, 0.33]` as a placeholder. T51–T53 calibration will tighten
   per-cell ranges (some attacks may have tighter or wider operational
   ranges than the naive Byzantine threshold).

4. **`AdversaryProfile` final type.** `typing.Protocol` now. T22 may
   promote to `abc.ABC` if dispatch needs concrete inheritance — but D2
   makes this unlikely.

5. **Safety-cost-budget column.** Currently lives in
   [[concepts/evaluation-metrics]]. T40 (CSV finalisation) may move it
   to a dedicated effect-schema slot. Defer to T40.

6. **LMD-GHOST reorg-inducer.** The brainstorm audit subsumed it under
   `delay-emission`. If W10 Casper results show structurally-distinct
   reorg dynamics, promote it to a fourth protocol-specific entry under
   §7.4.

7. **Bullshark/Mysticeti out-of-scope.** Reaffirmed by D5. Revisit only
   if family scope widens past Narwhal+Tusk (currently no plan).

8. **Snowman `α_p` vs `α_c` boundary.** Audit subsumed under
   colluding-sub-sampler. If T51 results expose a distinct attack at
   the preference-flip threshold, promote to §7.4.

---

## 8. Upstream Revisions register

Writing this spec triggers one Revisions entry on an upstream wiki page:

### [[concepts/node-model]] — `## Revisions`

```markdown
### 2026-05-13 — §9 scope contracts to attachment surface only

T18 ([[concepts/adversary-model]]) now owns adversary binding
semantics. §9 retains the attachment-surface declaration (per-protocol
FSM/outbound touchpoint matrix, `self.adversary` slot, protocol-
specific slot list) but no longer owns the cross-protocol semantic
detail. Per-cell binding semantics (mechanism, intensity range,
safety/liveness classification, invariant) live in
[[concepts/adversary-model]] §§3–7. The §9 matrix here remains as the
declaration of *which* `Node` method each capability gates; the
binding details for *what* the gated method does in each protocol are
on the adversary-model page.

No other §s are affected. Determinism rules (§8), inbound API (§6),
outbound API (§7), and role taxonomy (§5) are unchanged.
```

---

## 9. Handoff

**Next step.** Invoke `superpowers:writing-plans` against this spec to
produce the implementation plan for the wiki page write.

**Plan-stage outputs expected.**
1. Step-by-step ordered task list for writing both pages.
2. Companion updates: `wiki/index.md` (+2 entries), `wiki/log.md` (+1
   entry per [[docs/wiki-spec#log-format]]),
   [[concepts/node-model#revisions]] (entry per §8 above).
3. Verification criteria mapped to the T18 verify clauses (§6.1).
4. Commit cadence: per [[docs/workflow]] §commit-convention, target
   `task 18: define adversary catalog` as the In-Review commit when
   the page write is complete.

**Downstream consumers.**

| Task | Reads | Purpose |
| :-- | :-- | :-- |
| T22 | Page B §4 (sketch), §5 (determinism) | Implement `self.adversary` dispatch in `src/nodes/` |
| T51–T53 | Page A §§3–7 (catalog), Page B §2 (intensity), §3 (effect schema) | Generate `(adversary_id, protocol_id, f)` experiment triples |
| T55 | Page A §§3–7 invariant columns | Implement safety/liveness invariant detectors |
| T40 | Page B §3 effect schema | Finalise CSV column set |

**Out of this spec's terminal state.** No code is written. No wiki page
is written. The next action is `superpowers:writing-plans` producing the
implementation plan that then drives the wiki page write.
