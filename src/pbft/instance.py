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
    # T29: request payload, retained for self-contained view-change evidence
    # (Decision E). Set by _accept_pre_prepare alongside `digest`.
    request_payload: Optional[bytes] = None
    # T29: quorum collection. src -> digest, one entry per matching message.
    prepares: dict[int, bytes] = field(default_factory=dict)
    commits: dict[int, bytes] = field(default_factory=dict)

    def matching_prepares(self) -> int:
        """Count PREPAREs whose asserted digest matches this instance's
        pre-prepared digest. Zero while digest is None (Decision C)."""
        if self.digest is None:
            return 0
        return sum(1 for d in self.prepares.values() if d == self.digest)

    def matching_commits(self) -> int:
        """COMMIT analogue of `matching_prepares`."""
        if self.digest is None:
            return 0
        return sum(1 for d in self.commits.values() if d == self.digest)
