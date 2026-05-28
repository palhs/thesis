# T38 — Snowman Honest-Path Baseline: Design Spec

- **Task:** T38 (Engineer) — Implement Snowman as the third protocol; honest-path
  build-verification baseline at `n ∈ {4, 7, 10}` with byte-identical determinism.
- **Branch:** `task/T38-snowman`.
- **Date:** 2026-05-27.
- **Outcome (TASKS.md):** "If ready: implement DAG-based or Avalanche-style
  consensus." Scoped to **Snowman** by the T37 decision gate
  ([[concepts/week7-decision]]).
- **Scope decisions (human, 2026-05-27):**
  - **Block-production cadence (Q3):** slot-timer + round-robin proposer
    (`slot % n == self.id`), mirroring T32/T35's Casper FFG slot loop.
  - **Poll-round structure (Q1):** concurrent per-block polls (one
    `("poll", block_id)` timer per in-flight block).
  - **Poll-round close (Q2):** α-based early termination, **success-path only**
    — close on `agree[current_pref] ≥ α_c` OR `responses == K`. Failure-path
    early-close deferred (tangles with multi-block flip detection); under
    `drop_rate = 0` honest path, quorum-close always fires.
  - **Snowball semantics (Q4):** **full two-threshold Snowball** with dedicated
    unit test for the `α_p` preference-flip path. The flip path is honest-path
    dead code but production-faithful per `[ava-docs]`; the unit test guards
    it against regression and unblocks T18 / T51–T53 plumbing.
- **Fidelity decision (human, 2026-05-27):** honest-path core only. Slashing,
  selective-response adversaries, deadline-timer drop resilience, and the
  unified comparative CSV all defer to their owning tasks per
  `[[concepts/week7-decision]]` §4.2.

This spec is the canonical reference for the T38 implementation plan
(`superpowers:writing-plans`). It consumes the W3 design contracts
[[concepts/node-model]], [[concepts/message-types]] §5,
[[concepts/system-design-protocols]] §4, [[concepts/metric-reconciliation]],
and the algorithm page [[algorithms/avalanche]]. It mirrors the structure of
the T28/T29 PBFT and T32 PoS specs so the three protocol implementations stay
comparable.

## 1. Scope and non-goals

### In scope

- `SnowmanNode(Node)` implementing **full Snowball semantics**: per-block
  confidence accumulator, `α_p` preference-flip with counter reset, `α_c`
  counter increment, `β`-acceptance, `decided` event emission.
- **Slot-timer + round-robin proposer** (`slot % n == self.id`) emitting
  `BLOCK-ANNOUNCEMENT` every `slot_duration`. Honest-path is one block per
  conflict set.
- **Concurrent per-block poll loops** keyed by `block_id`; one
  `("poll", block_id)` timer per in-flight block.
- **α-based success-path early termination**: round closes when
  `agree[current_pref] ≥ α_c` OR `responses == K`. The success-path early-close
  is safe under the rescaling rule because `α_p + α_c > K` for `K ∈ [3, 20]`.
- **K-peer subsampling** via `Node.rng.sample(peers_excluding_self, K)`, with
  parameters from [[concepts/metric-reconciliation]] §Snowman parameter
  rescaling: `K = min(20, n-1)`, `α_p = ⌊K/2⌋+1`, `α_c = ⌈0.8·K⌉`. `β = 15`
  (cross-protocol comparison baseline per §Calibration defaults).
- New `src/snowman/` package (six modules) and `tests/snowman/` suite
  (eleven test files) registered as `make test-snowman` in the Makefile
  `SUITES` list.
- Honest-path build-verification baseline at **`n ∈ {4, 7, 10}`** with
  byte-identical determinism, mirroring T30 ([[experiments/2026-05-21_pbft-baseline]])
  and T35 ([[experiments/2026-05-25_pos-baseline]]). One experiment page
  `wiki/experiments/2026-05-27_snowman-baseline.md`.
- One dedicated unit-test scenario in `tests/snowman/test_node_flip.py` for
  the `α_p` preference-flip path (hand-crafted multi-block conflict set).

### Out of scope (deferred, with owning task)

- **Adversarial Snowman.** Selective response, adaptive colour flipping,
  sample-partitioning, colluding sub-sampler → T18
  ([[concepts/adversary-model]] §§3–5 generic capabilities, §7.1 Snowman-specific)
  and T51–T53 (W10 adversarial experiments).
- **Snowman-vs-rest unified CSV.** Defers to T40
  ([[concepts/output-format]] forward link).
- **Snowman Chapter 3 prose.** Defers to T36.1 (unblocked on T38 landing).
- **DAG-Avalanche.** Out of scope per [[algorithms/avalanche]] §Simulator
  mapping, reaffirmed by [[concepts/week7-decision]] §1.
- **Drop-resilience poll-deadline timer.** Defers to T47 via a `## Revisions`
  entry on [[concepts/system-design-protocols]] §4 at that time.
