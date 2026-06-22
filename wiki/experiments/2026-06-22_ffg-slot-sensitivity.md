# [2026-06-22] L-W10 H2(b) — Casper FFG slot-duration sensitivity sweep

A targeted sensitivity sweep that answers the methodology objection behind
L-W10 finding H2: is Casper FFG's apparent ~5× slower finality a PROTOCOL
property or an ARTIFACT of the as-run `slot_duration = 1 s` calibration? The
sweep varies FFG `slot_duration ∈ {0.5, 1.0, 2.0} s` at the as-run
`slots_per_epoch = 2`, `n = 10`, measures the canonical finality latency
`commit_latency_ms`, and characterises how the cross-protocol ordering
depends on the slot. It confirms FFG finality is exactly linear in the slot
(so the absolute number is calibration-set, not protocol-intrinsic) while the
qualitative finding — FFG finalises at coarser, epoch-granular latency at any
realistic slot cadence — is robust. Documentation/evidence only; no change to
any committed dataset or to the FFG implementation.

Sweeps the committed FFG slot-duration sensitivity range pinned by
[[concepts/metric-reconciliation]] §Calibration defaults (the `{0.5, 1, 2} s`
row), defended against the "knob-engineered" objection in the same page's
§Revisions [2026-06-22] H2 correction. Reuses the PBFT/Snowman ≈1000 ms
commit baseline from [[experiments/2026-06-03_scaling-baseline]] (cited, not
re-run). Feeds `drafts/ch4_results.md` §4.2.2.

## Configuration

- **Protocol:** Casper FFG (`src/pos/node.py` `CasperNode`), honest path,
  uniform stake.
- **Sweep grid:** `slot_duration ∈ {0.5, 1.0, 2.0} s` × `seed ∈ {0, 1, 2}` =
  9 runs. `slots_per_epoch = 2` (the as-run default), `attest_offset =
  slots_per_epoch // 2 = 1`.
- **`n`:** 10 validators (uniform stake 3.0 each). FFG finality is
  structurally `n`-invariant and seed-invariant — it depends only on the slot
  timer cadence and the attestation schedule, not on the workload RNG or on
  `n` beyond reaching the 2/3-stake quorum — so the grid is deliberately
  small (3 slots) with 3 seeds kept only to CONFIRM seed-invariance.
- **`t_max`:** 30 s — comfortably clears epoch-1 finality at the largest slot
  (`5 · 2.0 = 10 s`); several epochs finalise at every slot.
- **Network:** minimal constant delay (`1e-9 s`), the honest
  `static-baseline`-equivalent — satisfies the §Coherence constraint
  `E[delay] ≪ slot_duration` so attestations arrive within-slot.
- **Workload:** identical to the FFG baseline — `poisson` arrival,
  `offered_rate = 100` tx/s, `tx_bytes = 512`, `conflict_rate = 0.0`. Block
  content does not feed FFG finality timing; present only to keep the
  goodput/bytes columns populated.
- **Driver:** `src/pos/slot_sweep.py`, single process / sequential (no
  multiprocessing — parallel pools deadlock in the sandbox).
- **Commit hash:** `371236e` (recorded in the CSV `commit_hash` column;
  regenerate after commit for a clean-tree hash).

## Re-run

```
PYTHONPATH=src python3 -m pos.slot_sweep
# writes results/sensitivity/ffg_slot_sweep.csv (deterministic, byte-stable)

# Test (linear law + determinism + seed-invariance):
PYTHONPATH=src:tests/pos python3 -m unittest test_slot_sweep -v
# or: make test-pos
```

## Raw results

`results/sensitivity/ffg_slot_sweep.csv` (9 rows). Columns: `protocol, n,
slots_per_epoch, slot_duration_s, seed, commit_hash, t_max_s,
commit_latency_ms, expected_commit_latency_ms, finality_factor,
ratio_measured_over_5slot`.

## Sweep table

Measured epoch-1 `commit_latency_ms` (≡ FFG finality on the honest path),
identical across `seed ∈ {0, 1, 2}`:

| `slot_duration` (s) | measured `commit_latency_ms` | `5·slot·1000` (predicted) | ratio measured / `5·slot` |
| :---- | ----: | ----: | :----: |
| 0.5 | 2500.000001 | 2500.0 | 1.0000000004 |
| 1.0 (as-run) | 5000.000001 | 5000.0 | 1.0000000002 |
| 2.0 | 10000.000001 | 10000.0 | 1.0000000001 |

The `+1e-6 ms` tail is the single near-instant (`1e-9 s`) network hop on the
finality timestamp; the linear law `commit_latency_ms = 5 · slot_duration ·
1000` holds to that tolerance at every slot and every seed.

## Formula confirmation

Casper FFG time-to-finality of the first finalised epoch is

