# Wiki log

> Append-only chronological record. Format:
> ## [YYYY-MM-DD] <type> | task <N> — <title>

## [2026-04-20] sync | task S0 — Import BFT Foundation concepts
- role: Researcher
- touched: `wiki/concepts/byzantine-generals.md`, `wiki/concepts/flp-impossibility.md`, `wiki/concepts/cap-theorem.md`, `wiki/concepts/consensus-properties.md`, `wiki/concepts/synchrony-models.md`, `wiki/concepts/fault-model.md`, `wiki/concepts/quorum-arithmetic.md`, `wiki/concepts/consensus-families.md`, `wiki/index.md`, `TASKS.md`
- notes: Decomposed `resources/00_BFT_Foundation.md` into 8 concept pages. Skipped §5's operational adversary list (deferred to T18, `wiki/concepts/adversary-model.md`) and §9–10 implications (deferred to T14–T20). `TODO(cite)` markers left on BGP/FLP/CAP references pending bibliographic confirmation. Foundation pages are prerequisites for S1–S4 algorithm ingests: they provide link targets for `partial synchrony`, `3f+1`, `Byzantine faults`, and `consensus families`.

## [2026-04-21] ingest | task S2 — Import PoS finality deep-dive notes
- role: Researcher
- touched: `wiki/algorithms/pos.md`, `wiki/concepts/consensus-families.md`, `wiki/index.md`, `TASKS.md`
- notes: Imported `resources/02_PoS_Finality_DeepDive.md` into `wiki/algorithms/pos.md` (228 lines), mirroring the structural spine of `wiki/algorithms/pbft.md` (on `task/S1-pbft-deepdive`, still In Review): family scope → assumptions → two-round justify→finalise → slashing → accountable safety → delay/adversarial behaviour → simulator mapping → weaknesses. All T3 outcomes covered: validator voting, attestation, supermajority finality, slashing. Resolved the `TODO(link)` in `consensus-families.md` that was parked pending S2. Inline citations to Casper FFG [1] and Gasper [2]; dedicated `wiki/sources/` pages deferred to T8. Branched fresh from master (`task/S2-pos-finality`); stale `task/S2-import-pos-notes` branch left in place for later cleanup.
