# tests/integration/test_pos_baseline.py
"""T35 — PoS (simplified Casper FFG) correctness under honest validators.

A correctness experiment driving the full Casper FFG honest path
([[algorithms/pos]]) across the W3 stack with an all-honest validator set
at n in {4, 7, 10} uniform stake, plus an n=4 non-uniform-stake scenario
preserving the coverage of the superseded T32 baseline. Asserts the three
T35 outcomes — every node finalises, no forks, finalisation latency
logged — plus byte-identical determinism.

Distinct from tests/integration/test_casper_baseline.py (the T32
build-verification suite); T35 adds no src/ code — the protocol is
complete (T32 implementation + T33 stake-weighted proposer + T34
extracted finality module). Re-records the canonical event-stream
snapshot under the T33 proposer rule (the T32 page's ## Revisions note
forwards readers here).

Companion experiment page: wiki/experiments/2026-05-25_pos-baseline.md.

Re-run:
  PYTHONPATH=src:tests/integration python3 -m unittest test_pos_baseline -v
"""
import math
import unittest
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from pos import CasperNode


# The network model requires t_delivered > t_sent, so a literal-zero delay
# is unrepresentable; 1e-9 is the minimum constant delay (matches the T30
# / T32 baselines). Honest run: no drop, no partition.
_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)

# Honest scenarios. The first three sweep n at uniform stake (mirrors
# T30); the fourth preserves T32's non-uniform-stake coverage so this
# page fully supersedes the T32 byte-identical snapshot.
def _uniform(n: int) -> dict[int, float]:
    return {i: 3.0 for i in range(n)}


_SCENARIOS: tuple[tuple[str, int, dict[int, float]], ...] = (
    ("n=4 uniform", 4, _uniform(4)),
    ("n=7 uniform", 7, _uniform(7)),
    ("n=10 uniform", 10, _uniform(10)),
    ("n=4 non-uniform", 4, {0: 5.0, 1: 4.0, 2: 2.0, 3: 1.0}),
)

# slot_duration=1.0, slots_per_epoch=2, attest_offset=1 (default) =>
# epoch e finalises at t = (2*(e+1) + 1)*slot_duration + epsilon, so
# epoch 1 finalises near t=5.0 and epoch 8 near t=19.0. t_max=20.0
# matches the T32 baseline and covers 8 finalised epochs.
_T_MAX = 20.0
_SLOT_DURATION = 1.0
_SLOTS_PER_EPOCH = 2

# Epoch 1 cannot finalise before the slot-5 attestation fires (no earlier
# slot completes the second justify link). Used as the finalisation-time
# lower bound for the latency-logged check.
_EPOCH1_FINALISE_FLOOR = (
    (2 * _SLOTS_PER_EPOCH + 1) * _SLOT_DURATION  # = 5.0
)

# At t_max=20.0 every scenario finalises epochs 1..8 — eight per node.
_EXPECTED_FINALISED_EPOCHS = 8


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


def _factory(n: int, stake_table: dict[int, float]):
    """build_run wants (node_id, global_seed) -> Node. All-honest
    CasperNodes; each node carries the full stake_table and its own
    weight equals stake_table[node_id]."""
    def make(node_id: int, global_seed: int) -> CasperNode:
        return CasperNode(
            node_id=node_id, weight=stake_table[node_id], endpoint=None,
            global_seed=global_seed, n=n, stake_table=stake_table,
            slot_duration=_SLOT_DURATION, slots_per_epoch=_SLOTS_PER_EPOCH,
        )
    return make


def _run(n: int, stake_table: dict[int, float], global_seed: int = 42):
    """Build, attach an EventLogger, run to t_max -> (logger, result).

    Casper has no quiescence — the slot timer re-arms indefinitely — so
    every run is bounded by t_max only. config.factory.build_run does not
    pipe Config.t_max into scheduler.run(), so pass it through here (same
    pattern as test_casper_baseline.py).
    """
    logger = EventLogger()
    handle = build_run(_config(n), global_seed, _factory(n, stake_table))
    handle.scheduler.event_sink = logger.sink
    result = handle.scheduler.run(t_max=_T_MAX)
    return logger, result


def _count(records, event_type: str) -> int:
    return sum(1 for r in records if r.event_type == event_type)


def _decided(records):
    return [r for r in records if r.event_type == "decided"]


class TestPoSHonestBaseline(unittest.TestCase):
    """Honest Casper FFG at four scenarios: finalises, no forks, latency
    logged, determinism."""

    def test_every_node_finalises(self):
        """Outcome 1: every validator finalises every reachable epoch.
        Each of the n nodes emits casper_finalised + decided once per
        finalised epoch; under t_max=20.0 that is 8 epochs per node."""
        for label, n, stake in _SCENARIOS:
            with self.subTest(scenario=label):
                logger, result = _run(n, stake)
                self.assertEqual(result.stopped_by, "deadline")
                self.assertEqual(
                    _count(logger.records, "casper_finalised"),
                    n * _EXPECTED_FINALISED_EPOCHS)
                decided = _decided(logger.records)
                self.assertEqual(len(decided), n * _EXPECTED_FINALISED_EPOCHS)
                # Every node 0..n-1 appears, and emits exactly one decided
                # per finalised epoch.
                per_node: dict[int, int] = {}
                for r in decided:
                    per_node[r.node_id] = per_node.get(r.node_id, 0) + 1
                self.assertEqual(sorted(per_node), list(range(n)))
                for count in per_node.values():
                    self.assertEqual(count, _EXPECTED_FINALISED_EPOCHS)

    def test_no_forks(self):
        """Outcome 2: no forks. Every node's decided event for a given
        epoch carries the identical checkpoint_hash, and no validator
        rejects a message on the honest path."""
        for label, n, stake in _SCENARIOS:
            with self.subTest(scenario=label):
                logger, _ = _run(n, stake)
                by_epoch: dict[int, set[str]] = {}
                for r in _decided(logger.records):
                    epoch = r.fields["instance_id"]
                    by_epoch.setdefault(epoch, set()).add(r.fields["value"])
                # Epochs 1..8 all finalised, each agreed on one value.
                self.assertEqual(sorted(by_epoch),
                                 list(range(1, _EXPECTED_FINALISED_EPOCHS + 1)))
                for epoch, values in by_epoch.items():
                    self.assertEqual(
                        len(values), 1,
                        f"epoch {epoch} forked: {values}")
                self.assertEqual(_count(logger.records, "casper_rejected"), 0)

    def test_finalisation_latency_logged(self):
        """Outcome 3: finalisation latency is logged. Every decided
        event's t field is finite and at or after the earliest possible
        finalisation moment (the slot-5 attestation that completes epoch
        2's justify link, which finalises epoch 1)."""
        for label, n, stake in _SCENARIOS:
            with self.subTest(scenario=label):
                logger, _ = _run(n, stake)
                decided = _decided(logger.records)
                self.assertGreater(len(decided), 0)
                for r in decided:
                    self.assertTrue(math.isfinite(r.t))
                    self.assertGreaterEqual(r.t, _EPOCH1_FINALISE_FLOOR)

    def test_determinism(self):
        """Two seed-identical runs produce byte-identical event streams —
        the harness reproducibility contract holds for the PoS honest
        path at every scenario, under the T33 stake-weighted proposer
        rule."""
        for label, n, stake in _SCENARIOS:
            with self.subTest(scenario=label):
                a, _ = _run(n, stake, global_seed=42)
                b, _ = _run(n, stake, global_seed=42)
                self.assertEqual(list(a.records), list(b.records))


if __name__ == "__main__":
    unittest.main()
