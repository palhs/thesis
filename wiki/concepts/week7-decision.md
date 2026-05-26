# Week 7 — Decision Gate

T37 is the Week 7 decision gate: with PBFT (W5) and Casper FFG (W6)
landed, the simulator is at the fork between **Path A** — implement a
third protocol and keep the four-protocol ambition partially intact — and
**Path B** — spend the week stabilising the two-protocol baseline and
moving T40 (unified output format) forward.

This page records the decision, the evidence behind it, the scope handed
to T38 by the decision, and the scope that Path A explicitly does *not*
cover so downstream tasks (T36.1, T36.2, T40, T41, T46–T55, T67) inherit
an honest picture of what the thesis-as-shipped will contain.

## 1. Decision

**Path A — implement Snowman in W7 via T38; sequence Narwhal+Tusk to
T38.1 post-W10.** The final protocol set is still **four protocols** —
PBFT, Casper FFG, Snowman, Narwhal+Tusk — but the W7 decision sequences
them: the three-protocol adversarial sweep (T51–T55) runs against
PBFT + Casper FFG + Snowman; **T38.1** (Narwhal+Tusk implementation)
lands between T55 (W10 adversarial summary) and T57 (W11 enhancement),
so the comparative adversarial evidence — the thesis's stated
contribution per [[concepts/problem-statement]] §Contributions — lands
before Narwhal+Tusk competes for implementation time. DAG-Avalanche [9]
remains out of scope per [[algorithms/avalanche]] §Simulator mapping.

The choice of Snowman over DAG-Avalanche within the
[[algorithms/avalanche|Avalanche family]] is structural: Snowman is the
linearised production variant, directly comparable to PBFT and Casper FFG
under the same totally-ordered chain output structure
([[concepts/metric-reconciliation]] §1, asymmetry 1). DAG-Avalanche
would force the §1 asymmetry on two of three chain protocols and is in
any case out of scope per [[algorithms/avalanche]] §Simulator mapping.

## 2. Inputs to the decision

### 2.1 What is done

- **PBFT** ([[algorithms/pbft]]). Full three-phase commit + VIEW-CHANGE
  / NEW-VIEW recovery implemented (T28, T29). Honest-path baseline
  [[experiments/2026-05-21_pbft-baseline]] confirmed at `n ∈ {4, 7, 10}`,
  byte-identical determinism, zero forks.
- **Casper FFG** ([[algorithms/pos]]). Two-round justify→finalise over
  stake-weighted attestations implemented (T32, T33, T34). Honest-path
  baseline [[experiments/2026-05-25_pos-baseline]] confirmed at
  `n ∈ {4, 7, 10}` (uniform + non-uniform stake), byte-identical
  determinism, zero forks.
- **Shared infrastructure** ([[concepts/node-model]],
  [[concepts/network-model]], [[concepts/simulation-design]],
  [[concepts/event-log-schema]], [[concepts/reproducibility]]). Stable
  since W4. The six-phase bootstrap, the split-bind invariant, the
  determinism contract, and the three event-sink shapes have not been
  perturbed by either protocol implementation.
- **Test rig.** 497 unit + integration tests across 8 suites under
  `make test`. The full suite ran green at the start of T37 with zero
  failures. Per-suite breakdown: scheduler 46, nodes 46, network 62,
  event_log 30, config 39, pbft 130, pos 80, integration 64.

### 2.2 What is outstanding

- **T31** ([?] In Review). PBFT unit-test extension (5+ targeted tests).
  Lands as `tests/pbft/` additions; not a code change to `src/pbft/`.
- **T36** ([?] In Review). Chapter 3 (Methodology) first pass, covering
  the two implemented protocols. T36.1 and T36.2 ([!] Blocked) are
  reserved for the Snowman and Narwhal+Tusk Chapter 3 extensions.
- **T40** ([ ] Not Started). Unified output CSV per
  [[concepts/output-format]] (forward link in
  [[concepts/metric-reconciliation]] §T40 CSV schema implications). The
  schema is design-pinned by `metric-reconciliation`; the work is the
  runner refactor that produces a single comparative CSV across protocols.
