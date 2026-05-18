"""Recording stubs standing in for Node / Network in Scheduler tests.

Real Node / Network land in T22 / T23; these record calls so the scheduler
can be tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SimpleMessage:
    """Stand-in for the T23 Message envelope (network-model §3.1)."""
    src: int
    dst: int
    payload: Any


class RecordingNode:
    """Minimal Node stub: records inbound-hook calls in order."""

    def __init__(self, node_id: int) -> None:
        self.id = node_id
        self.calls: list[tuple] = []

    def on_message(self, msg: Any, t: float) -> None:
        self.calls.append(("on_message", msg, t))

    def on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        self.calls.append(("on_timer", timer_id, payload, t))

    def start(self, t: float) -> None:
        self.calls.append(("start", t))


class RecordingNetwork:
    """Minimal Network stub: records advance_phase calls in order."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def advance_phase(self, phase_id: int) -> None:
        self.calls.append(("advance_phase", phase_id))
