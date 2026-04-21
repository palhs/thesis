# [12] Spiegelman, Giridharan, Sonnino & Kokoris-Kogias — Bullshark: DAG BFT Protocols Made Practical (2022)

**Category:** Protocol · **Venue:** CCS.

## Full citation

A. Spiegelman, N. Giridharan, A. Sonnino, and L. Kokoris-Kogias,
"Bullshark: DAG BFT Protocols Made Practical," in *Proc. ACM Conf.
Computer and Communications Security (CCS)*, 2022, pp. 2705–2718.

## Key takeaways

1. **Partially-synchronous fast path with async fallback.** Under
   partial synchrony (the common case) Bullshark commits anchors in
   `2` DAG rounds — cutting Narwhal+Tusk's [11] latency roughly in
   half. Under asynchrony it falls back to a slower but still-safe
   path. This dual-mode structure is the pattern every later DAG BFT
   (including Mysticeti [13]) inherits.
2. **Same DAG mempool + anchor-ordering structure as [11].** Bullshark
   is architecturally a refinement, not a replacement — it runs on top
   of the Narwhal DAG mempool and only changes the anchor-commit rule.
   The separation of data availability from ordering is preserved. See
   [[algorithms/dag-based]] §family-table.
3. **Implementation simplicity.** The canonical Bullshark implementation
   is ~200 LoC layered on the Narwhal codebase. This simplicity is
   intrinsic to the paper's title claim (*Made Practical*) and is a
   direct reason to pick it over [11] as a simulator target — except
   that the thesis picks the older [11] for its cleaner two-layer
   pedagogical decomposition.
4. **Same `3f+1` threshold under partial synchrony.** No weakening of
   the safety or quorum bound from [1], [3]. Bullshark optimises latency
   and implementation complexity, not cryptographic or threshold
   assumptions.
5. **Fast-path/slow-path distinction informs the simulator.** Even
   though Bullshark itself is not implemented, the simulator's DAG
   module must support a fast-path/slow-path model to produce
   meaningful delay-sensitivity plots — a design choice that lands in
   [[algorithms/dag-based]] §simulator-mapping.

## Limitations / gaps

Formal safety proof for the asynchronous fallback is sketched but not
fully peer-reviewed in the main paper; details in accompanying tech
reports. Evaluation under adversarial validators (equivocation, delay)
is limited — one of the gaps the thesis simulator addresses (tasks
T51–T53).

## Links to affected wiki pages

- [[algorithms/dag-based]] — primary consumer; Bullshark is a
  descriptive variant.
- [[concepts/consensus-families]] — DAG-based family.
- [[concepts/synchrony-models]] — partial-sync fast path, async fallback.
- [[concepts/quorum-arithmetic]] — `3f+1` inherited.
