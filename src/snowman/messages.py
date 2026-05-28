"""Snowman message payloads (design spec §3, wiki/concepts/message-types §5).

Three wire payload types. The shared Message envelope (src, dst, type,
payload, t_sent) is owned by nodes/message.py and is not redeclared here.

Per design spec §3, signature fields are omitted: the simulator passes
Python objects, not signed bytes, and performs no signature verification.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BlockAnnouncementPayload:
    slot: int
    block_id: bytes              # 32-byte SHA-256 hash (see block.hash_block)
    parent_id: bytes             # 32-byte; b'\x00'*32 = genesis
    transactions: tuple[bytes, ...]
    proposer_idx: int


@dataclass(frozen=True)
class QueryPayload:
    request_id: int              # poller-monotone; unique per (poller, block_id, round)
    block_id: bytes              # the block being polled


@dataclass(frozen=True)
class QueryResponsePayload:
    request_id: int              # echoes the QUERY
    preferred_block_id: bytes    # responder's current preference for block_id's conflict set
