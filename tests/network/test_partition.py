"""Unit tests for Partition.blocks (network-model-phases.md §4)."""
import unittest

from network.phases import Partition


class TestPartitionBlocks(unittest.TestCase):
    def setUp(self):
        # two groups: {0,1} | {2,3}; node 4 is unconstrained
        self.part = Partition(groups=((0, 1), (2, 3)))

    def test_same_group_not_blocked(self):
        self.assertFalse(self.part.blocks(0, 1))
        self.assertFalse(self.part.blocks(2, 3))

    def test_cross_group_blocked_both_directions(self):
        self.assertTrue(self.part.blocks(0, 2))
        self.assertTrue(self.part.blocks(2, 0))

    def test_unconstrained_node_reachable(self):
        self.assertFalse(self.part.blocks(4, 0))
        self.assertFalse(self.part.blocks(0, 4))
        self.assertFalse(self.part.blocks(4, 4))

    def test_asymmetric_blocks_all_cross_edges_in_v1(self):
        # v1: symmetric=False behaves identically to symmetric=True
        asym = Partition(groups=((0, 1), (2, 3)), symmetric=False)
        self.assertTrue(asym.blocks(0, 2))
        self.assertTrue(asym.blocks(2, 0))


if __name__ == "__main__":
    unittest.main()
