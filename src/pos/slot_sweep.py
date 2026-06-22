"""Casper FFG slot-duration sensitivity sweep (L-W10 finding H2, part b).

The as-run FFG calibration is `slots_per_epoch = 2`, `slot_duration = 1 s`,
giving per-epoch finality `(2·slots_per_epoch + attest_offset)·slot_duration
= (2·2 + 1)·1 = 5 s` (`attest_offset = slots_per_epoch // 2 = 1`). The
per-block protocols (PBFT, Snowman) commit at ≈1 s, so at the as-run point
FFG looks ~5× slower. This module produces the evidence that the comparative
finding is ROBUST to the slot choice: it sweeps the slot over the committed
sensitivity range `{0.5, 1.0, 2.0} s`
(wiki/concepts/metric-reconciliation.md §Calibration) at `slots_per_epoch =
2`, `n = 10`, and confirms that measured `commit_latency_ms` is exactly
`5 · slot_duration · 1000` ms — linear in the slot, hence calibration-set
not protocol-intrinsic, yet always ABOVE the ≈1 s per-block commit across the
whole realistic range.

FFG finality here is structurally deterministic: it depends only on the slot
timer cadence and the (round-robin / stake-weighted) attestation schedule,
not on `n` beyond reaching the 2/3-stake quorum and not on the workload RNG
seed. The sweep keeps a small seed set (`{0, 1, 2}`) only to CONFIRM that
seed-invariance empirically; the headline latency is identical across seeds.

Single process, sequential — no multiprocessing (parallel pools deadlock in
the sandbox; see project memory). The sweep is tiny (3 slots × 3 seeds = 9
runs).

Re-run:
  PYTHONPATH=src python3 -m pos.slot_sweep
  # writes results/sensitivity/ffg_slot_sweep.csv (deterministic, byte-stable)

Design contract: wiki/concepts/metric-reconciliation.md §Calibration defaults
Companion experiment page: wiki/experiments/2026-06-22_ffg-slot-sensitivity.md
"""
from __future__ import annotations

import csv
import math
import os
import subprocess
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from network import DelayDist, Phase
from output.schema import ScenarioMeta
from workload import WorkloadConfig, generate_batches

from .node import CasperNode
from .summarise import summarise
from common import run_to_completion

# --- Sweep grid -----------------------------------------------------------
# Slot durations: the committed FFG sensitivity range
# (metric-reconciliation §Calibration). slots_per_epoch held at the as-run
# default 2.
SLOT_DURATIONS: tuple[float, ...] = (0.5, 1.0, 2.0)
SLOTS_PER_EPOCH: int = 2
N: int = 10
SEEDS: tuple[int, ...] = (0, 1, 2)

# Per-epoch finality = (2·spe + attest_offset)·slot, attest_offset = spe//2.
# At spe=2 that is (4 + 1)·slot = 5·slot seconds. t_max must comfortably
# clear epoch-1 finality at the LARGEST slot (5·2.0 = 10 s); 30 s leaves
# ample headroom and lets several epochs finalise at every slot.
T_MAX: float = 30.0

# Minimal near-instant network so attestations arrive within-slot (the
# §Coherence constraint: E[delay] ≪ slot_duration). Mirrors the baseline.
_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)

# Workload axis — identical to the FFG baseline (src/pos/baseline.py) so the
# stack and the reducer agree; block content does not affect FFG finality
# timing, this is only here to keep the goodput/bytes columns populated.
_ARRIVAL_PROCESS = "poisson"
_OFFERED_RATE = 100.0
_TX_BYTES = 512
_CONFLICT_RATE = 0.0

