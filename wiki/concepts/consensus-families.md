# Consensus Families — Design Space Map

> Prerequisite for this page: [[concepts/consensus-overview]] (what a
> blockchain is, how blocks are made, why consensus is needed, why it is
> hard). This page assumes that framing and jumps straight to the
> comparative positioning of the four families.

The four families evaluated in this thesis, positioned along the axes
introduced in [[concepts/consensus-properties]],
[[concepts/synchrony-models]], [[concepts/fault-model]], and
[[concepts/quorum-arithmetic]]. Return here whenever a design decision in a
specific family needs to be justified by reference to what the family
concedes and what it gains.

## Comparison table

| Family | Synchrony | Finality | Fault threshold | Primary cost concession |
| :---- | :---- | :---- | :---- | :---- |
| **PBFT-style** | Partial | Deterministic, single-slot | `f < n/3` | `O(n²)` per-block messages; view-change cost on leader failure. |
| **PoS-finality** | Partial | Deterministic, checkpoint-based | `f < n/3` by stake | Latency to finality spans multiple epochs; complex slashing logic. |
| **Avalanche-style** | Asynchronous / probabilistic | Probabilistic `(1 − ε)` | `f < n/5` for safety under repeated sampling (parameter-dependent) | No hard finality; parameter tuning required; security under adaptive adversary analysed probabilistically. |
| **DAG-based** | Asynchronous | Deterministic, induced by DAG order | `f < n/3` | Higher per-node storage and bandwidth; deeper pipeline before order is fixed. |

## Propagation of the BFT problem

Every family is a design response to the Byzantine Generals Problem (see
[[concepts/byzantine-generals]]). The tree below captures the propagation;
each branch is expanded in its own algorithm page.

```
                 +-------------------------------+
                 |  Byzantine Generals Problem   |
                 |  n >= 3f+1, safety + liveness |
                 +---------------+---------------+
                                 |
     +---------------------------+---------------------------+
     |                           |                           |
 Deterministic,            Deterministic,            Probabilistic,
 quorum-based,             stake-weighted +          random
 partial sync              economic                  subsampling
     |                           |                           |
 [[algorithms/pbft]]       [[algorithms/pos]]        [[algorithms/avalanche]]
 PBFT, HotStuff,           Casper FFG /              Snowball -> Snowflake
 Tendermint                Gasper / LMD              -> Avalanche
     |                           |                           |
     +-----------+---------------+---------------------------+
                 |
       Separate data-availability  ----> [[algorithms/dag-based]]
       from ordering (DAG layer)         Narwhal/Tusk,
                                         Bullshark,
                                         Mysticeti
```

## One-line framing per family

- **[[algorithms/pbft]] family.** Three-phase commit under partial synchrony;
  `3f+1` replicas; view-change recovers liveness after GST. Streamlined by
  HotStuff (linearised, pipelined) and Tendermint (round-robin leaders).

- **[[algorithms/pos]] family.** Conventional blockchain substrate overlaid
  with a BFT finality gadget (Casper FFG, Gasper). Two sequential
  supermajority votes finalise a checkpoint irreversibly. `3f+1`-by-stake;
  slashing deters equivocators economically as well as cryptographically.

- **[[algorithms/avalanche]] family.** Abandons quorums in favour of repeated
  random subsampling; confidence accumulates as repeated sample agreement is
  observed. Converges with probability `1 − ε`. Finality is probabilistic,
  not absolute.

- **[[algorithms/dag-based]] family.** Narwhal reliably broadcasts transaction
  batches and records a DAG of causal dependencies; Tusk/Bullshark/Mysticeti
  derive a total order from the DAG with zero extra messages in the common
  case. BFT kernel is unchanged (still `3f+1`) but operates on DAG vertices
  rather than raw transactions.

## When to consult this page

- Before any chapter that makes cross-family comparative claims.
- When sanity-checking an experimental result ("why would Family X degrade
  first under delay?" — look at its synchrony column).
- When deciding which family a simulator knob stresses hardest.
