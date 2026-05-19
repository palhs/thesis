"""Event-type name vocabulary for the structured event log (T24).

Single source of truth for the `event_type` string of every EventRecord.
Referencing a constant fails fast (NameError) on a typo; a bare string
literal does not. `src/nodes/node.py` imports HALTED / DECIDED from here
(node-model.md Revision 2026-05-19); the logger derives the transport names.

Design spec: docs/superpowers/specs/2026-05-19-t24-event-logging-design.md
"""
from __future__ import annotations

# Emit events — produced by Node.emit() (node-model.md §3 / §4 / §7).
HALTED = "halted"
DECIDED = "decided"

# Transport events — derived by the logger from the scheduler's typed
# event classes (simulation-design.md §5).
DELIVERY = "delivery"
TIMER_FIRE = "timer_fire"
PHASE_ADVANCE = "phase_advance"

# The event types the logger derives from a typed scheduler Event (as
# opposed to an ("emit", ...) tuple). Used by tests and documentation.
TRANSPORT_EVENT_TYPES = frozenset({DELIVERY, TIMER_FIRE, PHASE_ADVANCE})
