"""Equivocate adversary shared helpers: partition split + conflicting payloads (T53)."""
from __future__ import annotations

import unittest

from adversary.equivocate import conflicting_bytes, split_recipients


class _FakeNode:
    def __init__(self, n, node_id):
        self.n, self.id = n, node_id


class TestPartition(unittest.TestCase):
    def test_split_node0_exact_halves(self):
        lo, hi = split_recipients(_FakeNode(10, 0))
        self.assertEqual(lo, (1, 2, 3, 4))
        self.assertEqual(hi, (5, 6, 7, 8, 9))

    def test_split_excludes_self(self):
        lo, hi = split_recipients(_FakeNode(10, 0))
        self.assertNotIn(0, lo)
        self.assertNotIn(0, hi)

    def test_split_is_pure_on_recall(self):
        node = _FakeNode(10, 0)
        self.assertEqual(split_recipients(node), split_recipients(node))

    def test_split_node5_excludes_self_partitions_peers(self):
        node = _FakeNode(10, 5)
        lo, hi = split_recipients(node)
        self.assertNotIn(5, lo)
        self.assertNotIn(5, hi)
        peers = tuple(i for i in range(10) if i != 5)
        # lo+hi together cover all peers, disjoint, sizes differ by <= 1.
        self.assertEqual(tuple(sorted(lo + hi)), peers)
        self.assertEqual(set(lo) & set(hi), set())
        self.assertLessEqual(abs(len(lo) - len(hi)), 1)

    def test_conflicting_bytes_distinct_and_bytes(self):
        a, b = conflicting_bytes("pbft", 0, 3)
        self.assertNotEqual(a, b)
        self.assertIsInstance(a, bytes)
        self.assertIsInstance(b, bytes)

    def test_conflicting_bytes_deterministic_on_recall(self):
        self.assertEqual(conflicting_bytes("pbft", 0, 3),
                         conflicting_bytes("pbft", 0, 3))

    def test_conflicting_bytes_keyed(self):
        self.assertNotEqual(conflicting_bytes("pbft", 0, 3),
                            conflicting_bytes("pbft", 0, 4))


if __name__ == "__main__":
    unittest.main()
