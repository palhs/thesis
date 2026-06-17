"""T52 — offline-validators (Family C liveness-under-absence) figures.

Renders the Chapter-4 offline-validators figures from
``results/adversary/offline_validators.csv`` to ``results/adversary/plots/``
as PNG (screen) + PDF (vector, thesis import). Two figure families, one
figure per validator-set size ``n`` (560 rows; 20 seeds per cell):

1. ``fig_success_vs_f`` — finalization success rate (mean of ``success_rate``
   over the 20 seeds per cell) vs offline fraction ``f``, one curve per
   protocol. Each protocol's boundary ``f*`` (lowest f with mean success
   below 1.0) is highlighted.
2. ``fig_throughput_vs_f`` — mean ``throughput_ratio`` (± 95% CI) vs ``f``,
   one curve per protocol, with the §4 ``y = 1 - f`` invariant reference.

Protocols use different f-grids: Snowman has no f=0.40 cell (its line stops
at 0.33); PBFT / Casper FFG run to 0.40. Stall cells carry
``throughput_ratio = NaN`` (no finality) and are dropped from the mean/CI.

Sibling of output.adversary_plots; keyed on byzantine_fraction (offline
fraction) rather than delay_mult, and not faceted on m (no m axis here).
Reuses output.plots STYLE + PROTO_ORDER and output.delay_analysis.mean_ci.

Re-run:
    PYTHONPATH=src python3 -m output.offline_plots
"""
from __future__ import annotations

import csv
import math
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # headless / deterministic.
import matplotlib.pyplot as plt

from output.delay_analysis import mean_ci
from output.plots import STYLE, PROTO_ORDER

CSV_PATH = "results/adversary/offline_validators.csv"
PLOT_DIR = "results/adversary/plots"

NS = (10, 25)


def _fnum(x: str) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _load(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _save(fig, plot_dir: str, fname: str) -> str:
    fig.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(plot_dir, f"{fname}.{ext}"),
                    dpi=150 if ext == "png" else None)
    plt.close(fig)
    return fname


def _grid(ax):
    ax.grid(True, which="both", linestyle=":", linewidth=0.6, alpha=0.7)


def _cell_means(rows, n, metric):
    """Map (protocol, f) -> MeanCI of ``metric`` over the seeds in the cell,
    restricted to validator-set size ``n``. NaN-valued cells (e.g. stalled
    throughput_ratio) are dropped by mean_ci; an all-NaN cell yields a
    MeanCI with n==0 and a NaN mean, which callers skip."""
    buckets = defaultdict(list)
    for r in rows:
        if _fnum(r["n"]) != float(n):
            continue
        buckets[(r["protocol"], round(_fnum(r["byzantine_fraction"]), 4))].append(
            _fnum(r[metric]))
    return {k: mean_ci(v) for k, v in buckets.items()}


def _f_grid(rows, proto, n):
    """Sorted offline fractions actually present for (proto, n)."""
    fs = {round(_fnum(r["byzantine_fraction"]), 4) for r in rows
          if r["protocol"] == proto and _fnum(r["n"]) == float(n)}
    return sorted(fs)


def fig_success_vs_f(rows, plot_dir: str) -> list[str]:
    """Finalization success rate vs offline fraction f, one curve per
    protocol, one figure per n. Each protocol's boundary f* (lowest f whose
    mean success drops below 1.0) is highlighted with an open marker."""
    names = []
    for n in NS:
        means = _cell_means(rows, n, "success_rate")
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
        for proto in PROTO_ORDER:
            grid = _f_grid(rows, proto, n)
            pts = [(f, means[(proto, f)]) for f in grid
                   if (proto, f) in means and not math.isnan(means[(proto, f)].mean)]
            if not pts:
                continue
            xs = [f for f, _ in pts]
            ys = [c.mean for _, c in pts]
            ax.plot(xs, ys, linewidth=1.6, markersize=6, **STYLE[proto])
            # Boundary f*: lowest f where mean success first drops below 1.0.
            below = [f for f, c in pts if c.mean < 1.0]
            if below:
                fstar = below[0]
                ystar = means[(proto, fstar)].mean
                ax.plot([fstar], [ystar], marker="o", markersize=12,
                        markerfacecolor="none", markeredgewidth=1.8,
                        markeredgecolor=STYLE[proto]["color"], linestyle="none")
                ax.annotate(f"$f^*\\!=\\!{fstar:.2f}$", (fstar, ystar),
                            textcoords="offset points", xytext=(6, 6),
                            fontsize=7, color=STYLE[proto]["color"])
        ax.set_xlabel("offline-validator fraction $f$")
        ax.set_ylabel("finalization success rate")
        ax.set_ylim(-0.05, 1.08)
        ax.set_title(f"Finalization success vs offline fraction "
                     f"($n = {n}$, mean over 20 seeds)")
        _grid(ax)
        ax.legend(frameon=False)
        names.append(_save(fig, plot_dir, f"success_vs_f_n{n}"))
    return names


def fig_throughput_vs_f(rows, plot_dir: str) -> list[str]:
    """Mean throughput_ratio (± 95% CI) vs offline fraction f, one curve per
    protocol, one figure per n. The y = 1 - f reference line marks the §4
    ``>= (1 - f) * baseline`` invariant. NaN (stalled) cells are excluded;
    an all-NaN cell at some f simply has no point there."""
    names = []
    for n in NS:
        means = _cell_means(rows, n, "throughput_ratio")
        fig, ax = plt.subplots(figsize=(6.2, 4.0))
        for proto in PROTO_ORDER:
            grid = _f_grid(rows, proto, n)
            pts = [(f, means[(proto, f)]) for f in grid
                   if (proto, f) in means and not math.isnan(means[(proto, f)].mean)]
            if not pts:
                continue
            xs = [f for f, _ in pts]
            ys = [c.mean for _, c in pts]
            errs = [c.ci_half for _, c in pts]
            ax.errorbar(xs, ys, yerr=errs, capsize=3, linewidth=1.6,
                        markersize=6, **STYLE[proto])
        # y = 1 - f invariant reference across the full swept f-range.
        all_f = sorted({round(_fnum(r["byzantine_fraction"]), 4) for r in rows
                        if _fnum(r["n"]) == float(n)})
        if all_f:
            ax.plot(all_f, [1.0 - f for f in all_f], color="grey",
                    linewidth=1.0, linestyle="--", zorder=1,
                    label="$y = 1 - f$ invariant")
        ax.set_xlabel("offline-validator fraction $f$")
        ax.set_ylabel("throughput ratio (vs f=0 control)")
        ax.set_ylim(-0.05, 1.08)
        ax.set_title(f"Throughput retention vs offline fraction "
                     f"($n = {n}$, mean ± 95% CI)")
        _grid(ax)
        ax.legend(frameon=False)
        names.append(_save(fig, plot_dir, f"throughput_vs_f_n{n}"))
    return names


def render_all(csv_path: str = CSV_PATH, plot_dir: str = PLOT_DIR) -> list[str]:
    rows = _load(csv_path)
    names = []
    names += fig_success_vs_f(rows, plot_dir)
    names += fig_throughput_vs_f(rows, plot_dir)
    return names


def main() -> None:
    names = render_all()
    print(f"wrote {len(names)} figures -> {PLOT_DIR}: {', '.join(names)}")


if __name__ == "__main__":
    main()
