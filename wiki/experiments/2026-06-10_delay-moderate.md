# [2026-06-10] T46 — Moderate network delay (Family B, two timelines)

The first network-delay dataset: the three honest-path protocols (PBFT,
Casper FFG, Snowman) under two moderate-delay network timelines —
`delay-uniform` (uniform[100, 500] ms, mean 300 ms) and `delay-exponential`
(exponential mean 300 ms) — swept over two validator-set sizes
`n ∈ {10, 25}` at 20 seeds. Lands the first two of the six Family B (Delay)
timelines of [[concepts/experiment-matrix]] §3; the remaining four
(heavy-tail, loss, partial-sync-gst) are T47. Narwhal+Tusk is out of scope
(T38.1 blocked).

This page is the design contract the `src/delay/` harness references.

## Locked methodology (Week 9, human 2026-06-10)

- **Protocols:** PBFT, Casper FFG, Snowman only (Narwhal+Tusk / T38.1
  blocked). Honest nodes, baseline workload.
- **Timelines (this task, exactly two):**
  - `delay-uniform` — `uniform`, `low = 0.1 s, high = 0.5 s` (= [100, 500] ms,
    mean 300 ms; the "100–500 ms moderate" task framing).
  - `delay-exponential` — `exponential`, `mean = 0.3 s` (memoryless tail,
    same E[delay]).
  - Both have `E[delay] = 300 ms`, so Casper FFG `slot_duration = 1200 ms`
    (the §5 coherence rule `slot ≥ 4·E[delay]`); PBFT propose cadence and
    Snowman slot cadence keep their native `1.0 s`.
- **Sizes:** `n ∈ {10, 25}` — amends [[concepts/experiment-matrix]] §3's
  fixed `n = 10` for Family B. `n = 10` is the shared anchor with Family C;
  `n = 25` (`3f+1`, `f = 8`) amplifies delay degradation. Snowman
  `(K, α_c, β)` rescale with `n` automatically (`n = 25` → `K = 20`,
  `α_c = 16`, `β = 15`) per [[concepts/metric-reconciliation]] § Snowman
  parameter rescaling — `n = 25` is a normal input, not a margin case.
- **Seeds:** `0 … 19`, common random numbers across protocols at each
  `(timeline, n)` point ([[concepts/experiment-matrix]] §7).
- **Comparison column:** `commit_latency_ms` (uniformly defined for all
  three), **not** `finality_latency_ms` ([[concepts/output-format]] §13).
- **Family C (adversarial, T51–T56) stays at `n = 10`** — the symmetric
  Family-C-at-`n=25` extension is parked in `TASKS.md` Backlog (2026-06-10)
  and is **not** acted on here.

## Buffer / clip rule

Per the standing time-bounded-run decision ([[concepts/experiment-matrix]]
Backlog 2026-05-18) and the locked Week-9 rule:

> Run to `W + buffer`; `buffer ≥` one full protocol round; compute metrics
> for every block/epoch that **started** in `[0, W]` even if it finalizes
> in the buffer; clip events with `t > W`.

Implemented as a pure post-run filter `src/delay/clip.py`:

1. **Scope.** An instance is in-window-started iff its FIRST decision lands
   at or before `W + one_round` (the protocol's probe-measured one-round
   latency). Instances first decided later were proposed in the buffer —
   all their decided events are dropped.
2. **Clip (decided).** For an in-scope instance, decided events with
   `t > W` are the finalization tail spilling past the window; dropped from
   the per-event rate count, but the instance survives (its first,
   in-window decision is kept), so `commit_latency_ms` — the first
   in-window decision, always `≪ W` — is never perturbed.
