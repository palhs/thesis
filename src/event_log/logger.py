"""Structured event logger for the consensus simulator (T24).

A passive Scheduler.event_sink consumer: normalises the scheduler's
heterogeneous event stream (emit tuples + typed transport events) into
uniform EventRecords, buffers them, and exports to CSV.

Design contract: wiki/concepts/event-log-schema.md
Design spec: docs/superpowers/specs/2026-05-19-t24-event-logging-design.md
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scheduler import Delivery, PhaseAdvance, TimerFire

from .event_types import DELIVERY, PHASE_ADVANCE, TIMER_FIRE

_CSV_HEADER = ("t", "node_id", "event_type", "seq", "fields")


@dataclass(frozen=True)
class EventRecord:
    """One normalised entry in the event log (event-log-schema.md)."""
    t: float
    node_id: int
    event_type: str
    seq: int
    fields: dict
