# Consensus Overview

> Introductory page for readers new to blockchain consensus. Sits upstream of
> the technical foundation pages ([[concepts/byzantine-generals]],
> [[concepts/fault-model]], [[concepts/synchrony-models]],
> [[concepts/quorum-arithmetic]], [[concepts/consensus-properties]],
> [[concepts/flp-impossibility]]) and of the four-family design map
> [[concepts/consensus-families]]. Answers the prior question those pages
> assume: what is the system these protocols serve, and why is agreement
> the hard part?

## What a blockchain is

A **blockchain** is an append-only ordered log of transactions, maintained
in replicated form across a set of nodes that do not trust one another.
Every participating node keeps its own copy. The defining guarantee is that
all non-faulty copies converge on the same prefix of the log, even when
some nodes fail or lie, and even when the underlying network delays or
drops messages arbitrarily.

Three structural properties follow:

- **Append-only.** Once a block is committed, it is never removed or
  reordered by any non-faulty node. This is what makes prior transactions
  effectively permanent.
- **Chained.** Each block carries the cryptographic hash of its
  predecessor, so tampering with any past block breaks every subsequent
  hash. This is not the agreement mechanism; it is the data-integrity
  substrate that makes disagreement *detectable*.
- **Replicated.** Every **validator** — a node in the active set that
  participates in producing the log — maintains a full copy. No single
  node is the authoritative source of truth.

A **Layer 1 (L1)** blockchain is one that operates as its own base layer:
the log it maintains is the authoritative record, not a summary of
activity on another chain. The four families evaluated in this thesis are
all L1 designs. Layer-2 protocols (rollups, payment channels, sidechains)
inherit their security from an L1 substrate and are out of scope — see
[[concepts/problem-statement]].

## How blocks are created

At each **height** (slot, round, epoch — the terminology varies by family)
the validator set must produce exactly one new block. The typical stages:

1. **Proposer selection.** One validator is designated to propose the next
   block. Selection is round-robin (PBFT-style, Tendermint), stake-weighted
   pseudorandom (PoS families), or implicit in the ongoing broadcast
   pattern (DAG families). In probabilistic families
   ([[algorithms/avalanche]]) there is no single proposer — instead many
   candidate values circulate and convergence is produced by sampling.
2. **Transaction bundling.** The proposer selects a set of pending
   transactions from its local mempool, orders them, and wraps the result
   in a block header (parent hash, height, timestamp, proposer identity,
   signature).
3. **Broadcast.** The proposer sends the candidate block to the rest of
   the validator set. Other validators receive it through the network —
   reliably in principle, subject to delay, reordering, and loss in
   practice.
4. **Consensus.** Validators run a protocol to decide — collectively —
   whether this candidate becomes the block at this height, or is rejected
   in favour of another. This is the step that differs across families
   and that this thesis evaluates.
5. **Commit.** A validator that has concluded (per its family's finality
   rule) that the block is agreed appends it to its local copy of the log
   and advances to the next height.

Block creation without consensus would be trivial: one node writes,
everyone else accepts. Consensus becomes the hard problem once we require
correctness even when the proposer may be faulty, when validators may
disagree about what they received, or when the network may reorder or
suppress messages.

## Why consensus is needed

Distributed ledgers must solve one core problem: **at each height, all
non-faulty validators commit the same block.** Three concrete failure
modes motivate this.

- **Concurrent proposals.** In some families more than one validator may
  hold a candidate at the same height — temporary forks under natural
  network partitions, deliberate parallel proposals in DAG families,
  multiple candidate values in probabilistic families. Without a consensus
  rule, each non-faulty validator could pick differently, splitting the
  ledger.
- **Malicious proposers.** A proposer may send conflicting blocks to
  different subsets of validators — the *equivocation* attack. Without an
  agreement rule, one half of the network commits one block and the other
  half commits a different one at the same height, and the two halves
  then diverge permanently.
- **Network pathology.** Even with honest participants, delay and message
  loss cause different validators to observe different sequences of
  events. The protocol must still converge to a single committed history.

