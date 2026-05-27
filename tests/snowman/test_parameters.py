"""Tests for the Snowman parameter rescaling rule (design spec §7)."""
import unittest

from snowman.parameters import snowman_parameters


class TestSnowmanParametersTable(unittest.TestCase):
    """The exact five-row table from metric-reconciliation.md."""

    EXPECTED = {
        4:  (3,  2,  3),
        7:  (6,  4,  5),
        10: (9,  5,  8),
        16: (15, 8, 12),
        25: (20, 11, 16),
    }

    def test_table(self):
        for n, expected in self.EXPECTED.items():
            with self.subTest(n=n):
                self.assertEqual(snowman_parameters(n), expected)


class TestEarlyCloseSafetyInvariant(unittest.TestCase):
    """alpha_p + alpha_c > K for every K used by the simulator.

    Section 5 of the design spec relies on this invariant for
    success-path early-close to be flip-safe. If a future rescaling-rule
    change breaks the invariant, this test fails immediately.
    """

    def test_invariant_holds_for_thesis_n_range(self):
        for n in range(2, 22):
            with self.subTest(n=n):
                K, alpha_p, alpha_c = snowman_parameters(n)
                self.assertGreater(
                    alpha_p + alpha_c, K,
                    f"alpha_p+alpha_c > K violated at n={n}: "
                    f"K={K}, alpha_p={alpha_p}, alpha_c={alpha_c}")


class TestPreconditions(unittest.TestCase):
    def test_n_below_two_raises(self):
        for bad_n in (-1, 0, 1):
            with self.subTest(n=bad_n):
                with self.assertRaises(ValueError):
                    snowman_parameters(bad_n)


class TestProductionParity(unittest.TestCase):
    """At n=25, (K, alpha_p, alpha_c) matches [ava-docs] exactly."""

    def test_n_25_matches_avalanche_production(self):
        self.assertEqual(snowman_parameters(25), (20, 11, 16))


if __name__ == "__main__":
    unittest.main()
