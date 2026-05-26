# tests/pbft/test_view_change_timeout.py
"""T31 — PBFT timeouts: the view-change and escalation timers.

Category 3 of the T31 battery (TASKS.md T31: "timeout"). A per-instance
view-change timer is armed when an instance reaches PRE_PREPARED and
cancelled when it commits; if it fires on an unresolved instance the node
initiates a VIEW-CHANGE. A separate escalation timer recovers a lost
NEW-VIEW. This file exercises every timer-fire branch, including the ones
the T29 e2e scenarios deliberately do not reach (T29 spec § 10.3): the
fire on a PREPARED-but-uncommitted instance, on an unknown instance, and
the escalation path.
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
)


_REQ = b"R"


def _pre_prepared(n=4, recipient=1, vc_delay=10.0):
    node = make_node(recipient, n, vc_delay=vc_delay)
    cap = capturers(node)
    kickoff(node)
    node.on_message(pre_prepare(0, 0, 0, _REQ, dst=recipient), t=1.0)
    return node, cap


def _to_prepared(node, n=4, recipient=1):
    for src in others(recipient, n, 2 * f_of(n)):
        node.on_message(prepare(src, 0, 0, _REQ, dst=recipient), t=2.0)


class TestViewChangeTimerArming(unittest.TestCase):
    def test_timer_armed_when_instance_pre_prepared(self):
        _, cap = _pre_prepared()
        self.assertIn(("view_change", 0, 0), cap.timer_ids())

    def test_timer_delay_doubles_per_view(self):
        # Decision F: delay = vc_delay * 2^view.
        node = make_node(1, 4, vc_delay=3.0)
        cap = capturers(node)
        node._arm_view_change_timer(view=0, seq=0, t=0.0)
        node._arm_view_change_timer(view=1, seq=0, t=0.0)
        node._arm_view_change_timer(view=2, seq=0, t=0.0)
        delays = [dl for tid, dl, *_ in cap.timers
                  if tid[0] == "view_change"]
        self.assertEqual(delays, [3.0, 6.0, 12.0])


class TestViewChangeTimerFire(unittest.TestCase):
    """_on_view_change_timeout: fire on an unresolved instance initiates;
    fire on a resolved or unknown instance is a no-op."""

    def test_fire_on_pre_prepared_instance_initiates(self):
        node, cap = _pre_prepared()
        node.on_timer(("view_change", 0, 0), (0, 0), t=20.0)
        self.assertTrue(node.view_changing)
        self.assertEqual(node._target_view, 1)
        self.assertIn("VIEW-CHANGE", cap.broadcast_types())
        self.assertEqual(cap.count(PBFT_VIEW_CHANGE), 1)

    def test_fire_on_prepared_uncommitted_instance_initiates(self):
        # A PREPARED-but-not-COMMITTED instance is still unresolved: the
        # timer must still trigger recovery. Not reached by either T29
        # e2e scenario.
        node, cap = _pre_prepared()
        _to_prepared(node)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.PREPARED)
        node.on_timer(("view_change", 0, 0), (0, 0), t=20.0)
        self.assertTrue(node.view_changing)
        self.assertIn("VIEW-CHANGE", cap.broadcast_types())

    def test_fire_on_committed_instance_is_noop(self):
        node, cap = _pre_prepared()
        _to_prepared(node)
        for src in others(1, 4, 2):
            node.on_message(commit(src, 0, 0, _REQ, dst=1), t=5.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.COMMITTED)
        node.on_timer(("view_change", 0, 0), (0, 0), t=20.0)
        self.assertFalse(node.view_changing)
        self.assertNotIn("VIEW-CHANGE", cap.broadcast_types())

    def test_fire_on_unknown_instance_is_noop(self):
        # Timer fires for a (view, seq) the node never created — e.g. the
        # instance was garbage before the timer event was dispatched.
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        node.on_timer(("view_change", 9, 9), (9, 9), t=20.0)
        self.assertFalse(node.view_changing)
        self.assertEqual(cap.broadcasts, [])

    def test_repeated_fire_initiates_view_change_once(self):
        # Two timer fires for the same instance — the second is idempotent.
        node, cap = _pre_prepared()
        node.on_timer(("view_change", 0, 0), (0, 0), t=20.0)
        node.on_timer(("view_change", 0, 0), (0, 0), t=21.0)
        self.assertEqual(cap.count_broadcast("VIEW-CHANGE"), 1)
        self.assertEqual(cap.count(PBFT_VIEW_CHANGE), 1)


class TestEscalationTimer(unittest.TestCase):
    """If the NEW-VIEW never arrives, the escalation timer climbs to the
    next view — without it a lost NEW-VIEW stalls recovery forever
    (T29 spec § 7.3). Neither T29 e2e scenario delivers a late NEW-VIEW,
    so this path is unit-only."""

    def test_initiating_view_change_arms_escalation_timer(self):
        node = make_node(1, 4, vc_delay=2.0)
        cap = capturers(node)
        kickoff(node)
        node._initiate_view_change(1, t=5.0)
        self.assertIn(("vc_escalate", 1), cap.timer_ids())

    def test_escalation_delay_doubles_with_target_view(self):
        node = make_node(1, 4, vc_delay=2.0)
        cap = capturers(node)
        kickoff(node)
        node._initiate_view_change(1, t=5.0)
        delay = next(dl for tid, dl, *_ in cap.timers
                     if tid == ("vc_escalate", 1))
        self.assertEqual(delay, 2.0 * (2 ** 1))         # vc_delay * 2^new_view

    def test_escalation_fires_when_new_view_missing(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        node._initiate_view_change(1, t=5.0)
        node.on_timer(("vc_escalate", 1), 1, t=200.0)   # NEW-VIEW never came
        self.assertGreaterEqual(node._target_view, 2)
        self.assertEqual(cap.count_broadcast("VIEW-CHANGE"), 2)

    def test_escalation_noop_after_new_view_installed(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        node._initiate_view_change(1, t=5.0)
        node._new_view_installed.add(1)                 # NEW-VIEW arrived
        before = node._target_view
        node.on_timer(("vc_escalate", 1), 1, t=200.0)
        self.assertEqual(node._target_view, before)
        self.assertEqual(cap.count_broadcast("VIEW-CHANGE"), 1)


class TestUnknownTimerIgnored(unittest.TestCase):
    def test_unknown_timer_id_is_silent_noop(self):
        node, cap = _pre_prepared()
        broadcasts_before = len(cap.broadcasts)
        node.on_timer("not-a-real-timer", None, t=20.0)
        self.assertEqual(len(cap.broadcasts), broadcasts_before)


if __name__ == "__main__":
    unittest.main()
