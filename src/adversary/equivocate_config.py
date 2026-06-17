"""Family C equivocate-vote (T53) configuration.

The equivocating adversary forks conflicting payloads from the low-id Byzantine
prefix (byzantine_node_ids). The per-protocol intensity grid runs PBFT and
Casper FFG ABOVE the 1/3 fault threshold (f=0.40, 0.50) to expose the safety
cliff — equivocation above f>1/3 lets the Byzantine set forge conflicting
quorums / double-finalise. Snowman stops at 0.33 (liveness-only: a lying
responder can stall progress but there is no fork surface to break safety, so
sweeping above 1/3 buys no new signal) — design §2.

Calibration constants are PROBE-VERIFIED in Task 10 (see the calibration block
below). The static-baseline timeline (10 ms, loss-free) and the Snowman query
timeout are identical to T52, so the T52 values were expected to hold; the probe
confirms every FINALIZING cell decides well inside WINDOW_S in the equivocation
regime, so the values are carried over unchanged.
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

# Per-protocol Byzantine-fraction grid (f=0 is the honest control). PBFT/FFG
# run through above-1/3 (0.40, 0.50) to expose the safety cliff; Snowman stops
# at 0.33 (liveness-only, no fork surface) — design §2.
F_VALUES: dict[str, tuple[float, ...]] = {
    "pbft":       (0.0, 0.10, 0.20, 0.33, 0.40, 0.50),
    "casper-ffg": (0.0, 0.10, 0.20, 0.33, 0.40, 0.50),
    "snowman":    (0.0, 0.10, 0.20, 0.33),
}

# --- Window / buffer / view-change calibration (PROBE-VERIFIED 2026-06-18). ---
# Probed in the EQUIVOCATION regime (static baseline: 10 ms delay, loss-free,
# single-process; Snowman query timeout active at 15 s, below) via the sweep's
# pure _run_cell at a representative f-spread, n∈{10,25}, seed 0. The static
# timeline and the Snowman timeout are byte-identical to T52, so the T52 values
# were expected to hold — and the probe confirms it: every FINALIZING cell's
# first-decision (commit_latency_ms) sits far inside WINDOW_S. Unlike the offline
# regime there is no finalize/stall boundary here — every cell decides; the
# headline is the per-cell SAFETY signal, not a stall.
#
# Per-(protocol, n) first-decision latency from the probe (commit_latency_ms,
# seed 0):
#   PBFT       n=10: f≤0.20 1.03 s; f=0.33 4.05 s (10 view-changes); f≥0.40 1.03 s
#   PBFT       n=25: f≤0.20 1.03 s; f=0.33 4.05 s (25 view-changes); f≥0.40 1.03 s
#   Casper FFG n=10/25: 0.51 s at every f (equivocation does not slow finality)
#   Snowman    n=10/25: 1.31 s at every f (clip tail ~32.6% — degradation, below)
# Slowest finalizing cell in the whole probe: PBFT f=0.33 at 4.05 s — the
# view-change path closes the round under the Byzantine-prefix split before the
# honest 2f+1 quorum re-forms. 4.05 s ≪ 150 s (37× margin), so no finalizing cell
# is ever clipped out and finality_delay is well-defined everywhere.
#
# Cliff/safety signals confirmed by the probe (the headline, not calibration):
#   PBFT  safety_violation True at f≥0.40, False at f≤0.33 — the conflicting-
#         quorum fork opens exactly above 1/3, as designed.
#   FFG   max_slashable_stake_fraction grows with f and crosses 1/3 by f=0.50
#         (0.30→0.50 at n=10, 0.32→0.48 at n=25); safety_violation stays False
#         because FFG books equivocation as slashable stake, not a live fork.
#   Snowman safety_violation False at every f — a lying responder can stall but
#         has no fork surface to break safety.
#
# WINDOW_S — must be ≥ the slowest *finalizing* first-decision latency in the
# grid: 4.05 s (PBFT f=0.33). 150 s gives a ~37× margin, so the headline
# finality_delay (first in-window decision) is well-defined for every cell. Clip
# is REPORTED not guarded (human 2026-06-15, T47 Option-B precedent): Snowman's
# long block tail (~32.6% clipped) is a degradation signal, not noise.
WINDOW_S: float = 150.0
# BUFFER_S — lets an instance started just before W still finalize one block
# in-run. Worst single-block finalization under equivocation is PBFT's 4.05 s
# view-change round; Snowman blocks decide in 1.31 s. 80 s clears all of these
# with a wide margin (no cell is buffer-bound in this regime).
BUFFER_S: float = 80.0
T_MAX: float = WINDOW_S + BUFFER_S
# PBFT_VC_DELAY_S — kept realistic (≈3× the 1.03 s honest round). The probe shows
# it FIRES at the equivocation split: f=0.33 drives 10 (n=10) / 25 (n=25) view-
# changes and finalizes at 4.05 s; f≤0.20 finalizes with 0 view-changes; f≥0.40
# crosses into the safety-violation regime (the fork is the headline there, not a
# stall). 3.0 s is small enough to actually trigger at f=0.33, so the view-change
# path is exercised.
PBFT_VC_DELAY_S: float = 3.0
# ONE_ROUND_S — per-protocol clip scope bound ("instance started in [0,W]").
# PBFT/FFG finalize a round in ≤4.05 s / 0.51 s (scope bound 2 s covers the
# honest round; the f=0.33 view-change round is in-window regardless). Snowman's
# blocks decide in 1.31 s but spill a long tail; 72 s keeps the crippled-but-
# finalizing blocks in-scope (their inflated latency IS the degradation headline).
ONE_ROUND_S: dict[str, float] = {"pbft": 2.0, "casper-ffg": 2.0, "snowman": 72.0}
# Query-response timeout for Snowman polls. Identical to T52: set above T51's max
# injected delay (10 s) so a delayed-but-responsive validator still answers before
# the timeout. In the equivocation regime the timeout is a no-op for responsive
# nodes and bounds polls against a non-answering (equivocating-then-silent) one.
SNOWMAN_QUERY_TIMEOUT_S: float = 15.0
