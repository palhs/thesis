"""Unit tests for the T47 heavy-delay + packet-loss configuration.

Pins the locked methodology: the heavy-tail (Pareto) distribution with
E[delay] = 3 s, the four heavy timelines (one loss-free control + three
packet-loss levels 5–20 %), the 12 s FFG slot (slot >= 4*E[delay]), the
Option-B capped measurement window, and the calibrated PBFT view-change
timeout that distinguishes the heavy sweep from the frozen T46 one.
"""
from __future__ import annotations

import random
import unittest

from network import DelayDist

from delay import config as cfg
from delay import heavy
from delay.runners import T46


class TestHeavyTailDistribution(unittest.TestCase):
    def test_e_delay_is_3s(self):
        # scale * shape/(shape-1) = 1.0 * 1.5/0.5 = 3.0 s.
        self.assertAlmostEqual(heavy.HEAVY_E_DELAY_S, 3.0)

    def test_pareto_params(self):
        self.assertEqual(heavy.HEAVY_DELAY_SCALE_S, 1.0)
        self.assertEqual(heavy.HEAVY_DELAY_SHAPE, 1.5)

    def test_delay_is_heavy_tail_kind(self):
        d = heavy._heavy_delay()
        self.assertIsInstance(d, DelayDist)
        self.assertEqual(d.kind, "heavy_tail")
        self.assertEqual(d.params["scale"], 1.0)
        self.assertEqual(d.params["shape"], 1.5)

    def test_samples_land_in_1_to_5s_band_with_tail(self):
        # paretovariate(shape) >= 1, so min sample >= scale = 1.0 s; the bulk
        # sits in 1-5 s and the mean is ~3 s with a long right tail.
        rng = random.Random(12345)
        d = heavy._heavy_delay()
        samples = [d.sample(rng) for _ in range(20000)]
        self.assertGreaterEqual(min(samples), 1.0)          # min = scale
        self.assertAlmostEqual(sum(samples) / len(samples), 3.0, delta=0.4)
        in_band = sum(1 for s in samples if 1.0 <= s <= 5.0)
        self.assertGreater(in_band / len(samples), 0.6)     # mass in 1-5 s


class TestHeavyTimelines(unittest.TestCase):
    def test_four_timelines(self):
        self.assertEqual(len(heavy.HEAVY_TIMELINES), 4)

    def test_names_and_p_drop_levels(self):
        by_name = {t.name: t for t in heavy.HEAVY_TIMELINES}
        self.assertEqual(by_name["delay-heavy-tail"].p_drop, 0.0)
        self.assertEqual(by_name["delay-heavy-tail-loss-p05"].p_drop, 0.05)
        self.assertEqual(by_name["delay-heavy-tail-loss-p10"].p_drop, 0.10)
        self.assertEqual(by_name["delay-heavy-tail-loss-p20"].p_drop, 0.20)

    def test_control_timeline_first(self):
        # The p_drop=0 control is the finalization_rate denominator; it must
        # be the canonical control name.
        self.assertEqual(heavy.HEAVY_TIMELINES[0].name, heavy.CONTROL_TIMELINE)
        self.assertEqual(heavy.CONTROL_TIMELINE, "delay-heavy-tail")
        self.assertEqual(heavy.HEAVY_TIMELINES[0].p_drop, 0.0)

    def test_p_drop_levels_are_5_to_20_percent(self):
        self.assertEqual(heavy.P_DROP_LEVELS, (0.05, 0.10, 0.20))

    def test_all_share_one_heavy_tail_distribution(self):
        for tl in heavy.HEAVY_TIMELINES:
            self.assertEqual(tl.delay.kind, "heavy_tail")
            self.assertAlmostEqual(tl.e_delay_s, 3.0, msg=tl.name)

    def test_single_phase_carries_p_drop(self):
        for tl in heavy.HEAVY_TIMELINES:
            phases = tl.phases()
            self.assertEqual(len(phases), 1, msg=tl.name)
            self.assertEqual(phases[0].t_start, 0.0)
            self.assertEqual(phases[0].p_drop, tl.p_drop, msg=tl.name)


class TestHeavyFFGCoherence(unittest.TestCase):
    def test_ffg_slot_satisfies_coherence_rule(self):
        # experiment-matrix-runs §2: slot_duration = 12 s for the heavy-tail
        # regime (slot >= 4 * E[delay] = 12 s).
        self.assertEqual(heavy.HEAVY_FFG_SLOT_DURATION_S, 12.0)
        for tl in heavy.HEAVY_TIMELINES:
            self.assertGreaterEqual(tl.ffg_slot_duration_s,
                                    4 * tl.e_delay_s, msg=tl.name)


