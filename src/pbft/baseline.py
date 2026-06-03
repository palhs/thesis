"""PBFT honest baseline scenarios.

SCENARIOS is the list of (n, seed) runs swept by src/output/baseline.py and
asserted by tests/integration/test_pbft_baseline.py. run_scenario(meta)
builds the PBFT stack at meta.n, runs it over a fixed `_T_MAX` window, and
returns the (records, result, meta) triple the unified CSV writer consumes.

T41 windowing. The honest path was run to quiescence with a single trivial
request (one committed instance). It now runs over a fixed `t_max` window
(`_T_MAX`) and feeds the primary a real, deterministic transaction stream
(`src/workload/generator.py`), so the primary proposes continuously across
the window and many instances commit. This makes tps / goodput /
bytes_per_acu comparable to Casper FFG and Snowman, which are also windowed.

Batch payload. Each proposal carries the transaction *batch* that the
workload generator produced for that opportunity. PBFTNode treats the
PRE-PREPARE `request_payload` as an opaque `bytes` blob and only ever
`digest()`s it; node.py is therefore left UNCHANGED. The baseline encodes
each batch (a `tuple[bytes, ...]`) canonically as `b"".join(batch)` before
handing it to the primary's workload, so the on-the-wire payload stays
`bytes` and the digest call sites in node.py keep working byte-for-byte.
The per-message wire-byte budget used by `bytes_per_acu`
(`src/output/metrics.py`) is derived from `offered_rate * interval *
tx_bytes`, not from the concatenated blob length, so the canonical join
does not perturb the overhead columns.

First-instance latency invariant. `commit_latency_ms` /
`finality_latency_ms` are defined on the FIRST decided instance
(output-format.md §5.1). Node logic and the propose cadence (PROPOSE_DELAY)
are unchanged, so the first instance's commit time is byte-identical to the
pre-T41 value; only the throughput / overhead columns re-baseline.

Design spec: docs/superpowers/specs/2026-05-30-t41-scaling-workload-design.md
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

from . import PBFTNode


_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)

# Fixed simulation window. Matches the FFG / Snowman baselines so the
# windowed throughput / overhead columns are cross-protocol comparable.
_T_MAX = 20.0

# The primary's propose timer fires every PROPOSE_DELAY; with `_T_MAX`
# window and re-arming workload (pbft/node.py:139) the primary emits a
# PRE-PREPARE per interval until the window closes. Every `decided`
# event therefore carries t > PROPOSE_DELAY.
PROPOSE_DELAY = 1.0

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


def _factory(n: int):
    """build_run wants (node_id, global_seed) -> Node. All-honest
    PBFTNodes; the primary (node 0) carries the windowed transaction
    stream, non-primaries carry no workload. vc_delay is generous so no
    honest run ever triggers a view-change."""
    def make(node_id: int, global_seed: int) -> PBFTNode:
        workload = _primary_workload(global_seed) if node_id == 0 else None
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n,
                        workload=workload,
                        propose_delay=PROPOSE_DELAY, initial_view=0,
                        vc_delay=1000.0)
    return make


def _primary_workload(global_seed: int) -> list[bytes]:
    """Build the primary's per-instance workload for one run.

    Generates the deterministic batch stream once from `global_seed`
    (same `(config, global_seed)` -> identical stream — the generator's
    byte-identical contract), one batch per proposal opportunity, and
    encodes each batch canonically as `b"".join(batch)` so the node can
    `digest()` it as opaque `bytes`. We size the stream to cover the
    window with a small margin (`ceil(_T_MAX / PROPOSE_DELAY) + 2`) so the
    primary never drains mid-window and stops proposing early.
    """
    cfg = WorkloadConfig(_ARRIVAL_PROCESS, _OFFERED_RATE,
                         _TX_BYTES, _CONFLICT_RATE)
    n_opportunities = math.ceil(_T_MAX / PROPOSE_DELAY) + 2
    batches = generate_batches(cfg, global_seed,
                               n_opportunities=n_opportunities,
                               interval=PROPOSE_DELAY)
    return [b"".join(batch) for batch in batches]


def _scenario(n: int, seed: int) -> ScenarioMeta:
    """One windowed PBFT scenario. run_id omits the seed — the `seed`
    column disambiguates rows; row identity is (protocol, n, run_id, seed)."""
    return ScenarioMeta(
        run_id=f"pbft-n{n}", protocol="pbft", n=n, variant=None,
        seed=seed, t_max=_T_MAX,
        arrival_process=_ARRIVAL_PROCESS, tx_bytes=_TX_BYTES,
        conflict_rate=_CONFLICT_RATE, offered_rate=_OFFERED_RATE,
        interval=PROPOSE_DELAY,
    )


# Scaling sweep: n in {4,7,10,16,25} x seed in range(20) = 100 scenarios.
_N_VALUES: tuple[int, ...] = (4, 7, 10, 16, 25)
_SEEDS: tuple[int, ...] = tuple(range(20))

SCENARIOS: tuple[ScenarioMeta, ...] = tuple(
    _scenario(n, seed) for n in _N_VALUES for seed in _SEEDS
)


def run_scenario(meta: ScenarioMeta
                 ) -> tuple[list[EventRecord], RunResult, ScenarioMeta]:
    config = _config(meta.n)
    handle = build_run(config, meta.seed, _factory(meta.n))
    result, logger = run_to_completion(handle, t_max=_T_MAX)
    return logger.records, result, meta
