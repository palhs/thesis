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


def _pbft_instance_records(n: int, t_commit: float = 0.4,
                           t_final: float | None = None
                           ) -> list[EventRecord]:
    """n decided events at t_commit for instance_id=(0, 0), plus a single
    `pbft_client_finalized` (T70 finding #1) at `t_final` (default one hop
    past commit) emitted by the collector for the same seq.

    Pass `t_final=None` AND drop the finalize via `_no_finalize=True`-style
    callers is not supported here; use `_pbft_records_no_finalize` for the
    degenerate fallback path."""
    if t_final is None:
        t_final = t_commit * 1.5            # one network hop past the commit
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
    # The view-0 collector (node 0) finalizes seq 0 one hop later.
    recs.append(EventRecord(t=t_final, node_id=0,
                            event_type="pbft_client_finalized", seq=0,
                            fields={"seq": 0, "view": 0, "t": t_final}))
    return recs


def _pbft_records_no_finalize(n: int, t_commit: float = 0.4
                              ) -> list[EventRecord]:
    """Decided events only, no `pbft_client_finalized` — the degenerate
    fallback path where finality collapses back onto commit."""
    return [r for r in _pbft_instance_records(n, t_commit)
            if r.event_type != "pbft_client_finalized"]


class TestSummarise(unittest.TestCase):
    def test_keys_are_protocol_columns_only(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _meta(4))
        expected_keys = {
            "commit_latency_ms", "finality_latency_ms", "tps", "goodput",
            "consensus_msgs_per_acu", "bytes_per_acu",
            "success_rate", "fork_rate",
            "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
        }
        self.assertEqual(set(row.keys()), expected_keys)

    def test_commit_measured_at_quorum(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4, t_commit=0.4),
                        _result(), _meta(4))
        # commit_latency stays at the 2f+1 COMMIT quorum time (0.4 s).
        self.assertAlmostEqual(row["commit_latency_ms"], 400.0,
                               places=6)

    def test_finality_strictly_greater_than_commit(self):
        # T70 finding #1: client-observed finality is one hop past the COMMIT
        # quorum. With a finalize at t=0.6 vs commit at t=0.4, finality > commit.
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4, t_commit=0.4, t_final=0.6),
                        _result(), _meta(4))
        self.assertAlmostEqual(row["commit_latency_ms"], 400.0, places=6)
        self.assertAlmostEqual(row["finality_latency_ms"], 600.0, places=6)
        self.assertGreater(row["finality_latency_ms"],
                           row["commit_latency_ms"])

    def test_finality_falls_back_to_commit_without_finalize(self):
        # Degenerate: a run that decided but logged no client-finalize keeps
        # finality == commit so the row is still summarisable.
        from pbft.summarise import summarise
        row = summarise(_pbft_records_no_finalize(4, t_commit=0.4),
                        _result(), _meta(4))
        self.assertEqual(row["commit_latency_ms"],
                         row["finality_latency_ms"])

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


def _const_meta(n: int = 4, offered_rate: float = 10.0) -> ScenarioMeta:
    """Constant arrival so batch sizes are exact integers."""
    return ScenarioMeta(run_id=f"pbft-n{n}", protocol="pbft", n=n,
                        variant=None, seed=42, t_max=math.nan,
                        arrival_process="constant",
                        offered_rate=offered_rate, tx_bytes=512,
                        conflict_rate=0.0, interval=1.0)


class TestWorkloadColumns(unittest.TestCase):
    def test_goodput_is_float(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _const_meta(4))
        self.assertIsInstance(row["goodput"], float)
        self.assertIsInstance(row["bytes_per_acu"], float)

    def test_goodput_exact_value(self):
        # One distinct decided instance ((0,0)) -> n_opportunities=1.
        # constant offered_rate=10, interval=1.0 -> 10 committed tx.
        # result.now=0.5 -> goodput = 10 / 0.5 = 20.0.
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _const_meta(4))
        self.assertAlmostEqual(row["goodput"], 20.0, places=6)

    def test_bytes_per_acu_exact_value(self):
        # 4 PRE-PREPARE deliveries (tx-carrying), 4 decided events.
        # base PRE-PREPARE = 8+8+32 = 48; tx component = 10*1.0*512 = 5120.
        # per delivery = 48 + 5120 = 5168; total = 4*5168; /4 decided.
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _const_meta(4))
        self.assertAlmostEqual(row["bytes_per_acu"], 5168.0, places=6)

    def test_no_decided_bytes_per_acu_nan(self):
        from pbft.summarise import summarise
        row = summarise([], _result(), _const_meta(4))
        self.assertTrue(math.isnan(row["bytes_per_acu"]))
        self.assertTrue(math.isnan(row["goodput"]))


if __name__ == "__main__":
    unittest.main()
