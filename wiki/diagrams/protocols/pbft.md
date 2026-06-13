# PBFT — Main Loop

> One `(view, seq)` consensus instance through PBFT's three-phase
> commit, plus the view-change branch taken when the instance stalls.
> Mechanism reference: [[algorithms/pbft#three-phase-commit]] and
> [[algorithms/pbft#view-change]]. FSM states:
> [[concepts/node-model]] §4. Message catalog: [[concepts/message-types]] §3.
>
> Navigation entry point: [[diagrams/index]]. Owning page:
> [[concepts/system-design-protocols]] §2.

## Diagram

```mermaid
%% PBFT — three-phase commit for one (view, seq) instance (n=4, f=1, quorum 2f+1=3)
sequenceDiagram
    autonumber
    participant Primary
    participant ReplicaB
    participant ReplicaC
    participant ReplicaD

    Note over Primary,ReplicaD: FSM instance keyed by (view, seq) — every replica starts the instance in state idle.

    rect rgb(240,240,240)
        Note over Primary,ReplicaD: pre-prepare phase
        Primary->>Primary: on_timer(propose) — batch local mempool, assign (view, seq), digest
        Primary->>ReplicaB: PRE-PREPARE(view, seq, digest, request)
        Primary->>ReplicaC: PRE-PREPARE(view, seq, digest, request)
        Primary->>ReplicaD: PRE-PREPARE(view, seq, digest, request)
        Note over ReplicaB,ReplicaD: on_message — validate, arm view-change timer, idle → pre_prepared
    end

    rect rgb(240,240,240)
        Note over Primary,ReplicaD: prepare phase
        ReplicaB->>Primary: PREPARE(view, seq, digest)
        ReplicaB->>ReplicaC: PREPARE(view, seq, digest)
        ReplicaB->>ReplicaD: PREPARE(view, seq, digest)
        Note over Primary,ReplicaD: ReplicaC and ReplicaD broadcast PREPARE likewise (arrows omitted)
        Note over Primary,ReplicaD: on 2f+1 matching PREPARE collected — pre_prepared → prepared
    end

    rect rgb(240,240,240)
        Note over Primary,ReplicaD: commit phase
        ReplicaB->>Primary: COMMIT(view, seq, digest)
        ReplicaB->>ReplicaC: COMMIT(view, seq, digest)
        ReplicaB->>ReplicaD: COMMIT(view, seq, digest)
        Note over Primary,ReplicaD: ReplicaC and ReplicaD broadcast COMMIT likewise (arrows omitted)
        Note over Primary,ReplicaD: on 2f+1 matching COMMIT — prepared → committed, cancel timer, emit decided(digest, (view, seq))
    end

    Note over Primary,ReplicaD: liveness recovery — taken only if the instance stalls

    opt view-change timer fires before committed
        Note over Primary,ReplicaD: new_view = view + 1 = 1 — new primary = new_view mod n = ReplicaB
        ReplicaC->>ReplicaB: VIEW-CHANGE(new_view, last_stable_seq, prepared_evidence)
        ReplicaD->>ReplicaB: VIEW-CHANGE(new_view, last_stable_seq, prepared_evidence)
        Note over ReplicaB,ReplicaD: cross-instance — view_changing set, all (view, *) instances frozen
        Note over Primary,ReplicaD: ReplicaB (new primary) collects 2f+1 VIEW-CHANGE
        ReplicaB->>Primary: NEW-VIEW(new_view, vc_proofs, reissued_pre_prepares)
        Note over Primary,ReplicaD: ReplicaB also broadcasts NEW-VIEW to ReplicaC, ReplicaD (arrows omitted) — advance current view, replay prepared-not-committed
    end
```

## What this pins

**Two broadcast quorum rounds, one digest.** PREPARE and COMMIT each
cost an all-to-all broadcast — `O(n²)` messages per instance — but
carry only the 32-byte digest, not the request payload
([[concepts/message-types]] §3). Only `PRE-PREPARE` carries the batch.

**The FSM transition is quorum-triggered, not message-triggered.** A
replica advances `pre_prepared → prepared` on the *2f+1-th* matching
PREPARE, not on each one. The handler counts; the transition fires once
the count crosses threshold. Same pattern for `prepared → committed`.

**`decided` is emitted once, on commit.** Reaching `committed` is the
instance's terminal state ([[concepts/node-model]] §4); the
`decided(value, instance_id, t)` event is the latency / throughput
anchor the metric layer consumes. No separate finalise message exists.

**View change is a fallback edge, not the main path.** The `if` branch
runs only when the view-change timer (armed at `pre_prepared`) fires
before `committed`. It freezes every instance at the current view,
elects `new_view mod n` as the next primary, and replays
prepared-but-not-committed work — the `O(n³)` worst case the family
pays for liveness ([[algorithms/pbft#view-change]]).

**`Primary` is also a replica.** It runs the prepare/commit handlers
like everyone else ([[concepts/node-model]] §5); the diagram omits its
PREPARE/COMMIT arrows only to reduce clutter.

## Cross-links

- Mechanism: [[algorithms/pbft#three-phase-commit]],
  [[algorithms/pbft#view-change]].
- FSM states and `decided`: [[concepts/node-model]] §4.
- Message schemas and byte budget: [[concepts/message-types]] §3.
- Adversary attachment (primary equivocation, leader-disruptor):
  [[concepts/adversary-model]] §5, §6.
- Pseudocode: [[concepts/system-design-protocols]] §2.

## Source

Authored as part of T20 ([[concepts/system-design]]).

## Revisions

None.
