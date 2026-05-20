"""Integration: scrambled submission still dispatches in (t, node_id, seq).

TASKS.md Backlog (T21-review, "e2e determinism test scope"): the network
e2e determinism test reuses one insertion-ordered scenario, so it shows
"this scenario reproduces", not "the scheduler forces a deterministic
order on unordered input". This test closes that gap.

`TimerNode` submits its timers in a deliberately non-canonical order — the
LATE timer (t=200) before the two EARLY timers (t=100) — and nodes are
*started in reverse id order*. So neither the per-node submission order nor
the cross-node start order matches the canonical `(t, node_id, seq)`
dispatch order. The test asserts dispatch follows the canonical order
anyway, exercising all three tuple components:

  - t        : LATE submitted first per node, dispatched last;
  - node_id  : node n-1 started first, node 0 dispatched first;
  - seq      : early1 / early2 share a fire time, separated only by the
               per-Node seq the scheduler assigns at submission.
"""
import math
import unittest

from network import DelayDist, Phase
from _helpers import TimerNode, build_and_run

NODE_COUNTS = (4, 7, 10)
# Delay is irrelevant here (no messages are sent); a single static phase.
_PHASE = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 10.0})),)


def _canonical_fired(n):
    """Expected `fired` order: t-major, then node_id, then per-Node seq.
    early1 precedes early2 because it is submitted first (lower seq)."""
    expected = []
    for t, tags in ((TimerNode.FIRE_EARLY, ("early1", "early2")),
                    (TimerNode.FIRE_LATE, ("late",))):
        for nid in range(n):
            for tag in tags:
                expected.append((t, nid, tag))
    return expected


class TestDispatchOrdering(unittest.TestCase):
    def test_dispatch_follows_t_node_seq_under_scrambled_submission(self):
        for n in NODE_COUNTS:
            with self.subTest(n=n):
                fired: list = []
                # reverse id order: the scheduler must reorder despite the
                # last-created node starting (and submitting timers) first.
                nodes = [TimerNode(i, fired, global_seed=42)
                         for i in reversed(range(n))]
                result, _, dispatched = build_and_run(nodes, _PHASE, 42)

                self.assertEqual(result.stopped_by, "quiescence")
                self.assertEqual(result.events_processed, 3 * n)
                # the scramble is real: submission began with node n-1's
                # "late", yet dispatch begins with node 0's "early1".
                self.assertEqual(fired[0],
                                 (TimerNode.FIRE_EARLY, 0, "early1"))
                # handlers fire in exactly the canonical order
                self.assertEqual(fired, _canonical_fired(n))

    def test_dispatch_stream_is_strictly_increasing(self):
        # The (t, node_id, seq) key the scheduler pops on must be strictly
        # increasing across the whole run — no ties, no inversions.
        for n in NODE_COUNTS:
            with self.subTest(n=n):
                fired: list = []
                nodes = [TimerNode(i, fired, global_seed=42)
                         for i in reversed(range(n))]
                _, _, dispatched = build_and_run(nodes, _PHASE, 42)

                keys = [(t, nid, seq) for (t, nid, seq, _cls) in dispatched]
                self.assertEqual(len(keys), 3 * n)
                self.assertEqual(keys, sorted(keys))
                self.assertEqual(len(set(keys)), len(keys))   # strict

    def test_handler_order_matches_dispatch_order(self):
        # `fired` (handler-observed) must equal the timer subsequence of the
        # dispatch stream: _dispatch invokes handlers in pop order, no
        # reordering between heap pop and handler entry.
        for n in NODE_COUNTS:
            with self.subTest(n=n):
                fired: list = []
                nodes = [TimerNode(i, fired, global_seed=42)
                         for i in reversed(range(n))]
                _, _, dispatched = build_and_run(nodes, _PHASE, 42)

                self.assertEqual([(t, nid) for (t, nid, _tag) in fired],
                                 [(t, nid) for (t, nid, _s, _c) in dispatched])


if __name__ == "__main__":
    unittest.main()
