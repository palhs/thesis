# T39 — Unified Runner + Bootstrap-Seam Hardening: Design Spec

- **Task:** T39 (Engineer) — Unified `run()` interface across PBFT, Casper FFG,
  Snowman; targeted stabilization of bootstrap-seam fail-fast gaps.
- **Branch:** `task/T38-snowman` (worktree continues on this branch by
  pickup-flow convention; final branch is the per-task branch the human
  retitles on push).
- **Date:** 2026-05-27.
- **Outcome (TASKS.md, original):** *"If buffer: stabilize PBFT & PoS, fix
  bugs, unify interface."* The original framing assumed the W7-buffer branch
  the T37 decision did not take (T37 chose the Algorithm-3 branch and
  implemented Snowman via T38). The "stabilize / fix bugs" half is **not
  bound by accumulated backlog**: every "watch for" backlog item routes to a
  different downstream task (T40, T47, T57, T18, T26). T39's actual scope is
  therefore narrower than the entry suggests.
- **Scope decisions (human, 2026-05-27):**
  - **Runner purpose (Q1):** **thin scaffolding consolidation.** Collapse
    the ~12 LoC of duplicated bootstrap-tail boilerplate four callers
    repeat. CSV columns belong to T40; experiment-matrix sweeps belong to
    T41+. The runner is `EventLogger`-attach + `scheduler.run()`, nothing
    more.
  - **Migration (Q2):** migrate **all four callers** — the three baseline
    integration tests (`test_pbft_baseline`, `test_pos_baseline`,
    `test_snowman_baseline`) plus the in-`src/` driver (`src/pos/baseline.py`,
    the T35 sample-CSV writer). The T35-local CSV schema stays untouched
    pending T40.
  - **Stabilization scope (Q3):** **targeted sweep** — close two backlog
    items that sit exactly on the bootstrap seam the runner formalises
    (Cluster A + Cluster B, both Priority L, both "watch for T19/T27" and
    therefore retroactive once those tasks shipped).
  - **Runner shape:** **Approach 1** — a single `run_to_completion(handle,
    *, t_max, logger)` helper over an existing `RunHandle`. No `Runner`
    class; no one-shot `run(config, seed, factory, …)` composition (defer
    on YAGNI grounds).
  - **Wiki home:** a new `wiki/concepts/runner.md` page (matches the size
    pattern of `event-log-schema` / `reproducibility`).
  - **Backlog closure style:** append-resolved (preserve the entry, append
    a "Resolved 2026-05-27 by T39: …" suffix), matching the precedent set
    by the §6/§7 adversaries item (Resolved 2026-05-18 (during T19)).

This spec is the canonical reference for the T39 implementation plan
(`superpowers:writing-plans`). It consumes the W3 design contracts
[[concepts/node-model]], [[concepts/network-model]],
[[concepts/simulation-design]], [[concepts/reproducibility]] and rests on
the existing `config.factory.build_run()` seam from T27.

## 1. Scope and non-goals

### In scope

- **`src/common/runner.py`** — a new `src/common/` package containing
  exactly one helper: `run_to_completion(handle, *, t_max=None,
  logger=None) -> tuple[RunResult, EventLogger]`. ~15 LoC plus module
  docstring.
- **Fail-fast hardening at the bootstrap seam** — five guards:
  - **A1** `Node.__init__` rejects `node_id < 0` with `ValueError`.
  - **A2** `Node.__init__` rejects non-finite `weight` (`NaN`, `±inf`)
    with `ValueError`.
  - **B1** `Network.register(node)` raises `ValueError` on duplicate
    `node.id`.
  - **B2** `Scheduler.bind(node)` raises `ValueError` on duplicate
    `node.id`.
  - **B3** `Network.start()` raises `RuntimeError` on a second call.
- **Migration of four callers** to `run_to_completion`:
  `tests/integration/test_pbft_baseline.py`,
  `tests/integration/test_pos_baseline.py`,
  `tests/integration/test_snowman_baseline.py`, and
  `src/pos/baseline.py`. Same call shape, same assertions, byte-identical
  event streams pre/post.
