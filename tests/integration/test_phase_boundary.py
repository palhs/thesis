"""Integration: phase boundary crossed mid-broadcast (T25).

Closes T25 review gap I-1. The Network suite pins (NW-5) that phase
parameters are baked at submit time — a Delivery scheduled in phase i
is unaffected by a subsequent advance_phase(i+1). This composes the
contract at multi-node scale: a 7-node broadcast submitted in phase 0
crosses the phase-0 / phase-1 boundary before its deliveries arrive,
and every delivery must still use phase-0 delay parameters.

The cross-module composition seam under test:
  Scheduler dispatch order  +  PhaseAdvance handler  +  Network per-phase
  sampling  -- all three must compose so that the phase pointer advances
  before any same-t delivery, and so that deliveries submitted earlier
  retain their submit-time phase params on dispatch.
"""
import math
import unittest

from network import DelayDist, Phase
from _helpers import BroadcastNode, build_and_run


class TestPhaseBoundaryMidRun(unittest.TestCase):
    def test_phase0_broadcast_delays_unchanged_by_mid_run_rollover(self):
        # Phase 0: constant 10ms delay, ends at t=5. Phase 1: constant 100ms.
        # BroadcastNode broadcasts at t=0 (phase 0 active at submit), so
        # every per-recipient delivery is scheduled at t=0+10=10 -- which
        # is in phase 1. Per NW-5 they retain phase-0 delay (10ms), not
        # phase-1's 100ms.
        phases = (
            Phase(0.0, 5.0, DelayDist("constant", {"delay": 10.0})),
            Phase(5.0, math.inf, DelayDist("constant", {"delay": 100.0})),
        )
        n = 7
        nodes = [BroadcastNode(i, global_seed=42) for i in range(n)]
        result, deliveries, dispatched = build_and_run(nodes, phases, 42)

        self.assertEqual(result.stopped_by, "quiescence")
        # Every delivery uses the phase-0 delay (10.0), proving submit-time
        # baking under multi-node load.
        for (_src, _dst, _type, t_sent, t_delivered) in deliveries:
            self.assertEqual(t_delivered - t_sent, 10.0)

        # Confirm the scenario actually crosses the boundary: PhaseAdvance(1)
        # must fire at t=5, before the first delivery at t=10.
        phase_advances = [(t, nid, seq) for (t, nid, seq, cls) in dispatched
                          if cls == "PhaseAdvance"]
        delivery_events = [(t, nid, seq) for (t, nid, seq, cls) in dispatched
                           if cls == "Delivery"]
        self.assertEqual(len(phase_advances), 1)
        self.assertEqual(phase_advances[0][0], 5.0)
        self.assertEqual(len(delivery_events), n * (n - 1))
        self.assertLess(phase_advances[0][0], delivery_events[0][0])


if __name__ == "__main__":
    unittest.main()
