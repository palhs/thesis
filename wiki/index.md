# Wiki index

> Auto-maintained catalog of all wiki pages. One line per page.
> Format: `- [[path/to/page]] — one-line summary`
> Keep under ~500 lines. Revisit retrieval strategy if it grows past that.

## Algorithms

- [[algorithms/pbft]] — PBFT-family (Castro–Liskov, HotStuff, Tendermint): three-phase commit under partial synchrony; `3f+1` replicas; view change as liveness recovery.
- [[algorithms/pos]] — PoS-finality (Casper FFG, Gasper): BFT finality gadget over a chain; two-round justify→finalise at epoch granularity; stake-weighted `3f+1` with slashing-based accountable safety.
- [[algorithms/avalanche]] — Avalanche family (Slush → Snowflake → Snowball → DAG-Avalanche; production: Snowman): BFT via repeated random `k`-peer subsampling; probabilistic finality `1 − ε` with `ε < (1 − α_c/K)^β`; per-validator cost `O(K·β)` independent of `n`.
- [[algorithms/dag-based]] — DAG-based BFT (Narwhal+Tusk, Bullshark, Mysticeti): decouple data availability (DAG mempool) from ordering (anchor commit over DAG); `3f+1` threshold, async-safe, `O(n)` per-block messages, trades messages for per-node storage.

## Concepts