- **`α_p ≠ α_c` parameter-sensitivity sweep.** Defers to T19 / T44 if the
  rescaling rule needs sensitivity coverage beyond the §Calibration defaults.
- **Failure-path α-early-close.** Multi-block conflict-set flip detection
  makes the early-close condition complex; under `drop_rate = 0` honest path,
  quorum-close always fires before the failure-path would matter. If a future
  delay/drop task needs it, it lands as a `## Revisions` entry.
- **Any change to `src/scheduler/`, `src/network/`, `src/nodes/`, or
  `src/event_log/`.** [[concepts/week7-decision]] §4.3 prohibition; if a
  shared-infra shortfall surfaces, it lands as a `## Revisions` entry on
  the relevant W3 contract page plus a Backlog item, not as a silent edit.

## 2. Package layout — `src/snowman/`

Mirrors `src/pos/` (the closest precedent: T32 + T34 same shape). Six files.

| File | Role | `src/pos/` analogue |
| :-- | :-- | :-- |
| `__init__.py` | Package exports (`SnowmanNode`, `snowman_parameters`) | `__init__.py` |
| `messages.py` | Three payload dataclasses (§3) | `messages.py` |
| `block.py` | `Block` dataclass + `hash_block`; `ConflictSet` per `parent_id` with Snowball state; thin `Chain` for proposer tip-tracking (§4) | `chain.py` + `epoch.py` |
| `poll.py` | `Poll` instance, success-path early-close detection, `close_round` applying the full Snowball update (§5) | `finality.py` |
| `parameters.py` | Pure `snowman_parameters(n) -> (K, α_p, α_c)` implementing the [[concepts/metric-reconciliation]] rescaling rule (§7) | (no direct analogue) |
| `node.py` | `SnowmanNode(Node)` — slot loop, proposer, message handlers, `Node.rng.sample` plumbing (§6) | `node.py` |

Six files instead of the three suggested by [[concepts/week7-decision]] §4.1.
`block.py` and `parameters.py` are split out for isolated testability
following `src/pos/` precedent — an in-scope Engineer call per §4.1's
"the exact decomposition is the Engineer's call."

Estimated LOC: ~280 in `src/snowman/`, ~450 in `tests/snowman/`.

## 3. Message payloads — `src/snowman/messages.py`

Three frozen dataclasses, conforming to [[concepts/message-types]] §5
exactly. The shared `Message` envelope (`src`, `dst`, `type`, `payload`,
`t_sent`) is owned by [[concepts/node-model]] §6.

```python
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class BlockAnnouncementPayload:
    slot: int
    block_id: bytes              # 32-byte SHA-256 hash, see block.hash_block
    parent_id: bytes             # 32-byte; b'\x00'*32 = genesis
    transactions: tuple[bytes, ...]
    proposer_idx: int


@dataclass(frozen=True)
class QueryPayload:
    request_id: int              # poller-monotone; unique per (poller, block_id, round)
    block_id: bytes              # the block being polled


@dataclass(frozen=True)
class QueryResponsePayload:
    request_id: int              # echoes the QUERY
    preferred_block_id: bytes    # responder's current preference for block_id's conflict set
```

**`request_id` ownership.** Owned by the poller; monotone-incremented in
`SnowmanNode._start_poll_round` on each new round. The poller's `Poll`
instance stores its current `request_id`; any `QUERY-RESPONSE` with a
non-matching `request_id` is dropped silently at `_handle_response` entry.
This is the mechanism that makes α-based early termination safe: when a
round closes early, the next round bumps `request_id`, making late responses
from the closed round stale.

**`preferred_block_id` permissive default.** If the responder has not yet
seen any block in `block_id`'s conflict set (no `BLOCK-ANNOUNCEMENT`
received), it returns the queried `block_id` itself — a default that does
not bias against the proposer. Honest-path baseline never exercises this
branch (`delay = 1e-9 ≪ slot_duration = 1.0` puts announces well before
queries); covered by `tests/snowman/test_node_query.py`. Lands as a
behavioural clarification on [[concepts/message-types]] §5 via a `## Revisions`
entry (§10.2).

**No signature fields.** Per [[concepts/message-types]] §5, production
Snowman signatures are out of scope (same precedent as T28/T29 PBFT and T32
Casper FFG).

## 4. Per-block state — `src/snowman/block.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import hashlib

GENESIS_ID = b'\x00' * 32


@dataclass(frozen=True)
class Block:
    block_id: bytes
    parent_id: bytes
    slot: int
    proposer_idx: int
    transactions: tuple[bytes, ...]


def hash_block(
    *, slot: int, parent_id: bytes, proposer_idx: int,
    transactions: tuple[bytes, ...],
) -> bytes:
    """Deterministic SHA-256 over a canonical, length-prefixed encoding.

    Encoding (all integers big-endian, fixed width):
      uint64 slot || bytes(32) parent_id || uint32 proposer_idx
      || uint32 n_tx || (uint32 len || bytes len) for each tx
    """
    # implementation pinned in the plan; ~12 LOC


