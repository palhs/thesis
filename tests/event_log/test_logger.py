"""T24 EventLogger: normalisation, CSV export, determinism."""
import ast
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from nodes import Message
from scheduler import Delivery, PhaseAdvance, TimerFire

from event_log.logger import EventLogger, EventRecord


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


class TestSinkEmit(unittest.TestCase):
    def test_emit_tuple_becomes_record(self):
        logger = EventLogger()
        logger.sink(12.0, 5, -1,
                    ("emit", "decided",
                     {"value": "0xab", "instance_id": (2, 7)}))
        self.assertEqual(len(logger), 1)
        r = logger.records[0]
        self.assertEqual((r.t, r.node_id, r.event_type, r.seq),
                         (12.0, 5, "decided", -1))
        self.assertEqual(r.fields,
                         {"value": "0xab", "instance_id": (2, 7)})

    def test_emit_fields_dict_is_copied_not_aliased(self):
        logger = EventLogger()
        original = {"reason": "RUN_END"}
        logger.sink(3.0, 1, -1, ("emit", "halted", original))
        original["reason"] = "MUTATED"
        self.assertEqual(logger.records[0].fields, {"reason": "RUN_END"})

    def test_len_reflects_record_count(self):
        logger = EventLogger()
        self.assertEqual(len(logger), 0)
        logger.sink(1.0, 0, -1, ("emit", "halted", {}))
        logger.sink(2.0, 0, -1, ("emit", "decided", {}))
        self.assertEqual(len(logger), 2)


class TestSinkTransport(unittest.TestCase):
    def test_delivery_records_envelope_facts(self):
        logger = EventLogger()
        msg = Message(src=1, dst=3, type="PREPARE",
                      payload={"v": 0}, t_sent=4.0)
        logger.sink(8.5, 3, 4, Delivery(msg))
        r = logger.records[0]
        self.assertEqual(r.event_type, "delivery")
        self.assertEqual((r.t, r.node_id, r.seq), (8.5, 3, 4))
        self.assertEqual(r.fields,
                         {"msg_type": "PREPARE", "src": 1, "dst": 3})

    def test_timer_fire_records_timer_id_only(self):
        logger = EventLogger()
        logger.sink(5.0, 2, 7, TimerFire(timer_id="view-change",
                                         payload={"big": "object"}))
        r = logger.records[0]
        self.assertEqual(r.event_type, "timer_fire")
        self.assertEqual(r.fields, {"timer_id": "view-change"})

    def test_phase_advance_records_phase_id(self):
        logger = EventLogger()
        logger.sink(20.0, -1, 1, PhaseAdvance(phase_id=2))
        r = logger.records[0]
        self.assertEqual(r.event_type, "phase_advance")
        self.assertEqual(r.fields, {"phase_id": 2})


class TestSinkFailFast(unittest.TestCase):
    def test_unknown_payload_raises_type_error(self):
        logger = EventLogger()
        with self.assertRaises(TypeError):
            logger.sink(1.0, 0, 1, "not an event")

    def test_non_emit_tuple_raises_type_error(self):
        logger = EventLogger()
        with self.assertRaises(TypeError):
            logger.sink(1.0, 0, 1, ("notemit", "x", {}))


if __name__ == "__main__":
    unittest.main()
