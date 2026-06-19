# T54 — Adversarial liveness & safety degradation metrics — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Drive each code task with superpowers:test-driven-development. Dispatch a verification subagent at every commit boundary; run superpowers:verification-before-completion before flipping T54 to In Review.

**Goal:** Derive the liveness metric and the four per-protocol safety invariants from the three existing Family-C adversarial CSVs, emit a byte-stable robustness table + figures, and pin the durable metric spec in the wiki — no sweep re-run.

**Architecture:** A pure-stdlib analysis module (`src/output/adversary_analysis.py`) reads `results/adversary/{delayed_voters,offline_validators,equivocating_nodes}.csv` by column name, computes liveness (mean `success_rate` + Wilson) across all three families and the four safety invariants from the equivocate family, and writes `results/adversary/degradation_ranking.csv` + `snowman_epsilon_witness.csv`. A matplotlib module (`adversary_degradation_plots.py`) renders the figures. Mirrors the T48 `delay_analysis.py`/`delay_plots.py` split; clones the `offline_plots.py` figure idiom. Design contract: `docs/plans/2026-06-19-t54-adversarial-degradation-metrics-design.md`.

**Tech Stack:** Python 3 stdlib (`csv`, `math`, `dataclasses`, `collections`), `matplotlib` (Agg backend) for the render layer only, `unittest`. Reuses `output.analysis` (Student-t) + `output.delay_analysis.mean_ci` + `output.plots` (STYLE/PROTO_ORDER).

---

## Conventions (apply to every task)

- **Read by NAME**, never by column position — the three CSV tails diverge in membership *and* order.
- `_fnum(x)` = `float(x)` guarded to `nan` (copy the existing helper).
- φ = the `byzantine_fraction` column (the §3.4.2 convention symbol; `f` is the `n=3f+1` threshold).
- Safety signals are **seed-invariant** → no CI on safety; Wilson only on the liveness proportion.
- Concept name is **"safety-violation rate"**; the literal `fork_rate` column is referenced only as a column name.
- Output dir is `results/adversary/` (the task/T55 `results/adversarial/` spelling is a typo — flag in handoff, do not create the `-al` dir).
- Human commits; agent does not run `git commit`. The `git commit` blocks below are the *intended* boundaries — stage and report; the human commits. Do **not** mark T54 Completed.

---

## Task 1: Wilson interval helper in `analysis.py`

**Files:**
- Modify: `src/output/analysis.py` (add `wilson_interval`)
- Test: `tests/output/test_analysis.py` (add a `TestWilson` class)

**Step 1 — failing test:**

```python
# add to tests/output/test_analysis.py
import math, unittest
from output.analysis import wilson_interval

class TestWilson(unittest.TestCase):
    def test_zero_of_twenty_upper_bound(self):
        lo, hi = wilson_interval(0, 20)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.161, places=3)   # honest boundary (~0.16)

    def test_zero_of_thirty_upper_bound(self):
        lo, hi = wilson_interval(0, 30)
        self.assertAlmostEqual(hi, 0.113, places=3)   # matches ch3 §3.5 "≈0.11"

    def test_full_success_lower_bound(self):
        lo, hi = wilson_interval(20, 20)
        self.assertEqual(hi, 1.0)
        self.assertAlmostEqual(lo, 0.839, places=3)

    def test_half(self):
        lo, hi = wilson_interval(10, 20)
        self.assertLess(lo, 0.5)
        self.assertGreater(hi, 0.5)

    def test_empty_is_nan(self):
        lo, hi = wilson_interval(0, 0)
        self.assertTrue(math.isnan(lo) and math.isnan(hi))
```

**Step 2 — run, expect FAIL** (`ImportError: cannot import name 'wilson_interval'`):

`PYTHONPATH=src python3 -m pytest tests/output/test_analysis.py::TestWilson -v` (or `python3 -m unittest`).

**Step 3 — implement** (append to `src/output/analysis.py`):

```python
def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Two-sided Wilson score interval for a binomial proportion k/n.

    Honest at the boundary: a 0-of-n or n-of-n cell yields a non-degenerate
    interval (the normal approximation collapses to a point there). z = 1.96
    is the two-sided 95% normal critical value. n <= 0 -> (nan, nan). Used for
    the liveness success-rate and the Snowman empirical-epsilon upper bound
    (ch3_methodology.md §3.5 commits Wilson for rate metrics).
    """
    if n <= 0:
        return (float("nan"), float("nan"))
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / denom
    return (max(0.0, center - half), min(1.0, center + half))
```

**Step 4 — run, expect PASS.** Also run the whole `output` suite: `make test-output` (or `PYTHONPATH=src python3 -m unittest discover -s tests/output`). Expect green.

**Step 5 — commit:** `git add src/output/analysis.py tests/output/test_analysis.py && git commit -m "task 54: add Wilson score interval helper"`

