"""Unit tests for DelayDist (network-model-phases.md §2)."""
import random
import unittest

from network.phases import DelayDist


class TestDelayDistValidation(unittest.TestCase):
    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("triangular", {})

    def test_missing_required_param_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("constant", {})

    def test_constant_non_positive_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("constant", {"delay": 0})

    def test_uniform_non_positive_low_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("uniform", {"low": 0, "high": 5})

    def test_uniform_high_below_low_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("uniform", {"low": 10, "high": 5})

    def test_normal_negative_std_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("normal", {"mean": 10, "std": -1})

    def test_exponential_non_positive_mean_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("exponential", {"mean": 0})

    def test_heavy_tail_non_positive_shape_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("heavy_tail", {"scale": 10, "shape": 0})

    def test_normal_non_positive_clip_low_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("normal", {"mean": 10, "std": 1, "clip_low": 0})

    def test_heavy_tail_non_positive_scale_rejected(self):
        with self.assertRaises(ValueError):
            DelayDist("heavy_tail", {"scale": 0, "shape": 2})


class TestDelayDistSample(unittest.TestCase):
    def test_constant_is_exact(self):
        d = DelayDist("constant", {"delay": 12.5})
        self.assertEqual(d.sample(random.Random(0)), 12.5)

    def test_uniform_within_bounds(self):
        d = DelayDist("uniform", {"low": 100, "high": 500})
        rng = random.Random(1)
        for _ in range(200):
            s = d.sample(rng)
            self.assertGreaterEqual(s, 100)
            self.assertLessEqual(s, 500)

    def test_normal_floored_by_clip_low(self):
        # mean far below clip_low so the floor always binds
        d = DelayDist("normal", {"mean": -1000, "std": 1, "clip_low": 3.0})
        rng = random.Random(2)
        for _ in range(50):
            self.assertEqual(d.sample(rng), 3.0)

    def test_all_kinds_strictly_positive(self):
        dists = [
            DelayDist("constant", {"delay": 1}),
            DelayDist("uniform", {"low": 1, "high": 2}),
            DelayDist("normal", {"mean": 5, "std": 2}),
            DelayDist("exponential", {"mean": 5}),
            DelayDist("heavy_tail", {"scale": 1, "shape": 2}),
        ]
        rng = random.Random(3)
        for d in dists:
            for _ in range(200):
                self.assertGreater(d.sample(rng), 0.0)

    def test_sample_is_deterministic(self):
        d = DelayDist("exponential", {"mean": 50})
        a = [d.sample(random.Random(7)) for _ in range(5)]
        b = [d.sample(random.Random(7)) for _ in range(5)]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