class CSState(Enum):
    POLLING = "polling"
    ACCEPTED = "accepted"


@dataclass
class ConflictSet:
    """Snowball state for all blocks claiming one parent_id.

    `confidence[b]` is the monotonic per-block accumulator (Snowball's
    "highest-confidence preference" semantics): incremented every round
    where `b` is the round's majority block with `count ≥ α_p`.
    `counter` is the *consecutive* α_c-hits on the current `preference`;
    reset on a flip or on an α_c miss. `state` transitions to ACCEPTED
    when `counter ≥ β`.
    """
    parent_id: bytes
    members: dict[bytes, Block] = field(default_factory=dict)
    confidence: dict[bytes, int] = field(default_factory=dict)
    preference: bytes = b''      # initialised on first add_block
    counter: int = 0
    state: CSState = CSState.POLLING

    def add_block(self, block: Block) -> None:
        """First block added becomes the initial preference."""
        if block.block_id in self.members:
            return
        self.members[block.block_id] = block
        self.confidence.setdefault(block.block_id, 0)
        if self.preference == b'':
            self.preference = block.block_id


class Chain:
    """Linear chain bookkeeping for the proposer.

    Tracks the depth of every seen block (used to identify the tip the
    slot proposer extends) and the set of ACCEPTED blocks (used by the
    build-verification assertion).
    """
    def __init__(self) -> None:
        self.accepted: dict[bytes, Block] = {}
        self.depth: dict[bytes, int] = {GENESIS_ID: 0}
        self.tip: bytes = GENESIS_ID

    def on_announce(self, block: Block) -> None:
        parent_depth = self.depth.get(block.parent_id)
        if parent_depth is None:
            return       # out-of-order arrival — T46–T50 owns this
        self.depth[block.block_id] = parent_depth + 1
        if self.depth[block.block_id] > self.depth[self.tip]:
            self.tip = block.block_id

    def on_accept(self, block: Block) -> None:
        self.accepted[block.block_id] = block
```

**Self-announcement self-recording.** Same precedent as T29 Decision B
(PBFT primary self-records `PRE-PREPARE`): the proposer's
`BLOCK-ANNOUNCEMENT` broadcast is excluded from its own delivery by the
network's "broadcast excludes sender" convention. `SnowmanNode._propose`
calls `chain.on_announce(...)` and `conflict_sets[parent_id].add_block(...)`
on its own block explicitly.

**Out-of-order arrival unsupported.** `Chain.on_announce` short-circuits if
`parent_id` is unknown. Honest-path baseline never hits it because
`delay = 1e-9` and slot timers are synchronised. Heavy-delay scenarios
(T46–T50) will exercise this branch; a `## Revisions` entry lands then.

## 5. Poll round mechanics — `src/snowman/poll.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field

from .block import ConflictSet, CSState


@dataclass
class Poll:
    """In-flight poll round for one block_id.

    `request_id` makes responses to a closed-and-rearmed round filter out
    as stale at `SnowmanNode._handle_response` entry. `peers` is the
    `K`-sample drawn from this round's RNG call; stored so tests can
    inspect it and so determinism re-runs can be verified.
    """
    block_id: bytes
    request_id: int
    peers: tuple[int, ...]
    agree_per_block: dict[bytes, int] = field(default_factory=dict)
    responses_received: int = 0
    closed: bool = False


@dataclass(frozen=True)
class PollOutcome:
    flipped: bool
    new_preference: bytes
    counter: int
    accepted: bool


def on_response(
    *, poll: Poll, preferred_block_id: bytes,
    current_preference: bytes, alpha_c: int, K: int,
) -> bool:
    """Record one QUERY-RESPONSE; return True iff the success-path
    early-close trigger fired (agree[current_pref] ≥ α_c).

    Returning False means the round is still collecting; the caller
    closes the round on either (a) this returning True or
    (b) responses_received == K.
    """
    if poll.closed:
        return False
    poll.agree_per_block[preferred_block_id] = \
        poll.agree_per_block.get(preferred_block_id, 0) + 1
    poll.responses_received += 1
    if poll.agree_per_block.get(current_preference, 0) >= alpha_c:
        poll.closed = True
        return True
    return False


