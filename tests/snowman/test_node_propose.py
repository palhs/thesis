"""Round-robin proposer + slot timer (design spec §6.2, §6.3)."""
import unittest

from _helpers import build_run_harness, capturers, kickoff, make_node
from snowman.messages import BlockAnnouncementPayload


class TestSlotProposer(unittest.TestCase):
    def test_round_robin_proposer_for_n_4(self):
        """At n=4, slot s is proposed by node (s mod 4)."""
        logger, _, _ = build_run_harness(n=4, t_max=5.0)
        # Group announce events by (slot, proposer_idx); proposer_idx must
        # equal slot % 4 for every announced block.
        by_slot: dict[int, set[int]] = {}
        for e in logger.records:
            if e.event_type == "snowman_announced":
                by_slot.setdefault(
                    e.fields["slot"], set()).add(e.fields["proposer_idx"])
        self.assertGreater(len(by_slot), 0, "no announces observed")
        for slot, proposers in by_slot.items():
            self.assertEqual(proposers, {slot % 4},
                             f"slot {slot} proposer mismatch: {proposers}")

    def test_slot_timer_fires_each_period(self):
        """slot_duration=1.0 and t_max=4.5 should announce slots 0..3."""
        logger, _, _ = build_run_harness(n=4, t_max=4.5)
        announced = {e.fields["slot"] for e in logger.records
                     if e.event_type == "snowman_announced"}
        self.assertIn(0, announced)
        self.assertIn(1, announced)
        self.assertIn(2, announced)
        self.assertIn(3, announced)


class TestSlotIndexedWorkload(unittest.TestCase):
    """T41: `workload` is indexed by SLOT; the block at slot s carries
    workload[s] directly, regardless of which round-robin proposer node
    builds it. Empty/missing slot -> empty batch (backward-compatible)."""

    def _propose_payload(self, cap):
        """The single BLOCK-ANNOUNCEMENT payload broadcast by _propose."""
        broadcasts = [p for (ty, p, _) in cap.broadcasts
                      if ty == "BLOCK-ANNOUNCEMENT"]
        self.assertEqual(len(broadcasts), 1)
        self.assertIsInstance(broadcasts[0], BlockAnnouncementPayload)
        return broadcasts[0]

    def test_block_carries_its_slots_batch_two_proposers(self):
        # Distinct per-slot batches. Slot 1's proposer at n=4 is node 1;
        # slot 2's proposer is node 2 — two different round-robin proposers.
        workload = [
            (b"slot0-a",),
            (b"slot1-a", b"slot1-b"),
            (b"slot2-a", b"slot2-b", b"slot2-c"),
        ]
        # Node 1 proposes slot 1.
        node1 = make_node(node_id=1, n=4, workload=list(workload))
        cap1 = capturers(node1)
        kickoff(node1)
        node1._propose(slot=1, t=1.0)
        p1 = self._propose_payload(cap1)
        self.assertEqual(p1.slot, 1)
        self.assertEqual(p1.proposer_idx, 1)
        self.assertEqual(p1.transactions, workload[1])

        # Node 2 proposes slot 2 — different proposer, different slot.
        node2 = make_node(node_id=2, n=4, workload=list(workload))
        cap2 = capturers(node2)
        kickoff(node2)
        node2._propose(slot=2, t=2.0)
        p2 = self._propose_payload(cap2)
        self.assertEqual(p2.slot, 2)
        self.assertEqual(p2.proposer_idx, 2)
        self.assertEqual(p2.transactions, workload[2])

    def test_slot_past_workload_end_is_empty_batch(self):
        node = make_node(node_id=0, n=4, workload=[(b"only-slot-0",)])
        cap = capturers(node)
        kickoff(node)
        node._propose(slot=5, t=5.0)            # past the single entry
        self.assertEqual(self._propose_payload(cap).transactions, ())

    def test_no_workload_is_empty_batch(self):
        node = make_node(node_id=0, n=4, workload=None)
        cap = capturers(node)
        kickoff(node)
        node._propose(slot=0, t=1.0)
        self.assertEqual(self._propose_payload(cap).transactions, ())


if __name__ == "__main__":
    unittest.main()
