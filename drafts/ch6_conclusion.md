# Chapter 6 — Conclusions

`TODO(W12)` — This chapter is a stub. Sections 6.1 and 6.2 are written once the
delay (§4.3) and adversarial (§4.4) sweeps and the Chapter 5 Pareto synthesis
are complete. Section 6.3 is seeded ahead of that schedule to record a
direction for further work identified during the Week-8 baseline analysis.

## 6.1 Summary of findings

`TODO(W12)` — synthesis of RQ1–RQ5 once Chapters 4 and 5 are complete.

## 6.2 Limitations

`TODO(W12)` — model boundaries (the latency-only baseline, the absence of a
capacity model, the parameter rescaling at small `n`), to be drawn together
from the per-chapter caveats.

## 6.3 Directions for further work

### 6.3.1 Production-optimized protocol variants

The communication-overhead comparison of §4.2.4 evaluates each protocol at the
message granularity of its original specification: classical PBFT with
all-to-all prepare and commit phases, and Casper FFG with individually signed
attestations counted toward a supermajority
[[wiki/algorithms/pos#communication-complexity]]. Production deployments of both
families reduce this cost through signature aggregation. The Ethereum beacon
chain aggregates committee attestations with BLS signatures, which collapses
Casper FFG's per-epoch attestation cost from the `O(n²)` of propagated
individual votes to `O(n)` [[wiki/algorithms/pos#communication-complexity]];
HotStuff achieves the analogous reduction for the PBFT family, replacing the
quadratic vote phases with threshold-signature collection at the leader to
obtain linear normal-case and view-change communication
[[wiki/algorithms/pbft#communication-complexity]]. Modeling these aggregated
variants is the most direct extension of the present communication-overhead
results, and would establish whether the per-unit cost ordering observed at the
as-specified granularity survives at the granularity of deployed systems.

This extension carries a methodological requirement that constrains how it must
be undertaken. Signature aggregation is a property of a protocol family's
signature scheme rather than of an individual protocol; introducing it for one
family while leaving another at its un-aggregated specification would compare
implementations at different levels of optimization and would therefore
misstate the per-unit cost contrast that answers RQ3
[[wiki/concepts/research-questions]]. A faithful extension consequently either
models all signature-based families at their production-optimized message
granularity — aggregated Casper FFG against a HotStuff-style PBFT — or reports
the as-specified and the aggregated regimes side by side, so that the level of
optimization is held constant across the comparison. The decision between these
two framings is a methodological one and is reserved for the supervisor. An
implementation plan for the Casper FFG side — the aggregation topology, the
message-counting convention, and the comparability decision described here — is
recorded as a kickoff specification in the project repository.

### 6.3.2 Further directions

`TODO(W12)` — additional directions to be consolidated at submission, including
the completion of the Narwhal+Tusk implementation (reserved as T38.1), a
saturation-throughput capacity model that would replace the flat-goodput
baseline with a measured ceiling [[wiki/concepts/output-format]], and the
adaptive-timeout enhancement evaluated in Chapter 5.