def close_round(
    *, conflict_set: ConflictSet, poll: Poll,
    alpha_p: int, alpha_c: int, beta: int,
) -> PollOutcome:
    """Apply the full Snowball update for one closed round.

    Three-step rule (full α_p / α_c semantics):
      1. Identify majority block b* = argmax agree_per_block. Tie-break:
         highest count, then lowest block_id (bytes-lex). If
         count_majority ≥ α_p AND b* ≠ current preference, flip
         preference to b* and reset counter to 0. Increment
         confidence[b*] regardless of flip.
      2. Check agree[preference] against α_c; if ≥, counter += 1; else
         counter = 0.
      3. If counter ≥ β, state → ACCEPTED.
    """
    poll.closed = True

    # Step 1: majority block + α_p preference update
    majority_block, count_majority = min(
        poll.agree_per_block.items(),
        key=lambda kv: (-kv[1], kv[0]),     # max count, then min block_id
    )
    flipped = False
    if count_majority >= alpha_p:
        if majority_block != conflict_set.preference:
            conflict_set.preference = majority_block
            conflict_set.counter = 0
            flipped = True
        conflict_set.confidence[majority_block] = \
            conflict_set.confidence.get(majority_block, 0) + 1

    # Step 2: α_c counter update on the (possibly-new) preference
    pref_agree = poll.agree_per_block.get(conflict_set.preference, 0)
    if pref_agree >= alpha_c:
        conflict_set.counter += 1
    else:
        conflict_set.counter = 0

    # Step 3: β acceptance
    accepted = False
    if conflict_set.counter >= beta and conflict_set.state is CSState.POLLING:
        conflict_set.state = CSState.ACCEPTED
        accepted = True

    return PollOutcome(
        flipped=flipped,
        new_preference=conflict_set.preference,
        counter=conflict_set.counter,
        accepted=accepted,
    )
```

**Success-path early-close safety invariant.** Closing on
`agree[current_pref] ≥ α_c` is provably flip-safe under the rescaling rule:
`α_p + α_c > K` for `K ∈ [3, 20]`, so no other block can still reach `α_p`
with the responses remaining when `α_c` is hit. Asserted in
`tests/snowman/test_parameters.py` as a parametrised test across the full
`K` range.

**Why `close_round` is separated from `on_response`.** Quorum-close and
success-close both reuse `close_round`; only the trigger differs.
Centralising the Snowball update in one place keeps the α_p flip path
testable in isolation — `test_node_flip` calls `close_round` directly on
a hand-crafted `Poll` + `ConflictSet`.

**Tie-break determinism.** `min(..., key=lambda kv: (-kv[1], kv[0]))` picks
highest count, lex-lowest `block_id`. Honest-path baseline doesn't hit ties
(singleton conflict sets); the flip unit test exercises the tie-break path.

## 6. `SnowmanNode` — `src/snowman/node.py`

### 6.1 Constructor

```python
class SnowmanNode(Node):
    def __init__(
        self, *,
        node_id: int,
        n: int,
        slot_duration: float = 1.0,
        beta: int = 15,
        K: int | None = None,
        alpha_p: int | None = None,
        alpha_c: int | None = None,
        workload: Sequence[bytes] | None = None,
        weight: float = 1.0,
        rng: random.Random | None = None,
    ):
        super().__init__(node_id=node_id, weight=weight, rng=rng)
        K_d, p_d, c_d = snowman_parameters(n)
        self.n = n
        self.K = K if K is not None else K_d
        self.alpha_p = alpha_p if alpha_p is not None else p_d
        self.alpha_c = alpha_c if alpha_c is not None else c_d
        self.beta = beta
        self.slot_duration = slot_duration
        self.workload = tuple(workload or ())
        self._workload_cursor = 0

        self.chain = Chain()
        self.conflict_sets: dict[bytes, ConflictSet] = {}   # parent_id → CS
        self.polls: dict[bytes, Poll] = {}                  # block_id → current Poll
        self._next_request_id = 0
        self._peers_minus_self_cache: tuple[int, ...] | None = None
```

Defaults come from `snowman_parameters(n)`; explicit overrides exist for
the flip unit test. `β = 15` is the cross-protocol comparison baseline per
[[concepts/metric-reconciliation]] §Calibration defaults; the RQ4-only
regime (`β ∈ {3, 5}`) lives in T19/T44.

### 6.2 Handlers

```python
def start(self, t: float) -> None:
    self.set_timer("slot", self.slot_duration, 0, t)

def on_timer(self, timer_id, payload, t: float) -> None:
    if timer_id == "slot":
        slot = payload
        if slot % self.n == self.id:
            self._propose(slot, t)
        self.set_timer("slot", self.slot_duration, slot + 1, t)
    elif isinstance(timer_id, tuple) and timer_id[0] == "poll":
        block_id = timer_id[1]
        self._start_poll_round(block_id, t)

def on_message(self, msg, t: float) -> None:
    if msg.type == "BLOCK-ANNOUNCEMENT":
        self._handle_announce(msg.payload, t)
    elif msg.type == "QUERY":
        self._handle_query(msg, t)
    elif msg.type == "QUERY-RESPONSE":
        self._handle_response(msg, t)
    else:
        self._reject(reason="unknown_type", msg_type=msg.type, t=t)
