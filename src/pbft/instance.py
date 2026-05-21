# src/pbft/instance.py
"""Per-(view, seq) PBFT instance data plane (T28 spec § 5).

Realises wiki/algorithms/pbft.md § Three-phase commit. The four-state
enum is declared up front (skeleton-cut, Decision A); T28 only wires
IDLE -> PRE_PREPARED. The prepares / commits quorum dicts are reserved
for T29.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class InstanceState(Enum):
    IDLE = 0
    PRE_PREPARED = 1
    PREPARED = 2       # T29-wired
    COMMITTED = 3      # T29-wired


@dataclass
class Instance:
    """One PBFT (view, seq) instance. Lazily created on the first valid
    PRE-PREPARE (or on the primary's self-loop) per spec § 7.5.
    """
    view: int
    seq: int
    state: InstanceState = InstanceState.IDLE
    digest: Optional[bytes] = None
    # T29: quorum collection. src -> digest, one entry per matching message.
    prepares: dict[int, bytes] = field(default_factory=dict)
    commits: dict[int, bytes] = field(default_factory=dict)
