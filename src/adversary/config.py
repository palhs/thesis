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
M_VALUES: tuple[float, ...] = (2.0, 5.0, 10.0)
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

# --- Window / buffer / view-change calibration (PROBE-SET; later task). ---
# Family C runs on the fast static-baseline (10 ms delay), so the window is
# far shorter than the Family B delay sweeps. WINDOW_S must hold ≥ 25
# in-window-started decisions for every protocol with clip < 5 %; the worst
# attack cell (m=10) holds emissions by up to 10·ref = 10 s (PBFT/Snowman),
# so the buffer must clear one such delayed round. Confirm via --probe.
WINDOW_S: float = 120.0
BUFFER_S: float = 24.0
T_MAX: float = WINDOW_S + BUFFER_S

# PBFT view-change timeout: realistic (≈ 3× honest round) so a slow backup that
# pushes a vote past it trips an OBSERVABLE view-change (the §3 invariant),
# while honest (f=0) cells never rotate. Probe-confirmed (view_change_count
# = 0 at f=0, > 0 under attack at large m). PROBE-SET.
PBFT_VC_DELAY_S: float = 3.0

# Per-protocol one-round latency (the "started in [0,W]" scope bound for the
# clip). PROBE-SET from the worst-magnitude probe cell.
ONE_ROUND_S: dict[str, float] = {
    "pbft":       12.0,
    "casper-ffg": 4.0,
    "snowman":   12.0,
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
