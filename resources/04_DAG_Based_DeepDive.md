*Phase 1 — Deep Dive 4 of 4*

**DAG-Based BFT Consensus**

*Decoupling Data Availability from Ordering (Narwhal, Bullshark, Mysticeti)*

# **1\. Overview**

DAG-based BFT protocols answer the Byzantine Generals Problem with a structural reorganisation rather than a new voting scheme. They observe that the cost of classical BFT is dominated by two activities — reliably disseminating transaction batches and agreeing on their order — and that entangling the two is the root cause of latency and bandwidth inefficiency. The Narwhal mempool \[1\] separates data availability from consensus by maintaining a reliably-broadcast DAG of transaction batches, and subsequent protocols such as Bullshark \[2\] and Mysticeti \[3\] derive a total order from the DAG without additional communication in the common case.

For this thesis, DAG-based protocols occupy the high-throughput corner of the design space. They retain the deterministic finality and 3f+1 threshold of PBFT, yet achieve sustained throughput in the hundreds of thousands of transactions per second by letting block proposal and ordering proceed in parallel rather than in lock-step. The cost they pay is in per-node storage and the depth of the pipeline before an order is fixed.

# **2\. Protocol Mechanics**

## **2.1 Narwhal: the DAG mempool**

Narwhal organises time into rounds. In each round, every validator constructs a block (called a certificate-of-availability) that references at least 2f+1 blocks from the previous round. A block becomes a certificate once the validator collects 2f+1 signatures attesting availability of the block’s contents. The structure is thus a sequence of rounds, each containing up to n certificates, with edges between certificates in consecutive rounds representing parent references. No ordering is decided at this stage — only availability.

## **2.2 Tusk and Bullshark: zero-message ordering**

On top of the Narwhal DAG, Tusk \[1\] derives a total order via a deterministic leader schedule: every r rounds, a designated anchor certificate is nominated; a validator commits the anchor (and thus a total order on all ancestors) if a supermajority of certificates in a subsequent round reference it. Bullshark \[2\] refines this with a two-round fast path during synchronous periods, and a fall-back protocol for asynchrony that requires no extra messages beyond the DAG itself.

## **2.3 Mysticeti: uncertified DAGs for minimum latency**

Mysticeti \[3\] further removes the explicit certification step of Narwhal: blocks are broadcast without waiting for 2f+1 signatures, and the DAG edges themselves serve as implicit availability proofs. The commit rule is strengthened so that every block can in principle be committed without delay, reaching the theoretical lower bound of three message rounds for BFT consensus. Mysticeti reports WAN latency of approximately 0.5 s for consensus commit at throughput exceeding 200,000 transactions per second \[3\].

## **2.4 DAG structure**

   round r       round r+1      round r+2      round r+3

   \[v1\]----\\     \[v1\]----\\      \[v1\*\]----\\     \[v1\]

   \[v2\]-----\\    \[v2\]-----\\     \[v2\]------\\    \[v2\]

   \[v3\]------+-\> \[v3\]------+--\> \[v3\]-------+--\> \[v3\]

   \[v4\]-----/    \[v4\]-----/     \[v4\]------/     \[v4\]

                                 ^

                                 |

                  anchor certificate v1\* in round r+2

                  commit v1\* iff \>= 2f+1 certs in round r+3 reference it;

                  total order derived from DAG ancestors of v1\*.

# **3\. Assumptions**

* Asynchronous network for safety. Unlike PBFT, no GST assumption is required for safety; asynchrony affects only the latency with which certificates are completed.

* Byzantine fault threshold f \< n/3, identical to the PBFT family.

* Reliable broadcast primitive. Every validator can eventually broadcast a block to all honest validators; this is implemented via quorum-certificate signatures in Narwhal and via implicit DAG references in Mysticeti.

* Bounded per-validator storage. Each validator keeps the DAG of the most recent rounds until they are committed; committed rounds can be pruned.

# **4\. Behaviour under Network Delay**

DAG-based protocols exhibit the most graceful degradation under delay of any family studied here. Because certificates form independently per validator and are simply referenced (not voted on) in later rounds, a slow validator delays only its own certificate without stalling the round: the other validators fill their parent references from the 2f+1 certificates that did arrive. Throughput therefore declines only in proportion to the number of actually-delayed validators, not to the worst-case link in the network.

