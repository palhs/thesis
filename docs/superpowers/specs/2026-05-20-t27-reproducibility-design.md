# T27 — Reproducibility: seed control + YAML configs (design)

- Date: 2026-05-20
- Role: Engineer
- Status: Design approved (brainstorming, 2026-05-20)
- Artifacts: `src/config/` + `wiki/concepts/reproducibility.md` + boundary-gate edits in `src/{nodes,network,scheduler}/`
- Upstream wiki contracts pinned: [[concepts/node-model]] §8, [[concepts/network-model-phases]] §6, [[concepts/simulation-design-runtime]] §1, [[concepts/experiment-matrix]] §7
- Out-of-band context: `TASKS.md` § Backlog — four "Watch for T27" boundary-seam items

## 1. Scope and approach

T27 consolidates the per-component determinism hooks already implemented in T22 (`Node._stable_seed` via `blake2b`) and T23 (`Network._network_seed` via `blake2b`) into a harness-level reproducibility layer. The simulator already produces byte-identical event streams when given the same `global_seed` and the same constructor arguments; T27 adds the layer that produces those constructor arguments from a YAML file and injects the seed at the right surfaces.

**Chosen approach: Opaque-now, typed-later.**

- All six experiment-matrix axes (`n`, network timeline, adversary, protocol knobs, workload, seeds) are required top-level keys in the YAML — every config carries all six (honors [[concepts/experiment-matrix]] §2).
- Sections backed by finalized wiki contracts get full typed dataclasses today: `network` reuses `src/network/phases.{Phase, DelayDist, Partition}` directly; `seeds` is a new `SeedsConfig`; `n` and `t_max` are top-level scalars.
- The three sections whose wiki contracts are explicitly open-to-revision (adversary, protocol knobs, workload) are stored as `Mapping[str, Any]` opaque blobs — loaded, round-tripped through `Config`, **not** introspected by `build_run`. When T18 / T28+ / T41 land, each replaces its `dict` with a typed dataclass and updates the loader.

**Pinned macro-choices** (from the brainstorming session):

| Choice | Decision |
| :-- | :-- |
| Schema scope | Full schema, partial wiring (Approach B above) |
| Driver home | `src/config/` only (loader + factories). T41 will own a separate experiment-harness layer; T27 does not introduce `src/harness/`. |
| YAML library | PyYAML, `safe_load` only. Pin to `requirements.txt`. |
| Validation | Hand-rolled per-field validation in dataclass `__post_init__` and a `_validate_config` cross-field pass. No `jsonschema`, no `pydantic`. |
| Backlog gates | All four boundary-seam fail-fast checks in scope, applied at the offended boundary (not in the loader). |
| Sample configs | None committed to `configs/` at T27. The e2e determinism test uses an inline YAML string. |

## 2. Architecture and module layout

`src/config/` becomes a sibling of `src/{scheduler,nodes,network,event_log}`. Four files, no nested packages:

```
src/config/
  __init__.py        — re-exports: Config, SeedsConfig, RunHandle,
                       load_config, build_run, ConfigError
  schema.py          — frozen dataclasses: Config, SeedsConfig, RunHandle
                       (network sub-types reused from src/network/phases.py)
  loader.py          — load_config(path: str | Path) -> Config
                       PyYAML safe_load → required-key checks → schema
                       construction → cross-field validation
  factory.py         — build_run(config: Config, global_seed: int,
                                 node_factory: NodeFactory) -> RunHandle
                       constructs Scheduler → Network → Nodes; wires bind /
                       register / bind_network; calls Network.start; calls
                       Node.start in sorted(NodeId) order
```

`RunHandle` is a frozen dataclass `(scheduler, network, nodes: MappingProxyType[NodeId, Node])` — three handles in one named, immutable return value. The caller calls `scheduler.run(t_max=...)` directly; no convenience wrapper.

