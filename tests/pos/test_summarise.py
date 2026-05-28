"""Unit tests for pos.summarise. Synthetic records modelling one
finalised epoch at n=4 honest baseline.
"""
from __future__ import annotations

import math
import unittest

from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult


def _meta(n: int = 4, variant: str | None = "uniform") -> ScenarioMeta:
    return ScenarioMeta(
        run_id=f"casper-ffg-n{n}-{variant or 'none'}",
        protocol="casper-ffg", n=n, variant=variant,
        seed=42, t_max=20.0,
    )


def _result():
    return RunResult(stopped_by="deadline", now=20.0,
                     events_processed=200, events_tombstoned=0)


def _epoch_finalised_records(n: int) -> list[EventRecord]:
    """One decided event per node for epoch 1, all at t = 5.000000001."""
    return [
        EventRecord(t=5.000000001, node_id=i, event_type="decided",
                    seq=-1, fields={"instance_id": 1})
        for i in range(n)
    ]


class TestSummarise(unittest.TestCase):
    def test_keys_are_protocol_columns_only(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(), _meta())
        expected_keys = {
            "commit_latency_ms", "finality_latency_ms", "tps",
            "consensus_msgs_per_acu", "success_rate", "fork_rate",
            "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
        }
        self.assertEqual(set(row.keys()), expected_keys)

    def test_finality_latency_ms_median(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(), _meta())
        # 5.000000001 s * 1000 = 5000.000001 ms
        self.assertAlmostEqual(row["finality_latency_ms"],
                               5000.000001, places=6)

    def test_snowman_params_are_nan(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(), _meta())
        for col in ("K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K"):
            self.assertTrue(math.isnan(row[col]),
                            f"{col} must be NaN for Casper FFG")

    def test_no_decided_returns_nan_latency(self):
        from pos.summarise import summarise
        row = summarise([], _result(), _meta())
        self.assertTrue(math.isnan(row["commit_latency_ms"]))
        self.assertTrue(math.isnan(row["finality_latency_ms"]))
        self.assertEqual(row["success_rate"], 0.0)

    def test_fork_rate_zero_at_honest_baseline(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(), _meta())
        self.assertEqual(row["fork_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
