"""Unit tests for src/config/schema.py — Config, SeedsConfig, RunHandle."""
from __future__ import annotations

import math
import unittest
from dataclasses import FrozenInstanceError
from types import MappingProxyType

from config.schema import Config, RunHandle, SeedsConfig
from network.phases import DelayDist, Phase


class TestSeedsConfig(unittest.TestCase):
    def test_construction(self):
        s = SeedsConfig(n_runs=20)
        self.assertEqual(s.n_runs, 20)

    def test_frozen(self):
        s = SeedsConfig(n_runs=20)
        with self.assertRaises(FrozenInstanceError):
            s.n_runs = 21          # type: ignore[misc]

    def test_structural_equality(self):
        self.assertEqual(SeedsConfig(n_runs=5), SeedsConfig(n_runs=5))
        self.assertNotEqual(SeedsConfig(n_runs=5), SeedsConfig(n_runs=6))


_PHASES = (
    Phase(t_start=0.0, t_end=math.inf,
          delay=DelayDist("constant", {"delay": 50.0})),
)


class TestConfig(unittest.TestCase):
    def _make(self, **kw):
        defaults = dict(
            n=4,
            t_max=1000.0,
            seeds=SeedsConfig(n_runs=20),
            network=_PHASES,
            adversary={},
            protocol_knobs={},
            workload={},
        )
        defaults.update(kw)
        return Config(**defaults)

    def test_construction(self):
        c = self._make()
        self.assertEqual(c.n, 4)
        self.assertEqual(c.t_max, 1000.0)
        self.assertEqual(c.seeds.n_runs, 20)
        self.assertEqual(c.network, _PHASES)
        self.assertEqual(c.adversary, {})
        self.assertEqual(c.protocol_knobs, {})
        self.assertEqual(c.workload, {})

    def test_frozen(self):
        c = self._make()
        with self.assertRaises(FrozenInstanceError):
            c.n = 7                # type: ignore[misc]

    def test_structural_equality_same_inputs(self):
        # Two loads of the same YAML must produce equal Configs.
        self.assertEqual(self._make(), self._make())

    def test_inequality_when_seed_block_differs(self):
        self.assertNotEqual(self._make(seeds=SeedsConfig(n_runs=20)),
                            self._make(seeds=SeedsConfig(n_runs=30)))


class TestRunHandle(unittest.TestCase):
    def test_nodes_field_is_immutable_mapping(self):
        # Pure shape test — no Scheduler/Network construction here; that's
        # covered in test_factory.py.
        nodes_view = MappingProxyType({0: object(), 1: object()})
        handle = RunHandle(
            scheduler=object(),  # type: ignore[arg-type]
            network=object(),    # type: ignore[arg-type]
            nodes=nodes_view,
        )
        with self.assertRaises(TypeError):
            handle.nodes[2] = object()    # type: ignore[index]
        self.assertEqual(set(handle.nodes), {0, 1})


if __name__ == "__main__":
    unittest.main()
