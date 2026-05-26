import unittest

from pos.chain import Block, block_hash, Chain, GENESIS, GENESIS_HASH


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
        self.assertTrue(Block(slot=4, epoch=2, parent_hash=b"p" * 32,
                              block_hash=b"b" * 32, transactions=(),
                              proposer_idx=0).slot % 2 == 0)


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


if __name__ == "__main__":
    unittest.main()
