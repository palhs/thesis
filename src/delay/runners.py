"""Per-protocol run builders for the Family B delay sweep (T46).

Each `run_<proto>(timeline, n, seed)` mirrors the honest baseline factory
in src/{pbft,pos,snowman}/baseline.py but swaps three knobs that the
locked Week-9 delay methodology requires:

  1. NETWORK — the single-phase moderate-delay timeline (uniform[100,500] ms
     or exponential mean-300 ms) replaces the baseline's near-zero constant
     delay. This is the only axis Family B sweeps.
  2. FFG SLOT — Casper FFG's slot_duration rescales to 1.2 s to stay
     coherent with E[delay] = 0.3 s (slot ≥ 4·E[delay], experiment-matrix
     §5). PBFT propose cadence and Snowman slot cadence keep their native
     1.0 s — only FFG couples to the delay regime.
  3. HORIZON — the run executes to t_max = WINDOW_S + BUFFER_S so an
     instance that started just before WINDOW_S still finalizes inside the
     run. The workload covers the FULL horizon (proposers never drain
     mid-run); the WINDOW_S / buffer split and the clip happen downstream
     in src/delay/clip.py, NOT here.

`meta.t_max` is set to WINDOW_S (the measurement window), NOT the run
horizon — the existing T40 reducers use `meta.t_max` as the throughput
denominator, and Family B reports rate over the window, not the buffer.

No shared infrastructure is modified: every knob is an existing Node /
Config constructor argument. Snowman's (K, α_p, α_c) rescale with n
automatically inside SnowmanNode (snowman_parameters(n)); n=25 is a normal
input (K = min(20, 24) = 20, α_c = ⌈0.8·20⌉ = 16).

Design contract: wiki/experiments/2026-06-10_delay-moderate.md
"""
from __future__ import annotations

import math

from common import run_to_completion
from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult
from workload import WorkloadConfig, generate_batches

from pbft import PBFTNode
from pos.node import CasperNode
from snowman import SnowmanNode

from . import config as cfg

RunTriple = tuple[list[EventRecord], RunResult, ScenarioMeta]


def _config(n: int, timeline: cfg.Timeline) -> Config:
    """One Config point: the delay timeline as the network, run horizon
    t_max = WINDOW_S + BUFFER_S. The opaque sections stay empty (Family B
    is honest, baseline workload)."""
    return Config(
        n=n,
        t_max=cfg.T_MAX,
        seeds=SeedsConfig(n_runs=1),
        network=timeline.phases(),
        adversary={},
        protocol_knobs={},
        workload={},
    )


def _batches(seed: int, interval: float):
    """Deterministic batch stream covering the FULL run horizon plus a
    small margin, so the proposer never drains mid-run (which would stop
    new instances starting before the buffer even begins)."""
    n_opportunities = math.ceil(cfg.T_MAX / interval) + 2
    return generate_batches(
        WorkloadConfig(cfg.ARRIVAL_PROCESS, cfg.OFFERED_RATE,
                       cfg.TX_BYTES, cfg.CONFLICT_RATE),
        seed, n_opportunities=n_opportunities, interval=interval,
    )


def _meta(protocol: str, run_id: str, n: int, seed: int,
          interval: float, slots_per_epoch: int | None) -> ScenarioMeta:
    """ScenarioMeta with t_max = WINDOW_S (the measurement window, the
    throughput denominator the reducers read), NOT the run horizon."""
    return ScenarioMeta(
        run_id=run_id, protocol=protocol, n=n, variant=None, seed=seed,
        t_max=cfg.WINDOW_S,
        arrival_process=cfg.ARRIVAL_PROCESS, tx_bytes=cfg.TX_BYTES,
        conflict_rate=cfg.CONFLICT_RATE, offered_rate=cfg.OFFERED_RATE,
        interval=interval, slots_per_epoch=slots_per_epoch,
    )


# --- PBFT ---------------------------------------------------------------

def run_pbft(timeline: cfg.Timeline, n: int, seed: int) -> RunTriple:
    propose = cfg.PBFT_PROPOSE_DELAY_S
    batches = [b"".join(b) for b in _batches(seed, propose)]

    def make(node_id: int, global_seed: int) -> PBFTNode:
        workload = batches if node_id == 0 else None
        # vc_delay must clear the moderate-delay round so no honest run
        # spuriously triggers a view-change under 100–500 ms delay.
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n, workload=workload,
                        propose_delay=propose, initial_view=0,
                        vc_delay=10000.0)

    meta = _meta("pbft", f"pbft-n{n}", n, seed, propose, None)
    handle = build_run(_config(n, timeline), seed, make)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# --- Casper FFG ---------------------------------------------------------

def run_ffg(timeline: cfg.Timeline, n: int, seed: int) -> RunTriple:
    slot = timeline.ffg_slot_duration_s          # rescaled (1.2 s) per §5
    spe = cfg.FFG_SLOTS_PER_EPOCH
    stake = {i: 3.0 for i in range(n)}
    batches = [b for b in _batches(seed, slot)]

    def make(node_id: int, global_seed: int) -> CasperNode:
        return CasperNode(node_id=node_id, weight=stake[node_id],
                          endpoint=None, global_seed=global_seed, n=n,
                          stake_table=stake, slot_duration=slot,
                          slots_per_epoch=spe, workload=batches)

    meta = _meta("casper-ffg", f"casper-ffg-n{n}", n, seed, slot, spe)
    handle = build_run(_config(n, timeline), seed, make)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# --- Snowman ------------------------------------------------------------

def run_snowman(timeline: cfg.Timeline, n: int, seed: int) -> RunTriple:
    slot = cfg.SNOWMAN_SLOT_DURATION_S
    batches = [b for b in _batches(seed, slot)]

    def make(node_id: int, global_seed: int) -> SnowmanNode:
        # K / α_p / α_c rescale with n inside SnowmanNode (snowman_parameters).
        return SnowmanNode(node_id=node_id, weight=1.0, endpoint=None,
                           global_seed=global_seed, n=n, slot_duration=slot,
                           beta=cfg.SNOWMAN_BETA, workload=batches)

    meta = _meta("snowman", f"snowman-n{n}", n, seed, slot, None)
    handle = build_run(_config(n, timeline), seed, make)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# Dispatch table: protocol_id -> run builder.
RUNNERS = {
    "pbft":       run_pbft,
    "casper-ffg": run_ffg,
    "snowman":    run_snowman,
}