class TestHeavyCalibration(unittest.TestCase):
    def test_t_max_is_window_plus_buffer(self):
        self.assertAlmostEqual(heavy.HEAVY_T_MAX,
                               heavy.HEAVY_WINDOW_S + heavy.HEAVY_BUFFER_S)

    def test_window_capped_option_b(self):
        # Option B (human 2026-06-12): W is capped tractably, NOT grown to
        # hold the T46 <5% clip guard.
        self.assertLessEqual(heavy.HEAVY_WINDOW_S, 1500.0)

    def test_window_dominates_buffer(self):
        self.assertGreater(heavy.HEAVY_WINDOW_S, heavy.HEAVY_BUFFER_S)

    def test_buffer_covers_slowest_one_round(self):
        self.assertGreaterEqual(heavy.HEAVY_BUFFER_S,
                                max(heavy.HEAVY_ONE_ROUND_S.values()))

    def test_one_round_covers_all_protocols(self):
        self.assertEqual(set(heavy.HEAVY_ONE_ROUND_S),
                         {"pbft", "casper-ffg", "snowman"})

    def test_heavy_calib_wires_the_constants(self):
        self.assertEqual(heavy.HEAVY_CALIB.t_max, heavy.HEAVY_T_MAX)
        self.assertEqual(heavy.HEAVY_CALIB.window_s, heavy.HEAVY_WINDOW_S)
        self.assertEqual(heavy.HEAVY_CALIB.pbft_vc_delay,
                         heavy.HEAVY_PBFT_VC_DELAY_S)

    def test_view_change_enabled_unlike_t46(self):
        # T46 suppresses view-change (vc_delay 10000 s); T47 calibrates it
        # low enough that PBFT recovers under loss.
        self.assertLess(heavy.HEAVY_CALIB.pbft_vc_delay, T46.pbft_vc_delay)


class TestSeedPolicy(unittest.TestCase):
    _FULL = tuple(range(20))

    def test_snowman_n25_capped_at_8_seeds(self):
        self.assertEqual(heavy._seeds_for("snowman", 25, self._FULL),
                         tuple(range(8)))

    def test_other_classes_keep_full_seeds(self):
        self.assertEqual(heavy._seeds_for("snowman", 10, self._FULL),
                         self._FULL)
        self.assertEqual(heavy._seeds_for("pbft", 25, self._FULL), self._FULL)
        self.assertEqual(heavy._seeds_for("casper-ffg", 25, self._FULL),
                         self._FULL)

    def test_smoke_subset_stays_coherent(self):
        # 1-seed smoke: snowman n=25 still gets seed 0 (it is in the cap).
        self.assertEqual(heavy._seeds_for("snowman", 25, (0,)), (0,))

    def test_full_cell_count(self):
        cells = heavy._build_cells(self._FULL, skip_snowman_n25=False)
        # PBFT 160 + FFG 160 + Snowman(n10 80 + n25 32) 112 = 432.
        self.assertEqual(len(cells), 432)
        sn25 = [c for c in cells if c[0] == "snowman" and c[2] == 25]
        self.assertEqual(len(sn25), 32)          # 4 timelines × 8 seeds
        self.assertTrue(all(c[3] < 8 for c in sn25))

    def test_skip_drops_only_snowman_n25(self):
        cells = heavy._build_cells(self._FULL, skip_snowman_n25=True)
        self.assertEqual(len(cells), 400)        # 432 − 32
        self.assertFalse(any(c[0] == "snowman" and c[2] == 25 for c in cells))

    def test_every_loss_cell_has_a_control_at_same_seed(self):
        # The finalization_rate post-pass needs, for every loss cell, a
        # control (delay-heavy-tail) row at the same (protocol, n, seed).
        cells = heavy._build_cells(self._FULL, skip_snowman_n25=False)
        controls = {(p, n, s) for (p, tl, n, s) in cells
                    if tl == heavy.CONTROL_TIMELINE}
        for (p, tl, n, s) in cells:
            if tl != heavy.CONTROL_TIMELINE:
                self.assertIn((p, n, s), controls, msg=f"{p} n{n} {tl} seed{s}")


if __name__ == "__main__":
    unittest.main()
