"""Genuine Snowball preference semantics (audit finding #5).

close_round must set the conflict set's preference to the block with the
HIGHEST ACCUMULATED confidence (argmax over conflict_set.confidence),
flipping only when a challenger's confidence STRICTLY exceeds the current
preference's (tie-break: lowest block_id). This is Snowball, not
Snowflake's "flip to this round's sample majority".

The decisive case is the Snowflake-vs-Snowball divergence: a round where
the per-round majority block differs from the highest-confidence block.
Snowflake flips; genuine Snowball does not.
"""
import unittest

from snowman.block import (
    Block, ConflictSet, CSState, GENESIS_ID,
)
from snowman.poll import Poll, close_round


def _cs(*block_ids: bytes, parent_id: bytes = GENESIS_ID) -> ConflictSet:
    cs = ConflictSet(parent_id=parent_id)
    for i, bid in enumerate(block_ids):
        cs.add_block(Block(block_id=bid, parent_id=parent_id, slot=1,
                           proposer_idx=i, transactions=()))
    return cs


A = b"A" * 32
B = b"B" * 32
C = b"C" * 32


def _round(cs, agree, *, alpha_p, alpha_c, beta, block_id=A):
    poll = Poll(block_id=block_id, request_id=1, peers=(1, 2, 3, 4, 5))
    poll.agree_per_block = dict(agree)
    poll.responses_received = sum(agree.values())
    return close_round(conflict_set=cs, poll=poll,
                       alpha_p=alpha_p, alpha_c=alpha_c, beta=beta)


class TestSnowballArgmaxPreference(unittest.TestCase):
    """R5.1: preference = argmax(confidence), not this round's majority."""

    def test_preference_follows_accumulated_confidence(self):
        cs = _cs(A, B)
        # A is initial pref. Run three rounds where A is the alpha_p
        # majority -> confidence[A] climbs to 3, B stays 0.
        for _ in range(3):
            _round(cs, {A: 4, B: 1}, alpha_p=3, alpha_c=4, beta=15)
        self.assertEqual(cs.confidence[A], 3)
        self.assertEqual(cs.confidence.get(B, 0), 0)
        self.assertEqual(cs.preference, A)

    def test_flip_only_when_confidence_strictly_exceeds(self):
        cs = _cs(A, B)
        # Build A's confidence to 2.
        for _ in range(2):
            _round(cs, {A: 4, B: 1}, alpha_p=3, alpha_c=4, beta=15)
        self.assertEqual(cs.confidence[A], 2)
        # Now B wins alpha_p majorities. After B's confidence reaches 2 it
        # only ties A -> NO flip (must strictly exceed).
        out = _round(cs, {B: 4, A: 1}, alpha_p=3, alpha_c=4, beta=15)
        self.assertEqual(cs.confidence[B], 1)  # B at 1, A at 2
        self.assertFalse(out.flipped)
        self.assertEqual(cs.preference, A)
        out = _round(cs, {B: 4, A: 1}, alpha_p=3, alpha_c=4, beta=15)
        self.assertEqual(cs.confidence[B], 2)  # tie with A at 2
        self.assertFalse(out.flipped)          # tie does NOT flip
        self.assertEqual(cs.preference, A)
        # Third B-majority: confidence[B]=3 > confidence[A]=2 -> flip.
        out = _round(cs, {B: 4, A: 1}, alpha_p=3, alpha_c=4, beta=15)
        self.assertEqual(cs.confidence[B], 3)
        self.assertTrue(out.flipped)
        self.assertEqual(cs.preference, B)
        # Flip resets counter to 0; Step 2 then sees agree[B]=4 >= alpha_c=4
        # on the now-current preference and bumps it back to 1.
        self.assertEqual(out.counter, 1)