`ConfigError` subclasses `ValueError` so `pytest.raises(ValueError)` still catches it, but the custom name makes the source obvious in tracebacks. Constructor: `ConfigError(path, key_path, message)`; `__str__` returns `f"{path}: {key_path}: {message}"`.

No top-level CLI, no `if __name__ == "__main__"` entry. T41 introduces a CLI later.

## 3. Config schema

`src/network/phases.{Phase, DelayDist, Partition}` already exist as frozen dataclasses with `__post_init__` validation and an accompanying `validate_timeline` function. **Reuse them directly** — do not mirror them as `*Config` types.

Net-new types in `src/config/schema.py`:

```python
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable

from network.phases import Phase  # reused; see src/network/phases.py
from nodes import Node
from scheduler import Scheduler
from network import Network

NodeId = int
NodeFactory = Callable[[NodeId, int], Node]  # (node_id, global_seed) -> Node


@dataclass(frozen=True)
class SeedsConfig:
    n_runs: int


@dataclass(frozen=True)
class Config:
    n: int
    t_max: float
    seeds: SeedsConfig
    network: tuple[Phase, ...]
    adversary: Mapping[str, Any]       # opaque — typed by T18
    protocol_knobs: Mapping[str, Any]  # opaque — typed by T28+
    workload: Mapping[str, Any]        # opaque — typed by T41


@dataclass(frozen=True)
class RunHandle:
    scheduler: Scheduler
    network:   Network
    nodes:     Mapping[NodeId, Node]   # MappingProxyType view, immutable
```

YAML top-level shape (every key REQUIRED, including the three opaque sections — empty `{}` is the explicit "none configured" form; a missing key is a `ConfigError`):

```yaml
n: 4
t_max: 1000.0
seeds:
  n_runs: 20
network:
  phases:
    - t_start: 0
      t_end: .inf
      delay:
        kind: constant
        params: { delay: 50.0 }
      p_drop: 0.0
      partitions: []
adversary: {}
protocol_knobs: {}
workload: {}
```

Notes:

- `t_max` is top-level, not under a `run:` block. It is the only operational scalar needed today; adding a `run:` block now would prejudge T41.
- `n` is the validator-set size. The loader does **not** restrict `n ∈ {4, 7, 10, 16, 25}` — that value set is a property of the run catalog, not the schema.
- The loader does cross-validate `len(set(NodeIds derived from n))` against partitions, `t_max > 0`, `seeds.n_runs >= 1`.
- The schema contains no per-validator `NodeId` lists. The loader synthesises `NodeId ∈ {0, 1, ..., n-1}`; the factory uses those ints when constructing Nodes. A future revision could add a `validators:` block for per-validator stake overrides.
- `adversary: {}` means "no adversary today". The factory does not attach `Node.adversary` for any Node when this section is empty (the `Node.adversary = None` default in `Node.__init__` is the runtime state).

## 4. YAML loader

`loader.py` exposes one public function: `load_config(path: str | Path) -> Config`. Five sequential steps; every failure raises `ConfigError(path, key_path, msg)` and no other exception type — the loader is the funnel.

### 4.1. Parse

`yaml.safe_load(open(path).read())`. Any `yaml.YAMLError` is caught and re-raised as `ConfigError(path, "<root>", "YAML parse failed: ...")`. The top-level must be a `dict`; a YAML list at top level fails here. `safe_load` is mandatory — `yaml.load` with a non-safe loader is explicitly forbidden (forbidden-surface invariant of `wiki/concepts/reproducibility.md`).

### 4.2. Required-key check

A single hand-written dict-walk asserts the seven top-level keys (`n`, `t_max`, `seeds`, `network`, `adversary`, `protocol_knobs`, `workload`) and required sub-keys (`seeds.n_runs`, `network.phases`, per-phase `t_start` / `t_end` / `delay`, per-delay `kind` / `params`). Missing or extra keys raise `ConfigError`. **Unknown keys are a fail-fast error, not silently dropped** — a typo such as `n_run:` becomes a loud error rather than a config that silently defaults to 1 run.

