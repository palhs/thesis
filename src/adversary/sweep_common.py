"""Shared, strategy-agnostic helpers for the Family C adversary sweeps (T52+).

Holds only the arity-independent pieces reused across withhold (T52) and
equivocate (T53): the generic annotation column names, the strategy label, the
common-column CSV formatter, and the Snowman memory-heavy predicate. Cell shape,
the headline column, build_cells, and the post-pass stay strategy-specific (the
offline cell is a 4-tuple, delay's is a 5-tuple). T51's sweep.py is intentionally
not migrated here (frozen dataset). Design: docs/plans/2026-06-17-t52-offline-validators-design.md §3.2
"""
from __future__ import annotations

# Generic adversary annotation block (neutral names; no delay_mult).
ADV_COMMON_COLUMNS: tuple[str, ...] = (
    "adversary_strategy",     # "none" for f=0, else the capability tag
    "adversary_node_count",   # realized ⌊f·n⌋ adversarial nodes
    "byzantine_fraction",     # nominal f
    "view_change_count",      # PBFT view-changes in [0, W] (0 for FFG/Snowman)
    "clipped_fraction",       # tail past W / in-scope (reported, not guarded)
    "run_horizon_s",          # W + buffer
)

_CONTROL_F = 0.0


def strategy_label(f: float, kind: str) -> str:
    return "none" if f == _CONTROL_F else kind


def is_heavy_snowman(proto: str, n: int) -> bool:
    """Memory-heavy class: Snowman n>=25 (mirror sweep._is_heavy_cell)."""
    return proto == "snowman" and int(n) >= 25


def format_common_adv_cols(row: dict) -> dict:
    """Format the six ADV_COMMON_COLUMNS to strings (matches sweep.write_csv)."""
    return {
        "adversary_strategy":   str(row["adversary_strategy"]),
        "adversary_node_count": str(row["adversary_node_count"]),
        "byzantine_fraction":   f"{row['byzantine_fraction']:.6f}",
        "view_change_count":    str(row["view_change_count"]),
        "clipped_fraction":     f"{row['clipped_fraction']:.6f}",
        "run_horizon_s":        f"{row['run_horizon_s']:.3f}",
    }
