"""Per-protocol Family C runners: run success + monotone delay sanity (T51)."""
from __future__ import annotations

import unittest

from adversary import config as cfg
from adversary.runners import RUNNERS


def _decided(records):
    return [r for r in records if r.event_type == "decided"]


def _first_latency_ms(records):
    """First decided event's commit time, ms (a coarse cross-run proxy)."""
    dec = _decided(records)
    return min(r.t for r in dec) * 1000.0 if dec else float("nan")


class TestRunSuccess(unittest.TestCase):
    def test_every_protocol_control_finalizes(self):
        # f=0 control at small n finalizes for every protocol.
        for proto, runner in RUNNERS.items():
            records, result, meta = runner(n=7, f=0.0, m=0.0, seed=0)
            self.assertTrue(_decided(records), msg=f"{proto} produced no decisions")
            self.assertEqual(meta.protocol, proto)


class TestMonotoneSanity(unittest.TestCase):
    def test_slow_voters_do_not_speed_up_finality(self):
        # A delay-emission attack cell finalizes no EARLIER than its f=0
        # control at the same (n, seed). (Latency inflates or holds; never
        # improves.) Uses the largest magnitude for a clear signal.
        for proto, runner in RUNNERS.items():
            ctrl, _, _ = runner(n=7, f=0.0, m=0.0, seed=1)
            atk, _, _ = runner(n=7, f=0.30, m=10.0, seed=1)
            c = _first_latency_ms(ctrl)
            a = _first_latency_ms(atk)
            self.assertGreaterEqual(
                a + 1e-6, c,
                msg=f"{proto}: attack {a:.3f}ms < control {c:.3f}ms")


from adversary.runners import OFFLINE_RUNNERS


class TestOfflineRunners(unittest.TestCase):
    def test_control_finalizes_every_protocol(self):
        for proto, runner in OFFLINE_RUNNERS.items():
            records, result, meta = runner(n=7, f=0.0, seed=0)
            self.assertTrue(_decided(records), msg=f"{proto} control empty")
            self.assertEqual(meta.protocol, proto)

    def test_offline_control_matches_honest_baseline_bytewise(self):
        # f=0 offline == f=0 delay (both no-op) at the same (n, seed):
        # same decided count and same first-decision time.
        from adversary.runners import RUNNERS
        for proto in OFFLINE_RUNNERS:
            off, _, _ = OFFLINE_RUNNERS[proto](n=7, f=0.0, seed=3)
            dly, _, _ = RUNNERS[proto](n=7, f=0.0, m=0.0, seed=3)
            self.assertEqual(len(_decided(off)), len(_decided(dly)))
            self.assertEqual(_first_latency_ms(off), _first_latency_ms(dly))

    def test_pbft_above_threshold_stalls(self):
        # n=10, f=0.40 -> 4 offline, 6 honest < 2f+1=7 quorum -> no finality.
        records, result, meta = OFFLINE_RUNNERS["pbft"](n=10, f=0.40, seed=0)
        self.assertFalse(_decided(records),
                         msg="PBFT should stall above the 1/3 quorum threshold")


from adversary.runners import EQUIVOCATE_RUNNERS, run_pbft_equiv
from adversary.select import byzantine_node_ids


def _record_stream(records):
    return [(r.t, r.node_id, r.event_type, r.seq) for r in records]


class TestEquivocateRunners(unittest.TestCase):
    def test_dispatch_table_keys(self):
        self.assertEqual(set(EQUIVOCATE_RUNNERS),
                         {"pbft", "casper-ffg", "snowman"})

    def test_f_zero_has_no_byzantine_node(self):
        # Sanity: f=0 selects no Byzantine ids, so the equiv run is all-honest.
        self.assertEqual(byzantine_node_ids(4, 0.0), ())

    def test_pbft_f_zero_control_finalizes(self):
        # Real scheduler smoke run: honest (f=0) PBFT completes with decisions.
        records, result, meta = run_pbft_equiv(4, 0.0, 0)
        self.assertTrue(records, msg="empty record stream")
        self.assertTrue(_decided(records),
                        msg="f=0 honest PBFT produced no decisions")
        self.assertEqual(meta.protocol, "pbft")

    def test_pbft_equiv_is_deterministic(self):
        # Identical record streams across two runs of the same cell.
        r1, _, _ = run_pbft_equiv(4, 0.0, 0)
        r2, _, _ = run_pbft_equiv(4, 0.0, 0)
        self.assertEqual(_record_stream(r1), _record_stream(r2))


if __name__ == "__main__":
    unittest.main()
