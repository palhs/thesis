"""Window / buffer clip for the Family B delay sweep (T46).

The locked Week-9 buffer/clip rule:

  > Run to W + buffer; compute metrics for every block/epoch that STARTED
  > in [0, W] even if it finalizes in the buffer; clip events with t > W.

`clip_records` takes the raw event stream from a `run_<proto>` over the
full W+buffer horizon and returns the subset the reducer should see,
together with the clip statistics. Per the locked rule, EVERY event with
`t > W` is clipped — deliveries, timers, and decided alike — so the
overhead columns (`consensus_msgs_per_acu`, `bytes_per_acu`) count
messages over the SAME [0, W] window as their decided denominator.
Passing the buffer-period deliveries through (an earlier draft) inflated
PBFT / Snowman overhead by the buffer ratio (≈ W+buffer / W ≈ +10 %)
relative to the zero-delay baseline — a pure harness artifact, since the
message COUNT per instance is delay-invariant. The decided events carry
two extra refinements on top of the time clip:

  1. SCOPE — an instance is in-window-started iff its FIRST decision lands
     at or before `W + one_round` (the protocol's probe-measured one-round
     latency). Instances whose first decision is later were proposed in the
     buffer; their decided events are past W (so already time-clipped) and
     are tallied as `late_events`, excluded from the clipped_fraction
     denominator.
  2. CLIP — for an in-scope instance, decided events with `t > W` are the
     finalization tail spilling past the window; they are dropped from the
     per-event rate count but the instance is still counted (its first,
     in-window decision survives, so latency and the decision count keep it).

  Any decided event with `t <= W` is necessarily in-scope (its first
  decision is `<= t <= W <= W + one_round`), so the time clip and the scope
  filter agree on the KEPT decided set; SCOPE only refines the stats.

`clipped_fraction` is `tail_events / (kept_events + tail_events)` over the
in-scope instances — the quantity the calibration self-check asserts is
< 5 %. The reducers (src/output/*summarise.py) then run on the kept
[0, W] event stream (decided + transport, both window-bounded).

Note: this is a PURE filter — no clock reads, no RNG. The reducer's
`commit_latency_ms` is the FIRST in-window decision, always ≪ W, so the
clip never perturbs latency; it only trims the rate's denominator-tail
and aligns the overhead numerator to the same [0, W] window.

Design contract: wiki/experiments/2026-06-10_delay-moderate.md
"""
from __future__ import annotations

from dataclasses import dataclass

from event_log import EventRecord


@dataclass(frozen=True)
class ClipStats:
    """Per-run clip bookkeeping (one row's worth)."""
    in_scope_instances: int     # distinct instances started in [0, W]
    kept_events: int            # in-scope decided events with t <= W
    tail_events: int            # in-scope decided events with t > W (clipped)
    late_events: int            # decided events of instances started past W
    clipped_fraction: float     # tail / (kept + tail); the < 5 % guard


def clip_records(records: list[EventRecord], window_s: float,
                 one_round_s: float) -> tuple[list[EventRecord], ClipStats]:
    """Return `(kept_records, stats)`.

    `kept_records` is every event with `t <= window_s` (decided events
    must additionally be in-scope, but any decided with `t <= window_s`
    already is). `stats` carries the clip bookkeeping, including
    `clipped_fraction` for the calibration assertion.
    """
    decided = [r for r in records if r.event_type == "decided"]

    # First-decision time per instance.
    first: dict[object, float] = {}
    for r in decided:
        iid = r.fields.get("instance_id")
        t = r.t
        if iid not in first or t < first[iid]:
            first[iid] = t

    # Scope: instance started in [0, W]  ⇔  first decision <= W + one_round.
    scope_bound = window_s + one_round_s
    in_scope = {iid for iid, ft in first.items() if ft <= scope_bound}

    kept_events = 0
    tail_events = 0
    late_events = 0
    kept_decided: list[EventRecord] = []
    for r in decided:
        iid = r.fields.get("instance_id")
        if iid in in_scope:
            if r.t <= window_s:
                kept_events += 1
                kept_decided.append(r)
            else:
                tail_events += 1            # in-scope tail past W: clipped
        else:
            late_events += 1                # started in buffer: excluded

    denom = kept_events + tail_events
    clipped_fraction = (tail_events / denom) if denom else 0.0

    # Reassemble in original chronological order, clipping EVERY event at
    # t > W (the locked rule). Decided events additionally must be in the
    # kept set; since kept decided all have t <= W, the time clip alone
    # already drops every out-of-window decided, so this is one rule:
    # keep iff t <= W and (not a decided OR a kept decided).
    kept_ids = {id(r) for r in kept_decided}
    kept_records = [
        r for r in records
        if r.t <= window_s and (r.event_type != "decided" or id(r) in kept_ids)
    ]

    stats = ClipStats(
        in_scope_instances=len(in_scope),
        kept_events=kept_events,
        tail_events=tail_events,
        late_events=late_events,
        clipped_fraction=clipped_fraction,
    )
    return kept_records, stats
