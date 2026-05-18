# T22 — Node objects with state management: design spec

Engineer-register design spec for T22, consumed by `superpowers:writing-plans`.
Implements the shared lifecycle layer of the validator abstraction defined by
the T14 design contract `wiki/concepts/node-model.md`. The discrete-event
scheduler it binds against (T21) is complete in `src/scheduler/`.

- **Task:** T22 (`TASKS.md`, Week 4) — Implement node objects with state
  management. Role: Engineer. Artifact: `src/nodes/`.
- **Design contract:** `wiki/concepts/node-model.md` (T14).
- **Upstream code:** `src/scheduler/` (T21) — `Scheduler.bind`, `RunResult`,
  the six-phase bootstrap.

## 1. Scope

T22 builds **only the shared lifecycle layer** — the abstract `Node` base
class every protocol's validator subclasses. Per `node-model.md §1`
(two-layer commitment), the per-protocol FSM layer is out of scope:

- `PBFTNode` → T28; the PoS/Casper node → T32; the third algorithm → T38.
- T22 does **not** create stub files for those subclasses (scope discipline,
  `docs/workflow.md` § Scope).
- Per-protocol FSM instance tables, vote counting, view change, etc. — all
  deferred to the protocol tasks.
- `AdversaryProfile` internals — owned by T18; T22 ships only the opaque slot
  and a placeholder type.

The end-to-end test exercises a throwaway minimal `Node` subclass defined
inside the test file (a ping-pong protocol), not production code.

### Settled design decisions

Two decisions were taken with the human before this spec was written:

- **Seam = subclassing.** The shared `Node` is an abstract base; each protocol
  subclasses it (`PBFTNode(Node)`, …) — matching the `node-model.md §10`
  reference sketch literally. No contract Revision needed for the seam.
- **`Message` envelope owned by T22.** `node-model.md §6` declares the
  envelope; T22 implements it as a dataclass in `src/nodes/message.py`. T23
  (network) imports it rather than redefining. Decision A.
- **Stable RNG seed hash.** Per-Node RNG is seeded with a `blake2b`-derived
  stable hash, not Python's process-randomised `hash()`. Recorded as a
  `## Revisions` entry on `node-model.md §8`. Decision B.

## 2. Module layout — `src/nodes/`

| File | Contents |
| :-- | :-- |
| `node.py` | `Node` ABC — identity, lifecycle, RNG, inbound hooks, outbound placeholders, adversary slot |
| `lifecycle.py` | `Lifecycle` and `HaltReason` enums |
| `message.py` | `Message` envelope dataclass |
| `__init__.py` | package exports: `Node`, `Lifecycle`, `HaltReason`, `Message`, `AdversaryProfile` |

Tests land in `tests/nodes/` (mirrors `tests/scheduler/` from T21).

## 3. `Message` envelope — `message.py`

Realises `node-model.md §6`. Frozen dataclass, no behaviour.

```python
@dataclass(frozen=True)
class Message:
    src:     int          # NodeId of the sender
    dst:     int | str    # NodeId, or the literal "broadcast"
    type:    str          # protocol-specific tag (filled by T16/message-types)
    payload: object       # T16-defined per (protocol, type); Any at this layer
    t_sent:  float        # SimTime, set by the sender on emission
```

`payload` stays `object`/`Any` per `node-model.md §11` (T16 may tighten it to
a per-protocol union later). `t_sent` survives delivery so latency metrics
(`t - t_sent`) have an authoritative source.

## 4. `Lifecycle` / `HaltReason` — `lifecycle.py`

```python
class Lifecycle(Enum):
    CREATED = 0
    RUNNING = 1
    HALTED  = 2

class HaltReason(Enum):
    RUN_END = 0   # harness: configured stop condition reached
    CRASHED = 1   # harness: explicit fault injection / non-participant adversary
    SLASHED = 2   # FSM (Casper FFG only): slashable equivocation detected
    EXITED  = 3   # FSM (Casper FFG only): voluntary withdrawal at epoch boundary
```

