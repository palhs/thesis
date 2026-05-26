# tests/pbft/test_quorum_thresholds.py
"""T31 — PBFT quorum thresholds: insufficient votes and the 2f+1 boundary.

Category 2 of the T31 battery (TASKS.md T31: "insufficient votes"). The
prepare and commit phases each transition only at exactly 2f+1 matching
votes; 2f is insufficient. This file also pins the vote-counting edges
that keep the threshold honest under the T18/T53 adversarial input still
to come: a repeated vote from one src counts once, a src's later vote
overwrites its earlier one, votes for the wrong digest never count, and a
vote arriving after the instance is terminal does not re-fire the
transition. Degenerate small-n quorums (n <= 3, f = 0) are pinned too.
"""
import unittest

from pbft.instance import InstanceState
from pbft.node import PBFT_COMMITTED, PBFT_PREPARED

from _helpers import (
    capturers,
    commit,
    f_of,
    kickoff,
    make_node,
    others,
    pre_prepare,
    prepare,
    quorum,
)


_N = (4, 7, 10)        # f = 1, 2, 3 -> quorum 3, 5, 7
_REQ = b"R"


def _pre_prepared(n, recipient=1):
    """A recipient node at PRE_PREPARED for (0, 0), capturers installed."""
    node = make_node(recipient, n)
    cap = capturers(node)
    kickoff(node)
    node.on_message(pre_prepare(0, 0, 0, _REQ, dst=recipient), t=1.0)
    return node, cap


class TestPrepareThreshold(unittest.TestCase):
    """PRE_PREPARED -> PREPARED only at the 2f+1-th matching PREPARE."""

    def test_2f_prepares_is_insufficient(self):
        for n in _N:
            with self.subTest(n=n):
                node, cap = _pre_prepared(n)
                # self-vote already recorded; add 2f-1 peers -> 2f total.
                for src in others(1, n, 2 * f_of(n) - 1):
                    node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
                inst = node.inst[(0, 0)]
                self.assertEqual(inst.matching_prepares(), 2 * f_of(n))
                self.assertIs(inst.state, InstanceState.PRE_PREPARED)
                self.assertEqual(cap.count(PBFT_PREPARED), 0)

    def test_2f_plus_1_prepares_tips_to_prepared(self):
        for n in _N:
            with self.subTest(n=n):
                node, _ = _pre_prepared(n)
                peers = others(1, n, 2 * f_of(n))
                for src in peers[:-1]:                  # self + 2f-1 == 2f
                    node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
                self.assertIs(node.inst[(0, 0)].state,
                              InstanceState.PRE_PREPARED)
                node.on_message(prepare(peers[-1], 0, 0, _REQ, dst=1), t=3.0)
                self.assertIs(node.inst[(0, 0)].state,
                              InstanceState.PREPARED)
                self.assertEqual(node.inst[(0, 0)].matching_prepares(),
                                 quorum(n))


class TestCommitThreshold(unittest.TestCase):
    """PREPARED -> COMMITTED only at the 2f+1-th matching COMMIT."""

    def _prepared(self, n):
        node, cap = _pre_prepared(n)
        for src in others(1, n, 2 * f_of(n)):
            node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
        assert node.inst[(0, 0)].state is InstanceState.PREPARED
        return node, cap

    def test_2f_commits_is_insufficient(self):
        for n in _N:
            with self.subTest(n=n):
                node, cap = self._prepared(n)
                # self-COMMIT recorded at PREPARED; add 2f-1 peers -> 2f.
                for src in others(1, n, 2 * f_of(n) - 1):
                    node.on_message(commit(src, 0, 0, _REQ, dst=1), t=5.0)
                inst = node.inst[(0, 0)]
                self.assertEqual(inst.matching_commits(), 2 * f_of(n))
                self.assertIs(inst.state, InstanceState.PREPARED)
                self.assertEqual(cap.count(PBFT_COMMITTED), 0)
                self.assertEqual(cap.count("decided"), 0)

    def test_2f_plus_1_commits_tips_to_committed(self):
        for n in _N:
            with self.subTest(n=n):
                node, cap = self._prepared(n)
                peers = others(1, n, 2 * f_of(n))
                for src in peers[:-1]:
                    node.on_message(commit(src, 0, 0, _REQ, dst=1), t=5.0)
                self.assertIs(node.inst[(0, 0)].state,
                              InstanceState.PREPARED)
                node.on_message(commit(peers[-1], 0, 0, _REQ, dst=1), t=6.0)
                self.assertIs(node.inst[(0, 0)].state,
                              InstanceState.COMMITTED)
                self.assertEqual(cap.count("decided"), 1)


