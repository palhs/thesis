# Chapter 2 — Literature Review

## 2.1 Blockchains and the consensus problem

A Layer-1 blockchain commits one block per height across a set of mutually
distrusting validators; producing that agreement despite validators that may
behave arbitrarily is the Byzantine Generals Problem [1]
[[wiki/concepts/byzantine-generals]]. Chapter 1 fixed the three results that
bound any solution — the `3f+1` Byzantine threshold [1], the FLP impossibility
[2], and the partial-synchrony relaxation that makes consensus solvable for
`f < n/3` [3] [[wiki/concepts/synchrony-models]]. What they jointly produce is
not a single protocol but a design space of concessions. Every Layer-1
protocol concedes along the synchrony axis, the fault-model axis, or both.
The synchrony axis runs from synchronous through partial-synchronous and
asynchronous to probabilistic. The fault-model axis runs from crash through
omission to Byzantine, with stake-weighting where applicable
[[wiki/concepts/fault-model]]. Wherever a family preserves deterministic
safety, the `3f+1` quorum-intersection arithmetic recurs
[[wiki/concepts/quorum-arithmetic]].

The CAP theorem [18] makes the operational consequence concrete. Under
partition a chain must choose Consistency or Availability, with
partition-tolerance non-negotiable: PBFT-style and PoS-finality halt safely
to keep Consistency, while Avalanche-style continues with weakened guarantees
to keep Availability [[wiki/concepts/cap-theorem]].

## 2.2 The fork in the road

No foundational result permits a free lunch: every protocol begins by
choosing which constraint to relax. PBFT [4] and its descendants HotStuff
[5] and Tendermint [6] take the most direct point — a `3f+1` quorum under
partial synchrony. The other two families are best read as answers to a
single question — once PBFT's point is fixed, which assumption to loosen
next. Figure 2.1 traces the propagation from the Byzantine Generals Problem
to the three families.

**Figure 2.1 ([[diagrams/concepts/bft-families-tree]]).** From the Byzantine
Generals Problem to the three families.

- **PoS-finality** keeps the `3f+1` quorum and partial synchrony but adds an
  *economic* layer: a validator that equivocates can be slashed, converting
  the Byzantine fault model from an external assumption into a
  disincentivized behavior [7], [8].
- **Avalanche-style** abandons the quorum entirely, replacing it with
  repeated random sampling and accepting a non-zero safety-violation
  probability `ε` in exchange for asynchrony tolerance and per-validator cost
  independent of `n` [9], [10].

The choice each family makes determines the vocabulary in which it later
reports performance (§2.4).

## 2.3 The three families

Table 2.1 traces the same event — committing one proposed block — through
all three families. They do one thing in common: accumulate *agreement* on a
block until reversal is impossible. They differ on three axes: what counts
as agreement, how much is enough, and how many times that must happen. Across
those three axes the two deterministic families are nearly identical: about
two-thirds agreement, met twice, giving `ε = 0`. Avalanche-style breaks the
pattern: about 80% of a small random sample, repeated `β` times, giving a small
positive `ε`.

**Table 2.1 — How one block becomes irreversible.** Protocol-native terms
are in parentheses. Notation is defined below the table; per-family
citations appear in §2.3.

| | PBFT-style | PoS-finality | Avalanche-style |
|:--|:--|:--|:--|
| Synchrony assumption | partial synchrony | partial synchrony | asynchronous / probabilistic |
| Block proposer | one rotating leader (primary) | one leader per slot (stake-weighted) | one leader per slot (round-robin) |
| Unit of agreement | a replica's vote (`PREPARE`/`COMMIT`) | an attestation, weighted by stake | a polled peer's preference (`QUERY-RESPONSE`) |
| Agreement threshold | ~⅔ of all validators (`2f+1`) | ~⅔ of all stake | ~80% of a small random sample (`α_c` of `K`) |
| Agreement rounds | twice (`prepare`, `commit`) | twice, ≥2 epochs apart (`justify`, `finalize`) | `β`≈15 sampling rounds in a row |
| Finality guarantee | deterministic, `ε = 0` | deterministic, `ε = 0` | probabilistic, `ε ≤ (1−α_c/K)^β` |
| Communication cost | `O(n²)` | `O(n)`, BLS-aggregated to ~1 | `O(K·β)`, independent of `n` |
| Adversarial pressure point | stall the leader (liveness); safety holds `<n/3` | stall finality; breaking safety burns ≥⅓ stake | stall the counter (liveness); safety statistical |

**Notation.**

