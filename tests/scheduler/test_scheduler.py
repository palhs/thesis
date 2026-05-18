"""Unit tests for the Scheduler class (simulation-design.md §4-§7)."""
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


if __name__ == "__main__":
    unittest.main()
