"""Unit + regression tests for src/output/delay_analysis.py (T48).

The data layer is tested (the render layer in delay_plots.py is not, per the
project convention). Synthetic cases pin the AURC / survival-depth / CI math;
real-dataset cases lock the verified resilience numbers and the n=25
PBFT/Snowman statistical tie so a methodology regression cannot pass silently.
"""

import math
import os
import tempfile
import unittest

from output import delay_analysis as da


class TestAurc(unittest.TestCase):
    def test_flat_full_retention_is_one(self):
        curve = {p: 1.0 for p in da.P_DROPS}
        self.assertAlmostEqual(da.aurc(curve), 1.0)

    def test_immediate_collapse(self):
        # fr: 1.0 at p=0, 0 thereafter. Area = 0.05*(1+0)/2 = 0.025; /0.20.
        curve = {0.0: 1.0, 0.05: 0.0, 0.10: 0.0, 0.20: 0.0}
        self.assertAlmostEqual(da.aurc(curve), 0.025 / 0.20)

    def test_uneven_spacing_weights_wide_gap(self):
        # The 0.10->0.20 gap is twice as wide and must count double.
        curve = {0.0: 1.0, 0.05: 0.5, 0.10: 0.5, 0.20: 0.0}
        area = 0.05 * 0.75 + 0.05 * 0.5 + 0.10 * 0.25
        self.assertAlmostEqual(da.aurc(curve), area / 0.20)

    def test_missing_and_nan_points_read_as_zero(self):
        curve = {0.0: 1.0, 0.05: float("nan")}  # 0.10, 0.20 absent
        # Only the 0->0.05 trapezoid with fr(0.05)=0 contributes.
        self.assertAlmostEqual(da.aurc(curve), (0.05 * 0.5) / 0.20)


class TestMeanCI(unittest.TestCase):
    def test_known_mean_and_ci(self):
        # Matches the established analysis.py case: 1,2,3,4.
        m = da.mean_ci([1, 2, 3, 4])
        self.assertEqual(m.n, 4)
        self.assertAlmostEqual(m.mean, 2.5)
        self.assertAlmostEqual(m.ci_half, 3.182 * math.sqrt(5 / 3) / 2, places=4)

    def test_single_value_zero_width(self):
        m = da.mean_ci([7.0])
        self.assertEqual(m.ci_half, 0.0)
        self.assertEqual(m.ci_lo, m.ci_hi)

    def test_nan_dropped(self):
        m = da.mean_ci([2.0, float("nan"), 4.0])
        self.assertEqual(m.n, 2)
        self.assertAlmostEqual(m.mean, 3.0)

    def test_empty_is_nan(self):
        m = da.mean_ci([float("nan")])
        self.assertTrue(math.isnan(m.mean))
        self.assertEqual(m.n, 0)


class TestSurvivalDepth(unittest.TestCase):
    def test_deepest_positive_level(self):
        fr = {
            ("pbft", 10, 0.0): da.MeanCI(1.0, 0, 1.0, 1.0, 20),
            ("pbft", 10, 0.05): da.MeanCI(0.2, 0, 0.2, 0.2, 20),
            ("pbft", 10, 0.10): da.MeanCI(0.1, 0, 0.1, 0.1, 20),
            ("pbft", 10, 0.20): da.MeanCI(0.05, 0, 0.05, 0.05, 20),
        }
        self.assertEqual(da.survival_depth(fr, "pbft", 10), 0.20)

    def test_dies_before_deepest(self):
        fr = {
            ("snowman", 10, 0.0): da.MeanCI(1.0, 0, 1.0, 1.0, 20),
            ("snowman", 10, 0.05): da.MeanCI(0.2, 0, 0.2, 0.2, 20),
            ("snowman", 10, 0.10): da.MeanCI(0.0, 0, 0.0, 0.0, 20),
            ("snowman", 10, 0.20): da.MeanCI(0.0, 0, 0.0, 0.0, 20),
        }
        self.assertEqual(da.survival_depth(fr, "snowman", 10), 0.05)


class TestRealDataset(unittest.TestCase):
    """Lock the verified ranking against the committed heavy/moderate CSVs."""

    def setUp(self):
        if not (os.path.exists(da.HEAVY_CSV) and os.path.exists(da.MODERATE_CSV)):
            self.skipTest("delay CSVs not present")
        self.heavy = da.load_rows(da.HEAVY_CSV)
        self.moderate = da.load_rows(da.MODERATE_CSV)

    def _by_proto(self, n):
        return {r.protocol: r for r in
                da.ranking_for_n(self.heavy, self.moderate, n)}

    def test_n10_strict_order_pbft_snowman_casper(self):
        rows = da.ranking_for_n(self.heavy, self.moderate, 10)
        self.assertEqual([r.protocol for r in rows],
                         ["pbft", "snowman", "casper-ffg"])
        self.assertEqual([r.rank for r in rows], [1, 2, 3])
        self.assertFalse(any(r.tie for r in rows))

    def test_n10_aurc_values(self):
        by = self._by_proto(10)
        self.assertAlmostEqual(by["pbft"].aurc, 0.253, places=2)
        self.assertAlmostEqual(by["snowman"].aurc, 0.174, places=2)
        self.assertAlmostEqual(by["casper-ffg"].aurc, 0.149, places=2)

    def test_n25_top_two_are_a_tie(self):
        rows = da.ranking_for_n(self.heavy, self.moderate, 25)
        by = {r.protocol: r for r in rows}
        # Snowman edges PBFT on AURC but their CIs overlap -> shared rank 1.
        self.assertEqual(by["pbft"].rank, 1)
        self.assertEqual(by["snowman"].rank, 1)
        self.assertTrue(by["pbft"].tie)
        self.assertTrue(by["snowman"].tie)
        self.assertEqual(by["casper-ffg"].rank, 3)

    def test_n25_aurc_values_and_seedcount(self):
        by = self._by_proto(25)
        self.assertAlmostEqual(by["snowman"].aurc, 0.369, places=2)
        self.assertAlmostEqual(by["pbft"].aurc, 0.351, places=2)
        self.assertAlmostEqual(by["casper-ffg"].aurc, 0.140, places=2)
        self.assertEqual(by["snowman"].n_seeds, 8)  # the cost-wall cell

    def test_survival_depth_pbft_deepest(self):
        # PBFT alone still finalizes at the harshest loss level (both n).
        self.assertEqual(self._by_proto(10)["pbft"].survival_depth_p, 0.20)
        self.assertEqual(self._by_proto(25)["pbft"].survival_depth_p, 0.20)
        # Snowman dies one step earlier at n=10 than at n=25.
        self.assertEqual(self._by_proto(10)["snowman"].survival_depth_p, 0.05)
        self.assertEqual(self._by_proto(25)["snowman"].survival_depth_p, 0.10)

    def test_ranking_csv_is_byte_stable(self):
        with tempfile.TemporaryDirectory() as d:
            p1 = os.path.join(d, "a.csv")
            p2 = os.path.join(d, "b.csv")
            da.write_ranking_csv(p1, da.HEAVY_CSV, da.MODERATE_CSV)
            da.write_ranking_csv(p2, da.HEAVY_CSV, da.MODERATE_CSV)
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                self.assertEqual(f1.read(), f2.read())


if __name__ == "__main__":
    unittest.main()
