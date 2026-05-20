# Reproducibility

Harness-level reproducibility contract for the thesis simulator. Pins the
end-to-end claim: same `(YAML config, global_seed)` produces a byte-identical
`event_sink` stream. Consolidates three per-component determinism contracts
already in place — [[concepts/node-model]] §8, [[concepts/network-model-phases]]
§6, [[concepts/simulation-design-runtime]] §1 — and adds the harness layer
(`src/config/`) that injects `global_seed` and constructs configurations
from YAML.

## 1. Framing

Three claims:
- (a) Same YAML file → same `Config` (deterministic load).
- (b) Same `Config` + same `global_seed` → same `RunHandle` behaviour.
- (c) Captured `event_sink` stream end-to-end is byte-identical under (a) ∧ (b).

The thesis' central artifact is comparative measurement across four
consensus protocols ([[algorithms/pbft]], [[algorithms/casper-ffg]],
[[algorithms/snowman]], [[algorithms/narwhal-tusk]]). Every reported metric
— latency, throughput, message complexity, behaviour under fault injection
— is a function of (configuration, randomness). If a run is not
byte-identical for the same input, every reported metric inherits hidden
process-level noise (Python's per-process `hash()` randomisation, iteration
order over unsorted containers, wallclock reads), and no cross-protocol
verdict survives auditing — a regression in one protocol's numbers can
never be distinguished from the run drifting.

The contract is therefore strict: byte-identical, not "statistically
equivalent". The cost is small (`blake2b` seeds + sorted iteration in two
hot paths) and the value high — a single seed reproduces an entire result
row, and an external auditor with the same `(YAML, seed)` reproduces the
artifact bit-for-bit.

## 2. The three pre-existing contracts

| Contract | Source | Test | Commits to |
| :-- | :-- | :-- | :-- |
| Per-Node RNG seeding via stable hash | `src/nodes/node.py:19, 51`; [[concepts/node-model]] §8 | `tests/nodes/test_node.py::TestRng` | identical `Node.rng` streams across processes |
| Per-Network RNG seeding via stable hash | `src/network/network.py:16, 40`; [[concepts/network-model-phases]] §6 | `tests/network/test_network.py` (delay-sampling determinism) | identical `net_rng` stream across processes |
| Scheduler heap ordering by `(t, node_id, seq)` | `src/scheduler/scheduler.py`; [[concepts/simulation-design-runtime]] §1 | `tests/scheduler/test_scheduler.py::TestOrdering` | unambiguous dispatch order at any `t` |

T27 adds the layer that drives `global_seed` into the first two contracts
and orchestrates the bootstrap in a fixed order.

## 3. The single seed surface

`global_seed: int` is the sole randomness input to the simulator. Two
derivations:

- `_stable_seed(global_seed, node_id)` → `Node.rng` (`src/nodes/node.py:19`),
  one per Node.
- `_network_seed(global_seed)` → `Network.net_rng`
  (`src/network/network.py:16`), one for the whole run.

Both derivations are `blake2b`-based, fixed-size, and process-stable —
Python's built-in `hash()` is randomised per process, which would break
byte-identical replay across machines. The scheduler holds no RNG.

`global_seed` is NOT in the YAML. The harness enumerates seeds externally
(see [[concepts/experiment-matrix]] §7 — common random numbers across
protocols).

## 4. Config materialization

`load_config(path) -> Config` is itself deterministic:
- YAML parsing is `yaml.safe_load` only — no Python-object tags.
- Required-key, type-coercion, leaf-construction, and cross-field checks
  run in a fixed sequence (`src/config/loader.py` § 4.1–4.5).
- `Config` is a frozen dataclass — post-load mutation raises
  `FrozenInstanceError`.
- The three opaque sections (`adversary`, `protocol_knobs`, `workload`)
  are round-tripped as `dict[str, Any]`; their insertion order matches
  PyYAML's parse order, which itself is document-order under
  `safe_load`.

## 5. `build_run` determinism

`build_run(config, global_seed, node_factory)` orchestrates the canonical
six-phase bootstrap with no randomness of its own (full sequence in
`src/config/factory.py:build_run`):

1. `Scheduler()` — no RNG.
2. `Network(scheduler, config.network, global_seed)` — seeds `net_rng`.
3. For `nid in range(config.n)`: `node_factory(nid, global_seed)`;
   `network.register(node)`; `scheduler.bind(node)`; `network.bind(node)`.
4. `scheduler.bind_network(network)`.
5. `network.start()` — runs `validate_timeline`, arms phase-advance.
6. For `nid in sorted(nodes)`: `nodes[nid].start(t=0.0)`.

The factory consumes no global state. `random.seed()`, `os.urandom`,
`time.time()` are not called. Iteration is `range(n)` (already sorted)
and `sorted(nodes)`.

## 6. Forbidden surfaces

Inside `src/config/`:
- `yaml.load` with any unsafe loader. `safe_load` only.
- `random.seed()`, `random.random()` at module scope.
- `os.urandom`, `secrets.*` for any randomness.
- `time.time()`, `time.monotonic()`, or any wallclock read.
- Iteration over unordered containers (raw `set`, `dict.keys()` without
  `sorted`) where the iteration order is observable in the event stream.

These are greppable invariants — a `grep -nE` of the listed APIs across
`src/config/` should produce zero hits.

## 7. Test surface

| Test | Asserts |
| :-- | :-- |
| `tests/config/test_e2e_determinism.py::TestSameSeedByteIdentical` | Two `build_run` invocations with the same `(YAML, global_seed)` produce byte-identical `event_sink` capture streams. |
| `tests/config/test_e2e_determinism.py::TestSeedDivergence` | Different `global_seed` values produce different capture streams — proves the seed actually flows through per-Node RNG draws. |
| `tests/config/test_e2e_determinism.py::TestLoadDeterminism` | Two `load_config` calls on the same file produce equal `Config`s. |
| Per-component contracts | Each upstream test from § 2 above. |

## 8. Open to revision

- **Cross-process replay tested only on CPython.** The `blake2b`-based
  seed derivations are process-stable by construction, but the e2e test
  runs in a single Python process. If the thesis adds a distributed
  harness (T41+), spawn a subprocess with the same `(YAML, global_seed)`
  and `diff` the captured streams.
- **Thread-safety contract is single-threaded.** The simulator is
  intentionally single-threaded; the determinism contract does not extend
  to a multi-threaded harness. T41+ if multi-threading lands.
- **Opaque-section preservation depends on dict insertion order.** Python
  3.7+ preserves dict insertion order; PyYAML `safe_load` returns dicts
  in document order. If PyYAML's parse order changes, the byte view of
  `Config.adversary` could differ — irrelevant today because the loader
  does not introspect these.

## 9. Sources

Design contract; no primary-literature citations.

**Inbound:**
- [[concepts/node-model]] §8 — per-Node RNG seeding contract.
- [[concepts/network-model-phases]] §6 — network-scoped RNG and sampling
  order.
- [[concepts/simulation-design-runtime]] §1 — scheduler determinism
  mechanisms.
- [[concepts/experiment-matrix]] §7 — seed enumeration policy and
  common-random-numbers across protocols.

**Source files:**
- `src/config/schema.py`, `src/config/loader.py`, `src/config/factory.py`
- `src/nodes/node.py:19` (`_stable_seed`)
- `src/network/network.py:16` (`_network_seed`)

## 10. Revisions

None.
