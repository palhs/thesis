# Chapter 2 — Literature Review

## 2.1 Three families, one impossibility

A Layer-1 blockchain keeps a shared ledger across validators that do not trust
one another. They have to agree on the same transactions in the same order;
otherwise the same coin can be spent twice, or a transaction that already
settled can be rewritten. Reaching that agreement while some validators behave
arbitrarily is the Byzantine Generals Problem [1] [[wiki/concepts/byzantine-generals]]. Chapter 1 fixed the three results that
bound any solution: the `3f+1` Byzantine threshold [1], the FLP impossibility
[2], and the partial-synchrony relaxation that makes consensus solvable for
`f < n/3` [3] [[wiki/concepts/synchrony-models]].

No protocol escapes these bounds, so each must concede something. Every
Layer-1 design answers the same question: relax the timing assumption, the
fault model [[wiki/concepts/fault-model]], or both. The CAP theorem makes the
cost concrete: under partition a chain must give up either Consistency or
Availability, with partition-tolerance non-negotiable [18]
[[wiki/concepts/cap-theorem]]. The three families are three answers, each traced
from the Byzantine Generals Problem in Figure 2.1. Each makes a different choice:

- **PBFT-style** keeps the classical Byzantine fault model and the `3f+1`
  quorum, relaxing only timing (synchrony to partial synchrony) to make
  consensus solvable [4]; HotStuff [5] and Tendermint [6] inherit the same
  quorum-intersection arithmetic [[wiki/concepts/quorum-arithmetic]].
- **PoS-finality** keeps the `3f+1` quorum and partial synchrony but adds an
  *economic* layer: a validator that equivocates can be slashed, converting
  the Byzantine fault model from an external assumption into a
  disincentivized behavior [7], [8].
- **Avalanche-style** abandons the quorum entirely, replacing it with
  repeated random sampling and accepting a non-zero safety-violation
  probability `ε` in exchange for asynchrony tolerance and per-validator cost
  independent of `n` [9], [10].

The choice each family makes determines the vocabulary in which it later
reports performance (§2.3).

**Figure 2.1 ([[diagrams/concepts/bft-families-tree]]).** From the Byzantine
Generals Problem to the three families.

## 2.2 The three families

Table 2.1 traces one event, a block becoming irreversible, through all three
families. PBFT and Snowman act on the block directly; Casper FFG finalizes
blocks in batches at fixed checkpoints, not one at a time. All three accumulate
*agreement* until reversal is impossible; they differ in what counts as
agreement, how much locks the block, and how many times that repeats. On those
axes the two deterministic families nearly coincide (about two-thirds, met
twice, `ε = 0`); Avalanche-style is the outlier: about 80% of a small random
sample, repeated `β` times, for a small positive `ε`.

The table's last row names each family's adversarial weak point within the §1.4
taxonomy (silence, delayed voting, equivocation), measured directly in Chapter
4. The simulator-level treatment of each protocol is deferred to Chapter 3.

**Table 2.1 — How one block becomes irreversible.** Protocol-native terms
are in parentheses. Notation is defined below the table.

| | PBFT-style | PoS-finality | Avalanche-style |
|:--|:--|:--|:--|
| Synchrony assumption | partial synchrony | partial synchrony | asynchronous / probabilistic |
| Block proposer | one node per block, rotating | one node per block, stake-weighted | one node per block, round-robin |
| Unit of agreement | one vote per validator | one vote per validator, weighted by stake | one response per sampled peer |
| Agreement threshold | ⅔ of all validators (`2f+1`) | ⅔ of total stake | 80% of a small random sample (`α_c` of `K`) |
| Agreement rounds | two phases, sequential | two phases, epochs apart | `β`≈15 consecutive rounds |
| Finality guarantee | deterministic, `ε = 0` | deterministic, `ε = 0` | probabilistic, `ε ≤ (1−α_c/K)^β` |
| Communication cost | `O(n²)` | `O(n)`, aggregated to ~1 message | `O(K·β)` per validator |
| Adversarial pressure point | leader failure (liveness); `n/3` threshold (safety) | checkpoint delay (liveness); ≥⅓ stake burn (safety) | counter stall (liveness); statistical bound (safety) |

**Notation.**

| Symbol | Meaning | Relationships |
|:--|:--|:--|
| `n`, `f` | validators; maximum Byzantine | `n = 3f+1` for the quorum-based families |
| `K` | peers polled per round (Snowman) | `K ≈ 20`, or `min(20, n−1)` at thesis scale |
| `α_c` | sampled peers that must agree to count a round | `α_c ≈ 0.8K`; holding `α_c/K ≈ 0.8` fixes the safety-curve shape |
| `β` | consecutive agreeing rounds before a block is accepted | `β ≈ 15`; holding `β` fixed makes `ε` invariant in `n` |
| `ε` | probability two honest validators commit conflicting blocks | `0` for the two deterministic families; `≤ (1−α_c/K)^β` for Snowman |

## 2.3 Why the published numbers do not compare

The three families have all been measured, and the field has produced three
taxonomic surveys plus one quantitative methodological precedent. None yields
a cross-family comparison under matched conditions, for two distinct reasons.

### 2.3.1 Each family measures a different thing

The papers each family publishes measure what that family's design is trying
to prove.

PBFT and HotStuff were replacing slow replicated databases, so their papers
report throughput: thousands of operations per second on a low-latency local
network [4], [5]. Casper FFG was grafted onto Ethereum's existing block stream
to add irreversibility; it reports finality delay in epochs, two of them,
about twelve minutes on mainnet [7], [8]. Avalanche skips quorum entirely and
reports safety probability `ε` and per-transaction latency for one fixed
parameter set [9], [10].

None of them covers all three dimensions. PBFT says nothing about finality
delay. Casper FFG says nothing about throughput. Avalanche's latency figure is
only valid at one `K, β` setting: change the parameters and the number
changes too.

No shared unit exists for asking "which family is faster?" or "which is
safer?" All three families have been studied extensively; the measurements
just were not designed to sit next to each other.

### 2.3.2 Prior surveys and the one quantitative precedent

Comparative surveys of the three families exist [14], [15], [16], but none runs
its own measurements. The two that aggregate reported numbers include their own
disclaimer: harnesses are not matched, so the figures sit next to each other
without being comparable. They map the problem well enough; filling it is
another matter.

One study comes close. Gervais *et al.* [17] built a unified Proof-of-Work
simulator with a single metric schema, swept across block sizes and propagation
delays: the kind of controlled cross-condition evaluation the three BFT
families have never received. The limitation is the target: Proof-of-Work only.
No equivalent study covers PBFT-style, PoS-finality, and Avalanche-style
protocols under matched conditions.

## 2.4 The gap

The three families respond to the same impossibility and differ only in which
assumption they relax, so they are commensurable as objects of comparison.
Their per-family measurements, however abundant, do not support cross-family
judgment. The obstacle is that the measurements were never designed to be compared, not
any absence of data. The one methodological precedent for a matched evaluation is
Gervais *et al.* [17], which has been applied to Proof-of-Work only. Chapter 3
responds with a unified discrete-event simulator, a shared metric schema
instantiated identically for the three families, and an experiment matrix that
sweeps the network-delay, Byzantine-fraction, validator-set-size, and
adversarial-strategy axes under common assumptions
[[wiki/concepts/research-questions]], [[wiki/concepts/experiment-matrix]].
