"""T41 — _generic_cols emits the four workload_* columns from meta,
and _format_row renders goodput + bytes_per_acu at 6 decimals.
"""
from __future__ import annotations

import math
import unittest
from unittest.mock import patch

from output.csv import _GENERIC_COLUMNS, _format_row, _generic_cols
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult


def _meta() -> ScenarioMeta:
    return ScenarioMeta(
        run_id="pbft-n4", protocol="pbft", n=4, variant=None, seed=42,
        t_max=20.0, arrival_process="deterministic", tx_bytes=1024,
        conflict_rate=0.25, offered_rate=250.0, interval=0.5,
    )


def _result() -> RunResult:
    return RunResult(stopped_by="quiescence", now=1.0,
                     events_processed=2, events_tombstoned=0)


class TestWorkloadGenericCols(unittest.TestCase):
    def test_generic_cols_emit_workload_from_meta(self):
        with patch("output.csv._resolve_commit_hash", return_value="x"):
            row = _generic_cols([], _result(), _meta())
        self.assertEqual(row["workload_arrival_process"], "deterministic")
        self.assertEqual(row["workload_tx_bytes"], 1024)
        self.assertEqual(row["workload_conflict_rate"], 0.25)
        self.assertEqual(row["workload_offered_rate"], 250.0)

    def test_workload_cols_in_generic_columns_frozenset(self):
        for c in ("workload_arrival_process", "workload_tx_bytes",
                  "workload_conflict_rate", "workload_offered_rate"):
            self.assertIn(c, _GENERIC_COLUMNS)

    def test_goodput_and_bytes_per_acu_not_generic(self):
        # Per-protocol reducer outputs (Phase 3), not generic.
        self.assertNotIn("goodput", _GENERIC_COLUMNS)
        self.assertNotIn("bytes_per_acu", _GENERIC_COLUMNS)


class TestWorkloadFormatting(unittest.TestCase):
    def _full_row(self, **overrides):
        row = {c: float("nan") for c in COLUMN_ORDER}
        row.update({
            "run_id": "r", "protocol": "pbft", "n": 4, "seed": 0,
            "workload_arrival_process": "poisson", "workload_tx_bytes": 512,
            "workload_conflict_rate": 0.0, "workload_offered_rate": 100.0,
            "commit_hash": "x", "t_max": 20.0,
        })
        row.update(overrides)
        return row

    def test_goodput_six_decimals(self):
        out = _format_row(self._full_row(goodput=1.5))
        self.assertEqual(out["goodput"], "1.500000")

    def test_bytes_per_acu_six_decimals(self):
        out = _format_row(self._full_row(bytes_per_acu=1.5))
        self.assertEqual(out["bytes_per_acu"], "1.500000")

    def test_workload_cols_passthrough(self):
        out = _format_row(self._full_row())
        self.assertEqual(out["workload_arrival_process"], "poisson")
        self.assertEqual(out["workload_tx_bytes"], "512")
        self.assertEqual(out["workload_conflict_rate"], "0.0")
        self.assertEqual(out["workload_offered_rate"], "100.0")


if __name__ == "__main__":
    unittest.main()
