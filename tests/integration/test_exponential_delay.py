"""Integration: exponential delay distribution recovered statistically (T25).

Closes T25 review gap I-4. The exponential is the thesis's realistic-
RTT distribution (network-model.md) but the integration suite tests
only constant and uniform delays. test_delay_distribution.py pins the
uniform's mean and spread over a 2 520-sample pool; this is the
exponential analogue.

For exponential(mean = m): population mean = m, population sd = m.
The pool size and SE arithmetic mirror test_delay_distribution.py so
the tolerance reasoning is identical.
"""
import math
import statistics
import unittest

from network import DelayDist, Phase
from _helpers import BroadcastNode, build_and_run

_N = 7
_MEAN = 100.0
_SEEDS = tuple(range(60))                  # 60 * 42 = 2520 samples

_EXPECTED_MEAN = _MEAN
_EXPECTED_STD = _MEAN                      # exponential sd = mean

# SE of mean ~ 100 / sqrt(2520) ~= 2.0; +/-15 is ~7 SE wide. The wider
# bound (vs uniform's +/-20) reflects exponential's heavier tail.
_MEAN_TOL = 15.0
_STD_TOL = 15.0


class TestExponentialDelayDistribution(unittest.TestCase):
    def setUp(self):
        phases = (Phase(0.0, math.inf,
                        DelayDist("exponential", {"mean": _MEAN})),)
        self.samples: list[float] = []
        for seed in _SEEDS:
            nodes = [BroadcastNode(i, global_seed=seed) for i in range(_N)]
            _, deliveries, _ = build_and_run(nodes, phases, seed)
            self.samples.extend(
                t_delivered - t_sent
                for (*_x, t_sent, t_delivered) in deliveries)

    def test_sample_pool_is_the_expected_size(self):
        self.assertEqual(len(self.samples), len(_SEEDS) * _N * (_N - 1))

    def test_every_sample_is_strictly_positive(self):
        # Exponential is unbounded above; _LATENCY_FLOOR enforces > 0.
        for s in self.samples:
            self.assertGreater(s, 0.0)

    def test_mean_matches_configured(self):
        self.assertAlmostEqual(statistics.fmean(self.samples),
                               _EXPECTED_MEAN, delta=_MEAN_TOL)

    def test_spread_matches_exponential_sd_equals_mean(self):
        # The signature property of exponential: population sd = mean.
        self.assertAlmostEqual(statistics.pstdev(self.samples),
                               _EXPECTED_STD, delta=_STD_TOL)


if __name__ == "__main__":
    unittest.main()
