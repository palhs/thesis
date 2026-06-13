"""T48 — delay/loss resilience comparison figures.

Renders the Chapter-4 delay-comparison figures from the committed Family-B
datasets (``results/delay/delay_heavy.csv`` + ``results/delay/delay.csv``) to
``results/delay/plots/`` as PNG (screen) + PDF (vector, thesis import).

Descriptive only — the mechanism "why" is T49. Per the human-locked
methodology there is **no** 0.95-finalization reference line (the threshold is
arbitrary and saturates). Latency comparisons are anchored to each protocol's
own loss-free heavy-tail control, never to the differently-configured baseline
dataset.

Re-run:
    PYTHONPATH=src python3 -m output.delay_plots
"""

from __future__ import annotations

import math
import os

import matplotlib
matplotlib.use("Agg")  # headless / deterministic.
import matplotlib.pyplot as plt

from output import delay_analysis as da
from output.plots import STYLE, PROTO_ORDER

PLOT_DIR = "results/delay/plots"


def _save(fig, fname: str) -> str:
    fig.tight_layout()
    os.makedirs(PLOT_DIR, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(PLOT_DIR, f"{fname}.{ext}"),
                    dpi=150 if ext == "png" else None)
    plt.close(fig)
    return fname


def _grid(ax):
    ax.grid(True, which="both", linestyle=":", linewidth=0.6, alpha=0.7)


# --------------------------------------------------------------------------- #

def fig_finalization_degradation(heavy) -> str:
    """Headline: finalization_rate vs packet loss, faceted by n, 95% CI."""
    fr = da.heavy_metric_means(heavy, "finalization_rate")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        for proto in PROTO_ORDER:
            pts = [(p, fr[(proto, n, p)]) for p in da.P_DROPS
                   if (proto, n, p) in fr]
            xs = [p for p, _ in pts]
            ys = [c.mean for _, c in pts]
            errs = [c.ci_half for _, c in pts]
            ax.errorbar(xs, ys, yerr=errs, capsize=3, linewidth=1.6,
                        markersize=6, **STYLE[proto])
        ax.set_title(f"$n = {n}$")
        ax.set_xlabel("packet-loss probability $p_{drop}$")
        ax.set_xticks(da.P_DROPS)
        ax.set_ylim(-0.03, 1.05)
        _grid(ax)
    axes[0].set_ylabel("finalization rate (vs loss-free control)")
    axes[0].legend(frameon=False)
    fig.suptitle("Finalization rate under packet loss "
                 "(heavy-tail delay, mean ± 95% CI)")
    return _save(fig, "finalization_degradation")


def fig_latency_cliff(heavy) -> str:
    """Graceful-vs-cliff: commit latency vs loss; dead cells flagged."""
    lat = da.heavy_metric_means(heavy, "commit_latency_ms")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        ymax = 1.0
        for proto in PROTO_ORDER:
            alive = [(p, lat[(proto, n, p)].mean) for p in da.P_DROPS
                     if (proto, n, p) in lat
                     and not math.isnan(lat[(proto, n, p)].mean)]
            if alive:
                xs = [p for p, _ in alive]
                ys = [v for _, v in alive]
                ymax = max(ymax, max(ys))
                ax.plot(xs, ys, linewidth=1.6, markersize=6, **STYLE[proto])
                # Open "no finality" marker at the first dead level after death.
                last_p = xs[-1]
                nxt = [p for p in da.P_DROPS if p > last_p]
                if nxt:
                    ax.plot([nxt[0]], [ys[-1]], marker="x", markersize=9,
                            markeredgewidth=2, linestyle="none",
                            color=STYLE[proto]["color"])
        ax.set_title(f"$n = {n}$")
        ax.set_xlabel("packet-loss probability $p_{drop}$")
        ax.set_xticks(da.P_DROPS)
        ax.set_yscale("log")
        _grid(ax)
    axes[0].set_ylabel("commit latency (ms, log) — × = no finality")
    axes[0].legend(frameon=False)
    fig.suptitle("Commit-latency growth under packet loss "
                 "(solid = finalizing, × = liveness lost)")
    return _save(fig, "latency_cliff")


