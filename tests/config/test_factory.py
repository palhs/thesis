"""Unit tests for src/config/factory.py — build_run."""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from config import RunHandle, build_run, load_config
from network import Network
from scheduler import Scheduler

from _helpers import MINIMAL_YAML, MinimalNode, write_yaml


class _FactoryTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = pathlib.Path(self._tmp.name)
        self.path = write_yaml(self.tmp_path, MINIMAL_YAML)
        self.config = load_config(self.path)

    def tearDown(self):
        self._tmp.cleanup()


class TestReturn(_FactoryTestBase):
    def test_returns_run_handle(self):
        handle = build_run(self.config, global_seed=0,
                           node_factory=MinimalNode)
        self.assertIsInstance(handle, RunHandle)
        self.assertIsInstance(handle.scheduler, Scheduler)
        self.assertIsInstance(handle.network, Network)
        self.assertEqual(set(handle.nodes), {0, 1, 2, 3})

    def test_nodes_view_is_immutable(self):
        handle = build_run(self.config, global_seed=0,
                           node_factory=MinimalNode)
        with self.assertRaises(TypeError):
            handle.nodes[42] = object()        # type: ignore[index]


class TestFactoryContract(_FactoryTestBase):
    def test_node_factory_called_with_global_seed(self):
        seen: list[tuple[int, int]] = []

        def factory(nid, seed):
            seen.append((nid, seed))
            return MinimalNode(nid, seed)

        build_run(self.config, global_seed=99, node_factory=factory)
        self.assertEqual(seen,
                         [(0, 99), (1, 99), (2, 99), (3, 99)])

    def test_mismatched_node_id_fails_fast(self):
        def bad_factory(nid, seed):
            # Return a Node whose id differs from the requested nid.
            return MinimalNode(node_id=nid + 100, global_seed=seed)

        with self.assertRaises(AssertionError) as cm:
            build_run(self.config, global_seed=0, node_factory=bad_factory)
        self.assertIn("node.id", str(cm.exception).lower())


class TestBootstrapOrder(_FactoryTestBase):
    def test_network_started_before_any_node_started(self):
        # MinimalNode._on_start calls broadcast(), which raises if Network
        # is not started. The factory must therefore call Network.start
        # before any Node.start — proven by the construction succeeding
        # (a regression would raise "Network.submit_* called before start()").
        try:
            build_run(self.config, global_seed=0, node_factory=MinimalNode)
        except RuntimeError as e:
            self.fail(f"build_run raised {e!r}; "
                      "Network.start was not called before Node.start")

    def test_nodes_started_in_sorted_node_id_order(self):
        order: list[int] = []

        class OrderRecordingNode(MinimalNode):
            def _on_start(self, t):
                order.append(self.id)
                super()._on_start(t)

        build_run(self.config, global_seed=0,
                  node_factory=OrderRecordingNode)
        self.assertEqual(order, sorted(order))
        self.assertEqual(order, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