**Verification boundary:** dispatch a verification subagent — confirm the Wilson math (0/20→~0.16, 0/30→~0.11), no regression in `test_analysis.py`.

---

## Task 2: `adversary_analysis.py` — loader + liveness + safety reducers

**Files:**
- Create: `src/output/adversary_analysis.py`
- Test: `tests/output/test_adversary_analysis.py`

**Step 1 — failing tests** (synthetic; create the test file):

```python
"""Unit + regression tests for src/output/adversary_analysis.py (T54).

Data layer only (render layer in adversary_degradation_plots.py is not tested,
per project convention). Synthetic cases pin the loader/reducer/bracket math;
real-dataset cases lock the verified f_max brackets + the Snowman epsilon
witness so a methodology regression cannot pass silently.
"""
import math, os, tempfile, csv, unittest
from output import adversary_analysis as aa


def _write(path, cols, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


class TestLoader(unittest.TestCase):
    def test_family_tagging_and_by_name(self):
        with tempfile.TemporaryDirectory() as d:
            _write(os.path.join(d, "offline_validators.csv"),
                   ["protocol", "n", "seed", "byzantine_fraction", "success_rate"],
                   [{"protocol": "pbft", "n": 10, "seed": 0,
                     "byzantine_fraction": 0.0, "success_rate": 1.0}])
            rows = aa.load_adversary_rows(d)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["family"], "offline")


class TestLiveness(unittest.TestCase):
    def test_rate_and_wilson(self):
        rows = [{"family": "equivocate", "protocol": "casper-ffg", "n": 10,
                 "seed": s, "byzantine_fraction": 0.20,
                 "success_rate": (1.0 if s < 15 else 0.0)} for s in range(20)]
        cells = aa.liveness_rate(rows, "equivocate", "casper-ffg", 10)
        self.assertAlmostEqual(cells[0.20].mean, 0.75)
        self.assertEqual(cells[0.20].k, 15)
        self.assertEqual(cells[0.20].n_seeds, 20)


class TestSafetyReducers(unittest.TestCase):
    def _equiv(self, proto, n, phi, **extra):
        base = {"family": "equivocate", "protocol": proto, "n": n, "seed": 0,
                "byzantine_fraction": phi, "run_horizon_s": 230.0,
                "view_change_count": 0, "safety_violation": 0,
                "conflicting_instances": 0, "max_slashable_stake_fraction": 0.0,
                "K": 9, "alpha_p": 5, "alpha_c": 8, "beta": 15}
        base.update(extra); return base

    def test_pbft_view_change_rate(self):
        rows = [self._equiv("pbft", 10, 0.20, view_change_count=10)]
        r = aa.pbft_view_change_rate(rows, 10)
        self.assertAlmostEqual(r[0.20].mean, 10 / 230.0)

    def test_ffg_slashable(self):
        rows = [self._equiv("casper-ffg", 10, 0.40, max_slashable_stake_fraction=0.40)]
        r = aa.ffg_slashable(rows, 10)
        self.assertAlmostEqual(r[0.40].mean, 0.40)

    def test_snowman_epsilon_witness_zero_empirical(self):
        rows = [self._equiv("snowman", 10, phi, K=9, alpha_c=8, beta=15)
                for phi in (0.0, 0.10, 0.20, 0.33) for _ in range(20)]
        w = aa.snowman_epsilon_witness(rows, 10)
        self.assertEqual(w.empirical_rate, 0.0)
        self.assertAlmostEqual(w.analytical_bound, (1 - 8/9) ** 15)
        self.assertGreater(w.empirical_wilson_hi, 0.0)

    def test_nwt_is_deferred(self):
        self.assertEqual(aa.nwt_invariant()["status"], "deferred")


if __name__ == "__main__":
    unittest.main()
```

**Step 2 — run, expect FAIL** (module missing).

**Step 3 — implement** `src/output/adversary_analysis.py` (reducers half; the f_max/CSV half lands in Task 3):

