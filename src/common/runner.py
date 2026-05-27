"""Post-build half of the six-phase bootstrap (T39).

`run_to_completion` attaches an EventLogger to the scheduler's
event_sink, runs the scheduler to its stop condition, and returns
(RunResult, EventLogger). Pass-through over `RunHandle`; no scheduler-
layer adversary hook (that surface belongs to T18); no CSV output
(that surface belongs to T40).

Design contract: wiki/concepts/runner.md
Design spec:    docs/superpowers/specs/2026-05-27-t39-unified-runner-design.md
"""
from __future__ import annotations

from config.schema import RunHandle
from event_log import EventLogger
from scheduler import RunResult


def run_to_completion(
    handle: RunHandle,
    *,
    t_max: float | None = None,
    logger: EventLogger | None = None,
) -> tuple[RunResult, EventLogger]:
    """Attach a logger, run the scheduler, return (RunResult, EventLogger).

    `t_max=None` runs to quiescence (matches PBFT honest path).
    `t_max=<float>` runs to deadline (matches Casper / Snowman, which
    have no natural quiescence).

    A freshly-constructed `EventLogger` is used if `logger is None`;
    callers that want to share or pre-seed a logger may pass one. The
    same logger object is returned, so callers can introspect
    `logger.records` after the run.
    """
    if logger is None:
        logger = EventLogger()
    handle.scheduler.event_sink = logger.sink
    if t_max is None:
        result = handle.scheduler.run()
    else:
        result = handle.scheduler.run(t_max=t_max)
    return result, logger
