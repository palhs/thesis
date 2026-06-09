"""Explanatory baseline illustrations (read-only view; no new logic).

This module is a *new, additive* view over the already-committed Week-8
baseline artifacts. It touches none of the existing pipeline
(``analysis.py`` / ``aggregate.py`` / ``plots.py`` are unchanged); it only
reads the frozen CSVs and renders a handful of charts whose purpose is to
make the numbers *legible to a human reader* rather than thesis-ready.

Where ``plots.py`` renders one metric-vs-n curve per figure (the Chapter-4
figures), this module renders the *interpretation*:

  1. cost_per_commit_bar  — the RQ3 headline: msgs to commit one unit,
     log-scale bars at a fixed n, with the order-of-magnitude ratios called
     out. A bar chart makes the ≈14x (Snowman/PBFT) gap obvious where a
     log-line buries it.
  2. theory_vs_measured   — measured msgs/acu points overlaid on each
     protocol's *predicted* slope (PBFT 2n, Casper 1.2n, Snowman 2*K*beta).
     Visual check that the simulator tracks published theory (markers sit on
     the lines; the largest gaps, ~6-7%, are at n=4 — see the cis report).
     Promoted to a thesis figure (Ch4 Figure 4.7): also rendered as a tracked
     vector PDF into PLOT_DIR alongside the canonical plots.py figures.
  3. variance_heatmap     — coefficient of variation per metric x protocol.
     Shows at a glance that everything is deterministic (CV=0) except
     workload-driven goodput (CV ~= 2.2%).
  4. goodput_spread       — the 20 per-seed goodput samples per protocol
     at a single n, with the 95% CI band. The one metric that actually
     varies, shown honestly.
  5. profile_panel        — a normalized latency / goodput / cost profile
     per protocol at fixed n: each protocol's tradeoff shape at a glance.
  6. overview             — a single 2x2 dashboard stitching the four
     headline stories for a one-screen read.

Inputs (frozen, provenance 24a491a4):
    results/baseline/aggregated.csv  — per-(protocol,n) mean/ci/cv
    results/baseline/metrics.csv     — per-trial (20 seeds) rows

Output (new dir; does not collide with the Chapter-4 figures):
    results/baseline/explain/*.png

Re-run:
    PYTHONPATH=src python3 -m output.explain
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # headless / deterministic.
import matplotlib.pyplot as plt

AGG_PATH = "results/baseline/aggregated.csv"
TRIAL_PATH = "results/baseline/metrics.csv"
OUT_DIR = "results/baseline/explain"
# Thesis-figure dir (the canonical Chapter-4 figures from plots.py live here as
# tracked vector PDFs). One explanatory chart — theory_vs_measured — is promoted
# to a thesis figure (Ch4 Figure 4.7) and additionally rendered as PDF here.
PLOT_DIR = "results/baseline/plots"

# Same palette as plots.py so the explanatory charts read identically to the
# Chapter-4 figures (copied, not imported, to avoid coupling).
STYLE = {
    "pbft":       dict(color="#1f77b4", marker="o", label="PBFT"),
    "casper-ffg": dict(color="#ff7f0e", marker="s", label="Casper FFG"),
    "snowman":    dict(color="#2ca02c", marker="^", label="Snowman"),
}
PROTO_ORDER = ("pbft", "casper-ffg", "snowman")
NS = (4, 7, 10, 16, 25)
FIXED_N = 16  # all three protocols present; representative mid-size.


# --------------------------------------------------------------------------
# Loading (stdlib csv; the frozen artifacts are small).
# --------------------------------------------------------------------------
def load_agg():
    """Return {(protocol, n): {col: float}} from aggregated.csv, deduped.

    Casper appears as both ``-uniform`` and ``-nonuniform`` at n=4 with
    identical values; first-wins dedup on (protocol, n) is therefore safe.
    """
    out: dict = {}
    with open(AGG_PATH, newline="") as fh:
        for row in csv.DictReader(fh):
            key = (row["protocol"], int(row["n"]))
            if key in out:
                continue
            rec = {}
            for k, v in row.items():
                if k in ("run_id", "protocol"):
                    continue
                rec[k] = float(v)
            out[key] = rec
    return out


def load_trials():
    """Return {protocol: [goodput,...]} — the 20 per-seed samples at FIXED_N.

    goodput is flat in n by model design, so a single n already captures its
    full seed-to-seed spread. We deliberately take one n (FIXED_N, where all
    three protocols exist) rather than pooling across n: pooling would
    replicate each seed value once per n — inflating the apparent sample size
    from 20 to 80-120 and silently double-counting Casper's n=4
    uniform/nonuniform pair (distinct run_ids, identical rows). Restricting to
    one n keeps the box a true 20-sample distribution and lets the n=FIXED_N
    95% CI diamond sit on exactly the points it summarizes.
    """
    out = defaultdict(list)
    seen = set()
    with open(TRIAL_PATH, newline="") as fh:
        for row in csv.DictReader(fh):
            if int(row["n"]) != FIXED_N:
                continue
            # Guard against any duplicate (protocol, n) scenario sharing seeds.
            sig = (row["protocol"], row["n"], row["seed"])
            if sig in seen:
                continue
            seen.add(sig)
            out[row["protocol"]].append(float(row["goodput"]))
    return out


def _series(agg, proto, col):
    """(xs, ys) for a metric column across the n where `proto` exists."""
    xs, ys = [], []
    for n in NS:
        if (proto, n) in agg:
            xs.append(n)
            ys.append(agg[(proto, n)][col])
    return xs, ys


def _save(fig, name, pdf_dir=None):
    """Save the figure PNG to OUT_DIR (companion). If pdf_dir is given, also
    emit a vector PDF there first (for a chart promoted to a thesis figure)."""
    if pdf_dir is not None:
        os.makedirs(pdf_dir, exist_ok=True)
        fig.savefig(os.path.join(pdf_dir, f"{name}.pdf"))
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# 1. Cost to commit one unit — the RQ3 headline, as log-scale bars.
# --------------------------------------------------------------------------
def cost_per_commit_bar(agg):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    vals = [agg[(p, FIXED_N)]["total_msgs_per_acu_mean"] for p in PROTO_ORDER]
    colors = [STYLE[p]["color"] for p in PROTO_ORDER]
    labels = [STYLE[p]["label"] for p in PROTO_ORDER]
    bars = ax.bar(labels, vals, color=colors, width=0.6)
    ax.set_yscale("log")
    ax.set_ylabel("messages per committed unit (log scale)")
    ax.set_title(f"Cost to commit one unit  (n = {FIXED_N})")
    base = vals[0]  # PBFT reference.
    for bar, v in zip(bars, vals):
        tag = "PBFT baseline" if v == base else f"{v / base:.1f}x PBFT"
        ax.text(bar.get_x() + bar.get_width() / 2, v * 1.08,
                f"{v:.1f}\n({tag})",
                ha="center", va="bottom", fontsize=9)
    ax.margins(y=0.25)
    ax.grid(True, axis="y", which="both", linestyle=":", alpha=0.6)
    fig.tight_layout()
    return _save(fig, "cost_per_commit_bar")


# --------------------------------------------------------------------------
# 2. Theory vs measured — does the sim track published complexity?
# --------------------------------------------------------------------------
def _theory_line(proto, n):
    """Published per-committed-unit message complexity, evaluated at n."""
    if proto == "pbft":
        return 2 * n                       # O(n^2)/instance / n decisions -> 2n/acu
    if proto == "casper-ffg":
        return 1.2 * n                     # one aggregated attestation round
    if proto == "snowman":
        k = min(20, n - 1)                 # K = min(20, n-1)
        return 2 * k * 15.0                # 2 (query+response) * K * beta, beta~=15
    raise KeyError(proto)


def theory_vs_measured(agg):
    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    xs_fine = list(range(4, 26))
    for proto in PROTO_ORDER:
        st = STYLE[proto]
        xs, ys = _series(agg, proto, "total_msgs_per_acu_mean")
        ax.plot(xs, ys, linestyle="none", markersize=8,
                marker=st["marker"], color=st["color"],
                label=f"{st['label']} (measured)")
        tx = [x for x in xs_fine if x >= min(xs)]
        ax.plot(tx, [_theory_line(proto, x) for x in tx],
                linestyle="--", linewidth=1.4, color=st["color"], alpha=0.8)
    # Proxy handle so the dashed lines are named in the legend, not only the
    # footnote (a skimming reader otherwise can't tell theory from a trend).
    ax.plot([], [], linestyle="--", color="0.4", label="theory (predicted)")
    ax.set_yscale("log")
    ax.set_xlabel("validator-set size $n$")
    ax.set_ylabel("messages per committed unit (log)")
    ax.set_title("Measured cost vs. theoretical prediction (dashed)")
    ax.set_xticks(list(NS))
    ax.grid(True, which="both", linestyle=":", alpha=0.6)
    ax.legend(frameon=False, fontsize=9)
    fig.text(0.5, 0.01,
             "markers = simulator;  dashed = theory "
             "(PBFT 2n,  Casper 1.2n,  Snowman 2·K·β, K=min(20,n−1))",
             ha="center", fontsize=8, style="italic")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    # Promoted to Chapter-4 Figure 4.7: also emit a tracked vector PDF beside
    # the canonical thesis figures.
    return _save(fig, "theory_vs_measured", pdf_dir=PLOT_DIR)


# --------------------------------------------------------------------------
# 3. Variance heatmap — what is deterministic vs what carries seed noise.
# --------------------------------------------------------------------------
def variance_heatmap(agg):
    metrics = [
        ("commit_latency_ms_cv", "commit latency"),
        ("tps_cv", "decision rate (tps)"),
        ("goodput_cv", "goodput"),
        ("total_msgs_per_acu_cv", "msgs / unit"),
        ("bytes_per_acu_cv", "bytes / unit"),
        ("success_rate_cv", "success rate"),
    ]
    grid = []
    for _, _ in metrics:
        grid.append([])
    for p in PROTO_ORDER:
        for r, (col, _) in enumerate(metrics):
            # CV is constant in n per protocol here; take the fixed-n cell.
            grid[r].append(agg[(p, FIXED_N)][col])
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    im = ax.imshow(grid, aspect="auto", cmap="OrRd", vmin=0, vmax=2.5)
    ax.set_xticks(range(len(PROTO_ORDER)))
    ax.set_xticklabels([STYLE[p]["label"] for p in PROTO_ORDER])
    ax.set_yticks(range(len(metrics)))
    ax.set_yticklabels([m[1] for m in metrics])
    for r in range(len(metrics)):
        for c in range(len(PROTO_ORDER)):
            v = grid[r][c]
            ax.text(c, r, "0" if v == 0 else f"{v:.2f}%",
                    ha="center", va="center",
                    color="black" if v < 1.3 else "white", fontsize=9)
    ax.set_title("Variability across 20 seeds at fixed $n$ (CV %)\n"
                 "0 = identical every seed (not 'constant in $n$')")
    fig.colorbar(im, ax=ax, label="coefficient of variation (%)")
    fig.tight_layout()
    return _save(fig, "variance_heatmap")


# --------------------------------------------------------------------------
# 4. Goodput spread — the one metric with real variance, shown honestly.
# --------------------------------------------------------------------------
def goodput_spread(trials, agg):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    data = [trials[p] for p in PROTO_ORDER]
    positions = range(1, len(PROTO_ORDER) + 1)
    ax.boxplot(data, positions=list(positions), widths=0.5,
               showfliers=False, medianprops=dict(color="black"))
    for i, p in enumerate(PROTO_ORDER, start=1):
        xs = [i + (j % 5 - 2) * 0.03 for j in range(len(trials[p]))]
        ax.plot(xs, trials[p], linestyle="none", marker=".",
                color=STYLE[p]["color"], alpha=0.6, markersize=6)
        rec = agg[(p, FIXED_N)]
        ax.errorbar(i, rec["goodput_mean"],
                    yerr=rec["goodput_mean"] - rec["goodput_ci_lo"],
                    fmt="D", color=STYLE[p]["color"], capsize=5,
                    markersize=7, markeredgecolor="black")
    ax.set_xticks(list(positions))
    ax.set_xticklabels([STYLE[p]["label"] for p in PROTO_ORDER])
    ax.set_ylabel("goodput (committed tx/s)")
    ax.set_title(f"Goodput across 20 seeds at n = {FIXED_N}  "
                 "(diamonds = mean ± 95% CI)")
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    fig.tight_layout()
    return _save(fig, "goodput_spread")


# --------------------------------------------------------------------------
# 5. Profile panel — normalized tradeoff shape per protocol at fixed n.
# --------------------------------------------------------------------------
def profile_panel(agg):
    # Lower-is-better for latency and cost; higher-is-better for goodput.
    # Normalize each metric to [0,1] across protocols for shape comparison.
    lat = {p: agg[(p, FIXED_N)]["commit_latency_ms_mean"] for p in PROTO_ORDER}
    good = {p: agg[(p, FIXED_N)]["goodput_mean"] for p in PROTO_ORDER}
    cost = {p: agg[(p, FIXED_N)]["total_msgs_per_acu_mean"] for p in PROTO_ORDER}

    def norm(d, higher_better):
        # Ratio-to-best: the best protocol scores 1.0, others score the
        # fraction of the best they achieve. Unlike min-max this never
        # collapses a value to 0 (so no bar vanishes) and the bar height is
        # directly readable as "x% of the best protocol's value".
        if higher_better:
            best = max(d.values())
            return {p: v / best for p, v in d.items()}
        best = min(d.values())  # lower is better -> smallest is best.
        return {p: best / v for p, v in d.items()}

    speed = norm(lat, higher_better=False)
    thru = norm(good, higher_better=True)
    cheap = norm(cost, higher_better=False)
    axes_labels = ["speed\n(low latency)", "throughput\n(goodput)",
                   "frugality\n(low msg cost)"]
    fig, ax = plt.subplots(figsize=(6.6, 4.2))
    width = 0.25
    for i, p in enumerate(PROTO_ORDER):
        vals = [speed[p], thru[p], cheap[p]]
        xs = [j + (i - 1) * width for j in range(3)]
        ax.bar(xs, vals, width=width, color=STYLE[p]["color"],
               label=STYLE[p]["label"])
    ax.set_xticks(range(3))
    ax.set_xticklabels(axes_labels)
    ax.set_ylabel("fraction of the best protocol  (1.0 = best of the three)")
    ax.set_ylim(0, 1.15)
    ax.set_title(f"Protocol tradeoff profile  (n = {FIXED_N}, honest baseline)")
    ax.legend(frameon=False, fontsize=9)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)
    # Annotate each bar with the fraction so the shape is quantitative.
    for i, p in enumerate(PROTO_ORDER):
        vals = [speed[p], thru[p], cheap[p]]
        for j, val in enumerate(vals):
            x = j + (i - 1) * width
            ax.text(x, val + 0.02, f"{val:.2f}", ha="center",
                    va="bottom", fontsize=7)
    fig.text(0.5, 0.005,
             "ratio-to-best within this 3-protocol set (e.g. 0.20 speed = "
             "5x slower than the fastest); not absolute performance",
             ha="center", fontsize=8, style="italic")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    return _save(fig, "profile_panel")


# --------------------------------------------------------------------------
# 6. Overview dashboard — four stories on one screen.
# --------------------------------------------------------------------------
def overview(agg):
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.2))

    # (0,0) commit latency vs n.
    ax = axes[0][0]
    for p in PROTO_ORDER:
        xs, ys = _series(agg, p, "commit_latency_ms_mean")
        ax.plot(xs, ys, marker=STYLE[p]["marker"], color=STYLE[p]["color"],
                label=STYLE[p]["label"], linewidth=1.6)
    ax.set_title("(a) Commit latency — flat in n")
    ax.set_xlabel("n"); ax.set_ylabel("commit latency (ms)")
    ax.set_xticks(list(NS)); ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=False, fontsize=8)

    # (0,1) goodput vs n.
    ax = axes[0][1]
    for p in PROTO_ORDER:
        xs, ys = _series(agg, p, "goodput_mean")
        ax.plot(xs, ys, marker=STYLE[p]["marker"], color=STYLE[p]["color"],
                label=STYLE[p]["label"], linewidth=1.6)
    ax.set_title("(b) Goodput — flat (no saturation in model)")
    ax.set_xlabel("n"); ax.set_ylabel("committed tx/s")
    ax.set_xticks(list(NS)); ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=False, fontsize=8)

    # (1,0) message cost vs n (log).
    ax = axes[1][0]
    for p in PROTO_ORDER:
        xs, ys = _series(agg, p, "total_msgs_per_acu_mean")
        ax.plot(xs, ys, marker=STYLE[p]["marker"], color=STYLE[p]["color"],
                label=STYLE[p]["label"], linewidth=1.6)
    ax.set_yscale("log")
    ax.set_title("(c) Message cost per unit — the RQ3 contrast")
    ax.set_xlabel("n"); ax.set_ylabel("msgs / unit (log)")
    ax.set_xticks(list(NS)); ax.grid(True, which="both", linestyle=":", alpha=0.6)
    ax.legend(frameon=False, fontsize=8)

    # (1,1) decision-rate vs n (the artifact, labeled as such).
    ax = axes[1][1]
    for p in PROTO_ORDER:
        xs, ys = _series(agg, p, "tps_mean")
        ax.plot(xs, ys, marker=STYLE[p]["marker"], color=STYLE[p]["color"],
                label=STYLE[p]["label"], linewidth=1.6)
    ax.set_title("(d) Decision-event rate — scales with n by construction")
    ax.set_xlabel("n"); ax.set_ylabel("tps (decided events/s)")
    ax.set_xticks(list(NS)); ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(frameon=False, fontsize=8)

    fig.suptitle("Week-8 honest-baseline overview  (zero-delay, no faults)",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return _save(fig, "overview")


# --------------------------------------------------------------------------
# 7. PBFT 2n validation — derive the per-ACU cost from the message phases.
# --------------------------------------------------------------------------
# Per-instance delivery counts by phase, read off the simulator's message
# model (src/pbft/node.py; broadcast excludes the sender). Empirically
# confirmed exact at n in {4,7,10,16,25}: total deliveries / decided events
# reproduces total_msgs_per_acu to the last digit (e.g. n=4 -> 30/4 = 7.5).
def _pbft_phase_counts(n):
    """Deliveries per PBFT instance, by phase. Two all-to-all phases
    (PREPARE, COMMIT) at n(n-1) dominate; the leader's PRE-PREPARE and the
    REPLY hop are O(n). One instance yields n `decided` events."""
    return {
        "PRE-PREPARE (leader→all)": n - 1,
        "PREPARE (all→all)":        n * (n - 1),
        "COMMIT (all→all)":         n * (n - 1),
        "REPLY (all→collector)":    n - 1,
    }


PBFT_DECISIONS_PER_INSTANCE = lambda n: n  # one `decided` event per node.


def pbft_2n_validation(agg):
    fig, axes = plt.subplots(1, 3, figsize=(15.0, 4.6))
    blue = STYLE["pbft"]["color"]

    # (a) The "why n^2": one all-to-all phase as an n x n send matrix at n=4.
    ax = axes[0]
    demo_n = 4
    grid = [[0 if i == j else 1 for j in range(demo_n)] for i in range(demo_n)]
    ax.imshow(grid, cmap="Blues", vmin=0, vmax=1.4)
    for i in range(demo_n):
        for j in range(demo_n):
            ax.text(j, i, "—" if i == j else "msg", ha="center", va="center",
                    fontsize=8, color="0.4" if i == j else "white")
    ax.set_xticks(range(demo_n)); ax.set_yticks(range(demo_n))
    ax.set_xticklabels([f"r{j}" for j in range(demo_n)])
    ax.set_yticklabels([f"r{i}" for i in range(demo_n)])
    ax.set_xlabel("recipient"); ax.set_ylabel("sender")
    ax.set_title(f"(a) One all-to-all phase at n={demo_n}\n"
                 f"n(n−1) = {demo_n*(demo_n-1)} messages (no self-send)")

    # (b) Per-instance message budget by phase, stacked, vs n.
    ax = axes[1]
    phases = list(_pbft_phase_counts(4).keys())
    shades = ["#9ecae1", "#3182bd", "#08519c", "#c6dbef"]
    bottoms = [0.0] * len(NS)
    for ph, sh in zip(phases, shades):
        vals = [_pbft_phase_counts(n)[ph] for n in NS]
        ax.bar([str(n) for n in NS], vals, bottom=bottoms, color=sh, label=ph)
        bottoms = [b + v for b, v in zip(bottoms, vals)]
    ax.plot([str(n) for n in NS], [2 * (n * n - 1) for n in NS],
            color="black", marker="o", linewidth=1.3, markersize=4,
            label="total = 2(n²−1)")
    ax.set_xlabel("validator-set size $n$")
    ax.set_ylabel("message deliveries per instance")
    ax.set_title("(b) Per instance: two all-to-all phases\n"
                 "dominate → O(n²) total")
    ax.legend(frameon=False, fontsize=7.5)
    ax.grid(True, axis="y", linestyle=":", alpha=0.6)

    # (c) Divide by n decisions → measured msgs/ACU lands on 2n − 2/n → 2n.
    ax = axes[2]
    xs, ys = _series(agg, "pbft", "total_msgs_per_acu_mean")
    fine = list(range(4, 26))
    ax.plot(fine, [2 * n for n in fine], linestyle="--", color="0.4",
            label="asymptote 2n")
    ax.plot(fine, [2 * n - 2 / n for n in fine], color=blue, linewidth=1.4,
            label="closed form 2n − 2/n")
    ax.plot(xs, ys, linestyle="none", marker="o", markersize=9, color=blue,
            markeredgecolor="black", label="measured (sim)")
    ax.set_xlabel("validator-set size $n$")
    ax.set_ylabel("messages per committed unit")
    ax.set_title("(c) ÷ n decisions per instance\n"
                 "2(n²−1)/n = 2n − 2/n  →  2n")
    ax.set_xticks(list(NS))
    ax.legend(frameon=False, fontsize=8)
    ax.grid(True, linestyle=":", alpha=0.6)

    fig.suptitle("Validating PBFT's ≈2n messages per committed unit  "
                 "(honest baseline)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    return _save(fig, "pbft_2n_validation")


def generate():
    agg = load_agg()
    trials = load_trials()
    made = [
        cost_per_commit_bar(agg),
        theory_vs_measured(agg),
        variance_heatmap(agg),
        goodput_spread(trials, agg),
        profile_panel(agg),
        overview(agg),
        pbft_2n_validation(agg),
    ]
    return made


def main():
    made = generate()
    print(f"wrote {len(made)} explanatory figures to {OUT_DIR}/:")
    for m in made:
        print(f"  - {os.path.basename(m)}")


if __name__ == "__main__":
    main()
