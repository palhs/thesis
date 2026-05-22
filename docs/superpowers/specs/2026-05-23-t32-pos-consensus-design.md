# T32 — Simplified Casper FFG Consensus: Design Spec

- **Task:** T32 (Engineer) — Implement simplified PoS-inspired consensus.
- **Branch:** `task/T32-pos-consensus`.
- **Date:** 2026-05-23.
- **Outcome (TASKS.md):** "Validator-based voting; proposer by stake/turn;
  threshold finality." Protocol is Casper FFG (project scope —
  [[algorithms/pos]]).
- **Scope decision (human, 2026-05-23):** full vertical slice — T32
  implements a complete simplified Casper loop with an inline round-robin
  proposer and an inline two-thirds-stake finality rule, so it finalises
  end-to-end and is testable on its own. T33 later extracts `selection.py`
  and adds stake-weighting; T34 extracts `finality.py` and hardens edge
  cases.
- **Fidelity decision (human, 2026-05-23):** Approach 1 — honest-path core
  only. No slashing detection; no LMD-GHOST fork choice. `SLASHING-EVIDENCE`
  handling lands with T18/T53; fork-choice fidelity lands with T46–T50.

This spec is the canonical reference for the T32 implementation plan
(`superpowers:writing-plans`). It consumes the W3 design contracts
[[concepts/node-model]], [[concepts/message-types]] §4,
[[concepts/system-design-protocols]] §3, and the algorithm page
[[algorithms/pos]]. It mirrors the structure of the T28/T29 PBFT specs so
the two protocol implementations stay comparable.

## 1. Scope and non-goals

### In scope

- A `CasperNode(Node)` validator implementing the Casper FFG
  justify→finalise gadget over a chain of slot-proposed blocks.
- Fixed-length epochs of `slots_per_epoch` slots; one block per slot; the
  first block of each epoch is its checkpoint.
- Stake-weighted FFG vote aggregation; a supermajority link forms at
  `≥ 2/3` of total stake.
- The per-epoch FSM `unjustified → justified → finalised` and the mandatory
  `decided` event on finalisation.
- An inline round-robin proposer (`slot mod n`).
- Honest-path error handling: payload-shape guards and validation
  rejections that log-and-drop rather than crash.
- Unit tests, an end-to-end build-verification test, and a
  `wiki/experiments/` baseline page.

### Out of scope (deferred, with the owning task)

- **Stake-weighted proposer selection** and the 100-round fairness check —
  T33 (`src/pos/selection.py`).
- **Finality-rule edge-case hardening** extracted to a dedicated module —
  T34 (`src/pos/finality.py`).
- **Slashing** — double/surround-vote detection, `SLASHING-EVIDENCE`
  broadcast, the `slashed` halt. `OffenceKind` / `SlashingEvidencePayload`
  are not created. Lands with T18 (adversary model) / T53 (equivocation
  experiment).
- **LMD-GHOST fork choice.** The chain is treated as linear with a trivial
  head; delay-induced reorgs are out of scope until T46–T50.
- **The n=4/7/10 correctness sweep and comparison-ready CSV** — T35.
- **Adversary behaviour.** `Node.adversary` is left untouched, exactly as
  T28/T29 left it; T18 fills the slot.

## 2. Package layout — `src/pos/`

Mirrors `src/pbft/`. Five files; `selection.py` and `finality.py` are
deliberately absent (T33/T34 create them).

| File | Role | `src/pbft/` analogue |
| :-- | :-- | :-- |
| `__init__.py` | Package exports (`CasperNode`) | `__init__.py` |
| `messages.py` | Payload dataclasses (§3) | `messages.py` |
| `chain.py` | Block dataclass, block hashing, the linear chain, checkpoint identification, head selection (§4) | `digest.py` |
| `epoch.py` | `EpochState` — the per-epoch FSM instance and FFG aggregation (§5) | `instance.py` |
| `node.py` | `CasperNode(Node)` — slot loop, message handlers, inline proposer + finality wiring (§6–§8) | `node.py` |