- [[concepts/consensus-overview]] — Introductory framing: what a blockchain is, how blocks are created, why consensus is needed, why it is hard. Upstream of all other Concepts pages; recommended first read.
- [[concepts/byzantine-generals]] — Lamport–Shostak–Pease BGP formulation; `n ≥ 3f+1` solvability bound; origin of the two-thirds supermajority.
- [[concepts/flp-impossibility]] — Fischer–Lynch–Paterson: no deterministic async consensus with even one crash fault; motivates partial-sync, randomization, and layered relaxations.
- [[concepts/cap-theorem]] — Under partition, blockchains choose Consistency (PBFT, PoS-finality) or Availability (Avalanche); `P` is non-negotiable.
- [[concepts/consensus-properties]] — The four properties (Agreement, Validity, Termination, Integrity) and the safety/liveness tension.
- [[concepts/synchrony-models]] — Synchronous / partial-sync / async / probabilistic; which family assumes which.
- [[concepts/fault-model]] — Crash / omission / Byzantine classes; static vs adaptive adversary timing. Theoretical taxonomy only; operational simulator adversary is T18.
- [[concepts/quorum-arithmetic]] — Derivation of `n ≥ 3f+1` from safety (quorum intersection) + liveness (unresponsive tolerance) constraints. Applies to 3 of 4 families.
- [[concepts/consensus-families]] — Design-space table + BGP propagation tree; one-line framing per family. Central navigation hub for comparative work.
- [[concepts/problem-statement]] — Thesis title, the three-gap motivation, four objectives, scope (in/out), assumptions/limitations, success criteria, finalized status (T13, W2 KPI). Entry point for Chapter 1 framing.
- [[concepts/research-questions]] — RQ1–RQ5 with primary metrics and independent variables; maps each RQ to the family axis it stresses and to the downstream tasks that consume it.
- [[concepts/annotated-bibliography]] — Consolidated IEEE bibliography `[1]–[18]`; citation policy (unified numbering across chapters; surveys for framing only); resolver to `wiki/sources/` pages.
- [[concepts/evaluation-metrics]] — Unified metric schema (latency / throughput / overhead / reliability); reported literature ranges; adversarial and delay axes; metric → RQ map; simulator instrumentation contract. Canonical *definitions*; family-agnostic.
- [[concepts/metric-reconciliation]] — Companion to `evaluation-metrics`: per-protocol *formulas* against the four-protocol scope (PBFT, Casper FFG, Snowman, Narwhal+Tusk). Reconciles linear-chain vs DAG output, per-block / per-epoch / per-anchor-batch finality, Narwhal mempool/consensus message split, and Snowman parameter rescaling at thesis-scale `n`. Pins the T40 CSV column set and the simulator-scale calibration defaults (with per-RQ sensitivity-sweep policy) that defend cross-protocol verdicts against knob-engineering.
- [[concepts/node-model]] — Validator (`Node`) design contract: two-layer commitment (shared lifecycle + per-protocol FSMs); inbound (`on_message` / `on_timer`) + outbound (`send` / `broadcast` / `set_timer` / `emit` / `rng`) APIs; determinism (T27 hook); T18 adversary attachment surface; reference sketch + open-to-revision discipline.
- [[concepts/network-model]] — Network (`Network`) design contract: latency-only full-mesh delivery; T14 seam (`Message` envelope + `NodeId → endpoint` registry); at-most-once delivery, no order guarantee, no retries; outbound API integration; honest-infrastructure adversary boundary; reference sketch; open-to-revision register spanning both halves of T15.
- [[concepts/network-model-phases]] — Companion to `network-model`: phase-driven runtime mechanics (delay distributions, drop model, partition expression, phase timeline rules) plus the network-level determinism contract (network-scoped RNG, sampling order, forbidden surfaces). Split per `docs/wiki-spec.md` § Page size.
- [[concepts/message-types]] — Wire-level message catalog filling the `Message.type` / `payload` slots left opaque by `node-model` §6 and `network-model` §3.1. Per-protocol tables (PBFT: 5 types incl. `VIEW-CHANGE` / `NEW-VIEW`; Casper FFG: `BLOCK-PROPOSAL`, `ATTESTATION`, separate `SLASHING-EVIDENCE` broadcast; Snowman: `BLOCK-ANNOUNCEMENT` + unicast `QUERY` / `QUERY-RESPONSE`; Narwhal+Tusk: `HEADER`, `HEADER-VOTE`, `CERTIFICATE`; Tusk anchor commit = zero messages) declaring tag, recipient discipline, payload schema, byte budget, `node-model` §4 FSM transition triggered, and `{mempool,consensus}_{msgs,bytes}_per_acu` column fed.
- [[concepts/simulation-design]] — Discrete-event scheduler (`Scheduler`) design contract closing the W3 set; main page (the contract surface). Pins five structural decisions (custom min-heap, `(t, node_id, seq)` tie-break, typed event classes `Delivery` / `TimerFire` / `PhaseAdvance`, lazy-tombstone cancellation, three OR-composed stop conditions). Specifies state (heap + registry + per-Node seq counters + virtual clock + event_sink), public API (`schedule`, `set_timer`, `cancel_timer`, `bind`, `run` → `RunResult`), and six-phase harness bootstrap (split-bind invariant: scheduler owns timer/emit, network owns send/broadcast). Lands two upstream Revisions: [[concepts/node-model]] §6 (`Node.start(t)`) and [[concepts/network-model]] §5 (`Network.start()`). Visual contract: [[diagrams/scheduler/bootstrap]], [[diagrams/scheduler/event-enqueue]], [[diagrams/scheduler/event-dispatch]], [[diagrams/scheduler/timer-lifecycle]], [[diagrams/scheduler/constraints]] under [[diagrams/index]].
- [[concepts/simulation-design-runtime]] — Companion to `simulation-design`; the runtime obligations (determinism contract — seven mechanisms forcing byte-identical replay; adversary boundary — no scheduler-layer slot, justification; failure modes — four fail-fast validation gates), the illustrative Python reference sketch (~100 LoC) T21 implements against, and the consolidated open-to-revision register spanning both halves. Split per `docs/wiki-spec.md` § Page size; same precedent as `network-model` / `network-model-phases`.
- [[concepts/adversary-model]] — Adversary catalog (T18). Four-row generic capability × protocol matrix (`delay-emission`, `withhold-participation`, `equivocate-vote`, `disrupt-leader`) with one structural `N/A` (Snowman × `disrupt-leader`, no leader role) and one noted reduction (Snowman × `equivocate-vote` → lying responder, no inter-message intersection); plus three protocol-specific surfaces (Snowman colluding sub-sampler [9], Narwhal+Tusk data-availability withholding [11], Casper FFG slashable-equivocation refinements [7]). 18 valid `(adversary, protocol)` pairs — 12 exercised by T51–T53 (§§3–5), 6 (§6 / §7) catalogued design space only. Owns binding semantics; `node-model` §9 retains the attachment surface.
- [[concepts/adversary-model-runtime]] — Runtime companion to `adversary-model`. Pins per-protocol natural intensity unit (replicas for PBFT/Narwhal+Tusk, stake for Casper, validators for Snowman); uniform effect schema mapping capabilities to expected CSV column perturbations (with §6 register listing 15 column names not yet defined upstream — T40 follow-up); `AdversaryProfile` reference sketch (`typing.Protocol` + 7 frozen dataclasses, illustrative non-binding); T27 determinism interaction (per-Node RNG seeding + colluding-group seed derivation); 9-item open-to-revision register. Split per `docs/wiki-spec.md` § Page size; same precedent as `network-model` / `network-model-phases`.
- [[concepts/experiment-matrix]] — Experiment parameter space (T19): the six axes (validator-set size `n`, network timeline, adversary, protocol knobs, workload, seeds), three run families (A Scaling / B Delay / C Adversarial) each sweeping one axis, the per-RQ design map, the FFG `slot_duration`↔`E[delay]` coherence rule (FFG slot rescales with the delay regime — the analogue of Snowman `K`-rescaling), committed `workload_*` defaults, the peak-throughput ramp grid, and the seed/replication policy (common random numbers across protocols). Design half; enumerated catalog in the companion.
- [[concepts/experiment-matrix-runs]] — Run-catalog companion to `experiment-matrix`: the network-timeline parameter tables with the per-timeline FFG `slot_duration` pairing, the 12 covered adversary (capability × protocol) triples with intensity grids (T51/T52/T53), the 6 uncovered catalog surfaces, and the ~2,700-run combinatorial budget. Split per `docs/wiki-spec.md` § Page size.
- [[concepts/system-design]] — System synthesis (T20): how the W3 design contracts (node / network / message / scheduler / adversary models) compose into one running system. Component-layering table + the macro runtime view — one experiment-matrix cell to one `results.csv` row, six phases (init → workload → run loop → stop → flush → output). Diagram: [[diagrams/runtime/macro]]. Companion: `system-design-protocols`.
- [[concepts/system-design-protocols]] — Companion to `system-design`: the four protocols' main loops as event-handler pseudocode (PBFT three-phase commit, Casper FFG justify→finalise, Snowman `K`-peer poll loop, Narwhal+Tusk DAG round + zero-message anchor commit), each non-binding and paired with a Swimlanes.io diagram under `diagrams/protocols/`; carries the open-to-revision register spanning both pages.

