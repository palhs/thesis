"""Integration: a node halting mid-run drops subsequent inbound (T25).

Closes T25 review gap I-5. The 2-node PingPongNode e2e exercises a
mid-run halt, and the unit-level N-1 (test_halt_from_created_skips_running)
pins the never-started case; this is the multi-node case where node k
halts while the rest of an n = 7 broadcast is still in flight.

The HALTED-while-inbound-pending drop path (node-model.md §3) is the
contract under test: an inbound delivered to a node that has already
transitioned to HALTED at dispatch time is dropped silently by
Node.on_message's status guard.
"""
import math
import unittest

from nodes import HaltReason, Lifecycle
from network import DelayDist, Phase
from _helpers import BroadcastNode, build_and_run


class HaltOnFirstInboundNode(BroadcastNode):
    """A BroadcastNode that crashes itself after its first inbound is
    handled. Constructed identically to BroadcastNode so the existing
    helper bootstrap works unchanged."""

    def _on_message(self, msg, t):
        # Run the normal handler first so this inbound is recorded; the
        # halt guard in on_message will short-circuit subsequent inbounds.
        super()._on_message(msg, t)
        if self.status is Lifecycle.RUNNING:
            self.halt(HaltReason.CRASHED, t)


class TestHaltMidRun(unittest.TestCase):
    def test_halted_node_drops_remaining_same_t_inbounds(self):
        n = 7
        # Constant delay = every same-source delivery to node 0 lands at
        # the same t (= t_sent + 10). The first dispatch handles the
        # message and halts; the remaining same-t inbounds dispatch with
        # later seq and are dropped by the HALTED status guard.
        phases = (Phase(0.0, math.inf,
                        DelayDist("constant", {"delay": 10.0})),)
        nodes = ([HaltOnFirstInboundNode(0, global_seed=42)]
                 + [BroadcastNode(i, global_seed=42)
                    for i in range(1, n)])
        result, deliveries, _ = build_and_run(nodes, phases, 42)

        self.assertEqual(result.stopped_by, "quiescence")
        # node 0 recorded exactly 1 inbound (the rest were dropped by the
        # HALTED guard before _on_message ran).
        self.assertEqual(len(nodes[0].received), 1)
        self.assertIs(nodes[0].status, Lifecycle.HALTED)
        # All n-1 other nodes still received from every peer including
        # node 0 (whose broadcast was sent at t=0, before the halt).
        for node in nodes[1:]:
            srcs = sorted(src for src, _t in node.received)
            self.assertEqual(srcs, [i for i in range(n) if i != node.id])
        # All n*(n-1) deliveries were dispatched -- halt suppresses the
        # handler, not the dispatch itself.
        self.assertEqual(len(deliveries), n * (n - 1))


if __name__ == "__main__":
    unittest.main()
