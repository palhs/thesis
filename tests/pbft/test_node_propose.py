# tests/pbft/test_node_propose.py
"""PBFTNode construction, primary detection, and (Task 6) propose path."""
import unittest

from pbft.node import PBFTNode


def _node(node_id: int, n: int, *, workload=None, propose_delay=1.0,
          initial_view=0, weight=1.0, global_seed=42) -> PBFTNode:
    return PBFTNode(node_id=node_id, weight=weight, endpoint=None,
                    global_seed=global_seed, n=n, workload=workload,
                    propose_delay=propose_delay, initial_view=initial_view)


class TestPBFTNodeConstructor(unittest.TestCase):
    def test_defaults_for_non_primary(self):
        # workload=None -> empty list copy; never blocks construction.
        n = _node(1, n=4)
        self.assertEqual(n.n, 4)
        self.assertEqual(n.f, 1)             # (4-1)//3 = 1
        self.assertEqual(n.view, 0)
        self.assertFalse(n.view_changing)
        self.assertEqual(n.workload, [])
        self.assertEqual(n.propose_delay, 1.0)
        self.assertEqual(n.next_seq, 0)
        self.assertEqual(n.inst, {})

    def test_workload_is_copied(self):
        # Caller's list must not be mutated when the primary drains.
        src = [b"A", b"B"]
        n = _node(0, n=4, workload=src)
        n.workload.append(b"C")
        self.assertEqual(src, [b"A", b"B"])  # untouched

    def test_f_for_n_7(self):
        self.assertEqual(_node(0, n=7).f, 2)     # (7-1)//3 = 2

    def test_rejects_non_positive_n(self):
        with self.assertRaises(ValueError):
            _node(0, n=0)
        with self.assertRaises(ValueError):
            _node(0, n=-1)

    def test_rejects_node_id_outside_range(self):
        with self.assertRaises(ValueError):
            _node(4, n=4)                    # id == n is out of range
        # Negative node_id is caught upstream by Node.__init__; PBFTNode
        # narrows it to "must be < n".

    def test_rejects_non_positive_propose_delay(self):
        with self.assertRaises(ValueError):
            _node(0, n=4, propose_delay=0.0)
        with self.assertRaises(ValueError):
            _node(0, n=4, propose_delay=-1.0)


class TestIsPrimary(unittest.TestCase):
    def test_v_mod_n_rule_n4(self):
        nodes = [_node(i, n=4) for i in range(4)]
        # view 0 -> node 0; view 1 -> node 1; view 5 -> node 1.
        self.assertTrue(nodes[0]._is_primary(0))
        self.assertFalse(nodes[1]._is_primary(0))
        self.assertTrue(nodes[1]._is_primary(1))
        self.assertTrue(nodes[1]._is_primary(5))

    def test_v_mod_n_rule_n7(self):
        nodes = [_node(i, n=7) for i in range(7)]
        for v in range(14):
            primary_id = v % 7
            for i in range(7):
                self.assertEqual(nodes[i]._is_primary(v), i == primary_id,
                                 f"view={v} node={i} primary_id={primary_id}")


# Appended to tests/pbft/test_node_propose.py from Task 4.

from typing import Any

from nodes import Message
from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.messages import PrePreparePayload
from pbft.node import PBFT_PRE_PREPARED, PBFT_REJECTED


def _install_capturers(node: PBFTNode):
    emitted: list[tuple[str, dict, float]] = []
    broadcasts: list[tuple[str, object, float]] = []
    timers: list[tuple[Any, float, object, float]] = []
    node.emit = lambda et, fields, t: emitted.append((et, fields, t))
    node.broadcast = lambda type, payload, t: broadcasts.append(
        (type, payload, t))
    node.set_timer = lambda tid, delay, payload, t: timers.append(
        (tid, delay, payload, t))
    node.send = lambda *a, **kw: None
    node.cancel_timer = lambda tid: None
    return emitted, broadcasts, timers