3. **Clip (all events).** EVERY event with `t > W` is dropped — deliveries
   and timers, not only decided — per the locked rule's literal "clip
   events with `t > W`". This windows the overhead numerator
   (`consensus_msgs_per_acu`, `bytes_per_acu` count deliveries) to the same
   `[0, W]` as its decided denominator. Without it the deliveries span the
   full `528 s` horizon while decided spans the `480 s` window, inflating
   PBFT / Snowman overhead by the buffer ratio (`528/480 ≈ +10 %`) — a pure
   harness artifact, since per-instance message *count* is delay-invariant.
   (An earlier draft clipped only decided events; the inflation was caught
   in the T46 smoke run by comparing against the zero-delay baseline, and
   the fix — extend the time clip to all events — was confirmed by PBFT's
   overhead returning to exactly `2n`. Human decision 2026-06-11.)

`clipped_fraction = tail / (kept + tail)` over the in-scope instances is the
quantity the calibration self-check asserts is `< 5 %`. (Only decided
events count toward this guard; the all-events clip in step 3 is a separate
numerator-alignment concern.)

## Calibration (probe-derived, self-check)

Probe: 1 seed/regime, measure the one-round latency, then size the window
and buffer. Probe-measured one-round latencies (first decision time, seed 0,
`delay-uniform`, n=10):

| protocol | first decision (probe) | `ONE_ROUND_S` (buffer floor) |
| :-- | --: | --: |
| PBFT | ≈ 1.85 s | 2.0 s |
| Casper FFG | ≈ 6.20 s | 7.0 s |
| Snowman | ≈ 12.13 s | 16.0 s |

Snowman is the binding constraint on both axes (its `β = 15` sequential poll
rounds give a fat per-block tail). Sizing:

- **`W = 480 s`.** The clipped-fraction is `≈ round_latency / W`, so to hold
  it under 5 % for Snowman's ≈ 16 s tail needs `W ≳ 16 / 0.05 ≈ 320 s`;
  `W = 480 s` gives margin and `≫ 25` in-window decisions for every
  protocol.
- **`BUFFER = 48 s`.** `≥` one full protocol round so an instance started
  just before `W` still finalizes inside the run horizon; Snowman's heaviest
  exponential round at `n = 25` is the binding constraint.
- **`t_max = W + buffer = 528 s`** (the run horizon).

**Self-check result (the < 5 % guard):** PASS. Worst clipped-fraction across
all 12 cells × 20 seeds is **4.00 %** (Snowman, `delay-exponential`,
`n = 10`) — under 5 %. (The probe predicted the worst cell would be Snowman
exponential `n = 25`; the full sweep puts `n = 10` marginally higher —
4.00 % vs 3.85 % — but both clear the guard, so `W = 480 s` holds.)

`meta.t_max` is set to `W` (the measurement window), not the run horizon, so
the reducers' throughput denominator is the window. (See § Window
denominator below for the PBFT-specific correction.)

## Window denominator (PBFT correction)

The FFG and Snowman reducers divide throughput by `meta.t_max` (= `W`), so
after the clip they report rate over the window. The PBFT reducer
(`src/pbft/summarise.py`) divides `tps`/`goodput` by `result.now` — the
**run horizon** (`W + buffer = 528 s`), not the window. On a windowed delay
run this makes PBFT's throughput denominator ≈ 10 % larger than FFG /
Snowman's, breaking the cross-protocol throughput axis. The harness
re-bases PBFT `tps`/`goodput` onto `W` in `src/delay/sweep._window_denominator_fix`
— a harness-layer projection, no protocol-package change. It is a no-op for
FFG / Snowman (already window-based). On the zero-delay baseline this
divergence does not appear because PBFT's `result.now ≈ meta.t_max`.

## Configuration summary

- **Workload:** `poisson`, `offered_rate = 100` tx/s, `tx_bytes = 512`,
  `conflict_rate = 0.0` (the [[concepts/experiment-matrix]] §6 defaults),
  generated to cover the FULL `W + buffer` horizon so proposers never drain
  mid-run.
- **Cells:** 3 protocols × 2 timelines × 2 `n` × 20 seeds = **240 runs** →
  240 rows in `results/delay/delay.csv`.
