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

from . import SnowmanNode


_MINIMAL_DELAY = (
    Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),
)

_T_MAX = 20.0
_SLOT_DURATION = 1.0
_BETA = 15


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


SCENARIOS: tuple[ScenarioMeta, ...] = (
    ScenarioMeta(run_id="snowman-n4",  protocol="snowman", n=4,
                 variant=None, seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="snowman-n7",  protocol="snowman", n=7,
                 variant=None, seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="snowman-n10", protocol="snowman", n=10,
                 variant=None, seed=42, t_max=_T_MAX),
)


def run_scenario(meta: ScenarioMeta
                 ) -> tuple[list[EventRecord], RunResult, ScenarioMeta]:
    config = _config(meta.n)
    handle = build_run(config, meta.seed, _factory(meta.n))
    t_max = None if math.isnan(meta.t_max) else meta.t_max
    result, logger = run_to_completion(handle, t_max=t_max)
    return logger.records, result, meta
