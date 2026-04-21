# Wiki log

> Append-only chronological record. Format:
> ## [YYYY-MM-DD] <type> | task <N> — <title>

## [2026-04-20] sync | task S0 — Import BFT Foundation concepts
- role: Researcher
- touched: `wiki/concepts/byzantine-generals.md`, `wiki/concepts/flp-impossibility.md`, `wiki/concepts/cap-theorem.md`, `wiki/concepts/consensus-properties.md`, `wiki/concepts/synchrony-models.md`, `wiki/concepts/fault-model.md`, `wiki/concepts/quorum-arithmetic.md`, `wiki/concepts/consensus-families.md`, `wiki/index.md`, `TASKS.md`
- notes: Decomposed `resources/00_BFT_Foundation.md` into 8 concept pages. Skipped §5's operational adversary list (deferred to T18, `wiki/concepts/adversary-model.md`) and §9–10 implications (deferred to T14–T20). `TODO(cite)` markers left on BGP/FLP/CAP references pending bibliographic confirmation. Foundation pages are prerequisites for S1–S4 algorithm ingests: they provide link targets for `partial synchrony`, `3f+1`, `Byzantine faults`, and `consensus families`.

## [2026-04-21] ingest | task S1 — Import PBFT deep-dive notes
- role: Researcher
- touched: `wiki/algorithms/pbft.md`, `wiki/index.md`, `TASKS.md`
- notes: Ingested `resources/01_PBFT_DeepDive.md` into a single family page covering PBFT, HotStuff, and Tendermint as variants of the same skeleton. All T2 outcomes covered (three-phase commit, `3f+1`, view change). Concept-layer backlinks point to existing pages ([[concepts/quorum-arithmetic]], [[concepts/synchrony-models]], [[concepts/fault-model]], [[concepts/byzantine-generals]], [[concepts/consensus-properties]], [[concepts/consensus-families]]); no concept pages modified. Citations [1]–[3] carried inline pending dedicated `wiki/sources/` pages under T8. Scope decision: only classical PBFT will be simulated — HotStuff and Tendermint are descriptive family context only, so §Simulator mapping lists just two knobs (view-change timeout, Byzantine fraction). Threshold-break wording tightened: the failure mode at `f ≥ n/3` is an unvetoed intersection (equivocators in the ≥`f+1` overlap voting both ways), not disjoint quorums — this fixes how the T55 safety-violation detector must be designed.
## [2026-04-21] ingest | task S2 — Import PoS finality deep-dive notes
- role: Researcher
- touched: `wiki/algorithms/pos.md`, `wiki/concepts/consensus-families.md`, `wiki/index.md`, `TASKS.md`
- notes: Imported `resources/02_PoS_Finality_DeepDive.md` into `wiki/algorithms/pos.md` (228 lines), mirroring the structural spine of `wiki/algorithms/pbft.md` (on `task/S1-pbft-deepdive`, still In Review): family scope → assumptions → two-round justify→finalise → slashing → accountable safety → delay/adversarial behaviour → simulator mapping → weaknesses. All T3 outcomes covered: validator voting, attestation, supermajority finality, slashing. Resolved the `TODO(link)` in `consensus-families.md` that was parked pending S2. Inline citations to Casper FFG [1] and Gasper [2]; dedicated `wiki/sources/` pages deferred to T8. Branched fresh from master (`task/S2-pos-finality`); stale `task/S2-import-pos-notes` branch left in place for later cleanup.

## [2026-04-21] ingest | task S3 — Import Avalanche deep-dive notes
- role: Researcher
- touched: `wiki/algorithms/avalanche.md`, `wiki/index.md`, `TASKS.md`
- notes: Imported `resources/03_Avalanche_DeepDive.md` into `wiki/algorithms/avalanche.md` (286 lines), mirroring the spine of `wiki/algorithms/pos.md`: family scope → assumptions → subsampling cascade (Slush → Snowflake → Snowball → Avalanche → Snowman) → probabilistic safety bound → delay/adversarial behaviour → parameters + comms complexity → simulator mapping → weaknesses. All T4 outcomes covered: Snowball/Snowflake, subsampled voting, convergence. Source [3] is live Ava Labs documentation (accessed Apr 2026) and exposes the `α_p` vs `α_c` production split that the original paper [1] did not; [2] tightens worst-case async bounds beyond [1]'s informal treatment — flagged as a weakness to foreground. `consensus-families.md` did not need updating: `[[algorithms/avalanche]]` wikilinks were already in place from S0. Simulator target is Snowman (linearised production variant), not DAG-Avalanche. Inline citations to [1]–[3]; dedicated `wiki/sources/` pages deferred to T8.
