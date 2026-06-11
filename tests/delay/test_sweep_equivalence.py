"""The induction-over-the-grid witnesses for the resumable/parallel sweep
harness (T46.1).

These mechanize the equivalence argument written up in
wiki/experiments/2026-06-12_sweep-harness.md:

  - PER-CELL INVARIANT: one cell -> one row by a pure deterministic
    f(cell, run_constants); the same cell run twice is byte-identical.
  - BASE CASE: one cell's row is identical across {jobs=1, jobs>1,
    forced-resume}; and a committed T46 cell reproduces byte-for-byte
    modulo the provenance `commit_hash` column.
  - INDUCTIVE STEP: a k-cell grid mixing two real protocols + the three
    witness cells is byte-identical across {jobs=1, jobs=4, kill-resume}.

The witness timelines exercise the parameter shapes T47 introduces —
`heavy_tail` (Pareto) delay, `p_drop > 0` packet loss, and a 2-phase
timeline that crosses a `PhaseAdvance` rollover — so the induction covers
T47 without running T47.

Witness timelines are TEST-LOCAL (do not touch cfg.TIMELINES). The witness
adapter (`_w_run_cell` / `_w_cell_key` / `_w_param_fingerprint`) mirrors the
production `delay.sweep` adapter EXACTLY except for the timeline registry —
the only test-local part is a dict lookup, so the witnesses faithfully drive
the same `run_grid` + `_build_row` + `clip_records` + `RUNNERS` pipeline that
production uses. Everything is MODULE-LEVEL so it pickles under `spawn`.
"""
from __future__ import annotations

import csv
import hashlib
import math
import re
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from common import run_grid
from network import DelayDist, Phase
from output.schema import COLUMN_ORDER

from delay import config as cfg
from delay.clip import clip_records
from delay.runners import RUNNERS
from delay.sweep import (_DELAY_COLUMNS, _SCHEMA_TAG, _build_row, write_csv)
from delay.sweep import _cell_key as _prod_cell_key
from delay.sweep import _param_fingerprint as _prod_param_fingerprint
from delay.sweep import _run_cell as _prod_run_cell


# --- Test-local witness timelines (T47's param shapes, expressible today). -

@dataclass(frozen=True)
class _WTimeline:
    """A test-local timeline that can express multi-phase / p_drop, which
    cfg.Timeline (single-phase, p_drop=0) cannot. Exposes the same surface
    the runners + `_build_row` read: name, e_delay_s, ffg_slot_duration_s,
    phases()."""
    name: str
    phase_tuple: tuple
    e_delay_s: float
    ffg_slot_duration_s: float

    def phases(self) -> tuple:
        return self.phase_tuple


# w1: single-phase heavy_tail (Pareto). w2: single-phase p_drop>0 loss.
# w3: 2-phase (loss -> heavy_tail) crossing a PhaseAdvance at t=240 within
# the W+buffer=528 s horizon — without the boundary the induction has a hole.
_W1 = _WTimeline(
    "w-heavy-tail",
    (Phase(0.0, math.inf, DelayDist("heavy_tail", {"scale": 0.2, "shape": 2.0})),),
    e_delay_s=0.4, ffg_slot_duration_s=1.2)
_W2 = _WTimeline(
    "w-loss",
    (Phase(0.0, math.inf, DelayDist("uniform", {"low": 0.1, "high": 0.5}),
           p_drop=0.1),),
    e_delay_s=0.3, ffg_slot_duration_s=1.2)
_W3 = _WTimeline(
    "w-2phase",
    (Phase(0.0, 240.0, DelayDist("uniform", {"low": 0.1, "high": 0.5}),
           p_drop=0.05),
     Phase(240.0, math.inf, DelayDist("heavy_tail", {"scale": 0.2, "shape": 2.0}))),
    e_delay_s=0.35, ffg_slot_duration_s=1.2)

_WITNESS_TIMELINES = (_W1, _W2, _W3)

