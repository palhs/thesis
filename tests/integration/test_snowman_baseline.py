"""T38 honest-path build-verification baseline at n in {4, 7, 10}.

Asserts the four T38 outcomes per scenario (design spec §8.2):
  1. Every honest node ACCEPTS every announced block.
  2. Zero forks — every node's `decided` for a given block agrees on value.
  3. Finalisation latency is logged on every decided event.
  4. Two runs with the same (config, global_seed) are byte-identical.

Mirrors tests/integration/test_pos_baseline.py.
"""
import math
import unittest
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from snowman import SnowmanNode


_MINIMAL_DELAY = (
    Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),
)

_T_MAX = 20.0
_SLOT_DURATION = 1.0
_BETA = 15

_SCENARIOS: tuple[tuple[str, int], ...] = (
    ("n=4", 4),
    ("n=7", 7),
    ("n=10", 10),
)


def _config(n: int) -> Config:
    return Config(
        n=n,
        t_max=_T_MAX,
        seeds=SeedsConfig(n_runs=1),
        network=_MINIMAL_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _factory(n: int):
    def make(node_id: int, global_seed: int) -> SnowmanNode:
        return SnowmanNode(
            node_id=node_id, weight=1.0, endpoint=None,
            global_seed=global_seed, n=n,
            slot_duration=_SLOT_DURATION, beta=_BETA,
        )
    return make


def _run(n: int, global_seed: int = 42):
    logger = EventLogger()
    handle = build_run(_config(n), global_seed, _factory(n))
    handle.scheduler.event_sink = logger.sink
    result = handle.scheduler.run(t_max=_T_MAX)
    return logger, result, dict(handle.nodes)


def _by(records, event_type):
    return [r for r in records if r.event_type == event_type]


class TestSnowmanHonestBaseline(unittest.TestCase):

    def test_every_node_accepts_every_announced_block(self):
        """Outcome 1: every honest node decides every announced block."""
        for label, n in _SCENARIOS:
            with self.subTest(scenario=label):
                logger, result, nodes = _run(n)
                self.assertEqual(result.stopped_by, "deadline")
                announced = {r.fields["block_id"]
                             for r in _by(logger.records, "snowman_announced")}
                self.assertGreater(len(announced), 0)
                decided_by_node: dict[int, set] = {}
                for r in _by(logger.records, "decided"):
                    decided_by_node.setdefault(
                        r.node_id, set()).add(r.fields["instance_id"])
                self.assertEqual(sorted(decided_by_node), list(range(n)),
                                 f"{label}: not every node emitted decided")
                for node_id in range(n):
                    self.assertEqual(decided_by_node[node_id], announced,
                                     f"{label}: node {node_id} missed blocks")

    def test_no_forks(self):
        """Outcome 2: every node decides the same value for every block."""
        for label, n in _SCENARIOS:
            with self.subTest(scenario=label):
                logger, _, _ = _run(n)
                by_block: dict[bytes, set] = {}
                for r in _by(logger.records, "decided"):
                    by_block.setdefault(
                        r.fields["instance_id"], set()).add(r.fields["value"])
                self.assertGreater(len(by_block), 0)
                for block_id, values in by_block.items():
                    self.assertEqual(
                        len(values), 1,
                        f"{label}: fork at block {block_id!r}: {values}")
                self.assertEqual(
                    len(_by(logger.records, "snowman_rejected")), 0,
                    f"{label}: unexpected rejection on honest path")

    def test_finality_latency_logged(self):
        """Outcome 3: every decided event has a finite, positive timestamp."""
        for label, n in _SCENARIOS:
            with self.subTest(scenario=label):
                logger, _, _ = _run(n)
                decided = _by(logger.records, "decided")
                self.assertGreater(len(decided), 0)
                for r in decided:
                    self.assertTrue(math.isfinite(r.t))
                    self.assertGreater(r.t, 0.0)

    def test_determinism_byte_identical(self):
        """Outcome 4: two seed-identical runs produce byte-identical event
        streams — covers the RNG K-peer sampling path that PBFT and Casper
        FFG baselines do not (week7-decision §5.1 watch-for closure)."""
        for label, n in _SCENARIOS:
            with self.subTest(scenario=label):
                a, _, _ = _run(n, global_seed=42)
                b, _, _ = _run(n, global_seed=42)
                self.assertEqual(list(a.records), list(b.records),
                                 f"{label}: determinism broken")


if __name__ == "__main__":
    unittest.main()
