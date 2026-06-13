"""Family B HEAVY delay + packet-loss sweep orchestrator (T47).

Completes Family B's delay axis past the two moderate T46 timelines: a
heavy-tail delay regime (1–5 s band, Pareto, E[delay] ≈ 3 s) with no loss,
plus the same regime under three packet-loss levels (`p_drop ∈ {0.05, 0.10,
0.20}`) — the "heavy delay (1–5 s) + packet loss (5–20 %)" task framing.
The 6th Family-B timeline (`partial-sync-gst`) is a separate follow-up (see
TASKS.md Backlog 2026-06-12); it is NOT in this task.

It REUSES the shared infrastructure T46.1 built — `common.sweep.run_grid`
(resumable + parallel), `delay.clip.clip_records`, the per-protocol T40
reducers — and the T46 `delay.runners`, parameterised by a `Calibration`
object so the heavy window / horizon / PBFT view-change knobs differ from
T46 without touching the frozen T46 dataset or its induction witnesses.

What this sweep measures that T46 did not:

  - `finalization_rate` — the headline. Under heavy delay + loss, an
    instance that started in [0, W] may never finalize. We define
    `finalization_rate = finalized_instances(cell) /
    finalized_instances(p_drop=0 sibling)` at the same (protocol, n, seed):
    the loss-free `delay-heavy-tail` run is the 100 % control, so the loss
    runs read as the fraction of that control's in-window finalizations they
    still achieve. Computed in a POST-grid pass (`_finalization_rates`) over
    the collected rows, so each `_run_cell` stays a pure per-cell function —
    the property the T46.1 induction relies on.
  - `view_change_count` — PBFT recovery. T47 calibrates PBFT's view-change
    timeout (`HEAVY_PBFT_VC_DELAY_S`) so PBFT rotates leaders to recover
    under loss but not spuriously under honest heavy-tail delay (validated:
    ~0 at p_drop=0, > 0 under loss). Always 0 for FFG / Snowman (no leader).
  - `clipped_fraction` is REPORTED, not guarded. Per the Week-9 Option-B
    decision (human 2026-06-12), W is capped at a tractable bound and the
    clip fraction on the slowest Snowman heavy cells is surfaced as a
    degradation signal rather than held under 5 %.

Run from repo root:
    PYTHONPATH=src python3 -m delay.heavy                # full 4×3×2×20 sweep
    PYTHONPATH=src python3 -m delay.heavy --smoke        # 1 seed, fast sanity
    PYTHONPATH=src python3 -m delay.heavy --jobs 8       # parallel
    PYTHONPATH=src python3 -m delay.heavy --probe        # calibration probe only

Design contract: wiki/experiments/2026-06-12_delay-heavy.md
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

from common import run_grid_tiered
from common.sweep import estimate_runtime
from event_log import EventRecord
from network import DelayDist, Phase
from output.csv import _generic_cols, _format_row, _resolve_commit_hash
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult

from pbft import PBFT_VIEW_CHANGE
from pbft.summarise import summarise as _pbft_summarise
from pos.summarise import summarise as _pos_summarise
from snowman.summarise import summarise as _snowman_summarise

from . import config as cfg
from .clip import clip_records
from .runners import RUNNERS, Calibration
from .sweep import _DELAY_COLUMNS, _window_denominator_fix


_OUT = Path("results/delay/delay_heavy.csv")

_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}

_PROTOCOLS: tuple[str, ...] = ("pbft", "casper-ffg", "snowman")


# === Heavy calibration (probe-derived; Week-9 Option-B, human 2026-06-12). ===
#
# The heavy-tail regime is ~10× the T46 E[delay], so Snowman's β=15
# sequential poll rounds push per-block finality toward ~150 s. Per the
# Option-B decision, W is CAPPED at a tractable bound (not grown to hold the
# T46 <5 % clip guard); the clip fraction on the slowest cells is reported.
HEAVY_WINDOW_S: float = 1000.0          # measurement window W (capped)
HEAVY_BUFFER_S: float = 150.0           # ≥ the slowest finalization tail
HEAVY_T_MAX: float = HEAVY_WINDOW_S + HEAVY_BUFFER_S

# Per-protocol one-round latency — the "started in [0, W]" scope bound.
# Probe-measured first-decision (n=10, seed 0, heavy-tail control): PBFT
# ≈ 6 s, Casper FFG ≈ 61 s, Snowman ≈ 61 s; these carry margin for the
# Pareto tail without over-inflating the clipped-fraction denominator.
HEAVY_ONE_ROUND_S: dict[str, float] = {
    "pbft":       20.0,
    "casper-ffg": 90.0,
    "snowman":   120.0,
}

# Casper FFG slot rescales to stay coherent with E[delay] ≈ 3 s
# (slot ≥ 4·E[delay] ⇒ 12 s, experiment-matrix-runs §2 pairing table).
HEAVY_FFG_SLOT_DURATION_S: float = 12.0

# PBFT view-change timeout: large enough that an honest heavy-tail commit
# (~3 phases × E[delay] ≈ 10–30 s) does not rotate the leader, small enough
# that packet loss stalling an instance triggers recovery. Validated by the
# view_change_count column reading ~0 at p_drop=0 and > 0 under loss.
HEAVY_PBFT_VC_DELAY_S: float = 90.0

# Heavy-tail (Pareto) delay: scale·paretovariate(shape), paretovariate ≥ 1,
# so min sample = scale and E = scale·shape/(shape−1). scale=1.0 s, shape=1.5
# ⇒ min 1 s, E[delay] = 3.0 s, mass in the 1–5 s band with a long tail.
HEAVY_DELAY_SCALE_S: float = 1.0
HEAVY_DELAY_SHAPE: float = 1.5
HEAVY_E_DELAY_S: float = HEAVY_DELAY_SCALE_S * HEAVY_DELAY_SHAPE \
    / (HEAVY_DELAY_SHAPE - 1.0)         # = 3.0 s

# Packet-loss sub-sweep (experiment-matrix-runs §2: "5–20 % loss").
P_DROP_LEVELS: tuple[float, ...] = (0.05, 0.10, 0.20)

HEAVY_CALIB = Calibration(t_max=HEAVY_T_MAX, window_s=HEAVY_WINDOW_S,
                          pbft_vc_delay=HEAVY_PBFT_VC_DELAY_S)


@dataclass(frozen=True)
class HeavyTimeline:
    """One heavy-tail Family-B timeline (one `network_phase_id`).

    Same surface the T46 runners + clip read (`name`, `e_delay_s`,
    `ffg_slot_duration_s`, `phases()`), plus a `p_drop` carried into the
    single phase. `delay-heavy-tail` (p_drop=0) is the loss-free control;
    the three `delay-heavy-tail-loss-p*` timelines reuse the same Pareto
    distribution under a non-zero per-phase Bernoulli drop.
    """
    name: str
    delay: DelayDist
    e_delay_s: float
    ffg_slot_duration_s: float
    p_drop: float

    def phases(self) -> tuple[Phase, ...]:
        return (Phase(0.0, float("inf"), self.delay, p_drop=self.p_drop),)


def _heavy_delay() -> DelayDist:
    return DelayDist("heavy_tail", {"scale": HEAVY_DELAY_SCALE_S,
                                    "shape": HEAVY_DELAY_SHAPE})


# The control (p_drop=0) FIRST so it is the natural denominator reference.
HEAVY_TIMELINES: tuple[HeavyTimeline, ...] = (
    HeavyTimeline("delay-heavy-tail", _heavy_delay(), HEAVY_E_DELAY_S,
                  HEAVY_FFG_SLOT_DURATION_S, p_drop=0.0),
    *(HeavyTimeline(f"delay-heavy-tail-loss-p{int(round(p * 100)):02d}",
                    _heavy_delay(), HEAVY_E_DELAY_S,
                    HEAVY_FFG_SLOT_DURATION_S, p_drop=p)
      for p in P_DROP_LEVELS),
)

# The p_drop=0 control timeline name — the finalization_rate denominator.
CONTROL_TIMELINE = "delay-heavy-tail"

# Snowman n=25 heavy is the cost wall (~20 min, ~5 GB resident per cell;
# poll volume, not window — Backlog item (e)). Per the human 2026-06-12
# decision it runs at a REDUCED seed count while every other (protocol, n)
# keeps the full 20. The control AND loss timelines share this same reduced
# set, so every Snowman n=25 loss cell still has its finalization_rate
# control sibling at the same seed.
SNOWMAN_N25_SEEDS: tuple[int, ...] = tuple(range(8))


def _seeds_for(protocol: str, n: int,
               seeds: tuple[int, ...]) -> tuple[int, ...]:
    """The seed subset for one (protocol, n) class. Snowman n=25 is capped at
    SNOWMAN_N25_SEEDS; everything else uses the full set. Intersecting with
    `seeds` keeps `--smoke` (1 seed) coherent."""
    if protocol == "snowman" and n == 25:
        cap = set(SNOWMAN_N25_SEEDS)
        return tuple(s for s in seeds if s in cap)
    return seeds

# Extra columns appended after the T46 5-column Family-B block.
_HEAVY_EXTRA_COLUMNS: tuple[str, ...] = (
    "p_drop",              # per-phase Bernoulli drop probability
    "finalized_instances", # distinct instances finalized in [0, W]
    "view_change_count",   # PBFT view-changes in [0, W] (0 for FFG/Snowman)
    "finalization_rate",   # finalized / control's finalized (post-pass)
)

_ALL_HEAVY_COLUMNS = list(COLUMN_ORDER) + list(_DELAY_COLUMNS) \
    + list(_HEAVY_EXTRA_COLUMNS)


def _heavy_timeline_by_name(tl_name: str) -> HeavyTimeline:
    return next(t for t in HEAVY_TIMELINES if t.name == tl_name)


def _build_heavy_row(records: list[EventRecord], result: RunResult,
                     meta: ScenarioMeta, timeline: HeavyTimeline,
                     clipped_fraction: float,
                     commit_hash: str) -> dict[str, object]:
    """Project one clipped heavy run to a row: the T40 generic + reducer
    columns, the T46 Family-B annotation block, and the four T47 columns.
    `finalization_rate` is set to NaN here and filled by the post-pass."""
    row = _generic_cols(records, result, meta, commit_hash=commit_hash)
    row.update(_REDUCERS[meta.protocol](records, result, meta))
    _window_denominator_fix(row, records, meta)

    # T46 Family-B annotation block (run_horizon is the HEAVY horizon).
    row["network_phase_id"] = timeline.name
    row["e_delay_ms"] = timeline.e_delay_s * 1000.0
    row["slot_duration_ms"] = meta.interval * 1000.0
    row["clipped_fraction"] = clipped_fraction
    row["run_horizon_s"] = HEAVY_T_MAX

    # T47 columns. `records` are already clipped to [0, W], so both counts
    # are window-bounded.
    decided = [r for r in records if r.event_type == "decided"]
    finalized_instances = len({r.fields.get("instance_id") for r in decided})
    view_changes = sum(1 for r in records
                       if r.event_type == PBFT_VIEW_CHANGE)
    row["p_drop"] = timeline.p_drop
    row["finalized_instances"] = finalized_instances
    row["view_change_count"] = view_changes
    row["finalization_rate"] = float("nan")          # post-pass fills this
    return row


# --- Driver adapter (module-level for the `spawn` Pool). -----------------

_HEAVY_SCHEMA_TAG = (tuple(COLUMN_ORDER), _DELAY_COLUMNS,
                     _HEAVY_EXTRA_COLUMNS)


def _cell_key(cell: tuple) -> str:
    proto, tl_name, n, seed = cell
    return f"{proto}__{tl_name}__n{n}__seed{seed:02d}"


def _phase_canon(ph) -> tuple:
    return (ph.t_start, ph.t_end, ph.delay.kind,
            tuple(sorted(ph.delay.params.items())), ph.p_drop,
            repr(ph.partitions))


def _param_fingerprint(cell: tuple) -> str:
    """blake2b over the cell's canonicalized config. Canonicalizes over the
    timeline's phase tuple (delay kind/params, boundaries, p_drop) plus
    (protocol, n, HEAVY_T_MAX, schema_tag). The p_drop level enters the
    hash, so each loss level fingerprints distinctly."""
    proto, tl_name, n, seed = cell
    tl = _heavy_timeline_by_name(tl_name)
    canon = repr((proto, n, tl.name,
                  tuple(_phase_canon(ph) for ph in tl.phases()),
                  HEAVY_T_MAX, _HEAVY_SCHEMA_TAG))
    return hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()


def _run_cell(cell: tuple, run_constants: dict) -> dict[str, object]:
    """Pure per-cell row builder: heavy runner -> clip -> heavy row. The
    `commit_hash` is threaded in from run_constants (resolved once in the
    parent). `finalization_rate` is filled by the post-grid pass."""
    proto, tl_name, n, seed = cell
    timeline = _heavy_timeline_by_name(tl_name)
    records, result, meta = RUNNERS[proto](timeline, n, seed, HEAVY_CALIB)
    kept, stats = clip_records(records, HEAVY_WINDOW_S,
                               HEAVY_ONE_ROUND_S[proto])
    return _build_heavy_row(kept, result, meta, timeline,
                            stats.clipped_fraction,
                            run_constants["commit_hash"])


def _finalization_rates(rows: list[dict[str, object]]) -> None:
    """Fill each row's `finalization_rate` IN PLACE (post-grid pass).

    For a control (p_drop=0) row, the rate is 1.0 by definition. For a loss
    row, the rate is `finalized_instances` over the matched control row's
    `finalized_instances` at the same (protocol, n, seed), clamped to
    [0, 1]; NaN if the control finalized nothing (rate undefined) or the
    control row is absent from this collection (e.g. a p_drop-only subset).
    """
    control: dict[tuple, int] = {
        (r["protocol"], r["n"], r["seed"]): r["finalized_instances"]
        for r in rows if r["network_phase_id"] == CONTROL_TIMELINE
    }
    for r in rows:
        if r["network_phase_id"] == CONTROL_TIMELINE:
            r["finalization_rate"] = 1.0
            continue
        denom = control.get((r["protocol"], r["n"], r["seed"]))
        if denom is None or denom <= 0:
            r["finalization_rate"] = float("nan")
        else:
            r["finalization_rate"] = min(1.0,
                                         r["finalized_instances"] / denom)


def _is_heavy_cell(cell: tuple) -> bool:
    """The memory-heavy cell class: Snowman n≥25. One such cell materializes
    ~20–30 M EventRecords (~5 GB resident) — running two concurrently OOM'd a
    16 GB machine (the T47 jobs=2 failure). `run_grid_tiered` runs this class
    at `--heavy-jobs` (default 1) while everything else uses `--jobs`. The
    proper O(1)-memory fix is the streaming reducer (TASKS.md Backlog item
    (e) / the T47 follow-up); this scheduler bounds peak memory meanwhile."""
    proto, _tl, n, _seed = cell
    return proto == "snowman" and int(n) >= 25


def _build_cells(seeds: tuple[int, ...],
                 skip_snowman_n25: bool) -> list[tuple]:
    """The cell list, honouring the per-(protocol, n) seed policy and the
    optional two-pass skip of the memory-heavy Snowman n=25 block."""
    cells = []
    for p in _PROTOCOLS:
        for tl in HEAVY_TIMELINES:
            for n in cfg.N_VALUES:
                if skip_snowman_n25 and p == "snowman" and n == 25:
                    continue
                for s in _seeds_for(p, n, seeds):
                    cells.append((p, tl.name, n, s))
    return cells


def run_sweep(seeds: tuple[int, ...] | None = None, *,
              out: Path = _OUT, jobs: int = 1, heavy_jobs: int = 1,
              fresh: bool = False, skip_snowman_n25: bool = False,
              progress_stream=None,
              ) -> tuple[list[dict[str, object]], float]:
    """Execute the heavy sweep via the memory-aware resumable/parallel driver.
    Returns `(rows, worst_clipped_fraction)`; `finalization_rate` is filled by
    the post-grid pass before return.

    Memory-aware scheduling (`run_grid_tiered`): the light cells run at `jobs`
    and the Snowman n≥25 class (`_is_heavy_cell`, ~5 GB each) at `heavy_jobs`
    (default 1, one at a time), so peak memory can never exceed the 16 GB the
    jobs=2 sweep blew past. Output is byte-identical to a single `run_grid` —
    tiering changes only scheduling. The `--skip-snowman-n25` two-pass flag is
    still honoured for fully manual control, but is no longer needed: one
    `--jobs N --heavy-jobs 1` run is now OOM-safe by construction.

    Checkpoints live under `<out_dir>/.sweep_heavy` (never colliding with the
    T46 `.sweep`); `commit_hash` is resolved once in the parent.
    """
    seeds = cfg.SEEDS if seeds is None else seeds
    commit_hash = _resolve_commit_hash()
    cells = _build_cells(seeds, skip_snowman_n25)
    rows = run_grid_tiered(cells, _run_cell, _cell_key,
                           checkpoint_dir=Path(out).parent / ".sweep_heavy",
                           run_constants={"commit_hash": commit_hash},
                           param_fingerprint=_param_fingerprint,
                           is_heavy=_is_heavy_cell,
                           jobs=jobs, heavy_jobs=heavy_jobs,
                           fresh=fresh, progress_stream=progress_stream)
    _finalization_rates(rows)
    worst = max((r["clipped_fraction"] for r in rows), default=0.0)
    return rows, worst


def write_csv(rows: list[dict[str, object]], path: Path = _OUT) -> None:
    """Write rows in COLUMN_ORDER + the Family-B + T47 columns, sorted
    deterministically by (protocol, n, network_phase_id, seed)."""
    rows = sorted(rows, key=lambda r: (r["protocol"], r["n"],
                                       r["network_phase_id"], r["seed"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=_ALL_HEAVY_COLUMNS,
                                extrasaction="raise")
        writer.writeheader()
        for row in rows:
            formatted = _format_row({k: row[k] for k in COLUMN_ORDER})
            for col in _DELAY_COLUMNS:
                v = row[col]
                if col == "clipped_fraction":
                    formatted[col] = f"{v:.6f}"
                elif isinstance(v, float):
                    formatted[col] = f"{v:.3f}"
                else:
                    formatted[col] = str(v)
            formatted["p_drop"] = f"{row['p_drop']:.6f}"
            formatted["finalized_instances"] = str(row["finalized_instances"])
            formatted["view_change_count"] = str(row["view_change_count"])
            formatted["finalization_rate"] = f"{row['finalization_rate']:.6f}"
            writer.writerow(formatted)


def _preflight_estimate(seeds: tuple[int, ...], jobs: int, stream,
                        skip_snowman_n25: bool = False) -> None:
    """Pre-flight wall-clock estimate: time one cell per protocol at the
    smallest n on the control timeline, project to the full grid. Rough
    (smallest-n sample under-counts the Snowman n=25 tier); stderr only."""
    commit_hash = _resolve_commit_hash()
    n0 = min(cfg.N_VALUES)
    samples = [(p, CONTROL_TIMELINE, n0, seeds[0]) for p in _PROTOCOLS]
    timings = estimate_runtime(samples, _run_cell,
                               {"commit_hash": commit_hash})
    cells = _build_cells(seeds, skip_snowman_n25)
    total = 0.0
    for (proto, _, _, _), sec in timings.items():
        n_cells = sum(1 for c in cells if c[0] == proto)
        proj = n_cells * sec
        total += proj
        stream.write(f"[estimate] {proto}: ~{sec:.1f}s/cell (n={n0}) "
                     f"× {n_cells} cells ≈ {proj / 60:.1f} min "
                     f"(rough — Snowman n=25 is far costlier than the n={n0} "
                     f"sample)\n")
    eff = total / max(1, jobs)
    stream.write(f"[estimate] total ≈ {total / 60:.1f} min sequential, "
                 f"~{eff / 60:.1f} min at jobs={jobs} "
                 f"(rough, smallest-n sample, from scratch)\n")
    stream.flush()


def _probe(stream) -> None:
    """Calibration probe: one seed per (protocol, control-timeline, n=10),
    print first-decision latency + clip fraction + PBFT view-change count, so
    the HEAVY_ONE_ROUND_S / window / vc-delay constants can be tuned before
    the full sweep commits. Does not write the dataset."""
    n0 = min(cfg.N_VALUES)
    stream.write(f"[probe] heavy-tail control, n={n0}, seed 0 "
                 f"(W={HEAVY_WINDOW_S:.0f}s, horizon={HEAVY_T_MAX:.0f}s):\n")
    tl = _heavy_timeline_by_name(CONTROL_TIMELINE)
    for proto in _PROTOCOLS:
        records, result, meta = RUNNERS[proto](tl, n0, 0, HEAVY_CALIB)
        decided = [r for r in records if r.event_type == "decided"]
        first = min((r.t for r in decided), default=float("nan"))
        kept, stats = clip_records(records, HEAVY_WINDOW_S,
                                   HEAVY_ONE_ROUND_S[proto])
        vc = sum(1 for r in records if r.event_type == PBFT_VIEW_CHANGE)
        kept_dec = len({r.fields.get("instance_id") for r in kept
                        if r.event_type == "decided"})
        stream.write(
            f"  {proto:11s} first_decision={first:7.2f}s  "
            f"clipped={stats.clipped_fraction * 100:5.2f}%  "
            f"in_window_finalized={kept_dec:4d}  view_changes={vc}\n")
    stream.flush()


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Family B HEAVY delay + loss sweep (T47).")
    ap.add_argument("--smoke", action="store_true",
                    help="1 seed only (fast sanity, not the real dataset).")
    ap.add_argument("--probe", action="store_true",
                    help="calibration probe only (no dataset written).")
    ap.add_argument("--out", default=str(_OUT), help="output CSV path.")
    ap.add_argument("--jobs", type=int, default=1,
                    help="parallel workers for the LIGHT cell class (default 1).")
    ap.add_argument("--heavy-jobs", type=int, default=1,
                    help="parallel workers for the memory-heavy Snowman n>=25 "
                         "class (default 1; keep low — each cell is ~5 GB).")
    ap.add_argument("--fresh", action="store_true",
                    help="clear the checkpoint dir first (recompute all).")
    ap.add_argument("--skip-snowman-n25", action="store_true",
                    help="drop the memory-heavy Snowman n=25 block (run the "
                         "cheap ~90%% at high --jobs; a second resumable pass "
                         "without this flag fills it at low --jobs).")
    args = ap.parse_args()

    if args.probe:
        _probe(sys.stderr)
        return

    seeds = (0,) if args.smoke else cfg.SEEDS
    out = Path(args.out)
    _preflight_estimate(seeds, args.jobs, sys.stderr,
                        skip_snowman_n25=args.skip_snowman_n25)
    rows, worst = run_sweep(seeds=seeds, out=out, jobs=args.jobs,
                            heavy_jobs=args.heavy_jobs,
                            fresh=args.fresh,
                            skip_snowman_n25=args.skip_snowman_n25,
                            progress_stream=sys.stderr)
    write_csv(rows, out)
    print(f"wrote {len(rows)} rows -> {out}")
    print(f"worst clipped_fraction = {worst*100:.2f}%  "
          f"(reported, not guarded — Option-B W cap)")


if __name__ == "__main__":
    main()
