"""Pure view-change helpers (T29 spec § 8).

`collect_evidence` and `compute_reissue` operate on plain data with no
PBFTNode dependency, so they are unit-tested in isolation here.
"""
import unittest

from pbft.instance import Instance, InstanceState
from pbft.messages import PrePreparePayload, ViewChangePayload
from pbft.viewchange import collect_evidence, compute_reissue


def _inst(view, seq, state, digest=b"d" * 32, payload=b"REQ"):
    i = Instance(view=view, seq=seq)
    i.state = state
    i.digest = digest
    i.request_payload = payload
    return i


class TestCollectEvidence(unittest.TestCase):
    def test_includes_prepared_and_committed_only(self):
        inst = {
            (0, 0): _inst(0, 0, InstanceState.IDLE),
            (0, 1): _inst(0, 1, InstanceState.PRE_PREPARED),
            (0, 2): _inst(0, 2, InstanceState.PREPARED),
            (0, 3): _inst(0, 3, InstanceState.COMMITTED),
        }
        ev = collect_evidence(inst)
        self.assertEqual([(v, s) for v, s, _, _ in ev], [(0, 2), (0, 3)])

    def test_tuple_shape_and_sort(self):
        inst = {
            (1, 0): _inst(1, 0, InstanceState.PREPARED, b"x" * 32, b"X"),
            (0, 0): _inst(0, 0, InstanceState.PREPARED, b"y" * 32, b"Y"),
        }
        ev = collect_evidence(inst)
        self.assertEqual(ev[0], (0, 0, b"y" * 32, b"Y"))
        self.assertEqual(ev[1], (1, 0, b"x" * 32, b"X"))


class TestComputeReissue(unittest.TestCase):
    def test_unions_and_stamps_new_view(self):
        p1 = ViewChangePayload(2, -1, [(0, 0, b"a" * 32, b"A")])
        p2 = ViewChangePayload(2, -1, [(0, 1, b"b" * 32, b"B")])
        out = compute_reissue([p1, p2], new_view=2)
        self.assertEqual([pp.seq for pp in out], [0, 1])
        self.assertTrue(all(isinstance(pp, PrePreparePayload) for pp in out))
        self.assertTrue(all(pp.view == 2 for pp in out))

    def test_picks_highest_view_per_seq(self):
        p1 = ViewChangePayload(2, -1, [(0, 0, b"old" * 11 + b"o", b"OLD")])
        p2 = ViewChangePayload(2, -1, [(1, 0, b"new" * 11 + b"n", b"NEW")])
        out = compute_reissue([p1, p2], new_view=2)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].request_payload, b"NEW")


if __name__ == "__main__":
    unittest.main()
