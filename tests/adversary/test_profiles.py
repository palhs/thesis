"""DelayProfile shape + immutability (T51)."""
from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from adversary.profiles import DelayProfile


class TestDelayProfile(unittest.TestCase):
    def test_fields(self):
        p = DelayProfile(nodes=(8, 9), intensity=0.20, mult=5.0)
        self.assertEqual(p.nodes, (8, 9))
        self.assertEqual(p.intensity, 0.20)
        self.assertEqual(p.mult, 5.0)
        self.assertEqual(p.kind, "delay-emission")

    def test_is_frozen(self):
        p = DelayProfile(nodes=(), intensity=0.0, mult=0.0)
        with self.assertRaises(FrozenInstanceError):
            p.intensity = 0.5            # type: ignore[misc]

    def test_kind_is_fixed_default(self):
        # kind is not a constructor argument the caller varies; it identifies
        # the capability for the (future) adversary dispatch.
        p = DelayProfile(nodes=(9,), intensity=0.1, mult=2.0)
        self.assertEqual(p.kind, "delay-emission")


class TestOfflineProfile(unittest.TestCase):
    def test_offline_profile_fields(self):
        from adversary.profiles import OfflineProfile
        p = OfflineProfile(nodes=(8, 9), intensity=0.2)
        self.assertEqual(p.nodes, (8, 9))
        self.assertEqual(p.intensity, 0.2)
        self.assertEqual(p.kind, "withhold-participation")
        # No magnitude field: offline is binary, not dosed.
        self.assertFalse(hasattr(p, "mult"))


if __name__ == "__main__":
    unittest.main()
