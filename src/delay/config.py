"""Family B delay-experiment configuration (T46).

Pins the two T46 network-delay timelines and the window / buffer
calibration the locked Week-9 methodology requires. All delay values are
in SECONDS of simulator model time — the same unit the honest baselines
use (slot_duration = 1.0 s ⇒ commit_latency ≈ 1000 ms). The
[[concepts/experiment-matrix-runs]] §2 catalog quotes the same
distributions in milliseconds (uniform[100,500] ms, E[delay] = 300 ms);
they are expressed here as 0.1–0.5 s / mean 0.3 s.

Calibration (probe-derived; see the experiment page §Calibration):
  - WINDOW_S      — measurement window W. Metrics are computed for every
                    instance that STARTED in [0, W].
  - BUFFER_S      — run tail past W so in-window-started instances can
                    finalize; ≥ one full protocol round for every protocol.
  - t_max         = WINDOW_S + BUFFER_S (the run horizon).
  - clip rule     — decided events with t > W are dropped from the rate
                    count; latency uses the first instance, always ≪ W.

T46 covers EXACTLY the two timelines defined here. T47 owns the heavy-tail
/ loss / partial-sync-gst timelines (NOT implemented in this package).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from network import DelayDist, Phase

# --- Window / buffer calibration (probe-derived, locked methodology). ----
#
# Probe (1 seed/regime, see the experiment page §Calibration): one-round
# latency under moderate delay is ~1.6–1.9 s (PBFT), ~6.1 s (Casper FFG,
# first epoch), ~12–14 s (Snowman, β=15 sequential poll rounds). Snowman is
# the binding constraint on both axes.
#
# W is sized so (a) every protocol finalizes ≫ 25 in-window-STARTED
# decisions and (b) the finalization tail clipped past W is < 5 % of the
# in-window-started decided events. Snowman's fat ~14 s per-block tail makes
# the clipped-fraction ≈ round_latency / W, so W must be ≳ 16 s / 0.05 ≈
# 320 s; W = 480 s gives margin (worst-case probe clip = 3.81 %, Snowman
# n=25 exponential). BUFFER ≥ one full protocol round so an instance that
# started just before W still finalizes inside the run horizon; Snowman's
# heaviest exponential round (~14 s + n=25 tail) is the binding constraint,
# so BUFFER = 48 s.
WINDOW_S: float = 480.0
BUFFER_S: float = 48.0
T_MAX: float = WINDOW_S + BUFFER_S

# Per-protocol one-round latency (probe-measured, ms) — the buffer floor and
# the "started in [0,W]" scope guard. An instance is in-window-started iff
# its first decision lands at or before WINDOW_S + ONE_ROUND_S[protocol].
ONE_ROUND_S: dict[str, float] = {
    "pbft":       2.0,
    "casper-ffg": 7.0,
    "snowman":   16.0,
}

# --- Casper FFG slot rescaling (experiment-matrix §5 coherence rule). ----
#
# slot_duration ≥ 4 · E[delay]. Both T46 timelines have E[delay] = 0.3 s,
# so slot_duration = 1.2 s (1200 ms), per the §2 pairing table. Snowman and
# PBFT keep their native cadence (slot/propose = 1.0 s); only FFG rescales.
FFG_SLOT_DURATION_S: float = 1.2
FFG_SLOTS_PER_EPOCH: int = 2

# PBFT propose cadence and Snowman slot cadence (unchanged from baselines).
PBFT_PROPOSE_DELAY_S: float = 1.0
SNOWMAN_SLOT_DURATION_S: float = 1.0
SNOWMAN_BETA: int = 15

# --- Workload axis (experiment-matrix §6 committed defaults). ------------
ARRIVAL_PROCESS: str = "poisson"
OFFERED_RATE: float = 100.0
TX_BYTES: int = 512
CONFLICT_RATE: float = 0.0


@dataclass(frozen=True)
class Timeline:
    """One named network-delay timeline (one `network_phase_id` value).

    `delay` is the single-phase delivery-delay distribution; `e_delay_s`
    is its mean (the quantity the FFG coherence rule keys on);
    `ffg_slot_duration_s` is the FFG slot length paired to it. The mean is
    recorded so the output can annotate plots without re-deriving it.
    """
    name: str
    delay: DelayDist
    e_delay_s: float
    ffg_slot_duration_s: float

    def phases(self) -> tuple[Phase, ...]:
        """The single-phase [0, ∞) timeline this delay regime realises."""
        return (Phase(0.0, math.inf, self.delay),)


# The two T46 timelines (experiment-matrix-runs §2). E[delay] = 0.3 s both.
TIMELINES: tuple[Timeline, ...] = (
    Timeline(
        name="delay-uniform",
        delay=DelayDist("uniform", {"low": 0.1, "high": 0.5}),
        e_delay_s=0.3,
        ffg_slot_duration_s=FFG_SLOT_DURATION_S,
    ),
    Timeline(
        name="delay-exponential",
        delay=DelayDist("exponential", {"mean": 0.3}),
        e_delay_s=0.3,
        ffg_slot_duration_s=FFG_SLOT_DURATION_S,
    ),
)

# Validator-set sizes (locked Week-9 amendment to experiment-matrix §3):
# n = 10 (shared anchor with Family C) and n = 25 (3f+1, f = 8). Family C
# adversarial (T51–T56) stays at n = 10 — see TASKS.md Backlog 2026-06-10.
N_VALUES: tuple[int, ...] = (10, 25)
SEEDS: tuple[int, ...] = tuple(range(20))
