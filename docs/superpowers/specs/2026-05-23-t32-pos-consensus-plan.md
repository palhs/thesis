# T32 — Simplified Casper FFG Consensus Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to
> implement this plan task-by-task. Drive each task with
> superpowers:test-driven-development.

**Goal:** Build a new `src/pos/` package implementing a simplified,
honest-path Casper FFG consensus protocol — a `CasperNode` validator that
proposes blocks on a slot schedule, casts stake-weighted FFG attestations,
and finalises epochs through the two-round justify→finalise gadget.

**Architecture:** A `CasperNode(Node)` subclass mirroring `src/pbft/`. Time
is divided into epochs of `slots_per_epoch` slots; one block per slot; the
first block of an epoch is its checkpoint. A genesis block (slot 0) is
pre-installed and epoch 0 is finalised by construction, bootstrapping the
justify chain. A recurring `"slot"` timer proposes blocks (round-robin
proposer `slot mod n`) and, once per epoch, broadcasts an `ATTESTATION`
carrying an FFG `<source, target>` vote. Per-epoch `EpochState` instances
(`unjustified → justified → finalised`) aggregate attesting stake; a
supermajority link forms at `≥ 2/3` of total stake; two consecutive links
finalise an epoch and emit the mandatory `decided` event. No slashing, no
LMD-GHOST (design spec Approach 1).

**Design spec:** `docs/superpowers/specs/2026-05-23-t32-pos-consensus-design.md`
— read it before starting; this plan references its sections.

**Tech Stack:** Python 3, stdlib `unittest`, the discrete-event simulator
(`src/scheduler`, `src/nodes`, `src/network`, `src/event_log`,
`src/config`).

**Test commands:**
- Unit (one test): `PYTHONPATH=src:tests/pos python3 -m unittest <module>.<Class>.<test> -v`
- Unit (pos suite): `PYTHONPATH=src:tests/pos python3 -m unittest discover -s tests/pos -v`
- Integration: `PYTHONPATH=src:tests/integration python3 -m unittest <module> -v`
- Or via the Makefile once Task 1 lands: `make test-pos`, `make test`.

**Commits:** Per `docs/workflow.md` and the T29 precedent, the entire T32
implementation lands as **one commit** (`task 32: implement simplified
Casper FFG consensus`) at the In-Review flip. The `task 32: start`, design,
and plan commits are already on the branch. This plan has **no per-task
`git commit` steps**; Task 13 is the single commit/handoff checkpoint.

**Regression watch:** T32 creates a brand-new package and a new test
suite; it modifies no existing `src/` file. The only edit outside `src/pos/`
and `tests/pos/` is the `Makefile` (Task 1, additive) and the new
integration test (Task 11). No existing test should change behaviour — if
an upstream suite breaks, stop and debug; do not edit upstream tests.

**Slot/epoch model (pinned for the implementation):**
- Genesis block: `slot 0`, `epoch 0`, sentinel `parent_hash` (32 zero
  bytes), fixed `block_hash`, empty transactions, `proposer_idx = -1`.
  Pre-installed in every node's `Chain` at construction.
- Epoch 0 is `FINALISED` at construction; genesis is its checkpoint.
- The slot timer proposes slots `1, 2, 3, …`. Slot `s` is in epoch
  `s // slots_per_epoch`; epoch `e ≥ 1`'s checkpoint is the block at slot
  `e * slots_per_epoch`.
- The slot loop re-arms indefinitely; a Casper run has no natural
  quiescence, so every run is bounded by the scheduler's `t_max`.

---

## Task 1: Package and test-suite scaffolding

Create the `src/pos/` package, the `tests/pos/` suite directory, and wire
the suite into the `Makefile`.

**Files:**
- Create: `src/pos/__init__.py`
- Create: `tests/pos/__init__.py`
- Modify: `Makefile` (the `SUITES` line)

**Step 1: Create the package files**

`src/pos/__init__.py` — module docstring only for now (a one-line
description: "Simplified Casper FFG consensus — T32."). Exports are added
in Task 6. `tests/pos/__init__.py` — empty (package marker, matches
`tests/pbft/__init__.py`).

**Step 2: Wire the Makefile**

In `Makefile`, change the `SUITES` line to add `pos`:

```
SUITES        = scheduler nodes network event_log config pbft pos integration
```

**Step 3: Verify the suite is discoverable**

Run: `make test-pos`
Expected: `Ran 0 tests in ...s` / `OK` — the suite directory exists and is
empty, so discovery succeeds with zero tests. Exit status 0.

---

## Task 2: `messages.py` — payload dataclasses

Design spec §3. Three frozen dataclasses; no signature fields, no head
vote (spec §3, §15).

**Files:**
- Create: `src/pos/messages.py`
- Test: `tests/pos/test_messages.py`

**Step 1: Write the failing test**

Create `tests/pos/test_messages.py`:

```python
import unittest

from pos.messages import FFGVote, BlockProposalPayload, AttestationPayload


class TestFFGVote(unittest.TestCase):
    def test_fields(self):
        v = FFGVote(source_epoch=0, source_hash=b"s" * 32,
                    target_epoch=1, target_hash=b"t" * 32)
        self.assertEqual(v.source_epoch, 0)
        self.assertEqual(v.target_epoch, 1)
        self.assertEqual(v.target_hash, b"t" * 32)

    def test_frozen(self):
        v = FFGVote(0, b"s" * 32, 1, b"t" * 32)
        with self.assertRaises(Exception):
            v.target_epoch = 9


class TestBlockProposalPayload(unittest.TestCase):
    def test_fields(self):
        b = BlockProposalPayload(slot=2, epoch=1, parent_hash=b"p" * 32,
                                 block_hash=b"b" * 32,
                                 transactions=(b"tx",), proposer_idx=2)
        self.assertEqual(b.slot, 2)
        self.assertEqual(b.transactions, (b"tx",))


class TestAttestationPayload(unittest.TestCase):
    def test_carries_ffg_vote(self):
        v = FFGVote(0, b"s" * 32, 1, b"t" * 32)
        a = AttestationPayload(slot=3, epoch=1, ffg=v, attester_idx=2)
        self.assertIs(a.ffg, v)
        self.assertEqual(a.attester_idx, 2)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_messages -v`
Expected: FAIL — `pos.messages` does not exist.

**Step 3: Implement**

Create `src/pos/messages.py` with a module docstring referencing design
spec §3 and `wiki/concepts/message-types.md` §4. Define the three
`@dataclass(frozen=True)` classes exactly as design spec §3:
`FFGVote(source_epoch, source_hash, target_epoch, target_hash)`,
`BlockProposalPayload(slot, epoch, parent_hash, block_hash, transactions,
proposer_idx)`, `AttestationPayload(slot, epoch, ffg, attester_idx)`. Add a
comment on `AttestationPayload` noting `head_vote_hash` is omitted (LMD-GHOST
out of scope) and on both that signature fields are omitted, per spec §15.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_messages -v`
Expected: PASS.

---

## Task 3: `chain.py` — `Block`, block hashing, genesis

Design spec §4. The block dataclass, a deterministic hash, and the genesis
constant.

**Files:**
- Create: `src/pos/chain.py`
- Test: `tests/pos/test_chain.py`

**Step 1: Write the failing test**

Create `tests/pos/test_chain.py`:

```python
import unittest

