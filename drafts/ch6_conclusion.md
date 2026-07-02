# Chapter 6 — Conclusions

## 6.1 Summary of findings

Table 6.1 answers the five research questions; each answer is a claim about the representative implementation evaluated, not its whole protocol family.

**Table 6.1 — The five research questions and their answers over the three protocols evaluated.** Source: [[wiki/concepts/research-questions]], [[wiki/concepts/key-findings]].

| RQ | Question | Answer | Governing mechanism |
| :-- | :-- | :-- | :-- |
| RQ1 | latency under rising network-delay variance | flat in `n`; finality slows least for Casper FFG (×1.3, slot-bound), then PBFT (×1.9), then Snowman (×12–15) | round structure vs. `β` sequential polls |
| RQ2 | sustained throughput as `φ` rises to the threshold | three modes: PBFT holds then cliffs, Casper FFG ≈ `1 − φ`, Snowman starves earliest | quorum structure |
| RQ3 | communication overhead per committed unit | PBFT ≈ `2n`, Casper FFG ≈ `1.15n` (cheapest), Snowman ≈ `2Kβ` (≈ 14× PBFT at `n = 16`) | all-to-all / attestation vs. `K`-poll |
| RQ4 | which adversary causes liveness or safety loss | no protocol robust to all three; only PBFT's fork is measured, Snowman's safety rests on an unwitnessed analytical bound, Casper FFG alone is accountable by construction | each structural defense is also an exposure; safety differs in kind, not rank |
| RQ5 | consistent Pareto frontier; any dominance | a frontier exists; no family dominates across the measured axes plus the definitional safety ones | each family non-dominated on ≥ 1 axis |

## 6.2 Limitations

The findings hold within the following boundaries.

- **Cost model and workload.** The simulator charges network latency but no compute or bandwidth cost; this flatters cost and per-validator verdicts for PBFT and Casper FFG and does not affect message-count, liveness, or safety results. Goodput is reported below saturation (Poisson stream, zero conflict rate), so the flat-in-`n` result is a property of the unsaturated model rather than a claim about peak capacity.
- **Sub-production scale.** The sweep `n ∈ {4, …, 25}` is well below deployed scale; Snowman's rescaling (`K = min(20, n−1)`) collapses the subsampling mechanism at small `n`, so its measured performance may partly reflect a small-`n` artifact.
- **Family-vs-protocol generalization.** Each verdict applies to one representative implementation; a family-mate with a different structural choice can invert it: HotStuff's threshold-signature pipeline drops PBFT's `O(n²)` overhead to `O(n)` [[wiki/algorithms/pbft#communication-complexity]].
- **Snowman safety witnessed by bound.** Safety is reported through the analytical bound `ε ≤ (1 − α_c/K)^β` rather than a measured fork rate; the `n = 25` loss-resilience tie with PBFT rests on overlapping confidence intervals at a reduced seed count.
- **Permanent-loss bound.** Packet loss is modeled as permanent per-message drop with no transport retransmission; the loss-resilience curves are upper bounds on fragility rather than models of a retransmitting transport.
- **Leader-sparing coverage.** The sweep spares the view-0 primary; PBFT's liveness standing is established only against adversaries that leave its leader honest.

## 6.3 Future work

### 6.3.1 Production-optimized protocol variants

The overhead comparison evaluates each protocol at its specification-level message granularity. Production aggregation (BLS signatures for Casper FFG [8], threshold-signature collection at the leader for HotStuff [5]) changes this picture; a faithful extension would hold the optimization level constant across families or report both regimes.

### 6.3.2 Further directions

Several directions remain open beyond §6.3.1. Two would push the measurement itself further: a saturation-throughput capacity model that drives each protocol to a measured ceiling, and repetition at larger validator sets with bandwidth and retransmission modeled. A third tests a protocol change rather than the protocols as they stand, adding an adaptive-timeout enhancement with exponential backoff calibrated to observed round-trip time and evaluating it in a timeout-stressing regime. Snowman's analytical safety bound, reported here but never observed, calls for an empirical witness at weakened confidence depth. The harness could also be extended to a DAG-based family such as Narwhal+Tusk, together with its data-availability-withholding adversary.

## 6.4 Concluding remarks

This thesis contributes a controlled harness and the comparative reading it enables: a mechanism map of which structural commitment places each protocol on the performance-security frontier, rather than the naming of a single winner. No protocol dominates (§5.3); the same structural choice that holds one corner exposes another. The incidents that opened this study (§1.2), Ethereum's May 2023 finality stall [21] and the Solana and Cosmos halts, are separable consequences of those choices, not interchangeable faults to be engineered away by one better protocol.
