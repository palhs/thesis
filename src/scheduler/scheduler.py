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

    def schedule(self, event: Event, t: SimTime, node_id: NodeId) -> int:
        """Enqueue an event. The single funnel into the heap.

        Returns the per-Node seq assigned (DD4 / Revision R2), so set_timer
        can register the heap entry's exact seq without a second increment.
        Raises ValueError if `t` is in the past (fail-fast, runtime §3).
        """
        if t < self._now:
            raise ValueError(f"schedule in the past: t={t} < now={self._now}")
        seq = self._next_seq(node_id)
        heapq.heappush(self.heap, (t, node_id, seq, event))
        return seq

    def set_timer(self, node_id: NodeId, timer_id: TimerId,
                  delay: SimTime, payload: Any, t: SimTime) -> None:
        """Schedule a TimerFire for a Node. `delay == 0` is legal."""
        if delay < 0:
            raise ValueError(f"negative timer delay: {delay}")
        # Funnel through schedule() (single-funnel invariant, §5.1) and
        # register the seq it assigned (DD4 / Revision R2).
        seq = self.schedule(TimerFire(timer_id, payload), t + delay, node_id)
        self.registry[(node_id, timer_id)] = seq

    def cancel_timer(self, node_id: NodeId, timer_id: TimerId) -> None:
        """Cancel a timer. O(1); the heap entry is left as a lazy tombstone."""
        self.registry.pop((node_id, timer_id), None)