# Expected linear law: commit_latency_ms = 5 · slot_duration · 1000.
_FINALITY_SLOTS_FACTOR = 2 * SLOTS_PER_EPOCH + (SLOTS_PER_EPOCH // 2)  # = 5

_RESULT_DIR = os.path.join("results", "sensitivity")
_RESULT_CSV = os.path.join(_RESULT_DIR, "ffg_slot_sweep.csv")

# CSV columns. expected_commit_latency_ms and ratio make the linear-law
# check self-documenting in the artifact itself.
_COLUMNS: tuple[str, ...] = (
    "protocol", "n", "slots_per_epoch", "slot_duration_s", "seed",
    "commit_hash", "t_max_s",
    "commit_latency_ms", "expected_commit_latency_ms",
    "finality_factor", "ratio_measured_over_5slot",
)


def expected_commit_latency_ms(slot_duration: float) -> float:
    """The 5·slot finality law at slots_per_epoch=2, in milliseconds."""
    return _FINALITY_SLOTS_FACTOR * slot_duration * 1000.0


def _commit_hash() -> str:
    """Short git hash for provenance; 'unknown' if not in a git tree."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _stake_table(n: int) -> dict[int, float]:
    return {i: 3.0 for i in range(n)}


def _config(n: int) -> Config:
    return Config(
        n=n,
        t_max=T_MAX,
        seeds=SeedsConfig(n_runs=1),
        network=_MINIMAL_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _factory(n: int, slot_duration: float):
    stake_table = _stake_table(n)
    # One batch per slot opportunity over the window, +2 headroom for the
    # genesis slot 0 and any boundary slot the timer arms.
    n_opportunities = math.ceil(T_MAX / slot_duration) + 2

    def make(node_id: int, global_seed: int) -> CasperNode:
        batches = generate_batches(
            WorkloadConfig(_ARRIVAL_PROCESS, _OFFERED_RATE,
                           _TX_BYTES, _CONFLICT_RATE),
            global_seed,
            n_opportunities=n_opportunities,
            interval=slot_duration,
        )
        return CasperNode(
            node_id=node_id, weight=stake_table[node_id], endpoint=None,
            global_seed=global_seed, n=n, stake_table=stake_table,
            slot_duration=slot_duration, slots_per_epoch=SLOTS_PER_EPOCH,
            workload=[b for b in batches],
        )
    return make


def _meta(slot_duration: float, seed: int) -> ScenarioMeta:
    return ScenarioMeta(
        run_id=f"ffg-slot{slot_duration}-n{N}", protocol="casper-ffg",
        n=N, variant="uniform", seed=seed, t_max=T_MAX,
        arrival_process=_ARRIVAL_PROCESS, tx_bytes=_TX_BYTES,
        conflict_rate=_CONFLICT_RATE, offered_rate=_OFFERED_RATE,
        interval=slot_duration, slots_per_epoch=SLOTS_PER_EPOCH,
    )


def measure(slot_duration: float, seed: int) -> float:
    """Run one FFG cell and return measured epoch-1 commit_latency_ms."""
    meta = _meta(slot_duration, seed)
    config = _config(N)
    handle = build_run(config, seed, _factory(N, slot_duration))
    result, logger = run_to_completion(handle, t_max=T_MAX)
    row = summarise(logger.records, result, meta)
    return row["commit_latency_ms"]


def run_sweep() -> list[dict[str, object]]:
    """Run the full 3-slot × 3-seed grid sequentially; return CSV rows."""
    commit_hash = _commit_hash()
    rows: list[dict[str, object]] = []
    for slot_duration in SLOT_DURATIONS:
        expected = expected_commit_latency_ms(slot_duration)
        for seed in SEEDS:
            measured = measure(slot_duration, seed)
            rows.append({
                "protocol": "casper-ffg",
                "n": N,
                "slots_per_epoch": SLOTS_PER_EPOCH,
                "slot_duration_s": slot_duration,
                "seed": seed,
                "commit_hash": commit_hash,
                "t_max_s": T_MAX,
                "commit_latency_ms": measured,
                "expected_commit_latency_ms": expected,
                "finality_factor": _FINALITY_SLOTS_FACTOR,
                "ratio_measured_over_5slot": measured / expected,
            })
    return rows


def write_csv(rows: list[dict[str, object]], path: str = _RESULT_CSV) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    rows = run_sweep()
    write_csv(rows)
    # Console summary: one line per slot (seeds are invariant — print seed 0).
    print(f"FFG slot-duration sweep -> {_RESULT_CSV}")
    print(f"  slots_per_epoch={SLOTS_PER_EPOCH}  n={N}  "
          f"t_max={T_MAX}s  seeds={SEEDS}")
    print("  slot_s  measured_ms   expected(5·slot·1000)  ratio")
    for slot_duration in SLOT_DURATIONS:
        seed0 = next(r for r in rows
                     if r["slot_duration_s"] == slot_duration
                     and r["seed"] == 0)
        print(f"  {slot_duration:>5}  {seed0['commit_latency_ms']:>11.4f}"
              f"  {seed0['expected_commit_latency_ms']:>20.1f}"
              f"   {seed0['ratio_measured_over_5slot']:.9f}")


if __name__ == "__main__":
    main()
