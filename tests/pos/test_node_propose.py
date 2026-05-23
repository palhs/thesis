import unittest

from pos.messages import BlockProposalPayload
from _helpers import make_node, capturers, kickoff


class TestSlotLoop(unittest.TestCase):
    def test_start_schedules_slot_1(self):
        n = make_node(0, 4)
        cap = capturers(n)
        n._on_start(t=0.0)
        self.assertEqual(cap.timers[0][0], "slot")
        self.assertEqual(cap.timers[0][2], 1)        # payload = slot index

    def test_slot_timer_rearms_next_slot(self):
        n = make_node(0, 4)
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        rearm = [tm for tm in cap.timers if tm[0] == "slot"][-1]
        self.assertEqual(rearm[2], 2)

    def test_proposer_of_slot_broadcasts_block(self):
        # slot 1, n=4 -> proposer = 1 % 4 = 1.
        n = make_node(1, 4)
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        self.assertEqual(cap.count_broadcast("BLOCK-PROPOSAL"), 1)

    def test_non_proposer_does_not_broadcast_block(self):
        n = make_node(2, 4)                          # slot 1 proposer = 1
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        self.assertEqual(cap.count_broadcast("BLOCK-PROPOSAL"), 0)

    def test_proposer_self_records_own_block(self):
        n = make_node(1, 4)
        capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        # the proposed block is now the node's own chain head
        self.assertEqual(n.chain.head.slot, 1)
        self.assertEqual(n.chain.head.proposer_idx, 1)

    def test_block_payload_well_formed(self):
        n = make_node(1, 4, workload=[b"TX"])
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        payload = cap.broadcasts[0][1]
        self.assertIsInstance(payload, BlockProposalPayload)
        self.assertEqual(payload.slot, 1)
        self.assertEqual(payload.transactions, (b"TX",))
        self.assertEqual(payload.parent_hash, b"\x00" * 32)   # GENESIS_HASH


if __name__ == "__main__":
    unittest.main()
