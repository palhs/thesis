import unittest
from workload import WorkloadConfig, generate_batches

class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_stream(self):
        cfg = WorkloadConfig(arrival_process="poisson", offered_rate=100.0,
                             tx_bytes=512, conflict_rate=0.0)
        a = generate_batches(cfg, global_seed=42, n_opportunities=20, interval=1.0)
        b = generate_batches(cfg, global_seed=42, n_opportunities=20, interval=1.0)
        self.assertEqual(a, b)

    def test_different_seed_differs(self):
        cfg = WorkloadConfig("poisson", 100.0, 512, 0.0)
        a = generate_batches(cfg, 42, 20, 1.0)
        b = generate_batches(cfg, 7, 20, 1.0)
        self.assertNotEqual(a, b)


class TestRate(unittest.TestCase):
    def test_constant_is_exact(self):
        cfg = WorkloadConfig("constant", 100.0, 512, 0.0)
        batches = generate_batches(cfg, 0, 20, 1.0)
        self.assertTrue(all(len(b) == 100 for b in batches))

    def test_poisson_mean_in_tolerance(self):
        cfg = WorkloadConfig("poisson", 100.0, 512, 0.0)
        sizes = [len(b) for s in range(40) for b in generate_batches(cfg, s, 20, 1.0)]
        mean = sum(sizes) / len(sizes)
        self.assertAlmostEqual(mean, 100.0, delta=5.0)


class TestPayloadLength(unittest.TestCase):
    def test_exact_length_small_and_large(self):
        for tx_bytes in (16, 512):
            cfg = WorkloadConfig("constant", 10.0, tx_bytes, 0.0)
            batches = generate_batches(cfg, 3, 5, 1.0)
            for batch in batches:
                self.assertTrue(batch)  # constant rate 10 => non-empty
                for tx in batch:
                    self.assertEqual(len(tx), tx_bytes)

    def test_unknown_process_raises(self):
        cfg = WorkloadConfig("uniform", 10.0, 64, 0.0)
        with self.assertRaises(ValueError):
            generate_batches(cfg, 0, 5, 1.0)
