"""Family C sweep: cell grid, jobs-equivalence, ratio post-pass (T51)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from adversary import sweep
from adversary import config as cfg


class TestGrid(unittest.TestCase):
    def test_cells_per_proto_n_seed(self):
        # 1 control (f=0) + 3 f × 3 m attack = 10 cells per (proto, n, seed).
        cells = sweep._build_cells((0,))
        per = [c for c in cells if c[0] == "pbft" and c[1] == 10 and c[4] == 0]
        self.assertEqual(len(per), 10)
        controls = [c for c in per if c[2] == 0.0]
        self.assertEqual(len(controls), 1)
        self.assertEqual(controls[0][3], 0.0)            # control m == 0.0

    def test_cell_key_stable_and_safe(self):
        k = sweep._cell_key(("snowman", 25, 0.10, 5.0, 7))
        self.assertNotIn("/", k)
        self.assertNotIn(" ", k)
        # deterministic: same cell -> same key.
        self.assertEqual(k, sweep._cell_key(("snowman", 25, 0.10, 5.0, 7)))

    def test_distinct_cells_distinct_fingerprints(self):
        a = sweep._param_fingerprint(("pbft", 10, 0.10, 2.0, 0))
        b = sweep._param_fingerprint(("pbft", 10, 0.10, 5.0, 0))
        c = sweep._param_fingerprint(("pbft", 10, 0.20, 2.0, 0))
        self.assertNotEqual(a, b)        # m differs
        self.assertNotEqual(a, c)        # f differs
        d = sweep._param_fingerprint(("snowman", 10, 0.10, 2.0, 0))
        e = sweep._param_fingerprint(("pbft", 25, 0.10, 2.0, 0))
        self.assertNotEqual(a, d)        # protocol differs
        self.assertNotEqual(a, e)        # n differs


class TestFinalityRatioPostPass(unittest.TestCase):
    def test_control_is_one_attacks_are_ratio(self):
        rows = [
            {"protocol": "pbft", "n": 10, "seed": 0, "byzantine_fraction": 0.0,
             "delay_mult": 0.0, "commit_latency_ms": 100.0},
            {"protocol": "pbft", "n": 10, "seed": 0, "byzantine_fraction": 0.20,
             "delay_mult": 5.0, "commit_latency_ms": 250.0},
        ]
        sweep._finality_delay_ratios(rows)
        self.assertEqual(rows[0]["finality_delay_ratio"], 1.0)
        self.assertAlmostEqual(rows[1]["finality_delay_ratio"], 2.5)

    def test_nan_when_control_absent_or_zero(self):
        import math
        rows = [
            {"protocol": "snowman", "n": 25, "seed": 9,
             "byzantine_fraction": 0.30, "delay_mult": 10.0,
             "commit_latency_ms": 5000.0},   # no control sibling in this set
        ]
        sweep._finality_delay_ratios(rows)
        self.assertTrue(math.isnan(rows[0]["finality_delay_ratio"]))

    def test_nan_when_control_did_not_finalize(self):
        import math
        # Control present but commit_latency_ms is 0.0 (no finalization) -> NaN.
        rows = [
            {"protocol": "pbft", "n": 10, "seed": 0, "byzantine_fraction": 0.0,
             "delay_mult": 0.0, "commit_latency_ms": 0.0},
            {"protocol": "pbft", "n": 10, "seed": 0, "byzantine_fraction": 0.20,
             "delay_mult": 5.0, "commit_latency_ms": 250.0},
        ]
        sweep._finality_delay_ratios(rows)
        self.assertEqual(rows[0]["finality_delay_ratio"], 1.0)   # control still 1.0
        self.assertTrue(math.isnan(rows[1]["finality_delay_ratio"]))

    def test_nan_when_attack_latency_is_nan(self):
        import math
        rows = [
            {"protocol": "snowman", "n": 10, "seed": 2, "byzantine_fraction": 0.0,
             "delay_mult": 0.0, "commit_latency_ms": 1000.0},
            {"protocol": "snowman", "n": 10, "seed": 2, "byzantine_fraction": 0.30,
             "delay_mult": 10.0, "commit_latency_ms": float("nan")},
        ]
        sweep._finality_delay_ratios(rows)
        self.assertTrue(math.isnan(rows[1]["finality_delay_ratio"]))


class TestJobsEquivalence(unittest.TestCase):
    def test_jobs1_equals_jobs2_smoke(self):
        # 1-seed smoke grid byte-identical across jobs=1 and jobs=2.
        with tempfile.TemporaryDirectory() as d:
            out1 = Path(d) / "a.csv"
            out2 = Path(d) / "b.csv"
            rows1, _ = sweep.run_sweep(seeds=(0,), out=out1, jobs=1, fresh=True)
            sweep.write_csv(rows1, out1)
            rows2, _ = sweep.run_sweep(seeds=(0,), out=out2, jobs=2, fresh=True)
            sweep.write_csv(rows2, out2)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())


if __name__ == "__main__":
    unittest.main()
