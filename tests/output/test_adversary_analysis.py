"""Unit + regression tests for src/output/adversary_analysis.py (T54).

Data layer only (render layer in adversary_degradation_plots.py is not tested,
per project convention). Synthetic cases pin the loader/reducer math; the
f_max/real-dataset cases land in a later task.
"""
import math, os, tempfile, csv, unittest
from output import adversary_analysis as aa


def _write(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


class TestLoader(unittest.TestCase):
    def test_family_tagging_and_by_name(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "offline_validators.csv"),
                   ["protocol", "n", "seed", "byzantine_fraction", "success_rate"],
                   [{"protocol": "pbft", "n": 10, "seed": 0,
                     "byzantine_fraction": 0.0, "success_rate": 1.0}])
            rows = aa.load_adversary_rows(d)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["family"], "offline")


class TestLiveness(unittest.TestCase):
    def test_rate_and_wilson(self):
        rows = [{"family": "equivocate", "protocol": "casper-ffg", "n": 10,
                 "seed": s, "byzantine_fraction": 0.20,
                 "success_rate": (1.0 if s < 15 else 0.0)} for s in range(20)]
        cells = aa.liveness_rate(rows, "equivocate", "casper-ffg", 10)
        self.assertAlmostEqual(cells[0.20].mean, 0.75)
        self.assertEqual(cells[0.20].k, 15)
        self.assertEqual(cells[0.20].n_seeds, 20)


class TestSafetyReducers(unittest.TestCase):
    def _equiv(self, proto, n, phi, **extra):
        base = {"family": "equivocate", "protocol": proto, "n": n, "seed": 0,
                "byzantine_fraction": phi, "run_horizon_s": 230.0,
                "view_change_count": 0, "safety_violation": 0,
                "conflicting_instances": 0, "max_slashable_stake_fraction": 0.0,
                "K": 9, "alpha_p": 5, "alpha_c": 8, "beta": 15}
        base.update(extra); return base

    def test_pbft_view_change_rate(self):
        rows = [self._equiv("pbft", 10, 0.20, view_change_count=10)]
        r = aa.pbft_view_change_rate(rows, 10)
        self.assertAlmostEqual(r[0.20].mean, 10 / 230.0)

    def test_ffg_slashable(self):
        rows = [self._equiv("casper-ffg", 10, 0.40, max_slashable_stake_fraction=0.40)]
        r = aa.ffg_slashable(rows, 10)
        self.assertAlmostEqual(r[0.40].mean, 0.40)

    def test_snowman_epsilon_witness_zero_empirical(self):
        rows = [self._equiv("snowman", 10, phi, K=9, alpha_c=8, beta=15)
                for phi in (0.0, 0.10, 0.20, 0.33) for _ in range(20)]
        w = aa.snowman_epsilon_witness(rows, 10)
        self.assertEqual(w.empirical_rate, 0.0)
        self.assertAlmostEqual(w.analytical_bound, (1 - 8/9) ** 15)
        self.assertGreater(w.empirical_wilson_hi, 0.0)

    def test_nwt_is_deferred(self):
        self.assertEqual(aa.nwt_invariant()["status"], "deferred")


class TestMagnitudeReducers(unittest.TestCase):
    """The §4.4 figure-overlay reducers added for the T62 figure pass."""

    def _delay(self, proto, n, phi, m, ratio):
        return {"family": "delay", "protocol": proto, "n": n, "seed": 0,
                "byzantine_fraction": phi, "delay_mult": m,
                "finality_delay_ratio": ratio}

    def test_delay_finality_ratio_worst_over_magnitude(self):
        # at phi=0.20: m=2 cell mean = 15, m=10 cell mean = 60 -> keep the worst
        # (max over magnitude), NOT the pooled mean of 30.
        rows = [self._delay("snowman", 10, 0.20, 2.0, 10.0),
                self._delay("snowman", 10, 0.20, 2.0, 20.0),
                self._delay("snowman", 10, 0.20, 10.0, 60.0),
                self._delay("snowman", 10, 0.10, 10.0, 1.0)]
        curve = aa.delay_finality_ratio_by_phi(rows, "snowman", 10)
        self.assertAlmostEqual(curve[0.20], 60.0)
        self.assertAlmostEqual(curve[0.10], 1.0)

    def test_delay_finality_ratio_nan_skip(self):
        # a failed run carries NaN finality_delay_ratio (a liveness loss, not a
        # blow-up); it must be dropped, not pooled into a NaN cell.
        rows = [self._delay("casper-ffg", 10, 0.20, 10.0, float("nan")),
                self._delay("casper-ffg", 10, 0.20, 10.0, 1.0)]
        curve = aa.delay_finality_ratio_by_phi(rows, "casper-ffg", 10)
        self.assertAlmostEqual(curve[0.20], 1.0)

    def test_pbft_view_change_count(self):
        rows = [{"family": "equivocate", "protocol": "pbft", "n": 25, "seed": 0,
                 "byzantine_fraction": 0.33, "view_change_count": 25}]
        self.assertAlmostEqual(aa.pbft_view_change_count(rows, 25)[0.33].mean, 25.0)

    def test_pbft_conflicting_instances(self):
        rows = [{"family": "equivocate", "protocol": "pbft", "n": 10, "seed": 0,
                 "byzantine_fraction": 0.40, "conflicting_instances": 229}]
        self.assertAlmostEqual(
            aa.pbft_conflicting_instances(rows, 10)[0.40].mean, 229.0)

    def test_offline_throughput_ratio_nan_skip(self):
        rows = [{"family": "offline", "protocol": "snowman", "n": 25, "seed": 0,
                 "byzantine_fraction": 0.20, "throughput_ratio": 0.004},
                {"family": "offline", "protocol": "snowman", "n": 25, "seed": 1,
                 "byzantine_fraction": 0.20, "throughput_ratio": float("nan")}]
        self.assertAlmostEqual(
            aa.offline_throughput_ratio(rows, "snowman", 25)[0.20].mean, 0.004)


