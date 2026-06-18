"""Slow-node selection for the delay-emission adversary (T51, spec §3.3).

The slow set is the highest-id ⌊f·n⌋ nodes. PBFT's view-0 primary is node 0,
so selecting from the top keeps the attack on backups (delayed PREPARE/COMMIT
votes), not the leader -- this is delay-emission, not disrupt-leader. Snowman
is leaderless and Casper FFG rotates its proposer by slot, so the occasional
proposer overlap in FFG is reported (spec §3.3), not engineered away.
"""
from __future__ import annotations

import math


def slow_node_ids(n: int, f: float) -> tuple[int, ...]:
    """Return the ⌊f·n⌋ highest node ids, ascending. Empty when f == 0.

    For every f < 1 the count is < n, so node 0 (the PBFT primary) is never
    included -- the invariant the experiment relies on.
    """
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"f must be in [0, 1], got {f}")
    k = math.floor(f * n)
    if k <= 0:
        return ()
    return tuple(range(n - k, n))


def byzantine_node_ids(n: int, f: float) -> tuple[int, ...]:
    """Return the ⌊f·n⌋ LOWEST node ids, ascending. Empty when f == 0.

    The inverse of slow_node_ids (which spares node 0): equivocation needs the
    PBFT view-0 primary (node 0) and proposer slots INSIDE the Byzantine set, so
    the adversary is the low-id prefix. (T53; adversary-model.md §5.)
    """
    if not (0.0 <= f <= 1.0):
        raise ValueError(f"f must be in [0, 1], got {f}")
    k = math.floor(f * n)
    return tuple(range(0, k)) if k > 0 else ()