### 4.3. Type coercion

YAML scalars come back as Python primitives; the loader pins them: `int(yaml["n"])`, `float(yaml["t_max"])`, etc. A YAML scalar that fails coercion (`t_max: [1000]`) raises `TypeError`, re-wrapped as `ConfigError`. The three opaque sections are passed through as whatever `safe_load` returns (a `dict`); the loader does not introspect their contents but does assert each is a `dict`.

### 4.4. Construct typed members

Build leaves first (`DelayDist(**delay_dict)`, `Partition(...)`, `Phase(...)`), then the `tuple[Phase, ...]`, then `SeedsConfig`, then `Config`. The existing `__post_init__` validators on `DelayDist` / `Partition` / `Phase` fire here — their `ValueError`s are caught and re-wrapped as `ConfigError` with the key path appended (e.g. `network.phases[0].delay.params.low`).

### 4.5. Cross-field validation

`_validate_config(config) -> None` runs last. Three checks:

- `1 <= config.n <= 10_000` (sanity ceiling; a typo `n: 1000000` would silently consume RAM in `build_run`).
- `config.t_max > 0` and `math.isfinite(config.t_max)`.
- For every `Partition` in every `Phase`, every `NodeId` it references is in `range(config.n)` — caught at load time, not at `Network.start()` time (the loader has more information than `validate_timeline` does at construction time).

The full timeline contiguity check (gaps / overlaps) is **not** duplicated here — `validate_timeline` runs inside `Network.start()` at factory time and already raises `ValueError`. The factory wraps that `ValueError` as `ConfigError` so the load-vs-build boundary is invisible to the caller.

### 4.6. Error format

`ConfigError.__str__` returns `f"{path}: {key_path}: {message}"` — a caller printing the exception gets a one-line locator. No tracebacks-through-yaml-internals for malformed input.

## 5. `build_run` factory and seed injection

`Node` is abstract (ABC) — the concrete subclass arrives with T28+. `build_run` takes a **node factory** the caller supplies; T27 itself never constructs a concrete protocol Node.

```python
def build_run(config: Config,
              global_seed: int,
              node_factory: NodeFactory) -> RunHandle: ...
```

Construction order is fixed and deterministic, mirroring the wiki six-phase bootstrap. The reason for each step is in one line:

1. `scheduler = Scheduler()` — empty heap; no RNG owned ([[concepts/simulation-design-runtime]] §1).
2. `network = Network(scheduler, config.network, global_seed)` — `_network_seed(global_seed)` seeds `net_rng` here (the existing `blake2b` derivation at `src/network/network.py:16`).
3. For `nid in range(config.n)`:
   - `node = node_factory(nid, global_seed)`;
   - assert `node.id == nid` — caught immediately if the factory misbehaves;
   - `network.register(node)`;
   - `scheduler.bind(node)`;
   - `network.bind(node)`.
   The per-Node `_stable_seed(global_seed, nid)` is consumed inside `Node.__init__` already (`src/nodes/node.py:51`). The factory does not re-seed.
4. `scheduler.bind_network(network)` — required for `PhaseAdvance` dispatch.
5. `network.start()` — runs `validate_timeline` with the now-populated registry; arms interior `PhaseAdvance` events.
6. For `nid in sorted(nodes.keys())`: `nodes[nid].start(t=0.0)`. **Must come after `network.start()`** because the protocol `_on_start` may call `broadcast`, which hits `network._guard_started`.

Return `RunHandle(scheduler, network, MappingProxyType(nodes))`. The immutable-view wrapper makes accidental post-construction mutation a `TypeError`, not a silent bug.

**What the caller does next:** wires `scheduler.event_sink` (the T24 `EventLogger`, or a list-collecting closure for tests) and calls `handle.scheduler.run(t_max=config.t_max)`. The factory does **not** set `event_sink`.

