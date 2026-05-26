# tests/integration/test_casper_baseline.py
"""End-to-end: simplified Casper FFG across the full W3 stack
(T32 spec §12.2).

Casper has no quiescence — the slot timer re-arms indefinitely — so every
run is bounded by the scheduler's `t_max`. With slot_duration=1.0 and
slots_per_epoch=2, epoch e finalises after epoch e+1 is justified, which
requires reaching at least slot 3*spe + attest_offset = 7. t_max=20.0
covers ~10 slots — finalisation of epochs 1 and 2 is comfortably inside
the bound.
"""
import math
import unittest
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from pos import CasperNode


# Constant micro-delay: network requires t_delivered > t_sent.
_MINIMAL_DELAY = (
    Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),
)


def _config(n: int, t_max: float) -> Config:
    return Config(
        n=n,
        t_max=t_max,
        seeds=SeedsConfig(n_runs=1),
        network=_MINIMAL_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _factory(n: int, stake_table, *,
             slots_per_epoch: int = 2, slot_duration: float = 1.0):
    """build_run wants (node_id, global_seed) -> Node."""
    def make(node_id: int, global_seed: int) -> CasperNode:
        return CasperNode(
            node_id=node_id, weight=stake_table[node_id], endpoint=None,
            global_seed=global_seed, n=n, stake_table=stake_table,
            slot_duration=slot_duration, slots_per_epoch=slots_per_epoch,
        )
    return make


def _run(n: int, *, stake_table=None, t_max: float = 20.0,
         global_seed: int = 42, slots_per_epoch: int = 2):
    st = stake_table or {i: 3.0 for i in range(n)}
    logger = EventLogger()
    handle = build_run(_config(n, t_max), global_seed,
                       _factory(n, st, slots_per_epoch=slots_per_epoch))
    handle.scheduler.event_sink = logger.sink
    # Casper has no quiescence (the slot timer re-arms indefinitely) — the
    # run is bounded by t_max only. config.factory.build_run does not pipe
    # config.t_max into scheduler.run, so pass it through here.
    result = handle.scheduler.run(t_max=t_max)
    return logger, result


def _count(records, event_type: str) -> int:
    return sum(1 for r in records if r.event_type == event_type)


class TestCasperBaseline_n4(unittest.TestCase):
    def test_epochs_finalise(self):
        logger, _ = _run(n=4, t_max=20.0)
        self.assertGreaterEqual(_count(logger.records, "casper_finalised"), 1)
        self.assertGreaterEqual(_count(logger.records, "decided"), 1)

    def test_no_rejections(self):
        logger, _ = _run(n=4, t_max=20.0)
        self.assertEqual(_count(logger.records, "casper_rejected"), 0)

    def test_decided_in_epoch_order(self):
        logger, _ = _run(n=4, t_max=20.0)
        epochs = [r.fields["instance_id"] for r in logger.records
                  if r.event_type == "decided"]
        self.assertEqual(epochs, sorted(epochs))

    def test_determinism(self):
        a, _ = _run(n=4, t_max=20.0, global_seed=42)
        b, _ = _run(n=4, t_max=20.0, global_seed=42)
        self.assertEqual(list(a.records), list(b.records))


class TestCasperBaseline_n7(unittest.TestCase):
    def test_epochs_finalise(self):
        logger, _ = _run(n=7, t_max=20.0)
        self.assertGreaterEqual(_count(logger.records, "decided"), 1)

    def test_determinism(self):
        a, _ = _run(n=7, t_max=20.0, global_seed=42)
        b, _ = _run(n=7, t_max=20.0, global_seed=42)
        self.assertEqual(list(a.records), list(b.records))


class TestCasperBaseline_nonuniform_stake(unittest.TestCase):
    def test_finalises_with_unequal_stake(self):
        st = {0: 5.0, 1: 4.0, 2: 2.0, 3: 1.0}     # total 12
        logger, _ = _run(n=4, stake_table=st, t_max=20.0)
        self.assertGreaterEqual(_count(logger.records, "decided"), 1)


if __name__ == "__main__":
    unittest.main()
