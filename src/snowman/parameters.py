"""Snowman parameter rescaling rule.

See wiki/concepts/metric-reconciliation.md §Snowman parameter rescaling
for the derivation. The thesis sweeps n in {4, 7, 10, 16, 25}, well below
the production validator count of ~1000 that the Avalanche docs'
(K, alpha_p, alpha_c, beta) = (20, 11, 16, 15) assumes. Production K=20
is incoherent for n < 21. The rule below is the only rescaling used; it
is deterministic in n and reproducible across seeds.

beta is held constant at the production value (15) and is supplied
separately by the caller (SnowmanNode.__init__).
"""
from __future__ import annotations

import math


def snowman_parameters(n: int) -> tuple[int, int, int]:
    """Return (K, alpha_p, alpha_c) for a validator set of size n.

    Preconditions: n >= 2 (a single-node "network" has no peers to sample).
    """
    if n < 2:
        raise ValueError(f"snowman_parameters: n must be >= 2, got {n}")
    K = min(20, n - 1)
    alpha_p = K // 2 + 1
    alpha_c = math.ceil(0.8 * K)
    return K, alpha_p, alpha_c