class TestSnowflakeVsSnowballDivergence(unittest.TestCase):
    """R5.2: a sequence where flip-to-majority and argmax-confidence DIVERGE.

    Old (Snowflake) close_round flipped the preference to THIS round's
    alpha_p majority unconditionally. Genuine Snowball keeps the preference
    on the block whose ACCUMULATED confidence is highest. This test pins the
    divergent case: A has high confidence, a single round goes to B at
    alpha_p; Snowflake would flip to B, Snowball must NOT.
    """

    def test_single_majority_round_does_not_flip_high_confidence_pref(self):
        cs = _cs(A, B)
        # A accrues confidence 5 over five rounds.
        for _ in range(5):
            _round(cs, {A: 4, B: 1}, alpha_p=3, alpha_c=4, beta=15)
        self.assertEqual(cs.confidence[A], 5)
        self.assertEqual(cs.preference, A)
        # ONE round where B is the alpha_p majority. Snowflake-rule would
        # flip preference -> B here. Snowball must NOT: confidence[B]=1 < 5.
        out = _round(cs, {B: 4, A: 1}, alpha_p=3, alpha_c=4, beta=15)
        self.assertEqual(cs.confidence[B], 1)
        self.assertFalse(out.flipped)
        self.assertEqual(cs.preference, A)
        self.assertEqual(out.new_preference, A)

    def test_counter_not_reset_when_no_actual_flip(self):
        # Counter resets only on an ACTUAL preference change, not on every
        # round whose majority differs from the preference.
        cs = _cs(A, B)
        for _ in range(3):
            _round(cs, {A: 4, B: 1}, alpha_p=3, alpha_c=4, beta=15)
        # counter advanced because agree[A]=4 >= alpha_c each round.
        self.assertEqual(cs.counter, 3)
        # A round where B is alpha_p-majority but confidence[A] still wins:
        # preference unchanged -> counter must NOT be reset by a flip.
        # (It still resets via the alpha_c miss on the unchanged pref A.)
        out = _round(cs, {B: 4, A: 1}, alpha_p=3, alpha_c=4, beta=15)
        self.assertFalse(out.flipped)
        # A got only 1 reply < alpha_c=4 -> counter resets via Step 2, not a flip.
        self.assertEqual(cs.counter, 0)

    def test_flip_resets_counter_to_zero_distinctly(self):
        # Prove the flip itself resets the counter (independent of Step 2).
        # A leads on confidence with counter advanced; B then overtakes on a
        # round that does NOT give the new pref B an alpha_c majority, so the
        # only thing that could zero the counter is the flip reset.
        cs = _cs(A, B)
        for _ in range(2):  # A confidence -> 2, counter -> 2
            _round(cs, {A: 5, B: 0}, alpha_p=3, alpha_c=4, beta=15)
        self.assertEqual(cs.counter, 2)
        # B overtakes: needs confidence[B] > confidence[A]=2, i.e. 3 rounds of
        # B alpha_p-majority. First two rounds: B 1, then 2 (tie, no flip),
        # third: B 3 > 2 flip. On the flip round give B exactly alpha_p (3)
        # but below alpha_c (4): agree[B]=3 hits alpha_p but not alpha_c.
        _round(cs, {B: 3, A: 2}, alpha_p=3, alpha_c=4, beta=15)  # B=1
        _round(cs, {B: 3, A: 2}, alpha_p=3, alpha_c=4, beta=15)  # B=2 tie
        self.assertEqual(cs.preference, A)
        self.assertEqual(cs.counter, 0)  # A missed alpha_c on prior rounds
        # Re-seed A's counter to isolate the flip-reset on the next round.
        cs.counter = 7
        out = _round(cs, {B: 3, A: 2}, alpha_p=3, alpha_c=4, beta=15)  # B=3 flip
        self.assertTrue(out.flipped)
        self.assertEqual(cs.preference, B)
        # agree[B]=3 < alpha_c=4 so Step 2 leaves counter at the flip's 0.
        self.assertEqual(out.counter, 0)

    def test_counter_preserved_across_nonflipping_high_pref_round(self):
        # A keeps both alpha_p-majority AND alpha_c on every round; counter
        # climbs monotonically and is never disturbed.
        cs = _cs(A, B)
        for i in range(1, 6):
            out = _round(cs, {A: 5, B: 0}, alpha_p=3, alpha_c=4, beta=15)
            self.assertEqual(out.counter, i)
            self.assertFalse(out.flipped)


class TestSingletonUnchanged(unittest.TestCase):
    """R5.4: singleton conflict set behaves identically (argmax == majority)."""

    def test_singleton_accepts_at_beta(self):
        cs = _cs(A)
        last = None
        for _ in range(15):
            last = _round(cs, {A: 3}, alpha_p=2, alpha_c=3, beta=15)
        self.assertTrue(last.accepted)
        self.assertEqual(last.counter, 15)
        self.assertEqual(cs.preference, A)
        self.assertIs(cs.state, CSState.ACCEPTED)
        self.assertEqual(cs.confidence[A], 15)


if __name__ == "__main__":
    unittest.main()
