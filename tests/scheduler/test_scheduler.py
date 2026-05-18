"""Unit tests for the Scheduler class (simulation-design.md §4-§7)."""
import heapq
import unittest

from scheduler import Delivery, PhaseAdvance, Scheduler, TimerFire
from _stubs import RecordingNetwork, RecordingNode, SimpleMessage


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

    def test_schedule_with_non_finite_t_raises(self):
        # A NaN/inf t must be rejected: `nan < now` is False, so without an
        # explicit guard a non-finite t lands on the heap and corrupts the
        # ordering for the rest of the run (NaN comparisons are all False).
        s = Scheduler()
        for bad_t in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                s.schedule(PhaseAdvance(0), t=bad_t, node_id=0)
        self.assertEqual(s.heap, [])   # nothing slipped through


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

    def test_non_finite_delay_raises(self):
        # NaN/inf delay would push a non-finite TimerFire time onto the heap.
        s = Scheduler()
        for bad_delay in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                s.set_timer(node_id=0, timer_id="x", delay=bad_delay,
                            payload=None, t=0.0)
        self.assertEqual(s.heap, [])
        self.assertEqual(s.registry, {})

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

    def test_emit_with_no_sink_is_silent(self):
        s = Scheduler()  # event_sink left as None
        node = RecordingNode(7)
        s.bind(node)
        node.emit("x", {}, 1.0)  # must complete without raising


class TestRun(unittest.TestCase):
    def _scheduler_with_two_nodes(self):
        s = Scheduler()
        n0, n1 = RecordingNode(0), RecordingNode(1)
        s.bind(n0)
        s.bind(n1)
        return s, n0, n1

    def test_dispatch_delivery_to_on_message(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        msg = SimpleMessage(0, 1, "hello")
        s.schedule(Delivery(msg), t=10.0, node_id=1)
        result = s.run()
        self.assertEqual(n1.calls, [("on_message", msg, 10.0)])
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(result.events_processed, 1)

    def test_dispatch_timerfire_to_on_timer(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        n0.set_timer("round", 5.0, {"view": 2}, 0.0)
        s.run()
        self.assertEqual(n0.calls, [("on_timer", "round", {"view": 2}, 5.0)])

    def test_dispatch_phaseadvance_to_network(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        net = RecordingNetwork()
        s.bind_network(net)
        s.schedule(PhaseAdvance(3), t=7.0, node_id=Scheduler.PHASE_NODE_ID)
        s.run()
        self.assertEqual(net.calls, [("advance_phase", 3)])

    def test_cancelled_timer_is_tombstoned_not_dispatched(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        n0.set_timer("round", 5.0, None, 0.0)
        n0.cancel_timer("round")
        result = s.run()
        self.assertEqual(n0.calls, [])
        self.assertEqual(result.events_tombstoned, 1)
        self.assertEqual(result.events_processed, 0)

    def test_reregistered_timer_fires_once_old_entry_tombstoned(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        n0.set_timer("round", 5.0, "stale", 0.0)
        n0.set_timer("round", 8.0, "fresh", 0.0)
        result = s.run()
        self.assertEqual(n0.calls, [("on_timer", "round", "fresh", 8.0)])
        self.assertEqual(result.events_tombstoned, 1)

    def test_quiescence_on_drained_heap(self):
        s, _, _ = self._scheduler_with_two_nodes()
        result = s.run()
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(result.now, 0.0)

    def test_deadline_stops_after_pop_past_t_max(self):
        # Deadline semantics (simulation-design.md §3 D5): "Loop exits when
        # now >= t_max after a pop." Events strictly inside t_max run; the
        # first event that pushes `now` past t_max runs too (overshoot by
        # one); anything later is left unprocessed on the heap.
        s, n0, n1 = self._scheduler_with_two_nodes()
        s.schedule(Delivery(SimpleMessage(0, 1, "a")), t=10.0, node_id=1)
        s.schedule(Delivery(SimpleMessage(0, 1, "b")), t=30.0, node_id=1)
        s.schedule(Delivery(SimpleMessage(0, 1, "c")), t=50.0, node_id=1)
        result = s.run(t_max=20.0)
        self.assertEqual(result.stopped_by, "deadline")
        self.assertEqual(result.events_processed, 2)   # t=10 and t=30
        self.assertEqual(result.now, 30.0)
        self.assertEqual(len(s.heap), 1)               # t=50 still queued

    def test_empty_run_with_past_deadline_returns_deadline(self):
        s, _, _ = self._scheduler_with_two_nodes()
        result = s.run(t_max=0.0)
        self.assertEqual(result.stopped_by, "deadline")

    def test_predicate_stops_after_dispatch(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        for i in range(5):
            s.schedule(Delivery(SimpleMessage(0, 1, i)), t=float(i + 1),
                       node_id=1)
        result = s.run(stop_when=lambda: len(n1.calls) >= 3)
        self.assertEqual(result.stopped_by, "predicate")
        self.assertEqual(result.events_processed, 3)

    def test_dispatch_to_unbound_node_raises_keyerror(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        # node_id=99 was never bind()-ed.
        s.schedule(Delivery(SimpleMessage(0, 99, "m")), t=5.0, node_id=99)
        with self.assertRaises(KeyError):
            s.run()

    def test_phaseadvance_with_no_network_raises(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        # bind_network() deliberately not called.
        s.schedule(PhaseAdvance(3), t=7.0, node_id=Scheduler.PHASE_NODE_ID)
        with self.assertRaises(RuntimeError):
            s.run()

    def test_event_sink_called_before_dispatch_per_non_stale_event(self):
        s, n0, n1 = self._scheduler_with_two_nodes()
        seen: list[tuple] = []
        s.event_sink = lambda t, nid, seq, ev: seen.append((t, nid, type(ev).__name__))
        n0.set_timer("a", 5.0, None, 0.0)
        s.schedule(Delivery(SimpleMessage(0, 1, "m")), t=8.0, node_id=1)
        s.run()
        self.assertEqual(seen, [(5.0, 0, "TimerFire"), (8.0, 1, "Delivery")])


if __name__ == "__main__":
    unittest.main()