class TestOnStart(unittest.TestCase):
    def test_primary_arms_propose_timer(self):
        primary = _node(0, n=4, propose_delay=0.5)
        _, _, timers = _install_capturers(primary)
        primary.start(t=0.0)            # CREATED -> RUNNING -> _on_start

        self.assertEqual(len(timers), 1)
        tid, delay, payload, t = timers[0]
        self.assertEqual(tid, "propose")
        self.assertEqual(delay, 0.5)
        self.assertEqual(t, 0.0)

    def test_non_primary_does_not_arm_anything(self):
        replica = _node(2, n=4)
        emitted, broadcasts, timers = _install_capturers(replica)
        replica.start(t=0.0)

        self.assertEqual(timers, [])
        self.assertEqual(broadcasts, [])
        self.assertEqual(emitted, [])


class TestProposePath(unittest.TestCase):
    def test_one_propose_broadcasts_and_self_transitions(self):
        primary = _node(0, n=4, workload=[b"A"], propose_delay=1.0)
        emitted, broadcasts, timers = _install_capturers(primary)
        primary.start(t=0.0)
        # _on_start armed the timer; fire it manually.
        primary.on_timer("propose", None, t=1.0)

        # The PRE-PREPARE broadcast leads, with the right shape. T29's
        # uniform-quorum model (Decision B) means the primary's self-loop
        # accept also broadcasts a PREPARE, so two broadcasts are expected.
        typ, pp, t = broadcasts[0]
        self.assertEqual(typ, "PRE-PREPARE")
        self.assertIsInstance(pp, PrePreparePayload)
        self.assertEqual(pp.view, 0)
        self.assertEqual(pp.seq, 0)
        self.assertEqual(pp.request_payload, b"A")
        self.assertEqual(pp.request_digest, digest(b"A"))
        self.assertIn("PREPARE", [b[0] for b in broadcasts])

        # Self-loop: primary's own (0, 0) is PRE_PREPARED with one
        # pbft_pre_prepared event whose src == self.id.
        inst = primary.inst[(0, 0)]
        self.assertIs(inst.state, InstanceState.PRE_PREPARED)
        pre_prepared = [e for e in emitted if e[0] == PBFT_PRE_PREPARED]
        self.assertEqual(len(pre_prepared), 1)
        self.assertEqual(pre_prepared[0][1]["src"], 0)
        # No rejections on the primary's own work.
        self.assertNotIn(PBFT_REJECTED, [e[0] for e in emitted])

        # next_seq advanced.
        self.assertEqual(primary.next_seq, 1)

        # T29: the self-loop accept arms a per-instance view-change timer,
        # and _propose re-arms the propose timer.
        self.assertIn(("view_change", 0, 0), [tid for tid, *_ in timers])
        self.assertEqual(timers[-1][0], "propose")

    def test_drain_stops_when_workload_empty(self):
        primary = _node(0, n=4, workload=[b"A"], propose_delay=1.0)
        _, broadcasts, timers = _install_capturers(primary)
        primary.start(t=0.0)            # 1 timer armed
        primary.on_timer("propose", None, t=1.0)    # drains; re-arms 1 more
        primary.on_timer("propose", None, t=2.0)    # workload empty: no-op

        # Exactly one PRE-PREPARE; the second fire was a drain no-op.
        pre_prepares = [b for b in broadcasts if b[0] == "PRE-PREPARE"]
        self.assertEqual(len(pre_prepares), 1)
        # Two propose timers (_on_start + the one _propose re-arm); the
        # second fire drained nothing and armed nothing.
        self.assertEqual([t for t in timers if t[0] == "propose"].__len__(), 2)

    def test_next_seq_monotone_across_drain(self):
        primary = _node(0, n=4, workload=[b"A", b"B", b"C"],
                        propose_delay=1.0)
        _, broadcasts, _ = _install_capturers(primary)
        primary.start(t=0.0)
        for k in range(3):
            primary.on_timer("propose", None, t=float(k + 1))
        seqs = [b[1].seq for b in broadcasts if b[0] == "PRE-PREPARE"]
        self.assertEqual(seqs, [0, 1, 2])

    def test_unknown_timer_silently_no_op(self):
        primary = _node(0, n=4, workload=[b"A"])
        emitted, broadcasts, _ = _install_capturers(primary)
        primary.start(t=0.0)
        primary.on_timer("bogus", None, t=1.0)

        # Bogus timer did not propose, did not emit anything.
        self.assertEqual(broadcasts, [])
        self.assertEqual(emitted, [])


if __name__ == "__main__":
    unittest.main()
