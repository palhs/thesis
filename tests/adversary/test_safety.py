"""Tests for the cross-node safety reducer (T53, Task 7).

Constructs real EventRecords (frozen dataclass: t, node_id, event_type,
seq, fields) and checks the safety signals derived over honest nodes only.
"""
import unittest

from event_log import EventRecord
from pos.node import CASPER_SLASHING

from adversary.safety import safety_signals


def _decided(node_id, instance_id, value, t=1.0, seq=0):
    return EventRecord(t, node_id, "decided", seq,
                       {"value": value, "instance_id": instance_id, "t": t})


def _slashing(node_id, frac, t=1.0, seq=0):
    return EventRecord(t, node_id, CASPER_SLASHING, seq,
                       {"slashable_stake_fraction": frac})


class SafetySignalsTest(unittest.TestCase):

    def test_all_honest_agree(self):
        records = [
            _decided(2, "inst-0", "X"),
            _decided(3, "inst-0", "X"),
        ]
        out = safety_signals(records, frozenset())
        self.assertFalse(out["safety_violation"])
        self.assertEqual(out["conflicting_instances"], 0)

    def test_honest_conflict(self):
        records = [
            _decided(2, "inst-0", "X"),
            _decided(3, "inst-0", "Y"),
        ]
        out = safety_signals(records, frozenset())
        self.assertTrue(out["safety_violation"])
        self.assertEqual(out["conflicting_instances"], 1)

    def test_byzantine_excluded(self):
        # Honest node 2 decides X; Byzantine node 9 decides Y for same instance.
        records = [
            _decided(2, "inst-0", "X"),
            _decided(9, "inst-0", "Y"),
        ]
        out = safety_signals(records, frozenset({9}))
        self.assertFalse(out["safety_violation"])
        self.assertEqual(out["conflicting_instances"], 0)

    def test_slashing_aggregation_single(self):
        records = [_slashing(5, 0.33)]
        out = safety_signals(records, frozenset())
        self.assertAlmostEqual(out["max_slashable_stake_fraction"], 0.33)

    def test_slashing_aggregation_max_wins(self):
        records = [
            _slashing(5, 0.10),
            _slashing(6, 0.42),
            _slashing(7, 0.25),
        ]
        out = safety_signals(records, frozenset())
        self.assertAlmostEqual(out["max_slashable_stake_fraction"], 0.42)

    def test_no_slashing_defaults_zero(self):
        records = [_decided(2, "inst-0", "X")]
        out = safety_signals(records, frozenset())
        self.assertEqual(out["max_slashable_stake_fraction"], 0.0)


if __name__ == "__main__":
    unittest.main()
