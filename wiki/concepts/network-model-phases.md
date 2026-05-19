# Network Model — Phase Configuration

Companion page to [[concepts/network-model]] (T15). Specifies the
runtime mechanics of the `Network`'s phase abstraction: delay
distributions, drop model, partition expression, phase timeline
rules, and the network-level determinism contract. Consumed by
[[concepts/network-model]] §5 (`submit_unicast` /
`submit_broadcast` use the per-phase parameters defined here) and
by [[concepts/experiment-matrix]] (T19, which loads phase timelines
from experiment YAML); fills steps 2–4 of the five-step delivery
pipeline declared on [[concepts/network-model]] §1.

The split from [[concepts/network-model]] follows `docs/wiki-spec.md`
§ Page size. The "Open to revision" register that covers items
spanning both pages lives on [[concepts/network-model]] §8 and is
not duplicated here.

## 1. Per-phase model

A run is divided into a contiguous, non-overlapping sequence of
**phases** declared in the experiment configuration. Each phase
defines the active delay distribution, drop rate, and partition
topology over a half-open time interval `[t_start, t_end)`. At every
`send`, the `Network` ([[concepts/network-model]] §1) looks up the
phase containing the current simulator clock `t` and applies that
phase's parameters.

A phase is the unit at which network conditions change. There is no
intra-phase variation: within a single phase, delay distribution,
drop rate, and partition topology are all fixed. Transitions are
instantaneous at phase boundaries.

The phase abstraction is how the simulator exercises both partial
synchrony and asynchrony from [[concepts/synchrony-models]]: a
typical PBFT/Casper test declares an asynchronous phase before GST
(heavy-tailed delay, sustained partition) and a partial-sync phase
after GST (uniform-bounded delay, no partition). DAG-protocol tests
can omit the GST transition entirely
([[algorithms/dag-based]] §model-and-assumptions). The mapping
between thesis-level synchrony narratives and concrete phase
configurations is owned by [[concepts/experiment-matrix]] (T19), not
by this page.

## 2. Delay distributions

