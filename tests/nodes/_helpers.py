"""Test doubles for the shared-layer Node (T22)."""
from __future__ import annotations

from nodes import HaltReason, Message, Node
from scheduler import Delivery


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


class PingPongNode(Node):
    """Minimal real protocol: two nodes bounce a token; each halts after
    `budget` inbound messages. Draws from self.rng so the e2e determinism
    check exercises per-Node RNG seeding end-to-end."""

    def __init__(self, node_id, peer_id, budget, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.peer_id = peer_id
        self.budget = budget
        self.hops = 0

    def _on_start(self, t):
        if self.id == 0:
            self.send(self.peer_id, "PING",
                      {"hop": 0, "r": self.rng.random()}, t)

    def _on_message(self, msg, t):
        self.hops += 1
        if self.hops >= self.budget:
            self._emit_decided(value="done", instance_id=self.id, t=t)
            self.halt(HaltReason.RUN_END, t)
            return
        reply = "PONG" if msg.type == "PING" else "PING"
        self.send(msg.src, reply,
                  {"hop": self.hops, "r": self.rng.random()}, t)

    def _on_timer(self, timer_id, payload, t):
        pass


class LoopbackNetwork:
    """Minimal stand-in for the T23 Network: delivers each send/broadcast as a
    Scheduler Delivery after a fixed link delay. The real Network is T23."""

    # `type` param shadows the builtin to match the node-model §7 send/broadcast contract.
    LINK_DELAY = 10.0

    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.members: dict[int, Node] = {}

    def register(self, node):
        self.members[node.id] = node

    def bind(self, node):
        node.send = lambda dst, type, payload, t: self._deliver(
            node.id, dst, type, payload, t)
        node.broadcast = lambda type, payload, t: self._broadcast(
            node.id, type, payload, t)

    def _deliver(self, src, dst, type, payload, t):
        msg = Message(src=src, dst=dst, type=type, payload=payload, t_sent=t)
        self.scheduler.schedule(Delivery(msg), t + self.LINK_DELAY, dst)

    def _broadcast(self, src, type, payload, t):
        for dst in sorted(self.members):          # deterministic order
            if dst != src:
                self._deliver(src, dst, type, payload, t)
