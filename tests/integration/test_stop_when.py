"""Integration: stop_when predicate terminates a multi-node run (T25).

Closes T25 review gap I-6. Every other integration test ends in
stopped_by == "quiescence"; the scheduler's three stop conditions are
OR-composed but only quiescence is integration-pinned. This produces
stopped_by == "predicate" by passing a callback that fires after a
fixed delivery count, before the run would otherwise drain.
"""
import math
import unittest

from nodes import Node
from network import DelayDist, Network, Phase
from scheduler import Delivery, Scheduler

from _helpers import BroadcastNode


class TestStopWhenAtIntegrationScale(unittest.TestCase):
    def test_predicate_terminates_run_before_quiescence(self):
        n = 4
        sched = Scheduler()
        net = Network(sched,
                      (Phase(0.0, math.inf,
                             DelayDist("constant", {"delay": 10.0})),),
                      42)
        nodes = [BroadcastNode(i, global_seed=42) for i in range(n)]
        delivery_count = [0]

        def sink(t, nid, seq, ev):
            if isinstance(ev, Delivery):
                delivery_count[0] += 1

        sched.event_sink = sink
        for node in nodes:
            net.register(node)
        sched.bind_network(net)
        for node in nodes:
            sched.bind(node)
            net.bind(node)
        net.start()
        for node in nodes:
            node.start(0.0)

        # Stop after 5 deliveries dispatched. A full quiescent run would
        # process all n*(n-1)=12 deliveries; the predicate halts well
        # before that.
        result = sched.run(stop_when=lambda: delivery_count[0] >= 5)

        self.assertEqual(result.stopped_by, "predicate")
        self.assertGreaterEqual(delivery_count[0], 5)
        # events_processed counts dispatched events; not all deliveries
        # were dispatched yet.
        self.assertLess(result.events_processed, n * (n - 1))


if __name__ == "__main__":
    unittest.main()
