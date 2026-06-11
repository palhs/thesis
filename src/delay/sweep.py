"""Family B delay sweep orchestrator (T46).

Drives the two T46 timelines (delay-uniform, delay-exponential) × the two
validator sizes (n ∈ {10, 25}) × the three protocols (PBFT, Casper FFG,
Snowman) × 20 seeds, applies the window/buffer clip, and writes one
results/delay/delay.csv. Common random numbers: the same 20 seeds are
reused across protocols at each (timeline, n) point.

Per run the pipeline is:

    run_<proto>(timeline, n, seed)         # full W+buffer horizon
        -> clip_records(records, W, round) # keep in-window-started events
        -> reducer(kept_records, ...)      # the existing T40 reducer
        -> row + delay-annotation columns

The CSV is the 18-column T40 projection (run_id … alpha_c_over_K, via the
existing reducers and _generic_cols) PLUS five Family-B columns:
`network_phase_id`, `e_delay_ms`, `slot_duration_ms` (the protocol's
proposal cadence, FFG's rescaled), `clipped_fraction`, and
`run_horizon_s`. Plots annotate the per-timeline slot_duration and
E[delay] from these (experiment-matrix §5 "reported not hidden").

Run from repo root:
    PYTHONPATH=src python3 -m delay.sweep
    PYTHONPATH=src python3 -m delay.sweep --smoke   # 1 seed, fast sanity

Design contract: wiki/experiments/2026-06-10_delay-moderate.md
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from event_log import EventRecord
from output.csv import _generic_cols, _format_row, _resolve_commit_hash
from output.metrics import goodput as _goodput
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult

from pbft.summarise import summarise as _pbft_summarise
from pos.summarise import summarise as _pos_summarise
from snowman.summarise import summarise as _snowman_summarise

from . import config as cfg
from .clip import clip_records
from .runners import RUNNERS


_OUT = Path("results/delay/delay.csv")

_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}

# Family-B annotation columns appended after the 18-column T40 projection.
_DELAY_COLUMNS: tuple[str, ...] = (
    "network_phase_id",   # timeline name (delay-uniform / delay-exponential)
    "e_delay_ms",         # E[delay] of the timeline, ms
    "slot_duration_ms",   # proposal cadence (FFG rescaled to 1200 ms), ms
    "clipped_fraction",   # tail events past W / in-scope events (< 0.05)
    "run_horizon_s",      # W + buffer (the actual run t_max)
)

_PROTOCOLS: tuple[str, ...] = ("pbft", "casper-ffg", "snowman")


def _window_denominator_fix(row: dict[str, object],
                            kept: list[EventRecord],
                            meta: ScenarioMeta) -> None:
    """Re-base PBFT `tps` / `goodput` onto the measurement window W.

    The FFG and Snowman reducers divide their throughput by `meta.t_max`
    (which this harness sets to WINDOW_S — runners._meta), so after the
    clip they already report rate over the window. The PBFT reducer
    (src/pbft/summarise.py) instead divides by `result.now` — the *run
    horizon* (W + buffer), not the window — so on a windowed delay run its
    `tps` / `goodput` denominator is ~10 % too large relative to FFG /
    Snowman, breaking the cross-protocol throughput axis that is T46's
    headline. We recompute both PBFT columns over the in-window clipped
    `decided` stream and the WINDOW_S denominator here, where the harness
    owns its own projection, leaving the protocol package untouched. The
    fix is a no-op for FFG / Snowman (whose reducers are already
    window-based) — applied to PBFT only.

    This is the windowed analogue of the baseline, where PBFT's
    `result.now ≈ meta.t_max` makes the two denominators coincide; the
    divergence appears only once the run horizon exceeds the window.
    """
    if meta.protocol != "pbft":
        return
    decided = [r for r in kept if r.event_type == "decided"]
    window = meta.t_max                       # = WINDOW_S (runners._meta)
    if decided and window > 0:
        row["tps"] = len(decided) / window
        n_opportunities = len({r.fields.get("instance_id") for r in decided})
        row["goodput"] = _goodput(meta, n_opportunities, window)
    else:
        row["tps"] = float("nan")
        row["goodput"] = float("nan")


def _build_row(records: list[EventRecord], result: RunResult,
               meta: ScenarioMeta, timeline: cfg.Timeline,
               clipped_fraction: float, commit_hash: str) -> dict[str, object]:
    """Project one clipped run to a CSV row: the T40 generic + reducer
    columns, plus the Family-B annotation columns.

    `records` are the CLIPPED records (in-window-started, t<=W decided
    events plus the full transport stream); the reducers run on these.
    PBFT's throughput columns are then re-based onto the window
    denominator (`_window_denominator_fix`) so all three protocols report
    rate over [0, W]."""
    row = _generic_cols(records, result, meta, commit_hash=commit_hash)
    row.update(_REDUCERS[meta.protocol](records, result, meta))
    _window_denominator_fix(row, records, meta)
    row["network_phase_id"] = timeline.name
    row["e_delay_ms"] = timeline.e_delay_s * 1000.0
    row["slot_duration_ms"] = meta.interval * 1000.0
    row["clipped_fraction"] = clipped_fraction
    row["run_horizon_s"] = cfg.T_MAX
    return row


def run_sweep(seeds: tuple[int, ...] | None = None,
              ) -> tuple[list[dict[str, object]], float]:
    """Execute the full sweep. Returns `(rows, worst_clipped_fraction)`.

    `seeds=None` uses the locked 20-seed set; pass a subset for smoke runs.
    The worst clipped-fraction is surfaced so the orchestrator can assert
    the < 5 % calibration guard before trusting the dataset.
    """
    seeds = cfg.SEEDS if seeds is None else seeds
    commit_hash = _resolve_commit_hash()
    rows: list[dict[str, object]] = []
    worst = 0.0
    for protocol in _PROTOCOLS:
        runner = RUNNERS[protocol]
        one_round = cfg.ONE_ROUND_S[protocol]
        for timeline in cfg.TIMELINES:
            for n in cfg.N_VALUES:
                for seed in seeds:
                    records, result, meta = runner(timeline, n, seed)
                    kept, stats = clip_records(records, cfg.WINDOW_S,
                                               one_round)
                    worst = max(worst, stats.clipped_fraction)
                    rows.append(_build_row(kept, result, meta, timeline,
                                           stats.clipped_fraction,
                                           commit_hash))
    return rows, worst


def write_csv(rows: list[dict[str, object]], path: Path = _OUT) -> None:
    """Write rows to `path` in COLUMN_ORDER + the Family-B columns, sorted
    deterministically by (protocol, n, network_phase_id, seed)."""
    fieldnames = list(COLUMN_ORDER) + list(_DELAY_COLUMNS)
    rows = sorted(rows, key=lambda r: (r["protocol"], r["n"],
                                       r["network_phase_id"], r["seed"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames,
                                extrasaction="raise")
        writer.writeheader()
        for row in rows:
            formatted = _format_row({k: row[k] for k in COLUMN_ORDER})
            for col in _DELAY_COLUMNS:
                v = row[col]
                if col in ("e_delay_ms", "slot_duration_ms"):
                    formatted[col] = f"{v:.3f}" if isinstance(v, float) \
                        else str(v)
                elif col == "clipped_fraction":
                    formatted[col] = f"{v:.6f}"
                elif col == "run_horizon_s":
                    formatted[col] = f"{v:.3f}" if isinstance(v, float) \
                        else str(v)
                else:
                    formatted[col] = str(v)
            writer.writerow(formatted)


def main() -> None:
    ap = argparse.ArgumentParser(description="Family B delay sweep (T46).")
    ap.add_argument("--smoke", action="store_true",
                    help="1 seed only (fast sanity, not the real dataset).")
    ap.add_argument("--out", default=str(_OUT),
                    help="output CSV path.")
    args = ap.parse_args()

    seeds = (0,) if args.smoke else None
    rows, worst = run_sweep(seeds=seeds)
    write_csv(rows, Path(args.out))
    guard = "PASS" if worst < 0.05 else "FAIL (> 5% — see calibration)"
    print(f"wrote {len(rows)} rows -> {args.out}")
    print(f"worst clipped_fraction = {worst*100:.2f}%  [{guard}]")


if __name__ == "__main__":
    main()
