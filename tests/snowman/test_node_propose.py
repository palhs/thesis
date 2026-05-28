"""Round-robin proposer + slot timer (design spec §6.2, §6.3)."""
import unittest

from _helpers import build_run_harness


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


if __name__ == "__main__":
    unittest.main()