```
(2 · slots_per_epoch + attest_offset) · slot_duration
  = (2·2 + 1) · slot_duration                 # attest_offset = spe//2 = 1
  = 5 · slot_duration   seconds
```

The measured `commit_latency_ms` equals `5 · slot_duration · 1000` to a
`1e-6 ms` tolerance for every swept slot, and is byte-identical across the
three seeds — confirming finality is structurally deterministic and exactly
linear in the slot. The as-run `slot_duration = 1 s` is the `5000 ms` point.

## Robustness conclusions

1. **Linear, hence calibration-set not protocol-intrinsic.** FFG finality is
   exactly `5 · slot_duration` at `slots_per_epoch = 2`. The absolute ≈5000
   ms figure is set by the chosen slot length, not by anything intrinsic to
   the FFG protocol — pick a different slot and the absolute number moves
   linearly.

2. **Qualitative ordering is robust across the realistic range.** Across the
   committed sensitivity sweep `{0.5, 1, 2} s`, FFG finality spans
   **2.5–10 s**, which stays ABOVE the per-block protocols' ≈1000 ms commit
   (`commit_latency_ms ≈ 1000.000003 ms` for PBFT and Snowman across all `n`,
   [[experiments/2026-06-03_scaling-baseline]]) at every point. FFG only
   ties/beats them at sub-realistic slots. The qualitative finding — *FFG
   finalises at coarser, epoch-granular latency at any realistic cadence* —
   is therefore a STRUCTURAL property (epoch granularity: `~2` epochs of slot
   timers must elapse), not a single-point artifact of `slot = 1 s`.

3. **Crossover slot is below realistic slot times.** FFG ties the ≈1 s
   per-block commit when `5 · slot ≤ 1 s ⇒ slot ≤ 0.2 s`. A 0.2 s slot is
   below realistic slot cadences: Ethereum uses 12 s [8]; even fast chains
   use ≥ 0.4 s. So no realistic slot choice inverts the ordering — the
   reader's "the 5× was knob-engineered" objection does not survive the
   sweep.

## Wiki / draft links

- [[concepts/metric-reconciliation]] §Calibration defaults — pins the FFG
  `slots_per_epoch = 2` / `slot_duration = 1 s` defaults and the `{0.5, 1, 2}
  s` sensitivity-sweep range this experiment exercises.
- [[concepts/metric-reconciliation]] §Revisions [2026-06-22] — the L-W10 H2
  correction (calibration table reconciled to the as-run `2`/`1 s`); this
  sweep is the empirical evidence that the as-run gap is robust, not
  knob-engineered.
- [[experiments/2026-06-03_scaling-baseline]] — source of the PBFT/Snowman
  ≈1000 ms commit baseline cited in conclusion 2 (cited, not re-run).
- [[algorithms/pos]] — Casper FFG mechanism (two-round justify→finalise,
  epoch granularity).
- `drafts/ch4_results.md` §4.2.2 will cite this page for the slot-sensitivity
  robustness argument.

## Auggie verification

- **pickup-index** — query: *"FFG baseline runner in src/pos/baseline.py
  factory/workload pattern; CasperNode slot_duration/slots_per_epoch/
  attest_offset defaults in src/pos/node.py; how summarise.py derives
  commit_latency_ms; run_to_completion signature in src/common/runner.py"*.
  Returned the `baseline.py` `_factory`/`generate_batches` pattern, the
  `CasperNode.__init__` defaults (`slot_duration=1.0`, `slots_per_epoch=2`,
  `attest_offset = slots_per_epoch//2`), the `summarise()` epoch-1 median
  `commit_latency_ms` derivation, and the `run_to_completion(handle, *,
  t_max, logger)` signature. Located the constants `_SLOT_DURATION = 1.0`,
  `_SLOTS_PER_EPOCH = 2` to parameterise.
- **post-edit re-query** — query: *"describe src/pos/slot_sweep.py
  run_sweep/measure/write_csv/main, its imports, and any callers; confirm it
  does not shadow baseline.py/summarise.py/node.py symbols"*. Returned the
  new module's full surface and confirmed it imports only the public API,
  defines its own module-private helpers, is referenced solely by
  `tests/pos/test_slot_sweep.py`, and shadows no existing `src/pos` symbol
  (the per-module `_factory`/`_config`/`_meta` are independently scoped). No
  broken callsites.

## Verification summary

- New test `tests/pos/test_slot_sweep.py` — 6 tests, all pass (linear law,
  two explicit points, ratio-doubling, seed-invariance, crossover-below-
  realistic, as-run config).
- Existing `pos` suite — 115 tests pass (`make test-pos`), `integration`
  suite — 87 tests pass.
- Determinism — `results/sensitivity/ffg_slot_sweep.csv` byte-identical
  across two runs (sha256 `0bdc1d27…`).
