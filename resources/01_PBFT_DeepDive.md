*Phase 1 — Deep Dive 1 of 4*

**PBFT-Family Consensus**

*Deterministic BFT under Partial Synchrony*

# **1\. Overview**

The PBFT family answers the Byzantine Generals Problem under the partial-synchrony assumption. Its defining proposition is: if a network eventually stabilises and a supermajority of validators are honest, a deterministic three-phase protocol can commit blocks with immediate, irreversible finality. This family includes the original PBFT protocol by Castro and Liskov \[1\], the pipelined and linearised HotStuff \[2\], and the Tendermint protocol \[3\] which is used in Cosmos SDK chains. All three share the same skeleton: a rotating leader proposes, 3f+1 replicas vote in disciplined phases, and a view-change mechanism recovers liveness when the leader is faulty or slow.

For this thesis, PBFT-family protocols represent the safety-first end of the design spectrum. They will serve as the baseline against which probabilistic (Avalanche) and DAG-based families are compared on latency, throughput, and resilience under delay.

# **2\. Protocol Mechanics**

## **2.1 The three-phase commit**

PBFT operates in a sequence of views, each led by a designated primary replica. Within a view, every request goes through three message phases before it is committed.

* Pre-prepare. The primary assigns a sequence number to a client request and multicasts a PRE-PREPARE message to all replicas.

* Prepare. Each replica that accepts the pre-prepare multicasts a PREPARE message. A replica is said to be prepared for the request once it has collected 2f matching PREPARE messages plus the original pre-prepare (i.e. a quorum of 2f+1).

* Commit. Each prepared replica multicasts a COMMIT message. Once a replica collects 2f+1 matching COMMIT messages it executes the request and replies to the client.

The two-round quorum structure is what gives PBFT its safety guarantee: any two quorums of size 2f+1 within a 3f+1 replica set must intersect in at least f+1 honest replicas, so conflicting commits at the same sequence number are ruled out.

## **2.2 Message flow diagram**

     Client      Primary (R0)     R1         R2         R3

       |             |            |          |          |

       |--request---\>|            |          |          |

       |             |-pre-prep--\>|---------\>|---------\>|   \<-- Pre-Prepare

       |             |            |          |          |

       |             |\<--prepare--|\<---------|\<---------|

       |             |--prepare--\>|---------\>|---------\>|   \<-- Prepare (2f+1)

       |             |            |          |          |

       |             |\<--commit---|\<---------|\<---------|

       |             |--commit---\>|---------\>|---------\>|   \<-- Commit (2f+1)

       |             |            |          |          |

       |\<------------reply (f+1 matching)---- |----------|

## **2.3 View change**

If the primary is faulty or the network delays its messages beyond a timeout, each replica broadcasts a VIEW-CHANGE message containing evidence of its most recent prepared requests. When the next primary receives 2f+1 matching VIEW-CHANGE messages, it broadcasts a NEW-VIEW message that re-anchors all prepared-but-not-committed requests, and the protocol resumes in the new view. View change is the liveness recovery mechanism and is also the most expensive part of PBFT: in the original formulation it is O(n³) in messages, which motivated the linearised view change of HotStuff \[2\].

# **3\. Assumptions**

* Partial synchrony. The network alternates between asynchronous and synchronous periods; after an unknown Global Stabilisation Time (GST), message delivery is bounded by some Δ.

* Byzantine fault threshold. At most f out of n \= 3f+1 replicas may behave arbitrarily; the rest are honest and follow the protocol.

* Authenticated channels. Every message is signed, so forgery is computationally infeasible and any replica can verify the source of a message.

* Static validator set. The replica set is fixed within a view; validator rotation occurs only at epoch boundaries (in PoS variants) or is out of scope (in the original PBFT).

# **4\. Behaviour under Network Delay**

Network delay affects PBFT along two dimensions. First, within a view, delay extends the time required to assemble the 2f+1 quorum at each phase, linearly increasing end-to-end commit latency. Because PBFT requires synchronous quorum formation, a single slow link at the tail of the delay distribution is enough to stall the entire block. Second, if delay exceeds the view-change timeout, replicas trigger a view change even when the primary is honest — the so-called spurious view change. Spurious view changes waste the O(n²) or O(n³) view-change traffic and suppress throughput under bursty delay.

