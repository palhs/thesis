# [2026-06-12] T47 — Heavy delay (1–5 s) + packet loss (5–20 %) (Family B)

Completes Family B's delay axis past the two moderate T46 timelines: a
heavy-tail delay regime (Pareto, E[delay] ≈ 3 s, mass in the 1–5 s band)
under no loss, plus the same regime under three packet-loss levels
(`p_drop ∈ {0.05, 0.10, 0.20}`). Measures how PBFT, Casper FFG, and Snowman
degrade — the headline being **`finalization_rate`** (does an instance that
started in-window still finalize, under loss?), with PBFT's **view-change
recovery** instrumented. The 6th Family-B timeline (`partial-sync-gst`) is a
deferred follow-up (TASKS.md Backlog 2026-06-12).

This page is the design contract the `src/delay/heavy.py` harness references.

## Locked methodology (Week 9 + human decisions 2026-06-12)

- **Protocols:** PBFT, Casper FFG, Snowman (Narwhal+Tusk / T38.1 blocked).
  Honest nodes, baseline workload.
- **Scope (human 2026-06-12):** heavy-tail + packet loss only. The
  `partial-sync-gst` two-phase / partition timeline is split off to a
  separate task (TASKS.md Backlog) — it measures GST recovery, a different
  story than delay/loss degradation.
- **Timelines (four, each one `network_phase_id`):**
  - `delay-heavy-tail` — `heavy_tail`, `scale = 1.0 s, shape = 1.5`. Pareto:
    `sample = scale · paretovariate(shape)`, `paretovariate ≥ 1`, so min
    sample = 1 s and `E[delay] = scale·shape/(shape−1) = 3.0 s`, with a long
    right tail (shape < 2 ⇒ infinite variance). `p_drop = 0` — the loss-free
    **control**.
  - `delay-heavy-tail-loss-p05 / -p10 / -p20` — the same Pareto delay under
    a per-phase Bernoulli drop of 0.05 / 0.10 / 0.20. The "5–20 % loss"
    sub-sweep ([[concepts/experiment-matrix-runs]] §2).
- **Sizes:** `n ∈ {10, 25}` (the locked Week-9 Family-B axis).
- **Seeds:** `0 … 19`, common random numbers across protocols at each
  `(timeline, n)` point.
- **FFG slot:** rescaled to **12 s** for the heavy regime
  (`slot ≥ 4·E[delay] = 12 s`, [[concepts/experiment-matrix-runs]] §2). PBFT
  propose cadence and Snowman slot cadence keep their native 1.0 s.
- **PBFT view-change ENABLED (human 2026-06-12):** `vc_delay = 90 s`,
  calibrated so an honest heavy-tail commit (~3 phases) does not rotate the
  leader but packet loss stalling an instance triggers recovery. T46
  suppressed view-change (`vc_delay = 10000 s`); T47 models PBFT's real
  recovery mechanism. Validated: `view_change_count ≈ 0` at `p_drop = 0`,
  `> 0` under loss.
- **Window/cost — Option B (human 2026-06-12):** `W` is capped at a
  tractable bound (`1000 s`) and the per-cell clipped-fraction is **reported,
  not guarded** (the T46 `< 5 %` self-check does not apply; under heavy delay
  the clip fraction on the slowest Snowman cells is itself a degradation
  signal). Vietnamese-language tradeoff discussion of the three options
  (grow-W / cap-W / fewer-seeds) was held in chat; the user chose cap-W.
- **Comparison column:** `commit_latency_ms` (uniform across all three),
  **not** `finality_latency_ms` ([[concepts/output-format]] §13).

## Buffer / clip rule

Identical to T46 ([[experiments/2026-06-10_delay-moderate]] §Buffer/clip):
run to `W + buffer`; an instance is in-window-started iff its first decision
lands by `W + one_round`; clip every event with `t > W`. The same pure
filter `src/delay/clip.py` is reused unchanged. Only the calibration
constants differ (below); under Option B the `clipped_fraction` is recorded
per cell rather than asserted `< 5 %`.

## Calibration (probe-derived)

Probe (`PYTHONPATH=src python3 -m delay.heavy --probe`): one seed per
protocol on the `delay-heavy-tail` control at `n = 10`. Probe-measured
first-decision latency (heavy-tail roughly decuples the T46 figures):

