"""Unit tests for the T47 finalization-rate post-grid pass.

`_finalization_rates` is the headline degradation metric: a loss cell's
in-window finalizations as a fraction of its loss-free control (the
`delay-heavy-tail`, p_drop=0, run at the same protocol/n/seed). Tested on
synthetic rows so the join + ratio + clamp logic is verified without any
protocol run.
"""
from __future__ import annotations

import math
import unittest

from delay.heavy import _finalization_rates, CONTROL_TIMELINE


def _row(protocol, n, seed, phase_id, finalized):
    return {"protocol": protocol, "n": n, "seed": seed,
            "network_phase_id": phase_id, "finalized_instances": finalized,
            "finalization_rate": float("nan")}


class TestFinalizationRates(unittest.TestCase):
    def test_control_row_is_unity(self):
        rows = [_row("pbft", 10, 0, CONTROL_TIMELINE, 1180)]
        _finalization_rates(rows)
        self.assertEqual(rows[0]["finalization_rate"], 1.0)

    def test_loss_row_is_ratio_to_control(self):
        rows = [
            _row("pbft", 10, 0, CONTROL_TIMELINE, 1000),
            _row("pbft", 10, 0, "delay-heavy-tail-loss-p20", 600),
        ]
        _finalization_rates(rows)
        loss = rows[1]
        self.assertAlmostEqual(loss["finalization_rate"], 0.6)

    def test_ratio_clamped_to_one(self):
        # A loss run that (by sampling noise) finalized more than its control
        # is clamped to 1.0 — a degradation metric never exceeds 1.
        rows = [
            _row("snowman", 25, 3, CONTROL_TIMELINE, 50),
            _row("snowman", 25, 3, "delay-heavy-tail-loss-p05", 53),
        ]
        _finalization_rates(rows)
        self.assertEqual(rows[1]["finalization_rate"], 1.0)

    def test_control_finalized_zero_is_nan(self):
        # If the control finalized nothing, the ratio is undefined.
        rows = [
            _row("snowman", 25, 7, CONTROL_TIMELINE, 0),
            _row("snowman", 25, 7, "delay-heavy-tail-loss-p20", 0),
        ]
        _finalization_rates(rows)
        self.assertTrue(math.isnan(rows[1]["finalization_rate"]))

    def test_missing_control_sibling_is_nan(self):
        # A p_drop-only subset (no matching control row) leaves loss rows NaN
        # rather than inventing a denominator.
        rows = [_row("pbft", 10, 0, "delay-heavy-tail-loss-p10", 800)]
        _finalization_rates(rows)
        self.assertTrue(math.isnan(rows[0]["finalization_rate"]))

    def test_join_keys_on_protocol_n_seed(self):
        # Control of one (protocol, n, seed) must not leak into another's
        # loss row.
        rows = [
            _row("pbft", 10, 0, CONTROL_TIMELINE, 1000),
            _row("pbft", 10, 1, CONTROL_TIMELINE, 500),
            _row("pbft", 10, 0, "delay-heavy-tail-loss-p20", 250),
            _row("pbft", 10, 1, "delay-heavy-tail-loss-p20", 250),
        ]
        _finalization_rates(rows)
        # seed 0: 250/1000 = 0.25 ; seed 1: 250/500 = 0.5.
        self.assertAlmostEqual(rows[2]["finalization_rate"], 0.25)
        self.assertAlmostEqual(rows[3]["finalization_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
