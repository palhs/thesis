"""Simplified PBFT consensus subsystem (T28 + T29).

T28 (this PR) ships the pre-prepare phase: the primary drains a stub
workload, broadcasts PRE-PREPARE, locally self-transitions, recipients
validate against five rules and reach PRE_PREPARED. PREPARE / COMMIT /
VIEW-CHANGE / NEW-VIEW are silently no-op'd (skeleton-cut, Decision A);
T29 wires them.

Design spec: docs/superpowers/specs/2026-05-21-t28-pbft-proposal-design.md
Plan:        docs/superpowers/specs/2026-05-21-t28-pbft-proposal-plan.md
"""
from .digest import digest
from .instance import Instance, InstanceState
from .messages import (
    CommitPayload,
    NewViewPayload,
    PreparePayload,
    PrePreparePayload,
    ViewChangePayload,
)
from .node import PBFT_PRE_PREPARED, PBFT_REJECTED, PBFTNode

__all__ = [
    "PBFTNode",
    "Instance", "InstanceState",
    "PrePreparePayload", "PreparePayload", "CommitPayload",
    "ViewChangePayload", "NewViewPayload",
    "PBFT_PRE_PREPARED", "PBFT_REJECTED",
    "digest",
]
