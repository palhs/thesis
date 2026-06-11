"""Grid-agnostic, resumable, parallel sweep driver (T46.1).

`run_grid` runs a list of independent `cells` through a pure `run_cell`,
writing one fingerprinted sidecar per completed cell so a killed sweep
resumes and parallel workers never clobber. Output is byte-identical
across jobs / resume / completion order. Determinism contract:
wiki/concepts/sweep-harness.md. Design spec:
docs/superpowers/specs/2026-06-12-t46-1-sweep-harness-design.md

Picklability (spawn): every function crossing the multiprocessing.Pool
boundary — `run_cell`, `cell_key`, `param_fingerprint`, and the worker —
must be a MODULE-LEVEL function in the caller's module, and every `cell`
a plain picklable tuple. No closures / lambdas cross the process boundary
(required for the macOS-default `spawn` start method).
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import tempfile
import time
from pathlib import Path

_SCHEMA_VERSION = 1


class SweepCellError(RuntimeError):
    """Raised after a parallel sweep finishes when one or more cells failed.

    Continue-then-report policy (design spec §5): a failed cell simply has
    no sidecar, so a later resume retries it. `.failures` is a list of
    `(cell, message)` pairs."""

    def __init__(self, failures):
        self.failures = failures
        summary = ", ".join(f"{cell}: {msg}" for cell, msg in failures)
        super().__init__(f"{len(failures)} cell(s) failed: {summary}")


# Per-worker context for the spawn Pool. Populated by `_worker_init` in each
# child process; never crosses the boundary as a closure (plain module dict).
_WORKER_CTX: dict = {}


def _sidecar_path(checkpoint_dir: Path, key: str) -> Path:
    return checkpoint_dir / f"{key}.json"


def _write_sidecar(path: Path, payload: dict) -> None:
    """Atomic write: temp file in the SAME dir, then os.replace (same-fs
    rename, no EXDEV, no torn files). A crash leaves a complete sidecar
    or none."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as fh:
            json.dump(payload, fh, allow_nan=True, sort_keys=True)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _valid_sidecar(path: Path, commit_hash: str, fingerprint: str):
    """Return the stored payload iff it matches the current run, else None
    (treat as absent -> recompute). Guards against stale sidecars from a
    different commit or params (design spec §4, review B2)."""
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (ValueError, OSError):
        return None
    if (payload.get("schema_version") == _SCHEMA_VERSION
            and payload.get("commit_hash") == commit_hash
            and payload.get("param_fingerprint") == fingerprint):
        return payload
    return None


def _emit_progress(stream, key, dt, done, total) -> None:
    """One progress line per completed cell. `dt` is a perf_counter
    DURATION (stderr only) — it is never written into a row or sidecar."""
    if stream is not None:
        stream.write(f"{key}  [t={dt:.1f}s]  ({done}/{total})\n")
        stream.flush()


def run_grid(cells, run_cell, cell_key, *, checkpoint_dir, run_constants,
             param_fingerprint, jobs=1, fresh=False, progress_stream=None):
    """Run `cells` through `run_cell`, one fingerprinted sidecar per cell,
    and return the collected UNFORMATTED rows sorted by `cell_key`.

    Resume is the default: a cell whose sidecar already matches the current
    `commit_hash` + `param_fingerprint` + schema is skipped. `fresh=True`
    clears the checkpoint dir first. `jobs>1` runs via a spawn Pool.
    `progress_stream` (e.g. sys.stderr) gets one line per completed cell;
    timing there is a duration, never persisted.
    """
    checkpoint_dir = Path(checkpoint_dir)
    commit_hash = run_constants["commit_hash"]
    if fresh and checkpoint_dir.exists():
        for p in checkpoint_dir.glob("*.json"):
            p.unlink()
    # Resume-skip: only cells without a valid sidecar are pending.
    pending = []
    for cell in cells:
        key = cell_key(cell)
        if _valid_sidecar(_sidecar_path(checkpoint_dir, key),
                          commit_hash, param_fingerprint(cell)) is None:
            pending.append(cell)
    # Run pending cells. jobs is clamped to the cpu count and the pending
    # size so a huge --jobs on a tiny grid does not over-subscribe.
    n_jobs = max(1, min(int(jobs), os.cpu_count() or 1, len(pending) or 1))
    total = len(pending)
    if n_jobs == 1 or len(pending) <= 1:
        for i, cell in enumerate(pending, 1):
            t0 = time.perf_counter()
            key = _run_one(cell, run_cell, cell_key, checkpoint_dir,
                           run_constants, param_fingerprint)
            _emit_progress(progress_stream, key, time.perf_counter() - t0,
                           i, total)
    else:
        _run_parallel(pending, run_cell, cell_key, checkpoint_dir,
                      run_constants, param_fingerprint, n_jobs,
                      progress_stream)
    return _collect(cells, cell_key, checkpoint_dir)


