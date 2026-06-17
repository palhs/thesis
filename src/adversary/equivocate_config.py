"""Family C equivocate-vote (T53) configuration.

The equivocating adversary forks conflicting payloads from the low-id Byzantine
prefix (byzantine_node_ids). The per-protocol intensity grid runs PBFT and
Casper FFG ABOVE the 1/3 fault threshold (f=0.40, 0.50) to expose the safety
cliff — equivocation above f>1/3 lets the Byzantine set forge conflicting
quorums / double-finalise. Snowman stops at 0.33 (liveness-only: a lying
responder can stall progress but there is no fork surface to break safety, so
sweeping above 1/3 buys no new signal) — design §2.

Calibration constants are inherited PROVISIONALLY from T52 and re-finalised in
Task 10 (calibration probe).
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

# PROVISIONAL — re-probed and finalised in Task 10 (calibration probe).
WINDOW_S: float = 150.0
BUFFER_S: float = 80.0
T_MAX: float = WINDOW_S + BUFFER_S
PBFT_VC_DELAY_S: float = 3.0
ONE_ROUND_S: dict[str, float] = {"pbft": 2.0, "casper-ffg": 2.0, "snowman": 72.0}
SNOWMAN_QUERY_TIMEOUT_S: float = 15.0
