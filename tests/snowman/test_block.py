"""Tests for block.py (design spec §4) — Block + hash_block + ConflictSet + Chain."""
import unittest

from snowman.block import (
    Block,
    Chain,
    CSState,
    ConflictSet,
    GENESIS_ID,
    hash_block,
)


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


def _b(block_id: bytes, parent_id: bytes = GENESIS_ID, slot: int = 1,
       proposer_idx: int = 0) -> Block:
    return Block(block_id=block_id, parent_id=parent_id, slot=slot,
                 proposer_idx=proposer_idx, transactions=())


class TestConflictSet(unittest.TestCase):
    def test_initial_state(self):
        cs = ConflictSet(parent_id=GENESIS_ID)
        self.assertEqual(cs.members, {})
        self.assertEqual(cs.confidence, {})
        self.assertEqual(cs.preference, b"")
        self.assertEqual(cs.counter, 0)
        self.assertIs(cs.state, CSState.POLLING)

    def test_first_block_becomes_preference(self):
        cs = ConflictSet(parent_id=GENESIS_ID)
        cs.add_block(_b(b"a" * 32))
        self.assertEqual(cs.preference, b"a" * 32)
        self.assertIn(b"a" * 32, cs.members)
        self.assertEqual(cs.confidence[b"a" * 32], 0)

    def test_second_block_does_not_change_preference(self):
        cs = ConflictSet(parent_id=GENESIS_ID)
        cs.add_block(_b(b"a" * 32))
        cs.add_block(_b(b"b" * 32))
        self.assertEqual(cs.preference, b"a" * 32)
        self.assertIn(b"b" * 32, cs.members)

    def test_idempotent_re_add(self):
        cs = ConflictSet(parent_id=GENESIS_ID)
        b = _b(b"a" * 32)
        cs.add_block(b)
        cs.add_block(b)
        self.assertEqual(len(cs.members), 1)
        self.assertEqual(cs.confidence[b"a" * 32], 0)


class TestChain(unittest.TestCase):
    def test_initial_tip_is_genesis(self):
        c = Chain()
        self.assertEqual(c.tip, GENESIS_ID)
        self.assertEqual(c.accepted, {})

    def test_on_announce_extends_tip(self):
        c = Chain()
        c.on_announce(_b(b"a" * 32, GENESIS_ID, slot=1))
        self.assertEqual(c.tip, b"a" * 32)
        c.on_announce(_b(b"b" * 32, b"a" * 32, slot=2))
        self.assertEqual(c.tip, b"b" * 32)

    def test_on_announce_with_unknown_parent_is_noop(self):
        """Out-of-order arrival; design spec §4 short-circuits."""
        c = Chain()
        c.on_announce(_b(b"a" * 32, parent_id=b"z" * 32, slot=2))
        self.assertEqual(c.tip, GENESIS_ID)

    def test_on_announce_sibling_does_not_change_tip(self):
        """Two siblings of genesis; tip is the first one seen, not the
        deeper of two equal-depth blocks."""
        c = Chain()
        c.on_announce(_b(b"a" * 32, GENESIS_ID, slot=1))
        c.on_announce(_b(b"b" * 32, GENESIS_ID, slot=1))
        self.assertEqual(c.tip, b"a" * 32)

    def test_on_accept_records(self):
        c = Chain()
        b = _b(b"a" * 32, GENESIS_ID, slot=1)
        c.on_announce(b)
        c.on_accept(b)
        self.assertEqual(c.accepted, {b"a" * 32: b})


if __name__ == "__main__":
    unittest.main()