HotStuff \[2\] mitigates the first problem by pipelining phases (each phase is a vote on the next block, so three in-flight blocks at any time amortise the three-round latency) and mitigates the second by linearising view change to O(n). Tendermint \[3\] mitigates the second by using a round-robin leader schedule so that no replica is structurally privileged. The simulator for this thesis will expose the view-change timeout as a first-class parameter to let us quantify these effects empirically.

# **5\. Behaviour under Adversarial Conditions**

Within the f \< n/3 threshold, PBFT guarantees safety under any Byzantine behaviour, including full collusion, equivocation, and arbitrary message forgery. However, liveness — not safety — is the pressure point an adversary can exploit. Three adversarial strategies matter for the simulator.

* Silent non-participation. Byzantine replicas abstain from voting, forcing honest replicas to wait the full timeout before initiating a view change. This inflates latency without violating safety.

* Equivocating primary. A Byzantine primary sends conflicting PRE-PREPARE messages to different subsets of replicas. PBFT detects this at the PREPARE phase (no 2f+1 quorum ever forms for conflicting values), triggering a view change. The adversary’s gain is a liveness stall, not a safety break.

* Delayed voting. Byzantine replicas wait until the last possible moment to send their PREPARE and COMMIT messages. This extends every quorum round to the Byzantine replicas’ own schedule, degrading throughput even though correctness is preserved.

If the threshold is exceeded — i.e. f ≥ n/3 — safety can be violated: two conflicting values can each collect a quorum of 2f+1 and both commit. This is the threshold-boundary behaviour the thesis will probe by ramping the Byzantine fraction in the simulator.

# **6\. Communication Complexity**

| Protocol | Normal-case per block | View change | Latency (rounds) |
| :---- | :---- | :---- | :---- |
| **PBFT \[1\]** | O(n²) | O(n³) | 3 |
| **Tendermint \[3\]** | O(n²) | O(n²) | 3 |
| **HotStuff \[2\]** | O(n) | O(n) | 3 (pipelined) |

*The trend from PBFT to HotStuff is a progressive reduction in message complexity through threshold signatures (a single aggregated vote instead of n individual votes) and pipelining (overlapping phases across consecutive blocks). For the thesis, the simulator will report per-block message count directly so that protocols can be compared under identical workloads.*

# **7\. Relevance to this Thesis**

PBFT-family protocols anchor the safety-first corner of the design space. Their deterministic finality and well-understood worst-case behaviour make them the natural baseline for comparative evaluation. In the simulator we will implement a simplified PBFT variant following the skeleton in Section 2, exposing the following knobs for experimentation: (i) view-change timeout, (ii) pipeline depth (to mimic HotStuff’s optimisation), (iii) quorum size (to explore degraded or enhanced fault thresholds), and (iv) primary rotation policy.

Expected experimental findings — to be confirmed in Chapter 5 — are that PBFT-family protocols maintain safety across the full Byzantine threshold but degrade in throughput sharply as delay variance increases, and that view-change frequency is the dominant throughput killer under adversarial delay. These hypotheses will be evaluated against concrete latency and throughput curves produced by the simulator.

# **References**

**\[1\]** M. Castro and B. Liskov, “Practical Byzantine Fault Tolerance,” in Proc. 3rd USENIX Symposium on Operating Systems Design and Implementation (OSDI), 1999, pp. 173–186.

**\[2\]** M. Yin, D. Malkhi, M. K. Reiter, G. G. Gueta, and I. Abraham, “HotStuff: BFT Consensus with Linearity and Responsiveness,” in Proc. ACM Symposium on Principles of Distributed Computing (PODC), 2019, pp. 347–356.

**\[3\]** E. Buchman, J. Kwon, and Z. Milosevic, “The latest gossip on BFT consensus,” arXiv preprint arXiv:1807.04938, 2018\.