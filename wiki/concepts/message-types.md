# Message Types

Design contract for the wire-level message catalog in the thesis
simulator. Fills the `type` and `payload` slots left opaque by
[[concepts/node-model]] §6 and [[concepts/network-model]] §3.1, for
the four-protocol scope (PBFT / Casper FFG / Snowman / Narwhal+Tusk).
Consumed by [[concepts/simulation-design]] (T17), the W4
implementations in `src/nodes/` (T22) and `src/network/` (T23),
the message-count side of [[concepts/evaluation-metrics]] (T9.1) and
[[concepts/metric-reconciliation]] (the `{mempool,consensus}_{msgs,
bytes}_per_acu` columns), and the W10 adversarial experiments (T51–
T55) via [[concepts/adversary-model]] (T18).

This page covers the **catalog** — the per-protocol enumeration of
`type` tags, recipient discipline (unicast vs broadcast), payload
schemas, approximate byte sizes, and the FSM transitions each kind
drives. Out of scope and deferred to siblings: envelope routing and
delivery semantics (T15); event-loop scheduling (T17); adversarial
modification, suppression, or fabrication of messages (T18 —
modifications attach at [[concepts/node-model]] §9, not here);
encoding format (the simulator passes Python objects, not bytes).
Sizes are declared anyway so the metric layer can populate
`{mempool,consensus}_bytes_per_acu` and so the
[[concepts/network-model]] §8 bandwidth revision lands non-breaking.

## 1. Framing and scope

The simulator has **no external client**. Transactions enter at the
current proposer's local mempool, sourced by the experiment harness
(T19, T27). Per-protocol latency
([[concepts/evaluation-metrics]] §Latency,
[[concepts/metric-reconciliation]] §Latency) is therefore measured
from mempool insertion to inclusion in a committed-or-finalised
block, not from a wire request. Classical PBFT's `CLIENT-REQUEST`
and `REPLY` are accordingly **not in the catalog**. Adding them
later would be a §8 revision and would require
[[concepts/evaluation-metrics]] to grow a user-perceived-latency
definition; the v1 catalog avoids both.

The shared `Message` envelope from [[concepts/node-model]] §6 is the
fixed boundary every row in this page populates:

```
Message := {
  src:     NodeId,
  dst:     NodeId | "broadcast",
  type:    str,        # one of the §3–§6 tag strings
  payload: object,     # the per-row schema below
  t_sent:  SimTime,
}
```

Each catalog row fixes `type` to a literal tag string and `payload`
to a per-`(protocol, type)` field schema. `src`, `dst`, and `t_sent`
are envelope-level and **never duplicated in payload**.

## 2. Cross-protocol message groups

The four protocols have genuinely non-uniform message vocabularies.
The following groups are a **conceptual organising scheme** for this
page; no protocol implements all of them, and no two implement them
identically. The grouping serves cross-protocol comparison in
Chapter 4, not catalog structure.

| Group | Role | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **Propose** | Introduce a candidate value | `PRE-PREPARE` | `BLOCK-PROPOSAL` | `BLOCK-ANNOUNCEMENT` | `HEADER` |
| **Vote** | Express support / availability | `PREPARE` | `ATTESTATION` (FFG vote + head vote) | `QUERY-RESPONSE` | `HEADER-VOTE` |
| **Commit / Finalise** | Carry the threshold acknowledgement | `COMMIT` | — (finalisation is derived from accumulated `ATTESTATION` stake; no separate message) | — (acceptance is derived from local counter; no separate message) | `CERTIFICATE` |
| **Query** | Pull state from a peer | — | — | `QUERY` | — |
| **Recovery / Evidence** | Restore liveness or punish misbehaviour | `VIEW-CHANGE`, `NEW-VIEW` | `SLASHING-EVIDENCE` | — | — |

