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


class TestToCsv(unittest.TestCase):
    def test_header_and_rows(self):
        logger = EventLogger()
        logger.sink(12.0, 5, -1, ("emit", "decided", {"value": "0xab"}))
        logger.sink(8.5, 3, 4,
                    Delivery(Message(1, 3, "PREPARE", None, 4.0)))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "events.csv"
            logger.to_csv(out)
            rows = out.read_text().splitlines()
        self.assertEqual(rows[0], "t,node_id,event_type,seq,fields")
        self.assertEqual(len(rows), 3)            # header + 2 records
        self.assertTrue(rows[1].startswith("12.0,5,decided,-1,"))

    def test_fields_cell_has_sorted_keys(self):
        logger = EventLogger()
        # insertion order b, a — serialisation must sort to a, b.
        logger.sink(1.0, 0, -1, ("emit", "x", {"b": 2, "a": 1}))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "e.csv"
            logger.to_csv(out)
            data_row = out.read_text().splitlines()[1]
        # last CSV cell is the fields repr; parse it back.
        import csv as _csv
        fields_cell = next(_csv.reader([data_row]))[-1]
        self.assertEqual(fields_cell, "{'a': 1, 'b': 2}")
        self.assertEqual(ast.literal_eval(fields_cell), {"a": 1, "b": 2})

    def test_empty_buffer_writes_header_only(self):
        logger = EventLogger()
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "empty.csv"
            logger.to_csv(out)
            rows = out.read_text().splitlines()
        self.assertEqual(rows, ["t,node_id,event_type,seq,fields"])

    def test_creates_missing_parent_dirs(self):
        logger = EventLogger()
        logger.sink(1.0, 0, -1, ("emit", "halted", {}))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "nested" / "deeper" / "events.csv"
            logger.to_csv(out)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()