```python
"""T54 — adversarial liveness & safety degradation analysis.

Pure-stdlib reducers over the three committed Family-C adversarial CSVs:

- results/adversary/delayed_voters.csv      (T51 delay-emission)
- results/adversary/offline_validators.csv  (T52 withhold-participation)
- results/adversary/equivocating_nodes.csv  (T53 equivocate-vote)

Liveness (% of seed-runs reaching consensus = mean(success_rate) + Wilson) is
measured across all three families; the four per-protocol SAFETY invariants
(adversary-model §5/§7) come from the equivocate family only — the sole sweep
that carries them. Safety signals are seed-invariant (deterministic parity
partition, no adversary RNG), so they carry no CI; only the liveness proportion
gets a Wilson band. No third-party dependency, no matplotlib (headless-testable
like analysis.py). Design: docs/plans/2026-06-19-t54-adversarial-degradation-metrics-design.md
"""
from __future__ import annotations

import csv
import math
import os
from collections import defaultdict
from dataclasses import dataclass

from output.analysis import wilson_interval
from output.delay_analysis import mean_ci, MeanCI

ADVERSARY_DIR = "results/adversary"
RANKING_CSV = "results/adversary/degradation_ranking.csv"
EPSILON_CSV = "results/adversary/snowman_epsilon_witness.csv"

# filename -> family tag.
FAMILIES = {
    "delayed_voters.csv": "delay",
    "offline_validators.csv": "offline",
    "equivocating_nodes.csv": "equivocate",
}
PROTO_ORDER = ("pbft", "casper-ffg", "snowman")
NS = (10, 25)
PHI = "byzantine_fraction"


def _fnum(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def load_rows(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_adversary_rows(adversary_dir: str = ADVERSARY_DIR) -> list[dict]:
    """Load all present Family-C CSVs, tagging each row with `family`.

    Reads by column name (the three tails diverge in membership and order).
    Missing files are skipped (so a partial checkout still loads what exists).
    """
    out: list[dict] = []
    for fname, family in FAMILIES.items():
        path = os.path.join(adversary_dir, fname)
        if not os.path.exists(path):
            continue
        for r in load_rows(path):
            r = dict(r)
            r["family"] = family
            out.append(r)
    return out


# --------------------------------------------------------------------------- #
# Liveness (all three families)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class LivenessCell:
    phi: float
    mean: float        # mean(success_rate) over the cell's runs
    lo: float          # Wilson lower
    hi: float          # Wilson upper
    k: int             # successes
    n_seeds: int       # runs in the cell (delay pools over the m axis)


def liveness_rate(rows, family, protocol, n) -> dict[float, LivenessCell]:
    """{phi: LivenessCell} for one (family, protocol, n) group.

    For the delay family this pools over the magnitude axis (delay_mult) at each
    phi — the liveness pattern is m-invariant (FFG proposer-overlap dips do not
    depend on m), so the pooled proportion is representative and gives a tighter
    Wilson band. success_rate is a per-run 0/1 flag.
    """
    buckets: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        if r["family"] != family or r["protocol"] != protocol or int(r["n"]) != n:
            continue
        buckets[round(_fnum(r[PHI]), 4)].append(_fnum(r["success_rate"]))
    out: dict[float, LivenessCell] = {}
    for phi, vals in buckets.items():
        finite = [v for v in vals if not math.isnan(v)]
        nn = len(finite)
        k = sum(1 for v in finite if v >= 0.5)
        lo, hi = wilson_interval(k, nn)
        out[phi] = LivenessCell(phi, k / nn if nn else float("nan"), lo, hi, k, nn)
    return out


# --------------------------------------------------------------------------- #
# Safety invariants (equivocate family only)
# --------------------------------------------------------------------------- #

def _equiv_cell(rows, protocol, n, metric) -> dict[float, MeanCI]:
    buckets: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        if (r["family"] != "equivocate" or r["protocol"] != protocol
                or int(r["n"]) != n):
            continue
        buckets[round(_fnum(r[PHI]), 4)].append(_fnum(r[metric]))
    return {phi: mean_ci(v) for phi, v in buckets.items()}


def pbft_view_change_rate(rows, n) -> dict[float, MeanCI]:
    """PBFT §5 operational invariant: view-change frequency tracks equivocator
    rate. {phi: MeanCI of view_change_count / run_horizon_s}. Seed-invariant in
    the equivocate data (zero-width CI), reported as the mean."""
    buckets: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        if (r["family"] != "equivocate" or r["protocol"] != "pbft"
                or int(r["n"]) != n):
            continue
        horizon = _fnum(r["run_horizon_s"])
        vc = _fnum(r["view_change_count"])
        buckets[round(_fnum(r[PHI]), 4)].append(
            vc / horizon if horizon > 0 else float("nan"))
    return {phi: mean_ci(v) for phi, v in buckets.items()}


def ffg_slashable(rows, n) -> dict[float, MeanCI]:
    """Casper FFG §7.3 accountable-safety invariant: max_slashable_stake_fraction
    vs the 1/3 threshold. {phi: MeanCI}."""
    return _equiv_cell(rows, "casper-ffg", n, "max_slashable_stake_fraction")


def safety_violation_rate(rows, protocol, n) -> dict[float, MeanCI]:
    """Cross-node safety-violation rate (mean of the 0/1 safety_violation flag)
    for `protocol` on the equivocate family. {phi: MeanCI}; used by the f_max
    bracket and the cross-protocol cliff figure."""
    return _equiv_cell(rows, protocol, n, "safety_violation")


@dataclass(frozen=True)
class EpsilonWitness:
    n: int
    K: int
    alpha_c: int
    beta: int
    empirical_rate: float       # mean(safety_violation) over all Snowman runs at n
    empirical_wilson_hi: float  # Wilson upper bound on the 0-of-n_obs proportion
    analytical_bound: float     # (1 - alpha_c/K)^beta
    n_obs: int


def snowman_epsilon_witness(rows, n) -> EpsilonWitness | None:
    """Snowman §5/§7.1 invariant: empirical safety-violation rate <= (1-alpha_c/K)^beta.

    Empirical = mean(safety_violation) over ALL Snowman equivocate runs at this n
    (pooled across phi — the analytical bound is a per-n constant), with a Wilson
    upper bound. The empirical rate is structurally 0 at production beta=15; the
    bound is ~10^-15 (n=10) / ~10^-11 (n=25). The witness reports both — the
    invariant holds trivially. (The beta in {3,5} observability regime is deferred
    to a separate RQ4 sweep; not run here.)
    """
    sel = [r for r in rows if r["family"] == "equivocate"
           and r["protocol"] == "snowman" and int(r["n"]) == n]
    if not sel:
        return None
    k = sum(int(_fnum(r["safety_violation"])) for r in sel)
    nn = len(sel)
    K = int(_fnum(sel[0]["K"]))
    alpha_c = int(_fnum(sel[0]["alpha_c"]))
    beta = int(_fnum(sel[0]["beta"]))
    bound = (1.0 - alpha_c / K) ** beta if K else float("nan")
    _, hi = wilson_interval(k, nn)
    return EpsilonWitness(n, K, alpha_c, beta,
                          k / nn if nn else float("nan"), hi, bound, nn)


def nwt_invariant() -> dict:
    """Narwhal+Tusk §5 invariant (no conflicting header reaches 2f+1 signatures).

    Unmeasurable: NWT is unimplemented (T38.1, sequenced post-T55). Returned as
    an explicit deferral so the ranking table documents the gap rather than
    emitting a silent NaN row (output-format.md §4 absent-vs-NaN distinction).
    """
    return {"protocol": "narwhal-tusk",
            "invariant": "conflicting_header_reaches_2f1",
            "status": "deferred", "blocked_by": "T38.1",
            "note": "NWT unimplemented; defined in spec, measured when T38.1 lands"}
```

