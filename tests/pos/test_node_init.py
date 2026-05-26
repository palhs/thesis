import unittest

from pos import node as pos_node
from pos.node import CasperNode
from _helpers import make_node


class TestConstructor(unittest.TestCase):
    def test_basic_attributes(self):
        n = make_node(2, 4, slots_per_epoch=2)
        self.assertEqual(n.id, 2)
        self.assertEqual(n.n, 4)
        self.assertEqual(n.slots_per_epoch, 2)
        self.assertEqual(n.total_stake, 12.0)   # 4 x 3.0

    def test_rejects_bad_n(self):
        with self.assertRaises(ValueError):
            CasperNode(node_id=0, weight=0.0, endpoint=None, global_seed=42,
                       n=0, stake_table={})

    def test_rejects_node_id_outside_range(self):
        with self.assertRaises(ValueError):
            CasperNode(node_id=9, weight=3.0, endpoint=None, global_seed=42,
                       n=4, stake_table={i: 3.0 for i in range(4)})

    def test_rejects_nonpositive_slot_duration(self):
        with self.assertRaises(ValueError):
            make_node(0, 4, slot_duration=0.0)

    def test_rejects_nonpositive_slots_per_epoch(self):
        with self.assertRaises(ValueError):
            make_node(0, 4, slots_per_epoch=0)

    def test_rejects_stake_table_mismatch(self):
        with self.assertRaises(ValueError):
            make_node(0, 4, stake_table={0: 3.0, 1: 3.0})   # missing 2,3

    def test_rejects_zero_total_stake(self):
        # All-zero per-validator stake passes the >= 0 check but yields
        # total_stake = 0, which would let the 2/3 threshold be met
        # vacuously by an empty quorum. T34 precondition for the
        # finality rule.
        with self.assertRaises(ValueError):
            make_node(0, 4, stake_table={i: 0.0 for i in range(4)})

    def test_event_constants_exist(self):
        for name in ("CASPER_BLOCK_ACCEPTED", "CASPER_ATTESTED",
                     "CASPER_JUSTIFIED", "CASPER_FINALISED",
                     "CASPER_REJECTED"):
            self.assertTrue(hasattr(pos_node, name))

    def test_genesis_epoch_finalised_at_construction(self):
        from pos.epoch import EpochFSM
        n = make_node(0, 4)
        self.assertIs(n.epoch_states[0].state, EpochFSM.FINALISED)


if __name__ == "__main__":
    unittest.main()
