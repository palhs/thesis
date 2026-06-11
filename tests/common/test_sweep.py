"""Driver-level tests for the grid-agnostic sweep harness (T46.1).

These exercise `common.sweep.run_grid` against a FAKE pure `run_cell` (no
protocol code), so the driver's determinism / resume / parallel logic is
tested in isolation from the delay adapter. The delay-side induction
witnesses live in tests/delay/test_sweep_equivalence.py.

All fixtures are MODULE-LEVEL functions + plain-tuple cells so they are
picklable under the macOS `spawn` start method (the jobs>1 path).
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path

from common.sweep import run_grid, estimate_runtime, SweepCellError


# --- Module-level fixtures (picklable under spawn). ----------------------

def _fake_run_cell(cell, run_constants):
    # Pure: the row is a deterministic function of the cell + constants.
    proto, n, seed = cell
    return {"protocol": proto, "n": n, "seed": seed,
            "val": f"{proto}-{n}-{seed}", "hash": run_constants["commit_hash"]}


def _key(cell):
    proto, n, seed = cell
    return f"{proto}__n{n}__seed{seed:02d}"


def _fp(cell):
    return "fp-v1"   # constant fingerprint for the fake


def _tagging_run_cell(cell, run_constants):
    # Tags the row "computed" so a test can tell a recompute from a reused
    # (pre-written) sidecar row, which is tagged "reused".
    proto, n, seed = cell
    return {"protocol": proto, "n": n, "seed": seed, "source": "computed"}


def _raise_if_seed0(cell, run_constants):
    # Raises iff invoked for a seed-0 cell — used to prove a pre-written
    # seed-0 sidecar is SKIPPED (never recomputed) while a seed-1 cell runs.
    proto, n, seed = cell
    if seed == 0:
        raise AssertionError(f"run_cell must not be invoked for {cell}")
    return {"protocol": proto, "n": n, "seed": seed, "source": "computed"}


def _raise_on_seed3(cell, run_constants):
    # Raises for exactly one cell (seed 3) — drives the parallel branch's
    # continue-then-report policy: the other cells must still complete.
    proto, n, seed = cell
    if seed == 3:
        raise ValueError("boom: seed 3")
    return {"protocol": proto, "n": n, "seed": seed, "source": "computed"}


def _write_raw_sidecar(checkpoint_dir: Path, key: str, payload: dict) -> None:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (checkpoint_dir / f"{key}.json").write_text(json.dumps(payload))


def _valid_payload(row, commit_hash="H", fp="fp-v1"):
    return {"schema_version": 1, "commit_hash": commit_hash,
            "param_fingerprint": fp, "row": row}


class TestCollectOrder(unittest.TestCase):
    def test_rows_sorted_by_cell_key_regardless_of_input_order(self):
        cells = [("b", 7, 1), ("a", 4, 0), ("b", 7, 0)]
        with tempfile.TemporaryDirectory() as d:
            rows = run_grid(cells, _fake_run_cell, _key,
                            checkpoint_dir=Path(d) / ".sweep",
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=1)
        keys = [_key((r["protocol"], r["n"], r["seed"])) for r in rows]
        self.assertEqual(keys, sorted(keys))


class TestResumeSkip(unittest.TestCase):
    def test_valid_sidecar_is_skipped_pending_cell_runs(self):
        # Pre-write a valid sidecar for the seed-0 cell tagged "reused";
        # leave the seed-1 cell pending. `_raise_if_seed0` would raise if
        # the seed-0 cell were recomputed.
        cells = [("a", 4, 0), ("a", 4, 1)]
        with tempfile.TemporaryDirectory() as d:
            ckpt = Path(d) / ".sweep"
            _write_raw_sidecar(ckpt, _key(("a", 4, 0)), _valid_payload(
                {"protocol": "a", "n": 4, "seed": 0, "source": "reused"}))
            rows = run_grid(cells, _raise_if_seed0, _key,
                            checkpoint_dir=ckpt,
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=1)
        by_seed = {r["seed"]: r["source"] for r in rows}
        self.assertEqual(by_seed[0], "reused")     # skipped, not recomputed
        self.assertEqual(by_seed[1], "computed")   # pending cell ran


class TestStaleGuards(unittest.TestCase):
    def test_stale_commit_hash_recomputed(self):
        cells = [("a", 4, 0)]
        with tempfile.TemporaryDirectory() as d:
            ckpt = Path(d) / ".sweep"
            _write_raw_sidecar(ckpt, _key(("a", 4, 0)), _valid_payload(
                {"protocol": "a", "n": 4, "seed": 0, "source": "reused"},
                commit_hash="OLDHASH"))
            rows = run_grid(cells, _tagging_run_cell, _key,
                            checkpoint_dir=ckpt,
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=1)
        self.assertEqual(rows[0]["source"], "computed")  # stale -> recompute

    def test_stale_param_fingerprint_recomputed(self):
        cells = [("a", 4, 0)]
        with tempfile.TemporaryDirectory() as d:
            ckpt = Path(d) / ".sweep"
            _write_raw_sidecar(ckpt, _key(("a", 4, 0)), _valid_payload(
                {"protocol": "a", "n": 4, "seed": 0, "source": "reused"},
                fp="OLD-FP"))
            rows = run_grid(cells, _tagging_run_cell, _key,
                            checkpoint_dir=ckpt,
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=1)
        self.assertEqual(rows[0]["source"], "computed")  # stale -> recompute


class TestAtomicWrite(unittest.TestCase):
    def test_no_tmp_left_and_sidecar_well_formed(self):
        cells = [("a", 4, 0)]
        with tempfile.TemporaryDirectory() as d:
            ckpt = Path(d) / ".sweep"
            run_grid(cells, _tagging_run_cell, _key,
                     checkpoint_dir=ckpt,
                     run_constants={"commit_hash": "H"},
                     param_fingerprint=_fp, jobs=1)
            self.assertEqual(list(ckpt.glob("*.tmp")), [])   # no torn temp
            sidecar = ckpt / f"{_key(('a', 4, 0))}.json"
            payload = json.loads(sidecar.read_text())
            self.assertEqual(set(payload),
                             {"schema_version", "commit_hash",
                              "param_fingerprint", "row"})


class TestFresh(unittest.TestCase):
    def test_fresh_clears_existing_sidecars(self):
        cells = [("a", 4, 0)]
        with tempfile.TemporaryDirectory() as d:
            ckpt = Path(d) / ".sweep"
            _write_raw_sidecar(ckpt, _key(("a", 4, 0)), _valid_payload(
                {"protocol": "a", "n": 4, "seed": 0, "source": "reused"}))
            rows = run_grid(cells, _tagging_run_cell, _key,
                            checkpoint_dir=ckpt,
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=1, fresh=True)
        # Even though the sidecar matched, --fresh cleared it -> recompute.
        self.assertEqual(rows[0]["source"], "computed")


class TestJobsEquivalence(unittest.TestCase):
    def test_jobs1_equals_jobsN(self):
        # Byte-identical collected rows regardless of parallelism. (Fixtures
        # are module-level -> picklable under the macOS spawn start method.)
        cells = [("a", n, s) for n in (4, 7) for s in range(6)]

        def run(jobs, d):
            return run_grid(cells, _fake_run_cell, _key,
                            checkpoint_dir=Path(d) / ".sweep",
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=jobs)

        with tempfile.TemporaryDirectory() as d1, \
                tempfile.TemporaryDirectory() as d2:
            self.assertEqual(run(1, d1), run(4, d2))


class TestJobsClamp(unittest.TestCase):
    def test_jobs_over_cpu_and_grid_does_not_error(self):
        # jobs far above the grid size clamps cleanly and equals jobs=1.
        cells = [("a", 4, s) for s in range(3)]

        def run(jobs, d):
            return run_grid(cells, _fake_run_cell, _key,
                            checkpoint_dir=Path(d) / ".sweep",
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=jobs)

        with tempfile.TemporaryDirectory() as d1, \
                tempfile.TemporaryDirectory() as d2:
            self.assertEqual(run(1, d1), run(999, d2))


class TestWorkerException(unittest.TestCase):
    def test_continue_then_report_other_sidecars_exist_resume_completes(self):
        # One cell raises; the parallel branch finishes the rest, then
        # raises SweepCellError naming the failure. A follow-up resume run
        # with a non-raising run_cell completes the grid.
        cells = [("a", 4, s) for s in range(4)]   # seed 3 raises
        with tempfile.TemporaryDirectory() as d:
            ckpt = Path(d) / ".sweep"
            with self.assertRaises(SweepCellError) as ctx:
                run_grid(cells, _raise_on_seed3, _key, checkpoint_dir=ckpt,
                         run_constants={"commit_hash": "H"},
                         param_fingerprint=_fp, jobs=2)
            failed = [c for c, _ in ctx.exception.failures]
            self.assertIn(("a", 4, 3), failed)
            # Every non-failing cell durably wrote its sidecar.
            for s in (0, 1, 2):
                self.assertTrue(
                    (ckpt / f"{_key(('a', 4, s))}.json").exists())
            self.assertFalse((ckpt / f"{_key(('a', 4, 3))}.json").exists())
            # Resume (non-raising) retries only the missing cell -> 4 rows.
            rows = run_grid(cells, _tagging_run_cell, _key,
                            checkpoint_dir=ckpt,
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=2)
            self.assertEqual(len(rows), 4)


class TestProgress(unittest.TestCase):
    def test_one_line_per_completed_cell_return_unchanged(self):
        cells = [("a", 4, s) for s in range(3)]
        stream = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            rows = run_grid(cells, _fake_run_cell, _key,
                            checkpoint_dir=Path(d) / ".sweep",
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=1,
                            progress_stream=stream)
        lines = [ln for ln in stream.getvalue().splitlines() if ln.strip()]
        self.assertEqual(len(lines), 3)          # one per completed cell
        # Machine-readable return value is unchanged by progress.
        self.assertEqual([r["seed"] for r in rows], [0, 1, 2])
        for ln in lines:
            self.assertIn("/3)", ln)             # (done/total) counter


class TestNoTimingLeak(unittest.TestCase):
    def test_timing_never_enters_row_or_sidecar(self):
        # With progress on, the returned rows and the sidecar JSON must
        # carry exactly their data columns — no perf_counter/timing field.
        cells = [("a", 4, s) for s in range(3)]
        stream = io.StringIO()
        with tempfile.TemporaryDirectory() as d:
            ckpt = Path(d) / ".sweep"
            rows = run_grid(cells, _fake_run_cell, _key, checkpoint_dir=ckpt,
                            run_constants={"commit_hash": "H"},
                            param_fingerprint=_fp, jobs=1,
                            progress_stream=stream)
            for r in rows:
                self.assertEqual(set(r),
                                 {"protocol", "n", "seed", "val", "hash"})
            for sc in ckpt.glob("*.json"):
                payload = json.loads(sc.read_text())
                self.assertEqual(set(payload),
                                 {"schema_version", "commit_hash",
                                  "param_fingerprint", "row"})
                self.assertEqual(set(payload["row"]),
                                 {"protocol", "n", "seed", "val", "hash"})


class TestEstimate(unittest.TestCase):
    def test_times_each_sample_writes_no_sidecar(self):
        samples = [("a", 4, 0), ("b", 7, 0)]
        timings = estimate_runtime(samples, _fake_run_cell,
                                   {"commit_hash": "H"})
        self.assertEqual(set(timings), set(samples))
        for v in timings.values():
            self.assertGreaterEqual(v, 0.0)


if __name__ == "__main__":
    unittest.main()
