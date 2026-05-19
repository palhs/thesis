"""Unit tests for Phase and validate_timeline (network-model-phases.md §5)."""
import math
import unittest

from network.phases import DelayDist, Partition, Phase, validate_timeline

D = DelayDist("constant", {"delay": 10})


def _phase(t0, t1, p_drop=0.0, partitions=()):
    return Phase(t_start=t0, t_end=t1, delay=D, p_drop=p_drop,
                 partitions=partitions)


class TestValidateTimeline(unittest.TestCase):
    def test_valid_single_open_phase(self):
        validate_timeline((_phase(0, math.inf),), {0, 1})  # no raise

    def test_valid_multi_phase(self):
        validate_timeline(
            (_phase(0, 100), _phase(100, 250), _phase(250, math.inf)),
            {0, 1})  # no raise

    def test_valid_phase_with_well_formed_partition(self):
        good = Partition(groups=((0,), (1,)))
        validate_timeline(
            (_phase(0, math.inf, partitions=(good,)),), {0, 1})  # no raise

    def test_empty_timeline_rejected(self):
        with self.assertRaisesRegex(ValueError, "timeline is empty"):
            validate_timeline((), {0})

    def test_first_phase_not_at_zero_rejected(self):
        with self.assertRaisesRegex(ValueError, "first phase must start"):
            validate_timeline((_phase(5, math.inf),), {0})

    def test_zero_width_phase_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-positive width"):
            validate_timeline((_phase(0, 0), _phase(0, math.inf)), {0})

    def test_non_contiguous_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-contiguous"):
            validate_timeline((_phase(0, 100), _phase(150, math.inf)), {0})

    def test_infinite_interior_boundary_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-finite t_end"):
            validate_timeline(
                (_phase(0, math.inf), _phase(math.inf, math.inf)), {0})

    def test_p_drop_one_rejected(self):
        with self.assertRaisesRegex(ValueError, "not in"):
            validate_timeline((_phase(0, math.inf, p_drop=1.0),), {0})

    def test_partition_under_two_groups_rejected(self):
        bad = Partition(groups=((0, 1),))
        with self.assertRaisesRegex(ValueError, "2 groups"):
            validate_timeline((_phase(0, math.inf, partitions=(bad,)),),
                              {0, 1})

    def test_partition_empty_group_rejected(self):
        bad = Partition(groups=((0,), ()))
        with self.assertRaisesRegex(ValueError, "empty group"):
            validate_timeline((_phase(0, math.inf, partitions=(bad,)),), {0})

    def test_partition_overlapping_groups_rejected(self):
        bad = Partition(groups=((0, 1), (1, 2)))
        with self.assertRaisesRegex(ValueError,
                                    "appears in multiple groups"):
            validate_timeline((_phase(0, math.inf, partitions=(bad,)),),
                              {0, 1, 2})

    def test_partition_undeclared_nodeid_rejected(self):
        bad = Partition(groups=((0,), (9,)))
        with self.assertRaisesRegex(ValueError, "not registered"):
            validate_timeline((_phase(0, math.inf, partitions=(bad,)),),
                              {0, 1})


if __name__ == "__main__":
    unittest.main()
