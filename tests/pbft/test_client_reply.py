# tests/pbft/test_client_reply.py
"""T70 finding #1 — client-observed finality via a REPLY round.

PBFT finality was measured at the internal 2f+1 COMMIT quorum, one network
hop optimistic relative to the paper's client-observed finality. This suite
pins the REPLY round:

  - REPLY payload shape (view, seq, request_digest, replica_id);
  - on COMMITTED-local a replica sends a REPLY toward the committing view's
    primary (node = view mod n), the designated client-reply collector;
  - the collector finalizes a seq on f+1 matching (view, seq, digest)
    REPLYs, emitting `pbft_client_finalized` exactly once per seq.

Same idiom as the rest of the T31 battery (tests/pbft/_helpers.py): one
PBFTNode in isolation, capturers on the outbound API, hand-built Messages,
direct on_message calls. The collector path needs a node that IS the
primary of the committing view, so these tests drive node 0 in view 0.
"""
import unittest

from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import ReplyPayload
from pbft.node import (
    PBFT_CLIENT_FINALIZED,
    PBFT_COMMITTED,
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
    reply,
)


_HONEST_N = (4, 7, 10)        # f = 1, 2, 3
_REQUEST = b"REQUEST-0"


class TestReplyPayload(unittest.TestCase):
    """The REPLY wire payload carries (view, seq, request_digest, replica_id)."""

    def test_fields(self):
        d = digest(_REQUEST)
        rp = ReplyPayload(view=0, seq=3, request_digest=d, replica_id=2)
        self.assertEqual((rp.view, rp.seq, rp.request_digest, rp.replica_id),
                         (0, 3, d, 2))

    def test_frozen(self):
        from dataclasses import FrozenInstanceError
        rp = ReplyPayload(view=0, seq=0, request_digest=b"\x00" * 32,
                          replica_id=0)
        with self.assertRaises(FrozenInstanceError):
            rp.seq = 1


