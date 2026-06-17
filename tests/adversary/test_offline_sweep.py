import math
import unittest
from adversary.offline_sweep import run_sweep, _build_cells
from adversary import offline_config as oc


class TestOfflineSweep(unittest.TestCase):
    def test_cell_count(self):
        cells = _build_cells((0,))   # 1 seed
        # PBFT 5 f + FFG 5 f + Snowman 4 f, × 2 n × 1 seed = 28 cells.
        self.assertEqual(len(cells), (5 + 5 + 4) * 2)

    def test_smoke_one_seed_runs_and_rows_well_formed(self):
        rows, worst = run_sweep(seeds=(0,), jobs=1, heavy_jobs=1, fresh=True)
        self.assertEqual(len(rows), (5 + 5 + 4) * 2)
        for r in rows:
            self.assertIn(r["success_rate"], (0.0, 1.0))
            if r["byzantine_fraction"] == 0.0:
                self.assertEqual(r["throughput_ratio"], 1.0)

    def test_pbft_boundary_crossed(self):
        rows, _ = run_sweep(seeds=(0,), jobs=1, heavy_jobs=1, fresh=True)
        by = {(r["protocol"], r["n"], r["byzantine_fraction"]): r["success_rate"]
              for r in rows}
        self.assertEqual(by[("pbft", 10, 0.33)], 1.0)   # quorum intact
        self.assertEqual(by[("pbft", 10, 0.40)], 0.0)   # quorum lost → stall


if __name__ == "__main__":
    unittest.main()
