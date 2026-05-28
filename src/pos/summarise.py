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
from output.schema import ScenarioMeta
from scheduler import RunResult


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

    return {
        "commit_latency_ms":      commit_latency_ms,
        "finality_latency_ms":    finality_latency_ms,
        "tps":                    tps,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "success_rate":           success_rate,
        "fork_rate":              0.0,   # honest baseline; never forks
        "K":                      float("nan"),
        "alpha_p":                float("nan"),
        "alpha_c":                float("nan"),
        "beta":                   float("nan"),
        "alpha_c_over_K":         float("nan"),
    }
