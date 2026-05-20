"""Unit tests for the shared-layer Node (node-model.md, T22)."""
import unittest

from nodes import AdversaryProfile, HaltReason, Lifecycle, Message, Node
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

    def test_negative_node_id_rejected(self):
        # node_id = -1 is the PhaseAdvance sentinel; -2 etc. would still
        # silently sort before every real NodeId at the same t.
        with self.assertRaises(ValueError):
            FakeNode(node_id=-1)
        with self.assertRaises(ValueError):
            FakeNode(node_id=-7)

    def test_nan_weight_rejected(self):
        import math
        with self.assertRaises(ValueError):
            FakeNode(weight=math.nan)

    def test_pos_inf_weight_rejected(self):
        import math
        with self.assertRaises(ValueError):
            FakeNode(weight=math.inf)

    def test_neg_inf_weight_rejected(self):
        import math
        # `weight < 0` already rejects -inf, but the explicit guard names
        # `weight must be finite` in the error rather than `must be non-negative`.
        with self.assertRaises(ValueError) as cm:
            FakeNode(weight=-math.inf)
        self.assertIn("finite", str(cm.exception))


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

    def test_halt_from_created_skips_running_and_drops_inbound(self):
        # N-1: the harness blanket-halts every Node at run's end (spec §5.3);
        # for a Node that was never start()-ed, that transition is CREATED ->
        # HALTED, skipping RUNNING but still monotonic. The mandatory `halted`
        # event must fire, and any subsequently-dispatched message or timer
        # must be dropped (the HALTED guard in on_message/on_timer takes
        # precedence over the CREATED-raises guard).
        n = FakeNode()
        emitted = []
        n.emit = lambda et, fs, t: emitted.append((et, fs, t))
        self.assertIs(n.status, Lifecycle.CREATED)
        n.halt(HaltReason.RUN_END, 7.0)
        self.assertIs(n.status, Lifecycle.HALTED)
        self.assertIs(n._halt_reason, HaltReason.RUN_END)
        self.assertEqual(
            emitted,
            [("halted", {"node_id": n.id, "reason": "RUN_END", "t": 7.0}, 7.0)])
        # HALTED short-circuits both inbound guards: drop, do not raise.
        n.on_message(Message(src=1, dst=n.id, type="X", payload=None,
                             t_sent=0.0), 8.0)
        n.on_timer("tid", None, 8.0)
        self.assertEqual(n.calls, [])  # no _on_* delegation


class TestInboundGuards(unittest.TestCase):
    def _msg(self):
        return Message(src=1, dst=0, type="X", payload=None, t_sent=0.0)

    def test_on_message_before_start_raises(self):
        with self.assertRaises(RuntimeError):
            FakeNode().on_message(self._msg(), 1.0)

    def test_on_timer_before_start_raises(self):
        with self.assertRaises(RuntimeError):
            FakeNode().on_timer("tid", None, 1.0)

    def test_on_message_while_running_delegates(self):
        n = FakeNode()
        n.start(0.0)
        m = self._msg()
        n.on_message(m, 2.0)
        self.assertEqual(n.calls,
                         [("_on_start", 0.0), ("_on_message", m, 2.0)])

    def test_on_timer_while_running_delegates(self):
        n = FakeNode()
        n.start(0.0)
        n.on_timer("tid", "pl", 2.0)
        self.assertEqual(n.calls,
                         [("_on_start", 0.0), ("_on_timer", "tid", "pl", 2.0)])

    def test_on_message_after_halt_is_dropped(self):
        n, _ = _running_node_with_recorder()
        n.halt(HaltReason.RUN_END, 3.0)
        before = list(n.calls)
        n.on_message(self._msg(), 4.0)
        self.assertEqual(n.calls, before)        # _on_message NOT invoked

    def test_on_timer_after_halt_is_dropped(self):
        n, _ = _running_node_with_recorder()
        n.halt(HaltReason.RUN_END, 3.0)
        before = list(n.calls)
        n.on_timer("tid", None, 4.0)
        self.assertEqual(n.calls, before)


class TestEmitDecided(unittest.TestCase):
    def test_emit_decided_uses_uniform_schema(self):
        n = FakeNode()
        emitted = []
        n.emit = lambda et, fs, t: emitted.append((et, fs, t))
        n._emit_decided(value="digest", instance_id=(1, 2), t=8.0)
        self.assertEqual(
            emitted,
            [("decided",
              {"value": "digest", "instance_id": (1, 2), "t": 8.0}, 8.0)])


class TestAdversarySlot(unittest.TestCase):
    def test_adversary_profile_is_a_protocol(self):
        # typing.Protocol sets _is_protocol on the class.
        self.assertTrue(getattr(AdversaryProfile, "_is_protocol", False))

    def test_adversary_slot_is_assignable(self):
        n = FakeNode()
        sentinel = object()
        n.adversary = sentinel
        self.assertIs(n.adversary, sentinel)


if __name__ == "__main__":
    unittest.main()
