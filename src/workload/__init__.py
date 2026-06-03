"""Deterministic transaction-workload generation (T41).

See generator.py and docs/superpowers/specs/2026-05-30-t41-scaling-workload-design.md.
"""
from .generator import WorkloadConfig, generate_batches

__all__ = ["WorkloadConfig", "generate_batches"]
