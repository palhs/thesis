"""Aggregated baseline CSV with 95% confidence intervals (T44).

Reduces the per-trial long-format dataset
(``results/baseline/baseline.csv``, one row per ``(protocol, scenario,
seed)``) to one row per scenario (``run_id``) carrying, for each metric,
the across-seed mean and the 95% CI bounds. Realises the
[[concepts/output-format]] §2 pipeline step (``→ results/baseline/
aggregated.csv ← means + 95% CIs``) and resolves the §11 register entry
``*_ci_lo / *_ci_hi for every metric`` from ``pending`` to ``live``.

§11 left the layout choice to T44. The chosen layout is a **sibling wide
file**, not in-place CI columns on the per-trial file: the per-trial file
stays the long-format substrate (T48/T51 sweeps append rows to it), while
this wide file is the plot/table feed. ``n_runs`` is the realised seed
count per scenario (20 here); ``success_rate`` is reported as the
across-seed mean, i.e. the frequency the §3 schema anticipates.

Re-run:
    PYTHONPATH=src python3 -m output.aggregate
Byte-identical on re-run (pure function of the committed CSV).
"""

from __future__ import annotations

import csv
import os

from output import analysis

SRC = "results/baseline/baseline.csv"
DST = "results/baseline/aggregated.csv"

# Identity columns then, per metric, mean / ci_lo / ci_hi / cv. ci_half is
# recoverable as (ci_hi - mean); cv is carried because it is the at-a-glance
# flag for which metrics carry real seed variance (see the T44 stats notes).
_ID = ("run_id", "protocol", "n", "n_runs")
_SUFFIXES = ("mean", "ci_lo", "ci_hi", "cv")


def _header() -> list[str]:
    cols = list(_ID)
    for m in analysis.METRICS:
        cols += [f"{m}_{s}" for s in _SUFFIXES]
    return cols


def build_rows(src: str = SRC) -> list[dict]:
    aggs = analysis.aggregate(analysis.load_rows(src))
    # Index by run_id; every scenario shares one n_runs across metrics.
    by_run: dict[str, dict] = {}
    for a in aggs:
        row = by_run.setdefault(a.run_id, {
            "run_id": a.run_id, "protocol": a.protocol,
            "n": a.n, "n_runs": a.n_runs,
        })
        row[f"{a.metric}_mean"] = round(a.mean, 6)
        row[f"{a.metric}_ci_lo"] = round(a.ci_lo, 6)
        row[f"{a.metric}_ci_hi"] = round(a.ci_hi, 6)
        row[f"{a.metric}_cv"] = round(a.cv, 4)
    # Total order matching the per-trial file: (protocol, n, run_id).
    return [by_run[k] for k in sorted(by_run,
            key=lambda k: (by_run[k]["protocol"], by_run[k]["n"], k))]


def write(src: str = SRC, dst: str = DST) -> int:
    rows = build_rows(src)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_header(), extrasaction="raise")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def main() -> None:
    n = write()
    print(f"wrote {n} aggregated rows to {DST}")


if __name__ == "__main__":
    main()
