# T52 — Non-participating (offline) validators: Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a `withhold-participation` (offline) adversary alongside T51's
delay-emission, sweep PBFT/Casper FFG/Snowman over an offline-fraction grid that
crosses the 1/3 fault threshold, and report each protocol's success/failure
boundary `f*`.

**Architecture:** Offline = drop every outbound emission at the existing
post-`build_run` bind-seam wrap (no FSM hooks, no shared-infra edits). Reuse
`select.slow_node_ids` (primary spared), the T40 reducers' existing
`success_rate` column, `run_grid_tiered`, `clip_records`. Extract a shared
`_wrap_outbound` in `inject.py` (2 real consumers now). Share the generic
adversary annotation columns + formatting via a small `sweep_common.py`; write a
thin `offline_sweep.py` for the offline-specific glue (per-protocol `f` grid, no
`m` axis, `throughput_ratio` per-row, `finalization_success_rate` aggregate).

**Tech Stack:** Python 3, stdlib `unittest` (not pytest), `matplotlib` (Agg),
the existing simulator packages under `src/`. Tests run via
`make test-adversary` → `PYTHONPATH=src:tests/adversary python3 -m unittest
discover -s tests/adversary -v`. Full suite: `make test`.

**Approved design:** `docs/plans/2026-06-17-t52-offline-validators-design.md`
(read it first — methodology decisions, the architect-review findings D1–D6,
and the out-of-scope list live there).

**Environment notes for the executor:**
- `head -n` is shadowed by a non-coreutils HTTP binary — use `sed -n`/`tail`/`awk` in Bash.
- auggie (`mcp__auggie__codebase-retrieval`) IS available this session — use it
  for the mandated pre/post-edit structural queries and log them on the
  experiment page.
- The human commits and merges. Where steps say "Commit," prepare the change and
  the message; do not assume you push/merge.

---

## Task 1: Extract `_wrap_outbound`; add `OfflineProfile` + `inject_offline`

**Files:**
- Modify: `src/adversary/profiles.py`
- Modify: `src/adversary/inject.py`
- Modify: `src/adversary/__init__.py`
- Test: `tests/adversary/test_profiles.py`, `tests/adversary/test_inject.py`

**Step 1: Write failing tests for `OfflineProfile`.**

Append to `tests/adversary/test_profiles.py`:

```python
def test_offline_profile_fields():
    from adversary.profiles import OfflineProfile
    p = OfflineProfile(nodes=(8, 9), intensity=0.2)
    assert p.nodes == (8, 9)
    assert p.intensity == 0.2
    assert p.kind == "withhold-participation"
    # No magnitude field: offline is binary, not dosed.
    assert not hasattr(p, "mult")
```

**Step 2: Run, verify it fails.**
Run: `make test-adversary`
Expected: FAIL — `ImportError: cannot import name 'OfflineProfile'`.

**Step 3: Implement `OfflineProfile`.**

Append to `src/adversary/profiles.py` (after `DelayProfile`):

```python
@dataclass(frozen=True)
class OfflineProfile:
    """The ``withhold-participation`` adversary profile for one run.

    A non-participating (offline / crash-faulty) validator: it receives and
    runs its FSM but emits nothing, so it contributes to no quorum or poll.
    No magnitude field — offline is binary (skip vs participate), unlike
    delay-emission's dosed ``mult`` (adversary-model.md §4).

    - ``nodes``     -- the offline node ids (highest-id ⌊f·n⌋; select.py).
    - ``intensity`` -- nominal fraction f of offline nodes.
    - ``kind``      -- capability tag ("withhold-participation").
    """
    nodes: tuple[int, ...]
    intensity: float
    kind: str = "withhold-participation"
```

**Step 4: Run, verify the profile tests pass.**
Run: `make test-adversary` — Expected: profile tests PASS.

**Step 5: Write failing tests for `inject_offline` + the refactor invariant.**

Append to `tests/adversary/test_inject.py` (mirror the existing stub-node style):

