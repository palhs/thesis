# tests/pbft/test_multi_round.py
"""T31 — PBFT across multiple rounds (sequence numbers).

Category 5 of the T31 battery (TASKS.md T31: "multi-round"). One validator
drives several (view, seq) instances: each commits independently, votes
for different seqs interleave without cross-counting, and `decided` fires
exactly once per seq — including the case Decision G guards, where a seq
commits both in its original view and again in a reissued instance after
a view-change.
"""
import unittest

from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import PrePreparePayload
from pbft.node import PBFT_COMMITTED

from _helpers import (
    capturers,
    commit,
    f_of,
    kickoff,
    make_node,
    new_view,
    others,
    pre_prepare,
    prepare,
    vc_proofs,
)


def _commit_seq(node, n, seq, batch, *, recipient=1, base_t=0.0):
    """Drive (view=0, seq) on `node` from PRE-PREPARE to COMMITTED."""
    node.on_message(pre_prepare(0, 0, seq, batch, dst=recipient),
                    t=base_t + 1.0)
    for src in others(recipient, n, 2 * f_of(n)):
        node.on_message(prepare(src, 0, seq, batch, dst=recipient),
                        t=base_t + 2.0)
    for src in others(recipient, n, 2 * f_of(n)):
        node.on_message(commit(src, 0, seq, batch, dst=recipient),
                        t=base_t + 3.0)


class TestSequentialRounds(unittest.TestCase):
    """Three sequence numbers each run the full three-phase commit."""

    def test_three_seqs_each_commit_independently(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        batches = {0: b"R0", 1: b"R1", 2: b"R2"}
        for seq, batch in batches.items():
            _commit_seq(node, 4, seq, batch, base_t=10.0 * seq)
        for seq in batches:
            self.assertIs(node.inst[(0, seq)].state,
                          InstanceState.COMMITTED)
        self.assertEqual(cap.count("decided"), 3)
        decided = {e[1]["instance_id"]: e[1]["value"]
                   for e in cap.events("decided")}
        self.assertEqual(
            decided,
            {(0, seq): digest(b).hex() for seq, b in batches.items()})

    def test_decided_fires_once_per_seq(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        _commit_seq(node, 4, 0, b"R0")
        # an extra COMMIT for the same seq does not re-decide.
        node.on_message(commit(3, 0, 0, b"R0", dst=1), t=99.0)
        self.assertEqual(cap.count("decided"), 1)


class TestInterleavedRounds(unittest.TestCase):
    """Votes for different seqs arriving interleaved do not cross-count —
    each (view, seq) keeps its own quorum dict."""

    def test_interleaved_prepares_keep_separate_quorums(self):
        node = make_node(1, 4)
        capturers(node)
        kickoff(node)
        node.on_message(pre_prepare(0, 0, 0, b"R0", dst=1), t=1.0)
        node.on_message(pre_prepare(0, 0, 1, b"R1", dst=1), t=1.1)
        # interleave one seq-0 and one seq-1 PREPARE: each instance now has
        # self + node 2 == 2, one short of the n=4 quorum of 3.
        node.on_message(prepare(2, 0, 0, b"R0", dst=1), t=2.0)
        node.on_message(prepare(2, 0, 1, b"R1", dst=1), t=2.1)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.PRE_PREPARED)
        self.assertIs(node.inst[(0, 1)].state, InstanceState.PRE_PREPARED)
        # tip only seq 0 — seq 1 must stay put.
        node.on_message(prepare(3, 0, 0, b"R0", dst=1), t=3.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.PREPARED)
        self.assertIs(node.inst[(0, 1)].state, InstanceState.PRE_PREPARED)

    def test_seq1_commit_does_not_decide_seq0(self):
        node = make_node(1, 4)
        cap = capturers(node)
        kickoff(node)
        _commit_seq(node, 4, 1, b"R1")              # commit seq 1 only
        decided = cap.events("decided")
        self.assertEqual(len(decided), 1)
        self.assertEqual(decided[0][1]["instance_id"], (0, 1))
        self.assertNotIn((0, 0), node.inst)


class TestDecidedOnceAcrossViewChange(unittest.TestCase):
    """Decision G: a seq committed in its original view and again in a
    reissued instance after a view-change emits `decided` exactly once."""

    def test_commit_in_view0_then_again_in_view1_decides_once(self):
        node = make_node(2, 4)                      # plain recipient
        cap = capturers(node)
        kickoff(node)

        # (0, 0) commits in view 0.
        _commit_seq(node, 4, 0, b"R0", recipient=2)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.COMMITTED)
        self.assertEqual(cap.count("decided"), 1)
        self.assertEqual(cap.count(PBFT_COMMITTED), 1)

        # The node enters view 1 with seq 0 reissued as instance (1, 0).
        reissued = [PrePreparePayload(view=1, seq=0,
                                      request_digest=digest(b"R0"),
                                      request_payload=b"R0")]
        node.on_message(
            new_view(1, 1, dst=2, vc_proofs=vc_proofs(4, 1),
                     reissued=reissued), t=50.0)
        self.assertEqual(node.view, 1)
        self.assertIn((1, 0), node.inst)

        # Drive the reissued (1, 0) all the way to COMMITTED.
        for src in others(2, 4, 2):
            node.on_message(prepare(src, 1, 0, b"R0", dst=2), t=51.0)
        for src in others(2, 4, 2):
            node.on_message(commit(src, 1, 0, b"R0", dst=2), t=52.0)
        self.assertIs(node.inst[(1, 0)].state, InstanceState.COMMITTED)

        # Both instances committed, but `decided` and `pbft_committed`
        # each fired only once for seq 0.
        self.assertEqual(cap.count("decided"), 1)
        self.assertEqual(cap.count(PBFT_COMMITTED), 1)


if __name__ == "__main__":
    unittest.main()
