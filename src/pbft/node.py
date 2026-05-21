# src/pbft/node.py
"""Simplified PBFT validator (T28 spec § 7).

T28 ships the pre-prepare phase: the primary drains a stub workload,
broadcasts PRE-PREPARE, locally self-transitions; recipients validate
against five rules and reach PRE_PREPARED. PREPARE / COMMIT /
VIEW-CHANGE / NEW-VIEW are silently no-op'd (skeleton cut, Decision A);
T29 wires them.
"""
from __future__ import annotations

from typing import Any

from nodes import Message, Node

from .digest import digest
from .instance import Instance, InstanceState
from .messages import PrePreparePayload


PBFT_REJECTED = "pbft_rejected"
PBFT_PRE_PREPARED = "pbft_pre_prepared"


class PBFTNode(Node):
    """Classical PBFT validator restricted to the pre-prepare phase.

    Constructor parameters (keyword-only past super().__init__'s positional
    set; see spec § 7.1):
      n:             validator count (drives the v mod n primary rule and,
                     in T29, the 2f+1 quorum threshold).
      workload:      stub list[bytes] copied at construction; the primary
                     pops one item per propose timer fire (spec § 2 / Dec B).
      propose_delay: time between consecutive PRE-PREPARE emissions
                     (spec § 2 / Dec C).
      initial_view:  starting view; tests use 0. T29 may construct nodes in
                     a non-zero view to exercise view-change.
    """

    def __init__(self, node_id: int, weight: float, endpoint: object,
                 global_seed: int, *,
                 n: int,
                 workload: list[bytes] | None = None,
                 propose_delay: float = 1.0,
                 initial_view: int = 0) -> None:
        super().__init__(node_id, weight, endpoint, global_seed)
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        if not 0 <= node_id < n:
            raise ValueError(
                f"node_id {node_id} outside [0, {n})")
        if propose_delay <= 0:
            raise ValueError(
                f"propose_delay must be positive, got {propose_delay}")
        self.n: int = n
        self.f: int = (n - 1) // 3
        self.view: int = initial_view
        self.view_changing: bool = False
        self.workload: list[bytes] = list(workload or [])
        self.propose_delay: float = propose_delay
        self.next_seq: int = 0
        self.inst: dict[tuple[int, int], Instance] = {}

    # --- Node ABC hooks: stubs in this task; Tasks 5 + 6 fill them in. ---

    def _on_start(self, t: float) -> None:
        raise NotImplementedError("Task 6")

    def _on_message(self, msg: Message, t: float) -> None:
        raise NotImplementedError("Task 5")

    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        raise NotImplementedError("Task 6")

    # --- Primary detection (Decision D). ---

    def _is_primary(self, view: int) -> bool:
        return self.id == (view % self.n)
