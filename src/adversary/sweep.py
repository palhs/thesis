"""Family C delay-emission (delayed-voters) sweep orchestrator (T51).

Drives protocols × N_VALUES × (1 control + F×M attack cells) × seeds through
the resumable/parallel memory-aware ``common.run_grid_tiered`` (the Snowman
n=25 class runs at ``--heavy-jobs``, default 1), applies the T46 window/buffer
clip, runs the T40 reducers, and writes one results/adversary/delayed_voters.csv.

The per-cell pipeline mirrors src/delay/heavy.py:

    run_<proto>(n, f, m, seed)            # full W+buffer horizon, slow voters
        -> clip_records(records, W, one_round)
        -> reducer(kept, ...)             # the existing T40 reducer
        -> row + Family-C annotation columns

The headline ``finality_delay_ratio`` is filled by a POST-grid pass (mirroring
heavy.py::_finalization_rates), so each ``_run_cell`` stays a pure per-cell
function -- the property the T46.1 induction relies on.

Run from repo root:
    PYTHONPATH=src python3 -m adversary.sweep                 # full sweep
    PYTHONPATH=src python3 -m adversary.sweep --smoke         # 1 seed sanity
    PYTHONPATH=src python3 -m adversary.sweep --probe         # calibration only
    PYTHONPATH=src python3 -m adversary.sweep --jobs 8 --heavy-jobs 1

Design contract: wiki/experiments/2026-06-14_delayed-voters.md
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

from . import config as cfg
from .runners import RUNNERS


_OUT = Path("results/adversary/delayed_voters.csv")

_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}

_PROTOCOLS: tuple[str, ...] = ("pbft", "casper-ffg", "snowman")

# Family-C annotation columns appended after the 18-column T40 projection.
_ADV_COLUMNS: tuple[str, ...] = (
    "adversary_strategy",     # "delay-emission" (or "none" for f=0)
    "byzantine_fraction",     # nominal f
    "slow_node_count",        # realized ⌊f·n⌋
    "delay_mult",             # m (0.0 for the f=0 control)
    "view_change_count",      # PBFT view-changes in [0, W] (0 for FFG/Snowman)
    "clipped_fraction",       # tail past W / in-scope (reported)
    "run_horizon_s",          # W + buffer
    "finality_delay_ratio",   # headline (post-pass)
)

_ALL_COLUMNS = list(COLUMN_ORDER) + list(_ADV_COLUMNS)

# A control cell is identified by f == 0.0 (m is 0.0 and ignored there).
_CONTROL_F = 0.0


def _strategy(f: float) -> str:
    return "none" if f == _CONTROL_F else "delay-emission"


def _build_row(records: list[EventRecord], result: RunResult,
               meta: ScenarioMeta, n: int, f: float, m: float,
               clipped_fraction: float, commit_hash: str) -> dict[str, object]:
    """Project one clipped run to a CSV row: T40 generic + reducer columns,
    plus the Family-C annotation block. finality_delay_ratio is NaN here and
    filled by the post-grid pass."""
    row = _generic_cols(records, result, meta, commit_hash=commit_hash)
    row.update(_REDUCERS[meta.protocol](records, result, meta))
    _window_denominator_fix(row, records, meta)

    view_changes = sum(1 for r in records
                       if r.event_type == PBFT_VIEW_CHANGE)
    slow_count = math.floor(f * n)
    row["adversary_strategy"] = _strategy(f)
    row["byzantine_fraction"] = f
    row["slow_node_count"] = slow_count
    row["delay_mult"] = m
    row["view_change_count"] = view_changes
    row["clipped_fraction"] = clipped_fraction
    row["run_horizon_s"] = cfg.T_MAX
    row["finality_delay_ratio"] = float("nan")     # post-pass fills this
    return row


# --- Driver adapter (module-level for the `spawn` Pool). -----------------

_SCHEMA_TAG = (tuple(COLUMN_ORDER), _ADV_COLUMNS)


def _cell_key(cell: tuple) -> str:
    """Stable, total-order, filesystem-safe identity (filename + sort key)."""
    proto, n, f, m, seed = cell
    return (f"{proto}__n{n}__f{f:.2f}__m{m:04.1f}__seed{seed:02d}")


def _phase_canon(ph) -> tuple:
    return (ph.t_start, ph.t_end, ph.delay.kind,
            tuple(sorted(ph.delay.params.items())), ph.p_drop,
            repr(ph.partitions))


def _param_fingerprint(cell: tuple) -> str:
    """blake2b over the cell's canonicalized config: (proto, n, f, m, the
    static-baseline phase tuple, T_MAX, schema_tag). f and m both enter the
    hash, so every (f, m) point fingerprints distinctly. `seed` is the cell
    identity (in the filename), not a param, so it is excluded."""
    proto, n, f, m, seed = cell
    canon = repr((proto, n, f, m, cfg.STATIC_BASELINE.name,
                  tuple(_phase_canon(ph)
                        for ph in cfg.STATIC_BASELINE.phases()),
                  cfg.T_MAX, _SCHEMA_TAG))
    return hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()


def _run_cell(cell: tuple, run_constants: dict) -> dict[str, object]:
    """Pure per-cell row builder: runner -> clip -> _build_row. commit_hash is
    threaded in from run_constants (resolved once in the parent)."""
    proto, n, f, m, seed = cell
    records, result, meta = RUNNERS[proto](n, f, m, seed)
    kept, stats = clip_records(records, cfg.WINDOW_S, cfg.ONE_ROUND_S[proto])
    return _build_row(kept, result, meta, n, f, m,
                      stats.clipped_fraction, run_constants["commit_hash"])


def _finality_delay_ratios(rows: list[dict[str, object]]) -> None:
    """Fill each row's finality_delay_ratio IN PLACE (post-grid pass).

    Control (f=0) rows are 1.0 by definition. For an attack row, the ratio is
    commit_latency_ms(cell) / commit_latency_ms(control) at the same
    (protocol, n, seed); NaN if the control is absent from this collection or
    did not finalize (commit_latency_ms NaN or <= 0)."""
    control: dict[tuple, float] = {}
    for r in rows:
        if r["byzantine_fraction"] == _CONTROL_F:
            control[(r["protocol"], r["n"], r["seed"])] = r["commit_latency_ms"]
    for r in rows:
        if r["byzantine_fraction"] == _CONTROL_F:
            r["finality_delay_ratio"] = 1.0
            continue
        denom = control.get((r["protocol"], r["n"], r["seed"]))
        num = r["commit_latency_ms"]
        if (denom is None or not isinstance(denom, (int, float))
                or math.isnan(denom) or denom <= 0
                or not isinstance(num, (int, float)) or math.isnan(num)):
            r["finality_delay_ratio"] = float("nan")
        else:
            r["finality_delay_ratio"] = num / denom


def _is_heavy_cell(cell: tuple) -> bool:
    """The memory-heavy class: Snowman n>=25 (one cell materializes a large
    EventRecord stream; run it at --heavy-jobs, default 1). Mirrors
    delay.heavy._is_heavy_cell."""
    proto, n, _f, _m, _seed = cell
    return proto == "snowman" and int(n) >= 25


def _build_cells(seeds: tuple[int, ...]) -> list[tuple]:
    """The full cell list. Per (proto, n, seed): 1 control (f=0, m=0) + the
    F×M attack grid (f>0)."""
    attack_f = tuple(f for f in cfg.F_VALUES if f != _CONTROL_F)
    cells = []
    for p in _PROTOCOLS:
        for n in cfg.N_VALUES:
            for s in seeds:
                cells.append((p, n, _CONTROL_F, 0.0, s))      # control
                for f in attack_f:
                    for m in cfg.M_VALUES:
                        cells.append((p, n, f, m, s))
    return cells


def run_sweep(seeds: tuple[int, ...] | None = None, *,
              out: Path = _OUT, jobs: int = 1, heavy_jobs: int = 1,
              fresh: bool = False, progress_stream=None,
              ) -> tuple[list[dict[str, object]], float]:
    """Execute the Family C sweep via the memory-aware resumable/parallel
    driver. Returns (rows, worst_clipped_fraction); finality_delay_ratio is
    filled by the post-grid pass before return. Checkpoints live under
    <out_dir>/.sweep_adversary; commit_hash is resolved once in the parent."""
    seeds = cfg.SEEDS if seeds is None else seeds
    commit_hash = _resolve_commit_hash()
    cells = _build_cells(seeds)
    rows = run_grid_tiered(cells, _run_cell, _cell_key,
                           checkpoint_dir=Path(out).parent / ".sweep_adversary",
                           run_constants={"commit_hash": commit_hash},
                           param_fingerprint=_param_fingerprint,
                           is_heavy=_is_heavy_cell,
                           jobs=jobs, heavy_jobs=heavy_jobs,
                           fresh=fresh, progress_stream=progress_stream)
    _finality_delay_ratios(rows)
    worst = max((r["clipped_fraction"] for r in rows), default=0.0)
    return rows, worst


def write_csv(rows: list[dict[str, object]], path: Path = _OUT) -> None:
    """Write rows in COLUMN_ORDER + the Family-C columns, sorted by
    (protocol, n, byzantine_fraction, delay_mult, seed)."""
    rows = sorted(rows, key=lambda r: (r["protocol"], r["n"],
                                       r["byzantine_fraction"],
                                       r["delay_mult"], r["seed"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_ALL_COLUMNS,
                                extrasaction="raise")
        writer.writeheader()
        for row in rows:
            formatted = _format_row({k: row[k] for k in COLUMN_ORDER})
            formatted["adversary_strategy"] = str(row["adversary_strategy"])
            formatted["byzantine_fraction"] = f"{row['byzantine_fraction']:.6f}"
            formatted["slow_node_count"] = str(row["slow_node_count"])
            formatted["delay_mult"] = f"{row['delay_mult']:.6f}"
            formatted["view_change_count"] = str(row["view_change_count"])
            formatted["clipped_fraction"] = f"{row['clipped_fraction']:.6f}"
            formatted["run_horizon_s"] = f"{row['run_horizon_s']:.3f}"
            formatted["finality_delay_ratio"] = \
                f"{row['finality_delay_ratio']:.6f}"
            writer.writerow(formatted)


def _preflight_estimate(seeds: tuple[int, ...], jobs: int, stream) -> None:
    """Pre-flight wall-clock estimate: time one worst-magnitude cell per
    protocol at the smallest n, project to the full grid. Rough (smallest-n
    sample under-counts Snowman n=25); stderr only, never persisted."""
    commit_hash = _resolve_commit_hash()
    n0 = min(cfg.N_VALUES)
    m_max = max(cfg.M_VALUES)
    f_max = max(cfg.F_VALUES)
    samples = [(p, n0, f_max, m_max, seeds[0]) for p in _PROTOCOLS]
    timings = estimate_runtime(samples, _run_cell,
                               {"commit_hash": commit_hash})
    cells = _build_cells(seeds)
    total = 0.0
    for (proto, _, _, _, _), sec in timings.items():
        n_cells = sum(1 for c in cells if c[0] == proto)
        proj = n_cells * sec
        total += proj
        stream.write(f"[estimate] {proto}: ~{sec:.1f}s/cell (n={n0}, worst m) "
                     f"× {n_cells} cells ≈ {proj / 60:.1f} min "
                     f"(rough — Snowman n=25 is far costlier than n={n0})\n")
    eff = total / max(1, jobs)
    stream.write(f"[estimate] total ≈ {total / 60:.1f} min sequential, "
                 f"~{eff / 60:.1f} min at jobs={jobs} "
                 f"(rough, smallest-n sample, from scratch)\n")
    stream.flush()


def _probe(stream) -> None:
    """Calibration probe: one seed per (protocol, n=10) at the worst magnitude
    (m=max, slowest), printing first-decision latency, clip fraction, PBFT
    view-change count, and in-window finalizations, so WINDOW_S / BUFFER_S /
    ONE_ROUND_S / PBFT_VC_DELAY_S can be finalised before the full sweep
    commits. Does not write the dataset."""
    n0 = min(cfg.N_VALUES)
    m_max = max(cfg.M_VALUES)
    f_max = max(cfg.F_VALUES)
    stream.write(f"[probe] static-baseline, n={n0}, seed 0, worst attack "
                 f"(f={f_max}, m={m_max}); W={cfg.WINDOW_S:.0f}s, "
                 f"horizon={cfg.T_MAX:.0f}s:\n")
    for proto in _PROTOCOLS:
        records, result, meta = RUNNERS[proto](n0, f_max, m_max, 0)
        decided = [r for r in records if r.event_type == "decided"]
        first = min((r.t for r in decided), default=float("nan"))
        kept, stats = clip_records(records, cfg.WINDOW_S,
                                   cfg.ONE_ROUND_S[proto])
        vc = sum(1 for r in records if r.event_type == PBFT_VIEW_CHANGE)
        kept_dec = len({r.fields.get("instance_id") for r in kept
                        if r.event_type == "decided"})
        stream.write(
            f"  {proto:11s} first_decision={first:8.3f}s  "
            f"clipped={stats.clipped_fraction * 100:5.2f}%  "
            f"in_window_finalized={kept_dec:4d}  view_changes={vc}\n")
    stream.flush()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Family C delay-emission (delayed-voters) sweep (T51).")
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

    seeds = (0,) if args.smoke else cfg.SEEDS
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
