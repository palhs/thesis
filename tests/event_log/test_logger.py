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

    def test_fields_dict_is_mutable_in_place_known_contract_limitation(self):
        # Closes T25 review gap L-1. EventRecord is frozen at the dataclass
        # level — `r.t = X` raises FrozenInstanceError — but `r.fields` is a
        # plain dict, which is not frozen. Mutating via `r.fields[k] = v`
        # succeeds and modifies the buffered record. The emit-side defensive
        # copy in sink() protects the inbound direction (against caller
        # mutation of the source dict); this is the symmetric outbound
        # concern. If the footgun becomes a real problem, wrap fields in
        # types.MappingProxyType — for now we pin current behaviour.
        logger = EventLogger()
        logger.sink(1.0, 0, -1, ("emit", "decided", {"v": 1}))
        r = logger.records[0]
        r.fields["mutated"] = True
        self.assertEqual(logger.records[0].fields,
                         {"v": 1, "mutated": True})


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

    def test_two_tuple_emit_raises_type_error(self):
        # Closes T25 review gap L-6 (arity edge). Emit-tuple detection
        # requires len(payload) == 3 — a too-short tuple falls through to
        # the fail-fast raise just like the wrong-tag case.
        logger = EventLogger()
        with self.assertRaises(TypeError):
            logger.sink(1.0, 0, 1, ("emit", "x"))

    def test_four_tuple_emit_raises_type_error(self):
        # Closes T25 review gap L-6 (arity edge). Symmetric to the
        # 2-tuple case: a too-long tuple is also rejected.
        logger = EventLogger()
        with self.assertRaises(TypeError):
            logger.sink(1.0, 0, 1, ("emit", "x", {}, "extra"))


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

    def test_csv_cell_round_trips_tuple_via_ast_literal_eval(self):
        # Closes T25 review gap L-2. The design contract claims the CSV
        # cell round-trips the tuple instance_id of PBFT / Narwhal decided
        # events (event-log-schema.md "CSV format"); the existing
        # sorted-keys test only pinned that for plain {int, str} values.
        # A regression switching repr -> json.dumps would silently break
        # the tuple round-trip (JSON has no tuple type) without failing
        # any existing test.
        logger = EventLogger()
        logger.sink(1.0, 0, -1, ("emit", "decided",
                                  {"value": "0xab", "instance_id": (2, 7)}))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "e.csv"
            logger.to_csv(out)
            data_row = out.read_text().splitlines()[1]
        import csv as _csv
        fields_cell = next(_csv.reader([data_row]))[-1]
        parsed = ast.literal_eval(fields_cell)
        self.assertEqual(parsed,
                         {"instance_id": (2, 7), "value": "0xab"})
        # Type discipline: the round-trip preserves tuple, not list.
        self.assertIsInstance(parsed["instance_id"], tuple)

    def test_second_to_csv_to_same_path_overwrites(self):
        # Closes T25 review gap L-5 (overwrite half). Stdlib open(path, "w")
        # semantics — second export to the same path replaces, not appends.
        logger = EventLogger()
        logger.sink(1.0, 0, -1, ("emit", "halted", {}))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "e.csv"
            logger.to_csv(out)
            first = out.read_bytes()
            logger.sink(2.0, 0, -1, ("emit", "decided", {}))
            logger.to_csv(out)
            second = out.read_bytes()
        self.assertNotEqual(first, second)
        # Replaced, not appended — the second file is the new buffer in
        # full (header + 2 rows), not the old file with extra rows tacked on.
        self.assertEqual(second.count(b"\n"), 3)   # header + 2 records

    def test_sink_after_to_csv_extends_buffer(self):
        # Closes T25 review gap L-5 (resumability half). The logger holds
        # no file handle; to_csv is a pure read of the buffer. Further
        # sink() calls extend the buffer just like before.
        logger = EventLogger()
        logger.sink(1.0, 0, -1, ("emit", "halted", {}))
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "e.csv"
            logger.to_csv(out)
        logger.sink(2.0, 0, -1, ("emit", "decided", {}))
        self.assertEqual(len(logger), 2)
        self.assertEqual(logger.records[-1].event_type, "decided")


class TestPackageExports(unittest.TestCase):
    def test_public_names_importable_from_package_root(self):
        import event_log
        for name in ("EventLogger", "EventRecord", "HALTED", "DECIDED",
                     "DELIVERY", "TIMER_FIRE", "PHASE_ADVANCE",
                     "TRANSPORT_EVENT_TYPES"):
            self.assertIn(name, dir(event_log), name)


class TestDeterminism(unittest.TestCase):
    def test_identical_event_sequences_yield_identical_csv(self):
        # Same event sequence -> byte-identical CSV. fields dicts are
        # supplied in DIFFERENT insertion orders to prove sorted-key
        # serialisation makes the output order-independent.
        seq_a = [
            (1.0, 0, -1, ("emit", "decided", {"value": "v", "n": 1})),
            (2.0, 1, 4, Delivery(Message(0, 1, "PING", None, 1.0))),
        ]
        seq_b = [
            (1.0, 0, -1, ("emit", "decided", {"n": 1, "value": "v"})),
            (2.0, 1, 4, Delivery(Message(0, 1, "PING", None, 1.0))),
        ]
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.csv", Path(d) / "b.csv"
            la, lb = EventLogger(), EventLogger()
            for ev in seq_a:
                la.sink(*ev)
            for ev in seq_b:
                lb.sink(*ev)
            la.to_csv(a)
            lb.to_csv(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
