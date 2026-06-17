"""Family C delay-emission (delayed-voters) configuration (T51).

Family C fixes the network at a constant low delay (the "static-baseline"
timeline) and sweeps the ADVERSARY axes: intensity f (fraction of slow nodes)
and magnitude m (the fixed delay multiple of each protocol's round cadence).
All delay values are SECONDS of simulator model time (the unit the baselines
use: slot_duration = 1.0 s ⇒ commit_latency ≈ 1000 ms).

The WINDOW_S / BUFFER_S / PBFT_VC_DELAY_S constants are PROBE-SET: a later
task's `sweep.py --probe` prints first-decision latency, clip fraction, and
PBFT view-change count, after which these three are finalised. The values
below are the pre-probe defaults; the experiment page records the confirmed
numbers.

Design contract: docs/superpowers/specs/2026-06-14-t51-delayed-voters-design.md
                 wiki/experiments/2026-06-14_delayed-voters.md
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from network import DelayDist, Phase

# --- Swept adversary axes (human 2026-06-14). ----------------------------
# f = 0.00 is the honest CONTROL (0 slow nodes, no magnitude). m applies only
# to f > 0 cells. n=10 → {0,1,2,3} slow; n=25 → {0,2,5,7} slow (floor).
N_VALUES: tuple[int, ...] = (10, 25)
F_VALUES: tuple[float, ...] = (0.0, 0.10, 0.20, 0.30)
M_VALUES: tuple[float, ...] = (2.0, 4.0, 6.0, 8.0, 10.0)
SEEDS: tuple[int, ...] = tuple(range(20))

# --- Per-protocol round cadence ref (shift = m·ref). ---------------------
# PBFT propose cadence and Snowman slot cadence are the native 1.0 s. Casper
# FFG's slot is 0.1 s (default); static-baseline E[delay]=10 ms satisfies the
# §5 coherence rule slot ≥ 4·E[delay] = 40 ms. The FFG cadence asymmetry
# (shorter ref ⇒ smaller absolute shift) is a real finding, reported (spec §5).
REF_S: dict[str, float] = {
    "pbft":       1.0,
    "snowman":    1.0,
    "casper-ffg": 0.1,
}

# --- Per-protocol protocol knobs. ----------------------------------------
PBFT_PROPOSE_DELAY_S: float = 1.0
SNOWMAN_SLOT_DURATION_S: float = 1.0
SNOWMAN_BETA: int = 15
FFG_SLOT_DURATION_S: float = 0.1
FFG_SLOTS_PER_EPOCH: int = 2

# --- Window / buffer / view-change calibration (PROBE-SET 2026-06-15). ----
# Family C runs on the fast static-baseline (10 ms delay). Probe (worst attack
# f=0.30, m=10): first-finality is 1.03 s (PBFT, unchanged — honest quorum of 7
# is met without the ≤3 slow backups), 0.51 s (Casper FFG), but 71 s for
# Snowman at n=10 / 61 s at n=25 (β=15 sequential polls repeatedly sampling a
# slow responder). WINDOW_S=150 captures every protocol's worst first-finality
# with margin, so the headline finality_delay_ratio (first in-window decision)
# is well-defined for every cell. Per the human 2026-06-15 decision the clip is
# REPORTED, not guarded at <5% (the T47 Option-B precedent): Snowman's heavily
# attacked cells spill a large finalization tail past W (~37% at m=10) that no
# tractable window removes, and that spill is itself a degradation signal.
# BUFFER_S=80 ≥ one full Snowman block-finalization under the worst attack
# (~71 s), so an instance started just before W can still finalize in-run.
WINDOW_S: float = 150.0
BUFFER_S: float = 80.0
T_MAX: float = WINDOW_S + BUFFER_S

# PBFT view-change timeout. Probe finding: at f ≤ 0.30 the honest quorum is met
# without the slow backups, so PBFT never rotates the leader (view_change_count
# = 0 at every f, m) — delayed *backups* below the fault threshold do not stall
# the primary. vc_delay is kept realistic (≈ 3× honest round); it does not fire
# in this experiment, which is itself the finding (reported in the experiment
# page, not engineered around).
PBFT_VC_DELAY_S: float = 3.0

# Per-protocol one-round latency (the "started in [0,W]" scope bound for the
# clip). PROBE-SET 2026-06-15 from the worst-magnitude (m=10) cell: PBFT and
# FFG finalize a round in ≈1 s and ≈0.5 s (scope bound 2 s); Snowman's worst
# single-block finalization under attack is ≈71 s, so its scope bound is sized
# to keep those crippled-but-finalizing instances in-scope (their inflated
# latency is the headline, not noise to be dropped as "late").
ONE_ROUND_S: dict[str, float] = {
    "pbft":       2.0,
    "casper-ffg": 2.0,
    "snowman":   72.0,
}

# --- Workload axis (experiment-matrix §6 committed defaults). ------------
ARRIVAL_PROCESS: str = "poisson"
OFFERED_RATE: float = 100.0
TX_BYTES: int = 512
CONFLICT_RATE: float = 0.0


@dataclass(frozen=True)
class Timeline:
    """The single fixed Family C network timeline (one network_phase_id).

    Mirrors delay.config.Timeline's surface (`name`, `e_delay_s`,
    `ffg_slot_duration_s`, `phases()`) so the runners read it identically.
    """
    name: str
    delay: DelayDist
    e_delay_s: float
    ffg_slot_duration_s: float

    def phases(self) -> tuple[Phase, ...]:
        return (Phase(0.0, math.inf, self.delay),)


# The Family C fixed network: constant 10 ms delivery delay, loss-free.
STATIC_BASELINE: Timeline = Timeline(
    name="static-baseline",
    delay=DelayDist("constant", {"delay": 0.01}),
    e_delay_s=0.01,
    ffg_slot_duration_s=FFG_SLOT_DURATION_S,
)
