# Kickoff — Full signature aggregation for Casper FFG

**Status:** proposal / kickoff brief for a *fresh* Engineer session.
**Author of brief:** carried over from the 2026-06-09 Week-8 results-explainer session.
**Role for the new session:** Engineer (substantive task → use `superpowers:brainstorming`).
**Branch:** new branch from `main` (per `docs/workflow.md`), e.g. `task/T<N>-casper-bls-aggregation`.
**Assign a task ID** in `TASKS.md` before starting (suggested family: T38.x, alongside the
other protocol-fidelity work). This brief is *intent*, not an approved spec — the spec lands
in `docs/superpowers/specs/` via brainstorming.

---

## 1. Why this exists (the finding that motivates it)

During the Week-8 results explainer we validated each protocol's measured
`total_msgs_per_acu` against its message model (see
[[experiments/2026-06-09_baseline-explainers]],
[[experiments/2026-06-08_baseline-cis]]). For Casper FFG we found, **empirically and
exactly** (seed 0, n ∈ {4,7,10,16,25}, by running `pos.baseline.run_scenario` and
counting `delivery` events by `msg_type`):

| phase | per-window deliveries | order |
| :-- | :-- | :-- |
| BLOCK-PROPOSAL | `19(n−1)` | O(n) |
| **ATTESTATION** | **`9·n(n−1)`** | **O(n²)** |
| decided events | `8n` | — |

→ `total_msgs_per_acu = (n−1)(9n+19) / 8n ≈ 1.125n`.

**The problem:** `src/pos/node.py::_attest` has *every validator broadcast its ATTESTATION
to every other validator* (all-to-all gossip), so the attestation phase is `O(n²)` per
round — structurally identical to PBFT's vote phases. Real Casper/Ethereum uses **BLS
signature aggregation** (attestations aggregated in subnet committees, then into the block),
making the consensus-relevant cost `O(n)` per epoch. The current simulator therefore
**overstates Casper's consensus-message cost** and hides its central scalability advantage
(aggregation is *why* PoS Ethereum scales to ~10⁶ validators where PBFT cannot).