- **Output:** the 18-column T40 projection (via the existing reducers) plus
  five Family-B annotation columns: `network_phase_id`, `e_delay_ms`,
  `slot_duration_ms` (the protocol's proposal cadence — FFG's rescaled to
  1200 ms), `clipped_fraction`, `run_horizon_s`.
- **No shared infrastructure modified.** Every knob (network `Phase`,
  `slot_duration`, `propose_delay`, `vc_delay`, `t_max`) is an existing
  `Node` / `Config` constructor argument. PBFT `vc_delay = 10000 s` so no
  honest run spuriously triggers a view-change under 100–500 ms delay.
- **Commit hash:** `2ef410f7` (embedded in `delay.csv`) — the `task 46:
  moderate network-delay sweep` commit that introduced the `src/delay/`
  harness and generated this dataset. A clean checkout of `2ef410f` + re-run
  reproduces it byte-identically. (The sweep first stamped `2c04ef76-dirty`
  from the uncommitted working tree; restamped to the clean commit hash
  post-merge — only the `commit_hash` column changed, the data is identical
  by the determinism contract.)

## Re-run

```
PYTHONPATH=src python3 -m delay.sweep            # full 240-row sweep
PYTHONPATH=src python3 -m delay.sweep --smoke    # 1 seed (fast sanity)
# writes results/delay/delay.csv; prints worst clipped_fraction + PASS/FAIL
```

Tests (run-success + determinism evidence):

```
make test-delay
# tests/delay/{test_config,test_clip,test_window_denominator,test_e2e}.py
```

## Results (means over 20 seeds)

`commit_latency_ms` is the cross-protocol latency column; `tps`/`goodput`
are window-rate; `msgs/ACU` is `consensus_msgs_per_acu`; `bytes/ACU` is
`bytes_per_acu`; `clip%` is the per-cell max `clipped_fraction`. All 240
rows honest: `success_rate = 1.0`, `fork_rate = 0.0` everywhere.

| protocol | timeline | n | commit_latency_ms | tps | goodput | msgs/ACU | bytes/ACU | clip% |
| :-- | :-- | --: | --: | --: | --: | --: | --: | --: |
| PBFT | uniform | 10 | 1947.5 | 9.97 | 99.9 | 19.81 | 47068 | 0.58 |
| PBFT | uniform | 25 | 2005.7 | 24.92 | 99.9 | 49.96 | 51617 | 0.62 |
| PBFT | exponential | 10 | 1895.6 | 9.97 | 99.9 | 19.81 | 47069 | 0.62 |
| PBFT | exponential | 25 | 1994.7 | 24.92 | 99.9 | 49.94 | 51599 | 0.62 |
| Casper FFG | uniform | 10 | 6341.9 | 4.13 | 99.1 | 10.86 | 113471 | 1.49 |
| Casper FFG | uniform | 25 | 6359.2 | 10.31 | 99.1 | 26.06 | 123873 | 1.49 |
| Casper FFG | exponential | 10 | 6282.1 | 4.13 | 99.1 | 10.70 | 113433 | 1.49 |
| Casper FFG | exponential | 25 | 6318.4 | 10.31 | 99.1 | 25.61 | 123777 | 1.49 |
| Snowman | uniform | 10 | 12624.1 | 9.75 | 97.7 | 274.15 | 58168 | 3.57 |
| Snowman | uniform | 25 | 12203.6 | 24.38 | 97.8 | 608.02 | 74637 | 3.50 |
| Snowman | exponential | 10 | 15332.3 | 9.46 | 97.3 | 277.07 | 59696 | 4.00 |
| Snowman | exponential | 25 | 13407.9 | 23.18 | 96.1 | 615.45 | 77551 | 3.85 |

Zero-delay baseline reference ([[experiments/2026-06-03_scaling-baseline]],
means): `commit_latency_ms` — PBFT 1000, Casper FFG 5000, Snowman 1000 (all
`n`); `consensus_msgs_per_acu` — PBFT 19.80 / 49.92, Snowman 270.9 / 600.96
(`n = 10 / 25`). FFG baseline `msgs/ACU` (12.26 / 29.28) is from a short run
and over-counts startup; see Observations.