**Step 4 — run, expect PASS** on `TestLoader`/`TestLiveness`/`TestSafetyReducers`. Run `make test-output`. Expect green.

**Step 5 — commit:** `git add src/output/adversary_analysis.py tests/output/test_adversary_analysis.py && git commit -m "task 54: adversary_analysis loader + liveness + safety reducers"`

**Verification boundary:** verification subagent — confirm the loader reads by name, liveness pools the delay m-axis, the four reducers map to the right columns, ε bound `(1-8/9)^15` matches.

---

## Task 3: `adversary_analysis.py` — f_max bracket estimator + ranking CSVs

**Files:**
- Modify: `src/output/adversary_analysis.py` (add `bracket`, `f_max_for`, dataclasses, `write_ranking_csv`, `write_epsilon_witness_csv`, `main`)
- Test: `tests/output/test_adversary_analysis.py` (add `TestBracket`, `TestRealDataset`)

**Step 1 — failing tests** (append):

```python
class TestBracket(unittest.TestCase):
    def test_holds_then_breaks(self):
        # PBFT safety: holds (safety_violation==0) through 0.33, breaks at 0.40.
        holds = {0.0: True, 0.10: True, 0.20: True, 0.33: True, 0.40: False, 0.50: False}
        hold, brk = aa.bracket(holds.keys(), lambda p: holds[p])
        self.assertEqual(hold, 0.33)
        self.assertEqual(brk, 0.40)

    def test_right_censored_never_breaks(self):
        holds = {0.0: True, 0.10: True, 0.20: True, 0.33: True}
        hold, brk = aa.bracket(holds.keys(), lambda p: holds[p])
        self.assertEqual(hold, 0.33)
        self.assertIsNone(brk)

    def test_left_censored_breaks_immediately(self):
        holds = {0.0: True, 0.10: False}   # phi=0 control always holds
        hold, brk = aa.bracket(holds.keys(), lambda p: holds[p])
        self.assertEqual(hold, 0.0)
        self.assertEqual(brk, 0.10)


class TestRealDataset(unittest.TestCase):
    """Lock verified brackets/witness against the committed equivocate CSV."""
    def setUp(self):
        self.rows = aa.load_adversary_rows()
        if not any(r["family"] == "equivocate" for r in self.rows):
            self.skipTest("adversary CSVs not present")

    def test_pbft_safety_bracket_is_033_to_040(self):
        fm = aa.f_max_for(self.rows, "safety", "pbft", 10)
        self.assertEqual(fm.f_max_hold, 0.33)
        self.assertEqual(fm.f_max_break, 0.40)
        self.assertFalse(math.isnan(fm.f_max_count))
        self.assertTrue(math.isnan(fm.f_max_stake))

    def test_ffg_slashable_crosses_third_at_040(self):
        fm = aa.f_max_for(self.rows, "safety", "casper-ffg", 10)
        # holds (< 1/3) through 0.33, crosses at 0.40 -> stake column populated.
        self.assertEqual(fm.f_max_hold, 0.33)
        self.assertEqual(fm.f_max_break, 0.40)
        self.assertTrue(math.isnan(fm.f_max_count))
        self.assertFalse(math.isnan(fm.f_max_stake))

    def test_snowman_safety_right_censored(self):
        fm = aa.f_max_for(self.rows, "safety", "snowman", 10)
        self.assertEqual(fm.f_max_hold, 0.33)
        self.assertIsNone(fm.f_max_break)

    def test_pbft_safety_broken_flag_above_third(self):
        # The fork cliff: phi>=0.40 PBFT cells are live-but-forked.
        rate = aa.safety_violation_rate(self.rows, "pbft", 10)
        self.assertEqual(rate[0.33].mean, 0.0)
        self.assertEqual(rate[0.40].mean, 1.0)

    def test_snowman_epsilon_witness_real(self):
        w = aa.snowman_epsilon_witness(self.rows, 10)
        self.assertEqual(w.empirical_rate, 0.0)
        self.assertAlmostEqual(w.analytical_bound, (1 - 8/9) ** 15)

    def test_ranking_csv_is_byte_stable(self):
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = os.path.join(d, "a.csv"), os.path.join(d, "b.csv")
            aa.write_ranking_csv(p1)
            aa.write_ranking_csv(p2)
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                self.assertEqual(f1.read(), f2.read())
```

