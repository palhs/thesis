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


@dataclass(frozen=True)
class OfflineProfile:
    """The ``withhold-participation`` adversary profile for one run.

    A non-participating (offline / crash-faulty) validator: it receives and
    runs its FSM but emits nothing, so it contributes to no quorum or poll.
    No magnitude field — offline is binary (skip vs participate), unlike
    delay-emission's dosed ``mult`` (adversary-model.md §4).

    - ``nodes``     -- the offline node ids (highest-id ⌊f·n⌋; select.py).
    - ``intensity`` -- nominal fraction f of offline nodes.
    - ``kind``      -- capability tag ("withhold-participation").
    """
    nodes: tuple[int, ...]
    intensity: float
    kind: str = "withhold-participation"


@dataclass(frozen=True)
class EquivocateProfile:
    """The ``equivocate-vote`` adversary profile for one run (T53).

    A Byzantine validator that signs two incompatible messages where the
    protocol expects one, forking the payload across a deterministic half-half
    split of its recipients. No magnitude axis (binary, like offline). The
    behaviour lives in the adversarial node subclasses (equivocate.py); this
    object is stored for observability/provenance (adversary-model.md §5).
    """
    nodes: tuple[int, ...]
    intensity: float
    partition_strategy: str = "half-half"
    kind: str = "equivocate-vote"
