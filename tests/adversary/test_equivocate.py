"""Equivocate adversary shared helpers: partition split + conflicting payloads (T53)."""
from __future__ import annotations

import unittest

from adversary.equivocate import (
    EquivocatingCasperNode,
    EquivocatingPBFTNode,
    EquivocatingSnowmanNode,
    conflicting_bytes,
    split_recipients,
)
from nodes import Message
from pbft.digest import digest
from pbft.instance import Instance
from pos.chain import GENESIS_HASH, Block, block_hash
from pos.messages import AttestationPayload, FFGVote
from pos.node import CASPER_SLASHING, CasperNode
from snowman.block import GENESIS_ID, Block as SnowBlock, ConflictSet, hash_block
from snowman.messages import QueryPayload


class _FakeNode:
    def __init__(self, n, node_id):
        self.n, self.id = n, node_id


class TestPartition(unittest.TestCase):
    def test_split_node0_parity_groups(self):
        lo, hi = split_recipients(_FakeNode(10, 0))
        # lo = even-id peers (self 0 excluded), hi = odd-id peers.
        self.assertEqual(lo, (2, 4, 6, 8))
        self.assertEqual(hi, (1, 3, 5, 7, 9))

    def test_split_excludes_self(self):
        lo, hi = split_recipients(_FakeNode(10, 0))
        self.assertNotIn(0, lo)
        self.assertNotIn(0, hi)

    def test_split_is_pure_on_recall(self):
        node = _FakeNode(10, 0)
        self.assertEqual(split_recipients(node), split_recipients(node))

    def test_split_node5_excludes_self_partitions_peers(self):
        node = _FakeNode(10, 5)
        lo, hi = split_recipients(node)
        self.assertNotIn(5, lo)
        self.assertNotIn(5, hi)
        peers = tuple(i for i in range(10) if i != 5)
        # lo+hi together cover all peers and are disjoint (parity partition).
        self.assertEqual(tuple(sorted(lo + hi)), peers)
        self.assertEqual(set(lo) & set(hi), set())
        # lo is exactly the even-id peers, hi the odd-id peers.
        self.assertTrue(all(i % 2 == 0 for i in lo))
        self.assertTrue(all(i % 2 == 1 for i in hi))

    def test_conflicting_bytes_distinct_and_bytes(self):
        a, b = conflicting_bytes("pbft", 0, 3)
        self.assertNotEqual(a, b)
        self.assertIsInstance(a, bytes)
        self.assertIsInstance(b, bytes)

    def test_conflicting_bytes_deterministic_on_recall(self):
        self.assertEqual(conflicting_bytes("pbft", 0, 3),
                         conflicting_bytes("pbft", 0, 3))

    def test_conflicting_bytes_keyed(self):
        self.assertNotEqual(conflicting_bytes("pbft", 0, 3),
                            conflicting_bytes("pbft", 0, 4))


def _make_node(node_id=0, n=4, workload=None):
    """Build an EquivocatingPBFTNode with its outbound API replaced by
    capturing/no-op stubs (a unit-constructed node is not bound to a
    Network/Scheduler). Returns (node, sent) where sent collects
    (dst, type, payload) tuples."""
    node = EquivocatingPBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                                global_seed=0, n=n,
                                workload=list(workload or [b"x"]))
    sent: list = []
    node.send = lambda dst, type, payload, t: sent.append((dst, type, payload))
    node.set_timer = lambda *a, **k: None
    node.emit = lambda *a, **k: None
    node.broadcast = lambda *a, **k: None
    node.cancel_timer = lambda *a, **k: None
    return node, sent


