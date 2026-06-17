"""Unit tests for the window/buffer clip (src/delay/clip.py).

These are pure-function tests over hand-built EventRecord streams — no
protocol code. They pin the three behaviours the locked Week-9 buffer/clip
rule requires:

  1. SCOPE  — instances whose first decision lands past W + one_round are
              excluded entirely (started in the buffer).
  2. CLIP   — for an in-scope instance, decided events with t > W are
              dropped from the rate count, but the instance survives (its
              first, in-window decision is kept), so latency is unperturbed.
  3. STATS  — clipped_fraction = tail / (kept + tail), the < 5 % guard.

Every event with t > W is clipped — deliveries and timers included, not
just decided — so the overhead numerator shares the [0, W] window with
its decided denominator (no buffer inflation).
"""
from __future__ import annotations

import unittest

from event_log import EventRecord

from delay.clip import clip_records


def _decided(t: float, iid, node_id: int = 0) -> EventRecord:
    return EventRecord(t=t, node_id=node_id, event_type="decided", seq=-1,
                       fields={"instance_id": iid, "value": "v", "t": t})


def _delivery(t: float) -> EventRecord:
    return EventRecord(t=t, node_id=0, event_type="delivery", seq=1,
                       fields={"msg_type": "PREPARE", "src": 0, "dst": 1})


class TestScope(unittest.TestCase):
    def test_instance_started_in_buffer_is_excluded(self):
        W, one_round = 100.0, 5.0
        records = [
            _decided(10.0, iid=1),    # in-window: first decision at 10 <= 105
            _decided(110.0, iid=2),   # in-buffer: first decision at 110 > 105
        ]
        kept, stats = clip_records(records, W, one_round)
        self.assertEqual(stats.in_scope_instances, 1)
        self.assertEqual(stats.late_events, 1)
        kept_decided = [r for r in kept if r.event_type == "decided"]
        self.assertEqual([r.fields["instance_id"] for r in kept_decided], [1])

    def test_first_decision_within_one_round_grace_is_in_scope(self):
        # An instance proposed just before W finalizes inside [W, W+one_round].
        W, one_round = 100.0, 5.0
        records = [_decided(103.0, iid=1)]   # 103 <= 100 + 5 -> in scope
        kept, stats = clip_records(records, W, one_round)
        self.assertEqual(stats.in_scope_instances, 1)
        # ...but the event itself is past W, so it is a clipped tail event.
        self.assertEqual(stats.tail_events, 1)
        self.assertEqual(stats.kept_events, 0)


class TestClip(unittest.TestCase):
    def test_tail_event_dropped_first_decision_kept(self):
        W, one_round = 100.0, 5.0
        records = [
            _decided(50.0, iid=1, node_id=0),    # first, in-window: kept
            _decided(101.0, iid=1, node_id=1),   # same instance, past W: clipped
        ]
        kept, stats = clip_records(records, W, one_round)
        kept_decided = [r for r in kept if r.event_type == "decided"]
        self.assertEqual(len(kept_decided), 1)
        self.assertEqual(kept_decided[0].t, 50.0)
        self.assertEqual(stats.kept_events, 1)
        self.assertEqual(stats.tail_events, 1)

    def test_non_decided_events_clipped_at_window(self):
        # Deliveries past W are clipped too, so the overhead numerator does
        # not pick up buffer-period messages (the +10 % artifact fix).
        W, one_round = 100.0, 5.0
        records = [_delivery(50.0), _delivery(150.0), _decided(50.0, iid=1)]
        kept, _ = clip_records(records, W, one_round)
        deliveries = [r for r in kept if r.event_type == "delivery"]
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0].t, 50.0)

    def test_in_window_delivery_kept_when_instance_late(self):
        # A delivery at t <= W is kept on its own time-clip even if it
        # belongs to a buffer-started (late) instance — windowing is by
        # event time, the inherent O(one round) boundary effect.
        W, one_round = 100.0, 5.0
        records = [_delivery(99.0), _decided(110.0, iid=1)]
        kept, stats = clip_records(records, W, one_round)
        self.assertEqual([r.t for r in kept if r.event_type == "delivery"],
                         [99.0])
        self.assertEqual(stats.late_events, 1)

    def test_chronological_order_preserved(self):
        W, one_round = 100.0, 5.0
        records = [
            _delivery(10.0), _decided(20.0, iid=1),
            _delivery(30.0), _decided(40.0, iid=2),
        ]
        kept, _ = clip_records(records, W, one_round)
        ts = [r.t for r in kept]
        self.assertEqual(ts, sorted(ts))


class TestStats(unittest.TestCase):
    def test_clipped_fraction_formula(self):
        W, one_round = 100.0, 5.0
        # instance 1: one in-window + one tail; instance 2: in-window only.
        records = [
            _decided(50.0, iid=1, node_id=0),
            _decided(101.0, iid=1, node_id=1),
            _decided(60.0, iid=2, node_id=0),
        ]
        _, stats = clip_records(records, W, one_round)
        self.assertEqual(stats.kept_events, 2)
        self.assertEqual(stats.tail_events, 1)
        self.assertAlmostEqual(stats.clipped_fraction, 1 / 3)

    def test_empty_stream_zero_fraction(self):
        kept, stats = clip_records([], 100.0, 5.0)
        self.assertEqual(kept, [])
        self.assertEqual(stats.clipped_fraction, 0.0)

    def test_all_in_window_zero_fraction(self):
        records = [_decided(10.0, iid=1), _decided(20.0, iid=2)]
        _, stats = clip_records(records, 100.0, 5.0)
        self.assertEqual(stats.tail_events, 0)
        self.assertEqual(stats.clipped_fraction, 0.0)


if __name__ == "__main__":
    unittest.main()
