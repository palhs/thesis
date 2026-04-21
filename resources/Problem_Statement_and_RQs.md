*Phase 3 — Thesis Framing*

**Problem Statement, Research Questions, Title and Scope**

# **1\. Thesis Title**

**Performance–Security Evaluation of Layer-1 Consensus Algorithms under Network Delay and Adversarial Conditions: A Simulation-Based Comparative Study.**

The title preserves the proposal’s central contribution (performance–security evaluation under delay and adversarial conditions) and adds the methodological qualifier (simulation-based) and the framing (comparative) that distinguish the work from single-protocol measurements or purely theoretical treatments.

# **2\. Problem Statement**

Layer-1 blockchain consensus algorithms have proliferated into four architecturally distinct families — PBFT-style \[4\], \[5\], \[6\], Proof-of-Stake finality \[7\], \[8\], Avalanche-style probabilistic \[9\], and DAG-based \[11\], \[12\], \[13\] — each offering a different resolution of the classical Byzantine Fault Tolerance tradeoff between safety, liveness, and efficiency \[1\], \[2\], \[3\]. Practitioners and researchers presently lack a unified, internally-consistent empirical basis for comparing these families under realistic operating conditions.

Three gaps in the existing literature make such a comparison difficult. First, reported performance numbers originate from heterogeneous experimental harnesses that differ in hardware, workload, network topology, and batching parameters, so cross-protocol claims are not directly comparable — a limitation explicitly noted in the principal surveys \[14\], \[15\]. Second, existing benchmarks predominantly evaluate protocols under benign network conditions; systematic evaluation under configurable network delay, packet loss, and adversarial validator behaviour has been absent for BFT families, in contrast to the methodologically mature simulation studies available for Proof-of-Work \[17\]. Third, no single study has instrumented PBFT-style, PoS-finality, Avalanche-style, and DAG-based protocols under one simulator with a shared metric schema — the comparative analyses that exist are either qualitative \[16\] or cover only a subset of families \[14\].

This thesis addresses those gaps by constructing a discrete-event simulator that hosts simplified implementations of one representative from each of the four consensus families, instruments them with a unified metric schema (latency, throughput, communication overhead, and consensus reliability), and subjects them to controlled experiments under network delay and adversarial validator behaviour. The resulting dataset enables a like-for-like comparison of the performance–security tradeoff that is neither available in the current literature nor obtainable from isolated protocol-paper benchmarks.

# **3\. Research Questions**

Five research questions (RQ1–RQ5) structure the evaluation. Each is stated with a measurable scope so that its answer is empirical rather than speculative. The questions map one-to-one onto the metric schema in Evaluation\_Metrics.docx and define the experimental matrix of Chapter 4\.

| ID | Research question | Primary metric(s) | Independent variable |
| :---- | :---- | :---- | :---- |
| **RQ1** | How does end-to-end commit latency scale, for each of the four consensus families, as network delay variance increases from nominal to heavy-tailed? | Commit latency, round latency, time-to-finality | Delay distribution (constant, uniform, exponential, heavy-tailed) |
| **RQ2** | How does sustained throughput of each family degrade under increasing Byzantine fraction, below and approaching the theoretical threshold? | Throughput (tps), goodput, peak throughput | Byzantine fraction 0 → f\_max |
| **RQ3** | What is the relative communication overhead of each family, measured in messages per block and bytes per block, under a fixed workload and identical network assumptions? | Messages per block, bytes per block, per-validator state size | Validator-set size n |
| **RQ4** | Under which adversarial strategies (silent non-participation, delayed voting, equivocation, selective dropping) does each family experience liveness degradation, safety violations, or neither? | Consensus success rate, view-change/reorg frequency, safety-violation probability (ε) | Adversarial strategy × Byzantine fraction |
| **RQ5** | Is there a consistent Pareto frontier of the performance–security tradeoff across families, and does any family dominate the others across all operating regimes? | All four metric families jointly | Combined (delay, adversary, n, workload) |

*RQ1–RQ4 generate the data. RQ5 is the synthesis question whose answer is the headline contribution of the comparative analysis in Chapter 5\.*

# **4\. Thesis Objectives**

The research questions translate into four concrete objectives for the thesis.

1. Build a discrete-event simulator that exposes configurable network delay, packet loss, and adversarial-validator behaviours, and that uniformly instruments latency, throughput, communication overhead, and consensus-reliability metrics.

2. Implement one simplified representative per consensus family (PBFT-style, PoS-finality, Avalanche-style, DAG-based) within the simulator, with each implementation conforming to the same Validator / Messaging / Metrics API.

3. Design and execute a controlled experimental matrix that answers RQ1–RQ4 across the parameter space of delay distributions, adversarial strategies, and validator-set sizes.

4. Analyse the resulting dataset to answer RQ5 (the performance–security Pareto frontier) and to produce a comparative synthesis that the existing literature does not offer.

# **5\. Intended Contributions**

* A simulation framework for Layer-1 consensus evaluation under network delay and adversarial conditions, with a shared metric schema and a pluggable protocol interface.