- **Backlog watch items**, all Low- or Medium-priority hardening, none
  blocking a third protocol:
  - PBFT-specific network-drop integration test (deferred to T47).
  - Scheduler heap-compaction under high timer churn (deferred to
    T28/T29/T57 with a measurement gate).
  - Network / Scheduler / Node boundary-seam fail-fast checks (deferred
    to T19/T27 harness).
  - Adversarial PBFT malformed-payload guards (deferred to T18 / T29).
  - T35 sample CSV schema reconciliation (deferred to T40 by design —
    [[concepts/output-format]] is exactly that reconciliation).
  - T32 baseline-page transcription error (`casper_block_accepted = 77`
    vs measured 76 at `n=4`) — Linter follow-up.

### 2.3 Author preference

The author has selected **Avalanche family** as the third protocol;
within that family the choice is Snowman per §1.

## 3. Path A vs Path B

The decision is defended on four axes. Path A wins on three; the fourth
(scope risk) is the cost Path A accepts.

### 3.1 Implementation cost

**Path A — Snowman.** The handler-dispatch logic fits in ~30 lines of
pseudocode ([[concepts/system-design-protocols]] §4) and reuses the
existing `Node` outbound API (`send` / `set_timer` / `emit` / `rng`)
without any new mechanism in `Scheduler` or `Network`. New wire types
are two ([[concepts/message-types]]): `BLOCK-ANNOUNCEMENT` plus the
unicast `QUERY` / `QUERY-RESPONSE` pair. Per-`(view, seq)` instance
machinery (the heaviest part of `src/pbft/`) is not needed — Snowman's
state is one preference + one counter per pending block. By comparison,
`src/pbft/` is ~250 LOC across six modules; a comparable Snowman
implementation is estimated at ~120–150 LOC across three modules
(`node.py`, `messages.py`, `poll.py`) plus the test suite. **W7-feasible.**

**Path B — stabilise.** The `make test` suite is already green at 497
tests. There is no active failure to fix, no deferred regression. The
Backlog items §2.2 enumerates are deliberately deferred to later tasks
that own the relevant scope (T18, T19/T27, T28/T29/T47, T57); pulling
them forward into W7 would either duplicate that work or do it in a
context that lacks the consumers (e.g., the heap-compaction measurement
gate needs the high-churn timer load that T28/T29/T57 produce, not an
artificial benchmark). **Path B has no defined deliverable beyond
"polish."**

### 3.2 Stability-debt paydown

Both paths leave the same Backlog items deferred. Path A adds new
hardening surface (Snowman's `K`-peer sampling has its own determinism
concerns — see §5.1), but the surface is small and pinned by existing
contracts ([[concepts/node-model]] §8 per-Node RNG seeding,
[[concepts/network-model-phases]] §6 delivery-stream determinism).

### 3.3 Downstream unblocking

- **T36.1** ([!] Blocked: "no Snowman implementation task scheduled").
  Path A flips T36.1 to actionable on T38 landing; Path B leaves it
  permanently Blocked.
- **T40.** Both paths reach T40. Path A reaches it with the full final
  protocol set, so the unified CSV schema is implemented once, against
  the three protocols it will carry to submission. Path B implements
  T40 against two protocols and then either (a) refits when a third
  protocol arrives in W8+ (schema churn), or (b) never adds a third
  protocol, making T40's "comparative" framing two-protocol.
- **T41–T55** (W8–W10 experiments). Run-count is sensitive to protocol
  count per [[concepts/experiment-matrix-runs]]; Path A's three
  protocols set the experiment budget the matrix is currently sized
  against (minus the four-protocol cells that this decision eliminates,
  see §5.2). Path B contracts the run budget further.

### 3.4 Scope risk

This is the axis Path A accepts. Under sequencing (not removal), the
risk is **timing**, not scope reduction.

- **Narwhal+Tusk lands after the adversarial sweep, not before.** The
  four-protocol scope is preserved by sequence: T38.1 implements
  Narwhal+Tusk between T55 and T57. The honest-path build-verification
  follows the T30 / T35 / T38-baseline shape; the W10-style adversarial
  coverage for the three Narwhal+Tusk pairs in
  [[concepts/adversary-model]] §§3–5 lands as a follow-on experiment
  task once T38.1 is green.
- **Timing risk.** If T38.1 slips past the W12 cutoff, the thesis ships
  three protocols. The W12 T61 revision pass already exists; under
  sequencing its watch item is to *verify* the four-protocol framing in
  [[drafts/ch1_intro]] still matches what shipped, and amend to
  three-protocol only if T38.1 slipped — see §5.3.
