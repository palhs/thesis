"""Node lifecycle and halt-reason enumerations (node-model.md §3)."""
from __future__ import annotations

from enum import Enum


class Lifecycle(Enum):
    """Shared lifecycle stages every Node traverses, monotonically."""
    CREATED = 0
    RUNNING = 1
    HALTED = 2


class HaltReason(Enum):
    """Why a Node transitioned to HALTED (node-model.md §3 halt reasons)."""
    RUN_END = 0   # harness: configured stop condition reached
    CRASHED = 1   # harness: fault injection / non-participant adversary
    SLASHED = 2   # FSM (Casper FFG only): slashable equivocation detected
    EXITED = 3    # FSM (Casper FFG only): voluntary withdrawal at epoch end
