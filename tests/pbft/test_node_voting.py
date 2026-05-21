"""PBFT prepare/commit voting phases (T29 spec § 6).

Same idiom as `test_node_validation.py`: one PBFTNode in isolation, the
bind-time outbound API replaced with capturers, `_kickoff` to RUNNING,
hand-built Messages, direct `on_message` / `on_timer` calls.
"""
import unittest
from typing import Any

from nodes import Message
from nodes.lifecycle import Lifecycle
from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import PreparePayload, CommitPayload, PrePreparePayload
from pbft import node as pbft_node
from pbft.node import PBFTNode


def _node(node_id, n, *, view=0, vc_delay=10.0):
    return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                    global_seed=42, n=n, workload=None,
                    propose_delay=1.0, initial_view=view, vc_delay=vc_delay)


def _capturers(node):
    emitted, broadcasts, timers, cancels = [], [], [], []
    node.emit = lambda et, f, t: emitted.append((et, f, t))
    node.broadcast = lambda ty, p, t: broadcasts.append((ty, p, t))
    node.send = lambda d, ty, p, t: None
    node.set_timer = lambda tid, dl, p, t: timers.append((tid, dl, p, t))
    node.cancel_timer = lambda tid: cancels.append(tid)
    return emitted, broadcasts, timers, cancels


def _kickoff(node):
    node.status = Lifecycle.RUNNING


def _pre_prepare(src, view, seq, batch):
    pp = PrePreparePayload(view=view, seq=seq,
                           request_digest=digest(batch), request_payload=batch)
    return Message(src=src, dst=1, type="PRE-PREPARE", payload=pp, t_sent=0.0)


def _prepare(src, view, seq, batch):
    pp = PreparePayload(view=view, seq=seq, request_digest=digest(batch))
    return Message(src=src, dst=1, type="PREPARE", payload=pp, t_sent=0.0)


class TestConstructor(unittest.TestCase):
    def test_vc_delay_stored_and_validated(self):
        self.assertEqual(_node(0, 4, vc_delay=2.5).vc_delay, 2.5)
        with self.assertRaises(ValueError):
            _node(0, 4, vc_delay=0.0)

    def test_view_change_state_initialised(self):
        n = _node(1, 4)
        self.assertEqual(n._view_changes, {})
        self.assertEqual(n._decided_seqs, set())

    def test_event_constants_exist(self):
        for name in ("PBFT_PREPARED", "PBFT_COMMITTED",
                     "PBFT_VIEW_CHANGE", "PBFT_NEW_VIEW"):
            self.assertTrue(hasattr(pbft_node, name))


