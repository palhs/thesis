"""Run-success + determinism evidence for the T47 heavy sweep driver.

The byte-identical-across-jobs property of the shared `run_grid` pipeline is
proven generically by the T46.1 induction witnesses (which already cover the
heavy_tail + p_drop param shapes). These tests exercise the T47-SPECIFIC
additions on real cells: the HEAVY_CALIB run path, the four extra columns
(`p_drop` / `finalized_instances` / `view_change_count` / `finalization_rate`),
and the finalization-rate post-pass — under jobs=1 vs jobs=2.

PBFT-only at n=10 keeps the cells fast; Snowman heavy cells are exercised by
the full sweep, not the unit suite.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common import run_grid

from delay import heavy


def _grid_csv_bytes(cells, jobs, ckpt_dir: Path, csv_path: Path) -> bytes:
    """Run cells through the heavy adapter, fill finalization_rate, write
    the CSV, return its bytes."""
    rows = run_grid(cells, heavy._run_cell, heavy._cell_key,
                    checkpoint_dir=ckpt_dir,
                    run_constants={"commit_hash": "HEAVYTEST"},
                    param_fingerprint=heavy._param_fingerprint, jobs=jobs)
    heavy._finalization_rates(rows)
    heavy.write_csv(rows, csv_path)
    return csv_path.read_bytes()


# A loss-free control cell + a 20%-loss cell (PBFT, n=10, seed 0).
_CONTROL = ("pbft", "delay-heavy-tail", 10, 0)
_LOSS = ("pbft", "delay-heavy-tail-loss-p20", 10, 0)


class TestHeavyColumns(unittest.TestCase):
    def test_row_carries_the_four_t47_columns(self):
        rows = run_grid([_CONTROL], heavy._run_cell, heavy._cell_key,
                        checkpoint_dir=Path(tempfile.mkdtemp()) / "ck",
                        run_constants={"commit_hash": "HEAVYTEST"},
                        param_fingerprint=heavy._param_fingerprint, jobs=1)
        heavy._finalization_rates(rows)
        row = rows[0]
        for col in ("p_drop", "finalized_instances", "view_change_count",
                    "finalization_rate"):
            self.assertIn(col, row)
        # Control: p_drop=0, finalized > 0, finalization_rate = 1.0.
        self.assertEqual(row["p_drop"], 0.0)
        self.assertGreater(row["finalized_instances"], 0)
        self.assertEqual(row["finalization_rate"], 1.0)
        self.assertGreaterEqual(row["view_change_count"], 0)

    def test_loss_cell_p_drop_and_rate_bounds(self):
        cells = [_CONTROL, _LOSS]
        rows = run_grid(cells, heavy._run_cell, heavy._cell_key,
                        checkpoint_dir=Path(tempfile.mkdtemp()) / "ck",
                        run_constants={"commit_hash": "HEAVYTEST"},
                        param_fingerprint=heavy._param_fingerprint, jobs=1)
        heavy._finalization_rates(rows)
        loss = next(r for r in rows
                    if r["network_phase_id"] == "delay-heavy-tail-loss-p20")
        self.assertEqual(loss["p_drop"], 0.20)
        # finalization_rate is a fraction of the control (in [0, 1]).
        self.assertGreaterEqual(loss["finalization_rate"], 0.0)
        self.assertLessEqual(loss["finalization_rate"], 1.0)


class TestHeavyJobsEquivalence(unittest.TestCase):
    def test_jobs1_equals_jobs2_byte_identical(self):
        # The HEAVY_CALIB run path + loss (p_drop>0 drop-coin) + the post-pass
        # are byte-identical whether the grid runs sequentially or in two
        # worker processes.
        cells = [_CONTROL, _LOSS]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            b1 = _grid_csv_bytes(cells, 1, d / "j1", d / "j1.csv")
            b2 = _grid_csv_bytes(cells, 2, d / "j2", d / "j2.csv")
        self.assertEqual(b1, b2)


if __name__ == "__main__":
    unittest.main()
