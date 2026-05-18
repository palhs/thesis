"""End-to-end: the Scheduler drives Nodes through the six-phase bootstrap.

Exercises node-model.md lifecycle + the simulation-design.md §7.2 bootstrap
and the determinism contract (node-model.md §8).
"""
import unittest

from scheduler import Scheduler
from _helpers import LoopbackNetwork, PingPongNode


def _run(global_seed, budget=4):
    sched = Scheduler()
    net = LoopbackNetwork(sched)
    # Node 0's opening PING is not counted as one of its own hops, so node 1
    # is always one hop ahead and reaches `budget` first: it emits decided +
    # halted and stops replying, the exchange winds down to quiescence, and
    # node 0 ends un-halted at budget-1 hops. Exactly one node completes a
    # full decided->halted lifecycle -- sufficient for build verification;
    # per-node halt/decide paths are unit-tested in test_node.py.
    nodes = [
        PingPongNode(0, peer_id=1, budget=budget, global_seed=global_seed),
        PingPongNode(1, peer_id=0, budget=budget, global_seed=global_seed),
    ]
    capture: list = []
    sched.event_sink = lambda t, nid, seq, ev: capture.append(
        (t, nid, seq, repr(ev)))
    for n in nodes:                       # phase 2: register
        net.register(n)
    for n in nodes:                       # phase 3: split bind
        sched.bind(n)
        net.bind(n)
    for n in nodes:                       # phase 5: kickoff
        n.start(0.0)
    result = sched.run()                  # phase 6
    return result, capture


class TestNodeE2E(unittest.TestCase):
    def test_run_reaches_quiescence(self):
        result, _ = _run(global_seed=42)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_decided_and_halted_events_emitted(self):
        _, capture = _run(global_seed=42)
        kinds = [ev for (_, _, _, ev) in capture]
        self.assertTrue(any("'decided'" in k for k in kinds))
        self.assertTrue(any("'halted'" in k for k in kinds))

    def test_two_seed_identical_runs_are_byte_identical(self):
        _, cap_a = _run(global_seed=42)
        _, cap_b = _run(global_seed=42)
        self.assertEqual(cap_a, cap_b)


if __name__ == "__main__":
    unittest.main()
