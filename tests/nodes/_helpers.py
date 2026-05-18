"""Test doubles for the shared-layer Node (T22)."""
from __future__ import annotations

from nodes import Node


class FakeNode(Node):
    """Minimal concrete Node: records every protected-hook invocation."""

    def __init__(self, node_id=0, weight=1.0, endpoint=None, global_seed=0):
        super().__init__(node_id, weight, endpoint, global_seed)
        self.calls: list[tuple] = []

    def _on_start(self, t):
        self.calls.append(("_on_start", t))

    def _on_message(self, msg, t):
        self.calls.append(("_on_message", msg, t))

    def _on_timer(self, timer_id, payload, t):
        self.calls.append(("_on_timer", timer_id, payload, t))
