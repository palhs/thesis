"""Unit tests for the scheduler event taxonomy (simulation-design.md §5)."""
import unittest

from scheduler import Delivery, Event, PhaseAdvance, TimerFire


class TestEventTaxonomy(unittest.TestCase):
    def test_delivery_carries_message(self):
        d = Delivery(msg="envelope")
        self.assertEqual(d.msg, "envelope")

    def test_timerfire_carries_id_and_payload(self):
        tf = TimerFire(timer_id="round", payload={"view": 3})
        self.assertEqual(tf.timer_id, "round")
        self.assertEqual(tf.payload, {"view": 3})

    def test_phaseadvance_carries_phase_id(self):
        pa = PhaseAdvance(phase_id=2)
        self.assertEqual(pa.phase_id, 2)

    def test_event_union_includes_all_three(self):
        for ev in (Delivery(msg=None), TimerFire(timer_id="t", payload=None),
                   PhaseAdvance(phase_id=0)):
            self.assertIsInstance(ev, Event.__args__)


if __name__ == "__main__":
    unittest.main()