```python
class TestInjectOffline(unittest.TestCase):
    def test_offline_send_dropped(self):
        from adversary.inject import inject_offline
        handle, nodes = _stub_handle(4)
        inject_offline(handle, offline_ids=(3,), intensity=0.25)
        nodes[3].send(dst=0, type="VOTE", payload=b"x", t=2.0)
        nodes[3].broadcast(type="PREPARE", payload=b"p", t=5.0)
        self.assertEqual(nodes[3].sent, [])     # nothing recorded
        self.assertEqual(nodes[3].bcast, [])

    def test_honest_nodes_untouched(self):
        from adversary.inject import inject_offline
        handle, nodes = _stub_handle(4)
        inject_offline(handle, offline_ids=(3,), intensity=0.25)
        nodes[0].send(dst=1, type="VOTE", payload=b"y", t=2.0)
        nodes[0].broadcast(type="PRE", payload=b"q", t=3.0)
        self.assertEqual(nodes[0].sent, [(1, "VOTE", b"y", 2.0)])
        self.assertEqual(nodes[0].bcast, [("PRE", b"q", 3.0)])

    def test_empty_offline_set_is_noop(self):
        from adversary.inject import inject_offline
        handle, nodes = _stub_handle(4)
        before = {i: (nodes[i].send, nodes[i].broadcast) for i in range(4)}
        inject_offline(handle, offline_ids=(), intensity=0.0)
        for i in range(4):
            self.assertIs(nodes[i].send, before[i][0])
            self.assertIs(nodes[i].broadcast, before[i][1])
            self.assertIsNone(nodes[i].adversary)

    def test_profile_recorded(self):
        from adversary.inject import inject_offline
        from adversary.profiles import OfflineProfile
        handle, nodes = _stub_handle(4)
        inject_offline(handle, offline_ids=(2, 3), intensity=0.5)
        for i in (2, 3):
            self.assertIsInstance(nodes[i].adversary, OfflineProfile)
            self.assertEqual(nodes[i].adversary.nodes, (2, 3))
        self.assertIsNone(nodes[0].adversary)

    def test_double_injection_raises(self):
        from adversary.inject import inject_offline
        handle, nodes = _stub_handle(4)
        inject_offline(handle, offline_ids=(3,), intensity=0.25)
        with self.assertRaises(RuntimeError):
            inject_offline(handle, offline_ids=(3,), intensity=0.25)
```

**Step 6: Run, verify failure.**
Run: `make test-adversary` — Expected: FAIL — `cannot import name 'inject_offline'`.

**Step 7: Refactor `inject.py` to a shared `_wrap_outbound`, add `inject_offline`.**

Replace the body of `src/adversary/inject.py` below the imports. Keep the module
docstring; update the line "T52/T53 will need deeper FSM hooks; T51 does not."
to note T52 reuses this seam (offline = drop, no FSM hook needed; only T53
needs hooks). Add the import `from .profiles import DelayProfile, OfflineProfile`.

```python
def _wrap_outbound(handle, ids, profile, send_factory, broadcast_factory,
                   *, who: str) -> None:
    """Shared bind-seam wrap: attach `profile` to each node in `ids` and rebind
    its honest `send`/`broadcast` through the supplied factories. Call AFTER
    build_run, BEFORE run_to_completion. No-op when `ids` is empty.

    `who` only labels the double-injection error. The factories take the node's
    honest bound fn and return the replacement (delay shifts t; offline drops).
    """
    if not ids:
        return
    for nid in ids:
        node = handle.nodes[nid]
        if node.adversary is not None:
            raise RuntimeError(
                f"{who}: node {nid} already has an adversary profile "
                f"{node.adversary!r}; double-injection would silently stack")
        node.adversary = profile
        node.send = send_factory(node.send)
        node.broadcast = broadcast_factory(node.broadcast)


def inject_delay(handle: RunHandle, slow_ids: tuple[int, ...],
                 mult: float, ref: float, intensity: float) -> None:
    """Re-wrap slow nodes' outbound API to emit `mult·ref` s late. (T51 §3.1.)

    Behaviour byte-identical to the pre-refactor inject_delay — guarded by the
    existing TestInjectDelay suite and the T51 byte-identical CSV re-run.
    """
    if not slow_ids:
        return
    shift = mult * ref
    profile = DelayProfile(nodes=tuple(slow_ids), intensity=intensity,
                           mult=mult)
    _wrap_outbound(handle, slow_ids, profile,
                   lambda honest: _delayed_send(honest, shift),
                   lambda honest: _delayed_broadcast(honest, shift),
                   who="inject_delay")


def _dropped_send(honest_send):
    """A send that drops the emission entirely (offline node, T52)."""
    def send(dst, type, payload, t):
        return
    return send


def _dropped_broadcast(honest_broadcast):
    """A broadcast that drops the emission entirely (offline node, T52)."""
    def broadcast(type, payload, t):
        return
    return broadcast


def inject_offline(handle: RunHandle, offline_ids: tuple[int, ...],
                   intensity: float) -> None:
    """Re-wrap offline nodes' outbound API to drop every emission (T52 §3.2).

    The node still receives and runs its FSM; it just emits nothing, so it
    contributes to no quorum/poll — the consensus definition of a silent
    crash-faulty / non-participating validator (adversary-model.md §4). No
    magnitude axis. No adversary RNG consumed → per-cell byte-identical re-run;
    empty `offline_ids` is a strict no-op (== honest static-baseline).
    """
    profile = OfflineProfile(nodes=tuple(offline_ids), intensity=intensity)
    _wrap_outbound(handle, offline_ids, profile,
                   _dropped_send, _dropped_broadcast, who="inject_offline")
```

Keep `_delayed_send` / `_delayed_broadcast` as-is.

**Step 8: Update the package exports.**