class TestBracket(unittest.TestCase):
    def test_holds_then_breaks(self):
        holds = {0.0: True, 0.10: True, 0.20: True, 0.33: True, 0.40: False, 0.50: False}
        hold, brk = aa.bracket(holds.keys(), lambda p: holds[p])
        self.assertEqual(hold, 0.33)
        self.assertEqual(brk, 0.40)

    def test_right_censored_never_breaks(self):
        holds = {0.0: True, 0.10: True, 0.20: True, 0.33: True}
        hold, brk = aa.bracket(holds.keys(), lambda p: holds[p])
        self.assertEqual(hold, 0.33)
        self.assertIsNone(brk)

    def test_left_censored_breaks_immediately(self):
        holds = {0.0: True, 0.10: False}
        hold, brk = aa.bracket(holds.keys(), lambda p: holds[p])
        self.assertEqual(hold, 0.0)
        self.assertEqual(brk, 0.10)


class TestRealDataset(unittest.TestCase):
    """Lock verified brackets/witness against the committed equivocate CSV."""
    def setUp(self):
        self.rows = aa.load_adversary_rows()
        if not any(r["family"] == "equivocate" for r in self.rows):
            self.skipTest("adversary CSVs not present")

    def test_pbft_safety_bracket_is_033_to_040(self):
        fm = aa.f_max_for(self.rows, "safety", "pbft", 10)
        self.assertEqual(fm.f_max_hold, 0.33)
        self.assertEqual(fm.f_max_break, 0.40)
        self.assertFalse(math.isnan(fm.f_max_count))
        self.assertTrue(math.isnan(fm.f_max_stake))

    def test_ffg_slashable_crosses_third_at_040(self):
        fm = aa.f_max_for(self.rows, "safety", "casper-ffg", 10)
        self.assertEqual(fm.f_max_hold, 0.33)
        self.assertEqual(fm.f_max_break, 0.40)
        self.assertTrue(math.isnan(fm.f_max_count))
        self.assertFalse(math.isnan(fm.f_max_stake))

    def test_snowman_safety_right_censored(self):
        fm = aa.f_max_for(self.rows, "safety", "snowman", 10)
        self.assertEqual(fm.f_max_hold, 0.33)
        self.assertIsNone(fm.f_max_break)

    def test_pbft_safety_broken_flag_above_third(self):
        rate = aa.safety_violation_rate(self.rows, "pbft", 10)
        self.assertEqual(rate[0.33].mean, 0.0)
        self.assertEqual(rate[0.40].mean, 1.0)

    def test_snowman_epsilon_witness_real(self):
        w = aa.snowman_epsilon_witness(self.rows, 10)
        self.assertEqual(w.empirical_rate, 0.0)
        self.assertAlmostEqual(w.analytical_bound, (1 - 8/9) ** 15)

    def test_equivocate_pbft_liveness_row_flags_safety_broken(self):
        fm = aa.f_max_for(self.rows, "liveness", "pbft", 10)
        self.assertEqual(fm.f_max_hold, 0.0)
        self.assertEqual(fm.f_max_break, 0.10)
        self.assertTrue(fm.safety_broken)   # live-but-forked above 1/3

    def test_delay_pbft_liveness_not_safety_broken(self):
        # delay family: PBFT does not fork; liveness holds throughout.
        from output import adversary_analysis as _aa
        fm = _aa._liveness_fmax(self.rows, "delay", "pbft", 10)
        self.assertFalse(fm.safety_broken)

    def test_ranking_csv_is_byte_stable(self):
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = os.path.join(d, "a.csv"), os.path.join(d, "b.csv")
            aa.write_ranking_csv(p1)
            aa.write_ranking_csv(p2)
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                self.assertEqual(f1.read(), f2.read())


if __name__ == "__main__":
    unittest.main()
