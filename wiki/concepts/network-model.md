# Network Model

Design contract for the inter-node delivery layer (`Network`) in the
thesis simulator. Specifies what an honest message-delivery
infrastructure provides to validators, the seams it exposes to
[[concepts/node-model]] (T14, merged) and to its sibling W3 pages,
and the precise scope at which the simulator's network behaviour is
permitted to diverge from a real wire. Consumed by
[[concepts/message-types]] (T16), [[concepts/simulation-design]]
(T17), and the W4 implementations in `src/nodes/` (T22) and
`src/network/` (T23); exercised by the W9 delay experiments
(T46, T47) and the W10 adversarial experiments (T51–T55).

This page covers the **contract** — the `Network`'s shape, its seams,
the delivery guarantees it provides, and its adversary boundary.
Per-phase configuration mechanics — delay distributions, drop model,
partition expression, phase timeline rules, and the network-level
determinism contract — are specified in the companion page
[[concepts/network-model-phases]]. The split follows
`docs/wiki-spec.md` § Page size.

Out of scope and deferred to siblings: per-protocol message contents
(T16); event-loop scheduling and simultaneous-event tie-break (T17);
adversarial behaviour (T18 — the network is honest infrastructure
here, see §2 and §6); experiment configuration loading and YAML
schema (T19, T27).

## 1. Framing and scope

The `Network` is a *single system-level object* shared by every
`Node` in a run. It is not modelled as per-validator network stacks;
there is no notion of a `Node`'s own network adapter. Every outbound
call from a `Node` ([[concepts/node-model]] §7) is submitted to the
shared `Network`, which:

1. resolves the destination `NodeId` to the receiving `Node`
   (§3.2 endpoint table);
2. samples a delivery delay against the *currently active phase*'s
   distribution;
3. samples a per-message drop coin against the active phase's drop
   rate;
4. consults the active phase's partition predicate to decide whether
   the `(src, dst, t)` triple is reachable;
5. either drops the message silently or schedules a delivery event
   on the simulator scheduler (T17) at `t + delay`.

Steps 2–4 are specified in [[concepts/network-model-phases]].

This is the **latency-only, full-mesh** richness level chosen at
design time over latency+bandwidth or region-aware alternatives
(§8 [Open to revision]). The simulator does not model link capacity,
queueing, byte-level transmission time, or geography. Two
consequences:

- The thesis's experimental claims are about how each protocol
  *degrades under delay, drop, and partition* — not about
  *network saturation*. The W9 / W10 experimental matrix
  (T46, T47, T51–T55) is written in those terms.
- Adding bandwidth or regions later is a §8 revision, not a
  redesign — but it would touch [[concepts/message-types]] (T16)
  size declarations and the [[concepts/network-model-phases]]
  configuration shape.

## 2. Two-layer commitment

Inter-node delivery is modelled in two strictly separated layers,
mirroring the discipline established in [[concepts/node-model]] §1.

1. **System-level delivery infrastructure (T15, this page +
   [[concepts/network-model-phases]]).** The `Network` provides
   honest, finite-delay, lossy, optionally partitioned delivery of
   opaque `Message` envelopes. It does not introspect message
   contents and does not distinguish protocols. Uniform across PBFT,
   Casper FFG, Snowman, and Narwhal+Tusk.

2. **Per-protocol message contents (T16,
   [[concepts/message-types]]).** The `type` and `payload` fields of
   the §3 envelope are filled per `(protocol, type)` by T16. T15 does
   not enumerate or validate them.

The network is **honest infrastructure**. All adversarial behaviour
is owned by [[concepts/adversary-model]] (T18) and attaches at the
`Node` level (per [[concepts/node-model]] §9), not here. A Byzantine
validator that drops or delays messages does so via its own §9
`AdversaryProfile` slot, not via the `Network`. The honest network
can still be *hostile* — long delays, heavy drop, sustained
partitions — but that hostility is environmental, not Byzantine.
The boundary is restated in §6.

## 3. T14 seam — `Message` envelope and endpoint resolution

### 3.1. Message envelope

