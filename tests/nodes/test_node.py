"""Unit tests for the shared-layer Node (node-model.md, T22)."""
import unittest

from nodes import HaltReason, Lifecycle, Node
from nodes.node import _stable_seed
from _helpers import FakeNode


class TestConstruction(unittest.TestCase):
    def test_identity_attributes_stored(self):
        n = FakeNode(node_id=7, weight=2.5, endpoint="addr", global_seed=1)
        self.assertEqual((n.id, n.weight, n.endpoint), (7, 2.5, "addr"))

    def test_starts_in_created_status(self):
        self.assertIs(FakeNode().status, Lifecycle.CREATED)

    def test_adversary_slot_defaults_none(self):
        self.assertIsNone(FakeNode().adversary)

    def test_zero_weight_accepted(self):
        self.assertEqual(FakeNode(weight=0.0).weight, 0.0)

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            FakeNode(weight=-1.0)

    def test_node_is_abstract(self):
        with self.assertRaises(TypeError):
            Node(0, 1.0, None, 0)  # type: ignore[abstract]


class TestRng(unittest.TestCase):
    def test_stable_seed_is_fixed_for_fixed_input(self):
        # Process-stable: blake2b, not Python's randomised hash().
        self.assertEqual(_stable_seed(0, 0), _stable_seed(0, 0))
        self.assertIsInstance(_stable_seed(7, 3), int)
        # Pinned literal: a change to endianness, digest_size, or the seed
        # string format would alter this value and fail loudly.
        self.assertEqual(_stable_seed(42, 5), 4445322452963505364)

    def test_same_seed_and_id_give_identical_streams(self):
        a = FakeNode(node_id=5, global_seed=42)
        b = FakeNode(node_id=5, global_seed=42)
        self.assertEqual([a.rng.random() for _ in range(5)],
                         [b.rng.random() for _ in range(5)])

    def test_different_id_diverges(self):
        a = FakeNode(node_id=1, global_seed=42)
        b = FakeNode(node_id=2, global_seed=42)
        self.assertNotEqual(a.rng.random(), b.rng.random())

    def test_different_global_seed_diverges(self):
        a = FakeNode(node_id=1, global_seed=1)
        b = FakeNode(node_id=1, global_seed=2)
        self.assertNotEqual(a.rng.random(), b.rng.random())


class TestOutboundUnbound(unittest.TestCase):
    def test_send_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().send(1, "X", None, 0.0)

    def test_broadcast_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().broadcast("X", None, 0.0)

    def test_set_timer_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().set_timer("tid", 1.0, None, 0.0)

    def test_cancel_timer_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().cancel_timer("tid")

    def test_emit_raises_before_bind(self):
        with self.assertRaises(RuntimeError):
            FakeNode().emit("evt", {}, 0.0)

    def test_bind_overwrites_placeholder(self):
        n = FakeNode()
        n.emit = lambda et, fs, t: ("bound", et)   # simulate Scheduler.bind
        self.assertEqual(n.emit("evt", {}, 0.0), ("bound", "evt"))


class TestStart(unittest.TestCase):
    def test_start_transitions_to_running(self):
        n = FakeNode()
        n.start(0.0)
        self.assertIs(n.status, Lifecycle.RUNNING)

    def test_start_delegates_to_on_start(self):
        n = FakeNode()
        n.start(0.0)
        self.assertIn(("_on_start", 0.0), n.calls)

    def test_second_start_raises(self):
        n = FakeNode()
        n.start(0.0)
        with self.assertRaisesRegex(RuntimeError, "with status RUNNING"):
            n.start(0.0)


def _running_node_with_recorder():
    n = FakeNode()
    emitted = []
    n.emit = lambda et, fs, t: emitted.append((et, fs, t))
    n.start(0.0)
    return n, emitted


class TestHalt(unittest.TestCase):
    def test_halt_transitions_to_halted(self):
        n, _ = _running_node_with_recorder()
        n.halt(HaltReason.RUN_END, 5.0)
        self.assertIs(n.status, Lifecycle.HALTED)

    def test_halt_emits_halted_event(self):
        n, emitted = _running_node_with_recorder()
        n.halt(HaltReason.CRASHED, 9.0)
        self.assertEqual(
            emitted,
            [("halted", {"node_id": n.id, "reason": "CRASHED", "t": 9.0}, 9.0)])

    def test_second_halt_is_noop_and_keeps_first_reason(self):
        n, emitted = _running_node_with_recorder()
        n.halt(HaltReason.CRASHED, 9.0)
        n.halt(HaltReason.RUN_END, 12.0)        # blanket run-end halt
        self.assertIs(n._halt_reason, HaltReason.CRASHED)
        self.assertEqual(len(emitted), 1)        # no second event

    def test_start_after_halt_raises(self):
        n, _ = _running_node_with_recorder()
        n.halt(HaltReason.RUN_END, 5.0)
        with self.assertRaisesRegex(RuntimeError, "with status HALTED"):
            n.start(0.0)


if __name__ == "__main__":
    unittest.main()
