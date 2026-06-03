"""T40 — PBFT reducer.

Per-block deterministic finality. fork_rate = 0 by construction (PBFT
cannot fork below f).

T70 finding #1 — client-observed finality. `commit_latency_ms` is measured
at the internal 2f+1 COMMIT quorum (the `decided` events). `finality_latency_ms`
is now the *client-observed* finality, one network hop later: the time the
client-reply collector (the committing view's primary) saw f+1 matching
REPLYs and emitted `pbft_client_finalized`. On the honest baseline this is
strictly greater than `commit_latency_ms`. Both are defined on the FIRST
finalized / decided instance (output-format.md §5.1).

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


def summarise(records: list[EventRecord],
              result: RunResult,
              meta: ScenarioMeta) -> dict[str, Any]:
    decided = [r for r in records if r.event_type == "decided"]
    deliveries = [r for r in records if r.event_type == "delivery"]
    finalized = [r for r in records
                 if r.event_type == "pbft_client_finalized"]

    if decided:
        # Median per-node decision time (COMMIT quorum) for the first decided
        # instance — `commit_latency_ms`.
        first_inst = decided[0].fields.get("instance_id")
        first_seq = first_inst[1] if isinstance(first_inst, tuple) else None
        first_inst_ts = [r.t for r in decided
                         if r.fields.get("instance_id") == first_inst]
        commit_latency_ms = statistics.median(first_inst_ts) * 1000.0
        success_rate = 1.0
    else:
        commit_latency_ms = float("nan")
        first_seq = None
        success_rate = 0.0

    # T70 finding #1 — client-observed finality is one network hop past the
    # COMMIT quorum. `finality_latency_ms` is the time the client-reply
    # collector emitted `pbft_client_finalized` for the SAME seq as the first
    # decided instance (one collector emit per seq → median of one value).
    # Falls back to the earliest finalize, then to commit_latency, so a run
    # that decided but (degenerately) logged no finalize is still summarised.
    if finalized:
        match = [r.fields["t"] for r in finalized
                 if r.fields.get("seq") == first_seq]
        finality_ts = match if match else [finalized[0].fields["t"]]
        finality_latency_ms = statistics.median(finality_ts) * 1000.0
    else:
        finality_latency_ms = commit_latency_ms

    # Throughput on the quiescence path: decided events / final t.
    if decided and result.now > 0:
        tps = len(decided) / result.now
    else:
        tps = float("nan")

    if decided:
        consensus_msgs_per_acu = len(deliveries) / len(decided)
    else:
        consensus_msgs_per_acu = float("nan")

    # Workload axis (T41). PBFT: one decided instance = one batch
    # opportunity, so n_opportunities is the distinct decided instance
    # count; the throughput denominator matches `tps` (result.now,
    # output-format.md §5.1).
    n_opportunities = len({r.fields.get("instance_id") for r in decided})
    gp = goodput(meta, n_opportunities, result.now)
    bpa = bytes_per_acu(records, meta)

    return {
        "commit_latency_ms":      commit_latency_ms,   # 2f+1 COMMIT quorum
        "finality_latency_ms":    finality_latency_ms,  # f+1 client REPLYs
        "tps":                    tps,
        "goodput":                gp,
        "consensus_msgs_per_acu": consensus_msgs_per_acu,
        "bytes_per_acu":          bpa,
        "success_rate":           success_rate,
        "fork_rate":              0.0,
        "K":                      float("nan"),
        "alpha_p":                float("nan"),
        "alpha_c":                float("nan"),
        "beta":                   float("nan"),
        "alpha_c_over_K":         float("nan"),
    }
