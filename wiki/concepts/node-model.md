# Node Model

Design contract for the validator abstraction (`Node`) in the thesis
simulator. Specifies the shared structure every protocol's validator
implementation must conform to and the precise scope at which protocols
are permitted to differ. Consumed by [[concepts/network-model]] (T15),
[[concepts/message-types]] (T16), [[concepts/simulation-design]] (T17),
[[concepts/adversary-model]] (T18), [[concepts/reproducibility]] (T27),
and the W4 implementation in `src/nodes/` (T22). Out of scope and
deferred to siblings: wire-level message contents (T16); network delay
and loss (T15); event-loop logic (T17); adversary semantics (T18);
experiment configuration (T19, T27).

## Two-layer commitment

Validators are modelled in two strictly separated layers.

1. **Shared lifecycle layer.** Every `Node`, regardless of protocol,
   passes through the same lifecycle (`created → running → halted{...}`)
   and exposes the same inbound hook surface and outbound API. Uniform
   across PBFT, Casper FFG, Snowman, and Narwhal+Tusk.
2. **Per-protocol FSM layer.** Each protocol's per-decision state machine
   — PBFT's per-`(view, seq)` three-phase commit, Casper FFG's
   per-checkpoint two-round finalisation, Snowman's per-block confidence
   counter, Narwhal+Tusk's per-`(round, validator)` certificate-and-
   anchor structure — lives inside the `Node` as a protocol-specific
   module. State vocabularies, terminal states, and indexing schemes are
   **not unified** at this layer.

Cross-protocol measurement reconciliation — what makes the thesis's
comparative experiments commensurable — is the responsibility of
[[concepts/evaluation-metrics]] (T9.1) and the unified output schema
(T40), not of the FSM layer. Forcing a unified FSM vocabulary onto four
mechanically distinct protocols destroys mechanism fidelity (e.g.,
reduces Snowman's poll-driven confidence accumulation to a phantom
voting phase) and pre-empts the metric-layer reconciliation T9.1 exists
to perform. See [[concepts/consensus-families]] for the design-space
framing this layering preserves.

## Identity and weight

Three identity attributes, set at construction and read-only at the
shared layer.

- **`id: NodeId`** — integer, stable across the run; used for
  outbound message routing and as the deterministic seed input for
  per-`Node` randomness (see §8 [Determinism]).
- **`weight: float`** — non-negative; semantics are per-protocol
  (see table below).
- **`endpoint`** — opaque address consumed by
  [[concepts/network-model]] (T15) for delivery; not introspected at
  the shared layer. T15 owns the `NodeId → endpoint` resolution
  table; the §7 outbound API addresses peers by `NodeId` only.

Construction is driven by the experiment config (T19) and the
reproducibility harness (T27); the shared layer specifies only the
attribute surface, not how values are sourced.

### Per-protocol weight semantics

| Protocol | Threshold arithmetic | Per-validator weight | Mutability across run |
| :-- | :-- | :-- | :-- |
| **PBFT** | Count, `n = 3f+1` ([[concepts/quorum-arithmetic]]) | `1.0` (uniform) | Static |
| **Casper FFG** | Stake share, `f < 1/3` of total stake | Per-validator stake at genesis (epoch-effective stake lives in the FSM) | Static at shared layer; Casper FSM tracks epoch-effective stake separately |
| **Snowman** | Count of sample responses (`α_p`, `α_c` over `K`) | Stake (drives sampling probability only) | Static in this thesis's simulator |
| **Narwhal+Tusk** | Count, `n = 3f+1` | `1.0` (uniform) | Static |

The Snowman row carries the asymmetry [[concepts/evaluation-metrics]]
(T9.1) reconciles: the protocol arithmetic counts *responses*, not
stake; stake enters only via the sampling distribution. The shared
`weight` field therefore reflects sampling probability, while the FSM
module counts response cardinality independently.