```

### 6.3 Helper sketches

- `_propose(slot, t)` — build a `Block` extending `self.chain.tip` (parent_id =
  current tip); broadcast `BLOCK-ANNOUNCEMENT`; self-record via
  `chain.on_announce` and `conflict_sets[parent].add_block`; emit
  `snowman_announced{block_id, parent_id, slot, proposer_idx}`; arm the first
  `("poll", block_id)` timer at `t` (POLL_DELAY = `1e-9`).
- `_handle_announce(payload, t)` — payload-shape guard; construct `Block`
  via `hash_block(...)`; lazy-create `conflict_sets[payload.parent_id]`;
  `cs.add_block(block)`; `chain.on_announce(block)`; emit
  `snowman_announced`; if this is the first poll for the block, arm
  `("poll", block.block_id)` timer.
- `_start_poll_round(block_id, t)` — bump `self._next_request_id`; resolve
  `self._peers_minus_self()`; `peers = tuple(self.rng.sample(peers_minus_self, self.K))`;
  build a fresh `Poll(block_id, request_id, peers)`; replace
  `self.polls[block_id]`; send K `QUERY` messages; emit
  `snowman_poll_started{block_id, request_id, peers}`.
- `_handle_query(msg, t)` — look up the conflict set containing `msg.payload.block_id`;
  if found, respond with `cs.preference`; if not found, respond with the
  queried `block_id` (permissive default). Send `QUERY-RESPONSE`.
- `_handle_response(msg, t)` — look up `self.polls[msg.payload.block_id]`;
  drop on absent or `request_id` mismatch (stale). Call `on_response(...)`;
  if it returns True OR `poll.responses_received == self.K`, close the round
  via `close_round(...)`; emit `snowman_poll_closed{block_id, request_id,
  agree_per_block, flipped, new_preference, counter, accepted}`. If
  `outcome.accepted`: emit `decided{value: block_id, instance_id: block_id}`,
  call `chain.on_accept(block)`. If not: rearm `("poll", block_id)` at
  `t + POLL_DELAY`.

### 6.4 RNG-driven K-peer sampling

Single call site: `self.rng.sample(self._peers_minus_self(), self.K)` per
poll round. `Node.rng` is seeded from `(global_seed, node_id)` per
[[concepts/node-model]] §8 + [[concepts/reproducibility]]; determinism holds
by construction. The cache `_peers_minus_self_cache` is populated on first
sample call (the validator-set list is fixed by the harness at bind time);
it is *not* sorted independently of the registry's iteration order — the
registry already returns nodes in deterministic order per `Network.register`
contract.

### 6.5 Events emitted

| Event | When | Payload |
| :-- | :-- | :-- |
| `snowman_announced` | a `BLOCK-ANNOUNCEMENT` is processed (own or received) | `{block_id, parent_id, slot, proposer_idx}` |
| `snowman_poll_started` | a new poll round begins | `{block_id, request_id, peers}` |
| `snowman_poll_closed` | a round closes (success or quorum) | `{block_id, request_id, agree_per_block, flipped, new_preference, counter, accepted}` |
| `snowman_rejected` | a message is dropped (malformed, unknown type) | `{reason, ...}` |
| `decided` | β-acceptance | `{value: block_id, instance_id: block_id}` |

**No `view_changing`-equivalent state.** Snowman has no view-change analogue;
preference flips are local state, not protocol-level events. The
`Node._halted` lifecycle still applies for unrecoverable errors.

## 7. Parameter rescaling — `src/snowman/parameters.py`

```python
"""Snowman parameter rescaling rule
(wiki/concepts/metric-reconciliation §Snowman parameter rescaling).

Thesis sweeps n ∈ {4, 7, 10, 16, 25}; production K=20 is incoherent for
n < 21. The rule below is the only rescaling used; it is deterministic in
n and reproducible across seeds.
"""
from __future__ import annotations
import math


def snowman_parameters(n: int) -> tuple[int, int, int]:
    """Return (K, α_p, α_c) for a validator set of size n.

    β is held constant at the production value (15) and is not rescaled;
    it is supplied separately by the caller (SnowmanNode.__init__).

    Preconditions: n >= 2 (a single-node "network" has no peers to sample).
    """
    if n < 2:
        raise ValueError(f"snowman_parameters: n must be >= 2, got {n}")
    K = min(20, n - 1)
    alpha_p = K // 2 + 1
    alpha_c = math.ceil(0.8 * K)
    return K, alpha_p, alpha_c
