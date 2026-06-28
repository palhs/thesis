"""T54 — adversarial liveness & safety degradation figures.

Renders the Chapter-4 §4.4 adversarial figures from the three Family-C CSVs (via
output.adversary_analysis) to results/adversary/plots/ as PNG (screen) + PDF
(vector, thesis import). Render layer only (smoke-tested, not unit-tested, per
project convention); reuses output.plots STYLE + PROTO_ORDER (3 protocols, no
Narwhal+Tusk). No data is read or written here beyond the committed CSVs — the
byte-identical-CSV gate covers it.

Figures (draft numbers in parentheses):
  - liveness_vs_phi_delay        (Fig 4.14) liveness + finality blow-up, delay
  - liveness_vs_phi_offline      (Fig 4.15) liveness cliffs (phi* boxed), offline
  - throughput_degradation_vs_phi (Fig 4.21) throughput degradation (RQ2), offline
  - liveness_vs_phi_equivocate   (Fig 4.16) liveness, equivocate
  - pbft_viewchange_count_vs_phi (Fig 4.17) PBFT view-change COUNT, equivocate
  - safety_cliff_vs_phi          (Fig 4.18) safety-violation rate + 229 annotation
  - ffg_slashable_vs_phi         (Fig 4.19) Casper FFG slashable stake
  - adversary_tradeoff_matrix    (Fig 4.20) 3x3 protocol x adversary outcome map

In-image titles are descriptive only; interpretation lives in the chapter
captions (draft-style.md, no editorializing in figure titles).

Re-run:
    PYTHONPATH=src python3 -m output.adversary_degradation_plots
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")  # headless / deterministic.
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

from output import adversary_analysis as aa
from output.plots import STYLE, PROTO_ORDER

PLOT_DIR = "results/adversary/plots"
NS = (10, 25)
THIRD = 1.0 / 3.0
XLIM = (-0.02, 0.51)            # shared phi axis across the liveness figures
YLIM = (-0.05, 1.08)           # shared rate axis (0..1 metrics)
DODGE = 0.008                  # per-protocol x-offset so coincident series stay
                               # visible (e.g. PBFT == Snowman at 1.0 in Fig 4.14)


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


def _third_line(ax):
    """Faint 1/3 reference where a safety failure first becomes possible."""
    ax.axvline(THIRD, color="grey", linewidth=0.9, linestyle=":", alpha=0.8,
               zorder=1)


def _liveness_axis(ax, rows, family, n):
    """Draw per-protocol success-rate curves on ax over the shared phi axis.

    Returns {protocol: phi*} where phi* is the survival depth (deepest swept phi
    whose mean success rate is still > 0). Each protocol's swept endpoint reads
    off where its curve ends (e.g. Snowman is swept only to phi=0.33 on the
    equivocate family); the chapter captions state the per-family ranges.
    """
    survival: dict[str, float] = {}
    for i, proto in enumerate(PROTO_ORDER):
        cells = aa.liveness_rate(rows, family, proto, n)
        grid = sorted(cells)
        if not grid:
            continue
        ys = [cells[p].mean for p in grid]
        lo = [max(0.0, cells[p].mean - cells[p].lo) for p in grid]
        hi = [max(0.0, cells[p].hi - cells[p].mean) for p in grid]
        xs = [p + (i - 1) * DODGE for p in grid]  # dodge coincident curves apart
        ax.errorbar(xs, ys, yerr=[lo, hi], capsize=3, linewidth=1.6,
                    markersize=6, **STYLE[proto])
        alive = [p for p in grid if cells[p].mean > 0]
        survival[proto] = max(alive) if alive else grid[0]
    _third_line(ax)
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    _grid(ax)
    return survival


# --------------------------------------------------------------------------- #
# Fig 4.14 — delayed voting: liveness held vs latency paid
# --------------------------------------------------------------------------- #

def _draw_delay_latency(ax, rows, n):
    """Per-axis: delayed-voting time-to-finality ratio vs phi (log y) with the
    Snowman ×peak annotation. Extracted from
    :func:`fig_delay_liveness_and_latency` for reuse by ``output.panels``."""
    for i, proto in enumerate(PROTO_ORDER):
        curve = aa.delay_finality_ratio_by_phi(rows, proto, n)
        grid = sorted(curve)
        if not grid:
            continue
        xs = [p + (i - 1) * DODGE for p in grid]  # dodge PBFT/FFG apart at 1.0x
        ax.plot(xs, [curve[p] for p in grid], linewidth=1.6,
                markersize=6, **STYLE[proto])
    sm = aa.delay_finality_ratio_by_phi(rows, "snowman", n)
    if sm:
        pk_phi = max(sm, key=sm.get)
        pk = sm[pk_phi]
        ax.annotate(f"$\\times{pk:.0f}$", (pk_phi, pk),
                    textcoords="offset points", xytext=(-6, -2),
                    ha="right", va="top", fontsize=11,
                    color=STYLE["snowman"]["color"])
    ax.axhline(1.0, color="grey", linewidth=0.8, linestyle="--", zorder=1)
    ax.set_yscale("log")
    ax.set_xlim(*XLIM)
    ax.set_xlabel("adversarial fraction $\\varphi$")
    _grid(ax)


def fig_delay_liveness_and_latency(rows, plot_dir):
    """Delay family, faceted by n: success rate (top) and the finality blow-up
    (bottom, log scale). The two protocols that hold success at 1.0 in the top
    row — PBFT and Snowman — separate in the bottom row, where only Snowman pays
    the latency, so the figure no longer renders them as identically immune."""
    fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.6), sharex=True)
    for col, n in enumerate(NS):
        ax_live = axes[0][col]
        _liveness_axis(ax_live, rows, "delay", n)
        ax_live.set_title(f"$n = {n}$")
        _draw_delay_latency(axes[1][col], rows, n)
    axes[0][0].set_ylabel("finalization success rate")
    axes[1][0].set_ylabel("time-to-finality ratio (vs $\\varphi = 0$)")
    axes[0][1].legend(frameon=False)
    fig.suptitle("Liveness and time-to-finality under delayed voting "
                 "(mean $\\pm$ 95% Wilson; latency on log scale)")
    return _save(fig, plot_dir, "liveness_vs_phi_delay")


# --------------------------------------------------------------------------- #
# Fig 4.15 — silent non-participation: liveness cliffs as steps, with phi*
# --------------------------------------------------------------------------- #

def _draw_offline_survival_box(ax, rows, survival, n):
    """Per-axis decoration for the offline liveness cliffs: the phi* survival-
    depth box and the Snowman 'alive but starved' annotation. ``survival`` is
    the ``{protocol: phi*}`` dict returned by :func:`_liveness_axis`. Extracted
    from :func:`fig_offline_liveness` for reuse by ``output.panels``."""
    parts = [f"{STYLE[p]['label']} {survival[p]:.2f}"
             for p in PROTO_ORDER if p in survival]
    ax.text(0.03, 0.30, "$\\varphi^*$ survival depth\n" + "\n".join(parts),
            transform=ax.transAxes, fontsize=8, va="top",
            bbox=dict(boxstyle="round", fc="white", ec="grey", alpha=0.9))
    # 'alive but starved': annotate a surviving Snowman cell whose throughput
    # has collapsed (success > 0 but the committed-unit rate is a few %).
    tr = aa.offline_throughput_ratio(rows, "snowman", n)
    live = aa.liveness_rate(rows, "offline", "snowman", n)
    starved = [p for p in sorted(tr)
               if 0 < tr[p].mean < 0.10 and live.get(p) and live[p].mean > 0]
    if starved:
        p0 = starved[-1]
        # anchor at the plateau: success holds at 1.0 while throughput has
        # collapsed — that gap is the point of the label.
        ax.annotate(f"alive but starved\n($\\approx{tr[p0].mean*100:.1f}$% throughput)",
                    (p0, live[p0].mean), textcoords="offset points",
                    xytext=(8, -46), ha="left", va="top", fontsize=8,
                    color=STYLE["snowman"]["color"],
                    arrowprops=dict(arrowstyle="->", lw=0.8,
                                    color=STYLE["snowman"]["color"]))


def fig_offline_liveness(rows, plot_dir):
    """Offline family, faceted by n: success rate as liveness cliffs, with each
    protocol's survival depth phi* boxed and the 'alive but starved' Snowman
    cell labelled with its surviving throughput fraction."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), sharey=True)
    for ax, n in zip(axes, NS):
        survival = _liveness_axis(ax, rows, "offline", n)
        ax.set_title(f"$n = {n}$")
        ax.set_xlabel("silent fraction $\\varphi$")
        _draw_offline_survival_box(ax, rows, survival, n)
    axes[0].set_ylabel("finalization success rate")
    axes[1].legend(frameon=False, loc="upper right")
    fig.suptitle("Liveness under silent non-participation "
                 "(mean $\\pm$ 95% Wilson)")
    return _save(fig, plot_dir, "liveness_vs_phi_offline")


