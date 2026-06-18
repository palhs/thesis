"""Cross-node safety signals for the equivocate-vote sweep (T53).

A post-run reducer over the aggregated event stream. Safety is a property of
the HONEST nodes only (a Byzantine node deciding anything proves nothing), so
Byzantine node_ids are excluded before comparing decisions. Feeds T54's formal
four-invariant analysis; T53 only records the raw signals. (Design §6.)
"""
from __future__ import annotations

from event_log import EventRecord
from pos.node import CASPER_SLASHING


def safety_signals(records: list[EventRecord],
                   byzantine_ids: frozenset[int]) -> dict[str, object]:
    by_instance: dict[object, set] = {}
    max_slash = 0.0
    for r in records:
        if r.event_type == "decided" and r.node_id not in byzantine_ids:
            by_instance.setdefault(r.fields.get("instance_id"), set()).add(
                r.fields.get("value"))
        elif r.event_type == CASPER_SLASHING:
            frac = r.fields.get("slashable_stake_fraction", 0.0) or 0.0
            max_slash = max(max_slash, float(frac))
    conflicting = sum(1 for vals in by_instance.values() if len(vals) > 1)
    return {
        "safety_violation": conflicting > 0,
        "conflicting_instances": conflicting,
        "max_slashable_stake_fraction": max_slash,
    }
