"""Unit tests for the shared-layer Node (node-model.md, T22)."""
import unittest

from nodes import Lifecycle, Node
from nodes.node import _stable_seed
from _helpers import FakeNode


class TestConstruction(unittest.TestCase):
    def test_identity_attributes_stored(self):
        n = FakeNode(node_id=7, weight=2.5, endpoint="addr", global_seed=1)
        self.assertEqual((n.id, n.weight, n.endpoint), (7, 2.5, "addr"))

    def test_starts_in_created_status(self):
        self.assertIs(FakeNode().status, Lifecycle.CREATED)

    def test_adversary_slot_defaults_none(self):
        self.assertIsNone(FakeNode().adversary)

    def test_zero_weight_accepted(self):
        self.assertEqual(FakeNode(weight=0.0).weight, 0.0)

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            FakeNode(weight=-1.0)

    def test_node_is_abstract(self):
        with self.assertRaises(TypeError):
            Node(0, 1.0, None, 0)  # type: ignore[abstract]


class TestRng(unittest.TestCase):
    def test_stable_seed_is_fixed_for_fixed_input(self):
        # Process-stable: blake2b, not Python's randomised hash().
        self.assertEqual(_stable_seed(0, 0), _stable_seed(0, 0))
        self.assertIsInstance(_stable_seed(7, 3), int)
        # Pinned literal: a change to endianness, digest_size, or the seed
        # string format would alter this value and fail loudly.
        self.assertEqual(_stable_seed(42, 5), 4445322452963505364)

    def test_same_seed_and_id_give_identical_streams(self):
        a = FakeNode(node_id=5, global_seed=42)
        b = FakeNode(node_id=5, global_seed=42)
        self.assertEqual([a.rng.random() for _ in range(5)],
                         [b.rng.random() for _ in range(5)])

    def test_different_id_diverges(self):
        a = FakeNode(node_id=1, global_seed=42)
        b = FakeNode(node_id=2, global_seed=42)
        self.assertNotEqual(a.rng.random(), b.rng.random())

    def test_different_global_seed_diverges(self):
        a = FakeNode(node_id=1, global_seed=1)
        b = FakeNode(node_id=1, global_seed=2)
        self.assertNotEqual(a.rng.random(), b.rng.random())


if __name__ == "__main__":
    unittest.main()
