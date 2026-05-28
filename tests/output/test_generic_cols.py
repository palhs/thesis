"""Unit tests for output.csv._generic_cols + _total_msgs_per_acu.
Synthetic EventRecords; no scheduler / Node / Network involvement.
"""
from __future__ import annotations

import math
import unittest
from unittest.mock import patch

from event_log import EventRecord
from output.csv import (
    _generic_cols,
    _total_msgs_per_acu,
)
from output.schema import ScenarioMeta
from scheduler import RunResult


def _meta(protocol: str = "pbft", n: int = 4, run_id: str = "pbft-n4",
          variant: str | None = None, seed: int = 42,
          t_max: float = math.nan) -> ScenarioMeta:
    return ScenarioMeta(run_id=run_id, protocol=protocol, n=n,
                        variant=variant, seed=seed, t_max=t_max)


def _result(now: float = 1.234, processed: int = 100) -> RunResult:
    return RunResult(stopped_by="quiescence", now=now,
                     events_processed=processed, events_tombstoned=0)


class TestTotalMsgsPerAcu(unittest.TestCase):
    def test_normal_ratio(self):
        records = [
            EventRecord(t=0.1, node_id=0, event_type="delivery", seq=1,
                        fields={"msg_type": "x", "src": 0, "dst": 1}),
            EventRecord(t=0.2, node_id=1, event_type="delivery", seq=2,
                        fields={}),
            EventRecord(t=0.3, node_id=0, event_type="delivery", seq=3,
                        fields={}),
            EventRecord(t=0.4, node_id=0, event_type="decided", seq=-1,
                        fields={"instance_id": (0, 0)}),
        ]
        self.assertEqual(_total_msgs_per_acu(records, _result()), 3.0)

    def test_no_decided_returns_nan(self):
        records = [
            EventRecord(t=0.1, node_id=0, event_type="delivery", seq=1,
                        fields={}),
        ]
        v = _total_msgs_per_acu(records, _result())
        self.assertTrue(math.isnan(v))

    def test_no_deliveries_zero(self):
        records = [
            EventRecord(t=0.1, node_id=0, event_type="decided", seq=-1,
                        fields={"instance_id": (0, 0)}),
        ]
        self.assertEqual(_total_msgs_per_acu(records, _result()), 0.0)


class TestGenericCols(unittest.TestCase):
    def test_identity_passthrough(self):
        with patch("output.csv._resolve_commit_hash",
                   return_value="abc12345"):
            row = _generic_cols([], _result(),
                                _meta(run_id="pbft-n4", protocol="pbft",
                                      n=4, seed=42, t_max=20.0))
        self.assertEqual(row["run_id"], "pbft-n4")
        self.assertEqual(row["protocol"], "pbft")
        self.assertEqual(row["n"], 4)
        self.assertEqual(row["seed"], 42)
        self.assertEqual(row["commit_hash"], "abc12345")
        self.assertEqual(row["t_max"], 20.0)

    def test_keys_are_exactly_generic_columns(self):
        from output.csv import _GENERIC_COLUMNS
        with patch("output.csv._resolve_commit_hash", return_value="x"):
            row = _generic_cols([], _result(), _meta())
        self.assertEqual(set(row.keys()), set(_GENERIC_COLUMNS))


if __name__ == "__main__":
    unittest.main()
