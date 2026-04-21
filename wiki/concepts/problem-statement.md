# Thesis Problem Statement

Single-source framing for the thesis: the title, the gap the work closes, the
objectives it pursues, the scope boundary, and the criteria under which it is
judged complete. The research questions that structure the empirical work
live in [[concepts/research-questions]].

## Thesis title

*Performance–Security Evaluation of Layer-1 Consensus Algorithms under
Network Delay and Adversarial Conditions: A Simulation-Based Comparative
Study.*

The title preserves the central contribution (performance–security
evaluation under delay and adversarial conditions), qualifies the method
(*simulation-based*), and frames the treatment (*comparative*) —
distinguishing the work from single-protocol benchmarks and from purely
theoretical treatments.

## The gap

The four families evaluated in this thesis — [[algorithms/pbft]] (PBFT-style,
refs [4]–[6]), [[algorithms/pos]] (PoS-finality [7], [8]),
[[algorithms/avalanche]] (Avalanche-style probabilistic [9]), and
[[algorithms/dag-based]] (DAG-based [11]–[13]) — each resolve the classical
BFT tradeoff between safety, liveness, and efficiency [1]–[3] differently.
Practitioners and researchers lack a unified, internally-consistent empirical
basis for comparing them under realistic operating conditions.

Three specific gaps make comparison difficult:

1. **Heterogeneous harnesses.** Reported performance numbers originate from
   different hardware, workloads, topologies, and batching parameters, so
   cross-protocol claims are not directly comparable — a limitation
   explicitly noted in the principal surveys [14], [15].

2. **Benign-condition bias.** Existing benchmarks predominantly evaluate
   protocols under benign network conditions. Systematic evaluation under
   configurable network delay, packet loss, and adversarial validator
   behaviour is absent for BFT families, in contrast to the methodologically
   mature simulation studies available for Proof-of-Work [17].

3. **No unified harness across families.** No single study has instrumented
   PBFT-style, PoS-finality, Avalanche-style, and DAG-based protocols under
   one simulator with a shared metric schema. Existing comparative analyses
   are either qualitative [16] or cover only a subset of families [14].

## Thesis contribution

This thesis constructs a discrete-event simulator that hosts simplified
implementations of one representative from each of the four consensus
families, instruments them with a unified metric schema — latency,
throughput, communication overhead, and consensus reliability — and
subjects them to controlled experiments under network delay and adversarial
validator behaviour. The resulting dataset enables a like-for-like
comparison of the performance–security tradeoff that is neither available
in the current literature nor obtainable from isolated protocol-paper
benchmarks.

## Objectives

The research questions (see [[concepts/research-questions]]) translate into
four concrete objectives.

1. **Build** a discrete-event simulator that exposes configurable network
   delay, packet loss, and adversarial-validator behaviours, and that
   uniformly instruments latency, throughput, communication overhead, and
   consensus reliability.

2. **Implement** one simplified representative per consensus family
   ([[algorithms/pbft]], [[algorithms/pos]], [[algorithms/avalanche]],
   [[algorithms/dag-based]]) within the simulator, each conforming to the
   same Validator / Messaging / Metrics API.

3. **Execute** a controlled experimental matrix (delay distributions ×
   adversarial strategies × validator-set sizes) that answers RQ1–RQ4.

4. **Analyse** the resulting dataset to answer RQ5 (performance–security
   Pareto frontier) and produce a comparative synthesis that the existing
   literature does not offer.

## Intended contributions

- A simulation framework for Layer-1 consensus evaluation under network
  delay and adversarial conditions, with a shared metric schema and a
  pluggable protocol interface.
- Simplified reference implementations of four consensus families within a
  single harness, enabling reproducible like-for-like comparison.
- An experimental dataset and comparative analysis quantifying the
  performance–security tradeoff across the four families under matched
  conditions.
- Methodological precedent: extending the simulation-based,
  metrics-instrumented approach of Gervais et al. [17] (originally for
  Proof-of-Work) to BFT, PoS-finality, probabilistic, and DAG-based families.

## Scope

| In scope | Out of scope |
| :---- | :---- |
| Four L1 consensus families: PBFT-style, PoS-finality, Avalanche-style, DAG-based. | Proof-of-Work consensus as a subject of comparison (covered only as methodological baseline [17]). |
| Discrete-event simulation at the message-passing level. | Layer-2 protocols (rollups, payment channels, sidechains). |
| Configurable network delay (constant, uniform, exponential, heavy-tailed) and packet loss. | Deployment on a real testnet or mainnet; no live-network measurements. |
| Byzantine validator behaviours: silent non-participation, delayed voting, equivocation, selective dropping (see [[concepts/fault-model]]). | Economic/incentive design (reward schedules, token economics). |
| Uniform metrics: latency, throughput, communication overhead, consensus reliability. | Cryptographic primitive performance (signature schemes, threshold cryptography internals). |
| Validator sets up to hundreds of nodes (sized to support reproducible trials). | Governance, client software, or user-application concerns. |

## Assumptions and limitations

- **Simplified implementations are intentional.** The aim is fair
  comparison, not production performance. Results are indicative of
  protocol-family behaviour, not of any specific production codebase.

- **Idealised network model.** Delay and loss are configurable, but the
  simulator does not model TCP congestion control, kernel scheduling, or
  physical-layer jitter. This matches the abstraction level used in prior
  simulation studies [17].

- **Strategy-based adversarial coverage.** The four adversarial strategies
  evaluated are those most commonly discussed in the primary literature;
  attacks requiring specialised cryptographic or economic modelling are
  noted as future work.

- **Literature numbers are sanity checks, not validation targets.**
  Quantitative ranges from [11]–[13], [15] serve as order-of-magnitude
  checks. The simulator's contribution is internal consistency, not matching
  production throughput numbers.

## Success criteria

The thesis is complete when:

1. The simulator compiles and runs all four consensus-family implementations
   from a single configuration file.
2. Each experiment in the RQ1–RQ4 matrix produces reproducible metric
   outputs across repeated trials.
3. Chapter 5 presents a comparative Pareto analysis that directly answers
   RQ5 with supporting evidence from the dataset.
4. The simulator and dataset are archived in a form that permits third-party
   reproduction.

## Source

Imported from `resources/Problem_Statement_and_RQs.md` §§1–2, 4–8 (Phase 3
— Thesis Framing). Bracketed numbers `[N]` follow the annotated-bibliography
numbering carried forward from Phase 2; dedicated `wiki/sources/` pages for
[1]–[17] are produced under S6/T8. `TODO(cite)`: link bracketed refs to
source pages once S6 lands.

## Revisions

None.