**Step 2 — run, expect FAIL** (`bracket`/`f_max_for`/`write_ranking_csv` missing).

**Step 3 — implement** (append to `src/output/adversary_analysis.py`):

```python
# --------------------------------------------------------------------------- #
# f_max bracket estimator (Backlog item (b))
# --------------------------------------------------------------------------- #

def bracket(phi_grid, holds_at):
    """Interval-censored f_max over a sorted phi grid.

    Returns (hold_edge, break_edge): hold_edge = largest phi (scanning up) still
    holding before the first break; break_edge = first phi that breaks. The
    headline f_max is the hold_edge (largest-phi-that-holds, per the binding
    evaluation-metrics.md definition); the bracket [hold_edge, break_edge] is
    the censoring interval. Right-censored (never breaks) -> (max phi, None).
    Departs from T48's AURC: the equivocate axis is a discrete cliff, so the
    robustness scalar is this bracket, not an area under a smooth curve.
    """
    hold, brk = None, None
    for phi in sorted(phi_grid):
        if holds_at(phi):
            if brk is None:        # only extend the hold edge before the break
                hold = phi
        else:
            brk = phi
            break
    return (hold, brk)


THIRD = 1.0 / 3.0


@dataclass(frozen=True)
class FMaxRow:
    family: str            # delay / offline / equivocate
    metric: str            # liveness / safety
    invariant: str         # human-readable invariant id
    protocol: str
    n: int
    f_max_hold: float      # headline f_max (largest phi that holds); may be None
    f_max_break: float     # upper censoring edge; None if right-censored
    f_max_count: float     # populated for pbft/snowman/nwt, else NaN
    f_max_stake: float     # populated for casper-ffg, else NaN
    theoretical_bound: str
    safety_broken: bool    # PBFT live-but-forked phi region exists
    note: str


_THEORETICAL = {
    "pbft": "< n/3 (count)",
    "casper-ffg": "< 1/3 stake",
    "snowman": "parameter-dependent (alpha_c/K, beta)",
}


def _route(protocol, hold):
    """(f_max_count, f_max_stake): one populated by fault-attribution model."""
    val = float("nan") if hold is None else float(hold)
    if protocol == "casper-ffg":
        return (float("nan"), val)
    return (val, float("nan"))      # pbft / snowman (count)


def f_max_for(rows, metric, protocol, n) -> FMaxRow:
    """Compute the f_max bracket for one (metric, protocol, n).

    metric == "liveness": holds_at(phi) = mean(success_rate) >= 1.0 (full
    finalization), across the protocol's family — here the equivocate family
    (the safety-paired liveness); the delay/offline liveness brackets are built
    the same way per family in write_ranking_csv.
    metric == "safety": per-protocol invariant predicate.
    """
    family = "equivocate"
    if metric == "liveness":
        cells = liveness_rate(rows, family, protocol, n)
        grid = sorted(cells)
        hold, brk = bracket(grid, lambda p: cells[p].mean >= 1.0 - 1e-9)
        # PBFT non-monotone: live again above 1/3 where the FORK decides.
        broken = (protocol == "pbft"
                  and any(safety_violation_rate(rows, "pbft", n).get(p,
                          MeanCI(0, 0, 0, 0, 0)).mean > 0 for p in grid))
        inv, bound = "termination (success_rate>=1)", ""
        note = ("PBFT recovery via view-change pushes finalization past the "
                "measurement window at phi in {0.10,0.20} (window artifact, "
                "PBFT_VC_DELAY=3s); live again at phi>=0.40 via an UNSAFE fork"
                if protocol == "pbft" else "")
    elif protocol == "pbft":
        rate = safety_violation_rate(rows, "pbft", n)
        grid = sorted(rate)
        hold, brk = bracket(grid, lambda p: rate[p].mean == 0.0)
        broken = any(rate[p].mean > 0 for p in grid)
        inv = "no two-honest commit conflict at same (view,seq)"
        bound = _THEORETICAL["pbft"]
        note = "below 1/3: view-change rotation (safety holds); fork cliff above"
    elif protocol == "casper-ffg":
        slash = ffg_slashable(rows, n)
        grid = sorted(slash)
        hold, brk = bracket(grid, lambda p: slash[p].mean < THIRD)
        broken = any(slash[p].mean >= THIRD for p in grid)
        inv = "slashable stake < 1/3 (accountable safety)"
        bound = _THEORETICAL["casper-ffg"]
        note = ("never forks in-model; signal is economically-possible "
                "violation crossing the 1/3 slashing threshold")
    elif protocol == "snowman":
        rate = safety_violation_rate(rows, "snowman", n)
        grid = sorted(rate)
        hold, brk = bracket(grid, lambda p: rate[p].mean == 0.0)
        broken = False
        inv = "empirical safety-violation rate <= (1-alpha_c/K)^beta"
        bound = _THEORETICAL["snowman"]
        note = "no fork surface (equivocate reduces to lying-responder); see epsilon witness"
    else:
        raise ValueError(protocol)

    count, stake = _route(protocol, hold)
    return FMaxRow(family=family, metric=metric, invariant=inv, protocol=protocol,
                   n=n, f_max_hold=hold if hold is not None else float("nan"),
                   f_max_break=brk if brk is not None else float("nan"),
                   f_max_count=count, f_max_stake=stake, theoretical_bound=bound,
                   safety_broken=broken, note=note)


def _liveness_fmax(rows, family, protocol, n) -> FMaxRow:
    """Liveness bracket for an arbitrary family (delay/offline/equivocate)."""
    cells = liveness_rate(rows, family, protocol, n)
    grid = sorted(cells)
    hold, brk = bracket(grid, lambda p: cells[p].mean >= 1.0 - 1e-9)
    count, stake = _route(protocol, hold)
    return FMaxRow(family=family, metric="liveness",
                   invariant="termination (success_rate>=1)", protocol=protocol,
                   n=n, f_max_hold=hold if hold is not None else float("nan"),
                   f_max_break=brk if brk is not None else float("nan"),
                   f_max_count=count, f_max_stake=stake, theoretical_bound="",
                   safety_broken=False, note="")


_RANK_FIELDS = ("family", "metric", "invariant", "protocol", "n",
                "f_max_hold", "f_max_break", "f_max_count", "f_max_stake",
                "theoretical_bound", "safety_broken", "note")


def build_ranking(rows) -> list[FMaxRow]:
    out: list[FMaxRow] = []
    # Liveness across all three families.
    for family in ("delay", "offline", "equivocate"):
        for proto in PROTO_ORDER:
            for n in NS:
                if liveness_rate(rows, family, proto, n):
                    out.append(_liveness_fmax(rows, family, proto, n))
    # Safety from the equivocate family (3 implemented protocols).
    for proto in PROTO_ORDER:
        for n in NS:
            if _equiv_cell(rows, proto, n, "safety_violation"):
                out.append(f_max_for(rows, "safety", proto, n))
    # NWT deferral (documented, not silent NaN).
    nwt = nwt_invariant()
    for n in NS:
        out.append(FMaxRow("equivocate", "safety", nwt["invariant"],
                           "narwhal-tusk", n, float("nan"), float("nan"),
                           float("nan"), float("nan"), "< n/3 (count)", False,
                           nwt["note"]))
    return out


def write_ranking_csv(path: str = RANKING_CSV,
                      adversary_dir: str = ADVERSARY_DIR) -> str:
    rows = build_ranking(load_adversary_rows(adversary_dir))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_RANK_FIELDS)
        for r in rows:
            w.writerow([getattr(r, fld) for fld in _RANK_FIELDS])
    return path


_EPS_FIELDS = ("n", "K", "alpha_c", "beta", "empirical_rate",
               "empirical_wilson_hi", "analytical_bound", "n_obs")


def write_epsilon_witness_csv(path: str = EPSILON_CSV,
                              adversary_dir: str = ADVERSARY_DIR) -> str:
    rows = load_adversary_rows(adversary_dir)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_EPS_FIELDS)
        for n in NS:
            wt = snowman_epsilon_witness(rows, n)
            if wt:
                w.writerow([getattr(wt, fld) for fld in _EPS_FIELDS])
    return path


def main() -> None:
    print("wrote", write_ranking_csv())
    print("wrote", write_epsilon_witness_csv())


if __name__ == "__main__":
    main()
```

