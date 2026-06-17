"""Family C withhold-participation (offline-validators) sweep orchestrator (T52).

Drives protocols × N_VALUES × (1 control + per-protocol attack f's) × seeds
through the resumable/parallel memory-aware ``common.run_grid_tiered`` (the
Snowman n=25 class runs at ``--heavy-jobs``, default 1), applies the offline
window/buffer clip, runs the T40 reducers, and writes one
results/adversary/offline_validators.csv.

The per-cell pipeline mirrors src/adversary/sweep.py (the T51 delay sweep),
EXCEPT the cell is a 4-tuple ``(proto, n, f, seed)`` (offline has no magnitude
axis), the attack grid is per-protocol (PBFT/FFG include the above-cliff
f=0.40; Snowman stops at 0.33), the runner is ``OFFLINE_RUNNERS``, and the
headline post-pass is a ``throughput_ratio`` (tps vs the f=0 control) rather
than a finality-delay ratio:

    run_<proto>_offline(n, f, seed)       # full W+buffer horizon, offline nodes
        -> clip_records(records, W, one_round)
        -> reducer(kept, ...)             # the existing T40 reducer
        -> row + common adversary annotation columns

The headline ``throughput_ratio`` is filled by a POST-grid pass (mirroring
sweep.py::_finality_delay_ratios), so each ``_run_cell`` stays a pure per-cell
function.

Run from repo root:
    PYTHONPATH=src python3 -m adversary.offline_sweep                 # full
    PYTHONPATH=src python3 -m adversary.offline_sweep --smoke         # 1 seed
    PYTHONPATH=src python3 -m adversary.offline_sweep --probe         # calib
    PYTHONPATH=src python3 -m adversary.offline_sweep --jobs 8 --heavy-jobs 1

Design contract: docs/plans/2026-06-17-t52-offline-validators-design.md
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
import sys
from pathlib import Path

from common import run_grid_tiered
from common.sweep import estimate_runtime
from event_log import EventRecord
from output.csv import _generic_cols, _format_row, _resolve_commit_hash
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult

from pbft import PBFT_VIEW_CHANGE
from pbft.summarise import summarise as _pbft_summarise
from pos.summarise import summarise as _pos_summarise
from snowman.summarise import summarise as _snowman_summarise

from delay.clip import clip_records
from delay.sweep import _window_denominator_fix

from . import offline_config as ocfg
from .runners import OFFLINE_RUNNERS
from .sweep_common import (ADV_COMMON_COLUMNS, strategy_label, is_heavy_snowman,
                          format_common_adv_cols)


_OUT = Path("results/adversary/offline_validators.csv")

_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}

_PROTOCOLS: tuple[str, ...] = ("pbft", "casper-ffg", "snowman")

# Annotation columns: the shared adversary block + the offline headline.
_HEADLINE_COLUMNS: tuple[str, ...] = ("throughput_ratio",)
_ADV_COLUMNS: tuple[str, ...] = ADV_COMMON_COLUMNS + _HEADLINE_COLUMNS

_ALL_COLUMNS = list(COLUMN_ORDER) + list(_ADV_COLUMNS)

# A control cell is identified by f == 0.0.
_CONTROL_F = 0.0


def _build_row(records: list[EventRecord], result: RunResult,
               meta: ScenarioMeta, n: int, f: float,
               clipped_fraction: float, commit_hash: str) -> dict[str, object]:
    """Project one clipped run to a CSV row: T40 generic + reducer columns,
    plus the common adversary annotation block. throughput_ratio is NaN here
    and filled by the post-grid pass."""
    row = _generic_cols(records, result, meta, commit_hash=commit_hash)
    row.update(_REDUCERS[meta.protocol](records, result, meta))
    _window_denominator_fix(row, records, meta)

    view_changes = sum(1 for r in records
                       if r.event_type == PBFT_VIEW_CHANGE)
    row["adversary_strategy"] = strategy_label(f, "withhold-participation")
    row["adversary_node_count"] = math.floor(f * n)
    row["byzantine_fraction"] = f
    row["view_change_count"] = view_changes
    row["clipped_fraction"] = clipped_fraction
    row["run_horizon_s"] = ocfg.T_MAX
    row["throughput_ratio"] = float("nan")     # post-pass fills this
    return row


# --- Driver adapter (module-level for the `spawn` Pool). -----------------

_SCHEMA_TAG = (tuple(COLUMN_ORDER), _ADV_COLUMNS)


def _cell_key(cell: tuple) -> str:
    """Stable, total-order, filesystem-safe identity (filename + sort key)."""
    proto, n, f, seed = cell
    return (f"{proto}__n{n}__f{f:.2f}__seed{seed:02d}")


def _phase_canon(ph) -> tuple:
    return (ph.t_start, ph.t_end, ph.delay.kind,
            tuple(sorted(ph.delay.params.items())), ph.p_drop,
            repr(ph.partitions))


def _param_fingerprint(cell: tuple) -> str:
    """blake2b over the cell's canonicalized config: (proto, n, f, the
    static-baseline phase tuple, T_MAX, schema_tag). f enters the hash, so
    every f point fingerprints distinctly. `seed` is the cell identity (in the
    filename), not a param, so it is excluded."""
    proto, n, f, seed = cell
    canon = repr((proto, n, f, ocfg.STATIC_BASELINE.name,
                  tuple(_phase_canon(ph)
                        for ph in ocfg.STATIC_BASELINE.phases()),
                  ocfg.T_MAX, _SCHEMA_TAG))
    return hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()


def _run_cell(cell: tuple, run_constants: dict) -> dict[str, object]:
    """Pure per-cell row builder: runner -> clip -> _build_row. commit_hash is
    threaded in from run_constants (resolved once in the parent). The clip
    window reads from offline_config so it matches the offline run horizon."""
    proto, n, f, seed = cell
    records, result, meta = OFFLINE_RUNNERS[proto](n, f, seed)
    kept, stats = clip_records(records, ocfg.WINDOW_S, ocfg.ONE_ROUND_S[proto])
    return _build_row(kept, result, meta, n, f,
                      stats.clipped_fraction, run_constants["commit_hash"])


def _throughput_ratios(rows: list[dict[str, object]]) -> None:
    """Fill each row's throughput_ratio IN PLACE (post-grid pass).

    Control (f=0) rows are 1.0 by definition. For an attack row, the ratio is
    tps(cell) / tps(control) at the same (protocol, n, seed); NaN if the
    control is absent from this collection or had no throughput (tps NaN or
    <= 0), or if the attack cell's tps is NaN (a stall cell)."""
    control: dict[tuple, float] = {}
    for r in rows:
        if r["byzantine_fraction"] == _CONTROL_F:
            control[(r["protocol"], r["n"], r["seed"])] = r["tps"]
    for r in rows:
        if r["byzantine_fraction"] == _CONTROL_F:
            r["throughput_ratio"] = 1.0
            continue
        denom = control.get((r["protocol"], r["n"], r["seed"]))
        num = r["tps"]
        if (denom is None or not isinstance(denom, (int, float))
                or math.isnan(denom) or denom <= 0
                or not isinstance(num, (int, float)) or math.isnan(num)):
            r["throughput_ratio"] = float("nan")
        else:
            r["throughput_ratio"] = num / denom


