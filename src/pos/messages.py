"""Casper FFG message payloads (design spec §3, wiki/concepts/message-types §4).

Two wire payload types and one nested vote object. The shared `Message`
envelope (src, dst, type, payload, t_sent) is owned by nodes/message.py.

Per design spec §15, per-validator signature fields (`proposer_sig`,
`signature`) are omitted: the simulator passes Python objects, not signed
bytes, and performs no signature verification.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FFGVote:
    source_epoch: int
    source_hash: bytes
    target_epoch: int
    target_hash: bytes


@dataclass(frozen=True)
class BlockProposalPayload:
    slot: int
    epoch: int
    parent_hash: bytes
    block_hash: bytes
    transactions: tuple[bytes, ...]
    proposer_idx: int


@dataclass(frozen=True)
class AttestationPayload:
    # `head_vote_hash` from message-types §4 is omitted — LMD-GHOST is out
    # of scope for T32 (design spec Decision B).
    slot: int
    epoch: int
    ffg: FFGVote
    attester_idx: int
