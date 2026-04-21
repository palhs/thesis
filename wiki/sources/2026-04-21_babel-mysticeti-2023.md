# [13] Babel, Chursin, Danezis, Kokoris-Kogias & Sonnino — Mysticeti: Reaching the Latency Limits with Uncertified DAGs (2023)

**Category:** Protocol · **Venue:** arXiv:2310.14821 (deployed in Sui).

## Full citation

K. Babel, A. Chursin, G. Danezis, L. Kokoris-Kogias, and A. Sonnino,
"Mysticeti: Reaching the Latency Limits with Uncertified DAGs," arXiv
preprint arXiv:2310.14821, 2023.

## Key takeaways

1. **Uncertified DAG — no round certificates.** Unlike Narwhal+Tusk [11]
   and Bullshark [12], Mysticeti does not require each DAG round to
   collect a `2f+1` certificate before the next round begins. Removing
   this serialisation hits the `3`-round BFT latency lower bound derived
   from [1]–[3] under partial synchrony.
2. **Reported `> 200 ktps` throughput; `~0.5 s` WAN commit latency.**
   Current state-of-the-art numbers in the family; used as an *upper
   bound* reference in Ch. 5's enhancement chapter, not as a target the
   simulator is expected to reproduce. Numbers are vendor-reported (Mysten
   Labs) from the Sui production deployment.
3. **Production deployment anchor.** Live on Sui's mainnet. Gives the
   family an operational data point that complements the published
   arXiv evaluation — but also means the numbers are production-centric
   and hardware-specific, so they must be cited with qualifications.
4. **Same `3f+1` threshold, same DAG decoupling.** No weakening of
   safety or the data-availability / ordering separation established
   by [11]. Mysticeti is a latency optimisation on top of the same
   architectural spine.
5. **Out of scope for simulator implementation.** The thesis's DAG
   module targets simplified Narwhal + Tusk (per [[algorithms/dag-based]]
   §simulator-mapping); Mysticeti is retained as descriptive context
   for the upper-bound comparison and for Ch. 5's enhancement discussion
   (task T60).

## Limitations / gaps

Independent replication of the `200 ktps` / `0.5 s` numbers is limited;
primary source is Mysten Labs telemetry and the arXiv paper. Uncertified
DAG safety proof is newer and has received less peer scrutiny than the
certified-DAG lineage. Results are production-workload-specific.

## Links to affected wiki pages

- [[algorithms/dag-based]] — primary consumer; Mysticeti variant.
- [[concepts/consensus-families]] — DAG-based family.
- [[concepts/quorum-arithmetic]] — `3f+1` inherited.
- [[concepts/synchrony-models]] — reaches the `3`-round partial-sync
  lower bound.
- [[concepts/problem-statement]] — vendor-reported-number comparability
  concern.