The Casper row's mutability is layered: the shared `weight` attribute
is not mutated by the lifecycle layer; the Casper FFG FSM module
maintains an epoch-effective weight internally and resolves stake
changes (deposits, withdrawals, slashing-induced reductions) at epoch
boundaries.

## Shared lifecycle

Every `Node` traverses three stages, monotonically.

```
  +---------+       +---------+       +-----------------+
  | created |  -->  | running |  -->  | halted{reason}  |
  +---------+       +---------+       +-----------------+
```

- **`created`** — instantiated with identity attributes (§2) and a
  protocol module; the simulator clock has not advanced past start
  time; no inbound or outbound activity is permitted.
- **`running`** — clock has started; inbound hooks (§6) and outbound
  API (§7) are live; the per-protocol FSM (§4) operates within this
  stage and is orthogonal to it.
- **`halted{reason}`** — terminal. The `Node` ceases all message
  handling and timer firing. Monotonic: a halted `Node` cannot
  return to `running`.

### Halt reasons

| `reason` | Trigger | Protocol scope |
| :-- | :-- | :-- |
| `run_end` | Simulator's configured stop condition reached (max time, max committed blocks, max rounds) | All four |
| `crashed` | Explicit fault injection by the experiment harness (T52); also the canonical lifecycle representation of a non-participating adversary (T18) | All four |
| `slashed` | Per-protocol FSM detects slashable equivocation evidence and deducts the validator's deposit | Casper FFG only |
| `exited` | Per-protocol FSM observes a voluntary withdrawal at an epoch boundary | Casper FFG only |

`run_end` and `crashed` are initiated by the experiment harness;
`slashed` and `exited` are initiated by the per-protocol FSM. The
shared layer does not enumerate the FSM's internal conditions for
declaring slashing or exit; it only specifies that the resulting
transition flows through this lifecycle and emits the uniform halt
event below.

Network partition is **not** a halt reason. A partitioned validator
remains `running`; isolation is enforced by [[concepts/network-model]]
(T15) at the message-delivery layer, not by the lifecycle.

### Halt event emission

Every transition to `halted` MUST emit, via the outbound `emit` API
(§7):

```
halted(node_id: NodeId, reason: HaltReason, t: SimTime)
```

[[concepts/evaluation-metrics]] (T9.1) and the unified output
schema (T40) consume this event for liveness accounting (fraction
of validators in `halted{...}` over time, partitioned by reason).
The event is in addition to any FSM-level termination event from
§4 (e.g., a `slashed` halt is preceded by an FSM-level
`slashing_evidence` event).

## Per-protocol FSM

A `Node` hosts not one FSM but a **collection of FSM instances**, one
per consensus decision the protocol makes. The FSM module owned by a
`Node` maintains an instance table keyed by an index space that varies
per protocol. State vocabularies, terminal states, and indexing schemes
are deliberately not unified — see §1 (two-layer commitment). Mechanism
details (state-transition triggers, vote counting, quorum-intersection
arguments) live on the algorithm pages and are not duplicated here.

### Mapping table

| Protocol | Instance index | States | Terminal | `decided(...)` payload |
| :-- | :-- | :-- | :-- | :-- |
| **PBFT** | `(view, seq)` | `idle → pre_prepared → prepared → committed` | `committed` | `value=request_digest, instance_id=(view, seq)` |
| **Casper FFG** | `epoch` | `unjustified → justified → finalised` | `finalised` | `value=checkpoint_root, instance_id=epoch` |
| **Snowman** | `block_id` | `polling → accepted`; scalar `(preference, counter ∈ [0, β])` mutates within `polling` | `accepted` | `value=block_hash, instance_id=block_id` |
| **Narwhal+Tusk** | `(round, validator)` for certificates; `(anchor_round, anchor_id)` for commit | certificates: `proposing → certified → referenced`; anchor: `nominated → committed` | `committed` (anchor) | `value=anchor_cert_id, instance_id=(anchor_round, anchor_id)` |

