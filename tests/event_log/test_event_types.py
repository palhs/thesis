"""T24 event-type constant vocabulary."""
import unittest

from event_log import event_types as et


class TestEventTypes(unittest.TestCase):
    def test_emit_event_names(self):
        self.assertEqual(et.HALTED, "halted")
        self.assertEqual(et.DECIDED, "decided")

    def test_transport_event_names(self):
        self.assertEqual(et.DELIVERY, "delivery")
        self.assertEqual(et.TIMER_FIRE, "timer_fire")
        self.assertEqual(et.PHASE_ADVANCE, "phase_advance")

    def test_transport_set_is_exactly_the_three_transport_types(self):
        self.assertEqual(
            et.TRANSPORT_EVENT_TYPES,
            frozenset({"delivery", "timer_fire", "phase_advance"}))


if __name__ == "__main__":
    unittest.main()
