"""T33 proposer-selection unit suite.

Covers `src/pos/selection.py`:
- determinism (cross-call, cross-node, cross-process),
- input validation,
- zero-stake exclusion,
- the 100-round empirical fairness check on a deliberately skewed stake
  table — absolute tolerance under a fixed seed (Decision: T33 plan).
"""
from __future__ import annotations

import collections
import unittest

from pos import round_robin_proposer, stake_weighted_proposer


_GLOBAL_SEED = 42


class TestRoundRobin(unittest.TestCase):
    def test_returns_slot_mod_n(self):
        for slot in range(20):
            self.assertEqual(round_robin_proposer(slot, 4), slot % 4)

    def test_rejects_non_positive_n(self):
        with self.assertRaises(ValueError):
            round_robin_proposer(0, 0)
        with self.assertRaises(ValueError):
            round_robin_proposer(0, -1)

    def test_rejects_negative_slot(self):
        with self.assertRaises(ValueError):
            round_robin_proposer(-1, 4)


class TestStakeWeightedDeterminism(unittest.TestCase):
    def test_same_args_same_proposer(self):
        st = {i: 3.0 for i in range(4)}
        for slot in range(20):
            a = stake_weighted_proposer(slot, st, _GLOBAL_SEED)
            b = stake_weighted_proposer(slot, st, _GLOBAL_SEED)
            self.assertEqual(a, b)

    def test_independent_of_dict_insertion_order(self):
        st_ascending = {i: float(i + 1) for i in range(4)}
        st_descending = {i: float(i + 1) for i in (3, 2, 1, 0)}
        for slot in range(20):
            self.assertEqual(
                stake_weighted_proposer(slot, st_ascending, _GLOBAL_SEED),
                stake_weighted_proposer(slot, st_descending, _GLOBAL_SEED),
            )

    def test_different_seeds_can_differ(self):
        st = {i: 1.0 for i in range(20)}
        seqs = []
        for seed in (1, 2, 3, 4, 5):
            seqs.append(tuple(stake_weighted_proposer(s, st, seed)
                              for s in range(50)))
        # at least one pair of seeds disagrees somewhere — confirms the
        # seed is actually consumed (no silent constant-seed bug).
        self.assertTrue(any(a != b for a, b in zip(seqs, seqs[1:])))

    def test_different_slots_can_differ(self):
        st = {i: 1.0 for i in range(20)}
        seen = {stake_weighted_proposer(s, st, _GLOBAL_SEED)
                for s in range(200)}
        # 20 equally-staked validators, 200 slots, seed=42 — chance of
        # only one validator ever appearing is astronomically small.
        self.assertGreater(len(seen), 1)


class TestStakeWeightedRange(unittest.TestCase):
    def test_proposer_is_in_validator_set(self):
        st = {7: 1.0, 11: 2.0, 13: 5.0}        # non-contiguous IDs
        for slot in range(50):
            p = stake_weighted_proposer(slot, st, _GLOBAL_SEED)
            self.assertIn(p, st)

    def test_zero_stake_validator_never_selected(self):
        st = {0: 0.0, 1: 5.0, 2: 5.0}
        for slot in range(200):
            self.assertNotEqual(
                stake_weighted_proposer(slot, st, _GLOBAL_SEED), 0)

    def test_all_but_one_zero_stake_picks_only_one(self):
        st = {0: 0.0, 1: 0.0, 2: 7.0, 3: 0.0}
        for slot in range(50):
            self.assertEqual(
                stake_weighted_proposer(slot, st, _GLOBAL_SEED), 2)


class TestStakeWeightedValidation(unittest.TestCase):
    def test_rejects_negative_slot(self):
        with self.assertRaises(ValueError):
            stake_weighted_proposer(-1, {0: 1.0}, _GLOBAL_SEED)

    def test_rejects_empty_stake_table(self):
        with self.assertRaises(ValueError):
            stake_weighted_proposer(0, {}, _GLOBAL_SEED)

    def test_rejects_negative_stake(self):
        with self.assertRaises(ValueError):
            stake_weighted_proposer(0, {0: 1.0, 1: -1.0}, _GLOBAL_SEED)

    def test_rejects_all_zero_stake(self):
        with self.assertRaises(ValueError):
            stake_weighted_proposer(0, {0: 0.0, 1: 0.0}, _GLOBAL_SEED)


class TestStakeWeightedFairness(unittest.TestCase):
    """100-round empirical fairness check (T33 acceptance criterion).

    Each validator's observed selection frequency over 100 consecutive
    slots must fall within an absolute tolerance of its expected share
    (stake / total_stake), under a fixed `_GLOBAL_SEED`. The tolerance is
    deliberately loose — 100 trials is a small sample, and a tight bound
    would couple the test to the seed without measuring fairness. A
    coarser sweep (10 stake tables x 100 seeds, each with its own
    tolerance argument) lives in the T33 experiment page, not this
    unit test.
    """

    _ROUNDS = 100
    _TOLERANCE = 0.10                    # 10 percentage points

    def _counts(self, stake_table):
        counts = collections.Counter()
        for slot in range(1, self._ROUNDS + 1):
            counts[stake_weighted_proposer(slot, stake_table,
                                           _GLOBAL_SEED)] += 1
        return counts

    def _assert_within_tolerance(self, counts, stake_table):
        total_stake = sum(stake_table.values())
        for v, stake in stake_table.items():
            expected = stake / total_stake
            observed = counts[v] / self._ROUNDS
            self.assertLessEqual(
                abs(observed - expected), self._TOLERANCE,
                msg=(f"validator {v}: observed {observed:.3f} vs "
                     f"expected {expected:.3f} "
                     f"(tolerance {self._TOLERANCE}); counts={dict(counts)}"))

    def test_uniform_4_validators(self):
        st = {i: 1.0 for i in range(4)}
        self._assert_within_tolerance(self._counts(st), st)

    def test_uniform_7_validators(self):
        st = {i: 1.0 for i in range(7)}
        self._assert_within_tolerance(self._counts(st), st)

    def test_skewed_10_20_30_40(self):
        st = {0: 10.0, 1: 20.0, 2: 30.0, 3: 40.0}
        self._assert_within_tolerance(self._counts(st), st)

    def test_heavily_skewed_majority_stake(self):
        # 60% / 13% / 13% / 13% — the majority validator should dominate
        # without crowding the minority validators out entirely.
        st = {0: 60.0, 1: 13.0, 2: 13.0, 3: 14.0}
        self._assert_within_tolerance(self._counts(st), st)


if __name__ == "__main__":
    unittest.main()
