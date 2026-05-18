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
    EMIT_SEQ: int = -1           # emit events carry no real seq; placeholder slot

    def __init__(self) -> None:
        # per-node-monotonic seq makes (t, node_id, seq) unique by
        # construction, so heapq never reaches the 4th tuple element (event).
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
        """Schedule a TimerFire for a Node. `delay == 0` is legal.

        `timer_id` must be hashable (it keys the `registry` dict).
        """
        if delay < 0:
            raise ValueError(f"negative timer delay: {delay}")
        # Funnel through schedule() (single-funnel invariant, §5.1) and
        # register the seq it assigned (DD4 / Revision R2).
        seq = self.schedule(TimerFire(timer_id, payload), t + delay, node_id)
        self.registry[(node_id, timer_id)] = seq

    def cancel_timer(self, node_id: NodeId, timer_id: TimerId) -> None:
        """Cancel a timer. O(1); the heap entry is left as a lazy tombstone."""
        self.registry.pop((node_id, timer_id), None)

    def bind(self, node: Any) -> None:
        """Wire a Node's scheduler-owned outbound API and register it for
        dispatch. Does NOT wire send/broadcast — that is Network.bind's half.
        """
        self.nodes[node.id] = node   # DD3 / Revision R1: dispatch target.
        node.set_timer = lambda timer_id, delay, payload, t: self.set_timer(
            node.id, timer_id, delay, payload, t
        )
        node.cancel_timer = lambda timer_id: self.cancel_timer(
            node.id, timer_id
        )
        node.emit = lambda event_type, fields, t: (
            self.event_sink(t, node.id, self.EMIT_SEQ,
                            ("emit", event_type, fields))
            if self.event_sink is not None
            else None
        )

    def bind_network(self, network: Any) -> None:
        """Register the Network as the dispatch target for PhaseAdvance
        events (DD3 / Revision R1). Called once during bootstrap phase 3.
        """
        self.network = network

    def run(self, t_max: SimTime | None = None,
            stop_when: Callable[[], bool] | None = None) -> RunResult:
        """Run the dispatch loop until a stop condition fires.

        Stop conditions (OR-composed, §3 D5):
          - deadline   : `now >= t_max` checked before each pop;
          - quiescence : the heap drains;
          - predicate  : `stop_when()` returns True after a dispatch.
        """
        n_processed = 0
        n_tombstoned = 0
        while True:
            if t_max is not None and self._now >= t_max:
                return RunResult("deadline", self._now,
                                 n_processed, n_tombstoned)
            if not self.heap:
                return RunResult("quiescence", self._now,
                                 n_processed, n_tombstoned)
            t, node_id, seq, event = heapq.heappop(self.heap)
            self._now = t
            if isinstance(event, TimerFire) and \
                    self.registry.get((node_id, event.timer_id)) != seq:
                n_tombstoned += 1
                continue
            if self.event_sink is not None:
                self.event_sink(t, node_id, seq, event)
            self._dispatch(event, node_id, t)
            n_processed += 1
            if stop_when is not None and stop_when():
                return RunResult("predicate", self._now,
                                 n_processed, n_tombstoned)

    def _node(self, node_id: NodeId) -> Any:
        try:
            return self.nodes[node_id]
        except KeyError:
            raise KeyError(
                f"dispatch: no Node bound for node_id={node_id}"
            ) from None

    def _dispatch(self, event: Event, node_id: NodeId, t: SimTime) -> None:
        """Route a popped event to its handler, keyed on event class."""
        if isinstance(event, Delivery):
            self._node(node_id).on_message(event.msg, t)
        elif isinstance(event, TimerFire):
            self._node(node_id).on_timer(event.timer_id, event.payload, t)
        elif isinstance(event, PhaseAdvance):
            if self.network is None:
                raise RuntimeError(
                    "dispatch: PhaseAdvance with no network bound; "
                    "call bind_network() first"
                )
            self.network.advance_phase(event.phase_id)
        else:  # fail-fast on an unknown event class (runtime §3).
            raise TypeError(f"unknown event class: {type(event).__name__}")