```

Test coverage in `tests/snowman/test_parameters.py`:
- The exact five-row table from [[concepts/metric-reconciliation]] for
  `n ∈ {4, 7, 10, 16, 25}`.
- The **early-close safety invariant** `α_p + α_c > K` for every
  `K ∈ [3, 20]` (parametrised across `n ∈ [4, 21]`). Section 5's success-path
  early-close relies on this; the test guards against any future change to
  the rescaling rule that would break the invariant.
- The `n < 2` precondition raises `ValueError`.
- Production parity at `n = 25`: `(K, α_p, α_c) = (20, 11, 16)` exactly
  matches `[ava-docs]`.

`β` lives in `SnowmanNode.__init__`'s `beta` parameter (default 15) rather
than this module — it doesn't depend on `n`, and the RQ4 sensitivity sweep
(`β ∈ {3, 5}`) per [[concepts/metric-reconciliation]] §Calibration defaults
will pass an override.

## 8. Test suite — `tests/snowman/`

### 8.1 Unit + handler tests

| File | Coverage |
| :-- | :-- |
| `_helpers.py` | Fixtures: build an `n`-node `Network`, attach `SnowmanNode`s with a deterministic seed, construct hand-crafted `Poll` / `ConflictSet` for unit tests |
| `test_messages.py` | Dataclass frozen-ness, field shapes; documented permissive-default for unknown `block_id` |
| `test_block.py` | `hash_block` determinism + canonical encoding; `ConflictSet.add_block` preference-on-first-add + idempotency on re-add; `Chain.on_announce` tip-tracking + out-of-order short-circuit |
| `test_parameters.py` | Five-row table; `α_p + α_c > K` invariant across `K ∈ [3, 20]`; `n < 2` precondition; production parity at `n = 25` |
| `test_poll.py` | `on_response` success-path early-close; quorum close; stale-`request_id` drop; `close_round` Snowball update — (a) majority hits α_c no flip, (b) majority hits α_p not α_c, (c) no block hits α_p |
| `test_node_init.py` | Rescaled defaults at `n ∈ {4, 7, 10}`; explicit override accepted; `n < 2` rejected |
| `test_node_propose.py` | Slot timer arms at `start`; round-robin proposer rule; proposer self-records announce and starts first poll; non-proposer slots are no-ops |
| `test_node_announce.py` | `BLOCK-ANNOUNCEMENT` handling: malformed payload → `snowman_rejected`; first announce creates ConflictSet and arms `("poll", block_id)` timer; duplicate announce is a no-op |
| `test_node_query.py` | `QUERY` handling: responder returns current preference; unknown `block_id` → permissive default; `QUERY-RESPONSE` handling: stale `request_id` dropped, valid response updates `Poll`, success-close fires `close_round` |
| `test_node_flip.py` | ★ **The α_p preference-flip path** — hand-craft a two-block conflict set with `K=3`; deliver responses (1 for current_pref A, 2 for B); assert `close_round` returns `flipped=True, new_preference=B, counter=0`; subsequent full-quorum round for B advances `counter=1` |
| `test_node_accept.py` | β-acceptance and `decided` emission; counter advances through β rounds in honest path; `chain.on_accept` populates `chain.accepted`; subsequent `BLOCK-ANNOUNCEMENT` for an ACCEPTED block is a no-op |

### 8.2 Integration test — `tests/integration/test_snowman_baseline.py`

```python
class TestSnowmanBaseline(unittest.TestCase):
    """Honest-path build verification at n ∈ {4, 7, 10}.

    Four T38 outcomes per scenario:
      1. Every honest node ACCEPTS every announced block.
      2. Zero forks — exactly one ACCEPTED block per slot across the network.
      3. Finalisation latency is logged on every decided event.
      4. Two runs with the same (config, global_seed) are byte-identical.
    """
    SCENARIOS = [("n=4", 4), ("n=7", 7), ("n=10", 10)]

    def test_every_node_accepts_every_block(self): ...     # outcome 1
    def test_no_forks(self): ...                            # outcome 2
    def test_finality_latency_logged(self): ...             # outcome 3
    def test_determinism_byte_identical(self): ...          # outcome 4 — exercises RNG sampling
