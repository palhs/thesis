"""Integration: basic message exchange among 4/7/10 nodes (T25).

Drives the scheduler + Node + Network stack with `BroadcastNode`s and checks
that every node reaches every peer, the run reaches quiescence, and a
seed-identical re-run reproduces byte-identically across the *full*
`RunResult` — not just the delivery stream (TASKS.md Backlog, T23-review L1).

Node count is swept 4/7/10: 4 is the minimum BFT committee (`3f+1`, `f=1`),
7 and 10 confirm broadcast fan-out and determinism hold as the validator set
grows. The delay-distribution check (a statistical test, n-independent) lives
in test_delay_distribution.py at a single n.
"""
import math
import unittest

from network import DelayDist, Phase
from _helpers import BroadcastNode, build_and_run

NODE_COUNTS = (4, 7, 10)
_CONSTANT = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 10.0})),)
# Stochastic delay: sample() draws from net_rng, so the seed actually moves
# the output. A constant delay ignores net_rng and could not show that.
_UNIFORM = (Phase(0.0, math.inf, DelayDist("uniform", {"low": 5.0, "high": 50.0})),)


class TestMessageExchange(unittest.TestCase):
    def test_every_node_receives_from_every_peer(self):
        # One broadcast round: each of n nodes sends to the other n-1, so
        # exactly n*(n-1) deliveries and each node's inbound set is every
        # peer id but its own.
        for n in NODE_COUNTS:
            with self.subTest(n=n):
                nodes = [BroadcastNode(i, global_seed=42) for i in range(n)]
                result, deliveries, _ = build_and_run(nodes, _CONSTANT, 42)

                self.assertEqual(result.stopped_by, "quiescence")
                self.assertEqual(result.events_processed, n * (n - 1))
                self.assertEqual(len(deliveries), n * (n - 1))
                for node in nodes:
                    srcs = sorted(src for src, _type in node.received)
                    self.assertEqual(
                        srcs, [i for i in range(n) if i != node.id])
                    self.assertTrue(
                        all(t == "TOKEN" for _s, t in node.received))

    def test_constant_delay_on_every_delivery(self):
        for n in NODE_COUNTS:
            with self.subTest(n=n):
                nodes = [BroadcastNode(i, global_seed=42) for i in range(n)]
                _, deliveries, _ = build_and_run(nodes, _CONSTANT, 42)
                for (_src, _dst, _type, t_sent, t_delivered) in deliveries:
                    self.assertEqual(t_delivered - t_sent, 10.0)

    def test_same_seed_reproduces_full_runresult(self):
        # Determinism contract (network-model-phases.md §6.4) hardened per
        # the T23-review L1 Backlog note: compare the whole RunResult
        # (stopped_by, now, events_processed, events_tombstoned) as well as
        # the delivery stream, not the delivery stream alone.
        for n in NODE_COUNTS:
            with self.subTest(n=n):
                ra, da, _ = build_and_run(
                    [BroadcastNode(i, 42) for i in range(n)], _UNIFORM, 42)
                rb, db, _ = build_and_run(
                    [BroadcastNode(i, 42) for i in range(n)], _UNIFORM, 42)
                self.assertEqual(ra, rb)        # RunResult is a dataclass
                self.assertEqual(da, db)

    def test_different_seeds_diverge(self):
        # The seed knob must move the output: two distinct seeds drive two
        # distinct net_rng streams -> distinct delivery timings.
        for n in NODE_COUNTS:
            with self.subTest(n=n):
                _, da, _ = build_and_run(
                    [BroadcastNode(i, 42) for i in range(n)], _UNIFORM, 42)
                _, db, _ = build_and_run(
                    [BroadcastNode(i, 7) for i in range(n)], _UNIFORM, 7)
                self.assertNotEqual(da, db)


if __name__ == "__main__":
    unittest.main()
