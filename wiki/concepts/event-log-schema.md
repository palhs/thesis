# Event-log schema

The structured event log produced by `src/event_log/` (T24). A passive
recorder that observes the simulator's consensus event stream, normalises it
into a uniform record type, and exports it to CSV. This page pins the schema
and the cross-component seam the logger consumes.

The event log is the **raw event substrate**. It is not the metrics dataset:
T40 ([[concepts/output-format]]) *derives* the unified cross-protocol metrics
CSV from these records. T24 does not pin T40's column set.

## Purpose

The simulator emits a heterogeneous stream of events during a run — node
lifecycle events, message deliveries, timer fires, network-phase transitions.
The event log captures that stream as an ordered sequence of uniform
`EventRecord`s and writes it to a CSV file. Downstream analysis (T40 metrics,
adversarial-experiment invariant checks) reads the log rather than
instrumenting the protocols directly.

The subsystem is a *passive* consumer: it holds no scheduler reference and no
file handle, never schedules events, and never raises from a well-formed
event. It only observes.

## The `event_sink` seam

`Scheduler.event_sink` ([[concepts/simulation-design]] §4) is a single
optional callback, `Callable[[SimTime, NodeId, int, Event], None]`, assigned
at bootstrap **phase 4** (`simulation-design` §7.2) as
`scheduler.event_sink = logger.sink`. The scheduler invokes it from **two**
sites, producing a stream of **two distinct payload shapes**:

1. **Emit tuple** — `Scheduler.bind()`'s emit lambda. For every
   `Node.emit(event_type, fields, t)` call ([[concepts/node-model]] §7) it
   invokes `event_sink(t, node_id, EMIT_SEQ, ("emit", event_type, fields))`.
   The payload is the 3-tuple `("emit", event_type, fields)`. `EMIT_SEQ` is
   the scheduler constant `-1`: emit events carry no real per-node sequence
   number.

2. **Typed transport event** — `Scheduler.run()`'s dispatch loop. For every
   non-tombstoned popped event it invokes `event_sink(t, node_id, seq, event)`
   where `event` is a typed `Delivery` / `TimerFire` / `PhaseAdvance`
   dataclass ([[concepts/simulation-design]] §5) and `seq` is the real
   per-node sequence number. A `PhaseAdvance` carries `node_id == -1`
   (`PHASE_NODE_ID`): it is not attributable to any single node.

This two-shape seam is a cross-component contract — `Node.emit` →
`Scheduler.event_sink` → `EventLogger.sink`. T24 does not modify the
scheduler; it documents the seam here and consumes both shapes.

## `EventRecord` schema

Every entry in the log is one `EventRecord` (frozen dataclass), five fields:

| Field | Type | Meaning |
| :-- | :-- | :-- |
| `t` | `float` | `SimTime` of the event |
| `node_id` | `int` | `NodeId`; `-1` for `PhaseAdvance` (`PHASE_NODE_ID`) |
| `event_type` | `str` | one of the `event_types.py` constants |
| `seq` | `int` | per-node sequence number; `-1` for emit events (`EMIT_SEQ`) |
| `fields` | `dict` | open key/value map, event-type-specific |

The four scalar columns are fixed; `fields` is the **extensibility surface**
(design Decision A). T24's `TASKS.md` brief named `round` and `msg_id` as
columns, but neither has a source in the current event stream — `round` is
T28+ FSM state, and the `Message` envelope carries no id. They are therefore
`fields` *keys*, populated when protocol code emits them, with no schema
migration. Anything a future event needs lands in `fields`; the four columns
never change.

## Event-type vocabulary

`src/event_log/event_types.py` is the single source of truth for the
`event_type` string of every record. Referencing a constant fails fast
(`NameError`) on a typo; a bare string literal does not.

| Constant | Value | Shape | Emitted by |
| :-- | :-- | :-- | :-- |
| `HALTED` | `"halted"` | emit | `Node.halt` ([[concepts/node-model]] §3) |
| `DECIDED` | `"decided"` | emit | `Node._emit_decided` ([[concepts/node-model]] §7) |
| `DELIVERY` | `"delivery"` | transport | `Delivery` dispatch ([[concepts/network-model]]) |
| `TIMER_FIRE` | `"timer_fire"` | transport | `TimerFire` dispatch |
| `PHASE_ADVANCE` | `"phase_advance"` | transport | `PhaseAdvance` dispatch |

`TRANSPORT_EVENT_TYPES` is the frozenset of the three transport names — the
event types the logger derives from a typed scheduler `Event` rather than
from an `("emit", …)` tuple.

