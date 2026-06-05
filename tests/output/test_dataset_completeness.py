"""T42 — Objective completeness verification over the EXISTING shipped
baseline dataset (`results/baseline/baseline.csv` + the Snowman n=4
sanity sibling).

This test is the verification ACT itself: it runs against the on-disk
T41 dataset (provenance commit 24a491a4, regenerated under T70/PR#8 after
the PBFT client-observed-finality fix) WITHOUT regenerating it. A red here
means the dataset, not the test, is wrong — stop and report rather than
"fixing" the test.

It is independent of the derived metrics.csv view (test_metrics_view.py
covers that). Together they form the T42 completeness gate: this one
asserts the source is complete; the view test asserts the projection is
faithful.

Re-run: PYTHONPATH=src python3 -m pytest tests/output/test_dataset_completeness.py -q
"""
from __future__ import annotations

import csv as _csv
import math
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE = _REPO_ROOT / "results" / "baseline" / "baseline.csv"
_SANITY = _REPO_ROOT / "results" / "baseline" / "snowman_n4_sanity.csv"

# The provenance commit the whole dataset must carry (output-format §13;
# regenerated under T70/PR#8 — TASKS.md Backlog RX.2).
_EXPECTED_COMMIT = "24a491a4"

# The 15 in-scope run_ids (PBFT 5 + Casper FFG 6 + Snowman 4), each at
# 20 seeds 0..19 => 300 main rows. NOT a clean 3x5x20 grid:
#   PBFT     100 = 5 n x 20 seeds
#   Casper   120 = 6 run_ids (5 uniform n + 1 nonuniform n4) x 20 seeds
#   Snowman   80 = 4 n (n=4 routed to the sanity file) x 20 seeds
_EXPECTED_RUN_IDS = {
    "pbft-n4", "pbft-n7", "pbft-n10", "pbft-n16", "pbft-n25",
    "casper-ffg-n4-uniform", "casper-ffg-n4-nonuniform",
    "casper-ffg-n7-uniform", "casper-ffg-n10-uniform",
    "casper-ffg-n16-uniform", "casper-ffg-n25-uniform",
    "snowman-n7", "snowman-n10", "snowman-n16", "snowman-n25",
}

# Metric columns that must be populated (non-empty, finite) on every
# in-scope row: latency, throughput, communication overhead.
_METRIC_COLS = (
    "commit_latency_ms", "finality_latency_ms",
    "tps", "goodput",
    "consensus_msgs_per_acu", "total_msgs_per_acu", "bytes_per_acu",
)

# Snowman-only parameter columns: NaN on non-snowman rows, populated on
# snowman rows (output-format §6 NaN dispatch).
_SNOWMAN_PARAM_COLS = ("K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fh:
        return list(_csv.DictReader(fh))


def _is_nan(cell: str) -> bool:
    try:
        return math.isnan(float(cell))
    except (TypeError, ValueError):
        return False


def _is_finite_number(cell: str) -> bool:
    if cell is None or cell == "":
        return False
    try:
        return math.isfinite(float(cell))
    except (TypeError, ValueError):
        return False


class TestBaselineDatasetCompleteness(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _read_rows(_BASELINE)

    def test_exists(self):
        self.assertTrue(_BASELINE.exists(), f"missing {_BASELINE}")

    def test_row_count_is_300(self):
        self.assertEqual(len(self.rows), 300)

    def test_run_ids_are_the_expected_15(self):
        self.assertEqual({r["run_id"] for r in self.rows}, _EXPECTED_RUN_IDS)

    def test_every_run_id_has_all_20_seeds(self):
        from collections import defaultdict
        seeds_by_run = defaultdict(set)
        for r in self.rows:
            seeds_by_run[r["run_id"]].add(int(r["seed"]))
        expected_seeds = set(range(20))
        for run_id in _EXPECTED_RUN_IDS:
            self.assertEqual(
                seeds_by_run[run_id], expected_seeds,
                f"{run_id} does not have exactly seeds 0..19",
            )

    def test_no_empty_metric_cells(self):
        for r in self.rows:
            for col in _METRIC_COLS:
                self.assertTrue(
                    _is_finite_number(r[col]),
                    f"row {r['run_id']} seed {r['seed']}: "
                    f"{col}={r[col]!r} is empty/non-finite",
                )

    def test_snowman_params_nan_off_snowman_and_populated_on(self):
        for r in self.rows:
            is_snowman = r["protocol"] == "snowman"
            for col in _SNOWMAN_PARAM_COLS:
                if is_snowman:
                    self.assertTrue(
                        _is_finite_number(r[col]),
                        f"snowman row {r['run_id']} seed {r['seed']}: "
                        f"{col}={r[col]!r} should be populated",
                    )
                else:
                    self.assertTrue(
                        _is_nan(r[col]),
                        f"non-snowman row {r['run_id']} seed {r['seed']}: "
                        f"{col}={r[col]!r} should be NaN",
                    )

    def test_honest_path_invariant(self):
        for r in self.rows:
            self.assertEqual(float(r["success_rate"]), 1.0,
                             f"{r['run_id']} seed {r['seed']} success_rate")
            self.assertEqual(float(r["fork_rate"]), 0.0,
                             f"{r['run_id']} seed {r['seed']} fork_rate")

    def test_single_commit_hash(self):
        hashes = {r["commit_hash"] for r in self.rows}
        self.assertEqual(hashes, {_EXPECTED_COMMIT})

    def test_row_arithmetic_reconciliation(self):
        from collections import Counter
        by_proto = Counter(r["protocol"] for r in self.rows)
        self.assertEqual(by_proto["pbft"], 100)
        self.assertEqual(by_proto["casper-ffg"], 120)
        self.assertEqual(by_proto["snowman"], 80)
        self.assertEqual(sum(by_proto.values()), 300)

    def test_no_snowman_n4_in_main_file(self):
        snowman_ns = {int(r["n"]) for r in self.rows
                      if r["protocol"] == "snowman"}
        self.assertNotIn(4, snowman_ns)
        self.assertEqual(snowman_ns, {7, 10, 16, 25})


class TestSnowmanN4SanityFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = _read_rows(_SANITY)

    def test_exists(self):
        self.assertTrue(_SANITY.exists(), f"missing {_SANITY}")

    def test_has_20_data_rows(self):
        self.assertEqual(len(self.rows), 20)

    def test_all_degenerate_n4_snowman(self):
        for r in self.rows:
            self.assertEqual(r["protocol"], "snowman")
            self.assertEqual(int(r["n"]), 4)
            self.assertEqual(r["snowman_degenerate_n4"], "True")

    def test_seeds_0_to_19(self):
        self.assertEqual(sorted(int(r["seed"]) for r in self.rows),
                         list(range(20)))

    def test_single_commit_hash(self):
        self.assertEqual({r["commit_hash"] for r in self.rows},
                         {_EXPECTED_COMMIT})


if __name__ == "__main__":
    unittest.main()