def estimate_runtime(sample_cells, run_cell, run_constants) -> dict:
    """Pre-flight wall-clock estimate (item d): time one full run per
    sample cell and return `{cell: seconds}`. The caller multiplies these
    by the per-group pending counts and prints to stderr. Kept OUT of
    `run_grid` (single responsibility); writes no sidecar — timing is a
    duration, never persisted into a row.
    """
    timings: dict = {}
    for cell in sample_cells:
        t0 = time.perf_counter()
        run_cell(cell, run_constants)
        timings[cell] = time.perf_counter() - t0
    return timings


def _worker_init(run_cell, cell_key, checkpoint_dir, run_constants,
                 param_fingerprint) -> None:
    """Pool initializer: stash the per-cell call context in each child."""
    _WORKER_CTX.update(run_cell=run_cell, cell_key=cell_key,
                       checkpoint_dir=checkpoint_dir,
                       run_constants=run_constants,
                       param_fingerprint=param_fingerprint)


def _worker(cell):
    """Run one cell in a worker; never raises across the Pool boundary —
    failures are returned so the parent can apply continue-then-report.
    `dt` is a perf_counter duration for the parent's progress line only —
    it is not written into the sidecar (`_run_one` stores `row` alone)."""
    c = _WORKER_CTX
    t0 = time.perf_counter()
    try:
        key = _run_one(cell, c["run_cell"], c["cell_key"],
                       c["checkpoint_dir"], c["run_constants"],
                       c["param_fingerprint"])
        return (cell, key, None, time.perf_counter() - t0)
    except Exception as exc:                       # continue-then-report
        return (cell, None, f"{type(exc).__name__}: {exc}",
                time.perf_counter() - t0)


def _run_parallel(pending, run_cell, cell_key, checkpoint_dir, run_constants,
                  param_fingerprint, n_jobs, progress_stream=None) -> None:
    """multiprocessing.Pool over `pending` with imap_unordered(chunksize=1).
    Each worker writes its own sidecar (no shared writer, no lock). spawn
    start method (macOS default); pool.terminate() in finally tears workers
    down cleanly on Ctrl-C. Progress is emitted from this consumer loop as
    results resolve."""
    failures = []
    total = len(pending)
    done = 0
    ctx = mp.get_context("spawn")
    pool = ctx.Pool(n_jobs, initializer=_worker_init,
                    initargs=(run_cell, cell_key, checkpoint_dir,
                              run_constants, param_fingerprint))
    try:
        for cell, key, err, dt in pool.imap_unordered(_worker, pending,
                                                      chunksize=1):
            done += 1
            if err is not None:
                failures.append((cell, err))
            else:
                _emit_progress(progress_stream, key, dt, done, total)
        pool.close()
        pool.join()
    finally:
        pool.terminate()
    if failures:
        raise SweepCellError(failures)


def _run_one(cell, run_cell, cell_key, checkpoint_dir, run_constants,
             param_fingerprint) -> str:
    """Compute one cell's row and durably write its fingerprinted sidecar.
    Returns the cell_key (for progress)."""
    row = run_cell(cell, run_constants)
    payload = {"schema_version": _SCHEMA_VERSION,
               "commit_hash": run_constants["commit_hash"],
               "param_fingerprint": param_fingerprint(cell),
               "row": row}
    key = cell_key(cell)
    _write_sidecar(_sidecar_path(checkpoint_dir, key), payload)
    return key


def _collect(cells, cell_key, checkpoint_dir) -> list[dict]:
    """Read the sidecar of every requested cell, sort by `cell_key` (the
    total order), return the unformatted rows. Order-independent of run
    order — this is the canonical step the induction relies on."""
    keyed = []
    for cell in cells:
        key = cell_key(cell)
        payload = json.loads(_sidecar_path(checkpoint_dir, key).read_text())
        keyed.append((key, payload["row"]))
    keyed.sort(key=lambda kr: kr[0])
    return [row for _, row in keyed]
