# Adversary Model

## 1. Framing and scope

Design contract for the catalog of adversarial behaviours the simulator
admits across the four-protocol scope (PBFT, Casper FFG, Snowman,
Narwhal+Tusk). This page is the **catalog** — generic capability ×
protocol matrix (§§2–6) and protocol-specific attack surfaces (§7).
Runtime obligations (intensity normalization, effect schema,
`AdversaryProfile` reference sketch, T27 determinism) are in
[[concepts/adversary-model-runtime]]. Split per `docs/wiki-spec.md`
§ Page size; precedent: [[concepts/network-model]] /
[[concepts/network-model-phases]], [[concepts/simulation-design]] /
[[concepts/simulation-design-runtime]].

The catalog is organised in two layers. **Layer one** — generic
capability × protocol matrix: `delay-emission`, `withhold-participation`,
`equivocate-vote`, `disrupt-leader`, bound per-protocol with one
structural `N/A` and one noted reduction. **Layer two** —
protocol-specific surface: three attacks each rooted in a property only
one family exhibits. The catalog is **static-only**: an
`AdversaryProfile` is data, not behaviour; kind, intensity, node set,
and per-kind config are fixed at sim-start. Matches the static half of
[[concepts/fault-model]] and pins the determinism contract in
[[concepts/adversary-model-runtime]] §5. Intensity is denominated in
each protocol's **natural fault-threshold unit**: PBFT and Narwhal+Tusk
in replicas; Casper FFG in stake; Snowman in validators (full mapping
in [[concepts/adversary-model-runtime]] §2). Attachment is owned by
[[concepts/node-model#adversary-attachment]] (`self.adversary` slot +
per-protocol FSM touchpoint matrix); this page owns binding semantics
per cell. Effect columns reuse [[concepts/evaluation-metrics]]. Total
surface: **18 valid `(adversary_id, protocol_id)` pairs** = (4
capabilities × 4 protocols − 1 structural `N/A`) + 3 protocol-specific
surfaces. Of these, the Week-10 experiment tasks T51–T53 exercise the
**12** generic-capability pairs under §§3–5 (`delay-emission`,
`withhold-participation`, `equivocate-vote`); the 6 pairs under §6 and
§7 are catalogued design space with no experiment task (human scope
decision 2026-05-18 — see §8 Revisions and [[concepts/experiment-matrix]]
§8).

## 2. Generic capability × protocol matrix

The four generic capabilities and their per-protocol bindings. Rows are
protocol-agnostic capability classes; columns are the four protocols in
scope. Cells carry a terse mechanism phrase; the §§3–6 sections below
expand each row with intensity, S/L classification, invariant, and
source.

| Capability | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :-- | :-- | :-- | :-- | :-- |
| **delay-emission** | gate `PREPARE` / `COMMIT` broadcast | gate attestation broadcast | gate `QUERY-RESPONSE` send | gate certificate broadcast |
| **withhold-participation** | silent non-participation | non-participation; ≥1/3 stalls finalisation | skip `QUERY-RESPONSE` | skip certificate broadcast |
| **equivocate-vote** | conflicting `PRE-PREPARE` to disjoint subsets | double-vote / surround-vote (slashable) | reduces to "lying responder" (see §5) | distinct headers to disjoint peers |
| **disrupt-leader** | as primary: slow / refuse `PRE-PREPARE` | as slot proposer: refuse or equivocate | **N/A** — no leader role (see §6) | as anchor leader: withhold or refuse to reference anchor |

Two asymmetric cells are first-class findings, not gaps:

- **Snowman × `disrupt-leader` is structurally `N/A`** because Snowman
  has no leader role ([[concepts/node-model]] §5). Sampling is
  leaderless. The asymmetry is the comparative claim.
- **Snowman × `equivocate-vote` reduces to "lying responder"** because
  Snowman's vote-counting has no inter-message intersection step; the
  protocol cannot distinguish equivocation from selective response
  ([[concepts/node-model]] §9 ll. 470–473). The reduction is the
  comparative claim.

This matrix is the Chapter 4 comparison surface. Asymmetric cells encode
structural property differences between the four families (Snowman's
leaderlessness; Snowman's lack of message-intersection in vote-counting).
[[concepts/node-model]] §9 owns the *attachment surface* (which `Node`
method each capability gates); §§3–6 below own the *binding semantics*
(mechanism, intensity range, safety/liveness classification, invariant,
source).

## 3. delay-emission

Adversary gates outbound emissions past the protocol's timing tolerance.
Liveness attack class; safety is unaffected in all four bindings.

| Protocol | Mechanism | Intensity range | S/L | Invariant checked | Source |
| :-- | :-- | :-- | :-- | :-- | :-- |
| PBFT | gate `PREPARE` / `COMMIT` broadcast past view-change timeout | f ∈ [0, 0.33] of n replicas | L | view-change rate ≤ baseline + 3σ | [4] |
| Casper FFG | gate attestation broadcast past slot boundary | f ∈ [0, 0.33] of stake | L | finality lag ≤ 2 epochs from honest baseline | [7] |
| Snowman | gate `QUERY-RESPONSE` `send` past poll deadline | f ∈ [0, 0.33] of validators | L | accept_time p95 ≤ 5× honest baseline | [9] |
| Narwhal+Tusk | gate certificate broadcast past round boundary | f ∈ [0, 0.33] of n replicas | L | throughput ≥ (1 − f) · honest baseline | [11] |

Near the α-threshold, Snowman's preference can oscillate without
accepting: a delayed `QUERY-RESPONSE` arriving after the poll deadline
counts as a tail "don't-know" reply at the asynchrony boundary per
[[algorithms/avalanche#behaviour-under-adversarial-conditions]], not as
a vote for either colour. PBFT operationalises its liveness invariant as
the **view-change rate**: forced delay either fits inside the
view-change timeout (no effect) or trips a view change (observable). For
Narwhal+Tusk the degradation is throughput-proportional: round
formation absorbs the attack continuously until f approaches 1/3, where
certificate progress stalls per
[[algorithms/dag-based#behaviour-under-adversarial-conditions]].

## 4. withhold-participation

Adversary skips its participation step entirely rather than delaying it.
Same liveness class as §3 but with a different operational signature
(skip vs slow), and an explicit `halted{crashed}` lifecycle encoding per
[[concepts/node-model#halt-reasons]].

| Protocol | Mechanism | Intensity range | S/L | Invariant checked | Source |
| :-- | :-- | :-- | :-- | :-- | :-- |
| PBFT | silent abstain from `PREPARE` / `COMMIT`; or `halted{crashed}` | f ∈ [0, 0.33] of n replicas | L | progress per view ≥ baseline · (1 − f) | [4] |
| Casper FFG | skip attestation; or `halted{crashed}` | f ∈ [0, 0.33] of stake | L | finality lag ≤ 2 epochs while f < 1/3; finalisation stalls at f ≥ 1/3 | [7] |
| Snowman | skip `QUERY-RESPONSE`; or `halted{crashed}` | f ∈ [0, 0.33] of validators | L | accept rate ≥ (1 − f) · honest baseline | [9] |
| Narwhal+Tusk | skip certificate broadcast; or `halted{crashed}` | f ∈ [0, 0.33] of n replicas | L | throughput ≥ (1 − f) · honest baseline | [11] |

A `halted{crashed}` lifecycle entry distinguishes a permanent absence
from a transient skip; both are valid mechanism choices, and both
attach through the same outbound-API gating point per
[[concepts/node-model#adversary-attachment]]. The skip-vs-slow
distinction against §3 is operational: §3 emissions arrive late,
§4 emissions never arrive. Casper's ≥1/3-stake finalisation-stall
threshold is sharp per
[[algorithms/pos#behaviour-under-adversarial-conditions]]: below it the
invariant tracks honest baseline, at it finalisation stops. Narwhal's
degradation is throughput-proportional per
[[algorithms/dag-based#behaviour-under-adversarial-conditions]] — the
same proportional shape as §3 but driven by missing rather than late
inputs.

## 5. equivocate-vote

Adversary signs two incompatible messages where the protocol expects at
most one. Mechanism varies sharply across families because each
family's vote-counting machinery is structurally different.

| Protocol | Mechanism | Intensity range | S/L | Invariant checked | Source |
| :-- | :-- | :-- | :-- | :-- | :-- |
| PBFT | as primary: emit conflicting `PRE-PREPARE` to disjoint subsets | f ∈ [0, 0.33] of n; primary slot only | L (safety holds; triggers view change) | no two-honest commit conflict at same (view, seq) | [4] |
| Casper FFG | double-vote or surround-vote at attestation | f ∈ [0, 0.33] of stake | S above threshold; L below | accountable-safety: any two-conflicting-finalised → ≥1/3 stake slashable | [7] |
| Snowman | *reduces to* "lying responder" — return non-preference colour | f ∈ [0, 0.33] of validators | L (no fork-induction surface) | empirical safety-violation rate ≤ (1 − α_c/K)^β | [9] |
| Narwhal+Tusk | broadcast distinct headers to disjoint peer subsets | f ∈ [0, 0.33] of n replicas | L (blocked at cert step) | no conflicting header reaches 2f+1 signatures | [11] |

The Snowman row's *reduction* — not a fresh binding — falls out of the
absent inter-message intersection step: Snowman never compares two
messages from one validator in a quorum-collection round, so signing
incompatible colours is mechanically indistinguishable from selective
response (cf. [[concepts/node-model]] §9 ll. 470–473); the §5 Snowman
binding and the §4 Snowman binding therefore overlap mechanically while
differing in *intent*. Casper's row is the only one with an economic
safety-cost budget: a successful safety violation costs ~α/3 of stake
destroyed via slashing per [[algorithms/pos#accountable-safety]]. The
Narwhal row blocks at the certificate step: the `2f+1`-signature
requirement prevents any conflicting header from reaching certificate
status per [[algorithms/dag-based#safety-argument]]. PBFT routes the
attack through view-change-as-detector per
[[algorithms/pbft#behaviour-under-adversarial-conditions]]: equivocation
forces a view change rather than corrupting safety, so the operational
invariant is "view-change frequency tracks equivocator rate."

## 6. disrupt-leader

Adversary holds a leader slot and refuses its leader-specific duty,
either silently or via equivocation. Snowman's row is `N/A` because
sampling is leaderless.

| Protocol | Mechanism | Intensity range | S/L | Invariant checked | Source |
| :-- | :-- | :-- | :-- | :-- | :-- |
| PBFT | as primary: slow / refuse `PRE-PREPARE` to force view change | f ∈ [0, 0.33] of n; primary slot only | L | view-change rate tracks adversary fraction | [4] |
| Casper FFG | as slot proposer: refuse block production; or propose conflicting blocks (slashable) | f ∈ [0, 0.33] of stake; proposer slot only | L (slashable in equivocation case) | block proposal failure rate tracks adversary fraction | [7] |
| Snowman | **N/A** — no leader role | — | — | — | — |
| Narwhal+Tusk | as anchor leader: withhold or refuse to reference the anchor | f ∈ [0, 0.33] of n replicas; anchor slot only | L | anchor-commit lag bounded by 2× anchor period | [11] |

Snowman's `N/A` reflects a structural property: sampling is leaderless
per [[concepts/node-model]] §5; there is no per-slot proposer role to
hold or to refuse. The `N/A` is Snowman-specific and not
"leaderless-protocols-in-general" — the Narwhal+Tusk row carries an
anchor-leader binding, and the Bullshark / Mysticeti variants out of
scope per [[algorithms/dag-based#family-scope]] also have anchor
leaders; the scope wall is family membership, flagged for forward
compatibility if it ever widens. Casper's proposer-equivocation case
overlaps with §5 mechanically — proposer equivocation is also
slashable — while §7.3 carries the explicit slashing-payload
formulation.

## 7. Protocol-specific surfaces

Three adversaries are structurally unique to one protocol because they
exploit a property the other three families do not share (sampled
quorum; two-layer availability/ordering split; on-chain slashing). They
live here rather than in the §2 matrix because the matrix exists for
cross-protocol comparison; single-protocol attacks would be 3-`N/A`
rows.

### 7.1 Snowman colluding sub-sampler

**Action.** Multiple `Node`s' adversary profiles coordinate
`QUERY-RESPONSE` colours to bias `α_c` counts in honest validators'
samples per
[[algorithms/avalanche#behaviour-under-adversarial-conditions]]
(sample-partitioning).

**Victim protocol.** Snowman only.
**Intensity range.** f ∈ [0, 0.33] of validators in the colluding pool.
**S/L.** Safety (probabilistic).
**Invariant checked.** Empirical safety-violation rate ≤ theoretical
bound `(1 − α_c/K)^β` from [[algorithms/avalanche#probabilistic-safety]].
**Source.** [9].

**Structural uniqueness.** Snowman is the only family member that draws
a random sub-sample per query; the other three families operate over
fixed quorums (PBFT replica set, Casper validator set per epoch,
Narwhal committee). Coordination is "shared parameters + derived RNG
seed" per
[[concepts/adversary-model-runtime#5-determinism-interaction-with-t27]].

### 7.2 Narwhal+Tusk data-availability withholding

**Action.** Adversary worker certifies the header (gathers `2f+1`
signatures) but refuses to serve batch contents on subsequent `send`
requests per
[[algorithms/dag-based#behaviour-under-adversarial-conditions]] and
[[concepts/node-model]] §9 ll. 483–485.

**Victim protocol.** Narwhal+Tusk only.
**Intensity range.** f ∈ [0, 0.33] of n replicas.
**S/L.** Liveness (consensus stalls when missing batches block ordering).
**Invariant checked.** Batch availability rate ≥ honest baseline minus f.
**Source.** [11].

**Structural uniqueness.** Only Narwhal+Tusk separates data
availability from ordering. PBFT, Casper FFG, and Snowman all carry
payload in the consensus messages themselves; there is no
"certify but withhold" gap because there is no distinct availability
layer to attack.

### 7.3 Casper FFG slashable-equivocation refinements

**Action.** Surround vote (`<S₁, T₁>` surrounding own `<S₂, T₂>` with
`S₁ < S₂ < T₂ < T₁`) and double vote (two distinct votes with the same
target epoch), each with an explicit slashing-evidence payload per
[[algorithms/pos#slashing-conditions]].

**Victim protocol.** Casper FFG only.
**Intensity range.** f ∈ [0, 0.33] of stake.
**S/L.** Safety above threshold; cost-bounded.
**Invariant checked.** Successful safety violation → ≥1/3 stake
slashable (accountable-safety theorem per
[[algorithms/pos#accountable-safety]]).
**Source.** [7].

**Structural uniqueness.** Casper is the only family with on-chain
slashing. PBFT equivocation triggers a view change with no economic
penalty; Narwhal equivocation is blocked at certificate formation;
Snowman has no inter-message intersection to detect equivocation
against.

## 8. Revisions

### 2026-05-23 — PBFT view-change-evidence forgery is a deliberate non-capability

The catalog carries no capability that forges a Byzantine replica's
`VIEW-CHANGE` prepared evidence, and no `§7.4` PBFT view-change adversary
is planned. This is a deliberate modeling boundary — the simulator trusts
view-change evidence content (it carries no signatures), so PBFT
within-threshold safety against evidence-forgery is assumed, not
demonstrated. Authoritative statement: [[algorithms/pbft#simulator-mapping]].

### 2026-05-18 — §1 experiment-coverage claim narrowed

§1 previously read "T51–T53 sizes its experiment matrix against this
count" (all 18 pairs). T19 ([[concepts/experiment-matrix]] §8) surfaced
that the Week-10 experiment tasks T51–T53 exercise only the 12
generic-capability pairs under §§3–5; §6 `disrupt-leader` (3 pairs) and
the §7 protocol-specific surfaces (3 pairs) have no experiment task. A
human scope decision (`TASKS.md` § Backlog) resolved the mismatch by
narrowing the coverage claim rather than adding experiment tasks. The
18-pair catalog is **unchanged** — the 6 uncovered pairs remain
documented design space; only the claim that T51–T53 covers all of them
is corrected, here and in §1.

## 9. Sources

Citations `[4]`, `[7]`, `[9]`, `[11]` resolve via
[[concepts/annotated-bibliography]] to:

- [[sources/2026-04-21_castro-liskov-pbft-1999]] (`[4]`)
- [[sources/2026-04-21_buterin-griffith-casper-ffg-2017]] (`[7]`)
- [[sources/2026-04-21_team-rocket-avalanche-2019]] (`[9]`)
- [[sources/2026-04-21_danezis-narwhal-tusk-2022]] (`[11]`)
