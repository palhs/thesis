*Phase 2 — Literature Synthesis*

**Evaluation Metrics for Layer-1 Consensus**

*A Synthesised Metric Schema for the Simulator and Comparative Analysis*

# **1\. Purpose**

Each consensus family studied in this thesis has historically been evaluated with its own metric vocabulary. PBFT papers report operations per second and view-change cost \[4\], \[5\]; Casper FFG papers report time-to-finality in epochs \[7\]; Avalanche papers report probabilistic ε and per-transaction confirmation latency \[9\]; DAG-based papers report throughput in kilo-transactions per second and commit latency at the WAN \[11\]–\[13\]. Making these families comparable requires a single, shared metric schema that every implementation in the simulator exports, with every definition traceable to at least one primary source in the literature.

This document synthesises such a schema from the canonical and survey literature. Each metric below is defined formally, attributed to the sources that introduced or measured it, and annotated with the adversarial/delay conditions under which it is meaningful. The metric schema then drives the simulator’s instrumentation API in Phase 3\.

# **2\. Core Metric Schema**

The schema groups metrics into four families: latency, throughput, communication overhead, and consensus reliability. Each metric is instrumented uniformly in the simulator across all four consensus families so that comparative tables and plots operate on identical definitions.

| Family | Metric | Definition | Source(s) |
| :---- | :---- | :---- | :---- |
| **Latency** | End-to-end commit latency | Wall-clock time from transaction submission to first inclusion in a committed block, averaged over a measurement window. | \[4\], \[11\], \[17\] |
|  | Time-to-finality | Wall-clock time from transaction submission until finality (deterministic: 2f+1 commits collected or checkpoint finalised; probabilistic: confidence threshold β reached). | \[4\], \[7\], \[9\], \[13\] |
|  | Round latency | Time to complete one protocol round (prepare, commit, or Avalanche sampling round). | \[4\], \[5\], \[9\] |
| **Throughput** | Transactions per second (tps) | Count of committed transactions per unit wall-clock time, averaged over a stable-state measurement window. | \[11\]–\[13\], \[15\], \[17\] |
|  | Goodput | tps of transactions that survive to finality (excludes transactions in reorganised forks). | \[8\], \[17\] |
|  | Peak throughput | Maximum sustained tps before queueing delay diverges. | \[11\], \[13\], \[15\] |
| **Overhead** | Messages per block | Count of protocol messages transmitted per committed block; informs bandwidth cost and aggregation effectiveness. | \[4\], \[5\], \[11\] |
|  | Bytes per block | Total bytes of protocol messages per block (absolute bandwidth). | \[15\], \[17\] |
|  | Per-validator state size | Storage footprint required per validator to operate the protocol (DAG retention, vote caches, attestation buffers). | \[11\], \[13\] |
| **Reliability** | Consensus success rate | Fraction of protocol rounds that successfully commit a value under a given adversary/delay scenario. | \[4\], \[5\], \[9\], \[17\] |
|  | Fork rate | Fraction of proposed blocks/rounds that do not survive to finality (analogue of stale-block rate in PoW). | \[8\], \[17\] |
|  | View-change / reorg frequency | Count of view changes (PBFT-family) or reorgs (PoS-finality) per unit time, tracking liveness disruption. | \[4\], \[5\], \[8\] |
|  | Safety-violation probability (ε) | Empirical probability that two honest validators commit conflicting values; meaningful primarily for probabilistic protocols. | \[9\], \[10\] |
|  | Fault-tolerance threshold (f\_max) | Maximum adversarial fraction (by count or by stake) under which the protocol preserves safety in the simulator. | \[1\], \[3\], \[7\], \[14\] |

# **3\. Reported Metric Ranges in the Literature**

The table below reproduces the most widely cited quantitative claims across the four families. Every number is attributed to its primary source; these numbers are used in Chapter 5 only as baselines for qualitative comparison with the simulator’s own measurements, not as ground truth.

| Family | Throughput (reported) | Latency (reported) | f\_max | Source |
| :---- | :---- | :---- | :---- | :---- |
| **PBFT (LAN)** | Thousands of ops/s (LAN) | Sub-10 ms (LAN) | \< n/3 | \[4\] |
| **HotStuff** | Linear with n after optimisations | 3-round commit | \< n/3 | \[5\] |
| **Casper FFG / Gasper** | Block-proposal rate of underlying chain | Two-epoch finality (≤12.8 min for 32-slot epochs in Ethereum) | \< 1/3 of stake | \[7\], \[8\] |
| **Avalanche** | \~3.4 ktps (testnet) | \~1.35 s | Parameter-dependent (\~\< 1/5 typical) | \[9\], \[10\] |
| **Narwhal \+ Tusk** | \~140 ktps (WAN) | \~2–3 s | \< n/3 | \[11\] |
| **Bullshark** | \~125 ktps | 2-round fast path under synchrony | \< n/3 | \[12\] |
| **Mysticeti** | \>200 ktps | \~0.5 s (WAN, consensus commit) | \< n/3 | \[13\] |
| **PoW baseline (Bitcoin-style)** | Tens of tps max, block-interval dependent | \~10–60 min confirmation | \< \~1/4 hashrate (selfish-mining bound) | \[17\] |

