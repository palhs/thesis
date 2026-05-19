"""Test doubles for the Network (T23)."""
from __future__ import annotations

from nodes import HaltReason, Node


class StubNode(Node):
    """Minimal concrete Node: records inbound messages. For unit tests."""

    def __init__(self, node_id, global_seed=0):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.received: list = []

    def _on_start(self, t):
        pass

    def _on_message(self, msg, t):
        self.received.append((msg, t))

    def _on_timer(self, timer_id, payload, t):
        pass


class PingPongNode(Node):
    """Two nodes bounce a token; each halts after `budget` inbound messages."""

    def __init__(self, node_id, peer_id, budget, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.peer_id = peer_id
        self.budget = budget
        self.hops = 0

    def _on_start(self, t):
        if self.id == 0:
            self.send(self.peer_id, "PING", {"hop": 0}, t)

    def _on_message(self, msg, t):
        self.hops += 1
        if self.hops >= self.budget:
            self._emit_decided(value="done", instance_id=self.id, t=t)
            self.halt(HaltReason.RUN_END, t)
            return
        reply = "PONG" if msg.type == "PING" else "PING"
        self.send(msg.src, reply, {"hop": self.hops}, t)

    def _on_timer(self, timer_id, payload, t):
        pass
