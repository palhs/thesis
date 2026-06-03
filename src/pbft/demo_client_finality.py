# src/pbft/demo_client_finality.py
"""T70 finding #1 demo — PBFT client-observed finality (n=4).

Runs ONE honest PBFT request to completion at n=4 with the `t70.pbft` step
logger enabled at INFO, printing the full phase trace:

    pre-prepare -> prepare -> commit -> reply -> client-finalize

and a final two-line summary contrasting the COMMIT-quorum time (the old,
one-hop-optimistic finality) with the client-observed finality one network
hop later.

This is the ONLY place that calls logging.basicConfig — library code
(pbft/node.py) never configures handlers, so the trace is silent unless a
runner like this one turns it on.

Run:
    PYTHONPATH=src python3 -m pbft.demo_client_finality
"""
from __future__ import annotations

import logging
import math
from types import MappingProxyType

from common import run_to_completion
from config.factory import build_run
from config.schema import Config, SeedsConfig
from network import DelayDist, Phase

from . import PBFTNode


# A single, visible network hop so commit and client-finality are distinct,
# readable timestamps in the trace (the unit-test baseline uses 1e-9).
_HOP = 0.1
_NETWORK = (Phase(0.0, math.inf, DelayDist("constant", {"delay": _HOP})),)


def _config(n: int) -> Config:
    return Config(
        n=n, t_max=math.inf, seeds=SeedsConfig(n_runs=1),
        network=_NETWORK, adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}), workload=MappingProxyType({}),
    )


def _factory(n: int):
    def make(node_id: int, global_seed: int) -> PBFTNode:
        # One request on the primary (node 0); generous vc_delay so no
        # view-change fires on the honest path.
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n,
                        workload=[b"REQUEST-0"] if node_id == 0 else None,
                        propose_delay=1.0, initial_view=0, vc_delay=1000.0)
    return make


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    n, seed = 4, 42
    handle = build_run(_config(n), seed, _factory(n))
    _, logger = run_to_completion(handle)

    decided = [r for r in logger.records if r.event_type == "decided"]
    final = [r for r in logger.records
             if r.event_type == "pbft_client_finalized"]
    commit_t = min(r.t for r in decided)            # 2f+1 COMMIT quorum
    finality_t = min(r.fields["t"] for r in final)  # f+1 client REPLYs

    print("---")
    print(f"commit_t (2f+1 COMMIT quorum)      = {commit_t}")
    print(f"client_finality_t (f+1 REPLYs)     = {finality_t}")
    print(f"client finality is one hop later   = "
          f"{finality_t > commit_t} (+{finality_t - commit_t:.3f}s)")


if __name__ == "__main__":
    main()
