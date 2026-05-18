"""Validator (Node) package — shared lifecycle layer (node-model.md, T22).

See docs/superpowers/specs/2026-05-19-t22-node-objects-design.md.
"""
from .lifecycle import HaltReason, Lifecycle
from .message import Message
from .node import AdversaryProfile, Node

__all__ = [
    "AdversaryProfile",
    "HaltReason",
    "Lifecycle",
    "Message",
    "Node",
]
