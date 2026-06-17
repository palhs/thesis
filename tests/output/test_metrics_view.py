"""T42 — Tests for the derived metrics view (`results/baseline/metrics.csv`).

`results/baseline/metrics.csv` is a DERIVED, completeness-verified metrics
projection over `results/baseline/baseline.csv` (the canonical per-trial
file, provenance commit 24a491a4). It is NOT a rename and NOT new
collection — baseline.csv stays authoritative. The view's job is to expose
the latency / throughput / communication-overhead metric families keyed by
row identity, as a thin downstream-friendly slice.

These tests assert:
  (1) the view is regenerable and the artifact exists,
  (2) completeness — one view row per source main-file row, every metric
      column present and populated,
  (3) round-trip fidelity — each metric cell equals the corresponding
      baseline.csv cell byte-for-byte (the view is pass-through),
  (4) byte-identical determinism — building twice yields identical bytes,
  (5) provenance — commit_hash carried through is 24a491a4.

Re-run: PYTHONPATH=src python3 -m pytest tests/output/test_metrics_view.py -q
"""
from __future__ import annotations

import csv as _csv
import math
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from output.metrics_view import (
    IDENTITY_COLUMNS,
    METRIC_COLUMNS,
    VIEW_COLUMNS,
    build_metrics_view,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE = _REPO_ROOT / "results" / "baseline" / "baseline.csv"
_METRICS = _REPO_ROOT / "results" / "baseline" / "metrics.csv"

_EXPECTED_COMMIT = "24a491a4"


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(_csv.DictReader(fh))


class TestMetricsView(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src_rows = _read_rows(_BASELINE)

    def test_view_columns_are_identity_plus_metrics(self):
        self.assertEqual(
            list(VIEW_COLUMNS),
            list(IDENTITY_COLUMNS) + list(METRIC_COLUMNS),
        )

    def test_metric_columns_cover_three_families(self):
        # latency, throughput, communication overhead.
        self.assertEqual(
            set(METRIC_COLUMNS),
            {
                "commit_latency_ms", "finality_latency_ms",
                "tps", "goodput",
                "consensus_msgs_per_acu", "total_msgs_per_acu",
                "bytes_per_acu",
            },
        )

    def test_artifact_exists(self):
        self.assertTrue(_METRICS.exists(),
                        f"missing derived artifact {_METRICS}")

    def test_header_is_view_columns(self):
        with _METRICS.open(newline="") as fh:
            reader = _csv.DictReader(fh)
            self.assertEqual(reader.fieldnames, list(VIEW_COLUMNS))

    def test_row_count_matches_source(self):
        view_rows = _read_rows(_METRICS)
        self.assertEqual(len(view_rows), len(self.src_rows))
        self.assertEqual(len(view_rows), 300)

    def test_no_empty_metric_cells(self):
        for r in _read_rows(_METRICS):
            for col in METRIC_COLUMNS:
                cell = r[col]
                self.assertNotIn(cell, (None, ""),
                                 f"{r['run_id']} seed {r['seed']}: {col} empty")
                self.assertTrue(math.isfinite(float(cell)),
                                f"{r['run_id']} seed {r['seed']}: "
                                f"{col}={cell!r} non-finite")

    def test_round_trip_fidelity(self):
        """Every cell of the view equals the source cell byte-for-byte
        (string compare, since the view is pass-through)."""
        view_rows = _read_rows(_METRICS)
        # Key both sides by (run_id, seed) — unique in the per-trial schema.
        src_by_key = {(r["run_id"], r["seed"]): r for r in self.src_rows}
        for vr in view_rows:
            key = (vr["run_id"], vr["seed"])
            self.assertIn(key, src_by_key, f"view row {key} not in source")
            sr = src_by_key[key]
            for col in VIEW_COLUMNS:
                self.assertEqual(
                    vr[col], sr[col],
                    f"{key} col {col}: view {vr[col]!r} != src {sr[col]!r}",
                )

    def test_provenance_commit_hash(self):
        self.assertEqual({r["commit_hash"] for r in _read_rows(_METRICS)},
                         {_EXPECTED_COMMIT})

    def test_regenerable_and_byte_identical(self):
        with TemporaryDirectory() as td1, TemporaryDirectory() as td2:
            out1 = Path(td1) / "metrics.csv"
            out2 = Path(td2) / "metrics.csv"
            build_metrics_view(src_csv=_BASELINE, out_csv=out1)
            build_metrics_view(src_csv=_BASELINE, out_csv=out2)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())

    def test_rebuild_matches_committed_artifact(self):
        """Rebuilding into a temp file reproduces the on-disk artifact
        byte-for-byte (the artifact is the deterministic build output)."""
        with TemporaryDirectory() as td:
            out = Path(td) / "metrics.csv"
            build_metrics_view(src_csv=_BASELINE, out_csv=out)
            self.assertEqual(out.read_bytes(), _METRICS.read_bytes())


if __name__ == "__main__":
    unittest.main()