- **W8–W10 experiment matrix is three-protocol by design, not
  contracted.** T41–T55 simply have no Narwhal+Tusk rows because
  Narwhal+Tusk is not yet built. The
  [[concepts/experiment-matrix-runs]] §8 coverage count temporarily
  reads "9 of 18" rather than "12 of 18"; the catalogue itself is
  unchanged — see §5.2.
- **T36.2 stays `[!]` Blocked** with a named blocker (T38.1) rather
  than blocked-by-absence-of-task. Same Blocked flag, identifiable
  prerequisite.

The judgement: the three-protocol sweep through the W8–W10 baseline /
delay / adversarial regimes produces the comparative evidence that is
the thesis's stated contribution ([[concepts/problem-statement]]
§Contributions); Narwhal+Tusk lands on top of that evidence rather than
competing with it for W7 implementation time. T57–T58 (W11 enhancement)
has slack the calendar can absorb if T38.1 needs more than the W10→W11
bridge slot.

## 4. Scope handed to T38

T38 — "Implement DAG-based or Avalanche-style consensus" in `TASKS.md`
W7 — is hereby scoped to **Snowman**. The Engineer pickup brief:

### 4.1 In scope

- **Honest-path Snowman build-verification baseline** at `n ∈ {4, 7, 10}`
  with byte-identical determinism. Same shape as
  [[experiments/2026-05-21_pbft-baseline]] (T30) and
  [[experiments/2026-05-25_pos-baseline]] (T35); one experiment page
  under `wiki/experiments/<date>_snowman-baseline.md`.
- **Implementation against** [[concepts/system-design-protocols]] §4 as
  the reference sketch. Expected divergences (the `α_p` / `α_c`
  two-threshold split flagged in §6 of that page, instance creation
  timing, and the Snowman-specific RNG-driven peer sampling) land as
  `## Revisions` entries on the same page, same precedent as the T29 and
  T32 revisions already on it.
- **Knobs from** [[concepts/metric-reconciliation]] §Snowman parameter
  rescaling (the `(K, α_p, α_c, β)` rescaling rule at thesis-scale `n`)
  and §Calibration defaults (the `β = 15` cross-protocol baseline,
  `β ∈ {3, 5}` RQ4-only safety regime).
- **New package** `src/snowman/`. Estimated three modules
  (`node.py`, `messages.py`, `poll.py`); the exact decomposition is the
  Engineer's call.
- **Test suite** `tests/snowman/` registered as a new Makefile suite in
  `Makefile` § `SUITES`. The pattern is the same per-suite
  `PYTHONPATH=src:tests/<suite>` invocation already used by the seven
  existing suites.

### 4.2 Out of scope (T38 explicitly does NOT cover)

- **Adversarial Snowman.** Selective response, adaptive colour flipping,
  sample-partitioning, colluding sub-sampler — all defer to T18
  ([[concepts/adversary-model]] §§3–5 generic capabilities, §7.1
  Snowman-specific) and T51–T53 (W10 adversarial experiments).
- **Snowman-vs-rest unified CSV.** Defers to T40
  ([[concepts/output-format]] forward link).
- **Snowman Chapter 3 prose.** Defers to T36.1, which becomes actionable
  on T38 landing.
- **DAG-Avalanche.** Out of scope by [[algorithms/avalanche]]
  §Simulator mapping, reaffirmed here.
- **`α_p` ≠ `α_c` parameter-sensitivity sweep.** Defers to T19 / T44 if
  the rescaling rule needs sensitivity coverage beyond the §Calibration
  defaults already pinned.

### 4.3 No changes to shared infrastructure

T38 must not modify `src/scheduler/`, `src/network/`, `src/nodes/`, or
`src/event_log/`. The Snowman implementation is a `Node` subclass
implementing the `start` / `on_message` / `on_timer` handler surface
([[concepts/node-model]] §6); it consumes the existing outbound API and
the existing wire envelope ([[concepts/message-types]] §6 for the
Snowman row).

If T38 surfaces a structural shortfall in shared infrastructure (e.g.,
the `Node` RNG contract turns out to be insufficient for `K`-peer
sampling), the shortfall lands as a `## Revisions` entry on the
relevant W3 contract page plus a Backlog item, **not** as a silent edit
to `src/`.

## 5. Residual risks Path A does not pay down

### 5.1 Snowman determinism surface

