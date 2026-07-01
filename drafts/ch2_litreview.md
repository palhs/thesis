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
| Block proposer | one rotating leader (primary) | one leader per block (stake-weighted) | one leader per block (round-robin) |
| Unit of agreement | a replica's vote (`PREPARE`/`COMMIT`) | an attestation, weighted by stake | a polled peer's preference (`QUERY-RESPONSE`) |
| Agreement threshold | ~⅔ of all validators (`2f+1`) | ~⅔ of all stake | ~80% of a small random sample (`α_c` of `K`) |
| Agreement rounds | twice (`prepare`, `commit`) | twice, ≥2 epochs apart (`justify`, `finalize`) | `β`≈15 sampling rounds in a row |
| Finality guarantee | deterministic, `ε = 0` | deterministic, `ε = 0` | probabilistic, `ε ≤ (1−α_c/K)^β` |
| Communication cost | `O(n²)` | `O(n)`, BLS-aggregated to ~1 | `O(K·β)` per validator (aggregate `O(n·K·β)`) |
| Adversarial pressure point | stall the leader (liveness); safety holds `<n/3` | stall finality; breaking safety burns ≥⅓ stake | stall the counter (liveness); safety statistical |

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

### 2.3.1 Each family reports in its own vocabulary

Each family's primary papers report what its design concedes, and little
else. The PBFT and HotStuff papers report operations per second on a
low-latency LAN with view-change cost as the disturbance metric [4], [5].
Casper FFG reports time-to-finality in *epochs* (fixed batches of blocks, 32
on Ethereum), a unit that becomes physical only after multiplying by the block
time [7], [8]. Avalanche reports two
figures absent elsewhere: the probabilistic safety bound `ε` and a
per-transaction latency under one `K, α, β` parameterization [9], [10]. Table
2.2 collects the headline numbers.

**Table 2.2 — Reported metric vocabulary across families.** Headline numbers
from the cited primary sources. The columns are not directly comparable.

| Family | Throughput (reported) | Latency (reported) | Fault threshold | Source |
| :---- | :---- | :---- | :---- | :---- |
| PBFT (LAN) | Thousands of ops/s | Sub-10 ms | `< n/3` | [4] |
| HotStuff | Linear in `n` after optimizations | 3-round commit | `< n/3` | [5] |
| PoS-finality (Casper FFG / Gasper) | Block-proposal rate of underlying chain | Two-epoch finality (≤12.8 min on Ethereum) | `< 1/3` of stake | [7], [8] |
| Avalanche | ~3.4 ktps (testnet) | ~1.35 s | Parameter-dependent (no fixed fraction) | [9], [10] |

Hardware, workload, batching, topology, and adversarial assumption differ
between every pair of rows. The table cannot answer whether PBFT's thousands
of ops/s on a LAN reflects a family advantage or a more permissive harness. Nor
can it answer whether Avalanche's 1.35 s confirmation is structural or an
artifact of one `K, β` choice. The comparative question cannot even be posed in
a shared vocabulary, let alone answered.

### 2.3.2 The surveys measure nothing, and the one precedent targets PoW

Three taxonomic surveys place the families in qualitative terms — Bano *et al.*
[14] supply the canonical Systematization of Knowledge this chapter's taxonomy
reuses, Xiao *et al.* [15] aggregate reported throughput, latency, and
fault-tolerance ranges while flagging the cross-harness incomparability, and Cachin
and Vukolić [16] critique vendor-published permissioned-chain BFT numbers — but none
measures the families, and the two that aggregate numbers do so under the caveat that
the harnesses are not matched. The single quantitative precedent is Gervais *et al.*
[17], whose unified Proof-of-Work simulator — one metric schema, swept over block
size and propagation delay — is structurally the evaluation the BFT families have not
received; its limitation here is its target, Proof-of-Work. No equivalent
unified-harness study exists for PBFT-style, PoS-finality, and Avalanche-style
protocols evaluated jointly.

## 2.4 The gap

The three families respond to the same impossibility and differ only in which
assumption they relax, so they are commensurable as objects of comparison.
Their per-family measurements, however abundant, do not support cross-family
judgment. The obstacle is the reporting vocabulary itself, not any absence of
measurement. The one methodological precedent for a matched evaluation is
Gervais *et al.* [17], which has been applied to Proof-of-Work only. Chapter 3
responds with a unified discrete-event simulator, a shared metric schema
instantiated identically for the three families, and an experiment matrix that
sweeps the network-delay, Byzantine-fraction, validator-set-size, and
adversarial-strategy axes under common assumptions
[[wiki/concepts/research-questions]], [[wiki/concepts/experiment-matrix]].
