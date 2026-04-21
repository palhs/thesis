# [17] Gervais et al. — On the Security and Performance of Proof of Work Blockchains (2016)

**Category:** Empirical methodology · **Venue:** ACM CCS 2016.

## Full citation

A. Gervais, G. O. Karame, K. Wüst, V. Glykantzis, H. Ritzdorf, and
S. Capkun, "On the Security and Performance of Proof of Work
Blockchains," in *Proc. ACM Conf. Computer and Communications Security
(CCS)*, 2016, pp. 3–16.

## Key takeaways

1. **Methodological precedent for this thesis.** Builds a quantitative
   simulation framework for PoW security and performance, instruments it
   for throughput, stale-block rate, and selfish-mining success, and
   sweeps block size and propagation delay as independent variables.
   This is the exact approach — simulator + metric instrumentation +
   parameter sweep — that the thesis applies to BFT/PoS/DAG/Avalanche
   families. Cited on [[concepts/problem-statement]] §method as the
   methodological precedent.
2. **Independent-variable design.** Block size and propagation delay
   are treated as dials. The thesis reuses the same design pattern,
   substituting validator count and message delay as the primary dials
   for BFT-family simulation — see [[concepts/experiment-matrix]] (T19).
3. **Security as a measurable output.** Operationalises "security" as
   the probability of double-spend success and selfish-mining
   profitability under varying adversary stake and network conditions.
   The thesis adopts the same framing — "security" is a measured
   success-rate / fork-rate under adversarial inputs — see
   [[concepts/evaluation-metrics]] §reliability and
   [[concepts/adversary-model]] (T18).
4. **PoW scope, not BFT.** The specific metrics (stale-block rate,
   selfish-mining) are PoW-specific and do not transfer. What transfers
   is the methodology: parameterise, simulate, measure, compare. The
   thesis does not cite [17] for any BFT-family performance number —
   those come from [4]–[13].
5. **Reproducibility standard.** Publishes the simulation framework and
   parameters, enabling reproducibility — a standard this thesis aims
   to match via the T27 reproducibility harness and the
   experiment-page-per-run discipline in `docs/wiki-spec.md`.

## Limitations / gaps

PoW-specific scope; no coverage of BFT, PoS, DAG, or Avalanche families.
The simulator calibration assumes specific propagation-delay
distributions from the Bitcoin network, which do not generalise to
small-validator permissioned-BFT deployments. The thesis borrows the
methodology, not the numerical results.

## Links to affected wiki pages

- [[concepts/problem-statement]] — primary consumer; methodological
  precedent for the simulation-based comparative approach.
- [[concepts/evaluation-metrics]] — precedent for the security-as-
  measured-output framing.
- [[concepts/annotated-bibliography]] — the single empirical-methodology
  entry in the consolidated bibliography.