The shared layer enumerates all four reasons but only the lifecycle mechanics;
which FSM condition triggers `SLASHED`/`EXITED` is per-protocol (T32).

## 5. The `Node` ABC — `node.py`

`Node` is `abc.ABC`. It is constructed directly only in tests (via a test
subclass); production code constructs protocol subclasses.

### 5.1 Identity and construction

```python
def __init__(self, node_id: int, weight: float,
             endpoint: object, global_seed: int) -> None:
```

- `id: int` — stored as `self.id`; read-only by convention after construction.
- `weight: float` — must be `>= 0`, else `ValueError`. Per-protocol semantics
  (`node-model.md §2` table) are not interpreted at this layer.
- `endpoint: object` — opaque; stored, never introspected.
- `global_seed: int` — consumed only to seed `self.rng` (§5.2); not retained
  as a public attribute (avoids accidental reuse outside the seeding path).

Identity attributes are not frozen by language mechanism (Python lacks cheap
read-only instance attributes); the contract is "read-only by convention,"
documented and asserted by tests, not enforced at runtime.

### 5.2 Determinism — per-Node RNG (Decision B)

```python
self.rng: random.Random = random.Random(_stable_seed(global_seed, node_id))
```

`_stable_seed` derives a process-stable 64-bit integer:

```python
def _stable_seed(global_seed: int, node_id: int) -> int:
    h = hashlib.blake2b(f"{global_seed}:{node_id}".encode(),
                        digest_size=8)
    return int.from_bytes(h.digest(), "big")
```

Rationale: `node-model.md §8` writes `seed = hash((global_seed, node_id))`,
but §11 (open to revision) flags Python's `hash()` as process-randomised for
some inputs. `blake2b` is identical across processes and machines, pre-empting
the §11 revision and protecting the thesis's byte-identical-replay promise.
This divergence from the literal contract formula is recorded as a
`## Revisions` entry on `node-model.md §8` (see §9 of this spec).

All FSM randomness (peer sampling, jitter, timeout randomisation) MUST flow
through `self.rng`. No global RNG, ever (`node-model.md §8` forbidden
surfaces).

### 5.3 Lifecycle state and transitions

```python
self.status: Lifecycle = Lifecycle.CREATED
self._halt_reason: HaltReason | None = None
```

- **`start(t: float) -> None`** — concrete. Asserts `status is CREATED` (else
  `RuntimeError` — illegal re-entry); flips `CREATED → RUNNING`; delegates to
  abstract `_on_start(t)`. Called once per Node at bootstrap phase 5 with
  `t == 0`.
- **`halt(reason: HaltReason, t: float) -> None`** — concrete. If `status is
  HALTED` already, **no-op** (first reason wins — the harness blanket-halts
  every Node with `RUN_END` at run's end, including already-`CRASHED`/
  `SLASHED` Nodes). Otherwise: set `status = HALTED`, `_halt_reason = reason`,
  and emit the mandatory `halted` event (§5.6).
- Transitions are monotonic: no path returns a `HALTED` Node to `RUNNING`.
  `created → running → halted`; there is no `created → halted` (a Node that
  never starts is simply never halted).

### 5.4 Inbound hooks — template-method pattern

The scheduler dispatches by calling `node.on_message` / `node.on_timer` /
`node.start` (see `src/scheduler/scheduler.py` `_dispatch`). To avoid every
protocol subclass re-implementing the lifecycle guard, the base class keeps
the **public** hooks concrete and delegates to **protected abstract** hooks:

| Public (concrete, base) | Protected (abstract, subclass overrides) |
| :-- | :-- |
| `start(t)` | `_on_start(t)` |
| `on_message(msg, t)` | `_on_message(msg, t)` |
| `on_timer(timer_id, payload, t)` | `_on_timer(timer_id, payload, t)` |

Guard logic in the public `on_message` / `on_timer`:

