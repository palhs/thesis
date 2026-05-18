"""Unit tests for the Scheduler class (simulation-design.md §4-§7)."""
import heapq
import unittest

from scheduler import Scheduler


class TestSchedulerSkeleton(unittest.TestCase):
    def test_fresh_scheduler_has_empty_state(self):
        s = Scheduler()
        self.assertEqual(s.heap, [])
        self.assertEqual(s.registry, {})
        self.assertEqual(s.seq_per, {})
        self.assertEqual(s.now, 0.0)
        self.assertIsNone(s.event_sink)

    def test_now_is_read_only(self):
        s = Scheduler()
        with self.assertRaises(AttributeError):
            s.now = 5.0  # type: ignore[misc]

    def test_next_seq_increments_per_node_independently(self):
        s = Scheduler()
        self.assertEqual(s._next_seq(0), 1)
        self.assertEqual(s._next_seq(0), 2)
        self.assertEqual(s._next_seq(1), 1)   # node 1 counter is independent
        self.assertEqual(s._next_seq(0), 3)


from scheduler import PhaseAdvance, TimerFire


class TestSchedule(unittest.TestCase):
    def test_schedule_pushes_and_returns_seq(self):
        s = Scheduler()
        seq = s.schedule(PhaseAdvance(0), t=10.0, node_id=0)
        self.assertEqual(seq, 1)
        self.assertEqual(len(s.heap), 1)
        t, node_id, heap_seq, ev = s.heap[0]
        self.assertEqual((t, node_id, heap_seq), (10.0, 0, 1))

    def test_heap_orders_by_time_then_node_then_seq(self):
        s = Scheduler()
        # seq is a per-node counter incremented in schedule() CALL order,
        # not virtual-time order (simulation-design.md §3 D2). So node 0's
        # t=20 event gets seq 1 and its t=10 event gets seq 2.
        s.schedule(TimerFire("b", None), t=20.0, node_id=0)   # node 0, seq 1
        s.schedule(TimerFire("a", None), t=10.0, node_id=1)   # node 1, seq 1
        s.schedule(TimerFire("c", None), t=10.0, node_id=0)   # node 0, seq 2
        order = [heapq.heappop(s.heap)[:3] for _ in range(3)]
        self.assertEqual(order, [(10.0, 0, 2), (10.0, 1, 1), (20.0, 0, 1)])

    def test_schedule_in_the_past_raises(self):
        s = Scheduler()
        s.schedule(PhaseAdvance(0), t=10.0, node_id=0)
        s._now = 10.0
        with self.assertRaises(ValueError):
            s.schedule(PhaseAdvance(1), t=9.999, node_id=0)

    def test_schedule_at_now_is_allowed(self):
        s = Scheduler()
        s._now = 5.0
        seq = s.schedule(PhaseAdvance(0), t=5.0, node_id=0)
        self.assertEqual(seq, 1)


class TestTimers(unittest.TestCase):
    def test_set_timer_registers_heap_entry_seq(self):
        s = Scheduler()
        s.set_timer(node_id=0, timer_id="round", delay=5.0, payload=None, t=0.0)
        self.assertEqual(len(s.heap), 1)
        t, node_id, seq, ev = s.heap[0]
        self.assertEqual((t, node_id), (5.0, 0))
        self.assertIsInstance(ev, TimerFire)
        # Registry seq MUST equal the heap entry's seq (tombstone correctness).
        self.assertEqual(s.registry[(0, "round")], seq)

    def test_zero_delay_is_allowed(self):
        s = Scheduler()
        s.set_timer(node_id=0, timer_id="yield", delay=0.0, payload=None, t=3.0)
        self.assertEqual(s.heap[0][0], 3.0)

    def test_negative_delay_raises(self):
        s = Scheduler()
        with self.assertRaises(ValueError):
            s.set_timer(node_id=0, timer_id="x", delay=-1.0, payload=None, t=0.0)

    def test_cancel_timer_removes_registry_entry(self):
        s = Scheduler()
        s.set_timer(node_id=0, timer_id="round", delay=5.0, payload=None, t=0.0)
        s.cancel_timer(node_id=0, timer_id="round")
        self.assertNotIn((0, "round"), s.registry)
        # Lazy tombstone: heap entry is left in place.
        self.assertEqual(len(s.heap), 1)

    def test_cancel_unknown_timer_is_noop(self):
        s = Scheduler()
        s.cancel_timer(node_id=0, timer_id="never-set")  # must not raise

    def test_reregistration_overwrites_registry_seq(self):
        s = Scheduler()
        s.set_timer(node_id=0, timer_id="round", delay=5.0, payload=None, t=0.0)
        first_seq = s.registry[(0, "round")]
        s.set_timer(node_id=0, timer_id="round", delay=8.0, payload=None, t=0.0)
        second_seq = s.registry[(0, "round")]
        self.assertNotEqual(first_seq, second_seq)
        self.assertEqual(len(s.heap), 2)  # old entry left as a tombstone


from _stubs import RecordingNetwork, RecordingNode


class TestBind(unittest.TestCase):
    def test_bind_registers_node_for_dispatch(self):
        s = Scheduler()
        node = RecordingNode(7)
        s.bind(node)
        self.assertIs(s.nodes[7], node)

    def test_bind_wires_set_timer_curried_on_node_id(self):
        s = Scheduler()
        node = RecordingNode(7)
        s.bind(node)
        node.set_timer("round", 5.0, None, 0.0)
        self.assertEqual(s.registry[(7, "round")], s.heap[0][2])

    def test_bind_wires_cancel_timer_curried_on_node_id(self):
        s = Scheduler()
        node = RecordingNode(7)
        s.bind(node)
        node.set_timer("round", 5.0, None, 0.0)
        node.cancel_timer("round")
        self.assertNotIn((7, "round"), s.registry)

    def test_bind_wires_emit_through_event_sink(self):
        s = Scheduler()
        captured: list[tuple] = []
        s.event_sink = lambda t, nid, seq, ev: captured.append((t, nid, seq, ev))
        node = RecordingNode(7)
        s.bind(node)
        node.emit("committed", {"block": 1}, 12.0)
        self.assertEqual(captured,
                         [(12.0, 7, -1, ("emit", "committed", {"block": 1}))])

    def test_bind_network_sets_network_handle(self):
        s = Scheduler()
        net = RecordingNetwork()
        s.bind_network(net)
        self.assertIs(s.network, net)


if __name__ == "__main__":
    unittest.main()