class TestEquivocatingPBFT(unittest.TestCase):
    def test_primary_forks_pre_prepare(self):
        node, sent = _make_node(node_id=0, n=4, workload=[b"x"])
        node._propose(1.0)
        pps = [(dst, payload) for dst, type, payload in sent
               if type == "PRE-PREPARE"]
        lo, hi = split_recipients(node)
        # Exactly the two recipient halves got a PRE-PREPARE, disjoint and
        # covering all peers.
        lo_dsts = {dst for dst, payload in pps if dst in lo}
        hi_dsts = {dst for dst, payload in pps if dst in hi}
        self.assertEqual(lo_dsts, set(lo))
        self.assertEqual(hi_dsts, set(hi))
        self.assertEqual({dst for dst, _ in pps}, set(lo) | set(hi))
        self.assertEqual(set(lo) & set(hi), set())
        # The two halves carry DIFFERENT request_digests.
        digA = {payload.request_digest for dst, payload in pps if dst in lo}
        digB = {payload.request_digest for dst, payload in pps if dst in hi}
        self.assertEqual(len(digA), 1)
        self.assertEqual(len(digB), 1)
        self.assertNotEqual(digA, digB)
        # Each payload is internally consistent: digest(payload) == digest field.
        for _, payload in pps:
            self.assertEqual(digest(payload.request_payload),
                             payload.request_digest)

    def test_backup_forks_votes(self):
        node, sent = _make_node(node_id=1, n=4)
        reqA, reqB = conflicting_bytes("pbft", 0, 5)
        inst = Instance(view=0, seq=5)
        inst.digest = digest(reqA)
        node._broadcast_prepare(inst, 2.0)
        preps = [(dst, payload) for dst, type, payload in sent
                 if type == "PREPARE"]
        lo, hi = split_recipients(node)
        digA, digB = digest(reqA), digest(reqB)
        lo_digs = {payload.request_digest for dst, payload in preps
                   if dst in lo}
        hi_digs = {payload.request_digest for dst, payload in preps
                   if dst in hi}
        self.assertEqual(lo_digs, {digA})
        self.assertEqual(hi_digs, {digB})
        self.assertNotEqual(digA, digB)
        # self-record uses the instance's own (honest) digest.
        self.assertEqual(inst.prepares[node.id], inst.digest)


def _seed_epoch1_checkpoint(node):
    """Accept a block at slot 2 (epoch 1's checkpoint, slots_per_epoch=2) so
    `_attest(epoch=1, ...)` finds both its target (epoch 1) and source
    (epoch 0 = genesis) checkpoints."""
    bh = block_hash(slot=2, parent_hash=GENESIS_HASH, proposer_idx=0,
                    transactions=())
    block = Block(slot=2, epoch=1, parent_hash=GENESIS_HASH, block_hash=bh,
                  transactions=(), proposer_idx=0)
    node._accept_block(block, 0.0)
    return bh


def _make_casper(node_id=0, n=4):
    stake = {i: 3.0 for i in range(n)}
    node = EquivocatingCasperNode(node_id=node_id, weight=stake[node_id],
                                  endpoint=None, global_seed=0, n=n,
                                  stake_table=stake, slot_duration=1.0,
                                  slots_per_epoch=2)
    sent = []
    node.broadcast = lambda type, payload, t: sent.append((type, payload))
    node.send = lambda *a, **k: None
    node.set_timer = lambda *a, **k: None
    node.emit = lambda *a, **k: None
    node.cancel_timer = lambda *a, **k: None
    return node, sent


def _make_honest_casper(node_id=0, n=4):
    stake = {i: 3.0 for i in range(n)}
    node = CasperNode(node_id=node_id, weight=stake[node_id],
                      endpoint=None, global_seed=0, n=n,
                      stake_table=stake, slot_duration=1.0,
                      slots_per_epoch=2)
    events = []
    node.emit = lambda type, fields, t: events.append((type, fields))
    node.broadcast = lambda *a, **k: None
    node.send = lambda *a, **k: None
    node.set_timer = lambda *a, **k: None
    node.cancel_timer = lambda *a, **k: None
    return node, events


