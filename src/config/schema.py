"""Frozen dataclasses for the YAML config schema (T27 spec § 3).

Three sections (`adversary`, `protocol_knobs`, `workload`) are opaque
`Mapping[str, Any]` blobs by design — their upstream wiki contracts are
open-to-revision (adversary-model-runtime §4, node-model §11). When the
tasks that own those contracts (T18 binding, T28+, T41) land, each replaces
its `dict` with a typed dataclass.

Network sub-types are reused from src/network/phases.py — do not mirror
them as *Config types.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from network.phases import Phase
from nodes import Node
from scheduler import Scheduler


@dataclass(frozen=True)
class SeedsConfig:
    """Seeds / replication axis (experiment-matrix.md §7).

    `n_runs` is the only field today; the harness enumerates seeds
    0 … n_runs-1 externally. A future SeedsConfig revision may add a
    seed_seq override; deferred to T41.
    """
    n_runs: int


@dataclass(frozen=True)
class Config:
    """One configuration point — one row of the future T40 comparative CSV.

    Six axes (experiment-matrix.md §2) plus the operational t_max scalar.
    Three opaque sections are loaded round-trip but not introspected by
    build_run.
    """
    n: int
    t_max: float
    seeds: SeedsConfig
    network: tuple[Phase, ...]
    adversary: Mapping[str, Any]       # opaque — T18
    protocol_knobs: Mapping[str, Any]  # opaque — T28+
    workload: Mapping[str, Any]        # opaque — T41


@dataclass(frozen=True)
class RunHandle:
    """Three handles returned by build_run(): the Scheduler, the Network,
    and an immutable Mapping[NodeId, Node] view of the registered Nodes.
    """
    scheduler: Scheduler
    # `network` is forward-declared as Any to avoid a circular import; T27
    # does not depend on Network's type for any narrowing.
    network: Any
    nodes: Mapping[int, Node]
