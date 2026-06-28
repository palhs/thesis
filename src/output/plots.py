"""Baseline comparison plots (T43; CI overlay T44).

Reads the per-trial scaling dataset ``results/baseline/baseline.csv`` and
renders the Chapter-4 baseline figures to ``results/baseline/plots/`` as
both PNG (screen) and PDF (vector, thesis import). Each figure plots one
metric against validator-set size ``n`` with one curve per protocol.

Cross-protocol latency uses ``commit_latency_ms`` only, per
[[concepts/output-format]] §13 Revisions [2026-06-05] (the PBFT-only
client-REPLY hop makes ``finality_latency_ms`` non-comparable).

Re-run:
    PYTHONPATH=src python3 -m output.plots            # with 95% CI bars (T44)
    PYTHONPATH=src python3 -m output.plots --no-ci    # mean curves only (T43)
"""

from __future__ import annotations

import argparse
import os

import matplotlib
matplotlib.use("Agg")  # headless / deterministic; no display backend.
import matplotlib.pyplot as plt

from output import analysis

CSV_PATH = "results/baseline/baseline.csv"
PLOT_DIR = "results/baseline/plots"

# Stable per-protocol style so every figure (and Chapter 4) reads the same.
STYLE = {
    "pbft":       dict(color="#1f77b4", marker="o", label="PBFT"),
    "casper-ffg": dict(color="#ff7f0e", marker="s", label="Casper FFG"),
    "snowman":    dict(color="#2ca02c", marker="^", label="Snowman"),
}
PROTO_ORDER = ("pbft", "casper-ffg", "snowman")


def _curve(ax, aggs, show_ci):
    """Draw one protocol's mean-vs-n curve with optional 95% CI error bars."""
    xs = [a.n for a in aggs]
    ys = [a.mean for a in aggs]
    proto = aggs[0].protocol
    st = STYLE[proto]
    if show_ci:
        errs = [a.ci_half for a in aggs]
        ax.errorbar(xs, ys, yerr=errs, capsize=3, linewidth=1.6,
                    markersize=6, **st)
    else:
        ax.plot(xs, ys, linewidth=1.6, markersize=6, **st)


def _draw_metric(ax, idx, metric, title, ylabel, show_ci, logy=False,
                 protocols=PROTO_ORDER, legend=True):
    """Draw one metric-vs-n axis (one curve per protocol).

    Extracted from :func:`_fig` so both the single-panel figure and the
    composed Chapter-4 panel (``output.panels``) render an identical axis.
    """
    for proto in protocols:
        if proto in idx[metric]:
            _curve(ax, idx[metric][proto], show_ci)
    ax.set_xlabel("validator-set size $n$")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if logy:
        ax.set_yscale("log")
    ax.set_xticks([4, 7, 10, 16, 25])
    ax.grid(True, which="both", linestyle=":", linewidth=0.6, alpha=0.7)
    if legend:
        ax.legend(frameon=False)


def _fig(idx, metric, title, ylabel, fname, show_ci, logy=False,
         protocols=PROTO_ORDER):
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    _draw_metric(ax, idx, metric, title, ylabel, show_ci, logy=logy,
                 protocols=protocols)
    fig.tight_layout()
    os.makedirs(PLOT_DIR, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(PLOT_DIR, f"{fname}.{ext}"),
                    dpi=150 if ext == "png" else None)
    plt.close(fig)
    return fname


def generate(show_ci: bool = True) -> list[str]:
    rows = analysis.load_rows(CSV_PATH)
    idx = analysis.by_metric(analysis.aggregate(rows))
    suffix = " (mean ± 95% CI)" if show_ci else ""
    made = []
    made.append(_fig(
        idx, "commit_latency_ms",
        "Commit latency vs. validator count" + suffix,
        "commit latency (ms)", "latency_vs_n", show_ci))
    made.append(_fig(
        idx, "goodput",
        "Committed throughput vs. validator count" + suffix,
        "goodput (committed tx/s)", "throughput_vs_n", show_ci))
    made.append(_fig(
        idx, "total_msgs_per_acu",
        "Message overhead vs. validator count" + suffix,
        "messages per committed unit (log)", "msgs_vs_n", show_ci, logy=True))
    made.append(_fig(
        idx, "success_rate",
        "Consensus success rate vs. validator count" + suffix,
        "success rate", "success_rate_vs_n", show_ci))
    # Companion plots: the tps decision-event rate (scales with n by
    # construction — see stats notes) and a zoomed goodput-with-CI panel
    # showing the one metric that carries real seed variance.
    made.append(_fig(
        idx, "tps",
        "Decision-event rate vs. validator count" + suffix,
        "tps (decided events/s)", "decision_rate_vs_n", show_ci))
    made.append(_fig(
        idx, "goodput",
        "Goodput with 95% CI (workload-driven variance)",
        "goodput (committed tx/s)", "goodput_ci_vs_n", True))
    return made


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--no-ci", dest="ci", action="store_false",
                   help="draw mean curves without 95%% CI error bars (T43)")
    args = p.parse_args()
    made = generate(show_ci=args.ci)
    print(f"wrote {len(made)} figures (PNG+PDF) to {PLOT_DIR}/:")
    for m in made:
        print(f"  - {m}.png / {m}.pdf")


if __name__ == "__main__":
    main()