# Unified registry: real cfg timelines + the witnesses. The witness adapter
# resolves either, so a single run_grid call can mix real + witness cells.
_ALL_TIMELINES = {t.name: t for t in (*cfg.TIMELINES, *_WITNESS_TIMELINES)}


# --- Witness adapter (mirrors delay.sweep, but over _ALL_TIMELINES). ------

def _w_timeline_by_name(tl_name: str):
    return _ALL_TIMELINES[tl_name]


def _w_cell_key(cell: tuple) -> str:
    proto, tl_name, n, seed = cell
    return f"{proto}__{tl_name}__n{n}__seed{seed:02d}"


def _w_phase_canon(ph) -> tuple:
    return (ph.t_start, ph.t_end, ph.delay.kind,
            tuple(sorted(ph.delay.params.items())), ph.p_drop,
            repr(ph.partitions))


def _w_param_fingerprint(cell: tuple) -> str:
    proto, tl_name, n, seed = cell
    tl = _w_timeline_by_name(tl_name)
    canon = repr((proto, n, tl.name,
                  tuple(_w_phase_canon(ph) for ph in tl.phases()),
                  cfg.T_MAX, _SCHEMA_TAG))
    return hashlib.blake2b(canon.encode(), digest_size=16).hexdigest()


def _w_run_cell(cell: tuple, run_constants: dict) -> dict:
    proto, tl_name, n, seed = cell
    tl = _w_timeline_by_name(tl_name)
    records, result, meta = RUNNERS[proto](tl, n, seed)
    kept, stats = clip_records(records, cfg.WINDOW_S, cfg.ONE_ROUND_S[proto])
    return _build_row(kept, result, meta, tl, stats.clipped_fraction,
                      run_constants["commit_hash"])


# --- Helpers. ------------------------------------------------------------

def _witness_grid_csv(cells, jobs, ckpt_dir: Path, csv_path: Path,
                      commit_hash="WITNESS") -> bytes:
    """Run a grid through the witness adapter, write its CSV, return bytes."""
    rows = run_grid(cells, _w_run_cell, _w_cell_key,
                    checkpoint_dir=ckpt_dir,
                    run_constants={"commit_hash": commit_hash},
                    param_fingerprint=_w_param_fingerprint, jobs=jobs)
    write_csv(rows, csv_path)
    return csv_path.read_bytes()


def _row_csv_bytes(rows, phase_id, csv_path: Path) -> bytes:
    """Write the single row with the given network_phase_id, return bytes."""
    one = [r for r in rows if r["network_phase_id"] == phase_id]
    write_csv(one, csv_path)
    return csv_path.read_bytes()


_COMMITTED = Path("results/delay/delay.csv")


def _read_committed_row(proto, n, phase_id, seed):
    with _COMMITTED.open() as fh:
        for row in csv.DictReader(fh):
            if (row["protocol"] == proto and int(row["n"]) == n
                    and row["network_phase_id"] == phase_id
                    and int(row["seed"]) == seed):
                return row
    return None


class TestPerCellInvariant(unittest.TestCase):
    def test_each_witness_cell_byte_identical_across_two_runs(self):
        # heavy_tail, p_drop>0, and the 2-phase rollover each map to a row
        # by a pure f(cell, run_constants): same cell twice -> same bytes.
        for w in _WITNESS_TIMELINES:
            cell = ("pbft", w.name, 10, 0)
            with tempfile.TemporaryDirectory() as d:
                d = Path(d)
                b1 = _witness_grid_csv([cell], 1, d / "a", d / "a.csv")
                b2 = _witness_grid_csv([cell], 1, d / "b", d / "b.csv")
            self.assertEqual(b1, b2, msg=w.name)