**Step 4 — run.** First the synthetic `TestBracket` (expect PASS). Then run `TestRealDataset` — these assert against the committed CSV. If a locked value differs from the asserted anchor, **read the actual value off the CSV and correct the assertion** (the anchors here — PBFT bracket [0.33,0.40], FFG crosses at 0.40, Snowman right-censored, ε bound `(1-8/9)^15` — come from the verified workflow read; reconcile any drift to the data, not the other way). Run `make test-output`. Expect green.

**Step 5 — generate + commit:** generate the artifacts, then stage:

```bash
PYTHONPATH=src python3 -m output.adversary_analysis   # writes the two CSVs
git add src/output/adversary_analysis.py tests/output/test_adversary_analysis.py \
        results/adversary/degradation_ranking.csv results/adversary/snowman_epsilon_witness.csv
git commit -m "task 54: f_max bracket estimator + degradation ranking CSVs"
```

**Verification boundary:** verification subagent — re-derive the brackets from the CSV by hand, confirm count/stake routing, byte-stability, the PBFT `safety_broken` flag, and that the NWT row is a documented deferral (not silent NaN).

---

## Task 4: `adversary_degradation_plots.py` + smoke test + figures

**Files:**
- Create: `src/output/adversary_degradation_plots.py`
- Test: `tests/output/test_adversary_degradation_plots.py`