- **TASKS.md edit** — rewrite T39's entry with the agreed scope (preserve
  the W7-buffer parenthetical, same pattern as T29's 2026-05-21 rewrite);
  append-resolved the two relevant backlog items; recompute the dashboard
  arithmetic on flip to In Review.
- **Wiki touches** — new `wiki/concepts/runner.md`; three `## Revisions`
  blocks on `node-model.md`, `network-model.md`, `simulation-design.md`;
  inbound wikilinks added from `simulation-design.md` and
  `reproducibility.md`; `wiki/index.md` and `wiki/log.md` updated per
  `docs/wiki-spec.md`.

### Out of scope (deferred to their owning tasks)

- **Unified CSV column set / cross-protocol output schema** — **T40**
  (`[[concepts/output-format]]` is forward-referenced by 15 callers).
  `src/pos/baseline.py` keeps its T35-local schema.
- **Multi-seed sweeps, experiment-matrix driver, parameter exploration**
  — **T41+**.
- **One-shot `run(config, seed, factory, …)` composition** (Approach 2)
  — **deferred on YAGNI**. Revisit if a third caller wants the two-line
  preamble collapsed; until then `build_run` + `run_to_completion` reads
  honestly.
- **Adversary attachment surface** — **T18**. The runner has no
  scheduler-layer adversary hook (same posture as
  `[[concepts/simulation-design-runtime#adversary-boundary]]`).
- **Coverage tooling (`make coverage` target)** — backlog item "watch for
  T26".
- **Time-bounded experiments overshoot-and-clip semantics** — backlog
  item "run-past-`t_max`-then-clip", **T46/T47 + T41-harness territory.**
  The runner pipes `t_max` straight into `scheduler.run(t_max=…)`; no
  clipping introduced here.
- **Other "watch for" backlog items** (PBFT propose-side quiescence under
  view-change, tombstone heap growth, public halt-reason accessor, PBFT
  network-drop integration test, network distribution-shape e2e, …) —
  left routed to their stated future tasks.

### Non-changes (explicit no-touch surface)

- `config.factory.build_run()` signature and behaviour: unchanged.
- `scheduler.run()` / `scheduler.Scheduler` body: unchanged (B2 adds an
  input-validation `if` to `bind`; the dispatch loop is untouched).
- `Network` body: unchanged (B1 adds an `if` to `register`; B3 adds an
  `if` to `start`).
- `EventLogger` / `event_log/` package: unchanged.
- Event-stream contract: every existing `test_determinism*` case must
  still hold byte-identical pre/post migration.

## 2. Runner contract

### 2.1 File layout

```
src/common/__init__.py       # re-exports run_to_completion
src/common/runner.py         # ~40 LoC including docstring + types
```

### 2.2 Signature

```python
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
    """Attach a logger, run the scheduler to its stop condition, return both.

    Caller flow:

        handle = build_run(config, global_seed, factory)
        result, logger = run_to_completion(handle, t_max=20.0)

    `t_max=None` runs to quiescence (matches PBFT honest path).
    `t_max=<float>` runs to deadline (matches Casper / Snowman, which
    have no natural quiescence).

    A freshly-constructed `EventLogger` is used if `logger is None`;
    callers that want to share or pre-seed a logger may pass one.
    Returns both so callers can introspect `logger.records` and `result`
    (e.g. `stopped_by`).
    """
    if logger is None:
        logger = EventLogger()
    handle.scheduler.event_sink = logger.sink
    if t_max is None:
        result = handle.scheduler.run()
    else:
        result = handle.scheduler.run(t_max=t_max)
    return result, logger
```

### 2.3 Four runner decisions

