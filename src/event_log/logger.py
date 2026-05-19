"""Structured event logger for the consensus simulator (T24).

A passive Scheduler.event_sink consumer: normalises the scheduler's
heterogeneous event stream (emit tuples + typed transport events) into
uniform EventRecords, buffers them, and exports to CSV.

Design contract: wiki/concepts/event-log-schema.md
Design spec: docs/superpowers/specs/2026-05-19-t24-event-logging-design.md
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scheduler import Delivery, PhaseAdvance, TimerFire

from .event_types import DELIVERY, PHASE_ADVANCE, TIMER_FIRE

_CSV_HEADER = ("t", "node_id", "event_type", "seq", "fields")


@dataclass(frozen=True)
class EventRecord:
    """One normalised entry in the event log (event-log-schema.md)."""
    t: float
    node_id: int
    event_type: str
    seq: int
    fields: dict


class EventLogger:
    """Passive event_sink consumer. Buffers EventRecords; exports to CSV.

    Wired at bootstrap phase 4: `scheduler.event_sink = logger.sink`
    (simulation-design.md §7.2). Holds no file handle and no scheduler
    reference — a pure passive recorder.
    """

    def __init__(self) -> None:
        self.records: list[EventRecord] = []

    def __len__(self) -> int:
        return len(self.records)

    def sink(self, t: float, node_id: int, seq: int,
             payload: Any) -> None:
        """The Scheduler.event_sink callback. Normalises one event into an
        EventRecord and appends it. Raises TypeError on an unknown shape.

        Two payload shapes (event-log-schema.md §seam):
          - ("emit", event_type, fields)  — from Node.emit() via bind()
          - a typed Delivery / TimerFire / PhaseAdvance — from run()
        """
        if (isinstance(payload, tuple) and len(payload) == 3
                and payload[0] == "emit"):
            _, event_type, fields = payload
            self.records.append(
                EventRecord(t, node_id, event_type, seq, dict(fields)))
        elif isinstance(payload, Delivery):
            msg = payload.msg
            self.records.append(EventRecord(
                t, node_id, DELIVERY, seq,
                {"msg_type": msg.type, "src": msg.src, "dst": msg.dst}))
        elif isinstance(payload, TimerFire):
            self.records.append(EventRecord(
                t, node_id, TIMER_FIRE, seq,
                {"timer_id": payload.timer_id}))
        elif isinstance(payload, PhaseAdvance):
            self.records.append(EventRecord(
                t, node_id, PHASE_ADVANCE, seq,
                {"phase_id": payload.phase_id}))
        else:
            raise TypeError(
                f"EventLogger.sink: unrecognised payload {payload!r}")

    def to_csv(self, path) -> None:
        """Write the buffered records to `path` as CSV. Creates parent
        directories. The `fields` cell is the sorted-key repr of the dict —
        deterministic (insertion-order-independent) and round-trips simple
        types, including the tuple instance_id of PBFT/Narwhal decided
        events, via ast.literal_eval. An empty buffer writes header only.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(_CSV_HEADER)
            for r in self.records:
                writer.writerow((
                    r.t, r.node_id, r.event_type, r.seq,
                    repr(dict(sorted(r.fields.items()))),
                ))
