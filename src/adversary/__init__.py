"""Adversary-injection subsystem (T51).

The first fill of the opaque ``Node.adversary`` slot. Attaches an adversary
capability by re-wrapping a node's bound outbound API AFTER ``build_run`` --
the honest network/scheduler/FSMs are never edited (network-model.md §6).

T51 lands the ``delay-emission`` capability (slow voters). T52 (withhold) and
T53 (equivocate) extend this package.

Design spec: docs/superpowers/specs/2026-06-14-t51-delayed-voters-design.md
"""
from __future__ import annotations

from .inject import inject_delay, inject_offline
from .profiles import DelayProfile, EquivocateProfile, OfflineProfile
from .select import slow_node_ids

__all__ = ["DelayProfile", "EquivocateProfile", "OfflineProfile",
           "inject_delay", "inject_offline", "slow_node_ids"]