class TestEquivocatingFFG(unittest.TestCase):
    def test_double_vote_same_epoch_diff_hash(self):
        node, sent = _make_casper(node_id=0, n=4)
        _seed_epoch1_checkpoint(node)
        node._attest(epoch=1, slot=3, t=5.0)
        atts = [payload for type, payload in sent if type == "ATTESTATION"]
        self.assertEqual(len(atts), 2)
        self.assertEqual(atts[0].ffg.target_epoch, atts[1].ffg.target_epoch)
        self.assertEqual(atts[0].attester_idx, atts[1].attester_idx)
        self.assertNotEqual(atts[0].ffg.target_hash, atts[1].ffg.target_hash)

    def test_downstream_node_slashes(self):
        adv, sent = _make_casper(node_id=0, n=4)
        _seed_epoch1_checkpoint(adv)
        adv._attest(epoch=1, slot=3, t=5.0)
        atts = [payload for type, payload in sent if type == "ATTESTATION"]
        self.assertEqual(len(atts), 2)

        honest, events = _make_honest_casper(node_id=1, n=4)
        for ap in atts:
            honest._handle_attestation(
                Message(src=0, dst=1, type="ATTESTATION", payload=ap,
                        t_sent=5.0), 5.0)
        self.assertTrue(any(type == CASPER_SLASHING for type, _ in events))
        self.assertGreater(honest.slashable_stake_fraction(), 0.0)


def _make_snowman(node_id=0, n=4):
    """Build an EquivocatingSnowmanNode with capturing/no-op outbound stubs.
    Returns (node, sent) where sent collects (dst, type, payload) tuples."""
    node = EquivocatingSnowmanNode(node_id=node_id, weight=1.0, endpoint=None,
                                   global_seed=0, n=n, slot_duration=1.0,
                                   beta=15)
    sent: list = []
    node.send = lambda dst, type, payload, t: sent.append((dst, type, payload))
    node.set_timer = lambda *a, **k: None
    node.emit = lambda *a, **k: None
    node.broadcast = lambda *a, **k: None
    node.cancel_timer = lambda *a, **k: None
    return node, sent


class TestEquivocatingSnowman(unittest.TestCase):
    def test_proposer_forks_announcement(self):
        node, sent = _make_snowman(node_id=0, n=4)
        node._propose(slot=4, t=1.0)            # slot 4 % 4 == 0 -> node 0 proposes
        anns = [(dst, payload) for dst, type, payload in sent
                if type == "BLOCK-ANNOUNCEMENT"]
        lo, hi = split_recipients(node)
        lo_dsts = {dst for dst, _ in anns if dst in lo}
        hi_dsts = {dst for dst, _ in anns if dst in hi}
        self.assertEqual(lo_dsts, set(lo))
        self.assertEqual(hi_dsts, set(hi))
        self.assertEqual({dst for dst, _ in anns}, set(lo) | set(hi))
        self.assertEqual(set(lo) & set(hi), set())
        # The two halves carry DIFFERENT block_ids, same slot/parent_id.
        bidA = {p.block_id for dst, p in anns if dst in lo}
        bidB = {p.block_id for dst, p in anns if dst in hi}
        self.assertEqual(len(bidA), 1)
        self.assertEqual(len(bidB), 1)
        self.assertNotEqual(bidA, bidB)
        slots = {p.slot for _, p in anns}
        parents = {p.parent_id for _, p in anns}
        self.assertEqual(slots, {4})
        self.assertEqual(parents, {GENESIS_ID})

    def test_lying_responder_returns_non_preference(self):
        node, sent = _make_snowman(node_id=0, n=4)
        parent_id = GENESIS_ID
        cs = ConflictSet(parent_id=parent_id)
        bid1 = hash_block(slot=1, parent_id=parent_id, proposer_idx=2,
                          transactions=(b"one",))
        bid2 = hash_block(slot=1, parent_id=parent_id, proposer_idx=2,
                          transactions=(b"two",))
        cs.add_block(SnowBlock(block_id=bid1, parent_id=parent_id, slot=1,
                               proposer_idx=2, transactions=(b"one",)))
        cs.add_block(SnowBlock(block_id=bid2, parent_id=parent_id, slot=1,
                               proposer_idx=2, transactions=(b"two",)))
        cs.preference = bid1
        node.conflict_sets[parent_id] = cs
        node._handle_query(
            Message(src=2, dst=node.id, type="QUERY",
                    payload=QueryPayload(request_id=7, block_id=bid1),
                    t_sent=1.0), 1.0)
        resps = [p for dst, type, p in sent if type == "QUERY-RESPONSE"]
        self.assertEqual(len(resps), 1)
        self.assertIn(resps[0].preferred_block_id, cs.members)
        self.assertNotEqual(resps[0].preferred_block_id, cs.preference)


if __name__ == "__main__":
    unittest.main()
