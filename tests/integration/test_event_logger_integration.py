"""Integration: real EventLogger mounted on a 4/7/10-node run (T25).

Closes T25 review gaps L-3 (Module 4) and I-3 (Module 5) — paired close.
Module 4 LT-3 (multi-node byte-identical CSV across seed-identical runs)
also closes here.

The standard integration suite uses a custom inline capture sink
(_helpers.py); this test instead mounts the real EventLogger as
event_sink and asserts:
  - the logger captures the full dispatch stream
  - the logger's (t, node_id, seq) order is strictly increasing (it
    receives events in scheduler-dispatch order, by construction)
  - byte-identical CSV across seed-identical runs at 7 nodes
"""
import math
import tempfile
import unittest
from pathlib import Path

from event_log import EventLogger
from network import DelayDist, Network, Phase
from scheduler import Scheduler

from _helpers import BroadcastNode


def _run_with_real_logger(n, phases, global_seed):
    sched = Scheduler()
    net = Network(sched, tuple(phases), global_seed)
    nodes = [BroadcastNode(i, global_seed=global_seed) for i in range(n)]
    logger = EventLogger()
    for node in nodes:
        net.register(node)
    sched.bind_network(net)
    for node in nodes:
        sched.bind(node)
        net.bind(node)
    sched.event_sink = logger.sink
    net.start()
    for node in nodes:
        node.start(0.0)
    result = sched.run()
    return logger, result


class TestEventLoggerIntegration(unittest.TestCase):
    _CONSTANT = (Phase(0.0, math.inf,
                       DelayDist("constant", {"delay": 10.0})),)
    _UNIFORM = (Phase(0.0, math.inf,
                      DelayDist("uniform", {"low": 5.0, "high": 50.0})),)

    def test_logger_records_full_dispatch_stream_at_4_7_10(self):
        # BroadcastNode emits no decided/halted; single-phase Network
        # arms no PhaseAdvance (no interior boundaries); no timers. So
        # the recorded stream is exactly the n*(n-1) Delivery events.
        for n in (4, 7, 10):
            with self.subTest(n=n):
                logger, result = _run_with_real_logger(
                    n, self._CONSTANT, 42)
                self.assertEqual(result.stopped_by, "quiescence")
                self.assertEqual(len(logger), n * (n - 1))
                self.assertTrue(all(r.event_type == "delivery"
                                    for r in logger.records))

    def test_logger_order_is_strictly_increasing(self):
        # Closes L-3: the logger receives events in scheduler-dispatch
        # order (by construction), so the recorded (t, node_id, seq)
        # tuples are strictly increasing across the whole run. A
        # regression that buffered out of order would break this.
        logger, _ = _run_with_real_logger(7, self._UNIFORM, 42)
        keys = [(r.t, r.node_id, r.seq) for r in logger.records]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(set(keys)), len(keys))   # strict, no ties

    def test_byte_identical_csv_across_seed_identical_runs_at_7_nodes(self):
        # Closes Module 4 LT-3 at n=7. The unit e2e pins this at n=2;
        # this is the integration-scale composition: seed determinism
        # holds end-to-end through (scheduler + network + node + logger).
        with tempfile.TemporaryDirectory() as d:
            la, _ = _run_with_real_logger(7, self._UNIFORM, 42)
            lb, _ = _run_with_real_logger(7, self._UNIFORM, 42)
            a, b = Path(d) / "a.csv", Path(d) / "b.csv"
            la.to_csv(a)
            lb.to_csv(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
