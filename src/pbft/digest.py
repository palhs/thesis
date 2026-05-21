# src/pbft/digest.py
"""32-byte blake2b digest helper for PBFT message integrity (T28 spec § 6).

Matches the process-stable hash discipline established for the per-Node
RNG seed (src/nodes/node.py:_stable_seed) and the network RNG seed
(src/network/network.py:_network_seed). blake2b, not hash() — Python's
hash() of bytes is process-stable but the discipline is uniform.
"""
from __future__ import annotations

import hashlib


def digest(payload: bytes) -> bytes:
    """Return the 32-byte blake2b digest of `payload`.

    Width matches `wiki/concepts/message-types.md` § 7 (Hash digest = 32B).
    """
    return hashlib.blake2b(payload, digest_size=32).digest()
