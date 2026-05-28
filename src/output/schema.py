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
    """Identifies one (protocol, scenario, seed) row of the unified CSV."""
    run_id: str
    protocol: str
    n: int
    variant: str | None
    seed: int
    t_max: float


COLUMN_ORDER: tuple[str, ...] = (
    # Identity (generic — 4 cols).
    "run_id", "protocol", "n", "seed",
    # Reproducibility (generic — 2 cols).
    "commit_hash", "t_max",
    # Latency (per-protocol — 2 cols).
    "commit_latency_ms", "finality_latency_ms",
    # Throughput (per-protocol — 1 col).
    "tps",
    # Overhead (generic + per-protocol — 2 cols).
    "consensus_msgs_per_acu", "total_msgs_per_acu",
    # Reliability (per-protocol — 2 cols).
    "success_rate", "fork_rate",
    # Snowman parameters (Snowman-only; NaN elsewhere — 5 cols).
    "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
)
