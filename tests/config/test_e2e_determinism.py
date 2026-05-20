"""End-to-end determinism tests for T27.

Three claims, one test each:
  (a) Two builds with the same (YAML, global_seed) produce byte-identical
      event_sink capture streams.
  (b) Two builds with different global_seed values produce different
      capture streams — proving the seed actually flows.
  (c) Two load_config calls on the same file produce equal Configs —
      isolated check on the loader's own determinism.

The MinimalNode test fixture lives in tests/config/_helpers.py.
"""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from config import build_run, load_config

from _helpers import MINIMAL_YAML, MinimalNode, write_yaml


class _E2EBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self._tmp.name)
        self.path = write_yaml(self.tmp_path, MINIMAL_YAML)

    def tearDown(self):
        self._tmp.cleanup()

    def _capture_run(self, global_seed: int) -> list[tuple]:
        capture: list[tuple] = []
        config = load_config(self.path)
        handle = build_run(config, global_seed=global_seed,
                           node_factory=MinimalNode)
        handle.scheduler.event_sink = (
            lambda *args: capture.append(tuple(args)))
        handle.scheduler.run(t_max=config.t_max)
        return capture


class TestSameSeedByteIdentical(_E2EBase):
    def test_two_runs_byte_identical(self):
        cap_a = self._capture_run(global_seed=42)
        cap_b = self._capture_run(global_seed=42)
        self.assertEqual(cap_a, cap_b)
        self.assertGreater(len(cap_a), 0,
                           "capture should not be empty — MinimalNode "
                           "broadcasts on start, halts on first message")


class TestSeedDivergence(_E2EBase):
    def test_different_seeds_diverge(self):
        cap_a = self._capture_run(global_seed=42)
        cap_b = self._capture_run(global_seed=43)
        self.assertNotEqual(cap_a, cap_b,
                            "different global_seed must produce different "
                            "event streams — otherwise the seed is not "
                            "flowing through the random draws")


class TestLoadDeterminism(_E2EBase):
    def test_two_loads_equal(self):
        a = load_config(self.path)
        b = load_config(self.path)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