## Observations

**Latency vs the zero-delay baseline — the headline is how differently the
three protocols absorb delay.**

- **PBFT: `1000 → ~1900–2000 ms` (≈ +0.9 s).** The three-phase commit pays
  roughly one network round-trip per phase, so under `E[delay] = 300 ms` it
  gains ≈ 0.9 s. Near-flat in `n` (1895 → 1995 ms from `n = 10 → 25`):
  gathering a `2f+1` quorum across more replicas adds little because the
  phases overlap in time.
- **Casper FFG: `5000 → ~6350 ms` (≈ +27 %), and this rise is
  slot-dominated, not network-dominated.** The §5 coherence rule rescales
  the FFG slot `1.0 → 1.2 s`, turning 5-slot finality into ≈ 6.0 s; the
  residual ≈ 0.3 s is attestation propagation. Flat in `n` and in timeline.
  This is the honest RQ1 finding flagged in [[concepts/experiment-matrix]]
  §5: FFG time-to-finality is governed by its slot clock, which we couple
  to the delay regime, so its delay sensitivity is indirect.
- **Snowman: `1000 → 12 200–15 300 ms` (≈ 12–15×) — by far the most
  delay-exposed protocol.** Its `β = 15` poll rounds are SEQUENTIAL, each a
  query→response round-trip costing ≈ `2·E[delay]` under load, so the 15
  rounds add ≈ 12 s. Roughly flat (even slightly lower) in `n`: the
  `K`-sampling rescales with committee size (`K = 20` at `n = 25`), so more
  validators do not lengthen first-block finality. This sequential-confidence
  cost is the central degradation result the T48/T49 ranking will turn on.

**Uniform vs exponential (same `E[delay] = 300 ms`, different tail).** PBFT
and FFG are nearly identical across the two timelines (≤ 3 %): their latency
is set by a fixed count of rounds/slots, so the distribution *shape* washes
out. Snowman is the exception — exponential runs ≈ 10–21 % slower than
uniform (`n = 10`: 15.3 vs 12.6 s) because the memoryless tail inflates the
slowest-of-`K` response that gates each round, and that tail penalty
compounds over the 15 sequential rounds. Where one protocol's finality is a
chain of "wait for the slowest peer", tail shape matters, not just the mean.

**Throughput and overhead — structural columns are delay-invariant, as
predicted.** `tps` scales ≈ linearly with `n` (≈ 2.5× from `n = 10 → 25`,
matching the validator-count ratio — it is a decision-event rate);
`goodput` stays flat at ≈ 96–100 tx/s (offered 100, no saturation — the
model has no capacity ceiling, consistent with the baseline). Per-ACU
message/byte overhead does NOT move with delay: PBFT lands exactly on the
zero-delay `2n` (19.81 vs 19.80 at `n = 10`; 49.96 vs 49.92 at `n = 25`) and
Snowman within ≈ 2 % — message *count* per instance is fixed by protocol
structure, not by network timing. The one apparent exception, FFG reading
≈ 10.8 vs its `12.26` baseline, is a run-length artifact, not a delay
effect: a control re-run at zero delay over the same `W = 480 s` horizon
also gives 10.85, because the short baseline run over-weights startup/genesis
deliveries; over a long window FFG overhead converges and is delay-invariant
like the others.

## Scope and deferrals

- **T47 timelines** (heavy-tail 1–5 s, packet loss 5–20 %,
  partial-sync-gst) are NOT in this task — only the two moderate timelines.
- **Comparative plots + resilience ranking** are T48; **degradation
  analysis** is T49; **Ch. 4 delay section** is T50. This task lands the raw
  per-trial dataset + the harness.
- **CIs / aggregated sibling file** follow the T44 pattern when T48 needs
  them; this task lands the long-format rows.
- **Narwhal+Tusk** is T38.1 (blocked).