**Seed injection — three surfaces, factory orchestrates only:**

| Surface | Where seeded | Existing code path |
| :-- | :-- | :-- |
| `Network.net_rng` | `Network.__init__` via `_network_seed(global_seed)` | `src/network/network.py:16, 40` |
| `Node.rng` (per-node, n of them) | `Node.__init__` via `_stable_seed(global_seed, node_id)` | `src/nodes/node.py:19, 51` |
| Scheduler heap ordering | No RNG — deterministic `(t, node_id, seq)` tie-break | `src/scheduler/scheduler.py` |

There is no fourth surface. The factory's contribution to reproducibility is making sure `global_seed` reaches `Network.__init__` and `node_factory` for every Node. No global random state is touched. No `random.seed()` call.

**`global_seed` is NOT in the YAML** (per [[concepts/experiment-matrix]] §7 — seeds are enumerated externally by the harness as `0 ... n_runs-1`). It is a `build_run` parameter. A caller running one ad-hoc trial passes whatever int they want; a future T41 harness loops `for seed in range(config.seeds.n_runs): build_run(config, seed, factory)`.

## 6. Boundary-seam fail-fast gates

Four guards, each at the offended boundary. These are precondition checks for config-driven bootstrap; well-formed runs are unaffected. None of them live in `src/config/` — a Node constructed directly by a test (bypassing `build_run`) still needs to fail fast.

### Gate 1 — `Node.__init__` rejects `node_id < 0` and non-finite `weight`

```python
# src/nodes/node.py — extend the existing validation block
if node_id < 0:
    raise ValueError(
        f"node_id must be non-negative, got {node_id} "
        f"(values < 0 collide with the PhaseAdvance sentinel)")
if not math.isfinite(weight):
    raise ValueError(f"weight must be finite, got {weight}")
if weight < 0:                # already present
    raise ValueError(f"weight must be non-negative, got {weight}")
```

`node_id < 0` protects against the `PHASE_NODE_ID = -1` sentinel collision (`src/scheduler/scheduler.py:36`). `math.isfinite(weight)` rejects `NaN`, `+inf`, `-inf` — a non-issue today (no protocol uses `weight`) but a precondition for T32 Casper FFG where `weight` is staked balance.

### Gate 2 — `Network.register` rejects duplicate `node.id`

```python
# src/network/network.py — Network.register
def register(self, node: Node) -> None:
    if node.id in self.registry:
        raise ValueError(
            f"Network.register: NodeId {node.id} already registered")
    self.registry[node.id] = node
```

### Gate 3 — `Scheduler.bind` rejects duplicate `node.id`

```python
# src/scheduler/scheduler.py — Scheduler.bind
def bind(self, node: Any) -> None:
    if node.id in self.nodes:
        raise ValueError(
            f"Scheduler.bind: NodeId {node.id} already bound")
    self.nodes[node.id] = node
    # ... existing lambda wiring unchanged
```

Symmetric to Gate 2 — `build_run` calls them independently, and tests that bypass the factory might call only one.

### Gate 4 — `Network.start` is idempotent

```python
# src/network/network.py — Network.start
def start(self) -> None:
    if self._started:
        raise RuntimeError("Network.start: already started")
    validate_timeline(self.phases, set(self.registry))
    # ... rest unchanged; self._started = True at end
```

`self._started` already exists but is not checked at entry. A second `start()` re-runs `validate_timeline` (cheap) and re-schedules every interior `PhaseAdvance`, doubling phase rollovers on the heap.

## 7. `wiki/concepts/reproducibility.md` scope

The wiki page is one of T27's two artifacts. It is a **consolidation page** — three per-component determinism contracts already exist ([[concepts/node-model]] §8, [[concepts/network-model-phases]] §6, [[concepts/simulation-design-runtime]] §1); reproducibility.md pins the layer on top of them: harness-level reproducibility from `(Config, global_seed)` to byte-identical run behaviour.

