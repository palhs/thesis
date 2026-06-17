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
import hashlib
import sys
from pathlib import Path

from common import run_grid
from common.sweep import estimate_runtime
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


# --- Driver adapter (T46.1). --------------------------------------------
#
# The grid is a list of plain tuples `(protocol, timeline_name, n, seed)`
# driven through the shared `common.sweep.run_grid`. The four functions
# below are MODULE-LEVEL (no closures) so they pickle under the macOS
# `spawn` start method when `--jobs > 1`.

# Schema tag pinned into every fingerprint: a column-set change invalidates
# all sidecars (a row's shape changed), forcing a recompute on resume.
_SCHEMA_TAG = (tuple(COLUMN_ORDER), _DELAY_COLUMNS)


def _cell_key(cell: tuple) -> str:
    """Stable, total-order, filesystem-safe identity — used for BOTH the
    sidecar filename and the collect-sort order."""
    proto, tl_name, n, seed = cell
    return f"{proto}__{tl_name}__n{n}__seed{seed:02d}"


def _timeline_by_name(tl_name: str) -> cfg.Timeline:
    return next(t for t in cfg.TIMELINES if t.name == tl_name)


def _phase_canon(ph) -> tuple:
    """Canonical, deterministic form of one network Phase. `repr` of the
    float fields is the shortest round-tripping decimal (stable in
    Python 3), so semantically-equal configs fingerprint equal."""
    return (ph.t_start, ph.t_end, ph.delay.kind,
            tuple(sorted(ph.delay.params.items())), ph.p_drop,
            repr(ph.partitions))


def _param_fingerprint(cell: tuple) -> str:
    """blake2b over the cell's canonicalized config (design spec §4). Binds
    the sidecar to the params that produced it. Canonicalizes over the
    timeline's PHASE TUPLE, so it covers single-phase production timelines
    and the multi-phase / p_drop>0 witness timelines uniformly — the
    delay-kind, params, phase boundaries and drop probability all enter the
    hash. `seed` is the cell identity (in the filename), not a param, so it
    is excluded here."""
    proto, tl_name, n, seed = cell
    tl = _timeline_by_name(tl_name)
    canon = repr((proto, n, tl.name,
                  tuple(_phase_canon(ph) for ph in tl.phases()),
                  cfg.T_MAX, _SCHEMA_TAG))
    return hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()


def _run_cell(cell: tuple, run_constants: dict) -> dict[str, object]:
    """Pure per-cell row builder: runner -> clip -> _build_row. The
    `commit_hash` is THREADED IN from run_constants (resolved once in the
    parent), never resolved here (review B1)."""
    proto, tl_name, n, seed = cell
    timeline = _timeline_by_name(tl_name)
    records, result, meta = RUNNERS[proto](timeline, n, seed)
    kept, stats = clip_records(records, cfg.WINDOW_S, cfg.ONE_ROUND_S[proto])
    return _build_row(kept, result, meta, timeline, stats.clipped_fraction,
                      run_constants["commit_hash"])


def run_sweep(seeds: tuple[int, ...] | None = None, *,
              out: Path = _OUT, jobs: int = 1, fresh: bool = False,
              progress_stream=None,
              ) -> tuple[list[dict[str, object]], float]:
    """Execute the full sweep via the resumable/parallel driver. Returns
    `(rows, worst_clipped_fraction)`.

    `seeds=None` uses the locked 20-seed set; pass a subset for smoke runs.
    The checkpoint dir lives next to `out` (`<out_dir>/.sweep`), so distinct
    output paths checkpoint independently. `commit_hash` is resolved ONCE
    here in the parent and broadcast as a run constant. The worst
    clipped-fraction is surfaced for the < 5 % calibration guard.
    """
    seeds = cfg.SEEDS if seeds is None else seeds
    commit_hash = _resolve_commit_hash()             # ONCE, in the parent
    cells = [(p, tl.name, n, s)
             for p in _PROTOCOLS for tl in cfg.TIMELINES
             for n in cfg.N_VALUES for s in seeds]
    rows = run_grid(cells, _run_cell, _cell_key,
                    checkpoint_dir=Path(out).parent / ".sweep",
                    run_constants={"commit_hash": commit_hash},
                    param_fingerprint=_param_fingerprint,
                    jobs=jobs, fresh=fresh, progress_stream=progress_stream)
    worst = max((r["clipped_fraction"] for r in rows), default=0.0)
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


def _preflight_estimate(seeds: tuple[int, ...], jobs: int, stream) -> None:
    """Pre-flight wall-clock estimate (item d): time one cell per protocol
    at the smallest n / first timeline, then project per-protocol and total
    wall-clock to stderr. Rough — sampled at the smallest n, so it
    under-counts the Snowman n=25 tier; from-scratch (ignores already
    checkpointed cells). Timing is stderr-only, never persisted."""
    commit_hash = _resolve_commit_hash()
    n0 = min(cfg.N_VALUES)
    tl0 = cfg.TIMELINES[0].name
    samples = [(p, tl0, n0, seeds[0]) for p in _PROTOCOLS]
    timings = estimate_runtime(samples, _run_cell,
                               {"commit_hash": commit_hash})
    per_proto_cells = len(cfg.TIMELINES) * len(cfg.N_VALUES) * len(seeds)
    total = 0.0
    for (proto, _, _, _), sec in timings.items():
        proj = per_proto_cells * sec
        total += proj
        stream.write(f"[estimate] {proto}: ~{sec:.1f}s/cell (n={n0}) "
                     f"× {per_proto_cells} cells ≈ {proj / 60:.1f} min\n")
    eff = total / max(1, jobs)
    stream.write(f"[estimate] total ≈ {total / 60:.1f} min sequential, "
                 f"~{eff / 60:.1f} min at jobs={jobs} "
                 f"(rough, smallest-n sample, from scratch)\n")
    stream.flush()


def main() -> None:
    ap = argparse.ArgumentParser(description="Family B delay sweep (T46).")
    ap.add_argument("--smoke", action="store_true",
                    help="1 seed only (fast sanity, not the real dataset).")
    ap.add_argument("--out", default=str(_OUT),
                    help="output CSV path.")
    ap.add_argument("--jobs", type=int, default=1,
                    help="parallel worker processes (default 1: "
                         "single-process, clean provenance).")
    ap.add_argument("--fresh", action="store_true",
                    help="clear the checkpoint dir first (ignore resumable "
                         "sidecars and recompute every cell).")
    args = ap.parse_args()

    seeds = (0,) if args.smoke else cfg.SEEDS
    out = Path(args.out)
    _preflight_estimate(seeds, args.jobs, sys.stderr)
    rows, worst = run_sweep(seeds=seeds, out=out, jobs=args.jobs,
                            fresh=args.fresh, progress_stream=sys.stderr)
    write_csv(rows, out)
    guard = "PASS" if worst < 0.05 else "FAIL (> 5% — see calibration)"
    print(f"wrote {len(rows)} rows -> {out}")
    print(f"worst clipped_fraction = {worst*100:.2f}%  [{guard}]")


if __name__ == "__main__":
    main()