Snowman's `K`-peer sampling is the first protocol in the simulator that
draws on the per-Node RNG ([[concepts/node-model]] §8) for an inner-loop
decision — PBFT and Casper FFG only consume the RNG for one-shot
construction-time choices (proposer rotation in
[[algorithms/pos|FFG]] §Proposer selection). The determinism contract
covers this case by construction (one RNG stream per Node, seeded
deterministically from `(global_seed, node_id)`), but T38's experiment
page must explicitly verify byte-identical re-run **with sampling**, not
just the no-sampling determinism the existing baselines verify. **Watch
for T38:** the build-verification baseline includes a determinism case
that exercises the sampling path.

### 5.2 Adversary catalogue temporarily reads 9-of-18, not 12-of-18

[[concepts/experiment-matrix-runs]] §8 currently records 12 of 18
adversary (capability × protocol) pairs as in-scope for T51–T53. Under
sequencing, **the catalogue itself is unchanged** — the 18-pair design
space stays valid; the four-protocol scope is preserved. What changes
is the *operational coverage description*: T51–T55 exercise the **9
PBFT + Casper FFG + Snowman pairs** in §§3–5 (3 capabilities ×
3 protocols); the **3 Narwhal+Tusk pairs** in §§3–5 land with T38.1 as
a follow-on experiment; the 6 §6 / §7 pairs remain catalogued design
space out of experimental scope.

The `## Revisions` entry rewording [[concepts/adversary-model]] §8 and
[[concepts/experiment-matrix-runs]] §8 from "12 of 18 / 6 catalogued" to
"9 in-scope / 3 deferred-with-T38.1 / 6 catalogued design space" is
part of **T38.1**'s wiki output, not T38's; a Backlog entry records the
pending revision so it does not fall through. The §8 wording returns to
"12 / 6" when the post-T38.1 NWT-adversary follow-on lands.

### 5.3 Four-protocol framing contingent on T38.1

Chapters 1 and 2 ([[drafts/ch1_intro]], [[drafts/ch2_litreview]]) cite
the four-protocol scope as the methodological contribution. Both stay
factually correct under sequencing — the implementation plan still
ships four protocols; the W7 decision only sequences them. **Watch
for T61** (W12 revision pass): T61 verifies the four-protocol framing
in [[drafts/ch1_intro]] still matches what shipped, and amends to a
three-protocol framing **only if T38.1 slipped past the W12 cutoff**.
The action is contingent, not committed.

## 6. Cross-references

**Defended against:**

- [[algorithms/avalanche]] — protocol mechanism; §Simulator mapping
  fixes the Snowman-not-DAG-Avalanche scope.
- [[concepts/system-design-protocols]] §4 — reference sketch T38
  implements against.
- [[concepts/metric-reconciliation]] §Snowman parameter rescaling,
  §Calibration defaults — knobs and rescaling rule.
- [[concepts/message-types]] §6 — Snowman wire vocabulary.
- [[concepts/node-model]] §6, §8 — handler surface and RNG contract.
- [[concepts/adversary-model]] §5, §7.1 — adversarial Snowman, deferred
  to T18 / T51–T53.
- [[concepts/experiment-matrix-runs]] — W8–W10 run budget, contracts
  to ~2,025 runs.

**Downstream consumers:**

- T38 (this week) — Snowman implementation.
- T36.1 — Chapter 3 Snowman extension, unblocks on T38.
- T40 — unified output CSV, against the three protocols implemented by
  T38; the NWT column lands when T38.1 does.
- T41–T55 — W8–W10 experiment batteries, sized for three protocols.
- **T38.1** (post-W10, between T55 and T57) — Narwhal+Tusk
  implementation; unblocks T36.2, reopens the
  [[concepts/adversary-model]] §8 / [[concepts/experiment-matrix-runs]]
  §8 wording revision, and seeds the NWT-adversary follow-on
  experiments.
- T61 — W12 revision pass; verifies the four-protocol framing in
  [[drafts/ch1_intro]] still matches what shipped, amends to
  three-protocol only if T38.1 slipped.

## 7. Sources

This is a decision page; no primary-literature citations. Mechanism
citations are inherited from the linked algorithm and concept pages
([4] PBFT, [7] Casper FFG, [9] Avalanche, [10] Avalanche formal
analysis, [11] Narwhal+Tusk, `[ava-docs]` Snowman production), all
catalogued in [[concepts/annotated-bibliography]].

## Revisions

None.
