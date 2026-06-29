"""Chapter-4 combined multi-panel figures (page-cut composer).

Composes the existing single-panel Chapter-4 figures into five combined
multi-panel PDFs (+ PNGs) so the thesis spends fewer pages on figures without
re-deriving any plotting logic. Every panel is drawn by the SAME ``_draw_*``
helper the original single-panel figure uses, so the combined panels and the
standalone figures cannot drift:

  - baseline metric axes        -> output.plots._draw_metric
  - delay/loss resilience axes  -> output.delay_plots._draw_finalization /
                                   _draw_resilience_ranking / _draw_latency_cliff /
                                   _draw_cost_of_survival / _draw_operator_pareto
  - adversary axes              -> output.adversary_degradation_plots._liveness_axis /
                                   _draw_delay_latency / _draw_offline_survival_box /
                                   _draw_safety_cliff

No data is read or written beyond the committed CSVs the originals already use;
no editorializing text in titles (chapter captions carry interpretation, per
draft-style.md).

Outputs (each as .pdf vector + .png @150dpi):
  results/baseline/plots/baseline_panel
  results/delay/plots/loss_resilience_panel
  results/delay/plots/degradation_mechanism_panel
  results/adversary/plots/liveness_delay_offline_panel
  results/adversary/plots/equivocation_panel

Re-run:
    PYTHONPATH=src python3 -m output.panels
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")  # headless / deterministic.
import matplotlib.pyplot as plt

from output import analysis
from output import delay_analysis as da
from output import delay_plots as dp
from output import adversary_analysis as aa
from output import adversary_degradation_plots as ap
from output.plots import STYLE, PROTO_ORDER
import output.plots as bp


def _row_label(ax, letter: str) -> None:
    """Bold sub-panel row label (e.g. "(a)") at the top-left of a row's left
    panel, in axes coords so it tracks the panel and not the data. Lets the
    chapter cross-reference rows of the multi-row combined figures."""
    ax.text(0.012, 0.985, f"({letter})", transform=ax.transAxes,
            fontsize=12, fontweight="bold", va="top", ha="left", zorder=5)


def _save(fig, plot_dir: str, fname: str) -> str:
    """Dual PNG@150dpi + PDF(vector) save, mirroring the per-module helpers."""
    fig.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(plot_dir, f"{fname}.{ext}"),
                    dpi=150 if ext == "png" else None)
    plt.close(fig)
    return os.path.join(plot_dir, fname)


# --------------------------------------------------------------------------- #
# Panel 1 — baseline metric-vs-n, 2x2
# --------------------------------------------------------------------------- #

def baseline_panel(plot_dir: str = bp.PLOT_DIR) -> str:
    """1x2 baseline panel: (a) goodput w/ 95% CI, (b) commit latency. x-axis is
    validator-set size n; Snowman's curve starts at n=7 (absent at n=4 by
    design). The decision-event (tps) panel and the redundant plain-goodput
    panel were retired with the tps metric: goodput is the sole cross-protocol
    throughput axis, and panel (a) already carries it with CI bars."""
    rows = analysis.load_rows(bp.CSV_PATH)
    idx = analysis.by_metric(analysis.aggregate(rows))

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    ax_a, ax_b = axes

    bp._draw_metric(ax_a, idx, "goodput",
                    "(a) goodput (mean $\\pm$ 95% CI)",
                    "goodput (committed tx/s)", show_ci=True, legend=True)
    bp._draw_metric(ax_b, idx, "commit_latency_ms",
                    "(b) commit latency", "commit latency (ms)",
                    show_ci=False, legend=False)
    return _save(fig, plot_dir, "baseline_panel")


# --------------------------------------------------------------------------- #
# Panel 2 — loss-resilience, 2x2 (rows = metric, cols = n)
# --------------------------------------------------------------------------- #

def loss_resilience_panel(plot_dir: str = dp.PLOT_DIR) -> str:
    """2x2: row 1 = finalization rate vs packet loss (95% CI); row 2 = AURC
    resilience ranking (95% CI, p* survival-depth, tie bracket). Columns are
    n in {10, 25}."""
    heavy = da.load_rows(da.HEAVY_CSV)
    moderate = da.load_rows(da.MODERATE_CSV)
    fr = da.heavy_metric_means(heavy, "finalization_rate")

    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.4), sharex="row")
    for col, n in enumerate(da.NS):
        dp._draw_finalization(axes[0][col], fr, n)
        axes[0][col].set_title(f"$n = {n}$")
        ranked = {r.protocol: r for r in da.ranking_for_n(heavy, moderate, n)}
        dp._draw_resilience_ranking(axes[1][col], ranked)
    axes[0][0].set_ylabel("finalization rate (vs control)")
    axes[1][0].set_ylabel("AURC")
    _row_label(axes[0][0], "a")
    _row_label(axes[1][0], "b")
    axes[0][1].legend(frameon=False)
    return _save(fig, plot_dir, "loss_resilience_panel")


# --------------------------------------------------------------------------- #
# Panel 3 — degradation mechanism, 3x2 (rows = metric, cols = n)
# --------------------------------------------------------------------------- #

def degradation_mechanism_panel(plot_dir: str = dp.PLOT_DIR) -> str:
    """3x2: row 1 = commit-latency cliff (log y, × no-finality); row 2 = cost of
    survival (log y, PBFT view-change counts); row 3 = operator Pareto
    (finality retained vs added-latency ratio, log x, dead cells). Cols n in
    {10, 25}."""
    heavy = da.load_rows(da.HEAVY_CSV)
    lat = da.heavy_metric_means(heavy, "commit_latency_ms")
    msg = da.heavy_metric_means(heavy, "total_msgs_per_acu")
    vc = da.heavy_metric_means(heavy, "view_change_count")
    fr = da.heavy_metric_means(heavy, "finalization_rate")
    x_dead = dp._pareto_x_dead(lat)

    fig, axes = plt.subplots(3, 2, figsize=(10.5, 12.0))
    for col, n in enumerate(da.NS):
        dp._draw_latency_cliff(axes[0][col], lat, n)
        axes[0][col].set_title(f"$n = {n}$")
        dp._draw_cost_of_survival(axes[1][col], msg, vc, n)
        dp._draw_operator_pareto(axes[2][col], fr, lat, n, x_dead)
    axes[0][0].set_ylabel("commit latency (ms, log) — × = no finality")
    axes[1][0].set_ylabel("messages per committed unit (log)")
    axes[2][0].set_ylabel("finalization rate at that loss level")
    _row_label(axes[0][0], "a")
    _row_label(axes[1][0], "b")
    _row_label(axes[2][0], "c")
    axes[0][0].legend(frameon=False)
    return _save(fig, plot_dir, "degradation_mechanism_panel")


# --------------------------------------------------------------------------- #
# Panel 4 — adversary liveness/delay/offline, 3x2 (cols = n)
# --------------------------------------------------------------------------- #

def liveness_delay_offline_panel(plot_dir: str = ap.PLOT_DIR) -> str:
    """3x2 (cols = n in {10, 25}): row 1 = delayed-voting finalization success
    rate; row 2 = delayed-voting time-to-finality ratio (log y, Snowman ×peak);
    row 3 = silent non-participation success rate with phi* survival boxes and
    the Snowman 'alive but starved' annotation."""
    rows = aa.load_adversary_rows(aa.ADVERSARY_DIR)
    fig, axes = plt.subplots(3, 2, figsize=(10.5, 12.0))
    for col, n in enumerate(ap.NS):
        ap._liveness_axis(axes[0][col], rows, "delay", n)
        axes[0][col].set_title(f"$n = {n}$")
        ap._draw_delay_latency(axes[1][col], rows, n)
        survival = ap._liveness_axis(axes[2][col], rows, "offline", n)
        ap._draw_offline_survival_box(axes[2][col], rows, survival, n)
        axes[2][col].set_xlabel("$\\varphi$")
    axes[0][0].set_ylabel("finalization success rate")
    axes[1][0].set_ylabel("time-to-finality ratio (vs $\\varphi = 0$)")
    axes[2][0].set_ylabel("finalization success rate")
    _row_label(axes[0][0], "a")
    _row_label(axes[1][0], "b")
    _row_label(axes[2][0], "c")
    axes[0][1].legend(frameon=False)
    return _save(fig, plot_dir, "liveness_delay_offline_panel")


# --------------------------------------------------------------------------- #
# Panel 5 — equivocation, 2x2 (cols = n)
# --------------------------------------------------------------------------- #

def equivocation_panel(plot_dir: str = ap.PLOT_DIR) -> str:
    """2x2 (cols = n in {10, 25}): row 1 = equivocation finalization success
    rate per protocol; row 2 = cross-protocol safety-violation rate (steps-post)
    with the PBFT conflicting-instances annotation."""
    rows = aa.load_adversary_rows(aa.ADVERSARY_DIR)
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 8.4))
    for col, n in enumerate(ap.NS):
        ap._liveness_axis(axes[0][col], rows, "equivocate", n)
        axes[0][col].set_title(f"$n = {n}$")
        dp_ax = axes[1][col]
        ap._draw_safety_cliff(dp_ax, rows, n)
        dp_ax.set_xlabel("equivocator fraction $\\varphi$")
        axes[0][col].set_xlabel("equivocator fraction $\\varphi$")
    axes[0][0].set_ylabel("finalization success rate")
    axes[1][0].set_ylabel("safety-violation rate")
    _row_label(axes[0][0], "a")
    _row_label(axes[1][0], "b")
    axes[0][1].legend(frameon=False)
    return _save(fig, plot_dir, "equivocation_panel")


def generate() -> list[str]:
    return [
        baseline_panel(),
        loss_resilience_panel(),
        degradation_mechanism_panel(),
        liveness_delay_offline_panel(),
        equivocation_panel(),
    ]


def main() -> None:
    made = generate()
    print(f"wrote {len(made)} combined panels (PNG+PDF):")
    for m in made:
        print(f"  - {m}.png / {m}.pdf")


if __name__ == "__main__":
    main()
