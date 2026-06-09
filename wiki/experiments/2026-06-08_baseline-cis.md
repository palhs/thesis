# [2026-06-08] T44 — Multi-seed aggregation, 95% CIs, and statistical meaning

Aggregates the T41/T70 dataset (300 trials = 15 scenarios × 20 seeds,
provenance `24a491a4`) into per-scenario means with 95% confidence
intervals, regenerates the T43 plots with CI error bars, and audits the
**accuracy and meaning** of the resulting statistics against each
protocol's base theory. No new simulation.

## Artifacts

- `src/output/aggregate.py` → `results/baseline/aggregated.csv` (15 rows;
  `<metric>_{mean,ci_lo,ci_hi,cv}`). Byte-identical on re-run.
- T43 plots regenerated with 95% CI bars (`output.plots`, no `--no-ci`).
- `tests/output/test_aggregate.py` (9 tests). `make test-output` 93/93 green.
- CI method: Student-t, `df = n_runs − 1 = 19`, `t₀.₉₇₅ = 2.093`.

## Seed adequacy

20 seeds per scenario (the §7 common-random-numbers set, [[concepts/experiment-matrix]]).
This sits inside the T44 target of 20–30 and is **more than adequate**:
the one metric with real variance (`goodput`) has a CI half-width of
≈ 1.0% of its mean (CV ≈ 2.2%); every other metric is deterministic, so no
seed count would narrow its (zero-width) CI.

## Statistical accuracy — the dominant finding

At the zero-delay honest baseline the simulator is **deterministic in every
structural metric**: `commit_latency_ms`, `tps`, `consensus/total_msgs_per_acu`,
`success_rate`, and `fork_rate` all carry CV = 0 across the 20 seeds (the
reported `1e-14 %` on latency is float-formatting noise). Their 95% CIs are
zero-width — a correct, meaningful result, not a defect: protocol timing and
message counts are fixed by `(protocol, n)`, and the only seeded randomness
is the Poisson workload, which perturbs only `goodput` (CV ≈ 2.2%). The CI
exercise therefore (a) confirms determinism and (b) bounds workload noise.

## Meaning of the statistics — interpretation caveats

1. **`tps` is a decision-event rate, not system throughput.** `tps/n` is
   constant per protocol (PBFT/Snowman 0.95, Casper FFG 0.40), so `tps ∝ n`
   exactly. It counts `decided` events (one per node per committed unit), so
   it scales with `n` by construction. The honest comparative throughput is
   **`goodput`** (committed tx/s), which is flat in `n`.
2. **Flat goodput = no saturation, by model design.** The latency-only model
   has no per-tx/byte cost or queue, so offered load below the cadence rate
   is always absorbed (`success_rate = 1.0` everywhere). Saturation
   throughput (`peak_tps`) needs a capacity model — deferred
   ([[concepts/output-format]] §13). Do not read flat goodput as a measured
   capacity ceiling.
3. **Flat latency = zero-delay artifact.** Latency is round/timer-bounded
   here; the `n`- and delay-driven latency story is W9 (T46–T50).
4. **`success_rate`/`fork_rate` are uninformative at the honest baseline**
   (all 1.0 / 0.0). They discriminate only under the W10 adversary.
5. **Cross-protocol latency uses `commit_latency_ms`**, never
   `finality_latency_ms` (PBFT-only client hop, [[concepts/output-format]] §13).
6. **`bytes_per_acu` is an order-of-magnitude estimate** ([[concepts/message-types]] §7).

## Comparison with base theory (per protocol)

| protocol | theory | measured | verdict |
| :-- | :-- | :-- | :-- |
| **PBFT** | `O(n²)` msgs/block; 3-round latency [[algorithms/pbft#communication-complexity]] | `total_msgs/acu → 2n` (per-n 1.875→1.997); commit flat ≈1000 ms | ✓ per-instance is `O(n²)`; the ACU denominator (n decisions/instance) absorbs one factor of n → `O(n)` per-ACU |
| **Casper FFG** | `O(n)` aggregated/epoch; 2-epoch finality [[algorithms/pos#communication-complexity]] | `msgs/acu ≈ 1.2n`; commit flat ≈5000 ms | ✓ one attestation round (cheaper slope than PBFT's two broadcast phases); ≈5 s ≈ 2.5 epochs at `slot=1 s, slots/epoch=2` |
| **Snowman** | per-validator `O(K·β)`, latency invariant to `n` [[algorithms/avalanche#parameters-and-communication-complexity]] | `total_msgs/acu ≈ 2·K·β` (ratio 1.002–1.005); commit flat ≈1000 ms | ✓ near-exact: the ×2 is query+response; growth over `n` is the **K-rescaling** `K=min(20,n−1)`, not an `n`-dependence — the `n`-independence is masked below `n≈21` where `K` still tracks `n−1` |

**Headline contrast (RQ3).** Per committed unit, Snowman costs an order of
magnitude more than PBFT (≈26× per node vs ≈2×) — the price of repeated
subsampling — while its latency, like PBFT's, is flat in `n`. The standard
Avalanche "n-independent cost" advantage is a **per-validator** statement;
the network-aggregate `total_msgs_per_acu` does not show it as flatness, and
the thesis-scale K-rescaling further hides it across `n ∈ {7…25}`. Chapter 4
states this explicitly so the comparison is not misread.

## Scope / deferrals

- Delay-axis CIs → T48–T50; adversarial → T55. `peak_tps` → capacity model.
- §11 register entry `*_ci_lo / *_ci_hi` flips `pending → live` (sibling-file layout).

## Auggie verification

`mcp__auggie__codebase-retrieval` unavailable (as prior pages); local
`grep`/`Read` used. Confirmed `aggregate.py` consumes only `analysis.py`
(stdlib) + the committed CSV, writes one sibling file, and has no caller into
the simulator core; `plots.py` is its only peer consumer of `analysis`.

## Revisions

**[2026-06-09]** The Casper FFG row of the base-theory table cites the
theory as "`O(n)` aggregated/epoch." This is the *Ethereum production*
(BLS-aggregated) cost, not the original Casper FFG paper [1], whose votes are
individually signed and counted with no aggregation (arXiv:1710.09437,
Table 1). The simulator follows the paper: every validator broadcasts its own
signed `ATTESTATION` all-to-all, so the attestation phase is `O(n²)` (measured
`9·n(n−1)` deliveries/window) and the measured `≈1.2n` per-ACU validates that
*un-aggregated* model — not an aggregated `O(n)` one. The slope sits below
PBFT's because of the rounds-to-decisions ratio (one attestation phase, more
decisions per round), not aggregation. See
[[algorithms/pos#communication-complexity]]; adding aggregation is future work
([`docs/plans/2026-06-09-casper-bls-aggregation.kickoff.md`](../../docs/plans/2026-06-09-casper-bls-aggregation.kickoff.md)).
