# 2026-06-19 — Adversarial comparison tables & robustness ranking (T55)

Derived-analysis capstone over the three Family-C adversarial sweeps. **No new
simulation runs:** T55 synthesizes the committed T51/T52/T53 datasets and the
T54 `degradation_ranking.csv` into the cross-protocol *algorithm × adversary ×
metric* comparison and the per-adversary robustness ranking that Chapter 4 §4.4
(T56) draws on. The Family-C analog of T48's `delay_analysis.py`. Measurement
spec it reuses: [[concepts/adversarial-degradation-metrics]]. Scope: PBFT,
Casper FFG, Snowman (Narwhal+Tusk unimplemented — carried as explicit deferral
rows, T38.1).

## Inputs (source datasets + provenance)

| input | file | rows | commit_hash |
|---|---|---|---|
| delay (T51) | `results/adversary/delayed_voters.csv` | 1920 | `8b2d0bb0-dirty` |
| offline (T52) | `results/adversary/offline_validators.csv` | 560 | `366df826` |
| equivocate (T53) | `results/adversary/equivocating_nodes.csv` | 640 | `c18587d2` |
| T54 brackets | `results/adversary/degradation_ranking.csv` | 26 | — |

Each sweep: protocols `{pbft, casper-ffg, snowman}`, `n ∈ {10, 25}`, 20 seeds
(common random numbers). **Provenance caveat:** the T51 dataset was generated
off a dirty tree (`8b2d0bb0-dirty`); any delay-family figure carries that flag.
The analysis is a pure function of these committed CSVs (byte-stable output).

## Code + artifacts

- `src/output/adversary_comparison.py` — pure-stdlib reducers + the comparison
  and ranking builders. Reuses the T54 `f_max` brackets (`f_max_for`,
  `_liveness_fmax`) and the `load_adversary_rows` loader from
  `output.adversary_analysis`; no matplotlib (tables only — T54 already shipped
  the 6 figures).
- `tests/output/test_adversary_comparison.py` — 20 tests: synthetic reducer /
  ranking / structure cases, real-dataset locked numbers, the
  consumes-`degradation_ranking.csv` consistency check, CSV byte-stability +
  round-trip parseability.
- `results/adversary/adversary_comparison.csv` — 90 rows: the tidy long-format
  *algorithm × adversary × metric* summary (one row per `(adversary, protocol,
  n, metric)`) + 6 NWT deferral rows.
- `results/adversary/robustness_ranking.csv` — 24 rows: per-`(adversary, n)`
  ranking of the 3 protocols (18 measured + 6 NWT deferral).

## Commands to re-derive

```
PYTHONPATH=src python3 -m output.adversary_comparison   # writes the two CSVs + prints the ranking
make test-output                                        # 165 tests
```

Both CSVs are byte-stable (a pure function of the input CSVs; gated by
`test_*_byte_stable` + `test_csvs_round_trip_with_commas_in_notes`).

## Observation

The three protocols separate on a **different axis under each adversary, and no
protocol dominates across all three** — the RQ4 performance–security tradeoff
the table makes explicit:

- **delay-emission** (rank on full-liveness `f_max_hold`, finality-cost
  tiebreak): **PBFT ≈ Snowman ≫ Casper FFG**. PBFT and Snowman both hold full
  liveness to φ=0.30 (grid max), but Snowman pays a **~62× (n=10) / ~49× (n=25)
  time-to-finality blow-up** (sequential `K`-poll over slow responders) where
  PBFT is immune (1.0×) — so PBFT ranks #1, Snowman #2, both flagged tied on the
  liveness threshold. FFG keeps finality (1.0× on success) but its liveness dips
  (worst pooled success 0.60), ranking it last.
