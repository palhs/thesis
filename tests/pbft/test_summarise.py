"""Unit tests for pbft.summarise. Synthetic records modelling one
PBFT instance going PRE-PREPARE → PREPARE quorum → COMMIT quorum →
decided at n=4 honest baseline.
"""
from __future__ import annotations

import math
import unittest

from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult


def _meta(n: int = 4) -> ScenarioMeta:
    return ScenarioMeta(run_id=f"pbft-n{n}", protocol="pbft", n=n,
                        variant=None, seed=42, t_max=math.nan)


def _result():
    return RunResult(stopped_by="quiescence", now=0.5,
                     events_processed=50, events_tombstoned=0)


def _pbft_instance_records(n: int, t_commit: float = 0.4
                           ) -> list[EventRecord]:
    """n decided events at t_commit for instance_id=(0, 0)."""
    # Mock some delivery events too (consensus_msgs_per_acu ≠ NaN).
    recs: list[EventRecord] = []
    for i in range(n):
        recs.append(EventRecord(t=t_commit * 0.5, node_id=i,
                                event_type="delivery", seq=i,
                                fields={"msg_type": "PRE-PREPARE",
                                        "src": 0, "dst": i}))
    for i in range(n):
        recs.append(EventRecord(t=t_commit, node_id=i,
                                event_type="decided", seq=-1,
                                fields={"instance_id": (0, 0)}))
    return recs


class TestSummarise(unittest.TestCase):
    def test_keys_are_protocol_columns_only(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _meta(4))
        expected_keys = {
            "commit_latency_ms", "finality_latency_ms", "tps",
            "consensus_msgs_per_acu", "success_rate", "fork_rate",
            "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
        }
        self.assertEqual(set(row.keys()), expected_keys)

    def test_commit_equals_finality_for_pbft(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4, t_commit=0.4),
                        _result(), _meta(4))
        self.assertEqual(row["commit_latency_ms"],
                         row["finality_latency_ms"])
        self.assertAlmostEqual(row["commit_latency_ms"], 400.0,
                               places=6)

    def test_fork_rate_zero_by_construction(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _meta(4))
        self.assertEqual(row["fork_rate"], 0.0)

    def test_snowman_params_are_nan(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _meta(4))
        for col in ("K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K"):
            self.assertTrue(math.isnan(row[col]))

    def test_no_decided_returns_nan_latency(self):
        from pbft.summarise import summarise
        row = summarise([], _result(), _meta(4))
        self.assertTrue(math.isnan(row["commit_latency_ms"]))
        self.assertEqual(row["success_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