from pos.chain import Block, block_hash, GENESIS, GENESIS_HASH


class TestBlockHash(unittest.TestCase):
    def test_is_32_bytes(self):
        h = block_hash(slot=1, parent_hash=GENESIS_HASH,
                       proposer_idx=1, transactions=(b"tx",))
        self.assertIsInstance(h, bytes)
        self.assertEqual(len(h), 32)

    def test_deterministic(self):
        args = dict(slot=1, parent_hash=GENESIS_HASH,
                    proposer_idx=1, transactions=(b"tx",))
        self.assertEqual(block_hash(**args), block_hash(**args))

    def test_distinct_inputs_distinct_hash(self):
        a = block_hash(slot=1, parent_hash=GENESIS_HASH,
                       proposer_idx=1, transactions=())
        b = block_hash(slot=2, parent_hash=GENESIS_HASH,
                       proposer_idx=1, transactions=())
        self.assertNotEqual(a, b)


class TestGenesis(unittest.TestCase):
    def test_genesis_is_epoch0_checkpoint(self):
        self.assertEqual(GENESIS.slot, 0)
        self.assertEqual(GENESIS.epoch, 0)
        self.assertEqual(GENESIS.block_hash, GENESIS_HASH)

    def test_block_is_checkpoint_at_epoch_boundary(self):
        # slots_per_epoch is a Chain-level parameter; a slot is a checkpoint
        # iff slot % slots_per_epoch == 0.
        self.assertTrue(Block(slot=4, epoch=2, parent_hash=b"p" * 32,
                              block_hash=b"b" * 32, transactions=(),
                              proposer_idx=0).slot % 2 == 0)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_chain -v`
Expected: FAIL — `pos.chain` does not exist.

**Step 3: Implement**

Create `src/pos/chain.py` with a module docstring (design spec §4). Use the
process-stable `blake2b` discipline of `src/pbft/digest.py`:

```python
import hashlib
from dataclasses import dataclass

GENESIS_HASH = b"\x00" * 32

@dataclass(frozen=True)
class Block:
    slot: int
    epoch: int
    parent_hash: bytes
    block_hash: bytes
    transactions: tuple[bytes, ...]
    proposer_idx: int

def block_hash(slot, parent_hash, proposer_idx, transactions) -> bytes:
    """32-byte blake2b digest over the block's identifying fields."""
    h = hashlib.blake2b(digest_size=32)
    h.update(str(slot).encode())
    h.update(b"|")
    h.update(parent_hash)
    h.update(b"|")
    h.update(str(proposer_idx).encode())
    h.update(b"|")
    for tx in transactions:
        h.update(tx)
        h.update(b",")
    return h.digest()

GENESIS = Block(slot=0, epoch=0, parent_hash=GENESIS_HASH,
                block_hash=GENESIS_HASH, transactions=(), proposer_idx=-1)
```

(`GENESIS` uses `GENESIS_HASH` as its own `block_hash` — a fixed sentinel
so every node's genesis is byte-identical without a propagation step.)

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_chain -v`
Expected: PASS.

---

## Task 4: `chain.py` — the `Chain` (add, buffer, head, checkpoint)

Design spec §4. A linear chain with parent-buffering and checkpoint
lookup.

**Files:**
- Modify: `src/pos/chain.py`
- Test: `tests/pos/test_chain.py`

**Step 1: Write the failing tests**

Add to `tests/pos/test_chain.py`:

```python
from pos.chain import Chain


def _blk(slot, parent, spe=2, proposer=0, txs=()):
    bh = block_hash(slot=slot, parent_hash=parent,
                    proposer_idx=proposer, transactions=txs)
    return Block(slot=slot, epoch=slot // spe, parent_hash=parent,
                 block_hash=bh, transactions=txs, proposer_idx=proposer)


class TestChain(unittest.TestCase):
    def test_starts_at_genesis(self):
        c = Chain(slots_per_epoch=2)
        self.assertIs(c.head, GENESIS)
        self.assertEqual(c.checkpoint(0).block_hash, GENESIS_HASH)

    def test_add_extends_head(self):
        c = Chain(slots_per_epoch=2)
        b1 = _blk(1, GENESIS_HASH)
        c.add(b1)
        self.assertIs(c.head, b1)

    def test_unknown_parent_is_buffered_then_drains(self):
        c = Chain(slots_per_epoch=2)
        b1 = _blk(1, GENESIS_HASH)
        b2 = _blk(2, b1.block_hash)
        c.add(b2)                       # parent b1 unknown -> buffered
        self.assertIs(c.head, GENESIS)
        c.add(b1)                       # now b1 lands, b2 drains behind it
        self.assertIs(c.head, b2)

    def test_checkpoint_of_epoch(self):
        c = Chain(slots_per_epoch=2)
        b1 = _blk(1, GENESIS_HASH)
        b2 = _blk(2, b1.block_hash)     # slot 2 -> epoch 1 checkpoint
        b3 = _blk(3, b2.block_hash)
        for b in (b1, b2, b3):
            c.add(b)
        self.assertEqual(c.checkpoint(1).block_hash, b2.block_hash)
        self.assertEqual(c.checkpoint(0).block_hash, GENESIS_HASH)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_chain -v`
Expected: FAIL — `Chain` not defined.

**Step 3: Implement**

Add `Chain` to `src/pos/chain.py` per design spec §4:

- `__init__(self, slots_per_epoch)` — store `slots_per_epoch`; `blocks =
  {GENESIS_HASH: GENESIS}`; `head = GENESIS`; `_buffer = []` (blocks whose
  parent is not yet known).
- `add(block)` — if `block.parent_hash` not in `blocks`, append to
  `_buffer` and return. Otherwise insert into `blocks`; if `block.slot >
  head.slot`, set `head = block`. Then re-scan `_buffer`: any buffered
  block whose parent is now known is removed from the buffer and re-`add`ed
  (loop until no buffered block can be placed — drain in `sorted` order by
  `slot` for determinism).
- `head` — the attribute is maintained by `add`; the greatest-slot block on
  the known chain. Honest-path: a single chain, so this is unambiguous.
- `checkpoint(epoch)` — return the checkpoint `Block` of `epoch`: for
  `epoch == 0`, `GENESIS`; otherwise the block with `slot == epoch *
  slots_per_epoch` (look it up by walking `blocks`; raise `KeyError` if not
  present). T32 honest-path always has it once the run has advanced far
  enough.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_chain -v`
Expected: PASS.

---

## Task 5: `epoch.py` — `EpochState` and FFG aggregation

Design spec §5. The per-epoch FSM instance and the supermajority-link
arithmetic.

**Files:**
- Create: `src/pos/epoch.py`
- Test: `tests/pos/test_epoch.py`

**Step 1: Write the failing tests**

Create `tests/pos/test_epoch.py`:

```python
import unittest

from pos.epoch import EpochFSM, EpochState, meets_supermajority


class TestSupermajority(unittest.TestCase):
    def test_two_thirds_boundary(self):
        # >= 2/3 of total. total=9 -> need >= 6.
        self.assertFalse(meets_supermajority(5.0, 9.0))
        self.assertTrue(meets_supermajority(6.0, 9.0))

    def test_exact_two_thirds_passes(self):
        self.assertTrue(meets_supermajority(6.0, 9.0))


