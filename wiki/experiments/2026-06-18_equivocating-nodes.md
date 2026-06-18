# [2026-06-18] Equivocating nodes — Family C equivocate-vote (T53)

Runs the Week-10 Family C **`equivocate-vote`** experiment: Byzantine validators
sign two incompatible messages where the protocol expects one. The **lowest-id
`⌊f·n⌋`** nodes are Byzantine (the inverse of T51/T52's high-id rule — equivocation
needs the PBFT view-0 primary and proposer slots *inside* the adversary set). We
sweep the Byzantine fraction `f` **through and past `1/3`** so the safety cliff is
*measured*, not inferred, across PBFT, Casper FFG, and Snowman at `n ∈ {10, 25}`.

This is the **third** strategy filling the `Node.adversary` seam, after T51
(`delay-emission`) and T52 (`withhold-participation`). Unlike those two — which
attach a network-seam wrap to honest nodes — equivocation is a *node-level
semantic decision*, so the behaviour lives in three thin **adversarial node
subclasses** (`src/adversary/equivocate.py`), while selection, profile, runners,
the sweep orchestrator, and the safety reducer stay shared in `src/adversary/`
(B-hybrid; design `docs/plans/2026-06-18-t53-equivocating-nodes-design.md`).

Backlinks: [[concepts/adversary-model#5]] (the `equivocate-vote` row),
[[concepts/adversary-model-runtime#5]], [[concepts/node-model#9]],
[[concepts/experiment-matrix#3]], [[concepts/experiment-matrix-runs#3]],
[[concepts/output-format]], [[concepts/sweep-harness]],
[[experiments/2026-06-14_delayed-voters]] (T51 subsystem bootstrap),
[[experiments/2026-06-17_offline-validators]] (T52 — the harness this mirrors).
Consumed by **T54** (formal four-invariant measurement + ranking).

## Mechanism (B-hybrid subclasses)

The unifying structural fact (from reading the three FSMs): a real safety break
needs an equivocating **proposer** to create the fork *and* equivocating
**voters** to push the conflicting quorums. A lone conflicting message, with all
others honest, only causes a *liveness* event (a view change, a stalled poll) —
quorum intersection holds below `f = 1/3`. That is exactly why the sweep crosses
`1/3`.

- **PBFT** (`EquivocatingPBFTNode`): the primary forks `PRE-PREPARE` (request A to
  one half, B to the other), and every Byzantine replica forks its
  `PREPARE`/`COMMIT` votes by the same partition. The conflicting requests are
  keyed only on `(view, seq)`, so every colluding node derives the same pair
  independently.
- **Casper FFG** (`EquivocatingCasperNode`): **double-vote** — the honest
  attestation plus a second conflicting one (same target epoch, different target
  hash), **both broadcast to all** so every honest node's `EpochState` classifies
  the second as `CONFLICT` and the T70 detector fires (`casper_slashing` +
  `slashable_stake_fraction`). No forked proposal (see *Fidelity boundary*).
- **Snowman** (`EquivocatingSnowmanNode`): the proposer forks
  `BLOCK-ANNOUNCEMENT` (two blocks, one slot/parent → a genuine 2-member conflict
  set — the only thing there is to lie about), and the lying responder returns a
  non-preference block in `QUERY-RESPONSE`.

### The partition is a global parity split (not contiguous)

Recipients are split by **node-id parity** (even-id vs odd-id), a global
sender-independent rule. This is the crux of the PBFT result: the Byzantine set is
the contiguous low-id prefix `{0…k−1}`, so a contiguous-half split would put every
honest node (the high-id suffix) on one side — they would all receive the *same*
forked value and **no fork could form** (PBFT would only stall). Parity cuts
*across* the prefix, dividing the honest suffix so each half receives all `b`
Byzantine forked votes and two `2f+1` quorums form **exactly when `b > f`** (the
PBFT safety threshold). Pure function of `(n, node_id)` — no adversary RNG, so
per-cell replay stays byte-identical.

## Fidelity boundary — FFG has no representable cross-node fork

*Finding (from `src/pos/epoch.py`):* `EpochState.links` aggregates stake by
`source_epoch` only and **ignores `target_hash`** (target_hash drives only the
`DUPLICATE`/`CONFLICT` slashing classification). There is one `EpochState` per
target epoch. A forked checkpoint would therefore make two checkpoints "finalise"
under an honest supermajority — a **model artifact, not a real safety break**.
So FFG uses **double-vote only, no forked proposal**, and its faithful safety
signal is the **accountable-safety** one: `slashable_stake_fraction`, which the
model tracks correctly. The cross-node `safety_violation` reducer reads **0** for
FFG, which is the faithful outcome — accountable safety means *detect + slash*,
not *fork*. The genuine cross-node fork cliff is demonstrable only in PBFT (which
tracks digests in its quorum math).

## Config

- **Network:** static-baseline timeline — constant 10 ms delivery, loss-free
  (Family C fixed axis).
- **Swept axis:** Byzantine fraction `f` only — **no magnitude axis** (equivocation
  is binary, like offline). Per-protocol grid:
  - **PBFT, Casper FFG:** `f ∈ {0, 0.10, 0.20, 0.33, 0.40, 0.50}` (6 cells) —
    above `1/3` to expose the cliff.
  - **Snowman:** `f ∈ {0, 0.10, 0.20, 0.33}` (4 cells) — equivocation is
    liveness-only here (no fork-induction surface), so above-`1/3` adds no safety
    surface.
- **Sizes / seeds:** `n ∈ {10, 25}`, 20 seeds (common random numbers).
- **Grid:** `(6 + 6 + 4) protocol-cells × 2 n × 20 seeds = 640 runs`.
- **Realized byzantine_node_count** (floor): `f=0.33 → 3/10, 8/25`;
  `f=0.40 → 4/10, 10/25`; `f=0.50 → 5/10, 12/25`. `f=0` is the honest control
  (empty Byzantine set ⇒ pure honest run).

## Calibration (probe-derived 2026-06-18)

Constants inherited from T52 (identical static-baseline + Snowman query timeout)
and **re-probed for the equivocation regime**; every finalizing cell decides far
inside `WINDOW_S`:

| constant | value | role |
| :-- | --: | :-- |
| `WINDOW_S` | 150 s | throughput / finality window |
| `BUFFER_S` | 80 s | post-window scheduler buffer |
| `T_MAX` | 230 s | horizon |
| `PBFT_VC_DELAY_S` | 3.0 s | PBFT view-change timeout |
| `SNOWMAN_QUERY_TIMEOUT_S` | 15.0 s | Snowman poll-round deadline |

Probe first-decision latencies: PBFT honest 1.03 s, PBFT `f=0.33` 4.05 s (the
view-change-recovery path), FFG 0.51 s, Snowman 1.31 s — all ≪ `WINDOW_S` (≥ 37×
margin). Snowman clip ≈ 33 % is the degradation tail (Option-B: reported, not
guarded).

## Metrics & output

CSV = the 18-column T40 projection ([[concepts/output-format]]) + the shared
adversary annotation block (`adversary_strategy`, `adversary_node_count = ⌊f·n⌋`,
`byzantine_fraction`, `view_change_count`, `clipped_fraction`, `run_horizon_s`)
+ the T53 safety triple computed by `src/adversary/safety.py` over the **full
(unclipped)** event stream, excluding Byzantine deciders:

- **`safety_violation`** (bool): two honest nodes emitted `decided` with different
  values for the same `instance_id`.
- **`conflicting_instances`** (int): count of such instances.
- **`max_slashable_stake_fraction`** (float): max over any `casper_slashing` event.

## Findings

Equivocation splits the three protocols into **three distinct safety postures** —
the comparative result. (Safety signals are deterministic given the no-RNG parity
partition, so they are seed-invariant; the 20-seed run confirms them and adds the
latency/throughput spread.)

### Per-protocol (per-cell signal; identical across the 20 seeds)

| protocol | `f=0` | `0.10` | `0.20` | `0.33` | `0.40` | `0.50` | posture |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |
| **PBFT** `safety_violation` (n=10, n=25) | 0 | 0 | 0 | **0** | **1** | **1** | fork cliff at `b > f` |
| &nbsp;&nbsp;↳ `view_change_count` (n=10) | 0 | 10 | 10 | 10 | 0 | 0 | view-change *recovery* at `f≤1/3` |
| **Casper FFG** `max_slashable_stake_fraction` (n=10) | 0 | 0.10 | 0.20 | 0.30 | 0.40 | 0.50 | accountable safety |
| &nbsp;&nbsp;(n=25) | 0 | 0.08 | 0.20 | 0.32 | 0.40 | 0.48 | (= realized `⌊f·n⌋/n`) |
| &nbsp;&nbsp;↳ FFG `safety_violation` | 0 | 0 | 0 | 0 | 0 | 0 | no representable fork (faithful) |
| **Snowman** `safety_violation` | 0 | 0 | 0 | 0 | — | — | resists (no fork surface) |

**PBFT — a clean fork cliff that the protocol first *fights* with leader
rotation.** At `0 < f ≤ 0.33` the conflicting `PRE-PREPARE`s prevent a single
quorum, the per-instance view-change timer fires (10 view-changes at n=10, 25 at
n=25), and an honest primary eventually takes over → no fork, safety holds (this is
the catalog's "equivocation converts to leader rotation", `adversary-model.md` §5).
At `f ≥ 0.40` (`b > f_tol = ⌊(n−1)/3⌋`) the Byzantine votes manufacture two `2f+1`
commit quorums on the two parity halves → **two honest replicas decide conflicting
digests** (`conflicting_instances` jumps to 229 — identical at n=10 and n=25, since
the in-window instance count is set by the round cadence, not committee size —
`view_change_count → 0`). The
cliff sits exactly between `f=0.33` (b=3/10, 8/25 — safe) and `f=0.40` (b=4/10,
10/25 — broken), i.e. at `b > f_tol`, matching PBFT theory.

**Casper FFG — accountable safety, not a fork.** Every Byzantine attester is
detected (`slashable_stake_fraction ≈ realized f`), and the realized fraction
**first reaches ≥`1/3` at `f = 0.40`** (`0.40` at both n) — *not* at `f = 0.33`,
where the floor leaves it at `0.30`/`0.32`, just below `1/3`. This is the
accountable-safety cliff: above one-third Byzantine stake a violation becomes
economically possible but is always attributable to ≥1/3 slashable stake.
`safety_violation` stays 0 throughout (the model has no
cross-node fork to exhibit — see *Fidelity boundary*), which is the faithful
result.

**Snowman — resists.** `safety_violation = 0` and `max_slashable_stake_fraction =
0` across the whole grid: the proposer-fork + lying-responder attack cannot induce
two honest nodes to accept conflicting blocks (Snowball converges), confirming the
catalog's §5 "no fork-induction surface" reduction. The empirical safety-violation
rate stays at 0 against the `(1−α_c/K)^β` bound (≈ 0).

### Headline cross-protocol contrast (the thesis result)

Three protocols, three safety postures under equivocation: **PBFT** forks above
`b > f_tol` but resists below via leader rotation (deterministic safety with a
detectable liveness blip at threshold); **Casper FFG** never forks in-model but
makes any equivocation *accountable* — slashable stake rises to ≈ f and reaches
≥1/3 by `f = 0.40`; **Snowman** structurally resists (probabilistic safety, no fork
surface). The
cliff that the catalog documents (`adversary-model.md` §5/§7.3) is reproduced: a
deterministic fork cliff for PBFT, an accountable-safety cliff for FFG.

## Figures

Deferred to T54 (the formal four-invariant figures + cross-protocol robustness
ranking). The cliff is crisp in the per-cell table above; no thin witness figure
added here.

## Seeds, commit, re-run

- **Dataset:** `results/adversary/equivocating_nodes.csv` (640 rows).
- **commit_hash** (CSV column): `c18587d2` (uniform across all 640 rows).
- **Re-run:** `PYTHONPATH=src python3 -m adversary.equivocate_sweep --jobs 8 --heavy-jobs 1`
  (resumable; checkpoints under `results/adversary/.sweep_equivocate/`).
- **Probe:** `PYTHONPATH=src python3 -m adversary.equivocate_sweep --probe`
- **Verification:** every per-cell finding independently reconciled against the CSV
  (two recompute methods per protocol — numpy masking + awk distinct-value
  extraction); 52 T53 unit tests pass (`test_equivocate`, `test_safety`,
  `test_select`, `test_profiles`, `test_runners`, `test_equivocate_config`,
  `test_equivocate_sweep`).

## Cost

640 runs on the fast static-baseline (10 ms) network. The cost wall is the Snowman
`n=25` heavy tier (run at `--heavy-jobs`); PBFT/FFG cells are cheap. Single-process
(`--jobs 1`) is impractically slow for the full grid; the production run uses
`--jobs 8 --heavy-jobs 1` in a real terminal (the Claude Code sandbox deadlocks on
`--jobs>1`, so in-sandbox runs use `--jobs 1` or hand off). Keep `--heavy-jobs` at
**1** unless the host has ≥32 GB RAM: each Snowman `n=25` cell holds a ~5 GB event
stream, so `--heavy-jobs 2` needs ~10 GB and `4` will OOM a 16 GB Mac (cf. the T47
Snowman `n=25` OOM at two heavy cells).

## Auggie verification

The Engineer role mandates `mcp__auggie__codebase-retrieval` pre/post edit.

| phase | query | result |
| :-- | :-- | :-- |
| pickup-index | "src/adversary injection subsystem — inject_delay/inject_offline/_wrap_outbound, profiles, runners, sweep; per-protocol vote emission (PBFT PRE-PREPARE/PREPARE/COMMIT, FFG attestation + T70 slashing, Snowman QUERY-RESPONSE)" | located the bind-seam + the three emission paths; confirmed T53 needs FSM-level hooks (inject.py docstring anticipated it) |
| post-edit | "describe the final T53 equivocate subsystem + locate callers: equivocate.py subclasses / split_recipients / conflicting_bytes, byzantine_node_ids selection, EQUIVOCATE_RUNNERS dispatch, safety_signals consumers, equivocate_sweep wiring" | confirmed the B-hybrid final state: the three `Equivocating*` subclasses override only payload-emitting methods over untouched honest FSMs; `split_recipients` is the global even/odd parity split; `byzantine_node_ids` returns the low-id prefix (inverse of `slow_node_ids`, sparing nothing so node 0 = PBFT primary is in-set); `EQUIVOCATE_RUNNERS` dispatches the subclass-by-id with **no** `inject_*` wrap; `equivocate_sweep._run_cell` wires runner → `safety_signals` (full records) → `clip_records` → T40 reducer → row. No stale callers/broken refs. |
