"""End-to-end run-success evidence for the T46 delay harness.

Drives the real protocol baselines through the moderate-delay timeline,
the clip, and the row projection at n=10 for one seed per protocol — the
full run -> clip_records -> reducer -> _build_row pipeline. Asserts:

  - every protocol produces a row (run success);
  - the calibration guard holds: clipped_fraction < 5 % for every cell;
  - the row carries the 18-column T40 projection plus the five Family-B
    annotation columns, with the recorded slot_duration / e_delay;
  - determinism: a byte-identical re-run of the same (timeline, n, seed)
    yields an identical row (the determinism contract under the
    RNG-driven delay-sampling path).

n=25 is exercised by the full sweep (src/delay/sweep.py main); this suite
stays at n=10 for test speed while still crossing every protocol and both
timelines.
"""
from __future__ import annotations

import unittest

from output.schema import COLUMN_ORDER

from delay import config as cfg
from delay.clip import clip_records
from delay.runners import RUNNERS
from delay.sweep import _DELAY_COLUMNS, _build_row, write_csv

_N = 10
_SEED = 0


def _one(protocol: str, timeline: cfg.Timeline, n: int, seed: int):
    runner = RUNNERS[protocol]
    records, result, meta = runner(timeline, n, seed)
    kept, stats = clip_records(records, cfg.WINDOW_S, cfg.ONE_ROUND_S[protocol])
    row = _build_row(kept, result, meta, timeline, stats.clipped_fraction,
                     commit_hash="TESTHASH")
    return row, stats


class TestPipeline(unittest.TestCase):
    def test_every_protocol_produces_a_row(self):
        tl = cfg.TIMELINES[0]
        for protocol in RUNNERS:
            row, _ = _one(protocol, tl, _N, _SEED)
            self.assertEqual(row["protocol"], protocol)
            self.assertEqual(row["n"], _N)
            # The headline cross-protocol latency column is populated.
            self.assertGreater(row["commit_latency_ms"], 0.0)
            self.assertEqual(row["success_rate"], 1.0)

    def test_calibration_guard_holds(self):
        # Self-check: clipped_fraction < 5 % for every (protocol, timeline)
        # cell at n=10. (n=25 is checked by the full-sweep orchestrator.)
        for protocol in RUNNERS:
            for tl in cfg.TIMELINES:
                _, stats = _one(protocol, tl, _N, _SEED)
                self.assertLess(
                    stats.clipped_fraction, 0.05,
                    msg=f"{protocol}/{tl.name}: clip="
                        f"{stats.clipped_fraction:.4f}")

    def test_row_has_all_columns(self):
        row, _ = _one("pbft", cfg.TIMELINES[0], _N, _SEED)
        for col in COLUMN_ORDER:
            self.assertIn(col, row, msg=col)
        for col in _DELAY_COLUMNS:
            self.assertIn(col, row, msg=col)

    def test_annotation_columns_recorded(self):
        tl = next(t for t in cfg.TIMELINES if t.name == "delay-uniform")
        row, _ = _one("casper-ffg", tl, _N, _SEED)
        self.assertEqual(row["network_phase_id"], "delay-uniform")
        self.assertAlmostEqual(row["e_delay_ms"], 300.0)
        # FFG slot rescaled to 1200 ms (experiment-matrix §5 coherence).
        self.assertAlmostEqual(row["slot_duration_ms"], 1200.0)
        self.assertAlmostEqual(row["run_horizon_s"], cfg.T_MAX)


class TestDeterminism(unittest.TestCase):
    def test_byte_identical_rerun(self):
        # Same (protocol, timeline, n, seed) -> byte-identical CSV. Exercises
        # the RNG-driven delay-sampling path (network_seed(global_seed)).
        # Compared on the SERIALIZED row, not the raw dict: NaN-bearing
        # Snowman-parameter columns make a dict `==` spuriously fail
        # (nan != nan) even when the run is deterministic — the byte-level
        # CSV is the real determinism unit (renders nan as "nan").
        import tempfile
        from pathlib import Path

        tl = cfg.TIMELINES[1]   # delay-exponential — the memoryless-tail path
        for protocol in RUNNERS:
            row_a, _ = _one(protocol, tl, _N, _SEED)
            row_b, _ = _one(protocol, tl, _N, _SEED)
            with tempfile.TemporaryDirectory() as d:
                pa, pb = Path(d) / "a.csv", Path(d) / "b.csv"
                write_csv([row_a], pa)
                write_csv([row_b], pb)
                self.assertEqual(pa.read_bytes(), pb.read_bytes(),
                                 msg=protocol)


if __name__ == "__main__":
    unittest.main()
