# src/pbft/viewchange.py
"""Pure view-change helpers (T29 spec § 8).

`collect_evidence` and `compute_reissue` carry no `PBFTNode` dependency;
they operate on plain data (the per-instance dict and `ViewChangePayload`
lists) so the view-change recovery logic is unit-testable in isolation.
"""
from __future__ import annotations

from .instance import Instance, InstanceState
from .messages import PrePreparePayload, ViewChangePayload


def collect_evidence(
    inst: dict[tuple[int, int], Instance]
) -> list[tuple[int, int, bytes, bytes]]:
    """Every instance at state >= PREPARED, as (view, seq, digest,
    request_payload) 4-tuples sorted by (view, seq).

    Decision D: no checkpoint bound — all prepared-or-committed instances
    are evidence, uncapped.
    """
    evidence = [
        (i.view, i.seq, i.digest, i.request_payload)
        for i in inst.values()
        if i.state in (InstanceState.PREPARED, InstanceState.COMMITTED)
    ]
    return sorted(evidence, key=lambda tup: (tup[0], tup[1]))


def compute_reissue(
    proofs: list[ViewChangePayload], new_view: int
) -> list[PrePreparePayload]:
    """Union the `prepared` evidence across all VIEW-CHANGE proofs; for each
    distinct seq pick the tuple from the highest view (the most recent
    prepared certificate); return one PrePreparePayload stamped with
    `new_view` per seq, sorted by seq.

    The highest-view-per-seq rule is the simulator analogue of classical
    PBFT's O-set "max prepared view" rule (spec § 8). With honest nodes
    every proof agrees; the choice only becomes load-bearing once T18 / T53
    inject conflicting evidence.
    """
    best: dict[int, tuple[int, int, bytes, bytes]] = {}
    for proof in proofs:
        for view, seq, req_digest, payload in proof.prepared:
            current = best.get(seq)
            if current is None or view > current[0]:
                best[seq] = (view, seq, req_digest, payload)
    return [
        PrePreparePayload(view=new_view, seq=seq,
                          request_digest=best[seq][2],
                          request_payload=best[seq][3])
        for seq in sorted(best)
    ]
