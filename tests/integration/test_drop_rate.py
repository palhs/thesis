"""Integration: observed delivery rate matches the configured p_drop (T25).

Bernoulli analogue of test_delay_distribution.py. The per-subsystem suites
only pin the saturation case (`test_full_drop_phase_suppresses_delivery` at
`p_drop ~= 1.0`); this closes the mid-range calibration hole TASKS.md T25's
"delay distribution matches config" outcome implicitly covers for delay but
not for drop.

Run at a single n (drop sampling is per-message and n-independent; sweeping
n here would re-test identical RNG code). The pool is large because n=7
yields n*(n-1)=42 attempted deliveries per run; SEEDS runs give
42*len(SEEDS) Bernoulli trials.

The test is statistical but not flaky: the seed list is fixed, so the
observed count is deterministic. The tolerance is wide enough to clear
that fixed outcome comfortably and tight enough to fail if the configured
p_drop were wrong (a no-drop phase, or a drop rate shifted by ~10%).
"""
import math
import unittest

from network import DelayDist, Phase
from _helpers import BroadcastNode, build_and_run

_N = 7
_P_DROP = 0.3
_SEEDS = tuple(range(60))                  # 60 * 42 = 2520 Bernoulli trials

_TRIALS_PER_RUN = _N * (_N - 1)
_EXPECTED_DROPS = _P_DROP * len(_SEEDS) * _TRIALS_PER_RUN          # 756
_EXPECTED_RATE = _P_DROP

# Tolerance. With ~2520 Bernoulli(0.3) trials the standard error of the
# sample proportion is sqrt(p(1-p)/n) ~= 0.0091, so +/-0.03 is ~3.3 SE
# wide for the fixed-seed pool yet still rejects e.g. p_drop=0 (no drops)
# or p_drop=0.5 (much heavier loss).
_RATE_TOL = 0.03


class TestDropRate(unittest.TestCase):
    def setUp(self):
        phases = (Phase(0.0, math.inf,
                        DelayDist("constant", {"delay": 10.0}),
                        p_drop=_P_DROP),)
        self.attempted = 0
        self.delivered = 0
        for seed in _SEEDS:
            nodes = [BroadcastNode(i, global_seed=seed) for i in range(_N)]
            _, deliveries, _ = build_and_run(nodes, phases, seed)
            self.attempted += _TRIALS_PER_RUN
            self.delivered += len(deliveries)

    def test_trial_count_is_the_expected_size(self):
        self.assertEqual(self.attempted, len(_SEEDS) * _TRIALS_PER_RUN)

    def test_some_messages_dropped_some_delivered(self):
        # sanity: with p_drop=0.3 the pool is neither empty nor full
        self.assertGreater(self.delivered, 0)
        self.assertLess(self.delivered, self.attempted)

    def test_observed_drop_rate_matches_configured(self):
        observed_rate = 1.0 - self.delivered / self.attempted
        self.assertAlmostEqual(observed_rate, _EXPECTED_RATE,
                               delta=_RATE_TOL)


if __name__ == "__main__":
    unittest.main()