A delay distribution is a named distribution with parameters,
producing strictly-positive `SimTime` samples on demand. The
catalogue tracks the axes in
[[concepts/evaluation-metrics#adversarial-and-delay-axes]].

| Distribution | Parameters | Use in this thesis |
| :-- | :-- | :-- |
| `constant` | `delay` (ms) | Reference baseline (T41); useful for "perfect-channel" control runs. |
| `uniform` | `low`, `high` (ms) | Bounded variation; principal distribution for T46 moderate-delay experiments (100–500 ms). |
| `normal` | `mean`, `std`, `clip_low` | Gaussian jitter around a mean; `clip_low` enforces the latency floor. Default `clip_low = 1 ms`. |
| `exponential` | `mean` | Memoryless tail; standard model for queueing-free wide-area latency. |
| `heavy_tail` | `scale`, `shape` (Pareto α) | Long-tail latency for stressing partial-sync protocols pre-GST and for T47 heavy-delay (1–5 s with tail). |

All distributions must produce strictly-positive samples; any
implementation that can sample zero or negative values is
non-conformant (per [[concepts/network-model]] §4 latency floor).
Samples drawn from this catalogue use the §6 network RNG, not any
`Node.self.rng`.

Per-`(src, dst)` asymmetric delay tables are out of scope at this
richness level; if needed for region-aware revision
([[concepts/network-model]] §8), the phase's `delay` field
generalises from a single distribution to a
`dict[(region, region), DelayDist]`.

## 3. Drop model

Per-phase global Bernoulli: a single drop rate `p_drop ∈ [0, 1)`
applies to every message sent during the phase. For each message,
an independent coin is flipped against the §6 network RNG; on
heads (probability `p_drop`) the message is dropped silently.

| Sub-decision | Value |
| :-- | :-- |
| Scope | Per-phase global. Not per-link, not per-`(protocol, message-type)`. |
| Independence | Each message's coin is independent of every other. No bursty-loss model. |
| Composition with partition | Drop coin is flipped *before* the partition predicate (§4). A message is delivered iff `not dropped AND not partitioned`; the two mechanisms compose disjunctively. |
| Sender feedback | None (per [[concepts/network-model]] §4). |

`p_drop = 0` is the default (loss-free phase). `p_drop = 1` is
forbidden by configuration — use a partition that covers all pairs
instead. It expresses "no delivery" more honestly and scopes
explicitly to which validators are affected.

## 4. Partition expression

A **partition** is a time-bounded predicate over `(src, dst)` pairs
that, when active, prevents delivery between members of disjoint
groups. Within a phase, a partition is declared as:

```
partition := {
  groups:    list[list[NodeId]],   # ≥ 2 disjoint groups
  symmetric: bool = True,
}
```

Semantics:

- **Symmetric (`symmetric: True`, default).** A message from `src`
  to `dst` is dropped iff `src` and `dst` are in *different*
  groups of the partition. Within the same group, delivery
  proceeds normally (subject to §2 delay and §3 drop).
- **Asymmetric (`symmetric: False`).** Groups are ordered. By
  default all directed cross-group edges are blocked; per-edge
  allowlisting is a revision listed on [[concepts/network-model]] §8
  (not in v1).
- **Validators not in any group.** Validators omitted from every
  group are unconstrained by this partition — reachable to and from
  every other unconstrained validator and every group member
  (subject to §2 / §3).
- **Multiple partitions in one phase.** A phase may declare
  multiple partitions; their effects compose disjunctively (a
  message is partition-dropped iff *any* active partition blocks
  it).

A partition is a *network-layer* artefact: a partitioned `Node`
remains `running` ([[concepts/node-model]] §3 — "Network partition
is not a halt reason"); only its message traffic is affected.
Partition-induced drops are indistinguishable from §3 Bernoulli
drops from the sender's perspective
([[concepts/network-model]] §4: no sender feedback).

## 5. Phase timeline rules

| Rule | Statement |
| :-- | :-- |
| **Contiguity** | Phases form a contiguous sequence: `phase[i].t_end == phase[i+1].t_start`. No gaps. |
| **Coverage** | The first phase starts at `t = 0`; the last phase's `t_end` is the run's stop condition (or `+∞` for open-ended runs terminated by max-block / max-round). |
| **No overlap** | Phases do not overlap. At any `t`, exactly one phase is active. |
| **Boundary convention** | Half-open `[t_start, t_end)`. A message sent at `t = phase[i].t_end` is in `phase[i+1]`. |
| **Minimum count** | At least one phase. A single phase covering `[0, +∞)` is the static-network base case. |
| **Pre-validation** | Phase timeline is validated once at run start. Configuration errors (gaps, overlaps, empty group lists, undeclared `NodeId`s) abort before `t = 0`. |

The thesis-level synchrony narrative is owned upstream by
[[concepts/synchrony-models]]; the concrete mapping from
"partial-sync test", "asynchronous test", "static-network baseline"
to a phase timeline is owned downstream by
[[concepts/experiment-matrix]] (T19). This page only specifies
*what a phase timeline looks like*, not *which timelines the thesis
runs*.

## 6. Determinism

The `Network` is reproducible: given the same `global_seed` and the
same phase configuration, two runs produce byte-identical delivery
streams.

### 6.1. Network-level RNG

T15 maintains a **single network-scoped RNG**, distinct from any
`Node.self.rng` ([[concepts/node-model]] §8):

```
self.net_rng = Random(seed=hash(("network", global_seed)))
```

All delay sampling (§2) and drop coin-flipping (§3) flow through
`self.net_rng`. The network RNG is intentionally not derived from
any single `Node`'s seed — the network is a system-level entity,
not the property of any one validator.

Partition checks (§4) are deterministic functions of
`(src, dst, phase)` and do not consume RNG.

### 6.2. Sampling order

Per message, the `Network` performs samples and checks in a fixed
order:

1. Drop coin: `net_rng.random() < p_drop`. If dropped, stop.
2. Partition check: deterministic, no RNG. If partitioned, stop.
3. Delay sample: `delay_dist.sample(net_rng)`. Schedule delivery.

This order is pinned so determinism does not depend on whether a
message *would have been* partitioned: a partition-dropped message
does not consume a delay sample, preserving the §6.1 RNG state
exactly across configurations that differ only in partition
topology.

### 6.3. Forbidden surfaces

Inside the `Network`:

- No wallclock or other time source not passed as the simulator
  clock `t`.
- No direct use of any global RNG. All randomness flows through
  `self.net_rng`.
- No iteration over unordered containers in delivery scheduling.
  Broadcast recipient lists are iterated in `sorted(NodeId)` order
  so RNG consumption (one delay sample per recipient) is
  deterministic.

### 6.4. Test surface

T25 (`src/tests/`) MUST include a network-level determinism check:
two `global_seed`-identical runs produce identical delivery streams
(`(src, dst, type-tag, t_sent, t_delivered)` tuples). This is a
*pair* with the Node-level determinism check in
[[concepts/node-model]] §8.4 and detects T15-side regressions that
the Node-level check cannot.

## 7. Reference sketch — phase dataclasses (illustrative, non-binding)

Per the design-contract style established for this thesis's W3 → W4
hand-off, this sketch is **not a specification**. It exists so T23
(`src/network/`) has a starting shape for the phase-configuration
types. T23 may diverge; divergences land as `## Revisions` entries
per `docs/wiki-spec.md` § Revisions rule. The `Network` class that
consumes these types is sketched on [[concepts/network-model]] §7.

```python
# Reference sketch — illustrative, non-binding.
# Implementation (T23) may diverge; document via
# [[concepts/network-model]] §8 + wiki-spec §revisions-rule.
# Used by the `Network` class sketched on [[concepts/network-model]] §7.

from dataclasses import dataclass, field
from random import Random

SimTime = float
NodeId  = int

@dataclass
class DelayDist:
    kind: str          # "constant" | "uniform" | "normal" | "exponential" | "heavy_tail"
    params: dict       # see §2 table
    def sample(self, rng: Random) -> SimTime: ...   # strictly positive
                                                    # ([[concepts/network-model]] §4)

@dataclass
class Partition:
    groups: list[list[NodeId]]
    symmetric: bool = True
    def blocks(self, src: NodeId, dst: NodeId) -> bool: ...

@dataclass
class Phase:
    t_start: SimTime
    t_end:   SimTime                    # half-open [t_start, t_end)
    delay:   DelayDist
    p_drop:  float = 0.0
    partitions: list[Partition] = field(default_factory=list)
```

The sketch deliberately omits `DelayDist.sample` bodies (§2),
`Partition.blocks` logic (§4), and configuration loading
(T19, T27) — each is bounded by another section on this page or on
a sibling page.

## 8. Sources

Companion to a design contract; no primary-literature citations.
The "Open to revision" register spanning both halves of T15 is
maintained on [[concepts/network-model]] §8.

**Parent page:**

- [[concepts/network-model]] (T15) — the contract this page extends.
  §1 defines the five-step delivery pipeline whose steps 2–4 are
  specified here; §5 binds the outbound API that consumes phase
  parameters; §6 closes the adversary boundary that keeps these
  mechanics on the *honest* side; §8 registers revisions that span
  both pages.

**Inbound (existing wiki pages):**

- [[concepts/synchrony-models]] — partial-sync, asynchronous, and
  GST framing consumed by §1 / §5.
- [[concepts/evaluation-metrics]] — §"Adversarial and delay axes"
  enumerates the delay distributions, drop axis, and partition axis
  pinned in §2 / §3 / §4.
- [[concepts/node-model]] (T14) — §3 lifecycle ("partition is not
  a halt reason") referenced by §4; §8 determinism contract paired
  with §6 here.
- [[algorithms/dag-based]] — asynchronous safety + reliable-
  broadcast dependency referenced by §1 / §5.

**Forward references (sibling pages, not yet authored):**

- [[concepts/experiment-matrix]] (T19) — consumes the §5 phase
  timeline as part of the experiment YAML schema.
- [[concepts/reproducibility]] (T27) — harness-level `global_seed`
  injection consumed by §6.1.

## Revisions

### 2026-05-19 — §6.1 network RNG seed switched to `blake2b`

T23 implementation. §6.1 specifies the network RNG as
`Random(seed=hash(("network", global_seed)))`. Python's built-in
`hash()` of a tuple containing a `str` is process-randomised
(`PYTHONHASHSEED`), so that seed differs between processes — which
breaks the byte-identical cross-process replay this very page (§6)
promises. T23 diverges: the seed is derived by a `blake2b` digest of
`b"network:" + str(global_seed)` (`_network_seed()` / design spec
Decision D), a stable 64-bit value identical across processes and
machines. This mirrors the [[concepts/node-model]] §8 fix applied to
the per-`Node` RNG (2026-05-19). The §6.2 sampling order and §6.3
forbidden surfaces are unchanged.