def _is_heavy_cell(cell: tuple) -> bool:
    """The memory-heavy class: Snowman n>=25 (one cell materializes a large
    EventRecord stream; run it at --heavy-jobs, default 1)."""
    proto, n, _f, _seed = cell
    return is_heavy_snowman(proto, n)


def _build_cells(seeds: tuple[int, ...]) -> list[tuple]:
    """The full cell list. Per (proto, n, seed): 1 control (f=0) + the
    per-protocol attack f's (f>0). PBFT/FFG include the above-cliff f=0.40;
    Snowman stops at 0.33."""
    cells = []
    for p in _PROTOCOLS:
        attack_f = tuple(f for f in ocfg.F_VALUES[p] if f != _CONTROL_F)
        for n in ocfg.N_VALUES:
            for s in seeds:
                cells.append((p, n, _CONTROL_F, s))      # control
                for f in attack_f:
                    cells.append((p, n, f, s))
    return cells


def run_sweep(seeds: tuple[int, ...] | None = None, *,
              out: Path = _OUT, jobs: int = 1, heavy_jobs: int = 1,
              fresh: bool = False, progress_stream=None,
              ) -> tuple[list[dict[str, object]], float]:
    """Execute the offline-validators sweep via the memory-aware
    resumable/parallel driver. Returns (rows, worst_clipped_fraction);
    throughput_ratio is filled by the post-grid pass before return.
    Checkpoints live under <out_dir>/.sweep_offline; commit_hash is resolved
    once in the parent."""
    seeds = ocfg.SEEDS if seeds is None else seeds
    commit_hash = _resolve_commit_hash()
    cells = _build_cells(seeds)
    rows = run_grid_tiered(cells, _run_cell, _cell_key,
                           checkpoint_dir=Path(out).parent / ".sweep_offline",
                           run_constants={"commit_hash": commit_hash},
                           param_fingerprint=_param_fingerprint,
                           is_heavy=_is_heavy_cell,
                           jobs=jobs, heavy_jobs=heavy_jobs,
                           fresh=fresh, progress_stream=progress_stream)
    _throughput_ratios(rows)
    worst = max((r["clipped_fraction"] for r in rows), default=0.0)
    return rows, worst


