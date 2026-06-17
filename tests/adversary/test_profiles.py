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


class TestEquivocateProfile(unittest.TestCase):
    def test_fields_and_defaults(self):
        from adversary.profiles import EquivocateProfile
        p = EquivocateProfile(nodes=(8, 9), intensity=0.2)
        self.assertEqual(p.nodes, (8, 9))
        self.assertEqual(p.intensity, 0.2)
        self.assertEqual(p.partition_strategy, "half-half")
        self.assertEqual(p.kind, "equivocate-vote")
        # No magnitude field: equivocate is binary, like offline.
        self.assertFalse(hasattr(p, "mult"))

    def test_is_frozen(self):
        from adversary.profiles import EquivocateProfile
        p = EquivocateProfile(nodes=(), intensity=0.0)
        with self.assertRaises(FrozenInstanceError):
            p.intensity = 0.5            # type: ignore[misc]

    def test_importable_from_package_top_level(self):
        # Mirrors how DelayProfile/OfflineProfile are re-exported by the
        # adversary package (__init__.py import + __all__).
        from adversary import EquivocateProfile as PkgEquivocateProfile
        from adversary.profiles import EquivocateProfile
        self.assertIs(PkgEquivocateProfile, EquivocateProfile)


if __name__ == "__main__":
    unittest.main()
