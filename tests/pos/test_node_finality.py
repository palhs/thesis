import unittest

from nodes import Message
from pos.chain import GENESIS_HASH, block_hash
from pos.epoch import EpochFSM
from pos.messages import AttestationPayload, BlockProposalPayload, FFGVote
from _helpers import make_node, capturers, kickoff


def _att_msg(src, source_epoch, source_hash, target_epoch, target_hash):
    ffg = FFGVote(source_epoch, source_hash, target_epoch, target_hash)
    pp = AttestationPayload(slot=0, epoch=target_epoch, ffg=ffg,
                            attester_idx=src)
    return Message(src=src, dst=0, type="ATTESTATION", payload=pp,
                   t_sent=0.0)


def _populate_chain(node, upto_epoch):
    """Construct and deliver BLOCK-PROPOSALs for slots 1..(upto_epoch+1)*spe
    so `node`'s chain has every checkpoint up to `upto_epoch`. Returns the
    {epoch: checkpoint_hash} map. Bypasses the slot loop (so no
    self-attestations are filed during the drive)."""
    spe = node.slots_per_epoch
    last_slot = (upto_epoch + 1) * spe
    parent = GENESIS_HASH
    hashes = {0: GENESIS_HASH}
    for s in range(1, last_slot + 1):
        proposer = node._proposer_of(s)
        bh = block_hash(slot=s, parent_hash=parent, proposer_idx=proposer,
                        transactions=())
        pp = BlockProposalPayload(slot=s, epoch=s // spe,
                                  parent_hash=parent, block_hash=bh,
                                  transactions=(), proposer_idx=proposer)
        msg = Message(src=proposer, dst=node.id, type="BLOCK-PROPOSAL",
                      payload=pp, t_sent=0.0)
        node.on_message(msg, t=float(s))
        parent = bh
        epoch = s // spe
        if s == epoch * spe:
            hashes[epoch] = bh
    return hashes


class TestFinality(unittest.TestCase):
    def _setup(self, n_val=4, stake_table=None, upto_epoch=2):
        """Build a node, kick it off, populate its chain, return (node, cap,
        cps). The capture is fresh — populate happens before capture so
        block-accepted events from the drive do not leak in."""
        n = make_node(0, n_val, slots_per_epoch=2, stake_table=stake_table)
        capturers(n); kickoff(n)              # cap discarded; kickoff to RUNNING
        cps = _populate_chain(n, upto_epoch=upto_epoch)
        cap = capturers(n)                    # fresh capture after drive
        return n, cap, cps

    def test_supermajority_justifies_epoch(self):
        # n=4 total stake 12, 2/3 = 8. 3 peers x 3.0 = 9 -> justified.
        n, _, cps = self._setup(n_val=4, upto_epoch=2)
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        self.assertIs(n.epoch_states[1].state, EpochFSM.JUSTIFIED)

    def test_one_vote_short_does_not_justify(self):
        n, _, cps = self._setup(n_val=4, upto_epoch=2)
        for src in (1, 2):                       # 2 x 3 = 6 < 8
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        self.assertIs(n.epoch_states[1].state, EpochFSM.UNJUSTIFIED)

    def test_two_links_finalise_and_emit_decided(self):
        n, cap, cps = self._setup(n_val=4, upto_epoch=3)
        # link <0,1>: justifies epoch 1
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        # link <1,2>: justifies epoch 2 AND finalises epoch 1
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 1, cps[1], 2, cps[2]), t=11.0)
        self.assertIs(n.epoch_states[1].state, EpochFSM.FINALISED)
        self.assertIs(n.epoch_states[2].state, EpochFSM.JUSTIFIED)
        decided = cap.events("decided")
        self.assertEqual(len(decided), 1)
        self.assertEqual(decided[0][1]["instance_id"], 1)
        self.assertEqual(decided[0][1]["value"], cps[1].hex())

    def test_decided_emitted_once_per_epoch(self):
        n, cap, cps = self._setup(n_val=4, upto_epoch=3)
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 1, cps[1], 2, cps[2]), t=11.0)
        # a stray extra vote on the <1,2> link must not re-finalise epoch 1
        n.on_message(_att_msg(0, 1, cps[1], 2, cps[2]), t=12.0)
        self.assertEqual(len(cap.events("decided")), 1)

    def test_attester_outside_set_rejected(self):
        n, cap, cps = self._setup(n_val=4, upto_epoch=2)
        bad = _att_msg(9, 0, cps[0], 1, cps[1])      # attester_idx 9 >= n
        n.on_message(bad, t=10.0)
        self.assertIn("attester_out_of_range",
                      [e[1]["reason"] for e in cap.events("casper_rejected")])

    def test_non_uniform_stake_justifies_on_stake(self):
        # stakes 9,1,1,1 (total 12, 2/3 = 8). Node 0 alone (stake 9) > 8.
        st = {0: 9.0, 1: 1.0, 2: 1.0, 3: 1.0}
        # Use the test node = node 1 (stake 1) so we can deliver an
        # attestation from peer 0 (stake 9) without dedupe interference.
        n = make_node(1, 4, slots_per_epoch=2, stake_table=st)
        capturers(n); kickoff(n)
        cps = _populate_chain(n, upto_epoch=2)
        n.on_message(_att_msg(0, 0, cps[0], 1, cps[1]), t=10.0)
        self.assertIs(n.epoch_states[1].state, EpochFSM.JUSTIFIED)


if __name__ == "__main__":
    unittest.main()