## Sources

- [[sources/2026-04-21_lamport-shostak-pease-bgp-1982]] — [1] BGP formulation; deterministic agreement iff `n ≥ 3f+1`, round floor `f+1`; signatures relax to `f+1`.
- [[sources/2026-04-21_flp-impossibility-1985]] — [2] FLP: no deterministic async consensus with even one crash fault; motivates the four families' relaxations.
- [[sources/2026-04-21_dwork-lynch-stockmeyer-partial-sync-1988]] — [3] Partial-synchrony model; consensus under `f < n/3`; safety-always / liveness-after-GST separation.
- [[sources/2026-04-21_castro-liskov-pbft-1999]] — [4] PBFT: first practical BFT SMR; three-phase commit + view change; `O(n²)` normal / `O(n³)` view change.
- [[sources/2026-04-21_yin-hotstuff-2019]] — [5] HotStuff: linearises view change to `O(n)` via threshold signatures; responsive leader rotation.
- [[sources/2026-04-21_buchman-tendermint-2018]] — [6] Tendermint: round-robin leader BFT with locking rule; Cosmos SDK deployment basis.
- [[sources/2026-04-21_buterin-griffith-casper-ffg-2017]] — [7] Casper FFG: BFT finality gadget; two-round justify→finalise; accountable safety via slashing.
- [[sources/2026-04-21_buterin-gasper-2020]] — [8] Gasper: LMD-GHOST fork choice + Casper FFG finality; the deployed Ethereum PoS protocol.
- [[sources/2026-04-21_team-rocket-avalanche-2019]] — [9] Avalanche: subsampled-voting cascade Slush→Snowflake→Snowball→Avalanche; probabilistic `1 − ε` finality; per-node `O(K·β)`.
- [[sources/2026-04-21_amores-sesar-avalanche-analysis-2024]] — [10] Rigorous formal re-analysis of Avalanche; tightens safety bounds and identifies async-liveness gap vs [9]'s informal claims.
- [[sources/2026-04-21_danezis-narwhal-tusk-2022]] — [11] Narwhal+Tusk: DAG mempool + zero-overhead consensus; decouples data availability from ordering; `O(n)` messages.
- [[sources/2026-04-21_spiegelman-bullshark-2022]] — [12] Bullshark: partial-sync fast path + async fallback DAG BFT; simplifies Narwhal+Tusk in ~200 LoC.
- [[sources/2026-04-21_babel-mysticeti-2023]] — [13] Mysticeti: uncertified DAG at the 3-round BFT latency lower bound; deployed in Sui.
- [[sources/2026-04-21_bano-sok-consensus-2019]] — [14] SoK taxonomy of blockchain consensus families; taxonomic anchor for Ch. 2 and for [[concepts/consensus-families]].
- [[sources/2026-04-21_xiao-survey-2020]] — [15] Survey of blockchain consensus protocols with aggregated throughput / latency / fault-tolerance ranges across families; framing-only citation.
- [[sources/2026-04-21_cachin-vukolic-blockchain-wild-2017]] — [16] Qualitative review of permissioned-chain BFT; methodological anchor for formal models + public review; motivates the simulator-based approach.
- [[sources/2026-04-21_gervais-pow-security-2016]] — [17] PoW simulation framework for security + performance; methodological precedent for this thesis's BFT-family simulator.
- [[sources/2026-05-06_gilbert-lynch-cap-2002]] — [18] Formal proof of Brewer's CAP conjecture; atomic-consistent + available distributed register impossible under partition; partial-sync admits only `t-eventual` consistency.