`node.py` imports `HALTED` / `DECIDED` from this module (see the
[[concepts/node-model]] §7 Revision 2026-05-19). Protocol-specific event
types — FSM transitions, vote events — arrive with T28+ and extend this
vocabulary; they need no schema change, only a new constant.

## Per-event `fields`

`sink` derives `fields` by payload shape:

| Payload | `event_type` | `fields` |
| :-- | :-- | :-- |
| `("emit", et, f)` | `et` | `dict(f)` — a *copy* of the emitted dict |
| `Delivery` | `delivery` | `{"msg_type", "src", "dst"}` from the `Message` envelope |
| `TimerFire` | `timer_fire` | `{"timer_id"}` only |
| `PhaseAdvance` | `phase_advance` | `{"phase_id"}` |
| anything else | — | `raise TypeError` (fail-fast) |

Emit `fields` is copied, not aliased, so a later mutation of the caller's
dict cannot corrupt a buffered record. The `TimerFire` *payload* object is
deliberately **not** recorded — it is FSM-internal and may be large; only
`timer_id` is kept. The emit-tuple is recognised structurally
(`isinstance(payload, tuple) and len(payload) == 3 and payload[0] == "emit"`);
transport events by `isinstance` against the imported event classes. An
unrecognised payload raises `TypeError` — fail-fast, mirroring
`Scheduler._dispatch`'s unknown-event guard. No silent drops.

## `msg_id`

The logger synthesizes **no** `msg_id` (design Decision D). A content-hash id
was considered and rejected: `Network` broadcast expansion fans one logical
broadcast into N per-recipient `Delivery` events *before* the scheduler — and
hence the logger — sees anything, so broadcast-grouping information is
unrecoverable downstream. A hash over `(src, type, t_sent)` would collide
Snowman's `K` same-instant per-peer query `send`s; a hash including `dst`
cannot group broadcast copies. `delivery` events therefore record the genuine
envelope facts `{msg_type, src, dst}`, and `msg_id` remains a `fields` key
reserved for protocol code (T28+) that carries a real message id.

## CSV format

`EventLogger.to_csv(path)` writes the buffer via the stdlib `csv` module:

- Header row: `t,node_id,event_type,seq,fields`.
- One row per record, in `records` (dispatch) order.
- The `fields` cell is `repr(dict(sorted(fields.items())))` — the dict
  serialised with **sorted keys**. This is deterministic, insertion-order
  independent, and round-trips simple types — including the tuple
  `instance_id` of PBFT / Narwhal `decided` events — via `ast.literal_eval`.
- Missing parent directories are created.
- An empty buffer produces a header-only file.

Records are buffered in memory and written only on an explicit `to_csv` call
(design Decision B). They stay queryable in-process for tests and T40. A
crash mid-run loses the log — acceptable at thesis scale.

## Determinism

The logger preserves the byte-identical-replay contract
([[concepts/node-model]] §8). Two properties guarantee it:

1. **Record order is dispatch order.** `sink` is called synchronously from
   the scheduler in event-dispatch order, deterministic by the
   `(t, node_id, seq)` tie-break. The logger appends in call order and
   imposes no order of its own.
2. **Serialisation is order-stable.** `fields` is serialised with sorted
   keys, so the CSV cell is independent of dict insertion order; CPython
   `repr()` float formatting is deterministic.

Consequence: two `global_seed`-identical runs produce byte-identical
`records` and byte-identical CSV output.

## Related pages

- [[concepts/simulation-design]] — the `Scheduler`, `event_sink`, and the
  typed event taxonomy this log observes.
- [[concepts/node-model]] — the `Node.emit` API and the mandatory `halted` /
  `decided` events.
- [[concepts/network-model]] — the `Message` envelope and the broadcast
  expansion that motivates the no-`msg_id` decision.
- [[concepts/evaluation-metrics]] — the metric definitions the derived
  dataset reports.
- [[concepts/output-format]] — T40, the unified metrics CSV *derived* from
  this raw event log.

## Revisions

- **2026-05-28 by T40.** The unified comparative CSV produced by
  `src/output/csv.py` (see [[concepts/output-format]]) is a sibling
  consumer of the same `EventLogger.records` substrate this page
  describes. The two CSVs are *both* derived from the raw event log,
  with different column sets and different row granularities: the
  event-log CSV (this page) is one row per `EventRecord`, dispatch-
  ordered; the comparative CSV (output-format) is one row per
  `(protocol, scenario, seed)` simulation run.