- `status is HALTED` → **silently drop** (return). `node-model.md §3`: a
  halted Node ceases all message handling and timer firing. Not an error —
  the heap may still hold events addressed to a Node halted by `run_end`.
- `status is CREATED` → **`RuntimeError`**. The scheduler must not deliver
  before `start`; if it does, that is a bootstrap-ordering bug and should be
  loud.
- `status is RUNNING` → delegate to the protected hook.

`start` is the only hook that mutates lifecycle; `on_message`/`on_timer` never
do (a Node halts itself only via an FSM-initiated `halt`, called from inside a
protected hook).

This is still subclassing (the human's chosen seam); the template method
merely keeps the guard un-duplicated across T28/T32/T38. The public callback
names the scheduler binds against (`on_message`, `on_timer`, `start`) are
unchanged from the contract — no Revision needed.

### 5.5 Outbound API — bound at bootstrap

`node-model.md §7` + `simulation-design.md §6.4`: the scheduler's `bind()`
wires `set_timer` / `cancel_timer` / `emit` onto each Node instance as
attributes; the network's `bind()` wires `send` / `broadcast`. Binding
overwrites instance attributes (the existing `Scheduler.bind` already does
`node.set_timer = lambda ...`).

The base class defines all five as methods that raise:

```python
def send(self, dst, type, payload, t):
    raise RuntimeError("Node.send called before Network.bind()")
# ...likewise broadcast / set_timer / cancel_timer / emit
```

This makes a pre-bind outbound call (an FSM bug) fail loudly instead of
`AttributeError`-ing obscurely. After `Scheduler.bind` / `Network.bind`, the
instance attribute shadows the class method.

Signatures (from `node-model.md §7`):

```python
send(dst: int, type: str, payload: object, t: float) -> None
broadcast(type: str, payload: object, t: float) -> None
set_timer(timer_id, delay: float, payload: object, t: float) -> None
cancel_timer(timer_id) -> None
emit(event_type: str, fields: dict, t: float) -> None
```

### 5.6 Event emission — `halted` and `decided`

Two events are mandatory (`node-model.md §3`, §4):

- **`halted`** — emitted by `halt()` (§5.3):
  `self.emit("halted", {"node_id": self.id, "reason": reason.name, "t": t}, t)`
- **`decided`** — emitted by the FSM (subclass) when an instance reaches its
  terminal state. T22 provides a protected convenience helper so the four
  protocols emit a consistent field schema:

  ```python
  def _emit_decided(self, value, instance_id, t: float) -> None:
      self.emit("decided",
                {"value": value, "instance_id": instance_id, "t": t}, t)
  ```

`reason.name` (a `str`) is emitted rather than the enum object so the event
stream stays serialisation-friendly for T24 / T40.

### 5.7 Adversary slot

```python
self.adversary: "AdversaryProfile | None" = None
```

Opaque per `node-model.md §9` — T22 holds the slot, T18 fills the strategy.
T22 ships a placeholder structural type so the slot is annotated:

```python
class AdversaryProfile(Protocol):
    """Opaque adversary strategy slot. Owned by T18 (adversary-model.md);
    this placeholder exists only so Node.adversary is typed."""
    ...
```

No adversary dispatch logic in T22 — routing outbound emissions through
`self.adversary` is the FSM subclass's responsibility (T28/T32/T38) and the
strategy semantics are T18's. "Honest" is simply `adversary is None`.

## 6. Error handling — fail-fast

Consistent with the scheduler's fail-fast philosophy
(`simulation-design-runtime.md §3`): wrong-but-quiet is the worst outcome for
a thesis whose artefact is reproducible numbers.

| Condition | Behaviour |
| :-- | :-- |
| `weight < 0` at construction | `ValueError` |
| `start()` when `status is not CREATED` | `RuntimeError` |
| `on_message` / `on_timer` when `status is CREATED` | `RuntimeError` |
| `on_message` / `on_timer` when `status is HALTED` | silent drop (return) |
| outbound API called before `bind` | `RuntimeError` |
| `halt()` when already `HALTED` | no-op (first reason wins) |
| exception inside a protected hook | propagates out (scheduler does not catch) |

## 7. Testing

Test-driven: each behaviour gets a failing test before implementation.

### 7.1 Unit — `tests/nodes/test_node.py`, `test_message.py`, `test_lifecycle.py`

- **Construction:** identity attributes stored; `weight < 0` → `ValueError`;
  `weight == 0` accepted.
- **RNG determinism:** two Nodes with identical `(global_seed, node_id)` draw
  byte-identical `rng` sequences; differing `node_id` diverges; differing
  `global_seed` diverges; the seed is process-stable (assert `_stable_seed`
  returns a fixed known value for a fixed input).
- **Lifecycle:** `start` flips `CREATED → RUNNING` and invokes `_on_start`;
  second `start` → `RuntimeError`; `halt` flips `→ HALTED`, records reason,
  emits `halted`; second `halt` is a no-op and preserves the first reason.
- **Inbound guard:** `on_message`/`on_timer` before `start` → `RuntimeError`;
  after `halt` → dropped (protected hook not invoked); while `RUNNING` →
  protected hook invoked with the exact arguments.
- **Outbound unbound:** each of `send`/`broadcast`/`set_timer`/`cancel_timer`/
  `emit` raises `RuntimeError` before binding.
- **Adversary slot:** defaults `None`; assignable.
- **`Message`:** field round-trip; frozen (mutation → error).

### 7.2 End-to-end — `tests/nodes/test_e2e.py`

A minimal test-only `Node` subclass implementing a trivial ping-pong protocol
(`_on_start` sends a ping; `_on_message` replies until a hop budget is spent,
then `_emit_decided` + `halt`). Driven through the **real `Scheduler`** and
the six-phase bootstrap to quiescence.

- **Build verification:** the run reaches `quiescence`; expected `decided`
  and `halted` events appear in the `event_sink` capture.
- **Determinism:** two `global_seed`-identical e2e runs produce byte-identical
  `event_sink` capture sequences. (`node-model.md §8` nominally assigns the
  determinism regression to T25; including it here is the natural
  build-verification evidence and the standing rule that every implementation
  task ships run-success evidence.)

A tiny in-test network shim wires `send`/`broadcast` to `Scheduler.schedule`
of `Delivery` events (the real `Network` is T23); the shim iterates recipients
in sorted `NodeId` order to keep the e2e deterministic.

## 8. Verification before In Review

Per the Engineer role, `superpowers:verification-before-completion` runs
before the task flips to In Review: execute the full `tests/nodes/` suite and
the existing `tests/scheduler/` suite (confirm no regression from the shared
`Message` type), and paste the passing output into the experiment page.

## 9. Wiki deliverables

- `wiki/experiments/2026-05-19_node-baseline.md` — build-verification page:
  config, seeds, commit hash, commands to re-run, raw result location,
  one-paragraph observation. Back-links `[[concepts/node-model]]`,
  `[[concepts/simulation-design]]`.
- `## Revisions` entry on `wiki/concepts/node-model.md §8` — records the
  Decision B divergence: `hash((global_seed, node_id))` →
  `blake2b`-derived stable seed; notes this resolves the §11 open-to-revision
  item for per-Node RNG seeding.
- `wiki/index.md` — add the experiment page under Experiments.
- `wiki/log.md` — one `code`-type entry for T22.
- No new concept page: `node-model.md` is already the design contract; T22
  produces code + an experiment page, not a concept page.

## 10. Out of scope (deferred, with owning task)

- Per-protocol FSM logic, instance tables, role schedules — T28 / T32 / T38.
- `AdversaryProfile` strategy semantics and adversary dispatch — T18.
- `Network` (concrete `send`/`broadcast` routing, delay, loss) — T23.
- Structured logging / CSV export of the event stream — T24.
- Experiment harness, YAML config, `global_seed` sourcing — T19 / T27.
- The cross-run determinism regression test as a first-class suite — T25
  (T22 includes an e2e determinism check as build verification only).
