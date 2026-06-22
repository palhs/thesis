# tests/pos/test_slot_sweep.py
"""FFG slot-duration sensitivity sweep — linear-law + determinism test.

Guards the L-W10 finding-H2 (part b) claim that Casper FFG time-to-finality
is EXACTLY linear in slot_duration at slots_per_epoch=2:

    commit_latency_ms = (2·spe + attest_offset)·slot_duration·1000
                      = 5 · slot_duration · 1000   (spe=2, attest_offset=1)

So the absolute ≈5000 ms FFG figure is calibration-set, not protocol-
intrinsic — yet across the realistic sweep {0.5, 1, 2} s it stays well above
the per-block protocols' ≈1000 ms commit. The crossover slot where FFG would
tie the ≈1 s commit is 5·slot ≤ 1 s ⇒ slot ≤ 0.2 s, below realistic slot
times.

Sweep driver: src/pos/slot_sweep.py.
Companion experiment page: wiki/experiments/2026-06-22_ffg-slot-sensitivity.md.

Re-run:
  PYTHONPATH=src:tests/pos python3 -m unittest test_slot_sweep -v
"""
import unittest

from pos.slot_sweep import (
    SLOT_DURATIONS, SLOTS_PER_EPOCH, N, SEEDS,
    measure, expected_commit_latency_ms,
)

# Epsilon: one near-instant network hop (delay=1e-9 s) shows up as a
# +1e-6 ms tail on the finality timestamp. The linear law holds to within
# this; use a tolerance comfortably above it but far below one slot.
_EPS_MS = 1e-3


class TestFFGSlotLinearLaw(unittest.TestCase):
    """commit_latency_ms == 5·slot_duration·1000 at slots_per_epoch=2."""

    def test_finality_is_five_times_slot(self):
        """Linear law holds for every swept slot (>= two values)."""
        self.assertGreaterEqual(len(SLOT_DURATIONS), 2)
        for slot in SLOT_DURATIONS:
            with self.subTest(slot_duration=slot):
                measured = measure(slot, seed=0)
                expected = expected_commit_latency_ms(slot)
                # expected = 5·slot·1000 by construction; assert the factor
                # explicitly too so a slots_per_epoch change is caught.
                self.assertEqual(
                    expected, 5 * slot * 1000.0,
                    "finality factor must be 5 at slots_per_epoch=2")
                self.assertAlmostEqual(
                    measured, expected, delta=_EPS_MS,
                    msg=f"slot={slot}: measured {measured} ms != "
                        f"5·slot·1000 = {expected} ms")

    def test_linear_law_two_explicit_points(self):
        """Spot-check two specific slots independent of the grid constant."""
        # slot=0.5 -> 2500 ms; slot=2.0 -> 10000 ms.
        self.assertAlmostEqual(measure(0.5, seed=0), 2500.0, delta=_EPS_MS)
        self.assertAlmostEqual(measure(2.0, seed=0), 10000.0, delta=_EPS_MS)

    def test_ratio_doubles_with_slot(self):
        """Doubling the slot doubles finality — the linearity, ratio form."""
        lo = measure(0.5, seed=0)
        hi = measure(1.0, seed=0)
        self.assertAlmostEqual(hi / lo, 2.0, places=6)

    def test_seed_invariance(self):
        """FFG finality is structurally deterministic: identical across
        seeds at a fixed slot (the workload RNG does not touch timing)."""
        for slot in SLOT_DURATIONS:
            with self.subTest(slot_duration=slot):
                values = {measure(slot, seed) for seed in SEEDS}
                self.assertEqual(
                    len(values), 1,
                    f"slot={slot}: finality varied across seeds {SEEDS}: "
                    f"{values}")

    def test_crossover_slot_below_realistic(self):
        """The slot at which FFG would tie the ≈1 s per-block commit is
        5·slot = 1000 ms ⇒ slot = 0.2 s — below the swept realistic range,
        so every swept slot finalises strictly slower than ≈1 s."""
        crossover_slot = 1000.0 / expected_commit_latency_ms(1.0) * 1.0
        self.assertAlmostEqual(crossover_slot, 0.2, places=9)
        self.assertLess(crossover_slot, min(SLOT_DURATIONS))
        for slot in SLOT_DURATIONS:
            with self.subTest(slot_duration=slot):
                # Every realistic slot is strictly above the ≈1000 ms commit.
                self.assertGreater(expected_commit_latency_ms(slot), 1000.0)

    def test_config_is_as_run(self):
        """Sweep is at the as-run FFG calibration: spe=2, n=10."""
        self.assertEqual(SLOTS_PER_EPOCH, 2)
        self.assertEqual(N, 10)


if __name__ == "__main__":
    unittest.main()
