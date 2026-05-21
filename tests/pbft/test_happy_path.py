# tests/pbft/test_happy_path.py
"""T31 — PBFT happy path: the honest full three-phase commit.

Category 1 of the T31 battery (TASKS.md T31: "happy path"). One isolated
non-primary validator is driven PRE-PREPARE -> PREPARED -> COMMITTED ->
`decided` with exactly a 2f+1 quorum and no faults, parametrized over the
honest validator-set sizes n in {4, 7, 10}. This is the control the
insufficient-votes, message-loss, and multi-round files contrast against.

Idiom: tests/pbft/_helpers.py — one PBFTNode in isolation, capturers on
the outbound API, hand-built Messages, direct on_message calls.
"""
import unittest

from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.node import (
    PBFT_COMMITTED,
    PBFT_PRE_PREPARED,
    PBFT_PREPARED,
    PBFT_REJECTED,
)

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


_HONEST_N = (4, 7, 10)        # f = 1, 2, 3 -> quorum 3, 5, 7
_REQUEST = b"REQUEST-0"


class TestHappyPathThreePhaseCommit(unittest.TestCase):
    """A non-primary validator completes the full commit at every honest n."""

    def _drive(self, n):
        """Recipient = node 1 (non-primary in view 0). Returns (node, cap)."""
        node = make_node(1, n)
        cap = capturers(node)
        kickoff(node)
        # Phase 1: PRE-PREPARE from the view-0 primary (node 0).
        node.on_message(pre_prepare(0, 0, 0, _REQUEST, dst=1), t=1.0)
        # Phase 2: 2f peer PREPAREs (the node self-recorded its own).
        for k, src in enumerate(others(1, n, 2 * f_of(n))):
            node.on_message(prepare(src, 0, 0, _REQUEST, dst=1), t=2.0 + k)
        # Phase 3: 2f peer COMMITs (the node self-recorded its own).
        for k, src in enumerate(others(1, n, 2 * f_of(n))):
            node.on_message(commit(src, 0, 0, _REQUEST, dst=1), t=20.0 + k)
        return node, cap

    def test_reaches_committed_at_every_n(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                node, _ = self._drive(n)
                self.assertIs(node.inst[(0, 0)].state,
                              InstanceState.COMMITTED)

    def test_emits_each_phase_event_once(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                _, cap = self._drive(n)
                self.assertEqual(cap.count(PBFT_PRE_PREPARED), 1)
                self.assertEqual(cap.count(PBFT_PREPARED), 1)
                self.assertEqual(cap.count(PBFT_COMMITTED), 1)
                self.assertEqual(cap.count("decided"), 1)

    def test_decided_value_is_request_digest(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                _, cap = self._drive(n)
                dec = cap.events("decided")[0]
                self.assertEqual(dec[1]["value"], digest(_REQUEST).hex())
                self.assertEqual(dec[1]["instance_id"], (0, 0))

    def test_broadcasts_own_prepare_and_commit(self):
        # Decision B — every replica, primary or not, broadcasts its own
        # PREPARE and COMMIT.
        for n in _HONEST_N:
            with self.subTest(n=n):
                _, cap = self._drive(n)
                self.assertEqual(cap.count_broadcast("PREPARE"), 1)
                self.assertEqual(cap.count_broadcast("COMMIT"), 1)

    def test_no_rejections_and_no_view_change(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                _, cap = self._drive(n)
                self.assertEqual(cap.count(PBFT_REJECTED), 0)
                self.assertEqual(cap.count("pbft_view_change"), 0)
                self.assertNotIn("VIEW-CHANGE", cap.broadcast_types())

    def test_view_change_timer_cancelled_on_commit(self):
        # The per-instance timer armed at PRE_PREPARED is cancelled when the
        # instance commits — an honest run leaves nothing to escalate.
        for n in _HONEST_N:
            with self.subTest(n=n):
                _, cap = self._drive(n)
                self.assertIn(("view_change", 0, 0), cap.cancels)


class TestHappyPathQuorumIsExactlyMinimal(unittest.TestCase):
    """The happy-path drive feeds exactly 2f+1 votes — the minimum that
    transitions the phase, and the boundary test_quorum_thresholds probes."""

    def test_prepare_quorum_is_exactly_2f_plus_1(self):
        for n in (4, 7, 10):
            with self.subTest(n=n):
                node = make_node(1, n)
                capturers(node)
                kickoff(node)
                node.on_message(pre_prepare(0, 0, 0, _REQUEST, dst=1), t=1.0)
                for src in others(1, n, 2 * f_of(n)):
                    node.on_message(prepare(src, 0, 0, _REQUEST, dst=1),
                                    t=2.0)
                inst = node.inst[(0, 0)]
                # self + 2f peers == 2f+1 == quorum, and that tips PREPARED.
                self.assertEqual(inst.matching_prepares(), quorum(n))
                self.assertIs(inst.state, InstanceState.PREPARED)


if __name__ == "__main__":
    unittest.main()
