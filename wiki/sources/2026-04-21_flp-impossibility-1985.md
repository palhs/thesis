# [2] Fischer, Lynch & Paterson — Impossibility of Distributed Consensus with One Faulty Process (1985)

**Category:** Foundational · **Venue:** Journal of the ACM.

## Full citation

M. J. Fischer, N. A. Lynch, and M. S. Paterson, "Impossibility of
Distributed Consensus with One Faulty Process," *Journal of the ACM*,
vol. 32, no. 2, pp. 374–382, 1985.

## Key takeaways

1. **The FLP impossibility result.** No deterministic asynchronous
   consensus protocol can guarantee agreement, termination, and
   non-triviality when even a single process may crash. The proof
   proceeds by a bivalency argument showing an adversary can always
   extend a bivalent configuration indefinitely.
2. **Async + deterministic + fault-tolerance is the forbidden triangle.**
   Any real-world protocol must relax one corner. This is the single
   most important framing result for the thesis — see
   [[concepts/flp-impossibility]] for the breakdown of which corner each
   family relaxes.
3. **Relaxations used by the four families.**
   *(i)* [[algorithms/pbft]] and [[algorithms/pos]] weaken asynchrony via
   partial synchrony ([3]).
   *(ii)* [[algorithms/avalanche]] weakens determinism via randomised
   subsampling and accepts probabilistic finality `1 − ε`.
   *(iii)* [[algorithms/dag-based]] (Narwhal+Tusk, Bullshark) combine
   deterministic ordering with a partially-synchronous fast path and an
   asynchronous fallback for liveness under adversarial delay.
4. **Crash faults, not Byzantine.** The impossibility holds even in the
   weakest fault model. BFT families therefore cannot evade FLP — they
   only work around it by adding timing assumptions, randomness, or
   economic penalties (slashing on [[algorithms/pos]]).
5. **Bridges safety and liveness.** FLP makes explicit that safety and
   liveness cannot both be guaranteed under async with faults — a
   practical protocol must choose which it will sacrifice during a
   partition. This frames the safety-vs-liveness tension summarised in
   [[concepts/consensus-properties]] and
   [[concepts/cap-theorem]].

## Limitations / gaps

Theoretical impossibility only; no constructive alternative. The result
says what cannot be done, not how to build a working system. Its practical
bite is bounded by how adversarial the real network actually is.

## Links to affected wiki pages

- [[concepts/flp-impossibility]] — primary consumer; full statement and
  proof sketch.
- [[concepts/synchrony-models]] — FLP holds in async; partial synchrony
  sidesteps it.
- [[concepts/consensus-properties]] — safety/liveness tension.
- [[concepts/cap-theorem]] — CAP's partition corner follows from FLP.
- [[concepts/problem-statement]] — motivates the "why four families exist"
  framing.
- [[algorithms/avalanche]] — randomisation relaxation.
- [[algorithms/dag-based]] — async-safe designs that tolerate delay at
  the cost of liveness guarantees.