# --------------------------------------------------------------------------- #
# Fig 4.21 — silent non-participation: throughput degradation (the RQ2 reading)
# --------------------------------------------------------------------------- #

def fig_offline_throughput(rows, plot_dir):
    """Offline family, faceted by n in the §4.4 house style: committed-unit
    throughput ratio vs phi — the RQ2 reading of the same sweep behind Fig 4.15.
    The y = 1 - phi reference is the participating-stake invariant: PBFT holds
    flat to its quorum cliff, Casper FFG decays ~ (1 - phi), Snowman starves
    earliest. Supersedes the per-n square plots from output.offline_plots."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6), sharey=True)
    for ax, n in zip(axes, NS):
        phis: set[float] = set()
        for i, proto in enumerate(PROTO_ORDER):
            tr = aa.offline_throughput_ratio(rows, proto, n)
            grid = sorted(tr)
            phis.update(grid)
            if not grid:
                continue
            xs = [p + (i - 1) * DODGE for p in grid]  # dodge coincident curves apart
            ax.errorbar(xs, [tr[p].mean for p in grid],
                        yerr=[tr[p].ci_half for p in grid], capsize=3,
                        linewidth=1.6, markersize=6, **STYLE[proto])
        # y = 1 - phi participating-stake invariant across the swept range.
        ref = sorted(phis)
        if ref:
            ax.plot(ref, [1.0 - p for p in ref], color="grey", linewidth=1.0,
                    linestyle="--", zorder=1, label="$y = 1 - \\varphi$ invariant")
        _third_line(ax)
        ax.set_xlim(*XLIM)
        ax.set_ylim(*YLIM)
        ax.set_xlabel("silent fraction $\\varphi$")
        ax.set_title(f"$n = {n}$")
        _grid(ax)
    axes[0].set_ylabel("throughput ratio (vs $\\varphi = 0$ control)")
    axes[1].legend(frameon=False)
    fig.suptitle("Throughput degradation under silent non-participation "
                 "(mean $\\pm$ 95% CI)")
    return _save(fig, plot_dir, "throughput_degradation_vs_phi")


# --------------------------------------------------------------------------- #
# Fig 4.16 — equivocation: liveness
# --------------------------------------------------------------------------- #

def fig_equivocate_liveness(rows, plot_dir):
    """Equivocate family, faceted by n: success rate per protocol. PBFT's
    non-monotone curve and its 'recovery' above 1/3 are read through the chapter
    caption (the recovery is the safety failure of Fig 4.18, not live finality)."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    for ax, n in zip(axes, NS):
        _liveness_axis(ax, rows, "equivocate", n)
        ax.set_title(f"$n = {n}$")
        ax.set_xlabel("equivocator fraction $\\varphi$")
    axes[0].set_ylabel("finalization success rate")
    axes[1].legend(frameon=False)
    fig.suptitle("Liveness under equivocation (mean $\\pm$ 95% Wilson)")
    return _save(fig, plot_dir, "liveness_vs_phi_equivocate")


