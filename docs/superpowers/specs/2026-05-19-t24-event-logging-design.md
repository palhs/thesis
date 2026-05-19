# T24 — Logging for consensus events: design spec

Engineer-register design spec for T24, consumed by `superpowers:writing-plans`.
Implements the structured event-logging subsystem that records the simulator's
consensus event stream and exports it to CSV. The scheduler it observes (T21),
the `Node` it co-operates with (T22), and the `Network` it sees deliveries from
(T23) are all complete in `src/`.

- **Task:** T24 (`TASKS.md`, Week 4) — Add logging for consensus events.
  Role: Engineer. Priority M. Artifact: `src/event_log/` (see Decision E — the
  `TASKS.md` entry's literal `src/logging/` is a documented deviation).
- **Design contract surface:** `wiki/concepts/simulation-design.md` §4–§6
  (`event_sink`, `RunResult`, the event taxonomy); `wiki/concepts/node-model.md`
  §3 / §4 / §7 (the `emit` API and the mandatory `halted` / `decided` events).
- **Upstream code:** `src/scheduler/scheduler.py` — `Scheduler.event_sink`, the
  `bind()` emit lambda, the `run()` dispatch loop; `src/scheduler/events.py` —
  `Delivery` / `TimerFire` / `PhaseAdvance`; `src/nodes/node.py` — `Node.emit`,
  `Node.halt`, `Node._emit_decided`; `src/nodes/message.py` — the `Message`
  envelope; `src/network/network.py` — broadcast expansion (motivates the
  `msg_id` decision, Decision D).

## 1. Scope

T24 builds the **complete event-logging subsystem** — a passive `event_sink`
consumer that normalises the scheduler's heterogeneous event stream into a
uniform record type, buffers the records in memory, and exports them to CSV.

In scope:

- The `EventLogger` class and `EventRecord` record type (`src/event_log/`).
- A shared event-type name vocabulary (`src/event_log/event_types.py`).
- Adoption of that vocabulary in `src/nodes/node.py` for the `halted` /
  `decided` emit calls — closing the `TASKS.md` § Backlog item that names T24.
- Unit + e2e tests; a build-verification experiment page.
- A new wiki concept page pinning the event-log schema and the `event_sink`
  emit-tuple seam.

Out of scope, deferred to the owning task:

- The unified cross-protocol metrics CSV — T40 (`wiki/concepts/output-format.md`).
  T24's CSV is the **raw event log**; T40 *derives* the metrics dataset from it.
  T24 does not pin T40's column set.
- Protocol-specific event types (FSM transitions, vote events) — T28+. The open
  `fields` dict (§3.2) absorbs them with no schema change.
- YAML config, `global_seed` sourcing, the run harness that calls `to_csv()` —
  T19 / T27. T24's logger is constructed and exported in code/tests.
- The scrambled-call-order cross-component determinism test — T25 (`TASKS.md`
  § Backlog). T24 ships its own logger-level determinism check (§7).

### Settled design decisions

Taken with the human at brainstorming (2026-05-19):

- **Decision A — core columns + open `fields` dict.** The CSV has fixed core
  columns (`t`, `node_id`, `event_type`, `seq`) plus one `fields` column holding
  an open key/value map. T24's prescribed `round` / `msg_id` columns have no
  source in the current event stream (`round` is T28+ FSM state; the `Message`
  envelope carries no id); they become `fields` keys populated when protocol
  code emits them, with no schema migration.
- **Decision B — in-memory buffer + explicit export.** The logger appends to an
  in-memory `records` list; an explicit `to_csv(path)` call writes the file.
  Records stay queryable in-process for tests and T40. A crash mid-run loses the
  log — acceptable at thesis scale (modest event count per run).
- **Decision C — shared event-type constants, adopted in `node.py`.** Event-type
  names live in `src/event_log/event_types.py` as module constants. `node.py` is
  updated to import and use `HALTED` / `DECIDED` instead of the bare string
  literals, so a rename fails fast (`NameError`). Lands as a `## Revisions`
  entry on `node-model.md` (§6).
- **Decision D — no logger-synthesized `msg_id`.** A content-hash `msg_id` was
  considered and rejected: broadcast expansion in `Network.submit_broadcast`
  fans one logical broadcast into N per-recipient `Delivery` events *before* the
  scheduler — and hence the logger — sees anything, so broadcast-grouping
  information is unrecoverable downstream. A hash over `(src, type, t_sent)`
  collides Snowman's `K` same-instant per-peer `send` queries; a hash including
  `dst` cannot group broadcast copies. The logger therefore synthesizes no
  `msg_id`; `delivery` events record the genuine envelope facts `{msg_type,
  src, dst}`, and `msg_id` remains a `fields` key for protocol code (T28+) that
  carries a real message id.
- **Decision E — package named `event_log`, not `logging`.** The project has no
  `pyproject.toml` / `conftest.py`; tests run via
  `PYTHONPATH=src:tests/<dir> python3 -m unittest` (confirmed against the T23
  plan and the existing suite). `src/` is therefore a path root and every
  directory beneath it is a *top-level* package. A `src/logging/` directory
  would be importable as `logging` and, with `src` on `PYTHONPATH`, would
  **shadow the standard-library `logging` module** for the whole process — a
  latent break (e.g. any future `assertLogs` test imports `unittest._log`,
  which does `import logging`). The subsystem is therefore named `event_log`.
  The `TASKS.md` T24 entry's literal `_Artifact: src/logging/` is a documented
  deviation per `docs/workflow.md` § Evolution; flagged in the handoff summary.

## 2. Module layout — `src/event_log/`

| File | Contents |
| :-- | :-- |
| `event_types.py` | event-type name constants; `TRANSPORT_EVENT_TYPES` frozenset |
| `logger.py` | `EventRecord` dataclass; `EventLogger` class |
| `__init__.py` | re-exports `EventLogger`, `EventRecord`, the event-type constants |

The package is imported as the top-level name `event_log` (via `PYTHONPATH=src`,
the project convention). It imports the scheduler event classes for
`isinstance` checks via `from scheduler import Delivery, TimerFire,
PhaseAdvance` — the same top-level-package style used across `src/`
(cf. `network.py`'s `from scheduler import ...`). It does **not** import
`src/nodes/`; the dependency direction is `nodes → event_log` (§6), no cycle.

## 3. The contract

### 3.1. The `event_sink` seam (existing, observed)

`Scheduler.event_sink` is a single optional callback with signature
`Callable[[SimTime, NodeId, int, Event], None]`. It is invoked from **two**
sites in the current scheduler, producing a **heterogeneous** stream:

1. **`Scheduler.bind()`'s emit lambda** — for every `Node.emit(event_type,
   fields, t)` call, invokes `event_sink(t, node_id, EMIT_SEQ, ("emit",
   event_type, fields))`. `EMIT_SEQ` is the class constant `-1`; emit events
   carry no real per-Node `seq`.
2. **`Scheduler.run()`'s dispatch loop** — for every non-tombstoned popped
   event, invokes `event_sink(t, node_id, seq, event)` where `event` is a
   typed `Delivery` / `TimerFire` / `PhaseAdvance` dataclass and `seq` is the
   real per-Node sequence number.

The logger's `sink` is assigned to `event_sink` at bootstrap **phase 4**
(`simulation-design.md` §7.2). T24 does not change the scheduler; it documents
this two-shape seam in the wiki (§8) and consumes both shapes.

### 3.2. `EventRecord`

```python
@dataclass(frozen=True)
class EventRecord:
    t: float           # SimTime of the event
    node_id: int       # NodeId; -1 (PHASE_NODE_ID) for PhaseAdvance
    event_type: str    # one of the event_types.py constants
    seq: int           # per-Node seq; -1 (EMIT_SEQ) for emit events
    fields: dict       # open key/value map, event-type-specific
```

`fields` is the extensibility surface (Decision A): emit events pass their
`fields` dict through verbatim; transport events get a logger-derived dict
(§3.4). Protocol-specific keys (`round`, `view`, `msg_id`, …) land here with no
schema change.

### 3.3. `EventLogger`

```python
class EventLogger:
    records: list[EventRecord]
    def __init__(self) -> None: ...
    def sink(self, t, node_id, seq, payload) -> None: ...   # the event_sink callback
    def to_csv(self, path) -> None: ...
    def __len__(self) -> int: ...                            # len(logger) == len(records)
```

`sink` normalises and appends one `EventRecord`. `to_csv` writes the buffer.
The logger holds no file handle and no scheduler reference; it is a pure
passive recorder.

### 3.4. `sink` normalisation

`sink(t, node_id, seq, payload)` dispatches on the shape of `payload`:

| `payload` shape | `event_type` | `fields` |
| :-- | :-- | :-- |
| tuple `("emit", et, f)` | `et` (from the tuple) | `dict(f)` — copy of the emitted dict |
| `Delivery` | `DELIVERY` | `{"msg_type": msg.type, "src": msg.src, "dst": msg.dst}` |
| `TimerFire` | `TIMER_FIRE` | `{"timer_id": payload.timer_id}` |
| `PhaseAdvance` | `PHASE_ADVANCE` | `{"phase_id": payload.phase_id}` |
| anything else | — | `raise TypeError` (fail-fast, mirrors `Scheduler._dispatch`) |

The emit-tuple is recognised by `isinstance(payload, tuple) and len(payload) == 3
and payload[0] == "emit"`. Transport events are recognised by `isinstance`
against the imported event classes. `Delivery.msg` is the `Message` envelope;
`src` / `dst` / `type` are read off it. The `TimerFire` payload object is *not*
recorded — it is FSM-internal and may be large; only `timer_id` is kept.

### 3.5. `to_csv`

`to_csv(path)`:

- Creates parent directories (`Path(path).parent.mkdir(parents=True,
  exist_ok=True)`).
- Writes via the stdlib `csv` module. Header: `t,node_id,event_type,seq,fields`.
- One row per record, in `records` order. The `fields` cell is `repr()` of the
  dict **with keys sorted** — `repr(dict(sorted(fields.items())))` — which is
  deterministic and round-trips simple types (including the tuple `instance_id`
  of PBFT / Narwhal `decided` events) via `ast.literal_eval`.
- An empty buffer produces a header-only file.

## 4. Determinism

The logger must not break the byte-identical-replay contract
(`node-model.md` §8). Two properties guarantee this:

1. **Record order is dispatch order.** `sink` is called synchronously from the
   scheduler in event-dispatch order, which is deterministic by the
   `(t, node_id, seq)` tie-break. The logger appends in call order; it
   introduces no ordering of its own.
2. **Serialisation is order-stable.** `fields` is serialised with sorted keys,
   so the CSV cell is independent of dict insertion order. Float formatting via
   `repr()` is deterministic in CPython.

Consequence: two `global_seed`-identical runs produce byte-identical
`records` and byte-identical CSV output. This is asserted by a test (§7).

## 5. Error handling

- `sink` raises `TypeError` on an unrecognised `payload` shape — fail-fast,
  consistent with `Scheduler._dispatch`'s unknown-event-class guard. No silent
  drops.
- `to_csv` creates missing parent directories rather than failing.
- The scheduler's emit lambda already null-guards `event_sink`; the logger adds
  no guard of its own.
- The logger never raises from a *well-formed* event. A malformed event is a
  contract violation upstream and should surface loudly.

## 6. `node.py` adoption (Decision C)

`src/nodes/node.py` currently emits bare string literals: `self.emit("halted",
…)` in `halt()` and `self.emit("decided", …)` in `_emit_decided()`. T24 changes
both to import `HALTED` / `DECIDED` from `event_log.event_types` and use the
constants.

This is a deliberate edit outside `src/event_log/` — it is the `TASKS.md`
§ Backlog item that explicitly names T24 ("promote event-type names to a shared
constant/enum so a rename fails fast"). It lands as a dated `## Revisions` entry
on `wiki/concepts/node-model.md`, noting that the §7 event-emission table's
`halted` / `decided` names are now sourced from the shared `event_types`
module. Import direction is `nodes → event_log`; no cycle (`event_log` does not
import `nodes`; it `isinstance`-checks scheduler event classes only).

## 7. Build verification — tests

The project uses **`unittest`**, not `pytest` (no `pyproject.toml` /
`conftest.py`; T23 plan confirms). Tests are `unittest.TestCase` subclasses,
run via `PYTHONPATH=src:tests/event_log python3 -m unittest discover -s
tests/event_log -v`. Tests live in `tests/event_log/` — top-level `tests/`, as
for `tests/scheduler/`, `tests/nodes/`, `tests/network/`. (T24's `TASKS.md`
entry says `src/tests/`; the repo uses `tests/`.)

**Unit (`tests/event_log/test_logger.py`):**

- `sink` normalises an emit tuple → `EventRecord` with `event_type` and `fields`
  copied; `seq == -1`.
- `sink` normalises each of `Delivery` / `TimerFire` / `PhaseAdvance` → correct
  `event_type` and derived `fields`.
- `sink` raises `TypeError` on a garbage `payload`.
- `to_csv` writes the correct header and one row per record; `fields` cell is
  sorted-key `repr`.
- `to_csv` on an empty buffer → header-only file.
- `to_csv` creates missing parent directories.
- Determinism: two identical event sequences fed to two loggers → byte-identical
  CSV.

**e2e (`tests/event_log/test_e2e.py`):**

- Mirror the existing 2-node ping-pong baseline (`tests/scheduler/test_e2e.py`
  / `tests/network/test_e2e.py`), wire `scheduler.event_sink = logger.sink` at
  bootstrap phase 4, run to quiescence; assert the logger captured records
  spanning both emit and transport event types, and that `to_csv` produces a
  well-formed file.
- Two `global_seed`-identical full runs → byte-identical CSV.

`superpowers:verification-before-completion` is invoked before the task flips to
In Review.

## 8. Wiki deliverables

- **New `wiki/concepts/event-log-schema.md`** — pins the `event_sink`
  two-shape emit-tuple seam (§3.1), the `EventRecord` schema, the event-type
  vocabulary, the open-`fields` convention, and the CSV format. Added to
  `wiki/index.md` under Concepts.
- **`wiki/concepts/node-model.md`** — a dated `## Revisions` entry recording the
  Decision C constant adoption (§6).
- **`wiki/experiments/2026-05-19_logging-baseline.md`** — build-verification
  experiment page for the e2e run: config, seed, commit hash, re-run command,
  result location, one-paragraph observation (per the Engineer role). Records
  the Decision E deviation.
- **`wiki/log.md`** — one `code`-type task entry.

## 9. Deliverables summary

| Path | New / edit |
| :-- | :-- |
| `src/event_log/__init__.py` | new |
| `src/event_log/event_types.py` | new |
| `src/event_log/logger.py` | new |
| `src/nodes/node.py` | edit — adopt `HALTED` / `DECIDED` constants |
| `tests/event_log/test_logger.py` | new |
| `tests/event_log/test_e2e.py` | new |
| `wiki/concepts/event-log-schema.md` | new |
| `wiki/concepts/node-model.md` | edit — `## Revisions` entry |
| `wiki/index.md` | edit — index the new concept page |
| `wiki/experiments/2026-05-19_logging-baseline.md` | new |
| `wiki/log.md` | edit — task entry |
