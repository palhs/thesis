# PoS proposer-selection fairness — T33

100-round empirical fairness check on the stake-weighted random proposer
introduced in T33 (`src/pos/selection.py`'s `stake_weighted_proposer`).
Build-verification only: confirms the selection rule's empirical
selection frequencies track each validator's stake share within an
absolute tolerance under a fixed seed, across four stake distributions.
Not a protocol experiment — the canonical PoS baseline that replaces the
T32 byte-identical event-stream snapshot under the new rule is T35.

## Configuration

- Code under test: `src/pos/selection.py` on branch
  `task/T32-pos-consensus`, parent commit `c8174dc` (T32 baseline).
  Commit hash for the T33 change `TODO(human)` — assigned when the
  branch is committed per `docs/workflow.md`.
- `global_seed = 42`; rounds = 100 consecutive slots `s ∈ [1, 100]`.
- Selection function: `stake_weighted_proposer(slot, stake_table, 42)`,
  pure of any per-node `Node.rng`; per-slot RNG seeded from
  `blake2b("42:<slot>")` (`src/pos/selection.py:_stable_seed`).
- Tolerance: per-validator absolute difference
  `|observed_fraction − expected_fraction| ≤ 0.10`. The 10-percentage-
  point bound is deliberately loose — 100 trials is a small sample, and
  a tight bound would couple the assertion to the seed rather than
  measure fairness. The assertion is fixed-seed, so the test never
  flakes.

### Distributions exercised

- **Uniform n=4.** `stake_table = {0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0}`;
  expected `0.250` per validator.
- **Uniform n=7.** `stake_table = {i: 1.0 for i in range(7)}`; expected
  `0.143` per validator.
- **Skewed 10/20/30/40.** `stake_table = {0: 10.0, 1: 20.0, 2: 30.0,
  3: 40.0}`; expected `0.100, 0.200, 0.300, 0.400`.
- **Heavy majority 60/13/13/14.** `stake_table = {0: 60.0, 1: 13.0,
  2: 13.0, 3: 14.0}`; expected `0.600, 0.130, 0.130, 0.140`. Confirms
  the majority validator dominates without crowding the minority
  validators out entirely.

## Re-run

```
PYTHONPATH=src:tests/pos python3 -m unittest test_selection -v
```

## Result

All four distributions land inside the `|Δ| ≤ 0.10` envelope; the
worst observed deviation is `0.067` (validator 2 in uniform n=7).

| Case | Validator | Stake | Expected | Observed | Δ |
| :-- | --: | --: | --: | --: | --: |
| Uniform n=4 | 0 |  1.0 | 0.250 | 0.230 | −0.020 |
| Uniform n=4 | 1 |  1.0 | 0.250 | 0.290 | +0.040 |
| Uniform n=4 | 2 |  1.0 | 0.250 | 0.210 | −0.040 |
| Uniform n=4 | 3 |  1.0 | 0.250 | 0.270 | +0.020 |
| Uniform n=7 | 0 |  1.0 | 0.143 | 0.160 | +0.017 |
| Uniform n=7 | 1 |  1.0 | 0.143 | 0.100 | −0.043 |
| Uniform n=7 | 2 |  1.0 | 0.143 | 0.210 | +0.067 |
| Uniform n=7 | 3 |  1.0 | 0.143 | 0.080 | −0.063 |
| Uniform n=7 | 4 |  1.0 | 0.143 | 0.140 | −0.003 |
| Uniform n=7 | 5 |  1.0 | 0.143 | 0.130 | −0.013 |
| Uniform n=7 | 6 |  1.0 | 0.143 | 0.180 | +0.037 |
| Skewed 10/20/30/40 | 0 | 10.0 | 0.100 | 0.120 | +0.020 |
| Skewed 10/20/30/40 | 1 | 20.0 | 0.200 | 0.170 | −0.030 |
| Skewed 10/20/30/40 | 2 | 30.0 | 0.300 | 0.270 | −0.030 |
| Skewed 10/20/30/40 | 3 | 40.0 | 0.400 | 0.440 | +0.040 |
| Heavy majority | 0 | 60.0 | 0.600 | 0.560 | −0.040 |
| Heavy majority | 1 | 13.0 | 0.130 | 0.160 | +0.030 |
| Heavy majority | 2 | 13.0 | 0.130 | 0.110 | −0.020 |
| Heavy majority | 3 | 14.0 | 0.140 | 0.170 | +0.030 |

Companion unit tests in the same module pin the boundary behaviour the
fairness check does not exercise: cross-call and dict-insertion-order
determinism (the cross-node-agreement contract), seed and slot
sensitivity (no silent constant-seed bug), the validator-set
range (returned IDs always live in `stake_table`), zero-stake
exclusion, and the four input-validation rejections (negative slot,
empty table, negative stake, all-zero stake).

## Observation

100 trials per validator is small — the standard error of an unbiased
estimator under a uniform 4-way draw is `sqrt(0.25 × 0.75 / 100) ≈
0.043`, so observed deviations up to ≈ `4σ ≈ 0.17` are statistically
plausible even for a perfectly fair sampler. The empirical sweep is
therefore a structural sanity check rather than a tight statistical
test: it would catch a gross off-by-one error in the weighting (e.g. a
validator with 60 % stake being selected 25 % of the time), but it does
not rule out subtler bias that only a many-seeds × many-slots Monte
Carlo would detect. That tighter sweep is out of scope for T33 — the
acceptance criterion in `TASKS.md` is exactly "fairness verified over
100 rounds," and the fairness check feeds the T35 baseline rather than
standing alone as a security result.

The largest observed deviation (`0.067` for validator 2 of uniform n=7)
lies well inside the `0.10` tolerance and is consistent with binomial
sampling variance under the small-sample regime above. The fairness
test therefore acts as a regression sentinel: any future change that
breaks proportional selection by more than `0.10` per validator will
fail one of the four cases.

## Back-links

- [[algorithms/pos]] — the protocol the selection rule belongs to;
  proposer-selection knob added under §"Simulator mapping" in the same
  T33 commit.
- [[experiments/2026-05-23_casper-baseline]] — T32 build-verification
  baseline; its `## Revisions` section notes that the per-slot proposer
  identities recorded there are now historical to the T32 rule.
- [[concepts/node-model]] — the per-Node `rng` the selection rule
  deliberately does not consume; selection draws from a separate
  blake2b-seeded `Random` so that every validator computes the same
  proposer for any given slot.
- [[concepts/reproducibility]] — same-`(config, global_seed)`
  byte-identical replay contract that selection inherits via its
  pure-function form.
