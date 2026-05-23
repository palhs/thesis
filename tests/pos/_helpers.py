"""Shared fixtures for the T32 Casper FFG unit suite.

Mirrors tests/pbft/_helpers.py: one CasperNode in isolation, the bind-time
outbound API replaced with capturers, kickoff to RUNNING. Not a test
module — the `_` prefix keeps it out of unittest discover.
"""
from __future__ import annotations

from typing import Any

from nodes.lifecycle import Lifecycle
from pos.node import CasperNode


def uniform_stake(n: int, stake: float = 3.0) -> dict[int, float]:
    return {i: stake for i in range(n)}


def make_node(node_id: int, n: int, *, stake_table=None,
              slot_duration: float = 1.0, slots_per_epoch: int = 2,
              attest_offset: int | None = None,
              workload: list[bytes] | None = None) -> CasperNode:
    st = stake_table if stake_table is not None else uniform_stake(n)
    kwargs: dict[str, Any] = dict(
        node_id=node_id, weight=st[node_id], endpoint=None,
        global_seed=42, n=n, stake_table=st,
        slot_duration=slot_duration, slots_per_epoch=slots_per_epoch,
        workload=workload,
    )
    if attest_offset is not None:
        kwargs["attest_offset"] = attest_offset
    return CasperNode(**kwargs)


class Capture:
    """Records the outbound API channels a CasperNode drives."""

    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict, float]] = []
        self.broadcasts: list[tuple[str, object, float]] = []
        self.timers: list[tuple] = []
        self.cancels: list = []

    def events(self, et): return [e for e in self.emitted if e[0] == et]

    def count(self, et): return len(self.events(et))

    def broadcast_types(self): return [b[0] for b in self.broadcasts]

    def count_broadcast(self, ty):
        return sum(1 for b in self.broadcasts if b[0] == ty)


def capturers(node: CasperNode) -> Capture:
    cap = Capture()
    node.emit = lambda et, f, t: cap.emitted.append((et, f, t))
    node.broadcast = lambda ty, p, t: cap.broadcasts.append((ty, p, t))
    node.send = lambda *a, **kw: None
    node.set_timer = lambda tid, dl, p, t: cap.timers.append((tid, dl, p, t))
    node.cancel_timer = lambda tid: cap.cancels.append(tid)
    return cap


def kickoff(node: CasperNode) -> None:
    """Force RUNNING without firing _on_start (Node.on_message refuses a
    CREATED node)."""
    node.status = Lifecycle.RUNNING
