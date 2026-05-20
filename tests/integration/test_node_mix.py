"""Integration: heterogeneous BroadcastNode + TimerNode mix (T25).

Closes T25 review gap I-7. The existing tests exercise BroadcastNode
and TimerNode in separate runs; this composes them into one run so
Delivery and TimerFire events coexist on the heap and the scheduler's
mixed-class (t, node_id, seq) tie-break (ST-4) is re-pinned under
multi-node load.
"""
import math
import unittest

from network import DelayDist, Phase
from _helpers import BroadcastNode, TimerNode, build_and_run


class TestHeterogeneousNodeMix(unittest.TestCase):
    def test_mixed_broadcast_and_timer_nodes_dispatch_in_canonical_order(self):
        n_broadcast = 4
        n_timer = 4
        broadcasters = [BroadcastNode(i, global_seed=42)
                        for i in range(n_broadcast)]
        fired: list = []
        timers = [TimerNode(n_broadcast + i, fired, global_seed=42)
                  for i in range(n_timer)]
        nodes = broadcasters + timers
        # Constant 10ms delay: broadcaster deliveries arrive at t=10.
        # TimerNode arms timers firing at t=100 (early) and t=200 (late).
        # Mixed event classes appear in the dispatch stream.
        phases = (Phase(0.0, math.inf,
                        DelayDist("constant", {"delay": 10.0})),)
        result, deliveries, dispatched = build_and_run(nodes, phases, 42)

        self.assertEqual(result.stopped_by, "quiescence")

        # Broadcaster deliveries: 4*3 = 12 within the broadcast group;
        # broadcasters also send to timers (registered peers), so total
        # is n*(n-1) = 8*7 = 56. Timer nodes don't broadcast, so the
        # timer-to-broadcaster edge is absent.
        # Actually broadcasters call broadcast() which fans out to ALL
        # registered peers minus self; so each broadcaster sends n-1=7
        # deliveries; 4 broadcasters * 7 = 28 deliveries.
        self.assertEqual(len(deliveries), n_broadcast * (n_broadcast + n_timer - 1))

        # Dispatch keys strictly increasing in (t, node_id, seq).
        keys = [(t, nid, seq) for (t, nid, seq, _cls) in dispatched]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(set(keys)), len(keys))

        # Both event classes appear in the dispatch stream.
        classes = {cls for (_t, _nid, _seq, cls) in dispatched}
        self.assertIn("Delivery", classes)
        self.assertIn("TimerFire", classes)


if __name__ == "__main__":
    unittest.main()
