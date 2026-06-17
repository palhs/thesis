# [2026-06-17] Offline validators — Family C withhold-participation (T52)

Runs the Week-10 Family C **`withhold-participation`** experiment: the
highest-id `⌊f·n⌋` validators go **offline** — they still receive messages and
run their FSM, but every outbound emission is dropped, so they contribute to no
quorum and answer no poll. This is the consensus definition of a silent
crash-faulty / non-participating validator. We measure the impact on
**finalization success** (liveness) across PBFT, Casper FFG, and Snowman at
`n ∈ {10, 25}`.

This is the **second** strategy filling the `Node.adversary` seam, after T51's
`delay-emission`. It reuses the SAME post-`build_run` outbound-API wrap as T51
([[experiments/2026-06-14_delayed-voters]]); the only behavioural difference is
that the wrap **drops** every emission rather than time-shifting it.

Backlinks: [[concepts/adversary-model#4]] (the `withhold-participation` row),
[[concepts/adversary-model-runtime#4]], [[concepts/node-model#9]],
[[concepts/experiment-matrix#3]], [[concepts/experiment-matrix-runs#3]],
[[concepts/system-design-protocols#4]] (the Snowman poll round + the new query
timeout), [[concepts/sweep-harness]], [[concepts/output-format]],
[[experiments/2026-06-14_delayed-voters]] (the bind-seam + orchestrator
precedent this mirrors).

## Subsystem (the injection seam)

Offline = the `withhold-participation` adversary. The honest network stays honest
([[concepts/network-model]] §6), so the adversary attaches **after `build_run`**
by re-wrapping each offline node's bound `send` / `broadcast` (set by
`Network.bind`) to **drop the emission** — the wrapped call returns without ever
handing the message to the network. The node still receives, still runs its FSM,
and still raises timers; it simply emits nothing, so it joins no quorum and
answers no query. `adversary-model.md` §4 endorses this attachment: withhold
attaches through the same outbound-API gating point as delay ([[concepts/node-model#adversary-attachment]]).
No protocol FSM hook is touched.

A shared `_wrap_outbound` helper was extracted so `inject_delay` (time-shift) and
`inject_offline` (drop) share the wrap mechanism. `OfflineProfile(nodes,
intensity, kind="withhold-participation")` carries **no magnitude field** —
offline is binary (a node either emits or it does not), unlike delay's `m`.

Offline set = the **highest-id `⌊f·n⌋`** nodes ([[experiments/2026-06-14_delayed-voters]]
precedent), so the PBFT view-0 primary (node 0) is never offline — this keeps the
attack a pure withhold, not the separate [[concepts/adversary-model#6]]
`disrupt-leader` axis (which would silence the leader itself).

## Config

- **Network:** static-baseline timeline — constant 10 ms delivery delay,
  loss-free (Family C fixed axis).
- **Swept axis:** offline-fraction `f` only — **no magnitude axis** (offline is
  binary). Per-protocol grid:
  - **PBFT, Casper FFG:** `f ∈ {0, 0.10, 0.20, 0.33, 0.40}` (5 cells).
  - **Snowman:** `f ∈ {0, 0.10, 0.20, 0.33}` (4 cells).
- **Sizes / seeds:** `n ∈ {10, 25}`, 20 seeds (common random numbers).
- **Grid:** `(5 + 5 + 4) protocol-cells × 2 n × 20 seeds = 560 runs`.
- **Realized offline_node_count** (floor effect): `f=0.33 → 3/10, 8/25`;
  `f=0.40 → 4/10, 10/25`. The `f=0` control has an empty offline set, so
  `inject_offline` is a strict no-op (see Determinism note).

### Why the f=0.40 extension (PBFT / FFG only)

The catalogued withhold grid was `{0.10, 0.20, 0.33}`
([[concepts/experiment-matrix-runs#3]]). Under floor-rounding it never crosses
the 1/3 cliff: at `f=0.33`, `⌊0.33·10⌋ = 3` offline leaves **7 honest = exactly
the `2f+1 = 7` quorum**, so the quorum protocols still finalize. The single
above-threshold point `f=0.40` (`⌊0.40·10⌋ = 4` offline → 6 honest `< 7`) was
added for PBFT and Casper FFG (human roadmap decision 2026-06-17) so the
success/failure boundary is actually **measurable** rather than inferred. Snowman
omits `f=0.40` because its liveness boundary is already crossed *below* 1/3 (see
Findings) — extending it past 1/3 would only add already-dead cells.

### Determinism note (precise)

Suppressing an offline node's broadcast skips that node's per-recipient
**`net_rng` drop-coin draws**. Under the static-baseline timeline the delivery
delay is constant (consumes no delay sample) and `p_drop = 0`, but **each
delivery attempt still consumes exactly one `net_rng` draw — the drop coin**
(`src/network/network.py:139`). So an `f>0` cell's shared `net_rng` stream
advances differently from its control: it is **per-cell deterministic**
(byte-identical re-run) but **not** byte-identical to the control. This is the
expected consequence of removing deliveries, **not a bug** — and it is
"drop-coin draws", not delay samples. The `f=0` control (empty offline set ⇒
`inject_offline` is a strict no-op) is byte-identical to the honest
static-baseline.

## Calibration (probe-derived, Task 5)

The worst *attack* cell per protocol was probed at `n=10`. Calibration constants:

| constant | value | role |
| :-- | --: | :-- |
| `WINDOW_S` | 150 s | throughput / finality window |
| `BUFFER_S` | 80 s | post-window scheduler buffer |
| `T_MAX` | 230 s | horizon |
| `PBFT_VC_DELAY_S` | 3.0 s | PBFT view-change timeout (≈3× honest round) |
| `ONE_ROUND_S[snowman]` | 72.0 s | Snowman clip-scope round bound |

- **First-finality probes:** PBFT ≈ 1.03 s, Casper FFG ≈ 0.51 s. The slowest
  *finalizing* cell is **Snowman `n=25, f=0.20` at 44.31 s** — well inside
  `W=150 s`, so finalization is captured for every cell that finalizes at all.
- **Clip REPORTED, not guarded** (Option-B precedent, [[experiments/2026-06-12_delay-heavy]]):
  worst `clipped_fraction` overall = **67.74%**. The long degradation tail of
  crippled-but-finalizing cells (e.g. Snowman `n=25, f=0.20`) is itself a signal,
  so no tractable `W` cap is enforced.

### The Snowman query timeout (new shared-infra change)

The probe revealed Snowman has **no query/response timeout**: a poll round closes
only on `α_c` agreeing responses *or* all-`K` responses
([[concepts/system-design-protocols#4]], `src/snowman/node.py`). Offline nodes
never respond, so a round that samples more than `K − α_c` non-responders could
**never close** — the leaderless K-poll would stall forever. The catalogued
expectation ([[concepts/adversary-model#4]]: Snowman degrades proportionally,
`accept rate ≥ (1−f)·base`) was an assumption carried over from the **delay**
regime, where slow nodes eventually respond.

To handle genuine non-responders faithfully (real Avalanche uses a query
timeout), an **opt-in** `query_timeout` was added to `SnowmanNode`: when set, a
per-round cancellable timer closes the round at the timeout with whatever
responses have arrived (an `α_c`-miss resets the success counter). T52 sets
`SNOWMAN_QUERY_TIMEOUT_S = 15.0 s`, chosen **above T51's max injected delay of
10 s** (the T51 delay grid max `m=10` × Snowman `ref = 1 s`) so a
delayed-but-responsive validator still answers before the timeout — keeping the
delay (T51) and withhold (T52) adversary families distinct.

**T51 is provably unaffected.** The timeout is opt-in: the T51 delay runners do
not pass it, so no timer is ever scheduled and the code path is byte-identical to
the pre-T52 node. A byte-identical re-run guard reproduced T51's committed Snowman
control **and** worst-case (`f=0.1, m=10`) rows exactly
(`commit_latency_ms = 1310.000015`, `tps = 8.14`). This is a human-approved
methodology decision (2026-06-17): add the timeout for T52, do **not** re-run or
alter T51. The Snowman spec Revision records the timeout
([[concepts/system-design-protocols#4]] Revisions).

## Metrics & output

CSV = the 18-column T40 projection ([[concepts/output-format]]) + the generic
adversary annotation block: `adversary_strategy`, `adversary_node_count`
(`⌊f·n⌋`), `byzantine_fraction` (nominal `f`), `view_change_count`,
`clipped_fraction`, `run_horizon_s`, and the headline `throughput_ratio` =
`tps(cell) / tps(same-(proto, n, seed) f=0 control)` (NaN-guarded for stall
cells).

- **Per-row finality** = the existing `success_rate` (1.0 if the run reached
  `decided`, else 0.0).
- **Post-grid aggregate `finalization_success_rate`** = `mean(success_rate)`
  over the 20 seeds, per `(proto, n, f)`.
- **Boundary `f*`** = the lowest `f` at which `finalization_success_rate` drops
  below 1.0 — the liveness boundary this experiment localizes.

## Findings

Offline validators split the three protocols into **two failure shapes**, and the
boundary ordering reorders the protocols relative to the flat 1/3 threshold.

### Per-protocol

| protocol | `finalization_success_rate` per `f` (n=10 / n=25) | `f*` | view-changes | shape |
| :-- | :-- | :-- | :-- | :-- |
| **PBFT** | `1.00/1.00/1.00/1.00/0.00` (both n) | **0.40** | 0 at f≤0.33; **50 (n=10) / 125 (n=25) at f=0.40** | sharp cliff at 1/3 |
| **Casper FFG** | n=10 `1.00/0.85/0.75/0.60/0.00`; n=25 `1.00/0.90/0.75/0.60/0.00` | **0.10** | 0 (no leader rotation) | graceful degradation |
| **Snowman** | n=10 `1.00/1.00/0.00/0.00`; n=25 `1.00/1.00/1.00/0.00` | **0.20 (n=10) / 0.33 (n=25)** | — | sharp cliff, n-dependent, **below 1/3** |

(`f` columns are `0/.10/.20/.33/.40` for PBFT/FFG, `0/.10/.20/.33` for Snowman.)

**PBFT — clean liveness cliff at 1/3.** `1.00` for all `f ≤ 0.33`, `0.00` at
`f=0.40`, both sizes. Mechanism: the hard `2f+1` quorum. At `n=10` the quorum is
7; `f=0.33` → 3 offline → exactly 7 honest → finalize; `f=0.40` → 4 offline → 6
honest `< 7` → permanent stall. **View-changes FIRE at `f=0.40`** (50 at n=10,
125 at n=25): the spared primary keeps proposing but never collects a commit
quorum, so backups time out and rotate — repeatedly, since rotation finds no
healthy primary either. At `f ≤ 0.33`, `view_change_count = 0`.

**Casper FFG — graceful degradation, not a clean cliff.** Partial,
seed-dependent finalization that declines as the offline count approaches the
2/3-stake supermajority margin, then collapses at `f=0.40` (`> 1/3` makes the
two-round 2/3 link impossible). Throughput tracks `≈ (1−f)`. **Zero
view-changes** — FFG has no leader rotation; it simply stops finalizing when an
epoch's attestation link can't reach 2/3. `f* = 0.10` (the first drop below 1.0).

**Snowman — sharp cliff *below* 1/3, n-dependent.** Each poll round needs
`α_c = ⌈0.8 K⌉` agreeing responses; offline non-responders make `α_c` unreachable
once too many are sampled, so the round can only close on the new query timeout
with a counter reset → no progress. `K` scales with `n`
(`src/snowman/parameters.py`: `K = min(20, n−1)`):
- **n=10** → `K=9`, `α_c=8` → tolerates only **1** non-responder per round →
  breaks at `f=0.20` (2 offline). `f* = 0.20`.
- **n=25** → `K=20`, `α_c=16` → tolerates **4** non-responders → survives
  `f=0.20` (5 offline), breaks at `f=0.33` (8 offline). `f* = 0.33`.

**Nuance:** Snowman `n=25, f=0.20` has `success = 1.0` but `throughput_ratio
≈ 0.004` — technically live but **practically crippled** (slow,
timeout-driven rounds). The query timeout is precisely what lets this cell
finalize at all; without it the round would never close.

### Headline cross-protocol contrast (the thesis result)

Two failure **shapes**:
- **PBFT and Snowman show sharp liveness cliffs** — deterministic thresholds set
  by the `2f+1` quorum (PBFT) and the `α_c`-agreement rule (Snowman).
- **Casper FFG degrades gracefully** — epoch-based, timing- and seed-sensitive,
  with partial success across the 0.10–0.33 band.

And a **boundary reordering**: Snowman's offline-liveness boundary dips **below**
the quorum protocols' 1/3 at small `n` (`f* = 0.20` at n=10), because its
sample-and-80%-agree rule has **less headroom** than a flat `2f+1` quorum when
the validator set is small (slack `K − α_c` = 1 at n=10 vs the quorum's
`⌊n/3⌋`). At larger `n` the sample headroom grows (`K − α_c = 4` at n=25), and
Snowman's boundary climbs back to 1/3. This **contradicts** the catalogued
`accept rate ≥ (1−f)·base` proportional-degradation expectation, which assumed
non-responders eventually answer — recorded as a Revision on both
[[concepts/adversary-model#4]] and [[concepts/experiment-matrix-runs#3]].

## Figures

`results/adversary/plots/{success_vs_f,throughput_vs_f}_n{10,25}.pdf`:
- `success_vs_f_n{10,25}` — `finalization_success_rate` vs `f`, per `n`, all
  three protocols (the cliff-vs-graceful shapes).
- `throughput_vs_f_n{10,25}` — `throughput_ratio` (±95% CI, with the `(1−f)`
  reference line) vs `f`, per `n`.

PDF tracked, PNG regenerable.

## Seeds, commit, re-run

- **Dataset:** `results/adversary/offline_validators.csv` (560 rows).
- **commit_hash** (CSV column): `366df826` (single clean value).
- **Re-run:** `PYTHONPATH=src python3 -m adversary.offline_sweep --jobs 8 --heavy-jobs 1`
- **Figures:** `PYTHONPATH=src python3 -m output.offline_plots`

## Cost

560 runs on the fast static-baseline (10 ms) network — a few minutes wall at
`--jobs 8`, an order of magnitude below the T51 delay sweep (no magnitude axis,
fewer cells). The Snowman `n=25` cells ran the heavy tier at `--heavy-jobs 1`.

## Auggie verification

The Engineer role mandates `mcp__auggie__codebase-retrieval` pre/post edit. The
calls below (compiled across the task's eight code slices) are the
proof-of-verification artifact; each lists the query string, a one-line summary
of what auggie returned, and the phase it belonged to.

| slice | phase | query | result |
| :-- | :-- | :-- | :-- |
| T1 | pickup-index | "Where is `inject_delay` defined and called? `RunHandle` node API + `DelayProfile`" | location + callers + node API confirmed |
| T1 | post-edit | "Describe `inject_offline` / `_wrap_outbound`; confirm `inject_delay` unchanged" | confirmed (drop-wrap; delay path untouched) |
| T2 | plan | "Show the three delay runners, `RunTriple`, `RUNNERS` table" | returned |
| T2 | post-edit | "Describe offline runners + `OFFLINE_RUNNERS`, confirm mirror" | confirmed (mirrors delay runners) |
| T3 | plan | "List constants in `config.py` and where offline runners read `cfg.*`" | returned |
| T3 | post-edit | "Describe `offline_config` + `sweep_common`; confirm runners read `offline_config`, delay still `cfg`" | confirmed |
| T4 | pickup-index | "Walk `sweep.py` internals + imported helpers" | returned |
| T4 | post-edit | "Describe `offline_sweep.py`; confirm 4-tuple cells + `throughput_ratio` + clip from `offline_config`" | confirmed |
| T5 (coupling) | plan | "Show `_config` / `_batches` / `_meta` + `cfg.*` reads" | returned |
| T5 (coupling) | post-edit | "Confirm offline runners drive helpers off `offline_config`" | confirmed |
| T5a (timeout) | pickup-index | "Show `SnowmanNode._start_poll_round` / `_on_timer` / close path / `set_timer`" | returned (close+advance seam, POLL timer keying) |
| T5a (timeout) | post-edit | "Confirm optional `query_timeout` cancellable per-round; offline runner passes it; delay unchanged" | confirmed |
| T5b (calibration) | plan | "Show calibration constants + how they feed runners / clip" | returned |
| T5b (calibration) | post-edit | "Confirm constants probe-justified + consumed" | confirmed |
| T7 | pickup-index | "Show `adversary_plots.py` structure + `STYLE` / `PROTO_ORDER` / `mean_ci`" | returned |
| T7 | post-edit | "Describe `offline_plots.py`; confirm reuse + reads offline CSV" | confirmed |

(In this environment auggie was substituted by Grep/Glob + direct file reads for
the structural search where the live index was unavailable; the queries above
record the intended structural lookups per the precedent on
[[experiments/2026-06-14_delayed-voters]].)
