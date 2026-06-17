"""Unit tests for the PBFT window-denominator fix (src/delay/sweep.py).

The FFG / Snowman reducers divide throughput by `meta.t_max` (set to
WINDOW_S by this harness), so after the clip they report rate over the
window. The PBFT reducer divides by `result.now` (the run horizon), which
on a windowed delay run is W + buffer, not W. `_window_denominator_fix`
re-bases PBFT `tps` / `goodput` onto WINDOW_S so the three protocols share
a comparable throughput axis. It is a no-op for FFG / Snowman.

Pure-function tests over hand-built rows / records — no protocol code.
"""
from __future__ import annotations

import math
import unittest

from event_log import EventRecord
from output.schema import ScenarioMeta

from delay.sweep import _window_denominator_fix


def _decided(t: float, iid) -> EventRecord:
    return EventRecord(t=t, node_id=0, event_type="decided", seq=-1,
                       fields={"instance_id": iid, "value": "v", "t": t})


def _meta(protocol: str, window: float = 480.0) -> ScenarioMeta:
    return ScenarioMeta(run_id=f"{protocol}-n10", protocol=protocol, n=10,
                        variant=None, seed=0, t_max=window,
                        arrival_process="poisson", tx_bytes=512,
                        conflict_rate=0.0, offered_rate=100.0, interval=1.0)


class TestPBFTFix(unittest.TestCase):
    def test_tps_rebased_onto_window(self):
        window = 480.0
        kept = [_decided(float(i), iid=(0, i)) for i in range(48)]
        row = {"tps": 999.0, "goodput": 999.0}   # stale reducer values
        _window_denominator_fix(row, kept, _meta("pbft", window))
        # 48 in-window decided events / 480 s = 0.1 tps.
        self.assertAlmostEqual(row["tps"], 48 / window)

    def test_goodput_rebased_onto_window(self):
        window = 480.0
        kept = [_decided(float(i), iid=(0, i)) for i in range(48)]
        row = {"tps": 0.0, "goodput": 999.0}
        _window_denominator_fix(row, kept, _meta("pbft", window))
        self.assertFalse(math.isnan(row["goodput"]))
        # Sub-saturation goodput tracks offered_rate (100 tx/s) modulo the
        # batch-size variance; it is finite and positive.
        self.assertGreater(row["goodput"], 0.0)

    def test_no_decided_yields_nan(self):
        row = {"tps": 5.0, "goodput": 5.0}
        _window_denominator_fix(row, [], _meta("pbft"))
        self.assertTrue(math.isnan(row["tps"]))
        self.assertTrue(math.isnan(row["goodput"]))


class TestNoOpForOthers(unittest.TestCase):
    def test_ffg_untouched(self):
        kept = [_decided(1.0, iid=1)]
        row = {"tps": 4.125, "goodput": 98.9}
        _window_denominator_fix(row, kept, _meta("casper-ffg"))
        self.assertEqual(row["tps"], 4.125)
        self.assertEqual(row["goodput"], 98.9)

    def test_snowman_untouched(self):
        kept = [_decided(1.0, iid="b0")]
        row = {"tps": 9.75, "goodput": 97.7}
        _window_denominator_fix(row, kept, _meta("snowman"))
        self.assertEqual(row["tps"], 9.75)
        self.assertEqual(row["goodput"], 97.7)


if __name__ == "__main__":
    unittest.main()
