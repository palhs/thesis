"""Family C config: axes, static-baseline timeline, cadence refs (T51)."""
from __future__ import annotations

import math
import unittest

from adversary import config as cfg


class TestAxes(unittest.TestCase):
    def test_n_values(self):
        self.assertEqual(cfg.N_VALUES, (10, 25))

    def test_f_values_include_zero_control(self):
        self.assertEqual(cfg.F_VALUES, (0.0, 0.10, 0.20, 0.30))

    def test_m_values(self):
        self.assertEqual(cfg.M_VALUES, (2.0, 5.0, 10.0))

    def test_seeds(self):
        self.assertEqual(cfg.SEEDS, tuple(range(20)))


class TestStaticBaseline(unittest.TestCase):
    def test_single_phase_constant_10ms(self):
        phases = cfg.STATIC_BASELINE.phases()
        self.assertEqual(len(phases), 1)
        ph = phases[0]
        self.assertEqual(ph.t_start, 0.0)
        self.assertTrue(math.isinf(ph.t_end))
        self.assertEqual(ph.delay.kind, "constant")
        self.assertAlmostEqual(ph.delay.params["delay"], 0.01)
        self.assertEqual(ph.p_drop, 0.0)


class TestCadenceRefs(unittest.TestCase):
    def test_refs_per_protocol(self):
        self.assertAlmostEqual(cfg.REF_S["pbft"], 1.0)
        self.assertAlmostEqual(cfg.REF_S["snowman"], 1.0)
        self.assertAlmostEqual(cfg.REF_S["casper-ffg"], 0.1)

    def test_ffg_slot_satisfies_coherence(self):
        # static-baseline E[delay] = 10 ms; slot >= 4·E[delay] = 40 ms.
        self.assertGreaterEqual(cfg.FFG_SLOT_DURATION_S, 4 * 0.01)


class TestCalibration(unittest.TestCase):
    def test_horizon_is_window_plus_buffer(self):
        self.assertAlmostEqual(cfg.T_MAX, cfg.WINDOW_S + cfg.BUFFER_S)

    def test_one_round_keys(self):
        self.assertEqual(set(cfg.ONE_ROUND_S),
                         {"pbft", "casper-ffg", "snowman"})


if __name__ == "__main__":
    unittest.main()