The one latency cost is pipeline depth: commits follow anchors, and anchors are chosen only every few rounds. Bullshark and Mysticeti have reduced this depth to two or three rounds in the common case. Under heavy asynchrony, however, repeated failures to commit an anchor can push the pipeline to many rounds before consensus catches up, producing a latency spike but not a throughput collapse.

# **5\. Behaviour under Adversarial Conditions**

Three adversarial strategies are relevant to DAG-based protocols and will be implemented as simulator behaviours.

* Withholding. Byzantine validators skip broadcasting their own certificates. As long as at least 2f+1 certificates per round are still produced, the DAG continues to advance and the order of committed transactions is unaffected, though throughput is reduced proportionally.

* Equivocating broadcast. Byzantine validators broadcast different block contents to different peers in the same round. Narwhal’s certificate step — requiring 2f+1 signatures on a specific content hash — prevents any conflicting version from ever reaching certificate status. Mysticeti handles equivocation slightly differently: by requiring multiple implicit references before commitment, it tolerates equivocation without separate certificates.

* Anchor suppression. Byzantine validators refuse to reference a specific honest anchor certificate. Provided at least 2f+1 honest validators do reference the anchor, commit still proceeds. If the adversary can suppress references at exactly the right rounds, commit can be delayed but not permanently prevented.

Safety requires that no two honest validators commit different total orders; this follows from the DAG determinism and the 2f+1 anchor reference rule. As with PBFT, safety holds categorically up to the threshold and is violable only above it.

# **6\. Communication Complexity**

| Protocol | Per-block msgs | Latency (rounds) | Throughput (reported) |
| :---- | :---- | :---- | :---- |
| **Narwhal \+ Tusk \[1\]** | O(n) certs \+ refs | \~5–7 (to commit) | \~140 ktps \[1\] |
| **Bullshark \[2\]** | O(n) (same DAG) | 2 (fast path) | \~125 ktps \[2\] |
| **Mysticeti \[3\]** | O(n) implicit refs | 3 (theoretical lower bound) | \>200 ktps, \~0.5 s WAN \[3\] |

*The structural advantage is that ordering adds no new message class on top of the DAG itself — the same messages that provide data availability also provide the votes required for total order. Compared to PBFT’s O(n²) per-block quorum traffic, this reduces per-block message count by an order of magnitude for large validator sets.*

# **7\. Relevance to this Thesis**

DAG-based protocols anchor the high-throughput, asynchrony-tolerant corner of the design space. They preserve deterministic finality and the classical 3f+1 threshold, yet achieve throughput figures an order of magnitude above classical BFT by decoupling data availability from ordering. In the simulator we will implement a simplified Narwhal-like mempool with a Tusk-style commit rule, exposing: (i) round duration, (ii) certificate signature threshold, (iii) anchor period, and (iv) per-validator storage ceiling.

Expected findings — to be confirmed in Chapter 5 — are: (i) throughput is largely insensitive to delay up to the round duration, degrading gracefully rather than cliff-edging; (ii) adversarial withholding reduces throughput proportionally to the Byzantine fraction without endangering safety; (iii) anchor-suppression extends commit latency predictably. These position DAG-based protocols as the strongest throughput candidate in the comparative analysis while clarifying that their per-block storage cost is the dual tradeoff against PBFT’s per-block message cost.

# **References**

**\[1\]** G. Danezis, L. Kokoris-Kogias, A. Sonnino, and A. Spiegelman, “Narwhal and Tusk: A DAG-based Mempool and Efficient BFT Consensus,” in Proc. 17th European Conference on Computer Systems (EuroSys), 2022, pp. 34–50.

**\[2\]** A. Spiegelman, N. Giridharan, A. Sonnino, and L. Kokoris-Kogias, “Bullshark: DAG BFT Protocols Made Practical,” in Proc. ACM Conference on Computer and Communications Security (CCS), 2022, pp. 2705–2718.

**\[3\]** K. Babel, A. Chursin, G. Danezis, L. Kokoris-Kogias, and A. Sonnino, “Mysticeti: Reaching the Latency Limits with Uncertified DAGs,” arXiv preprint arXiv:2310.14821, 2023\.