"""Unit tests for the shared-layer Node (node-model.md, T22)."""
import unittest

from nodes import Lifecycle, Node
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


if __name__ == "__main__":
    unittest.main()
