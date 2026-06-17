"""inject_delay: the post-build outbound-API wrap (T51, spec §3.1).

Unit-tested against stub nodes (no full simulator run): inject_delay only
touches handle.nodes[*].send / .broadcast / .adversary, so a SimpleNamespace
handle with recording stub nodes exercises the wrap in isolation.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from adversary.inject import inject_delay
from adversary.profiles import DelayProfile


def _stub_node(node_id: int):
    """A node whose send/broadcast record (args) into .sent / .bcast."""
    node = SimpleNamespace(id=node_id, adversary=None, sent=[], bcast=[])
    node.send = lambda dst, type, payload, t, _n=node: _n.sent.append(
        (dst, type, payload, t))
    node.broadcast = lambda type, payload, t, _n=node: _n.bcast.append(
        (type, payload, t))
    return node


def _stub_handle(n: int):
    nodes = {i: _stub_node(i) for i in range(n)}
    return SimpleNamespace(nodes=nodes), nodes


class TestInjectDelay(unittest.TestCase):
    def test_slow_node_send_shifted(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(3,), mult=5.0, ref=1.0, intensity=0.25)   # shift = 5.0
        nodes[3].send(dst=0, type="VOTE", payload=b"x", t=2.0)
        # delivered as if emitted at t + 5.0 = 7.0
        self.assertEqual(nodes[3].sent, [(0, "VOTE", b"x", 7.0)])

    def test_slow_node_broadcast_shifted(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(3,), mult=2.0, ref=1.0, intensity=0.25)   # shift = 2.0
        nodes[3].broadcast(type="PREPARE", payload=b"p", t=10.0)
        self.assertEqual(nodes[3].bcast, [("PREPARE", b"p", 12.0)])

    def test_non_slow_nodes_untouched(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(3,), mult=5.0, ref=1.0, intensity=0.25)
        nodes[0].send(dst=1, type="VOTE", payload=b"y", t=2.0)
        nodes[0].broadcast(type="PRE", payload=b"q", t=3.0)
        # honest node 0: no shift.
        self.assertEqual(nodes[0].sent, [(1, "VOTE", b"y", 2.0)])
        self.assertEqual(nodes[0].bcast, [("PRE", b"q", 3.0)])

    def test_empty_slow_set_is_noop(self):
        handle, nodes = _stub_handle(4)
        before_send = {i: nodes[i].send for i in range(4)}
        before_bcast = {i: nodes[i].broadcast for i in range(4)}
        inject_delay(handle, slow_ids=(), mult=5.0, ref=1.0, intensity=0.0)
        # identity unchanged: no wrapping happened.
        for i in range(4):
            self.assertIs(nodes[i].send, before_send[i])
            self.assertIs(nodes[i].broadcast, before_bcast[i])
            self.assertIsNone(nodes[i].adversary)

    def test_multiple_slow_nodes_independent_shift(self):
        # Closure-correctness: each wrapped node keeps ITS OWN honest fn, not
        # the last loop iteration's. Sending from node 2 alone must leave
        # node 3's record untouched (cross-capture would write into it).
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(2, 3), mult=3.0, ref=1.0, intensity=0.5)
        nodes[2].send(dst=0, type="V", payload=b"a", t=1.0)
        self.assertEqual(nodes[2].sent, [(0, "V", b"a", 4.0)])
        self.assertEqual(nodes[3].sent, [])          # node 3 untouched
        nodes[3].send(dst=0, type="V", payload=b"b", t=1.0)
        self.assertEqual(nodes[3].sent, [(0, "V", b"b", 4.0)])

    def test_adversary_profile_recorded(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(2, 3), mult=5.0, ref=1.0, intensity=0.5)
        for i in (2, 3):
            self.assertIsInstance(nodes[i].adversary, DelayProfile)
            self.assertEqual(nodes[i].adversary.nodes, (2, 3))
            self.assertEqual(nodes[i].adversary.mult, 5.0)
            self.assertEqual(nodes[i].adversary.intensity, 0.5)
        self.assertIsNone(nodes[0].adversary)
        self.assertIsNone(nodes[1].adversary)


    def test_double_injection_raises(self):
        handle, nodes = _stub_handle(4)
        inject_delay(handle, slow_ids=(3,), mult=2.0, ref=1.0, intensity=0.25)
        with self.assertRaises(RuntimeError):
            inject_delay(handle, slow_ids=(3,), mult=2.0, ref=1.0,
                         intensity=0.25)


class TestInjectOffline(unittest.TestCase):
    def test_offline_send_dropped(self):
        from adversary.inject import inject_offline
        handle, nodes = _stub_handle(4)
        inject_offline(handle, offline_ids=(3,), intensity=0.25)
        nodes[3].send(dst=0, type="VOTE", payload=b"x", t=2.0)
        nodes[3].broadcast(type="PREPARE", payload=b"p", t=5.0)
        self.assertEqual(nodes[3].sent, [])     # nothing recorded
        self.assertEqual(nodes[3].bcast, [])

    def test_honest_nodes_untouched(self):
        from adversary.inject import inject_offline
        handle, nodes = _stub_handle(4)
        inject_offline(handle, offline_ids=(3,), intensity=0.25)
        nodes[0].send(dst=1, type="VOTE", payload=b"y", t=2.0)
        nodes[0].broadcast(type="PRE", payload=b"q", t=3.0)
        self.assertEqual(nodes[0].sent, [(1, "VOTE", b"y", 2.0)])
        self.assertEqual(nodes[0].bcast, [("PRE", b"q", 3.0)])

    def test_empty_offline_set_is_noop(self):
        from adversary.inject import inject_offline
        handle, nodes = _stub_handle(4)
        before = {i: (nodes[i].send, nodes[i].broadcast) for i in range(4)}
        inject_offline(handle, offline_ids=(), intensity=0.0)
        for i in range(4):
            self.assertIs(nodes[i].send, before[i][0])
            self.assertIs(nodes[i].broadcast, before[i][1])
            self.assertIsNone(nodes[i].adversary)

    def test_profile_recorded(self):
        from adversary.inject import inject_offline
        from adversary.profiles import OfflineProfile
        handle, nodes = _stub_handle(4)
        inject_offline(handle, offline_ids=(2, 3), intensity=0.5)
        for i in (2, 3):
            self.assertIsInstance(nodes[i].adversary, OfflineProfile)
            self.assertEqual(nodes[i].adversary.nodes, (2, 3))
        self.assertIsNone(nodes[0].adversary)

    def test_double_injection_raises(self):
        from adversary.inject import inject_offline
        handle, nodes = _stub_handle(4)
        inject_offline(handle, offline_ids=(3,), intensity=0.25)
        with self.assertRaises(RuntimeError):
            inject_offline(handle, offline_ids=(3,), intensity=0.25)


if __name__ == "__main__":
    unittest.main()
