"""T48 — delay/loss resilience ranking math over the Family-B datasets.

Pure-stdlib reducers over the two committed delay CSVs:

- ``results/delay/delay_heavy.csv`` (T47): heavy-tail delay (Pareto, E≈3 s)
  loss-free control plus packet loss ``p_drop ∈ {0.05, 0.10, 0.20}``; carries
  the headline ``finalization_rate`` (= finalizations under loss ÷ loss-free
  control; 1.0 at the control by construction).
- ``results/delay/delay.csv`` (T46): moderate delay (uniform / exponential,
  E=300 ms), loss-free; used only as latency-growth context.

Ranking methodology (human-locked 2026-06-13, see
[[experiments/2026-06-13_delay-comparison]]):

- The arbitrary 95%-finalization breakpoint is **dropped** — no theoretical
  backing and it saturates (every cell is below 0.95 at the first loss step).
- **Primary key = AURC**: area under the ``finalization_rate``-vs-``p_drop``
  curve over [0, 0.20], plain trapezoid over the *actual* uneven spacing,
  normalized by the 0.20 width. No threshold. Computed per seed so its 95%
  Student-t CI is available for the tie test.
- **Tiebreak = survival-depth**: deepest ``p_drop`` whose mean
  ``finalization_rate`` is still > 0 (the principled liveness-collapse
  boundary, not a convention).
- ``n=10`` and ``n=25`` are reported **unpooled** (committee size flips the
  Snowman story). When the top-two AURC CIs overlap the rows share a rank
  (a statistical tie).

Cost columns (latency inflation, message overhead, view-changes) are carried
for display only — never folded into the rank. The 95% Student-t machinery is
reused from :mod:`output.analysis`.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from dataclasses import dataclass

from output.analysis import t_critical_975

HEAVY_CSV = "results/delay/delay_heavy.csv"
MODERATE_CSV = "results/delay/delay.csv"
RANKING_CSV = "results/delay/resilience_ranking.csv"

PROTO_ORDER = ("pbft", "casper-ffg", "snowman")
NS = (10, 25)
# Loss axis present in the heavy dataset, ascending. The control (p=0) anchors
# the left end of every retention curve at finalization_rate = 1.0.
P_DROPS = (0.0, 0.05, 0.10, 0.20)
# Moderate-delay timelines (latency-growth context only).
MODERATE_TIMELINES = ("delay-uniform", "delay-exponential")


def _fnum(x: str) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def load_rows(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- #
# Core statistics
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class MeanCI:
    """Across-seed mean with a 95% Student-t confidence interval."""

    mean: float
    ci_half: float
    ci_lo: float
    ci_hi: float
    n: int


def mean_ci(values: list[float]) -> MeanCI:
    """Mean + 95% Student-t CI over a finite-valued sample.

    NaN entries are dropped. A single value (or none) yields a zero-width CI.
    """
    vals = [v for v in values if not math.isnan(v)]
    k = len(vals)
    if k == 0:
        return MeanCI(float("nan"), float("nan"), float("nan"), float("nan"), 0)
    mean = sum(vals) / k
    if k > 1:
        std = math.sqrt(sum((v - mean) ** 2 for v in vals) / (k - 1))
        ci_half = t_critical_975(k - 1) * std / math.sqrt(k)
    else:
        ci_half = 0.0
    return MeanCI(mean, ci_half, mean - ci_half, mean + ci_half, k)


def aurc(curve: dict[float, float]) -> float:
    """Normalized area under a finalization_rate-vs-p_drop curve.

    Trapezoid over the ACTUAL ``P_DROPS`` spacing (so the wide 0.10→0.20 gap
    counts double, as it physically should), divided by the total width
    (``P_DROPS[-1] - P_DROPS[0]``) so the result is on [0, 1]. Missing or NaN
    points are read as 0.0 (a level the protocol did not finalize at).
    """
    fr = [0.0 if (p not in curve or math.isnan(curve[p])) else curve[p]
          for p in P_DROPS]
    area = 0.0
    for i in range(len(P_DROPS) - 1):
        area += (P_DROPS[i + 1] - P_DROPS[i]) * (fr[i] + fr[i + 1]) / 2.0
    width = P_DROPS[-1] - P_DROPS[0]
    return area / width if width else float("nan")


# --------------------------------------------------------------------------- #
# Heavy-dataset aggregation
# --------------------------------------------------------------------------- #

def _heavy_by_cell(rows: list[dict]) -> dict[tuple, list[dict]]:
    """Group heavy rows by ``(protocol, n, p_drop)``."""
    g: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        g[(r["protocol"], int(r["n"]), round(_fnum(r["p_drop"]), 4))].append(r)
    return g


def heavy_metric_means(rows: list[dict], metric: str) -> dict[tuple, MeanCI]:
    """``(protocol, n, p_drop) -> MeanCI`` for one heavy-dataset column."""
    out: dict[tuple, MeanCI] = {}
    for key, g in _heavy_by_cell(rows).items():
        out[key] = mean_ci([_fnum(r[metric]) for r in g])
    return out


def per_seed_aurc(rows: list[dict], protocol: str, n: int) -> list[float]:
    """One AURC value per seed for ``(protocol, n)``.

    Each seed contributes its own ``finalization_rate``-vs-``p_drop`` curve, so
    the returned sample feeds :func:`mean_ci` for the AURC confidence interval
    the tie test turns on.
    """
    by_seed: dict[str, dict[float, float]] = defaultdict(dict)
    for r in rows:
        if r["protocol"] != protocol or int(r["n"]) != n:
            continue
        p = round(_fnum(r["p_drop"]), 4)
        by_seed[r["seed"]][p] = _fnum(r["finalization_rate"])
    return [aurc(curve) for curve in by_seed.values()]


def survival_depth(fr_means: dict[tuple, MeanCI], protocol: str, n: int) -> float:
    """Deepest ``p_drop`` whose mean finalization_rate is still > 0."""
    alive = [p for p in P_DROPS
             if (protocol, n, p) in fr_means
             and fr_means[(protocol, n, p)].mean > 0.0]
    return max(alive) if alive else 0.0


def worst_finalizing_p(lat_means: dict[tuple, MeanCI], protocol: str,
                       n: int) -> float:
    """Deepest ``p_drop`` at which commit latency is still finite (finalizes)."""
    alive = [p for p in P_DROPS
             if (protocol, n, p) in lat_means
             and not math.isnan(lat_means[(protocol, n, p)].mean)]
    return max(alive) if alive else 0.0


# --------------------------------------------------------------------------- #
# Moderate-dataset context
# --------------------------------------------------------------------------- #

def moderate_metric_means(rows: list[dict], metric: str) -> dict[tuple, MeanCI]:
    """``(protocol, n, timeline) -> MeanCI`` for one moderate-dataset column."""
    g: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        g[(r["protocol"], int(r["n"]), r["network_phase_id"])].append(r)
    return {k: mean_ci([_fnum(r[metric]) for r in v]) for k, v in g.items()}


# --------------------------------------------------------------------------- #
# Ranking
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RankRow:
    rank: int
    tie: bool
    protocol: str
    n: int
    n_seeds: int
    aurc: float
    aurc_ci_lo: float
    aurc_ci_hi: float
    fr_at_0_05: float
    fr_at_0_10: float
    fr_at_0_20: float
    survival_depth_p: float
    worst_finalizing_p: float
    added_latency_ratio_worst: float
    msgs_per_acu_worst: float
    view_changes_at_0_20: float
    control_commit_latency_ms: float
    moderate_delay_latency_ms: float


def _overlap(a: MeanCI, b: MeanCI) -> bool:
    return not (a.ci_hi < b.ci_lo or b.ci_hi < a.ci_lo)


def ranking_for_n(heavy_rows: list[dict], moderate_rows: list[dict],
                  n: int) -> list[RankRow]:
    """Build the ranked rows for one committee size ``n``.

    Sort by (AURC desc, survival-depth desc). Adjacent rows whose AURC CIs
    overlap share a rank (statistical tie).
    """
    fr_means = heavy_metric_means(heavy_rows, "finalization_rate")
    lat_means = heavy_metric_means(heavy_rows, "commit_latency_ms")
    msg_means = heavy_metric_means(heavy_rows, "total_msgs_per_acu")
    vc_means = heavy_metric_means(heavy_rows, "view_change_count")
    mod_lat = moderate_metric_means(moderate_rows, "commit_latency_ms")

    recs = []
    for proto in PROTO_ORDER:
        seeds = per_seed_aurc(heavy_rows, proto, n)
        a_ci = mean_ci(seeds)
        sd = survival_depth(fr_means, proto, n)
        wp = worst_finalizing_p(lat_means, proto, n)
        ctrl = lat_means.get((proto, n, 0.0))
        worst = lat_means.get((proto, n, wp))
        ratio = (worst.mean / ctrl.mean
                 if ctrl and worst and ctrl.mean not in (0.0,) and
                 not math.isnan(ctrl.mean) and not math.isnan(worst.mean)
                 else float("nan"))

        def _m(d, p, default=float("nan")):
            c = d.get((proto, n, p))
            return c.mean if c else default

        recs.append({
            "ci": a_ci, "sd": sd, "wp": wp, "ratio": ratio,
            "row": dict(
                protocol=proto, n=n, n_seeds=a_ci.n,
                aurc=a_ci.mean, aurc_ci_lo=a_ci.ci_lo, aurc_ci_hi=a_ci.ci_hi,
                fr_at_0_05=_m(fr_means, 0.05), fr_at_0_10=_m(fr_means, 0.10),
                fr_at_0_20=_m(fr_means, 0.20),
                survival_depth_p=sd, worst_finalizing_p=wp,
                added_latency_ratio_worst=ratio,
                msgs_per_acu_worst=_m(msg_means, wp),
                view_changes_at_0_20=_m(vc_means, 0.20),
                control_commit_latency_ms=_m(lat_means, 0.0),
                moderate_delay_latency_ms=(
                    mod_lat[(proto, n, "delay-uniform")].mean
                    if (proto, n, "delay-uniform") in mod_lat else float("nan")),
            ),
        })

    # Sort by AURC desc, then survival-depth desc. NaN AURC sinks to the bottom.
    def _sortkey(r):
        a = r["ci"].mean
        return (-(a if not math.isnan(a) else -1.0), -r["sd"])

    recs.sort(key=_sortkey)

    out: list[RankRow] = []
    for i, r in enumerate(recs):
        if i == 0:
            rank, tie = 1, False
        elif _overlap(r["ci"], recs[i - 1]["ci"]):
            rank = out[-1].rank          # share the previous row's rank
            tie = True
            out[-1] = RankRow(**{**out[-1].__dict__, "tie": True})
        else:
            rank, tie = i + 1, False
        out.append(RankRow(rank=rank, tie=tie, **r["row"]))
    return out


_RANK_FIELDS = (
    "rank", "tie", "protocol", "n", "n_seeds",
    "aurc", "aurc_ci_lo", "aurc_ci_hi",
    "fr_at_0_05", "fr_at_0_10", "fr_at_0_20",
    "survival_depth_p", "worst_finalizing_p", "added_latency_ratio_worst",
    "msgs_per_acu_worst", "view_changes_at_0_20",
    "control_commit_latency_ms", "moderate_delay_latency_ms",
)


def write_ranking_csv(path: str = RANKING_CSV,
                      heavy_csv: str = HEAVY_CSV,
                      moderate_csv: str = MODERATE_CSV) -> str:
    """Write the two-block resilience ranking table (n=10 then n=25).

    Pure read → compute → write; deterministic (same inputs → identical bytes).
    """
    import os

    heavy = load_rows(heavy_csv)
    moderate = load_rows(moderate_csv)
    rows: list[RankRow] = []
    for n in NS:
        rows.extend(ranking_for_n(heavy, moderate, n))

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_RANK_FIELDS)
        for r in rows:
            w.writerow([getattr(r, fld) for fld in _RANK_FIELDS])
    return path


def main() -> None:
    out = write_ranking_csv()
    print(f"wrote {out}")
    for n in NS:
        print(f"\n=== n={n} (ranked by AURC, tiebreak survival-depth) ===")
        heavy = load_rows(HEAVY_CSV)
        moderate = load_rows(MODERATE_CSV)
        for r in ranking_for_n(heavy, moderate, n):
            tie = " (tie)" if r.tie else ""
            print(f"  #{r.rank}{tie} {r.protocol:11s} AURC={r.aurc:.3f} "
                  f"[{r.aurc_ci_lo:.3f},{r.aurc_ci_hi:.3f}] "
                  f"survival≤{r.survival_depth_p:.2f} "
                  f"lat×{r.added_latency_ratio_worst:.2f}")


if __name__ == "__main__":
    main()
