# [11] Danezis, Kokoris-Kogias, Sonnino & Spiegelman — Narwhal and Tusk: A DAG-based Mempool and Efficient BFT Consensus (2022)

**Category:** Protocol · **Venue:** EuroSys.

## Full citation

G. Danezis, L. Kokoris-Kogias, A. Sonnino, and A. Spiegelman, "Narwhal and
Tusk: A DAG-based Mempool and Efficient BFT Consensus," in *Proc. 17th
European Conference on Computer Systems (EuroSys)*, 2022, pp. 34–50.

## Key takeaways

1. **Decouples data availability from ordering.** Narwhal is a
   DAG-structured mempool ensuring every transaction is reliably
   replicated and causally certified *before* consensus needs to order
   it; Tusk is a zero-message-overhead consensus layer that runs on top
   of the DAG. This separation is the family-defining idea shared by
   [12], [13] — see [[algorithms/dag-based]] §decoupling.
2. **`O(n)` per-block messages, async-safe.** Narwhal round certificates
   are `O(n)` rather than PBFT's `O(n²)`; Tusk picks anchor vertices
   from the already-certified DAG and derives a total order from the
   causal graph. Safety holds even under full asynchrony; liveness
   under partial sync or eventually-synchronous periods.
3. **`3f+1` threshold inherited.** Same Lamport–Shostak–Pease bound [1]
   as PBFT and PoS-finality; the DAG-based family does not relax the
   safety threshold, only the message pattern and storage model.
4. **Reported `~140 ktps` throughput on WAN.** The headline number
   motivating the family; must be cited as *reported*, not measured,
   pending independent replication. The figure depends on batching,
   workload (TLS-stripped plain transfers), and WAN topology — per
   [[concepts/problem-statement]] §heterogeneous-harnesses this is a
   typical comparability problem the thesis's simulator addresses.
5. **Reference implementation target for the DAG module.** The thesis's
   DAG-based simulator module (task T38 if the algorithm is implemented
   in Week 7) targets simplified Narwhal + Tusk — the clearest two-layer
   decomposition in the family; Bullshark [12] and Mysticeti [13] are
   descriptive context only.

## Limitations / gaps

WAN evaluation is deployment-specific; throughput numbers are workload
and batch-size sensitive. Per-node storage grows with DAG depth, trading
message complexity for storage — the simulator must surface this as an
explicit metric (task T42 communication + storage overhead).

## Links to affected wiki pages

- [[algorithms/dag-based]] — primary consumer; Narwhal + Tusk is the
  reference protocol.
- [[concepts/consensus-families]] — DAG-based family anchor.
- [[concepts/quorum-arithmetic]] — `3f+1` inherited.
- [[concepts/synchrony-models]] — async-safe, partial-sync-live.
- [[concepts/problem-statement]] — reported-throughput comparability gap.
