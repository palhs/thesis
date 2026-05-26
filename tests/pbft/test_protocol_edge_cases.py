# tests/pbft/test_protocol_edge_cases.py
"""T31 — PBFT protocol edge cases.

Cross-cutting edges that do not fall under one of the five named T31
categories but must not regress when later tasks touch PBFT (T39
stabilization, T51-T54 adversarial): malformed PRE-PREPARE payloads, the
NEW-VIEW rejection branches the T29 suite left untested, a corrupt
reissued PRE-PREPARE inside an otherwise-valid NEW-VIEW, non-zero initial
views, the demoted-primary propose guard, and fully out-of-order delivery.
"""
import unittest

from nodes import Message
from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import PrePreparePayload, ViewChangePayload
from pbft.node import PBFT_REJECTED

from _helpers import (
    capturers,
    commit,
    kickoff,
    make_node,
    new_view,
    others,
    pre_prepare,
    prepare,
    vc_proofs,
)


_REQ = b"R"


def _reasons(cap):
    return [e[1]["reason"] for e in cap.events(PBFT_REJECTED)]


class TestMalformedPrePreparePayload(unittest.TestCase):
    """A PRE-PREPARE carrying a non-PrePreparePayload is logged-and-dropped,
    not crashed on (T29 spec § 6.2 — T18 will inject exactly these). The
    T29 suite covered the malformed PREPARE/COMMIT/VIEW-CHANGE/NEW-VIEW
    guards but not the PRE-PREPARE one."""

    def test_none_payload_rejected(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        node.on_message(Message(src=0, dst=1, type="PRE-PREPARE",
                                payload=None, t_sent=0.0), t=1.0)
        self.assertIn("malformed_payload", _reasons(cap))
        self.assertNotIn((0, 0), node.inst)

    def test_wrong_dataclass_payload_rejected(self):
        # A ViewChangePayload object inside a PRE-PREPARE envelope.
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        bad = ViewChangePayload(new_view=1, last_stable_seq=-1, prepared=[])
        node.on_message(Message(src=0, dst=1, type="PRE-PREPARE",
                                payload=bad, t_sent=0.0), t=1.0)
        self.assertIn("malformed_payload", _reasons(cap))


class TestNewViewRejections(unittest.TestCase):
    """The NEW-VIEW validation branches the T29 suite did not cover — its
    test_node_viewchange exercised only `insufficient_proofs`."""

    def test_non_primary_sender_rejected(self):
        # A NEW-VIEW for view 1 must come from node 1 (1 % 4); node 3 spoofs.
        node = make_node(2, 4)
        cap = capturers(node)
        kickoff(node)
        node.on_message(new_view(3, 1, dst=2, vc_proofs=vc_proofs(4, 1)),
                        t=5.0)
        self.assertIn("non_primary_sender", _reasons(cap))
        self.assertEqual(node.view, 0)

    def test_stale_new_view_rejected(self):
        # Recipient already in view 2; a NEW-VIEW for view 1 is stale.
        node = make_node(2, 4, view=2)
        cap = capturers(node)
        kickoff(node)
        # primary of view 1 is node 1.
        node.on_message(new_view(1, 1, dst=2, vc_proofs=vc_proofs(4, 1)),
                        t=5.0)
        self.assertIn("stale_new_view", _reasons(cap))
        self.assertEqual(node.view, 2)

    def test_proof_for_wrong_view_rejected(self):
        # Enough proofs by count, but one asserts a different new_view.
        node = make_node(2, 4)
        cap = capturers(node)
        kickoff(node)
        proofs = [ViewChangePayload(1, -1, []),
                  ViewChangePayload(1, -1, []),
                  ViewChangePayload(2, -1, [])]      # wrong new_view
        node.on_message(new_view(1, 1, dst=2, vc_proofs=proofs), t=5.0)
        self.assertIn("insufficient_proofs", _reasons(cap))
        self.assertEqual(node.view, 0)

    def test_too_few_proofs_rejected(self):
        node = make_node(2, 4)
        cap = capturers(node)
        kickoff(node)
        # 1 proof < 2f+1 = 3.
        node.on_message(new_view(1, 1, dst=2,
                                 vc_proofs=vc_proofs(4, 1, count=1)), t=5.0)
        self.assertIn("insufficient_proofs", _reasons(cap))
        self.assertEqual(node.view, 0)


class TestCorruptReissue(unittest.TestCase):
    """A reissued PRE-PREPARE inside an otherwise-valid NEW-VIEW whose
    payload does not hash to its declared digest is rejected per-instance;
    the node still enters the new view (T29 node.py _enter_new_view)."""

    def test_digest_mismatched_reissue_rejected_but_view_entered(self):
        node = make_node(2, 4)
        cap = capturers(node)
        kickoff(node)
        corrupt = PrePreparePayload(view=1, seq=0,
                                    request_digest=digest(b"DECLARED"),
                                    request_payload=b"ACTUAL")
        node.on_message(
            new_view(1, 1, dst=2, vc_proofs=vc_proofs(4, 1),
                     reissued=[corrupt]), t=5.0)
        self.assertEqual(node.view, 1)               # view still entered
        self.assertIn("digest_mismatch", _reasons(cap))
        self.assertNotIn((1, 0), node.inst)          # corrupt inst dropped


class TestNonZeroInitialView(unittest.TestCase):
    """A node constructed already in a non-zero view (T29 builds these to
    exercise view-change) detects its primary by v mod n correctly."""

    def test_primary_detection_in_view_2(self):
        # n=4, view 2 -> primary is node 2.
        for node_id in range(4):
            with self.subTest(node_id=node_id):
                node = make_node(node_id, 4, view=2)
                self.assertEqual(node.view, 2)
                self.assertEqual(node._is_primary(2), node_id == 2)

    def test_primary_in_initial_view_arms_propose_timer(self):
        node = make_node(2, 4, view=2, workload=[b"W"])
        cap = capturers(node)
        node.start(t=0.0)
        self.assertIn("propose", cap.timer_ids())

    def test_non_primary_in_initial_view_arms_nothing(self):
        node = make_node(1, 4, view=2, workload=[b"W"])
        cap = capturers(node)
        node.start(t=0.0)
        self.assertNotIn("propose", cap.timer_ids())


class TestDemotedPrimaryProposeGuard(unittest.TestCase):
    """_propose returns early when the node is not the primary of its
    current view, or while a view-change is in progress."""

    def test_propose_is_noop_when_not_primary_of_current_view(self):
        # Node 0 is primary of view 0; advance it to view 1 (primary is
        # node 1). A stale propose timer must not emit a PRE-PREPARE.
        node = make_node(0, 4, workload=[b"W"])
        cap = capturers(node)
        kickoff(node)
        node.view = 1
        node._propose(t=1.0)
        self.assertEqual(cap.broadcasts, [])
        self.assertEqual(node.next_seq, 0)

    def test_propose_is_noop_while_view_changing(self):
        node = make_node(0, 4, workload=[b"W"])
        cap = capturers(node)
        kickoff(node)
        node.view_changing = True
        node._propose(t=1.0)
        self.assertEqual(cap.broadcasts, [])
        self.assertEqual(node.next_seq, 0)


class TestFullyOutOfOrderDelivery(unittest.TestCase):
    """The network gives no ordering guarantee (Decision C). A node that
    receives COMMITs, then PREPAREs, then finally the PRE-PREPARE still
    commits — the PRE-PREPARE landing cascades through both buffered
    quorums in a single dispatch."""

    def test_commit_then_prepare_then_pre_prepare_cascades_to_decided(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        # COMMITs first — buffered, digest unknown, no transition.
        for src in (0, 2):
            node.on_message(commit(src, 0, 0, _REQ, dst=1), t=1.0)
        # then PREPAREs — also buffered.
        for src in (0, 2):
            node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.IDLE)
        # finally the PRE-PREPARE: IDLE -> PRE_PREPARED -> PREPARED ->
        # COMMITTED in one shot.
        node.on_message(pre_prepare(0, 0, 0, _REQ, dst=1), t=3.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.COMMITTED)
        self.assertEqual(cap.count("decided"), 1)

    def test_commit_before_prepare_does_not_count_until_pre_prepare(self):
        # COMMITs alone, with no PRE-PREPARE: digest is unknown so
        # matching_commits stays 0 and the instance never leaves IDLE.
        node = make_node(1, 4)
        capturers(node)
        kickoff(node)
        for src in (0, 2, 3):
            node.on_message(commit(src, 0, 0, _REQ, dst=1), t=1.0)
        inst = node.inst[(0, 0)]
        self.assertIs(inst.state, InstanceState.IDLE)
        self.assertEqual(inst.matching_commits(), 0)
        self.assertEqual(len(inst.commits), 3)       # buffered


if __name__ == "__main__":
    unittest.main()
