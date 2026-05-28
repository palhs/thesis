"""Casper FFG honest baseline scenarios.

SCENARIOS is the list of (n, variant) scenarios run by
src/output/baseline.py and asserted by
tests/integration/test_pos_baseline.py. run_scenario(meta) builds the
FFG stack at meta.n with the meta.variant stake distribution, runs to
meta.t_max, and returns the (records, result, meta) triple the unified
CSV writer consumes.

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

from .node import CasperNode


_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)
_T_MAX = 20.0
_SLOT_DURATION = 1.0
_SLOTS_PER_EPOCH = 2


def _uniform(n: int) -> dict[int, float]:
    return {i: 3.0 for i in range(n)}


def _nonuniform_n4() -> dict[int, float]:
    return {0: 5.0, 1: 4.0, 2: 2.0, 3: 1.0}


def _stake_table(n: int, variant: str | None) -> dict[int, float]:
    if variant == "nonuniform":
        assert n == 4, "nonuniform is only defined at n=4 today"
        return _nonuniform_n4()
    return _uniform(n)


def _config(n: int, variant: str | None) -> Config:
    return Config(
        n=n,
        t_max=_T_MAX,
        seeds=SeedsConfig(n_runs=1),
        network=_MINIMAL_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _factory(n: int, variant: str | None):
    stake_table = _stake_table(n, variant)

    def make(node_id: int, global_seed: int) -> CasperNode:
        return CasperNode(
            node_id=node_id, weight=stake_table[node_id], endpoint=None,
            global_seed=global_seed, n=n, stake_table=stake_table,
            slot_duration=_SLOT_DURATION, slots_per_epoch=_SLOTS_PER_EPOCH,
        )
    return make


SCENARIOS: tuple[ScenarioMeta, ...] = (
    ScenarioMeta(run_id="casper-ffg-n4-uniform",     protocol="casper-ffg",
                 n=4,  variant="uniform",    seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="casper-ffg-n7-uniform",     protocol="casper-ffg",
                 n=7,  variant="uniform",    seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="casper-ffg-n10-uniform",    protocol="casper-ffg",
                 n=10, variant="uniform",    seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="casper-ffg-n4-nonuniform",  protocol="casper-ffg",
                 n=4,  variant="nonuniform", seed=42, t_max=_T_MAX),
)


def run_scenario(meta: ScenarioMeta
                 ) -> tuple[list[EventRecord], RunResult, ScenarioMeta]:
    config = _config(meta.n, meta.variant)
    handle = build_run(config, meta.seed, _factory(meta.n, meta.variant))
    t_max = None if math.isnan(meta.t_max) else meta.t_max
    result, logger = run_to_completion(handle, t_max=t_max)
    return logger.records, result, meta
