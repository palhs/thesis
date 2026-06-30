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

def _draw_finalization(ax, fr, n):
    """Per-axis: finalization_rate vs loss with 95% CI, one curve per protocol.

    Extracted from :func:`fig_finalization_degradation` so the composed
    Chapter-4 panel (``output.panels``) reuses the identical axis body.
    ``fr`` is ``da.heavy_metric_means(heavy, "finalization_rate")``.
    """
    for proto in PROTO_ORDER:
        pts = [(p, fr[(proto, n, p)]) for p in da.P_DROPS
               if (proto, n, p) in fr]
        xs = [p for p, _ in pts]
        ys = [c.mean for _, c in pts]
        errs = [c.ci_half for _, c in pts]
        ax.errorbar(xs, ys, yerr=errs, capsize=3, linewidth=1.6,
                    markersize=6, **STYLE[proto])
    ax.set_xlabel("packet-loss probability $p_{drop}$")
    ax.set_xticks(da.P_DROPS)
    ax.set_ylim(-0.03, 1.05)
    _grid(ax)


def fig_finalization_degradation(heavy) -> str:
    """Headline: finalization_rate vs packet loss, faceted by n, 95% CI."""
    fr = da.heavy_metric_means(heavy, "finalization_rate")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        _draw_finalization(ax, fr, n)
        ax.set_title(f"$n = {n}$")
    axes[0].set_ylabel("finalization rate (vs loss-free control)")
    axes[0].legend(frameon=False)
    fig.suptitle("Finalization rate under packet loss "
                 "(heavy-tail delay, mean ± 95% CI)")
    return _save(fig, "finalization_degradation")


def _draw_latency_cliff(ax, lat, n):
    """Per-axis: commit-latency vs loss (log y) with the × no-finality marker.

    Extracted from :func:`fig_latency_cliff` for reuse by ``output.panels``.
    ``lat`` is ``da.heavy_metric_means(heavy, "commit_latency_ms")``.
    """
    for proto in PROTO_ORDER:
        alive = [(p, lat[(proto, n, p)].mean) for p in da.P_DROPS
                 if (proto, n, p) in lat
                 and not math.isnan(lat[(proto, n, p)].mean)]
        if alive:
            xs = [p for p, _ in alive]
            ys = [v for _, v in alive]
            ax.plot(xs, ys, linewidth=1.6, markersize=6, **STYLE[proto])
            # Open "no finality" marker at the first dead level after death.
            last_p = xs[-1]
            nxt = [p for p in da.P_DROPS if p > last_p]
            if nxt:
                ax.plot([nxt[0]], [ys[-1]], marker="x", markersize=9,
                        markeredgewidth=2, linestyle="none",
                        color=STYLE[proto]["color"])
    ax.set_xlabel("packet-loss probability $p_{drop}$")
    ax.set_xticks(da.P_DROPS)
    ax.set_yscale("log")
    _grid(ax)


def fig_latency_cliff(heavy) -> str:
    """Graceful-vs-cliff: commit latency vs loss; dead cells flagged."""
    lat = da.heavy_metric_means(heavy, "commit_latency_ms")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        _draw_latency_cliff(ax, lat, n)
        ax.set_title(f"$n = {n}$")
    axes[0].set_ylabel("commit latency (ms, log) — × = no finality")
    axes[0].legend(frameon=False)
    fig.suptitle("Commit-latency growth under packet loss "
                 "(solid = finalizing, × = liveness lost)")
    return _save(fig, "latency_cliff")


def _pareto_x_dead(lat):
    """The x position used for dead (no-finality) cells: just right of the
    worst finite added-latency ratio across every (proto, n, loss). Shared by
    :func:`fig_operator_pareto` and the composed panel so dead cells line up."""
    ratios = []
    for proto in PROTO_ORDER:
        for n in da.NS:
            c = lat.get((proto, n, 0.0))
            for p in [p for p in da.P_DROPS if p > 0]:
                w = lat.get((proto, n, p))
                if c and w and not math.isnan(c.mean) and not math.isnan(w.mean):
                    ratios.append(w.mean / c.mean)
    return (max(ratios) if ratios else 10.0) * 1.4


def _draw_operator_pareto(ax, fr, lat, n, x_dead):
    """Per-axis: finality-retained vs added-latency-ratio scatter (log x), with
    dead cells parked on the 'no finality' band at ``x_dead``.

    Extracted from :func:`fig_operator_pareto` for reuse by ``output.panels``.
    """
    loss_levels = [p for p in da.P_DROPS if p > 0]
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
    ax.axvline(x_dead * 0.92, linestyle="--", linewidth=0.8, color="0.6")
    ax.text(x_dead, 0.02, "no finality", fontsize=7, color="0.4", ha="right")
    ax.set_xscale("log")
    ax.set_xlabel("added-latency ratio (loss ÷ control)")
    ax.set_ylim(-0.05, 1.05)
    _grid(ax)


def fig_operator_pareto(heavy) -> str:
    """Tradeoff: retained finality vs added-latency cost, per loss level."""
    fr = da.heavy_metric_means(heavy, "finalization_rate")
    lat = da.heavy_metric_means(heavy, "commit_latency_ms")
    x_dead = _pareto_x_dead(lat)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        _draw_operator_pareto(ax, fr, lat, n, x_dead)
        ax.set_title(f"$n = {n}$")
    axes[0].set_ylabel("finalization rate at that loss level")
    # Legend by protocol marker.
    handles = [plt.Line2D([], [], marker=STYLE[p]["marker"], linestyle="none",
                          color=STYLE[p]["color"], label=STYLE[p]["label"])
               for p in PROTO_ORDER]
    axes[1].legend(handles=handles, frameon=False)
    fig.suptitle("Operator tradeoff: finality retained vs latency paid "
                 "(upper-left is better)")
    return _save(fig, "operator_pareto")


