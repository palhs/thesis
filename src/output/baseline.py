"""T40 — Unified CSV orchestrator.

Imports each protocol's SCENARIOS + run_scenario, runs every scenario,
writes one results/baseline/baseline.csv. Snowman n=4 produces an
additional results/baseline/snowman_n4_sanity.csv (one row per seed) via
snowman.summarise.sanity_rows.

Run from repo root:
    PYTHONPATH=src python3 -m output.baseline

Design spec: docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

from pathlib import Path

import pbft.baseline as pbft_baseline
import pos.baseline as pos_baseline
import snowman.baseline as snowman_baseline
from snowman.summarise import sanity_rows

from .csv import _resolve_commit_hash, write_unified_csv


_OUT  = Path("results/baseline/baseline.csv")
_SANE = Path("results/baseline/snowman_n4_sanity.csv")


def _collect_runs():
    runs = []
    for meta in pbft_baseline.SCENARIOS:
        runs.append(pbft_baseline.run_scenario(meta))
    for meta in pos_baseline.SCENARIOS:
        runs.append(pos_baseline.run_scenario(meta))
    for meta in snowman_baseline.SCENARIOS:
        runs.append(snowman_baseline.run_scenario(meta))
    return runs


def main() -> None:
    # Snapshot the commit hash once before any writes so both output
    # files share the same value (the main-file write would otherwise
    # dirty the tree and shift the sanity hash mid-run; consecutive
    # runs from any tree state would also drift). output-format.md §10.
    commit_hash = _resolve_commit_hash()
    runs = _collect_runs()
    write_unified_csv(_OUT, runs, commit_hash=commit_hash)
    # All Snowman n=4 runs (every seed) are routed out of the main file
    # (write_unified_csv skips them, output-format.md §7) into the sanity
    # sibling — one row per seed.
    n4_runs = [(records, result, meta) for records, result, meta in runs
               if meta.protocol == "snowman" and meta.n == 4]
    sanity_rows(n4_runs, _SANE, commit_hash=commit_hash)


if __name__ == "__main__":
    main()
