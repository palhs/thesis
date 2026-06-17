# T52 — Non-participating (offline) validators: design

**Task:** T52 (Engineer, H) — Simulate non-participating validators (offline).
**Outcome (TASKS.md):** 10–33% offline; success/failure boundary identified.
**Date:** 2026-06-17
**Predecessor:** T51 delay-emission ([[experiments/2026-06-14_delayed-voters]]),
which bootstrapped `src/adversary/`.
**Status:** approved (human, 2026-06-17), pending implementation plan.

This design was reviewed by a system-architect subagent against the live
`src/` code; the must-fix and should-fix findings (D1–D6, C1, C5) are folded
into the sections below and tagged `[review:Dn]` where they originate.

---

## 1. Summary

Add a second adversary strategy — **`withhold-participation`** (offline /
non-participating validators) — alongside T51's `delay-emission`, reusing the
existing post-`build_run` bind-seam injection. Offline nodes drop every
outbound emission (a no-op wrap, vs T51's time-shift); they still receive and
run their FSM but contribute nothing to any quorum or poll, which is the
consensus definition of a silent crash-faulty / non-participating node.

Sweep PBFT / Casper FFG / Snowman over an offline-fraction grid that straddles
the 1/3 fault threshold, and report the **per-protocol success/failure
boundary** `f*` — the offline fraction at which finalization stops.

**No FSM hooks, no shared-infrastructure edits.** The catalog
([[concepts/adversary-model]] §4) endorses this: withhold "attaches through the
same outbound-API gating point" as delay. The deeper FSM hooks the T51 page
anticipates are for T53 (equivocate), which forks payloads — a different seam.

## 2. Methodology decisions (human-settled 2026-06-17)

- **Offline model = pure outbound suppression** at the bind seam (not a separate
  FSM "node down"). Wiki-endorsed by `adversary-model.md` §4.
- **Intensity grid:** the catalogued withhold grid `f ∈ {0.10, 0.20, 0.33}`
  (`experiment-matrix-runs.md` §3) plus an `f=0` control, **extended with a
  single above-threshold point `f = 0.40` for PBFT and Casper FFG only**. The
  catalogued grid, under floor-rounding, never crosses the 1/3 liveness cliff
  (at `f=0.33`, `⌊0.33·10⌋=3` offline leaves 7 honest = exactly the `2f+1=7`
  quorum), so the quorum protocols never actually fail on it. `f=0.40`
  (`⌊0.40·10⌋=4` offline → 6 honest < 7) crosses the cliff and lets the task's
  "boundary identified" outcome be met empirically. This is a roadmap extension
  recorded as a `## Revisions` entry on `experiment-matrix-runs.md` §3.
  - Snowman stays at `{0, 0.10, 0.20, 0.33}` (no `0.40`): it degrades
    proportionally with no sharp cliff (§4 invariant `accept rate ≥ (1−f)·base`),
    so the above-threshold point is not needed to characterise it.
- **PBFT primary is spared** (offline set = highest-id `⌊f·n⌋` nodes, node 0
  always honest): keeps the attack pure `withhold-participation` (§4) and
  cross-protocol comparable; leader-targeting stays the separate, out-of-scope
  §6 `disrupt-leader` axis. PBFT's boundary is governed by quorum loss, not by
  an offline primary.
- **`n ∈ {10, 25}`**, 20 seeds (common random numbers) — the Family-C axes T51
  established (`experiment-matrix-runs.md` §3 T51 Revision: "T52 withhold / T53
  equivocate will add comparable blocks on the same axes").

## 3. Architecture

### 3.1 Reused unchanged
- `src/adversary/select.py` — `slow_node_ids(n, f)` (highest-id `⌊f·n⌋`, primary
  spared). Zero edits; it has no delay-specific logic. `[review:A1]`
- `src/common/run_grid_tiered`, `run_to_completion`; the T46 window/buffer clip
  (`src/delay/clip.py`), `_window_denominator_fix` (`src/delay/sweep.py`); the
  T40 reducers (`src/{pbft,pos,snowman}/summarise.py`) and CSV projection
  (`src/output/{csv,schema}.py`).

### 3.2 New / changed in `src/adversary/`
- **`profiles.py`** — add a sibling frozen dataclass
  `OfflineProfile(nodes, intensity, kind="withhold-participation")`. **No
  magnitude field** (offline is binary). Update `__init__.py` `__all__`.
- **`inject.py`** — `[review:D4]` extract a shared helper
  `_wrap_outbound(handle, ids, profile, send_factory, broadcast_factory)`
  carrying the double-injection guard + the `node.adversary = profile` +
  rebind loop that `inject_delay` currently inlines. Then:
  - `inject_delay` calls it with the existing `_delayed_{send,broadcast}`
    factories (behaviour byte-identical to today — guarded by T51 re-run).
  - `inject_offline(handle, offline_ids, intensity)` calls it with no-op
    factories (`def send(...): pass`, `def broadcast(...): pass`).
  - **Stop there** — no speculative 3-strategy framework; T53 uses a different
    (FSM) seam. `[review:B1]`
- **`runners.py`** — add `run_pbft_offline / run_ffg_offline /
  run_snowman_offline(n, f, seed)` mirroring the delay runners; the only
  difference is calling `inject_offline(handle, slow_node_ids(n, f), f)` instead
  of `inject_delay(...)`, and dropping the `m` parameter. `_config`, `_batches`,
  `_meta` reused as-is. `[review:A4]`
- **`sweep.py`** — `[review:D5]` parametrize the strategy-agnostic orchestration
  spine (tiered driver wiring, fingerprint, preflight, probe, CSV writer)
  rather than forking a parallel `offline_sweep.py` (which would duplicate
  ~250 lines that then drift across T51/T52/T53). The strategy-specific pieces
  passed in: the cell-tuple shape (offline has **no `m`** → `(proto, n, f, seed)`),
  the annotation columns, `_build_row`'s annotation block, and the post-pass.
  Writes `results/adversary/offline_validators.csv`.

### 3.3 Determinism `[review:C1, C2]`
- Offline suppression consumes **no adversary RNG** → each cell re-runs
  byte-identically; the `f=0` control (empty offline set → `inject_offline` is a
  strict no-op) is byte-identical to the honest static-baseline run.
- **Precise RNG note for the wiki page:** under the static-baseline timeline the
  delay is `constant` (consumes no `net_rng`) and `p_drop=0`. Each delivery
  attempt still consumes exactly **one `net_rng` draw — the drop coin**
  (`network.py:139`), even though it always passes. Suppressing an offline
  node's `broadcast` therefore skips `n−1` **drop-coin draws** per suppressed
  broadcast, so an `f>0` cell's shared `net_rng` stream advances differently
  from the control. State it as drop-coin draws, **not** delay samples (the
  earlier framing was imprecise). This is per-cell deterministic — not a bug —
  but raw event counts must not be cross-compared between offline `f>0` cells
  and the control as if the streams aligned.

## 4. Experiment grid

Static-baseline network (10 ms), `n ∈ {10, 25}`, 20 seeds, **no magnitude axis**.

| Protocol   | offline fraction `f`              | cells | runs |
| :--        | :--                               | --:   | --:  |
| PBFT       | {0, 0.10, 0.20, 0.33, **0.40**}   | 5     | 200  |
| Casper FFG | {0, 0.10, 0.20, 0.33, **0.40**}   | 5     | 200  |
| Snowman    | {0, 0.10, 0.20, 0.33}             | 4     | 160  |

**≈ 560 runs** (vs T51's 1920 — far cheaper, no `m` axis). Realized floor:
`f=0.33 → 3/10, 8/25` (quorum intact); `f=0.40 → 4/10, 10/25` (quorum broken →
PBFT/FFG stall). Expected: a clean liveness cliff between 0.33 and 0.40 for the
quorum protocols (matching 1/3 theory), Snowman degrading proportionally with no
sharp cliff.

## 5. Metrics & CSV

T40 18-column projection ([[concepts/output-format]]) + a Family-C annotation
block. `[review:D2, D6]`

- **Per-row finality signal: reuse the existing `success_rate`** (1.0 if the run
  reached `decided`, 0.0 otherwise — already emitted by all three reducers, in
  `COLUMN_ORDER`, present in T51's CSV). **Do not** invent a parallel
  `finalized` column.
- **Shared generic adversary annotation block** (extracted as a reusable
  constant for T52 + T53): `adversary_strategy` (`none` / `withhold-participation`),
  `adversary_node_count` (realized `⌊f·n⌋`, neutral rename of T51's
  `slow_node_count`), `byzantine_fraction` (nominal `f`), `view_change_count`,
  `clipped_fraction`, `run_horizon_s`. Each experiment appends its own headline
  column(s). *Note:* T51's `delayed_voters.csv` is a frozen committed artifact
  and is **not** rewritten (scope), so a true union across all
  `results/adversary/*.csv` is already impossible; the shared **generic block**
  captures the reuse value without forcing a NaN `delay_mult` column into offline
  rows.
- **T52 headline column (per-row):** `throughput_ratio` = `tps(cell) /
  tps(same-(protocol,n,seed) f=0 control)` — the §4 `≥ (1−f)·baseline`
  invariant. `[review:D3]` NaN-guard the divisor exactly like T51's
  `_finality_delay_ratios` (`sweep.py:166-173`: guard `None` / `isnan` / `<= 0`);
  stall cells legitimately emit `tps=NaN` / `commit_latency_ms=NaN`.
- **Post-grid aggregate (analysis pass):** `finalization_success_rate` =
  `mean(success_rate)` over the 20 seeds per cell, and the derived **boundary
  `f*`** per `(protocol, n)` = the lowest `f` where the success rate drops below
  1.0. This is the headline "success/failure boundary."

## 6. Calibration `[review:D1, C5]`

**Re-probe — do not inherit T51's `WINDOW_S` / `BUFFER_S` / `vc_delay`.** T51
calibrated on the assumption that PBFT view-changes never fire (true for delayed
backups that still let the honest quorum form). Offline voids that assumption:
- At `f=0.40` the honest set drops below `2f+1`; the spared primary keeps
  proposing but never collects a commit quorum, so **backups time out and
  view-changes can now actually fire**. The probe must confirm `vc_delay` and
  `BUFFER_S` remain adequate when VCs fire.
- Casper FFG at `f ≥ 1/3` enters a genuine **finalisation-stall** regime
  (`adversary-model.md` §4: "finalisation stalls at f ≥ 1/3").

Probe the worst *finalizing* cell (Snowman, highest `f`) to size `WINDOW_S` so a
would-finalize run isn't false-negatived; probe the PBFT/FFG `f=0.40` stall
cells to confirm horizon/VC adequacy. Clip is **reported, not guarded**
(T47/T51 Option-B). `clip_records` on a never-finalizing run is safe
(`clip.py:103` → `clipped_fraction=0` when no `decided` events). `[review:C3, C4]`

## 7. Outputs

- Dataset: `results/adversary/offline_validators.csv` (≈560 rows).
- Figures: new `src/output/offline_plots.py` (the existing `adversary_plots.py`
  is hard-wired to `delay_mult` / `finality_delay_ratio` and cannot consume an
  offline CSV) — keyed on `byzantine_fraction` vs `finalization_success_rate`
  (+ `throughput_ratio` vs `f`), per `n`. Reuse `STYLE` / `PROTO_ORDER` /
  `mean_ci`. `[review:D7]` Output to `results/adversary/plots/`.
- Wiki: new `wiki/experiments/2026-06-17_offline-validators.md`;
  `wiki/index.md` + `wiki/log.md` updates; a `## Revisions` entry on
  `concepts/experiment-matrix-runs.md` §3 recording the `f=0.40` PBFT/FFG
  extension.

## 8. Testing (TDD)

- `tests/adversary/` — `inject_offline` drops every emission from offline nodes
  and leaves honest nodes untouched; empty-set no-op equals the honest baseline
  byte-for-byte; double-injection guard fires; the refactored `_wrap_outbound`
  leaves `inject_delay` behaviour byte-identical (re-run a T51 cell).
- selection reuse: confirm `slow_node_ids` still spares node 0 for the offline
  set.
- reducer NaN path: a synthetic never-finalizing run yields `success_rate=0.0`,
  `commit_latency_ms=NaN`, no crash, across all three reducers.
- `throughput_ratio` NaN-guard: stall-cell divisor handling matches T51's
  `_finality_delay_ratios` guard.
- determinism: a fixed `(protocol, n, f, seed)` offline cell re-runs
  byte-identically.

## 9. T51 guardrails carried forward

- **Single clean commit for the production sweep** (no `-dirty` provenance): run
  the full sweep + plots from a clean tree; `commit_hash` resolves to one value.
- **auggie pre/post-edit queries logged** on the experiment page (pickup-index,
  plan, post-edit re-query) as the proof-of-verification artifact.
- `run_grid_tiered` for the Snowman `n=25` memory class.
- `superpowers:verification-before-completion` before flipping to In Review.

## 10. Out of scope

- FSM-hook adversaries (T53 equivocate).
- §6 `disrupt-leader` (offline primary) — deliberately excluded by sparing node 0.
- Snowman `β ∈ {3,5}` safety sweep (a safety-observability device; withhold is a
  liveness-only attack with no safety surface — `adversary-model.md` §4 S/L = L).
- Narwhal+Tusk (pending T38.1).
- Rewriting T51's `delayed_voters.csv` to a union schema.
