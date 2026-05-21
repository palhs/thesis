"""PBFT view-change recovery path (T29 spec § 7).

Same isolation idiom as `test_node_voting.py`, whose `_node` / `_capturers`
/ `_kickoff` helpers are reused here.
"""
import unittest

from nodes import Message
from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import (
    NewViewPayload,
    PrePreparePayload,
    ViewChangePayload,
)
from pbft import node as pbft_node
from test_node_voting import _node, _capturers, _kickoff


class TestViewChangeTimer(unittest.TestCase):
    def test_arm_uses_per_view_exponential_backoff(self):
        n = _node(0, 4, vc_delay=2.0)
        _, _, timers, _ = _capturers(n)
        n._arm_view_change_timer(view=0, seq=0, t=1.0)
        n._arm_view_change_timer(view=1, seq=0, t=1.0)
        self.assertEqual(timers[0], (("view_change", 0, 0), 2.0, (0, 0), 1.0))
        self.assertEqual(timers[1], (("view_change", 1, 0), 4.0, (1, 0), 1.0))

    def test_cancel_targets_the_instance_timer(self):
        n = _node(0, 4)
        _, _, _, cancels = _capturers(n)
        n._cancel_view_change_timer(0, 2)
        self.assertEqual(cancels, [("view_change", 0, 2)])


class TestViewChangeInitiation(unittest.TestCase):
    def _pre_prepared(self, n, seq=0):
        pp = PrePreparePayload(0, seq, digest(b"A"), b"A")
        n.on_message(Message(src=0, dst=n.id, type="PRE-PREPARE",
                             payload=pp, t_sent=0.0), t=1.0)

    def test_timer_fire_on_stalled_instance_initiates(self):
        n = _node(1, 4, vc_delay=2.0)
        emitted, broadcasts, *_ = _capturers(n); _kickoff(n)
        self._pre_prepared(n)                               # PRE_PREPARED, stalled
        n.on_timer(("view_change", 0, 0), (0, 0), t=9.0)
        self.assertTrue(n.view_changing)
        self.assertIn("VIEW-CHANGE", [b[0] for b in broadcasts])
        self.assertIn(pbft_node.PBFT_VIEW_CHANGE, [e[0] for e in emitted])

    def test_timer_fire_on_committed_instance_is_noop(self):
        n = _node(1, 4)
        _capturers(n); _kickoff(n)
        self._pre_prepared(n)
        n.inst[(0, 0)].state = InstanceState.COMMITTED
        n.on_timer(("view_change", 0, 0), (0, 0), t=9.0)
        self.assertFalse(n.view_changing)

    def test_initiate_is_idempotent(self):
        n = _node(1, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        self._pre_prepared(n)
        n.on_timer(("view_change", 0, 0), (0, 0), t=9.0)
        n.on_timer(("view_change", 0, 0), (0, 0), t=9.1)
        self.assertEqual(sum(1 for b in broadcasts if b[0] == "VIEW-CHANGE"), 1)

    def test_f_plus_one_view_changes_trigger_catch_up(self):
        # n=4, f=1: f+1=2 VIEW-CHANGEs for view 1 make a lagging node join.
        n = _node(2, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        for src in (0, 1):
            vc = ViewChangePayload(new_view=1, last_stable_seq=-1, prepared=[])
            n.on_message(Message(src=src, dst=2, type="VIEW-CHANGE",
                                 payload=vc, t_sent=0.0), t=5.0)
        self.assertTrue(n.view_changing)
        self.assertIn("VIEW-CHANGE", [b[0] for b in broadcasts])


class TestNewView(unittest.TestCase):
    def _vc(self, new_view, prepared=()):
        return ViewChangePayload(new_view=new_view, last_stable_seq=-1,
                                 prepared=list(prepared))

    def test_new_primary_issues_new_view_on_quorum(self):
        # new_view=1 -> primary = node 1. Feed 2f+1=3 VIEW-CHANGEs.
        n = _node(1, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        for src in (0, 2, 3):
            n.on_message(Message(src=src, dst=1, type="VIEW-CHANGE",
                                 payload=self._vc(1), t_sent=0.0), t=5.0)
        self.assertIn("NEW-VIEW", [b[0] for b in broadcasts])
        self.assertEqual(n.view, 1)            # primary self-enters

    def test_new_view_recipient_advances_view(self):
        n = _node(2, 4)
        _capturers(n); _kickoff(n)
        nv = NewViewPayload(new_view=1,
                            vc_proofs=[self._vc(1), self._vc(1), self._vc(1)],
                            reissued=[])
        n.on_message(Message(src=1, dst=2, type="NEW-VIEW",
                             payload=nv, t_sent=0.0), t=6.0)
        self.assertEqual(n.view, 1)
        self.assertFalse(n.view_changing)

    def test_new_view_reissue_installs_and_resumes(self):
        n = _node(2, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        reissued = [PrePreparePayload(1, 0, digest(b"A"), b"A")]
        nv = NewViewPayload(1, [self._vc(1)] * 3, reissued)
        n.on_message(Message(src=1, dst=2, type="NEW-VIEW",
                             payload=nv, t_sent=0.0), t=6.0)
        self.assertIs(n.inst[(1, 0)].state, InstanceState.PRE_PREPARED)
        self.assertIn("PREPARE", [b[0] for b in broadcasts])

    def test_new_view_rejections(self):
        n = _node(2, 4)
        emitted, *_ = _capturers(n); _kickoff(n)
        bad = NewViewPayload(1, [self._vc(1)], [])           # < 2f+1 proofs
        n.on_message(Message(src=1, dst=2, type="NEW-VIEW",
                             payload=bad, t_sent=0.0), t=6.0)
        reasons = [e[1]["reason"] for e in emitted
                   if e[0] == pbft_node.PBFT_REJECTED]
        self.assertIn("insufficient_proofs", reasons)

    def test_propose_quiescent_while_view_changing(self):
        n = _node(0, 4)                        # node 0 is primary view 0
        n.workload = [b"A"]
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        n.view_changing = True
        n._propose(t=1.0)
        self.assertEqual(broadcasts, [])


class TestEscalation(unittest.TestCase):
    def test_initiating_view_change_arms_escalation_timer(self):
        n = _node(1, 4, vc_delay=2.0)
        _, _, timers, _ = _capturers(n); _kickoff(n)
        n._initiate_view_change(1, t=5.0)
        self.assertIn(("vc_escalate", 1),
                      [tid for tid, *_ in timers])

    def test_escalation_fires_when_no_new_view(self):
        n = _node(1, 4)
        _, broadcasts, *_ = _capturers(n); _kickoff(n)
        n._initiate_view_change(1, t=5.0)
        n.on_timer(("vc_escalate", 1), 1, t=99.0)            # NEW-VIEW never came
        self.assertGreaterEqual(n._target_view, 2)

    def test_escalation_noop_after_new_view_installed(self):
        n = _node(1, 4)
        _capturers(n); _kickoff(n)
        n._initiate_view_change(1, t=5.0)
        n._new_view_installed.add(1)
        before = n._target_view
        n.on_timer(("vc_escalate", 1), 1, t=99.0)
        self.assertEqual(n._target_view, before)


if __name__ == "__main__":
    unittest.main()