T15 inherits the envelope declared in [[concepts/node-model]] §6
verbatim:

```
Message := {
  src:     NodeId,
  dst:     NodeId | "broadcast",
  type:    str,        # owned by T16
  payload: object,     # owned by T16
  t_sent:  SimTime,    # set by src on emission (Node §7)
}
```

The network reads `src`, `dst`, and `t_sent`. It does not read
`type` or `payload`; both are opaque transit cargo. `t_sent` survives
delivery so latency metrics ([[concepts/evaluation-metrics]] T9.1
compute `t_delivered − t_sent`) have an authoritative source.

### 3.2. NodeId → endpoint resolution

Per [[concepts/node-model]] §2, T15 owns the `NodeId → endpoint`
resolution table. At simulation construction the experiment harness
(T19, T27) registers every `Node` with the `Network`, populating:

```
registry: dict[NodeId, Node]
```

Resolution is O(1) dict lookup: `registry[dst]` returns the
destination `Node` so the delivery event can be scheduled against
its `on_message` inbound hook ([[concepts/node-model]] §6). Failed
lookup (`dst` not in registry) is a configuration error and aborts
the run — it is not a runtime drop.

The `endpoint` attribute on a `Node` ([[concepts/node-model]] §2)
is **reserved for future use** at this richness level — region
labels, ports, multi-NIC support, etc. T15 does not introspect it
in the latency-only, full-mesh model. A future §8 revision adopting
region-aware delay would read `endpoint.region` and key the delay
table on the `(src.region, dst.region)` pair; the T14 seam is
unchanged.

`broadcast` resolves to *every member of the protocol's currently-
active validator set* (per [[concepts/node-model]] §5/§7). The
validator set is FSM-level state, not Network-level; the `Network`
receives the broadcast recipient list from the caller's outbound API
binding (§5), not from a network-level membership view.

## 4. Delivery contract

Every `send` or `broadcast` from a `Node` corresponds to
**at-most-one delivery attempt** per recipient. The attempt either
delivers the `Message` exactly once (via the recipient's
`on_message` hook) or drops it silently.

| Property | Guarantee |
| :-- | :-- |
| **Duplicate delivery** | Never. A single `send` produces at most one `on_message` invocation at the destination. |
| **Order preservation** | None. Two messages from the same sender to the same recipient may be delivered in either order or not at all. |
| **Sender notification on drop** | None. The sender receives no callback, exception, or event when a message is dropped. |
| **Retries** | None. The `Network` does not retry dropped messages. Protocol-level retry (PBFT view-change timeouts, Narwhal re-broadcast on missing certificates) is FSM-level. |
| **Latency floor** | Strictly positive. Every delivered message satisfies `t_delivered > t_sent`; zero-delay delivery is forbidden so the simulator's simultaneous-event tie-break ([[concepts/node-model]] §8) cannot collapse send and receive into a single instant. |

This contract matches the source-paper assumptions of all four
protocols: PBFT explicitly tolerates reordering and loss
([[algorithms/pbft]] §safety); Casper FFG, Snowman, and Narwhal+Tusk
each tag messages with their own coordinates — `(epoch, slot)`,
`block_id`, `(round, validator)` — so channel order is unnecessary
([[algorithms/pos]], [[algorithms/avalanche]],
[[algorithms/dag-based]]).

