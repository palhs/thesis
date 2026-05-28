# Runner

Post-build half of the six-phase bootstrap. `run_to_completion` attaches an
`EventLogger` to the scheduler's `event_sink`, runs the scheduler to its stop
condition, and returns `(RunResult, EventLogger)`. A pass-through over the
`RunHandle` produced by `build_run`; ~15 LoC; no scheduler-layer adversary
hook, no CSV output, no multi-seed sweep.

This page pins the contract for `src/common/runner.py` (T39). The implementation
references it from its module docstring.

## Purpose

The thesis simulator runs in two halves. **`build_run`** ([[concepts/reproducibility]]
§5) wires the canonical six-phase bootstrap ([[concepts/simulation-design]] §7.2)
and hands back a `RunHandle` carrying the constructed `Scheduler`, `Network`,
and node table. **`run_to_completion`** consumes that handle, attaches the
event-stream observer, and drives the scheduler dispatch loop to its terminal
state.

The split exists because tests and drivers frequently need to inspect
`handle.nodes` or pre-seed an `EventLogger` *before* the run begins. Folding the
two halves into one entry point would forbid that inspection without adding
optional pre-run hooks. Keeping `run_to_completion` post-build preserves the
inspection seam at zero API cost.

Before T39, four callers (three baseline integration tests plus
`src/pos/baseline.py`) each repeated the same ~3-line bootstrap tail —
construct logger, assign to `event_sink`, call `scheduler.run(...)`. The helper
collapses that boilerplate without altering observable behaviour: every
`test_determinism*` case passes byte-identical pre/post migration.

## Contract

Signature (`src/common/runner.py`):

```python
def run_to_completion(
    handle: RunHandle,
    *,
    t_max: float | None = None,
    logger: EventLogger | None = None,
) -> tuple[RunResult, EventLogger]:
```

Behaviour:

1. If `logger is None`, construct a fresh `EventLogger()`.
2. Assign `handle.scheduler.event_sink = logger.sink`.
3. If `t_max is None`, call `handle.scheduler.run()`; otherwise call
   `handle.scheduler.run(t_max=t_max)`.
4. Return `(result, logger)`.

The four decisions pinning this shape:

| # | Decision | Reason |
| :-- | :-- | :-- |
| R1 | Helper, not a class. | No state between calls; `RunHandle` already carries everything a caller introspects. Object-oriented wrapping fails YAGNI. |
| R2 | Helper owns the `event_sink` write. | Eliminates the line every caller currently repeats. The existing sink contract is preserved — a caller can supply a pre-seeded `EventLogger` to be reused. |
| R3 | `t_max=None` ⇒ quiescence; `t_max=<float>` ⇒ deadline. | `None` reads more honestly than `math.inf` ("no deadline" vs "deadline at infinity") and pipes straight into the scheduler's existing default `run()` semantics. |
| R4 | Returns `(RunResult, EventLogger)` — tuple, not dataclass. | Two fields, immediately destructured at every call site. If T40 ever wants a richer return type it builds its own dataclass on top. |

The helper takes no `Config`, no `node_factory`, and no `global_seed`: those
parameters belong to `build_run`. The helper takes no `stop_when` predicate:
the underlying `Scheduler.run` accepts one ([[concepts/simulation-design]] §6.5),
but the four current callers do not use it, so it is omitted from the helper
surface pending evidence of need.

## Stop modes

Two modes, selected by `t_max`:

| `t_max` | Stop condition | Typical caller |
| :-- | :-- | :-- |
| `None` | Quiescence (empty heap). `RunResult.stopped_by == "quiescence"`. | PBFT honest-path baseline — the protocol settles and stops emitting. |
| `<float>` | Deadline (`scheduler.now >= t_max` at next iteration). `RunResult.stopped_by == "deadline"`. | Casper FFG and Snowman baselines — re-arming timers prevent natural quiescence. |

The helper passes `t_max` straight into `scheduler.run(t_max=...)` with no
clipping, no buffer, and no adjustment. **Overshoot-and-clip semantics are
explicitly not introduced here.** A time-bounded run whose final event lands at
`scheduler.now > t_max` is the scheduler's concern, and the convention for
"run-past-`t_max`-then-clip" experiments is routed to
[[concepts/experiment-matrix]] (T41+ harness, T46/T47 delay/adversarial)
rather than absorbed into the runner.

The helper does not assert `result.stopped_by`. Each caller asserts the
appropriate label — PBFT expects `"quiescence"`, Casper/Snowman expect
`"deadline"`.

## Determinism

