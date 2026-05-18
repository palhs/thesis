"""Discrete-event scheduler package — the simulator's virtual-time engine.

See wiki/concepts/simulation-design.md for the design contract.
"""
from .events import (
    Delivery,
    Event,
    NodeId,
    PhaseAdvance,
    SimTime,
    TimerFire,
    TimerId,
)
from .scheduler import RunResult, Scheduler

__all__ = [
    "Delivery",
    "Event",
    "NodeId",
    "PhaseAdvance",
    "RunResult",
    "Scheduler",
    "SimTime",
    "TimerFire",
    "TimerId",
]
