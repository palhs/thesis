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
        # T41: workload is indexed by SLOT, each element a batch tuple.
        # slot 0 = genesis (no batch); slot 1's batch is workload[1].
        n = make_node(_SLOT_1_PROPOSER_N4, 4,
                      workload=[(), (b"TX",)])
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        payload = cap.broadcasts[0][1]
        self.assertIsInstance(payload, BlockProposalPayload)
        self.assertEqual(payload.slot, 1)
        self.assertEqual(payload.transactions, (b"TX",))
        self.assertEqual(payload.parent_hash, b"\x00" * 32)   # GENESIS_HASH

    def test_block_carries_slot_indexed_batch(self):
        # T41 slot-alignment: a block proposed at slot s carries exactly
        # workload[s] (the whole batch), regardless of which node proposes.
        # Two different proposers at two different slots each read their
        # own slot's batch — NOT a sequentially popped position.
        wl = [(), (b"a0",), (b"b0", b"b1"), (), (b"d0",)]
        # Proposer of slot 1 reads workload[1].
        p1 = stake_weighted_proposer(1, uniform_stake(4), _GLOBAL_SEED)
        n1 = make_node(p1, 4, workload=list(wl))
        cap1 = capturers(n1); kickoff(n1)
        n1._on_timer("slot", 1, t=1.0)
        self.assertEqual(cap1.broadcasts[0][1].transactions, (b"a0",))
        # Proposer of slot 4 reads workload[4] — a different node, a
        # non-contiguous slot. Pop-based logic would have returned the
        # wrong (earlier) batch here.
        p4 = stake_weighted_proposer(4, uniform_stake(4), _GLOBAL_SEED)
        n4 = make_node(p4, 4, workload=list(wl))
        cap4 = capturers(n4); kickoff(n4)
        n4._on_timer("slot", 4, t=4.0)
        self.assertEqual(cap4.broadcasts[0][1].transactions, (b"d0",))
        # Sanity: the two proposers picked are distinct slots, and the
        # batch read matches workload index, not call order.
        self.assertEqual(n4.chain.head.transactions, (b"d0",))

    def test_workload_shorter_than_slot_yields_empty_block(self):
        # Backward-compatible: slot beyond the workload list -> empty block.
        p1 = stake_weighted_proposer(1, uniform_stake(4), _GLOBAL_SEED)
        n = make_node(p1, 4, workload=[(), (b"only-slot-1",)])
        cap = capturers(n); kickoff(n)
        # Force a proposal at a slot past the end of the workload list.
        # Use the slot whose proposer is p1 if available; fall back to
        # asserting the empty-block path directly via _propose.
        n._propose(slot=99, epoch=49, t=99.0)
        self.assertEqual(cap.broadcasts[0][1].transactions, ())

    def test_no_workload_yields_empty_block(self):
        p1 = stake_weighted_proposer(1, uniform_stake(4), _GLOBAL_SEED)
        n = make_node(p1, 4, workload=None)
        cap = capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        self.assertEqual(cap.broadcasts[0][1].transactions, ())


if __name__ == "__main__":
    unittest.main()
