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

## 5. Determinism interaction with T27

## 6. Open to revision

## 7. Sources
