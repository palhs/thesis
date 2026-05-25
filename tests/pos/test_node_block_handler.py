import unittest

from nodes import Message
from pos import stake_weighted_proposer
from pos.chain import GENESIS_HASH, block_hash
from pos.messages import BlockProposalPayload
from _helpers import make_node, uniform_stake, capturers, kickoff


_GLOBAL_SEED = 42
_SLOT_1_PROPOSER_N4 = stake_weighted_proposer(1, uniform_stake(4), _GLOBAL_SEED)
_SLOT_2_PROPOSER_N4 = stake_weighted_proposer(2, uniform_stake(4), _GLOBAL_SEED)
_NON_PROPOSER_OF_SLOT_1 = (_SLOT_1_PROPOSER_N4 + 1) % 4


def _block_msg(src, slot, parent, *, spe=2, txs=(), bad_hash=False):
    bh = b"\xff" * 32 if bad_hash else block_hash(
        slot=slot, parent_hash=parent, proposer_idx=src, transactions=txs)
    pp = BlockProposalPayload(slot=slot, epoch=slot // spe,
                              parent_hash=parent, block_hash=bh,
                              transactions=txs, proposer_idx=src)
    return Message(src=src, dst=0, type="BLOCK-PROPOSAL", payload=pp,
                   t_sent=0.0)


class TestBlockHandler(unittest.TestCase):
    def test_valid_block_is_accepted(self):
        n = make_node(0, 4)
        capturers(n); kickoff(n)
        n.on_message(_block_msg(_SLOT_1_PROPOSER_N4, 1, GENESIS_HASH), t=1.0)
        self.assertEqual(n.chain.head.slot, 1)

    def test_block_from_non_proposer_rejected(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n.on_message(_block_msg(_NON_PROPOSER_OF_SLOT_1, 1, GENESIS_HASH),
                     t=1.0)
        reasons = [e[1]["reason"] for e in cap.events("casper_rejected")]
        self.assertIn("non_proposer", reasons)

    def test_block_with_bad_hash_rejected(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n.on_message(_block_msg(_SLOT_1_PROPOSER_N4, 1, GENESIS_HASH,
                                bad_hash=True), t=1.0)
        reasons = [e[1]["reason"] for e in cap.events("casper_rejected")]
        self.assertIn("hash_mismatch", reasons)

    def test_malformed_payload_rejected_not_crashed(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n.on_message(Message(src=1, dst=0, type="BLOCK-PROPOSAL",
                             payload=None, t_sent=0.0), t=1.0)
        reasons = [e[1]["reason"] for e in cap.events("casper_rejected")]
        self.assertIn("malformed_payload", reasons)

    def test_unknown_message_type_rejected(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n.on_message(Message(src=1, dst=0, type="WAT",
                             payload=None, t_sent=0.0), t=1.0)
        reasons = [e[1]["reason"] for e in cap.events("casper_rejected")]
        self.assertIn("unknown_type", reasons)

    def test_checkpoint_block_sets_epoch_checkpoint_hash(self):
        n = make_node(0, 4)
        capturers(n); kickoff(n)
        n.on_message(_block_msg(_SLOT_1_PROPOSER_N4, 1, GENESIS_HASH), t=1.0)
        h1 = n.chain.head.block_hash
        n.on_message(_block_msg(_SLOT_2_PROPOSER_N4, 2, h1), t=2.0)
        self.assertEqual(n.epoch_states[1].checkpoint_hash,
                         n.chain.head.block_hash)


if __name__ == "__main__":
    unittest.main()
