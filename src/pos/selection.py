"""Casper FFG proposer selection (T33).

Pure functions that pick the proposer of a given slot. Every validator
computes the same proposer for the same slot — recipients reject any
`BLOCK-PROPOSAL` whose `msg.src` disagrees (`CasperNode._handle_block_proposal`,
`src/pos/node.py`), so the rule must be deterministic and depend only on
arguments shared by every node.

`stake_weighted_proposer` is T33's selection rule, used by `CasperNode`. It
draws a Random seeded from `(global_seed, slot)`, independent of the
per-node `Node.rng`, and samples one validator with probability
proportional to its stake. Canonical iteration order is
`sorted(stake_table)` so the sampler sees the same key sequence on every
node and every Python invocation.

`round_robin_proposer` is kept as the T32-era rule (`slot mod n`) for
reference and direct unit testing; `CasperNode` no longer calls it.
"""
from __future__ import annotations

import hashlib
import random


def _stable_seed(global_seed: int, slot: int) -> int:
    """Derive a 64-bit RNG seed from (global_seed, slot) via blake2b.

    Mirrors `src/nodes/node.py:_stable_seed` (with `slot` in place of
    `node_id`) so seed derivation is process-stable across runs and
    independent of Python's `random.Random` accepted seed types (3.13
    rejects tuples)."""
    digest = hashlib.blake2b(f"{global_seed}:{slot}".encode(),
                             digest_size=8).digest()
    return int.from_bytes(digest, "big")


def round_robin_proposer(slot: int, n: int) -> int:
    """T32 inline rule: proposer of `slot` is `slot mod n`."""
    if n <= 0:
        raise ValueError(f"n must be positive, got {n}")
    if slot < 0:
        raise ValueError(f"slot must be non-negative, got {slot}")
    return slot % n


def stake_weighted_proposer(slot: int,
                            stake_table: dict[int, float],
                            global_seed: int) -> int:
    """Stake-weighted random proposer of `slot`.

    All arguments are shared across validators, so every node computes the
    same `node_id`. The probability of returning validator `v` is
    `stake_table[v] / sum(stake_table.values())`; validators with zero
    stake are never returned. Total stake must be strictly positive.
    """
    if slot < 0:
        raise ValueError(f"slot must be non-negative, got {slot}")
    if not stake_table:
        raise ValueError("stake_table must be non-empty")
    validators = sorted(stake_table)
    weights = [stake_table[v] for v in validators]
    for v, w in zip(validators, weights):
        if w < 0:
            raise ValueError(f"stake_table[{v}]={w} must be non-negative")
    total = sum(weights)
    if total <= 0:
        raise ValueError(f"total stake must be positive, got {total}")
    rng = random.Random(_stable_seed(global_seed, slot))
    return rng.choices(validators, weights=weights, k=1)[0]
