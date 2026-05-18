# Narwhal+Tusk — Main Loop

> One DAG round of the Narwhal mempool — header, vote, certificate —
> followed by the Tusk anchor-commit step that derives a total order
> with zero extra messages. Mechanism reference:
> [[algorithms/dag-based#narwhal--the-dag-mempool]] and
> [[algorithms/dag-based#tusk-and-bullshark--zero-message-ordering]].
> FSM states: [[concepts/node-model]] §4. Message catalog:
> [[concepts/message-types]] §6.
>
> Navigation entry point: [[diagrams/index]]. Owning page:
> [[concepts/system-design-protocols]] §5.

## Diagram

```swimlanes
title: Narwhal+Tusk — one DAG round + anchor commit (n=4, f=1, quorum 2f+1=3)

order: ValidatorA, ValidatorB, ValidatorC, ValidatorD
autonumber

note ValidatorA, ValidatorD: every validator proposes one HEADER per round; certificate FSM keyed by (round, validator). Round r shown for ValidatorA.

=: round r — Narwhal DAG mempool

ValidatorA -> ValidatorA: on_timer(round) — batch mempool, attach 2f+1 parent certs from round r-1
ValidatorA => ValidatorB: HEADER(r, validator=A, parent_certs, txs)
ValidatorA => ValidatorC: HEADER(r, validator=A, parent_certs, txs)
ValidatorA => ValidatorD: HEADER(r, validator=A, parent_certs, txs)
note ValidatorB, ValidatorD: B, C, D each broadcast their own round-r HEADER likewise (omitted)
ValidatorB --> ValidatorA: HEADER-VOTE(r, header_hash)
ValidatorC --> ValidatorA: HEADER-VOTE(r, header_hash)
ValidatorD --> ValidatorA: HEADER-VOTE(r, header_hash)
note ValidatorA: on **2f+1** HEADER-VOTEs: (r, A) **proposing → certified**
ValidatorA => ValidatorB: CERTIFICATE(r, validator=A, header_hash, signatures)
ValidatorA => ValidatorC: CERTIFICATE(r, validator=A, header_hash, signatures)
ValidatorA => ValidatorD: CERTIFICATE(r, validator=A, header_hash, signatures)
note ValidatorB, ValidatorD: CERTIFICATE is an eligible parent reference for round r+1

-: Tusk anchor commit — local predicate, zero messages

if: round r is an anchor round AND ≥ 2f+1 round-(r+1) certs reference round r's anchor
  note ValidatorA, ValidatorD: anchor `nominated → committed`; deterministically order the anchor's causal history; `emit decided(anchor_cert_id, (anchor_round, anchor_id))`
end
```

## What this pins

**Data availability and ordering are decoupled.** The HEADER / vote /
CERTIFICATE exchange (the DAG mempool) only certifies that a batch is
*available*; it decides nothing. Ordering is the separate Tusk step.
This is the structural split Narwhal's design is built around.

**Anchor commit costs zero wire messages.** The `if` block is a *local
predicate* over the validator's own DAG copy — no `Message` envelope is
constructed, no `Network` traffic results ([[concepts/message-types]]
§6). Every validator independently re-derives the same total order from
the same certificate references. This is why `consensus_msgs_per_acu`
is zero for this protocol ([[concepts/metric-reconciliation]]).

**Every validator proposes every round.** Unlike PBFT (one primary) or
Casper FFG (one slot proposer), all `n` validators broadcast a HEADER
each round in parallel ([[concepts/node-model]] §5). The diagram tracks
ValidatorA's header only; B, C, D run identical flows concurrently.

**`HEADER-VOTE` is unicast back to the proposer.** Only the proposer
needs the 2f+1 votes to assemble a `CERTIFICATE`; the certificate is
then broadcast so validators that missed the original header can still
use it as a round-`r+1` parent ([[concepts/message-types]] §6).

**`decided` fires at the anchor, not the header.** A certified header
is `referenced`, not decided; the terminal `committed` state and the
`decided` event belong to the *anchor* instance
([[concepts/node-model]] §4). One anchor commit finalises a whole
batch of causally-prior certificates at once.

## Cross-links

- Mechanism: [[algorithms/dag-based#narwhal--the-dag-mempool]],
  [[algorithms/dag-based#tusk-and-bullshark--zero-message-ordering]].
- FSM states (certificate + anchor) and `decided`:
  [[concepts/node-model]] §4.
- Message schemas and the mempool/consensus split:
  [[concepts/message-types]] §6, [[concepts/metric-reconciliation]].
- Adversary attachment (data-availability withholding, header
  equivocation): [[concepts/adversary-model]] §5, §7.
- Pseudocode: [[concepts/system-design-protocols]] §5.

## Source

Authored as part of T20 ([[concepts/system-design]]).

## Revisions

None.