**Step 1 — failing smoke test** (clone `test_adversary_plots.py`; build a tiny synthetic equivocate-shaped CSV with the columns the figures read — `protocol,n,seed,byzantine_fraction,success_rate,view_change_count,run_horizon_s,max_slashable_stake_fraction,safety_violation` — write it as `equivocating_nodes.csv` plus minimal `offline_validators.csv`/`delayed_voters.csv` in the temp dir, call `render_all(tmp_adversary_dir, tmp_plot_dir)`, assert each `name.pdf`/`name.png` exists).

**Step 2 — run, expect FAIL** (module missing).

**Step 3 — implement** `src/output/adversary_degradation_plots.py`. Clone the `offline_plots.py` idiom exactly (`_save`, `_grid`, `_cell_means`-style helpers, `matplotlib.use("Agg")`, dual PNG@150dpi + PDF, `PLOT_DIR = "results/adversary/plots"`, `STYLE`/`PROTO_ORDER` from `output.plots`). Figures:

- `fig_liveness_vs_phi` — one figure per family (`delay`/`offline`/`equivocate`), `mean(success_rate)` + Wilson band (use `LivenessCell.lo/.hi` as asymmetric error bars) vs φ, one curve per protocol, faceted 1×2 by n. PBFT non-monotone caveat in the title/caption for the equivocate panel.
- `fig_pbft_viewchange_rate_vs_phi` — `pbft_view_change_rate` vs φ, faceted by n (equivocate); annotate the φ≥0.40 collapse-to-0 (fork replaces rotation).
- `fig_ffg_slashable_vs_phi` — `ffg_slashable` vs φ with a horizontal `y = 1/3` reference line (clone the `y = 1-f` line idiom), faceted by n.
- `fig_safety_cliff_vs_phi` — `safety_violation_rate` for all three protocols vs φ, faceted by n; PBFT's 0→1 step at [0.33,0.40] is the headline.

`render_all(adversary_dir=ADVERSARY_DIR, plot_dir=PLOT_DIR)` loads via `adversary_analysis.load_adversary_rows`, calls each figure, returns the names. `main()` prints the count.

**Step 4 — run smoke test, expect PASS.** Then generate the real figures: `PYTHONPATH=src python3 -m output.adversary_degradation_plots`. Confirm PDFs+PNGs land in `results/adversary/plots/`.

**Step 5 — commit** (PDFs tracked, PNGs gitignored — confirm `.gitignore` already excludes `results/**/*.png` under the adversary re-includes; if PNGs are not ignored, do not stage them):

```bash
git add src/output/adversary_degradation_plots.py tests/output/test_adversary_degradation_plots.py \
        results/adversary/plots/*.pdf
git commit -m "task 54: adversarial degradation figures"
```

**Verification boundary:** verification subagent — smoke test green; the four figure families render for both n; Wilson bands present on liveness; the 1/3 line on FFG; no NWT curve (3-protocol STYLE).

---

## Task 5: Wiki metric-spec concept page

**Files:**
- Create: `wiki/concepts/adversarial-degradation-metrics.md`
- Modify: `wiki/index.md` (Concepts section)