# --------------------------------------------------------------------------- #
# Fig 4.17 — equivocation: PBFT view-change COUNT (not rate)
# --------------------------------------------------------------------------- #

def fig_pbft_viewchange_count(rows, plot_dir):
    """PBFT view-change COUNT vs phi (equivocate), shared y across n so the
    committee-size effect (10 at n=10, 25 at n=25) is visible; the count
    collapses to 0 at phi=0.40 where the deterministic fork replaces rotation."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    top = 0.0
    for ax, n in zip(axes, NS):
        cnt = aa.pbft_view_change_count(rows, n)
        grid = sorted(cnt)
        ys = [cnt[p].mean for p in grid]
        top = max(top, max(ys, default=0.0))
        ax.plot(grid, ys, linewidth=1.6, markersize=6, **STYLE["pbft"])
        # label the last-safe plateau and the collapse to zero.
        safe = [(p, y) for p, y in zip(grid, ys) if y > 0]
        if safe:
            p_last, y_last = safe[-1]
            ax.annotate(f"{int(round(y_last))}", (p_last, y_last),
                        textcoords="offset points", xytext=(-6, 7), ha="right",
                        fontsize=10, color=STYLE["pbft"]["color"])
        zero = [(p, y) for p, y in zip(grid, ys) if p > THIRD and y == 0]
        if zero:
            p0, _ = zero[0]
            ax.annotate("rotation $\\to$ fork\n(count $\\to 0$)", (p0, 0),
                        textcoords="offset points", xytext=(6, 22), ha="left",
                        va="bottom", fontsize=8, color="grey",
                        arrowprops=dict(arrowstyle="->", lw=0.8, color="grey"))
        _third_line(ax)
        ax.set_xlim(*XLIM)
        ax.set_xlabel("equivocator fraction $\\varphi$")
        ax.set_title(f"$n = {n}$")
        _grid(ax)
    # shared y across the n panels so the committee-size effect (10 vs 25) shows.
    axes[0].set_ylim(-1.5, top * 1.15 + 1)
    axes[0].set_ylabel("view-change count")
    fig.suptitle("PBFT view-change count under equivocation")
    return _save(fig, plot_dir, "pbft_viewchange_count_vs_phi")


# --------------------------------------------------------------------------- #
# Fig 4.18 — equivocation: cross-protocol safety-violation rate + 229 annotation
# --------------------------------------------------------------------------- #

def _draw_safety_cliff(ax, rows, n):
    """Per-axis: cross-protocol safety-violation rate vs phi (steps-post) with
    the PBFT conflicting-instances annotation. Extracted from
    :func:`fig_safety_cliff` for reuse by ``output.panels``."""
    for proto in PROTO_ORDER:
        rate = aa.safety_violation_rate(rows, proto, n)
        grid = sorted(rate)
        if not grid:
            continue
        ax.plot(grid, [rate[p].mean for p in grid], linewidth=1.6,
                markersize=6, drawstyle="steps-post", **STYLE[proto])
    ci = aa.pbft_conflicting_instances(rows, n)
    brk = [p for p in sorted(ci) if ci[p].mean > 0]
    if brk:
        p0 = brk[0]
        ax.annotate(f"{int(round(ci[p0].mean))} conflicting\ninstances",
                    (p0, 1.0), textcoords="offset points", xytext=(8, -4),
                    ha="left", va="top", fontsize=9,
                    color=STYLE["pbft"]["color"])
    _third_line(ax)
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_xlabel("equivocator fraction $\\varphi$")
    _grid(ax)


def fig_safety_cliff(rows, plot_dir):
    """Cross-protocol safety-violation rate vs phi (equivocate), faceted by n.
    Only PBFT departs from zero, stepping to a deterministic fork at phi=0.40;
    the fork's magnitude (conflicting (view,seq) instances) is annotated."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, NS):
        _draw_safety_cliff(ax, rows, n)
        ax.set_title(f"$n = {n}$")
    axes[0].set_ylabel("safety-violation rate")
    axes[1].legend(frameon=False)
    fig.suptitle("Cross-protocol safety-violation rate under equivocation")
    return _save(fig, plot_dir, "safety_cliff_vs_phi")