*Caveat: The literature does not report these figures under a unified experimental harness. Hardware, workload, batching, and geographic distribution differ across each source. The survey \[15\] explicitly notes this inconsistency as the primary obstacle to an accurate comparative evaluation, and it is the obstacle this thesis’s simulator is designed to remove.*

# **4\. Adversarial and Delay Axes for Experimental Design**

Metrics alone are insufficient for a comparative evaluation under stress. The literature identifies a consistent set of adversarial and delay dimensions along which consensus protocols must be probed. These will become the independent variables of the simulator’s experiments in Chapter 4\.

* Byzantine fraction. Fraction of validators exhibiting Byzantine behaviour, swept from 0 to just above the theoretical threshold for each family \[1\], \[3\], \[14\].

* Network delay distribution. Constant, uniform, exponential, and heavy-tailed delay models; the choice materially changes PBFT-family behaviour via view-change frequency \[4\], \[5\], and Avalanche via round-time variance \[9\], \[10\].

* Packet loss rate. Independent Bernoulli loss per message; probes the resilience of reliable-broadcast assumptions in DAG-based protocols \[11\], \[13\].

* Partitions and GST. Intervals of asynchrony bounded by a stabilisation time; required to exercise the partial-synchrony assumption faithfully \[3\].

* Adversarial strategies. Silent non-participation, delayed voting, equivocation, and selective message-dropping; each maps to a specific behaviour documented in one or more primary sources \[4\], \[7\], \[9\].

# **5\. Mapping Metric Schema to Simulator Instrumentation**

The schema above is enforced in the simulator as a Metric interface that every consensus family implementation must populate. Concretely, each family implementation exports: (i) a per-transaction timestamp log from which commit latency, time-to-finality, and goodput are derived; (ii) a per-block message count and byte-size log; (iii) an event log for view changes, reorgs, and safety-check failures; (iv) a per-validator state-size sample. The simulator runner aggregates these across trials and produces a single comparative CSV per scenario, whose columns match the metrics defined in Section 2\.

This is precisely the methodological practice recommended by \[14\] (Bano et al., 2019\) and critiqued as missing in \[16\] (Cachin and Vukolic, 2017). The thesis’s contribution is to apply the same practice, under a single simulator, to the four families above so that the reported ranges in Section 3 can be replaced with internally-consistent measurements.

# **References**

*References below reuse the numbering established in the annotated bibliography (Annotated\_Bibliography.xlsx); the same \[n\] values appear in this document, in the Phase-1 deep-dives, and will continue in Chapters 1 and 2 so that the thesis has a single coherent bibliography.*

**\[1\]** L. Lamport, R. Shostak, and M. Pease, “The Byzantine Generals Problem,” ACM TOPLAS, vol. 4, no. 3, pp. 382–401, 1982\.

**\[3\]** C. Dwork, N. Lynch, and L. Stockmeyer, “Consensus in the Presence of Partial Synchrony,” J. ACM, vol. 35, no. 2, pp. 288–323, 1988\.

**\[4\]** M. Castro and B. Liskov, “Practical Byzantine Fault Tolerance,” in Proc. OSDI, 1999, pp. 173–186.

**\[5\]** M. Yin et al., “HotStuff: BFT Consensus with Linearity and Responsiveness,” in Proc. PODC, 2019, pp. 347–356.

**\[7\]** V. Buterin and V. Griffith, “Casper the Friendly Finality Gadget,” arXiv:1710.09437, 2017\.

**\[8\]** V. Buterin et al., “Combining GHOST and Casper,” arXiv:2003.03052, 2020\.

**\[9\]** Team Rocket et al., “Scalable and Probabilistic Leaderless BFT Consensus through Metastability,” arXiv:1906.08936, 2019\.

**\[10\]** I. Amores-Sesar, C. Cachin, and P. Schneider, “An Analysis of Avalanche Consensus,” arXiv:2401.02811, 2024\.

**\[11\]** G. Danezis et al., “Narwhal and Tusk: A DAG-based Mempool and Efficient BFT Consensus,” in Proc. EuroSys, 2022, pp. 34–50.

**\[12\]** A. Spiegelman et al., “Bullshark: DAG BFT Protocols Made Practical,” in Proc. CCS, 2022, pp. 2705–2718.

**\[13\]** K. Babel et al., “Mysticeti: Reaching the Latency Limits with Uncertified DAGs,” arXiv:2310.14821, 2023\.

**\[14\]** S. Bano et al., “SoK: Consensus in the Age of Blockchains,” in Proc. AFT, 2019, pp. 183–198.

**\[15\]** Y. Xiao, N. Zhang, W. Lou, and Y. T. Hou, “A Survey of Distributed Consensus Protocols for Blockchain Networks,” IEEE Commun. Surveys & Tutorials, vol. 22, no. 2, pp. 1432–1465, 2020\.

**\[16\]** C. Cachin and M. Vukolic, “Blockchain Consensus Protocols in the Wild,” arXiv:1707.01873, 2017\.

**\[17\]** A. Gervais et al., “On the Security and Performance of Proof of Work Blockchains,” in Proc. CCS, 2016, pp. 3–16.