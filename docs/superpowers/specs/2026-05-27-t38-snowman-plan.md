# T38 — Snowman Honest-Path Baseline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to
> implement this plan task-by-task. Drive each task with
> superpowers:test-driven-development.

**Goal:** Build a new `src/snowman/` package implementing the honest-path
Snowman protocol from `[ava-docs]` — a `SnowmanNode` validator that
proposes blocks on a slot schedule, runs the full Snowball engine (per-block
confidence + α_p preference-flip + α_c counter-increment), accepts at β
consecutive successes, and emits the mandatory `decided` event. Land an
honest-path build-verification baseline at `n ∈ {4, 7, 10}` with
byte-identical determinism, mirroring T30 (PBFT) and T35 (Casper FFG).

**Architecture:** A `SnowmanNode(Node)` subclass mirroring `src/pos/`. Each
node runs an indefinite slot loop (`"slot"` timer at `slot_duration`),
with round-robin proposer `slot % n` emitting `BLOCK-ANNOUNCEMENT`s that
extend the local chain tip. For every announced block, a per-block poll
loop runs concurrently: each round samples K peers, sends `QUERY`s, and
accumulates `QUERY-RESPONSE`s into a `Poll` keyed by `(block_id,
request_id)`. The round closes on the **success-path early trigger**
`agree[current_pref] ≥ α_c` (provably flip-safe because `α_p + α_c > K`)
or on quorum (`responses == K`); the Snowball update applies on close, and
the block is ACCEPTED once `counter ≥ β`. No slashing, no view changes,
no fork choice — honest-path linear chain.

**Design spec:** `docs/superpowers/specs/2026-05-27-t38-snowman-design.md`
— read it before starting; this plan references its sections.

**Tech Stack:** Python 3, stdlib `unittest` and `hashlib`, the
discrete-event simulator (`src/scheduler`, `src/nodes`, `src/network`,
`src/event_log`, `src/config`).

**Test commands:**
- Unit (one test): `PYTHONPATH=src:tests/snowman python3 -m unittest <module>.<Class>.<test> -v`
- Unit (snowman suite): `PYTHONPATH=src:tests/snowman python3 -m unittest discover -s tests/snowman -v`
- Integration: `PYTHONPATH=src:tests/integration python3 -m unittest test_snowman_baseline -v`
- Or via Makefile once Task 1 lands: `make test-snowman`, `make test`.

**Commits:** Per `docs/workflow.md` and the T32 precedent, the entire T38
implementation lands as **one commit** (`task 38: implement Snowman
honest-path baseline`) at the In-Review flip. The `task 38: start` commit
is already on the branch (the design spec + plan land before it on the
same human commit). This plan has **no per-task `git commit` steps**;
Task 14 is the single commit/handoff checkpoint, executed by the human.

**Regression watch:** T38 creates a brand-new package and a new test
suite; it modifies no existing `src/` file. The only edits outside
`src/snowman/` and `tests/snowman/` are the `Makefile` (Task 1, additive),
one new integration test (Task 12), three wiki edits (Task 13), and
`TASKS.md` (Task 14, status flip). No existing test should change
behaviour — if an upstream suite breaks, stop and debug; do not edit
upstream tests.

**Node API reminder.** `SnowmanNode` inherits the `(node_id, weight,
endpoint, global_seed)` constructor signature from `src/nodes/node.py`.
Subclasses override `_on_start`, `_on_message`, `_on_timer` (note the
leading underscore — the public `start` / `on_message` / `on_timer`
wrappers in `Node` handle lifecycle gating and delegate). Per-Node RNG is
auto-derived from `(global_seed, node_id)` by `Node.__init__`; subclasses
use `self.rng` directly.

**Spec divergence captured here:** the design spec §6.1 listed
constructor params with `rng: random.Random | None` — that was authored
against the conceptual API; the implementation uses the inherited
`global_seed` argument and lets `Node.__init__` derive `self.rng`. The
public effect is identical (same RNG seed → byte-identical sampling). No
change to behaviour; the Task 8 + Task 9 constructor signatures in this
plan are authoritative.

---

## Task 1: Package and test-suite scaffolding

Create the `src/snowman/` package, the `tests/snowman/` suite directory,
and wire the suite into the `Makefile`.

**Files:**
- Create: `src/snowman/__init__.py`
- Create: `tests/snowman/__init__.py`
- Modify: `Makefile` (the `SUITES` line)

**Step 1: Create the package files**

