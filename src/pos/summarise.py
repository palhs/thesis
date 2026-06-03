"""T40 — Casper FFG reducer: maps (EventLogger.records, RunResult,
ScenarioMeta) to the protocol-specific columns of the unified CSV.

Per-column formulas pinned by wiki/concepts/output-format.md §Per-
protocol derivation rules / Casper FFG.

Design contract: wiki/concepts/output-format.md
Design spec:    docs/superpowers/specs/2026-05-28-t40-output-format-design.md
"""
from __future__ import annotations

import math
import statistics
from typing import Any

from event_log import EventRecord
from output.metrics import bytes_per_acu, goodput
from output.schema import ScenarioMeta
from scheduler import RunResult

# FFG node default slots_per_epoch (src/pos/node.py CasperNode default).
# Used when meta.slots_per_epoch is None (pre-Phase-4 metadata).
_SLOTS_PER_EPOCH = 2


def summarise(records: list[EventRecord],
              result: RunResult,
              meta: ScenarioMeta) -> dict[str, Any]:
    decided = [r for r in records if r.event_type == "decided"]
    deliveries = [r for r in records if r.event_type == "delivery"]

    # Per-node finalisation time of epoch 1 — the first finalised epoch
    # in every scenario. Median across nodes is the headline latency.
    epoch1 = [r.t for r in decided if r.fields.get("instance_id") == 1]
    if epoch1:
        latency_ms = statistics.median(epoch1) * 1000.0
        commit_latency_ms = latency_ms      # honest path: commit ≡ finality
        finality_latency_ms = latency_ms
        success_rate = 1.0
    else:
        commit_latency_ms = float("nan")
        finality_latency_ms = float("nan")
        success_rate = 0.0

    # Throughput: decided events per simulated second over the window.
    if not math.isnan(meta.t_max):
        tps = len(decided) / meta.t_max
    else:
        tps = float("nan")

    # Consensus messages per ACU: deliveries / decided. Honest path has
    # one decided per epoch per node; ACU is one finalised checkpoint
    # so we divide by decided count (= n × #epochs).
    if decided:
        consensus_msgs_per_acu = len(deliveries) / len(decided)
    else:
        consensus_msgs_per_acu = float("nan")

    # Workload axis (T41). FFG `decided` fires once per FINALISED EPOCH,
    # but transactions live in per-SLOT blocks: each finalised epoch
    # accounts for `slots_per_epoch` proposal opportunities. Indexing
    # assumption: FFG proposes from slot 1 (slot 0 = genesis, no batch —
    # src/pos/node.py `_on_start`). We map each distinct decided epoch to
    # `slots_per_epoch` batch opportunities; this slightly over-counts the
    # single genesis slot at the very start, an acceptable
    # order-of-magnitude approximation for the goodput estimate.
    # `slots_per_epoch` comes from meta (set by the FFG baseline in
    # Phase 4); falls back to the node default when None.
    slots_per_epoch = (meta.slots_per_epoch if meta.slots_per_epoch is not None
                       else _SLOTS_PER_EPOCH)
    n_epochs = len({r.fields.get("instance_id") for r in decided})
    n_opportunities = n_epochs * slots_per_epoch
    time_denom = float("nan") if math.isnan(meta.t_max) else meta.t_max
    gp = goodput(meta, n_opportunities, time_denom)
    bpa = bytes_per_acu(records, meta)

    return {
        "commit_latency_ms":      commit_latency_ms,
        "finality_latency_ms":    finality_latency_ms,
        "tps":                    tps,
        "goodput":                gp,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "bytes_per_acu":          bpa,
        "success_rate":           success_rate,
        "fork_rate":              0.0,   # honest baseline; never forks
        "K":                      float("nan"),
        "alpha_p":                float("nan"),
        "alpha_c":                float("nan"),
        "beta":                   float("nan"),
        "alpha_c_over_K":         float("nan"),
    }
