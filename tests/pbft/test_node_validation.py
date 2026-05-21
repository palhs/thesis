# tests/pbft/test_node_validation.py
"""Recipient validation of PRE-PREPARE (T28 spec § 7.4).

Each test instantiates one PBFTNode in isolation, hand-builds a Message,
stubs the bind-time outbound API (broadcast / set_timer / emit) with
capturers, and calls node.on_message directly. The five rejection rules
are exercised one-per-test plus the happy path.

Lifecycle: Node.on_message refuses CREATED nodes (src/nodes/node.py),
so every test calls _kickoff(node) to walk through start() -> RUNNING
without running the real propose path.
"""
import unittest
from typing import Any

from nodes import Message
from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import PrePreparePayload
from pbft.node import PBFT_PRE_PREPARED, PBFT_REJECTED, PBFTNode


def _node(node_id: int, n: int, *, view=0) -> PBFTNode:
    return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                    global_seed=42, n=n, workload=None,
                    propose_delay=1.0, initial_view=view)


def _install_capturers(node: PBFTNode):
    """Replace bind-time placeholders with capturers, returning the lists
    each captures into. Tests assert against these lists."""
    emitted: list[tuple[str, dict, float]] = []
    broadcasts: list[tuple[str, object, float]] = []
    sends: list[tuple[int, str, object, float]] = []
    timers: list[tuple[Any, float, object, float]] = []
    node.emit = lambda et, fields, t: emitted.append((et, fields, t))
    node.broadcast = lambda type, payload, t: broadcasts.append(
        (type, payload, t))
    node.send = lambda dst, type, payload, t: sends.append(
        (dst, type, payload, t))
    node.set_timer = lambda tid, delay, payload, t: timers.append(
        (tid, delay, payload, t))
    return emitted, broadcasts, sends, timers


def _kickoff(node: PBFTNode):
    """Force RUNNING without firing the real propose path. The Node ABC
    forbids on_message in CREATED; this is the minimum incantation."""
    from nodes.lifecycle import Lifecycle
    node.status = Lifecycle.RUNNING


def _pre_prepare_msg(src: int, view: int, seq: int, batch: bytes,
                     digest_override: bytes | None = None) -> Message:
    d = digest_override if digest_override is not None else digest(batch)
    pp = PrePreparePayload(view=view, seq=seq,
                           request_digest=d, request_payload=batch)
    return Message(src=src, dst=1, type="PRE-PREPARE", payload=pp,
                   t_sent=0.0)


# --- Happy path -----------------------------------------------------------

class TestHappyPath(unittest.TestCase):
    def test_valid_pre_prepare_transitions_idle_to_pre_prepared(self):
        node = _node(node_id=1, n=4)        # primary in view 0 is node 0
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"A")
        node.on_message(msg, t=5.0)

        inst = node.inst[(0, 0)]
        self.assertIs(inst.state, InstanceState.PRE_PREPARED)
        self.assertEqual(inst.digest, digest(b"A"))
        # One pbft_pre_prepared event, zero rejections.
        kinds = [e[0] for e in emitted]
        self.assertIn(PBFT_PRE_PREPARED, kinds)
        self.assertNotIn(PBFT_REJECTED, kinds)


# --- Rule 1: sender is the primary for the asserted view -----------------

class TestRule1NonPrimarySender(unittest.TestCase):
    def test_non_primary_sender_rejects(self):
        # In view 0 the primary is node 0; node 2 spoofing a PRE-PREPARE
        # must be rejected.
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = _pre_prepare_msg(src=2, view=0, seq=0, batch=b"A")
        node.on_message(msg, t=5.0)

        self.assertNotIn((0, 0), node.inst)
        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "non_primary_sender")


# --- Rule 2: view matches recipient's current view -----------------------

class TestRule2ViewMismatch(unittest.TestCase):
    def test_future_view_rejects(self):
        # Recipient is in view 0; primary for view 1 (node 1) sends a
        # PRE-PREPARE asserting view 1. The recipient drops it.
        node = _node(node_id=2, n=4, view=0)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = _pre_prepare_msg(src=1, view=1, seq=0, batch=b"A")
        node.on_message(msg, t=5.0)

        self.assertNotIn((1, 0), node.inst)
        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "view_mismatch")


# --- Rule 3: not view-changing ------------------------------------------

class TestRule3ViewChanging(unittest.TestCase):
    def test_view_changing_blocks_pre_prepare(self):
        # T29 will set view_changing; we set it by hand to exercise the
        # branch in T28.
        node = _node(node_id=1, n=4)
        node.view_changing = True
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"A")
        node.on_message(msg, t=5.0)

        self.assertNotIn((0, 0), node.inst)
        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "view_changing")


# --- Rule 4: not already advanced past IDLE for (view, seq) -------------

class TestRule4DuplicatePrePrepare(unittest.TestCase):
    def test_second_pre_prepare_for_same_view_seq_rejects(self):
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        first = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"A")
        node.on_message(first, t=5.0)
        # First call accepted (covered by TestHappyPath); reset emitted to
        # isolate the second one's effect.
        emitted.clear()

        # A second PRE-PREPARE for (0, 0), even with the same batch, is
        # a duplicate at this instance and must be dropped. Equivocation
        # (a different batch) is a stronger form of the same reject.
        second = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"B")
        node.on_message(second, t=6.0)

        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "duplicate_pre_prepare")
        # Instance state stays at the first PRE-PREPARE's digest.
        self.assertEqual(node.inst[(0, 0)].digest, digest(b"A"))


# --- Rule 5: digest integrity --------------------------------------------

class TestRule5DigestMismatch(unittest.TestCase):
    def test_payload_does_not_match_declared_digest(self):
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        # Honest digest is digest(b"A"); inject digest(b"B").
        msg = _pre_prepare_msg(src=0, view=0, seq=0, batch=b"A",
                               digest_override=digest(b"B"))
        node.on_message(msg, t=5.0)

        self.assertNotIn((0, 0), node.inst)
        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "digest_mismatch")


# --- Unknown-type rejection + malformed voting-payload rejection --------

class TestOnMessageDispatch(unittest.TestCase):
    def test_voting_types_reject_malformed_payload(self):
        # T29 wired PREPARE/COMMIT/VIEW-CHANGE/NEW-VIEW. A payload=None
        # envelope of any of those types is now rejected with
        # reason="malformed_payload" (the payload-shape guard, spec § 6.2),
        # not silently dropped as in the T28 skeleton — T18 will inject
        # malformed envelopes of exactly these types.
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        types = ("PREPARE", "COMMIT", "VIEW-CHANGE", "NEW-VIEW")
        for typ in types:
            msg = Message(src=0, dst=1, type=typ, payload=None, t_sent=0.0)
            node.on_message(msg, t=5.0)

        self.assertEqual(len(emitted), 4)
        for (event, fields, _), typ in zip(emitted, types):
            self.assertEqual(event, PBFT_REJECTED)
            self.assertEqual(fields["reason"], "malformed_payload")
            self.assertEqual(fields["msg_type"], typ)

    def test_unknown_type_rejects(self):
        node = _node(node_id=1, n=4)
        emitted, *_ = _install_capturers(node)
        _kickoff(node)

        msg = Message(src=0, dst=1, type="PING", payload=None, t_sent=0.0)
        node.on_message(msg, t=5.0)

        rejections = [e for e in emitted if e[0] == PBFT_REJECTED]
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0][1]["reason"], "unknown_type")


if __name__ == "__main__":
    unittest.main()