`src/snowman/__init__.py` — module docstring only for now ("Snowman
honest-path consensus — T38."). Exports are added in Task 9.
`tests/snowman/__init__.py` — empty (package marker, matches
`tests/pos/__init__.py`).

**Step 2: Wire the Makefile**

In `Makefile`, change the `SUITES` line to add `snowman` between `pos`
and `integration`:

```
SUITES        = scheduler nodes network event_log config pbft pos snowman integration
```

**Step 3: Verify discoverability**

Run: `make test-snowman`
Expected: `Ran 0 tests in ...s` / `OK` — empty suite, discovery succeeds.
Exit status 0.

---

## Task 2: `parameters.py` — rescaling-rule pure function

Design spec §7. Smallest module; pins the rescaling rule and the
early-close safety invariant.

**Files:**
- Create: `src/snowman/parameters.py`
- Test: `tests/snowman/test_parameters.py`

**Step 1: Write the failing test**

Create `tests/snowman/test_parameters.py`:

```python
"""Tests for the Snowman parameter rescaling rule (design spec §7)."""
import math
import unittest

from snowman.parameters import snowman_parameters


class TestSnowmanParametersTable(unittest.TestCase):
    """The exact five-row table from metric-reconciliation.md."""

    EXPECTED = {
        4:  (3,  2,  3),
        7:  (6,  4,  5),
        10: (9,  5,  8),
        16: (15, 8, 12),
        25: (20, 11, 16),
    }

    def test_table(self):
        for n, expected in self.EXPECTED.items():
            with self.subTest(n=n):
                self.assertEqual(snowman_parameters(n), expected)


class TestEarlyCloseSafetyInvariant(unittest.TestCase):
    """alpha_p + alpha_c > K for every K used by the simulator.

    Section 5 of the design spec relies on this invariant for
    success-path early-close to be flip-safe. If a future rescaling-rule
    change breaks the invariant, this test fails immediately.
    """

    def test_invariant_holds_for_thesis_n_range(self):
        for n in range(2, 22):
            with self.subTest(n=n):
                K, alpha_p, alpha_c = snowman_parameters(n)
                self.assertGreater(
                    alpha_p + alpha_c, K,
                    f"alpha_p+alpha_c > K violated at n={n}: "
                    f"K={K}, alpha_p={alpha_p}, alpha_c={alpha_c}")


class TestPreconditions(unittest.TestCase):
    def test_n_below_two_raises(self):
        for bad_n in (-1, 0, 1):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    snowman_parameters(bad_n)


class TestProductionParity(unittest.TestCase):
    """At n=25, (K, alpha_p, alpha_c) matches [ava-docs] exactly."""

    def test_n_25_matches_avalanche_production(self):
        self.assertEqual(snowman_parameters(25), (20, 11, 16))


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_parameters -v`
Expected: ModuleNotFoundError (`snowman.parameters` doesn't exist).

**Step 3: Write the implementation**

Create `src/snowman/parameters.py`:

```python
"""Snowman parameter rescaling rule.

See wiki/concepts/metric-reconciliation.md §Snowman parameter rescaling
for the derivation. The thesis sweeps n in {4, 7, 10, 16, 25}, well below
the production validator count of ~1000 that the Avalanche docs'
(K, alpha_p, alpha_c, beta) = (20, 11, 16, 15) assumes. Production K=20
is incoherent for n < 21. The rule below is the only rescaling used; it
is deterministic in n and reproducible across seeds.

beta is held constant at the production value (15) and is supplied
separately by the caller (SnowmanNode.__init__).
"""
from __future__ import annotations
import math


def snowman_parameters(n: int) -> tuple[int, int, int]:
    """Return (K, alpha_p, alpha_c) for a validator set of size n.

    Preconditions: n >= 2 (a single-node "network" has no peers to sample).
    """
    if n < 2:
        raise ValueError(f"snowman_parameters: n must be >= 2, got {n}")
    K = min(20, n - 1)
    alpha_p = K // 2 + 1
    alpha_c = math.ceil(0.8 * K)
    return K, alpha_p, alpha_c
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_parameters -v`
Expected: 4 tests pass (one `subTest`-driven table check, the invariant
check, the precondition check, and the production-parity check). All OK.

---

## Task 3: `messages.py` — payload dataclasses

Design spec §3. Three frozen dataclasses; no signature fields, matching
[[concepts/message-types]] §5.

**Files:**
- Create: `src/snowman/messages.py`
- Test: `tests/snowman/test_messages.py`

**Step 1: Write the failing test**

Create `tests/snowman/test_messages.py`:

```python
"""Tests for Snowman message payloads (design spec §3)."""
import dataclasses
import unittest

from snowman.messages import (
    BlockAnnouncementPayload,
    QueryPayload,
    QueryResponsePayload,
)


class TestBlockAnnouncementPayload(unittest.TestCase):
    def test_fields(self):
        p = BlockAnnouncementPayload(
            slot=3,
            block_id=b"b" * 32,
            parent_id=b"\x00" * 32,
            transactions=(b"tx1", b"tx2"),
            proposer_idx=1,
        )
        self.assertEqual(p.slot, 3)
        self.assertEqual(p.block_id, b"b" * 32)
        self.assertEqual(p.parent_id, b"\x00" * 32)
        self.assertEqual(p.transactions, (b"tx1", b"tx2"))
        self.assertEqual(p.proposer_idx, 1)

    def test_frozen(self):
        p = BlockAnnouncementPayload(
            slot=0, block_id=b"x"*32, parent_id=b"\x00"*32,
            transactions=(), proposer_idx=0)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            p.slot = 99  # type: ignore[misc]


class TestQueryPayload(unittest.TestCase):
    def test_fields(self):
        q = QueryPayload(request_id=7, block_id=b"a" * 32)
        self.assertEqual(q.request_id, 7)
        self.assertEqual(q.block_id, b"a" * 32)

    def test_frozen(self):
        q = QueryPayload(request_id=0, block_id=b"a"*32)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            q.request_id = 1  # type: ignore[misc]


class TestQueryResponsePayload(unittest.TestCase):
    def test_fields(self):
        r = QueryResponsePayload(request_id=7, preferred_block_id=b"b" * 32)
        self.assertEqual(r.request_id, 7)
        self.assertEqual(r.preferred_block_id, b"b" * 32)

    def test_frozen(self):
        r = QueryResponsePayload(request_id=0, preferred_block_id=b"a"*32)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r.request_id = 1  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_messages -v`
Expected: ModuleNotFoundError (`snowman.messages` doesn't exist).

**Step 3: Write the implementation**

Create `src/snowman/messages.py`:

```python
"""Snowman message payloads (design spec §3, wiki/concepts/message-types §5).

Three wire payload types. The shared Message envelope (src, dst, type,
payload, t_sent) is owned by nodes/message.py and is not redeclared here.

Per design spec §3, signature fields are omitted: the simulator passes
Python objects, not signed bytes, and performs no signature verification.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlockAnnouncementPayload:
    slot: int
    block_id: bytes              # 32-byte SHA-256 hash (see block.hash_block)
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

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_messages -v`
Expected: 6 tests pass.

---

## Task 4: `block.py` — `Block` + `hash_block`

Design spec §4. The pure block dataclass and its deterministic hash.

**Files:**
- Create: `src/snowman/block.py`
- Test: `tests/snowman/test_block.py`

**Step 1: Write the failing test**

Create `tests/snowman/test_block.py`:

```python
"""Tests for block.py (design spec §4) — Block + hash_block."""
import unittest

from snowman.block import Block, GENESIS_ID, hash_block


class TestGenesisId(unittest.TestCase):
    def test_is_32_zero_bytes(self):
        self.assertEqual(GENESIS_ID, b"\x00" * 32)


class TestBlock(unittest.TestCase):
    def test_fields(self):
        b = Block(block_id=b"x"*32, parent_id=GENESIS_ID, slot=1,
                  proposer_idx=0, transactions=(b"tx",))
        self.assertEqual(b.slot, 1)
        self.assertEqual(b.parent_id, GENESIS_ID)


class TestHashBlock(unittest.TestCase):
    def test_deterministic(self):
        h1 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=(b"tx1",))
        h2 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=(b"tx1",))
        self.assertEqual(h1, h2)

    def test_32_bytes(self):
        h = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                       transactions=())
        self.assertEqual(len(h), 32)

    def test_distinguishes_slot(self):
        h1 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=())
        h2 = hash_block(slot=2, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=())
        self.assertNotEqual(h1, h2)

    def test_distinguishes_parent(self):
        h1 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=())
        h2 = hash_block(slot=1, parent_id=b"\x01"*32, proposer_idx=0,
                        transactions=())
        self.assertNotEqual(h1, h2)

    def test_distinguishes_proposer(self):
        h1 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=())
        h2 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=1,
                        transactions=())
        self.assertNotEqual(h1, h2)

    def test_distinguishes_transactions(self):
        h1 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=(b"a",))
        h2 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=(b"b",))
        self.assertNotEqual(h1, h2)

    def test_distinguishes_tx_count_via_length_prefix(self):
        """(b'ab',) must not collide with (b'a', b'b') — length-prefixed."""
        h1 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=(b"ab",))
        h2 = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=0,
                        transactions=(b"a", b"b"))
        self.assertNotEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_block -v`
Expected: ModuleNotFoundError.

**Step 3: Write the implementation**

Create `src/snowman/block.py` (the `ConflictSet` and `Chain` classes are
added in later tasks; this task lands only the `Block` dataclass + hash):

```python
"""Snowman per-block state (design spec §4).

This file lands in three slices: this task adds the Block dataclass and
hash_block; Task 5 adds ConflictSet; Task 6 adds Chain.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass

GENESIS_ID: bytes = b"\x00" * 32


@dataclass(frozen=True)
class Block:
    block_id: bytes              # 32-byte SHA-256, see hash_block()
    parent_id: bytes
    slot: int
    proposer_idx: int
    transactions: tuple[bytes, ...]


def hash_block(
    *,
    slot: int,
    parent_id: bytes,
    proposer_idx: int,
    transactions: tuple[bytes, ...],
) -> bytes:
    """Deterministic SHA-256 over a canonical length-prefixed encoding.

    Encoding (all integers big-endian, fixed width):
      uint64 slot || bytes(32) parent_id || uint32 proposer_idx
      || uint32 n_tx || (uint32 len || bytes len) for each tx
    """
    if len(parent_id) != 32:
        raise ValueError(f"parent_id must be 32 bytes, got {len(parent_id)}")
    h = hashlib.sha256()
    h.update(struct.pack(">Q", slot))
    h.update(parent_id)
    h.update(struct.pack(">I", proposer_idx))
    h.update(struct.pack(">I", len(transactions)))
    for tx in transactions:
        h.update(struct.pack(">I", len(tx)))
        h.update(tx)
    return h.digest()
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_block -v`
Expected: 9 tests pass.

---

## Task 5: `block.py` — `ConflictSet`

Design spec §4. Snowball state for blocks sharing one `parent_id`.

**Files:**
- Modify: `src/snowman/block.py` (extend)
- Modify: `tests/snowman/test_block.py` (extend)

**Step 1: Write the failing tests**

Append to `tests/snowman/test_block.py`:

```python
from snowman.block import CSState, ConflictSet


class TestConflictSet(unittest.TestCase):
    def _block(self, block_id: bytes, parent_id: bytes = GENESIS_ID,
               slot: int = 1) -> Block:
        return Block(block_id=block_id, parent_id=parent_id, slot=slot,
                     proposer_idx=0, transactions=())

    def test_initial_state(self):
        cs = ConflictSet(parent_id=GENESIS_ID)
        self.assertEqual(cs.members, {})
        self.assertEqual(cs.confidence, {})
        self.assertEqual(cs.preference, b"")
        self.assertEqual(cs.counter, 0)
        self.assertIs(cs.state, CSState.POLLING)

    def test_first_block_becomes_preference(self):
        cs = ConflictSet(parent_id=GENESIS_ID)
        b = self._block(b"a" * 32)
        cs.add_block(b)
        self.assertEqual(cs.preference, b"a" * 32)
        self.assertIn(b"a" * 32, cs.members)
        self.assertEqual(cs.confidence[b"a" * 32], 0)

    def test_second_block_does_not_change_preference(self):
        cs = ConflictSet(parent_id=GENESIS_ID)
        cs.add_block(self._block(b"a" * 32))
        cs.add_block(self._block(b"b" * 32))
        self.assertEqual(cs.preference, b"a" * 32)
        self.assertIn(b"b" * 32, cs.members)

    def test_idempotent_re_add(self):
        cs = ConflictSet(parent_id=GENESIS_ID)
        b = self._block(b"a" * 32)
        cs.add_block(b)
        cs.add_block(b)
        self.assertEqual(len(cs.members), 1)
        self.assertEqual(cs.confidence[b"a" * 32], 0)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_block.TestConflictSet -v`
Expected: ImportError (`CSState`, `ConflictSet` missing).

**Step 3: Extend the implementation**

Append to `src/snowman/block.py`:

```python
from dataclasses import field
from enum import Enum


class CSState(Enum):
    POLLING = "polling"
    ACCEPTED = "accepted"


@dataclass
class ConflictSet:
    """Snowball state for all blocks claiming one parent_id.

    confidence[b] is the monotonic per-block accumulator (Snowball's
    "highest-confidence preference" semantics): incremented every round
    where b is the round's majority block with count >= alpha_p.
    counter is the *consecutive* alpha_c-hits on the current preference;
    reset on a flip or on an alpha_c miss. state transitions to ACCEPTED
    when counter >= beta.
    """
    parent_id: bytes
    members: dict[bytes, "Block"] = field(default_factory=dict)
    confidence: dict[bytes, int] = field(default_factory=dict)
    preference: bytes = b""
    counter: int = 0
    state: CSState = CSState.POLLING

    def add_block(self, block: "Block") -> None:
        """First block added becomes the initial preference."""
        if block.block_id in self.members:
            return
        self.members[block.block_id] = block
        self.confidence.setdefault(block.block_id, 0)
        if self.preference == b"":
            self.preference = block.block_id
```

(Note: also add `from dataclasses import field` and `from enum import Enum`
to the imports at the top of the file.)

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_block -v`
Expected: 13 tests pass (9 from Task 4 + 4 new).

---

## Task 6: `block.py` — `Chain`

Design spec §4. Linear chain bookkeeping for the proposer.

**Files:**
- Modify: `src/snowman/block.py` (extend)
- Modify: `tests/snowman/test_block.py` (extend)

**Step 1: Write the failing tests**

Append to `tests/snowman/test_block.py`:

```python
from snowman.block import Chain


class TestChain(unittest.TestCase):
    def _block(self, block_id: bytes, parent_id: bytes,
               slot: int = 1) -> Block:
        return Block(block_id=block_id, parent_id=parent_id, slot=slot,
                     proposer_idx=0, transactions=())

    def test_initial_tip_is_genesis(self):
        c = Chain()
        self.assertEqual(c.tip, GENESIS_ID)
        self.assertEqual(c.accepted, {})

    def test_on_announce_extends_tip(self):
        c = Chain()
        b1 = self._block(b"a" * 32, GENESIS_ID, slot=1)
        c.on_announce(b1)
        self.assertEqual(c.tip, b"a" * 32)
        b2 = self._block(b"b" * 32, b"a" * 32, slot=2)
        c.on_announce(b2)
        self.assertEqual(c.tip, b"b" * 32)

    def test_on_announce_with_unknown_parent_is_noop(self):
        """Out-of-order arrival; design spec §4 short-circuits."""
        c = Chain()
        orphan = self._block(b"a" * 32, parent_id=b"z" * 32, slot=2)
        c.on_announce(orphan)
        self.assertEqual(c.tip, GENESIS_ID)

    def test_on_announce_sibling_does_not_change_tip(self):
        """Two siblings of genesis; tip is the first one seen, not the
        deeper of two equal-depth blocks."""
        c = Chain()
        a = self._block(b"a" * 32, GENESIS_ID, slot=1)
        b = self._block(b"b" * 32, GENESIS_ID, slot=1)
        c.on_announce(a)
        c.on_announce(b)
        self.assertEqual(c.tip, b"a" * 32)

    def test_on_accept_records(self):
        c = Chain()
        b = self._block(b"a" * 32, GENESIS_ID, slot=1)
        c.on_announce(b)
        c.on_accept(b)
        self.assertEqual(c.accepted, {b"a" * 32: b})
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_block.TestChain -v`
Expected: ImportError (`Chain` missing).

**Step 3: Extend the implementation**

Append to `src/snowman/block.py`:

```python
class Chain:
    """Linear chain bookkeeping for the proposer.

    Tracks the depth of every seen block — used to identify the tip that
    the slot proposer extends — and the set of ACCEPTED blocks (used by
    the build-verification assertion). Out-of-order arrivals (a block
    whose parent has not been seen) short-circuit; T46–T50 will revisit.
    """

    def __init__(self) -> None:
        self.accepted: dict[bytes, Block] = {}
        self.depth: dict[bytes, int] = {GENESIS_ID: 0}
        self.tip: bytes = GENESIS_ID

    def on_announce(self, block: Block) -> None:
        parent_depth = self.depth.get(block.parent_id)
        if parent_depth is None:
            return       # out-of-order; T46–T50 owns this
        if block.block_id in self.depth:
            return       # already recorded
        self.depth[block.block_id] = parent_depth + 1
        if self.depth[block.block_id] > self.depth[self.tip]:
            self.tip = block.block_id

    def on_accept(self, block: Block) -> None:
        self.accepted[block.block_id] = block
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_block -v`
Expected: 18 tests pass.

---

## Task 7: `poll.py` — `Poll` and `on_response`

Design spec §5. In-flight poll state + the success-path early-close
detector.

**Files:**
- Create: `src/snowman/poll.py`
- Test: `tests/snowman/test_poll.py`

**Step 1: Write the failing test**

Create `tests/snowman/test_poll.py`:

```python
"""Tests for poll.py (design spec §5) — Poll and on_response."""
import unittest

from snowman.poll import Poll, on_response


class TestPoll(unittest.TestCase):
    def test_initial_state(self):
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        self.assertEqual(p.peers, (1, 2, 3))
        self.assertEqual(p.agree_per_block, {})
        self.assertEqual(p.responses_received, 0)
        self.assertFalse(p.closed)


class TestOnResponseSuccessPath(unittest.TestCase):
    """Round closes when agree[current_pref] >= alpha_c."""

    def test_early_close_at_alpha_c(self):
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        # K=3, alpha_c=3 (n=4). Three responses all for current_pref close
        # the round on the third response.
        closed1 = on_response(poll=p, preferred_block_id=b"a"*32,
                              current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertFalse(closed1)
        self.assertEqual(p.responses_received, 1)
        closed2 = on_response(poll=p, preferred_block_id=b"a"*32,
                              current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertFalse(closed2)
        closed3 = on_response(poll=p, preferred_block_id=b"a"*32,
                              current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertTrue(closed3)
        self.assertTrue(p.closed)

    def test_no_close_when_below_alpha_c(self):
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3, 4, 5))
        # K=5, alpha_c=4. Three responses for current_pref + two for B.
        for _ in range(3):
            closed = on_response(poll=p, preferred_block_id=b"a"*32,
                                 current_preference=b"a"*32, alpha_c=4, K=5)
            self.assertFalse(closed)
        for _ in range(2):
            closed = on_response(poll=p, preferred_block_id=b"b"*32,
                                 current_preference=b"a"*32, alpha_c=4, K=5)
            self.assertFalse(closed)
        # 5 responses received, agree[A] = 3 < 4, no early close. Quorum-close
        # is handled at the SnowmanNode call site, not in on_response.
        self.assertEqual(p.responses_received, 5)
        self.assertFalse(p.closed)

    def test_closed_poll_drops_further_responses(self):
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        for _ in range(3):
            on_response(poll=p, preferred_block_id=b"a"*32,
                        current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertTrue(p.closed)
        closed = on_response(poll=p, preferred_block_id=b"a"*32,
                             current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertFalse(closed)
        # State unchanged.
        self.assertEqual(p.responses_received, 3)
        self.assertEqual(p.agree_per_block[b"a"*32], 3)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_poll -v`
Expected: ModuleNotFoundError.

**Step 3: Write the implementation**

Create `src/snowman/poll.py`:

```python
"""Snowman poll round (design spec §5).

A Poll is an in-flight round for one block_id; on_response records each
QUERY-RESPONSE and signals the success-path early-close trigger. The
Snowball update applied on round close (close_round) is added in Task 8.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Poll:
    """In-flight poll round for one block_id (design spec §5)."""
    block_id: bytes
    request_id: int
    peers: tuple[int, ...]
    agree_per_block: dict[bytes, int] = field(default_factory=dict)
    responses_received: int = 0
    closed: bool = False


def on_response(
    *,
    poll: Poll,
    preferred_block_id: bytes,
    current_preference: bytes,
    alpha_c: int,
    K: int,
) -> bool:
    """Record one QUERY-RESPONSE; return True iff the success-path
    early-close trigger fires.

    The caller closes the round on either (a) this returning True, or
    (b) poll.responses_received == K (quorum). On a closed Poll, this
    function is a no-op returning False.
    """
    if poll.closed:
        return False
    poll.agree_per_block[preferred_block_id] = (
        poll.agree_per_block.get(preferred_block_id, 0) + 1
    )
    poll.responses_received += 1
    if poll.agree_per_block.get(current_preference, 0) >= alpha_c:
        poll.closed = True
        return True
    return False
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_poll -v`
Expected: 4 tests pass.

---

## Task 8: `poll.py` — `close_round` (Snowball update)

Design spec §5. The three-step Snowball rule applied on round close:
α_p preference update, α_c counter update, β acceptance.

**Files:**
- Modify: `src/snowman/poll.py` (extend)
- Modify: `tests/snowman/test_poll.py` (extend)

**Step 1: Write the failing tests**

Append to `tests/snowman/test_poll.py`:

```python
from snowman.block import ConflictSet, CSState, Block, GENESIS_ID
from snowman.poll import PollOutcome, close_round


def _cs_with_block(block_id: bytes,
                   parent_id: bytes = GENESIS_ID) -> ConflictSet:
    cs = ConflictSet(parent_id=parent_id)
    cs.add_block(Block(block_id=block_id, parent_id=parent_id,
                       slot=1, proposer_idx=0, transactions=()))
    return cs


class TestCloseRoundAlphaCSuccess(unittest.TestCase):
    """Case (a): agree[current_pref] >= alpha_c, no flip."""

    def test_increments_counter_no_flip(self):
        cs = _cs_with_block(b"a"*32)
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        p.agree_per_block = {b"a"*32: 3}
        p.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertFalse(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"a"*32)
        self.assertEqual(outcome.counter, 1)
        self.assertFalse(outcome.accepted)
        self.assertEqual(cs.counter, 1)
        self.assertEqual(cs.confidence[b"a"*32], 1)


class TestCloseRoundAlphaPFlip(unittest.TestCase):
    """Case (b): a non-pref block hits alpha_p, current_pref does not hit
    alpha_c. Preference flips to the majority block, counter resets, and
    confidence[new_pref] increments."""

    def test_flip_resets_counter(self):
        cs = _cs_with_block(b"a"*32)
        cs.add_block(Block(block_id=b"b"*32, parent_id=GENESIS_ID, slot=1,
                           proposer_idx=1, transactions=()))
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        p.agree_per_block = {b"a"*32: 1, b"b"*32: 2}
        p.responses_received = 3
        # K=3, alpha_p=2, alpha_c=3.
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"b"*32)
        self.assertEqual(outcome.counter, 0)
        self.assertFalse(outcome.accepted)
        self.assertEqual(cs.preference, b"b"*32)
        self.assertEqual(cs.confidence[b"b"*32], 1)


class TestCloseRoundNoAlphaPHit(unittest.TestCase):
    """Case (c): no block hits alpha_p. Counter resets to 0; preference
    unchanged; confidence unchanged."""

    def test_no_flip_counter_resets(self):
        cs = _cs_with_block(b"a"*32)
        cs.add_block(Block(block_id=b"b"*32, parent_id=GENESIS_ID, slot=1,
                           proposer_idx=1, transactions=()))
        cs.counter = 4  # was advancing
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3, 4, 5))
        # K=5, alpha_p=3. Split 2-2-1; no block hits alpha_p.
        p.agree_per_block = {b"a"*32: 2, b"b"*32: 2, b"c"*32: 1}
        p.responses_received = 5
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=3, alpha_c=4, beta=15)
        self.assertFalse(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"a"*32)
        self.assertEqual(outcome.counter, 0)
        self.assertFalse(outcome.accepted)
        self.assertNotIn(b"c"*32, cs.confidence)  # confidence only bumps on >= alpha_p


class TestCloseRoundAcceptance(unittest.TestCase):
    """Counter reaches beta -> ACCEPTED."""

    def test_acceptance_at_beta(self):
        cs = _cs_with_block(b"a"*32)
        cs.counter = 14  # one shy of beta=15
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        p.agree_per_block = {b"a"*32: 3}
        p.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.counter, 15)
        self.assertIs(cs.state, CSState.ACCEPTED)


class TestCloseRoundTieBreak(unittest.TestCase):
    """Argmax tie-break: lowest block_id wins."""

    def test_tie_break_by_block_id(self):
        cs = _cs_with_block(b"\xff" * 32)  # high lex
        cs.add_block(Block(block_id=b"\x01" * 32, parent_id=GENESIS_ID,
                           slot=1, proposer_idx=1, transactions=()))
        p = Poll(block_id=b"\xff"*32, request_id=0, peers=(1, 2, 3, 4))
        # Two blocks tied at 2 each. Lowest block_id (b"\x01"*32) should win.
        p.agree_per_block = {b"\xff" * 32: 2, b"\x01" * 32: 2}
        p.responses_received = 4
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"\x01" * 32)
```

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_poll -v`
Expected: ImportError (`PollOutcome`, `close_round` missing).

**Step 3: Extend the implementation**

Append to `src/snowman/poll.py`:

```python
from .block import ConflictSet, CSState


@dataclass(frozen=True)
class PollOutcome:
    flipped: bool
    new_preference: bytes
    counter: int
    accepted: bool


def close_round(
    *,
    conflict_set: ConflictSet,
    poll: Poll,
    alpha_p: int,
    alpha_c: int,
    beta: int,
) -> PollOutcome:
    """Apply the full Snowball update for one closed round (design spec §5).

    Three-step rule:
      1. Identify majority block b* = argmax agree_per_block. Tie-break:
         highest count, then lowest block_id bytes (lex). If
         count_majority >= alpha_p AND b* != current preference, flip
         preference to b* and reset counter to 0. Increment confidence[b*]
         regardless of flip.
      2. Check agree[preference] against alpha_c; if >=, counter += 1;
         else counter = 0.
      3. If counter >= beta, state -> ACCEPTED.
    """
    poll.closed = True

    # Step 1: majority + alpha_p
    majority_block, count_majority = min(
        poll.agree_per_block.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )
    flipped = False
    if count_majority >= alpha_p:
        if majority_block != conflict_set.preference:
            conflict_set.preference = majority_block
            conflict_set.counter = 0
            flipped = True
        conflict_set.confidence[majority_block] = (
            conflict_set.confidence.get(majority_block, 0) + 1
        )

    # Step 2: alpha_c on the (possibly-new) preference
    pref_agree = poll.agree_per_block.get(conflict_set.preference, 0)
    if pref_agree >= alpha_c:
        conflict_set.counter += 1
    else:
        conflict_set.counter = 0

    # Step 3: beta -> ACCEPTED
    accepted = False
    if (conflict_set.counter >= beta
            and conflict_set.state is CSState.POLLING):
        conflict_set.state = CSState.ACCEPTED
        accepted = True

    return PollOutcome(
        flipped=flipped,
        new_preference=conflict_set.preference,
        counter=conflict_set.counter,
        accepted=accepted,
    )
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_poll -v`
Expected: 9 tests pass.

---

## Task 9: `node.py` — `SnowmanNode.__init__` + `_on_start` + slot proposer

Design spec §6.1, §6.2, §6.3 (proposer half). Constructor + slot-loop +
round-robin proposer. The message handlers and poll-loop wiring land in
Tasks 10–11.

**Files:**
- Create: `src/snowman/node.py`
- Create: `tests/snowman/_helpers.py`
- Test: `tests/snowman/test_node_init.py`
- Test: `tests/snowman/test_node_propose.py`

**Step 1: Write `_helpers.py`**

Create `tests/snowman/_helpers.py`:

```python
"""Shared test fixtures for tests/snowman/.

Builds a minimal Scheduler + Network + n SnowmanNodes, drives one run to
quiescence, and exposes the captured event stream for inspection.
"""
from __future__ import annotations

from event_log.logger import EventLogger
from network.network import Network
from network.phases import ConstantDelay, NetworkPhase
from scheduler.scheduler import Scheduler

from snowman.node import SnowmanNode


def build_harness(*, n: int, global_seed: int = 42,
                  slot_duration: float = 1.0, beta: int = 15,
                  t_max: float = 20.0, delay: float = 1e-9):
    """Wire up scheduler + network + n SnowmanNodes; return (sched, net,
    nodes, logger). The harness is NOT started; caller drives sched.run."""
    logger = EventLogger()
    sched = Scheduler(event_sink=logger.handle)
    phase = NetworkPhase(
        t_start=0.0, t_end=float("inf"),
        delay=ConstantDelay(delay), drop_rate=0.0, partitions=())
    net = Network(timeline=(phase,), global_seed=global_seed)
    nodes = []
    for node_id in range(n):
        node = SnowmanNode(
            node_id=node_id, weight=1.0,
            endpoint=object(), global_seed=global_seed,
            n=n, slot_duration=slot_duration, beta=beta)
        net.register(node)
        sched.bind(node)
        nodes.append(node)
    net.start()
    return sched, net, nodes, logger
```

(If the actual `EventLogger` / `Network` / `Scheduler` constructor signatures
differ from the above stubs, follow `tests/pos/_helpers.py` and
`tests/integration/test_pos_baseline.py` as authoritative templates and
adapt.)

**Step 2: Write the failing init test**

Create `tests/snowman/test_node_init.py`:

```python
"""SnowmanNode constructor and rescaled-parameter defaults (design spec §6.1)."""
import unittest

from snowman.node import SnowmanNode


class TestInitRescaledDefaults(unittest.TestCase):
    def test_n_4_defaults(self):
        node = SnowmanNode(node_id=0, weight=1.0, endpoint=object(),
                           global_seed=42, n=4)
        self.assertEqual(node.n, 4)
        self.assertEqual(node.K, 3)
        self.assertEqual(node.alpha_p, 2)
        self.assertEqual(node.alpha_c, 3)
        self.assertEqual(node.beta, 15)

    def test_n_7_defaults(self):
        node = SnowmanNode(node_id=3, weight=1.0, endpoint=object(),
                           global_seed=42, n=7)
        self.assertEqual((node.K, node.alpha_p, node.alpha_c), (6, 4, 5))

    def test_n_10_defaults(self):
        node = SnowmanNode(node_id=0, weight=1.0, endpoint=object(),
                           global_seed=42, n=10)
        self.assertEqual((node.K, node.alpha_p, node.alpha_c), (9, 5, 8))

    def test_explicit_override(self):
        node = SnowmanNode(node_id=0, weight=1.0, endpoint=object(),
                           global_seed=42, n=4,
                           K=2, alpha_p=2, alpha_c=2, beta=3)
        self.assertEqual((node.K, node.alpha_p, node.alpha_c, node.beta),
                         (2, 2, 2, 3))


class TestInitPreconditions(unittest.TestCase):
    def test_n_below_two_rejected(self):
        for bad_n in (-1, 0, 1):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    SnowmanNode(node_id=0, weight=1.0, endpoint=object(),
                                global_seed=42, n=bad_n)

    def test_node_id_outside_range_rejected(self):
        with self.assertRaises(ValueError):
            SnowmanNode(node_id=5, weight=1.0, endpoint=object(),
                        global_seed=42, n=4)

    def test_slot_duration_nonpositive_rejected(self):
        with self.assertRaises(ValueError):
            SnowmanNode(node_id=0, weight=1.0, endpoint=object(),
                        global_seed=42, n=4, slot_duration=0)


if __name__ == "__main__":
    unittest.main()
```

**Step 3: Write the failing propose test**

Create `tests/snowman/test_node_propose.py`:

```python
"""Round-robin proposer + slot timer (design spec §6.2, §6.3)."""
import unittest

from _helpers import build_harness


class TestSlotProposer(unittest.TestCase):
    def test_round_robin_proposer_for_n_4(self):
        """At n=4, node 0 proposes slot 0, node 1 slot 1, etc."""
        sched, _, nodes, logger = build_harness(n=4, t_max=5.0)
        sched.run(t_max=5.0)
        # Filter snowman_announced events that the proposer self-recorded.
        announces = [e for e in logger.records
                     if e.event_type == "snowman_announced"]
        # Each slot is proposed by one node and announced by every node
        # (the proposer self-records, the others receive the broadcast).
        # Within a slot, proposer_idx should match slot % n.
        by_slot: dict[int, set[int]] = {}
        for a in announces:
            by_slot.setdefault(a.fields["slot"], set()).add(
                a.fields["proposer_idx"])
        for slot, proposers in by_slot.items():
            self.assertEqual(proposers, {slot % 4},
                             f"slot {slot} proposer mismatch: {proposers}")

    def test_slot_timer_rearms(self):
        """The slot timer fires every slot_duration; t_max=3.0 with
        slot_duration=1.0 fires slots 0, 1, 2."""
        sched, _, nodes, logger = build_harness(n=4, t_max=3.0)
        sched.run(t_max=3.0)
        announce_slots = {
            e.fields["slot"] for e in logger.records
            if e.event_type == "snowman_announced"
            and e.fields.get("proposer_idx") == e.node_id
        }
        self.assertIn(0, announce_slots)
        self.assertIn(1, announce_slots)
        self.assertIn(2, announce_slots)


if __name__ == "__main__":
    unittest.main()
```

**Step 4: Run tests to verify they fail**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_node_init test_node_propose -v`
Expected: ModuleNotFoundError (`snowman.node` doesn't exist).

**Step 5: Write the implementation (partial — constructor + slot loop only)**

Create `src/snowman/node.py`:

```python
"""SnowmanNode (design spec §6).

Implements the honest-path Snowman protocol over the W3 stack:
  - Constructor + slot loop + round-robin proposer (Task 9, this file).
  - BLOCK-ANNOUNCEMENT handling + poll-loop bootstrap (Task 10).
  - QUERY / QUERY-RESPONSE handling + poll-round close + acceptance (Task 11).
"""
from __future__ import annotations

import random
from collections.abc import Sequence
from typing import Any

from nodes.message import Message
from nodes.node import Node

from .block import GENESIS_ID, Block, Chain, ConflictSet, hash_block
from .messages import BlockAnnouncementPayload
from .parameters import snowman_parameters
from .poll import Poll

POLL_DELAY: float = 1e-9


class SnowmanNode(Node):
    def __init__(
        self,
        node_id: int,
        weight: float,
        endpoint: object,
        global_seed: int,
        *,
        n: int,
        slot_duration: float = 1.0,
        beta: int = 15,
        K: int | None = None,
        alpha_p: int | None = None,
        alpha_c: int | None = None,
        workload: Sequence[bytes] | None = None,
    ) -> None:
        super().__init__(node_id, weight, endpoint, global_seed)
        if n < 2:
            raise ValueError(f"n must be >= 2, got {n}")
        if not 0 <= node_id < n:
            raise ValueError(f"node_id {node_id} outside [0, {n})")
        if slot_duration <= 0:
            raise ValueError(
                f"slot_duration must be positive, got {slot_duration}")
        K_d, p_d, c_d = snowman_parameters(n)
        self.n = n
        self.K = K if K is not None else K_d
        self.alpha_p = alpha_p if alpha_p is not None else p_d
        self.alpha_c = alpha_c if alpha_c is not None else c_d
        self.beta = beta
        self.slot_duration = slot_duration
        self.workload: list[bytes] = list(workload or [])
        self._workload_cursor = 0

        self.chain: Chain = Chain()
        self.conflict_sets: dict[bytes, ConflictSet] = {}
        self.polls: dict[bytes, Poll] = {}
        self._next_request_id = 0
        self._peers_minus_self_cache: tuple[int, ...] | None = None

    # --- Lifecycle (design spec §6.2). ---

    def _on_start(self, t: float) -> None:
        """Arm slot 0 at slot_duration."""
        self.set_timer("slot", self.slot_duration, 0, t)

    def _on_message(self, msg: Message, t: float) -> None:
        # BLOCK-ANNOUNCEMENT lands in Task 10; QUERY / QUERY-RESPONSE in
        # Task 11. Until then, drop everything as unknown.
        self._reject(reason="unknown_type", t=t, msg_type=msg.type)

    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        if timer_id == "slot":
            slot = payload
            if slot % self.n == self.id:
                self._propose(slot, t)
            self.set_timer("slot", self.slot_duration, slot + 1, t)
        # ("poll", block_id) handling lands in Task 11.

    # --- Proposer (design spec §6.3). ---

    def _propose(self, slot: int, t: float) -> None:
        """Build, announce, and self-record a new block at this slot."""
        parent_id = self.chain.tip
        if self._workload_cursor < len(self.workload):
            tx = (self.workload[self._workload_cursor],)
            self._workload_cursor += 1
        else:
            tx = ()
        block_id = hash_block(slot=slot, parent_id=parent_id,
                              proposer_idx=self.id, transactions=tx)
        block = Block(block_id=block_id, parent_id=parent_id, slot=slot,
                      proposer_idx=self.id, transactions=tx)
        payload = BlockAnnouncementPayload(
            slot=slot, block_id=block_id, parent_id=parent_id,
            transactions=tx, proposer_idx=self.id)
        # Self-record before broadcast (Network.broadcast excludes sender).
        self._record_announce(block, t)
        self.broadcast("BLOCK-ANNOUNCEMENT", payload, t)

    def _record_announce(self, block: Block, t: float) -> None:
        """Single source for "I now know about this block" — used by the
        proposer self-record path and by Task 10's BLOCK-ANNOUNCEMENT
        handler."""
        cs = self.conflict_sets.setdefault(
            block.parent_id, ConflictSet(parent_id=block.parent_id))
        cs.add_block(block)
        self.chain.on_announce(block)
        self.emit("snowman_announced",
                  {"block_id": block.block_id, "parent_id": block.parent_id,
                   "slot": block.slot, "proposer_idx": block.proposer_idx}, t)
        # First-poll arming for this block lands in Task 11.

    # --- Reject helper (mirrors src/pos and src/pbft). ---

    def _reject(self, *, reason: str, t: float, **fields) -> None:
        self.emit("snowman_rejected", {"reason": reason, **fields}, t)
```

**Step 6: Run tests to verify they pass**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_node_init test_node_propose -v`
Expected: 10 tests pass (7 init + 2 propose). Note: `test_node_propose`
relies on the `_helpers.build_harness` fixture; if its imports are off,
adapt against `tests/pos/_helpers.py`.

---

## Task 10: `node.py` — `BLOCK-ANNOUNCEMENT` handling + first-poll arming

Design spec §6.3. Add the inbound message handler and arm the first
poll round per block.

**Files:**
- Modify: `src/snowman/node.py`
- Test: `tests/snowman/test_node_announce.py`

**Step 1: Write the failing test**

Create `tests/snowman/test_node_announce.py`:

```python
"""BLOCK-ANNOUNCEMENT handling (design spec §6.3)."""
import unittest

from _helpers import build_harness


class TestBlockAnnouncement(unittest.TestCase):
    def test_first_announce_creates_conflict_set(self):
        sched, _, nodes, logger = build_harness(n=4, t_max=1.5)
        sched.run(t_max=1.5)
        # All four nodes should have at least one ConflictSet by t=1.5
        # (slot 0 fires at t=1.0; proposer announces; delivery at t=1+1e-9).
        for node in nodes:
            self.assertGreaterEqual(len(node.conflict_sets), 1,
                f"node {node.id} has no conflict sets")

    def test_announce_arms_poll_timer(self):
        sched, _, nodes, logger = build_harness(n=4, t_max=1.5)
        sched.run(t_max=1.5)
        # Each receiver should emit a snowman_poll_started for the announced
        # block within the slot.
        starts = [e for e in logger.records
                  if e.event_type == "snowman_poll_started"]
        self.assertGreater(len(starts), 0)

    def test_duplicate_announce_is_idempotent(self):
        # Drive the harness, capture state, manually re-deliver the same
        # announce; assert no new ConflictSet / no extra members.
        sched, _, nodes, logger = build_harness(n=4, t_max=1.5)
        sched.run(t_max=1.5)
        # Re-applying the same block to the conflict set should be a no-op
        # (covered by ConflictSet.add_block idempotency; this test asserts
        # the node handler is also idempotent).
        node = nodes[1]
        if not node.conflict_sets:
            self.skipTest("no announces reached this node")
        cs = next(iter(node.conflict_sets.values()))
        original_members = dict(cs.members)
        # Replay one block via _record_announce; size unchanged.
        block = next(iter(cs.members.values()))
        node._record_announce(block, t=2.0)
        self.assertEqual(cs.members, original_members)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_node_announce -v`
Expected: failures (`_on_message` currently rejects all messages).

**Step 3: Extend the implementation**

In `src/snowman/node.py`:

1. Replace `_on_message` with:

```python
def _on_message(self, msg: Message, t: float) -> None:
    if msg.type == "BLOCK-ANNOUNCEMENT":
        self._handle_announce(msg, t)
    # QUERY / QUERY-RESPONSE land in Task 11.
    else:
        self._reject(reason="unknown_type", t=t, msg_type=msg.type)
```

2. Add the handler:

```python
def _handle_announce(self, msg: Message, t: float) -> None:
    p = msg.payload
    if not isinstance(p, BlockAnnouncementPayload):
        self._reject(reason="malformed_payload", t=t, msg_type=msg.type)
        return
    block = Block(block_id=p.block_id, parent_id=p.parent_id,
                  slot=p.slot, proposer_idx=p.proposer_idx,
                  transactions=p.transactions)
    if block.block_id in self.polls:
        return       # duplicate; idempotent
    self._record_announce(block, t)
    # Arm the first poll round for this block.
    self.set_timer(("poll", block.block_id), POLL_DELAY, block.block_id, t)
```

3. Extend `_record_announce` to **not** double-arm if the block is already
   known (the proposer's self-record path also arms via this; protect against
   double-arm). Actually: `_propose` calls `_record_announce` and then must
   itself arm the poll. Simpler: have `_record_announce` arm the timer
   iff `block.block_id` is new to `self.polls`, then both paths call it:

```python
def _record_announce(self, block: Block, t: float) -> None:
    cs = self.conflict_sets.setdefault(
        block.parent_id, ConflictSet(parent_id=block.parent_id))
    if block.block_id in cs.members:
        return       # idempotent
    cs.add_block(block)
    self.chain.on_announce(block)
    self.emit("snowman_announced",
              {"block_id": block.block_id, "parent_id": block.parent_id,
               "slot": block.slot, "proposer_idx": block.proposer_idx}, t)
    # Arm the first poll round (Task 11 wires the timer handler).
    self.set_timer(("poll", block.block_id), POLL_DELAY, block.block_id, t)
```

Then `_handle_announce` no longer calls `set_timer` itself; remove that
line — only `_record_announce` arms the timer. And `_propose` no longer
needs to call `set_timer` either.

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_node_announce -v`
Expected: 3 tests pass. The `test_node_propose` tests from Task 9 should
still pass.

Run the whole suite to be sure:

Run: `make test-snowman`
Expected: All tests so far green.

---

## Task 11: `node.py` — poll round (QUERY / QUERY-RESPONSE + accept)

Design spec §6.3. Wire the per-block poll loop: timer fires, sample K
peers, send QUERY, collect QUERY-RESPONSE, close round on early-success
or quorum, apply Snowball update, emit `decided` on acceptance.

**Files:**
- Modify: `src/snowman/node.py`
- Test: `tests/snowman/test_node_query.py`
- Test: `tests/snowman/test_node_accept.py`

**Step 1: Write the failing tests (query handling)**

Create `tests/snowman/test_node_query.py`:

```python
"""QUERY + QUERY-RESPONSE handling (design spec §6.3)."""
import unittest

from _helpers import build_harness


class TestQuery(unittest.TestCase):
    def test_query_started_after_announce(self):
        sched, _, nodes, logger = build_harness(n=4, t_max=2.0)
        sched.run(t_max=2.0)
        starts = [e for e in logger.records
                  if e.event_type == "snowman_poll_started"]
        self.assertGreater(len(starts), 0)
        # Each poll samples K=3 peers (n=4).
        for s in starts:
            self.assertEqual(len(s.fields["peers"]), 3)
            # Self-exclusion: the polling node's id is not in peers.
            self.assertNotIn(s.node_id, s.fields["peers"])


class TestQueryResponse(unittest.TestCase):
    def test_stale_request_id_dropped(self):
        # Build harness; tamper with one node's poll to bump request_id;
        # construct a fresh QUERY-RESPONSE with the old id; assert no
        # snowman_poll_closed event is emitted.
        # (Implementation guidance only; the actual test uses the harness
        # event stream + manual node._on_message call to inject the stale
        # response. See tests/pos/test_node_block_handler.py for the
        # one-node-driven test pattern.)
        pass  # filled in during execution; the executor adapts to harness API


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Write the failing tests (acceptance)**

Create `tests/snowman/test_node_accept.py`:

```python
"""beta-acceptance and the decided event (design spec §6.3)."""
import unittest

from _helpers import build_harness


class TestAcceptance(unittest.TestCase):
    def test_decided_fires_after_beta_polls(self):
        """At n=4, beta=15, every announced block should reach decided in
        well under one slot (delay=1e-9, POLL_DELAY=1e-9 → ~30 ns per block)."""
        sched, _, nodes, logger = build_harness(n=4, t_max=3.0)
        sched.run(t_max=3.0)
        decided = [e for e in logger.records if e.event_type == "decided"]
        # Slot 0, 1, 2 announced → ~3 * 4 = 12 decided events (every node
        # decides every block). Allow some slack for timing edge cases.
        self.assertGreaterEqual(len(decided), 4)

    def test_no_forks_one_decided_value_per_slot(self):
        """For each slot's block, every node decides the same value."""
        sched, _, nodes, logger = build_harness(n=4, t_max=3.0)
        sched.run(t_max=3.0)
        decided = [e for e in logger.records if e.event_type == "decided"]
        # Group by instance_id (= block_id); all decided events for one
        # block must agree on `value`.
        by_block: dict[bytes, set[bytes]] = {}
        for d in decided:
            by_block.setdefault(d.fields["instance_id"], set()).add(
                d.fields["value"])
        for block_id, values in by_block.items():
            self.assertEqual(len(values), 1, f"fork at block {block_id!r}")

    def test_accepted_block_polls_stop(self):
        """After β-acceptance, no further snowman_poll_started for that block."""
        sched, _, nodes, logger = build_harness(n=4, t_max=3.0)
        sched.run(t_max=3.0)
        # Collect (node_id, block_id) -> number of poll-started events.
        poll_starts: dict[tuple[int, bytes], int] = {}
        decided_by: dict[tuple[int, bytes], None] = {}
        for e in logger.records:
            key = (e.node_id, e.fields.get("block_id"))
            if e.event_type == "snowman_poll_started":
                poll_starts[key] = poll_starts.get(key, 0) + 1
            elif e.event_type == "decided":
                decided_by[(e.node_id, e.fields["instance_id"])] = None
        # Every decided (node, block) should have exactly beta poll-starts.
        for (node_id, block_id) in decided_by:
            self.assertEqual(
                poll_starts.get((node_id, block_id)), 15,
                f"node {node_id} block {block_id!r} ran "
                f"{poll_starts.get((node_id, block_id))} polls, expected 15")


if __name__ == "__main__":
    unittest.main()
```

**Step 3: Run tests to verify they fail**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_node_query test_node_accept -v`
Expected: failures (no poll-loop wiring yet).

**Step 4: Extend the implementation**

In `src/snowman/node.py`:

1. Import the new symbols:

```python
from .messages import (
    BlockAnnouncementPayload, QueryPayload, QueryResponsePayload,
)
from .poll import Poll, close_round, on_response
```

2. Extend `_on_timer` to handle `("poll", block_id)`:

```python
def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
    if timer_id == "slot":
        slot = payload
        if slot % self.n == self.id:
            self._propose(slot, t)
        self.set_timer("slot", self.slot_duration, slot + 1, t)
    elif isinstance(timer_id, tuple) and timer_id[0] == "poll":
        block_id = timer_id[1]
        self._start_poll_round(block_id, t)
```

3. Add the poll-round bootstrap, query handler, and response handler:

```python
def _peers_minus_self(self) -> tuple[int, ...]:
    if self._peers_minus_self_cache is None:
        self._peers_minus_self_cache = tuple(
            i for i in range(self.n) if i != self.id)
    return self._peers_minus_self_cache

def _start_poll_round(self, block_id: bytes, t: float) -> None:
    """Begin a new poll round: sample K peers, send K QUERYs, emit event."""
    cs = self._conflict_set_for(block_id)
    if cs is None or cs.state.name == "ACCEPTED":
        return       # nothing to poll for
    self._next_request_id += 1
    request_id = self._next_request_id
    peers = tuple(self.rng.sample(self._peers_minus_self(), self.K))
    poll = Poll(block_id=block_id, request_id=request_id, peers=peers)
    self.polls[block_id] = poll
    self.emit("snowman_poll_started",
              {"block_id": block_id, "request_id": request_id,
               "peers": peers}, t)
    payload = QueryPayload(request_id=request_id, block_id=block_id)
    for peer_id in peers:
        self.send(peer_id, "QUERY", payload, t)

def _conflict_set_for(self, block_id: bytes) -> ConflictSet | None:
    """Find the conflict set containing block_id (lookup is O(parents))."""
    for cs in self.conflict_sets.values():
        if block_id in cs.members:
            return cs
    return None

def _handle_query(self, msg: Message, t: float) -> None:
    p = msg.payload
    if not isinstance(p, QueryPayload):
        self._reject(reason="malformed_payload", t=t, msg_type=msg.type)
        return
    cs = self._conflict_set_for(p.block_id)
    preferred = cs.preference if cs is not None else p.block_id  # permissive default
    response = QueryResponsePayload(
        request_id=p.request_id, preferred_block_id=preferred)
    self.send(msg.src, "QUERY-RESPONSE", response, t)

def _handle_response(self, msg: Message, t: float) -> None:
    p = msg.payload
    if not isinstance(p, QueryResponsePayload):
        self._reject(reason="malformed_payload", t=t, msg_type=msg.type)
        return
    # Look up the poll keyed by which block this response is for. The
    # response carries only request_id and preferred_block_id; the
    # block_id under poll is implicit in the (poller, request_id) pair.
    # We scan self.polls for a matching request_id; honest-path has at
    # most a handful of in-flight polls, so this is fine.
    poll = None
    for candidate in self.polls.values():
        if candidate.request_id == p.request_id and not candidate.closed:
            poll = candidate
            break
    if poll is None:
        return       # stale or unknown; drop
    cs = self.conflict_sets.get(self._parent_of(poll.block_id))
    if cs is None:
        return
    early_close = on_response(
        poll=poll, preferred_block_id=p.preferred_block_id,
        current_preference=cs.preference, alpha_c=self.alpha_c, K=self.K)
    if early_close or poll.responses_received == self.K:
        self._close_and_continue(poll, cs, t)

def _parent_of(self, block_id: bytes) -> bytes | None:
    """Map block_id back to its parent_id (= ConflictSet key)."""
    for cs in self.conflict_sets.values():
        if block_id in cs.members:
            return cs.parent_id
    return None

def _close_and_continue(self, poll: Poll, cs: ConflictSet, t: float) -> None:
    """Apply close_round; emit events; arm next poll or finalise."""
    outcome = close_round(
        conflict_set=cs, poll=poll,
        alpha_p=self.alpha_p, alpha_c=self.alpha_c, beta=self.beta)
    self.emit("snowman_poll_closed",
              {"block_id": poll.block_id, "request_id": poll.request_id,
               "agree_per_block": dict(poll.agree_per_block),
               "flipped": outcome.flipped,
               "new_preference": outcome.new_preference,
               "counter": outcome.counter,
               "accepted": outcome.accepted}, t)
    if outcome.accepted:
        block = cs.members[poll.block_id]
        self.chain.on_accept(block)
        self.emit("decided",
                  {"value": poll.block_id, "instance_id": poll.block_id}, t)
        del self.polls[poll.block_id]
    else:
        self.set_timer(("poll", poll.block_id), POLL_DELAY,
                       poll.block_id, t)
```

4. Update `_on_message` to wire query + response:

```python
def _on_message(self, msg: Message, t: float) -> None:
    if msg.type == "BLOCK-ANNOUNCEMENT":
        self._handle_announce(msg, t)
    elif msg.type == "QUERY":
        self._handle_query(msg, t)
    elif msg.type == "QUERY-RESPONSE":
        self._handle_response(msg, t)
    else:
        self._reject(reason="unknown_type", t=t, msg_type=msg.type)
```

**Step 5: Run tests to verify they pass**

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_node_query test_node_accept -v`
Expected: query tests pass; acceptance tests pass.

Run: `make test-snowman`
Expected: All tests green.

---

## Task 12: `test_node_flip.py` — α_p preference-flip path

Design spec §1 in-scope commitment + §6.3 + Section 8.1 of the design.
Drive `close_round` directly on a hand-crafted multi-block conflict set;
guard the flip code path against regression.

**Files:**
- Test: `tests/snowman/test_node_flip.py`

**Step 1: Write the failing test**

Create `tests/snowman/test_node_flip.py`:

```python
"""The alpha_p preference-flip path (design spec §1, §8.1).

Honest-path baseline does not exercise this code path (singleton conflict
sets keep agree = K trivially on the single candidate). This test
guards the flip path against regression and unblocks T18 / T51–T53
adversary plumbing.
"""
import unittest

from snowman.block import (
    Block, ConflictSet, CSState, GENESIS_ID,
)
from snowman.poll import Poll, close_round


class TestPreferenceFlip(unittest.TestCase):
    def _two_block_cs(self) -> ConflictSet:
        """Conflict set with two candidates A (initial pref) and B."""
        cs = ConflictSet(parent_id=GENESIS_ID)
        cs.add_block(Block(block_id=b"A"*32, parent_id=GENESIS_ID, slot=1,
                           proposer_idx=0, transactions=()))
        cs.add_block(Block(block_id=b"B"*32, parent_id=GENESIS_ID, slot=1,
                           proposer_idx=1, transactions=()))
        return cs

    def test_flip_on_alpha_p(self):
        """K=3, alpha_p=2, alpha_c=3. Two responses for B, one for A.
        Preference flips A -> B; counter resets to 0; alpha_c (3) is not
        hit, so counter stays 0."""
        cs = self._two_block_cs()
        poll = Poll(block_id=b"A"*32, request_id=1, peers=(1, 2, 3))
        poll.agree_per_block = {b"A"*32: 1, b"B"*32: 2}
        poll.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=poll,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"B"*32)
        self.assertEqual(outcome.counter, 0)
        self.assertFalse(outcome.accepted)
        self.assertEqual(cs.confidence[b"B"*32], 1)

    def test_followup_round_advances_counter_for_new_pref(self):
        """After the flip, the next full-agreement round on B advances
        counter to 1."""
        cs = self._two_block_cs()
        # First round: flip.
        poll1 = Poll(block_id=b"A"*32, request_id=1, peers=(1, 2, 3))
        poll1.agree_per_block = {b"A"*32: 1, b"B"*32: 2}
        poll1.responses_received = 3
        close_round(conflict_set=cs, poll=poll1,
                    alpha_p=2, alpha_c=3, beta=15)
        # Second round: all three responses for B.
        poll2 = Poll(block_id=b"A"*32, request_id=2, peers=(1, 2, 3))
        poll2.agree_per_block = {b"B"*32: 3}
        poll2.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=poll2,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertFalse(outcome.flipped)
        self.assertEqual(outcome.counter, 1)
        self.assertEqual(cs.confidence[b"B"*32], 2)

    def test_no_flip_when_majority_below_alpha_p(self):
        """Three responses split 1-1-1: no block hits alpha_p=2; counter
        resets if it was positive; preference unchanged."""
        cs = self._two_block_cs()
        cs.add_block(Block(block_id=b"C"*32, parent_id=GENESIS_ID, slot=1,
                           proposer_idx=2, transactions=()))
        cs.counter = 5  # in-flight progress
        poll = Poll(block_id=b"A"*32, request_id=1, peers=(1, 2, 3))
        poll.agree_per_block = {b"A"*32: 1, b"B"*32: 1, b"C"*32: 1}
        poll.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=poll,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertFalse(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"A"*32)
        self.assertEqual(outcome.counter, 0)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it passes immediately**

This task does not add new production code; it adds tests that exercise
existing code in `close_round` (Task 8).

Run: `PYTHONPATH=src:tests/snowman python3 -m unittest test_node_flip -v`
Expected: 3 tests pass.

Run: `make test-snowman`
Expected: All snowman tests green.

---

## Task 13: Integration test — `tests/integration/test_snowman_baseline.py`

Design spec §8.2 + §9. The four T38 build-verification outcomes.

**Files:**
- Test: `tests/integration/test_snowman_baseline.py`

**Step 1: Write the failing test**

Create `tests/integration/test_snowman_baseline.py`:

```python
"""T38 honest-path build-verification baseline at n in {4, 7, 10}.

Asserts the four T38 outcomes per scenario:
  1. Every honest node ACCEPTS every announced block.
  2. Zero forks — exactly one ACCEPTED block per slot across the network.
  3. Finalisation latency is logged on every decided event.
  4. Two runs with the same (config, global_seed) are byte-identical.

Mirrors tests/integration/test_pos_baseline.py.
"""
import unittest

from event_log.logger import EventLogger
from network.network import Network
from network.phases import ConstantDelay, NetworkPhase
from scheduler.scheduler import Scheduler

from snowman.node import SnowmanNode


def _run(*, n: int, global_seed: int = 42, t_max: float = 20.0):
    logger = EventLogger()
    sched = Scheduler(event_sink=logger.handle)
    phase = NetworkPhase(
        t_start=0.0, t_end=float("inf"),
        delay=ConstantDelay(1e-9), drop_rate=0.0, partitions=())
    net = Network(timeline=(phase,), global_seed=global_seed)
    nodes = []
    for node_id in range(n):
        node = SnowmanNode(
            node_id=node_id, weight=1.0, endpoint=object(),
            global_seed=global_seed, n=n)
        net.register(node)
        sched.bind(node)
        nodes.append(node)
    net.start()
    result = sched.run(t_max=t_max)
    return result, logger, nodes


class TestSnowmanBaseline(unittest.TestCase):
    SCENARIOS = [("n=4", 4), ("n=7", 7), ("n=10", 10)]

    def test_every_node_accepts_every_announced_block(self):
        for label, n in self.SCENARIOS:
            with self.subTest(label):
                _, logger, nodes = _run(n=n)
                announced = {
                    e.fields["block_id"] for e in logger.records
                    if e.event_type == "snowman_announced"
                }
                # Every node has decided every announced block.
                decided_by_node: dict[int, set[bytes]] = {}
                for e in logger.records:
                    if e.event_type == "decided":
                        decided_by_node.setdefault(
                            e.node_id, set()).add(e.fields["instance_id"])
                for node in nodes:
                    self.assertEqual(
                        decided_by_node.get(node.id, set()),
                        announced,
                        f"{label}: node {node.id} did not decide every block")

    def test_no_forks(self):
        for label, n in self.SCENARIOS:
            with self.subTest(label):
                _, logger, _ = _run(n=n)
                by_block: dict[bytes, set[bytes]] = {}
                for e in logger.records:
                    if e.event_type == "decided":
                        by_block.setdefault(
                            e.fields["instance_id"], set()).add(
                            e.fields["value"])
                for block_id, values in by_block.items():
                    self.assertEqual(
                        len(values), 1, f"{label}: fork at {block_id!r}")

    def test_finality_latency_logged(self):
        for label, n in self.SCENARIOS:
            with self.subTest(label):
                _, logger, _ = _run(n=n)
                decided = [
                    e for e in logger.records if e.event_type == "decided"]
                self.assertGreater(len(decided), 0)
                for e in decided:
                    self.assertIsInstance(e.t, float)
                    self.assertGreater(e.t, 0)

    def test_determinism_byte_identical(self):
        for label, n in self.SCENARIOS:
            with self.subTest(label):
                _, logger_a, _ = _run(n=n, global_seed=42)
                _, logger_b, _ = _run(n=n, global_seed=42)
                self.assertEqual(
                    [(e.t, e.node_id, e.event_type, e.fields)
                     for e in logger_a.records],
                    [(e.t, e.node_id, e.event_type, e.fields)
                     for e in logger_b.records],
                    f"{label}: byte-identical determinism broken")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_snowman_baseline -v`
Expected: 4 tests pass (each is a `subTest`-loop over the three n values).

Run: `make test`
Expected: All eight suites green (scheduler, nodes, network, event_log,
config, pbft, pos, snowman, integration). Total ≈ 540 tests.

---

## Task 14: Wiki updates + In-Review handoff

Land the experiment page, the two `## Revisions` entries, and the index +
log updates. Flip T38 to In Review.

**Files:**
- Create: `wiki/experiments/2026-05-27_snowman-baseline.md`
- Modify: `wiki/concepts/system-design-protocols.md` (append to `## Revisions`)
- Modify: `wiki/concepts/message-types.md` (append to `## Revisions`)
- Modify: `wiki/index.md` (add experiment-page entry)
- Modify: `wiki/log.md` (append T38 entry)
- Modify: `TASKS.md` (flip T38 to In Review + dashboard arithmetic)

**Step 1: Write the experiment page**

Create `wiki/experiments/2026-05-27_snowman-baseline.md` per design spec
§9. Run the integration suite once and capture the actual per-scenario
event counts; populate the result table with real numbers.

To capture the counts, run interactively:

```
PYTHONPATH=src:tests/integration python3 -c '
from test_snowman_baseline import _run
from collections import Counter
for n in (4, 7, 10):
    _, logger, _ = _run(n=n)
    c = Counter(e.event_type for e in logger.records)
    print(n, dict(c))
'
```

Copy the numbers into the result table per design spec §9.5.

**Step 2: Append the `## Revisions` entry to `system-design-protocols.md`**

Use the draft text from design spec §10.1 verbatim. Append below the
existing `2026-05-23 (T32)` entry.

**Step 3: Append the `## Revisions` entry to `message-types.md`**

Use the draft text from design spec §10.2 verbatim. Append below the
existing `## Revisions` heading (or create the heading if empty).

**Step 4: Update `wiki/index.md`**

In the `## Experiments` section, append one line in `(path) — summary`
format:

```
- [[experiments/2026-05-27_snowman-baseline]] — T38 honest-path build-verification baseline: full Snowball at n ∈ {4, 7, 10} with rescaled (K, α_p, α_c) per metric-reconciliation; every node decides every announced block, zero forks, byte-identical determinism with the K-peer sampling path exercised.
```

**Step 5: Append the T38 entry to `wiki/log.md`**

Use the standard log format from `docs/wiki-spec.md`:

```
## [2026-05-27] code | task 38 — Snowman honest-path baseline
- role: Engineer
- touched: src/snowman/, tests/snowman/, tests/integration/test_snowman_baseline.py, Makefile, wiki/experiments/2026-05-27_snowman-baseline.md, wiki/concepts/system-design-protocols.md (Revisions), wiki/concepts/message-types.md (Revisions), wiki/index.md
- notes: Implements honest-path Snowman per [[concepts/week7-decision]] §4. New SnowmanNode validator running full Snowball (per-block confidence + α_p preference-flip + α_c counter-increment) with the rescaling rule from [[concepts/metric-reconciliation]]. Build-verification baseline at n ∈ {4, 7, 10} matches the T30 / T35 outcome triple plus byte-identical determinism on the RNG sampling path (week7-decision §5.1 watch-for closed). Five sketch divergences from [[concepts/system-design-protocols]] §4 landed as Revisions; one behavioural clarification on [[concepts/message-types]] §5 landed as Revisions. Unblocks T36.1; the NWT column for T40 lands when T38.1 does.
```

**Step 6: Flip TASKS.md and update the dashboard**

- Change T38's status from `[~]` to `[?]` (In Review).
- Dashboard: decrement In Progress (1→0), increment In Review (2→3); the
  In-Progress / In-Review totals must remain consistent with the actual
  state of the file.

**Step 7: Final verification**

Run `make test` once more to confirm no regression from the wiki edits
(none expected, but the verification-before-completion skill requires it):

Run: `make test`
Expected: All suites green.

Manual inspection checklist (per `superpowers:verification-before-completion`):

- `wiki/index.md` contains the new experiment-page entry.
- `wiki/log.md` contains the T38 entry.
- `wiki/experiments/2026-05-27_snowman-baseline.md` exists with all 10
  sections from design spec §9.
- Two `## Revisions` entries landed (verify by `grep -n "2026-05-27" wiki/concepts/*.md`).
- `TASKS.md` shows T38 as `[?]` In Review; dashboard arithmetic consistent.
- `make test` green; `make test-snowman` green in isolation.

**Step 8: Hand off to the human**

The human commits everything as `task 38: implement Snowman honest-path
baseline` per `docs/workflow.md`. They push the branch and you do not
run `git commit` or `git push` per the prj-pickup contract.

Report to the user (per `docs/workflow.md` step 9):

- Files touched: enumerate.
- Wiki pages added: `wiki/experiments/2026-05-27_snowman-baseline.md`.
- Wiki pages updated: `index.md`, `log.md`, `system-design-protocols.md`
  (Revisions), `message-types.md` (Revisions).
- Decisions made: the five scope/design picks captured in the design spec
  header (cadence, polls, close trigger, Snowball depth, plus the failure-
  path early-close deferral).
- Open questions: any divergence between the design spec's predicted event
  counts and the actually-observed counts in the integration run; note
  in the experiment page Revisions if needed.

---

## Execution checkpoint

After Task 14, T38 is In Review. The human reviews, merges, and flips to
Completed; nothing further is required from the executing session.
