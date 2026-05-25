"""Per-epoch FFG state aggregator (design spec §5).

One `EpochState` instance per target epoch — the [[concepts/node-model]] §4
FSM instance for Casper FFG. `record_vote` is dedup'd by attester
(Decision I): a duplicated delivery, or an honest validator's second vote
for the same target, leaves the link stake unchanged.

The supermajority test and the justify/finalise transition rule live in
[[algorithms/pos]] §5 and the `finality` module (T34); this file owns
aggregation only.
"""
from __future__ import annotations

from enum import Enum


class EpochFSM(Enum):
    UNJUSTIFIED = 0
    JUSTIFIED = 1
    FINALISED = 2


class EpochState:
    """Per-target-epoch FFG aggregation."""

    def __init__(self, epoch: int) -> None:
        self.epoch: int = epoch
        self.checkpoint_hash: bytes | None = None
        self.state: EpochFSM = EpochFSM.UNJUSTIFIED
        # source_epoch -> { attester_idx -> stake }
        self.links: dict[int, dict[int, float]] = {}
        self._attesters: set[int] = set()

    def record_vote(self, source_epoch: int, attester_idx: int,
                    stake: float) -> bool:
        """File one FFG vote. Returns False (and changes nothing) if this
        attester already voted for this target epoch."""
        if attester_idx in self._attesters:
            return False
        self._attesters.add(attester_idx)
        self.links.setdefault(source_epoch, {})[attester_idx] = stake
        return True

    def link_stake(self, source_epoch: int) -> float:
        return sum(self.links.get(source_epoch, {}).values())
