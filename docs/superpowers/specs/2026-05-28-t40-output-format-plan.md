# T40 — Unified Output Format: Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to
> implement this plan task-by-task. Each task is one TDD cycle (test →
> red → green → commit) and leaves `make test` green.

**Goal:** Land the canonical comparative-CSV contract page
(`wiki/concepts/output-format.md`) and the `src/output/` subsystem that
projects every implemented protocol's honest baseline through one writer
into one `results/baseline.csv`. Retire the T35-local CSV writer.
Harmonise the per-protocol baseline-driver surface so PBFT, Casper FFG,
and Snowman each expose `SCENARIOS` + `run_scenario` from a sibling
`src/<protocol>/baseline.py` module.

**Architecture:** Hybrid reducer dispatch — `src/output/csv.py` owns the
writer + generic columns; each `src/<protocol>/summarise.py` exports a
pure reducer that returns only the protocol-specific columns. Per-trial
row granularity (one row per `(protocol, scenario, seed)`); T44 owns
multi-seed aggregation. Snowman `n=4` is skipped from the main CSV and
written to a sibling sanity file.

**Tech Stack:** Python 3 stdlib only (`csv`, `subprocess`, `pathlib`,
`dataclasses`, `math`). `unittest` for tests. The existing
`config.factory.build_run` + `RunHandle` seam from T27, the `EventLogger`
from T24, and `common.run_to_completion` from T39. No new dependencies.

---

## 0. Spec → plan drift (read first)

The companion design spec
`docs/superpowers/specs/2026-05-28-t40-output-format-design.md` §7 lays
out a six-commit migration. This plan implements that migration as a
sequence of TDD tasks, with one or more tasks per commit and explicit
commit-boundary tasks at the ends.

**One deviation from spec §7's commit list:** Commit 2 lands the writer
with a `_REDUCERS` table that imports from `pbft.summarise` /
`pos.summarise` / `snowman.summarise` — three modules that do not yet
exist after Commit 2. The spec says these are "stubs that raise
`NotImplementedError`." This plan implements that by **deferring the
real `_REDUCERS` table population to Commit 6, Task 18**, and starting
Commit 2 with an empty `_REDUCERS = {}` plus a unit-test-only
`monkeypatch` injection point. This avoids three `NotImplementedError`
stub modules in the tree between Commit 2 and Commit 6 — cleaner
intermediate states, and `make test` stays green at every commit.

Everything else in the spec is unchanged: column set, NaN dispatch,
Snowman n=4 policy, the wiki page's 13-section structure, the two
upstream `## Revisions` blocks, the determinism contract, the
acceptance criteria.

## 0.1 Pre-flight check (no code change)

**Run:**

```bash
make test
PYTHONPATH=src python3 -m pos.baseline
shasum -a 256 results/pos/baseline.csv > /tmp/t40-pre-pos-baseline.sha
git status
```

**Expected:** every suite green; `results/pos/baseline.csv` exists with
the T35-local schema; one sha256 line captured; tree clean (no
uncommitted changes from prior task work).

A clean tree is mandatory before Task 1. Capture the pre-migration
`make test` line counts and the pre-migration sha — they appear in the
handoff summary and in the experiment page's "pre/post" comparison.

---

# Commit 1 — Wiki contract

Lands the new `wiki/concepts/output-format.md`, two upstream
`## Revisions` blocks, `wiki/index.md` + `wiki/log.md` entries, and
the T35-sample-CSV backlog append-resolve. No code changes; `make test`
is unaffected.

## Task 1: Author `wiki/concepts/output-format.md`

**Why:** the contract bind for everything downstream. Closes the L-W4
M1 finding (15 forward-references resolve).

**Files:**
- Create: `wiki/concepts/output-format.md` (~250 lines)

### Step 1: Write the page

Author the 13 sections enumerated in design spec §2.1. The full
authoring is too long to inline here — work from the design spec
section-by-section. Key contract elements to preserve verbatim:

- **§3 Canonical schema.** Lift the full ~30-column table from
  `wiki/concepts/metric-reconciliation.md §T40 CSV schema implications`
  (lines 329–352 of that page). One row per column in the wiki table:
  `column | dtype | unit | populated-today? | extension-register-entry`.
  Mark the 18 columns from `COLUMN_ORDER` (design spec §3.2) as
  `populated-today? = yes`; mark the rest with the owning task and
  `populated-today? = no`.
- **§4 Today's writer subset.** List the 18 columns from `COLUMN_ORDER`
  verbatim. Reference `src/output/schema.py:COLUMN_ORDER` as the
  source-of-truth pointer.
- **§5 Per-protocol derivation rules.** Three subsections (PBFT, Casper
  FFG, Snowman) lifted from design spec §3.4's docstring. NWT
  subsection is one line: "Lands with T38.1."
- **§6 NaN dispatch policy.** Three rules verbatim from design spec
  §2.1 item 6.
- **§7 Snowman n=4 row policy.** Skip + sibling sanity CSV. Rationale
  cites `metric-reconciliation.md §Snowman parameter rescaling
  §Comparative-claim exclusion at n=4`.
- **§8 Row identity & ordering.** `run_id` format
  `<protocol>-n<n>[-<variant>]`. Lex sort by `(protocol, n, run_id,
  seed)`. `seed=42` is constant today.
- **§11 Extension register.** Table with at least the 11 entries
  enumerated in design spec §2.1 item 11.

### Step 2: Verify forward-references resolve

```bash
grep -rE "\[\[concepts/output-format" wiki/ | wc -l
```

**Expected:** 15 (matches the L-W4 M1 finding count). If less, an
earlier reference was missed; if more, a new reference was added since
the lint pass — fine, just note it in the log entry.

### Step 3: No commit yet

Continue to Task 2 — the commit is at the end of Commit 1's task block.

## Task 2: Two `## Revisions` blocks on upstream pages

**Files:**
- Modify: `wiki/concepts/event-log-schema.md` (append a `## Revisions`
  section at the bottom — replaces the implicit absence)
- Modify: `wiki/concepts/runner.md` (append to the existing or new
  `## Revisions` section)

### Step 1: Append to `event-log-schema.md`

Add at the bottom of the file:

```markdown
## Revisions

- **2026-05-28 by T40.** The unified comparative CSV produced by
  `src/output/csv.py` (see [[concepts/output-format]]) is a sibling
  consumer of the same `EventLogger.records` substrate this page
  describes. The two CSVs are *both* derived from the raw event log,
  with different column sets and different row granularities: the
  event-log CSV (this page) is one row per `EventRecord`, dispatch-
  ordered; the comparative CSV (output-format) is one row per
  `(protocol, scenario, seed)` simulation run.
```

### Step 2: Append to `runner.md`

Add (or extend if it already has one) the `## Revisions` section at the
bottom:

```markdown
## Revisions

- **2026-05-28 by T40.** The CSV-output gap noted in §What's outside
  the runner / *CSV columns and output formatting → T40* is closed.
  The runner stays at pass-through — no scheduler-layer adversary, no
  CSV output. The comparative CSV is owned by `src/output/csv.py`; see
  [[concepts/output-format]].
```

### Step 3: No commit yet

## Task 3: `wiki/index.md` + `wiki/log.md` entries

**Files:**
- Modify: `wiki/index.md` (insert under `## Concepts`)
- Modify: `wiki/log.md` (append at top)

### Step 1: `wiki/index.md` entry

Insert under `## Concepts`, alphabetically (between `node-model` and
`problem-statement` or wherever `o…` lands; the current list is
hand-sorted by topic-cluster rather than strict alphabetical — match
neighbouring entries' position by reading what's adjacent to the
related pages):

```markdown
- [[concepts/output-format]] — Canonical comparative CSV schema (T40):
  the full ~30-column contract pinned by [[concepts/metric-reconciliation]],
  the 18-column subset populated today (PBFT, Casper FFG, Snowman),
  per-protocol derivation rules, NaN dispatch policy (Snowman params,
  `f_max_*` mutual exclusion, pending vs structurally N/A), Snowman n=4
  skip + sibling `snowman_n4_sanity.csv` policy, row identity & ordering
  rule, determinism contract, and the extension register pointing
  pending columns at T38.1 / T41 / T44 / T51–T54 / T48–T49 / T58.
  Closes L-W4 M1's 15 forward-references.
```

### Step 2: `wiki/log.md` entry

Insert at the top (newest-first convention):

```markdown
## [2026-05-28] code | task 40 — wiki contract for output-format

- role: Engineer
- touched: `wiki/concepts/output-format.md` (new),
  `wiki/concepts/event-log-schema.md` (Revisions block),
  `wiki/concepts/runner.md` (Revisions block), `wiki/index.md`
- notes: Landed the canonical comparative-CSV contract page pinned by
  [[concepts/metric-reconciliation]] §T40. Wiki contract first, code
  scaffolding lands next per spec §7. Two upstream Revisions blocks
  acknowledge the new downstream consumer of the event-log substrate
  and close T39's documented CSV-output gap. Closes L-W4 M1's 15
  forward-references.
```

### Step 3: No commit yet

## Task 4: `TASKS.md` Backlog — append-resolve T35-sample-CSV item

