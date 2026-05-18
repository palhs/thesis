"""Discrete-event scheduler — the simulator's virtual-time engine.

Design contract: wiki/concepts/simulation-design.md (+ -runtime companion)
Spec: docs/superpowers/specs/2026-05-13-t17-scheduler-design.md
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, Callable, Literal

from .events import (
    Delivery,
    Event,
    NodeId,
    PhaseAdvance,
    SimTime,
    TimerFire,
    TimerId,
)


@dataclass
class RunResult:
    """Outcome of a Scheduler.run() call (simulation-design.md §6.5)."""
    stopped_by: Literal["quiescence", "deadline", "predicate"]
    now: SimTime
    events_processed: int
    events_tombstoned: int


class Scheduler:
    """Custom min-heap discrete-event scheduler (simulation-design.md §3 D1)."""

    PHASE_NODE_ID: NodeId = -1   # sentinel node_id for PhaseAdvance (§3 D2)

    def __init__(self) -> None:
        self.heap: list[tuple[SimTime, NodeId, int, Event]] = []
        self.registry: dict[tuple[NodeId, TimerId], int] = {}
        self.seq_per: dict[NodeId, int] = {}
        self._now: SimTime = 0.0
        self.event_sink: Callable[[SimTime, NodeId, int, Event], None] | None = None
        # DD3 (Revision R1): dispatch targets held by the scheduler.
        self.nodes: dict[NodeId, Any] = {}   # populated by bind()
        self.network: Any | None = None      # set by bind_network()

    @property
    def now(self) -> SimTime:
        """Virtual clock. Read-only; Node handlers receive `t` as a param."""
        return self._now

    def _next_seq(self, node_id: NodeId) -> int:
        seq = self.seq_per.get(node_id, 0) + 1
        self.seq_per[node_id] = seq
        return seq
