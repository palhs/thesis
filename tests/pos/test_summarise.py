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
            "commit_latency_ms", "finality_latency_ms", "tps", "goodput",
            "consensus_msgs_per_acu", "bytes_per_acu",
            "success_rate", "fork_rate",
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


def _const_meta(n: int = 4, offered_rate: float = 10.0,
                slots_per_epoch: int | None = None) -> ScenarioMeta:
    """Constant arrival so batch sizes are exact integers."""
    return ScenarioMeta(
        run_id=f"casper-ffg-n{n}", protocol="casper-ffg", n=n,
        variant="uniform", seed=42, t_max=20.0,
        arrival_process="constant", offered_rate=offered_rate,
        tx_bytes=512, conflict_rate=0.0, interval=1.0,
        slots_per_epoch=slots_per_epoch,
    )


def _epoch_records_with_deliveries(n: int) -> list[EventRecord]:
    """One decided event per node for epoch 1, plus n ATTESTATION
    deliveries (not tx-carrying)."""
    recs: list[EventRecord] = [
        EventRecord(t=1.0, node_id=i, event_type="delivery", seq=i,
                    fields={"msg_type": "ATTESTATION", "src": 0, "dst": i})
        for i in range(n)
    ]
    recs += [
        EventRecord(t=5.000000001, node_id=i, event_type="decided",
                    seq=-1, fields={"instance_id": 1})
        for i in range(n)
    ]
    return recs


class TestWorkloadColumns(unittest.TestCase):
    def test_columns_are_floats(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(),
                        _const_meta(4))
        self.assertIsInstance(row["goodput"], float)
        self.assertIsInstance(row["bytes_per_acu"], float)

    def test_goodput_default_slots_per_epoch(self):
        # 1 distinct decided epoch * default slots_per_epoch(2) = 2
        # opportunities; constant offered_rate=10 -> 20 committed tx;
        # t_max=20 -> 20/20 = 1.0.
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(),
                        _const_meta(4))
        self.assertAlmostEqual(row["goodput"], 1.0, places=6)

    def test_goodput_explicit_slots_per_epoch(self):
        # slots_per_epoch=4 -> 1*4 = 4 opportunities; 40 tx / 20 = 2.0.
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(),
                        _const_meta(4, slots_per_epoch=4))
        self.assertAlmostEqual(row["goodput"], 2.0, places=6)

    def test_bytes_per_acu_exact_value(self):
        # 4 ATTESTATION deliveries (not tx-carrying): base =
        # 8+8+32+40+40+4+64 = 196 each; 4 decided -> 4*196 / 4 = 196.0.
        from pos.summarise import summarise
        row = summarise(_epoch_records_with_deliveries(4), _result(),
                        _const_meta(4))
        self.assertAlmostEqual(row["bytes_per_acu"], 196.0, places=6)

    def test_no_decided_columns_nan(self):
        from pos.summarise import summarise
        row = summarise([], _result(), _const_meta(4))
        self.assertTrue(math.isnan(row["goodput"]))
        self.assertTrue(math.isnan(row["bytes_per_acu"]))


if __name__ == "__main__":
    unittest.main()
