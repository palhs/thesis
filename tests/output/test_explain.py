"""Smoke + regression tests for the explanatory view (src/output/explain.py).

Mirrors the project convention that the *data* layer is tested while the
matplotlib *render* layer is not. These lock in the numbers each chart reads
from the frozen CSVs — in particular the goodput_spread fix (a true 20-sample
distribution at one n, not 80-120 pooled points) so the pooling/double-count
defect cannot silently return.
"""

import unittest

from output import explain


class TestLoadAgg(unittest.TestCase):
    def setUp(self):
        self.agg = explain.load_agg()

    def test_dedup_one_row_per_protocol_n(self):
        # casper n=4 appears twice in the CSV (uniform + nonuniform); load_agg
        # must collapse to a single (protocol, n) record.
        keys = list(self.agg.keys())
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn(("casper-ffg", 4), self.agg)

    def test_cost_bar_values_at_fixed_n(self):
        # The cost_per_commit_bar headline numbers.
        col = "total_msgs_per_acu_mean"
        self.assertAlmostEqual(self.agg[("pbft", 16)][col], 31.875, places=3)
        self.assertAlmostEqual(self.agg[("casper-ffg", 16)][col], 19.101562, places=3)
        self.assertAlmostEqual(self.agg[("snowman", 16)][col], 450.9375, places=3)

    def test_snowman_has_no_n4(self):
        self.assertNotIn(("snowman", 4), self.agg)


class TestLoadTrials(unittest.TestCase):
    def setUp(self):
        self.trials = explain.load_trials()

    def test_exactly_twenty_samples_per_protocol(self):
        # The goodput_spread fix: one n => a true 20-seed box, never the
        # 80-120 pooled-across-n inflation that double-counted casper n=4.
        for proto in explain.PROTO_ORDER:
            self.assertEqual(len(self.trials[proto]), 20, proto)

    def test_pbft_equals_snowman_sample_for_sample(self):
        # goodput is a per-seed workload draw independent of protocol, so at a
        # fixed n the two per-block protocols must match exactly.
        self.assertEqual(self.trials["pbft"], self.trials["snowman"])

    def test_means_match_aggregate(self):
        agg = explain.load_agg()
        for proto in explain.PROTO_ORDER:
            mean = sum(self.trials[proto]) / len(self.trials[proto])
            self.assertAlmostEqual(
                mean, agg[(proto, explain.FIXED_N)]["goodput_mean"], places=3)


class TestTheoryLine(unittest.TestCase):
    def test_pbft_and_casper_slopes(self):
        self.assertEqual(explain._theory_line("pbft", 16), 32)
        self.assertAlmostEqual(explain._theory_line("casper-ffg", 16), 19.2)

    def test_snowman_k_rescaling(self):
        # K = min(20, n-1): tracks n-1 below n=21, saturates at 20 above.
        self.assertEqual(explain._theory_line("snowman", 16), 2 * 15 * 15.0)
        self.assertEqual(explain._theory_line("snowman", 25), 2 * 20 * 15.0)

    def test_theory_within_seven_percent_of_measured(self):
        agg = explain.load_agg()
        col = "total_msgs_per_acu_mean"
        for proto in explain.PROTO_ORDER:
            for n in explain.NS:
                if (proto, n) not in agg:
                    continue
                measured = agg[(proto, n)][col]
                theory = explain._theory_line(proto, n)
                rel = abs(measured - theory) / theory
                self.assertLess(rel, 0.075, f"{proto} n={n}: {rel:.3f}")


if __name__ == "__main__":
    unittest.main()
