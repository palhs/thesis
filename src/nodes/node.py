"""Shared-layer validator abstraction (node-model.md, T14 / T22).

Design spec: docs/superpowers/specs/2026-05-19-t22-node-objects-design.md
Protocol behaviour is supplied by subclasses (PBFTNode = T28, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .lifecycle import HaltReason, Lifecycle
from .message import Message


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
