"""Integration: observed delay distribution matches the configured one (T25).

TASKS.md T25 outcome: "delay distribution matches config". The per-subsystem
suites only show that *a* random delay was drawn (test_e2e.py) and that
samples stay within bounds (test_delay_dist.py, unit level). This test
closes the gap the T23-review M1 Backlog note flagged: over many seeded
runs, the *shape* of the observed end-to-end delay — mean and spread —
must match the configured `uniform(low, high)`.

Run at a single n (delay sampling is per-message and n-independent;
sweeping n here would re-test identical RNG code — see the node-sweep
decision recorded for T25). The pool is large because n=7 yields
n*(n-1)=42 deliveries per run; SEEDS runs give 42*len(SEEDS) samples.

The test is statistical but not flaky: the seed list is fixed, so the
observed mean/spread are deterministic. The tolerances are wide enough to
clear that fixed outcome comfortably and tight enough to fail if the
configured distribution were wrong (a constant delay, or a shifted/narrower
uniform).
"""
import math
import statistics
import unittest

from network import DelayDist, Phase
from _helpers import BroadcastNode, build_and_run

_N = 7
_LOW, _HIGH = 100.0, 500.0
_SEEDS = tuple(range(60))   # 60 runs * 42 deliveries = 2520 delay samples

_EXPECTED_MEAN = (_LOW + _HIGH) / 2.0                 # 300.0
_EXPECTED_STD = (_HIGH - _LOW) / math.sqrt(12.0)      # ~115.47, uniform sd

# Tolerances. With ~2520 samples the standard error of the mean is
# ~115.47/sqrt(2520) ~= 2.3, so +/-20 on the mean is many SE wide for the
# fixed-seed pool yet still rejects e.g. uniform(100,300) (mean 200). The
# spread tolerance rejects a constant delay (sd 0) or a much narrower range.
_MEAN_TOL = 20.0
_STD_TOL = 20.0


class TestDelayDistribution(unittest.TestCase):
    def setUp(self):
        phases = (Phase(0.0, math.inf,
                        DelayDist("uniform", {"low": _LOW, "high": _HIGH})),)
        self.samples: list[float] = []
        for seed in _SEEDS:
            nodes = [BroadcastNode(i, global_seed=seed) for i in range(_N)]
            _, deliveries, _ = build_and_run(nodes, phases, seed)
            self.samples.extend(
                t_delivered - t_sent
                for (*_x, t_sent, t_delivered) in deliveries)

    def test_sample_pool_is_the_expected_size(self):
        self.assertEqual(len(self.samples), len(_SEEDS) * _N * (_N - 1))

    def test_every_sample_within_configured_bounds(self):
        for s in self.samples:
            self.assertGreaterEqual(s, _LOW)
            self.assertLessEqual(s, _HIGH)

    def test_mean_matches_configured_distribution(self):
        self.assertAlmostEqual(statistics.fmean(self.samples),
                               _EXPECTED_MEAN, delta=_MEAN_TOL)

    def test_spread_matches_configured_distribution(self):
        # population sd: the pool is the whole observed set, not a subsample
        self.assertAlmostEqual(statistics.pstdev(self.samples),
                               _EXPECTED_STD, delta=_STD_TOL)


if __name__ == "__main__":
    unittest.main()
