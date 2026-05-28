"""Unit tests for run_to_completion (T39, wiki/concepts/runner.md)."""
from __future__ import annotations

import math
import unittest
from types import MappingProxyType

from common import run_to_completion
from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from nodes import Node


_MIN_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)


class _QuiescentNode(Node):
    """Broadcasts one TOKEN on start; recipients do not re-broadcast,
    so the run reaches quiescence after one round of n*(n-1) deliveries."""

    def __init__(self, node_id, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)

    def _on_start(self, t):
        self.broadcast("TOKEN", {"from": self.id}, t)

    def _on_message(self, msg, t):
        pass

    def _on_timer(self, timer_id, payload, t):
        pass


class _ReArmingNode(Node):
    """Re-arms a 0.1-second timer indefinitely; no quiescence — only a
    deadline can stop the run."""

    def __init__(self, node_id, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)

    def _on_start(self, t):
        self.set_timer("tick", 0.1, None, t)

    def _on_message(self, msg, t):
        pass

    def _on_timer(self, timer_id, payload, t):
        self.set_timer("tick", 0.1, None, t)


def _config(n):
    return Config(
        n=n, t_max=math.inf, seeds=SeedsConfig(n_runs=1),
        network=_MIN_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _quiescent_factory():
    def make(node_id, global_seed):
        return _QuiescentNode(node_id=node_id, global_seed=global_seed)
    return make


def _rearming_factory():
    def make(node_id, global_seed):
        return _ReArmingNode(node_id=node_id, global_seed=global_seed)
    return make


class TestRunToCompletion(unittest.TestCase):

    def test_returns_run_result_and_logger(self):
        handle = build_run(_config(2), 42, _quiescent_factory())
        result, logger = run_to_completion(handle)
        self.assertIsInstance(logger, EventLogger)
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertGreater(len(logger.records), 0)

    def test_default_logger_constructed_when_omitted(self):
        handle = build_run(_config(2), 42, _quiescent_factory())
        _, logger = run_to_completion(handle)
        # Fresh logger captured the run.
        self.assertGreater(len(logger.records), 0)

    def test_caller_supplied_logger_used(self):
        pre = EventLogger()
        handle = build_run(_config(2), 42, _quiescent_factory())
        _, logger = run_to_completion(handle, logger=pre)
        self.assertIs(logger, pre)
        self.assertGreater(len(logger.records), 0)

    def test_t_max_none_runs_to_quiescence(self):
        handle = build_run(_config(2), 42, _quiescent_factory())
        result, _ = run_to_completion(handle, t_max=None)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_t_max_float_runs_to_deadline(self):
        handle = build_run(_config(2), 42, _rearming_factory())
        result, _ = run_to_completion(handle, t_max=1.0)
        self.assertEqual(result.stopped_by, "deadline")
        self.assertGreaterEqual(result.now, 1.0)

    def test_two_runs_byte_identical(self):
        h1 = build_run(_config(2), 42, _quiescent_factory())
        _, a = run_to_completion(h1)
        h2 = build_run(_config(2), 42, _quiescent_factory())
        _, b = run_to_completion(h2)
        self.assertEqual(list(a.records), list(b.records))


if __name__ == "__main__":
    unittest.main()
