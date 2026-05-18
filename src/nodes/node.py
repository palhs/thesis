"""Shared-layer validator abstraction (node-model.md, T14 / T22).

Design spec: docs/superpowers/specs/2026-05-19-t22-node-objects-design.md
Protocol behaviour is supplied by subclasses (PBFTNode = T28, etc.).
"""
from __future__ import annotations

import hashlib
import random
from abc import ABC, abstractmethod
from typing import Any, Optional

from .lifecycle import HaltReason, Lifecycle
from .message import Message


def _stable_seed(global_seed: int, node_id: int) -> int:
    """Derive a process-stable 64-bit RNG seed from (global_seed, node_id).

    Python's built-in hash() is process-randomised for some inputs; blake2b
    is identical across processes and machines. See the node-model.md §8
    Revision dated 2026-05-19.
    """
    digest = hashlib.blake2b(f"{global_seed}:{node_id}".encode(),
                             digest_size=8).digest()
    return int.from_bytes(digest, "big")


class Node(ABC):
    """Shared lifecycle layer of a validator. Identity, lifecycle FSM,
    per-Node RNG, template-method inbound hooks, outbound-API placeholders,
    and the opaque adversary slot. Subclasses supply the protocol FSM."""

    def __init__(self, node_id: int, weight: float,
                 endpoint: object, global_seed: int) -> None:
        if weight < 0:
            raise ValueError(f"weight must be non-negative, got {weight}")
        self.id: int = node_id
        self.weight: float = weight
        self.endpoint: object = endpoint
        self.rng: random.Random = random.Random(
            _stable_seed(global_seed=global_seed, node_id=node_id))
        self.status: Lifecycle = Lifecycle.CREATED
        self._halt_reason: Optional[HaltReason] = None
        self.adversary: Optional[object] = None   # typed in Task 10

    # --- Inbound hooks: protected; protocol subclasses override these. ---

    @abstractmethod
    def _on_start(self, t: float) -> None:
        """Protocol kickoff: schedule initial timers, emit first messages."""

    @abstractmethod
    def _on_message(self, msg: Message, t: float) -> None:
        """Handle a delivered message."""

    @abstractmethod
    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        """Handle a fired timer."""

    # --- Outbound API: placeholders overwritten at bind time (spec §5.5). ---

    def send(self, dst: int, type: str, payload: object, t: float) -> None:
        """Unicast `payload` to one peer. Bound by Network.bind() (spec §5.5)."""
        raise RuntimeError(
            f"Node {self.id}.send called before Network.bind()")

    def broadcast(self, type: str, payload: object, t: float) -> None:
        """Send `payload` to the active validator set. Bound by Network.bind()."""
        raise RuntimeError(
            f"Node {self.id}.broadcast called before Network.bind()")

    def set_timer(self, timer_id: Any, delay: float,
                  payload: object, t: float) -> None:
        """Register a timer firing on_timer after `delay`. Bound by Scheduler.bind()."""
        raise RuntimeError(
            f"Node {self.id}.set_timer called before Scheduler.bind()")

    def cancel_timer(self, timer_id: Any) -> None:
        """Cancel a previously-registered timer. Bound by Scheduler.bind()."""
        raise RuntimeError(
            f"Node {self.id}.cancel_timer called before Scheduler.bind()")

    def emit(self, event_type: str, fields: dict, t: float) -> None:
        """Emit a structured observability event. Bound by Scheduler.bind()."""
        raise RuntimeError(
            f"Node {self.id}.emit called before Scheduler.bind()")

    # --- Inbound hooks: public; called by the Scheduler (spec §5.4). ---

    def start(self, t: float) -> None:
        """Bootstrap kickoff (scheduler phase 5). CREATED -> RUNNING."""
        if self.status is not Lifecycle.CREATED:
            raise RuntimeError(
                f"start() on Node {self.id} with status {self.status.name}")
        self.status = Lifecycle.RUNNING
        self._on_start(t)

    def halt(self, reason: HaltReason, t: float) -> None:
        """Transition to HALTED and emit the mandatory `halted` event.
        Re-halting is a no-op: the first reason wins (the harness blanket-
        halts every Node with RUN_END at run's end). See spec §5.3."""
        if self.status is Lifecycle.HALTED:
            return
        self.status = Lifecycle.HALTED
        self._halt_reason = reason
        self.emit("halted",
                  {"node_id": self.id, "reason": reason.name, "t": t}, t)

    def on_message(self, msg: Message, t: float) -> None:
        """Scheduler-dispatched message delivery. Drops if halted, errors if
        not yet started, otherwise delegates to _on_message."""
        if self.status is Lifecycle.HALTED:
            return                       # halted Node ceases handling (§3)
        if self.status is Lifecycle.CREATED:
            raise RuntimeError(
                f"on_message before start() on Node {self.id}")
        self._on_message(msg, t)

    def on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        """Scheduler-dispatched timer fire. Same lifecycle guard as
        on_message, then delegates to _on_timer."""
        if self.status is Lifecycle.HALTED:
            return
        if self.status is Lifecycle.CREATED:
            raise RuntimeError(
                f"on_timer before start() on Node {self.id}")
        self._on_timer(timer_id, payload, t)
