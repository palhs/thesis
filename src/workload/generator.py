"""Deterministic transaction-workload generator (T41).

Design spec: docs/superpowers/specs/2026-05-30-t41-scaling-workload-design.md

A pure function of (WorkloadConfig, global_seed) that returns one transaction
batch per proposal opportunity. The same list is handed to every node; the
proposer at opportunity k uses batches[k]. Determinism is the cardinal
contract — the RNG is seeded only from the global seed via blake2b (no
module-level random, no wallclock), mirroring the network-model idiom in
src/network/network.py:_network_seed.
"""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkloadConfig:
    """Knobs for the offered transaction load.

    Fields (positional order is part of the public contract):
      arrival_process — "constant" or "poisson".
      offered_rate    — transactions per unit time (mean for poisson).
      tx_bytes        — exact byte length of each transaction payload.
      conflict_rate   — fraction of conflicting transactions (reserved; the
                        payload builder does not yet use it).
    """

    arrival_process: str
    offered_rate: float
    tx_bytes: int
    conflict_rate: float


def _workload_seed(global_seed: int) -> int:
    """Process-stable 64-bit seed for the workload RNG.

    blake2b, not hash() — Python's hash() of a str is process-randomised
    (PYTHONHASHSEED), which would break byte-identical replay. Domain tag
    ``workload:`` keeps this stream disjoint from the network/node streams.
    """
    digest = hashlib.blake2b(b"workload:" + str(global_seed).encode(),
                             digest_size=8).digest()
    return int.from_bytes(digest, "big")


def _tx_payload(global_seed: int, opportunity: int, idx: int,
                tx_bytes: int) -> bytes:
    """A distinct, content-stable byte string of EXACTLY ``tx_bytes`` length.

    Keyed on (global_seed, opportunity, idx) so every transaction across the
    whole workload is distinct, and identical across runs/processes. For small
    sizes a single blake2b digest suffices; for large sizes (e.g. 512) a
    seeded 64-byte pattern is repeated and truncated to exactly tx_bytes.
    """
    if tx_bytes <= 0:
        return b""
    key = f"{global_seed}:{opportunity}:{idx}".encode()
    if tx_bytes <= 64:
        return hashlib.blake2b(key, digest_size=tx_bytes).digest()
    # Large payloads: tile a 64-byte seeded pattern, then truncate.
    pattern = hashlib.blake2b(key, digest_size=64).digest()
    reps = math.ceil(tx_bytes / len(pattern))
    return (pattern * reps)[:tx_bytes]


def _batch_size(cfg: WorkloadConfig, rng: random.Random, interval: float) -> int:
    """Draw the number of transactions for one proposal opportunity.

    constant — round(offered_rate * interval), deterministic (no RNG draw).
    poisson  — Knuth's algorithm with mean = offered_rate * interval, driven
               entirely by rng.random().
    """
    mean = cfg.offered_rate * interval
    if cfg.arrival_process == "constant":
        return round(mean)
    if cfg.arrival_process == "poisson":
        if mean <= 0.0:
            return 0
        # Knuth: multiply uniforms until the product drops below e^-mean.
        limit = math.exp(-mean)
        k = 0
        product = 1.0
        while True:
            product *= rng.random()
            if product <= limit:
                return k
            k += 1
    raise ValueError(f"unknown arrival_process: {cfg.arrival_process!r}")


def generate_batches(cfg: WorkloadConfig, global_seed: int,
                     n_opportunities: int,
                     interval: float) -> tuple[tuple[bytes, ...], ...]:
    """Return one transaction batch per proposal opportunity.

    A single RNG, seeded from ``_workload_seed(global_seed)``, drives every
    batch-size draw in order. Returns nested tuples so the result is immutable
    and value-comparable (== works directly in tests).
    """
    rng = random.Random(_workload_seed(global_seed))
    batches: list[tuple[bytes, ...]] = []
    for opportunity in range(n_opportunities):
        size = _batch_size(cfg, rng, interval)
        batch = tuple(
            _tx_payload(global_seed, opportunity, idx, cfg.tx_bytes)
            for idx in range(size)
        )
        batches.append(batch)
    return tuple(batches)