**Files:**
- Modify: `TASKS.md` (Backlog item: "T35 sample CSV needs schema
  reconciliation in T40")

### Step 1: Append-resolve

Find the Backlog entry beginning `- **T35 sample CSV needs schema
reconciliation in T40** (introduced by T35 itself, 2026-05-25).` At the
end of that entry, append:

```markdown
 **Resolved 2026-05-28 by T40 (wiki contract):** [[concepts/output-format]]
landed with the binding column set + Snowman n=4 policy + extension
register. T35's three open semantic questions resolved: (i)
`commit_latency_ms` and `finality_latency_ms` are distinct columns with
explicit per-protocol formulas (§Per-protocol derivation rules); (ii)
`tps` is per-protocol per `metric-reconciliation.md §Throughput`; (iii)
row granularity is per-trial — `(run_id, scenario, seed)` — with T44
owning the aggregated sibling file. Code-side reconciliation (retiring
`src/pos/baseline.py`'s CSV writer + `results/pos/baseline.csv`)
follows in Commit 3 of this task.
```

### Step 2: No dashboard change yet

The In-Review flip + dashboard recompute lands in the final
TASKS.md-edit task (Task 25), not here. This task only resolves the
backlog item.

## Task 5: Commit 1

### Step 1: Verify clean intent

```bash
git status
git diff --stat
```

**Expected:** five files modified or created: `wiki/concepts/output-format.md`
(new), `wiki/concepts/event-log-schema.md`, `wiki/concepts/runner.md`,
`wiki/index.md`, `wiki/log.md`, `TASKS.md`. No `src/` or `tests/`
changes.

### Step 2: Commit

```bash
git add wiki/concepts/output-format.md \
        wiki/concepts/event-log-schema.md \
        wiki/concepts/runner.md \
        wiki/index.md wiki/log.md TASKS.md
git commit -m "task 40: wiki contract for output-format"
```

(Per `docs/workflow.md` the human runs the actual `git commit`; the
agent prepares the staged set.)

### Step 3: Confirm make test unaffected

```bash
make test
```

**Expected:** every suite green, identical line counts to the
pre-flight capture.

---

# Commit 2 — `src/output/` scaffolding + writer

Lands the new `src/output/` package with the writer's structure and
generic-column derivation. `_REDUCERS` starts empty (deviation §0);
writer-composition tests use a monkeypatched dispatch table.

## Task 6: `src/output/schema.py`

**Files:**
- Create: `src/output/__init__.py`
- Create: `src/output/schema.py`

### Step 1: Create `src/output/__init__.py`

```python
"""T40 — Unified output subsystem.

Today: one writer (write_unified_csv) + one orchestrator (baseline.main)
+ one schema bridge (ScenarioMeta, COLUMN_ORDER).
"""
from .csv import write_unified_csv
from .schema import COLUMN_ORDER, ScenarioMeta

__all__ = ("write_unified_csv", "ScenarioMeta", "COLUMN_ORDER")
```

(`csv` does not yet exist; the import lands in Task 7. Leave the
`__init__.py` referencing it now so we don't have to revisit.)

### Step 2: Create `src/output/schema.py`

```python
"""T40 — Unified CSV schema bridge.

Carries scenario identity through the pipeline:
  baseline.SCENARIOS  -> run_scenario(meta)  -> (records, result, meta)
                                                            |
                                                            v
                              write_unified_csv(path, runs of these triples)

COLUMN_ORDER is the today-writer projection of the full ~30-column
schema pinned by wiki/concepts/output-format.md §Canonical schema.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioMeta:
    """Identifies one (protocol, scenario, seed) row of the unified CSV."""
    run_id: str
    protocol: str
    n: int
    variant: str | None
    seed: int
    t_max: float


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

### Step 3: Confirm Python sees the package

```bash
PYTHONPATH=src python3 -c "from output.schema import ScenarioMeta, COLUMN_ORDER; print(len(COLUMN_ORDER))"
```

**Expected:** `18`. (Import of `output` package itself will fail until
Task 7 lands `csv.py`; this test uses the direct `output.schema`
import.)

## Task 7: `src/output/csv.py` — writer + generic columns

**Files:**
- Create: `src/output/csv.py`

### Step 1: Author the file

Copy verbatim from design spec §3.3, with one modification per
deviation §0: `_REDUCERS` starts as `{}` (empty dict). Add a docstring
note pointing forward to Task 18 where it gets populated.

The full source is in the design spec; reproduce it here without the
three `from <protocol>.summarise import …` lines, and with:

```python
# _REDUCERS is populated in Commit 6 (Task 18) once the three
# per-protocol summarise modules exist. Tests in Commit 2 inject a
# dispatch table via monkeypatch; tests in Commit 6 use the real one.
_REDUCERS: dict[str, object] = {}
```

Keep `_GENERIC_COLUMNS`, `_resolve_commit_hash`, `_total_msgs_per_acu`,
`_generic_cols`, `_format_row`, and `write_unified_csv` exactly as in
design spec §3.3.

### Step 2: Confirm import

```bash
PYTHONPATH=src python3 -c "from output import write_unified_csv, ScenarioMeta, COLUMN_ORDER; print('ok')"
```

**Expected:** `ok`.

### Step 3: No commit yet

## Task 8: `tests/output/test_generic_cols.py` — unit tests for `_generic_cols`

**Files:**
- Create: `tests/output/__init__.py` (empty file, Python package marker)
- Create: `tests/output/test_generic_cols.py`

### Step 1: Write the failing tests

```python
"""Unit tests for output.csv._generic_cols + _total_msgs_per_acu.
Synthetic EventRecords; no scheduler / Node / Network involvement.
"""
from __future__ import annotations

import math
import unittest
from unittest.mock import patch

from event_log import EventRecord
from output.csv import (
    _generic_cols,
    _total_msgs_per_acu,
    _resolve_commit_hash,
)
from output.schema import ScenarioMeta
from scheduler import RunResult


def _meta(protocol: str = "pbft", n: int = 4, run_id: str = "pbft-n4",
          variant: str | None = None, seed: int = 42,
          t_max: float = math.nan) -> ScenarioMeta:
    return ScenarioMeta(run_id=run_id, protocol=protocol, n=n,
                        variant=variant, seed=seed, t_max=t_max)


def _result(now: float = 1.234, processed: int = 100) -> RunResult:
    return RunResult(stopped_by="quiescence", now=now,
                     events_processed=processed, events_tombstoned=0)


class TestTotalMsgsPerAcu(unittest.TestCase):
    def test_normal_ratio(self):
        records = [
            EventRecord(t=0.1, node_id=0, event_type="delivery", seq=1,
                        fields={"msg_type": "x", "src": 0, "dst": 1}),
            EventRecord(t=0.2, node_id=1, event_type="delivery", seq=2,
                        fields={}),
            EventRecord(t=0.3, node_id=0, event_type="delivery", seq=3,
                        fields={}),
            EventRecord(t=0.4, node_id=0, event_type="decided", seq=-1,
                        fields={"instance_id": (0, 0)}),
        ]
        self.assertEqual(_total_msgs_per_acu(records, _result()), 3.0)

    def test_no_decided_returns_nan(self):
        records = [
            EventRecord(t=0.1, node_id=0, event_type="delivery", seq=1,
                        fields={}),
        ]
        v = _total_msgs_per_acu(records, _result())
        self.assertTrue(math.isnan(v))

    def test_no_deliveries_zero(self):
        records = [
            EventRecord(t=0.1, node_id=0, event_type="decided", seq=-1,
                        fields={"instance_id": (0, 0)}),
        ]
        self.assertEqual(_total_msgs_per_acu(records, _result()), 0.0)


class TestGenericCols(unittest.TestCase):
    def test_identity_passthrough(self):
        with patch("output.csv._resolve_commit_hash",
                   return_value="abc12345"):
            row = _generic_cols([], _result(),
                                _meta(run_id="pbft-n4", protocol="pbft",
                                      n=4, seed=42, t_max=20.0))
        self.assertEqual(row["run_id"], "pbft-n4")
        self.assertEqual(row["protocol"], "pbft")
        self.assertEqual(row["n"], 4)
        self.assertEqual(row["seed"], 42)
        self.assertEqual(row["commit_hash"], "abc12345")
        self.assertEqual(row["t_max"], 20.0)

    def test_keys_are_exactly_generic_columns(self):
        from output.csv import _GENERIC_COLUMNS
        with patch("output.csv._resolve_commit_hash", return_value="x"):
            row = _generic_cols([], _result(), _meta())
        self.assertEqual(set(row.keys()), set(_GENERIC_COLUMNS))


if __name__ == "__main__":
    unittest.main()
```

### Step 2: Run, confirm green

```bash
PYTHONPATH=src python3 -m unittest tests.output.test_generic_cols -v
```

**Expected:** 5 tests pass (3 in `TestTotalMsgsPerAcu`, 2 in
`TestGenericCols`).

### Step 3: No commit yet

## Task 9: `tests/output/test_csv.py` — writer composition with mocked reducers

**Files:**
- Create: `tests/output/test_csv.py`
- Create: `tests/output/fixtures/__init__.py` (empty marker)

### Step 1: Write the failing tests

```python
"""Unit tests for output.csv.write_unified_csv with monkeypatched
_REDUCERS. No protocol code involved.
"""
from __future__ import annotations

import csv as _csv
import math
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from event_log import EventRecord
from output.csv import write_unified_csv
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult


def _records():
    """One delivery + one decided so _total_msgs_per_acu = 1.0."""
    return [
        EventRecord(t=0.1, node_id=0, event_type="delivery", seq=1,
                    fields={"msg_type": "x", "src": 0, "dst": 1}),
        EventRecord(t=0.2, node_id=0, event_type="decided", seq=-1,
                    fields={"instance_id": (0, 0)}),
    ]


def _result():
    return RunResult(stopped_by="quiescence", now=1.0,
                     events_processed=2, events_tombstoned=0)


def _meta(protocol: str, n: int, run_id: str | None = None) -> ScenarioMeta:
    return ScenarioMeta(
        run_id=run_id or f"{protocol}-n{n}",
        protocol=protocol, n=n, variant=None, seed=42, t_max=math.nan,
    )


def _ok_protocol_cols(records, result, meta):
    """Mock reducer: returns all 11 non-generic columns with sentinel
    values, NaN for Snowman params unless protocol is snowman."""
    is_sn = meta.protocol == "snowman"
    return {
        "commit_latency_ms":      100.0,
        "finality_latency_ms":    100.0,
        "tps":                    1.0,
        "consensus_msgs_per_acu": 1.0,
        "success_rate":           1.0,
        "fork_rate":              0.0,
        "K":             3   if is_sn else float("nan"),
        "alpha_p":       2   if is_sn else float("nan"),
        "alpha_c":       3   if is_sn else float("nan"),
        "beta":          15  if is_sn else float("nan"),
        "alpha_c_over_K": 1.0 if is_sn else float("nan"),
    }


_REDUCERS_OK = {
    "pbft":       _ok_protocol_cols,
    "casper-ffg": _ok_protocol_cols,
    "snowman":    _ok_protocol_cols,
}


class TestWriteUnifiedCsv(unittest.TestCase):
    def test_three_runs_one_per_protocol(self):
        runs = [
            (_records(), _result(), _meta("pbft", 4)),
            (_records(), _result(), _meta("casper-ffg", 7)),
            (_records(), _result(), _meta("snowman", 7)),
        ]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK), \
                 patch("output.csv._resolve_commit_hash",
                       return_value="abc12345"):
                write_unified_csv(path, runs)
            with path.open() as fh:
                reader = _csv.DictReader(fh)
                rows = list(reader)
                self.assertEqual(reader.fieldnames, list(COLUMN_ORDER))
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [r["protocol"] for r in rows],
            ["casper-ffg", "pbft", "snowman"],  # lex sort
        )

    def test_skips_snowman_n4(self):
        runs = [
            (_records(), _result(), _meta("snowman", 4)),
            (_records(), _result(), _meta("snowman", 7)),
        ]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK), \
                 patch("output.csv._resolve_commit_hash",
                       return_value="abc12345"):
                write_unified_csv(path, runs)
            with path.open() as fh:
                rows = list(_csv.DictReader(fh))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["protocol"], "snowman")
        self.assertEqual(rows[0]["n"], "7")

    def test_empty_runs_header_only(self):
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK):
                write_unified_csv(path, [])
            with path.open() as fh:
                lines = fh.read().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], ",".join(COLUMN_ORDER))

    def test_unknown_protocol_raises(self):
        runs = [(_records(), _result(), _meta("foo", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK):
                with self.assertRaises(KeyError) as cm:
                    write_unified_csv(path, runs)
        self.assertIn("foo", str(cm.exception))

    def test_reducer_returns_generic_col_raises(self):
        def _bad(records, result, meta):
            d = _ok_protocol_cols(records, result, meta)
            d["n"] = 99   # generic column collision
            return d
        runs = [(_records(), _result(), _meta("pbft", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", {"pbft": _bad}):
                with self.assertRaises(ValueError) as cm:
                    write_unified_csv(path, runs)
        self.assertIn("generic", str(cm.exception))
        self.assertIn("n", str(cm.exception))

    def test_reducer_returns_unknown_col_raises(self):
        def _bad(records, result, meta):
            d = _ok_protocol_cols(records, result, meta)
            d["foobar"] = 1.0   # not in COLUMN_ORDER
            return d
        runs = [(_records(), _result(), _meta("pbft", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", {"pbft": _bad}):
                with self.assertRaises(ValueError) as cm:
                    write_unified_csv(path, runs)
        self.assertIn("unknown", str(cm.exception))
        self.assertIn("foobar", str(cm.exception))

    def test_parent_directory_auto_created(self):
        runs = [(_records(), _result(), _meta("pbft", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "deep" / "tree" / "baseline.csv"
            with patch("output.csv._REDUCERS", _REDUCERS_OK), \
                 patch("output.csv._resolve_commit_hash",
                       return_value="x"):
                write_unified_csv(path, runs)
            self.assertTrue(path.exists())

    def test_float_formatting(self):
        """commit_latency_ms is .9f, tps is .6f."""
        def _custom(records, result, meta):
            d = _ok_protocol_cols(records, result, meta)
            d["commit_latency_ms"] = 312.500000123456
            d["tps"] = 1.23456789
            return d
        runs = [(_records(), _result(), _meta("pbft", 4))]
        with TemporaryDirectory() as td:
            path = Path(td) / "baseline.csv"
            with patch("output.csv._REDUCERS", {"pbft": _custom}), \
                 patch("output.csv._resolve_commit_hash",
                       return_value="x"):
                write_unified_csv(path, runs)
            row = next(iter(_csv.DictReader(path.open())))
        self.assertEqual(row["commit_latency_ms"], "312.500000123")
        self.assertEqual(row["tps"],               "1.234568")


if __name__ == "__main__":
    unittest.main()
```

### Step 2: Run, confirm green

```bash
PYTHONPATH=src python3 -m unittest tests.output.test_csv -v
```

**Expected:** 8 tests pass.

### Step 3: No commit yet

## Task 10: Makefile target `test-output`

**Files:**
- Modify: `Makefile`

### Step 1: Locate the existing test target

```bash
grep -nE "^test|^\.PHONY" Makefile | head -20
```

### Step 2: Add the new target

Append at the bottom of the file (alphabetical with neighbouring
per-suite targets if the Makefile uses that pattern; else group with
related targets):

```makefile

.PHONY: test-output
test-output:
	PYTHONPATH=src python3 -m unittest discover -s tests/output -v
```

If `make test` aggregates per-suite targets, add `test-output` to its
dependency list. Otherwise (if `make test` uses `unittest discover` at
the top level), no change needed — the new test files are auto-
discovered.

### Step 3: Verify

```bash
make test-output
make test
```

**Expected:** both green. `make test` line count for `tests.output`
suite shows 13 (5 in `test_generic_cols` + 8 in `test_csv`).

### Step 4: No commit yet

## Task 11: Commit 2

### Step 1: Verify clean intent

```bash
git status
```

**Expected:** new files
`src/output/__init__.py`, `src/output/schema.py`, `src/output/csv.py`,
`tests/output/__init__.py`, `tests/output/test_generic_cols.py`,
`tests/output/test_csv.py`, `tests/output/fixtures/__init__.py`;
modified `Makefile`. No other changes.

### Step 2: Commit

```bash
git add src/output/ tests/output/ Makefile
git commit -m "task 40: src/output writer + scaffolding"
```

### Step 3: Confirm green

```bash
make test
```

**Expected:** every suite green, including the new `tests.output`.

---

# Commit 3 — Harmonise `src/pos/baseline.py` + `pos.summarise`

Lifts the FFG epoch-finalisation logic from the old `_summarise` into a
reducer; retires the T35-local CSV writer. The integration test stays
green throughout.

## Task 12: `tests/pos/test_summarise.py` — red

**Files:**
- Create: `tests/pos/test_summarise.py`

### Step 1: Write the failing tests

```python
"""Unit tests for pos.summarise. Synthetic records modelling two
finalised epochs at n=4 honest baseline.
"""
from __future__ import annotations

import math
import unittest

from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult


def _meta(n: int = 4, variant: str | None = "uniform") -> ScenarioMeta:
    return ScenarioMeta(
        run_id=f"casper-ffg-n{n}-{variant or 'none'}",
        protocol="casper-ffg", n=n, variant=variant,
        seed=42, t_max=20.0,
    )


def _result():
    return RunResult(stopped_by="deadline", now=20.0,
                     events_processed=200, events_tombstoned=0)


def _epoch_finalised_records(n: int) -> list[EventRecord]:
    """One decided event per node for epoch 1, all at t = 5.000000001."""
    return [
        EventRecord(t=5.000000001, node_id=i, event_type="decided",
                    seq=-1, fields={"instance_id": 1})
        for i in range(n)
    ]


class TestSummarise(unittest.TestCase):
    def test_keys_are_protocol_columns_only(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(), _meta())
        expected_keys = {
            "commit_latency_ms", "finality_latency_ms", "tps",
            "consensus_msgs_per_acu", "success_rate", "fork_rate",
            "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
        }
        self.assertEqual(set(row.keys()), expected_keys)

    def test_finality_latency_ms_median(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(), _meta())
        # 5.000000001 s * 1000 = 5000.000001 ms
        self.assertAlmostEqual(row["finality_latency_ms"],
                               5000.000001, places=6)

    def test_snowman_params_are_nan(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(), _meta())
        for col in ("K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K"):
            self.assertTrue(math.isnan(row[col]),
                            f"{col} must be NaN for Casper FFG")

    def test_no_decided_returns_nan_latency(self):
        from pos.summarise import summarise
        row = summarise([], _result(), _meta())
        self.assertTrue(math.isnan(row["commit_latency_ms"]))
        self.assertTrue(math.isnan(row["finality_latency_ms"]))
        self.assertEqual(row["success_rate"], 0.0)

    def test_fork_rate_zero_at_honest_baseline(self):
        from pos.summarise import summarise
        row = summarise(_epoch_finalised_records(4), _result(), _meta())
        self.assertEqual(row["fork_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
```

### Step 2: Run, confirm FAIL with `ImportError`

```bash
PYTHONPATH=src python3 -m unittest tests.pos.test_summarise -v
```

**Expected:** every test fails with `ImportError: cannot import name
'summarise' from 'pos.summarise'`.

## Task 13: `src/pos/summarise.py` — green

**Files:**
- Create: `src/pos/summarise.py`

### Step 1: Implement

```python
"""T40 — Casper FFG reducer: maps (EventLogger.records, RunResult,
ScenarioMeta) to the protocol-specific columns of the unified CSV.

Per-column formulas pinned by wiki/concepts/output-format.md §Per-
protocol derivation rules / Casper FFG.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import math
import statistics
from typing import Any

from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult


def summarise(records: list[EventRecord],
              result: RunResult,
              meta: ScenarioMeta) -> dict[str, Any]:
    decided = [r for r in records if r.event_type == "decided"]
    deliveries = [r for r in records if r.event_type == "delivery"]

    # Per-node finalisation time of epoch 1 — the first finalised epoch
    # in every scenario. Median across nodes is the headline latency.
    epoch1 = [r.t for r in decided if r.fields.get("instance_id") == 1]
    if epoch1:
        latency_ms = statistics.median(epoch1) * 1000.0
        commit_latency_ms = latency_ms      # honest path: commit ≡ finality
        finality_latency_ms = latency_ms
        success_rate = 1.0
    else:
        commit_latency_ms = float("nan")
        finality_latency_ms = float("nan")
        success_rate = 0.0

    # Throughput: decided events per simulated second over the window.
    if not math.isnan(meta.t_max):
        tps = len(decided) / meta.t_max
    else:
        tps = float("nan")

    # Consensus messages per ACU: deliveries / decided. Honest path has
    # one decided per epoch per node; ACU is one finalised checkpoint
    # so we divide by decided count (= n × #epochs).
    if decided:
        consensus_msgs_per_acu = len(deliveries) / len(decided)
    else:
        consensus_msgs_per_acu = float("nan")

    return {
        "commit_latency_ms":      commit_latency_ms,
        "finality_latency_ms":    finality_latency_ms,
        "tps":                    tps,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "success_rate":           success_rate,
        "fork_rate":              0.0,   # honest baseline; never forks
        "K":                      float("nan"),
        "alpha_p":                float("nan"),
        "alpha_c":                float("nan"),
        "beta":                   float("nan"),
        "alpha_c_over_K":         float("nan"),
    }
```

### Step 2: Run, confirm green

```bash
PYTHONPATH=src python3 -m unittest tests.pos.test_summarise -v
```

**Expected:** 5 tests pass.

### Step 3: No commit yet

## Task 14: Harmonise `src/pos/baseline.py`

**Files:**
- Modify: `src/pos/baseline.py`

### Step 1: Read the current file

```bash
PYTHONPATH=src python3 -c "import inspect, pos.baseline; print(inspect.getsourcefile(pos.baseline))"
```

Open and locate the existing `SCENARIOS`, `_run_scenario`, `_summarise`,
`_COLUMNS`, `write_baseline_csv`, `main` symbols (current `src/pos/
baseline.py` is 125 LoC; the auggie pickup-index map applies).

### Step 2: Rewrite

Replace the file's contents with:

```python
"""Casper FFG honest baseline scenarios.

SCENARIOS is the list of (n, variant) scenarios run by
src/output/baseline.py and asserted by
tests/integration/test_pos_baseline.py. run_scenario(meta) builds the
FFG stack at meta.n with the meta.variant stake distribution, runs to
meta.t_max, and returns the (records, result, meta) triple the unified
CSV writer consumes.

Design spec: docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import math

from common import run_to_completion
from config import build_run
from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult

# Existing config + factory helpers (lifted unchanged from the old
# _config / _factory). Their bodies are protocol-specific; keep them
# byte-identical with the pre-harmonisation version so determinism
# holds.

_T_MAX = 20.0


def _uniform(n: int) -> dict[int, float]:
    return {i: 1.0 for i in range(n)}


def _nonuniform_n4() -> dict[int, float]:
    return {0: 0.4, 1: 0.3, 2: 0.2, 3: 0.1}


def _stake_table(n: int, variant: str | None) -> dict[int, float]:
    if variant == "nonuniform":
        assert n == 4, "nonuniform is only defined at n=4 today"
        return _nonuniform_n4()
    return _uniform(n)


# … keep _config(n, variant) and _factory(n) here, byte-identical with
#   the prior versions. The only signature change is _config gaining
#   the `variant` parameter (was implicit via stake_table arg).


SCENARIOS: tuple[ScenarioMeta, ...] = (
    ScenarioMeta(run_id="casper-ffg-n4-uniform",     protocol="casper-ffg",
                 n=4,  variant="uniform",    seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="casper-ffg-n7-uniform",     protocol="casper-ffg",
                 n=7,  variant="uniform",    seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="casper-ffg-n10-uniform",    protocol="casper-ffg",
                 n=10, variant="uniform",    seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="casper-ffg-n4-nonuniform",  protocol="casper-ffg",
                 n=4,  variant="nonuniform", seed=42, t_max=_T_MAX),
)


def run_scenario(meta: ScenarioMeta
                 ) -> tuple[list[EventRecord], RunResult, ScenarioMeta]:
    config = _config(meta.n, meta.variant)
    handle = build_run(config, meta.seed, _factory(meta.n))
    t_max = None if math.isnan(meta.t_max) else meta.t_max
    result, logger = run_to_completion(handle, t_max=t_max)
    return logger.records, result, meta
```

**Critical:** preserve `_config` and `_factory` byte-identical (apart
from `_config`'s new `variant` parameter that dispatches to
`_stake_table`). The integration test's existing assertions depend on
the exact same event stream as before.

Delete the symbols: `_summarise`, `write_baseline_csv`, `_COLUMNS`,
`main`, the `csv` + `statistics` + `Path` imports if no longer needed,
and the `if __name__ == "__main__":` block.

### Step 3: Update the integration test

**Files:**
- Modify: `tests/integration/test_pos_baseline.py`

Read the current file; locate the helper trio (`_config`, `_factory`,
`_run`). Replace with:

```python
from pos.baseline import SCENARIOS, run_scenario
```

Replace the test loop body that calls `_run(n, …)` with
`records, result, meta = run_scenario(scenario)` inside a `for scenario
in SCENARIOS` loop. Test assertions stay verbatim.

### Step 4: Delete the tracked T35-local CSV

```bash
git rm results/pos/baseline.csv
```

Verify `.gitignore` covers re-creation:

```bash
grep -E "results/pos" .gitignore
```

**Expected:** either `results/pos/` or `results/pos/baseline.csv`
present. If absent, add `results/pos/` to `.gitignore` (the directory
itself can stay, since other future POS-specific artifacts may need it
— gitignoring the dir is fine because no other tracked file lives
there).

### Step 5: Run

```bash
make test
PYTHONPATH=src python3 -m unittest tests.integration.test_pos_baseline -v
PYTHONPATH=src python3 -m unittest tests.pos.test_summarise -v
```

**Expected:** every suite green; integration test produces the same
event-stream snapshot as before (the existing byte-identical-run
assertion still holds; the event stream itself hasn't changed).

If the integration test fails: the harmonisation broke determinism.
Most likely cause: an unintended change to `_config` or `_factory`.
Diff against the pre-harmonisation version and restore byte-identical
behaviour.

### Step 6: No commit yet

## Task 15: Commit 3

### Step 1: Verify

```bash
git status
git diff --stat
```

**Expected:** new files `src/pos/summarise.py`, `tests/pos/test_summarise.py`;
modified `src/pos/baseline.py`, `tests/integration/test_pos_baseline.py`;
deleted `results/pos/baseline.csv` (possibly added `.gitignore`).

### Step 2: Commit

```bash
git add src/pos/summarise.py src/pos/baseline.py \
        tests/pos/test_summarise.py tests/integration/test_pos_baseline.py \
        .gitignore
git rm results/pos/baseline.csv 2>/dev/null || true   # already staged
git commit -m "task 40: harmonise src/pos/baseline; add pos.summarise"
```

### Step 3: Confirm green

```bash
make test
```

**Expected:** every suite green.

---

# Commit 4 — `src/pbft/baseline.py` + `pbft.summarise`

Same pattern as Commit 3: write the reducer test first (red), implement
the reducer (green), then lift the scenarios out of the integration
test into a new baseline module.

## Task 16: `tests/pbft/test_summarise.py` — red

**Files:**
- Create: `tests/pbft/test_summarise.py`

### Step 1: Write the failing tests

```python
"""Unit tests for pbft.summarise. Synthetic records modelling one
PBFT instance going PRE-PREPARE → PREPARE quorum → COMMIT quorum →
decided at n=4 honest baseline.
"""
from __future__ import annotations

import math
import unittest

from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult


def _meta(n: int = 4) -> ScenarioMeta:
    return ScenarioMeta(run_id=f"pbft-n{n}", protocol="pbft", n=n,
                        variant=None, seed=42, t_max=math.nan)


def _result():
    return RunResult(stopped_by="quiescence", now=0.5,
                     events_processed=50, events_tombstoned=0)


def _pbft_instance_records(n: int, t_commit: float = 0.4
                           ) -> list[EventRecord]:
    """n decided events at t_commit for instance_id=(0, 0)."""
    # Mock some delivery events too (consensus_msgs_per_acu ≠ NaN).
    recs: list[EventRecord] = []
    for i in range(n):
        recs.append(EventRecord(t=t_commit * 0.5, node_id=i,
                                event_type="delivery", seq=i,
                                fields={"msg_type": "PRE-PREPARE",
                                        "src": 0, "dst": i}))
    for i in range(n):
        recs.append(EventRecord(t=t_commit, node_id=i,
                                event_type="decided", seq=-1,
                                fields={"instance_id": (0, 0)}))
    return recs


class TestSummarise(unittest.TestCase):
    def test_keys_are_protocol_columns_only(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _meta(4))
        expected_keys = {
            "commit_latency_ms", "finality_latency_ms", "tps",
            "consensus_msgs_per_acu", "success_rate", "fork_rate",
            "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
        }
        self.assertEqual(set(row.keys()), expected_keys)

    def test_commit_equals_finality_for_pbft(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4, t_commit=0.4),
                        _result(), _meta(4))
        self.assertEqual(row["commit_latency_ms"],
                         row["finality_latency_ms"])
        self.assertAlmostEqual(row["commit_latency_ms"], 400.0,
                               places=6)

    def test_fork_rate_zero_by_construction(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _meta(4))
        self.assertEqual(row["fork_rate"], 0.0)

    def test_snowman_params_are_nan(self):
        from pbft.summarise import summarise
        row = summarise(_pbft_instance_records(4), _result(), _meta(4))
        for col in ("K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K"):
            self.assertTrue(math.isnan(row[col]))

    def test_no_decided_returns_nan_latency(self):
        from pbft.summarise import summarise
        row = summarise([], _result(), _meta(4))
        self.assertTrue(math.isnan(row["commit_latency_ms"]))
        self.assertEqual(row["success_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
```

### Step 2: Confirm FAIL

```bash
PYTHONPATH=src python3 -m unittest tests.pbft.test_summarise -v
```

**Expected:** `ImportError` on `pbft.summarise`.

## Task 17: `src/pbft/summarise.py` — green

**Files:**
- Create: `src/pbft/summarise.py`

### Step 1: Implement

```python
"""T40 — PBFT reducer.

Per-block deterministic finality: commit_latency = finality_latency.
fork_rate = 0 by construction (PBFT cannot fork below f).

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import math
import statistics
from typing import Any

from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult


def summarise(records: list[EventRecord],
              result: RunResult,
              meta: ScenarioMeta) -> dict[str, Any]:
    decided = [r for r in records if r.event_type == "decided"]
    deliveries = [r for r in records if r.event_type == "delivery"]

    if decided:
        # Median per-node decision time for the first decided instance.
        first_inst = decided[0].fields.get("instance_id")
        first_inst_ts = [r.t for r in decided
                         if r.fields.get("instance_id") == first_inst]
        latency_ms = statistics.median(first_inst_ts) * 1000.0
        success_rate = 1.0
    else:
        latency_ms = float("nan")
        success_rate = 0.0

    # Throughput on the quiescence path: decided events / final t.
    if decided and result.now > 0:
        tps = len(decided) / result.now
    else:
        tps = float("nan")

    if decided:
        consensus_msgs_per_acu = len(deliveries) / len(decided)
    else:
        consensus_msgs_per_acu = float("nan")

    return {
        "commit_latency_ms":      latency_ms,
        "finality_latency_ms":    latency_ms,   # PBFT: commit ≡ finality
        "tps":                    tps,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "success_rate":           success_rate,
        "fork_rate":              0.0,
        "K":                      float("nan"),
        "alpha_p":                float("nan"),
        "alpha_c":                float("nan"),
        "beta":                   float("nan"),
        "alpha_c_over_K":         float("nan"),
    }
```

### Step 2: Confirm green

```bash
PYTHONPATH=src python3 -m unittest tests.pbft.test_summarise -v
```

**Expected:** 5 tests pass.

### Step 3: No commit yet

## Task 18: `src/pbft/baseline.py` + integration-test edit

**Files:**
- Create: `src/pbft/baseline.py`
- Modify: `tests/integration/test_pbft_baseline.py`

### Step 1: Read current integration-test helpers

```bash
grep -nE "^def _|^class " tests/integration/test_pbft_baseline.py
```

Identify the `_config(n)`, `_factory(n)`, `_run(n, global_seed=42)`
helpers (locations from the auggie pickup-index).

### Step 2: Lift to `src/pbft/baseline.py`

Create the file with the design spec §3.5 shape, copying `_config` and
`_factory` byte-identical from the integration test:

```python
"""PBFT honest baseline scenarios.

SCENARIOS is the list of n values run by src/output/baseline.py and
asserted by tests/integration/test_pbft_baseline.py. run_scenario(meta)
builds the PBFT stack at meta.n, runs to quiescence, and returns the
(records, result, meta) triple the unified CSV writer consumes.

Design spec: docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import math

from common import run_to_completion
from config import build_run
from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult


# --- Config + factory: lifted byte-identical from the prior integration
# --- test helpers _config / _factory (see test_pbft_baseline.py history).

def _config(n: int):
    ...   # body verbatim from the prior test's _config


def _factory(n: int):
    ...   # body verbatim from the prior test's _factory


SCENARIOS: tuple[ScenarioMeta, ...] = (
    ScenarioMeta(run_id="pbft-n4",  protocol="pbft", n=4,
                 variant=None, seed=42, t_max=math.nan),
    ScenarioMeta(run_id="pbft-n7",  protocol="pbft", n=7,
                 variant=None, seed=42, t_max=math.nan),
    ScenarioMeta(run_id="pbft-n10", protocol="pbft", n=10,
                 variant=None, seed=42, t_max=math.nan),
)


def run_scenario(meta: ScenarioMeta
                 ) -> tuple[list[EventRecord], RunResult, ScenarioMeta]:
    config = _config(meta.n)
    handle = build_run(config, meta.seed, _factory(meta.n))
    t_max = None if math.isnan(meta.t_max) else meta.t_max
    result, logger = run_to_completion(handle, t_max=t_max)
    return logger.records, result, meta
```

### Step 3: Update integration test

Replace the helper trio block in `tests/integration/test_pbft_baseline.py`
with:

```python
from pbft.baseline import SCENARIOS, run_scenario
```

Replace `_run(n, global_seed=42)` callsites in test methods with
`run_scenario(scenario)` where `scenario in SCENARIOS`. The test class
becomes a `for scenario in SCENARIOS: with self.subTest(...)` loop.
Assertions stay verbatim.

### Step 4: Run

```bash
make test
PYTHONPATH=src python3 -m unittest tests.integration.test_pbft_baseline -v
PYTHONPATH=src python3 -m unittest tests.pbft.test_summarise -v
```

**Expected:** every suite green. Event-stream determinism preserved.

## Task 19: Commit 4

### Step 1: Verify + commit

```bash
git status
git add src/pbft/summarise.py src/pbft/baseline.py \
        tests/pbft/test_summarise.py tests/integration/test_pbft_baseline.py
git commit -m "task 40: src/pbft/baseline + pbft.summarise"
```

### Step 2: Confirm green

```bash
make test
```

---

# Commit 5 — `src/snowman/baseline.py` + `snowman.summarise`

Same pattern as Commit 4, plus the additional `sanity_row()` export
for the n=4 rescaling-boundary file.

## Task 20: `tests/snowman/test_summarise.py` — red

**Files:**
- Create: `tests/snowman/test_summarise.py`

### Step 1: Write the failing tests

```python
"""Unit tests for snowman.summarise + snowman.summarise.sanity_row.
Synthetic records modelling one Snowman block reaching counter β.
"""
from __future__ import annotations

import csv as _csv
import math
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from event_log import EventRecord
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult


def _meta(n: int) -> ScenarioMeta:
    return ScenarioMeta(run_id=f"snowman-n{n}", protocol="snowman",
                        n=n, variant=None, seed=42, t_max=20.0)


def _result():
    return RunResult(stopped_by="deadline", now=20.0,
                     events_processed=300, events_tombstoned=0)


def _snowman_records(n: int, t_decided: float = 1.0
                     ) -> list[EventRecord]:
    """n decided events at t_decided, plus some mock query deliveries."""
    recs: list[EventRecord] = []
    for i in range(n):
        recs.append(EventRecord(t=t_decided * 0.1, node_id=i,
                                event_type="delivery", seq=i,
                                fields={"msg_type": "QUERY",
                                        "src": 0, "dst": i}))
    for i in range(n):
        recs.append(EventRecord(t=t_decided, node_id=i,
                                event_type="decided", seq=-1,
                                fields={"block_hash": "x"}))
    return recs


class TestSummarise(unittest.TestCase):
    def test_keys_are_protocol_columns_only(self):
        from snowman.summarise import summarise
        row = summarise(_snowman_records(7), _result(), _meta(7))
        expected = {
            "commit_latency_ms", "finality_latency_ms", "tps",
            "consensus_msgs_per_acu", "success_rate", "fork_rate",
            "K", "alpha_p", "alpha_c", "beta", "alpha_c_over_K",
        }
        self.assertEqual(set(row.keys()), expected)

    def test_n7_rescale(self):
        """At n=7 the rescaling rule gives K=6, α_p=4, α_c=5, β=15,
        α_c/K = 5/6."""
        from snowman.summarise import summarise
        row = summarise(_snowman_records(7), _result(), _meta(7))
        self.assertEqual(row["K"], 6)
        self.assertEqual(row["alpha_p"], 4)
        self.assertEqual(row["alpha_c"], 5)
        self.assertEqual(row["beta"], 15)
        self.assertAlmostEqual(row["alpha_c_over_K"], 5/6, places=6)

    def test_n10_rescale(self):
        from snowman.summarise import summarise
        row = summarise(_snowman_records(10), _result(), _meta(10))
        self.assertEqual(row["K"], 9)
        self.assertEqual(row["alpha_p"], 5)
        self.assertEqual(row["alpha_c"], 8)
        self.assertEqual(row["beta"], 15)
        self.assertAlmostEqual(row["alpha_c_over_K"], 8/9, places=6)

    def test_n25_caps_at_production(self):
        """At n=25 the rule caps K at 20 (production parameters)."""
        from snowman.summarise import summarise
        row = summarise(_snowman_records(25), _result(), _meta(25))
        self.assertEqual(row["K"], 20)
        self.assertEqual(row["alpha_c"], 16)
        self.assertAlmostEqual(row["alpha_c_over_K"], 0.8, places=6)


class TestSanityRow(unittest.TestCase):
    def test_writes_one_row_to_sibling_file(self):
        from snowman.summarise import sanity_row
        with TemporaryDirectory() as td:
            path = Path(td) / "snowman_n4_sanity.csv"
            sanity_row(_snowman_records(4), _result(), _meta(4), path)
            with path.open() as fh:
                reader = _csv.DictReader(fh)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)
        # Same 18 columns as main schema, plus the degenerate flag.
        self.assertEqual(fieldnames,
                         list(COLUMN_ORDER) + ["snowman_degenerate_n4"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["protocol"], "snowman")
        self.assertEqual(rows[0]["n"], "4")
        self.assertEqual(rows[0]["snowman_degenerate_n4"], "True")
        # n=4 rescaling: K=3, α_p=2, α_c=3, β=15, α_c/K=1.0
        self.assertEqual(rows[0]["K"], "3")
        self.assertEqual(rows[0]["alpha_c"], "3")


if __name__ == "__main__":
    unittest.main()
```

### Step 2: Confirm FAIL

```bash
PYTHONPATH=src python3 -m unittest tests.snowman.test_summarise -v
```

## Task 21: `src/snowman/summarise.py` — green

**Files:**
- Create: `src/snowman/summarise.py`

### Step 1: Implement

```python
"""T40 — Snowman reducer + sanity-row writer.

Per-block probabilistic finality: counter-β is finality
(commit_latency = finality_latency in the implemented honest baseline).

Snowman parameter columns populated per metric-reconciliation.md
§Snowman parameter rescaling — rescaling rule reproduced here as the
canonical Python source.

sanity_row writes the n=4 degenerate-boundary row to a sibling CSV.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import csv as _csv
import math
import statistics
from pathlib import Path
from typing import Any

from event_log import EventRecord
from output.schema import COLUMN_ORDER, ScenarioMeta
from scheduler import RunResult


def _rescale(n: int) -> dict[str, Any]:
    """Snowman (K, α_p, α_c, β, α_c/K) rescaling per metric-
    reconciliation.md §Snowman parameter rescaling."""
    K = min(20, n - 1)
    alpha_p = K // 2 + 1
    alpha_c = math.ceil(0.8 * K)
    beta = 15
    return {
        "K":              K,
        "alpha_p":        alpha_p,
        "alpha_c":        alpha_c,
        "beta":           beta,
        "alpha_c_over_K": alpha_c / K if K else float("nan"),
    }


def summarise(records: list[EventRecord],
              result: RunResult,
              meta: ScenarioMeta) -> dict[str, Any]:
    decided = [r for r in records if r.event_type == "decided"]
    deliveries = [r for r in records if r.event_type == "delivery"]

    if decided:
        # Median per-node decision time for the first block accepted.
        first_block = decided[0].fields.get("block_hash")
        first_block_ts = [r.t for r in decided
                          if r.fields.get("block_hash") == first_block]
        latency_ms = statistics.median(first_block_ts) * 1000.0
        success_rate = 1.0
    else:
        latency_ms = float("nan")
        success_rate = 0.0

    if not math.isnan(meta.t_max):
        tps = len(decided) / meta.t_max
    else:
        tps = float("nan")

    if decided:
        consensus_msgs_per_acu = len(deliveries) / len(decided)
    else:
        consensus_msgs_per_acu = float("nan")

    row: dict[str, Any] = {
        "commit_latency_ms":      latency_ms,
        "finality_latency_ms":    latency_ms,
        "tps":                    tps,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "success_rate":           success_rate,
        "fork_rate":              0.0,   # honest baseline; pre-β flips
                                         # would land here at T54+.
    }
    row.update(_rescale(meta.n))
    return row


def sanity_row(records: list[EventRecord],
               result: RunResult,
               meta: ScenarioMeta,
               path: Path) -> None:
    """Write the Snowman n=4 rescaling-boundary row to a sibling CSV.

    Same 18-column schema as the main CSV plus a `snowman_degenerate_n4`
    boolean flag column. Header-row + one data row.
    """
    from output.csv import _format_row, _generic_cols   # local import to
                                                         # avoid cycle

    if meta.protocol != "snowman" or meta.n != 4:
        raise ValueError(
            f"sanity_row only valid for Snowman n=4, got "
            f"{meta.protocol!r} n={meta.n}"
        )
    generic = _generic_cols(records, result, meta)
    protocol = summarise(records, result, meta)
    row = {**generic, **protocol, "snowman_degenerate_n4": True}

    fieldnames = list(COLUMN_ORDER) + ["snowman_degenerate_n4"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = _csv.DictWriter(fh, fieldnames=fieldnames,
                                 extrasaction="raise")
        writer.writeheader()
        formatted = _format_row({k: row[k] for k in COLUMN_ORDER})
        formatted["snowman_degenerate_n4"] = str(row["snowman_degenerate_n4"])
        writer.writerow(formatted)
```

### Step 2: Confirm green

```bash
PYTHONPATH=src python3 -m unittest tests.snowman.test_summarise -v
```

**Expected:** 6 tests pass.

## Task 22: `src/snowman/baseline.py` + integration-test edit

**Files:**
- Create: `src/snowman/baseline.py`
- Modify: `tests/integration/test_snowman_baseline.py`

### Step 1: Lift `_config / _factory / _T_MAX` from the integration test

Open `tests/integration/test_snowman_baseline.py`; locate the helpers
(`_T_MAX`, `_config`, `_factory`, `_run`). Lift their bodies into
`src/snowman/baseline.py` byte-identical:

```python
"""Snowman honest baseline scenarios.

Includes n=4 in SCENARIOS — the rescaling-boundary case
(metric-reconciliation §Snowman parameter rescaling §Comparative-claim
exclusion at n=4). The unified CSV writer skips n=4 from the main file
and src/output/baseline.py writes the sanity row to a sibling.

Design spec: docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import math

from common import run_to_completion
from config import build_run
from event_log import EventRecord
from output.schema import ScenarioMeta
from scheduler import RunResult


_T_MAX = 20.0


def _config(n: int):
    ...   # body verbatim from the prior test's _config


def _factory(n: int):
    ...   # body verbatim from the prior test's _factory


SCENARIOS: tuple[ScenarioMeta, ...] = (
    ScenarioMeta(run_id="snowman-n4",  protocol="snowman", n=4,
                 variant=None, seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="snowman-n7",  protocol="snowman", n=7,
                 variant=None, seed=42, t_max=_T_MAX),
    ScenarioMeta(run_id="snowman-n10", protocol="snowman", n=10,
                 variant=None, seed=42, t_max=_T_MAX),
)


def run_scenario(meta: ScenarioMeta
                 ) -> tuple[list[EventRecord], RunResult, ScenarioMeta]:
    config = _config(meta.n)
    handle = build_run(config, meta.seed, _factory(meta.n))
    t_max = None if math.isnan(meta.t_max) else meta.t_max
    result, logger = run_to_completion(handle, t_max=t_max)
    return logger.records, result, meta
```

### Step 2: Update integration test

Same pattern as Tasks 14 / 18: replace helper trio with `from
snowman.baseline import SCENARIOS, run_scenario`; restructure test
methods to loop over `SCENARIOS`. Assertions verbatim.

### Step 3: Run

```bash
make test
```

**Expected:** every suite green.

## Task 23: Commit 5

```bash
git add src/snowman/summarise.py src/snowman/baseline.py \
        tests/snowman/test_summarise.py \
        tests/integration/test_snowman_baseline.py
git commit -m "task 40: src/snowman/baseline + snowman.summarise"
make test
```

---

# Commit 6 — Wire orchestrator + canonical artifacts

Populates `_REDUCERS`, lands the orchestrator + the e2e test, runs the
orchestrator once, and commits the canonical CSV artifacts + the
experiment page.

## Task 24: Populate `_REDUCERS` in `src/output/csv.py`

**Files:**
- Modify: `src/output/csv.py`

### Step 1: Replace the empty dispatch table

Find the line `_REDUCERS: dict[str, object] = {}` and replace with:

```python
from pbft.summarise    import summarise as _pbft_summarise
from pos.summarise     import summarise as _pos_summarise
from snowman.summarise import summarise as _snowman_summarise

_REDUCERS = {
    "pbft":       _pbft_summarise,
    "casper-ffg": _pos_summarise,
    "snowman":    _snowman_summarise,
}
```

Remove the forward-reference comment.

### Step 2: Verify mocked tests still pass

```bash
PYTHONPATH=src python3 -m unittest tests.output.test_csv -v
```

**Expected:** still 8 tests pass (the monkeypatches in the test
override the real `_REDUCERS`).

## Task 25: `src/output/baseline.py`

**Files:**
- Create: `src/output/baseline.py`

### Step 1: Implement per design spec §3.6

```python
"""T40 — Unified CSV orchestrator.

Imports each protocol's SCENARIOS + run_scenario, runs every scenario,
writes one results/baseline.csv. Snowman n=4 produces an additional
results/snowman_n4_sanity.csv via snowman.summarise.sanity_row.

Run from repo root:
    PYTHONPATH=src python3 -m output.baseline

Design spec: docs/superpowers/specs/2026-05-28-t40-output-format-design.md
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


def _collect_runs():
    runs = []
    for meta in pbft_baseline.SCENARIOS:
        runs.append(pbft_baseline.run_scenario(meta))
    for meta in pos_baseline.SCENARIOS:
        runs.append(pos_baseline.run_scenario(meta))
    for meta in snowman_baseline.SCENARIOS:
        runs.append(snowman_baseline.run_scenario(meta))
    return runs


def main() -> None:
    runs = _collect_runs()
    write_unified_csv(_OUT, runs)
    for records, result, meta in runs:
        if meta.protocol == "snowman" and meta.n == 4:
            sanity_row(records, result, meta, _SANE)
            break


if __name__ == "__main__":
    main()
```

### Step 2: Smoke-test importability

```bash
PYTHONPATH=src python3 -c "import output.baseline; print('ok')"
```

**Expected:** `ok`.

## Task 26: `tests/output/test_baseline_e2e.py`

**Files:**
- Create: `tests/output/test_baseline_e2e.py`

### Step 1: Write the e2e test

```python
"""End-to-end determinism test for the unified output orchestrator.
Drives output.baseline.main into a tmp directory twice; asserts the
two results/baseline.csv files are byte-identical.
"""
from __future__ import annotations

import csv as _csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import output.baseline as base
from output.schema import COLUMN_ORDER


class TestBaselineE2E(unittest.TestCase):
    def _run_once(self, out_dir: Path) -> tuple[bytes, bytes]:
        main_csv   = out_dir / "baseline.csv"
        sanity_csv = out_dir / "snowman_n4_sanity.csv"
        with patch.object(base, "_OUT",  main_csv), \
             patch.object(base, "_SANE", sanity_csv), \
             patch("output.csv._resolve_commit_hash",
                   return_value="abc12345"):
            base.main()
        return main_csv.read_bytes(), sanity_csv.read_bytes()

    def test_byte_identical(self):
        with TemporaryDirectory() as td1, TemporaryDirectory() as td2:
            main1, sane1 = self._run_once(Path(td1))
            main2, sane2 = self._run_once(Path(td2))
        self.assertEqual(main1, main2)
        self.assertEqual(sane1, sane2)

    def test_row_count(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                rows = list(_csv.DictReader(fh))
            with (Path(td) / "snowman_n4_sanity.csv").open() as fh:
                sane_rows = list(_csv.DictReader(fh))
        # 3 PBFT + 4 POS + 2 Snowman (n=4 skipped) = 9 rows.
        self.assertEqual(len(rows), 9)
        self.assertEqual(len(sane_rows), 1)

    def test_no_snowman_n4_in_main_file(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                rows = list(_csv.DictReader(fh))
        snowman_ns = sorted(int(r["n"]) for r in rows
                            if r["protocol"] == "snowman")
        self.assertEqual(snowman_ns, [7, 10])

    def test_sanity_row_has_degenerate_flag(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "snowman_n4_sanity.csv").open() as fh:
                reader = _csv.DictReader(fh)
                self.assertIn("snowman_degenerate_n4",
                              reader.fieldnames or [])
                row = next(iter(reader))
        self.assertEqual(row["snowman_degenerate_n4"], "True")
        self.assertEqual(row["protocol"], "snowman")
        self.assertEqual(row["n"], "4")

    def test_header_is_column_order(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                reader = _csv.DictReader(fh)
                self.assertEqual(reader.fieldnames, list(COLUMN_ORDER))


if __name__ == "__main__":
    unittest.main()
```

### Step 2: Run, confirm green

```bash
PYTHONPATH=src python3 -m unittest tests.output.test_baseline_e2e -v
```

**Expected:** 5 tests pass. If `test_byte_identical` fails: the
event-stream determinism is broken somewhere — investigate before
proceeding.

## Task 27: Run the orchestrator; commit canonical artifacts

**Files:**
- Create: `results/baseline.csv`
- Create: `results/snowman_n4_sanity.csv`

### Step 1: Run

```bash
PYTHONPATH=src python3 -m output.baseline
ls -la results/baseline.csv results/snowman_n4_sanity.csv
```

**Expected:** both files exist. Inspect:

```bash
cat results/baseline.csv | head -2
wc -l results/baseline.csv results/snowman_n4_sanity.csv
```

**Expected:** `results/baseline.csv` has 10 lines (1 header + 9 data
rows); `results/snowman_n4_sanity.csv` has 2 lines (1 header + 1 data
row). Header matches `COLUMN_ORDER`.

### Step 2: Determinism check

```bash
shasum -a 256 results/baseline.csv > /tmp/t40-baseline.sha
PYTHONPATH=src python3 -m output.baseline
shasum -a 256 -c /tmp/t40-baseline.sha
```

**Expected:** `results/baseline.csv: OK`. If not, stop and diagnose —
the determinism contract is violated.

### Step 3: `.gitignore` check

Verify `results/baseline.csv` and `results/snowman_n4_sanity.csv` are
NOT git-ignored (the spec calls for them to be tracked):

```bash
git check-ignore results/baseline.csv results/snowman_n4_sanity.csv
```

**Expected:** no output (neither file is ignored). If a parent
`results/` rule ignores everything, narrow it.

## Task 28: New experiment page `wiki/experiments/2026-05-28_unified-output.md`

**Files:**
- Create: `wiki/experiments/2026-05-28_unified-output.md`
- Modify: `wiki/index.md`
- Modify: `wiki/log.md`

### Step 1: Author the experiment page

```markdown
# T40 unified output format — build verification

> Build-verification baseline for the unified comparative-CSV pipeline
> introduced by T40. Three protocols' honest-path scenarios driven
> through one writer; one canonical `results/baseline.csv` produced;
> byte-identical determinism verified.

## Outcome

T40 lands the cross-protocol CSV contract pinned by
[[concepts/output-format]] and its implementation in `src/output/`.
The four T40 verify outcomes — **wiki contract resolves the 15
forward-references**, **all three implemented protocols populate the
18-column today subset**, **Snowman n=4 is skipped from the main file
and written to a sibling sanity CSV**, and **two seed-identical runs
produce byte-identical results/baseline.csv** — are asserted by the
new `tests/output/test_baseline_e2e.py` plus the per-reducer + writer-
composition unit tests under `tests/output/`, `tests/pbft/`,
`tests/pos/`, `tests/snowman/`.

## Configuration

- `global_seed = 42` (project default).
- PBFT: 3 scenarios at n ∈ {4, 7, 10}, quiescence stop.
- Casper FFG: 4 scenarios at n ∈ {4, 7, 10} uniform + n=4 nonuniform,
  `t_max = 20.0 s`.
- Snowman: 3 scenarios at n ∈ {4, 7, 10}, `t_max = 20.0 s`.
- Commit hash captured at write time per the T27 / T66 reproducibility
  contract; in this baseline = `<HASH-AT-COMMIT>`.

## Result row count

| File | Rows (incl. header) |
| :--- | ---: |
| `results/baseline.csv` | 10 (1 header + 9 data) |
| `results/snowman_n4_sanity.csv` | 2 (1 header + 1 data) |

The 9 data rows: 3 PBFT + 4 Casper FFG + 2 Snowman (`snowman-n4` is
skipped from the main file per [[concepts/output-format]] §7).

## Headline columns

(Insert the actual values produced by `python3 -m output.baseline` at
commit time. Format: one row per scenario, `commit_latency_ms`,
`finality_latency_ms`, `tps`, `consensus_msgs_per_acu`, `success_rate`,
`fork_rate`. Reference design spec §8 for the expected approximate
values.)

## Determinism check

```bash
shasum -a 256 results/baseline.csv > /tmp/t40-baseline.sha
PYTHONPATH=src python3 -m output.baseline
shasum -a 256 -c /tmp/t40-baseline.sha
# results/baseline.csv: OK
```

## Auggie verification

- **Pickup-index call.** Query: describe T40's prior-art surface —
  existing CSV writers, the event-log API, the runner seam,
  per-protocol baseline modules, RunResult, the config schema. Returned:
  the full source-of-truth map for the writer's inputs (full output
  retained in the brainstorming transcript).
- **Plan-phase re-query.** Query: enumerate every reference to
  `output-format`, `results/baseline.csv`, `_summarise`,
  `write_baseline_csv` across the codebase + wiki. Returned: the 15
  forward-references + the one CSV-writing callsite the plan was
  migrating.
- **Post-edit re-query.** Query: describe the new `src/output/`
  package; locate every call site of `write_unified_csv` and
  `summarise`; confirm no stale CSV-writing surface remains in
  `src/pos/baseline.py`. Returned: (insert at execution time;
  `write_unified_csv` called only from `output.baseline.main`;
  `summarise` called only from `output.csv.write_unified_csv` and the
  three unit-test files; `src/pos/baseline.py` no longer imports
  `csv`).

## Source pages

- [[concepts/output-format]] — design contract.
- [[concepts/metric-reconciliation]] — per-protocol formulas.
- [[concepts/event-log-schema]] — raw substrate.
- [[concepts/runner]] — upstream producer.

## Related experiments

- [[experiments/2026-05-25_pos-baseline]] — T35 honest baseline,
  superseded by the T40 unified path.
- [[experiments/2026-05-21_pbft-baseline]] — T30 honest baseline,
  preserved on its own per-protocol terms; the unified CSV is a sibling.
- [[experiments/2026-05-27_snowman-baseline]] — T38 honest baseline,
  same.
```

Fill in the `<HASH-AT-COMMIT>` placeholder with the actual git hash at
commit time, and the `Headline columns` section with the actual numbers
from the run.

### Step 2: `wiki/index.md` entry

Insert under `## Experiments`, top of the list (newest-first):

```markdown
- [[experiments/2026-05-28_unified-output]] — T40 build-verification
  baseline: three protocols' honest-path scenarios driven through one
  writer; `results/baseline.csv` has 9 rows (3 PBFT + 4 Casper FFG + 2
  Snowman, n=4 skipped); `results/snowman_n4_sanity.csv` has 1 row;
  two seed-identical runs byte-identical.
```

### Step 3: `wiki/log.md` entry

Insert at top:

```markdown
## [2026-05-28] code | task 40 — wire output orchestrator + canonical artifacts

- role: Engineer
- touched: `src/output/csv.py` (real `_REDUCERS` populated),
  `src/output/baseline.py` (new), `tests/output/test_baseline_e2e.py`
  (new), `results/baseline.csv` (new canonical artifact),
  `results/snowman_n4_sanity.csv` (new sibling), `wiki/experiments/
  2026-05-28_unified-output.md` (new), `wiki/index.md`, `wiki/log.md`
- notes: T40 implementation complete. Three protocols' honest baselines
  driven through one writer. Byte-identical determinism verified. T35-
  local CSV writer retired. L-W4 M1's 15 forward-references closed (in
  the wiki-contract commit).
```

### Step 4: No commit yet

## Task 29: Commit 6

```bash
git status
git add src/output/csv.py src/output/baseline.py \
        tests/output/test_baseline_e2e.py \
        results/baseline.csv results/snowman_n4_sanity.csv \
        wiki/experiments/2026-05-28_unified-output.md \
        wiki/index.md wiki/log.md
git commit -m "task 40: wire output.baseline orchestrator; canonical results/baseline.csv"
make test
```

**Expected:** every suite green.

---

## §M-verify: full-suite verification before TASKS.md flip

Per the Engineer role prompt's
`superpowers:verification-before-completion` requirement, gate on a
clean full-suite run + byte-identical CSV reproduction before flipping
T40 to In Review.

```bash
make test
shasum -a 256 results/baseline.csv > /tmp/t40-baseline.sha
PYTHONPATH=src python3 -m output.baseline
shasum -a 256 -c /tmp/t40-baseline.sha
shasum -a 256 results/snowman_n4_sanity.csv > /tmp/t40-sanity.sha
PYTHONPATH=src python3 -m output.baseline
shasum -a 256 -c /tmp/t40-sanity.sha
```

**Expected:** `make test` green; both `results/baseline.csv: OK` and
`results/snowman_n4_sanity.csv: OK`. If either fails the determinism
contract is broken — stop and diagnose.

**Run auggie post-edit re-query** with the query string captured in
Task 28's experiment page. Append the actual returned summary to the
experiment page's `## Auggie verification` § Post-edit re-query bullet.

---

## Task 30: TASKS.md — flip T40 to In Review + recompute dashboard

**Files:**
- Modify: `TASKS.md`

### Step 1: Flip status (line ~205)

Find the T40 entry. Change `[~]` to `[?]`:

```markdown
- `[?]` **T40** `H` Engineer — Unify output format across all algorithms
```

### Step 2: Update outcome to reflect the actual delivered schema

The original outcome line names a 7-column schema; T40 delivered the
18-column subset per the wiki contract. Append a rewrite parenthetical
(precedent: T29's 2026-05-21 rewrite, T39's 2026-05-27 supersession):

Read the current outcome line. Append after the existing `_Outcome:_`
text a parenthetical with the agreed delivered scope:

```markdown
  _Outcome:_ (superseded 2026-05-28 by [[concepts/output-format]] §4)
  Unified per-trial CSV at `results/baseline.csv` with the 18-column
  subset of the binding ~30-column schema pinned by
  [[concepts/metric-reconciliation]] §T40; per-protocol reducers in
  `src/<protocol>/summarise.py`; orchestrator at
  `src/output/baseline.py`; T35-local CSV writer retired (the seven
  T35-sketched columns are a strict subset of today's 18). Multi-seed
  sweeps + 95% CIs + NWT row population + adversarial / delay columns
  on the wiki extension register, deferred to T41 / T44 / T38.1 /
  T48–T49 / T51–T54 / T58 respectively.
  · _Artifact:_ `wiki/concepts/output-format.md`,
  `src/output/{csv,baseline,schema}.py`,
  `src/pbft/{baseline,summarise}.py`,
  `src/pos/{baseline,summarise}.py`,
  `src/snowman/{baseline,summarise}.py`,
  `tests/output/`, `results/baseline.csv`,
  `results/snowman_n4_sanity.csv`,
  `wiki/experiments/2026-05-28_unified-output.md`
```

(Preserve the entry's other fields verbatim.)

### Step 3: Recompute Dashboard arithmetic (line ~9)

Before this task: `Completed: 57 · In Review: 2 · In Progress: 1 ·
Not Started: 30 · Blocked: 3`.

After flipping T40 from `[~]` In Progress to `[?]` In Review:
`Completed: 57 · In Review: 3 · In Progress: 0 · Not Started: 30 ·
Blocked: 3`.

Verify the arithmetic: 57 + 3 + 0 + 30 + 3 = 93. Total tasks: 75 +
sync 10 + lint-checkpoints 5 + lint-followups 4 = 94. Off by one —
recount against `TASKS.md` directly:

```bash
grep -cE "^- \`\[" TASKS.md
grep -cE "^- \`\[x\]" TASKS.md
grep -cE "^- \`\[\?\]" TASKS.md
grep -cE "^- \`\[~\]" TASKS.md
grep -cE "^- \`\[ \]" TASKS.md
grep -cE "^- \`\[!\]" TASKS.md
```

Adjust the dashboard line to match the actual counts. (Drift is
acceptable; the dashboard is informational, not authoritative.)

### Step 4: Commit

```bash
git add TASKS.md
git commit -m "task 40: flip to In Review; outcome rewrite; dashboard"
```

### Step 5: Final verification

```bash
make test
git log --oneline -10
```

**Expected:** every suite green; the last ~9 commits are the T40 task
series (Commits 1–6 plus the In-Review-flip commit).

### Step 6: Run `superpowers:verification-before-completion`

Per the Engineer role prompt's mandatory invocation.

---

## 8. Acceptance criteria (mirror of design spec §8)

A T40 implementation is complete iff every box below is checked.

- [ ] `wiki/concepts/output-format.md` exists, ~250 lines, 13 sections
      per design spec §2.1.
- [ ] `grep -rE "\[\[concepts/output-format" wiki/` returns ≥15 matches
      (the L-W4 M1 inbound count).
- [ ] `wiki/concepts/event-log-schema.md` and `wiki/concepts/runner.md`
      each carry a `## Revisions` block dated 2026-05-28.
- [ ] `wiki/index.md` has the new `## Concepts` entry for
      `output-format` and the new `## Experiments` entry for
      `2026-05-28_unified-output`.
- [ ] `wiki/log.md` has two entries dated 2026-05-28 (one for the wiki
      contract, one for the orchestrator wiring).
- [ ] `src/output/__init__.py`, `src/output/schema.py`,
      `src/output/csv.py`, `src/output/baseline.py` all exist.
- [ ] `src/pbft/baseline.py`, `src/pbft/summarise.py`,
      `src/pos/summarise.py`, `src/snowman/baseline.py`,
      `src/snowman/summarise.py` all exist.
- [ ] `src/pos/baseline.py` no longer defines `_summarise`,
      `write_baseline_csv`, `_COLUMNS`, or a `__main__`.
- [ ] `src/pos/baseline.py` no longer imports `csv` or `statistics`.
- [ ] `tests/output/test_generic_cols.py`, `tests/output/test_csv.py`,
      `tests/output/test_baseline_e2e.py`, `tests/pbft/test_summarise.py`,
      `tests/pos/test_summarise.py`, `tests/snowman/test_summarise.py`
      all exist.
- [ ] `tests/integration/test_pbft_baseline.py`,
      `tests/integration/test_pos_baseline.py`,
      `tests/integration/test_snowman_baseline.py` each import
      `SCENARIOS, run_scenario` from their protocol's `baseline`
      module.
- [ ] `make test` is green.
- [ ] `make test-output` is green.
- [ ] `PYTHONPATH=src python3 -m output.baseline` writes
      `results/baseline.csv` (10 lines) and
      `results/snowman_n4_sanity.csv` (2 lines).
- [ ] Two consecutive `python3 -m output.baseline` runs produce
      byte-identical `results/baseline.csv` and
      `results/snowman_n4_sanity.csv` (verified by `shasum -c`).
- [ ] `results/pos/baseline.csv` is deleted from the repo.
- [ ] The T35-sample-CSV backlog item is append-resolved.
- [ ] `wiki/experiments/2026-05-28_unified-output.md` exists with
      a populated `## Auggie verification` section (pickup-index,
      plan-phase, post-edit).
- [ ] T40's TASKS.md status is `[?]` In Review; dashboard arithmetic
      reflects the change.

---

## Handoff summary template (for the In-Review post)

When pushing the branch and requesting human review, summarise:

```
Task: T40 — Unify output format across all algorithms.
Branch: <branch name from git>.

Files touched:
  - wiki/concepts/output-format.md (new, ~250 lines, closes L-W4 M1)
  - wiki/concepts/event-log-schema.md (+ Revisions block)
  - wiki/concepts/runner.md (+ Revisions block)
  - wiki/index.md, wiki/log.md (entries)
  - wiki/experiments/2026-05-28_unified-output.md (new)
  - src/output/{__init__,schema,csv,baseline}.py (new package)
  - src/pbft/{baseline,summarise}.py (new)
  - src/pos/baseline.py (harmonised — CSV writer retired)
  - src/pos/summarise.py (new)
  - src/snowman/{baseline,summarise}.py (new)
  - tests/output/{test_generic_cols,test_csv,test_baseline_e2e}.py
  - tests/pbft/test_summarise.py
  - tests/pos/test_summarise.py
  - tests/snowman/test_summarise.py
  - tests/integration/test_{pbft,pos,snowman}_baseline.py (harmonised)
  - Makefile (test-output target)
  - results/baseline.csv, results/snowman_n4_sanity.csv (canonical)
  - results/pos/baseline.csv (deleted)
  - TASKS.md (T40 flipped to [?] In Review; backlog item resolved;
    dashboard recomputed)

Decisions made (locked during brainstorming, see design spec §0):
  - Schema scope: minimal-set + extension register.
  - Row granularity: per-trial / long format.
  - Reducer wiring: hybrid (src/output owns generic; each protocol
    owns its summarise.py).
  - Orchestration: single src/output/baseline.py; T35-local CSV writer
    retired.
  - Snowman n=4 policy: skip from main CSV; sibling sanity CSV.

Verification:
  - `make test`: green (line counts before vs after: <capture>).
  - `python3 -m output.baseline` × 2: byte-identical
    `results/baseline.csv` and `results/snowman_n4_sanity.csv`.
  - Auggie post-edit re-query: confirms no stale CSV writer in
    src/pos/baseline.py; _REDUCERS dispatch wired into all three
    protocols.

Open questions (none blocking):
  - None. All design choices were locked during brainstorming.

Watch-for items for downstream tasks:
  - T44 chooses the aggregated-file layout (sibling vs in-place
    *_ci_lo/_ci_hi columns) — wiki extension register flags this.
  - T38.1 reducer is the next natural addition (one module + one entry
    in _REDUCERS).
  - The Snowman fork_rate reducer is honest-baseline-zero today;
    extending it to count pre-β preference flips for T54 will need
    additional reducer accounting (~30 LoC). Backlog this when T54
    starts.
```