```

**The determinism case** ([[concepts/week7-decision]] §5.1 watch-for closure):
`test_determinism_byte_identical` runs each scenario twice with the same
`global_seed`, captures the full event-stream tuple per
[[concepts/event-log-schema]] (`t, node_id, event_type, fields`), and
asserts both runs are byte-identical. Because Snowman's poll loop draws on
`Node.rng` β times per accepted block at every node, this test exercises
the sampling path that PBFT and Casper FFG baselines do not.

### 8.3 Configuration (mirrored from T35)

```python
global_seed = 42
slot_duration = 1.0
beta = 15
delay = 1e-9                    # minimum non-zero
drop_rate = 0
t_max = 20.0                    # ~19 slot fires → ~19 accepted blocks per scenario
```

### 8.4 Makefile registration

One-line diff:

```
-SUITES        = scheduler nodes network event_log config pbft pos integration
+SUITES        = scheduler nodes network event_log config pbft pos snowman integration
```

`make test-snowman` runs the suite in isolation; `make test` runs all.

## 9. Build-verification baseline page

`wiki/experiments/2026-05-27_snowman-baseline.md` — mirrors
[[experiments/2026-05-25_pos-baseline]] (T35) in structure:

1. **Header.** What's under test (full Snowball honest-path across the W3
   stack, driven by `SnowmanNode`); T30 (PBFT) and T35 (PoS) as analogues;
   T38 added one integration test, `src/snowman/` package, this page; no
   shared-infra change.
2. **Configuration.** Code under test (`src/snowman/`, branch
   `task/T38-snowman`, commit hash `TODO(human)`); the per-scenario
   parameter table from [[concepts/metric-reconciliation]] §Snowman
   parameter rescaling; `global_seed = 42`, `slot_duration = 1.0`,
   `β = 15`, `delay = 1e-9`, `drop_rate = 0`, `t_max = 20.0`.
3. **Scenarios.** Three: `n=4`, `n=7`, `n=10` at uniform `weight = 1.0`.
   No non-uniform-weight scenario (Snowman is not stake-weighted).
4. **Re-run.** Two commands (unit + integration), `make test` runs both.
5. **Result.** Per-scenario event counts table; first accepted block's
   `decided.t`; per-scenario `α_c/K` row; analytical safety bound
   `(1 − α_c/K)^β` per scenario (`n=4`: 0; `n=7`: ≈6.5e-12; `n=10`: ≈4.4e-14);
   empirical ε = 0 across all seeds; note that meaningful empirical-ε
   study is RQ4 (T51–T53), not this page.
6. **Honest-path outcomes table.** Four T38 outcomes mapped to integration
   tests.
7. **`n = 4` rescaling-boundary note.** Per [[concepts/metric-reconciliation]]
   §Comparative-claim exclusion at n=4: at K=3, α_c=3, `α_c/K = 1.0` and
   `(1−α_c/K)^β = 0` — Snowman degenerates to "flood-vote-with-counter."
   The build-verification baseline includes n=4 as a sanity check that the
   rescaling rule reduces to its boundary cleanly; downstream comparative
   tables (T41+) exclude this row.
8. **Determinism observation.** `global_seed = 42` re-runs produce
   byte-identical event streams across all three scenarios — week7-decision
   §5.1 watch-for closed by direct observation. Per-node RNG draws
   `β · 19 ≈ 285` samples per scenario, all on the K-peer sampling path.
9. **Forward references.** What this page does not cover and which task
   owns: adversarial Snowman (T18 / T51–T53), empirical ε under adversary
   (T51–T53 with `β ∈ {3, 5}` regime), unified CSV (T40), Ch.3 prose
   (T36.1), out-of-order arrival / heavy delay (T46–T50), drop-resilience
   deadline timer (T47).
10. **Page-tail.** Sources (`[9]`, `[ava-docs]` via
    [[concepts/annotated-bibliography]]). Revisions section (initially empty).

The page does **not** carry a sample CSV. T35 carries one as a T35-local
placeholder; the Backlog already says T40 will reconcile. T38 inherits the
deferral and adds no second placeholder.

## 10. `## Revisions` entries landed by T38

### 10.1 — `wiki/concepts/system-design-protocols.md`

One new entry, mirroring T29 / T32 structure. Five divergences:

> **2026-05-27 (T38).** The §4 Snowman sketch diverges from the T38
> implementation (`src/snowman/`) in five ways a reader reproducing the
> protocol from the sketch alone would get wrong:
>
> - **`α_p` / `α_c` split.** The sketch uses a single `ALPHA_C`. The
>   implementation splits the production thresholds per `[ava-docs]` and
>   [[concepts/metric-reconciliation]] §Snowman parameter rescaling:
>   `α_p = ⌊K/2⌋+1` controls *preference-flip*; `α_c = ⌈0.8·K⌉` controls
>   *counter-increment*. The §6 register already flagged this; the entry
>   pins the specific rule.
> - **`ConflictSet` keyed by `parent_id`.** The sketch's `self.block[block_id]
>   = (preference, counter, state)` tuple is too compact for the flip path:
>   detecting `α_p` requires per-block `agree` and per-block `confidence`,
>   which only make sense once blocks are grouped into a conflict set. The
>   implementation introduces `ConflictSet` keyed by `parent_id` with
>   `members: dict[block_id, Block]`, `confidence: dict[block_id, int]`,
>   plus per-set `preference`, `counter`, `state`.
> - **α-based early termination.** The sketch closes the round on
>   `responses == K`. The implementation closes on
>   `agree[current_pref] ≥ α_c` (success-path) OR `responses == K`
>   (quorum-path); the failure-path early-close is deliberately not
>   implemented. The success-path early close is safe under the rescaling
>   rule because `α_p + α_c > K` for all `K ∈ [3, 20]`, asserted in
>   `tests/snowman/test_parameters.py`. Drop-resilience (a poll-deadline
>   timer) defers to T47 via a subsequent `## Revisions` entry.
> - **Self-announcement self-recording.** The sketch handles
>   `BLOCK-ANNOUNCEMENT` only via `on_message`. `Network.broadcast` excludes
>   the sender, so the proposer never receives its own announcement. The
>   implementation has `_propose` explicitly call `chain.on_announce` and
>   `conflict_sets[parent_id].add_block` on its own block — same precedent
>   as T29 Decision B (PBFT primary self-records `PRE-PREPARE`).
> - **Slot-driven proposer rotation.** The sketch's `start(t)` is `pass`
>   ("idle until a block arrives"); the implementation arms a `"slot"`
>   timer at `t = 0` with cadence `slot_duration` and round-robin proposer
>   rule `slot % n == self.id` — the cross-protocol-comparable choice
>   matching `CasperNode`'s slot loop (T32 Decision J).
>
> The §6 register already flagged the sketch as non-binding; this entry
> records the specific divergences. The control spine — per-block subsampled
> `K`-peer poll, Snowball counter accumulator, `β`-acceptance, `decided`
> event on acceptance — is unchanged.

