"""Adversary strategy profiles (T51).

``DelayProfile`` is the first concrete fill of the opaque ``Node.adversary``
slot (node-model.md §9). It mirrors the adversary-model-runtime.md §4
``DelayProfile`` reference sketch, trimmed to exactly what the
``delay-emission`` capability needs: the slow-node set, the nominal intensity
(fraction f), and the fixed delay multiple (m). ``kind`` tags the capability.

Stored on the node for observability/provenance; the actual late-emission
behaviour is realised by ``adversary.inject.inject_delay`` (the bind-seam
wrap), not by the FSM reading this object (spec §3.2 / the node-model.md §9
Revision).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DelayProfile:
    """The ``delay-emission`` adversary profile for one run.

    - ``nodes``     -- the slow-node ids (highest-id ⌊f·n⌋; select.py).
    - ``intensity`` -- nominal fraction f of slow nodes.
    - ``mult``      -- m, the fixed delay multiple of the protocol round
                       cadence applied to every outbound emission.
    - ``kind``      -- capability tag ("delay-emission").
    """
    nodes: tuple[int, ...]
    intensity: float
    mult: float
    kind: str = "delay-emission"
