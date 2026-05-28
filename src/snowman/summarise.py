"""T40 — Snowman reducer + sanity-row writer.

Per-block probabilistic finality: counter-β is finality
(commit_latency = finality_latency in the implemented honest baseline).

Snowman parameter columns populated per metric-reconciliation.md
§Snowman parameter rescaling — rescaling rule reproduced here as the
canonical Python source.

sanity_row writes the n=4 degenerate-boundary row to a sibling CSV.

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

    row: dict[str, Any] = {
        "commit_latency_ms":      latency_ms,
        "finality_latency_ms":    latency_ms,
        "tps":                    tps,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "success_rate":           success_rate,
        "fork_rate":              0.0,   # honest baseline; pre-β flips
                                         # would land here at T54+.
    }
    row.update(_rescale(meta.n))
    return row


def sanity_row(records: list[EventRecord],
               result: RunResult,
               meta: ScenarioMeta,
               path: Path,
               commit_hash: str | None = None) -> None:
    """Write the Snowman n=4 rescaling-boundary row to a sibling CSV.

    Same 18-column schema as the main CSV plus a `snowman_degenerate_n4`
    boolean flag column. Header-row + one data row.

    `commit_hash`: if None, resolved internally. Pass through when
    pairing with `write_unified_csv` from one orchestrator pass so both
    files share the same pre-write hash.
    """
    from output.csv import _format_row, _generic_cols   # local import to
                                                         # avoid cycle

    if meta.protocol != "snowman" or meta.n != 4:
        raise ValueError(
            f"sanity_row only valid for Snowman n=4, got "
            f"{meta.protocol!r} n={meta.n}"
        )
    generic = _generic_cols(records, result, meta, commit_hash=commit_hash)
    protocol = summarise(records, result, meta)
    row = {**generic, **protocol, "snowman_degenerate_n4": True}

    fieldnames = list(COLUMN_ORDER) + ["snowman_degenerate_n4"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = _csv.DictWriter(fh, fieldnames=fieldnames,
                                 extrasaction="raise")
        writer.writeheader()
        formatted = _format_row({k: row[k] for k in COLUMN_ORDER})
        formatted["snowman_degenerate_n4"] = str(row["snowman_degenerate_n4"])
        writer.writerow(formatted)
