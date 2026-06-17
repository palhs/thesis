"""Unit tests for src/output/analysis.py (T43/T44 aggregation math).

The statistics that feed the Chapter-4 plots and the aggregated CSV must be
correct, so the mean / sample-std / standard-error / 95%-CI computation is
checked against hand-worked values, and the grouping rules (per run_id, the
Casper FFG n=4 variant handling) are pinned.
"""

import math
import os
import unittest

from output import analysis


def _row(protocol, run_id, n, seed, **metrics):
    base = {"protocol": protocol, "run_id": run_id, "n": str(n), "seed": str(seed)}
    for m in analysis.METRICS:
        base[m] = ""
    base.update({k: str(v) for k, v in metrics.items()})
    return base


class TestTCritical(unittest.TestCase):
    def test_df19_is_2093(self):
        self.assertAlmostEqual(analysis.t_critical_975(19), 2.093, places=3)

    def test_small_df(self):
        self.assertAlmostEqual(analysis.t_critical_975(1), 12.706, places=3)

    def test_large_df_falls_back_to_normal(self):
        self.assertAlmostEqual(analysis.t_critical_975(500), 1.960, places=3)

    def test_nonpositive_df_is_nan(self):
        self.assertTrue(math.isnan(analysis.t_critical_975(0)))


class TestAggregate(unittest.TestCase):
    def test_known_mean_std_ci(self):
        # tps over 4 seeds: 1,2,3,4 -> mean 2.5, sample std sqrt(5/3)=1.29099,
        # sem = std/2 = 0.645497, t_{.975,df=3}=3.182 -> ci_half=2.05397.
        rows = [_row("pbft", "pbft-n7", 7, s, tps=v)
                for s, v in enumerate([1, 2, 3, 4])]
        aggs = {a.metric: a for a in analysis.aggregate(rows, metrics=("tps",))}
        a = aggs["tps"]
        self.assertEqual(a.n_runs, 4)
        self.assertAlmostEqual(a.mean, 2.5)
        self.assertAlmostEqual(a.std, math.sqrt(5 / 3), places=6)
        self.assertAlmostEqual(a.sem, math.sqrt(5 / 3) / 2, places=6)
        self.assertAlmostEqual(a.ci_half, 3.182 * math.sqrt(5 / 3) / 2, places=4)
        self.assertAlmostEqual(a.ci_lo, a.mean - a.ci_half, places=6)
        self.assertAlmostEqual(a.ci_hi, a.mean + a.ci_half, places=6)

    def test_zero_variance_gives_zero_width_ci(self):
        # The baseline reality: deterministic metrics carry zero CI width.
        rows = [_row("pbft", "pbft-n7", 7, s, commit_latency_ms=1000.0)
                for s in range(20)]
        a = {x.metric: x for x in
             analysis.aggregate(rows, metrics=("commit_latency_ms",))}["commit_latency_ms"]
        self.assertEqual(a.std, 0.0)
        self.assertEqual(a.ci_half, 0.0)
        self.assertEqual(a.cv, 0.0)
        self.assertEqual(a.ci_lo, a.ci_hi)

    def test_nan_cells_dropped_from_sample(self):
        # Snowman parameter columns are NaN for non-snowman rows; an empty
        # metric cell must not poison the mean.
        rows = [_row("pbft", "pbft-n7", 7, s, tps=v)
                for s, v in enumerate([2, 4])]
        rows.append(_row("pbft", "pbft-n7", 7, 99))  # tps cell left ""
        a = {x.metric: x for x in
             analysis.aggregate(rows, metrics=("tps",))}["tps"]
        self.assertEqual(a.n_runs, 2)
        self.assertAlmostEqual(a.mean, 3.0)

    def test_groups_are_per_run_id(self):
        rows = ([_row("casper-ffg", "casper-ffg-n4-uniform", 4, s, tps=1.0)
                 for s in range(3)]
                + [_row("casper-ffg", "casper-ffg-n4-nonuniform", 4, s, tps=9.0)
                   for s in range(3)])
        aggs = analysis.aggregate(rows, metrics=("tps",))
        self.assertEqual(len(aggs), 2)  # not pooled into one n=4 cell
        means = sorted(a.mean for a in aggs)
        self.assertEqual(means, [1.0, 9.0])


class TestByMetric(unittest.TestCase):
    def test_drops_casper_nonuniform_from_curve(self):
        rows = ([_row("casper-ffg", "casper-ffg-n4-uniform", 4, s, tps=1.0)
                 for s in range(2)]
                + [_row("casper-ffg", "casper-ffg-n4-nonuniform", 4, s, tps=9.0)
                   for s in range(2)])
        idx = analysis.by_metric(analysis.aggregate(rows, metrics=("tps",)))
        pts = idx["tps"]["casper-ffg"]
        self.assertEqual(len(pts), 1)
        self.assertAlmostEqual(pts[0].mean, 1.0)

    def test_curve_sorted_by_n(self):
        rows = []
        for n in (25, 4, 10):
            rows += [_row("pbft", f"pbft-n{n}", n, s, tps=float(n))
                     for s in range(2)]
        idx = analysis.by_metric(analysis.aggregate(rows, metrics=("tps",)))
        self.assertEqual([a.n for a in idx["tps"]["pbft"]], [4, 10, 25])


class TestRealDataset(unittest.TestCase):
    """Smoke check against the committed baseline CSV when present."""

    def setUp(self):
        self.path = "results/baseline/baseline.csv"
        if not os.path.exists(self.path):
            self.skipTest("baseline.csv not present")

    def test_loads_and_aggregates(self):
        aggs = analysis.aggregate(analysis.load_rows(self.path))
        self.assertTrue(aggs)
        # Every aggregate is internally consistent.
        for a in aggs:
            self.assertGreaterEqual(a.n_runs, 1)
            self.assertLessEqual(a.ci_lo, a.ci_hi)


if __name__ == "__main__":
    unittest.main()
