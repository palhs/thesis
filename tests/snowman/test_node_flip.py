"""The alpha_p preference-flip path (design spec §1, §8.1).

Honest-path baseline does not exercise this code path (singleton conflict
sets keep agree = K trivially on the single candidate). This test guards
the flip path against regression and unblocks T18 / T51–T53 adversary
plumbing.
"""
import unittest

from snowman.block import (
    Block, ConflictSet, CSState, GENESIS_ID,
)
from snowman.poll import Poll, close_round


def _two_block_cs() -> ConflictSet:
    """Conflict set with two candidates A (initial pref) and B."""
    cs = ConflictSet(parent_id=GENESIS_ID)
    cs.add_block(Block(block_id=b"A"*32, parent_id=GENESIS_ID, slot=1,
                       proposer_idx=0, transactions=()))
    cs.add_block(Block(block_id=b"B"*32, parent_id=GENESIS_ID, slot=1,
                       proposer_idx=1, transactions=()))
    return cs


class TestPreferenceFlip(unittest.TestCase):
    def test_flip_on_alpha_p(self):
        """K=3, alpha_p=2, alpha_c=3. Two responses for B, one for A.
        Preference flips A -> B; counter resets to 0; alpha_c (3) is not
        hit, so counter stays 0."""
        cs = _two_block_cs()
        poll = Poll(block_id=b"A"*32, request_id=1, peers=(1, 2, 3))
        poll.agree_per_block = {b"A"*32: 1, b"B"*32: 2}
        poll.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=poll,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"B"*32)
        self.assertEqual(outcome.counter, 0)
        self.assertFalse(outcome.accepted)
        self.assertEqual(cs.confidence[b"B"*32], 1)

    def test_followup_round_advances_counter_for_new_pref(self):
        """After the flip, the next full-agreement round on B advances
        counter to 1."""
        cs = _two_block_cs()
        # First round: flip.
        poll1 = Poll(block_id=b"A"*32, request_id=1, peers=(1, 2, 3))
        poll1.agree_per_block = {b"A"*32: 1, b"B"*32: 2}
        poll1.responses_received = 3
        close_round(conflict_set=cs, poll=poll1,
                    alpha_p=2, alpha_c=3, beta=15)
        # Second round: all three responses for B.
        poll2 = Poll(block_id=b"A"*32, request_id=2, peers=(1, 2, 3))
        poll2.agree_per_block = {b"B"*32: 3}
        poll2.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=poll2,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertFalse(outcome.flipped)
        self.assertEqual(outcome.counter, 1)
        self.assertEqual(cs.confidence[b"B"*32], 2)

    def test_no_flip_when_majority_below_alpha_p(self):
        """Three responses split 1-1-1: no block hits alpha_p=2; counter
        resets if it was positive; preference unchanged."""
        cs = _two_block_cs()
        cs.add_block(Block(block_id=b"C"*32, parent_id=GENESIS_ID, slot=1,
                           proposer_idx=2, transactions=()))
        cs.counter = 5
        poll = Poll(block_id=b"A"*32, request_id=1, peers=(1, 2, 3))
        poll.agree_per_block = {b"A"*32: 1, b"B"*32: 1, b"C"*32: 1}
        poll.responses_received = 3
        outcome = close_round(conflict_set=cs, poll=poll,
                              alpha_p=2, alpha_c=3, beta=15)
        self.assertFalse(outcome.flipped)
        self.assertEqual(outcome.new_preference, b"A"*32)
        self.assertEqual(outcome.counter, 0)


if __name__ == "__main__":
    unittest.main()