In `src/adversary/__init__.py`:
```python
from .inject import inject_delay, inject_offline
from .profiles import DelayProfile, OfflineProfile
from .select import slow_node_ids

__all__ = ["DelayProfile", "OfflineProfile", "inject_delay",
           "inject_offline", "slow_node_ids"]
```

**Step 9: Run the adversary suite — both old and new inject tests must pass.**
Run: `make test-adversary`
Expected: PASS, including all pre-existing `TestInjectDelay` tests (proves the
`_wrap_outbound` refactor preserved delay behaviour).

**Step 10: Commit.**
```bash
git add src/adversary/inject.py src/adversary/profiles.py \
        src/adversary/__init__.py tests/adversary/test_inject.py \
        tests/adversary/test_profiles.py
git commit -m "task 52: add offline (withhold-participation) injection seam"
```

---

## Task 2: Offline per-protocol runners

**Files:**
- Modify: `src/adversary/runners.py`
- Test: `tests/adversary/test_runners.py`

**Step 1: Write failing tests.**

Append to `tests/adversary/test_runners.py`:

```python
from adversary.runners import OFFLINE_RUNNERS


class TestOfflineRunners(unittest.TestCase):
    def test_control_finalizes_every_protocol(self):
        for proto, runner in OFFLINE_RUNNERS.items():
            records, result, meta = runner(n=7, f=0.0, seed=0)
            self.assertTrue(_decided(records), msg=f"{proto} control empty")
            self.assertEqual(meta.protocol, proto)

    def test_offline_control_matches_honest_baseline_bytewise(self):
        # f=0 offline == f=0 delay (both no-op) at the same (n, seed):
        # same decided count and same first-decision time.
        from adversary.runners import RUNNERS
        for proto in OFFLINE_RUNNERS:
            off, _, _ = OFFLINE_RUNNERS[proto](n=7, f=0.0, seed=3)
            dly, _, _ = RUNNERS[proto](n=7, f=0.0, m=0.0, seed=3)
            self.assertEqual(len(_decided(off)), len(_decided(dly)))
            self.assertEqual(_first_latency_ms(off), _first_latency_ms(dly))

    def test_pbft_above_threshold_stalls(self):
        # n=10, f=0.40 → 4 offline, 6 honest < 2f+1=7 quorum → no finality.
        records, result, meta = OFFLINE_RUNNERS["pbft"](n=10, f=0.40, seed=0)
        self.assertFalse(_decided(records),
                         msg="PBFT should stall above the 1/3 quorum threshold")
```

**Step 2: Run, verify failure.**
Run: `make test-adversary` — Expected: FAIL — `cannot import name 'OFFLINE_RUNNERS'`.

**Step 3: Add offline runners.**

In `src/adversary/runners.py`: add `from .inject import inject_delay, inject_offline`
(extend the existing import). After the three delay runners, add three offline
runners — identical to `run_pbft`/`run_ffg`/`run_snowman` except (a) signature
drops `m`, (b) the inject line. Example for PBFT (FFG/Snowman analogous —
copy the corresponding delay runner, drop `m`, swap the inject call):

```python
def run_pbft_offline(n: int, f: float, seed: int) -> RunTriple:
    propose = cfg.PBFT_PROPOSE_DELAY_S
    batches = [b"".join(b) for b in _batches(seed, propose)]

    def make(node_id: int, global_seed: int) -> PBFTNode:
        workload = batches if node_id == 0 else None
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n, workload=workload,
                        propose_delay=propose, initial_view=0,
                        vc_delay=cfg.PBFT_VC_DELAY_S)

    meta = _meta("pbft", f"pbft-n{n}", n, seed, propose, None)
    handle = build_run(_config(n), seed, make)
    inject_offline(handle, slow_node_ids(n, f), f)
    result, logger = run_to_completion(handle, t_max=cfg.T_MAX)
    return logger.records, result, meta
```

Then the dispatch table:
```python
OFFLINE_RUNNERS = {
    "pbft":       run_pbft_offline,
    "casper-ffg": run_ffg_offline,
    "snowman":    run_snowman_offline,
}
```

`slow_node_ids` is reused unchanged — for the offline set it still returns the
highest-id ⌊f·n⌋ nodes, sparing the primary (node 0). No selection edit.

**Step 4: Run, verify pass.**
Run: `make test-adversary`
Expected: PASS. (Note: `test_pbft_above_threshold_stalls` confirms the stall
regime D1/C5 flagged — PBFT loses quorum at f=0.40.)

**Step 5: Commit.**
```bash
git add src/adversary/runners.py tests/adversary/test_runners.py
git commit -m "task 52: add offline per-protocol runners"
```

---

## Task 3: Offline config constants + shared annotation helpers

**Files:**
- Create: `src/adversary/offline_config.py`
- Create: `src/adversary/sweep_common.py`
- Test: `tests/adversary/test_offline_config.py`, `tests/adversary/test_sweep_common.py`