# --------------------------------------------------------------------------- #
# Fig 4.19 — equivocation: Casper FFG slashable stake
# --------------------------------------------------------------------------- #

def fig_ffg_slashable(rows, plot_dir):
    """Casper FFG max slashable stake vs phi (equivocate) with the 1/3
    accountable-safety threshold marked, faceted by n."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, n in zip(axes, NS):
        slash = aa.ffg_slashable(rows, n)
        grid = sorted(slash)
        ax.plot(grid, [slash[p].mean for p in grid], linewidth=1.6,
                markersize=6, **STYLE["casper-ffg"])
        ax.axhline(THIRD, color="grey", linewidth=1.0, linestyle="--", zorder=1,
                   label="$1/3$ accountable-safety threshold")
        ax.set_xlim(*XLIM)
        ax.set_xlabel("equivocator fraction $\\varphi$")
        ax.set_title(f"$n = {n}$")
        _grid(ax)
    axes[0].set_ylabel("max slashable stake fraction")
    axes[1].legend(frameon=False)
    fig.suptitle("Casper FFG maximum slashable stake under equivocation")
    return _save(fig, plot_dir, "ffg_slashable_vs_phi")


# --------------------------------------------------------------------------- #
# Fig 4.20 — the cross-adversary outcome matrix (Table 4.2, visualized)
# --------------------------------------------------------------------------- #

# Outcome class -> fill colour. Each cell's class encodes the *kind* of outcome;
# the label carries the magnitude. The five classes make the no-dominance
# inversion legible: each protocol's row spans several classes, none all-green.
_CLASS_COLOR = {
    "robust":      "#a6dba0",  # liveness held, safe
    "costly":      "#fde08a",  # survives, but pays latency/throughput
    "liveness":    "#fdb87d",  # liveness degrades or fails
    "accountable": "#9ecae1",  # safety failure, but provably attributable
    "break":       "#f4a3a3",  # safety break, unaccountable
}
_CLASS_LABEL = {
    "robust": "robust (liveness held)",
    "costly": "survives at a latency cost",
    "liveness": "liveness loss",
    "accountable": "safety failure, accountable",
    "break": "safety break, unaccountable",
}
_ADVERSARY_COLS = (("delay", "Delayed\nvoting"),
                   ("offline", "Silent non-\nparticipation"),
                   ("equivocate", "Equivocation"))
# (class, magnitude label) per (protocol, adversary), traceable to Table 4.2.
_CELL = {
    ("pbft", "delay"):            ("robust", "immune\n$1.0\\times$, 0 VC"),
    ("pbft", "offline"):          ("robust", "clean cliff\n$\\varphi=0.40$"),
    ("pbft", "equivocate"):       ("break", "fork: 229\nunaccountable"),
    ("casper-ffg", "delay"):      ("liveness", "liveness dip\n$0.60/0.65$"),
    ("casper-ffg", "offline"):    ("liveness", "graceful decay\n$\\approx 1-\\varphi$"),
    ("casper-ffg", "equivocate"): ("accountable", "$\\geq\\!1/3$ slashable"),
    ("snowman", "delay"):         ("costly", "survives\n$\\times62 / \\times49$"),
    ("snowman", "offline"):       ("liveness", "early cliff\n$\\varphi=0.10/0.20$"),
    ("snowman", "equivocate"):    ("robust", "no fork surface\n$\\varepsilon\\!\\approx\\!5\\times10^{-15}$"),
}


def fig_tradeoff_matrix(rows, plot_dir):
    """3x3 protocol x adversary outcome matrix rendering Table 4.2 visually:
    cell colour = outcome class, cell label = the headline magnitude. No data is
    read from `rows` (the matrix is the synthesized verdict); the argument is
    kept for a uniform render_all signature."""
    nrow, ncol = len(PROTO_ORDER), len(_ADVERSARY_COLS)
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    for i, proto in enumerate(PROTO_ORDER):
        y = nrow - 1 - i
        for j, (adv, _label) in enumerate(_ADVERSARY_COLS):
            cls, text = _CELL[(proto, adv)]
            ax.add_patch(Rectangle((j, y), 1, 1, facecolor=_CLASS_COLOR[cls],
                                   edgecolor="white", linewidth=2))
            ax.text(j + 0.5, y + 0.5, text, ha="center", va="center",
                    fontsize=9.5)
    ax.set_xlim(0, ncol)
    ax.set_ylim(0, nrow)
    ax.set_xticks([j + 0.5 for j in range(ncol)])
    ax.set_xticklabels([lbl for _a, lbl in _ADVERSARY_COLS])
    ax.set_yticks([nrow - 1 - i + 0.5 for i in range(nrow)])
    ax.set_yticklabels([STYLE[p]["label"] for p in PROTO_ORDER])
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Adversarial outcomes by protocol and strategy")
    handles = [Patch(facecolor=_CLASS_COLOR[c], edgecolor="white",
                     label=_CLASS_LABEL[c]) for c in _CLASS_COLOR]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08),
              ncol=3, frameon=False, fontsize=8)
    return _save(fig, plot_dir, "adversary_tradeoff_matrix")


def render_all(adversary_dir: str = aa.ADVERSARY_DIR, plot_dir: str = PLOT_DIR):
    rows = aa.load_adversary_rows(adversary_dir)
    names = []
    if any(r["family"] == "delay" for r in rows):
        names.append(fig_delay_liveness_and_latency(rows, plot_dir))
    if any(r["family"] == "offline" for r in rows):
        names.append(fig_offline_liveness(rows, plot_dir))
        names.append(fig_offline_throughput(rows, plot_dir))
    if any(r["family"] == "equivocate" for r in rows):
        names.append(fig_equivocate_liveness(rows, plot_dir))
        names.append(fig_pbft_viewchange_count(rows, plot_dir))
        names.append(fig_safety_cliff(rows, plot_dir))
        names.append(fig_ffg_slashable(rows, plot_dir))
    names.append(fig_tradeoff_matrix(rows, plot_dir))
    return names


def main() -> None:
    names = render_all()
    print(f"wrote {len(names)} figures (PNG+PDF) -> {PLOT_DIR}: {', '.join(names)}")


if __name__ == "__main__":
    main()