| # | Decision | Reason |
|---|---|---|
| **R1** | Helper, not a class. | No state between calls; the `RunHandle` already carries everything the caller might want to introspect. Object-oriented wrapping fails YAGNI. |
| **R2** | Helper owns the `event_sink` write. | Eliminates the line every caller currently repeats; preserves the existing sink contract (caller can supply a pre-seeded `EventLogger`). |
| **R3** | `t_max=None` ⇒ quiescence-only; `t_max=<float>` ⇒ deadline. | PBFT honest path stops on empty heap; Casper/Snowman have no quiescence. `None` reads more honestly than `math.inf` ("no deadline" vs "deadline at infinity") and pipes straight into the scheduler's existing default `run()` semantics. |
| **R4** | Returns `(RunResult, EventLogger)` — tuple, not dataclass. | Two fields, immediately destructured by every caller. Surface stays narrow; if T40 ever wants a richer return type, it builds its own dataclass on top. |

### 2.4 Deliberate non-decisions

The runner deliberately does **not** make these decisions; each is
deferred to its owning task:

- **No `Config` parameter, no `node_factory` parameter.** Those live one
  layer down (`build_run`). Keeping `run_to_completion` post-build lets
  tests that need to inspect `handle.nodes` *before* the run still do so.
- **No CSV writing or output formatting.** T40 owns the output column
  set; mixing it in would force this spec to decide what T40 owns.
- **No multi-seed loop, no parameter sweep.** T41+ experiment harness.
- **No `result.stopped_by` assertion inside the helper.** Each caller
  asserts the appropriate stop reason — PBFT expects `"quiescence"`,
  Casper/Snowman expect `"deadline"`.
- **No overshoot-and-clip semantics.** The runner pipes `t_max`
  unchanged. The backlog item on time-bounded experiments routes the
  buffer + clip decision to T46/T47 + T41-harness, not to T39.
- **No adversary hook.** Same posture as
  `[[concepts/simulation-design-runtime#adversary-boundary]]`.

### 2.5 Import / cycle check

`src/common/runner.py` imports from `config.schema`, `event_log`,
`scheduler`. None of those import from `src/common/`. No cycle.

## 3. Bootstrap-seam fail-fast hardening (Cluster A + B)

Five guards, each one-liner, each with a focused unit test. Order of
checks within `Node.__init__`: cheapest first (A1 before A2 before
existing `weight < 0`).

### 3.1 Cluster A — `Node.__init__` input validation

The current `src/nodes/node.py` validates `weight < 0` but `NaN < 0` is
`False` so non-finite weights slip past; `node_id` is unvalidated.

| # | Guard | Site | Exception |
|---|---|---|---|
| **A1** | `node_id < 0` | `Node.__init__` | `ValueError(f"node_id must be non-negative; got {node_id}")` |
| **A2** | `not math.isfinite(weight)` | `Node.__init__` | `ValueError(f"weight must be finite; got {weight!r}")` |

**A1 reason.** `-1` is the scheduler's `PhaseAdvance` sentinel for the
`(t, node_id, seq)` tie-break (`scheduler.py`); a misconfigured `Node`
with `id = -1` would silently sort *with* phase events rather than
after them, scrambling deterministic order.

**A2 reason.** Once T32+ uses `weight` as Casper stake, a `NaN`/`±inf`
weight from a malformed config would silently corrupt threshold
arithmetic. The existing `weight < 0` check stays — `-inf < 0` would
already be caught there, but A2 produces a clearer error message and
also catches `NaN`/`+inf`.

### 3.2 Cluster B — bootstrap-seam idempotency / collision guards

| # | Guard | Site | Exception |
|---|---|---|---|
| **B1** | `node.id in self._registry` | `Network.register` | `ValueError(f"duplicate node_id {node.id} in Network.register")` |
| **B2** | `node.id in self.nodes` | `Scheduler.bind` | `ValueError(f"duplicate node_id {node.id} in Scheduler.bind")` |
| **B3** | `self._started is True` | `Network.start` | `RuntimeError("Network.start() called twice")` |

**B1 / B2 reason.** Symmetric with the unregistered-`dst` paths in
`Network._try_deliver` and `Scheduler._dispatch._node`, which already
fail-fast with `KeyError`. The current `registry[node.id] = node`
silently clobbers; a duplicate-`id` config would drop a validator
without raising.

