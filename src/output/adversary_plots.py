"""T51 — delayed-voters (Family C delay-emission) dose-response figures.

Renders the Chapter-4 figures from results/adversary/delayed_voters.csv to
results/adversary/plots/ as PNG (screen) + PDF (vector, thesis import). The
headline is the dose-response of finality_delay_ratio (commit latency under
attack ÷ the f=0 control's latency) against the two swept adversary axes:
magnitude m and intensity f, faceted by committee size n.

Reuses output.plots STYLE + PROTO_ORDER and the output.delay_analysis
Student-t CI.

Re-run:
    PYTHONPATH=src python3 -m output.adversary_plots
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

CSV_PATH = "results/adversary/delayed_voters.csv"
PLOT_DIR = "results/adversary/plots"

NS = (10, 25)
F_ATTACK = (0.10, 0.20, 0.30)
M_VALUES = (2.0, 4.0, 6.0, 8.0, 10.0)


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


def _ratio_means(rows, key_fields):
    """Map key_fields-tuple -> MeanCI of finality_delay_ratio over seeds.

    Non-numeric fields (protocol) are kept as-is; numeric fields are converted
    via _fnum so the key is (str, float, float, float) regardless of how the
    CSV serialised the numbers.
    """
    _numeric = {"n", "byzantine_fraction", "delay_mult"}
    buckets = defaultdict(list)
    for r in rows:
        key = tuple(
            _fnum(r[k]) if k in _numeric else r[k]
            for k in key_fields
        )
        buckets[key].append(_fnum(r["finality_delay_ratio"]))
    return {k: mean_ci(v) for k, v in buckets.items()}


def fig_ratio_vs_m(rows, plot_dir: str) -> list[str]:
    """Dose-response: finality_delay_ratio vs magnitude m, one panel per
    fixed intensity f, faceted by n. One figure per n."""
    means = _ratio_means(
        [r for r in rows if _fnum(r["byzantine_fraction"]) != 0.0],
        ("protocol", "n", "byzantine_fraction", "delay_mult"))
    names = []
    for n in NS:
        fig, axes = plt.subplots(1, len(F_ATTACK),
                                 figsize=(4.0 * len(F_ATTACK), 4.0),
                                 sharey=True)
        for ax, f in zip(axes, F_ATTACK):
            for proto in PROTO_ORDER:
                pts = [(m, means[(proto, float(n), f, m)])
                       for m in M_VALUES
                       if (proto, float(n), f, m) in means]
                if not pts:
                    continue
                xs = [m for m, _ in pts]
                ys = [c.mean for _, c in pts]
                errs = [c.ci_half for _, c in pts]
                ax.errorbar(xs, ys, yerr=errs, capsize=3, linewidth=1.6,
                            markersize=6, **STYLE[proto])
            ax.set_title(f"$f = {f:.2f}$")
            ax.set_xlabel("delay magnitude $m$ (× round cadence)")
            ax.set_xticks(M_VALUES)
            ax.axhline(1.0, color="grey", linewidth=0.8, linestyle="--")
            _grid(ax)
        axes[0].set_ylabel("finality delay ratio (vs f=0 control)")
        axes[0].legend(frameon=False)
        fig.suptitle(f"Finality delay vs slow-voter magnitude "
                     f"($n = {n}$, mean ± 95% CI)")
        names.append(_save(fig, plot_dir, f"ratio_vs_m_n{n}"))
    return names


def fig_ratio_vs_f(rows, plot_dir: str) -> list[str]:
    """finality_delay_ratio vs intensity f, one panel per fixed magnitude m,
    faceted by n. One figure per n."""
    means = _ratio_means(
        [r for r in rows if _fnum(r["byzantine_fraction"]) != 0.0],
        ("protocol", "n", "delay_mult", "byzantine_fraction"))
    names = []
    for n in NS:
        fig, axes = plt.subplots(1, len(M_VALUES),
                                 figsize=(4.0 * len(M_VALUES), 4.0),
                                 sharey=True)
        for ax, m in zip(axes, M_VALUES):
            for proto in PROTO_ORDER:
                pts = [(f, means[(proto, float(n), m, f)])
                       for f in F_ATTACK
                       if (proto, float(n), m, f) in means]
                if not pts:
                    continue
                xs = [f for f, _ in pts]
                ys = [c.mean for _, c in pts]
                errs = [c.ci_half for _, c in pts]
                ax.errorbar(xs, ys, yerr=errs, capsize=3, linewidth=1.6,
                            markersize=6, **STYLE[proto])
            ax.set_title(f"$m = {m:.0f}$")
            ax.set_xlabel("slow-voter fraction $f$")
            ax.set_xticks(F_ATTACK)
            ax.axhline(1.0, color="grey", linewidth=0.8, linestyle="--")
            _grid(ax)
        axes[0].set_ylabel("finality delay ratio (vs f=0 control)")
        axes[0].legend(frameon=False)
        fig.suptitle(f"Finality delay vs slow-voter fraction "
                     f"($n = {n}$, mean ± 95% CI)")
        names.append(_save(fig, plot_dir, f"ratio_vs_f_n{n}"))
    return names


def render_all(csv_path: str = CSV_PATH, plot_dir: str = PLOT_DIR) -> list[str]:
    rows = _load(csv_path)
    names = []
    names += fig_ratio_vs_m(rows, plot_dir)
    names += fig_ratio_vs_f(rows, plot_dir)
    return names


def main() -> None:
    names = render_all()
    print(f"wrote {len(names)} figures -> {PLOT_DIR}: {', '.join(names)}")


if __name__ == "__main__":
    main()
