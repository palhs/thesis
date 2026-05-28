"""T40 — Unified CSV writer.

Composes generic per-row columns with per-protocol reducer output and
writes the result to a CSV file in COLUMN_ORDER. The writer is a pure
projection over (records, result, meta) triples; no I/O beyond the final
file write; no clock reads; no RNG draws.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path
from typing import Iterable

from event_log import EventRecord
from scheduler import RunResult

from pbft.summarise    import summarise as _pbft_summarise
from pos.summarise     import summarise as _pos_summarise
from snowman.summarise import summarise as _snowman_summarise

from .schema import COLUMN_ORDER, ScenarioMeta

_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}

# Columns produced by _generic_cols. Used by the collision guard to
# detect reducer drift at row-build time.
_GENERIC_COLUMNS = frozenset({
    "run_id", "protocol", "n", "seed",
    "commit_hash", "t_max",
    "total_msgs_per_acu",
})


def _resolve_commit_hash() -> str:
    """Return the short commit hash, '<hash>-dirty' on a dirty tree, or
    'WORKING_TREE' if git is unavailable or cwd is not a repo.

    Reproducibility contract — T27 + T66. The marker is surfaced rather
    than crashed-on so the writer stays runnable in CI sandboxes and
    pre-commit hooks where HEAD may not exist.
    """
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True, text=True, check=True, timeout=2.0,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True, timeout=2.0,
        ).stdout.strip()
        return f"{rev}-dirty" if status else rev
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "WORKING_TREE"


def _total_msgs_per_acu(records: list[EventRecord],
                        result: RunResult) -> float:
    """Generic: total delivery events per decided event. NaN if no
    decided events fired (the denominator is undefined)."""
    deliveries = sum(1 for r in records if r.event_type == "delivery")
    decided    = sum(1 for r in records if r.event_type == "decided")
    if decided == 0:
        return float("nan")
    return deliveries / decided


def _generic_cols(records: list[EventRecord],
                  result: RunResult,
                  meta: ScenarioMeta) -> dict[str, object]:
    return {
        "run_id":             meta.run_id,
        "protocol":           meta.protocol,
        "n":                  meta.n,
        "seed":               meta.seed,
        "commit_hash":        _resolve_commit_hash(),
        "t_max":              meta.t_max,
        "total_msgs_per_acu": _total_msgs_per_acu(records, result),
    }


def _format_row(row: dict[str, object]) -> dict[str, str]:
    """Apply column-specific float formatting; integers and strings
    pass through; floats become repr-stable strings."""
    out: dict[str, str] = {}
    for col in COLUMN_ORDER:
        v = row[col]
        if col.endswith("_ms"):
            out[col] = f"{v:.9f}" if isinstance(v, float) else str(v)
        elif col in {"tps", "consensus_msgs_per_acu",
                     "total_msgs_per_acu", "success_rate", "fork_rate",
                     "alpha_c_over_K"}:
            out[col] = f"{v:.6f}" if isinstance(v, float) else str(v)
        else:
            out[col] = str(v)
    return out


def write_unified_csv(
    path: Path,
    runs: Iterable[tuple[list[EventRecord], RunResult, ScenarioMeta]],
) -> None:
    """Project each run to one CSV row in COLUMN_ORDER. Snowman n=4
    rows are skipped (output-format.md §7). Raises:

      KeyError   — meta.protocol has no entry in _REDUCERS.
      ValueError — a reducer returned a key in _GENERIC_COLUMNS or a
                   key not in COLUMN_ORDER (reducer-vs-generic clash or
                   schema drift).
    """
    rows: list[dict[str, object]] = []
    for records, result, meta in runs:
        if meta.protocol == "snowman" and meta.n == 4:
            continue
        if meta.protocol not in _REDUCERS:
            raise KeyError(f"no reducer for protocol={meta.protocol!r}")
        row = _generic_cols(records, result, meta)
        protocol_cols = _REDUCERS[meta.protocol](records, result, meta)
        collisions = _GENERIC_COLUMNS & protocol_cols.keys()
        if collisions:
            raise ValueError(
                f"reducer for {meta.protocol!r} returned generic columns: "
                f"{sorted(collisions)!r}"
            )
        unknown = protocol_cols.keys() - set(COLUMN_ORDER)
        if unknown:
            raise ValueError(
                f"reducer for {meta.protocol!r} returned unknown columns: "
                f"{sorted(unknown)!r}"
            )
        row.update(protocol_cols)
        rows.append(row)

    rows.sort(key=lambda r: (r["protocol"], r["n"], r["run_id"], r["seed"]))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMN_ORDER,
                                extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(_format_row(row))
