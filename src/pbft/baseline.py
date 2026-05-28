"""PBFT honest baseline scenarios.

SCENARIOS is the list of n values run by src/output/baseline.py and
asserted by tests/integration/test_pbft_baseline.py. run_scenario(meta)
builds the PBFT stack at meta.n, runs to quiescence, and returns the
(records, result, meta) triple the unified CSV writer consumes.

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

from . import PBFTNode


_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)

# The single request the honest run commits; rides on node 0's workload.
REQUEST = b"X"

# The primary's propose timer fires at this t, emitting the PRE-PREPARE
# for seq 0; every `decided` event therefore carries t > PROPOSE_DELAY.
PROPOSE_DELAY = 1.0


def _config(n: int) -> Config:
    return Config(
        n=n,
        t_max=math.inf,
        seeds=SeedsConfig(n_runs=1),
        network=_MINIMAL_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _factory(n: int):
    """build_run wants (node_id, global_seed) -> Node. All-honest
    PBFTNodes; the single request rides on node 0; vc_delay is
    generous so no honest run ever triggers a view-change."""
    def make(node_id: int, global_seed: int) -> PBFTNode:
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n,
                        workload=[REQUEST] if node_id == 0 else None,
                        propose_delay=PROPOSE_DELAY, initial_view=0,
                        vc_delay=1000.0)
    return make


SCENARIOS: tuple[ScenarioMeta, ...] = (
    ScenarioMeta(run_id="pbft-n4",  protocol="pbft", n=4,
                 variant=None, seed=42, t_max=math.nan),
    ScenarioMeta(run_id="pbft-n7",  protocol="pbft", n=7,
                 variant=None, seed=42, t_max=math.nan),
    ScenarioMeta(run_id="pbft-n10", protocol="pbft", n=10,
                 variant=None, seed=42, t_max=math.nan),
)


def run_scenario(meta: ScenarioMeta
                 ) -> tuple[list[EventRecord], RunResult, ScenarioMeta]:
    config = _config(meta.n)
    handle = build_run(config, meta.seed, _factory(meta.n))
    t_max = None if math.isnan(meta.t_max) else meta.t_max
    result, logger = run_to_completion(handle, t_max=t_max)
    return logger.records, result, meta
