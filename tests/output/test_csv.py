"""Unit tests for output.csv.write_unified_csv with monkeypatched
_REDUCERS. No protocol code involved.
"""
from __future__ import annotations

import csv as _csv
import math
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from event_log import EventRecord
from output.csv import write_unified_csv
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult


def _records():
    """One delivery + one decided so _total_msgs_per_acu = 1.0."""
    return [
        EventRecord(t=0.1, node_id=0, event_type="delivery", seq=1,
                    fields={"msg_type": "x", "src": 0, "dst": 1}),
        EventRecord(t=0.2, node_id=0, event_type="decided", seq=-1,
                    fields={"instance_id": (0, 0)}),
    ]


def _result():
    return RunResult(stopped_by="quiescence", now=1.0,
                     events_processed=2, events_tombstoned=0)


def _meta(protocol: str, n: int, run_id: str | None = None) -> ScenarioMeta:
    return ScenarioMeta(
        run_id=run_id or f"{protocol}-n{n}",
        protocol=protocol, n=n, variant=None, seed=42, t_max=math.nan,
    )


def _ok_protocol_cols(records, result, meta):
    """Mock reducer: returns all 13 non-generic columns with sentinel
    values, NaN for Snowman params unless protocol is snowman.

    goodput + bytes_per_acu (T41) are per-protocol reducer outputs; the
    real reducers fill them in Phase 3, so this stand-in supplies
    sentinels to exercise the writer's full COLUMN_ORDER projection."""
    is_sn = meta.protocol == "snowman"
    return {
        "commit_latency_ms":      100.0,
        "finality_latency_ms":    100.0,
        "tps":                    1.0,
        "goodput":                1.0,
        "consensus_msgs_per_acu": 1.0,
        "bytes_per_acu":          1.0,
        "success_rate":           1.0,
        "fork_rate":              0.0,
        "K":             3   if is_sn else float("nan"),
        "alpha_p":       2   if is_sn else float("nan"),
        "alpha_c":       3   if is_sn else float("nan"),
        "beta":          15  if is_sn else float("nan"),
        "alpha_c_over_K": 1.0 if is_sn else float("nan"),
    }


_REDUCERS_OK = {
    "pbft":       _ok_protocol_cols,
    "casper-ffg": _ok_protocol_cols,
    "snowman":    _ok_protocol_cols,
}


class TestWriteUnifiedCsv(unittest.TestCase):
    def test_three_runs_one_per_protocol(self):
        runs = [
            (_records(), _result(), _meta("pbft", 4)),
            (_records(), _result(), _meta("casper-ffg", 7)),
            (_records(), _result(), _meta("snowman", 7)),
        ]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK), \
                 patch("output.csv._resolve_commit_hash",
                       return_value="abc12345"):
                write_unified_csv(path, runs)
            with path.open() as fh:
                reader = _csv.DictReader(fh)
                rows = list(reader)
                fieldnames = reader.fieldnames
        self.assertEqual(fieldnames, list(COLUMN_ORDER))
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [r["protocol"] for r in rows],
            ["casper-ffg", "pbft", "snowman"],  # lex sort
        )

    def test_skips_snowman_n4(self):
        runs = [
            (_records(), _result(), _meta("snowman", 4)),
            (_records(), _result(), _meta("snowman", 7)),
        ]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK), \
                 patch("output.csv._resolve_commit_hash",
                       return_value="abc12345"):
                write_unified_csv(path, runs)
            with path.open() as fh:
                rows = list(_csv.DictReader(fh))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["protocol"], "snowman")
        self.assertEqual(rows[0]["n"], "7")

    def test_empty_runs_header_only(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK):
                write_unified_csv(path, [])
            with path.open() as fh:
                lines = fh.read().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], ",".join(COLUMN_ORDER))

    def test_unknown_protocol_raises(self):
        runs = [(_records(), _result(), _meta("foo", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK):
                with self.assertRaises(KeyError) as cm:
                    write_unified_csv(path, runs)
        self.assertIn("foo", str(cm.exception))

    def test_reducer_returns_generic_col_raises(self):
        def _bad(records, result, meta):
            d = _ok_protocol_cols(records, result, meta)
            d["n"] = 99   # generic column collision
            return d
        runs = [(_records(), _result(), _meta("pbft", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", {"pbft": _bad}):
                with self.assertRaises(ValueError) as cm:
                    write_unified_csv(path, runs)
        self.assertIn("generic", str(cm.exception))
        self.assertIn("n", str(cm.exception))

    def test_reducer_returns_unknown_col_raises(self):
        def _bad(records, result, meta):
            d = _ok_protocol_cols(records, result, meta)
            d["foobar"] = 1.0   # not in COLUMN_ORDER
            return d
        runs = [(_records(), _result(), _meta("pbft", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", {"pbft": _bad}):
                with self.assertRaises(ValueError) as cm:
                    write_unified_csv(path, runs)
        self.assertIn("unknown", str(cm.exception))
        self.assertIn("foobar", str(cm.exception))

    def test_parent_directory_auto_created(self):
        runs = [(_records(), _result(), _meta("pbft", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "deep" / "tree" / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK), \
                 patch("output.csv._resolve_commit_hash",
                       return_value="x"):
                write_unified_csv(path, runs)
            self.assertTrue(path.exists())

    def test_float_formatting(self):
        """commit_latency_ms is .9f, tps is .6f."""
        def _custom(records, result, meta):
            d = _ok_protocol_cols(records, result, meta)
            d["commit_latency_ms"] = 312.500000123456
            d["tps"] = 1.23456789
            return d
        runs = [(_records(), _result(), _meta("pbft", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", {"pbft": _custom}), \
                 patch("output.csv._resolve_commit_hash",
                       return_value="x"):
                write_unified_csv(path, runs)
            with path.open() as fh:
                row = next(iter(_csv.DictReader(fh)))
        self.assertEqual(row["commit_latency_ms"], "312.500000123")
        self.assertEqual(row["tps"],               "1.234568")


if __name__ == "__main__":
    unittest.main()
