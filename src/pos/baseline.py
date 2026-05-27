"""T35 — sample CSV writer for the simplified Casper FFG honest baseline.

Runs the four T35 scenarios (n=4/7/10 uniform stake + n=4 non-uniform
stake) end-to-end and writes one row per scenario to
`results/pos/baseline.csv`. The schema is a T35-local stand-in for the
unified cross-protocol CSV T40 will define against
`wiki/concepts/output-format.md`; until then a sample CSV is the
artifact T35's "same CSV format as PBFT" verify clause produces.

Re-run from the repo root:

    PYTHONPATH=src python3 -m pos.baseline

Outputs:
    results/pos/baseline.csv

This module is independent of `tests/integration/test_pos_baseline.py`;
the test asserts correctness, this module reports it. Both follow the
same config (slot_duration=1.0, slots_per_epoch=2, t_max=20.0,
global_seed=42) so the numbers line up.
"""
from __future__ import annotations

import csv
import math
import statistics
from pathlib import Path
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from common import run_to_completion
from network import DelayDist, Phase

from .node import CasperNode


_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)
_T_MAX = 20.0
_SLOT_DURATION = 1.0
_SLOTS_PER_EPOCH = 2
_GLOBAL_SEED = 42


def _uniform(n: int) -> dict[int, float]:
    return {i: 3.0 for i in range(n)}


SCENARIOS: tuple[tuple[str, int, dict[int, float]], ...] = (
    ("pos-n4-uniform", 4, _uniform(4)),
    ("pos-n7-uniform", 7, _uniform(7)),
    ("pos-n10-uniform", 10, _uniform(10)),
    ("pos-n4-nonuniform", 4, {0: 5.0, 1: 4.0, 2: 2.0, 3: 1.0}),
)


def _run_scenario(n: int, stake_table: dict[int, float]):
    config = Config(
        n=n,
        t_max=_T_MAX,
        seeds=SeedsConfig(n_runs=1),
        network=_MINIMAL_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )

    def factory(node_id: int, global_seed: int) -> CasperNode:
        return CasperNode(
            node_id=node_id, weight=stake_table[node_id], endpoint=None,
            global_seed=global_seed, n=n, stake_table=stake_table,
            slot_duration=_SLOT_DURATION, slots_per_epoch=_SLOTS_PER_EPOCH,
        )

    handle = build_run(config, _GLOBAL_SEED, factory)
    _, logger = run_to_completion(handle, t_max=_T_MAX)
    return logger


def _summarise(run_id: str, n: int, logger: EventLogger) -> dict[str, object]:
    records = list(logger.records)
    decided = [r for r in records if r.event_type == "decided"]
    deliveries = [r for r in records if r.event_type == "delivery"]
    # Per-node finalisation time of epoch 1 — the first finalised epoch
    # in every scenario; median across nodes is the headline latency the
    # T40 schema will eventually carry.
    epoch1 = [r.t for r in decided if r.fields["instance_id"] == 1]
    latency_ms = (statistics.median(epoch1) * 1000.0) if epoch1 else float("nan")
    # Throughput: decided events per simulated second over the run window.
    throughput = len(decided) / _T_MAX
    return {
        "run_id": run_id,
        "algorithm": "casper-ffg",
        "n_validators": n,
        "latency_ms": f"{latency_ms:.9f}",
        "throughput": f"{throughput:.6f}",
        "msg_count": len(deliveries),
        "success": bool(decided),
    }


_COLUMNS = ("run_id", "algorithm", "n_validators",
            "latency_ms", "throughput", "msg_count", "success")


def write_baseline_csv(path: Path) -> None:
    rows = [_summarise(run_id, n, _run_scenario(n, stake))
            for run_id, n, stake in SCENARIOS]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    # Anchor the output path relative to the repo root, two levels up
    # from this file: src/pos/baseline.py -> repo root.
    repo_root = Path(__file__).resolve().parents[2]
    write_baseline_csv(repo_root / "results" / "pos" / "baseline.csv")


if __name__ == "__main__":
    main()
