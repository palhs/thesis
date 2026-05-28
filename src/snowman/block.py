"""Snowman per-block state (design spec §4).

Block dataclass + canonical hash; ConflictSet (Snowball state for all
blocks sharing one parent_id); Chain (linear chain bookkeeping for the
proposer).
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field
from enum import Enum

GENESIS_ID: bytes = b"\x00" * 32


@dataclass(frozen=True)
class Block:
    block_id: bytes              # 32-byte SHA-256, see hash_block()
    parent_id: bytes
    slot: int
    proposer_idx: int
    transactions: tuple[bytes, ...]


def hash_block(
    *,
    slot: int,
    parent_id: bytes,
    proposer_idx: int,
    transactions: tuple[bytes, ...],
) -> bytes:
    """Deterministic SHA-256 over a canonical length-prefixed encoding.

    Encoding (all integers big-endian, fixed width):
      uint64 slot || bytes(32) parent_id || uint32 proposer_idx
      || uint32 n_tx || (uint32 len || bytes len) for each tx
    """
    if len(parent_id) != 32:
        raise ValueError(f"parent_id must be 32 bytes, got {len(parent_id)}")
    h = hashlib.sha256()
    h.update(struct.pack(">Q", slot))
    h.update(parent_id)
    h.update(struct.pack(">I", proposer_idx))
    h.update(struct.pack(">I", len(transactions)))
    for tx in transactions:
        h.update(struct.pack(">I", len(tx)))
        h.update(tx)
    return h.digest()


class CSState(Enum):
    POLLING = "polling"
    ACCEPTED = "accepted"


@dataclass
class ConflictSet:
    """Snowball state for all blocks claiming one parent_id.

    confidence[b] is the monotonic per-block accumulator (Snowball's
    "highest-confidence preference" semantics): incremented every round
    where b is the round's majority block with count >= alpha_p.
    counter is the *consecutive* alpha_c-hits on the current preference;
    reset on a flip or on an alpha_c miss. state transitions to ACCEPTED
    when counter >= beta.
    """
    parent_id: bytes
    members: dict[bytes, Block] = field(default_factory=dict)
    confidence: dict[bytes, int] = field(default_factory=dict)
    preference: bytes = b""
    counter: int = 0
    state: CSState = CSState.POLLING

    def add_block(self, block: Block) -> None:
        """First block added becomes the initial preference."""
        if block.block_id in self.members:
            return
        self.members[block.block_id] = block
        self.confidence.setdefault(block.block_id, 0)
        if self.preference == b"":
            self.preference = block.block_id


class Chain:
    """Linear chain bookkeeping for the proposer.

    Tracks the depth of every seen block — used to identify the tip that
    the slot proposer extends — and the set of ACCEPTED blocks (used by
    the build-verification assertion). Out-of-order arrivals (a block
    whose parent has not been seen) short-circuit; T46–T50 will revisit.
    """

    def __init__(self) -> None:
        self.accepted: dict[bytes, Block] = {}
        self.depth: dict[bytes, int] = {GENESIS_ID: 0}
        self.tip: bytes = GENESIS_ID

    def on_announce(self, block: Block) -> None:
        parent_depth = self.depth.get(block.parent_id)
        if parent_depth is None:
            return       # out-of-order; T46–T50 owns this
        if block.block_id in self.depth:
            return       # already recorded
        self.depth[block.block_id] = parent_depth + 1
        if self.depth[block.block_id] > self.depth[self.tip]:
            self.tip = block.block_id

    def on_accept(self, block: Block) -> None:
        self.accepted[block.block_id] = block
