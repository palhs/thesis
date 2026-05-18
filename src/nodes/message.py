"""The Message envelope exchanged between Nodes (node-model.md §6).

Declared by the node-model contract; owned here (T22) so the Node inbound
hooks are typed against it. T23 (network) imports this rather than redefining.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    """Wire envelope. `type` / `payload` are filled per protocol by T16."""
    src: int               # NodeId of the sender
    dst: int | str         # NodeId, or the literal "broadcast"
    type: str              # protocol-specific tag (message-types, T16)
    payload: object        # T16-defined per (protocol, type)
    t_sent: float          # SimTime the sender emitted the message
