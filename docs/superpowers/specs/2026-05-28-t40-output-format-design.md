# T40 — Unified Output Format: Design Spec

- **Task:** T40 (Engineer) — Unify output format across all algorithms; land
  the canonical `wiki/concepts/output-format.md` contract page and the
  `src/output/` subsystem that projects `(EventLogger.records, RunResult,
  ScenarioMeta)` triples to one CSV row per `(protocol, scenario, seed)`.
- **Branch:** `task/T38-snowman` (worktree continues on this branch by
  pickup-flow convention; final branch is the per-task branch the human
  retitles on push).
- **Date:** 2026-05-28.
- **Outcome (`TASKS.md`):** *"Common CSV: run_id, algorithm, n_validators,
  latency_ms, throughput, msg_count, success."* The 7-column sketch is the
  T35-local schema written by `src/pos/baseline.py` (Backlog 2026-05-25,
  raised by T35 itself) — it predates the cross-protocol asymmetries
  reconciled by T9.1 and `wiki/concepts/metric-reconciliation.md`. The
  **binding** column-set is the one pinned by
  `metric-reconciliation.md §T40 CSV schema implications`; T40 lands the
  wiki contract for the full schema and the writer for an in-scope subset.
- **Scope decisions (human, 2026-05-28):**
  - **Schema scope (Q1):** **minimal set + extension register** — the
    wiki page pins the full ~30-column schema (single source of truth, the
    bind for the L-W4 M1 fifteen forward-references); the writer today
    populates an 18-column subset and the wiki carries a `## Extension
    register` listing every column not yet live with its owning task.
  - **Row granularity (Q2):** **per-trial / long format** — one row per
    `(protocol, scenario, seed)` simulation run. T40 writes the per-trial
    file; T44 owns a separate `results/baseline_aggregated.csv` for means
    and CIs. Tidy-data convention.
  - **Reducer wiring (Q3):** **hybrid** — `src/output/csv.py` owns the
    generic columns every protocol shares and the writer composition; each
    `src/<protocol>/summarise.py` exports a pure-function reducer that
    returns only the protocol-specific columns. Adding NWT under T38.1 is
    one new `src/narwhal_tusk/summarise.py` + one entry in the dispatch
    table.
  - **Orchestration (Q4):** **single `src/output/baseline.py`** with a
    `__main__` entry point that imports each protocol's `SCENARIOS` +
    `run_scenario` and writes one `results/baseline.csv`. T35-local
    `results/pos/baseline.csv` is retired. Each protocol's scenarios are
    lifted out of its integration test file into a new
    `src/<protocol>/baseline.py` (POS already has one; PBFT and Snowman
    don't).
  - **Snowman `n=4` row policy:** **skip + sibling sanity CSV** — per
    `metric-reconciliation.md §Snowman parameter rescaling`, Snowman at
    `n=4` is the degenerate boundary (`α_c = K`, unanimity). The writer
    skips it from `results/baseline.csv` entirely; `snowman.summarise`
    exports a separate `sanity_row()` path that writes
    `results/snowman_n4_sanity.csv`. Downstream consumers (T44 aggregator,
    T48 plots, Chapter 4 tables) do not have to re-implement the
    exclusion.

This spec is the canonical reference for the T40 implementation plan
(`superpowers:writing-plans`). It consumes the W3 design contracts
[[concepts/event-log-schema]], [[concepts/runner]],
[[concepts/metric-reconciliation]], [[concepts/evaluation-metrics]],
[[concepts/reproducibility]] and rests on the
`src/common/runner.run_to_completion` seam from T39 and the
`config.factory.build_run()` seam from T27.

## 1. Scope and non-goals

### In scope

- **New wiki page `wiki/concepts/output-format.md`** — ~250 lines; 13
  sections (purpose, pipeline position, canonical schema table, today's
  subset, per-protocol derivation rules, NaN dispatch policy, Snowman
  `n=4` policy, row identity & ordering, CSV mechanics, determinism,
  extension register, cross-references, Revisions). Closes the 15 inbound
  forward-references the L-W4 M1 finding catalogues
  (`wiki/lint/2026-05-21_report.md`).
- **New `src/output/` package** — three modules:
  - `src/output/schema.py` — `ScenarioMeta` frozen dataclass +
    `COLUMN_ORDER` 18-column tuple (~40 LoC).
  - `src/output/csv.py` — `write_unified_csv(path, runs)` + the
    `_generic_cols` helper + the `_REDUCERS` dispatch table (~110 LoC).
  - `src/output/baseline.py` — `main()` orchestrator with `__main__` entry
    point (~50 LoC).
- **New per-protocol reducers** — one module per implemented protocol:
  - `src/pbft/summarise.py` (~50 LoC).
  - `src/pos/summarise.py` (~60 LoC; lifts the FFG epoch-finalisation
    logic from the old `_summarise`).
  - `src/snowman/summarise.py` (~70 LoC; also exports `sanity_row` for
    the `n=4` rescaling-boundary file).
- **New `src/pbft/baseline.py` + `src/snowman/baseline.py`** (~80 LoC
  each) — `SCENARIOS: tuple[ScenarioMeta, ...]` + `run_scenario(meta) ->
  (records, result, meta)`. Mirrors `src/pos/baseline.py`'s shape so the
  three protocols expose a uniform Python API the orchestrator composes
  against.
- **Harmonisation of `src/pos/baseline.py`** — delete `_summarise`,
  `write_baseline_csv`, `_COLUMNS`, `__main__`, the `csv` import; replace
  `_run_scenario` with `run_scenario(meta) -> (records, result, meta)`;
  re-shape `SCENARIOS` to `tuple[ScenarioMeta, ...]` preserving the
  `nonuniform` variant. Net ~80 LoC out, ~50 LoC in.
- **Harmonisation of three integration test files** —
  `tests/integration/test_pbft_baseline.py`,
  `tests/integration/test_pos_baseline.py`,
  `tests/integration/test_snowman_baseline.py` — replace the inline
  `_config / _factory / _run` helper trio with `from <protocol>.baseline
  import SCENARIOS, run_scenario`. Test assertions stay verbatim.
- **New tests** — five new test files, ~330 LoC total:
  - `tests/output/test_generic_cols.py` (~50 LoC).
  - `tests/output/test_csv.py` (~80 LoC; golden-file + collision +
    unknown-protocol).
  - `tests/output/test_baseline_e2e.py` (~80 LoC; byte-identical CSV).
  - `tests/pbft/test_summarise.py` (~50 LoC).
  - `tests/pos/test_summarise.py` (~60 LoC).
  - `tests/snowman/test_summarise.py` (~70 LoC; includes `sanity_row`
    test).
- **Two ## Revisions blocks** — on `wiki/concepts/event-log-schema.md`
  §CSV format (note the unified comparative CSV is now a sibling consumer
  of the same event substrate) and on `wiki/concepts/runner.md` §What's
  outside the runner (note the T40 CSV-output gap is now closed).
- **Wiki index + log updates** — new entry under `## Concepts` for
  `output-format`; one log entry per `docs/wiki-spec.md §Log format`.
- **`TASKS.md` edits** — flip T40 to `[?]` In Review on push; recompute
  the dashboard arithmetic; close the T35-sample-CSV reconciliation
  backlog item (append-resolved per the precedent set by T39's
  Cluster-A/Cluster-B closures).
- **One new experiment page** — `wiki/experiments/2026-05-28_unified-
  output.md` documenting the build-verification baseline of the unified
  writer + the canonical `results/baseline.csv` produced by `python3 -m
  output.baseline` (~80 lines, the standard experiment-page shape).
- **`Makefile` target** — new `test-output` target alongside the existing
  per-suite targets.
- **Repository artifact churn** — delete tracked `results/pos/baseline.csv`
  (T35-local); commit the new tracked `results/baseline.csv` and
  `results/snowman_n4_sanity.csv` as the canonical artifacts the
  experiment page references; `.gitignore` already covers
  `results/pos/baseline.csv`.

### Out of scope (deferred to their owning tasks)

- **Multi-seed sweeps and 95% CI computation** → T44. T40 writes one row
  per scenario at the project default `global_seed=42`; the `seed` column
  is constant today. T44 owns sweeping seeds and computing the aggregated
  file (`results/baseline_aggregated.csv` per the recommended layout).
- **YAML-config-driven scenario sweeps** → T41. T40 keeps scenarios as
  Python tuples inside each `src/<protocol>/baseline.py`; T41 lifts them
  into `configs/baseline.yaml` and adds the harness loop that consumes
  them.
- **Narwhal+Tusk column population** → T38.1. The schema admits the NWT
  columns (`mempool_msgs_per_acu`, `mempool_tps`, the NWT row in
  `consensus_msgs_per_acu`); T38.1 lands `src/narwhal_tusk/summarise.py`
  and one entry in the `_REDUCERS` dispatch table.
- **Adversarial-experiment columns** → T51–T54. `byzantine_fraction`,
  `adversary_strategy`, `empirical_epsilon`, `analytical_epsilon_bound`,
  `f_max_count`, `f_max_stake`, `view_change_or_reorg_count` are all on
  the wiki extension register pointed at T51/T52/T53/T54.
- **Delay-regime columns** → T48–T49. Network phase metadata
  (`network_phase_id` etc.) is on the extension register.
- **Aggregated file format choice** → T44. The wiki extension register
  records "T44 chooses the layout: either `*_ci_lo/_ci_hi` columns
  rewritten in place, or sibling `baseline_aggregated.csv`. T40 leaves the
  choice open."
- **NWT-pending catalogue revision text** → T38.1 (per Backlog 2026-05-27
  T37 follow-up). `concepts/adversary-model §8` and
  `concepts/experiment-matrix-runs §8` stay at "9 in-scope / 3 deferred
  with T38.1 / 6 catalogued" until T38.1 lands.

## 2. The wiki page contract

### 2.1 File: `wiki/concepts/output-format.md`

~250 lines. Authored against the [[concepts/metric-reconciliation]] §T40
CSV schema implications column set as the bind. Section structure:

1. **Purpose** (~15 lines). Pins the unified comparative CSV produced by
   `src/output/csv.py`; the derived dataset downstream of
   [[concepts/event-log-schema]]; names the four asymmetries from
   [[concepts/metric-reconciliation]] it inherits and resolves into CSV
   columns.
2. **Position in the pipeline** (~10 lines). ASCII data-path block from
   `EventLogger.records` + `RunResult` → reducer → writer →
   `results/baseline.csv` → (T44) → `results/baseline_aggregated.csv` →
   (Chapter 4) plots. Calls out the per-trial row granularity.
3. **Canonical schema** (~80 lines). The full ~30-column schema lifted
   verbatim from `metric-reconciliation.md §T40 CSV schema implications`,
   organised into five groups (identity, workload, network +
   reproducibility, per-metric category × 4, Snowman params). One table
   row per column: `column | dtype | unit | populated-today? (yes / no /
   protocol-list) | extension-register-entry`. This is the contract every
   future implementation milestone has to honour.
4. **Today's writer subset** (~30 lines). The 18-column projection T40
   actually populates (§3 below). Explicit table of which columns are
   blank for the not-yet-implemented surfaces; NWT columns are absent
   rows (not `NaN`) — the writer simply doesn't produce them yet.
5. **Per-protocol derivation rules** (~60 lines). Four short
   subsections, one per protocol, each ~15 lines. Each gives the closed-
   form formula or reduction algorithm that maps `(EventRecord stream,
   RunResult, ScenarioMeta)` to each column. NWT is one line: "Lands
   with T38.1; the reducer is the open-to-revision surface."
6. **NaN dispatch policy** (~20 lines). Three rules:
   - Snowman parameter columns (`K`, `alpha_p`, `alpha_c`, `beta`,
     `alpha_c_over_K`) are `NaN` for non-Snowman rows.
   - `f_max_count` and `f_max_stake` are mutually exclusive — exactly
     one is populated per row; the other is `NaN`. Dispatch by protocol
     fault-attribution model (count for PBFT/Snowman/NWT; stake for
     Casper FFG).
   - Any column whose extension-register entry is unresolved is written
     as the empty string `""`, not `NaN` — empty distinguishes "not
     implemented yet" from "structurally not applicable to this
     protocol."
7. **Snowman `n=4` row policy** (~15 lines). Skip from main CSV; sibling
   `results/snowman_n4_sanity.csv` carries the row. Rationale lifted
   from `metric-reconciliation.md §Snowman parameter rescaling §
   Comparative-claim exclusion at n=4`. The sanity row includes the
   18-column schema plus a single extra `snowman_degenerate_n4` boolean
   flag column (always `True` in the sanity file; the column does not
   exist in the main file).
8. **Row identity & ordering** (~15 lines). `run_id` format:
   `<protocol>-n<n>[-<variant>]` — e.g. `pbft-n4`,
   `casper-ffg-n4-nonuniform`, `snowman-n7`. Lexicographic
   `(protocol, n, run_id, seed)` row order (deterministic and
   grep-friendly). `seed` is the integer `global_seed` from
   `build_run(config, global_seed, factory)`; today every scenario runs
   at the project default `global_seed=42`, so the column is constant
   but present (T41 sweeps it).
9. **CSV mechanics** (~15 lines). Stdlib `csv.DictWriter`, header row,
   `newline=""`, parent directories created on write, overwrite-on-write
   (no append; T41 owns the multi-file aggregator pattern). Float
   formatting: `latency_ms` columns at `.9f`, `tps` and `*_per_acu` at
   `.6f`, `success_rate` / `fork_rate` at `.6f`, Snowman parameters as
   integers, `alpha_c_over_K` at `.6f`. Empty `runs` → header-only file.
10. **Determinism contract** (~10 lines). Same `(YAML config,
    global_seed)` → byte-identical `results/baseline.csv`. Inherited
    from upstream layers (T22 / T23 / T24 / T39) plus three local
    properties: total row ordering; pure-function reducer; order-stable
    float formatting.
11. **Extension register** (~20 lines). Table: `column |
    depends-on-task | status (pending/live)`. Initial entries:
    - `*_ci_lo`, `*_ci_hi` for every metric → T44 (pending).
    - `mempool_msgs_per_acu`, `mempool_tps`, NWT row population
      everywhere → T38.1 (pending).
    - `empirical_epsilon` (Snowman observed `ε`) → T54 (pending).
    - `analytical_epsilon_bound` (Snowman analytical `(1 − α_c/K)^β`) →
      T54 (pending; could be added at T40 trivially but waits for T54's
      verify-gate context to avoid premature commit).
    - `byzantine_fraction`, `adversary_strategy` → T51–T54 (pending).
    - `network_phase_id` → T19 + T48 (pending; constant per the
      calibration default phase today).
    - `workload_arrival_process`, `workload_tx_bytes`,
      `workload_conflict_rate`, `workload_offered_rate` → T41 (pending;
      currently no separate workload layer in the simulator).
    - `view_change_or_reorg_count` → T54 (pending; the PBFT view-change
      count IS observable today but `metric-reconciliation` defines it as
      part of the adversarial-result column family).
    - `f_max_count`, `f_max_stake` → T54 (pending).
    - `peak_tps`, `goodput`, `bytes_per_acu`,
      `per_validator_state_bytes` → T41 + T58 (pending; require either
      a workload model or sustained-load sweeps that don't exist today).
12. **Cross-references** (~5 lines). Outbound links to
    [[concepts/metric-reconciliation]], [[concepts/evaluation-metrics]],
    [[concepts/event-log-schema]], [[concepts/runner]],
    [[concepts/experiment-matrix]], plus inbound expectations from
    [[concepts/experiment-matrix-runs]] and the Chapter 4 plots
    referenced from [[drafts/ch3_methodology]].
13. **Revisions** (~3 lines). Empty initial section per
    `docs/wiki-spec.md §Revisions rule`.

### 2.2 Inbound forward-references the page resolves

15 forward-references currently point at `[[concepts/output-format]]`
(per `wiki/lint/2026-05-21_report.md` M1). Once the page lands, all 15
resolve and the L-W4 M1 finding closes. The reference list:
- [[concepts/metric-reconciliation]] — six references (every per-protocol
  table's "T40 CSV column" cross-reference).
- [[concepts/event-log-schema]] — one reference (the "derived dataset"
  pointer in the Purpose section).
- [[concepts/runner]] — one reference (T39's deferral notice).
- [[concepts/experiment-matrix-runs]] — three references (the
  ~2,700-run combinatorial budget paragraph).
- [[concepts/adversary-model]] — one reference (§8 column-set
  cross-link).
- [[concepts/adversary-model-runtime]] — one reference (§6 register
  cross-link).
- [[concepts/experiment-matrix]] — two references (the per-RQ design
  map cross-link + the seed/replication policy paragraph).

Auggie verifies the count post-landing (see §M-verify).

### 2.3 Two ## Revisions blocks on upstream pages

- **`wiki/concepts/event-log-schema.md` §CSV format** appends a
  Revisions block: "2026-05-28 by T40: the unified comparative CSV
  produced by `src/output/csv.py` is a sibling consumer of the same
  `EventLogger.records` substrate this section describes; the two CSVs
  are *both* derived from the raw event log, with different column sets
  and different row granularities. See [[concepts/output-format]]."
- **`wiki/concepts/runner.md` §What's outside the runner** appends a
  Revisions block: "2026-05-28 by T40: the CSV-output gap noted in §CSV
  columns and output formatting → T40 is closed. The runner stays at
  pass-through; the comparative CSV is owned by `src/output/csv.py`. See
  [[concepts/output-format]]."

These two blocks preserve the wiki graph's contract honesty: the upstream
pages know their downstream consumer.

## 3. The code subsystem

### 3.1 File layout

```
src/
  output/                          # NEW package
    __init__.py                    # re-exports write_unified_csv + ScenarioMeta
    csv.py                         # writer + generic-column computation
    baseline.py                    # __main__ orchestrator
    schema.py                      # ScenarioMeta + COLUMN_ORDER
  pbft/
    baseline.py                    # NEW — SCENARIOS + run_scenario
    summarise.py                   # NEW — pbft.summarise reducer
  pos/
    baseline.py                    # HARMONISED — drops CSV writer; keeps
                                   #   SCENARIOS + run_scenario in new shape
    summarise.py                   # NEW — pos.summarise reducer
  snowman/
    baseline.py                    # NEW — SCENARIOS + run_scenario
    summarise.py                   # NEW — snowman.summarise + sanity_row

tests/
  output/                          # NEW
    test_generic_cols.py
    test_csv.py
    test_baseline_e2e.py
  pbft/
    test_summarise.py              # NEW
  pos/
    test_summarise.py              # NEW
  snowman/
    test_summarise.py              # NEW
  integration/
    test_pbft_baseline.py          # HARMONISED — imports SCENARIOS
    test_snowman_baseline.py       # HARMONISED — imports SCENARIOS
    test_pos_baseline.py           # HARMONISED — imports SCENARIOS
```

Sizes: ~110 + 50 + 40 = 200 LoC of new `src/output/` code; ~80 × 2 =
160 LoC of new baseline scaffolding; ~50 + 60 + 70 = 180 LoC of reducer
logic; ~330 LoC of new tests; ~30 LoC of test-file edits. Net ~870 new
LoC; net ~80 deleted from `src/pos/baseline.py`. Larger than T39 (~200
LoC), smaller than T28 / T29.

### 3.2 `src/output/schema.py`

```python
"""T40 — Unified CSV schema bridge.

Carries scenario identity through the pipeline:
  baseline.SCENARIOS  -> run_scenario(meta)  -> (records, result, meta)
                                                            |
                                                            v
                              write_unified_csv(path, runs of these triples)

COLUMN_ORDER is the today-writer projection of the full ~30-column
schema pinned by wiki/concepts/output-format.md §Canonical schema.
Adding a future column is a one-line edit here plus an extension-register
update in the wiki page.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioMeta:
    """Identifies one (protocol, scenario, seed) row of the unified CSV.

    Carried alongside (records, result) so the reducer + generic-cols
    helper can resolve protocol identity, scenario variant, n, and the
    seed used to produce the run. output-format.md §Row identity pins
    the run_id rule.
    """
    run_id: str           # "pbft-n4", "casper-ffg-n4-nonuniform", ...
    protocol: str         # "pbft" | "casper-ffg" | "snowman"
    n: int                # n_validators
    variant: str | None   # "uniform" / "nonuniform" / None (POS only today)
    seed: int             # global_seed used in build_run
    t_max: float          # run deadline (math.nan for quiescence runs)


COLUMN_ORDER: tuple[str, ...] = (
    # Identity (generic — 4 cols).
    "run_id", "protocol", "n", "seed",
    # Reproducibility (generic — 2 cols).
    "commit_hash", "t_max",
    # Latency (per-protocol — 2 cols).
    "commit_latency_ms", "finality_latency_ms",
    # Throughput (per-protocol — 1 col).
    "tps",
    # Overhead (generic + per-protocol — 2 cols).
    "consensus_msgs_per_acu", "total_msgs_per_acu",
    # Reliability (per-protocol — 2 cols).
    "success_rate", "fork_rate",
    # Snowman parameters (Snowman-only; NaN elsewhere — 5 cols).
    "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
)
```

18 columns total. Wiki §Today's writer subset cross-references this
tuple as the authoritative column ordering.

### 3.3 `src/output/csv.py`

The writer + generic-column derivation + dispatch table.

```python
"""T40 — Unified CSV writer.

Composes generic per-row columns with per-protocol reducer output and
writes the result to a CSV file in COLUMN_ORDER. The writer is a pure
projection over (records, result, meta) triples; no I/O beyond the final
file write; no clock reads; no RNG draws.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import csv
import subprocess
from pathlib import Path
from typing import Iterable

from event_log import EventRecord
from scheduler import RunResult

from pbft.summarise import summarise as _pbft_summarise
from pos.summarise import summarise as _pos_summarise
from snowman.summarise import summarise as _snowman_summarise

from .schema import COLUMN_ORDER, ScenarioMeta


_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}

# Columns produced by _generic_cols. Used by the collision guard to
# detect reducer drift at row-build time.
_GENERIC_COLUMNS = frozenset({
    "run_id", "protocol", "n", "seed",
    "commit_hash", "t_max",
    "total_msgs_per_acu",
})


def _resolve_commit_hash() -> str:
    """Return the short commit hash, '<hash>-dirty' on a dirty tree, or
    'WORKING_TREE' if git is unavailable or cwd is not a repo.

    Reproducibility contract — T27 + T66. The marker is surfaced rather
    than crashed-on so the writer stays runnable in CI sandboxes and
    pre-commit hooks where HEAD may not exist.
    """
    try:
        rev = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            capture_output=True, text=True, check=True, timeout=2.0,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True, timeout=2.0,
        ).stdout.strip()
        return f"{rev}-dirty" if status else rev
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "WORKING_TREE"


def _total_msgs_per_acu(records, result) -> float:
    """Generic: total delivery events per decided event. NaN if no
    decided events fired (the denominator is undefined)."""
    deliveries = sum(1 for r in records if r.event_type == "delivery")
    decided    = sum(1 for r in records if r.event_type == "decided")
    if decided == 0:
        return float("nan")
    return deliveries / decided


def _generic_cols(records, result, meta: ScenarioMeta) -> dict[str, object]:
    return {
        "run_id":             meta.run_id,
        "protocol":           meta.protocol,
        "n":                  meta.n,
        "seed":               meta.seed,
        "commit_hash":        _resolve_commit_hash(),
        "t_max":              meta.t_max,
        "total_msgs_per_acu": _total_msgs_per_acu(records, result),
    }


def _format_row(row: dict[str, object]) -> dict[str, str]:
    """Apply column-specific float formatting; integers and strings
    pass through; floats become repr-stable strings."""
    out: dict[str, str] = {}
    for col in COLUMN_ORDER:
        v = row[col]
        if col.endswith("_ms"):
            out[col] = f"{v:.9f}" if isinstance(v, float) else str(v)
        elif col in {"tps", "consensus_msgs_per_acu",
                     "total_msgs_per_acu", "success_rate", "fork_rate",
                     "alpha_c_over_K"}:
            out[col] = f"{v:.6f}" if isinstance(v, float) else str(v)
        else:
            out[col] = str(v)
    return out


def write_unified_csv(
    path: Path,
    runs: Iterable[tuple[list[EventRecord], RunResult, ScenarioMeta]],
) -> None:
    """Project each run to one CSV row in COLUMN_ORDER. Snowman n=4
    rows are skipped (output-format.md §7). Raises:

      KeyError   — meta.protocol has no entry in _REDUCERS.
      ValueError — a reducer returned a key in _GENERIC_COLUMNS or a
                   key not in COLUMN_ORDER (reducer-vs-generic clash or
                   schema drift).
    """
    rows: list[dict[str, object]] = []
    for records, result, meta in runs:
        if meta.protocol == "snowman" and meta.n == 4:
            continue
        if meta.protocol not in _REDUCERS:
            raise KeyError(f"no reducer for protocol={meta.protocol!r}")
        row = _generic_cols(records, result, meta)
        protocol_cols = _REDUCERS[meta.protocol](records, result, meta)
        collisions = _GENERIC_COLUMNS & protocol_cols.keys()
        if collisions:
            raise ValueError(
                f"reducer for {meta.protocol!r} returned generic columns: "
                f"{sorted(collisions)!r}"
            )
        unknown = protocol_cols.keys() - set(COLUMN_ORDER)
        if unknown:
            raise ValueError(
                f"reducer for {meta.protocol!r} returned unknown columns: "
                f"{sorted(unknown)!r}"
            )
        row.update(protocol_cols)
        rows.append(row)

    rows.sort(key=lambda r: (r["protocol"], r["n"], r["run_id"], r["seed"]))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMN_ORDER,
                                extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(_format_row(row))
```

Notes on the writer:
- `extrasaction="raise"` is a belt-and-braces second guard against
  unknown columns (the explicit pre-check is the primary).
- Float formatting matches the precedent set by the T35-local writer in
  `src/pos/baseline.py` (`.9f` for `latency_ms`, `.6f` for ratios).
- The sort is total: `(protocol, n, run_id, seed)` resolves
  `casper-ffg-n4-uniform` before `casper-ffg-n4-nonuniform` because
  `nonuniform < uniform` alphabetically — acceptable; grep-friendly is
  the primary requirement, not human-reading order.
- The writer is a pure function over its inputs except for the
  `subprocess.run(["git", ...])` call in `_resolve_commit_hash`. The
  commit-hash resolution is the only impurity surface; tests
  monkeypatch it.

### 3.4 Per-protocol reducer interface

```python
# src/<protocol>/summarise.py
def summarise(records: list[EventRecord],
              result: RunResult,
              meta: ScenarioMeta) -> dict[str, object]:
    """Return ONLY the protocol-specific columns. The set of keys
    returned is fixed per protocol and validated against COLUMN_ORDER
    (minus _GENERIC_COLUMNS) by the writer.

    Required keys for ALL reducers:
      commit_latency_ms, finality_latency_ms,   # float, NaN on no-decided
      tps, consensus_msgs_per_acu,              # float, NaN on no-decided
      success_rate, fork_rate,                  # float in [0, 1] or NaN
      K, alpha_p, alpha_c, beta, alpha_c_over_K # NaN for non-Snowman

    PBFT-specific notes:
      commit_latency_ms = finality_latency_ms (per-block deterministic).
      fork_rate = 0.0 by construction (PBFT never forks below f).
      success_rate = decided_count / proposed_count.

    Casper FFG-specific notes:
      finality_latency_ms = median per-node time-of-first finalised
                            epoch's decided event.
      commit_latency_ms = slot-proposal-to-block-included latency
                          (less than finality_latency_ms by ~1 slot).
      fork_rate = pre-finality reorg count over proposed blocks
                  (currently 0 at honest baseline).

    Snowman-specific notes:
      finality_latency_ms = commit_latency_ms (Snowman has no separate
                            pre-finality state in the implemented model;
                            counter-β IS finality).
      K, alpha_p, alpha_c, beta, alpha_c_over_K from
        `snowman.parameters.rescale(meta.n)`.
      fork_rate = pre-β preference-flip count / total polls.
      Non-Snowman reducers populate K..alpha_c_over_K = float("nan").
    """
```

Each reducer's per-column formula is documented in
`wiki/concepts/output-format.md §Per-protocol derivation rules`. The
docstring above is the in-code mirror.

### 3.5 `src/<protocol>/baseline.py` shape

```python
"""<Protocol> baseline scenarios — the SCENARIOS list run by
src/output/baseline.py and asserted by tests/integration/test_<protocol>_baseline.py.

Each scenario is a ScenarioMeta. run_scenario(meta) builds the protocol
stack at meta.n, runs to completion or t_max, and returns the (records,
result, meta) triple the unified CSV writer consumes.
"""
from __future__ import annotations

import math

from common import run_to_completion
from config import build_run
from output.schema import ScenarioMeta

from . import _factory                                # protocol-specific
from .config_helpers import _config                   # protocol-specific


SCENARIOS: tuple[ScenarioMeta, ...] = (
    ScenarioMeta(run_id="<proto>-n4",  protocol="<proto>", n=4,
                 variant=None, seed=42, t_max=math.nan),
    ScenarioMeta(run_id="<proto>-n7",  protocol="<proto>", n=7,
                 variant=None, seed=42, t_max=math.nan),
    ScenarioMeta(run_id="<proto>-n10", protocol="<proto>", n=10,
                 variant=None, seed=42, t_max=math.nan),
)


def run_scenario(meta: ScenarioMeta):
    """Build, run, return (records, result, meta) for one scenario.

    Determinism inherited from build_run + run_to_completion. Tests
    in tests/integration/test_<proto>_baseline.py assert byte-identical
    re-runs at the same meta.seed.
    """
    config = _config(meta.n, meta.variant)
    handle = build_run(config, meta.seed, _factory(meta.n))
    t_max = None if math.isnan(meta.t_max) else meta.t_max
    result, logger = run_to_completion(handle, t_max=t_max)
    return logger.records, result, meta
```

Per-protocol specialisation:
- **PBFT**: `t_max=math.nan` (runs to quiescence on honest path).
  Variant is always `None`. n ∈ {4, 7, 10}.
- **Casper FFG (POS)**: `t_max=20.0`. Variants: `"uniform"` (n ∈ {4, 7,
  10}) and `"nonuniform"` (n=4 only; per the T35 / T33 scenarios).
- **Snowman**: `t_max=20.0`. Variant always `None`. n ∈ {4, 7, 10}.
  `meta.n=4` is included in the SCENARIOS list (it runs); the writer
  skips writing its row to the main CSV.

### 3.6 `src/output/baseline.py`

```python
"""T40 — Unified CSV orchestrator.

Imports each protocol's SCENARIOS + run_scenario, runs every scenario,
and writes one results/baseline.csv. Snowman n=4 produces an additional
results/snowman_n4_sanity.csv via snowman.summarise.sanity_row.

Run from repo root:
    PYTHONPATH=src python3 -m output.baseline
"""
from __future__ import annotations

from pathlib import Path

import pbft.baseline as pbft_baseline
import pos.baseline as pos_baseline
import snowman.baseline as snowman_baseline
from snowman.summarise import sanity_row

from .csv import write_unified_csv


_OUT  = Path("results/baseline.csv")
_SANE = Path("results/snowman_n4_sanity.csv")


def main() -> None:
    runs = []
    for meta in pbft_baseline.SCENARIOS:
        runs.append(pbft_baseline.run_scenario(meta))
    for meta in pos_baseline.SCENARIOS:
        runs.append(pos_baseline.run_scenario(meta))
    for meta in snowman_baseline.SCENARIOS:
        runs.append(snowman_baseline.run_scenario(meta))
    write_unified_csv(_OUT, runs)

    # Sibling sanity file for the Snowman n=4 rescaling boundary
    # (output-format.md §7).
    for records, result, meta in runs:
        if meta.protocol == "snowman" and meta.n == 4:
            sanity_row(records, result, meta, _SANE)
            break


if __name__ == "__main__":
    main()
```

### 3.7 Harmonisation of `src/pos/baseline.py`

The existing file (125 LoC) loses:
- `_summarise()` (lines 80–99) — its logic moves to `src/pos/summarise.py`
  with the protocol-specific column slice extracted.
- `write_baseline_csv()` (lines 106–114) — superseded by
  `write_unified_csv`.
- `_COLUMNS` tuple (lines 102–103) — superseded by `COLUMN_ORDER`.
- `main()` (line 117–) — superseded by `output.baseline.main`.
- The `csv` and `statistics` imports — no longer used here.

The existing file gains:
- A `SCENARIOS: tuple[ScenarioMeta, ...]` constant in place of the
  current `SCENARIOS: tuple[tuple[str, int, dict[int, float]], ...]`.
  The 4 entries become 4 `ScenarioMeta` values with `variant="uniform"`
  for n=4/7/10 and `variant="nonuniform"` for the n=4-nonuniform case.
- A `run_scenario(meta) -> (records, result, meta)` function. The
  `_config` and `_factory` helpers stay (they're still useful and the
  integration test imports them).

Net: ~80 LoC out, ~50 LoC in.

### 3.8 Integration-test harmonisation

The three integration baseline tests (`tests/integration/test_pbft_baseline.py`,
`test_pos_baseline.py`, `test_snowman_baseline.py`) currently each define:
- `_T_MAX` constant.
- `_config(n)` helper.
- `_factory(n)` helper.
- `_run(n, global_seed)` helper.
- The assertion-bearing `TestXxx` class.

The harmonisation replaces the first four with `from <protocol>.baseline
import SCENARIOS, run_scenario`. The test class's assertions stay
verbatim — they were already operating on `(records, result)` returned
by `_run`. The new test loop becomes:

```python
class TestPBFTHonestBaseline(unittest.TestCase):
    def test_each_scenario_decides(self):
        for meta in pbft_baseline.SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                records, result, _ = pbft_baseline.run_scenario(meta)
                # … existing assertions verbatim …
```

Net change per file: ~10 LoC out (the helper trio), ~5 LoC in (the
import + the subTest loop). Test count and assertion content unchanged.

### 3.9 `src/output/__init__.py`

```python
"""T40 — Unified output subsystem.

Today: one writer (write_unified_csv) + one orchestrator (baseline.main)
+ one schema bridge (ScenarioMeta, COLUMN_ORDER).
"""
from .csv import write_unified_csv
from .schema import COLUMN_ORDER, ScenarioMeta

__all__ = ("write_unified_csv", "ScenarioMeta", "COLUMN_ORDER")
```

## 4. Testing strategy

Four layers, mirroring the code surface. ~330 LoC total across five new
test files plus ~30 LoC of integration-test edits.

### 4.1 `tests/output/test_generic_cols.py` (~50 LoC)

Unit tests for `_generic_cols` and `_total_msgs_per_acu` over synthetic
`EventRecord` streams. Cases:
- Identity columns pass through verbatim from `ScenarioMeta`.
- `total_msgs_per_acu` = `delivery_count / decided_count` for a stream
  with both event types.
- Zero `decided` events → `total_msgs_per_acu = NaN` (denominator
  undefined).
- Zero `delivery` events but one `decided` → `total_msgs_per_acu = 0.0`.
- Monkeypatch `_resolve_commit_hash` to a fixed value and assert it
  appears verbatim in the row.

### 4.2 `tests/<protocol>/test_summarise.py` (~50–70 LoC each)

For each implemented protocol, a unit test file constructs the minimum
event stream a real run would produce — for PBFT, a single `(0,0)`
instance going PRE-PREPARE → PREPARE quorum → COMMIT quorum →
`decided`; for FFG, two epochs each finalising; for Snowman, one block
reaching counter `β` via 15 polls. Asserts:

- Reducer returns exactly the protocol-specific column set (no generic
  columns, no Snowman columns for PBFT/POS — those are `NaN`).
- Each column's value matches the closed-form formula in
  `wiki/concepts/output-format.md §Per-protocol derivation rules`.
- Negative case: a stream with no `decided` event → `commit_latency_ms
  = NaN`, `success_rate = 0.0`, `fork_rate = NaN`.
- Snowman extra: a separate test for `sanity_row()` at `n=4` producing
  a single-row CSV with the same 18 columns plus the
  `snowman_degenerate_n4` flag column.

### 4.3 `tests/output/test_csv.py` (~80 LoC)

Unit tests for `write_unified_csv`'s composition behaviour.
Monkeypatches the `_REDUCERS` table with deterministic mock reducers so
the test doesn't depend on protocol code. Cases:
- 3 synthetic runs (one per protocol) → CSV has 4 lines (header + 3),
  columns in `COLUMN_ORDER`, rows in `(protocol, n, run_id, seed)` sort
  order.
- Mock reducer returns `{"n": 99}` → `ValueError("reducer for 'pbft'
  returned generic columns: ['n']")`.
- Mock reducer returns `{"foobar": 1.0}` → `ValueError("reducer for
  'pbft' returned unknown columns: ['foobar']")`.
- Unknown protocol → `KeyError`.
- Empty `runs` iterable → header-only CSV file.
- Snowman `n=4` scenario in `runs` → row absent from output.
- Path with nonexistent parent → parent auto-created.
- Float formatting: `commit_latency_ms = 312.500000123456` is written
  as `312.500000123`.
- Golden-file test: a 3-run input → byte-exact match against
  `tests/output/fixtures/golden_baseline.csv` (regenerated by a
  `make golden-output` target as part of the spec).

### 4.4 `tests/output/test_baseline_e2e.py` (~80 LoC)

The headline build-verification test for T40. Drives `output.baseline.main`
end-to-end against a `tmp_path`-rooted `_OUT` and `_SANE`. Cases:
- Two consecutive calls produce byte-identical
  `results/baseline.csv` files (determinism contract).
- Row count = `|PBFT.SCENARIOS| + |POS.SCENARIOS| + |SNOWMAN.SCENARIOS|
  - 1` (the `-1` is the skipped Snowman n=4).
- Every row's `commit_hash` is identical (single run, single git
  state).
- No row has `(protocol="snowman", n=4)` in `results/baseline.csv`.
- One row exists in `results/snowman_n4_sanity.csv` with the
  `snowman_degenerate_n4` column set to `True`.
- Reading back with `csv.DictReader`: header is exactly
  `COLUMN_ORDER`; all 18 columns present.
- Per-row sanity: `t_max` matches `meta.t_max`; `n` matches
  `meta.n`; `success_rate ∈ {0.0, 1.0}` at honest baseline (probability
  of partial-success degenerate at n_runs=1).

### 4.5 Integration-test edits

Same three tests, ~10 LoC each. Replace inline helper trio with
`from <protocol>.baseline import SCENARIOS, run_scenario`. Assertions
verbatim.

### 4.6 Make target

```
.PHONY: test-output
test-output:
	PYTHONPATH=src python3 -m pytest \
	    tests/output \
	    tests/pbft/test_summarise.py \
	    tests/pos/test_summarise.py \
	    tests/snowman/test_summarise.py \
	    -v
```

Plus `tests/output` added to the existing `test` target's collection
list. `make test` stays green at every step of the migration.

## 5. Error handling

Behaviour matrix:

| Condition                                  | Behaviour                                                          | Rationale                                                                                  |
| :---                                       | :---                                                               | :---                                                                                       |
| Reducer key collides with generic column   | `ValueError` at row-build time                                     | Catch contract drift early; silent overwrite would scramble columns.                       |
| Reducer returns key not in `COLUMN_ORDER`  | `ValueError` at row-build time                                     | Schema-drift guard; new column must update both `schema.py` and the wiki register.         |
| Unknown `meta.protocol`                    | `KeyError` from `_REDUCERS[k]`                                     | Adding a new protocol must update the dispatch table.                                      |
| `meta.protocol="snowman"`, `meta.n=4`      | Skipped in main CSV; row written to sanity CSV by orchestrator     | output-format.md §7; per metric-reconciliation.md §Snowman rescaling §Comparative-claim.   |
| `meta.t_max = NaN`                         | `run_to_completion(..., t_max=None)` — quiescence                  | PBFT runs to quiescence on honest path; FFG / Snowman use a real deadline.                 |
| No `decided` events in a run               | `success_rate=0.0`; `commit_latency_ms=NaN`; `fork_rate=NaN`       | Run failed; preserve the row, mark observations undefined.                                 |
| `git rev-parse HEAD` fails                 | `commit_hash="WORKING_TREE"`                                       | Not in a repo or no git binary — keep the writer runnable in CI sandboxes.                 |
| Dirty working tree                         | `commit_hash="<8char>-dirty"`                                      | Surfaces the reproducibility violation without crashing.                                   |
| `path.parent` doesn't exist                | Auto-created via `mkdir(parents=True, exist_ok=True)`              | Matches `EventLogger.to_csv` precedent.                                                    |
| Output file already exists                 | Overwritten (no append, no warning)                                | Single-shot baseline writer; T41 owns append / aggregation.                                |
| Empty `runs` iterable                      | Header-only CSV written                                            | Matches `EventLogger.to_csv` precedent.                                                    |
| Reducer raises                             | Bubble up (no catch)                                               | Protocol bug; fail-fast.                                                                   |

No silent drops anywhere. Every reducer raises if its input event
stream is malformed for its protocol (e.g. a `decided` event with a
non-tuple `instance_id` for PBFT). The writer never tries to guess — it
either has formulas from the reducer, or the column gets `NaN`/empty
per the dispatch policy.

## 6. Determinism contract

Same `(YAML config, global_seed)` → byte-identical `results/baseline.csv`.
The contract is inherited from upstream layers and reinforced by three
local properties.

**Inherited.** `build_run(config, global_seed, factory)` produces a
deterministic `RunHandle` (T27 / reproducibility.md). `run_to_completion`
is a pass-through over the scheduler (T39). The scheduler dispatches
events in canonical `(t, node_id, seq)` order (T17 / simulation-design.md).
`EventLogger.records` are appended in dispatch order (T24 / event-log-schema.md).
So `(records, result)` is byte-identical across runs at the same seed.

**Local properties.**

1. **Reducer is a pure function.** Each `summarise(records, result, meta)`
   has no I/O, no clock reads, no RNG draws, no side effects. Same
   inputs → same output. Tests assert this via a `dataclasses.replace`
   round-trip on the meta.
2. **Row ordering is total.** Rows are sorted by
   `(protocol, n, run_id, seed)` before writing. The four-tuple uniquely
   identifies a row in the per-trial schema, so the sort is total
   regardless of `runs` iterable order.
3. **Float formatting is order-stable.** `f"{v:.9f}"` and `f"{v:.6f}"`
   are CPython-deterministic. No locale-aware formatting.

**One impurity surface: `_resolve_commit_hash`.** The `subprocess` call
reads the git tree state at the moment of the write. Determinism in this
column is contingent on the tree state, not the simulator inputs. Tests
monkeypatch the function to a constant value to keep the CSV byte-
identical across the test's two `main()` calls.

**The e2e test** (`tests/output/test_baseline_e2e.py`) asserts the
byte-identical-CSV property end-to-end. This is the build-verification
gate the experiment page references.

## 7. Migration plan — six commits

Land in this order. Each commit independently builds and passes
`make test`.

### Commit 1: wiki contract

- New `wiki/concepts/output-format.md` (~250 lines).
- `wiki/index.md` entry under `## Concepts`.
- `wiki/log.md` entry (`## [2026-05-28] code | task 40 — output-format.md`).
- Two `## Revisions` blocks on `event-log-schema.md` and `runner.md`.
- `TASKS.md` Backlog: append-resolved on the T35-sample-CSV
  reconciliation item.

Commit message: `task 40: wiki contract for output-format`.

Verification: auggie post-edit re-query confirms the page resolves the
15 inbound forward-references; `grep -r 'concepts/output-format' wiki/`
returns the resolved set; no code changes; `make test` unaffected.

### Commit 2: src/output scaffolding + writer

- New `src/output/__init__.py`, `src/output/schema.py`,
  `src/output/csv.py`.
- New `tests/output/test_generic_cols.py`, `tests/output/test_csv.py`
  (the latter uses mock reducers).
- The `_REDUCERS` table in `csv.py` imports from
  `pbft.summarise` / `pos.summarise` / `snowman.summarise` — stubs that
  raise `NotImplementedError`.
- New `Makefile` target `test-output`.

Commit message: `task 40: src/output writer + scaffolding`.

Verification: `make test-output` passes (against the mock-reducer
table); `make test` stays green (the three reducer-stub raises don't
trigger because nothing calls them yet).

### Commit 3: harmonise src/pos/baseline + add pos.summarise

- New `src/pos/summarise.py` — lifts FFG epoch-finalisation logic from
  the old `_summarise`, returns the protocol-specific column slice.
- Harmonise `src/pos/baseline.py` — drop CSV-writing path; reshape
  `SCENARIOS` and `_run_scenario`; remove `__main__`.
- Update `tests/integration/test_pos_baseline.py` — import from new
  baseline module.
- New `tests/pos/test_summarise.py`.
- Delete tracked `results/pos/baseline.csv`.

Commit message: `task 40: harmonise src/pos/baseline; add pos.summarise`.

Verification: `make test` green; the T35 sample CSV is gone but its
data is now derived through the unified path.

### Commit 4: src/pbft/baseline + pbft.summarise

- New `src/pbft/baseline.py` — lifts `_config / _factory / _run`
  scenarios out of `tests/integration/test_pbft_baseline.py`; exports
  `SCENARIOS` + `run_scenario`.
- New `src/pbft/summarise.py`.
- Update `tests/integration/test_pbft_baseline.py` — import from new
  baseline module; assertions verbatim.
- New `tests/pbft/test_summarise.py`.

Commit message: `task 40: src/pbft/baseline + pbft.summarise`.

Verification: `make test` green; the PBFT baseline test produces the
same events as pre-commit (byte-identical determinism).

### Commit 5: src/snowman/baseline + snowman.summarise

- New `src/snowman/baseline.py` — same shape as PBFT.
- New `src/snowman/summarise.py` — includes `sanity_row()` export.
- Update `tests/integration/test_snowman_baseline.py`.
- New `tests/snowman/test_summarise.py` — includes a `sanity_row` test.

Commit message: `task 40: src/snowman/baseline + snowman.summarise`.

Verification: `make test` green; Snowman baseline test produces same
events.

### Commit 6: wire orchestrator + canonical artifacts

- New `src/output/baseline.py` — wires the three protocols' SCENARIOS
  through `write_unified_csv`.
- New `tests/output/test_baseline_e2e.py` — byte-identical CSV
  assertion.
- Run `PYTHONPATH=src python3 -m output.baseline` once; commit the
  produced `results/baseline.csv` and `results/snowman_n4_sanity.csv`.
- New `wiki/experiments/2026-05-28_unified-output.md` (~80 lines)
  documenting the build-verification baseline.
- `wiki/index.md` entry under `## Experiments`.
- `wiki/log.md` entry (`## [2026-05-28] code | task 40 — wire output orchestrator`).

Commit message: `task 40: wire output.baseline orchestrator; canonical results/baseline.csv`.

Verification: full `make test` green; auggie post-edit re-query
confirms the writer is wired into all three protocols' baselines;
`results/baseline.csv` exists with the expected row count.

After Commit 6: flip `TASKS.md` T40 to `[?]` In Review; recompute the
dashboard arithmetic. Per `prj-pickup` and `docs/workflow.md` the
human handles the actual `git commit`s and the In-Review flip's commit.

## 8. The unified CSV's expected first canonical content

At project default `global_seed=42`, the SCENARIOS-product produces:
- PBFT: 3 rows (n=4, n=7, n=10).
- Casper FFG: 4 rows (n=4-uniform, n=7-uniform, n=10-uniform, n=4-nonuniform).
- Snowman: 2 rows (n=7, n=10; n=4 is skipped).

Total: 9 rows + 1 header line = 10 lines in `results/baseline.csv`.

`results/snowman_n4_sanity.csv` carries 1 row + 1 header line.

Approximate expected values (numbers from prior baselines — final
values determined by the runner at commit time):

| run_id                    | commit_latency_ms | finality_latency_ms | tps      | consensus_msgs_per_acu | success_rate | fork_rate |
| :---                      | ---:              | ---:                | ---:     | ---:                   | ---:         | ---:      |
| `casper-ffg-n4-nonuniform`| ~5000             | ~5000               | ~1.6     | (FFG-aggregated)       | 1.0          | 0.0       |
| `casper-ffg-n4-uniform`   | ~5000             | ~5000               | ~1.6     | "                      | 1.0          | 0.0       |
| `casper-ffg-n7-uniform`   | ~5000             | ~5000               | ~2.8     | "                      | 1.0          | 0.0       |
| `casper-ffg-n10-uniform`  | ~5000             | ~5000               | ~4.0     | "                      | 1.0          | 0.0       |
| `pbft-n4`                 | (PBFT-3-phase)    | =commit             | (PBFT)   | (PBFT-O(n²))           | 1.0          | 0.0       |
| `pbft-n7`                 | "                 | "                   | "        | "                      | 1.0          | 0.0       |
| `pbft-n10`                | "                 | "                   | "        | "                      | 1.0          | 0.0       |
| `snowman-n7`              | ~1000             | =commit             | (Snowman)| (Snowman-O(Kβ))        | 1.0          | (≥0)      |
| `snowman-n10`             | ~1000             | =commit             | "        | "                      | 1.0          | (≥0)      |

(Casper FFG `~5000` derives from the T35 baseline finalising epoch 1 at
`≈ 5.000000001 s`; PBFT and Snowman values are the protocol's natural
honest-path latency at the simulator's default network phase.)

## 9. Verification before In-Review flip

Per the Engineer role prompt:

1. **`superpowers:verification-before-completion`** invocation.
2. **Auggie post-edit re-query** — describe the new
   `src/output/` package + the per-protocol reducers; locate every
   call site of `write_unified_csv` and `summarise`. Confirms the
   dispatch table is consistent with the on-disk modules and that no
   stale `write_baseline_csv` callsite lingers in `src/pos/baseline.py`.
3. **Auggie verification log** appended to the new
   `wiki/experiments/2026-05-28_unified-output.md` page per the
   Engineer role prompt's mandatory "Auggie verification" subsection.
4. **Full `make test`** green.
5. **Byte-identical e2e** verified by running the orchestrator twice
   into two tmp directories and `cmp`-ing the outputs.

## §M-verify: full-suite verification before In-Review flip

```bash
make test
shasum -a 256 results/baseline.csv > /tmp/t40-baseline.sha
PYTHONPATH=src python3 -m output.baseline
shasum -a 256 -c /tmp/t40-baseline.sha
```

Expected: `results/baseline.csv: OK`. If it does **not** verify, stop —
the second run diverged from the first, which violates the
determinism contract.

## 10. Open questions / known risks

1. **Reducer-vs-generic boundary drift.** A future column may be
   ambiguous — e.g. `bytes_per_acu` could be computed from raw
   `delivery` payload bytes (generic) or from protocol-specific byte
   accounting (reducer). The wiki page's `## Per-protocol derivation
   rules` section is the contract; the dispatch is by who has the
   formula, not by where the data lives. Watch for boundary creep
   when T44 / T48 / T54 land their columns.
2. **`success_rate` at n_runs=1.** Today `success_rate` is a 0/1
   indicator, not a frequency. The column will become a real
   [0, 1] frequency once T44 lands multi-seed sweeps; the schema
   stays unchanged. No code-level adjustment needed.
3. **Snowman fork_rate measurement.** Pre-`β` preference-flip count
   per total polls requires the reducer to walk the `query_response`
   event sequence per `(node, block)`. This is the most algorithmically
   involved reducer; expect ~30 LoC of accounting in
   `snowman.summarise.py` (~50% of the file). Tests cover the empty,
   one-flip, and many-flip cases.
4. **The 18-column subset is opinionated.** It deliberately drops
   `bytes_per_acu`, `peak_tps`, `goodput`, `per_validator_state_bytes`
   from the today writer (those need a workload model or sustained-load
   sweep to be meaningful). Each is on the extension register pointed at
   T41 / T58. A reader who expects "everything in metric-reconciliation"
   will need to consult the register; the wiki page's §4 calls this out
   explicitly.
5. **Test fixture maintenance.** The `tests/output/fixtures/
   golden_baseline.csv` file commits to specific float values. Any
   future scheduler / Node / Network change that alters event-stream
   timing will regenerate it. The Makefile `make golden-output` target
   exists to make regeneration explicit, not silent. Watch for hidden
   regenerations in commits.

## 11. Source pages consulted

- `wiki/concepts/metric-reconciliation.md` — the binding schema and
  per-protocol formulas.
- `wiki/concepts/evaluation-metrics.md` — the metric vocabulary.
- `wiki/concepts/event-log-schema.md` — the raw substrate the writer
  consumes.
- `wiki/concepts/runner.md` — the upstream `run_to_completion` seam.
- `wiki/concepts/reproducibility.md` — the determinism contract.
- `wiki/concepts/node-model.md` — the `emit` API and the `decided` /
  `halted` event semantics the reducers parse.
- `wiki/lint/2026-05-21_report.md` — the L-W4 M1 finding that this
  page closes (15 forward-references resolved).
- `docs/superpowers/specs/2026-05-27-t39-unified-runner-design.md` —
  the precedent for the `src/common/` + per-protocol-baseline pattern.

## 12. Auggie verification log entries (to be filled at execution time)

Per the Engineer role prompt's mandatory "Auggie verification"
subsection on the experiment page. Three calls expected:

- **Pickup-index (made before this spec was written).** Query:
  describe T40's prior-art surface — existing CSV writers, the event
  log API, the runner seam, per-protocol baseline modules,
  RunResult, the config schema.
- **Plan-phase re-query (made at the start of execution).** Query:
  enumerate every reference to `output-format`, `results/baseline.csv`,
  `_summarise`, `write_baseline_csv` across the codebase + wiki;
  confirm the migration plan touches all of them.
- **Post-edit re-query (made before the In-Review flip).** Query:
  describe the new `src/output/` package; locate every call site of
  `write_unified_csv` and `summarise`; confirm no stale CSV-writing
  surface remains in `src/pos/baseline.py`.