* Simplified reference implementations of four consensus families within a single harness, enabling reproducible like-for-like comparison.

* An experimental dataset and comparative analysis quantifying the performance–security tradeoff across the four families under matched conditions.

* Methodological precedent: extending the simulation-based, metrics-instrumented approach of Gervais et al. \[17\] (which targeted Proof-of-Work) to the BFT, PoS-finality, probabilistic, and DAG-based families.

# **6\. Scope — In and Out**

| In scope | Out of scope |
| :---- | :---- |
| • Four Layer-1 consensus families: PBFT-style, PoS-finality, Avalanche-style, DAG-based. • Discrete-event simulation at the message-passing level. • Configurable network delay (constant, uniform, exponential, heavy-tailed) and packet loss. • Byzantine validator behaviours: silent non-participation, delayed voting, equivocation, selective dropping. • Uniform metrics: latency, throughput, communication overhead, consensus reliability. • Validator sets up to hundreds of nodes (sized to support reproducible trials). | • Proof-of-Work consensus as a subject of comparison (covered only as methodological baseline \[17\]). • Layer-2 protocols (rollups, payment channels, sidechains). • Deployment on a real testnet or mainnet; no live-network measurements. • Economic/incentive design (reward schedules, token economics). • Cryptographic primitive performance (signature schemes, threshold cryptography internals). • Governance, client software, or user-application concerns. |

# **7\. Assumptions and Limitations**

* Simplified implementations are intentional: the aim is fair comparison, not production performance. Results are therefore indicative of protocol-family behaviour rather than of any specific production codebase.

* Simulated network is idealised. Although delay and loss are configurable, the simulator does not model TCP congestion control, kernel scheduling, or physical-layer jitter. This is consistent with the level of abstraction used in prior simulation studies \[17\].

* Adversarial coverage is strategy-based, not exhaustive. The four adversarial strategies evaluated are those most commonly discussed in the primary literature; attacks requiring specialised cryptographic or economic modelling are noted as future work.

* Quantitative ranges cited from the literature \[11\]–\[13\], \[15\] serve as expected-order-of-magnitude sanity checks for the simulator, not as validation targets. The simulator’s contribution is internal consistency, not matching production throughput numbers.

# **8\. Success Criteria**

The thesis is considered complete when: (i) the simulator compiles and runs all four consensus-family implementations from a single configuration file; (ii) each experiment in the RQ1–RQ4 matrix produces reproducible metric outputs across repeated trials; (iii) Chapter 5 presents a comparative Pareto analysis that directly answers RQ5 with supporting evidence from the dataset; and (iv) the simulator and dataset are archived in a form that permits third-party reproduction.

# **References**

*References reuse the numbering established in the Annotated Bibliography (Phase 2).*

**\[1\]** L. Lamport, R. Shostak, and M. Pease, “The Byzantine Generals Problem,” ACM TOPLAS, 1982\.

**\[2\]** M. J. Fischer, N. A. Lynch, and M. S. Paterson, “Impossibility of Distributed Consensus with One Faulty Process,” J. ACM, 1985\.

**\[3\]** C. Dwork, N. Lynch, and L. Stockmeyer, “Consensus in the Presence of Partial Synchrony,” J. ACM, 1988\.

**\[4\]** M. Castro and B. Liskov, “Practical Byzantine Fault Tolerance,” OSDI, 1999\.

**\[5\]** M. Yin et al., “HotStuff: BFT Consensus with Linearity and Responsiveness,” PODC, 2019\.

**\[6\]** E. Buchman, J. Kwon, and Z. Milosevic, “The Latest Gossip on BFT Consensus,” arXiv:1807.04938, 2018\.

**\[7\]** V. Buterin and V. Griffith, “Casper the Friendly Finality Gadget,” arXiv:1710.09437, 2017\.

**\[8\]** V. Buterin et al., “Combining GHOST and Casper,” arXiv:2003.03052, 2020\.

**\[9\]** Team Rocket et al., “Scalable and Probabilistic Leaderless BFT Consensus through Metastability,” arXiv:1906.08936, 2019\.

**\[11\]** G. Danezis et al., “Narwhal and Tusk,” EuroSys, 2022\.

**\[12\]** A. Spiegelman et al., “Bullshark: DAG BFT Protocols Made Practical,” CCS, 2022\.

**\[13\]** K. Babel et al., “Mysticeti,” arXiv:2310.14821, 2023\.

**\[14\]** S. Bano et al., “SoK: Consensus in the Age of Blockchains,” AFT, 2019\.

**\[15\]** Y. Xiao et al., “A Survey of Distributed Consensus Protocols for Blockchain Networks,” IEEE CST, 2020\.

**\[16\]** C. Cachin and M. Vukolic, “Blockchain Consensus Protocols in the Wild,” arXiv:1707.01873, 2017\.

**\[17\]** A. Gervais et al., “On the Security and Performance of Proof of Work Blockchains,” CCS, 2016\.