**Rationale (YAGNI-bounded reuse, per design §3.2 / review D5–D6):** extract only
the genuinely arity-independent, immediately-reused pieces — the generic
annotation column names, the strategy label, the common-column formatter, and
the Snowman-heavy predicate. The fully Spec-driven driver that would also migrate
T51's frozen `sweep.py` is deferred to T53 (third consumer); T51's merged
orchestrator and its frozen `delayed_voters.csv` are left untouched (repro
safety). This is the architect's "should, not must" taken as the pragmatic middle.

**Step 1: Write failing tests for `sweep_common`.**

`tests/adversary/test_sweep_common.py`:
```python
import unittest
from adversary.sweep_common import (ADV_COMMON_COLUMNS, strategy_label,
                                     is_heavy_snowman)


class TestSweepCommon(unittest.TestCase):
    def test_common_columns_are_neutral(self):
        # Generic block: no strategy-specific names (no delay_mult / slow_*).
        assert "adversary_strategy" in ADV_COMMON_COLUMNS
        assert "adversary_node_count" in ADV_COMMON_COLUMNS
        assert "byzantine_fraction" in ADV_COMMON_COLUMNS
        assert "delay_mult" not in ADV_COMMON_COLUMNS
        assert "slow_node_count" not in ADV_COMMON_COLUMNS

    def test_strategy_label(self):
        assert strategy_label(0.0, "withhold-participation") == "none"
        assert strategy_label(0.2, "withhold-participation") == \
            "withhold-participation"

    def test_is_heavy_snowman(self):
        assert is_heavy_snowman("snowman", 25) is True
        assert is_heavy_snowman("snowman", 10) is False
        assert is_heavy_snowman("pbft", 25) is False
```

**Step 2: Run, verify failure** (`make test-adversary` → ImportError).

**Step 3: Implement `src/adversary/sweep_common.py`.**

```python
"""Shared, strategy-agnostic helpers for the Family C adversary sweeps (T52+).

Holds only the arity-independent pieces reused across withhold (T52) and
equivocate (T53): the generic annotation column names, the strategy label, the
common-column CSV formatter, and the Snowman memory-heavy predicate. Cell shape,
the headline column, build_cells, and the post-pass stay strategy-specific (the
offline cell is a 4-tuple, delay's is a 5-tuple). T51's sweep.py is intentionally
not migrated here (frozen dataset). Design: docs/plans/2026-06-17-...-design.md §3.2
"""
from __future__ import annotations

# Generic adversary annotation block (neutral names; no delay_mult).
ADV_COMMON_COLUMNS: tuple[str, ...] = (
    "adversary_strategy",     # "none" for f=0, else the capability tag
    "adversary_node_count",   # realized ⌊f·n⌋ adversarial nodes
    "byzantine_fraction",     # nominal f
    "view_change_count",      # PBFT view-changes in [0, W] (0 for FFG/Snowman)
    "clipped_fraction",       # tail past W / in-scope (reported, not guarded)
    "run_horizon_s",          # W + buffer
)

_CONTROL_F = 0.0


def strategy_label(f: float, kind: str) -> str:
    return "none" if f == _CONTROL_F else kind


def is_heavy_snowman(proto: str, n: int) -> bool:
    """Memory-heavy class: Snowman n>=25 (mirror sweep._is_heavy_cell)."""
    return proto == "snowman" and int(n) >= 25


def format_common_adv_cols(row: dict) -> dict:
    """Format the six ADV_COMMON_COLUMNS to strings (matches sweep.write_csv)."""
    return {
        "adversary_strategy":   str(row["adversary_strategy"]),
        "adversary_node_count": str(row["adversary_node_count"]),
        "byzantine_fraction":   f"{row['byzantine_fraction']:.6f}",
        "view_change_count":    str(row["view_change_count"]),
        "clipped_fraction":     f"{row['clipped_fraction']:.6f}",
        "run_horizon_s":        f"{row['run_horizon_s']:.3f}",
    }
```

**Step 4: Write failing tests for `offline_config`.**

`tests/adversary/test_offline_config.py`:
```python
import unittest
from adversary import offline_config as oc


class TestOfflineConfig(unittest.TestCase):
    def test_per_protocol_f_grid(self):
        # PBFT/FFG cross the 1/3 cliff (f=0.40); Snowman stops at 0.33.
        assert oc.F_VALUES["pbft"] == (0.0, 0.10, 0.20, 0.33, 0.40)
        assert oc.F_VALUES["casper-ffg"] == (0.0, 0.10, 0.20, 0.33, 0.40)
        assert oc.F_VALUES["snowman"] == (0.0, 0.10, 0.20, 0.33)

    def test_no_magnitude_axis(self):
        assert not hasattr(oc, "M_VALUES")

    def test_n_and_seeds(self):
        assert oc.N_VALUES == (10, 25)
        assert oc.SEEDS == tuple(range(20))
```

