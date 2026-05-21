# tests/pbft/test_messages.py
"""PBFT payload dataclasses (T28 spec § 4).

T28 only constructs `PrePreparePayload`. The four placeholder payloads
exist so T29 grows by filling in handlers, not by adding new dataclasses;
the tests guard their shape so a T29 PR cannot silently break it.
"""
import unittest
from dataclasses import FrozenInstanceError

from pbft.messages import (
    CommitPayload,
    NewViewPayload,
    PreparePayload,
    PrePreparePayload,
    ViewChangePayload,
)


class TestPrePreparePayload(unittest.TestCase):
    def test_required_field_construction(self):
        pp = PrePreparePayload(view=0, seq=0,
                               request_digest=b"\x00" * 32,
                               request_payload=b"BATCH")
        self.assertEqual(pp.view, 0)
        self.assertEqual(pp.seq, 0)
        self.assertEqual(pp.request_digest, b"\x00" * 32)
        self.assertEqual(pp.request_payload, b"BATCH")

    def test_frozen(self):
        pp = PrePreparePayload(view=0, seq=0,
                               request_digest=b"\x00" * 32,
                               request_payload=b"BATCH")
        with self.assertRaises(FrozenInstanceError):
            pp.view = 1


class TestPlaceholderPayloads(unittest.TestCase):
    """T29 owns these. The shapes are pinned here so a T29 change is loud."""

    def test_prepare_payload_fields(self):
        p = PreparePayload(view=0, seq=0, request_digest=b"\x00" * 32)
        self.assertEqual((p.view, p.seq, p.request_digest),
                         (0, 0, b"\x00" * 32))

    def test_commit_payload_fields(self):
        c = CommitPayload(view=0, seq=0, request_digest=b"\x00" * 32)
        self.assertEqual((c.view, c.seq, c.request_digest),
                         (0, 0, b"\x00" * 32))

    def test_view_change_payload_fields(self):
        vc = ViewChangePayload(new_view=1, last_stable_seq=0, prepared=[])
        self.assertEqual(vc.new_view, 1)
        self.assertEqual(vc.last_stable_seq, 0)
        self.assertEqual(vc.prepared, [])

    def test_view_change_payload_prepared_holds_four_tuples(self):
        # T29 Decision E: prepared evidence carries the request payload as a
        # fourth element so the new primary can reissue without having
        # prepared the instance itself.
        from pbft.messages import ViewChangePayload
        vc = ViewChangePayload(
            new_view=1, last_stable_seq=-1,
            prepared=[(0, 0, b"d" * 32, b"REQ")])
        self.assertEqual(vc.prepared[0], (0, 0, b"d" * 32, b"REQ"))
        self.assertEqual(vc.new_view, 1)

    def test_new_view_payload_fields(self):
        nv = NewViewPayload(new_view=1, vc_proofs=[], reissued=[])
        self.assertEqual(nv.new_view, 1)
        self.assertEqual(nv.vc_proofs, [])
        self.assertEqual(nv.reissued, [])


if __name__ == "__main__":
    unittest.main()
