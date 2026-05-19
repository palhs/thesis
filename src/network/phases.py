"""Phase configuration for the honest delivery layer (network-model-phases.md, T15/T23).

Design spec: docs/superpowers/specs/2026-05-19-t23-network-design.md
"""
from __future__ import annotations

import math   # used by validate_timeline (Task 3)
import random
from dataclasses import dataclass

NodeId = int
SimTime = float

# Strictly-positive guard so t_delivered > t_sent (network-model.md §4).
# Only ever binds on the measure-zero exponential edge case.
_LATENCY_FLOOR: float = 1e-9

_DELAY_KINDS = ("constant", "uniform", "normal", "exponential", "heavy_tail")
_REQUIRED_PARAMS = {
    "constant": ("delay",),
    "uniform": ("low", "high"),
    "normal": ("mean", "std"),
    "exponential": ("mean",),
    "heavy_tail": ("scale", "shape"),
}


@dataclass(frozen=True)
class DelayDist:
    """A named delivery-delay distribution (network-model-phases.md §2).

    `sample()` returns strictly-positive SimTime. Bad params raise
    ValueError at construction (fail-fast, before any run).

    Note: `params` is not deep-frozen — do not mutate it after construction
    (validation runs only at construction).
    """
    kind: str
    params: dict

    def __post_init__(self) -> None:
        if self.kind not in _DELAY_KINDS:
            raise ValueError(f"unknown delay kind: {self.kind!r}")
        for key in _REQUIRED_PARAMS[self.kind]:
            if key not in self.params:
                raise ValueError(
                    f"delay kind {self.kind!r} requires param {key!r}")
        p = self.params
        if self.kind == "constant":
            if p["delay"] <= 0:
                raise ValueError(f"constant delay must be > 0, got {p['delay']}")
        elif self.kind == "uniform":
            if p["low"] <= 0:
                raise ValueError(f"uniform low must be > 0, got {p['low']}")
            if p["high"] < p["low"]:
                raise ValueError(
                    f"uniform high {p['high']} < low {p['low']}")
        elif self.kind == "normal":
            if p["std"] < 0:
                raise ValueError(f"normal std must be >= 0, got {p['std']}")
            if p.get("clip_low", 1.0) <= 0:
                raise ValueError(
                    f"normal clip_low must be > 0, got {p.get('clip_low')}")
        elif self.kind == "exponential":
            if p["mean"] <= 0:
                raise ValueError(
                    f"exponential mean must be > 0, got {p['mean']}")
        else:  # heavy_tail
            if p["scale"] <= 0:
                raise ValueError(
                    f"heavy_tail scale must be > 0, got {p['scale']}")
            if p["shape"] <= 0:
                raise ValueError(
                    f"heavy_tail shape must be > 0, got {p['shape']}")

    def sample(self, rng: random.Random) -> SimTime:
        p = self.params
        if self.kind == "constant":
            raw = p["delay"]
        elif self.kind == "uniform":
            raw = rng.uniform(p["low"], p["high"])
        elif self.kind == "normal":
            raw = max(rng.normalvariate(p["mean"], p["std"]),
                      p.get("clip_low", 1.0))
        elif self.kind == "exponential":
            raw = rng.expovariate(1.0 / p["mean"])
        else:  # heavy_tail — Pareto, paretovariate() >= 1.0
            raw = p["scale"] * rng.paretovariate(p["shape"])
        return max(raw, _LATENCY_FLOOR)


@dataclass(frozen=True)
class Partition:
    """A network partition: blocks delivery between disjoint groups
    (network-model-phases.md §4).

    v1 asymmetric (symmetric=False) blocks all directed cross-group edges,
    identically to symmetric. The `symmetric` field is reserved for the
    per-edge allowlisting revision (network-model.md §8); it does not yet
    change `blocks` behaviour.
    """
    groups: tuple[tuple[NodeId, ...], ...]
    symmetric: bool = True

    def _group_of(self, node: NodeId) -> int | None:
        for i, g in enumerate(self.groups):
            if node in g:
                return i
        return None

    def blocks(self, src: NodeId, dst: NodeId) -> bool:
        gs = self._group_of(src)
        gd = self._group_of(dst)
        if gs is None or gd is None:
            return False          # unconstrained validators stay reachable
        return gs != gd


@dataclass(frozen=True)
class Phase:
    """One contiguous network-condition interval, half-open [t_start, t_end)
    (network-model-phases.md §1, §5). The final phase may have
    t_end = math.inf; every interior phase has a finite t_end.
    """
    t_start: SimTime
    t_end: SimTime
    delay: DelayDist
    p_drop: float = 0.0
    partitions: tuple[Partition, ...] = ()


def validate_timeline(phases: tuple[Phase, ...],
                       registered_ids: set[NodeId]) -> None:
    """Fail-fast validation of a phase timeline (network-model-phases.md §5).

    Raises ValueError naming the first violation found. Run once by
    Network.start(), before t=0.
    """
    if not phases:
        raise ValueError("phase timeline is empty; need >= 1 phase")
    if phases[0].t_start != 0:
        raise ValueError(
            f"first phase must start at t=0, got {phases[0].t_start}")
    last_idx = len(phases) - 1
    for i, ph in enumerate(phases):
        if ph.t_start >= ph.t_end:
            raise ValueError(
                f"phase {i} has non-positive width: "
                f"[{ph.t_start}, {ph.t_end})")
        if i != last_idx:
            if not math.isfinite(ph.t_end):
                raise ValueError(
                    f"interior phase {i} has non-finite t_end={ph.t_end}")
            if ph.t_end != phases[i + 1].t_start:
                raise ValueError(
                    f"phase {i} t_end={ph.t_end} != phase {i + 1} "
                    f"t_start={phases[i + 1].t_start} (non-contiguous)")
        if not (0.0 <= ph.p_drop < 1.0):
            raise ValueError(
                f"phase {i} p_drop={ph.p_drop} not in [0, 1) "
                f"(1.0 is forbidden — use a covering partition)")
        for j, part in enumerate(ph.partitions):
            if len(part.groups) < 2:
                raise ValueError(
                    f"phase {i} partition {j}: need >= 2 groups, "
                    f"got {len(part.groups)}")
            seen: set[NodeId] = set()
            for g in part.groups:
                if not g:
                    raise ValueError(
                        f"phase {i} partition {j}: empty group")
                for nid in g:
                    if nid in seen:
                        raise ValueError(
                            f"phase {i} partition {j}: NodeId {nid} "
                            f"appears in multiple groups")
                    seen.add(nid)
                    if nid not in registered_ids:
                        raise ValueError(
                            f"phase {i} partition {j}: NodeId {nid} "
                            f"not registered")