class TestEpochState(unittest.TestCase):
    def test_starts_unjustified(self):
        es = EpochState(epoch=1)
        self.assertIs(es.state, EpochFSM.UNJUSTIFIED)
        self.assertIsNone(es.checkpoint_hash)

    def test_record_vote_accumulates_link_stake(self):
        es = EpochState(epoch=1)
        es.record_vote(source_epoch=0, attester_idx=0, stake=3.0)
        es.record_vote(source_epoch=0, attester_idx=1, stake=3.0)
        self.assertEqual(es.link_stake(0), 6.0)

    def test_dedupe_one_vote_per_attester(self):
        es = EpochState(epoch=1)
        self.assertTrue(es.record_vote(0, attester_idx=0, stake=3.0))
        # same attester again (any source) -> ignored, returns False
        self.assertFalse(es.record_vote(0, attester_idx=0, stake=3.0))
        self.assertEqual(es.link_stake(0), 3.0)

    def test_link_stake_unknown_source_is_zero(self):
        self.assertEqual(EpochState(epoch=1).link_stake(7), 0.0)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_epoch -v`
Expected: FAIL — `pos.epoch` does not exist.

**Step 3: Implement**

Create `src/pos/epoch.py` per design spec §5:

```python
from enum import Enum

class EpochFSM(Enum):
    UNJUSTIFIED = 0
    JUSTIFIED   = 1
    FINALISED   = 2

def meets_supermajority(stake: float, total_stake: float) -> bool:
    """True iff `stake` is >= 2/3 of `total_stake`. Division-free form so
    whole-number stakes compare exactly (design spec §5.2)."""
    return 3.0 * stake >= 2.0 * total_stake

class EpochState:
    """Per-target-epoch FFG instance (node-model.md §4 FSM for Casper)."""
    def __init__(self, epoch: int) -> None:
        self.epoch = epoch
        self.checkpoint_hash: bytes | None = None
        self.state: EpochFSM = EpochFSM.UNJUSTIFIED
        # source_epoch -> { attester_idx -> stake }
        self.links: dict[int, dict[int, float]] = {}
        self._attesters: set[int] = set()      # dedupe across all sources

    def record_vote(self, source_epoch, attester_idx, stake) -> bool:
        """File one FFG vote. Returns False (and changes nothing) if this
        attester already voted for this target epoch (Decision I)."""
        if attester_idx in self._attesters:
            return False
        self._attesters.add(attester_idx)
        self.links.setdefault(source_epoch, {})[attester_idx] = stake
        return True

    def link_stake(self, source_epoch: int) -> float:
        return sum(self.links.get(source_epoch, {}).values())
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_epoch -v`
Expected: PASS.

---

## Task 6: `node.py` — constructor, validation, event constants, helpers

Design spec §6.1, §10. The `CasperNode` skeleton: identity, knobs, stake
table, cross-instance state, event constants. Plus the `tests/pos/`
shared `_helpers.py` and the `src/pos/__init__.py` export.

**Files:**
- Create: `src/pos/node.py`
- Modify: `src/pos/__init__.py`
- Create: `tests/pos/_helpers.py`
- Test: `tests/pos/test_node_init.py`

**Step 1: Write the failing test**

Create `tests/pos/_helpers.py` (the suite-shared fixture module, `_`-prefixed
so `unittest discover` skips it — mirrors `tests/pbft/_helpers.py`):

```python
"""Shared fixtures for the T32 Casper FFG unit suite."""
from __future__ import annotations

from nodes import Message
from nodes.lifecycle import Lifecycle
from pos.node import CasperNode


def uniform_stake(n: int, stake: float = 3.0) -> dict[int, float]:
    return {i: stake for i in range(n)}


def make_node(node_id: int, n: int, *, stake_table=None,
              slot_duration: float = 1.0, slots_per_epoch: int = 2,
              attest_offset: int | None = None,
              workload: list[bytes] | None = None) -> CasperNode:
    st = stake_table if stake_table is not None else uniform_stake(n)
    kwargs = dict(node_id=node_id, weight=st[node_id], endpoint=None,
                  global_seed=42, n=n, stake_table=st,
                  slot_duration=slot_duration, slots_per_epoch=slots_per_epoch,
                  workload=workload)
    if attest_offset is not None:
        kwargs["attest_offset"] = attest_offset
    return CasperNode(**kwargs)


class Capture:
    """Records the outbound API channels a CasperNode drives."""
    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict, float]] = []
        self.broadcasts: list[tuple[str, object, float]] = []
        self.timers: list[tuple] = []
        self.cancels: list = []

    def events(self, et): return [e for e in self.emitted if e[0] == et]
    def count(self, et): return len(self.events(et))
    def broadcast_types(self): return [b[0] for b in self.broadcasts]
    def count_broadcast(self, ty):
        return sum(1 for b in self.broadcasts if b[0] == ty)


def capturers(node: CasperNode) -> Capture:
    cap = Capture()
    node.emit = lambda et, f, t: cap.emitted.append((et, f, t))
    node.broadcast = lambda ty, p, t: cap.broadcasts.append((ty, p, t))
    node.send = lambda *a, **kw: None
    node.set_timer = lambda tid, dl, p, t: cap.timers.append((tid, dl, p, t))
    node.cancel_timer = lambda tid: cap.cancels.append(tid)
    return cap


def kickoff(node: CasperNode) -> None:
    """Force RUNNING without firing _on_start (Node.on_message refuses a
    CREATED node)."""
    node.status = Lifecycle.RUNNING
```

Create `tests/pos/test_node_init.py`:

```python
import unittest

from pos import node as pos_node
from _helpers import make_node, uniform_stake


class TestConstructor(unittest.TestCase):
    def test_basic_attributes(self):
        n = make_node(2, 4, slots_per_epoch=2)
        self.assertEqual(n.id, 2)
        self.assertEqual(n.n, 4)
        self.assertEqual(n.slots_per_epoch, 2)
        self.assertEqual(n.total_stake, 12.0)   # 4 x 3.0

    def test_rejects_bad_n(self):
        with self.assertRaises(ValueError):
            make_node(0, 0)

    def test_rejects_node_id_outside_range(self):
        with self.assertRaises(ValueError):
            CasperNode_outside()

    def test_rejects_nonpositive_slot_duration(self):
        with self.assertRaises(ValueError):
            make_node(0, 4, slot_duration=0.0)

    def test_rejects_nonpositive_slots_per_epoch(self):
        with self.assertRaises(ValueError):
            make_node(0, 4, slots_per_epoch=0)

    def test_rejects_stake_table_mismatch(self):
        with self.assertRaises(ValueError):
            make_node(0, 4, stake_table={0: 3.0, 1: 3.0})   # missing 2,3

    def test_event_constants_exist(self):
        for name in ("CASPER_BLOCK_ACCEPTED", "CASPER_ATTESTED",
                     "CASPER_JUSTIFIED", "CASPER_FINALISED",
                     "CASPER_REJECTED"):
            self.assertTrue(hasattr(pos_node, name))

    def test_genesis_epoch_finalised_at_construction(self):
        from pos.epoch import EpochFSM
        n = make_node(0, 4)
        self.assertIs(n.epoch_states[0].state, EpochFSM.FINALISED)