| Symbol | Meaning | Relationships |
|:--|:--|:--|
| `n`, `f` | validators; maximum Byzantine | `n = 3f+1` for the quorum-based families |
| `K` | peers polled per round (Snowman) | `K ≈ 20`, or `min(20, n−1)` at thesis scale |
| `α_c` | sampled peers that must agree to count a round | `α_c ≈ 0.8K`; holding `α_c/K ≈ 0.8` fixes the safety-curve shape |
| `β` | consecutive agreeing rounds before a block is accepted | `β ≈ 15`; holding `β` fixed makes `ε` invariant in `n` |
| `ε` | probability two honest validators commit conflicting blocks | `0` for the two deterministic families; `≤ (1−α_c/K)^β` for Snowman |

*At `n = 7`:* the two deterministic families lock a block with a ~5-of-7
agreement (or ⅔ of stake), met twice. Snowman instead needs ~5-of-6 polled
peers to agree 15 rounds running — reaching `ε ≈ 10⁻¹²` by repetition, not by
one counted quorum.

Table 2.1 fixes how the three differ in operation. What the literature adds,
and the table cannot carry, is the documented variants of each family and the
adversarial weakness documented for it within the §1.4 taxonomy (silent
non-participation, delayed voting, equivocation). The simulator-level
treatment of each protocol is deferred to Chapter 3.

**PBFT-style.** The documented weakness is a *delayed-voting* adversary in the
§1.4 sense, and it is leader-targeted. A Byzantine or delaying leader triggers
successive view changes whose `O(n³)` cost in the original formulation [4]
degrades latency well before any safety threshold is approached. Safety stays
unconditional below `f < n/3` — an equivocating leader is caught at the prepare
round, where no two-thirds agreement forms for either value
[[wiki/algorithms/pbft#safety-argument]].

**PoS-finality.** Casper FFG, the finality gadget of the deployed Ethereum
specification [8], has accountable safety as its signature property: two
conflicting finalized checkpoints imply that at least one-third of stake signed
a slashable message, making a violation attributable, not merely infeasible
[7]. The most-studied weakness is *equivocation*. Slashing exists to deter it, and
the safety proof depends on that slashing being credibly enforced [7], [8]. The
secondary weakness is *silent non-participation*, which, if prolonged, leaks
absent validators' stake to restore a quorum while the time-to-finality window
widens [[wiki/algorithms/pos#behaviour-under-adversarial-conditions]].

**Avalanche-style.** The production form is Snowman, the linearized Avalanche
variant [9]. The family has no fixed `f < n/3` threshold: the tolerated
Byzantine fraction is set by the parameter choice. Its per-validator cost
`O(K·β)` is independent of `n`. The documented weakness is *equivocation*.
Amores-Sesar, Cachin and Schneider [10] show that an adversary influencing as
few as two undecided validators can stall the confidence counter beyond any
number of rounds polynomial in `β`, a far worse cost than the original analysis
[9] implies. The same work confirms fast convergence absent such an adversary
and proposes a fix.

## 2.4 Why the published numbers do not compare

The three families have all been measured, and the field has produced three
taxonomic surveys plus one quantitative methodological precedent. None yields
a cross-family comparison under matched conditions, for two distinct reasons.

### 2.4.1 Each family reports in its own vocabulary

Each family's primary papers report what its design concedes, and little
else. The PBFT and HotStuff papers report operations per second on a
low-latency LAN with view-change cost as the disturbance metric [4], [5].
Casper FFG reports time-to-finality in *epochs*, a unit that becomes physical
only after multiplication by a slot duration [7], [8]. Avalanche reports two
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
artifact of one `K, β` choice. The comparative question is hard to phrase before
it is hard to answer.

### 2.4.2 The surveys measure nothing, and the one precedent targets PoW

Three taxonomic surveys place the families in qualitative terms. Bano *et al.*
[14] supply the canonical Systematization of Knowledge and the taxonomic
backbone this chapter reuses. Xiao *et al.* [15] aggregate reported
throughput, latency, and fault-tolerance ranges across families while
flagging the cross-harness incomparability. Cachin and Vukolić [16] supply a
methodological critique of permissioned-chain BFT that questions the
robustness of vendor-published numbers. None measures the families; the two
that aggregate numbers do so under the caveat that the harnesses are not
matched.

The single quantitative precedent is Gervais *et al.* [17]. Their unified
Proof-of-Work simulator — one metric schema, swept over block size and
propagation delay, applied uniformly to the protocols compared — is
structurally the evaluation the BFT families have not received. Its
limitation, for this thesis, is its target: Proof-of-Work, not the three BFT
families. No equivalent unified-harness study exists for PBFT-style,
PoS-finality, and Avalanche-style protocols evaluated jointly.

## 2.5 The gap

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