The runner introduces no new randomness, holds no RNG, and adds no scheduling
gate. It is pass-through: every byte the scheduler would emit through
`event_sink` in the absence of the helper is emitted unchanged in its presence.

The seven mechanisms enumerated in [[concepts/simulation-design-runtime]] §1
(heap key `(t, node_id, seq)`; monotonic `now`; `schedule()` past-check;
`seq_per` monotonicity; scheduler holds no RNG; `registry` key-only access;
handler exceptions propagate) are unaffected. The harness-level reproducibility
claim in [[concepts/reproducibility]] §1 — same `(YAML, global_seed)` produces
the same event stream — therefore extends through the runner without
qualification.

The runner-level determinism check is
`tests/common/test_runner.py::test_two_runs_byte_identical`: two
`(config, global_seed)`-identical invocations of
`build_run` + `run_to_completion` produce structurally-identical
`EventRecord` sequences (asserted as `list(a.records) == list(b.records)`).
Literal-byte CSV equality is the scope of T40
([[concepts/output-format]]) once events serialise to disk; the runner's
contract is the structural equality that underwrites it.

## Adversary boundary

The runner has **no** adversary attachment slot — same posture as
[[concepts/simulation-design-runtime#adversary-boundary]]. All adversary
semantics live at the `Node` boundary
([[concepts/node-model]] §9, [[concepts/network-model]] §6) and gate the
Node's outbound API before any call reaches `Network.submit_*` or
`Scheduler.schedule`. By the time the dispatch loop runs, adversarial
behaviour has already been applied; the runner sees only post-adversary
events.

T18 attaches the adversary at the `Node` layer. Adding a runner-layer adversary
hook would model a threat with no production analogue (kernel schedulers and
event loops are not network elements an attacker reaches). If a future RQ
requires queue-layer reordering or duplication, that lands as a `## Revisions`
entry on this page; v1 intentionally omits the slot.

## What it does NOT own

- **CSV columns and output formatting → T40** ([[concepts/output-format]]).
  The runner returns the `EventLogger` containing the raw `EventRecord`
  buffer; projecting that buffer to a unified cross-protocol metrics CSV is
  T40's scope. `src/pos/baseline.py` keeps its T35-local schema pending T40.
- **Multi-seed sweeps and parameter exploration → T41+**
  ([[concepts/experiment-matrix]]). The runner consumes one already-built
  `RunHandle` per call; enumerating `global_seed` values, varying
  configurations, and aggregating across runs belong to the experiment harness
  one layer above.
- **Adversary wiring → T18**
  ([[concepts/adversary-model]]). The runner has no adversary parameter; T18
  attaches its faults at `Node.adversary` before bootstrap, where the existing
  `Node` contract already gates outbound calls.

## Sources

Design contract; no primary-literature citations.

**Design spec:**

- `docs/superpowers/specs/2026-05-27-t39-unified-runner-design.md` — the
  engineer-register companion (§2 Contract, §2.3 R1–R4 decisions, §2.4
  deliberate non-decisions, §6.1 wiki home outline) consumed by
  `superpowers:writing-plans` for T39 execution.

**Inbound (existing wiki pages):**

- [[concepts/simulation-design]] §7.2 — the six-phase bootstrap whose
  post-build tail this helper formalises.
- [[concepts/simulation-design-runtime]] §1 — the seven determinism mechanisms
  the runner is pass-through over.
- [[concepts/simulation-design-runtime#adversary-boundary]] — the
  no-scheduler-layer-adversary posture this helper inherits.
- [[concepts/reproducibility]] §5 — `build_run`, the build half this helper
  pairs with.
- [[concepts/event-log-schema]] — the `EventLogger` and `EventRecord` schema
  the helper attaches and returns.

**Source files:**

- `src/common/runner.py` — the implementation.
- `src/common/__init__.py` — re-exports `run_to_completion`.
- `tests/common/test_runner.py` — six-test contract suite.

**Forward references (sibling pages):**

- [[concepts/output-format]] (T40) — consumes the returned `EventLogger.records`
  for unified cross-protocol CSV columns.
- [[concepts/experiment-matrix]] (T41+) — wraps the runner in the multi-seed
  sweep harness.
- [[concepts/adversary-model]] (T18) — attaches faults at the `Node` boundary
  before the run.

## Revisions

- **2026-05-28 by T40.** The CSV-output gap noted in §What's outside the
  runner / *CSV columns and output formatting → T40* is closed. The
  runner stays at pass-through — no scheduler-layer adversary, no CSV
  output. The comparative CSV is owned by `src/output/csv.py`; see
  [[concepts/output-format]].
