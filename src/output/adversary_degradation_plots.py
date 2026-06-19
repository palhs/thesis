"""T54 — adversarial liveness & safety degradation figures.

Renders the Chapter-4 adversarial figures from the three Family-C CSVs (via
output.adversary_analysis) to results/adversary/plots/ as PNG (screen) + PDF
(vector, thesis import). Liveness (mean success_rate + Wilson band) is shown per
adversary family; the four per-protocol safety invariants come from the
equivocate family. Sibling of output.adversary_plots (T51) / output.offline_plots
(T52); reuses output.plots STYLE + PROTO_ORDER (3 protocols, no Narwhal+Tusk).
Render layer only (smoke-tested, not unit-tested, per project convention).

Re-run:
    PYTHONPATH=src python3 -m output.adversary_degradation_plots
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")  # headless / deterministic.
import matplotlib.pyplot as plt

from output import adversary_analysis as aa
from output.plots import STYLE, PROTO_ORDER

PLOT_DIR = "results/adversary/plots"
NS = (10, 25)
THIRD = 1.0 / 3.0
FAMILY_LABEL = {"delay": "delayed voters", "offline": "offline validators",
                "equivocate": "equivocating nodes"}


def _save(fig, plot_dir, fname):
    fig.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(plot_dir, f"{fname}.{ext}"),
                    dpi=150 if ext == "png" else None)
    plt.close(fig)
    return fname


def _grid(ax):
    ax.grid(True, which="both", linestyle=":", linewidth=0.6, alpha=0.7)


def fig_liveness_vs_phi(rows, family, plot_dir):
    """mean(success_rate) + Wilson band vs phi, faceted 1x2 by n, per protocol."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, NS):
        for proto in PROTO_ORDER:
            cells = aa.liveness_rate(rows, family, proto, n)
            grid = sorted(cells)
            if not grid:
                continue
            ys = [cells[p].mean for p in grid]
            # Wilson arms; clamp at 0 — a saturated cell (mean==1.0, k==n) has
            # hi==1.0 so the upper arm is exactly 0 but floats to -0.0/tiny-neg,
            # which matplotlib.errorbar rejects as a "negative" yerr.
            lo = [max(0.0, cells[p].mean - cells[p].lo) for p in grid]
            hi = [max(0.0, cells[p].hi - cells[p].mean) for p in grid]
            ax.errorbar(grid, ys, yerr=[lo, hi], capsize=3, linewidth=1.6,
                        markersize=6, **STYLE[proto])
        ax.set_xlabel("adversarial fraction $\\varphi$")
        ax.set_title(f"$n = {n}$")
        ax.set_ylim(-0.05, 1.08)
        _grid(ax)
    axes[0].set_ylabel("finalization success rate")
    axes[1].legend(frameon=False)
    note = ("  (PBFT recovers via an UNSAFE fork above 1/3)"
            if family == "equivocate" else "")
    fig.suptitle(f"Liveness vs adversarial fraction — {FAMILY_LABEL[family]} "
                 f"(mean ± 95% Wilson){note}")
    return _save(fig, plot_dir, f"liveness_vs_phi_{family}")


def fig_pbft_viewchange_rate_vs_phi(rows, plot_dir):
    """PBFT view-change rate vs phi (equivocate), faceted by n."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, NS):
        rate = aa.pbft_view_change_rate(rows, n)
        grid = sorted(rate)
        ax.plot(grid, [rate[p].mean for p in grid], linewidth=1.6,
                markersize=6, **STYLE["pbft"])
        ax.set_xlabel("adversarial fraction $\\varphi$")
        ax.set_title(f"$n = {n}$")
        _grid(ax)
    axes[0].set_ylabel("view-change rate (events / s)")
    fig.suptitle("PBFT view-change rate vs equivocator fraction "
                 "(rises to 1/3, collapses to 0 at the fork)")
    return _save(fig, plot_dir, "pbft_viewchange_rate_vs_phi")


def fig_ffg_slashable_vs_phi(rows, plot_dir):
    """Casper FFG max slashable stake vs phi (equivocate) with the 1/3 line."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, NS):
        slash = aa.ffg_slashable(rows, n)
        grid = sorted(slash)
        ax.plot(grid, [slash[p].mean for p in grid], linewidth=1.6,
                markersize=6, **STYLE["casper-ffg"])
        ax.axhline(THIRD, color="grey", linewidth=1.0, linestyle="--", zorder=1,
                   label="$1/3$ accountable-safety threshold")
        ax.set_xlabel("adversarial fraction $\\varphi$")
        ax.set_title(f"$n = {n}$")
        _grid(ax)
    axes[0].set_ylabel("max slashable stake fraction")
    axes[1].legend(frameon=False)
    fig.suptitle("Casper FFG slashable stake vs equivocator fraction "
                 "(crosses 1/3 at $\\varphi = 0.40$)")
    return _save(fig, plot_dir, "ffg_slashable_vs_phi")


def fig_safety_cliff_vs_phi(rows, plot_dir):
    """Cross-protocol safety-violation rate vs phi (equivocate), faceted by n."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, NS):
        for proto in PROTO_ORDER:
            rate = aa.safety_violation_rate(rows, proto, n)
            grid = sorted(rate)
            if not grid:
                continue
            ax.plot(grid, [rate[p].mean for p in grid], linewidth=1.6,
                    markersize=6, **STYLE[proto])
        ax.set_xlabel("adversarial fraction $\\varphi$")
        ax.set_title(f"$n = {n}$")
        ax.set_ylim(-0.05, 1.08)
        _grid(ax)
    axes[0].set_ylabel("safety-violation rate")
    axes[1].legend(frameon=False)
    fig.suptitle("Cross-protocol safety-violation rate vs equivocator fraction "
                 "(PBFT fork cliff in $[0.33, 0.40]$)")
    return _save(fig, plot_dir, "safety_cliff_vs_phi")


def render_all(adversary_dir: str = aa.ADVERSARY_DIR, plot_dir: str = PLOT_DIR):
    rows = aa.load_adversary_rows(adversary_dir)
    names = []
    for family in ("delay", "offline", "equivocate"):
        if any(r["family"] == family for r in rows):
            names.append(fig_liveness_vs_phi(rows, family, plot_dir))
    if any(r["family"] == "equivocate" for r in rows):
        names.append(fig_pbft_viewchange_rate_vs_phi(rows, plot_dir))
        names.append(fig_ffg_slashable_vs_phi(rows, plot_dir))
        names.append(fig_safety_cliff_vs_phi(rows, plot_dir))
    return names


def main() -> None:
    names = render_all()
    print(f"wrote {len(names)} figures (PNG+PDF) -> {PLOT_DIR}: {', '.join(names)}")


if __name__ == "__main__":
    main()