**B3 reason.** `Network.start()` is not idempotent — `_started` is set
but never checked; a second call re-runs `validate_timeline` (cheap) and
re-schedules every interior `PhaseAdvance` boundary, double-firing phase
rollovers. Uses `RuntimeError` (wrong call sequence), not `ValueError`
(bad value).

### 3.3 Honest-path invariance

Every existing test constructs nodes with valid `node_id ≥ 0`, finite
`weight`, unique `id`s, and calls `Network.start` exactly once. None of
the five guards fire on any current run. Event streams stay byte-identical
pre/post: this is provable from the determinism contract
`[[concepts/reproducibility]]` because the five guards add `if … raise`
branches outside the dispatch loop, with no `if`-not-taken side effect
visible to the event stream.

### 3.4 Backlog items closed

Two backlog entries in `TASKS.md` are closed by this section:

- "`Node.__init__` accepts non-finite `weight` (`NaN`, `±inf`)" → A2.
- "`Network.register` / `Scheduler.bind` / `Network.start` lack
  fail-fast collision-or-repeat checks; `Node.__init__` accepts
  `node_id = -1` (the `PhaseAdvance` sentinel)" → A1 + B1 + B2 + B3.

Closure style: **append-resolved.** Each entry is preserved verbatim
with a `**Resolved 2026-05-27 by T39:** …` suffix appended, mirroring the
"Resolved 2026-05-18 (during T19)" pattern already in the file.

## 4. Migration plan

