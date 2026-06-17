"""Audit finding #3 — Casper FFG accountable safety (T70).

Casper FFG has two slashable offences (Casper paper §3, "Commandments"):

  1. DOUBLE VOTE:    two distinct votes by one validator with the same
                     target epoch.
  2. SURROUND VOTE:  votes (s1,t1) and (s2,t2) by one validator with
                     s1 < s2 < t2 < t1 (one strictly surrounds the other).

The pre-fix `EpochState.record_vote` dedup'd by attester index alone, so a
validator's SECOND, CONFLICTING vote for the same target epoch was swallowed
exactly like a duplicate delivery — neither offence was detectable. These
tests pin the fixed behaviour: exact duplicates stay idempotent, conflicting
votes are flagged via a `casper_slashing` event, and the slashable-stake
fraction is surfaced.

Mirrors tests/pos/test_node_finality.py drive style: populate the chain off
the slot loop, then deliver crafted ATTESTATION messages.
"""
import unittest

from nodes import Message
from pos.chain import GENESIS_HASH, block_hash
from pos.epoch import EpochState, VoteStatus
from pos.messages import AttestationPayload, BlockProposalPayload, FFGVote
from pos.node import CASPER_SLASHING
from _helpers import make_node, capturers, kickoff


def _att_msg(src, source_epoch, source_hash, target_epoch, target_hash):
    ffg = FFGVote(source_epoch, source_hash, target_epoch, target_hash)
    pp = AttestationPayload(slot=0, epoch=target_epoch, ffg=ffg,
                            attester_idx=src)
    return Message(src=src, dst=0, type="ATTESTATION", payload=pp,
                   t_sent=0.0)


def _populate_chain(node, upto_epoch):
    """Deliver BLOCK-PROPOSALs so `node`'s chain has every checkpoint up to
    `upto_epoch`. Returns {epoch: checkpoint_hash}. Off the slot loop, so no
    self-attestations are filed."""
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


def _fake_cp(tag: bytes) -> bytes:
    """A 32-byte checkpoint hash distinct from any real chain hash."""
    return tag * 32


class TestEpochStateVoteStatus(unittest.TestCase):
    """R3.1 — record_vote distinguishes NEW / DUPLICATE / CONFLICT."""

    def test_first_vote_is_new(self):
        es = EpochState(epoch=1)
        st = es.record_vote(source_epoch=0, attester_idx=0, stake=3.0,
                            source_hash=_fake_cp(b"s"), target_hash=_fake_cp(b"t"))
        self.assertIs(st, VoteStatus.NEW)
        self.assertEqual(es.link_stake(0), 3.0)

    def test_exact_duplicate_is_idempotent(self):
        es = EpochState(epoch=1)
        es.record_vote(source_epoch=0, attester_idx=0, stake=3.0,
                       source_hash=_fake_cp(b"s"), target_hash=_fake_cp(b"t"))
        st = es.record_vote(source_epoch=0, attester_idx=0, stake=3.0,
                            source_hash=_fake_cp(b"s"), target_hash=_fake_cp(b"t"))
        self.assertIs(st, VoteStatus.DUPLICATE)
        self.assertEqual(es.link_stake(0), 3.0)   # no double-count

    def test_conflicting_target_hash_is_conflict(self):
        es = EpochState(epoch=1)
        es.record_vote(source_epoch=0, attester_idx=0, stake=3.0,
                       source_hash=_fake_cp(b"s"), target_hash=_fake_cp(b"t"))
        st = es.record_vote(source_epoch=0, attester_idx=0, stake=3.0,
                            source_hash=_fake_cp(b"s"), target_hash=_fake_cp(b"u"))
        self.assertIs(st, VoteStatus.CONFLICT)
        # conflicting second vote must NOT inflate link stake
        self.assertEqual(es.link_stake(0), 3.0)

    def test_conflicting_source_epoch_is_conflict(self):
        es = EpochState(epoch=2)
        es.record_vote(source_epoch=0, attester_idx=0, stake=3.0,
                       source_hash=_fake_cp(b"a"), target_hash=_fake_cp(b"t"))
        st = es.record_vote(source_epoch=1, attester_idx=0, stake=3.0,
                            source_hash=_fake_cp(b"b"), target_hash=_fake_cp(b"t"))
        self.assertIs(st, VoteStatus.CONFLICT)

    def test_backward_compatible_default_hashes(self):
        # legacy 3-arg call still works (honest-path callers pre-fix shape)
        es = EpochState(epoch=1)
        self.assertIs(es.record_vote(0, attester_idx=0, stake=3.0),
                      VoteStatus.NEW)
        self.assertIs(es.record_vote(0, attester_idx=0, stake=3.0),
                      VoteStatus.DUPLICATE)


class TestDoubleVote(unittest.TestCase):
    """R3.2 — double vote -> casper_slashing(double_vote)."""

    def _setup(self, n_val=4, upto_epoch=2):
        n = make_node(0, n_val, slots_per_epoch=2)
        capturers(n); kickoff(n)
        cps = _populate_chain(n, upto_epoch=upto_epoch)
        cap = capturers(n)
        return n, cap, cps

    def test_double_vote_emits_slashing(self):
        n, cap, cps = self._setup()
        other = _fake_cp(b"X")   # a conflicting target-1 checkpoint
        n.on_message(_att_msg(1, 0, cps[0], 1, cps[1]), t=10.0)
        n.on_message(_att_msg(1, 0, cps[0], 1, other), t=11.0)   # double
        slashings = cap.events(CASPER_SLASHING)
        self.assertEqual(len(slashings), 1)
        f = slashings[0][1]
        self.assertEqual(f["reason"], "double_vote")
        self.assertEqual(f["attester_idx"], 1)
        self.assertEqual(f["target_epoch"], 1)

    def test_exact_duplicate_does_not_slash(self):
        n, cap, cps = self._setup()
        n.on_message(_att_msg(1, 0, cps[0], 1, cps[1]), t=10.0)
        n.on_message(_att_msg(1, 0, cps[0], 1, cps[1]), t=11.0)  # exact dup
        self.assertEqual(len(cap.events(CASPER_SLASHING)), 0)


