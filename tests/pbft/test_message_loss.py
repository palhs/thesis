# tests/pbft/test_message_loss.py
"""T31 — PBFT under message loss.

Category 4 of the T31 battery (TASKS.md T31: "message loss"). At the unit
level a lost message is simply an on_message call that never happens. Two
regimes are pinned: loss within the 2f+1 quorum's tolerance — up to f
votes lost, the node still commits — and loss past it — the node stalls
at PRE_PREPARED or PREPARED, and the view-change timer is the recovery
path. The PRE-PREPARE-loss case is the sharp edge: a node that never
receives the PRE-PREPARE arms no view-change timer of its own and depends
entirely on the f+1 catch-up from peers.

End-to-end network drop is exercised generically by
tests/integration/test_drop_rate.py; a PBFT-specific drop experiment is a
Backlog item for T47.
"""
import unittest

from pbft.instance import InstanceState
from pbft.node import PBFT_VIEW_CHANGE

from _helpers import (
    capturers,
    commit,
    f_of,
    kickoff,
    make_node,
    others,
    pre_prepare,
    prepare,
    view_change,
)


_REQ = b"R"
_N = (4, 7, 10)        # n = 3f+1: the validator sizes with f = 1, 2, 3


class TestLossWithinTolerance(unittest.TestCase):
    """Losing up to f votes still leaves a 2f+1 quorum. Feeding exactly 2f
    peer votes models dropping the other f = (n-1) - 2f peers."""

    def test_prepares_reach_quorum_with_f_lost(self):
        for n in _N:
            with self.subTest(n=n):
                node = make_node(1, n)
                capturers(node)
                kickoff(node)
                node.on_message(pre_prepare(0, 0, 0, _REQ, dst=1), t=1.0)
                # n-1 peers could PREPARE; only 2f arrive (f dropped).
                for src in others(1, n, 2 * f_of(n)):
                    node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
                self.assertIs(node.inst[(0, 0)].state,
                              InstanceState.PREPARED)

    def test_commits_reach_quorum_with_f_lost(self):
        for n in _N:
            with self.subTest(n=n):
                node = make_node(1, n)
                cap = capturers(node)
                kickoff(node)
                node.on_message(pre_prepare(0, 0, 0, _REQ, dst=1), t=1.0)
                for src in others(1, n, 2 * f_of(n)):
                    node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
                for src in others(1, n, 2 * f_of(n)):
                    node.on_message(commit(src, 0, 0, _REQ, dst=1), t=5.0)
                self.assertIs(node.inst[(0, 0)].state,
                              InstanceState.COMMITTED)
                self.assertEqual(cap.count("decided"), 1)


class TestLossBeyondTolerance(unittest.TestCase):
    """Losing more than f votes drops the count below 2f+1: the node
    stalls, and the view-change timer is the recovery path."""

    def test_stalls_at_pre_prepared_when_a_prepare_is_lost(self):
        for n in _N:
            with self.subTest(n=n):
                node = make_node(1, n)
                cap = capturers(node)
                kickoff(node)
                node.on_message(pre_prepare(0, 0, 0, _REQ, dst=1), t=1.0)
                # one short of quorum: 2f-1 peers -> 2f with the self-vote.
                for src in others(1, n, 2 * f_of(n) - 1):
                    node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
                self.assertIs(node.inst[(0, 0)].state,
                              InstanceState.PRE_PREPARED)
                self.assertEqual(cap.count("decided"), 0)

    def test_stalls_at_prepared_when_a_commit_is_lost(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        node.on_message(pre_prepare(0, 0, 0, _REQ, dst=1), t=1.0)
        for src in others(1, 4, 2):
            node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.PREPARED)
        node.on_message(commit(2, 0, 0, _REQ, dst=1), t=5.0)    # 2f only
        self.assertIs(node.inst[(0, 0)].state, InstanceState.PREPARED)
        self.assertEqual(cap.count("decided"), 0)

    def test_view_change_timer_recovers_a_stalled_instance(self):
        # The instance stalls one vote short; the timer armed at
        # PRE_PREPARED fires and initiates recovery.
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        node.on_message(pre_prepare(0, 0, 0, _REQ, dst=1), t=1.0)
        node.on_message(prepare(2, 0, 0, _REQ, dst=1), t=2.0)   # 2f, stalled
        self.assertIs(node.inst[(0, 0)].state, InstanceState.PRE_PREPARED)
        node.on_timer(("view_change", 0, 0), (0, 0), t=99.0)
        self.assertTrue(node.view_changing)
        self.assertEqual(cap.count(PBFT_VIEW_CHANGE), 1)


class TestPrePrepareLoss(unittest.TestCase):
    """The PRE-PREPARE itself is lost. The node never reaches PRE_PREPARED,
    so it arms no view-change timer and never self-initiates recovery — it
    can only join via the f+1 catch-up from peers."""

    def test_votes_buffer_but_instance_stays_idle(self):
        node = make_node(1, 4)
        capturers(node)
        kickoff(node)
        # PREPAREs arrive; the PRE-PREPARE never does.
        for src in (0, 2, 3):
            node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
        inst = node.inst[(0, 0)]
        self.assertIs(inst.state, InstanceState.IDLE)
        self.assertEqual(inst.matching_prepares(), 0)   # digest unknown
        self.assertEqual(len(inst.prepares), 3)         # but buffered

    def test_no_view_change_timer_armed_without_pre_prepare(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        for src in (0, 2, 3):
            node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
        self.assertNotIn(("view_change", 0, 0), cap.timer_ids())

    def test_node_joins_view_change_via_f_plus_one_catch_up(self):
        # n=4, f=1: f+1 = 2 VIEW-CHANGEs for view 1 pull a node that never
        # saw the PRE-PREPARE into the view-change anyway.
        node = make_node(2, 4)
        cap = capturers(node)
        kickoff(node)
        for src in (0, 1):
            node.on_message(view_change(src, 1, dst=2), t=5.0)
        self.assertTrue(node.view_changing)
        self.assertIn("VIEW-CHANGE", cap.broadcast_types())


if __name__ == "__main__":
    unittest.main()
