"""T54 — adversarial liveness & safety degradation analysis.

Pure-stdlib reducers over the three committed Family-C adversarial CSVs:

- results/adversary/delayed_voters.csv      (T51 delay-emission)
- results/adversary/offline_validators.csv  (T52 withhold-participation)
- results/adversary/equivocating_nodes.csv  (T53 equivocate-vote)

Liveness (% of seed-runs reaching consensus = mean(success_rate) + Wilson) is
measured across all three families; the four per-protocol SAFETY invariants
(adversary-model §5/§7) come from the equivocate family only — the sole sweep
that carries them. Safety signals are seed-invariant (deterministic parity
partition, no adversary RNG), so they carry no CI; only the liveness proportion
gets a Wilson band. No third-party dependency, no matplotlib (headless-testable
like analysis.py). Design: docs/plans/2026-06-19-t54-adversarial-degradation-metrics-design.md
"""
from __future__ import annotations

import csv
import math
import os
from collections import defaultdict
from dataclasses import dataclass

from output.analysis import wilson_interval
from output.delay_analysis import mean_ci, MeanCI

ADVERSARY_DIR = "results/adversary"
RANKING_CSV = "results/adversary/degradation_ranking.csv"
EPSILON_CSV = "results/adversary/snowman_epsilon_witness.csv"

# filename -> family tag.
FAMILIES = {
    "delayed_voters.csv": "delay",
    "offline_validators.csv": "offline",
    "equivocating_nodes.csv": "equivocate",
}
PROTO_ORDER = ("pbft", "casper-ffg", "snowman")
NS = (10, 25)
PHI = "byzantine_fraction"