class TestVoteCountingEdges(unittest.TestCase):
    """Edge cases that keep the 2f+1 count honest under adversarial input."""

    def test_repeated_prepare_from_one_src_counts_once(self):
        # n=4: node 2 floods three PREPAREs. The quorum dict is keyed by
        # src, so the count is self + node 2 == 2, never 4.
        node, _ = _pre_prepared(4)
        for t in (2.0, 2.1, 2.2):
            node.on_message(prepare(2, 0, 0, _REQ, dst=1), t=t)
        inst = node.inst[(0, 0)]
        self.assertEqual(inst.matching_prepares(), 2)
        self.assertIs(inst.state, InstanceState.PRE_PREPARED)

    def test_later_vote_from_one_src_overwrites_earlier(self):
        # A src votes the honest digest, then re-votes a conflicting one:
        # the dict is last-write-wins, so the honest vote is lost and the
        # count drops. Documents the equivocation seam T53 will exercise.
        node, _ = _pre_prepared(4)
        node.on_message(prepare(2, 0, 0, _REQ, dst=1), t=2.0)        # honest
        self.assertEqual(node.inst[(0, 0)].matching_prepares(), 2)
        node.on_message(prepare(2, 0, 0, b"OTHER", dst=1), t=2.1)    # flips
        self.assertEqual(node.inst[(0, 0)].matching_prepares(), 1)   # self

    def test_wrong_digest_prepares_never_count(self):
        for n in _N:
            with self.subTest(n=n):
                node, _ = _pre_prepared(n)
                for src in others(1, n, 2 * f_of(n)):
                    node.on_message(prepare(src, 0, 0, b"WRONG", dst=1),
                                    t=2.0)
                inst = node.inst[(0, 0)]
                self.assertEqual(inst.matching_prepares(), 1)   # self only
                self.assertIs(inst.state, InstanceState.PRE_PREPARED)

    def test_prepare_after_prepared_does_not_refire(self):
        # An extra matching PREPARE once the instance is already PREPARED
        # must not re-emit pbft_prepared (the quorum check guards on state).
        node, cap = _pre_prepared(4)
        for src in others(1, 4, 2):
            node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.PREPARED)
        before = cap.count(PBFT_PREPARED)
        node.on_message(prepare(3, 0, 0, _REQ, dst=1), t=3.0)       # extra
        self.assertEqual(cap.count(PBFT_PREPARED), before)

    def test_commit_after_committed_does_not_refire_decided(self):
        node, cap = _pre_prepared(4)
        for src in others(1, 4, 2):
            node.on_message(prepare(src, 0, 0, _REQ, dst=1), t=2.0)
        for src in others(1, 4, 2):
            node.on_message(commit(src, 0, 0, _REQ, dst=1), t=5.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.COMMITTED)
        self.assertEqual(cap.count("decided"), 1)
        node.on_message(commit(3, 0, 0, _REQ, dst=1), t=6.0)        # extra
        self.assertEqual(cap.count("decided"), 1)


class TestFaultThreshold(unittest.TestCase):
    """f = (n-1)//3 across the validator-set sizes the experiment matrix
    sweeps (T19/T41: n in {4, 7, 10, 16, 25})."""

    def test_f_table(self):
        for n, expected_f in [(4, 1), (7, 2), (10, 3), (16, 5), (25, 8)]:
            with self.subTest(n=n):
                self.assertEqual(make_node(0, n).f, expected_f)
                self.assertEqual(quorum(n), 2 * expected_f + 1)


class TestDegenerateQuorumSmallN(unittest.TestCase):
    """n <= 3 gives f = 0 and a quorum of 1: a node decides on its own
    vote alone. Documents that PBFT below 3f+1 = 4 has no fault tolerance
    whatsoever — a fact T39 and the adversarial tasks must not trip over."""

    def test_f_is_zero_below_four(self):
        for n in (1, 2, 3):
            with self.subTest(n=n):
                self.assertEqual(make_node(0, n).f, 0)
                self.assertEqual(quorum(n), 1)

    def test_single_node_self_commits_with_no_peers(self):
        # n=1: the lone node is primary; one propose drives its own
        # instance straight to `decided` with zero network messages.
        node = make_node(0, 1, workload=[b"SOLO"])
        cap = capturers(node)
        node.start(t=0.0)                   # CREATED -> RUNNING -> _on_start
        node.on_timer("propose", None, t=1.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.COMMITTED)
        self.assertEqual(cap.count("decided"), 1)

    def test_n3_recipient_commits_on_pre_prepare_alone(self):
        # n=3, f=0: a recipient reaches COMMITTED the instant it accepts
        # the PRE-PREPARE — its self-PREPARE and self-COMMIT each already
        # meet the quorum of 1, with no peer vote at all.
        node = make_node(1, 3)
        cap = capturers(node)
        kickoff(node)
        node.on_message(pre_prepare(0, 0, 0, _REQ, dst=1), t=1.0)
        self.assertIs(node.inst[(0, 0)].state, InstanceState.COMMITTED)
        self.assertEqual(cap.count("decided"), 1)


if __name__ == "__main__":
    unittest.main()
