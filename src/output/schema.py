"""T40 — Unified CSV schema bridge.

Carries scenario identity through the pipeline:
  baseline.SCENARIOS  -> run_scenario(meta)  -> (records, result, meta)
                                                            |
                                                            v
                              write_unified_csv(path, runs of these triples)

COLUMN_ORDER is the today-writer projection of the full ~30-column
schema pinned by wiki/concepts/output-format.md §Canonical schema.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioMeta:
    """Identifies one (protocol, scenario, seed) row of the unified CSV.

    The five trailing fields (T41) carry the workload axis: how
    transactions arrive (`arrival_process`), their size (`tx_bytes`),
    the fraction that conflict (`conflict_rate`), the offered submission
    rate (`offered_rate`), and the inter-arrival `interval`. All default
    to the T41 baseline so pre-T41 constructions stay valid.
    """
    run_id: str
    protocol: str
    n: int
    variant: str | None
    seed: int
    t_max: float
    arrival_process: str = "poisson"
    tx_bytes: int = 512
    conflict_rate: float = 0.0
    offered_rate: float = 100.0
    interval: float = 1.0
    # T41: slots per epoch, set by the Casper FFG baseline so the FFG
    # reducer can map finalised-epoch decided events back to per-slot
    # batch opportunities. None falls back to the FFG node default (2).
    slots_per_epoch: int | None = None


COLUMN_ORDER: tuple[str, ...] = (
    # Identity (generic — 4 cols).
    "run_id", "protocol", "n", "seed",
    # Workload axis (generic; T41 — 4 cols).
    "workload_arrival_process", "workload_tx_bytes",
    "workload_conflict_rate", "workload_offered_rate",
    # Reproducibility (generic — 2 cols).
    "commit_hash", "t_max",
    # Latency (per-protocol — 2 cols).
    "commit_latency_ms", "finality_latency_ms",
    # Throughput (per-protocol; goodput is T41 — 2 cols).
    "tps", "goodput",
    # Overhead (generic + per-protocol; bytes_per_acu is T41 — 3 cols).
    "consensus_msgs_per_acu", "total_msgs_per_acu", "bytes_per_acu",
    # Reliability (per-protocol — 2 cols).
    "success_rate", "fork_rate",
    # Snowman parameters (Snowman-only; NaN elsewhere — 5 cols).
    "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
)
