"""T40 — PBFT reducer.

Per-block deterministic finality: commit_latency = finality_latency.
fork_rate = 0 by construction (PBFT cannot fork below f).

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

    if decided:
        # Median per-node decision time for the first decided instance.
        first_inst = decided[0].fields.get("instance_id")
        first_inst_ts = [r.t for r in decided
                         if r.fields.get("instance_id") == first_inst]
        latency_ms = statistics.median(first_inst_ts) * 1000.0
        success_rate = 1.0
    else:
        latency_ms = float("nan")
        success_rate = 0.0

    # Throughput on the quiescence path: decided events / final t.
    if decided and result.now > 0:
        tps = len(decided) / result.now
    else:
        tps = float("nan")

    if decided:
        consensus_msgs_per_acu = len(deliveries) / len(decided)
    else:
        consensus_msgs_per_acu = float("nan")

    return {
        "commit_latency_ms":      latency_ms,
        "finality_latency_ms":    latency_ms,   # PBFT: commit ≡ finality
        "tps":                    tps,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "success_rate":           success_rate,
        "fork_rate":              0.0,
        "K":                      float("nan"),
        "alpha_p":                float("nan"),
        "alpha_c":                float("nan"),
        "beta":                   float("nan"),
        "alpha_c_over_K":         float("nan"),
    }
