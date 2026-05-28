"""BLOCK-ANNOUNCEMENT handling (design spec §6.3)."""
import unittest

from _helpers import build_run_harness, capturers, kickoff, make_node
from nodes.message import Message
from snowman.block import GENESIS_ID, hash_block
from snowman.messages import BlockAnnouncementPayload


class TestAnnounceHarness(unittest.TestCase):
    def test_all_nodes_record_announce_under_harness(self):
        logger, _, nodes = build_run_harness(n=4, t_max=1.5)
        # Slot 0 fires at t=1.0; every node records the announce.
        for node in nodes.values():
            self.assertGreaterEqual(len(node.conflict_sets), 1,
                                    f"node {node.id} has no conflict sets")


class TestAnnounceUnit(unittest.TestCase):
    def test_malformed_payload_is_rejected(self):
        node = make_node(node_id=0, n=4)
        cap = capturers(node)
        kickoff(node)
        bad = Message(src=1, dst=0, type="BLOCK-ANNOUNCEMENT",
                      payload="not-a-payload", t_sent=0.0)
        node.on_message(bad, t=0.5)
        rejected = cap.events("snowman_rejected")
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0][1]["reason"], "malformed_payload")

    def test_announce_creates_conflict_set_and_arms_poll(self):
        node = make_node(node_id=0, n=4)
        cap = capturers(node)
        kickoff(node)
        block_id = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=1,
                              transactions=())
        payload = BlockAnnouncementPayload(
            slot=1, block_id=block_id, parent_id=GENESIS_ID,
            transactions=(), proposer_idx=1)
        msg = Message(src=1, dst=0, type="BLOCK-ANNOUNCEMENT",
                      payload=payload, t_sent=0.0)
        node.on_message(msg, t=1.0)
        # ConflictSet created, block added, snowman_announced emitted.
        self.assertIn(GENESIS_ID, node.conflict_sets)
        cs = node.conflict_sets[GENESIS_ID]
        self.assertIn(block_id, cs.members)
        self.assertEqual(cs.preference, block_id)
        self.assertEqual(cap.count("snowman_announced"), 1)
        # Poll timer armed.
        poll_timers = [tid for (tid, *_) in cap.timers
                       if isinstance(tid, tuple) and tid[0] == "poll"]
        self.assertEqual(poll_timers, [("poll", block_id)])

    def test_duplicate_announce_is_idempotent(self):
        node = make_node(node_id=0, n=4)
        cap = capturers(node)
        kickoff(node)
        block_id = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=1,
                              transactions=())
        payload = BlockAnnouncementPayload(
            slot=1, block_id=block_id, parent_id=GENESIS_ID,
            transactions=(), proposer_idx=1)
        msg = Message(src=1, dst=0, type="BLOCK-ANNOUNCEMENT",
                      payload=payload, t_sent=0.0)
        node.on_message(msg, t=1.0)
        node.on_message(msg, t=1.0)
        # Only one announce event; conflict-set membership unchanged.
        self.assertEqual(cap.count("snowman_announced"), 1)
        cs = node.conflict_sets[GENESIS_ID]
        self.assertEqual(len(cs.members), 1)


if __name__ == "__main__":
    unittest.main()
