"""T40 — Snowman reducer + sanity-row writer.

Per-block probabilistic finality: counter-β is finality
(commit_latency = finality_latency in the implemented honest baseline).

Snowman parameter columns populated per metric-reconciliation.md
§Snowman parameter rescaling — rescaling rule reproduced here as the
canonical Python source.

sanity_row / sanity_rows write the n=4 degenerate-boundary rows to a
sibling CSV.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import csv as _csv
import math
import statistics
from pathlib import Path
from typing import Any

from event_log import EventRecord
from output.metrics import bytes_per_acu, goodput
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult


def _rescale(n: int) -> dict[str, Any]:
    """Snowman (K, α_p, α_c, β, α_c/K) rescaling per metric-
    reconciliation.md §Snowman parameter rescaling."""
    K = min(20, n - 1)
    alpha_p = K // 2 + 1
    alpha_c = math.ceil(0.8 * K)
    beta = 15
    return {
        "K":              K,
        "alpha_p":        alpha_p,
        "alpha_c":        alpha_c,
        "beta":           beta,
        "alpha_c_over_K": alpha_c / K if K else float("nan"),
    }


def summarise(records: list[EventRecord],
              result: RunResult,
              meta: ScenarioMeta) -> dict[str, Any]:
    decided = [r for r in records if r.event_type == "decided"]
    deliveries = [r for r in records if r.event_type == "delivery"]

    if decided:
        # Median per-node decision time for the first block accepted.
        # Snowman emits `instance_id` as block identity (see
        # tests/integration/test_snowman_baseline.py lines 81-83).
        first_block = decided[0].fields.get("instance_id")
        first_block_ts = [r.t for r in decided
                          if r.fields.get("instance_id") == first_block]
        latency_ms = statistics.median(first_block_ts) * 1000.0
        success_rate = 1.0
    else:
        latency_ms = float("nan")
        success_rate = 0.0

    if not math.isnan(meta.t_max):
        tps = len(decided) / meta.t_max
    else:
        tps = float("nan")

    if decided:
        consensus_msgs_per_acu = len(deliveries) / len(decided)
    else:
        consensus_msgs_per_acu = float("nan")

    # Workload axis (T41). Snowman: each decided block = one slot's batch,
    # so n_opportunities is the distinct decided instance (block) count;
    # the throughput denominator matches `tps` (meta.t_max).
    n_opportunities = len({r.fields.get("instance_id") for r in decided})
    time_denom = float("nan") if math.isnan(meta.t_max) else meta.t_max
    gp = goodput(meta, n_opportunities, time_denom)
    bpa = bytes_per_acu(records, meta)

    row: dict[str, Any] = {
        "commit_latency_ms":      latency_ms,
        "finality_latency_ms":    latency_ms,
        "tps":                    tps,
        "goodput":                gp,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "bytes_per_acu":          bpa,
        "success_rate":           success_rate,
        "fork_rate":              0.0,   # honest baseline; pre-β flips
                                         # would land here at T54+.
    }
    row.update(_rescale(meta.n))
    return row


def _sanity_record(records: list[EventRecord],
                   result: RunResult,
                   meta: ScenarioMeta,
                   commit_hash: str | None = None) -> dict[str, Any]:
    """Build one Snowman n=4 sanity row (un-formatted). Same 18-column
    schema as the main CSV plus a `snowman_degenerate_n4` boolean flag."""
    from output.csv import _generic_cols   # local import to avoid cycle

    if meta.protocol != "snowman" or meta.n != 4:
        raise ValueError(
            f"sanity_row only valid for Snowman n=4, got "
            f"{meta.protocol!r} n={meta.n}"
        )
    generic = _generic_cols(records, result, meta, commit_hash=commit_hash)
    protocol = summarise(records, result, meta)
    return {**generic, **protocol, "snowman_degenerate_n4": True}


def _write_sanity(rows: list[dict[str, Any]], path: Path) -> None:
    """Write pre-built sanity rows to `path`, sorted deterministically by
    (protocol, n, run_id, seed) to match the main writer, header + one
    data row per run."""
    from output.csv import _format_row   # local import to avoid cycle

    rows = sorted(
        rows,
        key=lambda r: (r["protocol"], r["n"], r["run_id"], r["seed"]),
    )
    fieldnames = list(COLUMN_ORDER) + ["snowman_degenerate_n4"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = _csv.DictWriter(fh, fieldnames=fieldnames,
                                 extrasaction="raise")
        writer.writeheader()
        for row in rows:
            formatted = _format_row({k: row[k] for k in COLUMN_ORDER})
            formatted["snowman_degenerate_n4"] = str(
                row["snowman_degenerate_n4"]
            )
            writer.writerow(formatted)


def sanity_rows(runs, path: Path, commit_hash: str | None = None) -> None:
    """Write all Snowman n=4 rescaling-boundary rows to a sibling CSV.

    `runs` is an iterable of (records, result, meta) triples — typically
    every n=4 run from the orchestrator's sweep (20 seeds). Each triple
    is projected to one row; the header is written once, rows are sorted
    by (protocol, n, run_id, seed) for determinism (matching
    write_unified_csv). Same 18-column schema as the main CSV plus a
    `snowman_degenerate_n4` boolean flag column.

    `commit_hash`: if None, resolved internally per row. Pass through
    when pairing with `write_unified_csv` from one orchestrator pass so
    both files share the same pre-write hash (output-format.md §10).
    """
    rows = [_sanity_record(records, result, meta, commit_hash=commit_hash)
            for records, result, meta in runs]
    _write_sanity(rows, path)


def sanity_row(records: list[EventRecord],
               result: RunResult,
               meta: ScenarioMeta,
               path: Path,
               commit_hash: str | None = None) -> None:
    """Write a single Snowman n=4 rescaling-boundary row to a sibling CSV.

    Single-run convenience wrapper over `sanity_rows`. Same 18-column
    schema plus a `snowman_degenerate_n4` flag; header-row + one data row.

    `commit_hash`: if None, resolved internally. Pass through when
    pairing with `write_unified_csv` from one orchestrator pass so both
    files share the same pre-write hash.
    """
    sanity_rows([(records, result, meta)], path, commit_hash=commit_hash)
