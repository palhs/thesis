"""Snowman honest baseline scenarios.

Includes n=4 in SCENARIOS — the rescaling-boundary case
(metric-reconciliation §Snowman parameter rescaling §Comparative-claim
exclusion at n=4). The unified CSV writer skips n=4 from the main file
and src/output/baseline.py writes the sanity row to a sibling.

Design spec: docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import math
from types import MappingProxyType

from common import run_to_completion
from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventRecord
from network import DelayDist, Phase
from output.schema import ScenarioMeta
from scheduler import RunResult
from workload import WorkloadConfig, generate_batches

from . import SnowmanNode


_MINIMAL_DELAY = (
    Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),
)

_T_MAX = 20.0
_SLOT_DURATION = 1.0
_BETA = 15

# Workload axis defaults (experiment-matrix §6 committed defaults). Held in
# one place so ScenarioMeta and the generator config cannot drift apart.
_ARRIVAL_PROCESS = "poisson"
_OFFERED_RATE = 100.0
_TX_BYTES = 512
_CONFLICT_RATE = 0.0


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


def _slot_workload(global_seed: int) -> list[tuple[bytes, ...]]:
    """Build the slot-indexed batch stream for one run.

    Generates the deterministic batch stream once from `global_seed`
    (same `(config, global_seed)` -> identical stream — the generator's
    byte-identical contract), one batch per slot. Every SnowmanNode holds
    this same list; only the per-slot round-robin proposer reads its slot's
    entry (snowman/node.py:_propose). We size to cover the window with a
    small margin (`ceil(_T_MAX / _SLOT_DURATION) + 2`) so no slot the
    window reaches ever falls past the stream.
    """
    cfg = WorkloadConfig(_ARRIVAL_PROCESS, _OFFERED_RATE,
                         _TX_BYTES, _CONFLICT_RATE)
    n_opportunities = math.ceil(_T_MAX / _SLOT_DURATION) + 2
    batches = generate_batches(cfg, global_seed,
                               n_opportunities=n_opportunities,
                               interval=_SLOT_DURATION)
    return [b for b in batches]


def _factory(n: int):
    def make(node_id: int, global_seed: int) -> SnowmanNode:
        return SnowmanNode(
            node_id=node_id, weight=1.0, endpoint=None,
            global_seed=global_seed, n=n,
            slot_duration=_SLOT_DURATION, beta=_BETA,
            workload=_slot_workload(global_seed),
        )
    return make


def _scenario(n: int, seed: int) -> ScenarioMeta:
    """One windowed Snowman scenario. run_id omits the seed — the `seed`
    column disambiguates rows; row identity is (protocol, n, run_id, seed).
    slots_per_epoch stays None (N/A for Snowman; per-block finality)."""
    return ScenarioMeta(
        run_id=f"snowman-n{n}", protocol="snowman", n=n, variant=None,
        seed=seed, t_max=_T_MAX,
        arrival_process=_ARRIVAL_PROCESS, tx_bytes=_TX_BYTES,
        conflict_rate=_CONFLICT_RATE, offered_rate=_OFFERED_RATE,
        interval=_SLOT_DURATION,
    )


# Scaling sweep: n in {4,7,10,16,25} x seed in range(20) = 100 scenarios.
# n=4 stays in SCENARIOS — the orchestrator routes it to the sibling
# snowman_n4_sanity.csv (it is excluded from the main file).
_N_VALUES: tuple[int, ...] = (4, 7, 10, 16, 25)
_SEEDS: tuple[int, ...] = tuple(range(20))

SCENARIOS: tuple[ScenarioMeta, ...] = tuple(
    _scenario(n, seed) for n in _N_VALUES for seed in _SEEDS
)


def run_scenario(meta: ScenarioMeta
                 ) -> tuple[list[EventRecord], RunResult, ScenarioMeta]:
    config = _config(meta.n)
    handle = build_run(config, meta.seed, _factory(meta.n))
    t_max = None if math.isnan(meta.t_max) else meta.t_max
    result, logger = run_to_completion(handle, t_max=t_max)
    return logger.records, result, meta
