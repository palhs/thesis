# Chapter 2 — Literature Review

## 2.1 Chapter roadmap

Chapter 1 introduced the four Layer-1 consensus families this thesis
evaluates and motivated, at an executive level, the absence of a unified
comparative evaluation from the existing literature. The present chapter
develops that motivation at literature-review depth, supporting three
claims on which the remainder of the thesis depends:

- **C1.** Each of the four families is a principled relaxation of a shared
  foundational impossibility rather than an arbitrary engineering choice
  [[wiki/concepts/consensus-families]].
- **C2.** Each family has been measured in a vocabulary specific to its
  own design — operations per second and view-change rate for PBFT-style
  [4], [5]; epoch-granularity time-to-finality for PoS-finality [7], [8];
  probabilistic safety `ε` for Avalanche-style [9]; WAN-scale ktps and
  commit latency for DAG-based [11]–[13] — so the primary numbers do not
  cross family boundaries.
- **C3.** No published work evaluates all four BFT families in a single,
  controlled harness with a common metric schema; the only methodological
  precedent for that approach, Gervais *et al.* [17], applies it to
  Proof-of-Work rather than to BFT-style protocols.

Two scope notes pin the chapter. First, Proof-of-Work appears as a
methodological precedent through [17] only; it is not a subject of
comparison, consistent with the scope contract in
[[wiki/concepts/problem-statement#scope]]. Second, the chapter surveys the
*literature* on each family at the level of mechanism, guarantees, and
documented adversarial weakness; the simulator-level mechanics of each
protocol are the concern of Chapter 3.

The remainder of the chapter is organized as follows. §2.2 frames the
consensus problem at the level of a replicated log and recalls the three
foundational impossibilities every family inherits. §2.3 maps how those
impossibilities carve out a four-region design space, summarized by
Figure 2.1. §2.4 surveys each region in turn on a uniform skeleton, with
Table 2.1 as the cross-family scorecard. §2.5 turns to the existing
evaluations of those families and demonstrates, with Table 2.2, that the
reporting vocabulary itself blocks comparative judgment. §2.6 states the
resulting unified-harness gap and forwards the reader into Chapter 3.

## 2.2 Blockchains and the consensus problem

A Layer-1 blockchain is a replicated, append-only log of transactions
maintained by mutually distrusting validators
[[wiki/concepts/consensus-overview#what-a-blockchain-is]]. At each height
every honest validator must commit the same block; the mechanism producing
that agreement is the consensus protocol. Block agreement is, at each
height, an instance of the Byzantine Generals Problem [1]: a set of
processes, some of which may behave arbitrarily, must converge on a single
value despite contradictory messages. The classical distributed-systems
literature already supplies the bounds within which any Layer-1 protocol
must operate.

Three foundational results define those bounds. Lamport, Shostak and Pease
[1] proved that a deterministic solution to the Byzantine Generals Problem
requires at least `3f+1` participants, where `f` is the number of
arbitrarily-faulty processes; this bound is the origin of the two-thirds
supermajority recurring throughout the BFT literature
[[wiki/concepts/byzantine-generals]]. Fischer, Lynch and Paterson [2]
showed that, in a purely asynchronous network, no deterministic protocol
can guarantee both safety and liveness in the presence of even a single
crash-faulty process. The FLP impossibility is not specific to malice; it
is what forces every Layer-1 protocol to relax some assumption
[[wiki/concepts/flp-impossibility]]. Dwork, Lynch and Stockmeyer [3]
supply the most influential of those relaxations: under *partial
synchrony* — message delays are bounded but the bound is not known a
priori — consensus is solvable for `f < n/3`
[[wiki/concepts/synchrony-models]].

These results jointly define the design space. Every Layer-1 protocol
concedes along the synchrony axis (synchronous, partial-synchronous,
asynchronous, or probabilistic), the fault-model axis (crash, omission,
Byzantine, with stake-weighting where applicable
[[wiki/concepts/fault-model]]), or both. Across the concession space, the
`3f+1` quorum-intersection arithmetic recurs wherever a family preserves
deterministic safety [[wiki/concepts/quorum-arithmetic]]. The CAP theorem
[18], projected onto blockchains, renders the operational consequence
concrete: under partition, a chain must choose Consistency (PBFT-style and
PoS-finality halt safely) or Availability (Avalanche-style continues with
weakened guarantees); partition-tolerance is non-negotiable
[[wiki/concepts/cap-theorem]]. The four properties expected of a consensus
protocol — Agreement, Validity, Termination, and Integrity
[[wiki/concepts/consensus-properties]] — sit on top of the concession space
and trade off against one another whenever the assumed model is violated.

No fifth foundational result permits a free lunch; every Layer-1 protocol
begins by choosing which of the existing constraints to relax. The next
section maps how the four families chose.

## 2.3 The design space the impossibilities create

A `3f+1` quorum under partial synchrony is one habitable point in the
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

The three non-PBFT branches are best read as answers to the question of
what to relax when partial synchrony's assumption is too strong.
PoS-finality retains `3f+1` and partial synchrony but adds an *economic*
layer — accountable safety via slashing — converting the Byzantine fault
model from an exogenous assumption into a behaviorally disincentivized one
[7], [8]. Avalanche-style abandons quorums altogether and replaces them
with repeated random subsampling, accepting a non-zero safety-violation
probability `ε` in exchange for asynchrony tolerance and per-validator
cost independent of `n` [9], [10]. DAG-based protocols retain `3f+1` but
separate the two responsibilities classical consensus bundles — data
availability and ordering — routing the first to a DAG mempool and the
second to a thin commit rule that derives total order from the DAG with
zero additional messages in the common case [11]–[13].

The choice each branch makes determines the metric vocabulary in which it
later reports its performance. §2.4 examines each branch in turn, on the
uniform skeleton previewed in Table 2.1.

## 2.4 The four families

**Table 2.1 — Four-family design space.** Adapted from
[[wiki/concepts/consensus-families#comparison-table]]. Each row is read as
the lens applied to that family in §2.4.1–§2.4.4.

| Family | Synchrony | Finality | Fault threshold | Primary cost concession |
| :---- | :---- | :---- | :---- | :---- |
| **PBFT-style** | Partial | Deterministic, single-slot | `f < n/3` | `O(n²)` per-block messages; view-change cost on leader failure |
| **PoS-finality** | Partial | Deterministic, checkpoint-based | `f < n/3` by stake | Time-to-finality spans multiple epochs; slashing-logic complexity |
| **Avalanche-style** | Asynchronous / probabilistic | Probabilistic `(1 − ε)` | `f < n/5` (parameter-dependent) | No deterministic finality; parameter tuning required |
| **DAG-based** | Asynchronous | Deterministic, induced by DAG order | `f < n/3` | Higher per-node storage and bandwidth; deeper pipeline before order is fixed |

Each subsection follows the same four-paragraph structure: mechanism,
guarantees and their assumption, the documented adversarial weakness
within the §1.4 adversary taxonomy (silent non-participation, delayed
voting, equivocation, selective dropping), and the role the family plays
in the simulator.

### 2.4.1 PBFT-style

*Mechanism.* PBFT [4] is a leader-driven, three-phase commit protocol
operating on a partially-synchronous network of `3f+1` replicas: the
designated leader broadcasts a *pre-prepare*; replicas reply with
*prepare* upon validation; once a replica has collected a `2f+1`
prepare-quorum, it broadcasts *commit*; the accumulation of a `2f+1`
commit-quorum finalizes the block [[wiki/algorithms/pbft]]. HotStuff [5]
linearizes the view-change path to `O(n)` via threshold signatures and
pipelines the phases; Tendermint [6] adopts round-robin leader rotation
with a locking rule that simplifies the safety proof.

*Guarantees and assumption.* Single-slot deterministic finality and
`f < n/3` safety hold under the partial-synchrony assumption [3]; once a
block accumulates `2f+1` commit messages it cannot be reverted by any
combination of `f` faults. Liveness is recovered after the Global
Stabilization Time via view change.

*Documented adversarial weakness.* The most-studied weakness within the
§1.4 taxonomy is **leader-targeted delayed voting**: a Byzantine leader,
or a delaying coalition that includes the leader, induces successive view
changes whose `O(n³)` cost in the original formulation [4] degrades
latency well before any safety threshold is approached.

*Simulator role.* The PBFT-family module exists primarily to stress RQ1
(commit latency under delay) and RQ3 (the `O(n²)` scaling exponent), and
to supply the deterministic-finality reference point against which
Avalanche-style probabilistic finality is measured.

### 2.4.2 PoS-finality

*Mechanism.* The PoS-finality family overlays a BFT finality gadget on a
conventional fork-choice-based blockchain. Casper FFG [7] runs a two-round
voting protocol on epoch-boundary checkpoints: a checkpoint is *justified*
once a `2f+1`-by-stake supermajority votes for it, and is *finalized* once
it and its successor are both justified [[wiki/algorithms/pos]]. Gasper
[8] composes Casper FFG with the LMD-GHOST fork-choice rule and
constitutes the deployed Ethereum PoS specification.

*Guarantees and assumption.* Deterministic checkpoint finality holds under
`f < 1/3` of total stake, again under partial synchrony [3], [7]. The
distinguishing addition is *accountable safety*: a pair of contradictory
votes by the same validator yields cryptographic evidence sufficient to
slash that validator's stake, converting the Byzantine fault model into an
economically disincentivized one rather than leaving it exogenous.

*Documented adversarial weakness.* The most-studied weakness within the
§1.4 taxonomy is **equivocation**, both because slashing exists to deter
it and because the FFG safety proof depends on the slashing condition
being credibly enforced [7], [8]. The inactivity-leak behavior under
prolonged silent non-participation is a secondary concern: after a
finality drought, the protocol gradually leaks the stake of
non-participating validators to restore a `2f+1` quorum, at the cost of a
widened time-to-finality window.

*Simulator role.* The PoS-finality module stresses RQ4 (safety against
liveness under equivocation and silent non-participation) and contributes
the *epoch-granularity* time-to-finality measurement to the unified
schema.

### 2.4.3 Avalanche-style

*Mechanism.* Avalanche [9] is the leaderless, quorum-free family. Each
validator queries `K` randomly-sampled peers per round and adopts the
super-majority answer when at least `α · K` of the responses agree;
confidence accumulates over `β` consecutive rounds of sample agreement, at
which point the value is committed [[wiki/algorithms/avalanche]]. The
four-stage cascade Slush → Snowflake → Snowball → Avalanche layers
metastability resistance, persistence, and DAG operation onto the basic
sampling primitive.

*Guarantees and assumption.* Safety is *probabilistic*: the
safety-violation probability is bounded by `ε < (1 − α_c/K)^β` and decays
exponentially in the confidence parameter `β` [9]. Liveness holds
asynchronously under the assumption of a non-adaptive Byzantine fraction
below the parameter-dependent threshold (typically `f < n/5` for the
parameter sets reported in [9]). Per-validator message cost is `O(K · β)`
and independent of `n` — a structural asymmetry with respect to the three
quorum-based families.

*Documented adversarial weakness.* The most-studied weakness within the
§1.4 taxonomy is **selective message dropping in combination with delayed
voting**, the regime in which the formal re-analysis of Amores-Sesar,
Cachin and Schneider [10] tightens the informal liveness claims of [9] and
identifies configurations under which sampling rounds fail to converge as
quickly as [9] predicts.

*Simulator role.* The Avalanche-family module stresses RQ3 (the
`n`-independent message cost) and RQ4 (probabilistic safety under
adversarial sampling), and supplies the only non-deterministic finality
metric in the unified schema.

### 2.4.4 DAG-based

*Mechanism.* Narwhal [11] separates the two duties classical consensus
bundles — data availability and ordering — by running a reliable-broadcast
DAG mempool that records the causal dependencies of every transaction
batch. Tusk [11] derives a total order from the DAG with zero additional
messages in the common case; Bullshark [12] simplifies Tusk and adds a
two-round partial-synchrony fast path; Mysticeti [13] removes block
certification and reaches the three-round BFT latency lower bound
[[wiki/algorithms/dag-based]].

*Guarantees and assumption.* The BFT kernel remains deterministic with
`f < n/3` safety, but the network model is asynchronous: reliable
broadcast in the DAG mempool absorbs adversarial timing without driving
view changes [11], [12]. Per-block message complexity is `O(n)`, with
per-validator storage and bandwidth as the cost concession (the DAG must
be retained until ordering passes through it).

*Documented adversarial weakness.* The most-studied weakness within the
§1.4 taxonomy is **selective dropping by a Byzantine sender attempting to
withhold a block from a subset of receivers**, the case the
reliable-broadcast layer is explicitly designed to defeat [11], [13]. The
worst-case condition for the family combines sustained packet loss with
adversarial mempool inputs that force longer DAG retention windows.

*Simulator role.* The DAG-based module stresses RQ3 (the `O(n)` scaling
exponent) and RQ4 (reliable broadcast under packet loss), and contributes
the WAN-scale throughput baseline against which the PBFT-style and
PoS-finality modules are compared.

## 2.5 Existing comparative evaluations

The four families have all been measured in the primary literature, and
the field has produced three taxonomic surveys together with one
quantitative methodological precedent. None of these efforts, however,
yields a cross-family comparison under matched conditions. Two distinct
subproblems explain the absence.

### 2.5.1 Per-family evaluations and their vocabularies

Each family's primary papers report what that family's design concedes —
and little else. The PBFT and HotStuff papers report operations per second
on a low-latency LAN harness with view-change cost as the principal
disturbance metric [4], [5]. Casper FFG reports time-to-finality in
*epochs* — a unit that becomes physical only after multiplication by the
underlying chain's slot duration [7], [8]. Avalanche reports two figures
absent from the other families: the probabilistic safety-violation `ε` and
a per-transaction confirmation latency under a specific `K, α, β`
parameterization [9], [10]. The DAG-based papers report
kilo-transactions-per-second at WAN scale together with a three-round
commit latency [11]–[13]. Table 2.2 collects the headline numbers.

**Table 2.2 — Reported metric vocabulary across families.** Adapted from
[[wiki/concepts/evaluation-metrics#reported-ranges-in-the-literature]].
The columns are not directly comparable; this incomparability is precisely
the obstacle.

| Family | Throughput (reported) | Latency (reported) | Fault threshold | Source |
| :---- | :---- | :---- | :---- | :---- |
| PBFT (LAN) | Thousands of ops/s | Sub-10 ms | `< n/3` | [4] |
| HotStuff | Linear in `n` after optimizations | 3-round commit | `< n/3` | [5] |
| PoS-finality (Casper FFG / Gasper) | Block-proposal rate of underlying chain | Two-epoch finality (≤12.8 min on Ethereum) | `< 1/3` of stake | [7], [8] |
| Avalanche | ~3.4 ktps (testnet) | ~1.35 s | Parameter-dependent, ~`< n/5` | [9], [10] |
| Narwhal + Tusk | ~140 ktps (WAN) | ~2–3 s | `< n/3` | [11] |
| Bullshark | ~125 ktps | 2-round fast path under synchrony | `< n/3` | [12] |
| Mysticeti | >200 ktps | ~0.5 s commit (WAN) | `< n/3` | [13] |

Hardware, workload, batching strategy, network topology, and adversarial
assumption differ between every pair of rows. A reader cannot infer from
Table 2.2 whether Mysticeti's >200 ktps reflects an intrinsic family
advantage or a more permissive harness; nor whether Avalanche's 1.35 s
confirmation is a structural cost of probabilistic finality or an artifact
of a particular `K, β` choice. The vocabulary fragmentation makes the
comparative question difficult to phrase even before it is difficult to
answer.

### 2.5.2 Surveys, critiques, and the methodological precedent

Three taxonomic surveys position the families qualitatively without
contributing measurements of their own. Bano *et al.* [14] supply the
canonical Systematization of Knowledge and the taxonomic backbone reused
by [[wiki/concepts/consensus-families]]. Xiao *et al.* [15] aggregate
reported throughput, latency, and fault-tolerance ranges across families
while explicitly flagging the cross-harness incomparability problem.
Cachin and Vukolić [16] supply a methodological critique of
permissioned-chain BFT that motivates formal models and public review and
questions the robustness of vendor-published numbers. None of the three
measures the families. The two that aggregate numbers ([15] explicitly,
[14] implicitly) do so under the caveat that the underlying harnesses are
not matched.

The single quantitative methodological precedent is Gervais *et al.* [17].
Their unified Proof-of-Work simulator — instrumented with a single metric
schema, swept over block size and propagation delay, and applied uniformly
to the protocols compared — is structurally the kind of evaluation the
BFT families have not received. The relevant limitation, for the present
thesis, is the protocol family it targets: Proof-of-Work, not the four
BFT families. No equivalent unified-harness study exists for PBFT-style,
PoS-finality, Avalanche-style, and DAG-based protocols evaluated jointly.
This is the gap claim **C3** identifies, now established at
literature-review depth.

## 2.6 The unified-harness gap and the methodology it calls for

Claims C1, C2, and C3 jointly position the thesis. C1 establishes that the
four families are commensurable as objects of comparison: they respond to
the same impossibility, differ only in which assumption they relax, and
share the underlying `3f+1` arithmetic wherever they retain deterministic
safety. C2 establishes that the existing per-family measurements, although
abundant, do not support cross-family judgment under matched conditions;
the obstacle is the reporting vocabulary itself, not the absence of
measurement. C3 establishes that the one methodological precedent for the
kind of evaluation the field needs — Gervais *et al.* [17] — has been
applied to Proof-of-Work only, and that the analogous study for the BFT
families has not been performed.

Chapter 3 responds to that gap with a unified discrete-event simulator, a
shared metric schema instantiated identically for the four families —
latency, throughput, overhead, and reliability
[[wiki/concepts/evaluation-metrics]] — and an experiment matrix that
sweeps the network-delay axis (RQ1), the Byzantine-fraction axis (RQ2),
the validator-set-size axis (RQ3), and the adversarial-strategy axis (RQ4)
under common assumptions [[wiki/concepts/research-questions]],
[[wiki/concepts/experiment-matrix]]. Chapter 4 reports the resulting data
and answers RQ1–RQ4. Chapter 5 supplies the cross-family Pareto synthesis
demanded by RQ5. Chapter 6 concludes.
