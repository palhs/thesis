"""Tests for poll.py (design spec §5) — Poll, on_response, close_round."""
import unittest

from snowman.block import (
    Block, ConflictSet, CSState, GENESIS_ID,
)
from snowman.poll import Poll, PollOutcome, close_round, on_response


def _cs_with_block(block_id: bytes,
                   parent_id: bytes = GENESIS_ID) -> ConflictSet:
    cs = ConflictSet(parent_id=parent_id)
    cs.add_block(Block(block_id=block_id, parent_id=parent_id,
                       slot=1, proposer_idx=0, transactions=()))
    return cs


class TestPoll(unittest.TestCase):
    def test_initial_state(self):
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        self.assertEqual(p.peers, (1, 2, 3))
        self.assertEqual(p.agree_per_block, {})
        self.assertEqual(p.responses_received, 0)
        self.assertFalse(p.closed)


class TestOnResponseSuccessPath(unittest.TestCase):
    """Round closes when agree[current_pref] >= alpha_c."""

    def test_early_close_at_alpha_c(self):
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        # K=3, alpha_c=3 (n=4). Three responses all for current_pref close
        # the round on the third response.
        closed1 = on_response(poll=p, preferred_block_id=b"a"*32,
                              current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertFalse(closed1)
        self.assertEqual(p.responses_received, 1)
        closed2 = on_response(poll=p, preferred_block_id=b"a"*32,
                              current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertFalse(closed2)
        closed3 = on_response(poll=p, preferred_block_id=b"a"*32,
                              current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertTrue(closed3)
        self.assertTrue(p.closed)

    def test_no_close_when_below_alpha_c(self):
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3, 4, 5))
        # K=5, alpha_c=4. Three responses for current_pref + two for B.
        for _ in range(3):
            closed = on_response(poll=p, preferred_block_id=b"a"*32,
                                 current_preference=b"a"*32, alpha_c=4, K=5)
            self.assertFalse(closed)
        for _ in range(2):
            closed = on_response(poll=p, preferred_block_id=b"b"*32,
                                 current_preference=b"a"*32, alpha_c=4, K=5)
            self.assertFalse(closed)
        # 5 responses received, agree[A] = 3 < 4, no early close.
        self.assertEqual(p.responses_received, 5)
        self.assertFalse(p.closed)

    def test_closed_poll_drops_further_responses(self):
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        for _ in range(3):
            on_response(poll=p, preferred_block_id=b"a"*32,
                        current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertTrue(p.closed)
        closed = on_response(poll=p, preferred_block_id=b"a"*32,
                             current_preference=b"a"*32, alpha_c=3, K=3)
        self.assertFalse(closed)
        # State unchanged.
        self.assertEqual(p.responses_received, 3)
        self.assertEqual(p.agree_per_block[b"a"*32], 3)


class TestCloseRoundAlphaCSuccess(unittest.TestCase):
    """Case (a): agree[current_pref] >= alpha_c, no flip."""

    def test_increments_counter_no_flip(self):
        cs = _cs_with_block(b"a"*32)
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        p.agree_per_block = {b"a"*32: 3}
        p.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertFalse(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"a"*32)
        self.assertEqual(outcome.counter, 1)
        self.assertFalse(outcome.accepted)
        self.assertEqual(cs.counter, 1)
        self.assertEqual(cs.confidence[b"a"*32], 1)


class TestCloseRoundAlphaPFlip(unittest.TestCase):
    """Case (b): non-pref block hits alpha_p; preference flips, counter resets."""

    def test_flip_resets_counter(self):
        cs = _cs_with_block(b"a"*32)
        cs.add_block(Block(block_id=b"b"*32, parent_id=GENESIS_ID, slot=1,
                           proposer_idx=1, transactions=()))
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        p.agree_per_block = {b"a"*32: 1, b"b"*32: 2}
        p.responses_received = 3
        # K=3, alpha_p=2, alpha_c=3.
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"b"*32)
        self.assertEqual(outcome.counter, 0)
        self.assertFalse(outcome.accepted)
        self.assertEqual(cs.preference, b"b"*32)
        self.assertEqual(cs.confidence[b"b"*32], 1)


class TestCloseRoundNoAlphaPHit(unittest.TestCase):
    """Case (c): no block hits alpha_p; counter resets to 0."""

    def test_no_flip_counter_resets(self):
        cs = _cs_with_block(b"a"*32)
        cs.add_block(Block(block_id=b"b"*32, parent_id=GENESIS_ID, slot=1,
                           proposer_idx=1, transactions=()))
        cs.counter = 4  # was advancing
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3, 4, 5))
        # K=5, alpha_p=3. Split 2-2-1; no block hits alpha_p.
        p.agree_per_block = {b"a"*32: 2, b"b"*32: 2, b"c"*32: 1}
        p.responses_received = 5
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=3, alpha_c=4, beta=15)
        self.assertFalse(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"a"*32)
        self.assertEqual(outcome.counter, 0)
        self.assertFalse(outcome.accepted)
        self.assertNotIn(b"c"*32, cs.confidence)


class TestCloseRoundAcceptance(unittest.TestCase):
    """Counter reaches beta -> ACCEPTED."""

    def test_acceptance_at_beta(self):
        cs = _cs_with_block(b"a"*32)
        cs.counter = 14  # one shy of beta=15
        p = Poll(block_id=b"a"*32, request_id=0, peers=(1, 2, 3))
        p.agree_per_block = {b"a"*32: 3}
        p.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.counter, 15)
        self.assertIs(cs.state, CSState.ACCEPTED)


class TestCloseRoundTieBreak(unittest.TestCase):
    """Argmax tie-break: lowest block_id wins."""

    def test_tie_break_by_block_id(self):
        cs = _cs_with_block(b"\xff" * 32)  # high lex
        cs.add_block(Block(block_id=b"\x01" * 32, parent_id=GENESIS_ID,
                           slot=1, proposer_idx=1, transactions=()))
        p = Poll(block_id=b"\xff"*32, request_id=0, peers=(1, 2, 3, 4))
        # Two blocks tied at 2 each. Lowest block_id (b"\x01"*32) should win.
        p.agree_per_block = {b"\xff" * 32: 2, b"\x01" * 32: 2}
        p.responses_received = 4
        outcome = close_round(conflict_set=cs, poll=p,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"\x01" * 32)


if __name__ == "__main__":
    unittest.main()