## Experiments

- [[experiments/2026-05-18_scheduler-baseline]] — T21 build-verification baseline: the discrete-event scheduler drives a 2-node ping-pong through the full six-phase bootstrap to quiescence; determinism contract holds (byte-identical re-run).

## Lint reports

- [[lint/2026-04-21_sync-report]] — S9 sync-completeness pass: T1 artifact `consensus-overview.md` missing on disk and from index; all other W0–W2 completed tasks check out.
- [[lint/2026-05-06_report]] — L-W2 end-of-Week-2 lint pass: H1 dashboard arithmetic drift in `TASKS.md`; M1 three forward-reference missing pages owned by W3 (T16/T18/T19); M2 stale `TODO(cite)` markers superseded by S6/S9; plus 4 Low findings. Orphans / index drift / stale-status artifacts / draft citations / draft dead links / contradictions all clean.

## Drafts

- [[drafts/ch1_intro]] — Chapter 1 Introduction: background, motivation, problem statement, operational performance/security definitions, scope and assumptions, RQ1–RQ5, contributions, and chapter roadmap.
- [[drafts/ch2_litreview]] — Chapter 2 Literature Review: blockchain & the consensus problem, the four-family design space (Figure 2.1), per-family survey on a uniform mechanism / guarantees / adversarial-weakness / RQ-role skeleton (Table 2.1), and the metric-vocabulary fragmentation that obstructs cross-family comparison (Table 2.2). Establishes the unified-harness gap as a literature-level claim and hands off to Chapter 3.
