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


if __name__ == "__main__":
    unittest.main()
