"""Family C equivocate-vote (equivocating-nodes) sweep orchestrator (T53).

Drives protocols × N_VALUES × (1 control + per-protocol attack f's) × seeds
through the resumable/parallel memory-aware ``common.run_grid_tiered`` (the
Snowman n=25 class runs at ``--heavy-jobs``, default 1), applies the equivocate
window/buffer clip, runs the T40 reducers, and writes one
results/adversary/equivocating_nodes.csv.

The per-cell pipeline mirrors src/adversary/offline_sweep.py (the T52 offline
sweep), EXCEPT: the runner is ``EQUIVOCATE_RUNNERS`` (the equivocating-subclass
factories — no inject_* wrap), the per-protocol attack grid runs PBFT/FFG ABOVE
the 1/3 threshold (f=0.40, 0.50) to expose the safety cliff while Snowman stops
at 0.33, and the headline is a per-cell SAFETY signal triple rather than an
offline throughput ratio:

    run_<proto>_equiv(n, f, seed)         # full W+buffer horizon, Byzantine prefix
        -> safety_signals(records, byz)   # on the FULL (unclipped) records
        -> clip_records(records, W, one_round)
        -> reducer(kept, ...)             # the existing T40 reducer
        -> row + common adversary annotation columns + safety triple

Unlike offline_sweep, there is NO post-grid pass: the safety signals are
computed per-cell (a safety violation anywhere in the run — even in the
post-window buffer — counts), so each ``_run_cell`` is fully self-contained.

Run from repo root:
    PYTHONPATH=src python3 -m adversary.equivocate_sweep                 # full
    PYTHONPATH=src python3 -m adversary.equivocate_sweep --smoke         # 1 seed
    PYTHONPATH=src python3 -m adversary.equivocate_sweep --probe         # calib
    PYTHONPATH=src python3 -m adversary.equivocate_sweep --jobs 8 --heavy-jobs 1
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

from . import equivocate_config as ecfg
from .runners import EQUIVOCATE_RUNNERS
from .safety import safety_signals
from .select import byzantine_node_ids
from .sweep_common import (ADV_COMMON_COLUMNS, strategy_label, is_heavy_snowman,
                          format_common_adv_cols)


_OUT = Path("results/adversary/equivocating_nodes.csv")

_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}

_PROTOCOLS: tuple[str, ...] = ("pbft", "casper-ffg", "snowman")

# Annotation columns: the shared adversary block + the equivocate safety triple.
_HEADLINE_COLUMNS: tuple[str, ...] = ("safety_violation",
                                      "conflicting_instances",
                                      "max_slashable_stake_fraction")
_ADV_COLUMNS: tuple[str, ...] = ADV_COMMON_COLUMNS + _HEADLINE_COLUMNS

_ALL_COLUMNS = list(COLUMN_ORDER) + list(_ADV_COLUMNS)

# A control cell is identified by f == 0.0.
_CONTROL_F = 0.0


def _build_row(records: list[EventRecord], result: RunResult,
               meta: ScenarioMeta, n: int, f: float,
               clipped_fraction: float, commit_hash: str,
               safety: dict) -> dict[str, object]:
    """Project one clipped run to a CSV row: T40 generic + reducer columns,
    plus the common adversary annotation block and the safety headline triple.
    ``safety`` is computed by the caller on the FULL (unclipped) records."""
    row = _generic_cols(records, result, meta, commit_hash=commit_hash)
    row.update(_REDUCERS[meta.protocol](records, result, meta))
    _window_denominator_fix(row, records, meta)

    view_changes = sum(1 for r in records
                       if r.event_type == PBFT_VIEW_CHANGE)
    row["adversary_strategy"] = strategy_label(f, "equivocate-vote")
    row["adversary_node_count"] = math.floor(f * n)
    row["byzantine_fraction"] = f
    row["view_change_count"] = view_changes
    row["clipped_fraction"] = clipped_fraction
    row["run_horizon_s"] = ecfg.T_MAX
    row.update(safety)
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
    static-baseline phase tuple, T_MAX, WINDOW_S, BUFFER_S, schema_tag). f
    enters the hash, so every f point fingerprints distinctly. WINDOW_S and
    BUFFER_S are hashed independently of T_MAX (so a re-probe that shifts them
    oppositely with T_MAX constant still invalidates stale checkpoints). The
    safety-triple schema tag (in _SCHEMA_TAG) distinguishes this dataset's
    checkpoints from offline's. `seed` is the cell identity, not a param."""
    proto, n, f, seed = cell
    canon = repr((proto, n, f, ecfg.STATIC_BASELINE.name,
                  tuple(_phase_canon(ph)
                        for ph in ecfg.STATIC_BASELINE.phases()),
                  ecfg.T_MAX, ecfg.WINDOW_S, ecfg.BUFFER_S, _SCHEMA_TAG))
    return hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()


def _run_cell(cell: tuple, run_constants: dict) -> dict[str, object]:
    """Pure per-cell row builder: runner -> safety (full records) -> clip ->
    _build_row. commit_hash is threaded in from run_constants (resolved once in
    the parent). Safety is measured on the FULL records so a violation that
    lands in the post-window buffer still counts; the reducer columns are
    measured on the clipped window."""
    proto, n, f, seed = cell
    records, result, meta = EQUIVOCATE_RUNNERS[proto](n, f, seed)
    byz = frozenset(byzantine_node_ids(n, f))
    safety = safety_signals(records, byz)              # on FULL records
    kept, stats = clip_records(records, ecfg.WINDOW_S, ecfg.ONE_ROUND_S[proto])
    return _build_row(kept, result, meta, n, f, stats.clipped_fraction,
                      run_constants["commit_hash"], safety)


