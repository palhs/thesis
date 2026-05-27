"""Tests for Snowman message payloads (design spec §3)."""
import dataclasses
import unittest

from snowman.messages import (
    BlockAnnouncementPayload,
    QueryPayload,
    QueryResponsePayload,
)


class TestBlockAnnouncementPayload(unittest.TestCase):
    def test_fields(self):
        p = BlockAnnouncementPayload(
            slot=3,
            block_id=b"b" * 32,
            parent_id=b"\x00" * 32,
            transactions=(b"tx1", b"tx2"),
            proposer_idx=1,
        )
        self.assertEqual(p.slot, 3)
        self.assertEqual(p.block_id, b"b" * 32)
        self.assertEqual(p.parent_id, b"\x00" * 32)
        self.assertEqual(p.transactions, (b"tx1", b"tx2"))
        self.assertEqual(p.proposer_idx, 1)

    def test_frozen(self):
        p = BlockAnnouncementPayload(
            slot=0, block_id=b"x"*32, parent_id=b"\x00"*32,
            transactions=(), proposer_idx=0)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            p.slot = 99  # type: ignore[misc]


class TestQueryPayload(unittest.TestCase):
    def test_fields(self):
        q = QueryPayload(request_id=7, block_id=b"a" * 32)
        self.assertEqual(q.request_id, 7)
        self.assertEqual(q.block_id, b"a" * 32)

    def test_frozen(self):
        q = QueryPayload(request_id=0, block_id=b"a"*32)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            q.request_id = 1  # type: ignore[misc]


class TestQueryResponsePayload(unittest.TestCase):
    def test_fields(self):
        r = QueryResponsePayload(request_id=7, preferred_block_id=b"b" * 32)
        self.assertEqual(r.request_id, 7)
        self.assertEqual(r.preferred_block_id, b"b" * 32)

    def test_frozen(self):
        r = QueryResponsePayload(request_id=0, preferred_block_id=b"a"*32)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r.request_id = 1  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
