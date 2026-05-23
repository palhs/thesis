"""Casper FFG block chain (design spec §4).

Honest-path: a single linear chain of slot-proposed blocks. The genesis
block sits at slot 0 / epoch 0 with a fixed sentinel hash, so every node's
chain shares a byte-identical root without a propagation step. The block
hash is `hashlib.blake2b` over a canonical field encoding — same primitive
family as src/pbft/digest.py, process-stable across runs (no Python `hash`).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass


GENESIS_HASH: bytes = b"\x00" * 32


@dataclass(frozen=True)
class Block:
    slot: int
    epoch: int
    parent_hash: bytes
    block_hash: bytes
    transactions: tuple[bytes, ...]
    proposer_idx: int


def block_hash(slot: int, parent_hash: bytes,
               proposer_idx: int,
               transactions: tuple[bytes, ...]) -> bytes:
    """32-byte blake2b digest over the block's identifying fields."""
    h = hashlib.blake2b(digest_size=32)
    h.update(str(slot).encode())
    h.update(b"|")
    h.update(parent_hash)
    h.update(b"|")
    h.update(str(proposer_idx).encode())
    h.update(b"|")
    for tx in transactions:
        h.update(tx)
        h.update(b",")
    return h.digest()


GENESIS: Block = Block(slot=0, epoch=0, parent_hash=GENESIS_HASH,
                       block_hash=GENESIS_HASH, transactions=(),
                       proposer_idx=-1)


class Chain:
    """Linear chain of slot-proposed blocks (design spec §4).

    Blocks arrive over the network out of order; a block whose parent has
    not yet been delivered is buffered and re-examined when the next block
    lands. Buffered blocks drain in ascending slot order for determinism.
    Honest-path: a single chain, so `head` is the block at the greatest
    known slot — fork-choice (LMD-GHOST) is deferred to T46–T50.
    """

    def __init__(self, slots_per_epoch: int) -> None:
        self.slots_per_epoch: int = slots_per_epoch
        self.blocks: dict[bytes, Block] = {GENESIS_HASH: GENESIS}
        self.head: Block = GENESIS
        self._buffer: list[Block] = []

    def add(self, block: Block) -> None:
        if block.parent_hash not in self.blocks:
            self._buffer.append(block)
            return
        self.blocks[block.block_hash] = block
        if block.slot > self.head.slot:
            self.head = block
        self._drain_buffer()

    def _drain_buffer(self) -> None:
        while True:
            ready = [b for b in self._buffer if b.parent_hash in self.blocks]
            if not ready:
                return
            ready.sort(key=lambda b: b.slot)
            for b in ready:
                self._buffer.remove(b)
                self.blocks[b.block_hash] = b
                if b.slot > self.head.slot:
                    self.head = b

    def checkpoint(self, epoch: int) -> Block:
        """Return the checkpoint Block of `epoch` (the block at
        `epoch * slots_per_epoch`). Raises KeyError if not yet known."""
        if epoch == 0:
            return GENESIS
        target_slot = epoch * self.slots_per_epoch
        for b in self.blocks.values():
            if b.slot == target_slot:
                return b
        raise KeyError(f"no checkpoint block for epoch {epoch}")