def _fnum(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def load_rows(path: str) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_adversary_rows(adversary_dir: str = ADVERSARY_DIR) -> list[dict]:
    """Load all present Family-C CSVs, tagging each row with `family`.

    Reads by column name (the three tails diverge in membership and order).
    Missing files are skipped (so a partial checkout still loads what exists).
    """
    out: list[dict] = []
    for fname, family in FAMILIES.items():
        path = os.path.join(adversary_dir, fname)
        if not os.path.exists(path):
            continue
        for r in load_rows(path):
            r = dict(r)
            r["family"] = family
            out.append(r)
    return out


# --------------------------------------------------------------------------- #
# Liveness (all three families)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class LivenessCell:
    phi: float
    mean: float        # mean(success_rate) over the cell's runs
    lo: float          # Wilson lower
    hi: float          # Wilson upper
    k: int             # successes
    n_seeds: int       # runs in the cell (delay pools over the m axis)


def liveness_rate(rows, family, protocol, n) -> dict[float, LivenessCell]:
    """{phi: LivenessCell} for one (family, protocol, n) group.

    For the delay family this pools over the magnitude axis (delay_mult) at each
    phi — the liveness pattern is m-invariant (FFG proposer-overlap dips do not
    depend on m), so the pooled proportion is representative and gives a tighter
    Wilson band. success_rate is a per-run 0/1 flag.
    """
    buckets: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        if r["family"] != family or r["protocol"] != protocol or int(r["n"]) != n:
            continue
        buckets[round(_fnum(r[PHI]), 4)].append(_fnum(r["success_rate"]))
    out: dict[float, LivenessCell] = {}
    for phi, vals in buckets.items():
        finite = [v for v in vals if not math.isnan(v)]
        nn = len(finite)
        k = sum(1 for v in finite if v >= 0.5)
        lo, hi = wilson_interval(k, nn)
        out[phi] = LivenessCell(phi, k / nn if nn else float("nan"), lo, hi, k, nn)
    return out


# --------------------------------------------------------------------------- #
# Safety invariants (equivocate family only)
# --------------------------------------------------------------------------- #

def _equiv_cell(rows, protocol, n, metric) -> dict[float, MeanCI]:
    buckets: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        if (r["family"] != "equivocate" or r["protocol"] != protocol
                or int(r["n"]) != n):
            continue
        buckets[round(_fnum(r[PHI]), 4)].append(_fnum(r[metric]))
    return {phi: mean_ci(v) for phi, v in buckets.items()}


def pbft_view_change_rate(rows, n) -> dict[float, MeanCI]:
    """PBFT §5 operational invariant: view-change frequency tracks equivocator
    rate. {phi: MeanCI of view_change_count / run_horizon_s}. Seed-invariant in
    the equivocate data (zero-width CI), reported as the mean."""
    buckets: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        if (r["family"] != "equivocate" or r["protocol"] != "pbft"
                or int(r["n"]) != n):
            continue
        horizon = _fnum(r["run_horizon_s"])
        vc = _fnum(r["view_change_count"])
        buckets[round(_fnum(r[PHI]), 4)].append(
            vc / horizon if horizon > 0 else float("nan"))
    return {phi: mean_ci(v) for phi, v in buckets.items()}


def ffg_slashable(rows, n) -> dict[float, MeanCI]:
    """Casper FFG §7.3 accountable-safety invariant: max_slashable_stake_fraction
    vs the 1/3 threshold. {phi: MeanCI}."""
    return _equiv_cell(rows, "casper-ffg", n, "max_slashable_stake_fraction")


def safety_violation_rate(rows, protocol, n) -> dict[float, MeanCI]:
    """Cross-node safety-violation rate (mean of the 0/1 safety_violation flag)
    for `protocol` on the equivocate family. {phi: MeanCI}; used by the f_max
    bracket and the cross-protocol cliff figure."""
    return _equiv_cell(rows, protocol, n, "safety_violation")


@dataclass(frozen=True)
class EpsilonWitness:
    n: int
    K: int
    alpha_c: int
    beta: int
    empirical_rate: float       # mean(safety_violation) over all Snowman runs at n
    empirical_wilson_hi: float  # Wilson upper bound on the 0-of-n_obs proportion
    analytical_bound: float     # (1 - alpha_c/K)^beta
    n_obs: int


def snowman_epsilon_witness(rows, n) -> "EpsilonWitness | None":
    """Snowman §5/§7.1 invariant: empirical safety-violation rate <= (1-alpha_c/K)^beta.

    Empirical = mean(safety_violation) over ALL Snowman equivocate runs at this n
    (pooled across phi — the analytical bound is a per-n constant), with a Wilson
    upper bound. The empirical rate is structurally 0 at production beta=15; the
    bound is ~10^-15 (n=10) / ~10^-11 (n=25). The witness reports both — the
    invariant holds trivially. (The beta in {3,5} observability regime is deferred
    to a separate RQ4 sweep; not run here.)
    """
    sel = [r for r in rows if r["family"] == "equivocate"
           and r["protocol"] == "snowman" and int(r["n"]) == n]
    if not sel:
        return None
    k = sum(int(_fnum(r["safety_violation"])) for r in sel)
    nn = len(sel)
    K = int(_fnum(sel[0]["K"]))
    alpha_c = int(_fnum(sel[0]["alpha_c"]))
    beta = int(_fnum(sel[0]["beta"]))
    bound = (1.0 - alpha_c / K) ** beta if K else float("nan")
    _, hi = wilson_interval(k, nn)
    return EpsilonWitness(n, K, alpha_c, beta,
                          k / nn if nn else float("nan"), hi, bound, nn)


def nwt_invariant() -> dict:
    """Narwhal+Tusk §5 invariant (no conflicting header reaches 2f+1 signatures).

    Unmeasurable: NWT is unimplemented (T38.1, sequenced post-T55). Returned as
    an explicit deferral so the ranking table documents the gap rather than
    emitting a silent NaN row (output-format.md §4 absent-vs-NaN distinction).
    """
    return {"protocol": "narwhal-tusk",
            "invariant": "conflicting_header_reaches_2f1",
            "status": "deferred", "blocked_by": "T38.1",
            "note": "NWT unimplemented; defined in spec, measured when T38.1 lands"}


# --------------------------------------------------------------------------- #
# f_max bracket estimator (Backlog item (b))
# --------------------------------------------------------------------------- #

def bracket(phi_grid, holds_at):
    """Interval-censored f_max over a sorted phi grid.

    Returns (hold_edge, break_edge): hold_edge = largest phi (scanning up) still
    holding before the first break; break_edge = first phi that breaks. The
    headline f_max is the hold_edge (largest-phi-that-holds, per the binding
    evaluation-metrics.md definition); the bracket [hold_edge, break_edge] is
    the censoring interval. Right-censored (never breaks) -> (max phi, None).
    Departs from T48's AURC: the equivocate axis is a discrete cliff, so the
    robustness scalar is this bracket, not an area under a smooth curve.
    """
    hold, brk = None, None
    for phi in sorted(phi_grid):
        if holds_at(phi):
            if brk is None:        # only extend the hold edge before the break
                hold = phi
        else:
            brk = phi
            break
    return (hold, brk)


THIRD = 1.0 / 3.0


@dataclass(frozen=True)
class FMaxRow:
    family: str            # delay / offline / equivocate
    metric: str            # liveness / safety
    invariant: str         # human-readable invariant id
    protocol: str
    n: int
    f_max_hold: float      # headline f_max (largest phi that holds); nan if none
    f_max_break: object    # upper censoring edge; None if right-censored
    f_max_count: float     # populated for pbft/snowman/nwt, else NaN
    f_max_stake: float     # populated for casper-ffg, else NaN
    theoretical_bound: str
    safety_broken: bool    # PBFT live-but-forked phi region exists
    note: str


_THEORETICAL = {
    "pbft": "< n/3 (count)",
    "casper-ffg": "< 1/3 stake",
    "snowman": "parameter-dependent (alpha_c/K, beta)",
}


def _route(protocol, hold):
    """(f_max_count, f_max_stake): one populated by fault-attribution model."""
    val = float("nan") if hold is None else float(hold)
    if protocol == "casper-ffg":
        return (float("nan"), val)
    return (val, float("nan"))      # pbft / snowman (count)


def f_max_for(rows, metric, protocol, n) -> FMaxRow:
    """Compute the f_max bracket for one (metric, protocol, n).

    metric == "liveness": holds_at(phi) = mean(success_rate) >= 1.0 over the
    equivocate family (the safety-paired liveness). metric == "safety":
    per-protocol invariant predicate.
    """
    family = "equivocate"
    if metric == "liveness":
        return _liveness_fmax(rows, "equivocate", protocol, n)
    if protocol == "pbft":
        rate = safety_violation_rate(rows, "pbft", n)
        grid = sorted(rate)
        hold, brk = bracket(grid, lambda p: rate[p].mean == 0.0)
        broken = any(rate[p].mean > 0 for p in grid)
        inv = "no two-honest commit conflict at same (view,seq)"
        bound = _THEORETICAL["pbft"]
        note = "below 1/3: view-change rotation (safety holds); fork cliff above"
    elif protocol == "casper-ffg":
        slash = ffg_slashable(rows, n)
        grid = sorted(slash)
        hold, brk = bracket(grid, lambda p: slash[p].mean < THIRD)
        broken = any(slash[p].mean >= THIRD for p in grid)
        inv = "slashable stake < 1/3 (accountable safety)"
        bound = _THEORETICAL["casper-ffg"]
        note = ("never forks in-model; signal is economically-possible "
                "violation crossing the 1/3 slashing threshold")
    elif protocol == "snowman":
        rate = safety_violation_rate(rows, "snowman", n)
        grid = sorted(rate)
        hold, brk = bracket(grid, lambda p: rate[p].mean == 0.0)
        broken = False
        inv = "empirical safety-violation rate <= (1-alpha_c/K)^beta"
        bound = _THEORETICAL["snowman"]
        note = "no fork surface (equivocate reduces to lying-responder); see epsilon witness"
    else:
        raise ValueError(protocol)

    count, stake = _route(protocol, hold)
    return FMaxRow(family=family, metric=metric, invariant=inv, protocol=protocol,
                   n=n, f_max_hold=hold if hold is not None else float("nan"),
                   f_max_break=brk, f_max_count=count, f_max_stake=stake,
                   theoretical_bound=bound, safety_broken=broken, note=note)


def _liveness_fmax(rows, family, protocol, n) -> FMaxRow:
    """Liveness bracket for any family. For PBFT under equivocation, flag the
    live-but-forked region (success_rate recovers to 1.0 above 1/3 via an UNSAFE
    fork) so the row is never read as resilience."""
    cells = liveness_rate(rows, family, protocol, n)
    grid = sorted(cells)
    hold, brk = bracket(grid, lambda p: cells[p].mean >= 1.0 - 1e-9)
    count, stake = _route(protocol, hold)
    broken = (family == "equivocate" and protocol == "pbft"
              and any(c.mean > 0
                      for c in safety_violation_rate(rows, "pbft", n).values()))
    note = ("PBFT recovers liveness above 1/3 via an UNSAFE fork "
            "(success_rate back to 1.0 at phi>=0.40); see the paired safety row"
            if broken else "")
    return FMaxRow(family=family, metric="liveness",
                   invariant="termination (success_rate>=1)", protocol=protocol,
                   n=n, f_max_hold=hold if hold is not None else float("nan"),
                   f_max_break=brk, f_max_count=count, f_max_stake=stake,
                   theoretical_bound="", safety_broken=broken, note=note)


_RANK_FIELDS = ("family", "metric", "invariant", "protocol", "n",
                "f_max_hold", "f_max_break", "f_max_count", "f_max_stake",
                "theoretical_bound", "safety_broken", "note")


def build_ranking(rows) -> list:
    out = []
    for family in ("delay", "offline", "equivocate"):
        for proto in PROTO_ORDER:
            for n in NS:
                if liveness_rate(rows, family, proto, n):
                    out.append(_liveness_fmax(rows, family, proto, n))
    for proto in PROTO_ORDER:
        for n in NS:
            if _equiv_cell(rows, proto, n, "safety_violation"):
                out.append(f_max_for(rows, "safety", proto, n))
    nwt = nwt_invariant()
    for n in NS:
        out.append(FMaxRow("equivocate", "safety", nwt["invariant"],
                           "narwhal-tusk", n, float("nan"), None,
                           float("nan"), float("nan"), "< n/3 (count)", False,
                           nwt["note"]))
    return out


def _cell(v):
    """Deterministic CSV cell rendering (None break -> empty string)."""
    return "" if v is None else v


def write_ranking_csv(path: str = RANKING_CSV,
                      adversary_dir: str = ADVERSARY_DIR) -> str:
    rows = build_ranking(load_adversary_rows(adversary_dir))
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_RANK_FIELDS)
        for r in rows:
            w.writerow([_cell(getattr(r, fld)) for fld in _RANK_FIELDS])
    return path


_EPS_FIELDS = ("n", "K", "alpha_c", "beta", "empirical_rate",
               "empirical_wilson_hi", "analytical_bound", "n_obs")


def write_epsilon_witness_csv(path: str = EPSILON_CSV,
                              adversary_dir: str = ADVERSARY_DIR) -> str:
    rows = load_adversary_rows(adversary_dir)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(_EPS_FIELDS)
        for n in NS:
            wt = snowman_epsilon_witness(rows, n)
            if wt:
                w.writerow([getattr(wt, fld) for fld in _EPS_FIELDS])
    return path


def main() -> None:
    print("wrote", write_ranking_csv())
    print("wrote", write_epsilon_witness_csv())


if __name__ == "__main__":
    main()