def CasperNode_outside():
    from pos.node import CasperNode
    return CasperNode(node_id=9, weight=3.0, endpoint=None, global_seed=42,
                      n=4, stake_table={i: 3.0 for i in range(4)})


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_init -v`
Expected: FAIL — `pos.node` does not exist.

**Step 3: Implement**

Create `src/pos/node.py` per design spec §6.1, §10. Module docstring
references the design spec. Module-level event constants:

```python
CASPER_BLOCK_ACCEPTED = "casper_block_accepted"
CASPER_ATTESTED       = "casper_attested"
CASPER_JUSTIFIED      = "casper_justified"
CASPER_FINALISED      = "casper_finalised"
CASPER_REJECTED       = "casper_rejected"
```

`class CasperNode(Node)`:

- `__init__(self, node_id, weight, endpoint, global_seed, *, n,
  stake_table, slot_duration=1.0, slots_per_epoch=2, attest_offset=None,
  workload=None)`. Call `super().__init__(node_id, weight, endpoint,
  global_seed)`. Validate (raise `ValueError`): `n <= 0`; `node_id` outside
  `[0, n)`; `slot_duration <= 0`; `slots_per_epoch <= 0`; `stake_table`
  keys != `set(range(n))`; any stake non-finite or negative;
  `stake_table[node_id] != weight`.
- Store `self.n`, `self.slots_per_epoch`, `self.slot_duration`,
  `self.stake_table` (a plain dict copy), `self.total_stake =
  sum(stake_table.values())`, `self.workload = list(workload or [])`.
- `self.attest_offset = attest_offset if attest_offset is not None else
  slots_per_epoch // 2`. Validate it is in `[0, slots_per_epoch)`.
- Cross-instance state: `self.chain = Chain(slots_per_epoch)`;
  `self.epoch_states: dict[int, EpochState] = {}`;
  `self._block_buffer` is owned by `Chain`, not here.
- Bootstrap epoch 0: create `EpochState(0)`, set `state = FINALISED`,
  `checkpoint_hash = GENESIS_HASH`, store in `epoch_states[0]` (Decision F).
- `self.highest_justified = 0`, `self.highest_finalised = 0`,
  `self.decided_epochs: set[int] = set()`.

Add a private `_epoch_state(epoch)` helper: `epoch_states.setdefault(epoch,
EpochState(epoch))` (lazy creation — Decision H).

The three abstract hooks `_on_start`, `_on_message`, `_on_timer` must exist
or the class cannot instantiate (they are `@abstractmethod` on `Node`).
Add them as minimal bodies now — `_on_start`: `pass`; `_on_message`:
`pass`; `_on_timer`: `pass`. Tasks 7–10 fill them.

In `src/pos/__init__.py`: `from .node import CasperNode` and
`__all__ = ["CasperNode"]` (mirror `src/pbft/__init__.py`).

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_init -v`
Expected: PASS.

---

## Task 7: `node.py` — `_on_start` and the slot loop (proposing)

Design spec §6.3, §6.4 step 2. The recurring `"slot"` timer; the
round-robin proposer builds and broadcasts blocks.

**Files:**
- Modify: `src/pos/node.py`
- Test: `tests/pos/test_node_propose.py`

**Step 1: Write the failing tests**

Create `tests/pos/test_node_propose.py`:

```python
import unittest

from pos.messages import BlockProposalPayload
from _helpers import make_node, capturers, kickoff