def _is_heavy_cell(cell: tuple) -> bool:
    """The memory-heavy class: Snowman n>=25 (one cell materializes a large
    EventRecord stream; run it at --heavy-jobs, default 1)."""
    proto, n, _f, _seed = cell
    return is_heavy_snowman(proto, n)


def _build_cells(seeds: tuple[int, ...]) -> list[tuple]:
    """The full cell list. Per (proto, n, seed): 1 control (f=0) + the
    per-protocol attack f's (f>0). PBFT/FFG include the above-cliff f=0.40,
    0.50; Snowman stops at 0.33."""
    cells = []
    for p in _PROTOCOLS:
        attack_f = tuple(f for f in ecfg.F_VALUES[p] if f != _CONTROL_F)
        for n in ecfg.N_VALUES:
            for s in seeds:
                cells.append((p, n, _CONTROL_F, s))      # control
                for f in attack_f:
                    cells.append((p, n, f, s))
    return cells


def run_sweep(seeds: tuple[int, ...] | None = None, *,
              out: Path = _OUT, jobs: int = 1, heavy_jobs: int = 1,
              fresh: bool = False, progress_stream=None,
              ) -> tuple[list[dict[str, object]], float]:
    """Execute the equivocating-nodes sweep via the memory-aware
    resumable/parallel driver. Returns (rows, worst_clipped_fraction). There is
    NO post-grid pass — the safety triple is per-cell. Checkpoints live under
    <out_dir>/.sweep_equivocate; commit_hash is resolved once in the parent."""
    seeds = ecfg.SEEDS if seeds is None else seeds
    commit_hash = _resolve_commit_hash()
    cells = _build_cells(seeds)
    rows = run_grid_tiered(cells, _run_cell, _cell_key,
                           checkpoint_dir=Path(out).parent / ".sweep_equivocate",
                           run_constants={"commit_hash": commit_hash},
                           param_fingerprint=_param_fingerprint,
                           is_heavy=_is_heavy_cell,
                           jobs=jobs, heavy_jobs=heavy_jobs,
                           fresh=fresh, progress_stream=progress_stream)
    worst = max((r["clipped_fraction"] for r in rows), default=0.0)
    return rows, worst


def write_csv(rows: list[dict[str, object]], path: Path = _OUT) -> None:
    """Write rows in COLUMN_ORDER + the common adversary columns + the safety
    triple, sorted by (protocol, n, byzantine_fraction, seed)."""
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
            formatted["safety_violation"] = str(int(bool(row["safety_violation"])))
            formatted["conflicting_instances"] = str(int(row["conflicting_instances"]))
            formatted["max_slashable_stake_fraction"] = \
                f"{row['max_slashable_stake_fraction']:.6f}"
            writer.writerow(formatted)


def _preflight_estimate(seeds: tuple[int, ...], jobs: int, stream) -> None:
    """Pre-flight wall-clock estimate: time one largest-f cell per protocol at
    the smallest n, project to the full grid. Rough (smallest-n sample
    under-counts Snowman n=25); stderr only, never persisted."""
    commit_hash = _resolve_commit_hash()
    n0 = min(ecfg.N_VALUES)
    samples = [(p, n0, max(ecfg.F_VALUES[p]), seeds[0]) for p in _PROTOCOLS]
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
    f for that protocol (PBFT/FFG include the above-cliff f=0.50), printing
    first-decision latency, clip fraction, in-window finalizations, PBFT
    view-change count, AND the safety headline (safety_violation +
    max_slashable_stake_fraction) so WINDOW_S/BUFFER_S/ONE_ROUND_S can be
    finalised and the cliff confirmed (Task 10/11). Does not write the dataset."""
    stream.write(f"[probe] static-baseline, seed 0, largest-f per protocol; "
                 f"W={ecfg.WINDOW_S:.0f}s, horizon={ecfg.T_MAX:.0f}s:\n")
    for proto in _PROTOCOLS:
        f_max = max(ecfg.F_VALUES[proto])
        for n in ecfg.N_VALUES:
            records, result, meta = EQUIVOCATE_RUNNERS[proto](n, f_max, 0)
            byz = frozenset(byzantine_node_ids(n, f_max))
            safety = safety_signals(records, byz)
            decided = [r for r in records if r.event_type == "decided"]
            first = min((r.t for r in decided), default=float("nan"))
            kept, stats = clip_records(records, ecfg.WINDOW_S,
                                       ecfg.ONE_ROUND_S[proto])
            vc = sum(1 for r in records if r.event_type == PBFT_VIEW_CHANGE)
            kept_dec = len({r.fields.get("instance_id") for r in kept
                            if r.event_type == "decided"})
            stream.write(
                f"  {proto:11s} n={n:<3d} f={f_max:.2f}  "
                f"first_decision={first:8.3f}s  "
                f"clipped={stats.clipped_fraction * 100:5.2f}%  "
                f"in_window_finalized={kept_dec:4d}  view_changes={vc}  "
                f"safety_violation={int(bool(safety['safety_violation']))}  "
                f"conflicting={safety['conflicting_instances']}  "
                f"max_slashable={safety['max_slashable_stake_fraction']:.4f}\n")
    stream.flush()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Family C equivocate-vote (equivocating-nodes) sweep (T53).")
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

    seeds = (0,) if args.smoke else ecfg.SEEDS
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
