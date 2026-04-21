# [3] Dwork, Lynch & Stockmeyer — Consensus in the Presence of Partial Synchrony (1988)

**Category:** Foundational · **Venue:** Journal of the ACM.

## Full citation

C. Dwork, N. Lynch, and L. Stockmeyer, "Consensus in the Presence of
Partial Synchrony," *Journal of the ACM*, vol. 35, no. 2, pp. 288–323,
1988.

## Key takeaways

1. **Defines partial synchrony.** Two formulations, both weaker than
   synchrony and stronger than asynchrony:
   *(a)* message delay is bounded by an unknown `Δ`, or
   *(b)* `Δ` is known but holds only after an unknown Global Stabilisation
   Time (GST). Both admit consensus; neither requires the protocol to
   know when "synchrony kicks in."
2. **Matches the real Internet.** Real networks behave synchronously
   most of the time but with unpredictable delay spikes. Partial sync
   captures this without the unrealistic tight bounds of the synchronous
   model. Catalogued in [[concepts/synchrony-models]].
3. **Threshold result: `f < n/3` under partial sync with Byzantine
   faults.** Same `3f+1` bound as synchronous BGP [1], but now under a
   more realistic network assumption. This is the timing assumption
   adopted by [[algorithms/pbft]] (Castro–Liskov, HotStuff, Tendermint)
   and [[algorithms/pos]] (Casper FFG).
4. **Separates safety from liveness timing.** Safety holds always;
   liveness holds only after GST. This is *the* mental model for modern
   BFT protocols — they preserve safety through arbitrary async periods
   and recover progress once network conditions permit (via view change
   in PBFT; leader rotation in Tendermint; asynchronous fallback in
   Bullshark / Mysticeti, [[algorithms/dag-based]]).
5. **Motivates timeouts and leader rotation.** The protocol must detect
   "we are in the async phase" to swap leaders or trigger fallback —
   which is exactly the mechanism PBFT's view change, HotStuff's pacemaker,
   and Tendermint's round-robin implement. Timeout calibration is the
   enhancement target in task T57 (adaptive timeout).

## Limitations / gaps

Model rather than system; no real-latency/throughput measurements. The
GST formulation provides no guidance on how long the async phase can
last in practice — a calibration concern the simulator is specifically
designed to probe (task T46–T48 network delay experiments).

## Links to affected wiki pages

- [[concepts/synchrony-models]] — primary consumer; partial-sync
  definitions.
- [[concepts/flp-impossibility]] — partial sync is the chosen relaxation
  for the PBFT and PoS families.
- [[concepts/quorum-arithmetic]] — same `3f+1` bound under partial sync.
- [[algorithms/pbft]] — all three variants assume partial synchrony.
- [[algorithms/pos]] — Casper FFG's finality argument assumes partial
  synchrony for liveness.
- [[algorithms/dag-based]] — Bullshark's fast path is partially
  synchronous; asynchronous fallback takes over otherwise.