class TestSlotLoop(unittest.TestCase):
    def test_start_schedules_slot_1(self):
        n = make_node(0, 4)
        cap = capturers(n)
        n._on_start(t=0.0)
        self.assertEqual(cap.timers[0][0], "slot")
        self.assertEqual(cap.timers[0][2], 1)        # payload = slot index

    def test_slot_timer_rearms_next_slot(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        rearm = [tm for tm in cap.timers if tm[0] == "slot"][-1]
        self.assertEqual(rearm[2], 2)

    def test_proposer_of_slot_broadcasts_block(self):
        # slot 1, n=4 -> proposer = 1 % 4 = 1.
        n = make_node(1, 4)
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        self.assertEqual(cap.count_broadcast("BLOCK-PROPOSAL"), 1)

    def test_non_proposer_does_not_broadcast_block(self):
        n = make_node(2, 4)                          # slot 1 proposer = 1
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        self.assertEqual(cap.count_broadcast("BLOCK-PROPOSAL"), 0)

    def test_proposer_self_records_own_block(self):
        n = make_node(1, 4)
        capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        # the proposed block is now the node's own chain head
        self.assertEqual(n.chain.head.slot, 1)
        self.assertEqual(n.chain.head.proposer_idx, 1)

    def test_block_payload_well_formed(self):
        n = make_node(1, 4, workload=[b"TX"])
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        payload = cap.broadcasts[0][1]
        self.assertIsInstance(payload, BlockProposalPayload)
        self.assertEqual(payload.slot, 1)
        self.assertEqual(payload.transactions, (b"TX",))
        self.assertEqual(payload.parent_hash, b"\x00" * 32)   # GENESIS_HASH


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_propose -v`
Expected: FAIL — `_on_start` / `_on_timer` are `pass` stubs.

**Step 3: Implement**

In `src/pos/node.py`:

- `_on_start(t)` — `self.set_timer("slot", self.slot_duration, 1, t)`
  (slot 0 is genesis; the loop proposes from slot 1).
- `_on_timer(timer_id, payload, t)` — dispatch: if `timer_id == "slot"`,
  call `_on_slot(payload, t)`; else silent no-op.
- `_on_slot(slot, t)`:
  1. `epoch = slot // self.slots_per_epoch`.
  2. If `self._proposer_of(slot) == self.id`: call `_propose(slot, t)`.
  3. Attestation belongs to Task 8 — leave a `# Task 8: attest` placeholder.
  4. Re-arm: `self.set_timer("slot", self.slot_duration, slot + 1, t)`.
- `_proposer_of(slot)` → `slot % self.n` (Decision E — the T33 seam; keep
  it a named method).
- `_propose(slot, t)`:
  - `parent = self.chain.head`; `txs = (self.workload.pop(0),) if
    self.workload else ()`.
  - `bh = block_hash(slot=slot, parent_hash=parent.block_hash,
    proposer_idx=self.id, transactions=txs)`.
  - Build `Block(slot, slot // slots_per_epoch, parent.block_hash, bh,
    txs, self.id)`.
  - `BlockProposalPayload(slot, epoch, parent.block_hash, bh, txs,
    self.id)`; `self.broadcast("BLOCK-PROPOSAL", payload, t)`.
  - Self-record: `self._accept_block(block, t)` (Decision C). `_accept_block`
    is the shared seam Task 9's handler also calls — implement a first
    version here: `self.chain.add(block)`; if the block is a checkpoint
    (`slot % slots_per_epoch == 0`), set
    `self._epoch_state(epoch).checkpoint_hash = block.block_hash`; emit
    `CASPER_BLOCK_ACCEPTED` with `{slot, epoch, block_hash: bh.hex()}`.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_propose -v`
Expected: PASS.

---

## Task 8: `node.py` — the slot loop (attesting)

Design spec §6.4 step 3, Decision J. Once per epoch, broadcast an
`ATTESTATION` carrying the FFG `<source, target>` vote; self-record it.

**Files:**
- Modify: `src/pos/node.py`
- Test: `tests/pos/test_node_attest.py`

**Step 1: Write the failing tests**

Create `tests/pos/test_node_attest.py`:

```python
import unittest

from pos.messages import AttestationPayload
from pos.chain import GENESIS_HASH
from _helpers import make_node, capturers, kickoff


class TestAttesting(unittest.TestCase):
    def _advance_to(self, n, last_slot, t0=1.0):
        """Fire the slot timer for slots 1..last_slot."""
        for s in range(1, last_slot + 1):
            n._on_timer("slot", s, t=float(s))

    def test_attestation_emitted_once_per_epoch(self):
        # slots_per_epoch=2, attest_offset=1 -> attest on slots 3,5,7,...
        n = make_node(0, 4, slots_per_epoch=2, attest_offset=1)
        cap = capturers(n); kickoff(n)
        self._advance_to(n, 4)
        # epoch 1 (slots 2,3) attested at slot 3; epoch 2 not yet (slot 5).
        self.assertEqual(cap.count_broadcast("ATTESTATION"), 1)

    def test_attestation_payload_carries_ffg_link(self):
        n = make_node(0, 4, slots_per_epoch=2, attest_offset=1)
        cap = capturers(n); kickoff(n)
        self._advance_to(n, 3)
        att = [b for b in cap.broadcasts if b[0] == "ATTESTATION"][0][1]
        self.assertIsInstance(att, AttestationPayload)
        self.assertEqual(att.ffg.source_epoch, 0)        # genesis epoch
        self.assertEqual(att.ffg.target_epoch, 1)
        self.assertEqual(att.ffg.source_hash, GENESIS_HASH)
        self.assertEqual(att.attester_idx, 0)

    def test_node_self_records_own_ffg_vote(self):
        n = make_node(0, 4, slots_per_epoch=2, attest_offset=1)
        capturers(n); kickoff(n)
        self._advance_to(n, 3)
        es = n.epoch_states[1]
        self.assertEqual(es.link_stake(0), 3.0)          # own stake counted

    def test_casper_attested_event_emitted(self):
        n = make_node(0, 4, slots_per_epoch=2, attest_offset=1)
        cap = capturers(n); kickoff(n)
        self._advance_to(n, 3)
        self.assertEqual(cap.count("casper_attested"), 1)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_attest -v`
Expected: FAIL — no attestation is emitted (Task 7 left a placeholder).

**Step 3: Implement**

In `_on_slot`, replace the Task-7 attestation placeholder. After the
propose step, if `slot % self.slots_per_epoch == self.attest_offset` and
`epoch >= 1`, call `_attest(epoch, slot, t)`:

- `target_cp = self.chain.checkpoint(epoch)` — the epoch's checkpoint
  block; if not yet on the local chain, skip the attestation this run
  (honest-path with a sane `attest_offset` always has it — guard with a
  `try/except KeyError` and a `casper_rejected` reason
  `checkpoint_unavailable`, so a too-early offset fails loud, not silent).
- `source_epoch = self.highest_justified`; `source_cp =
  self.chain.checkpoint(source_epoch)`.
- Build `FFGVote(source_epoch, source_cp.block_hash, epoch,
  target_cp.block_hash)` and `AttestationPayload(slot, epoch, ffg,
  self.id)`.
- `self.broadcast("ATTESTATION", payload, t)`; emit `CASPER_ATTESTED` with
  `{epoch, slot}`.
- Self-record (Decision C): call the shared `_file_ffg_vote(ffg,
  attester_idx=self.id, t=t)` seam — implement it minimally here as
  "record the vote into the target `EpochState`"; Task 10 extends it with
  the justify/finalise transition check:

```python
def _file_ffg_vote(self, ffg, attester_idx, t):
    es = self._epoch_state(ffg.target_epoch)
    stake = self.stake_table[attester_idx]
    if not es.record_vote(ffg.source_epoch, attester_idx, stake):
        return                              # dedupe (Decision I)
    # Task 10: run the justify -> finalise transition here.
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_attest -v`
Expected: PASS.

---

## Task 9: `node.py` — `_on_message` dispatch and the `BLOCK-PROPOSAL` handler

Design spec §7, §7.1, §11. Message dispatch with payload-shape guards;
block validation and acceptance.

**Files:**
- Modify: `src/pos/node.py`
- Test: `tests/pos/test_node_block_handler.py`

**Step 1: Write the failing tests**

Create `tests/pos/test_node_block_handler.py`:

```python
import unittest

from nodes import Message
from pos.chain import GENESIS_HASH, block_hash
from pos.messages import BlockProposalPayload
from pos import node as pos_node
from _helpers import make_node, capturers, kickoff


def _block_msg(src, slot, parent, *, spe=2, txs=(), bad_hash=False):
    bh = b"\xff" * 32 if bad_hash else block_hash(
        slot=slot, parent_hash=parent, proposer_idx=src, transactions=txs)
    pp = BlockProposalPayload(slot=slot, epoch=slot // spe,
                              parent_hash=parent, block_hash=bh,
                              transactions=txs, proposer_idx=src)
    return Message(src=src, dst=0, type="BLOCK-PROPOSAL", payload=pp,
                   t_sent=0.0)


class TestBlockHandler(unittest.TestCase):
    def test_valid_block_is_accepted(self):
        n = make_node(0, 4)                  # slot 1 proposer = 1
        capturers(n); kickoff(n)
        n.on_message(_block_msg(1, 1, GENESIS_HASH), t=1.0)
        self.assertEqual(n.chain.head.slot, 1)

    def test_block_from_non_proposer_rejected(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n.on_message(_block_msg(2, 1, GENESIS_HASH), t=1.0)  # 2 != 1%4
        reasons = [e[1]["reason"] for e in cap.events("casper_rejected")]
        self.assertIn("non_proposer", reasons)

    def test_block_with_bad_hash_rejected(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n.on_message(_block_msg(1, 1, GENESIS_HASH, bad_hash=True), t=1.0)
        reasons = [e[1]["reason"] for e in cap.events("casper_rejected")]
        self.assertIn("hash_mismatch", reasons)

    def test_malformed_payload_rejected_not_crashed(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n.on_message(Message(src=1, dst=0, type="BLOCK-PROPOSAL",
                             payload=None, t_sent=0.0), t=1.0)
        reasons = [e[1]["reason"] for e in cap.events("casper_rejected")]
        self.assertIn("malformed_payload", reasons)

    def test_unknown_message_type_rejected(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n.on_message(Message(src=1, dst=0, type="WAT",
                             payload=None, t_sent=0.0), t=1.0)
        reasons = [e[1]["reason"] for e in cap.events("casper_rejected")]
        self.assertIn("unknown_type", reasons)

    def test_checkpoint_block_sets_epoch_checkpoint_hash(self):
        # slot 2 -> epoch 1 checkpoint. proposer of slot 2 = 2.
        n = make_node(0, 4)
        capturers(n); kickoff(n)
        n.on_message(_block_msg(1, 1, GENESIS_HASH), t=1.0)
        h1 = n.chain.head.block_hash
        n.on_message(_block_msg(2, 2, h1), t=2.0)
        self.assertEqual(n.epoch_states[1].checkpoint_hash,
                         n.chain.head.block_hash)
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_block_handler -v`
Expected: FAIL — `_on_message` is a `pass` stub.

**Step 3: Implement**

In `src/pos/node.py`:

- `_on_message(msg, t)` — dispatch on `msg.type`: `"BLOCK-PROPOSAL"` →
  `_handle_block_proposal`; `"ATTESTATION"` → `_handle_attestation` (Task
  10 — add a `pass` stub for now); anything else → `_reject(t,
  "unknown_type", msg_type=msg.type, src=msg.src)`.
- `_reject(self, t, reason, **fields)` — `self.emit(CASPER_REJECTED,
  {"reason": reason, **fields}, t)` (mirror `PBFTNode._reject`).
- `_handle_block_proposal(msg, t)`:
  1. `bp = msg.payload`; if `not isinstance(bp, BlockProposalPayload)` →
     `_reject(t, "malformed_payload", msg_type="BLOCK-PROPOSAL",
     src=msg.src)`, return.
  2. If `msg.src != self._proposer_of(bp.slot)` → `_reject(t,
     "non_proposer", slot=bp.slot, src=msg.src)`, return.
  3. If `bp.epoch != bp.slot // self.slots_per_epoch` → `_reject(t,
     "epoch_mismatch", slot=bp.slot, src=msg.src)`, return.
  4. Recompute the hash; if `block_hash(slot=bp.slot,
     parent_hash=bp.parent_hash, proposer_idx=bp.proposer_idx,
     transactions=bp.transactions) != bp.block_hash` → `_reject(t,
     "hash_mismatch", slot=bp.slot, src=msg.src)`, return.
  5. Build the `Block` from the payload and call `_accept_block(block, t)`
     (the Task-7 seam — `Chain.add` handles the unknown-parent buffering,
     so no parent check is needed here).

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_block_handler -v`
Expected: PASS.

---

## Task 10: `node.py` — the `ATTESTATION` handler and FFG transitions

Design spec §5.3, §7.2, Decision G/H/I. File received FFG votes; run the
justify→finalise transition; emit `decided` on finalisation.

**Files:**
- Modify: `src/pos/node.py`
- Test: `tests/pos/test_node_finality.py`

**Step 1: Write the failing tests**

Create `tests/pos/test_node_finality.py`:

```python
import unittest

from nodes import Message
from pos.chain import GENESIS_HASH, block_hash
from pos.epoch import EpochFSM
from pos.messages import FFGVote, AttestationPayload
from _helpers import make_node, capturers, kickoff


def _att_msg(src, source_epoch, source_hash, target_epoch, target_hash):
    ffg = FFGVote(source_epoch, source_hash, target_epoch, target_hash)
    pp = AttestationPayload(slot=0, epoch=target_epoch, ffg=ffg,
                            attester_idx=src)
    return Message(src=src, dst=0, type="ATTESTATION", payload=pp,
                   t_sent=0.0)


class TestFinality(unittest.TestCase):
    def _checkpoint_hashes(self, n, upto_epoch):
        """Drive the slot loop far enough to populate the chain's
        checkpoints for epochs 1..upto_epoch; return {epoch: hash}."""
        capturers(n); kickoff(n)
        last_slot = (upto_epoch + 1) * n.slots_per_epoch
        for s in range(1, last_slot + 1):
            # feed every node's proposer; here drive node's own loop only
            n._on_timer("slot", s, t=float(s))
        return {e: n.chain.checkpoint(e).block_hash
                for e in range(0, upto_epoch + 1)}

    def test_supermajority_justifies_epoch(self):
        n = make_node(0, 4, slots_per_epoch=2)   # total stake 12, 2/3 = 8
        cps = self._checkpoint_hashes(n, upto_epoch=2)
        # 3 peers x 3.0 stake = 9 >= 8 -> epoch 1 justified.
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        self.assertIs(n.epoch_states[1].state, EpochFSM.JUSTIFIED)

    def test_one_vote_short_does_not_justify(self):
        n = make_node(0, 4, slots_per_epoch=2)
        cps = self._checkpoint_hashes(n, upto_epoch=2)
        for src in (1, 2):                       # 2 x 3 = 6 < 8
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        self.assertIs(n.epoch_states[1].state, EpochFSM.UNJUSTIFIED)

    def test_two_links_finalise_and_emit_decided(self):
        n = make_node(0, 4, slots_per_epoch=2)
        cap_events = n.emit  # placeholder; real capture below
        cps = self._checkpoint_hashes(n, upto_epoch=3)
        cap = capturers(n)                       # re-capture after the drive
        # link <0,1>: justifies epoch 1
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        # link <1,2>: justifies epoch 2 AND finalises epoch 1
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 1, cps[1], 2, cps[2]), t=11.0)
        self.assertIs(n.epoch_states[1].state, EpochFSM.FINALISED)
        self.assertIs(n.epoch_states[2].state, EpochFSM.JUSTIFIED)
        decided = cap.events("decided")
        self.assertEqual(len(decided), 1)
        self.assertEqual(decided[0][1]["instance_id"], 1)
        self.assertEqual(decided[0][1]["value"], cps[1].hex())

    def test_decided_emitted_once_per_epoch(self):
        n = make_node(0, 4, slots_per_epoch=2)
        cps = self._checkpoint_hashes(n, upto_epoch=3)
        cap = capturers(n)
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 1, cps[1], 2, cps[2]), t=11.0)
        # a stray extra vote on the <1,2> link must not re-finalise epoch 1
        n.on_message(_att_msg(0, 1, cps[1], 2, cps[2]), t=12.0)
        self.assertEqual(len(cap.events("decided")), 1)

    def test_attester_outside_set_rejected(self):
        n = make_node(0, 4, slots_per_epoch=2)
        cps = self._checkpoint_hashes(n, upto_epoch=2)
        cap = capturers(n)
        bad = _att_msg(9, 0, cps[0], 1, cps[1])      # attester_idx 9 >= n
        n.on_message(bad, t=10.0)
        self.assertIn("attester_out_of_range",
                      [e[1]["reason"] for e in cap.events("casper_rejected")])

    def test_non_uniform_stake_justifies_on_stake(self):
        # stakes 9,1,1,1 (total 12, 2/3 = 8). Node 0 alone (stake 9) > 8.
        st = {0: 9.0, 1: 1.0, 2: 1.0, 3: 1.0}
        n = make_node(1, 4, slots_per_epoch=2, stake_table=st)
        cps = self._checkpoint_hashes(n, upto_epoch=2)
        cap = capturers(n)
        n.on_message(_att_msg(0, 0, cps[0], 1, cps[1]), t=10.0)
        self.assertIs(n.epoch_states[1].state, EpochFSM.JUSTIFIED)
```

> Note for the executing engineer: the `_checkpoint_hashes` helper drives a
> single node's own slot loop so its `Chain` has every checkpoint block.
> The slot loop also self-files the node's own FFG votes; the tests above
> add the *peer* votes needed to cross the threshold. If a node's own
> self-vote already counts toward a link, adjust the peer set so the
> assertion still pins the exact threshold — keep the assertions, tune the
> fixture (per `superpowers:test-driven-development`).

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_finality -v`
Expected: FAIL — `_handle_attestation` is a stub; no transitions run.

**Step 3: Implement**

In `src/pos/node.py`:

- `_handle_attestation(msg, t)`:
  1. `ap = msg.payload`; if `not isinstance(ap, AttestationPayload)` →
     `_reject(t, "malformed_payload", msg_type="ATTESTATION", src=msg.src)`,
     return.
  2. If `not 0 <= ap.attester_idx < self.n` → `_reject(t,
     "attester_out_of_range", src=msg.src)`, return.
  3. If `ap.ffg.target_epoch != ap.epoch` → `_reject(t, "epoch_mismatch",
     src=msg.src)`, return.
  4. `self._file_ffg_vote(ap.ffg, ap.attester_idx, t)`.
- Extend `_file_ffg_vote` (the Task-8 seam) — after `record_vote` succeeds,
  call `_run_ffg_transitions(ffg.source_epoch, ffg.target_epoch, t)`.
- `_is_justified(epoch)` → `epoch == 0 or
  self._epoch_state(epoch).state in (JUSTIFIED, FINALISED)`.
- `_run_ffg_transitions(source_epoch, target_epoch, t)` — design spec §5.3:

```python
def _run_ffg_transitions(self, source_epoch, target_epoch, t):
    tgt = self._epoch_state(target_epoch)
    # 1. Justify the target.
    if (tgt.state is EpochFSM.UNJUSTIFIED
            and self._is_justified(source_epoch)
            and meets_supermajority(tgt.link_stake(source_epoch),
                                    self.total_stake)):
        tgt.state = EpochFSM.JUSTIFIED
        self.highest_justified = max(self.highest_justified, target_epoch)
        self.emit(CASPER_JUSTIFIED,
                  {"epoch": target_epoch,
                   "checkpoint_hash": _hexor(tgt.checkpoint_hash)}, t)
        # 2. Finalise the source if target is its direct child.
        src = self._epoch_state(source_epoch)
        if (target_epoch == source_epoch + 1
                and src.state is EpochFSM.JUSTIFIED):
            src.state = EpochFSM.FINALISED
            self.highest_finalised = max(self.highest_finalised,
                                         source_epoch)
            self._finalise(source_epoch, t)
```

- `_finalise(epoch, t)` — emit `CASPER_FINALISED` with `{epoch,
  checkpoint_hash}`; then, if `epoch not in self.decided_epochs`, add it
  and emit the mandatory `decided` event via the base helper:
  `self._emit_decided(value=checkpoint_hash.hex(), instance_id=epoch, t=t)`
  (Decision G — once per epoch).
- `_hexor(h)` — small helper: `h.hex() if h is not None else None` (the
  checkpoint hash may be unset if an attestation outran block delivery).

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src:tests/pos python3 -m unittest test_node_finality -v`
Expected: PASS. Then run the whole suite:
`PYTHONPATH=src:tests/pos python3 -m unittest discover -s tests/pos -v`
Expected: every `tests/pos` test green.

---

## Task 11: Integration — the Casper baseline e2e test

Design spec §12.2. The full Week-3 stack drives `CasperNode` validators to
epoch finalisation; determinism holds.

**Files:**
- Create: `tests/integration/test_casper_baseline.py`

**Step 1: Write the test**

Model the harness on `tests/integration/test_pbft_consensus.py` —
`_config`, a `_factory` closure, `_run`, `_count_event`. The factory builds
the shared `stake_table` once and passes each node its own `weight`. A
Casper run has no quiescence, so bound it with `t_max` covering ~3 epochs.

```python
import math
import unittest
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from pos import CasperNode

_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)


def _config(n, t_max):
    return Config(n=n, t_max=t_max, seeds=SeedsConfig(n_runs=1),
                  network=_MINIMAL_DELAY, adversary=MappingProxyType({}),
                  protocol_knobs=MappingProxyType({}),
                  workload=MappingProxyType({}))


def _factory(n, stake_table, *, slots_per_epoch=2, slot_duration=1.0):
    def make(node_id, global_seed):
        return CasperNode(node_id=node_id, weight=stake_table[node_id],
                          endpoint=None, global_seed=global_seed, n=n,
                          stake_table=stake_table,
                          slot_duration=slot_duration,
                          slots_per_epoch=slots_per_epoch)
    return make


def _run(n, *, stake_table=None, t_max=20.0, global_seed=42,
         slots_per_epoch=2):
    st = stake_table or {i: 3.0 for i in range(n)}
    logger = EventLogger()
    handle = build_run(_config(n, t_max), global_seed,
                       _factory(n, st, slots_per_epoch=slots_per_epoch))
    handle.scheduler.event_sink = logger.sink
    result = handle.scheduler.run()
    return logger, result


def _count(records, event_type):
    return sum(1 for r in records if r.event_type == event_type)


class TestCasperBaseline_n4(unittest.TestCase):
    def test_epochs_finalise(self):
        logger, _ = _run(n=4, t_max=20.0)
        self.assertGreaterEqual(_count(logger.records, "casper_finalised"), 1)
        self.assertGreaterEqual(_count(logger.records, "decided"), 1)

    def test_no_rejections(self):
        logger, _ = _run(n=4, t_max=20.0)
        self.assertEqual(_count(logger.records, "casper_rejected"), 0)

    def test_decided_in_epoch_order(self):
        logger, _ = _run(n=4, t_max=20.0)
        epochs = [r.fields["instance_id"] for r in logger.records
                  if r.event_type == "decided"]
        self.assertEqual(epochs, sorted(epochs))

    def test_determinism(self):
        a, _ = _run(n=4, t_max=20.0, global_seed=42)
        b, _ = _run(n=4, t_max=20.0, global_seed=42)
        self.assertEqual(list(a.records), list(b.records))


class TestCasperBaseline_n7(unittest.TestCase):
    def test_epochs_finalise(self):
        logger, _ = _run(n=7, t_max=20.0)
        self.assertGreaterEqual(_count(logger.records, "decided"), 1)

    def test_determinism(self):
        a, _ = _run(n=7, t_max=20.0, global_seed=42)
        b, _ = _run(n=7, t_max=20.0, global_seed=42)
        self.assertEqual(list(a.records), list(b.records))


class TestCasperBaseline_nonuniform_stake(unittest.TestCase):
    def test_finalises_with_unequal_stake(self):
        st = {0: 5.0, 1: 4.0, 2: 2.0, 3: 1.0}     # total 12
        logger, _ = _run(n=4, stake_table=st, t_max=20.0)
        self.assertGreaterEqual(_count(logger.records, "decided"), 1)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the test**

Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_casper_baseline -v`
Expected: with Tasks 1–10 done, the protocol code exists — the test should
PASS once the harness is correct and `t_max` is large enough.

**Step 3: Tune `t_max` / `slots_per_epoch` if needed**

If no epoch finalises, the run is too short — epoch `e` finalises only
once epoch `e+1` is justified, so the run must reach at least slot
`3 · slots_per_epoch + attest_offset`. Raise `t_max` (each slot is
`slot_duration` apart) until at least one `decided` fires. Do **not**
weaken assertions; tune the run. If a genuine protocol bug surfaces, fix
it in `src/pos/` and add a reproducing unit test to `tests/pos/` per
`superpowers:systematic-debugging`. Record the working `t_max` /
`slots_per_epoch` in the test docstring.

**Step 4: Re-run to confirm green**

Run: `PYTHONPATH=src:tests/integration python3 -m unittest test_casper_baseline -v`
Expected: PASS.

---

## Task 12: Experiment page and wiki updates

Design spec §13. The build-verification page, index/log updates, and the
`## Revisions` entries from spec §15.

**Files:**
- Create: `wiki/experiments/2026-05-23_casper-baseline.md`
- Modify: `wiki/index.md`
- Modify: `wiki/log.md`
- Modify: `wiki/concepts/system-design-protocols.md` (`## Revisions`)
- Modify: `wiki/concepts/message-types.md` (`## Revisions`)

**Step 1: Write the experiment page**

Create `wiki/experiments/2026-05-23_casper-baseline.md` following the T29
template (`2026-05-21_pbft-consensus-baseline.md`): a one-paragraph framing
(build-verification of the Casper FFG honest-path core across the W3
stack); a Configuration section (n=4/7, uniform and non-uniform stake,
`slots_per_epoch`, `slot_duration`, `t_max`, `global_seed`); the Re-run
commands; a Result section with the per-scenario event counts
(`casper_block_accepted`, `casper_attested`, `casper_justified`,
`casper_finalised`, `decided`, `casper_rejected`) filled from the **actual**
test output; a determinism confirmation; and a one-paragraph Observation.
Add a Back-links section to `[[algorithms/pos]]`,
`[[concepts/system-design-protocols]]`, `[[concepts/node-model]]`,
`[[concepts/message-types]]`, `[[concepts/simulation-design]]`.

**Step 2: Update `wiki/index.md`**

Add under `## Experiments`, in the established `- [[path]] — summary`
style:
`- [[experiments/2026-05-23_casper-baseline]] — T32 build-verification baseline: the simplified Casper FFG honest-path core across the W3 stack; n=4/7 runs justify and finalise epochs through two-round FFG aggregation, decided fires in epoch order, determinism byte-identical.`

**Step 3: Append to `wiki/log.md`**

Append one entry per `docs/wiki-spec.md` § Log format:
`## [2026-05-23] code | task 32 — implement simplified Casper FFG consensus`,
role Engineer, the touched-file list, a 1–3 sentence note.

**Step 4: Add the `## Revisions` entries**

Per design spec §15:

- `wiki/concepts/system-design-protocols.md` — append a `## Revisions`
  entry dated 2026-05-23 (T32): the §3 Casper sketch attests every slot and
  references a `self.lmd_ghost` fork-choice object; the T32 implementation
  attests once per epoch (Decision J) and has no fork-choice object
  (Approach 1 — LMD-GHOST deferred). The control spine — slot loop,
  per-epoch FFG aggregation, justify→finalise, `decided` on finalisation —
  is unchanged.
- `wiki/concepts/message-types.md` — append a `## Revisions` entry dated
  2026-05-23 (T32): the §4 `ATTESTATION` payload omits `head_vote_hash`
  (LMD-GHOST out of scope) and per-validator `signature`; `BLOCK-PROPOSAL`
  omits `proposer_sig` — the simulator passes Python objects, not signed
  bytes, and performs no signature verification. The §4 byte-size columns
  therefore overstate the wire payloads by the omitted fields.

**Step 5: Verify wikilinks resolve**

Confirm the new `wiki/index.md` line and the experiment page's back-links
point at files that exist on disk.

---

## Task 13: Verification, In-Review flip, and handoff

**Files:**
- Modify: `TASKS.md` (status flip + dashboard)

**Step 1: Run the full test suite**

REQUIRED SUB-SKILL: `superpowers:verification-before-completion`.

Run every suite and record the pass counts:
```
make test
```
or, suite by suite:
```
PYTHONPATH=src:tests/pos python3 -m unittest discover -s tests/pos -v
PYTHONPATH=src:tests/integration python3 -m unittest discover -s tests/integration -v
PYTHONPATH=src:tests/scheduler python3 -m unittest discover -s tests/scheduler -v
PYTHONPATH=src:tests/nodes python3 -m unittest discover -s tests/nodes -v
PYTHONPATH=src:tests/network python3 -m unittest discover -s tests/network -v
PYTHONPATH=src:tests/event_log python3 -m unittest discover -s tests/event_log -v
PYTHONPATH=src:tests/config python3 -m unittest discover -s tests/config -v
PYTHONPATH=src:tests/pbft python3 -m unittest discover -s tests/pbft -v
```
Expected: all green. The upstream suites (scheduler/nodes/network/
event_log/config/pbft) must be unchanged from the pre-T32 baseline — T32
added a new package and a new suite and touched no existing `src/` file.

**Step 2: Confirm artifacts exist**

Verify on disk: `src/pos/{__init__,messages,chain,epoch,node}.py`; the
`tests/pos/` suite (`_helpers.py` + the test modules); the new
`tests/integration/test_casper_baseline.py`; the experiment page; the
`wiki/index.md` / `wiki/log.md` updates; the two `## Revisions` entries.

**Step 3: Flip `TASKS.md` to In Review**

In `TASKS.md`: change T32 `[~]` → `[?]`; update the dashboard line
(`In Progress: 1 → 0`, `In Review: 1 → 2`).

**Step 4: Hand off to the human**

Summarize for the human per `docs/workflow.md` step 9: files touched, the
new wiki experiment page and the two Revisions, the design decisions
(Approach 1 honest-path core; inline round-robin proposer and 2/3 finality
as the T33/T34 seams; one attestation per epoch), the confirmation that
backlog follow-up (a) needed no work and (b) stays deferred, and any open
questions. State the suggested commit message — `task 32: implement
simplified Casper FFG consensus` — and the branch `task/T32-pos-consensus`.
The human reviews, commits, and merges.

---

## Notes for the executing engineer

- Read the design spec
  `docs/superpowers/specs/2026-05-23-t32-pos-consensus-design.md` first —
  it carries the decision table and section-level behaviour; this plan
  gives the test-first sequence and the exact test code.
- TDD throughout (`superpowers:test-driven-development`): write the test,
  watch it fail, implement the minimum, watch it pass. Never weaken an
  assertion to make a test green — if a test and the code disagree,
  diagnose which is wrong.
- Tasks 7–8 introduce shared seams (`_accept_block`, `_file_ffg_vote`) that
  later tasks extend. Tasks 8–10 leave `pass` stubs (the attestation step
  in Task 7's `_on_slot`, `_handle_attestation` in Task 9); do not forget
  to replace them.
- T32 modifies no existing `src/` file. If an upstream suite breaks, that
  is a real regression — stop and use `superpowers:systematic-debugging`;
  do not edit upstream tests.
- The whole T32 change is **one commit** at Task 13; the agent runs no
  per-task `git commit`.