### 10.2 — `wiki/concepts/message-types.md`

One new entry, behavioural clarification:

> **2026-05-27 (T38).** The §5 Snowman wire schema is implemented as written,
> with one behavioural clarification a reader reproducing the protocol from
> §5 alone might miss: when a responder receives `QUERY(request_id, block_id)`
> for a `block_id` whose conflict set it has not yet learned (no
> `BLOCK-ANNOUNCEMENT` received), it returns
> `QUERY-RESPONSE(request_id, preferred_block_id = block_id)` — the *queried*
> `block_id` itself, as a permissive default that does not bias against the
> proposer. Honest-path baseline never exercises this branch
> (`delay = 1e-9 ≪ slot_duration = 1.0`), but the code path exists and is
> exercised by `tests/snowman/test_node_query.py`.

### 10.3 — Other wiki updates (not Revisions)

- `wiki/index.md`: append the new experiment page entry under `## Experiments`.
- `wiki/log.md`: one task entry per the standard format
  (`## [2026-05-27] code | task 38 — Snowman honest-path baseline`).

### 10.4 — Updates explicitly NOT landed by T38

- The `## Revisions` rewording of [[concepts/adversary-model]] §8 and
  [[concepts/experiment-matrix-runs]] §8 from "12-of-18" to
  "9-in-scope / 3-deferred-with-T38.1 / 6-catalogued" is owned by **T38.1**
  per the Backlog entry, NOT T38.
- No update to [[algorithms/avalanche]] — T38 implements what is described
  there; no contradiction.

## 11. Cross-references

**Inbound (existing wiki contracts T38 consumes):**

- [[concepts/week7-decision]] §4 — Scope handed to T38 by the W7 gate.
- [[concepts/system-design-protocols]] §4 — Reference sketch.
- [[concepts/metric-reconciliation]] §Snowman parameter rescaling,
  §Calibration defaults — Rescaling rule and `β = 15` baseline.
- [[concepts/message-types]] §5 — Wire vocabulary.
- [[concepts/node-model]] §6, §8 — Handler surface and per-Node RNG contract.
- [[concepts/network-model]] — Delivery semantics (broadcast-excludes-sender).
- [[concepts/reproducibility]] — `(global_seed, node_id)` per-Node RNG seeding.
- [[algorithms/avalanche]] §Snowman, §Probabilistic safety — Mechanism.

**Outbound (T38 unblocks or feeds):**

- **T36.1** (Chapter 3 Snowman prose) — `[!]` Blocked → actionable on T38
  landing.
- **T40** (unified output CSV) — Snowman column added when T40 picks up.
- **T41–T55** (W8–W10 experiments) — Three-protocol comparative sweep
  becomes runnable.
- **T18 / T51–T53** — Adversarial Snowman extensions plug into the
  `SnowmanNode` handler surface T38 lands.
- **T38.1** (Narwhal+Tusk) — Follows T38 as the fourth protocol, between T55
  and T57.

## 12. Implementation checklist (for the plan phase)

The implementation plan (`superpowers:writing-plans`) will sequence these.
Order chosen so each step is testable before moving on:

1. `src/snowman/parameters.py` + `tests/snowman/test_parameters.py`
   (smallest module; pins the rescaling rule).
2. `src/snowman/messages.py` + `tests/snowman/test_messages.py` (pure
   dataclasses).
3. `src/snowman/block.py` + `tests/snowman/test_block.py` (`Block`,
   `hash_block`, `ConflictSet`, `Chain`).
4. `src/snowman/poll.py` + `tests/snowman/test_poll.py` (`Poll`,
   `on_response`, `close_round`).
5. `src/snowman/node.py` + `tests/snowman/_helpers.py` + the six
   `test_node_*.py` files including `test_node_flip.py`.
6. Makefile suite registration (`snowman` added to `SUITES`).
7. `tests/integration/test_snowman_baseline.py` (four outcomes).
8. `wiki/experiments/2026-05-27_snowman-baseline.md`.
9. `## Revisions` entries on `system-design-protocols.md` and
   `message-types.md`.
10. `wiki/index.md` + `wiki/log.md` updates.

Each step ends with `make test-<suite>` green before moving on. Final
step before flipping to In Review: `make test` runs all eight suites green
(scheduler, nodes, network, event_log, config, pbft, pos, snowman,
integration), per
`superpowers:verification-before-completion`.