Page structure (W3 design-contract style — prose + tables + Revisions section, but no "reference sketch" because the implementation exists; pointers to source files instead). Target length: ~180 lines, well under the 300-line ceiling in `docs/wiki-spec.md` § Page size.

| § | Section | One-line content |
| :-: | :-- | :-- |
| 1 | Framing | What reproducibility means here; three claims: YAML → Config; Config + seed → behaviour; captured event stream end-to-end. |
| 2 | Three pre-existing contracts | Pointer table to node-model §8, network-model-phases §6, simulation-design-runtime §1 with source files and exercising tests. |
| 3 | Single seed surface | `global_seed: int` is the sole randomness input; `_network_seed` and `_stable_seed` derivations; scheduler holds no RNG. |
| 4 | Config materialization | YAML → Config has no randomness; canonical iteration order; `Config` is frozen. |
| 5 | `build_run` determinism | Construction order pinned in §5 of this spec; no `random.seed`, no `os.urandom`, no `time.time`. |
| 6 | Test surface | E2E determinism test asserts byte-identical event streams across two same-seed builds; seed-sensitivity test asserts the seed actually flows. |
| 7 | Forbidden surfaces | Recap from the three upstream pages plus new ones T27 adds: `safe_load` only; `build_run` is grep-clean of global RNG / wallclock. |
| 8 | Open to revision | (a) cross-process replay tested only on CPython; (b) thread-safety contract single-threaded; (c) opaque-section pass-through preserves dict insertion order. |
| 9 | Sources | Back-links to node-model, network-model-phases, simulation-design-runtime, experiment-matrix §7. |
| 10 | Revisions | Empty at landing. |

### Index / log updates

- `wiki/index.md`: add `[[concepts/reproducibility]]` line under `## Concepts`. Update neighbouring lines whose "Forward references" comment mentions reproducibility (node-model, network-model-phases, simulation-design-runtime) — those are now resolved. This is index maintenance, not a wiki Revision.
- `wiki/log.md`: one entry, type `code`, per `docs/wiki-spec.md` § Log format.

Upstream pages (node-model, network-model-phases, simulation-design-runtime) get **no `## Revisions` entry** — reproducibility.md does not contradict any of their claims; it consolidates them. Their "Forward references (sibling pages, not yet authored)" lists may move the reproducibility line to "Inbound" as optional tidying, but this is not required for the contract.

## 8. Test surface

User-feedback memory: every implementation task ships unit + e2e tests. T27 splits them this way.

### Unit tests — new files under `tests/config/`

| File | Coverage |
| :-- | :-- |
| `tests/config/test_schema.py` | `Config` / `SeedsConfig` shape; frozen-dataclass immutability (`FrozenInstanceError` on mutation); `MappingProxyType` view on `RunHandle.nodes`. |
| `tests/config/test_loader.py` | Success path (canonical inline YAML); missing required key per top-level slot (parameterised over the seven keys); unknown key; `safe_load` rejects YAML tags (`!!python/object`); type-coercion edges (`t_max: "1000"` succeeds; `t_max: [1000]` fails); `ConfigError.__str__` contains `path:keypath:reason`. |
| `tests/config/test_factory.py` | `build_run` returns three populated handles; `node_factory` called with `(nid, global_seed)` for each `nid in range(n)`; `node.id == nid` mismatch fails fast; `Network.start` called before any `Node.start`; `Node.start` called in `sorted(NodeId)` order. |

### Unit tests — extensions for the four boundary gates

| File | New cases |
| :-- | :-- |
| `tests/nodes/test_node.py` | `Node(node_id=-1, ...)` raises `ValueError`; `Node(weight=math.nan, ...)` raises `ValueError`; `Node(weight=math.inf, ...)` raises `ValueError`. |
| `tests/network/test_network.py` | duplicate `Network.register(node)` raises `ValueError`; double `Network.start()` raises `RuntimeError`. |
| `tests/scheduler/test_scheduler.py` | duplicate `Scheduler.bind(node)` raises `ValueError`. |