**Step 5: Run, verify failure.**

**Step 6: Implement `src/adversary/offline_config.py`.**

Re-export the unchanged simulator knobs from the T51 `config` module and add the
offline-specific grid. The WINDOW/BUFFER/VC constants are **pre-probe defaults**
re-confirmed in Task 5 (do NOT inherit T51's numbers blindly — design §6 / D1):

```python
"""Family C withhold-participation (offline-validators) configuration (T52).

Offline has NO magnitude axis (binary skip). The intensity grid is per-protocol:
PBFT and Casper FFG cross the 1/3 liveness cliff with an above-threshold f=0.40
point; Snowman stops at 0.33 (proportional degradation, no sharp cliff) — design §2.
WINDOW_S / BUFFER_S / PBFT_VC_DELAY_S are PROBE-SET in Task 5 (re-probed for the
offline stall + view-change regime, not inherited from T51 — design §6).
"""
from __future__ import annotations

# Shared simulator knobs (timeline, cadence, protocol knobs, workload) — reuse
# T51's values unchanged; only the swept axes + calibration differ.
from .config import (STATIC_BASELINE, REF_S, PBFT_PROPOSE_DELAY_S,
                     SNOWMAN_SLOT_DURATION_S, SNOWMAN_BETA, FFG_SLOT_DURATION_S,
                     FFG_SLOTS_PER_EPOCH, ARRIVAL_PROCESS, OFFERED_RATE,
                     TX_BYTES, CONFLICT_RATE)

N_VALUES: tuple[int, ...] = (10, 25)
SEEDS: tuple[int, ...] = tuple(range(20))

# Per-protocol offline-fraction grid (f=0 is the honest control).
F_VALUES: dict[str, tuple[float, ...]] = {
    "pbft":       (0.0, 0.10, 0.20, 0.33, 0.40),
    "casper-ffg": (0.0, 0.10, 0.20, 0.33, 0.40),
    "snowman":    (0.0, 0.10, 0.20, 0.33),
}

# Calibration — PROBE-SET in Task 5. Defaults below are starting points only.
WINDOW_S: float = 150.0
BUFFER_S: float = 80.0
T_MAX: float = WINDOW_S + BUFFER_S
PBFT_VC_DELAY_S: float = 3.0
ONE_ROUND_S: dict[str, float] = {"pbft": 2.0, "casper-ffg": 2.0, "snowman": 72.0}
```

NOTE: the offline runners (Task 2) read `cfg.T_MAX`, `cfg.WINDOW_S`,
`cfg.PBFT_VC_DELAY_S`, etc. from `adversary.config` (the T51 module). To keep the
offline sweep's calibration independent without editing T51's config, the
offline runners must read from `offline_config`. **Adjust Task 2**: have the
offline runners import `from . import offline_config as cfg` instead of the T51
`config`. (The delay runners keep importing the T51 `config`.) Split the runner
module imports accordingly, or parametrize `_config`/`_meta` to take the horizon
constants. Simplest: in `runners.py`, the three offline runners reference
`offline_config` values explicitly for `T_MAX`, `WINDOW_S`, `PBFT_VC_DELAY_S`,
while continuing to reuse `_config`/`_batches`/`_meta` by passing the horizon in.
Confirm `make test-adversary` still green after this wiring.

**Step 7: Run, verify pass** (`make test-adversary`).

**Step 8: Commit.**
```bash
git add src/adversary/offline_config.py src/adversary/sweep_common.py \
        tests/adversary/test_offline_config.py \
        tests/adversary/test_sweep_common.py src/adversary/runners.py
git commit -m "task 52: offline config grid + shared adversary annotation helpers"
```

---

## Task 4: Offline sweep orchestrator

**Files:**
- Create: `src/adversary/offline_sweep.py`
- Test: `tests/adversary/test_offline_sweep.py`

Mirror `src/adversary/sweep.py` structurally, with these offline-specific
changes (the executor should open `sweep.py` side-by-side):

- **Cell is a 4-tuple** `(proto, n, f, seed)` (no `m`). Update `_cell_key`,
  `_param_fingerprint`, `_run_cell`, `_build_cells`, `_is_heavy_cell` (use
  `sweep_common.is_heavy_snowman`).
- **`_build_cells`** iterates the **per-protocol** `offline_config.F_VALUES[p]`
  (PBFT/FFG include 0.40; Snowman does not). One control (f=0) + the attack f's,
  per (proto, n, seed). Dispatch through `OFFLINE_RUNNERS`.
- **Annotation columns** = `sweep_common.ADV_COMMON_COLUMNS` + the offline
  headline `("throughput_ratio",)`. The per-row finality signal is the existing
  `success_rate` (already in `COLUMN_ORDER` via the reducer — do NOT add a
  `finalized` column; review D2).
- **`_build_row`** (offline version):
  ```python
  def _build_row(records, result, meta, n, f, clipped_fraction, commit_hash):
      row = _generic_cols(records, result, meta, commit_hash=commit_hash)
      row.update(_REDUCERS[meta.protocol](records, result, meta))
      _window_denominator_fix(row, records, meta)
      view_changes = sum(1 for r in records if r.event_type == PBFT_VIEW_CHANGE)
      row["adversary_strategy"] = strategy_label(f, "withhold-participation")
      row["adversary_node_count"] = math.floor(f * n)
      row["byzantine_fraction"] = f
      row["view_change_count"] = view_changes
      row["clipped_fraction"] = clipped_fraction
      row["run_horizon_s"] = ocfg.T_MAX
      row["throughput_ratio"] = float("nan")   # post-pass fills this
      return row
  ```
- **Post-pass `_throughput_ratios(rows)`** — model exactly on T51's
  `_finality_delay_ratios` (sweep.py:151-173), but ratio of `tps` (not
  `commit_latency_ms`) to the same-(protocol,n,seed) f=0 control, with the
  identical NaN/None/≤0 guard (review D3). Control rows = 1.0.
- **`write_csv`** — sort by `(protocol, n, byzantine_fraction, seed)` (no
  `delay_mult`); fieldnames = `COLUMN_ORDER + ADV_COMMON_COLUMNS +
  ("throughput_ratio",)`; format generic via `_format_row`, common via
  `sweep_common.format_common_adv_cols`, and `throughput_ratio` via `:.6f`.
- **`_probe`** — print per (proto, n=10 AND n=25) at the **largest** f for that
  protocol: first-decision latency, clip %, in-window finalized count, AND
  `view_change_count`. Crucial: include the PBFT/FFG f=0.40 cells (the stall +
  view-change regime). This is the data that sets WINDOW/BUFFER/VC in Task 5.
- **`main`** — argparse with `--smoke`, `--probe`, `--out`, `--jobs`,
  `--heavy-jobs`, `--fresh`; checkpoint dir `.sweep_offline`; output
  `results/adversary/offline_validators.csv`.

**Step 1: Write a failing smoke test.**

`tests/adversary/test_offline_sweep.py`:
```python
import math
import unittest
from adversary.offline_sweep import run_sweep, _build_cells
from adversary import offline_config as oc


class TestOfflineSweep(unittest.TestCase):
    def test_cell_count(self):
        cells = _build_cells((0,))   # 1 seed
        # PBFT 5 f + FFG 5 f + Snowman 4 f, × 2 n × 1 seed = 28 cells.
        self.assertEqual(len(cells), (5 + 5 + 4) * 2)

    def test_smoke_one_seed_runs_and_rows_well_formed(self):
        rows, worst = run_sweep(seeds=(0,), jobs=1, heavy_jobs=1, fresh=True)
        self.assertEqual(len(rows), (5 + 5 + 4) * 2)
        for r in rows:
            self.assertIn(r["success_rate"], (0.0, 1.0))
            # control rows have throughput_ratio == 1.0
            if r["byzantine_fraction"] == 0.0:
                self.assertEqual(r["throughput_ratio"], 1.0)

    def test_pbft_boundary_crossed(self):
        rows, _ = run_sweep(seeds=(0,), jobs=1, heavy_jobs=1, fresh=True)
        by = {(r["protocol"], r["n"], r["byzantine_fraction"]): r["success_rate"]
              for r in rows}
        self.assertEqual(by[("pbft", 10, 0.33)], 1.0)   # quorum intact
        self.assertEqual(by[("pbft", 10, 0.40)], 0.0)   # quorum lost → stall
```

**Step 2: Run, verify failure** (module missing).

**Step 3: Implement `offline_sweep.py`** per the spec above.

**Step 4: Run the smoke test.**
Run: `make test-adversary`
Expected: PASS. `test_pbft_boundary_crossed` confirms the success/failure
boundary is genuinely crossed.

**Step 5: Determinism test — append to `tests/adversary/test_determinism.py`.**
```python
def test_offline_cell_byte_identical_rerun(self):
    from adversary.offline_sweep import _run_cell
    rc = {"commit_hash": "test"}
    a = _run_cell(("snowman", 10, 0.20, 0), rc)
    b = _run_cell(("snowman", 10, 0.20, 0), rc)
    self.assertEqual({k: a[k] for k in a if not (isinstance(a[k], float)
                     and math.isnan(a[k]))},
                     {k: b[k] for k in b if not (isinstance(b[k], float)
                     and math.isnan(b[k]))})
```
Run: `make test-adversary` — Expected: PASS.

**Step 6: Commit.**
```bash
git add src/adversary/offline_sweep.py tests/adversary/test_offline_sweep.py \
        tests/adversary/test_determinism.py
git commit -m "task 52: offline-validators sweep orchestrator"
```

---

## Task 5: Re-probe calibration (do NOT inherit T51 numbers)

**Files:** Modify `src/adversary/offline_config.py` (the three calibration constants).

**Why (design §6 / review D1, C5):** T51's WINDOW/BUFFER/VC were set on the
assumption that PBFT view-changes never fire and nothing stalls. Offline breaks
both: at f=0.40 PBFT loses quorum (the spared primary keeps proposing, backups
time out → **view-changes now fire**), and FFG enters a finalisation stall.

**Step 1: Run the probe.**
Run: `PYTHONPATH=src python3 -m adversary.offline_sweep --probe`
Read the printed first-decision latency, clip %, in-window finalized, and
view-change count for every (protocol, n) at its largest f — *especially* the
PBFT/FFG f=0.40 cells and the Snowman f=0.33 cells.

**Step 2: Set the constants from the probe.**
- `WINDOW_S` ≥ the slowest *finalizing* cell's first-decision latency with
  margin (Snowman at its worst f is the likely driver, as in T51).
- `BUFFER_S` ≥ one full slowest-protocol finalization so an instance starting
  near W can still finalize in-run.
- `ONE_ROUND_S["snowman"]` ≥ the worst Snowman single-block finalization.
- `PBFT_VC_DELAY_S`: confirm it is realistic and observe whether VCs fire at
  f=0.40 (they should). Record the observed count.
- Add a comment block citing the probe output (mirror T51 config.py:51-86).

**Step 3: Re-run the smoke + boundary tests** to confirm the new horizon still
finalizes the would-finalize cells.
Run: `make test-adversary` — Expected: PASS.

**Step 4: Commit.**
```bash
git add src/adversary/offline_config.py
git commit -m "task 52: probe-set offline window/buffer/view-change calibration"
```

---

## Task 6: Run the production sweep (single clean commit, no -dirty)

**Files:** Create `results/adversary/offline_validators.csv` (+ checkpoint dir,
gitignored).

**Why (T51 guardrail / design §9):** T51's CSV shipped a `*-dirty` commit_hash
because the sweep spanned two commits with a dirty tree. Run from a clean tree so
`commit_hash` resolves to one value.

**Step 1: Confirm a clean tree** (`git status` shows nothing uncommitted that
affects the cell-computation path).

**Step 2: Run the full sweep.**
Run: `PYTHONPATH=src python3 -m adversary.offline_sweep --jobs 8 --heavy-jobs 1`
Expected: `wrote N rows -> results/adversary/offline_validators.csv` with N =
(5+5+4)·2·20 = **560**, plus the worst clipped_fraction line.

**Step 3: Sanity-check the dataset** (use `sed`/`awk`, not `head`):
- Row count is 560; `success_rate` ∈ {0,1}; PBFT/FFG f=0.40 rows show
  `success_rate=0` (stall) and f≤0.33 show `success_rate=1`; Snowman degrades
  but does not hard-stall; `commit_hash` is a single non-dirty value.

**Step 4: Commit the dataset.**
```bash
git add results/adversary/offline_validators.csv
git commit -m "task 52: offline-validators dataset (560 rows)"
```

---

## Task 7: Offline figures

**Files:**
- Create: `src/output/offline_plots.py`
- (figures land in `results/adversary/plots/`, PDFs tracked)

**Why a new module (review D7):** `adversary_plots.py` is hard-wired to
`delay_mult` / `finality_delay_ratio` and facets on `m`; it cannot consume the
offline CSV. Reuse `STYLE`, `PROTO_ORDER` (`output.plots`) and `mean_ci`
(`output.delay_analysis`).

**Step 1: Implement `offline_plots.py`** with two figure families, one figure
per `n`:
- `fig_success_vs_f`: `finalization_success_rate` (mean of `success_rate` over
  seeds) vs offline fraction `f`, one line per protocol; mark the boundary `f*`.
- `fig_throughput_vs_f`: mean `throughput_ratio` (± 95% CI via `mean_ci`) vs `f`,
  with the §4 invariant reference line `(1−f)` drawn for comparison.

Mirror `adversary_plots.py`'s `_load`/`_save`/`_grid`/`_fnum` helpers and the
`render_all`/`main` shape. CSV path `results/adversary/offline_validators.csv`.

**Step 2: Run it.**
Run: `PYTHONPATH=src python3 -m output.offline_plots`
Expected: `wrote 4 figures -> results/adversary/plots: ...`.

**Step 3: Visually confirm** the success-rate plot shows the PBFT/FFG cliff
between 0.33 and 0.40 and Snowman's smoother decline.

**Step 4: Commit.**
```bash
git add src/output/offline_plots.py results/adversary/plots/*.pdf
git commit -m "task 52: offline-validators success-rate + throughput figures"
```

---

## Task 8: Wiki experiment page + catalog Revision + index/log

**Files:**
- Create: `wiki/experiments/2026-06-17_offline-validators.md`
- Modify: `wiki/index.md` (add the experiment under ## Experiments)
- Modify: `wiki/log.md` (append the task entry)
- Modify: `wiki/concepts/experiment-matrix-runs.md` (## Revisions entry)

**Step 1: Write the experiment page** following the T51 page
(`wiki/experiments/2026-06-14_delayed-voters.md`) as the template. Required
sections: Subsystem (the drop wrap; cite §4 same-gating-point), Config (grid,
no-m, per-protocol f, n, seeds, realized floor), **Calibration** (the Task 5
probe table + the re-probe rationale), Metrics & output (success_rate reused;
throughput_ratio; the finalization_success_rate aggregate + boundary f*),
**Findings** (per-protocol boundary f*; PBFT/FFG sharp cliff at 1/3 vs Snowman
proportional; expected: PBFT VCs fire at f=0.40 — report observed count), Seeds/
commit/re-run, Cost, and **Auggie verification** (pickup-index, plan, post-edit
queries — log the actual query strings and one-line results).

**Determinism wording fix (review C1):** state that suppressing a broadcast skips
that node's per-recipient **`net_rng` drop-coin draws** (constant delay consumes
no delay sample), so f>0 cells' RNG stream diverges from control — per-cell
deterministic, not a bug; do not write "delay samples."

**Step 2: Add the index line** under `## Experiments` in `wiki/index.md`:
`- [[experiments/2026-06-17_offline-validators]] — T52 ...` (one-line summary in
the established style).

**Step 3: Append the `wiki/log.md` entry** (format per `docs/wiki-spec.md`):
```
## [2026-06-17] experiment | task 52 — offline (non-participating) validators
- role: Engineer
- touched: src/adversary/{inject,profiles,runners,offline_config,sweep_common,offline_sweep}.py, src/output/offline_plots.py, results/adversary/offline_validators.csv, wiki/experiments/2026-06-17_offline-validators.md
- notes: <1–3 sentences>
```

**Step 4: Add the `## Revisions` entry** to
`wiki/concepts/experiment-matrix-runs.md` §3 recording the **f=0.40 PBFT/FFG
above-threshold extension** to the catalogued withhold grid (the human roadmap
decision 2026-06-17), with the rationale (floor-rounding keeps the catalogued
{0.10,0.20,0.33} below the cliff; f=0.40 crosses it so the boundary is
measurable). Note Snowman stays at the catalogued grid.

**Step 5: Commit.**
```bash
git add wiki/experiments/2026-06-17_offline-validators.md wiki/index.md \
        wiki/log.md wiki/concepts/experiment-matrix-runs.md
git commit -m "task 52: offline-validators experiment page + catalog revision"
```

---

## Task 9: Verification + flip to In Review

**Step 1: auggie post-edit re-query (mandatory).** Call
`mcp__auggie__codebase-retrieval` asking it to describe the new offline strategy
and locate its callers/coupling; confirm no shared-infra edits and that
`inject_delay` behaviour is unchanged. Record the query + result on the
experiment page's Auggie verification subsection.

**Step 2: Full suite.**
Run: `make test`
Expected: all suites green (every pre-existing protocol suite still passes —
proves the `inject.py`/`runners.py` refactor broke nothing).

**Step 3: T51 no-regression check.** Re-run a single T51 delay cell and confirm
its row is byte-identical to the committed `delayed_voters.csv` (modulo
`commit_hash`) — proves `_wrap_outbound` preserved delay behaviour:
Run: `PYTHONPATH=src python3 -m adversary.sweep --smoke` (or a one-cell harness)
and diff against the frozen witness row.

**Step 4: Invoke `superpowers:verification-before-completion`** — run the
verification commands, confirm output, make no success claim without evidence.

**Step 5: Flip status + Dashboard in `TASKS.md`.** T52 `[~]` → `[?]` In Review;
In Progress 1→0, In Review 0→1. Commit:
```bash
git add TASKS.md
git commit -m "task 52: offline non-participating validators (in review)"
```

**Step 6: Handoff summary for the human** — files touched, wiki pages
added/updated, the f=0.40 roadmap-extension decision, the boundary f* per
protocol, observed PBFT view-change behaviour at f=0.40, and any open questions.

---

## Notes / deferrals (documented, not silent)

- **Full Spec-driven sweep driver + T51 migration** (review D5/D6 in its
  strongest form) is deferred to T53, when a third consumer makes the
  generalization concrete (YAGNI). T51's frozen orchestrator/dataset stay
  untouched for reproducibility.
- **Snowman f=0.40** omitted by the human grid decision (0.40 scoped to the
  quorum protocols). Adding it later is ~40 runs if a symmetric max-f is wanted.
- **Out of scope** (design §10): FSM-hook adversaries (T53), §6 disrupt-leader
  (primary spared), Snowman β safety sweep, Narwhal+Tusk (T38.1), rewriting
  T51's CSV to a union schema.
```
