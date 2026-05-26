import unittest

from pos.epoch import EpochFSM, EpochState


class TestEpochState(unittest.TestCase):
    def test_starts_unjustified(self):
        es = EpochState(epoch=1)
        self.assertIs(es.state, EpochFSM.UNJUSTIFIED)
        self.assertIsNone(es.checkpoint_hash)

    def test_record_vote_accumulates_link_stake(self):
        es = EpochState(epoch=1)
        es.record_vote(source_epoch=0, attester_idx=0, stake=3.0)
        es.record_vote(source_epoch=0, attester_idx=1, stake=3.0)
        self.assertEqual(es.link_stake(0), 6.0)

    def test_dedupe_one_vote_per_attester(self):
        es = EpochState(epoch=1)
        self.assertTrue(es.record_vote(0, attester_idx=0, stake=3.0))
        # same attester again (any source) -> ignored, returns False
        self.assertFalse(es.record_vote(0, attester_idx=0, stake=3.0))
        self.assertEqual(es.link_stake(0), 3.0)

    def test_link_stake_unknown_source_is_zero(self):
        self.assertEqual(EpochState(epoch=1).link_stake(7), 0.0)


if __name__ == "__main__":
    unittest.main()
