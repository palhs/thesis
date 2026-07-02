"""T62 — Chapter-5 cross-family synthesis figure (RQ5 Pareto frontier).

Renders the Chapter-5 §5.4 synthesis figure to results/synthesis/plots/ as PNG
(screen) + PDF (vector, thesis import). One figure:

  - frontier_radar (Fig 5.1) overlaid radar of the three families evaluated
    (PBFT, Casper FFG, Snowman) over the eight cross-regime axes of Table 5.1,
    normalized by ordinal rank per axis (3 = best / outer ring, 1 = worst; ties
    shared). The three polygons overlap with none enclosing another, so the
    RQ5 no-dominance verdict reads directly off the image: each family spikes on
    a different axis cluster.

This is a synthesis figure, so — exactly like the §4.4 tradeoff matrix
(adversary_degradation_plots.fig_tradeoff_matrix, traceable to Table 4.2) — it
encodes the *synthesized verdict*, not a re-derivation from raw CSVs. The per-axis
ranks are the Table 5.1 ordering; two of the eight axes are interpretive verdicts
no single CSV column yields (equivocation-safety ranks Snowman first on a reported
analytical bound, not an empirical witness; accountable safety is a capability only
a slashing-based protocol offers). Each axis below carries the source wiki page its
rank is read from. Render layer only (smoke-tested, not unit-tested, per project
convention); reuses output.plots STYLE + PROTO_ORDER (3 protocols, no Narwhal+Tusk).

Re-run:
    PYTHONPATH=src python3 -m output.synthesis_plots
"""
from __future__ import annotations

import math
import os

import matplotlib
matplotlib.use("Agg")  # headless / deterministic.
import matplotlib.pyplot as plt

from output.plots import STYLE, PROTO_ORDER

PLOT_DIR = "results/synthesis/plots"

# The eight cross-regime axes of Table 5.1. Two-line rim labels for the radar.
# Source pages per axis are given against the rank table below.
AXES = (
    "Baseline\nlatency",
    "Comm.\noverhead",
    "Delay\nslowdown",
    "Loss\nresilience",
    "Liveness\n(slow voters)",
    "Liveness\n(silence)",
    "Equivocation\nsafety",
    "Accountable\nsafety",
)

# Ordinal rank per axis (3 = best / outer, 1 = worst; ties shared). This IS the
# synthesized Table 5.1 verdict — the "Best" column read onto a 3/2/1 scale — not
# a re-derivation from raw data. Per-axis provenance (index -> Table 5.1 row):
#   0 baseline latency      PBFT ~1s ~= Snowman ~1s > Casper FFG ~5s
#                           [[experiments/2026-06-03_scaling-baseline]]
#   1 comm. overhead        Casper FFG ~1.15n < PBFT ~2n < Snowman ~2Kbeta (~14x)
#                           [[experiments/2026-06-08_baseline-cis]]
#   2 delay slowdown        Casper FFG x1.3 (slot-bound, least) < PBFT x1.9
#                           < Snowman x12-13 (relative finality slowdown vs
#                           baseline; least slowdown = best)
#                           [[experiments/2026-06-13_delay-analysis]]
#   3 loss resilience       PBFT first (alive @20%) > Snowman (cliffs by 10%)
#                           > Casper FFG last
#                           [[experiments/2026-06-13_delay-comparison]]
#   4 liveness, slow voters PBFT immune (1.0x) > Snowman survives (x62) >
#                           Casper FFG success dips (->0.60)
#                           [[experiments/2026-06-19_adversary-comparison]]
#   5 liveness, silence     PBFT ~= Casper FFG (to phi=0.33) > Snowman
#                           (cliff phi=0.20 @n=10)
#                           [[experiments/2026-06-17_offline-validators]]
#   6 equivocation safety   Snowman (no fork surface, eps~5e-15) > Casper FFG
#                           (accountable, no fork) > PBFT (deterministic fork)
#                           [[experiments/2026-06-19_adversarial-degradation]]
#   7 accountable safety    Casper FFG (slashable >=1/3) > PBFT (none) ~=
#                           Snowman (not applicable; probabilistic)
#                           [[experiments/2026-06-19_adversarial-degradation]]
RANK = {
    #                bal ovh dly los lvD lvS eqS acS
    "pbft":         (3,  2,  2,  3,  3,  3,  1,  1),
    "casper-ffg":   (1,  3,  3,  1,  1,  3,  2,  3),
    "snowman":      (3,  1,  1,  2,  2,  1,  3,  1),
}


def _save(fig, plot_dir, fname):
    fig.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(plot_dir, f"{fname}.{ext}"),
                    dpi=150 if ext == "png" else None)
    plt.close(fig)
    return fname


def _angles(n):
    return [i / n * 2 * math.pi for i in range(n)]


def fig_frontier_radar(plot_dir):
    """Overlaid radar over the eight Table 5.1 axes, one polygon per family,
    ordinal rank per axis (outer = better). No data is read (the ranks are the
    synthesized verdict); see the module docstring for per-axis provenance."""
    n = len(AXES)
    base = _angles(n)
    closed = base + [base[0]]
    fig, ax = plt.subplots(figsize=(7.6, 7.6), subplot_kw=dict(polar=True))
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(base)
    ax.set_xticklabels(AXES, fontsize=9)
    ax.set_ylim(0, 3)
    ax.set_yticks([1, 2, 3])
    ax.set_yticklabels(["worst", "mid", "best"], fontsize=7, color="0.45")
    ax.set_rlabel_position(180.0 / n)
    for proto in PROTO_ORDER:
        vals = list(RANK[proto])
        vals = vals + [vals[0]]
        ax.plot(closed, vals, linewidth=2.0, color=STYLE[proto]["color"],
                label=STYLE[proto]["label"])
        ax.fill(closed, vals, color=STYLE[proto]["color"], alpha=0.12)
    ax.set_title("Cross-family performance–security frontier\n"
                 "(ordinal rank per axis; outer = better)", fontsize=12, pad=24)
    ax.legend(loc="upper left", bbox_to_anchor=(1.22, 1.12), fontsize=9,
              frameon=True, borderpad=0.8)
    return _save(fig, plot_dir, "frontier_radar")


def render_all(plot_dir: str = PLOT_DIR):
    return [fig_frontier_radar(plot_dir)]


def main() -> None:
    names = render_all()
    print(f"wrote {len(names)} figures (PNG+PDF) -> {PLOT_DIR}: {', '.join(names)}")


if __name__ == "__main__":
    main()