## Auggie verification

Per the Engineer protocol, every `mcp__auggie__codebase-retrieval` call made
during the task (query, one-line result, phase):

- **pickup-index** — query: *"existing delay-experiment infrastructure: the
  DelayDist/Phase classes and how uniform/exponential are sampled;
  build_run, Config/SeedsConfig; run_to_completion; PBFTNode/CasperNode/
  SnowmanNode constructor kwargs; snowman_parameters(n) rescaling;
  ScenarioMeta/COLUMN_ORDER; output.csv _generic_cols/_format_row/
  _resolve_commit_hash; per-protocol summarise() reducers; EventRecord
  schema and whether decided events carry instance_id; workload
  generate_batches/WorkloadConfig."* Result: mapped the full dependency
  surface — confirmed `DelayDist("uniform"/"exponential", …).sample(rng)`,
  `build_run(config, global_seed, node_factory)`, the three node
  constructors' keyword-only knobs, and that `decided` events carry
  `instance_id` (PBFT `(view, seq)`, FFG epoch int, Snowman block_id),
  validating the clip's grouping key.

- **pickup-index (resume, 2026-06-11)** — query: *"resuming T46; verify the
  `src/delay/` harness against live infrastructure — reducer signatures
  `(records, result, meta)` and returned columns for pbft/pos/snowman
  summarise; `output.csv._generic_cols`/`_format_row`/`_resolve_commit_hash`;
  `output.schema.COLUMN_ORDER` + `ScenarioMeta` fields; how runners wire the
  delay `Phase` via `build_run`; confirm `decided` carries `instance_id`."*
  Result: confirmed the harness is coherent — the PBFT reducer divides
  `tps`/`goodput` by `result.now` (run horizon) so the window-denominator
  fix is genuinely needed, while FFG/Snowman already divide by `meta.t_max`
  (window); `decided` carries `instance_id`, validating both the clip key
  and the `_window_denominator_fix` opportunity count.
- **post-edit re-query (2026-06-11)** — query: *"clip_records now drops every
  event with `t > window_s` (not only decided); describe current behavior,
  locate all callers, and confirm no reducer relies on receiving
  delivery/timer events past the window."* Result: `clip_records` is called
  only from `delay.sweep.run_sweep`; all three reducers consume the stream
  by counting `len(deliveries)` / `len(decided)` over whatever records they
  are handed, so none breaks under the tighter clip — the change correctly
  windows both the delivery numerator and `bytes_per_acu`.

The `src/delay/` package was scaffolded in a prior session (untracked
working-tree state) referencing this page as its contract. This resume
session verified it against the live infrastructure, **found and fixed an
overhead-inflation bug** (the clip passed buffer-period deliveries through,
inflating PBFT/Snowman `consensus_msgs_per_acu` by ≈ 10 %; human-approved
fix to clip all events at `W`, see §Buffer/clip rule step 3), added a
delivery-clip unit test and updated the existing pass-through test, ran the
full 240-row sweep (parallelized into 5 deterministic
subsets merged through `write_csv`; seed-0 rows verified byte-identical to a
sequential control run), and filled this page's Results/Observations. The
`delay` suite is green (32 tests); `make test` green.

## Cross-references

- [[concepts/experiment-matrix]] §3 (Family B + the n∈{10,25} Revision), §5
  (FFG slot coherence), §6 (workload), §7 (seeds).
- [[concepts/experiment-matrix-runs]] §2 (the two timelines' parameters +
  FFG slot pairing), §4 (run-count budget Revision).
- [[concepts/output-format]] §13 — `commit_latency_ms` as the cross-protocol
  latency column.
- [[concepts/metric-reconciliation]] — per-protocol metric formulas +
  Snowman `(K, α_c, β)` rescaling.
- [[concepts/network-model-phases]] §2 — the delay-distribution catalogue.
- [[experiments/2026-06-03_scaling-baseline]] — the zero-delay baseline this
  delay dataset is read against.
