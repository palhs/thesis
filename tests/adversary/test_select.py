"""slow_node_ids: highest-id ⌊f·n⌋ selection (T51, spec §3.3)."""
from __future__ import annotations

import unittest

from adversary.select import byzantine_node_ids, slow_node_ids


class TestSlowNodeIds(unittest.TestCase):
    def test_floor_count_n10(self):
        # n=10: f=0.10 -> 1, f=0.20 -> 2, f=0.30 -> 3.
        self.assertEqual(slow_node_ids(10, 0.10), (9,))
        self.assertEqual(slow_node_ids(10, 0.20), (8, 9))
        self.assertEqual(slow_node_ids(10, 0.30), (7, 8, 9))

    def test_floor_count_n25(self):
        # n=25: f=0.10 -> 2 (floor 2.5), f=0.20 -> 5, f=0.30 -> 7 (floor 7.5).
        self.assertEqual(slow_node_ids(25, 0.10), (23, 24))
        self.assertEqual(slow_node_ids(25, 0.20), (20, 21, 22, 23, 24))
        self.assertEqual(slow_node_ids(25, 0.30), (18, 19, 20, 21, 22, 23, 24))

    def test_zero_fraction_is_empty(self):
        self.assertEqual(slow_node_ids(10, 0.0), ())
        self.assertEqual(slow_node_ids(25, 0.0), ())

    def test_excludes_primary_for_all_f_below_one(self):
        # Node 0 (PBFT view-0 primary) must never be slow while f < 1.
        for n in (10, 25):
            for f in (0.10, 0.20, 0.30):
                self.assertNotIn(0, slow_node_ids(n, f),
                                 msg=f"n={n} f={f}")

    def test_returns_sorted_ascending(self):
        ids = slow_node_ids(25, 0.30)
        self.assertEqual(list(ids), sorted(ids))


class TestByzantineNodeIds(unittest.TestCase):
    def test_lowest_ids_include_primary(self):
        self.assertEqual(byzantine_node_ids(10, 0.4), (0, 1, 2, 3))

    def test_zero_is_empty(self):
        self.assertEqual(byzantine_node_ids(10, 0.0), ())

    def test_floor(self):
        self.assertEqual(byzantine_node_ids(25, 0.33), (0, 1, 2, 3, 4, 5, 6, 7))

    def test_rejects_out_of_range_f(self):
        with self.assertRaises(ValueError):
            byzantine_node_ids(10, 1.5)


if __name__ == "__main__":
    unittest.main()