The wiki currently cites `O(n) aggregated/epoch` theory
([[algorithms/pos#communication-complexity]]) while the simulator measures `O(n²)` gossip —
an internal inconsistency this task should resolve.

## 2. Goal

Model BLS-style attestation aggregation for Casper FFG so the message-cost metric reflects
aggregated `O(n)` behavior, **without breaking the existing baseline**. The headline success
signal: aggregated Casper's `total_msgs_per_acu` should flatten from `≈1.125n` to roughly
`O(1)`-per-node (a gentle / near-constant slope), and the `theory_vs_measured` overlay
should reconcile against the aggregated `O(n)` line.

**Strongly recommended:** implement it as a *variant/flag* (`aggregated` vs the existing
`gossip` path), so both can be measured and compared side by side. This preserves the
Week-8 baseline as the un-aggregated reference and turns the change into an additive
comparison rather than a destructive rewrite.

## 3. Where it lives (orient here first)

- `src/pos/node.py` — `_attest` (broadcasts ATTESTATION, ~line 201/215),
  `_handle_attestation` (~line 377), FFG vote filing, supermajority-link logic.
- `src/pos/messages.py` — ATTESTATION payload (`FFGVote`); a new AGGREGATE payload likely
  needed.
- `src/pos/finality.py`, `src/pos/epoch.py` — epoch/checkpoint + 2-epoch finality.
- `src/pos/baseline.py` — `SCENARIOS`, `run_scenario`, `_config` (where a variant axis
  would be threaded).
- `src/output/csv.py::_total_msgs_per_acu` = `deliveries / decided`;
  `src/output/metrics.py` — `consensus_msgs_per_acu`, `bytes_per_acu`. **The metric counts
  raw delivery events**, so the aggregation benefit only shows up if the model emits fewer /
  differently-typed deliveries.

## 4. Design questions to resolve in brainstorming (do NOT pre-decide)

1. **Aggregation topology.** Simplest defensible: a single per-epoch aggregator (e.g. the
   next proposer) collects attestations and propagates one AGGREGATE. Ethereum-realistic:
   two-tier subnet committees → local aggregate → global aggregate. Pick the simplest model
   that captures the `O(n)` property; document the simplification.
2. **Message-counting convention (critical for comparability).** Does one AGGREGATE count
   as 1 delivery × `(n−1)` recipients (O(n)), and do the validator→aggregator submissions
   count (another O(n))? Define exactly, and justify that an AGGREGATE "message" is
   comparable to a PBFT COMMIT "message" given different payload/verify cost. This convention
   *is* a methodology claim — write it into `concepts/output-format`.
3. **Fairness / RQ3 framing — REQUIRES ADVISOR SIGN-OFF.** If Casper gets aggregation,
   should PBFT also get its threshold-signature variant (HotStuff, `O(n)`)? Aggregating one
   family but not another creates a *new* asymmetry. Current baseline models all three at the
   "naive / un-optimized propagation" level, which is internally consistent. Decide
   deliberately whether the thesis compares (a) all-naive, (b) all-production-optimized, or
   (c) reports both. **This shapes the central RQ3 conclusion — settle it before coding.**
4. **Byte accounting.** Aggregation's real win is bytes (1 aggregate sig vs `n` sigs).
   Update `bytes_per_acu` / `_BASE_BUDGET` so the byte metric reflects aggregate-signature
   size, not `n` individual signatures.
5. **Variant plumbing.** How to thread an `attestation_mode ∈ {gossip, aggregated}` axis
   through `ScenarioMeta` / `baseline.py` / the experiment matrix without disturbing existing
   `run_id`s and committed CSVs.

## 5. Scope

**In:** Casper attestation aggregation model + message/byte accounting; a `gossip` vs
`aggregated` variant axis; unit + e2e tests; re-run of the Casper baseline matrix under the
new variant; wiki + theory-line reconciliation; a comparison chart (gossip vs aggregated).

**Out (unless the §4.3 fairness decision says otherwise):** changes to PBFT or Snowman
message models; slashing/safety-rule changes; networking realism beyond delivery counting;
the W9 delay axis and W10 adversary (separate tasks).

## 6. Acceptance criteria

- Aggregated Casper `total_msgs_per_acu` is `O(n)`-flat (or clearly sub-`1.125n`), validated
  empirically the same way PBFT's `2n` was (delivery-by-type counts reduce to a closed form,
  locked in a test — mirror `tests/output/test_explain.py::TestPbftPhaseDerivation`).
- Existing `gossip`-path baseline reproduces byte-for-byte (no silent regression of the
  Week-8 dataset).
- `theory_vs_measured` reconciles aggregated Casper against the `O(n)` line.
- Wiki updated: [[algorithms/pos]] communication-complexity section distinguishes
  "production (aggregated) `O(n)`" from "simulator gossip `O(n²)`", and the chosen counting
  convention is recorded in [[concepts/output-format]].
- Per Engineer role (`docs/roles.md`): brainstorming spec, TDD, pre/post-edit auggie queries
  logged, `superpowers:verification-before-completion`, `wiki/experiments/` page, `log.md`,
  `index.md`.

## 7. Process reminders

- Substantive task → `superpowers:brainstorming` first (design → approval → plan → approval
  → execute). Spec stays in `docs/superpowers/specs/`.
- **Resolve §4.3 (fairness) with the advisor before implementation** — it is a methodology
  decision, not an engineering one (cf. the standing "user-in-loop on evaluation
  methodology" rule).
- One task per session; branch from `main`; humans flip to Completed.

## 8. References

- This session's findings: [[experiments/2026-06-09_baseline-explainers]],
  [[experiments/2026-06-08_baseline-cis]] (per-protocol theory table).
- Algorithm page: [[algorithms/pos]] (esp. communication-complexity).
- Metric semantics: [[concepts/output-format]] §13; [[concepts/message-types]].
- Empirical reproduction (run from repo root):
  ```
  PYTHONPATH=src python3 -c "from collections import Counter; import pos.baseline as P; \
  [print(m.n, Counter(r.fields['msg_type'] for r in P.run_scenario(m)[0] if r.event_type=='delivery'), \
  sum(1 for r in P.run_scenario(m)[0] if r.event_type=='decided')) \
  for m in P.SCENARIOS if m.seed==0 and getattr(m,'variant',None)!='nonuniform']"
  ```
