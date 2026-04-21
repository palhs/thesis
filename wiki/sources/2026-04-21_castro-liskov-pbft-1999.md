# [4] Castro & Liskov — Practical Byzantine Fault Tolerance (1999)

**Category:** Protocol · **Venue:** OSDI.

## Full citation

M. Castro and B. Liskov, "Practical Byzantine Fault Tolerance," in
*Proc. 3rd USENIX Symp. Operating Systems Design and Implementation
(OSDI)*, 1999, pp. 173–186.

## Key takeaways

1. **First practical BFT state-machine replication.** Prior BFT results
   [1], [3] were theoretical; Castro–Liskov produced a working system with
   LAN-realistic latency (few ms per operation) under `n = 4` (`f = 1`).
   The protocol made BFT practical rather than merely possible — this is
   the canonical citation for the PBFT family in the thesis.
2. **Three-phase commit under partial synchrony.**
   **pre-prepare → prepare → commit**, each phase gathering a quorum of
   `2f+1` matching votes. Safety is maintained across asynchrony; liveness
   depends on partial synchrony in the sense of [3]. See
   [[algorithms/pbft]] for the full state-machine.
3. **View change as liveness recovery.** When the primary is suspected
   faulty, replicas trigger a view change, exchange their local state,
   and elect a new primary. This is the mechanism the simulator must
   model to probe delay/adversarial sensitivity; `O(n³)` worst-case
   message complexity is the primary cost.
4. **`3f+1` replicas; `2f+1` quorum.** Exactly the Lamport–Shostak–Pease
   bound [1] under partial sync from [3]. Inherited by HotStuff [5],
   Tendermint [6], Casper FFG [7], and the DAG-based family [11]–[13].
5. **`O(n²)` normal-path messages.** Every replica multicasts to every
   other replica in prepare and commit. This quadratic cost is the
   scalability bottleneck that HotStuff [5] later linearises via
   threshold signatures.

## Limitations / gaps

LAN-scale evaluation only (`n ≤ 4`); no WAN measurements, no adversarial
delay injection, no packet loss. The empirical gap this thesis's simulator
(tasks T41–T48) is explicitly designed to close.

## Links to affected wiki pages

- [[algorithms/pbft]] — primary consumer; Castro–Liskov is the reference
  protocol.
- [[concepts/quorum-arithmetic]] — `2f+1` intersection argument.
- [[concepts/synchrony-models]] — partial synchrony inherited from [3].
- [[concepts/fault-model]] — Byzantine faults, crash included.
- [[concepts/consensus-families]] — classical-BFT family anchor.
- [[concepts/problem-statement]] — LAN-to-WAN generalisation gap.