The formal vocabulary for what consensus must guarantee — Agreement,
Validity, Termination, Integrity — is given in
[[concepts/consensus-properties]]. The canonical abstraction of the
problem (generals who may be traitors coordinating across unreliable
messengers) is [[concepts/byzantine-generals]].

## Why consensus is hard

Three structural obstacles make consensus hard in the environment a public
blockchain runs in.

1. **Some validators may be Byzantine.** "Byzantine" means *arbitrary*:
   faulty validators may crash, lie, collude, or send conflicting messages
   to different peers. The fault-class taxonomy is in
   [[concepts/fault-model]]. Every algorithm family in this thesis is
   designed for the Byzantine case — weaker models (crash-only,
   omission-only) admit simpler protocols (Paxos, Raft) that are
   unsuitable for open, adversarial settings.
2. **The network is not synchronous.** Real networks delay, reorder, and
   drop messages. A validator that has not heard from a peer cannot
   distinguish "peer is slow" from "peer is offline" from "peer is lying".
   The space of formal timing assumptions — synchronous, partial-synchronous,
   asynchronous, probabilistic — is catalogued in
   [[concepts/synchrony-models]].
3. **FLP impossibility.** Under pure asynchrony — no timing assumptions
   at all — [[concepts/flp-impossibility]] proves that no deterministic
   protocol can guarantee both safety and liveness with even one
   crash-faulty process. Every deployed protocol relaxes one of FLP's
   assumptions: partial synchrony ([[algorithms/pbft]],
   [[algorithms/pos]]), randomisation ([[algorithms/avalanche]]), or
   layered decomposition over a broadcast mempool
   ([[algorithms/dag-based]]).

The combination of Byzantine faults, an asynchronous network, and FLP is
why a forty-year research literature on consensus exists, and why no
single protocol dominates the others. Each family is a different trade in
the same design space — different assumptions relaxed, different costs
paid. The two-thirds supermajority (`3f+1`) that recurs in most of these
protocols falls out of this trade; the derivation is in
[[concepts/quorum-arithmetic]].

## How this thesis approaches the problem

The thesis evaluates four Layer-1 consensus families under a common
discrete-event simulator:

- [[algorithms/pbft]] — partial-synchrony deterministic BFT (Castro–Liskov
  PBFT, HotStuff, Tendermint).
- [[algorithms/pos]] — proof-of-stake BFT finality gadgets over a chain
  substrate (Casper FFG, Gasper).
- [[algorithms/avalanche]] — probabilistic BFT via repeated random
  subsampling (Slush → Snowflake → Snowball → Avalanche, production
  variant Snowman).
- [[algorithms/dag-based]] — BFT layered over a DAG mempool
  (Narwhal+Tusk, Bullshark, Mysticeti).

Their comparative positioning (synchrony assumptions, fault thresholds,
finality model, primary cost concession) is in
[[concepts/consensus-families]]. The specific gap the thesis closes, its
objectives, and the scope boundary are in [[concepts/problem-statement]].
The measurable research questions structuring the empirical work are in
[[concepts/research-questions]], and the unified metric schema is
[[concepts/evaluation-metrics]].

Readers new to this material should proceed in roughly this order:

1. This page.
2. [[concepts/byzantine-generals]] — the formal problem.
3. [[concepts/consensus-properties]] — what any solution must guarantee.
4. [[concepts/fault-model]] and [[concepts/synchrony-models]] — the
   adversary and network assumptions.
5. [[concepts/flp-impossibility]] and [[concepts/quorum-arithmetic]] —
   why the problem is non-trivial, and where the `3f+1` bound comes from.
6. [[concepts/consensus-families]] — how the four families relate.
7. The algorithm pages themselves, in any order.

## Source

New authorship for task T1.1, filling the introductory framing gap flagged
as High-severity finding H1 in [[lint/2026-04-21_sync-report]]. No single
raw source: the content is a consolidation of introductory framing already
established in the S0 foundation pages and in the surveys [14], [15] (see
[[concepts/annotated-bibliography]]). No new claims are introduced — all
factual content is derivable from pages already in the wiki.

## Revisions

None.
