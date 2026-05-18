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


if __name__ == "__main__":
    unittest.main()