- **withhold-participation** (rank on the **survival/collapse boundary**, not
  the full-liveness onset): **PBFT ≈ Casper FFG > Snowman**. PBFT and FFG both
  survive (finalize at all) to the 1/3 quorum cliff at φ=0.40 — PBFT with no
  degradation, FFG gracefully decaying (throughput ≈ 1−φ, worst surviving ≈0.49)
  — so they tie on survival depth (PBFT #1 on the throughput tiebreak). Snowman
  cliffs early and n-dependently (survives only to φ=0.10 at n=10 / 0.20 at
  n=25, with an `α_c`-starvation cell at n=25 φ=0.20 that is *alive but at 0.4%
  throughput*), ranking last.
- **equivocate-vote** (rank on safety `f_max_hold`): **Snowman > Casper FFG >
  PBFT**. All three tolerate equivocation to φ=0.33 (tied on the hold edge), but
  differ in **failure kind** past it: Snowman never breaks in-grid (probabilistic
  safety, ε ≈ 4.9·10⁻¹⁵ at n=10 / 3.3·10⁻¹¹ at n=25, witnessed by
  `snowman_epsilon_witness.csv`); FFG breaks *accountably* at φ=0.40 (≥1/3 stake
  becomes slashable, no in-model fork); PBFT breaks *catastrophically* at φ=0.40
  (a deterministic fork, `conflicting_instances`=229 at both n, unaccountable).
  PBFT's liveness "recovery" above 1/3 is that unsafe fork — flagged
  `safety_broken` so it is never read as resilience.

**Cross-adversary verdict:** PBFT wins delay & withholding but is the *worst*
under equivocation (the only unaccountable fork); Snowman wins equivocation-
safety but is worst under withholding and pays the largest delay-finality cost;
Casper FFG never wins but is the only protocol with *accountable* equivocation
safety. This is the RQ4 tradeoff §4.4 (T56) reports.

## Methodology note — onset vs survival, and why withholding ranks on survival

A withholding adversary degrades **liveness** (the ability to keep finalizing),
and there are two distinct ways to say "liveness failed". They give *opposite*
Casper FFG-vs-Snowman orderings, so the choice of key is load-bearing:

- **Onset** — `liveness_f_max_hold` (the T54 bracket): the largest φ at which the
  protocol still finalizes on *every* run (`success_rate = 1.0`). Answers *when
  does degradation first begin?*
- **Survival** — `liveness_survival_phi`: the deepest φ at which the protocol
  still finalizes *at all* (`success_rate > 0`). Answers *when does liveness
  collapse entirely?*

Worked example (offline, n=10), mean `success_rate` per φ:

| φ | PBFT | Casper FFG | Snowman |
|---|---|---|---|
| 0.10 | 1.00 | 0.85 | 1.00 |
| 0.20 | 1.00 | 0.75 | 0.00 |
| 0.33 | 1.00 | 0.60 | 0.00 |
| 0.40 | 0.00 | 0.00 | — |

- by **onset**: PBFT 0.33 > Snowman 0.10 > FFG 0.0 → **FFG last**;
- by **survival**: PBFT 0.33 ≈ FFG 0.33 > Snowman 0.10 → **FFG second (tied with PBFT)**.

FFG degrades *early* (it loses full liveness already at φ=0.10) but never
collapses until φ=0.40 — as deep as PBFT and deeper than Snowman (which collapses
at 0.20). The **onset** key therefore ranks FFG **last precisely for degrading
gracefully**, while *rewarding* Snowman's perfect-then-cliff brittleness — which
is backwards for a robustness verdict, where graceful degradation is the virtue
and a high-then-sudden-death curve is the fragility. T55 ranks withholding on
**survival** (the faithful "where liveness fails", and T48's Family-B
survival-depth convention).

The onset bracket is **not discarded**: it is carried on every comparison and
ranking row as `liveness_f_max_hold` / `f_max_break` (and `survival_phi`), so
"FFG degrades first" stays visible right next to "FFG survives deepest" — the two
columns together tell the graceful-vs-cliff story that one scalar cannot, and a
reader can re-rank by onset if they want the *onset-of-degradation* question
instead of the *total-collapse* one.

Why the shapes differ: FFG keeps finalizing with fewer participants, just slower
(throughput ≈ 1−φ); Snowman's sampled supermajority `α_c` needs enough responsive
validators per poll, and below that threshold the poll never completes → a hard
stall (cliff); PBFT's `2f+1` quorum is exact — fine until the quorum cannot form
at the 1/3 boundary, then dead.

**delay** (no protocol collapses in-grid — worst FFG ≈0.6, never 0) and
**equivocate** (safety, not liveness, is the threat) keep their `f_max_hold`
keys; only withholding switches to survival. Each ranking row carries `ranked_on`
+ `rank_value` so the basis of every verdict is explicit.

## Deferrals / follow-ups (flagged, not done here)

- **Narwhal+Tusk** — its 3 generic-capability pairs are unimplemented (T38.1,
  post-T55); carried as explicit deferral rows (`rank=""`, `f_max_*`=NaN, note
  cites T38.1) in both CSVs, never a silent NaN
  ([[concepts/output-format]] §4).
- **`results/adversarial/` (with `-al`)** — the T54/T55 task text spelling; all
  on-disk artifacts (T51–T55) use `results/adversary/`. T55 writes to the
  consistent `adversary/` dir; the `-al` spelling is treated as a task-text typo.
  Flagged for the human (same flag T54 raised).
- **`fork_rate` → `safety_violation_rate`** — T55 uses the concept name
  "safety-violation rate" and never introduces `fork_rate` as a concept; the
  literal source column is untouched (its rename is a separate schema task).

## Auggie verification

| phase | query (abridged) | one-line result |
|---|---|---|
| pickup-index | structural map of adversary_analysis (degradation_ranking columns, f_max/liveness reducers), the T48 delay_analysis/delay_plots ranking template, the raw sweep CSV schemas, the output test conventions + Makefile | located degradation_ranking.csv (26 rows) as the primary input, the T48 RankRow/_RANK_FIELDS template to mirror, the 3-tier test pattern, and `make test-output` (suite pre-registered) |
| post-edit (initial) | describe new adversary_comparison behavior; locate importers; confirm adversary_analysis/analysis/delay_analysis/plots unchanged | self-contained leaf — only its test imports it; reuses load_adversary_rows/f_max_for/_liveness_fmax + wilson via liveness_rate; no existing module changed |
| post-edit (final, after the survival-key + cleanup revision) | confirm final function/dataclass set + `_RANK_FIELDS`; that offline_survival_phi delegates to the generic survival_phi; that the sibling modules remain unbroken | confirmed 15-column `_RANK_FIELDS`, offline_survival_phi → survival_phi delegation, dead import removed, leaf status intact, T54/T48/T43 modules untouched |
