"""SnowmanNode constructor and rescaled-parameter defaults (design spec §6.1)."""
import unittest

from snowman.node import SnowmanNode


def _kwargs(**overrides):
    base = dict(node_id=0, weight=1.0, endpoint=None, global_seed=42, n=4)
    base.update(overrides)
    return base


class TestInitRescaledDefaults(unittest.TestCase):
    def test_n_4_defaults(self):
        node = SnowmanNode(**_kwargs(n=4))
        self.assertEqual(node.n, 4)
        self.assertEqual(node.K, 3)
        self.assertEqual(node.alpha_p, 2)
        self.assertEqual(node.alpha_c, 3)
        self.assertEqual(node.beta, 15)

    def test_n_7_defaults(self):
        node = SnowmanNode(**_kwargs(node_id=3, n=7))
        self.assertEqual((node.K, node.alpha_p, node.alpha_c), (6, 4, 5))

    def test_n_10_defaults(self):
        node = SnowmanNode(**_kwargs(n=10))
        self.assertEqual((node.K, node.alpha_p, node.alpha_c), (9, 5, 8))

    def test_explicit_override(self):
        node = SnowmanNode(**_kwargs(
            n=4, K=2, alpha_p=2, alpha_c=2, beta=3))
        self.assertEqual((node.K, node.alpha_p, node.alpha_c, node.beta),
                         (2, 2, 2, 3))


class TestInitPreconditions(unittest.TestCase):
    def test_n_below_two_rejected(self):
        for bad_n in (-1, 0, 1):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    SnowmanNode(**_kwargs(n=bad_n))

    def test_node_id_outside_range_rejected(self):
        with self.assertRaises(ValueError):
            SnowmanNode(**_kwargs(node_id=5, n=4))

    def test_slot_duration_nonpositive_rejected(self):
        with self.assertRaises(ValueError):
            SnowmanNode(**_kwargs(n=4, slot_duration=0))


if __name__ == "__main__":
    unittest.main()
