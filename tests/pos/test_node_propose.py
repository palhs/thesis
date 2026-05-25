import unittest

from pos import stake_weighted_proposer
from pos.messages import BlockProposalPayload
from _helpers import make_node, uniform_stake, capturers, kickoff


# Stable across this module: tests build nodes with the helper's defaults
# (global_seed=42, uniform_stake(n)). The T33 selection rule depends on
# those values, so derive the slot-1 proposer once.
_GLOBAL_SEED = 42
_SLOT_1_PROPOSER_N4 = stake_weighted_proposer(1, uniform_stake(4), _GLOBAL_SEED)
_NON_PROPOSER_N4 = (_SLOT_1_PROPOSER_N4 + 1) % 4


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
        n = make_node(_SLOT_1_PROPOSER_N4, 4)
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        self.assertEqual(cap.count_broadcast("BLOCK-PROPOSAL"), 1)

    def test_non_proposer_does_not_broadcast_block(self):
        n = make_node(_NON_PROPOSER_N4, 4)
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        self.assertEqual(cap.count_broadcast("BLOCK-PROPOSAL"), 0)

    def test_proposer_self_records_own_block(self):
        n = make_node(_SLOT_1_PROPOSER_N4, 4)
        capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        # the proposed block is now the node's own chain head
        self.assertEqual(n.chain.head.slot, 1)
        self.assertEqual(n.chain.head.proposer_idx, _SLOT_1_PROPOSER_N4)

    def test_block_payload_well_formed(self):
        n = make_node(_SLOT_1_PROPOSER_N4, 4, workload=[b"TX"])
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        payload = cap.broadcasts[0][1]
        self.assertIsInstance(payload, BlockProposalPayload)
        self.assertEqual(payload.slot, 1)
        self.assertEqual(payload.transactions, (b"TX",))
        self.assertEqual(payload.parent_hash, b"\x00" * 32)   # GENESIS_HASH


if __name__ == "__main__":
    unittest.main()
