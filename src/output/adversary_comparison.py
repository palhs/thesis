"""T55 — adversarial comparison tables + robustness ranking.

Synthesizes the three Family-C adversarial sweeps into the cross-protocol
comparison Chapter 4 §4.4 (T56) draws on:

- results/adversary/delayed_voters.csv      (T51 delay-emission)
- results/adversary/offline_validators.csv  (T52 withhold-participation)
- results/adversary/equivocating_nodes.csv  (T53 equivocate-vote)

Two byte-stable CSVs land under results/adversary/:

- ``adversary_comparison.csv`` — the algorithm x adversary x metric summary
  (tidy long-format: one row per (adversary, protocol, n, metric)).
- ``robustness_ranking.csv`` — the per-(adversary, n) protocol ranking.

This is the Family-C analog of T48's ``delay_analysis.py``. It REUSES the T54
``f_max`` brackets (``output.adversary_analysis``, the same values committed to
``degradation_ranking.csv``) and adds reducers for the per-adversary headline
MAGNITUDES that the bracket CSV omits — Snowman's finality blow-up under delay,
the throughput decay under withholding, and PBFT's fork-cliff
``conflicting_instances`` under equivocation. Pure-stdlib, no matplotlib
(headless-testable); no new simulation runs. Liveness Wilson bands are surfaced
via ``adversary_analysis.liveness_rate``.

Ranking methodology (human-locked 2026-06-19, see
[[experiments/2026-06-19_adversary-comparison]]):

- Per adversary, per committee size ``n``, on the invariant that adversary
  actually breaks. The ranking key (``ranked_on`` / ``rank_value`` columns):
    * delay-emission -> ``liveness_f_max_hold`` (largest phi with full liveness).
      Delay causes no liveness COLLAPSE in the grid (worst FFG ~0.6, never 0),
      so the onset hold is the only liveness signal; the finality blow-up breaks
      ties (PBFT immune vs Snowman tens-of-x).
    * withhold-participation -> ``liveness_survival_phi`` (deepest phi still
      finalizing at all, success_rate > 0): the genuine liveness-robustness
      boundary, mirroring T48's survival-depth. Ranking on the full-liveness
      ONSET would rank a gracefully-degrading protocol (FFG) below a
      perfect-then-cliff one (Snowman) even though FFG survives deeper — so the
      survival boundary is used and the onset bracket is carried for context.
    * equivocate-vote -> ``safety_f_max_hold`` (where safety, not liveness, is
      the threat; ``fork_rate`` is 0 below threshold for the others).
- A right-censored hold (never breaks in the grid) ranks above a finite one.
  ``n=10`` and ``n=25`` are reported unpooled. ``tie`` flags protocols that
  share the ranking-key value; the order *within* a tie is set by the signature
  magnitude (lower finality blow-up / higher surviving throughput / fewer
  conflicting instances), named in the row's ``note`` — distinct from T48's
  CI-overlap tie, because these axes are discrete with seed-deterministic
  safety, not smooth retention curves with a CI.
- The PBFT equivocate liveness "recovery" above 1/3 is an UNSAFE fork
  (``safety_broken``), so liveness is reported jointly with safety and never
  read as resilience. **No protocol dominates across all three adversaries** —
  that cross-adversary tradeoff is the RQ4 finding this table makes explicit.

Count-vs-stake fault attribution (``f_max_count`` for PBFT / Snowman, stake for
Casper FFG) is carried as the ``accounting`` axis so the comparison is honest
about not being apples-to-apples across that boundary. Narwhal+Tusk's three
generic-capability pairs are unimplemented (T38.1, sequenced post-T55) and
appear as explicit deferral rows, never a silent NaN
([[concepts/output-format]] §4). The metric named throughout is the
"safety-violation rate" (the literal CSV column is still ``fork_rate`` pending
its rename); ``fork_rate`` is never introduced here as a concept name.
"""
from __future__ import annotations

import csv
import math
import os
from collections import defaultdict
from dataclasses import dataclass

from output import adversary_analysis as aa
from output.adversary_analysis import load_adversary_rows

ADVERSARY_DIR = "results/adversary"
COMPARISON_CSV = "results/adversary/adversary_comparison.csv"
RANKING_CSV = "results/adversary/robustness_ranking.csv"

PROTO_ORDER = ("pbft", "casper-ffg", "snowman")
NS = (10, 25)
PHI = "byzantine_fraction"