The empty cells are structural, not gaps. PBFT carries no separate
query because every quorum step is a broadcast; Casper FFG and
Snowman have no separate commit message because the finality
predicate is locally evaluable from accumulated `ATTESTATION` /
`QUERY-RESPONSE` cardinality; Snowman has no recovery message
because there is no leader to fail. Tusk's anchor-commit step adds
**zero new messages** — the total order is derived from existing
DAG parent references ([[concepts/metric-reconciliation]] §Narwhal
mempool-consensus message split).

Convention: where a `type` group has no entry for a protocol, that
combination is unreachable, not a configuration error. The
`Network` (T15) only routes envelopes whose `type` is in this
catalog; an unknown `type` aborts the run, per
[[concepts/network-model]] §3.2.

## 3. PBFT

PBFT round structure is the three-phase commit from
[[algorithms/pbft#three-phase-commit]], driven inside a single view
by the elected primary, plus the liveness-recovery view-change
mechanism from [[algorithms/pbft#view-change]]. The catalog covers
both; classical PBFT is the simulator target, so HotStuff's
threshold-signature variants are not enumerated.

| `type` | Sender → Recipients | Payload fields | Size (bytes) | FSM transition ([[concepts/node-model]] §4) | Metric column |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `PRE-PREPARE` | primary → broadcast | `view, seq, request_digest, request_payload` | `8 + 8 + 32 + |req|` | `(view, seq)`: `idle → pre_prepared` on recipient | `consensus_msgs_per_acu` |
| `PREPARE` | replica → broadcast | `view, seq, request_digest` | `8 + 8 + 32` | `(view, seq)`: `pre_prepared → prepared` on 2f+1 matching | `consensus_msgs_per_acu` |
| `COMMIT` | replica → broadcast | `view, seq, request_digest` | `8 + 8 + 32` | `(view, seq)`: `prepared → committed` on 2f+1 matching | `consensus_msgs_per_acu` |
| `VIEW-CHANGE` | replica → broadcast | `new_view, last_stable_seq, prepared_evidence: list[(view, seq, digest)]` | `8 + 8 + k·48` | cross-instance: sets `view_changing`; freezes per-`(view, seq)` instances | `consensus_msgs_per_acu` |
| `NEW-VIEW` | new primary → broadcast | `new_view, view_change_proofs: list[VIEW-CHANGE.payload], reissued_pre_prepares: list[PRE-PREPARE.payload]` | `8 + (2f+1)·|VIEW-CHANGE| + k·|PRE-PREPARE|` | cross-instance: advances current view; replays prepared-but-not-committed instances | `consensus_msgs_per_acu` |

`request_digest` is the hash of the proposed transaction batch;
`request_payload` is the batch itself, carried only in the
`PRE-PREPARE`. `PREPARE` and `COMMIT` carry the digest alone, so
`2f+1`-quorum collection costs `O(n²)` *small* messages, not
payload-bearing ones — the asymmetry that makes the size column
load-bearing for Chapter 4's bandwidth-vs-message-count discussion.

`VIEW-CHANGE` evidence cardinality `k` is the number of prepared
instances at or above the last stable checkpoint; the simulator
caps it at the configured high-water mark per
[[algorithms/pbft#view-change]] cost analysis. `NEW-VIEW` is the
single message that justifies the family's `O(n³)` worst-case view
change: a quadratic-sized payload broadcast to `n` recipients.

## 4. Casper FFG

Casper FFG round structure is the two-round justify-then-finalise
gadget from [[algorithms/pos#two-round-finalisation]] operating on
top of a chain produced by the block-proposal layer. Per
[[algorithms/pos]] §Simulator mapping the simulator keeps LMD-GHOST
fork choice in scope at minimum fidelity (delay-induced reorgs),
which forces the `ATTESTATION` payload to carry **both** the FFG
`<source, target>` vote and the LMD-GHOST head vote.

| `type` | Sender → Recipients | Payload fields | Size (bytes) | FSM transition | Metric column |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `BLOCK-PROPOSAL` | slot proposer → broadcast | `slot, epoch, parent_hash, block_hash, transactions, proposer_idx, proposer_sig` | `8 + 8 + 32 + 32 + n_tx·|tx| + 4 + 64` | feeds the LMD-GHOST view; no direct FFG instance transition | `consensus_msgs_per_acu` |
| `ATTESTATION` | attester → broadcast | `slot, epoch, head_vote_hash, ffg_source: (epoch, hash), ffg_target: (epoch, hash), attester_idx, signature` | `8 + 8 + 32 + 40 + 40 + 4 + 64` | `epoch`: `unjustified → justified` once stake-weighted FFG votes for `<S, T>` ≥ 2/3; `justified → finalised` on the next supermajority link from `T` | `consensus_msgs_per_acu` |
| `SLASHING-EVIDENCE` | observer → broadcast | `offender_idx, offence_kind ∈ {double_vote, surround_vote}, vote_pair: (ATTESTATION.payload, ATTESTATION.payload)` | `4 + 1 + 2·|ATTESTATION|` | triggers `slashed` halt ([[concepts/node-model]] §3) for `offender_idx` once verified | `consensus_msgs_per_acu` |

`ATTESTATION` byte size assumes per-validator signatures
(Ed25519-class, 64 B). Production Ethereum BLS-aggregates committee
attestations into a single ~96 B object; the simulator measures
per-validator counts for instrumentation parity with the other
three protocols and notes aggregation cost as a separate fixed
overhead per committee, per [[algorithms/pos]] §Communication
complexity. The aggregation question lands in §8 below.

`SLASHING-EVIDENCE` is a first-class wire message in this
simulator. Detection is local — any node that observes two
slashable `ATTESTATION`s from the same offender constructs the
pair — but publication is immediate broadcast, not bundled into a
later `BLOCK-PROPOSAL`. This decouples slashing latency from
proposer scheduling, which matters for the economic-cost-of-attack
metric on [[algorithms/pos]] §Behaviour under adversarial
conditions ("`α/3` of stake burned") and for the T53 equivocation
experiment. Bundling-vs-broadcast is recorded as a §8 revision
trigger in case T18 wants to model an evidence-suppressing
adversary that prefers the bundled production semantics.

## 5. Snowman

Snowman round structure is the subsampled poll from
[[algorithms/avalanche#snowman--linearised-production]] and
[[algorithms/avalanche#sampling-round]]. Each validator repeatedly
samples `K` peers, queries their preference for an outstanding
block, and accumulates a confidence counter against `α_p` /
`α_c` / `β` thresholds.

| `type` | Sender → Recipients | Payload fields | Size (bytes) | FSM transition | Metric column |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `BLOCK-ANNOUNCEMENT` | proposer → broadcast | `block_id, parent_id, transactions, proposer_idx` | `32 + 32 + n_tx·|tx| + 4` | introduces `block_id` instance in `polling` state on recipient | `consensus_msgs_per_acu` |
| `QUERY` | poller → unicast (one sampled peer per call; `K` calls per round) | `request_id, block_id` | `8 + 32` | no remote state change on send | `consensus_msgs_per_acu` |
| `QUERY-RESPONSE` | sampled peer → unicast (poller) | `request_id, preferred_block_id` | `8 + 32` | `block_id`: increments local counter on `≥ α_c` agreeing of `K` responses; on `counter ≥ β` → `polling → accepted` | `consensus_msgs_per_acu` |

`BLOCK-ANNOUNCEMENT` is modelled as a single broadcast on
block emission. Real Snowman distributes new blocks via gossip
rounds; gossip fidelity is below this simulator's modelling level
and is flagged as a §8 revision target. The single-broadcast
abstraction does not affect the dominant `O(K·β)` message cost of
the protocol (which lives in the query / response loop, independent
of `n`), so the simplification is non-load-bearing for the
performance comparison in Chapter 4.

`QUERY` and `QUERY-RESPONSE` are unicast — Snowman's whole point is
that no message touches every validator. The simulator therefore
uses `node.send` (not `node.broadcast`) for both. The
`request_id` field threads each `QUERY-RESPONSE` back to the
specific `QUERY` it answers; without it the validator cannot
distinguish responses from concurrent polls on the same `block_id`.

## 6. Narwhal+Tusk

Narwhal round structure is the DAG mempool from
[[algorithms/dag-based#narwhal--the-dag-mempool]]; Tusk anchor
commit is the consensus layer from
[[algorithms/dag-based#tusk-and-bullshark--zero-message-ordering]]
and adds **zero** new wire messages — the entire catalog below is
the mempool layer.

| `type` | Sender → Recipients | Payload fields | Size (bytes) | FSM transition | Metric column |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `HEADER` | validator → broadcast | `round, validator_idx, parent_certs: list[CertId], transactions, proposer_sig` | `8 + 4 + (2f+1)·36 + n_tx·|tx| + 64` | `(round, validator)`: `— → proposing` for the proposer; reference candidate on recipient | `mempool_msgs_per_acu` |
| `HEADER-VOTE` | recipient of `HEADER` → unicast (proposer) | `round, header_hash, voter_idx, voter_sig` | `8 + 32 + 4 + 64` | proposer's `(round, validator)`: `proposing → certified` on 2f+1 matching | `mempool_msgs_per_acu` |
| `CERTIFICATE` | proposer (after 2f+1 votes) → broadcast | `round, validator_idx, header_hash, signatures: list[Sig]` | `8 + 4 + 32 + (2f+1)·64` | observers' `(round, validator)`: `— → certified`; eligible parent for round `r+1` `HEADER`s | `mempool_msgs_per_acu` |

`CertId` is `(round, validator_idx)`; a list of `2f+1` of them is
the parent-reference quota Narwhal enforces per
[[algorithms/dag-based#narwhal--the-dag-mempool]].

Anchor commit at every `r`-th round, per
[[algorithms/dag-based#tusk-and-bullshark--zero-message-ordering]],
is **not** a wire message. The simulator triggers it as a local
predicate over the validator's DAG: if `≥ 2f+1` certificates in
round `r·k+1` reference the anchor at round `r·k`, the validator
flips the anchor's FSM `nominated → committed` and emits the
`decided` event ([[concepts/node-model]] §4). No `Message`
envelope is constructed; no `Network` traffic results. This is the
mechanism behind the `consensus_msgs_per_acu = 0` row in
[[concepts/metric-reconciliation]] §Narwhal mempool-consensus
message split.

The `CERTIFICATE` broadcast is **explicit** in this catalog: the
proposer re-broadcasts the header hash plus the aggregated
`2f+1` signatures so that validators which missed the original
`HEADER` can still treat the certificate as an eligible parent in
round `r+1`. Some production Narwhal variants make this implicit
(the certificate is "discovered" from the next round's parent-
references) and Mysticeti elides the certification step entirely
([[algorithms/dag-based]] §Mysticeti). The explicit-broadcast
choice is recorded as a §8 revision trigger.

## 7. Size accounting

The byte sizes in §3–§6 use the following fixed component widths.
The numbers are an honest order-of-magnitude budget for
`{mempool,consensus}_bytes_per_acu`; they are not declared as
production-realistic and are not consumed by the v1
[[concepts/network-model]] latency-only delivery model.

| Component | Width (bytes) | Notes |
| :-- | :-- | :-- |
| `NodeId`, validator index | 4 | 32-bit integer per [[concepts/node-model]] §2 |
| Slot, epoch, view, seq, round | 8 | 64-bit integer |
| Hash digest (block, request, header) | 32 | SHA-256 / Keccak-256 width |
| Signature (per-validator) | 64 | Ed25519-class |
| BLS aggregate signature | 96 | One per aggregated set, regardless of size |
| Transaction | `|tx|` | Variable; experiment-configured (T19) |

Message-count accounting follows the wire-level convention from
[[concepts/network-model]] §4: one `broadcast` call counts as
`|active validator set|` deliveries, each a distinct contribution
to `{mempool,consensus}_msgs_per_acu`. The per-protocol totals in
[[concepts/metric-reconciliation]] §Narwhal mempool-consensus
message split are derivable from this catalog by summing each
row's per-block expected count over the protocol's catalog set.

`consensus_msgs_per_acu` collects every row except the three
Narwhal+Tusk rows (which go to `mempool_msgs_per_acu`); PBFT,
Casper FFG, and Snowman put zero into `mempool_msgs_per_acu` per
the §3.3 metric convention. `consensus_bytes_per_acu` and
`mempool_bytes_per_acu` follow the same split, weighted by the
size column.

## 8. Reference sketch — payload dataclasses (illustrative, non-binding)

Per the W3 design-contract style, this sketch is **not a
specification**. T22 / T23 may diverge; divergences land as
`## Revisions` entries per `docs/wiki-spec.md` § Revisions rule.
The shared `Message` envelope is declared on
[[concepts/node-model]] §6 and is not redeclared here.

```python
# Reference sketch — illustrative, non-binding.
# Implementation (T22, T23) may diverge; document via §9 + wiki-spec §revisions-rule.

from dataclasses import dataclass
from enum import Enum

# --- PBFT (§3) ---
@dataclass
class PrePreparePayload:  view: int; seq: int; request_digest: bytes; request: list
@dataclass
class PreparePayload:     view: int; seq: int; request_digest: bytes
@dataclass
class CommitPayload:      view: int; seq: int; request_digest: bytes
@dataclass
class ViewChangePayload:  new_view: int; last_stable_seq: int; prepared: list[tuple[int, int, bytes]]
@dataclass
class NewViewPayload:     new_view: int; vc_proofs: list[ViewChangePayload]; reissued: list[PrePreparePayload]

# --- Casper FFG (§4) ---
@dataclass
class FFGVote:            source_epoch: int; source_hash: bytes; target_epoch: int; target_hash: bytes
@dataclass
class BlockProposalPayload:  slot: int; epoch: int; parent_hash: bytes; block_hash: bytes; \
                             transactions: list; proposer_idx: int; proposer_sig: bytes
@dataclass
class AttestationPayload:    slot: int; epoch: int; head_vote_hash: bytes; ffg: FFGVote; \
                             attester_idx: int; signature: bytes
class OffenceKind(Enum):  DOUBLE_VOTE = 0; SURROUND_VOTE = 1
@dataclass
class SlashingEvidencePayload:  offender_idx: int; offence: OffenceKind; \
                                vote_pair: tuple[AttestationPayload, AttestationPayload]

# --- Snowman (§5) ---
@dataclass
class BlockAnnouncementPayload:  block_id: bytes; parent_id: bytes; transactions: list; proposer_idx: int
@dataclass
class QueryPayload:           request_id: int; block_id: bytes
@dataclass
class QueryResponsePayload:   request_id: int; preferred_block_id: bytes

# --- Narwhal+Tusk (§6) ---
CertId = tuple[int, int]  # (round, validator_idx)
@dataclass
class HeaderPayload:      round: int; validator_idx: int; parent_certs: list[CertId]; \
                          transactions: list; proposer_sig: bytes
@dataclass
class HeaderVotePayload:  round: int; header_hash: bytes; voter_idx: int; voter_sig: bytes
@dataclass
class CertificatePayload: round: int; validator_idx: int; header_hash: bytes; signatures: list[bytes]
```

Serialisation, signature verification, and adversary-dispatch
wrappers are bounded by other pages ([[concepts/network-model]] §3.1;
[[concepts/adversary-model]] T18; T22 for verification cost).

## 9. Open to revision

The catalog above is precise but not final. Items below are
expected fit issues; any change beyond a typo lands as a
`## Revisions` entry per `docs/wiki-spec.md` § Revisions rule.

- **Client-driven messages** (§1). v1 excludes `CLIENT-REQUEST` /
  `REPLY`. A user-perceived-latency RQ would grow this row in §3
  and a matching definition in [[concepts/evaluation-metrics]].
- **BLS aggregation reporting** (§4, §7). `ATTESTATION` size is
  declared per-validator (64 B); production aggregates a
  committee to ~96 B. If T34 / T35 finds aggregation dominates
  baseline plots, §7 grows an aggregated-attestation mode and the
  metric layer disambiguates "1 aggregated" vs "n per-validator"
  in `consensus_msgs_per_acu`.
- **Snowman gossip granularity** (§5). The single-broadcast
  abstraction may need explicit gossip-round modelling under T38;
  §5 would grow a `BLOCK-GOSSIP` row.
- **Narwhal `CERTIFICATE` explicitness** (§6). v1 declares it as
  an explicit broadcast. Production variants and Mysticeti make
  it implicit; T38 may drop the row, reducing
  `mempool_msgs_per_acu` by `r·n²`.
- **Narwhal worker / batch decomposition** (§6). If T38 separates
  workers per [[concepts/node-model]] §11, §6 grows
  `BATCH-REQUEST` / `BATCH-RESPONSE` and `HEADER.transactions`
  becomes `batch_refs`.
- **`SLASHING-EVIDENCE` bundling** (§4). v1 declares it as a
  distinct broadcast. T18 may want an evidence-suppressing
  adversary or a bundled-publication honest variant for
  Ethereum-fidelity studies; the row would gain an optional
  `BLOCK-PROPOSAL.slashing_evidence` field as a configuration
  toggle rather than spawn a new type.
- **`VIEW-CHANGE` evidence size cap** (§3). `prepared_evidence`
  cardinality is capped at the high-water mark. T29 may need a
  stricter cap; parameterisation would land in
  [[concepts/experiment-matrix]] (T19).

## 10. Sources

Design contract; no primary-literature citations. Mechanism
semantics are deferred to the algorithm pages, which carry the
bibliography.

**Inbound (existing wiki pages):**

- [[concepts/node-model]] (T14) — §6 envelope, §4 FSM transitions,
  §9 adversary boundary.
- [[concepts/network-model]] (T15) — §3.1 envelope, §4
  broadcast-as-`n`-unicasts convention (§7 above).
- [[concepts/evaluation-metrics]] and [[concepts/metric-reconciliation]]
  (T9.1) — per-protocol `{mempool,consensus}_{msgs,bytes}_per_acu`
  columns that §3–§6 sum to.
- [[algorithms/pbft]], [[algorithms/pos]], [[algorithms/avalanche]],
  [[algorithms/dag-based]] — per-protocol round structure consumed
  by §3, §4, §5, §6 respectively.

**Forward references (sibling pages, not yet authored):**

- [[concepts/simulation-design]] (T17) — routes envelopes declared
  here.
- [[concepts/adversary-model]] (T18) — modifies / suppresses /
  fabricates messages via [[concepts/node-model]] §9.
- [[concepts/experiment-matrix]] (T19) — `|tx|`, `K`, `r`,
  view-change cap parameterisation feeding the size column.
- [[concepts/output-format]] (T40) — CSV schema consuming the
  per-row metric tag.

## Revisions

- **2026-05-21 (T29).** `VIEW-CHANGE` evidence is a **4-tuple**, not the
  3-tuple declared in §3 and the §8 sketch. The T29 implementation
  (`src/pbft/messages.py`) carries `prepared` as
  `list[(view, seq, request_digest, request_payload)]` — the request
  payload is included so the new primary can reissue a valid `PRE-PREPARE`
  (which must satisfy the digest-integrity rule) for an instance it never
  personally prepared (T29 design spec Decision E). The §3 size column
  `8 + 8 + k·48` therefore understates the payload by `k·|req|`.
- **2026-05-21 (T29).** §9's "VIEW-CHANGE evidence size cap" item
  anticipated "T29 may need a stricter cap". T29 applies **no cap**: it
  drops the checkpoint protocol entirely (T29 design spec Decision D), so
  `last_stable_seq` is vestigial — fixed at `-1` — and the evidence is
  *every* instance the replica holds at state ≥ `PREPARED`. A bounded cap
  is deferred to a future task that models checkpointing.