class TestPreparePhase(unittest.TestCase):
    def test_pre_prepared_broadcasts_prepare_and_self_records(self):
        n = _node(1, 4)                       # primary view0 = node0
        emitted, broadcasts, timers, _ = _capturers(n)
        _kickoff(n)
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=5.0)
        kinds = [b[0] for b in broadcasts]
        self.assertIn("PREPARE", kinds)
        self.assertEqual(n.inst[(0, 0)].prepares[1], digest(b"A"))
        self.assertTrue(any(tid[0] == "view_change" for tid, *_ in timers))

    def test_quorum_of_prepares_transitions_to_prepared(self):
        n = _node(1, 4)                       # f=1, 2f+1=3
        emitted, broadcasts, *_ = _capturers(n)
        _kickoff(n)
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=5.0)   # self-prepare = 1
        n.on_message(_prepare(2, 0, 0, b"A"), t=5.1)       # = 2
        self.assertIs(n.inst[(0, 0)].state, InstanceState.PRE_PREPARED)
        n.on_message(_prepare(3, 0, 0, b"A"), t=5.2)       # = 3 -> PREPARED
        self.assertIs(n.inst[(0, 0)].state, InstanceState.PREPARED)
        self.assertIn("COMMIT", [b[0] for b in broadcasts])
        self.assertIn(pbft_node.PBFT_PREPARED, [e[0] for e in emitted])

    def test_prepare_before_pre_prepare_is_buffered(self):
        n = _node(1, 4)
        _capturers(n); _kickoff(n)
        n.on_message(_prepare(2, 0, 0, b"A"), t=5.0)        # arrives early
        n.on_message(_prepare(3, 0, 0, b"A"), t=5.1)
        self.assertIs(n.inst[(0, 0)].state, InstanceState.IDLE)
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=5.2)    # now digest known
        self.assertIs(n.inst[(0, 0)].state, InstanceState.PREPARED)

    def test_digest_mismatched_prepare_does_not_count(self):
        n = _node(1, 4)
        _capturers(n); _kickoff(n)
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=5.0)
        n.on_message(_prepare(2, 0, 0, b"B"), t=5.1)        # wrong digest
        n.on_message(_prepare(3, 0, 0, b"B"), t=5.2)
        self.assertIs(n.inst[(0, 0)].state, InstanceState.PRE_PREPARED)

    def test_malformed_prepare_payload_rejected(self):
        n = _node(1, 4)
        emitted, *_ = _capturers(n); _kickoff(n)
        n.on_message(Message(src=2, dst=1, type="PREPARE",
                             payload=None, t_sent=0.0), t=5.0)
        self.assertEqual([e for e in emitted if e[0] == pbft_node.PBFT_REJECTED]
                         [0][1]["reason"], "malformed_payload")


def _commit(src, view, seq, batch):
    cp = CommitPayload(view=view, seq=seq, request_digest=digest(batch))
    return Message(src=src, dst=1, type="COMMIT", payload=cp, t_sent=0.0)


class TestCommitPhase(unittest.TestCase):
    def _drive_to_prepared(self, n):
        n.on_message(_pre_prepare(0, 0, 0, b"A"), t=1.0)
        n.on_message(_prepare(2, 0, 0, b"A"), t=1.1)
        n.on_message(_prepare(3, 0, 0, b"A"), t=1.2)        # -> PREPARED, self-commit

    def test_quorum_of_commits_finalizes(self):
        n = _node(1, 4)
        emitted, _, _, cancels = _capturers(n); _kickoff(n)
        self._drive_to_prepared(n)                          # self-commit = 1
        n.on_message(_commit(2, 0, 0, b"A"), t=1.3)         # = 2
        n.on_message(_commit(3, 0, 0, b"A"), t=1.4)         # = 3 -> COMMITTED
        self.assertIs(n.inst[(0, 0)].state, InstanceState.COMMITTED)
        kinds = [e[0] for e in emitted]
        self.assertIn(pbft_node.PBFT_COMMITTED, kinds)
        self.assertIn("decided", kinds)
        self.assertIn(("view_change", 0, 0), cancels)

    def test_decided_value_is_request_digest(self):
        n = _node(1, 4)
        emitted, *_ = _capturers(n); _kickoff(n)
        self._drive_to_prepared(n)
        n.on_message(_commit(2, 0, 0, b"A"), t=1.3)
        n.on_message(_commit(3, 0, 0, b"A"), t=1.4)
        dec = [e for e in emitted if e[0] == "decided"][0]
        self.assertEqual(dec[1]["value"], digest(b"A").hex())
        self.assertEqual(dec[1]["instance_id"], (0, 0))

    def test_decided_emitted_once_per_seq(self):
        # An extra COMMIT after COMMITTED must not re-emit decided.
        n = _node(1, 4)
        emitted, *_ = _capturers(n); _kickoff(n)
        self._drive_to_prepared(n)
        n.on_message(_commit(2, 0, 0, b"A"), t=1.3)
        n.on_message(_commit(3, 0, 0, b"A"), t=1.4)
        n.on_message(_commit(0, 0, 0, b"A"), t=1.5)
        self.assertEqual(sum(1 for e in emitted if e[0] == "decided"), 1)


if __name__ == "__main__":
    unittest.main()
