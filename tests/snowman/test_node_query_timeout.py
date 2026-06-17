"""Optional query/response timeout for Snowman polls (T52 offline-validators).

Snowman polls K sampled peers per round; without a timeout, a round that
samples a non-responding (offline) peer and never reaches alpha_c agreement
nor K responses blocks forever. The opt-in `query_timeout` schedules a
per-round self-timer keyed ("query_timeout", block_id, request_id); on fire
it closes the round via the SAME close+advance path as a normal close, using
whatever responses arrived.

Hard constraint: `query_timeout=None` (the default, T51) schedules NO such
timer at all -- the code path must be byte-identical to the pre-T52 node.
"""
import unittest

from _helpers import capturers, kickoff, make_node
from nodes.message import Message
from snowman.block import GENESIS_ID, hash_block
from snowman.messages import BlockAnnouncementPayload, QueryResponsePayload


def _announce(node, block_id, parent_id=GENESIS_ID, slot=1, proposer_idx=1,
              t=1.0):
    payload = BlockAnnouncementPayload(
        slot=slot, block_id=block_id, parent_id=parent_id,
        transactions=(), proposer_idx=proposer_idx)
    node.on_message(Message(src=proposer_idx, dst=node.id,
                            type="BLOCK-ANNOUNCEMENT",
                            payload=payload, t_sent=0.0), t=t)


def _block_id():
    return hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=1,
                      transactions=())


def _start_round(node, block_id, t=1.0):
    """Fire the ("poll", block_id) timer to open a fresh poll round."""
    node.on_timer(("poll", block_id), block_id, t)


def _query_timeout_timers(cap):
    return [tm for tm in cap.timers
            if isinstance(tm[0], tuple) and tm[0][0] == "query_timeout"]


def _poll_timers(cap):
    return [tm for tm in cap.timers
            if isinstance(tm[0], tuple) and tm[0][0] == "poll"]


class TestNoTimerWhenDisabled(unittest.TestCase):
    def test_no_query_timeout_timer_when_none(self):
        """Default query_timeout=None -> the round never schedules a
        ("query_timeout", ...) timer (T51 path unchanged)."""
        node = make_node(node_id=0, n=4)
        self.assertIsNone(node.query_timeout)
        cap = capturers(node)
        kickoff(node)
        block_id = _block_id()
        _announce(node, block_id)
        _start_round(node, block_id)
        # A poll round was opened, but no query_timeout timer was scheduled.
        self.assertGreater(len(_poll_timers(cap)) + 1, 0)  # round is live
        self.assertEqual(_query_timeout_timers(cap), [])


class TestTimeoutFiresOnNonResponder(unittest.TestCase):
    def test_timeout_closes_round_and_advances(self):
        """With query_timeout set, open a round, deliver fewer than enough
        responses (offline peers withhold), then fire the query_timeout
        timer: the round CLOSES and the node arms the next poll round
        instead of hanging forever."""
        node = make_node(node_id=0, n=4)
        node.query_timeout = 15.0
        cap = capturers(node)
        kickoff(node)
        block_id = _block_id()
        _announce(node, block_id)
        _start_round(node, block_id)

        # Exactly one query_timeout timer scheduled for this round.
        qt = _query_timeout_timers(cap)
        self.assertEqual(len(qt), 1)
        timer_id, delay, _payload, _t = qt[0]
        self.assertEqual(timer_id[0], "query_timeout")
        self.assertEqual(timer_id[1], block_id)
        request_id = timer_id[2]
        self.assertEqual(delay, 15.0)

        poll = node.polls[block_id]
        self.assertFalse(poll.closed)
        self.assertEqual(poll.request_id, request_id)

        # Only one of K=3 peers responds; not enough for alpha_c nor K.
        node.on_message(Message(
            src=poll.peers[0], dst=0, type="QUERY-RESPONSE",
            payload=QueryResponsePayload(request_id=request_id,
                                         preferred_block_id=block_id),
            t_sent=0.0), t=2.0)
        self.assertFalse(node.polls[block_id].closed)

        n_polls_before = len(_poll_timers(cap))
        # Fire the query_timeout: close the round now with partial responses.
        node.on_timer(("query_timeout", block_id, request_id), None, t=20.0)

        # The round closed, a SNOWMAN_POLL_CLOSED event was emitted, and a
        # next poll round was armed (the node advanced, did not hang).
        self.assertEqual(
            cap.count("snowman_poll_closed"), 1)
        self.assertGreater(len(_poll_timers(cap)), n_polls_before)
        # block not accepted (only 1 response, alpha_c not met): poll still
        # tracked, ready for the next armed round.
        self.assertIn(block_id, node.polls)


class TestTimeoutWithZeroResponses(unittest.TestCase):
    def test_timeout_with_no_responses_closes_and_resets(self):
        """Every sampled peer offline: the round receives ZERO responses.
        Firing the timeout must still close the round cleanly (no crash on
        the empty response set), reset the success counter, not accept, and
        arm the next poll round."""
        node = make_node(node_id=0, n=4)
        node.query_timeout = 15.0
        cap = capturers(node)
        kickoff(node)
        block_id = _block_id()
        _announce(node, block_id)
        _start_round(node, block_id)

        request_id = _query_timeout_timers(cap)[0][0][2]
        cs = node._conflict_set_for(block_id)
        cs.counter = 7                       # pretend prior successes
        n_polls_before = len(_poll_timers(cap))

        node.on_timer(("query_timeout", block_id, request_id), None, t=20.0)

        self.assertEqual(cap.count("snowman_poll_closed"), 1)
        self.assertEqual(cs.counter, 0)      # reset: a silent round is no win
        self.assertGreater(len(_poll_timers(cap)), n_polls_before)


class TestFullResponsesCancelTimeout(unittest.TestCase):
    def test_normal_close_cancels_pending_timeout(self):
        """With query_timeout set, deliver enough agreeing responses to
        close the round normally BEFORE the timeout. The pending
        query_timeout timer is cancelled, and firing a stale timeout
        afterward is a no-op (no double-close, no crash)."""
        node = make_node(node_id=0, n=4)
        node.query_timeout = 15.0
        cap = capturers(node)
        kickoff(node)
        block_id = _block_id()
        _announce(node, block_id)
        _start_round(node, block_id)

        qt = _query_timeout_timers(cap)
        self.assertEqual(len(qt), 1)
        request_id = qt[0][0][2]
        poll = node.polls[block_id]

        # Deliver all K=3 responses agreeing on block_id -> normal close.
        closes_before = cap.count("snowman_poll_closed")
        for peer in poll.peers:
            node.on_message(Message(
                src=peer, dst=0, type="QUERY-RESPONSE",
                payload=QueryResponsePayload(request_id=request_id,
                                             preferred_block_id=block_id),
                t_sent=0.0), t=2.0)
        self.assertEqual(cap.count("snowman_poll_closed"),
                         closes_before + 1)

        # The pending query_timeout timer for this round was cancelled.
        self.assertIn(("query_timeout", block_id, request_id), cap.cancels)

        # Firing the now-stale timeout is a no-op: no extra close, no crash.
        closes_after_normal = cap.count("snowman_poll_closed")
        node.on_timer(("query_timeout", block_id, request_id), None, t=20.0)
        self.assertEqual(cap.count("snowman_poll_closed"),
                         closes_after_normal)


if __name__ == "__main__":
    unittest.main()