class TestSurroundVote(unittest.TestCase):
    """R3.3 — surround vote -> casper_slashing(surround_vote)."""

    def _setup(self, n_val=4, upto_epoch=4):
        n = make_node(0, n_val, slots_per_epoch=2)
        capturers(n); kickoff(n)
        cps = _populate_chain(n, upto_epoch=upto_epoch)
        cap = capturers(n)
        return n, cap, cps

    def test_surround_emits_slashing(self):
        n, cap, cps = self._setup()
        # wide link (s1=1, t1=4) then inner link (s2=2, t2=3): 1<2<3<4
        n.on_message(_att_msg(1, 1, cps[1], 4, cps[4]), t=10.0)
        n.on_message(_att_msg(1, 2, cps[2], 3, cps[3]), t=11.0)
        slashings = cap.events(CASPER_SLASHING)
        reasons = [s[1]["reason"] for s in slashings]
        self.assertIn("surround_vote", reasons)
        sv = [s[1] for s in slashings if s[1]["reason"] == "surround_vote"][0]
        self.assertEqual(sv["attester_idx"], 1)

    def test_surround_both_orderings(self):
        # inner first, then wide — must still detect.
        n, cap, cps = self._setup()
        n.on_message(_att_msg(2, 2, cps[2], 3, cps[3]), t=10.0)
        n.on_message(_att_msg(2, 1, cps[1], 4, cps[4]), t=11.0)
        reasons = [s[1]["reason"] for s in cap.events(CASPER_SLASHING)]
        self.assertIn("surround_vote", reasons)

    def test_nested_non_surround_does_not_slash(self):
        # adjacent, non-surrounding links by one attester: (1,2) then (2,3).
        # s1<s2 but t1<t2 (no surround), distinct targets (no double vote).
        n, cap, cps = self._setup()
        n.on_message(_att_msg(1, 1, cps[1], 2, cps[2]), t=10.0)
        n.on_message(_att_msg(1, 2, cps[2], 3, cps[3]), t=11.0)
        self.assertEqual(len(cap.events(CASPER_SLASHING)), 0)


class TestSlashableStakeFraction(unittest.TestCase):
    """R3.4 — slashable-stake fraction computed + surfaced."""

    def _setup(self, n_val=4, upto_epoch=4):
        n = make_node(0, n_val, slots_per_epoch=2)
        capturers(n); kickoff(n)
        cps = _populate_chain(n, upto_epoch=upto_epoch)
        cap = capturers(n)
        return n, cap, cps

    def test_fraction_zero_on_honest(self):
        n, _, cps = self._setup()
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        self.assertEqual(n.slashable_stake_fraction(), 0.0)

    def test_fraction_after_one_double_voter(self):
        # n=4 uniform stake 3.0 each, total 12. One offender -> 3/12 = 0.25.
        n, cap, cps = self._setup()
        n.on_message(_att_msg(1, 0, cps[0], 1, cps[1]), t=10.0)
        n.on_message(_att_msg(1, 0, cps[0], 1, _fake_cp(b"Z")), t=11.0)
        self.assertAlmostEqual(n.slashable_stake_fraction(), 0.25)
        # surfaced on the event too
        f = cap.events(CASPER_SLASHING)[0][1]
        self.assertAlmostEqual(f["slashable_stake_fraction"], 0.25)

    def test_fraction_counts_offender_once(self):
        # same offender slashes twice -> still one offender -> 0.25.
        n, cap, cps = self._setup()
        n.on_message(_att_msg(1, 0, cps[0], 1, cps[1]), t=10.0)
        n.on_message(_att_msg(1, 0, cps[0], 1, _fake_cp(b"Z")), t=11.0)
        n.on_message(_att_msg(1, 1, cps[1], 4, cps[4]), t=12.0)
        n.on_message(_att_msg(1, 2, cps[2], 3, cps[3]), t=13.0)
        self.assertAlmostEqual(n.slashable_stake_fraction(), 0.25)


class TestHonestPathUnchanged(unittest.TestCase):
    """R3.5 — honest-path votes never slash and finalisation still works."""

    def test_no_slashing_on_clean_finalisation(self):
        n = make_node(0, 4, slots_per_epoch=2)
        capturers(n); kickoff(n)
        cps = _populate_chain(n, upto_epoch=3)
        cap = capturers(n)
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 0, cps[0], 1, cps[1]), t=10.0)
        for src in (1, 2, 3):
            n.on_message(_att_msg(src, 1, cps[1], 2, cps[2]), t=11.0)
        self.assertEqual(len(cap.events(CASPER_SLASHING)), 0)
        self.assertEqual(n.slashable_stake_fraction(), 0.0)
        self.assertEqual(len(cap.events("decided")), 1)


if __name__ == "__main__":
    unittest.main()
