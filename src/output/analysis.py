"""Aggregation helpers for the baseline scaling dataset (T43/T44).

Pure-stdlib reducers over the per-trial long-format CSV
(``results/baseline/baseline.csv``, one row per ``(protocol, scenario,
seed)``; see [[concepts/output-format]]). Two consumers share this module:

- ``plots.py`` (T43) draws per-protocol metric-vs-n curves;
- the T44 aggregation writes ``results/baseline/aggregated.csv`` with
  means and 95% confidence intervals.

No third-party dependency. The 95% CI uses Student's t (small-sample,
unknown variance) with a built-in two-sided 0.975 critical-value table;
every baseline configuration carries 20 seeds, so ``df = 19`` and
``t = 2.093`` is the working value. ``cv`` (coefficient of variation) is
reported so a reader can see at a glance which metrics carry real
seed-to-seed variation and which are deterministic at this baseline.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass

# Metrics aggregated for the comparison. Cross-protocol latency is
# commit_latency_ms only (NOT finality_latency_ms) per
# [[concepts/output-format]] §13 Revisions [2026-06-05]: the PBFT-only
# client-REPLY hop makes finality_latency_ms non-comparable across protocols.
METRICS = (
    "commit_latency_ms",
    "tps",
    "goodput",
    "consensus_msgs_per_acu",
    "total_msgs_per_acu",
    "bytes_per_acu",
    "success_rate",
    "fork_rate",
)

# Two-sided 0.975 Student-t critical values, df 1..30 then the normal limit.
_T_975 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
    8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080,
    22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048,
    29: 2.045, 30: 2.042,
}


def t_critical_975(df: int) -> float:
    """Two-sided 95% Student-t critical value for ``df`` degrees of freedom."""
    if df <= 0:
        return float("nan")
    if df in _T_975:
        return _T_975[df]
    return 1.960  # df > 30: normal approximation is within ~1%.


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


@dataclass(frozen=True)
class Agg:
    """One aggregated (protocol, n, metric) cell."""

    protocol: str
    run_id: str
    n: int
    metric: str
    n_runs: int
    mean: float
    std: float          # sample standard deviation (ddof=1)
    sem: float          # standard error of the mean
    ci_half: float      # half-width of the 95% CI
    ci_lo: float
    ci_hi: float
    cv: float           # coefficient of variation, percent


def _fnum(x: str) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def load_rows(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def aggregate(rows: list[dict], metrics=METRICS) -> list[Agg]:
    """Aggregate per ``run_id`` (each a distinct scenario at fixed n).

    Grouping is by ``run_id`` rather than ``(protocol, n)`` so the two
    Casper FFG variants at n=4 (uniform / nonuniform) stay distinct, each
    with its own 20-seed sample — never pooled, which would corrupt both
    the mean and the CI.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["protocol"], r["run_id"], int(r["n"]))].append(r)

    out: list[Agg] = []
    for (protocol, run_id, n), g in sorted(groups.items()):
        for m in metrics:
            vals = [_fnum(r[m]) for r in g]
            vals = [v for v in vals if not math.isnan(v)]
            if not vals:
                continue
            k = len(vals)
            mean = sum(vals) / k
            if k > 1:
                std = math.sqrt(sum((v - mean) ** 2 for v in vals) / (k - 1))
                sem = std / math.sqrt(k)
                ci_half = t_critical_975(k - 1) * sem
            else:
                std = sem = ci_half = 0.0
            cv = (std / mean * 100.0) if mean != 0 else 0.0
            out.append(Agg(
                protocol=protocol, run_id=run_id, n=n, metric=m, n_runs=k,
                mean=mean, std=std, sem=sem, ci_half=ci_half,
                ci_lo=mean - ci_half, ci_hi=mean + ci_half, cv=cv,
            ))
    return out


def by_metric(aggs: list[Agg]) -> dict[str, dict[str, list[Agg]]]:
    """Index aggregates as ``[metric][protocol] -> [Agg sorted by n]``.

    Casper FFG n=4 collapses to the ``uniform`` variant for the
    cross-protocol curves (one point per n), matching the comparison
    convention; the ``nonuniform`` variant is retained in the aggregated
    CSV but dropped from the per-protocol curve to avoid a double point.
    """
    idx: dict[str, dict[str, list[Agg]]] = defaultdict(lambda: defaultdict(list))
    for a in aggs:
        if a.run_id == "casper-ffg-n4-nonuniform":
            continue
        idx[a.metric][a.protocol].append(a)
    for metric in idx:
        for proto in idx[metric]:
            idx[metric][proto].sort(key=lambda a: a.n)
    return idx
