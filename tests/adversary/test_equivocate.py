"""Equivocate adversary shared helpers: partition split + conflicting payloads (T53)."""
from __future__ import annotations

import unittest

from adversary.equivocate import (
    EquivocatingPBFTNode,
    conflicting_bytes,
    split_recipients,
)
from pbft.digest import digest
from pbft.instance import Instance


class _FakeNode:
    def __init__(self, n, node_id):
        self.n, self.id = n, node_id


class TestPartition(unittest.TestCase):
    def test_split_node0_exact_halves(self):
        lo, hi = split_recipients(_FakeNode(10, 0))
        self.assertEqual(lo, (1, 2, 3, 4))
        self.assertEqual(hi, (5, 6, 7, 8, 9))

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
        # lo+hi together cover all peers, disjoint, sizes differ by <= 1.
        self.assertEqual(tuple(sorted(lo + hi)), peers)
        self.assertEqual(set(lo) & set(hi), set())
        self.assertLessEqual(abs(len(lo) - len(hi)), 1)

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


if __name__ == "__main__":
    unittest.main()
