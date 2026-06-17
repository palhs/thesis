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

# Calibration — PROBE-SET in Task 5. Defaults below are starting points only.
WINDOW_S: float = 150.0
BUFFER_S: float = 80.0
T_MAX: float = WINDOW_S + BUFFER_S
PBFT_VC_DELAY_S: float = 3.0
ONE_ROUND_S: dict[str, float] = {"pbft": 2.0, "casper-ffg": 2.0, "snowman": 72.0}
