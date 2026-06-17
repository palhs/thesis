# T53 — Equivocating nodes (Family C `equivocate-vote`) — Design

**Task:** T53 (Engineer, H). Simulate equivocating nodes across the
three implemented protocols (PBFT, Casper FFG, Snowman); intensity sweep
including above-threshold `f > 1/3` to expose the safety cliff the catalog
documents (`wiki/concepts/adversary-model.md` §5, §7.1, §7.3).

**Status:** design approved (human, 2026-06-18). Implementation handed to
`writing-plans`.

**Backlinks:** [[concepts/adversary-model#5]] (the `equivocate-vote` row),
[[concepts/adversary-model-runtime#5]], [[concepts/node-model#9]],
[[concepts/experiment-matrix#3]], [[concepts/experiment-matrix-runs#3]],
[[experiments/2026-06-14_delayed-voters]] (T51 — the adversary subsystem
bootstrap), [[experiments/2026-06-17_offline-validators]] (T52 — the
closest structural precedent: shared harness, per-protocol f-grid,
boundary localization), [[concepts/output-format]], [[concepts/sweep-harness]].

---

## 1. Goal and scope

Run the Week-10 Family C **`equivocate-vote`** experiment: Byzantine
validators sign two incompatible messages where the protocol expects at
most one. Measure the impact on **safety** (and the liveness events that
precede it) across PBFT, Casper FFG, and Snowman at `n ∈ {10, 25}`,
sweeping the Byzantine fraction `f` **through and past** `1/3` so the
safety cliff is *measured*, not inferred.

**In scope (this task):** the `equivocate-vote` mechanism (3 adversarial
node subclasses + shared harness), the sweep, the raw safety + liveness
signals written to the CSV, and a **descriptive** experiment page that
witnesses the cliff appearing where theory predicts.

**Out of scope (deferred):**
- **Formal four-invariant measurement, the liveness/safety-degradation
  plots, and the cross-protocol robustness ranking** → **T54**. T53
  produces the dataset + raw signals; T54 does the analysis.
- **Narwhal+Tusk** equivocation (`distinct headers to disjoint peers`) →
  post-T38.1 follow-on (NWT is unimplemented; `T38.1` Blocked). Three
  protocols this task, not four — consistent with `adversary-model.md` §1
  ("12 exercised by T51–T53", 9 pre-T38.1).
- **§7.1 Snowman colluding sub-sampler** and **§7 protocol-specific
  surfaces** → catalogued design space, no experiment task (human scope
  decision 2026-05-18). T53 Snowman uses the §5 lying-responder reduction.
- **FFG surround-vote** as a swept adversary variant → double-vote only
  (human decision 2026-06-18); the T70 surround *detection* stays active
  and is reported if it happens to fire.

---

## 2. The unifying mechanism

Reading the three FSMs surfaced one structural fact that shapes the whole
design: **a real safety break needs an equivocating *proposer* to create
the fork *and* equivocating *voters/responders* to push the conflicting
quorums.** A single conflicting message, with all other nodes honest,
only ever causes a *liveness* event (a view change, a stalled poll), never
a safety break — quorum intersection holds below `f = 1/3`. This is
exactly why the task mandates sweeping above `1/3`: the cliff only exists
when the Byzantine fraction is large enough to manufacture two
intersecting quorums on disjoint honest subsets.

### Mechanism placement — B-hybrid (approved)

Behavior lives in **adversarial node subclasses**; selection, profiles,
runners, sweep, instrumentation, and the CSV story stay **shared** in
`src/adversary/`. Rationale (human discussion 2026-06-18): equivocation is
a *node-level semantic decision* (a Byzantine node chooses to sign
contradictory messages), unlike delay/offline which are timing/transport
effects faithfully modeled at the network seam. The per-protocol semantics
are stateful and multi-message (FFG double-vote, Snowman proposer-fork +
lying responder, PBFT per-seq conflicting pre-prepare), so full FSM access
makes them *correct* — and correctness of the adversary is what the
analysis rests on. Keeping the harness shared preserves the unified
Chapter-4 methodology narrative ("one injection harness, three Byzantine
behaviors"). The `src/adversary/inject.py` docstring anticipated this:
*"Only T53 (equivocate), which forks payloads per-recipient, will need
deeper FSM hooks."*

**Simplification vs the T51/T52 seam:** because the behavior is in the
node class, T53 needs **no post-`build_run` wrap**. The runner's
`make(node_id, global_seed)` factory returns the adversarial subclass for
Byzantine ids and the honest class otherwise. `build_run` already takes a
per-id make-fn.

---

## 3. Per-protocol equivocation semantics

### 3.1 PBFT (Byzantine set must include the primary)

`EquivocatingPBFTNode(PBFTNode)`:
- **`_propose`** (primary only): for one `(view, seq)`, build two requests
  `reqA`, `reqB` (e.g. `reqB = reqA + b"\x00"`), each with its matching
  `digest`, and send `PRE-PREPARE(reqA)` to the low half of `peers−self`,
  `PRE-PREPARE(reqB)` to the high half. Self-accept one (`reqA`) as today.
- **`_broadcast_prepare` / `_broadcast_commit`**: a Byzantine backup forks
  its vote — `PREPARE/COMMIT(digest_A)` to the low half, `(digest_B)` to
  the high half.
- **Below `1/3`:** honest `2f+1` can form only one quorum; honest nodes
  that received conflicting pre-prepares cannot prepare → the per-instance
  **view-change timer** fires (liveness signal); safety holds.
  Invariant: *no two honest replicas commit conflicting digests at the
  same `(view, seq)`* (`adversary-model.md` §5).
- **At/above `1/3`:** enough equivocating voters to push two `2f+1` commit
  quorums on disjoint honest subsets → **two honest replicas decide
  conflicting digests** = the safety break. (Equivocating only the
  `PRE-PREPARE` would never break safety even above `1/3`, so it would not
  expose the cliff.)

### 3.2 Casper FFG (double-vote)

`EquivocatingCasperNode(CasperNode)`:
- **`_propose`** (on its slots): fork `BLOCK-PROPOSAL` — block A to the low
  half, block B to the high half — splitting honest checkpoints.
- **`_attest`**: **double-vote** — emit two `ATTESTATION`s for the same
  target epoch with different target hashes (A to low half, B to high
  half). The T70 machinery (`casper_slashing` event +
  `slashable_stake_fraction()`) fires automatically on the conflicting
  second vote.
- **Below `1/3`:** detected, ≤ 1 checkpoint finalises, the accountable-
  safety bound (≥ 1/3 stake slashable on any conflict) holds; safe.
- **At/above `1/3`:** each honest half + Byzantine stake clears 2/3 → **two
  finalised conflicting checkpoints** = break, with ≥ 1/3 stake slashable
  (the accountable-safety theorem, confirmed empirically). Invariant:
  *any two conflicting finalised checkpoints ⇒ ≥ 1/3 stake slashable*
  (`adversary-model.md` §5 / §7.3).

### 3.3 Snowman (equivocating proposer + lying responders)

`EquivocatingSnowmanNode(SnowmanNode)`:
- **`_propose`** (on its slots): fork `BLOCK-ANNOUNCEMENT` — two blocks for
  the same slot/parent, A to the low half, B to the high half. This is the
  only way to create a **non-singleton conflict set**, i.e. something to
  lie about (the honest baseline has one block per slot).
- **`_handle_query`**: lying responder — return the **non-preference**
  block id in `QUERY-RESPONSE` instead of `cs.preference`.
- **Expected result:** the §5 reduction is **liveness-only / "no
  fork-induction surface"**. The measured quantity is the **empirical
  safety-violation rate vs the bound `(1 − α_c/K)^β`** (`adversary-model.md`
  §5 / §7.1, `algorithms/avalanche#probabilistic-safety`). Expectation:
  ≈ 0 (Snowman resists the fork) right up to the threshold — itself the
  comparative finding. No safety surface exists above `1/3`, so the grid
  stops at `1/3` (human decision 2026-06-18).

---

## 4. Selection and partition

- **`byzantine_node_ids(n, f) = {0 … ⌊f·n⌋ − 1}`** (lowest-id, ascending).
  The **inverse** of the T51/T52 `slow_node_ids` rule, because equivocation
  needs the PBFT view-0 primary (node 0) and proposer slots *inside* the
  Byzantine set. Empty when `f = 0`.
- **Partition: deterministic half-half** of the sorted `peers − self`
  (`lo = peers[:len//2]`, `hi = peers[len//2:]`). No adversary RNG → the
  partition is a pure function of `(n, self.id)`, so byte-identical replay
  is preserved. Half-half maximizes the two-quorum potential that exposes
  the cliff.

---

## 5. Config and grid

- **Network:** static-baseline timeline — constant 10 ms delivery delay,
  loss-free (Family C fixed axis; matches T51/T52).
- **Swept axis:** Byzantine fraction `f` only — **no magnitude axis**
  (equivocation is binary, like offline).
  - **PBFT, Casper FFG:** `f ∈ {0, 0.10, 0.20, 0.33, 0.40, 0.50}` (6 cells)
    — above `1/3` to expose the cliff.
  - **Snowman:** `f ∈ {0, 0.10, 0.20, 0.33}` (4 cells).
- **Sizes / seeds:** `n ∈ {10, 25}`, 20 seeds (common random numbers).
- **Grid:** `(6 + 6 + 4) protocol-cells × 2 n × 20 seeds = 640 runs`.
- **Realized byzantine_node_count** (floor): `f=0.33 → 3/10, 8/25`;
  `f=0.40 → 4/10, 10/25`; `f=0.50 → 5/10, 12/25`. `f=0` = empty Byzantine
  set ⇒ pure honest run.
- **Calibration:** probe the worst attack cell per protocol (`--probe`),
  set `WINDOW_S` / `BUFFER_S` / `T_MAX` to capture every finalizing cell;
  PBFT `vc_delay` per the T51/T52 precedent; Snowman opt-in `query_timeout`
  reused from T52 (offline-style stalls can recur when lying responders
  starve a poll round). Clip **reported, not guarded** (Option-B, human
  precedent).

---

## 6. Instrumentation and output

CSV = the 18-column T40 projection ([[concepts/output-format]]) + the
adversary annotation block + safety/liveness signals:

- **Annotation:** `adversary_strategy = "equivocate-vote"`,
  `byzantine_node_count` (`⌊f·n⌋`), `byzantine_fraction` (nominal `f`),
  `partition_strategy = "half-half"`, `clipped_fraction`, `run_horizon_s`.
- **Safety signals (the T53 deliverable feeding T54):**
  - **Universal:** `safety_violation` — the **cross-node conflicting-
    decision reducer** (`src/adversary/safety.py`): over `decided` events,
    for each `instance_id`, flag whether two honest nodes decided different
    values. (Per the T54 note this reads 0 below threshold for PBFT — that
    is the point; it is reported, not the sole signal.)
  - **PBFT:** `view_change_count` (existing `pbft_view_change` events).
  - **FFG:** `slashable_stake_fraction` (max over honest nodes, from
    `casper_slashing`); conflicting-finalised-checkpoint count.
  - **Snowman:** empirical safety-violation rate (conflicting-block
    accepts), to be compared against `(1 − α_c/K)^β` (the comparison is
    T54's; T53 records the raw rate).
- **Liveness:** reuse `success_rate` / finalization (the T52 headline).

Dataset → `results/adversary/equivocating_nodes.csv`. Figures: only the
minimum needed to *witness* the cliff in the descriptive page; the
polished invariant figures are T54.

---

## 7. Determinism

- `f = 0` is a **pure honest run, byte-identical to the honest
  static-baseline** (no adversarial subclass instantiated).
- `f > 0` cells are **per-cell byte-identical** on re-run: the overrides
  touch payloads and recipient partitioning, never RNG draws. (The
  Byzantine Snowman node still samples honestly via its own per-node RNG
  stream — deterministic.) They are **not** byte-identical to the control
  (different messages flow), the same accepted caveat as T52.
- A **byte-identical re-run guard** reproduces the honest baseline and a
  committed worst-case row, and confirms the honest protocol FSMs are
  untouched (subclasses live in `src/adversary/`, importing the honest
  classes — no edit to `src/{pbft,pos,snowman}/`).

---

## 8. File plan

New in `src/adversary/`:
- `equivocate.py` — `EquivocatingPBFTNode`, `EquivocatingCasperNode`,
  `EquivocatingSnowmanNode`; the shared half-half partition helper.
- `safety.py` — cross-node conflicting-decision reducer + per-protocol
  signal extraction.
- `equivocate_sweep.py` — orchestrator (mirrors `offline_sweep.py`;
  reuses `run_grid_tiered`, clip, the T40 reducers).
- additions to `profiles.py` (`EquivocateProfile`), `select.py`
  (`byzantine_node_ids`), `runners.py` (`EQUIVOCATE_RUNNERS` +
  `equivocate_config`), `__init__.py` `__all__`.

New tests in `tests/adversary/` (registered as a `make` suite):
- **Unit:** half-half partition determinism; each subclass emits two
  conflicting payloads to disjoint subsets; `f=0` byte-identical to honest.
- **E2e:** PBFT/FFG `safety_violation = 0` below `1/3` (view-change /
  slashable fires) and `> 0` at/above the cliff; Snowman empirical
  violation rate ≈ 0 throughout (resists); each protocol's worst cell
  finalizes inside the window or is reported as stalled.

Untouched: `src/scheduler/`, `src/network/`, `src/nodes/`,
`src/event_log/`, and the honest `src/{pbft,pos,snowman}/` FSMs.

---

## 9. Wiki + handoff deliverables

- `wiki/experiments/2026-06-18_equivocating-nodes.md` — config, grid,
  determinism note, calibration, descriptive per-protocol findings (the
  cliff witness), Auggie verification subsection, re-run commands.
- `## Revisions` on [[concepts/adversary-model#5]] — the `equivocate-vote`
  row gains a runtime realization (subclass-based, the third
  `Node.adversary` fill), noting any catalog expectation confirmed or
  contradicted (esp. the Snowman §5 "no fork-induction surface" claim).
- `wiki/index.md` + `wiki/log.md` updates.
- T54 is unblocked to consume `results/adversary/equivocating_nodes.csv`.

---

## 10. TDD

Non-trivial logic (the conflicting-quorum mechanics, the safety reducer)
is driven by `superpowers:test-driven-development`: write the failing
unit/e2e test first, then the subclass/reducer. A verification subagent
runs at each commit boundary (per the per-commit verification protocol);
`superpowers:verification-before-completion` + the Auggie pre/post-edit
queries gate the flip to In Review.