## 3. Message payloads — `src/pos/messages.py`

Two payload dataclasses, conforming to [[concepts/message-types]] §4. The
shared `Message` envelope (`src`, `dst`, `type`, `payload`, `t_sent`) is
owned by [[concepts/node-model]] §6 and is not redeclared.

```python
@dataclass(frozen=True)
class FFGVote:
    source_epoch: int
    source_hash: bytes      # checkpoint root of the source epoch
    target_epoch: int
    target_hash: bytes      # checkpoint root of the target epoch

@dataclass(frozen=True)
class BlockProposalPayload:
    slot: int
    epoch: int
    parent_hash: bytes
    block_hash: bytes
    transactions: tuple[bytes, ...]   # stub workload items
    proposer_idx: int

@dataclass(frozen=True)
class AttestationPayload:
    slot: int
    epoch: int
    ffg: FFGVote
    attester_idx: int
    # head_vote_hash is omitted: LMD-GHOST is out of scope (Decision B).
    # message-types.md §4 lists it; its absence is a §15 divergence.
```

`type` tag strings: `"BLOCK-PROPOSAL"`, `"ATTESTATION"` (the literals from
[[concepts/message-types]] §2). `"SLASHING-EVIDENCE"` is not produced or
handled (Decision B).

Per-validator signature fields (`proposer_sig`, `signature`) from the
message-types §4 catalog are **omitted**: the simulator passes Python
objects, not bytes, and performs no signature verification (the catalog's
own §1 notes encoding is out of scope). Their omission is recorded as a
§15 divergence so the byte-size column is not silently contradicted.

## 4. The block chain — `src/pos/chain.py`

The block-proposal layer. Honest-path: a single linear chain.

- **`Block`** — frozen dataclass: `slot`, `epoch`, `parent_hash`,
  `block_hash`, `transactions`, `proposer_idx`. `epoch == slot //
  slots_per_epoch`. A block is a **checkpoint** iff `slot %
  slots_per_epoch == 0`.
- **`block_hash(...)`** — deterministic hash over block contents
  (`hashlib.blake2b` of a canonical field encoding; same primitive family
  as `src/pbft/digest.py`). The genesis block has a fixed sentinel hash.
- **`Chain`** — holds blocks keyed by `block_hash`, the genesis block at
  construction, and a `head` pointer. `add(block)` validates the parent is
  known and links the block; `head` is the block at the greatest slot on
  the known chain (trivial selection — Decision B defers LMD-GHOST).
  `checkpoint(epoch)` returns the checkpoint block of an epoch (the
  ancestor of `head` whose `slot % slots_per_epoch == 0` and whose epoch is
  the queried one).
- **Genesis** is epoch 0's checkpoint and is **justified and finalised by
  construction** (Decision F) — it bootstraps the FFG justify chain.

## 5. Epoch FSM and FFG aggregation — `src/pos/epoch.py`

One `EpochState` instance per **target epoch**; the `CasperNode` holds them
in a table keyed by `epoch`. This is the [[concepts/node-model]] §4 FSM
instance for Casper FFG.

### 5.1 State

```python
class EpochFSM(Enum):
    UNJUSTIFIED = 0
    JUSTIFIED   = 1
    FINALISED   = 2

class EpochState:
    epoch: int
    checkpoint_hash: bytes | None          # known once the checkpoint block arrives
    state: EpochFSM = UNJUSTIFIED
    # FFG votes for this target, grouped by source epoch:
    #   source_epoch -> { attester_idx -> stake }
    links: dict[int, dict[int, float]]
```

`links` records, per source epoch `S`, the stake of every validator that
cast an FFG vote `<S, this.epoch>`. Grouping by `attester_idx` gives the
dedupe guard (Decision I) and lets `link_stake(S)` sum distinct attesters.

### 5.2 Supermajority link