**Content** (technical register; the durable "metrics spec" deliverable):
- **Liveness:** `% of seed-runs reaching consensus = mean(success_rate)` per `(family,protocol,n,φ)` + Wilson; the delay-family m-pooling note; the PBFT non-monotone / window-artifact caveat (report jointly with safety; flag φ≥0.40 PBFT as live-but-forked).
- **The four safety invariants** (per-protocol operationalization, each citing `[[concepts/adversary-model#...]]`): PBFT view-change rate + fork cliff; Casper FFG slashable-stake-vs-⅓ (with the in-model no-fork fidelity note); Snowman empirical-vs-analytical ε witness; Narwhal+Tusk deferred-with-T38.1 (defined, not measured).
- **f_max bracket estimator:** the interval-censored `[hold,break]` bracket; headline = hold edge (largest-φ-that-holds, reconciling `[[concepts/evaluation-metrics]]` "largest-that-holds" vs §3.5 "smallest-that-breaks"); `f_max_count`/`f_max_stake` routing; **no CI on safety** (seed-invariance); the deliberate **departure from T48's AURC** (discrete cliff, not smooth curve).
- Back-links: `[[concepts/adversary-model]]`, `[[concepts/adversary-model-runtime]]`, `[[concepts/evaluation-metrics]]`, `[[concepts/metric-reconciliation]]`, `[[concepts/output-format]]`, `[[experiments/2026-06-19_adversarial-degradation]]`.

Add the index line under `## Concepts`. Commit: `git add wiki/concepts/adversarial-degradation-metrics.md wiki/index.md && git commit -m "task 54: adversarial degradation metrics spec (wiki)"`.

**Verification boundary:** verification subagent — every wikilink resolves; the four invariants + liveness + f_max are pinned; concept name "safety-violation rate" (no `fork_rate` as a concept).

---

## Task 6: Experiment page, index/log, post-edit auggie, In Review

**Files:**
- Create: `wiki/experiments/2026-06-19_adversarial-degradation.md`
- Modify: `wiki/index.md` (Experiments), `wiki/log.md`, `TASKS.md` (T54 → In Review)

**Step 1 — post-edit auggie re-query (MANDATORY):** call `mcp__auggie__codebase-retrieval` asking it to describe the new `adversary_analysis.py` / `adversary_degradation_plots.py` behavior and locate callers; capture the query + one-line result.

**Step 2 — experiment page:** config (3 source CSVs + commits, **T51 `8b2d0bb0-dirty` flagged**), the derived artifacts (`degradation_ranking.csv`, `snowman_epsilon_witness.csv`, figures), exact re-run commands (`python3 -m output.adversary_analysis`, `… adversary_degradation_plots`), one-paragraph observation (PBFT fork cliff [0.33,0.40]; FFG slashing crosses ⅓ at 0.40; Snowman ε=0 vs bound; liveness shapes per family; the PBFT window-artifact caveat), the **deferrals** (NWT, β∈{3,5}, §3.5 gloss sync), and the **## Auggie verification** subsection (pickup-index + plan + post-edit queries, each: query string, one-line result, phase).

**Step 3 — index + log:** add the experiment line under `## Experiments`; append the `wiki/log.md` entry (`## [2026-06-19] experiment | task 54 — adversarial degradation metrics`, role Engineer, touched files, 1–3 sentence note).

**Step 4 — verification-before-completion:** run `superpowers:verification-before-completion`. Then `make test` (full suite) — expect all suites green. Re-confirm byte-stable CSVs.

**Step 5 — flip status:** `TASKS.md` T54 `[~]` → `[?]` (In Review) and the dashboard (`In Progress: 1 → 0`, `In Review: 0 → 1`). Do **not** mark Completed.

**Step 6 — commit:** `git add wiki/experiments/2026-06-19_adversarial-degradation.md wiki/index.md wiki/log.md TASKS.md && git commit -m "task 54: adversarial degradation experiment page + In Review"`. Then push the branch and write the human handoff (files touched, wiki pages, decisions, the flagged follow-ups: §3.5 f_max gloss Writer sync, β∈{3,5} ε sweep, NWT-with-T38.1, the `results/adversarial/` typo, T55 consumes this).

**Verification boundary:** final verification subagent + `superpowers:verification-before-completion` — full `make test` green, auggie subsection complete, no self-Completed flip.

---

## Out of scope / flagged follow-ups (do NOT do here)

- §3.5 `f_max` gloss "smallest-that-breaks" → "largest-that-holds" — Writer follow-up (don't edit Ch3).
- Snowman β ∈ {3,5} ε-observability sweep — separate RQ4 regime.
- Narwhal+Tusk §5 invariant — deferred with T38.1.
- `fork_rate` → `safety_violation_rate` column rename — separate schema task.
- T55 (algorithm × adversary × metric comparison tables + robustness ranking) consumes these artifacts.