Algorithm-page back-references for mechanism:

- PBFT: [[algorithms/pbft#three-phase-commit]]; view-change:
  [[algorithms/pbft#view-change]].
- Casper FFG: [[algorithms/pos#two-round-finalisation]].
- Snowman: [[algorithms/avalanche#snowman--linearised-production]];
  sampling: [[algorithms/avalanche#sampling-round]].
- Narwhal+Tusk: certificates:
  [[algorithms/dag-based#narwhal--the-dag-mempool]]; anchor commit:
  [[algorithms/dag-based#tusk-and-bullshark--zero-message-ordering]].

### Decision event emission

Every FSM instance reaching its protocol's terminal state MUST emit,
via the outbound `emit` API (§7):

```
decided(value, instance_id, t: SimTime)
```

`instance_id` is protocol-specific (see table). The unified output
schema (T40) treats `instance_id` as a protocol-tagged opaque key and
`value` as a digest, projecting both into a uniform CSV row.
[[concepts/evaluation-metrics]] (T9.1) enumerates which downstream
metrics each protocol's `decided` event feeds — latency, throughput,
finality time, fork rate.

The `decided` event is FSM-level and per-instance; it is distinct from
and orthogonal to the lifecycle-level `halted` event in §3.

### Cross-instance state

Each FSM module also maintains *cross-instance* state, internal to the
protocol module and not exposed at the shared API surface:

- **PBFT** — current view; `view_changing` flag (freezes all
  per-`(view, seq)` instances at the current view); view-change
  evidence buffer; high-water mark for committed `seq`.
- **Casper FFG** — justified/finalised checkpoint chain;
  epoch-effective validator set and stake table; slashing-evidence
  buffer.
- **Snowman** — accepted-block chain; per-block parent pointers for
  ancestor preference resolution.
- **Narwhal+Tusk** — DAG of certificates indexed by
  `(round, validator)`; per-round parent-reference quotas; anchor
  leader schedule.

T22 implementers may persist this cross-instance state however they
choose so long as determinism (§8) is preserved.

## Role taxonomy

Role is a **per-protocol** concept. The shared `Node` exposes no
common `role` field; each protocol's FSM module owns its own role
taxonomy. Cross-protocol role aggregation (e.g., "fraction of time
spent as leader") is the responsibility of the metric layer
([[concepts/evaluation-metrics]] T9.1, [[concepts/output-format]]
T40), not the shared `Node` layer.

### Per-protocol roles

| Protocol | Roles | Rotation | Notes |
| :-- | :-- | :-- | :-- |
| **PBFT** | `primary` (1 per view), `replica` (all `n`, including current primary) | Per view; deterministic schedule (e.g., `view mod n`); view change advances the schedule | All validators eligible; primary is also a replica |
| **Casper FFG** | `attester` (all validators in epoch committee), `proposer` (1 per slot) | Slot proposer drawn deterministically from current epoch's validator set | Simulator does not model RANDAO; the Casper FSM derives the per-epoch proposer schedule deterministically from `(global_seed, epoch)` — an FSM-level derivation identical on every `Node`, independent of `self.rng` (which is `Node`-local per §8) |
| **Snowman** | None | — | Every validator uniform; no consensus role differentiation |
| **Narwhal+Tusk** | `primary` (every validator, every round), `anchor_leader` (1, rotates every `r` rounds) | Primaries do not rotate; anchor leader on a deterministic schedule | Workers (Narwhal mempool batch sources) subsumed into primary at the simulator level — see §11 |

### Validator-set membership

Membership — which `Node`s are currently in the active validator set
— is per-protocol cross-instance state (§4); the shared lifecycle
does not model joins or exits.

- **PBFT**, **Narwhal+Tusk**, **Snowman**: validator set is fixed for
  the run in this simulator.
- **Casper FFG**: rotates at epoch boundaries; the Casper FSM module
  maintains the epoch-effective set. A `Node` removed from the active
  set by the FSM continues `running` (§3) until either the run ends,
  the harness crashes it, or the FSM emits a `slashed` / `exited`
  halt.

### Role vs adversary profile

Roles in this section are **consensus roles** — positions in the
protocol's normal-case message flow. They are distinct from
`adversary: Optional[AdversaryProfile]` (§9), which describes
operational deviation from honest behaviour. A `Node` may be both
`primary` (consensus role) and an equivocator (adversary profile);
the two are orthogonal and live in different slots.

## Inbound hook surface

The scheduler (T17, T21) drives a `running` `Node` by invoking three
callbacks (one one-shot lifecycle entry, two recurring): `start`,
`on_message`, and `on_timer`. The hook surface is intentionally
minimal: every other form of activity flows through the outbound API
(§7).

### `start(t: SimTime) -> None`

Invoked exactly once per `Node` during simulator bootstrap, before
the first event is popped, with `t == 0`. The Node's FSM uses this
to schedule its initial timers and emit its first messages —
without `start`, the heap can never be populated before `run()`
begins. Added by T17 ([[concepts/simulation-design]] §7.1); see
[[diagrams/scheduler/bootstrap]] phase 5 for the bootstrap sequence.

### `on_message(msg: Message, t: SimTime) -> None`

Invoked when a message addressed to this `Node` becomes deliverable
per [[concepts/network-model]] (T15)'s delay-and-loss model. Returns
nothing; all consequent activity is performed via the outbound API
(§7) inside the callback body. The message envelope, declared here
so [[concepts/message-types]] (T16) has a fixed boundary to fill:

```
Message := {
  src:     NodeId,
  dst:     NodeId | "broadcast",
  type:    str,        # protocol-specific tag (T16)
  payload: object,     # T16-defined per (protocol, type)
  t_sent:  SimTime,    # set by src on emission
}
```

`t_sent` survives delivery so latency metrics (T9.1: `t - t_sent`)
have an authoritative source. T16 owns `type` and `payload`; the
shared layer does not introspect either.

### `on_timer(timer_id: TimerId, payload: object, t: SimTime) -> None`

Invoked when a timer previously registered via `self.set_timer(...)`
(§7) reaches its delay. `timer_id` and `payload` are exactly the
values supplied at registration. FSM modules use the payload to
encode per-instance state (e.g., `(view, seq)` for a PBFT view-change
timeout); the shared layer does not interpret either.

T57 (adaptive timeout) tunes timer delays via §7's `set_timer`
surface, not via this callback.

### Time is a parameter, never read from the system

A `Node` MUST NOT read wallclock or any other time source not passed
to it. The simulator clock arrives via the `t: SimTime` parameter on
every inbound callback; outbound operations (§7) accept `t` as well.
This is a hard determinism requirement — see §8 — and applies
recursively to FSM modules.

### No `on_tick` callback

In a discrete-event simulator (T17), time advances to the next
scheduled event; there is no clock heartbeat. Anything periodic —
Casper slot boundaries, Narwhal round timeouts, Snowman poll
intervals — is expressed as a recurring self-registered timer (§7),
not a tick. This keeps the recurring inbound surface to two
callbacks (`on_message`, `on_timer`) and eliminates the per-protocol
question of what a tick means. The one-shot `start` hook is separate
and fires only at bootstrap.

## Outbound API

Surface a `running` `Node` calls to act on the world. T17/T21 (the
scheduler) provides these as bound methods on every `Node` instance.
T22 may call only these methods — direct access to the network, the
clock, or any global RNG is forbidden.

### Message emission

```
self.send(dst: NodeId, type: str, payload: object, t: SimTime) -> None
self.broadcast(type: str, payload: object, t: SimTime) -> None
```

Both construct a `Message` envelope per §6 (`src = self.id`,
`t_sent = t`) and submit it to [[concepts/network-model]] (T15) for
delivery. `broadcast` targets every member of the protocol's
currently-active validator set (§5); `send` targets a specific
`NodeId`. Snowman's sampled query is `send` per sampled peer, not
`broadcast`.

### Timer registration

```
self.set_timer(timer_id: TimerId, delay: SimTime,
               payload: object, t: SimTime) -> None
self.cancel_timer(timer_id: TimerId) -> None
```

`set_timer` registers a timer that fires `on_timer(timer_id, payload,
t + delay)` (§6). `timer_id` is caller-supplied; re-registering an
existing `timer_id` overwrites the prior registration.
`cancel_timer` is a no-op for unknown ids. T57 (adaptive timeout)
varies `delay`; the surface is fixed.

### Event emission

```
self.emit(event_type: str, fields: dict, t: SimTime) -> None
```

Submits a structured event for T24 (`src/logging/`) and the unified
output schema (T40). Two events are mandatory; their signatures are
pinned by this contract:

| Event | Source | Fields |
| :-- | :-- | :-- |
| `halted` | §3 lifecycle | `node_id`, `reason`, `t` |
| `decided` | §4 FSM termination | `value`, `instance_id`, `t` |

Additional event types are protocol-specific and standardised by
T24's schema.

### Determinism surface

```
self.rng: Random
```

Per-`Node` RNG attribute, seeded as specified in §8. All randomness
in the FSM module — peer sampling, jitter draws, timeout
randomisation — MUST flow through `self.rng`. Direct use of any
global random source is forbidden.

### Not on this surface

- No direct reference to other `Node`s — inter-node activity is
  message-level, routed by T15.
- No `now()` clock-read — `t` arrives as a parameter (§6).
- No mutation of identity attributes (§2): `id`, `weight`, `endpoint`
  are read-only after construction.
- No read of another `Node`'s FSM cross-instance state — private per
  §4.

## Determinism and reproducibility

A `Node` MUST be reproducible: given the same `global_seed` and the
same configuration, two runs produce byte-identical event streams.
The contract is enforced at the `Node` boundary, not retroactively
by [[concepts/reproducibility]] (T27).

### Per-`Node` RNG seeding

`self.rng` (§7) is seeded at construction from:

```
seed = hash((global_seed, node_id))
```

`global_seed` is supplied by the experiment harness; `node_id` is
the identity attribute (§2). Two `Node`s in the same run draw
independent streams; the same `Node` in two seed-identical runs
draws identical streams.

### Forbidden surfaces

Inside `Node` and any FSM module:

- No wallclock or other time source not passed as `t` (§6).
- No direct use of any global RNG (`random.random()` at module
  scope, `numpy.random.default_rng()` without explicit seeding,
  etc.). All randomness flows through `self.rng` (§7).
- No iteration over containers with non-deterministic order (raw
  `set`, `dict.keys()` under unconstrained Python versions). Use
  `sorted(...)` when iteration order is observable.

### Simultaneous-event tie-break

When two events on the scheduler queue share `t`, the scheduler
(T17) breaks ties by `(t, NodeId, sequence_number)`. The `Node`
does not need to be aware of this; it is documented here so T22
implementers do not introduce per-`Node` heuristics that reorder
events non-deterministically.

### Test surface

T25 (`src/tests/`) MUST include a determinism check: two
`global_seed`-identical runs produce identical `decided` and
`halted` event streams. Failures here block all downstream
experiments (T41+) and are the canonical regression detector for
violations of this section.

## Adversary attachment

[[concepts/adversary-model]] (T18) owns adversary semantics. T14
declares the **attachment surface** — the `Node`-level slot and the
per-protocol §4 FSM states / §7 outbound calls each generic adversary
modifies.

### `Node`-level slot

```
self.adversary: Optional[AdversaryProfile] = None
```

When non-`None`, the FSM module dispatches outbound emissions and
state-mutation decisions through `self.adversary` first; the profile
may modify, drop, or fork outbound messages and may inject state
mutations. `AdversaryProfile` is owned by T18.

`adversary` is orthogonal to consensus role (§5) and lifecycle (§3):
a `Node` may be `primary` AND an equivocator AND `running`.

### Generic-adversary attachment matrix

T18's four generic adversaries each attach at specific points per
protocol. N/A entries are first-class.

| | **PBFT** | **Casper FFG** | **Snowman** | **Narwhal+Tusk** |
| :-- | :-- | :-- | :-- | :-- |
| **delayer** | gate `broadcast` for PREPARE / COMMIT | gate attestation `broadcast` | gate query-response `send` | gate certificate `broadcast` |
| **equivocator** | as primary in `pre_prepared`: emit conflicting `PRE-PREPARE` per peer via `send` | at attestation: double-vote or surround-vote (slashable; triggers `slashed` halt §3 if detected) | reduces to **lying responder** at query-response: return non-preference colour | at header `proposing`: broadcast distinct headers to disjoint peer subsets |
| **non-participant** | skip outbound; or `halted{crashed}` | skip attestation; or `halted{crashed}` | skip query-response; or `halted{crashed}` | skip certificate outbound; or `halted{crashed}` |
| **leader-disruptor** | as primary: refuse / slow `PRE-PREPARE` to force view change | as slot proposer: refuse block production; or propose conflicting blocks (proposer equivocation, slashable) | **N/A** — no leader role (§5) | as anchor leader: withhold or refuse to reference the anchor |

The Snowman equivocator's "lying responder" reduction is pinned by
T18 ([[algorithms/avalanche#behaviour-under-adversarial-conditions]]);
PBFT/Casper/Narwhal equivocation relies on quorum-intersection
detection at vote aggregation, which Snowman lacks.

### Protocol-specific adversary slots

Three protocol-specific adversaries flagged by T18 plug into the same
slot:

- **Snowman colluding sub-sampler** — multiple `Node`s' adversary
  profiles coordinate query-response colours to bias `α_c`. T18
  specifies the coordination protocol.
- **Narwhal+Tusk data-availability withholding** — adversary certifies
  the header but withholds batch contents on subsequent `send`
  requests. T18 specifies which emission path is gated.
- **Casper FFG slashable equivocation refinements** — surround / double
  vote with explicit slashing semantics. Attachment is at attestation
  emission with payload distinguishing the slashing condition.

### Boundary

T14 declares attachment points only. Modification rules, intensity
knobs, stake-percentage parameters, and safety/liveness invariants
are T18's. T22 implements `self.adversary` as an opaque strategy
slot; T18 fills the strategy.

## Reference sketch (illustrative, non-binding)

Per the design-contract style established for this thesis's W3 → W4
hand-off, this sketch is **not a specification**. It exists so T22
(`src/nodes/`) has a starting shape and so a reader scanning this page
cold can picture the artifact. T22 may diverge; divergences land as
`## Revisions` entries per `docs/wiki-spec.md` § Revisions rule.

```python
# Reference sketch — illustrative, non-binding.
# Implementation (T22) may diverge; document via §11 + wiki-spec §revisions-rule.

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional, Protocol
from random import Random

class Lifecycle(Enum):    CREATED = 0; RUNNING = 1; HALTED = 2
class HaltReason(Enum):   RUN_END = 0; CRASHED = 1; SLASHED = 2; EXITED = 3

@dataclass
class Message:
    src: int                  # NodeId
    dst: int | str            # NodeId or "broadcast"
    type: str
    payload: Any
    t_sent: float             # SimTime

class AdversaryProfile(Protocol):  # owned by T18
    ...

class Node:
    id: int
    weight: float
    endpoint: Any
    rng: Random
    adversary: Optional[AdversaryProfile] = None
    status: Lifecycle = Lifecycle.CREATED

    # Inbound (§6) — overridden per FSM module.
    def on_message(self, msg: Message, t: float) -> None: ...
    def on_timer(self, timer_id: Any, payload: Any, t: float) -> None: ...

    # Outbound (§7) — bound by scheduler at construction.
    def send(self, dst: int, type: str, payload: Any, t: float) -> None: ...
    def broadcast(self, type: str, payload: Any, t: float) -> None: ...
    def set_timer(self, timer_id: Any, delay: float,
                  payload: Any, t: float) -> None: ...
    def cancel_timer(self, timer_id: Any) -> None: ...
    def emit(self, event_type: str, fields: dict, t: float) -> None: ...

# --- Protocol-specific FSM states (§4) ---

class PBFTState(Enum):           IDLE=0; PRE_PREPARED=1; PREPARED=2; COMMITTED=3
class CasperState(Enum):         UNJUSTIFIED=0; JUSTIFIED=1; FINALISED=2
class SnowmanState(Enum):        POLLING=0; ACCEPTED=1
class NarwhalCertState(Enum):    PROPOSING=0; CERTIFIED=1; REFERENCED=2
class NarwhalAnchorState(Enum):  NOMINATED=0; COMMITTED=1

class PBFTNode(Node):     ...   # instances by (view, seq); cross-instance: current view, view_changing flag
class CasperNode(Node):   ...   # instances by epoch; cross-instance: justified/finalised chain, epoch-effective stake
class SnowmanNode(Node):  ...   # instances by block_id; cross-instance: accepted-block chain
class NarwhalNode(Node):  ...   # FSMs: cert by (round, validator), anchor by anchor_id; cross-instance: DAG, anchor schedule
```

The sketch deliberately omits constructor signatures, RNG seeding
logic (§8), adversary dispatch logic (§9), and FSM transition bodies
(§4) — each is bounded by another section on this page and does not
need to be re-stated.

## Open to revision

The contract above is precise but not final. The following points are
expected to be re-examined as T22+ implementation reveals fit issues;
any change beyond a typo lands as a `## Revisions` entry per
`docs/wiki-spec.md` § Revisions rule — not a silent overwrite. Each item
names the section affected and the task most likely to surface the
revision.

- **Narwhal primary/worker decomposition** (§5). Workers are currently
  subsumed into primary at the simulator level. T38 may find the
  worker abstraction is necessary for accurate batch handling under
  data-availability adversaries (§9), at which point §5 and §4's
  Narwhal row both expand.
- **Snowman per-instance FSM** (§4). The production Snowman
  `α_p` / `α_c` split decouples preference flips from counter
  increments. The current `(preference, counter)` representation may
  be too coarse; T38 may need a richer FSM distinguishing the two
  thresholds.
- **Adversary dispatch granularity** (§9). `self.adversary` is a
  single optional slot per `Node`. T18 may discover some adversaries
  — notably the Snowman colluding sub-sampler — need cross-`Node`
  coordination state; if so, the slot extends with a registry surface.
- **Message envelope payload type** (§6). `payload: Any` is loose. T16
  may tighten to a per-protocol union; if so, the envelope's payload
  type narrows but `Any` remains valid for protocol-agnostic routing
  in T15.
- **Per-`Node` RNG seeding hash** (§8). `hash((global_seed, node_id))`
  uses Python's process-randomised hash for some inputs. T27 may need
  to replace with a stable hash (`hashlib.blake2b` or similar) once
  cross-process or cross-machine reproducibility is exercised.

This list is not exhaustive; it is the set of fit issues already
visible at design time. Other revisions become possible as T22, T28,
T32, T38, T18, T27, and T40 land.

## Sources

Design contract; no primary-literature citations. Mechanism semantics
are deferred to the algorithm pages, which carry the bibliography.

**Inbound (existing wiki pages):**

- [[algorithms/pbft]], [[algorithms/pos]], [[algorithms/avalanche]],
  [[algorithms/dag-based]] — per-protocol mechanisms (§4, §5, §9).
- [[concepts/consensus-families]] — design-space framing for the
  two-layer commitment (§1).
- [[concepts/quorum-arithmetic]] — `n = 3f+1` reasoning underlying
  §2 weight semantics for PBFT and Narwhal+Tusk.
- [[concepts/fault-model]] — taxonomy boundary; T18 owns operational
  adversary modelling (§9).
- [[concepts/evaluation-metrics]] — T9.1 metric-layer reconciliation;
  consumes §3 `halted` and §4 `decided` events.

**Forward references (sibling pages, not yet authored):**

- [[concepts/network-model]] (T15) — consumes the §6 `Message`
  envelope; routes `send` / `broadcast` from §7.
- [[concepts/message-types]] (T16) — fills §6 envelope `type` /
  `payload` per protocol.
- [[concepts/simulation-design]] (T17) — discrete-event scheduler
  driving §6 inbound and providing §7 outbound.
- [[concepts/adversary-model]] (T18) — fills the §9 attachment
  surface and `AdversaryProfile` slot.
- [[concepts/reproducibility]] (T27) — harness-level seeding and
  YAML config; consumes the §8 determinism contract.
- [[concepts/output-format]] (T40) — unified CSV row schema across
  protocols; consumes §3 `halted` and §4 `decided` events.

## Revisions

### 2026-05-13 — §6 inbound hook surface extended with `start(t)`

T17 ([[concepts/simulation-design]] §7.1) requires a per-`Node`
kickoff hook called once during bootstrap phase 5 to populate the
scheduler heap before `run()` begins. Added `start(t: SimTime) -> None`
as a third inbound callback alongside `on_message` and `on_timer`.
Updated the §6 intro from "two callbacks" to "three callbacks (one
one-shot lifecycle entry, two recurring)" and the `No on_tick`
subsection's closing language to reflect that the *recurring*
inbound surface remains two callbacks. Outbound API (§7),
determinism rules (§8), and adversary attachment (§9) are unchanged.

### 2026-05-13 — §9 scope contracts to attachment surface only

T18 ([[concepts/adversary-model]]) now owns adversary binding
semantics. §9 retains the attachment-surface declaration (per-protocol
FSM/outbound touchpoint matrix, `self.adversary` slot, protocol-
specific slot list) but no longer owns the cross-protocol semantic
detail. Per-cell binding semantics (mechanism, intensity range,
safety/liveness classification, invariant) live in
[[concepts/adversary-model]] §§3–7. The §9 matrix here remains as the
declaration of *which* `Node` method each capability gates; the
binding details for *what* the gated method does in each protocol are
on the adversary-model page.

No other §s are affected. Determinism rules (§8), inbound API (§6),
outbound API (§7), and role taxonomy (§5) are unchanged.

### 2026-05-19 — §8 per-Node RNG seeding uses a stable hash

T22 (`src/nodes/`) implements per-Node RNG seeding with a `blake2b`-derived
stable hash — `int.from_bytes(blake2b(f"{global_seed}:{node_id}").digest())`
— rather than the literal `seed = hash((global_seed, node_id))` of §8.
Python's built-in `hash()` is process-randomised for string and bytes inputs
and is not guaranteed stable across processes or machines; `blake2b` is. This
resolves the §11 open-to-revision item "Per-`Node` RNG seeding hash" and
upholds the §8 byte-identical-replay contract under T27's cross-process
reproducibility. No other §s are affected: the determinism *contract* is
unchanged; only the seed-derivation primitive is pinned.

### 2026-05-19 — §7 event-emission names sourced from the shared `event_types` module

T24 (`src/event_log/`) introduces `event_log/event_types.py` as the single
source of truth for `event_type` strings. `src/nodes/node.py` now imports
`HALTED` / `DECIDED` from it instead of the bare string literals `"halted"` /
`"decided"` in `Node.halt` and `Node._emit_decided`. A typo in an event-type
name now fails fast (`NameError`) rather than silently producing an
unrecognised event. The §7 mandatory-event table is unchanged in content —
the emitted strings are byte-identical; only their definition site moved.
No other §s affected.
