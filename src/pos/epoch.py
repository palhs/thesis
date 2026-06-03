"""Per-epoch FFG state aggregator (design spec §5).

One `EpochState` instance per target epoch — the [[concepts/node-model]] §4
FSM instance for Casper FFG. `record_vote` is dedup'd by attester
(Decision I): a duplicated *delivery* leaves the link stake unchanged.

Audit finding #3 (T70) refines that dedupe. The pre-fix `record_vote`
keyed on attester index alone, so a validator's SECOND, CONFLICTING vote
for the same target epoch (different source/target hashes) was swallowed
identically to a duplicate delivery — masking Casper FFG's two slashable
offences. `record_vote` now classifies the vote against the attester's
prior vote for this target epoch:

  - NEW       — first vote by this attester for this target; stake counted.
  - DUPLICATE — byte-identical re-delivery; idempotent no-op (as before).
  - CONFLICT  — same attester, same target epoch, but a differing source
                epoch / source hash / target hash. Stake is NOT
                re-counted (the link keeps the first vote's weight), and
                the caller is signalled so it can run slashing detection.

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


class VoteStatus(Enum):
    """Classification of one `record_vote` call against prior votes by the
    same attester for this target epoch."""
    NEW = 0          # first vote by this attester for this target epoch
    DUPLICATE = 1    # byte-identical re-delivery — idempotent no-op
    CONFLICT = 2     # same attester+target, differing source/hashes


class EpochState:
    """Per-target-epoch FFG aggregation."""

    def __init__(self, epoch: int) -> None:
        self.epoch: int = epoch
        self.checkpoint_hash: bytes | None = None
        self.state: EpochFSM = EpochFSM.UNJUSTIFIED
        # source_epoch -> { attester_idx -> stake }
        self.links: dict[int, dict[int, float]] = {}
        # attester_idx -> the (source_epoch, source_hash, target_hash) of the
        # first vote that attester filed for this target epoch. The presence
        # of a key is the dedupe set; the value lets us tell an idempotent
        # re-delivery (DUPLICATE) from a slashable second vote (CONFLICT).
        self._filed: dict[int, tuple[int, bytes | None, bytes | None]] = {}

    def record_vote(self, source_epoch: int, attester_idx: int,
                    stake: float, source_hash: bytes | None = None,
                    target_hash: bytes | None = None) -> "VoteStatus":
        """File one FFG vote for this target epoch and classify it.

        Returns:
          VoteStatus.NEW       — first vote by `attester_idx`; stake counted.
          VoteStatus.DUPLICATE — identical (source_epoch, source_hash,
                                  target_hash) re-delivery; no-op.
          VoteStatus.CONFLICT  — same attester, differing link; stake is NOT
                                  re-counted (first vote keeps its weight).

        `source_hash`/`target_hash` default to None so legacy 3-arg callers
        (and unit fixtures) keep working; with both None the duplicate vs
        conflict test reduces to `source_epoch` equality.
        """
        prior = self._filed.get(attester_idx)
        if prior is not None:
            if prior == (source_epoch, source_hash, target_hash):
                return VoteStatus.DUPLICATE
            return VoteStatus.CONFLICT
        self._filed[attester_idx] = (source_epoch, source_hash, target_hash)
        self.links.setdefault(source_epoch, {})[attester_idx] = stake
        return VoteStatus.NEW

    def link_stake(self, source_epoch: int) -> float:
        return sum(self.links.get(source_epoch, {}).values())
