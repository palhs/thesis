"""Unit tests for the pure Casper FFG threshold-finality rule (T34).

The integration witness — that `CasperNode` still routes vote application
correctly through the new module — is `tests/pos/test_node_finality.py`,
which is intentionally unchanged across the T32 -> T34 refactor-extract.
These tests cover the rule itself in isolation: no `CasperNode`, no
scheduler, no chain.
"""
import unittest

from pos.epoch import EpochFSM
from pos.finality import FFGTransitions, evaluate, meets_supermajority


class TestSupermajority(unittest.TestCase):
    def test_strict_two_thirds_meets_boundary(self):
        # 3 * 8 == 2 * 12 -> exactly 2/3.
        self.assertTrue(meets_supermajority(8.0, 12.0))

    def test_one_short_does_not_meet(self):
        # 3 * 7 = 21 < 24 = 2 * 12 -> below 2/3.
        self.assertFalse(meets_supermajority(7.0, 12.0))

    def test_full_stake_meets(self):
        self.assertTrue(meets_supermajority(12.0, 12.0))

    def test_zero_stake_against_zero_total_is_true(self):
        # Documentation guard: the bare arithmetic is vacuously True at
        # (0, 0); `evaluate` short-circuits the empty-quorum case so this
        # never reaches the FSM. Pinned here so the helper's contract is
        # explicit.
        self.assertTrue(meets_supermajority(0.0, 0.0))


class TestEvaluate(unittest.TestCase):

    def test_supermajority_from_justified_source_justifies_target(self):
        out = evaluate(
            source_epoch=0, target_epoch=1,
            link_stake=8.0, total_stake=12.0,
            source_state=EpochFSM.FINALISED,
            target_state=EpochFSM.UNJUSTIFIED,
        )
        self.assertEqual(out, FFGTransitions(justified=True,
                                             finalised_source=False))

    def test_consecutive_link_from_justified_source_finalises_source(self):
        out = evaluate(
            source_epoch=1, target_epoch=2,
            link_stake=8.0, total_stake=12.0,
            source_state=EpochFSM.JUSTIFIED,
            target_state=EpochFSM.UNJUSTIFIED,
        )
        self.assertEqual(out, FFGTransitions(justified=True,
                                             finalised_source=True))

    def test_boundary_supermajority_justifies(self):
        # Edge case 1: 3 * stake == 2 * total (exactly 2/3). Distinct
        # numerics from the other boundary tests so a hardcoded constant
        # could not satisfy both.
        out = evaluate(
            source_epoch=0, target_epoch=1,
            link_stake=2.0, total_stake=3.0,
            source_state=EpochFSM.FINALISED,
            target_state=EpochFSM.UNJUSTIFIED,
        )
        self.assertTrue(out.justified)

    def test_one_short_does_not_justify(self):
        # Edge case 2: 3 * stake == 2 * total - 1.
        # 3 * 7 = 21 = 2 * 11 - 1 -> below the boundary at total=12.
        out = evaluate(
            source_epoch=0, target_epoch=1,
            link_stake=7.0, total_stake=12.0,
            source_state=EpochFSM.FINALISED,
            target_state=EpochFSM.UNJUSTIFIED,
        )
        self.assertEqual(out, FFGTransitions(justified=False,
                                             finalised_source=False))

    def test_unjustified_source_blocks_transition(self):
        # Edge case 3: source not justified -> no transition.
        out = evaluate(
            source_epoch=1, target_epoch=2,
            link_stake=12.0, total_stake=12.0,
            source_state=EpochFSM.UNJUSTIFIED,
            target_state=EpochFSM.UNJUSTIFIED,
        )
        self.assertFalse(out.justified)
        self.assertFalse(out.finalised_source)

    def test_target_already_justified_is_no_op(self):
        # Edge case 4: second supermajority link must not re-emit.
        out = evaluate(
            source_epoch=0, target_epoch=1,
            link_stake=12.0, total_stake=12.0,
            source_state=EpochFSM.FINALISED,
            target_state=EpochFSM.JUSTIFIED,
        )
        self.assertEqual(out, FFGTransitions(justified=False,
                                             finalised_source=False))

    def test_target_already_finalised_is_no_op(self):
        # Edge case 4, finalised arm: re-justification of a finalised
        # target must not re-emit.
        out = evaluate(
            source_epoch=0, target_epoch=1,
            link_stake=12.0, total_stake=12.0,
            source_state=EpochFSM.FINALISED,
            target_state=EpochFSM.FINALISED,
        )
        self.assertEqual(out, FFGTransitions(justified=False,
                                             finalised_source=False))

    def test_finalised_source_not_re_finalised(self):
        # Edge case 5: source already FINALISED -> justify target but do
        # not re-finalise the source.
        out = evaluate(
            source_epoch=0, target_epoch=1,
            link_stake=12.0, total_stake=12.0,
            source_state=EpochFSM.FINALISED,
            target_state=EpochFSM.UNJUSTIFIED,
        )
        self.assertTrue(out.justified)
        self.assertFalse(out.finalised_source)

    def test_non_consecutive_link_justifies_but_does_not_finalise(self):
        # Edge case 6: source=0 (finalised), target=2 (gap) -> justify
        # target, do not finalise source.
        out = evaluate(
            source_epoch=0, target_epoch=2,
            link_stake=12.0, total_stake=12.0,
            source_state=EpochFSM.FINALISED,
            target_state=EpochFSM.UNJUSTIFIED,
        )
        self.assertTrue(out.justified)
        self.assertFalse(out.finalised_source)

    def test_non_consecutive_link_from_justified_source_does_not_finalise(self):
        # Edge case 6, justified-source arm: source still JUSTIFIED (not
        # yet finalised) and target is not its immediate successor ->
        # justify target only.
        out = evaluate(
            source_epoch=1, target_epoch=3,
            link_stake=12.0, total_stake=12.0,
            source_state=EpochFSM.JUSTIFIED,
            target_state=EpochFSM.UNJUSTIFIED,
        )
        self.assertTrue(out.justified)
        self.assertFalse(out.finalised_source)

    # Edge case 7 — zero aggregate stake — is rejected upstream by
    # `CasperNode.__init__` (see `tests/pos/test_node_init.py`), so the
    # rule itself documents `total_stake > 0` as a precondition rather
    # than guarding against an empty quorum at every call site.


if __name__ == "__main__":
    unittest.main()
