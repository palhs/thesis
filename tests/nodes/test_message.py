"""Unit tests for the Message envelope (node-model.md §6)."""
import dataclasses
import unittest

from nodes import Message


class TestMessage(unittest.TestCase):
    def test_fields_round_trip(self):
        m = Message(src=1, dst=2, type="PING", payload={"k": 1}, t_sent=3.0)
        self.assertEqual((m.src, m.dst, m.type, m.payload, m.t_sent),
                         (1, 2, "PING", {"k": 1}, 3.0))

    def test_dst_accepts_broadcast_literal(self):
        m = Message(src=1, dst="broadcast", type="X", payload=None, t_sent=0.0)
        self.assertEqual(m.dst, "broadcast")

    def test_message_is_frozen(self):
        m = Message(src=1, dst=2, type="PING", payload=None, t_sent=0.0)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            m.src = 9  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
