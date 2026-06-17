"""Family C withhold-participation (offline-validators) configuration (T52).

Offline has NO magnitude axis (binary skip). The intensity grid is per-protocol:
PBFT and Casper FFG cross the 1/3 liveness cliff with an above-threshold f=0.40
point; Snowman stops at 0.33 (proportional degradation, no sharp cliff) — design §2.
WINDOW_S / BUFFER_S / PBFT_VC_DELAY_S are PROBE-SET in Task 5 (re-probed for the
offline stall + view-change regime, not inherited from T51 — design §6).
"""
from __future__ import annotations

# Shared simulator knobs (timeline, cadence, protocol knobs, workload) — reuse
# T51's values unchanged; only the swept axes + calibration differ.
from .config import (STATIC_BASELINE, REF_S, PBFT_PROPOSE_DELAY_S,
                     SNOWMAN_SLOT_DURATION_S, SNOWMAN_BETA, FFG_SLOT_DURATION_S,
                     FFG_SLOTS_PER_EPOCH, ARRIVAL_PROCESS, OFFERED_RATE,
                     TX_BYTES, CONFLICT_RATE)

N_VALUES: tuple[int, ...] = (10, 25)
SEEDS: tuple[int, ...] = tuple(range(20))

# Per-protocol offline-fraction grid (f=0 is the honest control).
F_VALUES: dict[str, tuple[float, ...]] = {
    "pbft":       (0.0, 0.10, 0.20, 0.33, 0.40),
    "casper-ffg": (0.0, 0.10, 0.20, 0.33, 0.40),
    "snowman":    (0.0, 0.10, 0.20, 0.33),
}

# --- Window / buffer / view-change calibration (PROBE-SET 2026-06-17). ----
# Re-probed for the OFFLINE stall regime WITH the Snowman query timeout active
# (15 s, below), single-process, static-baseline (10 ms delay). The offline grid
# has a hard finalize/stall boundary per protocol; calibration is sized off the
# SLOWEST FINALIZING cell, not the stalled cells (which produce no decisions).
#
# Per-(protocol, n) finalize/stall map (seeds 0–2), first-decision latency of
# the finalizing cells:
#   PBFT       n=10: finalizes f≤0.33 (1.03 s); STALLS f=0.40 (61 view-changes)
#   PBFT       n=25: finalizes f≤0.33 (1.03 s); STALLS f=0.40 (151 view-changes)
#   Casper FFG n=10: finalizes f≤0.33 (0.51 s); STALLS f=0.40 (0 view-changes)
#   Casper FFG n=25: finalizes f≤0.33 (0.51 s); STALLS f=0.40 (0 view-changes)
#   Snowman    n=10: finalizes f≤0.10 (1.30 s); STALLS f≥0.20  → boundary f*=0.20
#   Snowman    n=25: finalizes f≤0.20;          STALLS f=0.33  → boundary f*=0.33
#     Snowman n=25 f=0.20 first-decision: 36.31 / 44.31 / 23.35 s (seeds 0/1/2).
# Snowman's boundary now sits where responders drop below alpha_c (≈0.8·K): at
# n=10 (K=9, alpha_c=8) one offline node (f≥0.20 ⇒ ⌊0.20·10⌋=2) already prevents
# alpha_c, so f≥0.20 stalls; at n=25 (K=20, alpha_c=16) it takes ⌊0.33·25⌋=8
# offline to stall, so f=0.20 (5 offline) still finalizes (slowly). The timeout
# is what lets the slow-but-finalizing n=25 f=0.20 cell close rounds at all
# (without it those polls waited forever).
#
# WINDOW_S — must be ≥ the slowest *finalizing* first-decision latency in the
# whole grid: 44.31 s (Snowman n=25, f=0.20, seed 1). 150 s gives a 3.4× margin,
# so the headline finality_delay (first in-window decision) is well-defined for
# every finalizing cell. Clip is REPORTED not guarded (human 2026-06-15, T47
# Option-B precedent): the worst Snowman finalizing cell spills a long block tail
# past W (single blocks finalize out to the horizon ~229 s) — that spill is a
# degradation signal, not noise to engineer away.
WINDOW_S: float = 150.0
# BUFFER_S — must let an instance started just before W still finalize one block
# in-run. Worst single-block finalization under attack: the max gap between
# consecutive Snowman block decisions in the slowest finalizing cell is ~40 s
# (n=25 f=0.20 seed 2) and the worst first-block is 44.31 s. 80 s ≥ that with
# ~1.8× margin; PBFT/FFG finalize in ≤1.03 s so they are never buffer-bound.
BUFFER_S: float = 80.0
T_MAX: float = WINDOW_S + BUFFER_S
# PBFT_VC_DELAY_S — kept realistic (≈3× the 1.03 s honest round). Probe confirms
# it FIRES exactly at the offline cliff: f≤0.33 finalizes with 0 view-changes
# (honest quorum met without the offline backups), f=0.40 drives 61 (n=10) / 151
# (n=25) view-changes as the primary's quorum can no longer be reached. The
# firing at f=0.40 is the headline PBFT finding, so vc_delay must be small enough
# to actually trigger — 3.0 s does.
PBFT_VC_DELAY_S: float = 3.0
# ONE_ROUND_S — per-protocol clip scope bound ("instance started in [0,W]").
# PBFT/FFG finalize a round in ≈1.03 s / ≈0.51 s (scope bound 2 s covers them).
# Snowman's worst single-block finalization under attack is 44.31 s (first
# decision) / ~40 s (max inter-block gap), so 72 s keeps those crippled-but-
# finalizing blocks in-scope (their inflated latency IS the headline, not a
# "late" instance to drop).
ONE_ROUND_S: dict[str, float] = {"pbft": 2.0, "casper-ffg": 2.0, "snowman": 72.0}

# Query-response timeout for Snowman polls. Set above T51's max injected delay
# (10 s = mult 10 × ref 1 s) so a delayed-but-responsive validator still answers
# before the timeout — the timeout is a no-op for responsive nodes and only
# triggers for non-responding (offline) ones, keeping the delay (T51) and
# withhold (T52) adversary families distinct.
SNOWMAN_QUERY_TIMEOUT_S: float = 15.0
