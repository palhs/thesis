"""The equivocate-vote adversary: three node subclasses + shared helpers (T53).

Behaviour lives here as thin subclasses of the honest node classes; the honest
FSMs under src/{pbft,pos,snowman}/ are never edited (B-hybrid, design §2). Each
subclass overrides only its payload-emitting methods to fork a conflicting
payload across a deterministic half-half split of its recipients — NO adversary
RNG, so per-cell replay is byte-identical (design §7).

Design contract: docs/plans/2026-06-18-t53-equivocating-nodes-design.md
"""
from __future__ import annotations


def split_recipients(node) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Split peers-minus-self into (lo, hi) halves; pure fn of (node.n, node.id)."""
    peers = tuple(i for i in range(node.n) if i != node.id)
    mid = len(peers) // 2
    return peers[:mid], peers[mid:]


def conflicting_bytes(tag: str, k1: int, k2: int) -> tuple[bytes, bytes]:
    """Two distinct request/tx blobs, a pure fn of the instance key, so every
    colluding Byzantine node derives the SAME pair independently."""
    return (f"EQV-A:{tag}:{k1}:{k2}".encode(),
            f"EQV-B:{tag}:{k1}:{k2}".encode())