def _draw_cost_of_survival(ax, msg, vc, n):
    """Per-axis: message overhead vs loss (log y) with PBFT view-change counts
    annotated. Extracted from :func:`fig_cost_of_survival` for ``output.panels``.
    ``msg`` / ``vc`` are the total_msgs_per_acu / view_change_count mean maps."""
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
    ax.set_xlabel("packet-loss probability $p_{drop}$")
    ax.set_xticks(da.P_DROPS)
    ax.set_yscale("log")
    _grid(ax)


def fig_cost_of_survival(heavy) -> str:
    """Cost: message overhead vs loss, with PBFT view-change churn."""
    msg = da.heavy_metric_means(heavy, "total_msgs_per_acu")
    vc = da.heavy_metric_means(heavy, "view_change_count")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        _draw_cost_of_survival(ax, msg, vc, n)
        ax.set_title(f"$n = {n}$")
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
    axes[0].legend(loc="upper left", frameon=True, framealpha=0.9,
                   title="moderate timeline (E=300 ms)")
    fig.suptitle("Latency under moderate delay (context for the loss sweep)")
    return _save(fig, "moderate_latency")


def _draw_resilience_ranking(ax, ranked):
    """Per-axis: AURC bars with 95% CI, p* survival-depth annotations, and the
    tie bracket over statistically tied pairs. ``ranked`` is
    ``{protocol: RankRow}`` from ``da.ranking_for_n``. Extracted from
    :func:`fig_resilience_ranking` for reuse by ``output.panels``."""
    xs = range(len(PROTO_ORDER))
    for x, proto in zip(xs, PROTO_ORDER):
        r = ranked[proto]
        ci_half = (r.aurc_ci_hi - r.aurc_ci_lo) / 2.0
        ax.bar([x], [r.aurc], 0.62, yerr=[ci_half], capsize=4,
               color=STYLE[proto]["color"], alpha=0.85,
               edgecolor="0.3", linewidth=0.6)
        ax.annotate(f"$p^*\\!=\\!{r.survival_depth_p:.2f}$",
                    (x, r.aurc_ci_hi), textcoords="offset points",
                    xytext=(0, 4), ha="center", fontsize=7,
                    color=STYLE[proto]["color"])
    # Bracket any statistically tied pair (overlapping CIs share a rank), so
    # the n=25 PBFT-Snowman tie is visible in the figure, not only in prose.
    for i in range(len(PROTO_ORDER)):
        for j in range(i + 1, len(PROTO_ORDER)):
            ri, rj = ranked[PROTO_ORDER[i]], ranked[PROTO_ORDER[j]]
            if ri.aurc_ci_lo <= rj.aurc_ci_hi and rj.aurc_ci_lo <= ri.aurc_ci_hi:
                y = max(ri.aurc_ci_hi, rj.aurc_ci_hi) + 0.035
                ax.plot([i, i, j, j], [y - 0.012, y, y, y - 0.012],
                        color="0.35", linewidth=1.0)
                ax.text((i + j) / 2.0, y + 0.004, "tie", ha="center",
                        va="bottom", fontsize=7, color="0.35")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([STYLE[p]["label"] for p in PROTO_ORDER])
    ax.set_ylim(0, 0.45)
    _grid(ax)


def fig_resilience_ranking(heavy, moderate) -> str:
    """The ranking itself: AURC with 95% CI + survival-depth, faceted by n.

    Bars are AURC (normalized area under the finalization-rate-vs-loss curve;
    higher = more finality retained across the loss sweep). Error bars are the
    95% Student-t CI over seeds — the interval the ``n=25`` statistical tie
    turns on (overlapping CIs share a rank, ``delay_analysis.ranking_for_n``).
    Each bar is annotated with its survival-depth ``p*`` (deepest loss with mean
    finality > 0). This is the only figure that shows the AURC scalar with its
    CI, so the reader can *see* the tie (overlap) and the survival-depth
    tiebreak in one view. Reads the same ``ranking_for_n`` the ranking CSV is
    written from, so the figure and the table cannot drift.
    """
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, da.NS):
        ranked = {r.protocol: r for r in da.ranking_for_n(heavy, moderate, n)}
        _draw_resilience_ranking(ax, ranked)
        ax.set_title(f"$n = {n}$")
    axes[0].set_ylabel("AURC (area under retention curve)")
    fig.suptitle("Loss-resilience ranking: AURC with 95% CI "
                 "($p^*$ = survival depth; overlapping CIs share a rank)")
    return _save(fig, "resilience_ranking")


def generate() -> list[str]:
    heavy = da.load_rows(da.HEAVY_CSV)
    moderate = da.load_rows(da.MODERATE_CSV)
    return [
        fig_finalization_degradation(heavy),
        fig_latency_cliff(heavy),
        fig_operator_pareto(heavy),
        fig_cost_of_survival(heavy),
        fig_moderate_latency(moderate),
        fig_resilience_ranking(heavy, moderate),
    ]


def main() -> None:
    made = generate()
    print(f"wrote {len(made)} figures (PNG+PDF) to {PLOT_DIR}/:")
    for m in made:
        print(f"  - {m}.png / {m}.pdf")


if __name__ == "__main__":
    main()
