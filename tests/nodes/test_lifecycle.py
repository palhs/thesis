"""Unit tests for the Node lifecycle enums (node-model.md §3)."""
import unittest

from nodes import HaltReason, Lifecycle


class TestLifecycleEnums(unittest.TestCase):
    def test_lifecycle_has_three_monotonic_stages(self):
        self.assertEqual([s.name for s in Lifecycle],
                         ["CREATED", "RUNNING", "HALTED"])

    def test_lifecycle_values_are_zero_to_two(self):
        self.assertEqual([s.value for s in Lifecycle], [0, 1, 2])

    def test_halt_reason_has_four_members(self):
        self.assertEqual({r.name for r in HaltReason},
                         {"RUN_END", "CRASHED", "SLASHED", "EXITED"})


if __name__ == "__main__":
    unittest.main()