class TestReplicaRepliesOnCommit(unittest.TestCase):
    """R1.1 — on COMMITTED-local each replica sends a REPLY toward the
    committing view's primary (the client-reply collector)."""

    def _drive_to_commit(self, n, recipient):
        """Drive `recipient` (a non-collector node) through the full
        three-phase commit for (view=0, seq=0)."""
        node = make_node(recipient, n)
        cap = capturers(node)
        kickoff(node)
        node.on_message(pre_prepare(0, 0, 0, _REQUEST, dst=recipient), t=1.0)
        for src in others(recipient, n, 2 * f_of(n)):
            node.on_message(prepare(src, 0, 0, _REQUEST, dst=recipient), t=2.0)
        for src in others(recipient, n, 2 * f_of(n)):
            node.on_message(commit(src, 0, 0, _REQUEST, dst=recipient), t=3.0)
        return node, cap

    def test_replica_sends_reply_to_view_primary(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                # node 1 is a non-primary in view 0; collector = 0 mod n = 0.
                node, cap = self._drive_to_commit(n, recipient=1)
                self.assertIs(node.inst[(0, 0)].state, InstanceState.COMMITTED)
                # Exactly one REPLY, addressed to node 0, the view-0 primary.
                reply_sends = [s for s in cap.sends if s[0][1] == "REPLY"]
                self.assertEqual(len(reply_sends), 1)
                args = reply_sends[0][0]
                dst, _type, payload = args[0], args[1], args[2]
                self.assertEqual(dst, 0)              # view 0 mod n == 0
                self.assertIsInstance(payload, ReplyPayload)
                self.assertEqual(payload.view, 0)
                self.assertEqual(payload.seq, 0)
                self.assertEqual(payload.request_digest, digest(_REQUEST))
                self.assertEqual(payload.replica_id, 1)


class TestCollectorFinalizes(unittest.TestCase):
    """R1.2 — the collector (node = view mod n) finalizes a seq on f+1
    matching REPLYs and emits `pbft_client_finalized` exactly once."""

    def _collector(self, n):
        """Collector = node 0 (view-0 primary). Driven to its own COMMIT so
        it both self-replies and collects peer replies."""
        node = make_node(0, n)
        cap = capturers(node)
        kickoff(node)
        node.on_message(pre_prepare(0, 0, 0, _REQUEST, dst=0), t=1.0)
        for src in others(0, n, 2 * f_of(n)):
            node.on_message(prepare(src, 0, 0, _REQUEST, dst=0), t=2.0)
        for src in others(0, n, 2 * f_of(n)):
            node.on_message(commit(src, 0, 0, _REQUEST, dst=0), t=3.0)
        return node, cap

    def test_no_finalize_below_f_plus_1(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                node, cap = self._collector(n)
                f = f_of(n)
                # The collector self-recorded one REPLY at commit. Feed f-1
                # more peer REPLYs: total f, still one short of f+1.
                for src in others(0, n, f - 1):
                    node.on_message(reply(src, 0, 0, _REQUEST, dst=0), t=4.0)
                self.assertEqual(cap.count(PBFT_CLIENT_FINALIZED), 0)

    def test_finalize_at_f_plus_1(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                node, cap = self._collector(n)
                f = f_of(n)
                # Self REPLY (1) + f peer REPLYs = f+1 matching.
                for src in others(0, n, f):
                    node.on_message(reply(src, 0, 0, _REQUEST, dst=0), t=5.0)
                self.assertEqual(cap.count(PBFT_CLIENT_FINALIZED), 1)
                ev = cap.events(PBFT_CLIENT_FINALIZED)[0]
                self.assertEqual(ev[1]["seq"], 0)
                self.assertEqual(ev[1]["view"], 0)
                self.assertEqual(ev[1]["t"], 5.0)

    def test_finalize_emitted_once_despite_extra_replies(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                node, cap = self._collector(n)
                # Feed every remaining peer REPLY — well past f+1.
                for src in others(0, n, n - 1):
                    node.on_message(reply(src, 0, 0, _REQUEST, dst=0), t=6.0)
                self.assertEqual(cap.count(PBFT_CLIENT_FINALIZED), 1)

    def test_mismatched_digest_replies_do_not_count(self):
        for n in _HONEST_N:
            with self.subTest(n=n):
                node, cap = self._collector(n)
                f = f_of(n)
                wrong = b"WRONG"
                # f peer REPLYs with a non-matching digest: must not finalize
                # (collector has only its own matching self-REPLY).
                for src in others(0, n, f):
                    node.on_message(reply(src, 0, 0, wrong, dst=0), t=7.0)
                self.assertEqual(cap.count(PBFT_CLIENT_FINALIZED), 0)


class TestCommitStillFiresAndPrecedesReply(unittest.TestCase):
    """R1.3 sanity at the unit level — the COMMIT-quorum `pbft_committed`
    and `decided` still fire, and finalization happens strictly later."""

    def test_commit_event_precedes_client_finalize(self):
        n = 4
        node = make_node(0, n)
        cap = capturers(node)
        kickoff(node)
        node.on_message(pre_prepare(0, 0, 0, _REQUEST, dst=0), t=1.0)
        for src in others(0, n, 2 * f_of(n)):
            node.on_message(prepare(src, 0, 0, _REQUEST, dst=0), t=2.0)
        for src in others(0, n, 2 * f_of(n)):
            node.on_message(commit(src, 0, 0, _REQUEST, dst=0), t=3.0)
        # commit fired at t=3.0; client-finalize one hop later at t=4.0.
        for src in others(0, n, f_of(n)):
            node.on_message(reply(src, 0, 0, _REQUEST, dst=0), t=4.0)
        commit_t = cap.events(PBFT_COMMITTED)[0][2]
        final_t = cap.events(PBFT_CLIENT_FINALIZED)[0][2]
        self.assertEqual(commit_t, 3.0)
        self.assertEqual(final_t, 4.0)
        self.assertGreater(final_t, commit_t)


if __name__ == "__main__":
    unittest.main()
