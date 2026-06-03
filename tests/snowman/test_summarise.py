"""Unit tests for snowman.summarise + snowman.summarise.sanity_row.
Synthetic records modelling one Snowman block reaching counter β.

The synthetic `decided` events use `fields["instance_id"]` as block
identity, matching the real Snowman emit shape (see
tests/integration/test_snowman_baseline.py lines 81-83). Plan literal
used `block_hash`; adapted here so the reducer works on actual event
streams.
"""
from __future__ import annotations

import csv as _csv
import math
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from event_log import EventRecord
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult


def _meta(n: int) -> ScenarioMeta:
    return ScenarioMeta(run_id=f"snowman-n{n}", protocol="snowman",
                        n=n, variant=None, seed=42, t_max=20.0)


def _result():
    return RunResult(stopped_by="deadline", now=20.0,
                     events_processed=300, events_tombstoned=0)


def _snowman_records(n: int, t_decided: float = 1.0
                     ) -> list[EventRecord]:
    """n decided events at t_decided, plus some mock query deliveries."""
    recs: list[EventRecord] = []
    for i in range(n):
        recs.append(EventRecord(t=t_decided * 0.1, node_id=i,
                                event_type="delivery", seq=i,
                                fields={"msg_type": "QUERY",
                                        "src": 0, "dst": i}))
    for i in range(n):
        recs.append(EventRecord(t=t_decided, node_id=i,
                                event_type="decided", seq=-1,
                                fields={"instance_id": b"block0"}))
    return recs


class TestSummarise(unittest.TestCase):
    def test_keys_are_protocol_columns_only(self):
        from snowman.summarise import summarise
        row = summarise(_snowman_records(7), _result(), _meta(7))
        expected = {
            "commit_latency_ms", "finality_latency_ms", "tps", "goodput",
            "consensus_msgs_per_acu", "bytes_per_acu",
            "success_rate", "fork_rate",
            "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
        }
        self.assertEqual(set(row.keys()), expected)

    def test_n7_rescale(self):
        """At n=7 the rescaling rule gives K=6, α_p=4, α_c=5, β=15,
        α_c/K = 5/6."""
        from snowman.summarise import summarise
        row = summarise(_snowman_records(7), _result(), _meta(7))
        self.assertEqual(row["K"], 6)
        self.assertEqual(row["alpha_p"], 4)
        self.assertEqual(row["alpha_c"], 5)
        self.assertEqual(row["beta"], 15)
        self.assertAlmostEqual(row["alpha_c_over_K"], 5/6, places=6)

    def test_n10_rescale(self):
        from snowman.summarise import summarise
        row = summarise(_snowman_records(10), _result(), _meta(10))
        self.assertEqual(row["K"], 9)
        self.assertEqual(row["alpha_p"], 5)
        self.assertEqual(row["alpha_c"], 8)
        self.assertEqual(row["beta"], 15)
        self.assertAlmostEqual(row["alpha_c_over_K"], 8/9, places=6)

    def test_n25_caps_at_production(self):
        """At n=25 the rule caps K at 20 (production parameters)."""
        from snowman.summarise import summarise
        row = summarise(_snowman_records(25), _result(), _meta(25))
        self.assertEqual(row["K"], 20)
        self.assertEqual(row["alpha_c"], 16)
        self.assertAlmostEqual(row["alpha_c_over_K"], 0.8, places=6)


def _const_meta(n: int, offered_rate: float = 10.0) -> ScenarioMeta:
    """Constant arrival so batch sizes are exact integers."""
    return ScenarioMeta(run_id=f"snowman-n{n}", protocol="snowman",
                        n=n, variant=None, seed=42, t_max=20.0,
                        arrival_process="constant",
                        offered_rate=offered_rate, tx_bytes=512,
                        conflict_rate=0.0, interval=1.0)


class TestWorkloadColumns(unittest.TestCase):
    def test_columns_are_floats(self):
        from snowman.summarise import summarise
        row = summarise(_snowman_records(7), _result(), _const_meta(7))
        self.assertIsInstance(row["goodput"], float)
        self.assertIsInstance(row["bytes_per_acu"], float)

    def test_goodput_exact_value(self):
        # One distinct decided block -> n_opportunities=1; constant
        # offered_rate=10 -> 10 committed tx; t_max=20 -> 10/20 = 0.5.
        from snowman.summarise import summarise
        row = summarise(_snowman_records(7), _result(), _const_meta(7))
        self.assertAlmostEqual(row["goodput"], 0.5, places=6)

    def test_bytes_per_acu_exact_value(self):
        # 7 QUERY deliveries (NOT tx-carrying): base = 8+32 = 40 each.
        # 7 decided events. total = 7*40; / 7 = 40.0.
        from snowman.summarise import summarise
        row = summarise(_snowman_records(7), _result(), _const_meta(7))
        self.assertAlmostEqual(row["bytes_per_acu"], 40.0, places=6)


class TestSanityRow(unittest.TestCase):
    def test_writes_one_row_to_sibling_file(self):
        from snowman.summarise import sanity_row
        with TemporaryDirectory() as td:
            path = Path(td) / "snowman_n4_sanity.csv"
            sanity_row(_snowman_records(4), _result(), _meta(4), path)
            with path.open() as fh:
                reader = _csv.DictReader(fh)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)
        # Same 18 columns as main schema, plus the degenerate flag.
        self.assertEqual(fieldnames,
                         list(COLUMN_ORDER) + ["snowman_degenerate_n4"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["protocol"], "snowman")
        self.assertEqual(rows[0]["n"], "4")
        self.assertEqual(rows[0]["snowman_degenerate_n4"], "True")
        # n=4 rescaling: K=3, α_p=2, α_c=3, β=15, α_c/K=1.0
        self.assertEqual(rows[0]["K"], "3")
        self.assertEqual(rows[0]["alpha_c"], "3")


if __name__ == "__main__":
    unittest.main()
