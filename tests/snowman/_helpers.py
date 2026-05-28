"""Shared fixtures for the T38 Snowman unit suite.

Two roles:
  - make_node / capturers / kickoff: one SnowmanNode in isolation with the
    bind-time outbound API replaced with capturers (mirrors tests/pos and
    tests/pbft).
  - build_run_harness: a full Scheduler + Network + n nodes harness driving
    a real Snowman run to either deadline or quiescence, with an
    EventLogger attached. Used by handler-level tests that need real
    delivery + RNG sampling.
"""
from __future__ import annotations

import math
from types import MappingProxyType
from typing import Any

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from nodes.lifecycle import Lifecycle
from snowman.node import SnowmanNode


_MINIMAL_DELAY = (
    Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),
)


def make_node(node_id: int, n: int, *, slot_duration: float = 1.0,
              beta: int = 15, K: int | None = None,
              alpha_p: int | None = None, alpha_c: int | None = None,
              workload: list[bytes] | None = None,
              global_seed: int = 42) -> SnowmanNode:
    kwargs: dict[str, Any] = dict(
        node_id=node_id, weight=1.0, endpoint=None, global_seed=global_seed,
        n=n, slot_duration=slot_duration, beta=beta, workload=workload,
    )
    if K is not None: kwargs["K"] = K
    if alpha_p is not None: kwargs["alpha_p"] = alpha_p
    if alpha_c is not None: kwargs["alpha_c"] = alpha_c
    return SnowmanNode(**kwargs)


class Capture:
    """Records the outbound API channels a SnowmanNode drives."""

    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict, float]] = []
        self.broadcasts: list[tuple[str, object, float]] = []
        self.sends: list[tuple[int, str, object, float]] = []
        self.timers: list[tuple] = []
        self.cancels: list = []

    def events(self, et): return [e for e in self.emitted if e[0] == et]

    def count(self, et): return len(self.events(et))


def capturers(node: SnowmanNode) -> Capture:
    cap = Capture()
    node.emit = lambda et, f, t: cap.emitted.append((et, dict(f), t))
    node.broadcast = lambda ty, p, t: cap.broadcasts.append((ty, p, t))
    node.send = lambda dst, ty, p, t: cap.sends.append((dst, ty, p, t))
    node.set_timer = lambda tid, dl, p, t: cap.timers.append((tid, dl, p, t))
    node.cancel_timer = lambda tid: cap.cancels.append(tid)
    return cap


def kickoff(node: SnowmanNode) -> None:
    """Force RUNNING without firing _on_start (Node.on_message refuses a
    CREATED node)."""
    node.status = Lifecycle.RUNNING


def _config(n: int, t_max: float) -> Config:
    return Config(
        n=n,
        t_max=t_max,
        seeds=SeedsConfig(n_runs=1),
        network=_MINIMAL_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def build_run_harness(*, n: int, t_max: float, global_seed: int = 42,
                      slot_duration: float = 1.0, beta: int = 15):
    """Build + run a full n-node Snowman simulation; return (logger, result, nodes)."""
    def factory(node_id: int, gs: int) -> SnowmanNode:
        return SnowmanNode(
            node_id=node_id, weight=1.0, endpoint=None, global_seed=gs,
            n=n, slot_duration=slot_duration, beta=beta)
    logger = EventLogger()
    handle = build_run(_config(n, t_max), global_seed, factory)
    handle.scheduler.event_sink = logger.sink
    result = handle.scheduler.run(t_max=t_max)
    return logger, result, dict(handle.nodes)