# family tag (in the loaded rows) -> the adversary capability label.
ADVERSARIES = ("delay", "offline", "equivocate")
ADVERSARY_LABEL = {
    "delay": "delay-emission",
    "offline": "withhold-participation",
    "equivocate": "equivocate-vote",
}
# what the per-adversary ranking is keyed on (see module docstring).
RANKED_ON = {
    "delay": "liveness_f_max_hold",
    "offline": "liveness_survival_phi",
    "equivocate": "safety_f_max_hold",
}

_NAN = float("nan")


def _fnum(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _accounting(protocol: str) -> str:
    """Fault-attribution model: count (replicas/validators) vs stake."""
    return "stake" if protocol == "casper-ffg" else "count"


# --------------------------------------------------------------------------- #
# Per-adversary headline magnitude reducers (what the bracket CSV omits)
# --------------------------------------------------------------------------- #

def delay_finality_blowup(rows, protocol, n) -> float:
    """Worst per-(phi, delay_mult)-cell mean ``finality_delay_ratio`` over the
    adversarial cells (phi > 0), NaN-skipped.

    The signature delay-emission weakness. NaN-skip is load-bearing: Casper FFG
    carries ``finality_delay_ratio = NaN`` on failed runs, so a naive pooled
    mean is NaN; every *successful* FFG run is exactly 1.0 (its degradation is
    liveness, not finality). PBFT is 1.0 (immune); Snowman blows up to tens of x
    (sequential K-poll over slow responders).
    """
    buckets: dict[tuple, list[float]] = defaultdict(list)
    for r in rows:
        if (r["family"] != "delay" or r["protocol"] != protocol
                or int(r["n"]) != n):
            continue
        if _fnum(r[PHI]) <= 0.0:
            continue
        key = (round(_fnum(r[PHI]), 4), round(_fnum(r.get("delay_mult", "nan")), 4))
        v = _fnum(r["finality_delay_ratio"])
        if not math.isnan(v):
            buckets[key].append(v)
    cell_means = [sum(v) / len(v) for v in buckets.values() if v]
    return max(cell_means) if cell_means else float("nan")


def delay_min_success(rows, protocol, n) -> tuple[float, float, float]:
    """``(min_success_rate, wilson_lo, wilson_hi)`` over the adversarial cells.

    Pools over the delay magnitude axis at each phi (the liveness pattern is
    m-invariant), then takes the worst (lowest) cell. PBFT / Snowman stay 1.0;
    FFG dips (proposer-rotation overlap). The Wilson band is that worst cell's.
    """
    cells = aa.liveness_rate(rows, "delay", protocol, n)
    adv = [c for phi, c in cells.items() if phi > 0.0]
    if not adv:
        return (float("nan"), float("nan"), float("nan"))
    worst = min(adv, key=lambda c: (c.mean, c.phi))   # phi breaks mean ties
    return (worst.mean, worst.lo, worst.hi)


def survival_phi(rows, family, protocol, n) -> float:
    """Deepest fault fraction still finalizing at all (mean success_rate > 0).

    The liveness survival/collapse boundary (the analog of T48's survival-depth).
    Under withholding PBFT / FFG reach the 1/3 quorum cliff (0.40); Snowman
    cliffs earlier and n-dependently (alpha_c starvation). Under delay nothing
    collapses, so this saturates at the grid maximum.
    """
    cells = aa.liveness_rate(rows, family, protocol, n)
    alive = [phi for phi, c in cells.items() if c.mean > 0.0]
    return max(alive) if alive else 0.0


def offline_survival_phi(rows, protocol, n) -> float:
    """``survival_phi`` for the withhold-participation family (kept as a named
    public reducer for the comparison table + tests)."""
    return survival_phi(rows, "offline", protocol, n)


def offline_worst_surviving_throughput(rows, protocol, n) -> float:
    """Lowest mean ``throughput_ratio`` over cells that still finalize.

    PBFT holds 1.0 to the cliff; FFG decays ~ (1 - phi); Snowman exposes the
    n=25 phi=0.20 starvation case (alive but throughput ~ 0.4% of baseline).
    """
    buckets: dict[float, list[float]] = defaultdict(list)
    succ: dict[float, list[float]] = defaultdict(list)
    for r in rows:
        if (r["family"] != "offline" or r["protocol"] != protocol
                or int(r["n"]) != n):
            continue
        phi = round(_fnum(r[PHI]), 4)
        if phi <= 0.0:
            continue
        buckets[phi].append(_fnum(r["throughput_ratio"]))
        succ[phi].append(_fnum(r["success_rate"]))
    surviving = []
    for phi, tr in buckets.items():
        s = [v for v in succ[phi] if not math.isnan(v)]
        if s and sum(s) / len(s) > 0.0:           # the cell still finalizes
            finite = [v for v in tr if not math.isnan(v)]
            if finite:
                surviving.append(sum(finite) / len(finite))
    return min(surviving) if surviving else float("nan")


def _equiv_max(rows, protocol, n, metric) -> float:
    """Max of a seed-invariant equivocate column over the phi grid."""
    vals = [_fnum(r[metric]) for r in rows
            if r["family"] == "equivocate" and r["protocol"] == protocol
            and int(r["n"]) == n]
    finite = [v for v in vals if not math.isnan(v)]
    return max(finite) if finite else float("nan")


def equiv_max_conflicting(rows, protocol, n) -> float:
    """Peak ``conflicting_instances`` (PBFT 229 at the fork cliff; FFG / Snowman 0)."""
    return _equiv_max(rows, protocol, n, "conflicting_instances")


def equiv_max_slashable(rows, protocol, n) -> float:
    """Peak ``max_slashable_stake_fraction`` (FFG ~0.5; PBFT / Snowman 0)."""
    return _equiv_max(rows, protocol, n, "max_slashable_stake_fraction")


# --------------------------------------------------------------------------- #
# Comparison table (algorithm x adversary x metric, tidy long-format)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ComparisonRow:
    adversary: str       # delay-emission / withhold-participation / equivocate-vote
    protocol: str
    n: int
    metric: str
    value: object        # float, or None for a right-censored / deferred cell
    ci_lo: float         # Wilson band for rate metrics; NaN otherwise
    ci_hi: float
    accounting: str      # count / stake (for f_max metrics) else ""
    unit: str            # fraction / ratio / rate / count / bool
    note: str


_NWT_NOTE = "NWT unimplemented; deferred to T38.1 (3 generic-capability pairs)"


def _cmp_rows_for_cell(rows, adversary, protocol, n) -> list[ComparisonRow]:
    """The metric rows for one measured (adversary, protocol, n) cell."""
    label = ADVERSARY_LABEL[adversary]
    acct = _accounting(protocol)
    out: list[ComparisonRow] = []

    def add(metric, value, unit, note="", ci=(_NAN, _NAN), accounting=""):
        out.append(ComparisonRow(label, protocol, n, metric, value,
                                  ci[0], ci[1], accounting, unit, note))

    if adversary in ("delay", "offline"):
        live = aa._liveness_fmax(rows, adversary, protocol, n)
        add("liveness_f_max_hold", live.f_max_hold, "fraction",
            "largest phi with full liveness (success_rate>=1)", accounting=acct)
        add("liveness_f_max_break", live.f_max_break, "fraction",
            "first phi with any liveness loss", accounting=acct)

    if adversary == "delay":
        add("worst_finality_delay_ratio", delay_finality_blowup(rows, protocol, n),
            "ratio", "max cell-mean time-to-finality vs the f=0 control")
        mn, lo, hi = delay_min_success(rows, protocol, n)
        add("min_success_rate", mn, "rate",
            "worst pooled liveness over phi>0", ci=(lo, hi))

    elif adversary == "offline":
        add("liveness_survival_phi", offline_survival_phi(rows, protocol, n),
            "fraction", "deepest phi still finalizing at all (success_rate>0)",
            accounting=acct)
        add("worst_surviving_throughput_ratio",
            offline_worst_surviving_throughput(rows, protocol, n), "ratio",
            "lowest throughput vs control among surviving cells")

    elif adversary == "equivocate":
        safe = aa.f_max_for(rows, "safety", protocol, n)
        add("safety_f_max_hold", safe.f_max_hold, "fraction",
            safe.invariant, accounting=acct)
        add("safety_f_max_break", safe.f_max_break, "fraction",
            "first phi the safety invariant breaks", accounting=acct)
        live = aa.f_max_for(rows, "liveness", protocol, n)
        add("liveness_f_max_hold", live.f_max_hold, "fraction",
            live.note or "paired liveness (report jointly with safety)",
            accounting=acct)
        add("safety_broken", 1.0 if safe.safety_broken else 0.0, "bool",
            "an unsafe-fork / >=1/3-slashable phi region exists")
        add("conflicting_instances_max", equiv_max_conflicting(rows, protocol, n),
            "count", "peak two-honest conflicting commits (PBFT fork cliff)")
        add("max_slashable_stake_max", equiv_max_slashable(rows, protocol, n),
            "fraction", "peak economically-slashable stake (FFG accountable safety)")
    return out


def _nwt_cmp_row(adversary, n) -> ComparisonRow:
    metric = ("safety_f_max_hold" if adversary == "equivocate"
              else "liveness_survival_phi" if adversary == "offline"
              else "liveness_f_max_hold")
    return ComparisonRow(ADVERSARY_LABEL[adversary], "narwhal-tusk", n, metric,
                         None, _NAN, _NAN, "count", "fraction", _NWT_NOTE)


def build_comparison(rows) -> list[ComparisonRow]:
    out: list[ComparisonRow] = []
    for adversary in ADVERSARIES:
        for proto in PROTO_ORDER:
            for n in NS:
                if aa.liveness_rate(rows, adversary, proto, n):
                    out.extend(_cmp_rows_for_cell(rows, adversary, proto, n))
        for n in NS:
            out.append(_nwt_cmp_row(adversary, n))
    return out


# --------------------------------------------------------------------------- #
# Robustness ranking (per adversary, per n)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RankRow:
    adversary: str
    rank: object         # 1..k for measured protocols; "" for the deferred NWT row
    tie: bool            # shares the ranking-key value with another row
    protocol: str
    n: int
    ranked_on: str       # liveness_f_max_hold / liveness_survival_phi / safety_f_max_hold
    rank_value: float    # the ranking-key value (higher = more robust)
    f_max_hold: float    # onset / safety hold (from the T54 bracket)
    f_max_break: object  # onset / safety break; None if right-censored
    survival_phi: float  # deepest phi still finalizing; NaN for equivocate
    accounting: str      # count / stake
    signature_metric: str
    signature_value: float
    safety_broken: bool
    note: str


# tiebreak: (signature metric, +1 = lower is better / -1 = higher is better)
_SIGNATURE = {
    "delay": ("worst_finality_delay_ratio", +1.0),
    "offline": ("worst_surviving_throughput_ratio", -1.0),
    "equivocate": ("conflicting_instances_max", +1.0),
}


def _signature_value(rows, adversary, protocol, n) -> float:
    if adversary == "delay":
        return delay_finality_blowup(rows, protocol, n)
    if adversary == "offline":
        return offline_worst_surviving_throughput(rows, protocol, n)
    return equiv_max_conflicting(rows, protocol, n)


def _fmax_for_rank(rows, adversary, protocol, n):
    if adversary == "equivocate":
        return aa.f_max_for(rows, "safety", protocol, n)
    return aa._liveness_fmax(rows, adversary, protocol, n)


def ranking_for(rows, adversary, n) -> list[RankRow]:
    """Rank the three measured protocols for one (adversary, n), then append the
    deferred Narwhal+Tusk row.

    Key: delay / equivocate sort on ``f_max_hold`` (right-censored break ranks
    above finite, then the signature tiebreak); withholding sorts on the
    survival boundary, then the signature. ``tie`` marks a shared ranking-key
    value.
    """
    sig_metric, sig_dir = _SIGNATURE[adversary]
    recs = []
    for proto in PROTO_ORDER:
        fm = _fmax_for_rank(rows, adversary, proto, n)
        if math.isnan(fm.f_max_hold):
            continue
        surv = (survival_phi(rows, adversary, proto, n)
                if adversary != "equivocate" else float("nan"))
        sig = _signature_value(rows, adversary, proto, n)
        rank_value = surv if adversary == "offline" else fm.f_max_hold
        brk_rank = math.inf if fm.f_max_break is None else float(fm.f_max_break)
        sig_sort = sig_dir * (sig if not math.isnan(sig) else 0.0)
        if adversary == "offline":          # no censoring term — survival is the key
            sort_key = (-rank_value, sig_sort)
        else:                               # hold, then right-censored-is-better, then sig
            sort_key = (-rank_value, -brk_rank, sig_sort)
        recs.append({
            "proto": proto, "fm": fm, "surv": surv, "sig": sig,
            "rank_value": rank_value, "sort_key": sort_key,
        })
    recs.sort(key=lambda r: r["sort_key"])

    keyvals = [r["rank_value"] for r in recs]
    out: list[RankRow] = []
    for i, r in enumerate(recs):
        fm = r["fm"]
        shared = sum(1 for v in keyvals if abs(v - r["rank_value"]) < 1e-9) > 1
        out.append(RankRow(
            adversary=ADVERSARY_LABEL[adversary], rank=i + 1, tie=shared,
            protocol=r["proto"], n=n, ranked_on=RANKED_ON[adversary],
            rank_value=r["rank_value"], f_max_hold=fm.f_max_hold,
            f_max_break=fm.f_max_break, survival_phi=r["surv"],
            accounting=_accounting(r["proto"]),
            signature_metric=sig_metric, signature_value=r["sig"],
            safety_broken=fm.safety_broken,
            note=_rank_note(adversary, r, shared, sig_metric)))
    out.append(RankRow(
        adversary=ADVERSARY_LABEL[adversary], rank="", tie=False,
        protocol="narwhal-tusk", n=n, ranked_on=RANKED_ON[adversary],
        rank_value=_NAN, f_max_hold=_NAN, f_max_break=None, survival_phi=_NAN,
        accounting="count", signature_metric=sig_metric, signature_value=_NAN,
        safety_broken=False, note=_NWT_NOTE))
    return out


def _rank_note(adversary, r, shared, sig_metric) -> str:
    fm, sig = r["fm"], r["sig"]
    if adversary == "equivocate":
        if fm.f_max_break is None:
            base = "safety holds through the grid (probabilistic; see epsilon witness)"
        elif sig and sig > 0:
            base = "deterministic fork above threshold (unaccountable)"
        else:
            base = "accountable safety: >=1/3 stake becomes slashable above threshold"
    elif adversary == "delay":
        base = ("immune" if sig <= 1.0 + 1e-9
                else f"survives but time-to-finality x{sig:.0f}")
    else:  # offline: keyed on survival depth, onset reported as context
        if sig >= 1.0 - 1e-9:
            base = f"no degradation below the quorum cliff (survives to phi={r['surv']:.2f})"
        else:
            onset = "" if math.isnan(fm.f_max_hold) else f" from phi={fm.f_max_break}"
            base = (f"degrades (throughput x{sig:.2f}){onset} but survives to "
                    f"phi={r['surv']:.2f}")
    if shared:
        base += f"; tied on {RANKED_ON[adversary]}, ordered by {sig_metric}"
    return base


def build_ranking(rows) -> list[RankRow]:
    out: list[RankRow] = []
    for adversary in ADVERSARIES:
        for n in NS:
            out.extend(ranking_for(rows, adversary, n))
    return out


# --------------------------------------------------------------------------- #
# CSV writers (byte-stable: pure read -> compute -> write)
# --------------------------------------------------------------------------- #

def _cell(v):
    """Deterministic CSV cell rendering (None -> empty string)."""
    return "" if v is None else v


_CMP_FIELDS = ("adversary", "protocol", "n", "metric", "value",
               "ci_lo", "ci_hi", "accounting", "unit", "note")
_RANK_FIELDS = ("adversary", "rank", "tie", "protocol", "n", "ranked_on",
                "rank_value", "f_max_hold", "f_max_break", "survival_phi",
                "accounting", "signature_metric", "signature_value",
                "safety_broken", "note")


def _write_csv(path, fields, records) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(fields)
        for r in records:
            w.writerow([_cell(getattr(r, fld)) for fld in fields])
    return path


def write_comparison_csv(path: str = COMPARISON_CSV,
                         adversary_dir: str = ADVERSARY_DIR) -> str:
    return _write_csv(path, _CMP_FIELDS,
                      build_comparison(load_adversary_rows(adversary_dir)))


def write_ranking_csv(path: str = RANKING_CSV,
                      adversary_dir: str = ADVERSARY_DIR) -> str:
    return _write_csv(path, _RANK_FIELDS,
                      build_ranking(load_adversary_rows(adversary_dir)))


def main() -> None:
    print("wrote", write_comparison_csv())
    print("wrote", write_ranking_csv())
    rows = load_adversary_rows()
    for adversary in ADVERSARIES:
        for n in NS:
            print(f"\n=== {ADVERSARY_LABEL[adversary]} | n={n} "
                  f"(rank by {RANKED_ON[adversary]}) ===")
            for r in ranking_for(rows, adversary, n):
                if r.rank == "":
                    print(f"  [deferred] {r.protocol:12s} {r.note}")
                    continue
                t = " (tie)" if r.tie else ""
                print(f"  #{r.rank}{t} {r.protocol:11s} "
                      f"{r.ranked_on}={r.rank_value:.2f} [{r.accounting}] "
                      f"{r.signature_metric}={r.signature_value:.3g}"
                      f"{'  SAFETY-BROKEN' if r.safety_broken else ''}")


if __name__ == "__main__":
    main()
