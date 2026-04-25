# Chapter 2 — Literature Review

## 2.1 Chapter roadmap

Chapter 1 introduced the four Layer-1 consensus families this thesis
evaluates and motivated, at the level of an executive argument, why a
unified comparative evaluation is missing from the literature. This chapter
develops that argument at literature-review depth and establishes the three
claims the rest of the thesis depends on:

- **C1.** Each of the four families is a principled relaxation of a
  shared foundational impossibility, not an arbitrary engineering choice
  [[wiki/concepts/consensus-families]].
- **C2.** Each family has been measured in its own vocabulary —
  operations per second and view-change rate for PBFT-style [4], [5];
  epoch-granularity time-to-finality for PoS-finality [7]; probabilistic
  safety `ε` for Avalanche-style [9]; WAN-scale ktps and commit latency
  for DAG-based [11]–[13] — so primary numbers do not cross family
  boundaries.
- **C3.** No published work evaluates all four BFT families in a single,
  controlled harness with a common metric schema; the only methodological
  precedent for that approach, Gervais *et al.* [17], applies it to
  Proof-of-Work rather than to BFT-style protocols.

Two scope notes pin the chapter. First, Proof-of-Work is treated only as a
methodological precedent through [17]; it is not a subject of comparison,
consistent with the scope statement in
[[wiki/concepts/problem-statement#scope]]. Second, the chapter surveys the
*literature* on each family at the level of mechanism, guarantees, and
documented weakness; the simulator-level mechanics of each protocol are
the subject of Chapter 3.

The remainder of the chapter is organised as follows. §2.2 frames the
consensus problem at the level of a replicated log and recalls the three
foundational impossibilities every family inherits. §2.3 shows how those
impossibilities carve out a four-region design space, summarised by
Figure 2.1. §2.4 surveys each region in turn, on a uniform skeleton, with
Table 2.1 as the cross-family scorecard. §2.5 turns to the existing
evaluations of those families and demonstrates, with Table 2.2, that the
reporting vocabulary itself is what blocks comparative judgement. §2.6
states the resulting unified-harness gap and forwards the reader into
Chapter 3.

## 2.2 Blockchains and the consensus problem

A Layer-1 blockchain is a replicated, append-only log of transactions
maintained by mutually distrusting validators
[[wiki/concepts/consensus-overview#what-a-blockchain-is]]. At each height,
honest validators must agree on a single block; the mechanism that
produces that agreement is the consensus protocol. Block agreement is, at
each height, an instance of the Byzantine Generals Problem [1]: a set of
processes, some of which may behave arbitrarily, must converge on a
single value despite contradictory messages. The classical
distributed-systems literature already supplies the bounds within which
any L1 protocol must operate.

Three foundational results define those bounds. Lamport, Shostak and Pease
[1] proved that a deterministic protocol can solve BGP if and only if at
least `3f+1` participants are present, where `f` is the number of
arbitrarily-faulty processes; the bound is the source of the recurring
two-thirds supermajority across the BFT literature
[[wiki/concepts/byzantine-generals]]. Fischer, Lynch and Paterson [2]
showed that, in a purely asynchronous network, no deterministic
protocol can guarantee both safety and liveness in the presence of even a
single crash-faulty process. The FLP impossibility is not specific to
malice; it is what forces every L1 protocol to relax some assumption
[[wiki/concepts/flp-impossibility]]. Dwork, Lynch and Stockmeyer [3]
provided the most influential of those relaxations: under
*partial synchrony* — message delays are bounded but the bound is not
known a priori — consensus is solvable for `f < n/3`
[[wiki/concepts/synchrony-models]].

These results jointly define the design space. Every L1 protocol concedes
on the synchrony axis (synchronous, partial-synchronous, asynchronous, or
probabilistic), the fault-model axis (crash, omission, Byzantine, with
stake-weighting where applicable [[wiki/concepts/fault-model]]), or both.
Across this concession space, the same `3f+1` quorum-intersection
arithmetic recurs whenever a family commits to deterministic safety
[[wiki/concepts/quorum-arithmetic]]. The CAP theorem, projected onto
blockchains, makes the operational consequence concrete: under partition,
a chain must choose Consistency (PBFT-style and PoS-finality halt safely)
or Availability (Avalanche-style continues with weakened guarantees);
partition-tolerance is non-negotiable
[[wiki/concepts/cap-theorem]]. The four properties consensus protocols are
expected to preserve — Agreement, Validity, Termination and Integrity
[[wiki/concepts/consensus-properties]] — sit on top of this concession
space and trade off against one another whenever the assumed model is
violated.

The literature does not contain a fifth foundational result that would
permit a free lunch; every L1 protocol begins by choosing which of these
constraints to relax. The next section maps how the four families chose.

## 2.3 The design space the impossibilities create

`3f+1` participants under partial synchrony is one habitable point in the
concession space, and the most direct one. PBFT [4] and its descendants
HotStuff [5] and Tendermint [6] occupy it. Three other habitable points
exist, and the four families evaluated in this thesis sit at the four
points respectively. Figure 2.1 redraws the propagation tree from
[[wiki/concepts/consensus-families#propagation-of-the-bft-problem]].

**Figure 2.1 — From the Byzantine Generals Problem to the four families.**

```
                   Byzantine Generals Problem
                   n >= 3f+1, safety + liveness
                              |
        +---------------+-----+----------+--------------------+
        |               |                |                    |
   Deterministic   Deterministic     Probabilistic      Decouple data-
   quorum-based    stake-weighted    random              availability
   partial sync    + economic        subsampling         from ordering
        |               |                |                    |
   PBFT family     PoS-finality      Avalanche family    DAG-based family
   (PBFT,          (Casper FFG,      (Slush -> Snowflake (Narwhal+Tusk,
   HotStuff,       Gasper)           -> Snowball ->      Bullshark,
   Tendermint)                        Avalanche)         Mysticeti)
       [4]–[6]         [7], [8]          [9], [10]         [11]–[13]
```

The three non-PBFT branches are best read as answers to the question
"what does the protocol do when partial synchrony's assumption is too
strong?". PoS-finality keeps `3f+1` and partial synchrony but adds an
*economic* layer — accountable safety via slashing — to convert the
Byzantine fault model from an exogenous assumption into a behaviourally
disincentivised one [7], [8]. Avalanche-style abandons quorums altogether
and replaces them with repeated random subsampling, accepting a non-zero
safety-violation probability `ε` in exchange for asynchrony tolerance and
per-validator cost independent of `n` [9], [10]. DAG-based protocols keep
`3f+1` but separate the two responsibilities consensus historically bundles
— data availability and ordering — sending the first to a DAG mempool and
the second to a thin commit rule that derives total order from the DAG with
zero extra messages in the common case [11]–[13].

Each branch's choice is what determines the metric vocabulary in which it
later reports its performance. §2.4 examines each branch in turn, on the
uniform skeleton previewed in Table 2.1.

## 2.4 The four families

**Table 2.1 — Four-family design space.** Adapted from
[[wiki/concepts/consensus-families#comparison-table]]. The four columns
are read horizontally as the lens applied to each family in §2.4.1–§2.4.4.

| Family | Synchrony | Finality | Fault threshold | Primary cost concession |
| :---- | :---- | :---- | :---- | :---- |
| **PBFT-style** | Partial | Deterministic, single-slot | `f < n/3` | `O(n²)` per-block messages; view-change cost on leader failure |
| **PoS-finality** | Partial | Deterministic, checkpoint-based | `f < n/3` by stake | Latency to finality spans multiple epochs; complex slashing logic |
| **Avalanche-style** | Asynchronous / probabilistic | Probabilistic `(1 − ε)` | `f < n/5` (parameter-dependent) | No hard finality; parameter tuning required |
| **DAG-based** | Asynchronous | Deterministic, induced by DAG order | `f < n/3` | Higher per-node storage and bandwidth; deeper pipeline before order is fixed |

Each subsection follows the same four-paragraph structure: mechanism,
guarantees and their assumption, the documented adversarial weakness in
the Chapter 1 §1.4 taxonomy (silent non-participation, delayed voting,
equivocation, selective dropping), and a one-sentence note on which RQ
the simulator stresses with this family.

### 2.4.1 PBFT-style

*Mechanism.* PBFT [4] is a leader-driven, three-phase commit protocol
operating on a partially-synchronous network of `3f+1` replicas: the
designated leader broadcasts a *pre-prepare*, replicas reply with
*prepare* upon validation, and after a `2f+1` prepare-quorum has been
collected each replica broadcasts *commit*; a `2f+1` commit-quorum
finalises the block [[wiki/algorithms/pbft]]. HotStuff [5] linearises the
view-change path to `O(n)` via threshold signatures and pipelines the
phases; Tendermint [6] adopts round-robin leader rotation with a locking
rule that simplifies the proof of safety.

*Guarantees and assumption.* Single-slot deterministic finality and
`f < n/3` safety hold under the partial-synchrony assumption [3]; once a
block has accumulated `2f+1` commit messages, it cannot be reverted by
any combination of `f` faults. Liveness is restored after the Global
Stabilisation Time via view change.

*Documented adversarial weakness.* The protocol's most-studied weakness
under the §1.4 adversary taxonomy is **leader-targeted delayed voting**:
a Byzantine leader, or a delaying coalition that includes the leader,
forces successive view changes whose `O(n³)` cost in the original PBFT
formulation [4] degrades latency well before any safety threshold is
approached.

*Simulator role.* The PBFT-family module exists primarily to stress
RQ1 (commit latency under delay) and RQ3 (the `O(n²)` scaling exponent),
and to provide the deterministic-finality reference point against which
Avalanche's probabilistic finality is measured.

### 2.4.2 PoS-finality

*Mechanism.* The PoS-finality family overlays a BFT finality gadget on a
conventional fork-choice-based blockchain. Casper FFG [7] runs a two-round
voting protocol on epoch-boundary checkpoints: a checkpoint is
*justified* by a `2f+1`-by-stake supermajority, and a checkpoint
*finalised* once it and its successor are both justified
[[wiki/algorithms/pos]]. Gasper [8] composes Casper FFG with the
LMD-GHOST fork-choice rule and supplies the deployed Ethereum
specification.

*Guarantees and assumption.* Deterministic checkpoint-finality holds
under `f < 1/3` of total stake, again under partial synchrony [3], [7].
The distinguishing addition is *accountable safety*: any pair of
contradictory votes by the same validator produces cryptographic evidence
sufficient to slash that validator's stake — the Byzantine fault model
is converted into an economically disincentivised one rather than left
exogenous.

*Documented adversarial weakness.* The most-studied weakness under the
§1.4 taxonomy is **equivocation**, both because it is the behaviour
slashing exists to deter and because the FFG safety proof depends on the
slashing condition being credibly enforced [7], [8]. Inactivity-leak
behaviour under prolonged silent non-participation is a secondary
concern: after a finality drought, the protocol gradually leaks the
stake of non-participating validators to restore a `2f+1` quorum, at the
cost of widening the time-to-finality window.

*Simulator role.* The PoS-finality module stresses RQ4 (safety vs
liveness under equivocation and silent non-participation) and contributes
the *epoch-granularity* time-to-finality measurement to the unified
schema.

### 2.4.3 Avalanche-style

*Mechanism.* Avalanche [9] is the leaderless, quorum-free family. Each
validator queries `K` randomly-sampled peers per round and adopts the
super-majority answer when at least `α · K` of the responses agree;
confidence accumulates over `β` consecutive rounds of sample agreement,
at which point the value is committed [[wiki/algorithms/avalanche]]. The
four-stage cascade Slush → Snowflake → Snowball → Avalanche layers
metastability resistance, persistence, and DAG operation onto the basic
sampling primitive.

*Guarantees and assumption.* Safety is *probabilistic*: the
safety-violation probability is bounded by
`ε < (1 − α_c/K)^β` and decays exponentially in the confidence parameter
`β` [9]. Liveness holds asynchronously under the assumption of a
non-adaptive Byzantine fraction below the parameter-dependent threshold
(typically `f < n/5` for the parameter sets reported in [9]). Per-validator
message cost is `O(K · β)` and is independent of `n` — a structural
asymmetry with the three quorum-based families.

*Documented adversarial weakness.* The most-studied weakness under the
§1.4 taxonomy is **selective message dropping** combined with delayed
voting, the regime in which Amores-Sesar, Cachin and Schneider's
re-analysis [10] tightens [9]'s informal liveness claims and identifies
configurations under which sampling rounds fail to converge faster than
[9] predicts.

*Simulator role.* The Avalanche-family module stresses RQ3 (the
`n`-independent message cost), RQ4 (probabilistic safety under adversarial
sampling), and supplies the only non-deterministic finality metric in the
unified schema.

### 2.4.4 DAG-based

*Mechanism.* Narwhal [11] separates the two duties classical consensus
bundles — data availability and ordering — by running a reliable-broadcast
DAG mempool that records the causal dependencies of every transaction
batch. Tusk [11] derives a total order from the DAG with zero additional
messages in the common case; Bullshark [12] simplifies Tusk and adds a
two-round partial-sync fast path; Mysticeti [13] removes block
certification and reaches the three-round BFT latency lower bound
[[wiki/algorithms/dag-based]].

*Guarantees and assumption.* The BFT kernel remains deterministic with
`f < n/3` safety, but the network model is asynchronous: reliable
broadcast in the DAG mempool absorbs adversarial timing without driving
view changes [11], [12]. Per-block message complexity is `O(n)`, with
per-validator storage and bandwidth as the cost concession (the DAG must
be retained until ordering passes through it).

*Documented adversarial weakness.* The most-studied weakness under the
§1.4 taxonomy is **selective dropping by a Byzantine sender attempting
to withhold a block from a subset of receivers**, the case the
reliable-broadcast layer is explicitly designed to defeat [11], [13]. The
worst-case scenario for the family is sustained packet loss combined
with adversarial mempool inputs that force longer DAG retention windows.

*Simulator role.* The DAG-based module stresses RQ3 (the `O(n)` scaling
exponent), RQ4 (reliable broadcast under packet loss), and contributes
the WAN-scale throughput baseline against which the PBFT-style and
PoS-finality modules are compared.

## 2.5 Existing comparative evaluations

The four families have all been measured in the primary literature, and
the field has produced three taxonomic surveys plus one quantitative
methodological precedent. Yet none of these efforts produces a
cross-family comparison under matched conditions. Two distinct subproblems
explain why.

### 2.5.1 Per-family evaluations and their vocabularies

Each family's primary papers report what its design concedes — and
nothing else. The PBFT and HotStuff papers report operations per second
on a low-latency LAN harness and view-change cost as the principal
disturbance metric [4], [5]. Casper FFG reports time-to-finality in
*epochs* — a unit that makes physical sense only after multiplication by
the underlying chain's slot time [7], [8]. Avalanche reports two numbers
not seen in the other families at all: the probabilistic safety
violation `ε` and the per-transaction confirmation latency under a
specific `K, α, β` parameterisation [9], [10]. The DAG-based papers
report kilo-transactions-per-second at WAN scale and three-round commit
latency [11]–[13]. Table 2.2 collects the headline numbers.

**Table 2.2 — Reported metric vocabulary across families.** Adapted from
[[wiki/concepts/evaluation-metrics#reported-ranges-in-the-literature]].
Columns are not directly comparable; this is precisely the obstacle.

| Family | Throughput (reported) | Latency (reported) | Fault threshold | Source |
| :---- | :---- | :---- | :---- | :---- |
| PBFT (LAN) | Thousands of ops/s | Sub-10 ms | `< n/3` | [4] |
| HotStuff | Linear in `n` after optimisations | 3-round commit | `< n/3` | [5] |
| PoS-finality (Casper FFG / Gasper) | Block-proposal rate of underlying chain | Two-epoch finality (≤12.8 min on Ethereum) | `< 1/3` of stake | [7], [8] |
| Avalanche | ~3.4 ktps (testnet) | ~1.35 s | Parameter-dependent, ~`< n/5` | [9], [10] |
| Narwhal + Tusk | ~140 ktps (WAN) | ~2–3 s | `< n/3` | [11] |
| Bullshark | ~125 ktps | 2-round fast path under synchrony | `< n/3` | [12] |
| Mysticeti | >200 ktps | ~0.5 s commit (WAN) | `< n/3` | [13] |

The hardware, workload, batching strategy, network topology and
adversarial assumption differ between every pair of rows. A reader
cannot infer from Table 2.2 whether Mysticeti's >200 ktps reflects an
intrinsic family advantage or a more permissive harness; nor whether
Avalanche's 1.35 s confirmation is a structural cost of probabilistic
finality or an artefact of a particular `K, β` choice. The vocabulary
fragmentation makes the question itself difficult to phrase.

### 2.5.2 Surveys, critiques, and the one methodological precedent

Three taxonomic surveys position the families qualitatively but do not
add measurements. Bano *et al.* [14] supply the canonical Systematisation
of Knowledge and the taxonomic backbone for
[[wiki/concepts/consensus-families]]; Xiao *et al.* [15] aggregate
reported throughput, latency and fault-tolerance ranges across families
but explicitly flag the cross-harness incomparability problem; Cachin and
Vukolić [16] supply a methodological critique of permissioned-chain BFT
that motivates formal models and public review while questioning the
robustness of vendor-published numbers. None of the three measures the
families itself, and the two that aggregate numbers ([15] explicitly,
[14] implicitly) do so under the caveat that the underlying harnesses are
not matched.

The one quantitative methodological precedent is Gervais *et al.* [17].
Their unified PoW simulator — instrumented with a single metric schema,
swept over block size and propagation delay, and applied uniformly to
the protocols compared — is structurally the kind of evaluation the BFT
families have not received. Its limitation, for the present thesis, is
the protocol family it targets: PoW, not the four BFT families. No
equivalent unified-harness study exists for PBFT-style, PoS-finality,
Avalanche-style and DAG-based protocols evaluated jointly. This is the
gap claim **C3** identifies, now established at literature-review
depth.

## 2.6 The unified-harness gap and the methodology it calls for

Claims C1, C2 and C3 jointly position the thesis. C1 establishes that the
four families are commensurable as objects of comparison: they answer the
same impossibility, differ only in which assumption they relax, and share
the underlying `3f+1` arithmetic wherever they retain deterministic
safety. C2 establishes that the existing per-family numbers, although
plentiful, do not support cross-family judgement under matched
conditions; the obstacle is the reporting vocabulary, not the absence of
measurement. C3 establishes that the one methodological precedent for
the kind of evaluation the field needs — Gervais *et al.* [17] — has been
applied to PoW only, and that the analogous study for the BFT families
has not been done.

Chapter 3 responds to that gap with a unified discrete-event simulator,
a shared metric schema instantiated identically for the four families
(latency, throughput, overhead, reliability)
[[wiki/concepts/evaluation-metrics]], and an experimental matrix that
sweeps the network-delay axis (RQ1), the validator-set-size axis (RQ3),
the Byzantine-fraction axis (RQ2), and the adversarial-strategy axis
(RQ4) under common assumptions
[[wiki/concepts/research-questions]]. Chapter 4 reports the resulting
data and answers RQ1–RQ4. Chapter 5 supplies the cross-family Pareto
synthesis demanded by RQ5. Chapter 6 concludes.