A supermajority link `S → T` exists when
`sum(links[S].values()) >= twothirds(total_stake)`, where
`twothirds(x)` is the smallest stake strictly meeting the `≥ 2/3`
threshold. `total_stake` is the sum of the constructor stake table
(Decision D). The `≥ 2/3` comparison is the inline finality rule; T34
extracts and hardens it.

### 5.3 Transitions

The `CasperNode`, on filing an FFG vote for target `T` with source `S`,
evaluates in order:

1. **Justify `T`.** If `EpochState[T].state == UNJUSTIFIED`, source `S` is
   itself justified, and link `S → T` exists, then `T → JUSTIFIED`. Emit
   `casper_justified`.
2. **Finalise `S`.** A justified epoch `S` is finalised when its direct
   child epoch `S+1` is justified by a link `S → S+1` — i.e. two
   consecutive supermajority links ([[algorithms/pos#two-round-finalisation]]).
   Concretely: when step 1 justifies `T` via link `S → T` and `T == S+1`,
   then if `EpochState[S].state == JUSTIFIED` it transitions
   `S → FINALISED`. Emit `casper_finalised` and the mandatory `decided`
   event (Decision G).

Genesis (epoch 0) is `FINALISED` at construction (Decision F), so it is a
valid justified ancestor for epoch 1's first link.

### 5.4 `decided` payload

On finalisation of epoch `e`, emit via the base `Node`:

```
decided(value=checkpoint_hash_of(e).hex(), instance_id=e, t=t)
```

This matches the [[concepts/node-model]] §4 mapping-table row for Casper
FFG (`value=checkpoint_root, instance_id=epoch`).

## 6. `CasperNode` — lifecycle and the slot loop

`src/pos/node.py`. Subclass of `Node` ([[concepts/node-model]],
`src/nodes/node.py`).

### 6.1 Constructor

```python
def __init__(self, node_id, weight, endpoint, global_seed, *,
             n: int,
             stake_table: dict[int, float],
             slot_duration: float = 1.0,
             slots_per_epoch: int = 4,
             attest_offset: int = ...,        # see Decision J
             workload: list[bytes] | None = None) -> None
```

- `n` — validator count; drives the `slot mod n` proposer rule.
- `stake_table` — `{node_id: stake}` for every validator (Decision D). A
  node knows only its own `Node.weight`; weighting other validators'
  attestations requires the full table. `total_stake = sum(...)`.
  Validated: keys are `range(n)`, every stake finite and non-negative,
  `stake_table[node_id] == weight`.
- `slot_duration`, `slots_per_epoch`, `attest_offset` — timing knobs;
  test-friendly defaults here, real values come from
  [[concepts/experiment-matrix]] via the T41 harness.
- `workload` — optional stub `list[bytes]`; the proposer pops items to fill
  a block's `transactions`. An empty/absent workload yields empty blocks —
  finality is per-checkpoint, not per-transaction, so this does not block
  the protocol.

Constructor validation mirrors `PBFTNode.__init__`: reject `n <= 0`,
`node_id` outside `[0, n)`, non-positive `slot_duration`, non-positive
`slots_per_epoch`. Non-finite `weight` is already rejected by
`Node.__init__` (`src/nodes/node.py:50` — backlog follow-up (a), already
resolved; T32 adds nothing there).

### 6.2 Cross-instance state

`epoch_states: dict[int, EpochState]`; the `Chain`; the highest justified
epoch and highest finalised epoch; `decided_epochs: set[int]` (Decision G).

### 6.3 `_on_start(t)`

Schedule the first slot: `set_timer("slot", slot_duration, 0, t)`.

### 6.4 The slot timer

`_on_timer("slot", slot, t)`:

1. `epoch = slot // slots_per_epoch`.
2. **Propose.** If `_is_proposer(slot)` (Decision E), build a block
   extending `chain.head` carrying up to one popped `workload` item;
   `broadcast("BLOCK-PROPOSAL", ...)`; self-record the block into the local
   chain (Decision C).
3. **Attest.** If `slot` is this epoch's attestation slot
   (`slot % slots_per_epoch == attest_offset`, Decision J), build the FFG
   vote `<highest-justified checkpoint, this epoch's checkpoint>`,
   `broadcast("ATTESTATION", ...)`, and self-record the node's own FFG vote
   (Decision C).
4. **Re-arm.** `set_timer("slot", slot_duration, slot + 1, t)`.

The slot timer fires every slot (proposer rotation); an `ATTESTATION` is
emitted once per epoch (Decision J).

## 7. Message handlers and validation

`_on_message` dispatches on `msg.type`. Each handler first applies an
`isinstance` payload-shape guard and emits `casper_rejected` on failure
(§11) — never crashes. Unknown `msg.type` → `casper_rejected` with reason
`unknown_type`. This is the PBFT log-and-drop discipline
(`src/pbft/node.py` `_handle_*`).

### 7.1 `BLOCK-PROPOSAL`

Validation rules (reject → `casper_rejected`, drop):

1. Payload is a `BlockProposalPayload`.
2. `msg.src == proposer_of(payload.slot)` — sender is the slot's proposer.
3. `payload.epoch == payload.slot // slots_per_epoch` — epoch consistent.
4. `payload.block_hash == block_hash(payload fields)` — hash integrity
   (the §4 analogue of PBFT's digest-integrity Rule 5).

A block whose `parent_hash` is not yet known is **buffered**, not
rejected: the network gives no ordering guarantee, so a child can arrive
before its parent. Buffered blocks are re-examined when a new block lands.
(Honest-path: buffering drains once delivery completes.)

On acceptance: add to `chain`; if the block is a checkpoint, set the
corresponding `EpochState.checkpoint_hash`; emit `casper_block_accepted`.

### 7.2 `ATTESTATION`

Validation rules:

1. Payload is an `AttestationPayload` carrying an `FFGVote`.
2. `0 <= payload.attester_idx < n` — attester in the validator set.
3. `payload.ffg.target_epoch == payload.epoch` — vote epoch consistent.

On acceptance: file the FFG vote into `EpochState[target]` (created lazily
with `setdefault` — Decision H) under
`links[source_epoch][attester_idx] = stake_table[attester_idx]`. If that
attester already has a vote recorded for this target epoch, the later vote
is **ignored** (Decision I) — honest validators attest once per epoch; the
guard also absorbs a duplicated delivery. Then run the §5.3 transition
check.

### 7.3 Self-recording (Decision C)

`Network.broadcast` excludes the sender ([[concepts/network-model]]), so a
node never receives its own `BLOCK-PROPOSAL` or `ATTESTATION`. Each node
therefore records its own block into `chain` and its own FFG vote into the
epoch state directly, at emission time — otherwise its stake never counts
toward the `2/3` threshold and finality tops out short. This is the exact
analogue of PBFT Decision B.

## 8. Proposer selection — inline (T33 boundary)

`_is_proposer(slot)` returns `slot % n == self.id`; `proposer_of(slot)`
returns `slot % n`. Round-robin, fully deterministic, no RNG (Decision E).

This is the **T33 seam**: T33 replaces these two methods with a
stake-weighted selection in `src/pos/selection.py` and adds the 100-round
fairness check. T32 keeps them inline and trivial so the protocol is
exercisable now. Keeping them as two small methods (rather than inlining
the modulo at call sites) makes the T33 extraction a localised change.

## 9. Determinism

Per [[concepts/node-model]] §8 and [[concepts/reproducibility]]: two
`global_seed`-identical runs produce byte-identical event streams.

- The proposer schedule is `slot mod n` — deterministic, no randomness.
- T32 draws no randomness at all: there is no peer sampling, no jitter, no
  randomised timeout. `self.rng` is untouched. (T33's stake-weighted
  selection will introduce a seed-derived schedule; per
  [[concepts/node-model]] §5 that derivation is FSM-level from
  `(global_seed, epoch)`, identical on every node, not `self.rng`.)
- All container iteration that is observable (e.g. choosing source epochs
  to test for links, ordering buffered blocks) uses `sorted(...)`.
- Time arrives only as the `t` parameter; no wallclock read.

## 10. Events

Protocol-specific event-type strings are module-level constants in
`src/pos/node.py` (the PBFT pattern — `PBFT_REJECTED` etc.). The mandatory
`decided` / `halted` strings come from the base `Node` (which imports them
from `event_log/event_types.py`).

| Constant | String | Emitted when |
| :-- | :-- | :-- |
| `CASPER_BLOCK_ACCEPTED` | `casper_block_accepted` | a `BLOCK-PROPOSAL` passes validation and is linked |
| `CASPER_ATTESTED` | `casper_attested` | this node broadcasts its own `ATTESTATION` |
| `CASPER_JUSTIFIED` | `casper_justified` | an epoch transitions to `JUSTIFIED` |
| `CASPER_FINALISED` | `casper_finalised` | an epoch transitions to `FINALISED` |
| `CASPER_REJECTED` | `casper_rejected` | any payload-shape or validation failure |
| (base) | `decided` | epoch finalised (§5.4); once per epoch (Decision G) |
| (base) | `halted` | lifecycle halt — honest-path: only `run_end` |

Event payloads carry enough to reconstruct the run: `casper_justified` /
`casper_finalised` carry `epoch` and `checkpoint_hash`; `casper_rejected`
carries `reason` plus context fields. The exact field set per event is
pinned in the implementation plan.

## 11. Error handling

Honest-path log-and-drop, identical in spirit to T28/T29:

- Every handler opens with an `isinstance` payload guard; a mismatch emits
  `casper_rejected` (reason `malformed_payload`) and returns.
- Validation-rule failures (§7.1, §7.2) emit `casper_rejected` with a
  specific reason and drop the message.
- An unknown `msg.type` emits `casper_rejected` (reason `unknown_type`).
- A halted node drops inbound work — enforced by the base `Node`
  (`on_message` / `on_timer` guard), not re-implemented here.

No exception escapes a handler under any input. This honours the
[[concepts/system-design-protocols]] §3 intent and pre-positions the code
for T18's malformed-message injection without doing T18's work.

## 12. Testing

Per the Engineer role and the standing rule that every implementation task
ships unit + e2e tests as run-success evidence.

### 12.1 Unit tests — `tests/pos/`

Drive `epoch.py` / `chain.py` / `messages.py` directly:

- FFG aggregation crosses the `2/3` threshold at exactly the right stake;
  one unit below threshold does not justify.
- The two-link justify→finalise sequence: epoch `e` finalises only once
  epoch `e+1` is justified by a link from `e`.
- Genesis is justified+finalised at construction.
- Epoch/slot/checkpoint arithmetic (`epoch = slot // slots_per_epoch`;
  checkpoint detection).
- `Chain.add` rejects an unknown-parent block to the buffer; buffered
  blocks drain when the parent arrives.
- Attestation dedupe: a second vote from an already-counted attester does
  not double-count stake.
- Payload-shape guards: a malformed payload yields `casper_rejected`, not
  an exception.
- Non-uniform stake: a validator set with unequal stakes justifies on
  stake, not on head-count.

### 12.2 End-to-end build-verification test

Drive the full Week-3 stack (scheduler + `Network` + `CasperNode`) the way
`tests/integration/` and the T28/T29 e2e tests do:

- n=4 and n=7, all-honest, uniform and non-uniform stake.
- Assert epochs reach `finalised` and `decided` events fire in epoch
  order.
- Assert determinism: two `global_seed`-identical runs produce
  byte-identical `decided` + `halted` streams (the
  [[concepts/node-model]] §8 contract).

### 12.3 Verification gate

Before flipping T32 to In Review, run
`superpowers:verification-before-completion`: the full test suite passes,
and the §12.2 run is shown actually reaching finalisation.

## 13. Wiki deliverables

Per `docs/workflow.md` and `docs/wiki-spec.md`:

- **This spec** — `docs/superpowers/specs/2026-05-23-t32-pos-consensus-design.md`
  (committed; superpowers references it in place — do not relocate).
- **Build-verification page** —
  `wiki/experiments/2026-05-23_casper-baseline.md`: config, seeds, commit
  hash, commands to re-run, raw result location, one-paragraph
  observation.
- **`wiki/index.md`** — add the new experiment page under `## Experiments`.
- **`wiki/log.md`** — append one `code`-type entry for task 32.
- **`system-design-protocols.md` `## Revisions`** — if the implementation
  diverges from the non-binding §3 Casper sketch, record the divergences
  there (as T29 did for the PBFT sketch). The expected divergences are
  already listed in §15 below.

No new algorithm or concept page is created: [[algorithms/pos]] already
covers the mechanism, and T32 is an Engineer (code) task.

## 14. Decisions

| ID | Decision |
| :-- | :-- |
| **A** | Full vertical slice: inline round-robin proposer + inline `2/3` finality, in `node.py` / `epoch.py`. T33/T34 extract `selection.py` / `finality.py` later. |
| **B** | Fidelity = Approach 1: no slashing detection, no LMD-GHOST. `OffenceKind` / `SlashingEvidencePayload` / `selection.py` / `finality.py` are not created. |
| **C** | Self-recording: each node records its own block and its own FFG vote locally, because `Network.broadcast` excludes the sender. Analogue of PBFT Decision B. |
| **D** | The constructor takes a full `stake_table: dict[int, float]`; `total_stake` is its sum. A node weights every attestation by `stake_table[attester_idx]`. |
| **E** | Proposer is round-robin `slot mod n` — deterministic, no RNG. The T33 extraction seam. |
| **F** | Genesis (epoch 0) is justified and finalised by construction; it bootstraps the FFG justify chain. |
| **G** | `decided` is emitted once per epoch, on first finalisation (`decided_epochs` set guards re-emission). |
| **H** | Lazy `EpochState` creation: an `ATTESTATION` may arrive before the local checkpoint block; create the state with `setdefault` and file the vote regardless. Analogue of PBFT Decision C. |
| **I** | Attestation dedupe: one FFG vote per `(attester, target_epoch)` counts; a later vote from the same attester for the same target epoch is ignored. |
| **J** | One `ATTESTATION` per validator per epoch, emitted at slot offset `attest_offset` within the epoch (default: a mid-epoch slot, so the checkpoint block has time to propagate). The slot timer still fires every slot for proposer rotation. This is a simplification of the [[concepts/system-design-protocols]] §3 sketch, which attests every slot — justified because the per-slot head vote is LMD-GHOST-only and LMD-GHOST is out of scope (Decision B). |

## 15. Open to revision — expected divergences from the wiki

Per `docs/wiki-spec.md` § Revisions rule, the following divergences from
the non-binding wiki sketches will land as `## Revisions` entries on the
named pages as part of T32:

- **`system-design-protocols.md` §3** — the Casper sketch attests every
  slot and references `self.lmd_ghost`. T32 attests once per epoch
  (Decision J) and has no fork-choice object (Decision B). Record both.
- **`message-types.md` §4** — the `ATTESTATION` payload in the catalog
  carries a `head_vote_hash` and per-validator `signature`; T32 omits both
  (LMD-GHOST out of scope; the simulator passes objects, not signed
  bytes). `BLOCK-PROPOSAL` likewise omits `proposer_sig`. Record as a
  Revision so the §3/§4 byte-size columns are not silently contradicted.
- **`node-model.md` §11** — the open-to-revision list anticipates T32
  surfacing fit issues; if none beyond the above arise, no entry is
  needed.

These are anticipated, not committed: the implementation plan confirms
each before the corresponding Revision is written.