def fig_operator_pareto(heavy) -> str:
    """Tradeoff: retained finality vs added-latency cost, per loss level."""
    fr = da.heavy_metric_means(heavy, "finalization_rate")
    lat = da.heavy_metric_means(heavy, "commit_latency_ms")
    loss_levels = [p for p in da.P_DROPS if p > 0]

    # Position dead cells just right of the worst finite ratio.
    ratios = []
    for proto in PROTO_ORDER:
        for n in da.NS:
            c = lat.get((proto, n, 0.0))
            for p in loss_levels:
                w = lat.get((proto, n, p))
                if c and w and not math.isnan(c.mean) and not math.isnan(w.mean):
                    ratios.append(w.mean / c.mean)
    x_dead = (max(ratios) if ratios else 10.0) * 1.4

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        ctrl = {proto: lat.get((proto, n, 0.0)) for proto in PROTO_ORDER}
        for proto in PROTO_ORDER:
            st = STYLE[proto]
            for p in loss_levels:
                w = lat.get((proto, n, p))
                frc = fr.get((proto, n, p))
                yv = frc.mean if frc else 0.0
                c = ctrl[proto]
                if w and c and not math.isnan(w.mean) and not math.isnan(c.mean):
                    xv = w.mean / c.mean
                    ax.scatter([xv], [yv], marker=st["marker"], s=70,
                               color=st["color"], zorder=3)
                else:
                    ax.scatter([x_dead], [0.0], marker=st["marker"], s=70,
                               facecolors="none", edgecolors=st["color"],
                               zorder=3)
                ax.annotate(f"{int(p*100)}%",
                            (xv if (w and c and not math.isnan(w.mean)
                                    and not math.isnan(c.mean)) else x_dead,
                             yv if (frc and not math.isnan(yv)) else 0.0),
                            textcoords="offset points", xytext=(5, 4),
                            fontsize=7, color=st["color"])
        ax.axvline(x_dead * 0.92, linestyle="--", linewidth=0.8,
                   color="0.6")
        ax.text(x_dead, 0.02, "no finality", fontsize=7, color="0.4",
                ha="right")
        ax.set_xscale("log")
        ax.set_title(f"$n = {n}$")
        ax.set_xlabel("added-latency ratio (loss ÷ control)")
        ax.set_ylim(-0.05, 1.05)
        _grid(ax)
    axes[0].set_ylabel("finalization rate at that loss level")
    # Legend by protocol marker.
    handles = [plt.Line2D([], [], marker=STYLE[p]["marker"], linestyle="none",
                          color=STYLE[p]["color"], label=STYLE[p]["label"])
               for p in PROTO_ORDER]
    axes[1].legend(handles=handles, frameon=False)
    fig.suptitle("Operator tradeoff: finality retained vs latency paid "
                 "(upper-left is better)")
    return _save(fig, "operator_pareto")


def fig_cost_of_survival(heavy) -> str:
    """Cost: message overhead vs loss, with PBFT view-change churn."""
    msg = da.heavy_metric_means(heavy, "total_msgs_per_acu")
    vc = da.heavy_metric_means(heavy, "view_change_count")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        for proto in PROTO_ORDER:
            pts = [(p, msg[(proto, n, p)].mean) for p in da.P_DROPS
                   if (proto, n, p) in msg
                   and not math.isnan(msg[(proto, n, p)].mean)]
            if pts:
                ax.plot([p for p, _ in pts], [v for _, v in pts],
                        linewidth=1.6, markersize=6, **STYLE[proto])
        # Annotate PBFT view-change counts (the recovery work that buys survival).
        for p in da.P_DROPS:
            c = vc.get(("pbft", n, p))
            m = msg.get(("pbft", n, p))
            if c and m and not math.isnan(c.mean) and not math.isnan(m.mean) \
                    and c.mean > 0:
                ax.annotate(f"{c.mean:.0f} vc", (p, m.mean),
                            textcoords="offset points", xytext=(4, -10),
                            fontsize=7, color=STYLE["pbft"]["color"])
        ax.set_title(f"$n = {n}$")
        ax.set_xlabel("packet-loss probability $p_{drop}$")
        ax.set_xticks(da.P_DROPS)
        ax.set_yscale("log")
        _grid(ax)
    axes[0].set_ylabel("messages per committed unit (log)")
    axes[0].legend(frameon=False)
    fig.suptitle("Communication cost under packet loss "
                 "(PBFT view-change counts annotated)")
    return _save(fig, "cost_of_survival")


def fig_moderate_latency(moderate) -> str:
    """Context: latency growth under moderate delay (uniform vs exponential)."""
    lat = da.moderate_metric_means(moderate, "commit_latency_ms")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    width = 0.35
    for ax, n in zip(axes, da.NS):
        xs = range(len(PROTO_ORDER))
        for j, tl in enumerate(da.MODERATE_TIMELINES):
            ys = [lat[(proto, n, tl)].mean if (proto, n, tl) in lat else 0.0
                  for proto in PROTO_ORDER]
            errs = [lat[(proto, n, tl)].ci_half if (proto, n, tl) in lat else 0.0
                    for proto in PROTO_ORDER]
            offs = (j - 0.5) * width
            ax.bar([x + offs for x in xs], ys, width, yerr=errs, capsize=3,
                   label=tl.replace("delay-", ""))
        ax.set_title(f"$n = {n}$")
        ax.set_xticks(list(xs))
        ax.set_xticklabels([STYLE[p]["label"] for p in PROTO_ORDER])
        ax.set_yscale("log")
        _grid(ax)
    axes[0].set_ylabel("commit latency (ms, log)")
    axes[0].legend(frameon=False, title="moderate timeline (E=300 ms)")
    fig.suptitle("Latency under moderate delay (context for the loss sweep)")
    return _save(fig, "moderate_latency")


def generate() -> list[str]:
    heavy = da.load_rows(da.HEAVY_CSV)
    moderate = da.load_rows(da.MODERATE_CSV)
    return [
        fig_finalization_degradation(heavy),
        fig_latency_cliff(heavy),
        fig_operator_pareto(heavy),
        fig_cost_of_survival(heavy),
        fig_moderate_latency(moderate),
    ]


def main() -> None:
    made = generate()
    print(f"wrote {len(made)} figures (PNG+PDF) to {PLOT_DIR}/:")
    for m in made:
        print(f"  - {m}.png / {m}.pdf")


if __name__ == "__main__":
    main()
