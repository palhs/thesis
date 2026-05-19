"""Structured event-logging subsystem (T24).

Records the simulator's consensus event stream and exports it to CSV.
See wiki/concepts/event-log-schema.md for the design contract.

Named `event_log`, not `logging`, to avoid shadowing the stdlib module
under PYTHONPATH=src (design spec, Decision E).
"""
from .event_types import (
    DECIDED,
    DELIVERY,
    HALTED,
    PHASE_ADVANCE,
    TIMER_FIRE,
    TRANSPORT_EVENT_TYPES,
)
from .logger import EventLogger, EventRecord

__all__ = [
    "DECIDED",
    "DELIVERY",
    "EventLogger",
    "EventRecord",
    "HALTED",
    "PHASE_ADVANCE",
    "TIMER_FIRE",
    "TRANSPORT_EVENT_TYPES",
]