Four callers move. All four shrink without behaviour change. Every
existing assertion stays. Every `test_determinism*` case must still pass
byte-identical (this is the migration's correctness proof).

### 4.1 `tests/integration/test_pbft_baseline.py` (M1)

Current `_run` (7 lines) collapses to 3:

```python
def _run(n: int, global_seed: int = 42):
    handle = build_run(_config(n), global_seed, _factory(n))
    result, logger = run_to_completion(handle)    # quiescence-stop
    return logger, result
```

- No `t_max` arg (PBFT stops on quiescence).
- Return-tuple shape `(logger, result)` preserved — call-sites unchanged.
- `result.stopped_by == "quiescence"` assertion in
  `test_every_node_finalizes` still holds.

### 4.2 `tests/integration/test_pos_baseline.py` (M2)

```python
def _run(n, stake_table, global_seed=42):
    handle = build_run(_config(n), global_seed, _factory(n, stake_table))
    result, logger = run_to_completion(handle, t_max=_T_MAX)
    return logger, result
```

- `result.stopped_by == "deadline"` assertion still holds.

### 4.3 `tests/integration/test_snowman_baseline.py` (M3)

```python
def _run(n, global_seed=42):
    handle = build_run(_config(n), global_seed, _factory(n))
    result, logger = run_to_completion(handle, t_max=_T_MAX)
    return logger, result, dict(handle.nodes)
```

Snowman's `dict(handle.nodes)` extraction stays at the caller —
protocol-specific introspection, deliberately not the runner's job
(R-non-decision §2.4). `handle.nodes` is the `MappingProxyType` view
`build_run` already provides.

### 4.4 `src/pos/baseline.py` `_run_scenario` (M4)

Same shape as M2. The `_summarise` step is unchanged; the T35-local CSV
columns are untouched (per the scope agreement). The `__main__`
entrypoint `PYTHONPATH=src python3 -m pos.baseline` still works
post-migration. `results/pos/baseline.csv` stays byte-identical (same
seed, same events ⇒ same summary).

### 4.5 Imports

Each migrated file adds:

```python
from common import run_to_completion
```

The `from event_log import EventLogger` import in M1/M2/M3 becomes
unused (the runner constructs the logger) and is removed. M4 keeps it —
`src/pos/baseline.py` doesn't import the logger directly after migration
either, but its surrounding context (`_summarise`) uses the logger's
records via the variable returned from `run_to_completion`. The import
becomes unused in M4 too and is removed.

### 4.6 Order of edits (each commit leaves the tree green)

1. **Cluster A + B guards land first** — pure additions, no caller
   depends on them. All existing tests pass.
2. **`src/common/runner.py` + `tests/common/test_runner.py` land next**
   — additive. Existing suites untouched.
3. **Migrate callers** (M1–M4), each commit leaving `make test` green.
4. **Wiki + TASKS.md updates last**, after `make test` confirms
   everything green.

The Engineer flow runs `superpowers:test-driven-development` inside this
— each guard's test lands before its guard, each migration runs
`make test` after.

## 5. Testing strategy

### 5.1 New test surface

| File | Tests | Asserts |
|---|---|---|
| `tests/common/test_runner.py` (new) | 6 | `run_to_completion` contract |
| `tests/nodes/test_node.py` | +2 | A1 + A2 guards |
| `tests/network/test_network.py` | +2 | B1 + B3 guards |
| `tests/scheduler/test_scheduler.py` | +1 | B2 guard |

Eleven new tests. Each under 30 LoC.

### 5.2 `tests/common/test_runner.py` — six cases

The runner is small enough to fully spec. Each test uses
`tests/integration/_helpers.BroadcastNode` (or a 2-node minimal subclass)
so the runner exercises the real `build_run` seam, not a mock.

| # | Test | Asserts |
|---|---|---|
| 1 | `test_returns_run_result_and_logger` | Right tuple shape; `logger.records` non-empty after a 2-node run. |
| 2 | `test_default_logger_constructed_when_omitted` | Omitted `logger` ⇒ fresh `EventLogger`; `logger.records` captures the run's events. |
| 3 | `test_caller_supplied_logger_used` | Caller-passed `logger` is the same object returned; pre-existing records survive. |
| 4 | `test_t_max_none_runs_to_quiescence` | Quiescent workload (`BroadcastNode`) ⇒ `result.stopped_by == "quiescence"`. |
| 5 | `test_t_max_float_runs_to_deadline` | Non-quiescent workload (re-arming `TimerNode`) + `t_max=1.0` ⇒ `result.stopped_by == "deadline"` and `result.now ≥ 1.0`. |
| 6 | `test_two_runs_byte_identical` | Same `(config, global_seed)` twice ⇒ `list(a.records) == list(b.records)`. Runner-level determinism check. |

### 5.3 Five guard tests — one per guard

Each asserts exception type **and** a substring of the message (so the
message can't drift silently):

```python
# tests/nodes/test_node.py (A1, A2)
def test_init_rejects_negative_node_id(self):
    with self.assertRaisesRegex(ValueError, "node_id must be non-negative"):
        Node(node_id=-1, weight=1.0, endpoint=None, global_seed=42)

def test_init_rejects_non_finite_weight(self):
    for bad in (float("nan"), float("inf"), float("-inf")):
        with self.subTest(weight=bad):
            with self.assertRaisesRegex(ValueError, "weight must be finite"):
                Node(node_id=0, weight=bad, endpoint=None, global_seed=42)

# tests/network/test_network.py (B1, B3)
def test_register_rejects_duplicate_node_id(self): ...
def test_start_rejects_double_call(self): ...

# tests/scheduler/test_scheduler.py (B2)
def test_bind_rejects_duplicate_node_id(self): ...
```

### 5.4 Regression-floor check

The migration is a sequencing refactor; the guards reject inputs no
existing test produces. Acceptance criterion before T39 flips to In
Review (per the Engineer prompt's
`superpowers:verification-before-completion` requirement):

```
make test          # all suites green, including all four test_determinism*
```

Test count + pass count captured pre- and post-migration; the diff goes
into the handoff summary.

### 5.5 Coverage

The repo has no `make coverage` target — backlog item "watch for T26",
not T39. Spot-check only:

```bash
PYTHONPATH=src python3 -m trace --count -C /tmp/cov \
    -m unittest tests.common.test_runner -v
```

`src/common/runner.py` should hit 100% line coverage from
`tests/common/test_runner.py` alone (no defensive unreachable branches
in 15 LoC).

### 5.6 What is NOT tested by T39

- **CSV column semantics** — T40.
- **Multi-seed / sweep behaviour** — T41+.
- **Adversary attachment via the runner** — T18.
- **Cross-protocol metric comparability** — T40 + T42 + T48.
- **Overshoot-and-clip semantics** — T46/T47 + T41-harness.

## 6. Wiki touches and TASKS.md edit

Per `docs/workflow.md` step 6–7 and `docs/wiki-spec.md`.

### 6.1 New page: `wiki/concepts/runner.md`

~120 lines (well under the 300-line cap). Mirrors the size and tone of
`wiki/concepts/event-log-schema.md`. Sections:

1. **Purpose.** `run_to_completion` is the post-build half of the
   bootstrap; pairs with `build_run` (build half) and the six-phase
   bootstrap from `[[concepts/simulation-design#bootstrap]]`.
2. **Contract.** Signature + the four decisions R1–R4 from §2.3.
3. **Stop modes.** `t_max=None` ⇒ quiescence; `t_max=<float>` ⇒
   deadline. Explicit non-introduction of overshoot-and-clip.
4. **Determinism.** Runner is pass-through; the seven determinism
   mechanisms from `[[concepts/simulation-design-runtime]]` are
   unaffected.
5. **Adversary boundary.** Explicit non-slot — same posture as
   `[[concepts/simulation-design-runtime#adversary-boundary]]`; T18
   attaches at the `Node` layer.
6. **What it does NOT own.** CSV columns (T40), multi-seed sweeps
   (T41+), adversary wiring (T18). One bullet each.

### 6.2 Inbound wikilinks

- `[[concepts/simulation-design]]` § Bootstrap — one sentence:
  `[[concepts/runner]]` is the canonical post-build entrypoint.
- `[[concepts/reproducibility]]` — one bullet adding
  `[[concepts/runner]]` to the harness-level contract list.

### 6.3 Three `## Revisions` blocks

Per `docs/wiki-spec.md § Revisions rule` (add, not silent overwrite):

- **`wiki/concepts/node-model.md`** — `Node.__init__` now rejects
  `node_id < 0` and non-finite `weight` (Cluster A guards); 2026-05-27.
- **`wiki/concepts/network-model.md`** — `Network.register` rejects
  duplicate `node.id`; `Network.start` rejects second call (B1 + B3);
  2026-05-27.
- **`wiki/concepts/simulation-design.md`** — `Scheduler.bind` rejects
  duplicate `node.id` (B2); 2026-05-27.

Three blocks, ~3–5 lines each.

### 6.4 `wiki/index.md` update

One new entry under `## Concepts`:

```
- [[concepts/runner]] — Post-build half of the six-phase bootstrap:
  `run_to_completion(handle, *, t_max, logger)` attaches an EventLogger,
  runs the scheduler to its stop condition, returns (RunResult,
  EventLogger). Pairs with `[[concepts/simulation-design]]` (build half);
  pass-through determinism (no new RNG, no scheduler-layer adversary);
  T40 owns CSV columns, T41+ owns sweeps, T18 owns adversary wiring.
```

### 6.5 `wiki/log.md` entry

One entry per `docs/wiki-spec.md § Log format`:

```
## [2026-05-27] code | task 39 — unified runner + fail-fast seam hardening
- role: Engineer
- touched: src/common/runner.py, src/common/__init__.py,
    src/nodes/node.py, src/network/network.py, src/scheduler/scheduler.py,
    tests/common/test_runner.py, tests/nodes/test_node.py,
    tests/network/test_network.py, tests/scheduler/test_scheduler.py,
    tests/integration/test_pbft_baseline.py,
    tests/integration/test_pos_baseline.py,
    tests/integration/test_snowman_baseline.py, src/pos/baseline.py,
    wiki/concepts/runner.md,
    wiki/concepts/{node-model,network-model,simulation-design}.md
      (Revisions blocks),
    wiki/index.md, TASKS.md
- notes: Lands the post-build run helper run_to_completion(handle, *,
    t_max, logger) → (RunResult, EventLogger), collapsing ~12 LoC of
    duplicated bootstrap-tail boilerplate across four callers. Fail-fast
    hardens five bootstrap-seam holes (negative node_id, non-finite
    weight, duplicate register/bind, double start). T35-local CSV schema
    in src/pos/baseline.py untouched — T40 owns reconciliation per
    [[concepts/output-format]] when it lands. T39 entry rewritten to
    drop the W7-buffer counterfactual framing.
```

### 6.6 `TASKS.md` edits

1. **T39 entry rewrite.** Replace the "If buffer: …" outcome with the
   agreed scope; preserve the original under a *"(superseded 2026-05-27
   by W7 decision; original framing assumed the buffer branch the T37
   decision did not take)"* parenthetical, mirroring T29's 2026-05-21
   rewrite.

2. **Backlog closures** — append-resolved:
   - "`Node.__init__` accepts non-finite `weight`": append `**Resolved
     2026-05-27 by T39:** A2 guard in Node.__init__ rejects non-finite
     weight with ValueError; covered by tests/nodes/test_node.py
     test_init_rejects_non_finite_weight.`
   - "`Network.register` / `Scheduler.bind` / `Network.start` lack
     fail-fast collision-or-repeat checks; `Node.__init__` accepts
     `node_id = -1`": append `**Resolved 2026-05-27 by T39:** A1 + B1 +
     B2 + B3 guards across Node.__init__, Network.register,
     Scheduler.bind, Network.start; covered by the corresponding
     one-test-per-guard suite.`

3. **Dashboard arithmetic** — recompute on flip to In Review.

### 6.7 Spec file location

This design spec lands at:

```
docs/superpowers/specs/2026-05-27-t39-unified-runner-design.md
```

The companion implementation plan (next step,
`superpowers:writing-plans`) will land at:

```
docs/superpowers/specs/2026-05-27-t39-unified-runner-plan.md
```

Per the Engineer role prompt, specs stay in `docs/superpowers/specs/` —
do not relocate.

## 7. Risks and open questions

- **None blocking.** All four scope questions (Q1–Q3 + runner shape + wiki
  home + backlog closure style) resolved with the human during
  brainstorming.
- **Latent risk:** if a future caller ends up writing `build_run` +
  `run_to_completion` four lines apart with no introspection between, the
  one-shot `run(config, seed, factory, …)` composition (Approach 2 from
  the brainstorming) becomes worth landing. Until then, YAGNI.
- **Migration risk:** the migration's byte-identical claim rests on the
  fact that `run_to_completion` does `event_sink` assignment + `run()`
  in the same order callers currently do. Verified at execute time by
  running `make test` after each migration commit — every
  `test_determinism*` case must pass byte-identical.

## 8. Acceptance criteria

T39 is ready to flip to In Review (Engineer hands off to human merge)
when **all** of the following hold:

- [ ] `src/common/runner.py` exists with the §2.2 signature.
- [ ] All five guards (A1, A2, B1, B2, B3) are in place; each has the
      corresponding test in §5.3.
- [ ] All four callers (M1, M2, M3, M4) use `run_to_completion`; the
      `EventLogger` import is removed from any caller that no longer
      uses it directly.
- [ ] `make test` is green from a clean checkout. Every existing
      `test_determinism*` case still passes byte-identical.
- [ ] `src/pos/baseline.py`'s `results/pos/baseline.csv` output is
      byte-identical pre/post (one-time `diff` check captured in the
      handoff summary).
- [ ] `wiki/concepts/runner.md` exists; three `## Revisions` blocks
      added to `node-model.md` / `network-model.md` /
      `simulation-design.md`; `wiki/index.md` updated; `wiki/log.md`
      appended.
- [ ] `TASKS.md` updated: T39 entry rewritten, two backlog items
      append-resolved, dashboard recomputed.
- [ ] `superpowers:verification-before-completion` invoked; the
      handoff summary records pre/post test counts and any deferred
      observations.