def write_csv(rows: list[dict[str, object]], path: Path = _OUT) -> None:
    """Write rows in COLUMN_ORDER + the common adversary columns + the offline
    headline, sorted by (protocol, n, byzantine_fraction, seed)."""
    rows = sorted(rows, key=lambda r: (r["protocol"], r["n"],
                                       r["byzantine_fraction"], r["seed"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_ALL_COLUMNS,
                                extrasaction="raise")
        writer.writeheader()
        for row in rows:
            formatted = _format_row({k: row[k] for k in COLUMN_ORDER})
            formatted.update(format_common_adv_cols(row))
            formatted["throughput_ratio"] = f"{row['throughput_ratio']:.6f}"
            writer.writerow(formatted)


def _preflight_estimate(seeds: tuple[int, ...], jobs: int, stream) -> None:
    """Pre-flight wall-clock estimate: time one largest-f cell per protocol at
    the smallest n, project to the full grid. Rough (smallest-n sample
    under-counts Snowman n=25); stderr only, never persisted."""
    commit_hash = _resolve_commit_hash()
    n0 = min(ocfg.N_VALUES)
    samples = [(p, n0, max(ocfg.F_VALUES[p]), seeds[0]) for p in _PROTOCOLS]
    timings = estimate_runtime(samples, _run_cell,
                               {"commit_hash": commit_hash})
    cells = _build_cells(seeds)
    total = 0.0
    for (proto, _, _, _), sec in timings.items():
        n_cells = sum(1 for c in cells if c[0] == proto)
        proj = n_cells * sec
        total += proj
        stream.write(f"[estimate] {proto}: ~{sec:.1f}s/cell (n={n0}, max f) "
                     f"× {n_cells} cells ≈ {proj / 60:.1f} min "
                     f"(rough — Snowman n=25 is far costlier than n={n0})\n")
    eff = total / max(1, jobs)
    stream.write(f"[estimate] total ≈ {total / 60:.1f} min sequential, "
                 f"~{eff / 60:.1f} min at jobs={jobs} "
                 f"(rough, smallest-n sample, from scratch)\n")
    stream.flush()


def _probe(stream) -> None:
    """Calibration probe: one seed per (protocol, n=10 AND n=25) at the largest
    f for that protocol (PBFT/FFG include f=0.40, the above-cliff stall +
    view-change regime), printing first-decision latency, clip fraction,
    in-window finalizations, and PBFT view-change count, so WINDOW_S / BUFFER_S
    / ONE_ROUND_S / PBFT_VC_DELAY_S can be finalised before the full sweep
    commits. Does not write the dataset."""
    stream.write(f"[probe] static-baseline, seed 0, largest-f per protocol; "
                 f"W={ocfg.WINDOW_S:.0f}s, horizon={ocfg.T_MAX:.0f}s:\n")
    for proto in _PROTOCOLS:
        f_max = max(ocfg.F_VALUES[proto])
        for n in ocfg.N_VALUES:
            records, result, meta = OFFLINE_RUNNERS[proto](n, f_max, 0)
            decided = [r for r in records if r.event_type == "decided"]
            first = min((r.t for r in decided), default=float("nan"))
            kept, stats = clip_records(records, ocfg.WINDOW_S,
                                       ocfg.ONE_ROUND_S[proto])
            vc = sum(1 for r in records if r.event_type == PBFT_VIEW_CHANGE)
            kept_dec = len({r.fields.get("instance_id") for r in kept
                            if r.event_type == "decided"})
            stream.write(
                f"  {proto:11s} n={n:<3d} f={f_max:.2f}  "
                f"first_decision={first:8.3f}s  "
                f"clipped={stats.clipped_fraction * 100:5.2f}%  "
                f"in_window_finalized={kept_dec:4d}  view_changes={vc}\n")
    stream.flush()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Family C withhold-participation (offline-validators) "
                    "sweep (T52).")
    ap.add_argument("--smoke", action="store_true",
                    help="1 seed only (fast sanity, not the real dataset).")
    ap.add_argument("--probe", action="store_true",
                    help="calibration probe only (no dataset written).")
    ap.add_argument("--out", default=str(_OUT), help="output CSV path.")
    ap.add_argument("--jobs", type=int, default=1,
                    help="parallel workers for the light cell class (default 1).")
    ap.add_argument("--heavy-jobs", type=int, default=1,
                    help="parallel workers for the Snowman n>=25 class "
                         "(default 1; each cell is memory-heavy).")
    ap.add_argument("--fresh", action="store_true",
                    help="clear the checkpoint dir first (recompute all).")
    args = ap.parse_args()

    if args.probe:
        _probe(sys.stderr)
        return

    seeds = (0,) if args.smoke else ocfg.SEEDS
    out = Path(args.out)
    _preflight_estimate(seeds, args.jobs, sys.stderr)
    rows, worst = run_sweep(seeds=seeds, out=out, jobs=args.jobs,
                            heavy_jobs=args.heavy_jobs, fresh=args.fresh,
                            progress_stream=sys.stderr)
    write_csv(rows, out)
    print(f"wrote {len(rows)} rows -> {out}")
    print(f"worst clipped_fraction = {worst*100:.2f}%  "
          f"(reported, not guarded — Option-B W cap, human 2026-06-15)")


if __name__ == "__main__":
    main()
