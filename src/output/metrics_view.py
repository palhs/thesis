"""T42 — Derived metrics view over the canonical per-trial baseline CSV.

`results/baseline/metrics.csv` is a thin DERIVED projection of
`results/baseline/baseline.csv` (the canonical per-trial file written by
`src/output/csv.py`, design contract wiki/concepts/output-format.md). It
exposes the latency / throughput / communication-overhead metric families
keyed by row identity, for downstream consumers that want the metric slice
without the full ~24-column schema.

This module does NOT collect anything new and does NOT rename baseline.csv
— baseline.csv stays authoritative (output-format §2). The view is a pure
read -> project -> write:

  - Cells are copied through verbatim as STRINGS from baseline.csv. Because
    baseline.csv was already written with the output-format §9 float formats
    (*_ms at .9f; tps / *_per_acu / rates at .6f), pass-through guarantees
    the view's metric cells are byte-identical to their source and the view
    is byte-stable without re-formatting.
  - Row order is inherited from baseline.csv (already the total
    (protocol, n, run_id, seed) sort, output-format §8), so output is
    input-order-independent.
  - commit_hash is carried through from baseline.csv; the impure
    `_resolve_commit_hash` git call is NOT re-invoked (provenance is
    inherited, output-format §10).

Re-run (after the source dataset exists):
    PYTHONPATH=src python3 -m output.metrics_view
"""
from __future__ import annotations

import csv as _csv
from pathlib import Path

# Identity columns: enough to uniquely key a row and carry provenance.
IDENTITY_COLUMNS: tuple[str, ...] = (
    "run_id", "protocol", "n", "seed", "commit_hash",
)

# Metric columns — the three families T42 verifies:
#   latency:               commit_latency_ms, finality_latency_ms
#   throughput:            tps, goodput
#   communication overhead: consensus_msgs_per_acu, total_msgs_per_acu,
#                           bytes_per_acu
METRIC_COLUMNS: tuple[str, ...] = (
    "commit_latency_ms", "finality_latency_ms",
    "tps", "goodput",
    "consensus_msgs_per_acu", "total_msgs_per_acu", "bytes_per_acu",
)

VIEW_COLUMNS: tuple[str, ...] = IDENTITY_COLUMNS + METRIC_COLUMNS

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SRC = _REPO_ROOT / "results" / "baseline" / "baseline.csv"
_DEFAULT_OUT = _REPO_ROOT / "results" / "baseline" / "metrics.csv"


def build_metrics_view(
    src_csv: Path | str = _DEFAULT_SRC,
    out_csv: Path | str = _DEFAULT_OUT,
) -> Path:
    """Read `src_csv`, project to `VIEW_COLUMNS`, write `out_csv`.

    Pure read -> project -> write. Cells are copied through verbatim, so the
    view is byte-identical to its source on every projected column and the
    build is deterministic (same source -> identical bytes). Row order is
    inherited unchanged from the source. Overwrite-on-write; parent dirs are
    created.

    Returns the output path.
    """
    src_path = Path(src_csv)
    out_path = Path(out_csv)

    with src_path.open(newline="") as fh:
        reader = _csv.DictReader(fh)
        src_fields = reader.fieldnames or []
        missing = [c for c in VIEW_COLUMNS if c not in src_fields]
        if missing:
            raise ValueError(
                f"source {src_path} is missing required columns: {missing}"
            )
        rows = list(reader)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as fh:
        writer = _csv.DictWriter(
            fh, fieldnames=list(VIEW_COLUMNS), extrasaction="ignore"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row[col] for col in VIEW_COLUMNS})

    return out_path


def main() -> None:
    out = build_metrics_view()
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