| protocol | first decision (probe) | `HEAVY_ONE_ROUND_S` (scope bound) |
| :-- | --: | --: |
| PBFT | ≈ 6.0 s | 20 s |
| Casper FFG | ≈ 61 s | 90 s |
| Snowman | ≈ 61 s | 120 s |

- **`W = 1000 s`** (Option-B cap). Gives ≫ 25 in-window decisions for every
  protocol (PBFT ~1000+, Snowman ~900 pipelined blocks) while keeping the
  Snowman event volume tractable.
- **`BUFFER = 150 s`** ≥ the slowest finalization tail, so an instance
  started just before `W` finalizes inside the horizon.
- **`t_max = W + buffer = 1150 s`** (the run horizon).

## Casper FFG source-checkpoint guard (robustness fix)

The heavy-tail probe surfaced a latent crash: `CasperNode._attest` guarded
its *target* checkpoint lookup but not the *source* one. Under heavy delay a
node can mark an epoch justified (from aggregated FFG votes) before that
epoch's checkpoint **block** has been delivered locally, so
`chain.checkpoint(highest_justified)` raised `KeyError` and aborted the run.
The guard is now symmetric: the node skips that slot's attestation gracefully
(emits `casper_rejected`, reason `source_checkpoint_unavailable`) and retries
on a later slot — the "finalisation simply stalls under delay" behaviour
[[algorithms/pos#behaviour-under-network-delay]] already describes, now
realised in code. **No-op under low delay** (source block always present), so
the T46 dataset and the honest baselines are byte-identical (107-test pos
suite green). Recorded as a `## Revisions` entry on [[algorithms/pos]];
covered by `tests/pos/test_node_attest_source_guard.py`.

## Output

The 18-column T40 projection + the 5 T46 Family-B annotation columns
(`network_phase_id`, `e_delay_ms`, `slot_duration_ms`, `clipped_fraction`,
`run_horizon_s`) + **four T47 columns**:

- `p_drop` — the per-phase Bernoulli drop probability.
- `finalized_instances` — distinct instances finalized in `[0, W]`.
- `view_change_count` — PBFT view-changes in `[0, W]` (0 for FFG / Snowman).
- `finalization_rate` — the headline. `finalized_instances` over the
  matched **control** (`delay-heavy-tail`, same `protocol/n/seed`)
  `finalized_instances`, clamped to `[0, 1]`; `1.0` for control rows, `NaN`
  if the control finalized nothing. Computed in a post-grid pass
  (`_finalization_rates`) so each per-cell function stays pure (the T46.1
  induction property). This operationalizes "fraction of in-window-started
  instances that finalize within W" using the loss-free run as the 100 %
  reference — exact when loss changes only *whether* in-window instances
  finalize, not *which* are started.

Written to **`results/delay/delay_heavy.csv`** (T46's `delay.csv` untouched;
T48 reads both). Checkpoints under `results/delay/.sweep_heavy/`.

- **Cells:** 3 protocols × 4 timelines × 2 `n` = 24 cell-classes. Seeds: 20
  for every class **except Snowman n=25**, capped at **8 seeds** (human
  2026-06-12 — it is the cost wall, ~5 GB / ~22 min per cell). So
  `(160 PBFT + 160 FFG + 80 Snowman-n10) + 32 Snowman-n25 = ` **432 runs**.
  Snowman n=25 carries wider CIs, flagged in §Results.

## Run strategy (memory-aware, after an OOM)

The first attempt at `--jobs 2` **OOM'd** after ~6 h: two concurrent Snowman
n=25 cells (~5 GB each, ~20–30 M `EventRecord`s materialized per cell)
exhausted the 16 GB machine and hung the worker `Pool`. Fix (human 2026-06-12,
"memory-aware scheduler now + streaming reducer as follow-up"):
`common.sweep.run_grid_tiered` ([[concepts/sweep-harness]] §9) runs the
Snowman n≥25 class at `--heavy-jobs 1` (one ~5 GB cell at a time) while the
light cells use full `--jobs` — byte-identical to `run_grid`, scheduling-only.
The deep O(1)-memory fix (streaming reducer) is a filed follow-up
(TASKS.md Backlog 2026-06-12), to land before the larger T51–T56 sweeps. The
resumable sidecars meant the OOM cost no recomputation — the run resumed from
where it died.

## Re-run

```
# Full 432-row sweep, memory-safe: light cells at --jobs, the Snowman n>=25
# class at --heavy-jobs 1 (one ~5 GB cell at a time — do NOT raise it on a
# 16 GB machine until the streaming-reducer follow-up lands).
PYTHONPATH=src python3 -m delay.heavy --jobs 6 --heavy-jobs 1
PYTHONPATH=src python3 -m delay.heavy --smoke --skip-snowman-n25   # fast sanity
PYTHONPATH=src python3 -m delay.heavy --probe       # calibration probe only
# writes results/delay/delay_heavy.csv; resumable (skip completed cells)
```

Tests (run-success + determinism evidence):

```
make test-delay        # tests/delay/{test_heavy_config,test_heavy_finalization,test_heavy_sweep}.py (+ T46)
make test-pos          # tests/pos/test_node_attest_source_guard.py (+ baselines)
make test-integration  # tests/integration/test_pbft_heavy_loss.py
```

## Results (means over seeds; Snowman n=25 over 8 seeds, rest over 20)

`finalization_rate` is the headline — finalizations as a fraction of the
loss-free control at the same `(protocol, n, seed)`. `vc@.20` is the mean
PBFT `view_change_count` at 20 % loss; `commit_ms` is the control →
20 %-loss `commit_latency_ms` (NaN once nothing finalizes in-window).

| protocol | n | fr@0 | fr@.05 | fr@.10 | fr@.20 | vc@.20 | commit_ms (0 → .20) |
| :-- | --: | --: | --: | --: | --: | --: | :-- |
| PBFT       | 10 | 1.00 | 0.169 | 0.161 | **0.104** | 30 | 7141 → 20311 |
| PBFT       | 25 | 1.00 | 0.533 | 0.211 | **0.056** | 75 | 7797 → 27874 |
| Casper FFG | 10 | 1.00 | 0.070 | 0.018 | 0.000 | 0 | 62005 → NaN |
| Casper FFG | 25 | 1.00 | 0.051 | 0.006 | 0.000 | 0 | 62123 → NaN |
| Snowman    | 10 | 1.00 | 0.195 | 0.000 | 0.000 | 0 | 71693 → NaN |
| Snowman    | 25 | 1.00 | **0.904** | 0.047 | 0.000 | 0 | 71205 → NaN |

Control `clipped_fraction` (reported, not guarded — Option B): PBFT ≈ 2.1 %,
FFG ≈ 7.0 %, Snowman ≈ 14 %. All control rows finalize fully (`fr = 1.0`);
all `vc` at `p_drop = 0` are 0 (no spurious view-change — the `vc_delay = 90 s`
calibration holds).

## Observations

**Resilience ranking under packet loss: PBFT > Snowman > Casper FFG.** Only
PBFT finalizes anything at 20 % loss (`fr` 0.06–0.10); FFG and Snowman both
hit zero. This is RQ4's headline and it traces to *recovery mechanism*, not
raw speed.

- **PBFT survives loss via view-change.** As loss rises, stalled instances
  trip the per-instance view-change timer and the leader rotates —
  `view_change_count` climbs 0 → 16 → 30 (n=10) and 0 → 28 → 63 → 75 (n=25),
  exactly tracking the loss level. Recovery is not free: `commit_latency_ms`
  inflates ≈ 3–4× (7.1 → 27.9 s at n=25). PBFT trades latency for liveness
  and is the only protocol that keeps making progress under heavy loss.
- **Casper FFG is the most fragile.** A 5 % per-message drop already collapses
  it to `fr ≈ 0.06`; it is effectively dead by 10 %. Its 12 s slot couples
  finality to a supermajority (≥ 2/3 stake) of attestation *links*, and once
  enough attestations drop, no epoch justifies — there is no recovery path
  (no leader to rotate, no resampling). The source-checkpoint guard (above)
  converts what would have been a crash into this honest stall.
- **Snowman's loss-resilience scales with committee size — the clearest n=25
  payoff.** At n=10 (K=9) Snowman collapses at 10 % loss; at n=25 (K=20) it
  holds `fr = 0.90` at 5 % loss before cliff-collapsing at 10 % (0.047). More
  peers per `K`-poll means more redundancy against dropped query/response
  messages, so a larger committee tolerates low loss far better — but the
  `β=15` sequential-confidence requirement still cliffs hard once loss
  exceeds what resampling can absorb. Snowman's surviving blocks are also the
  slowest to finalize (130–220 s).
- **The n-axis (why n=25 was added) cuts three ways.** Larger committee
  *improves* loss-resilience for PBFT (0.169 → 0.533 at 5 %) and dramatically
  for Snowman (0.195 → 0.904 at 5 %), but slightly *worsens* it for FFG
  (0.070 → 0.051) — more attestation links to lose. Committee size is a
  resilience lever for the subsampling/leader-rotation protocols and a mild
  liability for the all-to-all attestation protocol.
- **Latency vs. liveness is the real axis here.** Heavy-tail delay alone
  (control) already separates the protocols (PBFT ~7 s, FFG ~62 s slot-bound,
  Snowman ~72 s from `β=15` sequential polls); loss then attacks *liveness*,
  and only PBFT's leader-rotation answers it. T48/T49 will turn the
  `finalization_rate` curves into the comparative degradation plot + ranking.

## Scope and deferrals

- **`partial-sync-gst`** (Family B's 6th timeline) is NOT in this task — see
  TASKS.md Backlog 2026-06-12. It is a two-phase async→partial-sync timeline
  with a partition that heals at GST, measuring recovery, not degradation.
- **Comparative plots + resilience ranking** are T48; **degradation
  analysis** is T49; **Ch. 4 delay section** is T50. This task lands the raw
  per-trial dataset + the harness.
- **Narwhal+Tusk** is T38.1 (blocked).

## Auggie verification

Per the Engineer protocol, every `mcp__auggie__codebase-retrieval` call made
during the task (query, one-line result, phase):

- **pickup-index** — query: *"structural map of the delay sweep harness:
  src/delay/sweep.py grid + common.sweep.run_grid; how network timelines /
  delay distributions (uniform/exponential/heavy_tail) are defined and where
  drop_rate / partition is set on the Network / Phase; the window/buffer/clip
  logic; the CSV schema + how success/fork are recorded; existing
  tests/delay and tests/integration drop-rate tests."* Result: mapped
  `src/delay/{config,runners,clip,sweep}.py`, confirmed the cell tuple
  `(protocol, timeline_name, n, seed)` driven through `run_grid`, the
  reducers + `_generic_cols` populate `success_rate`/`fork_rate`, and that
  `clip_records` takes `(window, one_round)` as args — establishing the
  parameterise-via-Calibration + self-contained-heavy.py architecture.
- **post-edit re-query** — query: *"describe the post-change behavior and
  locate all callers of (1) the new `runners.py` `Calibration` param on
  run_pbft/run_ffg/run_snowman, (2) the new `src/delay/heavy.py` module's
  exports + its imports from common.sweep / delay.clip / delay.runners /
  delay.sweep / output.csv / pbft, (3) the `CasperNode._attest` source-
  checkpoint guard + the `_reject` signature."* Result: confirmed the two
  3-arg `RUNNERS[proto](timeline, n, seed)` call sites (`delay.sweep._run_cell`
  + the T46.1 witness adapter) bind the default `T46` calibration so T46 is
  byte-identical; `heavy.py`'s imported symbols (`_DELAY_COLUMNS`,
  `_window_denominator_fix`, `PBFT_VIEW_CHANGE`, the reducers) all exist;
  `_attest` is reached only from the slot loop, and `_reject(self, t, reason,
  **fields)` matches the new `source_checkpoint_unavailable` call exactly — no
  stale callsite or broken reference.

## Cross-references

- [[experiments/2026-06-10_delay-moderate]] — T46, the moderate-delay
  precursor (the buffer/clip rule + the two T46 timelines this extends).
- [[concepts/sweep-harness]] — the resumable/parallel `run_grid` (T46.1) this
  sweep runs on; the induction covers the heavy_tail + `p_drop` param shapes.
- [[concepts/experiment-matrix-runs]] §2 — the heavy-tail / loss timeline
  catalog + the 12 s FFG slot pairing.
- [[concepts/network-model-phases]] §2/§3 — the `heavy_tail` distribution and
  the per-phase Bernoulli drop model.
- [[algorithms/pos]] §Revisions — the source-checkpoint guard.
- [[concepts/output-format]] §13 — `commit_latency_ms` as the cross-protocol
  latency column.
