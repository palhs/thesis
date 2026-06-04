"""T41 — shared, pure metric helpers for the workload axis.

Computes the two T41 reducer columns that depend on the deterministic
transaction stream rather than on protocol-internal FSM state:

  - `goodput`        — committed valid transactions per unit time.
  - `bytes_per_acu`  — an honest order-of-magnitude wire-byte budget per
                       atomic-commit-unit (ACU), summed over delivery
                       events from the per-message-type size table.

Design spec:    docs/superpowers/specs/2026-05-30-t41-scaling-workload-design.md
Design contract: wiki/concepts/output-format.md §5 (per-protocol derivation),
                 wiki/concepts/message-types.md §3–§7 (size budgets).

These helpers are pure functions of their arguments: no wallclock, no
module-level RNG. `committed_tx` re-derives the deterministic batch
stream from the scenario metadata (same `(config, global_seed)` →
identical stream, per the generator's byte-identical contract), so the
reducer that calls it stays reproducible.
"""
from __future__ import annotations

from typing import Any

from event_log import EventRecord
from output.schema import ScenarioMeta
from workload import WorkloadConfig, generate_batches


# --- Per-message-type byte budgets ---------------------------------------
#
# Fixed component widths from message-types.md §7:
#   NodeId / validator index = 4; slot/epoch/view/seq/round = 8;
#   hash digest = 32; per-validator signature = 64.
#
# Each entry below is the sum of a message type's FIXED-width payload
# components ONLY — the variable `transactions` component is NOT included
# here. For transaction-carrying types (see `_TX_CARRYING`) the caller
# adds `offered_rate * interval * tx_bytes` on top of the fixed budget.
#
# Source: the per-type `Size (bytes)` column in message-types.md §3–§7,
# with the §4/§5 T32/T38 Revisions noted where they change the count.
# These budgets are explicitly an honest order-of-magnitude estimate and
# are declared non-binding by message-types.md §7.
_BASE_BUDGET: dict[str, int] = {
    # PBFT (§3). request_payload (tx) excluded — added via _TX_CARRYING.
    "PRE-PREPARE": 8 + 8 + 32,                 # view + seq + request_digest
    "PREPARE":     8 + 8 + 32,                 # view + seq + request_digest
    "COMMIT":      8 + 8 + 32,                 # view + seq + request_digest
    "REPLY":       8 + 8 + 32 + 4,             # view + seq + request_digest
                                               #   + replica_id (T70 finding #1
                                               #   client-observed finality)
    "VIEW-CHANGE": 8 + 8,                      # new_view + last_stable_seq
                                               #   (k·evidence = 0 on the
                                               #   honest path; §3 + T29 Rev)
    "NEW-VIEW":    8,                          # new_view (proofs/reissued
                                               #   empty on honest path; §3)
    # Casper FFG (§4). transactions on BLOCK-PROPOSAL added via _TX_CARRYING.
    # §4 size column kept as-written (catalog values, an upper bound; the
    # T32 Revision notes the implementation omits sig/head_vote fields).
    "BLOCK-PROPOSAL":    8 + 8 + 32 + 32 + 4 + 64,   # slot+epoch+parent+
                                                     #   block_hash+
                                                     #   proposer_idx+sig
    "ATTESTATION":       8 + 8 + 32 + 40 + 40 + 4 + 64,  # slot+epoch+head+
                                                         #   ffg_src+ffg_tgt+
                                                         #   attester_idx+sig
    "SLASHING-EVIDENCE": 4 + 1 + 2 * (8 + 8 + 32 + 40 + 40 + 4 + 64),
                                               # offender+kind+2·ATTESTATION
    # Snowman (§5). transactions on BLOCK-ANNOUNCEMENT via _TX_CARRYING.
    "BLOCK-ANNOUNCEMENT": 32 + 32 + 4,         # block_id+parent_id+
                                               #   proposer_idx
    "QUERY":              8 + 32,              # request_id + block_id
    "QUERY-RESPONSE":     8 + 32,              # request_id + preferred_block_id
}

# Message types whose payload carries the proposal's transaction batch.
# For these, the full transaction-component byte cost
# `offered_rate * interval * tx_bytes` is added to the fixed base budget.
_TX_CARRYING: frozenset[str] = frozenset({
    "PRE-PREPARE",          # PBFT primary proposal
    "BLOCK-PROPOSAL",       # Casper FFG slot proposal
    "BLOCK-ANNOUNCEMENT",   # Snowman slot announcement
})


def committed_tx(meta: ScenarioMeta, n_opportunities: int) -> int:
    """Total committed transactions over the first `n_opportunities`
    proposal opportunities.

    Re-derives the deterministic batch stream from the scenario metadata
    (the same stream the proposers consumed) and sums batch sizes. With
    `conflict_rate == 0` every committed transaction is valid, so this is
    the tx-level committed count. Returns 0 for a non-positive opportunity
    count.
    """
    if n_opportunities <= 0:
        return 0
    cfg = WorkloadConfig(meta.arrival_process, meta.offered_rate,
                         meta.tx_bytes, meta.conflict_rate)
    batches = generate_batches(cfg, meta.seed, n_opportunities, meta.interval)
    return sum(len(b) for b in batches)


def goodput(meta: ScenarioMeta, n_opportunities: int,
            time_denom: float) -> float:
    """Committed transactions per unit time = `committed_tx / time_denom`.

    NaN when the time denominator is non-positive or there are no
    committed opportunities (the rate is undefined).
    """
    if time_denom > 0 and n_opportunities > 0:
        return committed_tx(meta, n_opportunities) / time_denom
    return float("nan")


def bytes_per_acu(records: list[EventRecord], meta: ScenarioMeta) -> float:
    """Honest order-of-magnitude wire-byte budget per ACU.

    `Σ over delivery events of base_budget(msg_type) ÷ decided_count`,
    where `base_budget(mt)` is the fixed per-type byte budget from
    `_BASE_BUDGET`, plus `offered_rate * interval * tx_bytes` when `mt`
    is transaction-carrying. `decided_count` is the raw number of decided
    EVENTS (not deduplicated by instance), matching the sibling
    `consensus_msgs_per_acu = delivery_count / decided_count` convention
    in the reducers.

    NaN when no decided events fired (the denominator is undefined).

    Raises:
      KeyError — a delivery event carries a `msg_type` absent from
                 `_BASE_BUDGET` (fail-fast; an unbudgeted type must not
                 be silently scored as zero).
    """
    decided_count = sum(1 for r in records if r.event_type == "decided")
    if decided_count == 0:
        return float("nan")
    tx_component = meta.offered_rate * meta.interval * meta.tx_bytes
    total = 0.0
    for r in records:
        if r.event_type != "delivery":
            continue
        mt = r.fields["msg_type"]
        budget = _BASE_BUDGET[mt]          # KeyError on unbudgeted type
        if mt in _TX_CARRYING:
            budget += tx_component
        total += budget
    return total / decided_count
