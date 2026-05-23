import unittest

from pos.messages import FFGVote, BlockProposalPayload, AttestationPayload


class TestFFGVote(unittest.TestCase):
    def test_fields(self):
        v = FFGVote(source_epoch=0, source_hash=b"s" * 32,
                    target_epoch=1, target_hash=b"t" * 32)
        self.assertEqual(v.source_epoch, 0)
        self.assertEqual(v.target_epoch, 1)
        self.assertEqual(v.target_hash, b"t" * 32)

    def test_frozen(self):
        v = FFGVote(0, b"s" * 32, 1, b"t" * 32)
        with self.assertRaises(Exception):
            v.target_epoch = 9


class TestBlockProposalPayload(unittest.TestCase):
    def test_fields(self):
        b = BlockProposalPayload(slot=2, epoch=1, parent_hash=b"p" * 32,
                                 block_hash=b"b" * 32,
                                 transactions=(b"tx",), proposer_idx=2)
        self.assertEqual(b.slot, 2)
        self.assertEqual(b.transactions, (b"tx",))


class TestAttestationPayload(unittest.TestCase):
    def test_carries_ffg_vote(self):
        v = FFGVote(0, b"s" * 32, 1, b"t" * 32)
        a = AttestationPayload(slot=3, epoch=1, ffg=v, attester_idx=2)
        self.assertIs(a.ffg, v)
        self.assertEqual(a.attester_idx, 2)


if __name__ == "__main__":
    unittest.main()
