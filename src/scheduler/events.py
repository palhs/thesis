"""Scheduler event taxonomy and core type aliases.

Design contract: wiki/concepts/simulation-design.md §4-§5
Spec: docs/superpowers/specs/2026-05-13-t17-scheduler-design.md §4.2
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Core type aliases (simulation-design.md §4).
SimTime = float   # virtual time, milliseconds (network-model §1)
NodeId = int      # validator identifier (node-model §2)
TimerId = Any     # caller-supplied timer key (node-model §7)


@dataclass
class Delivery:
    """A message arriving at a Node."""
    msg: Any   # Message envelope (network-model §3.1); concrete type from T23.


@dataclass
class TimerFire:
    """A Node's self-scheduled wake-up."""
    timer_id: TimerId
    payload: Any


@dataclass
class PhaseAdvance:
    """A network-phase boundary transition."""
    phase_id: int


Event = Delivery | TimerFire | PhaseAdvance
