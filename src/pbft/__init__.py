"""Simplified PBFT consensus subsystem (T28 + T29).

T28 shipped the pre-prepare phase: the primary drains a stub workload,
broadcasts PRE-PREPARE, locally self-transitions, recipients validate
against five rules and reach PRE_PREPARED.

T29 wires the full classical protocol: PREPARE / COMMIT voting,
commit/finalization (the `decided` event), and the VIEW-CHANGE -> NEW-VIEW
recovery path.

Design spec: docs/superpowers/specs/2026-05-21-t29-pbft-voting-design.md
Plan:        docs/superpowers/specs/2026-05-21-t29-pbft-voting-plan.md
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
from .node import (
    PBFT_COMMITTED,
    PBFT_NEW_VIEW,
    PBFT_PRE_PREPARED,
    PBFT_PREPARED,
    PBFT_REJECTED,
    PBFT_VIEW_CHANGE,
    PBFTNode,
)
from .viewchange import collect_evidence, compute_reissue

__all__ = [
    "PBFTNode",
    "Instance", "InstanceState",
    "PrePreparePayload", "PreparePayload", "CommitPayload",
    "ViewChangePayload", "NewViewPayload",
    "PBFT_PRE_PREPARED", "PBFT_REJECTED",
    "PBFT_PREPARED", "PBFT_COMMITTED", "PBFT_VIEW_CHANGE", "PBFT_NEW_VIEW",
    "collect_evidence", "compute_reissue",
    "digest",
]