class TestBaseCase(unittest.TestCase):
    def test_one_cell_identical_across_jobs_and_forced_resume(self):
        # The 2-phase witness (the richest cell) under three execution modes.
        X = ("pbft", _W3.name, 10, 0)
        Y = ("pbft", _W1.name, 10, 0)     # companion for parallel / resume
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            # (i) jobs=1, single cell.
            b1 = _witness_grid_csv([X], 1, d / "s1", d / "a.csv")
            # (ii) jobs=2, 2-cell grid -> extract X's row.
            r2 = run_grid([X, Y], _w_run_cell, _w_cell_key,
                          checkpoint_dir=d / "s2",
                          run_constants={"commit_hash": "WITNESS"},
                          param_fingerprint=_w_param_fingerprint, jobs=2)
            b2 = _row_csv_bytes(r2, _W3.name, d / "b.csv")
            # (iii) forced resume: populate, delete X's sidecar, re-run.
            run_grid([X, Y], _w_run_cell, _w_cell_key, checkpoint_dir=d / "s3",
                     run_constants={"commit_hash": "WITNESS"},
                     param_fingerprint=_w_param_fingerprint, jobs=1)
            (d / "s3" / f"{_w_cell_key(X)}.json").unlink()
            r3 = run_grid([X, Y], _w_run_cell, _w_cell_key,
                          checkpoint_dir=d / "s3",
                          run_constants={"commit_hash": "WITNESS"},
                          param_fingerprint=_w_param_fingerprint, jobs=1)
            b3 = _row_csv_bytes(r3, _W3.name, d / "c.csv")
        self.assertEqual(b1, b2)
        self.assertEqual(b1, b3)

    def test_reproduces_committed_t46_row_modulo_commit_hash(self):
        # A real committed T46 cell recomputed on the new harness equals the
        # committed row on every column EXCEPT the provenance commit_hash.
        committed = _read_committed_row("pbft", 10, "delay-uniform", 0)
        self.assertIsNotNone(committed, "anchor row missing from delay.csv")
        cell = ("pbft", "delay-uniform", 10, 0)
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            rows = run_grid([cell], _prod_run_cell, _prod_cell_key,
                            checkpoint_dir=d / ".sweep",
                            run_constants={"commit_hash": "RECOMPUTE"},
                            param_fingerprint=_prod_param_fingerprint, jobs=1)
            write_csv(rows, d / "r.csv")
            with (d / "r.csv").open() as fh:
                recomputed = next(csv.DictReader(fh))
        for col in list(COLUMN_ORDER) + list(_DELAY_COLUMNS):
            if col == "commit_hash":
                continue
            self.assertEqual(recomputed[col], committed[col], msg=col)
        # commit_hash asserted well-formed separately (not compared).
        self.assertRegex(committed["commit_hash"], r"^[0-9a-f]{7,40}(-dirty)?$")
        self.assertEqual(recomputed["commit_hash"], "RECOMPUTE")


class TestInductiveStep(unittest.TestCase):
    def test_mixed_grid_identical_across_jobs1_jobs4_resume(self):
        # Two real protocols + the three witness cells. Adding cells /
        # parallelism / resume points cannot perturb a row, because cells
        # are independent and the collect-sort imposes a total order.
        cells = [
            ("pbft", "delay-uniform", 10, 0),         # real protocol 1
            ("casper-ffg", "delay-uniform", 10, 0),   # real protocol 2
            ("pbft", _W1.name, 10, 0),                # heavy_tail witness
            ("pbft", _W2.name, 10, 0),                # p_drop witness
            ("pbft", _W3.name, 10, 0),                # 2-phase witness
        ]
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            b1 = _witness_grid_csv(cells, 1, d / "m1", d / "m1.csv")
            b4 = _witness_grid_csv(cells, 4, d / "m4", d / "m4.csv")
            # kill-and-resume: complete a 2-cell prefix, then resume the grid.
            run_grid(cells[:2], _w_run_cell, _w_cell_key, checkpoint_dir=d / "mr",
                     run_constants={"commit_hash": "WITNESS"},
                     param_fingerprint=_w_param_fingerprint, jobs=1)
            br = _witness_grid_csv(cells, 1, d / "mr", d / "mr.csv")
        self.assertEqual(b1, b4)
        self.assertEqual(b1, br)


if __name__ == "__main__":
    unittest.main()
