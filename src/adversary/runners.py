"""Per-protocol run builders for the Family C delay-emission sweep (T51).

Each ``run_<proto>(n, f, m, seed)`` mirrors the honest baseline factory
(src/{pbft,pos,snowman}/baseline.py) on the Family C static-baseline timeline,
then applies the delay-emission adversary: the highest-id ⌊f·n⌋ nodes hold every
outbound emission by ``m·ref`` seconds (``adversary.inject.inject_delay``). The
f=0 control applies no wrap (byte-identical to honest static-baseline).

Same ``RunTriple`` shape and ``meta`` discipline as src/delay/runners.py:
``meta.t_max`` is the measurement WINDOW (the reducers' throughput denominator),
while the scheduler runs to the full ``T_MAX = WINDOW_S + BUFFER_S`` horizon.

No shared infrastructure is modified -- the adversary attaches entirely at the
Node outbound API, post-build (spec §3.2).

Design contract: wiki/experiments/2026-06-14_delayed-voters.md
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
from . import offline_config as ocfg
from .inject import inject_delay, inject_offline
from .select import slow_node_ids

RunTriple = tuple[list[EventRecord], RunResult, ScenarioMeta]


def _config(n: int, src=cfg) -> Config:
    """One Config point on the static-baseline timeline, horizon T_MAX.

    ``src`` is the calibration module supplying the scheduler horizon and the
    timeline (defaults to T51 ``cfg`` for the delay runners; the offline runners
    pass ``ocfg`` so the run horizon tracks offline_config). ``src`` must expose
    ``T_MAX`` and ``STATIC_BASELINE``."""
    return Config(
        n=n,
        t_max=src.T_MAX,
        seeds=SeedsConfig(n_runs=1),
        network=src.STATIC_BASELINE.phases(),
        adversary={},
        protocol_knobs={},
        workload={},
    )


def _batches(seed: int, interval: float, src=cfg):
    """Deterministic batch stream covering the full horizon plus margin.

    ``src.T_MAX`` sets how far the batch stream must reach: the offline runners
    pass ``ocfg`` so the workload covers the (possibly longer) offline horizon
    rather than the T51 one. Workload-shape knobs (arrival process, offered
    rate, tx bytes, conflict rate) are shared between calibrations and read from
    ``src`` (identical in both today)."""
    n_opportunities = math.ceil(src.T_MAX / interval) + 2
    return generate_batches(
        WorkloadConfig(src.ARRIVAL_PROCESS, src.OFFERED_RATE,
                       src.TX_BYTES, src.CONFLICT_RATE),
        seed, n_opportunities=n_opportunities, interval=interval,
    )


def _meta(protocol: str, run_id: str, n: int, seed: int,
          interval: float, slots_per_epoch: int | None, src=cfg) -> ScenarioMeta:
    """ScenarioMeta with t_max = WINDOW_S (the measurement window).

    ``t_max`` is the throughput denominator; it must match the clip window used
    downstream. The offline runners pass ``ocfg`` so ``meta.t_max`` equals
    ``ocfg.WINDOW_S`` (the same window ``offline_sweep._run_cell`` clips to),
    keeping the throughput numerator and denominator on the same window."""
    return ScenarioMeta(
        run_id=run_id, protocol=protocol, n=n, variant=None, seed=seed,
        t_max=src.WINDOW_S,
        arrival_process=src.ARRIVAL_PROCESS, tx_bytes=src.TX_BYTES,
        conflict_rate=src.CONFLICT_RATE, offered_rate=src.OFFERED_RATE,
        interval=interval, slots_per_epoch=slots_per_epoch,
    )


# --- PBFT ---------------------------------------------------------------

def run_pbft(n: int, f: float, m: float, seed: int) -> RunTriple:
    propose = cfg.PBFT_PROPOSE_DELAY_S
    batches = [b"".join(b) for b in _batches(seed, propose)]

    def make(node_id: int, global_seed: int) -> PBFTNode:
        workload = batches if node_id == 0 else None
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n, workload=workload,
                        propose_delay=propose, initial_view=0,
                        vc_delay=cfg.PBFT_VC_DELAY_S)

    meta = _meta("pbft", f"pbft-n{n}", n, seed, propose, None)
    handle = build_run(_config(n), seed, make)
    inject_delay(handle, slow_node_ids(n, f), m, cfg.REF_S["pbft"], f)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# --- Casper FFG ---------------------------------------------------------

def run_ffg(n: int, f: float, m: float, seed: int) -> RunTriple:
    slot = cfg.FFG_SLOT_DURATION_S
    spe = cfg.FFG_SLOTS_PER_EPOCH
    stake = {i: 3.0 for i in range(n)}
    batches = [b for b in _batches(seed, slot)]

    def make(node_id: int, global_seed: int) -> CasperNode:
        return CasperNode(node_id=node_id, weight=stake[node_id],
                          endpoint=None, global_seed=global_seed, n=n,
                          stake_table=stake, slot_duration=slot,
                          slots_per_epoch=spe, workload=batches)

    meta = _meta("casper-ffg", f"casper-ffg-n{n}", n, seed, slot, spe)
    handle = build_run(_config(n), seed, make)
    inject_delay(handle, slow_node_ids(n, f), m, cfg.REF_S["casper-ffg"], f)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# --- Snowman ------------------------------------------------------------

def run_snowman(n: int, f: float, m: float, seed: int) -> RunTriple:
    slot = cfg.SNOWMAN_SLOT_DURATION_S
    batches = [b for b in _batches(seed, slot)]

    def make(node_id: int, global_seed: int) -> SnowmanNode:
        return SnowmanNode(node_id=node_id, weight=1.0, endpoint=None,
                           global_seed=global_seed, n=n, slot_duration=slot,
                           beta=cfg.SNOWMAN_BETA, workload=batches)

    meta = _meta("snowman", f"snowman-n{n}", n, seed, slot, None)
    handle = build_run(_config(n), seed, make)
    inject_delay(handle, slow_node_ids(n, f), m, cfg.REF_S["snowman"], f)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta


# Dispatch table: protocol_id -> run builder.
RUNNERS = {
    "pbft":       run_pbft,
    "casper-ffg": run_ffg,
    "snowman":    run_snowman,
}


# --- Offline runners (T52) ----------------------------------------------
# Each mirrors its delay sibling exactly, EXCEPT: the signature drops the
# magnitude axis m (offline has no magnitude), and the inject line drops
# every emission from the highest-id ⌊f·n⌋ nodes (inject_offline) instead of
# shifting it (inject_delay). f=0 is a strict no-op == honest static-baseline.

def run_pbft_offline(n: int, f: float, seed: int) -> RunTriple:
    propose = ocfg.PBFT_PROPOSE_DELAY_S
    batches = [b"".join(b) for b in _batches(seed, propose, ocfg)]

    def make(node_id: int, global_seed: int) -> PBFTNode:
        workload = batches if node_id == 0 else None
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n, workload=workload,
                        propose_delay=propose, initial_view=0,
                        vc_delay=ocfg.PBFT_VC_DELAY_S)

    meta = _meta("pbft", f"pbft-n{n}", n, seed, propose, None, ocfg)
    handle = build_run(_config(n, ocfg), seed, make)
    inject_offline(handle, slow_node_ids(n, f), f)
    result, logger = run_to_completion(handle, t_max=ocfg.T_MAX)
    return logger.records, result, meta


def run_ffg_offline(n: int, f: float, seed: int) -> RunTriple:
    slot = ocfg.FFG_SLOT_DURATION_S
    spe = ocfg.FFG_SLOTS_PER_EPOCH
    stake = {i: 3.0 for i in range(n)}
    batches = [b for b in _batches(seed, slot, ocfg)]

    def make(node_id: int, global_seed: int) -> CasperNode:
        return CasperNode(node_id=node_id, weight=stake[node_id],
                          endpoint=None, global_seed=global_seed, n=n,
                          stake_table=stake, slot_duration=slot,
                          slots_per_epoch=spe, workload=batches)

    meta = _meta("casper-ffg", f"casper-ffg-n{n}", n, seed, slot, spe, ocfg)
    handle = build_run(_config(n, ocfg), seed, make)
    inject_offline(handle, slow_node_ids(n, f), f)
    result, logger = run_to_completion(handle, t_max=ocfg.T_MAX)
    return logger.records, result, meta


def run_snowman_offline(n: int, f: float, seed: int) -> RunTriple:
    slot = ocfg.SNOWMAN_SLOT_DURATION_S
    batches = [b for b in _batches(seed, slot, ocfg)]

    def make(node_id: int, global_seed: int) -> SnowmanNode:
        return SnowmanNode(node_id=node_id, weight=1.0, endpoint=None,
                           global_seed=global_seed, n=n, slot_duration=slot,
                           beta=ocfg.SNOWMAN_BETA, workload=batches)

    meta = _meta("snowman", f"snowman-n{n}", n, seed, slot, None, ocfg)
    handle = build_run(_config(n, ocfg), seed, make)
    inject_offline(handle, slow_node_ids(n, f), f)
    result, logger = run_to_completion(handle, t_max=ocfg.T_MAX)
    return logger.records, result, meta


# Dispatch table: protocol_id -> offline run builder.
OFFLINE_RUNNERS = {
    "pbft":       run_pbft_offline,
    "casper-ffg": run_ffg_offline,
    "snowman":    run_snowman_offline,
}
