"""T24 EventLogger: normalisation, CSV export, determinism."""
import ast
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from nodes import Message
from scheduler import Delivery, PhaseAdvance, TimerFire

from event_log.logger import EventRecord


class TestEventRecord(unittest.TestCase):
    def test_fields_are_accessible(self):
        r = EventRecord(t=12.0, node_id=5, event_type="decided",
                        seq=-1, fields={"value": "0xab"})
        self.assertEqual(r.t, 12.0)
        self.assertEqual(r.node_id, 5)
        self.assertEqual(r.event_type, "decided")
        self.assertEqual(r.seq, -1)
        self.assertEqual(r.fields, {"value": "0xab"})

    def test_record_is_frozen(self):
        r = EventRecord(t=0.0, node_id=0, event_type="halted",
                        seq=-1, fields={})
        with self.assertRaises(FrozenInstanceError):
            r.t = 9.0


if __name__ == "__main__":
    unittest.main()
