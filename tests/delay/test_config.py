"""Unit tests for the T46 delay-experiment configuration.

Asserts the locked Week-9 methodology invariants are pinned in code:
the two T46 timelines and their distributions, E[delay] = 0.3 s, the FFG
slot rescaling (slot >= 4 * E[delay]), n in {10, 25}, the 20-seed set,
and the buffer/window calibration sizing.
"""
from __future__ import annotations

import unittest

from network import DelayDist

from delay import config as cfg


class TestTimelines(unittest.TestCase):
    def test_exactly_two_timelines(self):
        # T46 covers EXACTLY delay-uniform + delay-exponential; T47 owns
        # heavy-tail / loss / partial-sync-gst.
        self.assertEqual(len(cfg.TIMELINES), 2)
        self.assertEqual({t.name for t in cfg.TIMELINES},
                         {"delay-uniform", "delay-exponential"})

    def test_uniform_distribution_params(self):
        tl = next(t for t in cfg.TIMELINES if t.name == "delay-uniform")
        self.assertIsInstance(tl.delay, DelayDist)
        self.assertEqual(tl.delay.kind, "uniform")
        # uniform[0.1, 0.5] s = uniform[100, 500] ms, mean 300 ms.
        self.assertEqual(tl.delay.params["low"], 0.1)
        self.assertEqual(tl.delay.params["high"], 0.5)
        self.assertAlmostEqual(
            (tl.delay.params["low"] + tl.delay.params["high"]) / 2, 0.3)

    def test_exponential_distribution_params(self):
        tl = next(t for t in cfg.TIMELINES if t.name == "delay-exponential")
        self.assertEqual(tl.delay.kind, "exponential")
        self.assertEqual(tl.delay.params["mean"], 0.3)

    def test_both_timelines_have_e_delay_300ms(self):
        for tl in cfg.TIMELINES:
            self.assertAlmostEqual(tl.e_delay_s, 0.3, msg=tl.name)

    def test_single_phase_timeline(self):
        for tl in cfg.TIMELINES:
            phases = tl.phases()
            self.assertEqual(len(phases), 1, msg=tl.name)
            self.assertEqual(phases[0].t_start, 0.0)


class TestFFGCoherence(unittest.TestCase):
    def test_ffg_slot_satisfies_coherence_rule(self):
        # experiment-matrix §5: slot_duration >= 4 * E[delay].
        for tl in cfg.TIMELINES:
            self.assertGreaterEqual(
                tl.ffg_slot_duration_s, 4 * tl.e_delay_s, msg=tl.name)

    def test_ffg_slot_is_1200ms(self):
        for tl in cfg.TIMELINES:
            self.assertEqual(tl.ffg_slot_duration_s, 1.2, msg=tl.name)


class TestAxes(unittest.TestCase):
    def test_n_values_amendment(self):
        # Locked Week-9 amendment to experiment-matrix §3: n in {10, 25}.
        self.assertEqual(cfg.N_VALUES, (10, 25))

    def test_twenty_seeds(self):
        self.assertEqual(cfg.SEEDS, tuple(range(20)))


class TestCalibration(unittest.TestCase):
    def test_t_max_is_window_plus_buffer(self):
        self.assertAlmostEqual(cfg.T_MAX, cfg.WINDOW_S + cfg.BUFFER_S)

    def test_window_larger_than_buffer(self):
        # The measurement window must dominate the settling buffer.
        self.assertGreater(cfg.WINDOW_S, cfg.BUFFER_S)

    def test_buffer_covers_slowest_one_round(self):
        # Buffer >= one full protocol round so an instance started just
        # before W still finalizes inside the run horizon.
        self.assertGreaterEqual(cfg.BUFFER_S, max(cfg.ONE_ROUND_S.values()))

    def test_one_round_table_covers_all_protocols(self):
        self.assertEqual(set(cfg.ONE_ROUND_S),
                         {"pbft", "casper-ffg", "snowman"})


if __name__ == "__main__":
    unittest.main()