`broadcast` is **per-recipient independent**: one `broadcast` call is
modelled as `|validator_set|` independent `send` operations, each
with its own delay sample, drop coin, and partition check. A
broadcast is therefore not atomic — some recipients may receive
while others do not, in either order. This matches PBFT's reality
that pre-prepare can reach some replicas and not others, which is
exactly why prepare/commit phases each need their own `2f+1` echo
([[algorithms/pbft#three-phase-commit]]).

## 5. Outbound API integration

The `Network` is invoked exclusively through the bound outbound
methods on each `Node` ([[concepts/node-model]] §7). No `Node` calls
the `Network` directly. The scheduler (T17, T21) binds the
following at `Node` construction:

```
node.send       -> Network.submit_unicast(src, dst, type, payload,
                                          t_sent)
node.broadcast  -> Network.submit_broadcast(src, recipients, type,
                                            payload, t_sent)
```

`recipients` is supplied by the per-protocol FSM module's active
validator-set view ([[concepts/node-model]] §5 cross-instance
state). The `Network` does not maintain a separate validator-set
view; this is the FSM-membership seam flagged for revision in
[[concepts/node-model]] §12 item 3.

`submit_*` performs the §1 five-step pipeline (whose phase-dependent
steps 2–4 are specified in [[concepts/network-model-phases]]) and
either drops the message or schedules a delivery event:

```
scheduler.schedule(deliver(node=registry[dst], msg=Message{...},
                           t=t_sent + delay))
```

When the scheduler fires the delivery event, it invokes
`node.on_message(msg, t)`. T15 does not own timers; timer
scheduling is the scheduler's responsibility
([[concepts/node-model]] §6 / §7's `set_timer`), and timer-fired
callbacks (`on_timer`) do not interact with the `Network` at all.

### Bootstrap kickoff

Beyond the per-`Node` binding above, the `Network` exposes one
construction-time kickoff method:

```
Network.start() -> None
```

Called once by the experiment harness during bootstrap phase 5
(after §3.2 endpoint registration; before `Scheduler.run()`).
Schedules a `PhaseAdvance(phase_id)` event on the scheduler at each
`phase[i].t_end` boundary so the active phase rolls over without
per-pop polling. Internal-only; not part of the Node-facing API.
Added by T17 ([[concepts/simulation-design]] §7.1); see
[[diagrams/scheduler/bootstrap]] phase 5 for the bootstrap sequence
and [[concepts/network-model-phases]] §5 for the phase timeline
contract this method realises.

## 6. Adversary boundary

T18 ([[concepts/adversary-model]]) owns all operational adversary
semantics. **No adversary attaches at the `Network` level.** The
boundary is:

| Behaviour | Owner | Mechanism |
| :-- | :-- | :-- |
| Honest delay, drop, partition | T15 ([[concepts/network-model-phases]]) | Phase configuration; environmental, not Byzantine. |
| Byzantine drop / delay by a specific validator | T18, at `Node.adversary` | A `delayer` or `non-participant` `AdversaryProfile` gates the `Node`'s outbound `send`/`broadcast` calls; the `Network` itself never sees the suppressed messages. |
| Byzantine equivocation | T18, at `Node.adversary` | `equivocator` profile emits *additional* `Message` envelopes via §5; the `Network` delivers them honestly. |
| "Adversarial" network partition (e.g., MitM-style split) | Modelled as an *environmental* partition in [[concepts/network-model-phases]] §4 | Indistinguishable from "honest infrastructure happens to drop these messages"; this thesis does not model an actively malicious router that introspects payloads. |

This collapses the "is the network adversarial?" question:
adversaries are validators (per [[concepts/node-model]] §9). A
hostile network is just a phase configuration with heavy drop or
sustained partition. If a future research question requires a
network-layer adversary — a malicious relay that delays only PBFT
`PRE-PREPARE` messages, say — it lands as a §8 revision and would
introduce a `NetworkAdversaryProfile` slot here, but the v1 contract
intentionally omits that slot.

## 7. Reference sketch — `Network` class (illustrative, non-binding)

Per the design-contract style established for this thesis's W3 → W4
hand-off, this sketch is **not a specification**. It exists so T23
(`src/network/`) has a starting shape and so a reader scanning this
page cold can picture the artefact. T23 may diverge; divergences
land as `## Revisions` entries per `docs/wiki-spec.md` § Revisions
rule. Phase-configuration dataclasses (`Phase`, `DelayDist`,
`Partition`) are sketched on [[concepts/network-model-phases]] §7.

```python
# Reference sketch — illustrative, non-binding.
# Implementation (T23) may diverge; document via §8 + wiki-spec §revisions-rule.
# Phase / DelayDist / Partition dataclasses are defined on
# [[concepts/network-model-phases]] §7.

from random import Random
from typing import Any

SimTime = float
NodeId  = int

class Network:
    registry:  dict[NodeId, "Node"]     # populated at construction (§3.2)
    phases:    list["Phase"]            # see network-model-phases §7
    net_rng:   Random                   # seeded from global_seed
                                        # (network-model-phases §6.1)
    scheduler: "Scheduler"              # T17

    def submit_unicast(self, src: NodeId, dst: NodeId,
                       type: str, payload: Any, t_sent: SimTime) -> None: ...
    def submit_broadcast(self, src: NodeId, recipients: list[NodeId],
                         type: str, payload: Any, t_sent: SimTime) -> None: ...

    # Internal pipeline (§1 five-step;
    # sampling order in network-model-phases §6.2):
    def _try_deliver(self, src, dst, type, payload, t_sent) -> None:
        phase = self._phase_at(t_sent)
        if self.net_rng.random() < phase.p_drop:                # 1. drop coin
            return
        if any(p.blocks(src, dst) for p in phase.partitions):   # 2. partition
            return
        delay = phase.delay.sample(self.net_rng)                # 3. delay
        msg = Message(src=src, dst=dst, type=type,
                      payload=payload, t_sent=t_sent)
        self.scheduler.schedule(
            lambda: self.registry[dst].on_message(msg, t_sent + delay),
            t_sent + delay,
        )

    def _phase_at(self, t: SimTime) -> "Phase": ...             # O(log P) bisect

# --- Outbound API binding (§5) ---
# At Node construction, the scheduler binds:
#   node.send      = lambda dst, type, payload, t: \
#                    network.submit_unicast(node.id, dst, type, payload, t)
#   node.broadcast = lambda type, payload, t: \
#                    network.submit_broadcast(node.id,
#                                             node.fsm.active_validator_set(),
#                                             type, payload, t)
```

The sketch deliberately omits scheduler event-firing internals (T17)
and configuration loading (T19, T27) — each is bounded by another
page.

## 8. Open to revision

The contract above is precise but not final. The following points
are expected to be re-examined as T23+ implementation reveals fit
issues; any change beyond a typo lands as a `## Revisions` entry per
`docs/wiki-spec.md` § Revisions rule — not a silent overwrite.
Each item names the section affected (on this page or on
[[concepts/network-model-phases]]) and the task most likely to
surface the revision.

- **Bandwidth / link-capacity model** (§1; [[concepts/network-model-phases]] §1).
  The richness level is latency-only by design choice (option 1
  over option 2 at design time). T42 (RQ2 throughput) may show that
  the network is never the bottleneck and the thesis wants to claim
  it could be; at that point [[concepts/network-model-phases]] grows
  a `bandwidth` field per phase, T16 byte sizes become load-bearing,
  and queue dynamics enter the determinism contract.
- **Region-aware delay** ([[concepts/network-model-phases]] §2). The
  richness level is full-mesh by design choice (option 1 over
  option 3). T58 / W11 enhancement window may have time for a
  region-aware run set; at that point `Phase.delay` generalises from
  `DelayDist` to `dict[(region, region), DelayDist]` and starts
  consuming `Node.endpoint.region`. T14's §3.2 endpoint reservation
  makes this a non-breaking change at the seam.
- **Per-edge asymmetric partition allowlisting**
  ([[concepts/network-model-phases]] §4). v1 asymmetric partitions
  block all directed cross-group edges; T18 may discover an
  adversary that requires finer control (e.g., a one-way reachability
  hole between specific pairs). The `Partition` dataclass would gain
  an `allowed_edges` field.
- **Network-layer adversary slot** (§6). The v1 contract
  intentionally omits a `NetworkAdversaryProfile` slot — all
  adversary semantics live at the `Node` level per
  [[concepts/node-model]] §9. A future research question requiring
  a malicious relay (a router that delays only a specific protocol's
  messages, or introspects payloads to drop selectively) would land
  here as a §6 expansion, driven by T18 or by an RQ added in W11.
- **Bursty / correlated drop model**
  ([[concepts/network-model-phases]] §3). Independent Bernoulli per
  message is the v1 model. T47 heavy-loss experiments may show that
  real-world network failures are bursty (Gilbert–Elliott two-state,
  etc.) and the thesis's drop axis is unrealistic. At that point the
  "Per-phase global Bernoulli" specification expands to a drop-model
  selector with parameter sets per model.

This list is not exhaustive; it is the set of fit issues already
visible at design time. Other revisions become possible as T23, T25,
T41+, T46/T47, and T51–T55 land.

## 9. Sources

Design contract; no primary-literature citations. Synchrony-model
semantics are deferred to the protocol pages and to
[[concepts/synchrony-models]], which carry the bibliography.

**Inbound (existing wiki pages):**

- [[concepts/node-model]] (T14) — §6 `Message` envelope, §7 outbound
  API, §8 determinism contract. Owns the `Node`-level half of the
  seam this page describes.
- [[concepts/synchrony-models]] — partial-sync, asynchronous, and
  GST framing consumed by the phase narratives on
  [[concepts/network-model-phases]] §5.
- [[concepts/evaluation-metrics]] — §"Adversarial and delay axes"
  enumerates the delay distributions, drop axis, and partition axis
  pinned in [[concepts/network-model-phases]].
- [[algorithms/pbft]] — reordering / loss tolerance referenced by
  §4; partial-sync assumption referenced from
  [[concepts/network-model-phases]] §5.
- [[algorithms/pos]] — partial-sync with epoch tagging referenced
  by §4 and [[concepts/network-model-phases]] §5.
- [[algorithms/avalanche]] — asynchronous / probabilistic operation
  referenced by §4.
- [[algorithms/dag-based]] — asynchronous safety + reliable-
  broadcast dependency referenced by §4 and
  [[concepts/network-model-phases]] §5.
- [[concepts/fault-model]] — taxonomy boundary; T18 owns
  operational adversary modelling (§6).

**Companion page:**

- [[concepts/network-model-phases]] — per-phase configuration
  mechanics (delay, drop, partition, timeline) plus the
  network-level determinism contract. Split per `docs/wiki-spec.md`
  § Page size.

**Forward references (sibling pages, not yet authored):**

- [[concepts/message-types]] (T16) — fills the §3 envelope `type` /
  `payload` per `(protocol, type)`.
- [[concepts/simulation-design]] (T17) — discrete-event scheduler
  that fires delivery events queued by §5's `submit_*`.
- [[concepts/adversary-model]] (T18) — `Node`-level adversary
  attachment; closes the §6 boundary.
- [[concepts/experiment-matrix]] (T19) — consumes the phase timeline
  from [[concepts/network-model-phases]] §5 as part of the
  experiment YAML schema.
- [[concepts/reproducibility]] (T27) — harness-level `global_seed`
  injection consumed by [[concepts/network-model-phases]] §6.1.
- [[concepts/output-format]] (T40) — consumes delivery events
  (`t_sent`, `t_delivered`) for latency metrics
  ([[concepts/evaluation-metrics]] T9.1).

## Revisions

### 2026-05-13 — §5 outbound API integration extended with `Network.start()`

T17 ([[concepts/simulation-design]] §7.1) requires `Network` to
schedule its phase-boundary `PhaseAdvance` events on the scheduler
at bootstrap time, so the active phase rolls over deterministically
without per-pop polling. Added `Network.start() -> None` as a
construction-time kickoff method invoked once during bootstrap
phase 5. Internal-only; the §5 outbound binding for `send` /
`broadcast` is unchanged, and the honest-infrastructure adversary
boundary (§6) is unchanged.

### 2026-05-27 — §3.2 / §5 fail-fast guards on `register` and `start`

- **2026-05-27 (T39):** `Network.register(node)` rejects duplicate
  `node.id` with `ValueError` (B1; shipped with T23, recorded here
  against the backlog closure — symmetric with the unregistered-`dst`
  `KeyError` in `_try_deliver`). `Network.start()` rejects a second
  call with `RuntimeError` (B3; new in T39 — re-running `start` would
  re-schedule every interior `PhaseAdvance` boundary, double-firing
  phase rollovers). Test surface:
  `tests/network/test_network.py::test_duplicate_register_rejected`,
  `test_start_rejects_double_call`.
