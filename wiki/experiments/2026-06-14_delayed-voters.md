# [2026-06-14] Delayed voters — Family C delay-emission (T51)

Bootstraps the simulator's **adversary-injection subsystem** (`src/adversary/`)
and runs the Week-10 Family C **`delay-emission`** experiment: the highest-id
`⌊f·n⌋` validators hold every outbound emission by a fixed `m·ref` seconds
(`ref` = the protocol's round cadence); we measure the impact on time-to-finality
across PBFT, Casper FFG, and Snowman at `n ∈ {10, 25}`.

This is the **first** task to fill the opaque `Node.adversary` slot with a
working strategy. The seam (`inject_delay`) is reused by T52 (withhold) and T53
(equivocate).

Backlinks: [[concepts/adversary-model#3]], [[concepts/adversary-model-runtime#4]],
[[concepts/node-model#9]], [[concepts/experiment-matrix#3]],
[[concepts/experiment-matrix-runs#3]], [[concepts/sweep-harness]],
[[concepts/output-format]], [[experiments/2026-06-12_delay-heavy]] (the
`heavy.py` orchestrator + tiered-scheduler precedent),
[[experiments/2026-06-13_delay-comparison]] (Student-t CI plot style).

## Subsystem (the injection seam)

The honest network must stay honest ([[concepts/network-model]] §6), so the
adversary attaches **after `build_run`** by re-wrapping each slow node's bound
`send` / `broadcast` (set by `Network.bind`) to shift the `t_sent` argument
forward by `shift = m·ref`. The honest network then adds its normal delivery
delay on top. No edit touches the network, scheduler, or any protocol FSM — only
the new `src/adversary/` package plus the existing `Node.adversary` slot. This is
a pragmatic realization of the [[concepts/node-model]] §9 `delayer` cell: for the
delay capability (which neither rewrites payloads nor drops/forks messages),
intercepting at the bound outbound API is behaviourally identical to FSM-level
dispatch and far less invasive. T52/T53 will need deeper FSM hooks.

Slow set = the **highest-id `⌊f·n⌋`** nodes (`src/adversary/select.py`), so the
PBFT view-0 primary (node 0) is never slowed — the attack hits *backups*, keeping
this `delay-emission`, not `disrupt-leader`.

## Config

- **Network:** static-baseline timeline — constant 10 ms delivery delay,
  loss-free (Family C fixed axis).
- **Swept axes:** intensity `f ∈ {0, 0.10, 0.20, 0.30}` (slow-node fraction; the
  `f=0` row is the honest control) × magnitude `m ∈ {2, 4, 6, 8, 10}` (fixed
  delay multiple of the round cadence; `m` applies only to `f>0` cells).
- **Sizes / seeds:** `n ∈ {10, 25}`, 20 seeds (common random numbers), full set
  for every `(protocol, n)` — no seed cap needed (the static-baseline cells are
  cheap; see § Cost).
- **Realized slow_node_count** (floor effect): `n=10 → {0,1,2,3}`;
  `n=25 → {0,2,5,7}` (so nominal `f=0.10` at `n=25` realizes `2/25 = 0.08`).
- **Per-protocol cadence `ref`:** PBFT propose = 1.0 s, Snowman slot = 1.0 s,
  Casper FFG slot = 0.1 s (static-baseline `E[delay]=10 ms` satisfies the §5
  coherence rule `slot ≥ 4·E[delay]`). So a slow node holds each emission by
  `m·ref`: PBFT/Snowman 2–10 s; FFG 0.2–1.0 s. The FFG asymmetry (shorter
  cadence ⇒ smaller absolute shift) is reported, not hidden.
- **Grid:** 3 protocols × 2 `n` × (1 control + 3 `f` × 5 `m` = 16 cells) × 20
  seeds = **1920 runs**.

## Calibration (probe-derived, human decisions 2026-06-15)

`sweep.py --probe` times the worst attack cell (`f=0.30, m=10`) per protocol at
`n=10`. Final probe (W=150 s):

| protocol | first finality | clipped | in-window finalized | view-changes |
| :-- | --: | --: | --: | --: |
| PBFT | 1.03 s | 1.3 % | 149 | 0 |
| Casper FFG | 0.51 s | 1.1 % | 358 | 0 |
| Snowman | 71.12 s | 84.9 % | 11 | 0 |

- **Window/buffer:** `WINDOW_S = 150 s`, `BUFFER_S = 80 s` (≥ one full Snowman
  block-finalization under the worst attack, ~71 s), horizon `T_MAX = 230 s`.
  `WINDOW_S` captures every protocol's worst first-finality, so the headline
  `finality_delay_ratio` is well-defined for every cell.
- **Clip is REPORTED, not guarded at <5 %** (the T47 Option-B precedent, human
  2026-06-15): Snowman's heavily-attacked cells spill a large finalization tail
  past `W` that no tractable window removes — that spill is itself a degradation
  signal. Worst clipped fraction = **88.9 %** (Snowman `n=10, f=0.20, m=10`);
  PBFT/FFG mean ≈ 1.3 %.
- **`ONE_ROUND_S`** (clip scope bound) probe-set to the per-protocol round:
  PBFT/FFG 2 s, Snowman 72 s (so crippled-but-finalizing Snowman blocks stay
  in-scope rather than being dropped as "late").
- **PBFT `vc_delay = 3 s`** (≈ 3× honest round). It never fires:
  `view_change_count = 0` across all 1920 rows — at `f ≤ 0.30` the honest quorum
  is met without the slow backups, so the primary commits without rotation
  (itself a finding, § Findings).

## Metrics & output

CSV = the 18-column T40 projection ([[concepts/output-format]]) + a Family-C
annotation block: `adversary_strategy`, `byzantine_fraction` (nominal `f`),
`slow_node_count` (realized `⌊f·n⌋`), `delay_mult` (`m`), `view_change_count`,
`clipped_fraction`, `run_horizon_s`, and the headline `finality_delay_ratio`.

**`finality_delay_ratio`** (post-grid pass): for an attack cell,
`commit_latency_ms(cell) / commit_latency_ms(control)` at the same
`(protocol, n, seed)` where the control is the `f=0` row; control rows = 1.0;
NaN if the control or the attack cell did not finalize. `commit_latency_ms` is
the cross-protocol-comparable column ([[concepts/output-format]] §13). PBFT's
`tps`/`goodput` are re-based onto `WINDOW_S` via `delay.sweep._window_denominator_fix`
(matching the T46/T47 harnesses), keeping throughput cross-protocol-comparable.

## Findings (one paragraph + table)

Slow voters below the fault threshold split the three protocols by **failure
mode**, and the split tracks protocol structure (quorum voting vs sequential
sampling):

| protocol | finality latency under worst attack (`f=0.30, m=10`) | liveness (seeds finalizing, m=10) | mechanism |
| :-- | :-- | :-- | :-- |
| **PBFT** | **unchanged (≈1.0×)** | 20/20 at every `f` | honest backups already meet the `2f+1` quorum; primary is honest ⇒ no rotation (`view_change_count=0`) |
| **Casper FFG** | **unchanged (≈1.0×) when it finalizes** | **degrades: 17 / 15 / 12 of 20** at `f=0.10/0.20/0.30` (n=10; 18/15/13 at n=25) | quorum attestation tolerates slow voters, but the per-slot proposer **rotates** — a slow node is sometimes the proposer and stalls that slot's block (the §3.3 overlap), occasionally preventing in-window finalization |
| **Snowman** | **explodes: ~54× (n=10), ~49× (n=25)** | 20/20 (never stalls) | leaderless `K`-peer polling: every one of `β=15` sequential poll rounds can sample a slow responder, compounding the per-block delay |

Snowman dose-response (mean `finality_delay_ratio`, NaN-dropped):

| | `f=0.10` | `f=0.20` (m=2 → 10) | `f=0.30` (m=2 → 10) |
| :-- | --: | --: | --: |
| n=10 | ≈ 1.0 (flat) | 18.4 → 61.9 | 18.4 → 54.3 |
| n=25 | ≈ 1.0 (flat) | 10.7 → 44.4 | 24.4 → 49.1 |

Two structural observations. (1) **Snowman has a threshold near `f=0.20`:** at
`f=0.10` (1 slow node of 10, or 2 of 25) the slow responders are rarely sampled
in the `K`-peer polls, so finality is essentially unchanged; from `f=0.20` it
degrades steeply and **linearly in `m`** (the dose-response curve). (2) **PBFT
and Casper FFG are latency-immune** to delayed *backups* below `f=1/3` because
their finality is quorum-gated and an honest supermajority remains — FFG's only
casualty is *liveness*, via proposer rotation, never *latency*. The headline:
**only the sequential-sampling protocol (Snowman) pays a latency cost; the
quorum-voting protocols do not.**

## Seeds, commit, re-run

- **Dataset:** `results/adversary/delayed_voters.csv` (1920 rows).
- **Figures:** `results/adversary/plots/{ratio_vs_m,ratio_vs_f}_n{10,25}.pdf`
  (PDF tracked, PNG regenerable).
- **commit_hash** (CSV column): `8b2d0bb0-dirty`. **Provenance note:** the sweep
  spanned two commits (`8ea5cf6` Task-9 calibration → `8b2d0bb` Task-11 plots);
  the cell-computation code path (runners / inject / clip / reducers / config) is
  byte-identical between them — Task 11 only added the plot module and a
  `.gitignore` line — so every row is reproducible at `8b2d0bb`, and the column
  was normalized to that single value. The `-dirty` suffix reflects an
  uncommitted plan-doc edit and an untracked run log present during the sweep,
  neither affecting computation.
- **Re-run:** `PYTHONPATH=src python3 -m adversary.sweep --jobs 8 --heavy-jobs 4`
- **Probe:** `PYTHONPATH=src python3 -m adversary.sweep --probe`
- **Figures:** `PYTHONPATH=src python3 -m output.adversary_plots`

## Cost

The static-baseline network (10 ms) makes cells cheap: the worst Snowman `n=25`
cell is ~900k events (≈40 s wall at horizon 230 s), nothing like T47's multi-GB
heavy-tail cells. The tiered scheduler (`run_grid_tiered`, `is_heavy = snowman &
n≥25`) ran the heavy tier at `--heavy-jobs 4`. The dominant cost was the Casper
FFG `n=25` cells (~100 s CPU each — hundreds of attestations × 25 nodes through
the reducer). Full sweep ≈ 1 h wall at `--jobs 8`.

## Auggie verification

The Engineer role mandates `mcp__auggie__codebase-retrieval` pre/post edit.
**auggie is unavailable in this environment.** Substitute: Grep/Glob + direct
file reads for the structural search, logged here (precedent: the T41 page).

- **pickup-index** — Grep/Read for `Node.adversary`, `Network.bind`,
  `config.factory.build_run`, `common.run_grid_tiered`, `delay/runners.py`,
  `delay/heavy.py`, `delay/clip.py` → mapped the bind seam (`node.send`/
  `broadcast` lambdas take `(…, t)` flowing to `t_sent`), the `RunHandle.nodes`
  mapping, and the T46/T47 sweep precedents the orchestrator mirrors.
- **plan** — Read `src/network/network.py`, `src/nodes/node.py`,
  `src/output/{csv,schema,delay_analysis,plots}.py`, `src/common/sweep.py` →
  confirmed `_window_denominator_fix` lives in `delay.sweep`, `mean_ci` in
  `output.delay_analysis`, `STYLE`/`PROTO_ORDER` in `output.plots`,
  `run_grid_tiered` signature, and the `DelayDist("constant", …)` validation.
- **post-edit re-query** — Grep over `src/adversary/` + `make`-suite run
  (`tests/adversary` 34 tests green; `tests/output` 122 green; `tests/delay`,
  `tests/common` unchanged) → confirmed no shared-infra edits, the new package's
  only inbound coupling is `delay.{clip,sweep}` + `output.{csv,schema}` +
  `common`, and the bind-seam wrap leaves all frozen baselines byte-identical.

This Grep/Glob substitution is the proof-of-verification artifact for the task.