### E2E determinism test — `tests/config/test_e2e_determinism.py`

Three test cases, sharing a `MinimalNode` fixture defined inline (concrete `Node` subclass, ~10 lines: `_on_start` broadcasts one message; `_on_message` halts; `_on_timer` raises — defensive, never called). The fixture exists only here; T28+ tests will use their own protocol Nodes.

```python
def test_byte_identical_event_stream_with_same_seed(tmp_path):
    yaml_path = tmp_path / "cfg.yaml"
    yaml_path.write_text(MINIMAL_YAML)

    captures: list[list] = []
    for _ in range(2):
        capture: list = []
        config = load_config(yaml_path)
        handle = build_run(config, global_seed=42, node_factory=MinimalNode)
        handle.scheduler.event_sink = lambda *args: capture.append(args)
        handle.scheduler.run(t_max=config.t_max)
        captures.append(capture)

    assert captures[0] == captures[1]


def test_different_seeds_diverge(tmp_path): ...   # seeds 42 and 43 → NOT equal

def test_load_then_load_again_is_identical(tmp_path): ...   # Config __eq__ structural
```

The captured tuple is `(t, node_id, seq, event)` — exactly what `event_sink` receives.

`MINIMAL_YAML`: `n: 4`; single-phase constant-delay network (`delay: 50.0`, `p_drop: 0.0`, no partitions); `t_max: 1000.0`; `seeds.n_runs: 1`; empty opaque sections. Embedded as a Python string in the test file, not committed to `configs/`.

**`MinimalNode` rather than reusing `tests/integration/`'s fixture.** T25's integration suite uses a ping-pong Node aimed at exercising 4 / 7 / 10-node delay distributions. Reusing it would couple T27's e2e test to T25's scenario; T27's `MinimalNode` is intentionally tiny and stable.

### Coverage

T27 does not gate on coverage but adds the new `src/config/*` files to whatever the existing `coverage.py` config covers. Branch coverage on `loader.py` and `factory.py` is where regressions will surface fastest. The T26 backlog already flagged adding `make coverage` with branch coverage as a follow-up.

### Not tested

Cross-process determinism (subprocess-spawning test). The seed derivations are `blake2b`-based and proven stable across processes already by [[concepts/node-model]] §8 Revision and [[concepts/network-model-phases]] §6.1 Revision; a subprocess test is mostly CI complexity for no signal. If the harness ever distributes runs across machines (T41+), the test moves there.

## 9. Out of scope

- Protocol-specific Nodes (T28+ Engineer tasks).
- Adversary attachment binding (T18-followup).
- Workload generation (T41+).
- CLI entry point — `python -m simulator <config.yaml>` is T41's.
- Sample YAML files in `configs/`.
- Multi-process / multi-machine reproducibility tests.
- `make coverage` Makefile target — pre-flagged for T26 Backlog follow-up; T27 does not add it.

## 10. Dependency change

`requirements.txt` currently reads `# The simulator (src/) currently uses the Python standard library only.` plus a comment that T27 will pin its YAML dependency. T27 pins:

```
PyYAML>=6.0
```

This is the simulator's first non-stdlib runtime dependency. `requirements.txt` comment is updated to reflect that.

## 11. Open questions for the planning step

None blocking. The following are deferred and listed here only so the planning step does not re-open them:

- Whether `Config` should grow a `protocol: str` discriminator so `build_run` can dispatch to a built-in registry of node factories (instead of requiring the caller to pass one). Deferred to T28's pickup — it is the task that first has a concrete protocol Node to dispatch to.
- Whether `SeedsConfig` should grow a `seed_seq: Sequence[int]` field for explicit seed enumeration instead of implicit `range(n_runs)`. Deferred to T41 (the experiment harness owns the enumeration policy).
- Whether the loader should accept multi-document YAML (`---` separators) for batched configs. Deferred to T41.
