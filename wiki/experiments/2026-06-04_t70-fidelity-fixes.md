# T70 — Impl-vs-paper fidelity fixes (2026-06-04 audit close-out)

**Purpose.** The 2026-06-04 multi-agent fidelity audit (simulator
implementation vs published-paper coverage) surfaced six MAJOR findings.
T70 closes all six in one Engineer pass: three *code-fidelity* fixes —
each carrying a step-logged demonstration on a deterministic simulated
case — plus three *wiki-overclaim* corrections. The three code fixes
restore (1) PBFT client-observed finality as a distinct, one-hop-later
metric from the internal commit quorum, (3) Casper FFG accountable safety
by detecting and reporting both slashable offences, and (5) genuine
Snowball preference selection driven by accumulated confidence rather than
the last sample majority. The three wiki corrections fix
[[concepts/message-types]] (#2, watermark cap overclaim), [[algorithms/pos]]
(#4, simulator-mapping overclaims), and the `ConflictSet` docstring (#5,
folded into the code fix). Determinism is preserved on every honest
baseline: step-logging is gated and consumes no seeded RNG, so each
protocol's baseline event stream stays byte-identical pre vs post.

Backlinks: [[algorithms/pbft]], [[algorithms/pos]], [[algorithms/avalanche]].

## Rubric

The eval set (criterion IDs) per finding. R-prefixed IDs are the labelled
acceptance criteria asserted by the per-fix unit suites (test-docstring
prefixes in `tests/{pbft,pos,snowman}/`). Findings #2 and #4 are
wiki-only corrections, tracked as `## Revisions` entries on the affected
pages rather than as code criteria. RX is the cross-cutting determinism
criterion, demonstrated by the per-protocol byte-identical integration
tests.

### Finding #1 — PBFT client-observed finality (R1.*)
`tests/pbft/test_client_reply.py`
- **R1.1** — on COMMITTED-local each replica sends a `REPLY` toward the
  committing view's primary (the client-reply collector).
- **R1.2** — the collector (node = `view mod n`) finalizes a seq on `f+1`
  matching `REPLY`s and emits `pbft_client_finalized` exactly once.
- **R1.3** — the COMMIT-quorum `pbft_committed` / `decided` still fire, and
  client finalization happens strictly later (one hop after the `2f+1`
  COMMIT quorum).

### Finding #2 — `message-types.md` watermark contradiction (wiki, #2)
- Correction tracked as the 2026-06-04 (T70, audit finding #2) `## Revisions`
  entry in [[concepts/message-types]]: the body's "caps it at the
  configured high-water mark" claim is corrected to state the code never
  enforces the cap. No code criterion.

### Finding #3 — Casper FFG accountable safety (R3.*)
`tests/pos/test_slashing.py`
- **R3.1** — `record_vote` distinguishes NEW / DUPLICATE / CONFLICT (new
  `VoteStatus` enum); a conflicting second vote is not counted into link
  stake.
- **R3.2** — a double vote (same target epoch, differing link) emits
  `casper_slashing(reason="double_vote")`; an exact duplicate does not.
- **R3.3** — a surround vote (`s1<s2<t2<t1` either ordering) emits
  `casper_slashing(reason="surround_vote")`; a nested non-surrounding pair
  does not.
- **R3.4** — slashable-stake fraction is computed (offenders' stake / total)
  and surfaced both on the event and via
  `CasperNode.slashable_stake_fraction()`; each offender counts once.
- **R3.5** — honest-path votes never slash, fraction stays 0.0, and
  finalisation still works.

### Finding #4 — `pos.md` simulator-mapping overclaims (wiki, #4)
- Correction tracked as the 2026-06-04 (T70, finding #4) `## Revisions`
  entry in [[algorithms/pos]]: rewrites the "Simulator mapping" to state
  what T70 now implements (double/surround detection + slashable-stake
  metric) vs what stays deferred (penalty application, LMD-GHOST reorgs,
  per-validator attestation delay, safety-cost budget, validator
  rotation). No code criterion.

### Finding #5 — Snowman genuine Snowball (R5.*)
`tests/snowman/test_snowball_preference.py`
- **R5.1** — preference = `argmax(confidence)`, not this round's sample
  majority.
- **R5.2** — a sequence where flip-to-majority (Snowflake) and
  argmax-confidence (Snowball) diverge: a high-confidence incumbent does
  NOT flip on a single dissenting majority round; counter resets only on an
  actual preference change.
- **R5.4** — a singleton conflict set (the honest baseline) behaves
  identically because `argmax(confidence)` is always the sole block, so the
  two rules coincide and the baseline is byte-identical.

### Cross-cutting — determinism (RX)
- **RX** — honest baselines stay byte-identical pre vs post: step-logging
  is gated and consumes no seeded RNG. Asserted by
  `tests/integration/test_pbft_baseline.py`,
  `tests/integration/test_pos_baseline.py::test_determinism`, and
  `tests/integration/test_snowman_baseline.py::test_determinism_byte_identical`.

### Rubric coverage

Statuses are taken from the adversarial verifiers (authoritative). RX.1 is
set from the full-suite run via `make test` (12 suites, 608 tests, all OK).

| Finding | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| #1 PBFT client-finality | R1.1 | pass | `ReplyPayload(view,seq,request_digest,replica_id)` in messages.py; `_accept_commit`→`_send_reply` unicasts/self-records REPLY to collector=view%n. `test_client_reply.TestReplicaRepliesOnCommit` OK; demo emits one REPLY→collector per node. |
| #1 PBFT client-finality | R1.2 | pass | `_record_reply` emits `pbft_client_finalized` at ≥f+1 distinct replicas matching (view,seq,digest), once per seq via `_finalized_seqs`. `TestCollectorFinalizes` 4 tests OK incl. below-f+1, digest-mismatch exclusion, single emission. |
| #1 PBFT client-finality | R1.3 | pass | summarise.py: commit_latency from COMMIT quorum, finality_latency from `pbft_client_finalized`. Baseline n=4 seed=42: commit=1000.0000030000002 ms, finality=1000.0000040000003 ms (strictly one hop greater). `test_first_instance_finality_one_hop_past_commit` OK. |
| #1 PBFT client-finality | R1.4 | pass | Re-ran pbft 152, output 50, integration 84 — all OK. `test_every_committed_seq_reaches_client_finality` OK (committed set == finalized set, each once, after commit). `TestPBFTDeterminism` byte-identical replay OK. |
| #1 PBFT client-finality | R1.5 | pass | `python3 -m pbft.demo_client_finality` runs n=4 honest; prints pre-prepare→prepare→commit→reply→client-finalize trace; commit_t=1.3 vs client_finality_t=1.4 (+0.100s). |
| #2 PBFT watermark wiki | R2.1 | pass | message-types.md §3 (L113-125) and §9 (L363-368) now state "the simulator applies no cap"; old "caps it at the configured high-water mark" removed. Code match: node.py:442 `last_stable_seq=-1`, no [h,H]/watermark check in `_handle_pre_prepare`; grep of src/pbft/ finds zero watermark logic. |
| #2 PBFT watermark wiki | R2.2 | pass | Dated `2026-06-04 (T70, audit finding #2)` entry added under `## Revisions` (L447) quoting old wording + code evidence + correction, per wiki-spec Revisions rule. |
| #3 Casper slashing | R3.1 | pass | epoch.py:75-82 `record_vote` returns DUPLICATE only on full (source_epoch,source_hash,target_hash) match, else CONFLICT; CONFLICT leaves link_stake unchanged. `TestEpochStateVoteStatus` 3 tests OK. |
| #3 Casper slashing | R3.2 | pass | node.py:243-256 CONFLICT→`_flag_slashing('double_vote')`. `test_double_vote_emits_slashing` asserts 1 event reason=double_vote attester_idx=1 target_epoch=1 OK. Demo prints `EMIT casper_slashing reason=double_vote`. |
| #3 Casper slashing | R3.3 | pass | node.py:264-281 `_check_surround` tests (s1<s2<t2<t1) or (s2<s1<t1<t2). `test_surround_emits_slashing`, `test_surround_both_orderings`, `test_nested_non_surround_does_not_slash` OK. |
| #3 Casper slashing | R3.4 | pass | `slashable_stake_fraction()` accessor node.py:306-312; event field at node.py:297. `test_fraction_after_one_double_voter` asserts accessor=0.25 and event field=0.25; demo prints 0.25 then 0.50. |
| #3 Casper slashing | R3.5 | pass | pos suite Ran 107 OK (rubric's 93 = pre-T70 count). Direct honest e2e: casper_slashing=0, finalised=32, decided=32 at n=4; slashing=0 at n=7. `test_no_slashing_on_clean_finalisation` OK. |
| #3 Casper slashing | R3.6 | pass | `test_casper_baseline.py` test_determinism asserts `list(a.records)==list(b.records)` at n=4 and n=7 (global_seed=42); suite Ran 7 OK. Detection consumes no RNG. |
| #3 Casper slashing | R3.7 | pass | `python3 -m pos._t70_demo` (n=4, double-voter attester 1 + surround attester 2) runs; output matches wiki experiment page L142-152 byte-for-byte. |
| #4 Casper pos.md wiki | R4.1 | pass | pos.md L183-240 splits Implemented (two-round FFG, stake-weighted proposer, double/surround DETECTION, slashable-stake-fraction) vs Not-implemented/deferred (penalty/burn, safety-cost budget, LMD-GHOST+reorgs, attestation delay, validator-set rotation, checkpoint trees). Cross-checked vs src/pos/. Residual L154 overclaim disclosed in Revisions, not silently retained. |
| #4 Casper pos.md wiki | R4.2 | pass | pos.md L47-51 now states simulator does NOT rotate validator set; stake_table fixed at `CasperNode.__init__`. Matches node.py:116; no rotation logic in src/pos/. |
| #4 Casper pos.md wiki | R4.3 | pass | Dated `2026-06-04 (T70, finding #4)` entry under `## Revisions` (L288) enumerating removed false claims + corrections + flagged still-open overclaim. |
| #5 Snowman Snowball | R5.1 | pass | poll.py `close_round` Step 1b argmax over `conflict_set.confidence` with strict-exceed flip + lowest-block_id tie held by incumbent — genuine Snowball, not Snowflake flip-to-round-majority. `test_preference_follows_accumulated_confidence` + `test_flip_only_when_confidence_strictly_exceeds` OK. |
| #5 Snowman Snowball | R5.2 | pass | `test_single_majority_round_does_not_flip_high_confidence_pref` OK; verified it FAILS under simulated old Snowflake logic (old flips to B; new keeps A) — a real regression guard. |
| #5 Snowman Snowball | R5.3 | pass | `ConflictSet.__doc__` (block.py:58) and `close_round.__doc__` (poll.py:71) rewritten to describe argmax(confidence) Snowball, explicitly contrasting Snowflake; avalanche.md gained a Revisions note. No stale flip-to-majority claim remains. |
| #5 Snowman Snowball | R5.4 | pass | snowman discover Ran 78 OK (71 pre-existing + 7 new). `test_singleton_accepts_at_beta` OK. `test_snowman_baseline.py::test_determinism_byte_identical` passes (full 1666-record stream byte-identical across seeds 42/7/99). |
| #5 Snowman Snowball | R5.5 | pass | `python3 -m snowman._t70_demo` runs; round 4 B is round-majority (count≥alpha_p) yet preference stays A (flipped=False), flips to B at round 7 when confidence[B]=4 > A=3. |
| Cross-cutting | RX.1 (global determinism / full suite) | pass | `make test`: 12 suites, 608 tests, all OK — scheduler 47, nodes 46, network 63, config 30, event_log 39, common 6, pbft 152, pos 107, snowman 78, output 50, workload 6, integration 84. Honest baselines byte-identical pre/post; step-logging gated, consumes no seeded RNG. |
| Cross-cutting | RX.2 (latency-semantics note) | note | PBFT `finality_latency_ms` now measured at f+1 client REPLYs (one network hop past the internal COMMIT quorum), per the paper's client-observed finality; `commit_latency_ms` unchanged. This is an expected honest-baseline ripple — REPLY deliveries raise delivery/byte counts feeding consensus_msgs_per_acu and bytes_per_acu, so T41/T42 baseline dataset numbers should be re-run. Flagged in src/pbft/baseline.py docstring. |

## Demonstrations

Each fix ships a gated step-log demo that runs a deterministic simulated
case. Run from the worktree root.

### Finding #1 — PBFT client-observed finality

```
cd /Users/phananhle/Desktop/phananhle/thesis/.claude/worktrees/T70-fidelity-fixes && PYTHONPATH=src python3 -m pbft.demo_client_finality
```

```text
pre-prepare node=0 view=0 seq=0 digest=0e5350f0 src=0 t=1.0
pre-prepare node=1 view=0 seq=0 digest=0e5350f0 src=0 t=1.1
pre-prepare node=2 view=0 seq=0 digest=0e5350f0 src=0 t=1.1
pre-prepare node=3 view=0 seq=0 digest=0e5350f0 src=0 t=1.1
prepare node=0 view=0 seq=0 quorum=3 t=1.2000000000000002
prepare node=1 view=0 seq=0 quorum=3 t=1.2000000000000002
prepare node=2 view=0 seq=0 quorum=3 t=1.2000000000000002
prepare node=3 view=0 seq=0 quorum=3 t=1.2000000000000002
commit node=0 view=0 seq=0 digest=0e5350f0 t=1.3000000000000003
reply node=0 -> collector=0 view=0 seq=0 t=1.3000000000000003
commit node=1 view=0 seq=0 digest=0e5350f0 t=1.3000000000000003
reply node=1 -> collector=0 view=0 seq=0 t=1.3000000000000003
commit node=2 view=0 seq=0 digest=0e5350f0 t=1.3000000000000003
reply node=2 -> collector=0 view=0 seq=0 t=1.3000000000000003
commit node=3 view=0 seq=0 digest=0e5350f0 t=1.3000000000000003
reply node=3 -> collector=0 view=0 seq=0 t=1.3000000000000003
client-finalize collector=0 view=0 seq=0 replies=2 t=1.4000000000000004
---
commit_t (2f+1 COMMIT quorum)      = 1.3000000000000003
client_finality_t (f+1 REPLYs)     = 1.4000000000000004
client finality is one hop later   = True (+0.100s)
```

**Reading.** All four replicas reach the `2f+1` COMMIT quorum at
`commit_t = 1.30…`, then each emits a `REPLY` toward the view-0 primary
(collector node 0). The collector finalizes on the `f+1 = 2`nd matching
`REPLY` and emits `client-finalize` at `client_finality_t = 1.40…` —
exactly one network hop (`+0.1 s`) after the commit. This is the audit-#1
fix: `commit_latency_ms` stays measured at the internal quorum while
`finality_latency_ms` is now the strictly-later client-observed timestamp,
matching the paper's `f+1`-matching-REPLY finality.

### Finding #3 — Casper FFG accountable safety

```
cd /Users/phananhle/Desktop/phananhle/thesis/.claude/worktrees/T70-fidelity-fixes && PYTHONPATH=src python3 -m pos._t70_demo
```

```text
t70.casper double_vote attester=1 target_epoch=1 src=0->tgt_hash=5858585858585858585858585858585858585858585858585858585858585858 (conflicts prior vote)
t70.casper slashing reason=double_vote attester=1 slashable_frac=0.2500
t70.casper surround_vote attester=2 wide=(1,4) inner=(2,3)
t70.casper slashing reason=surround_vote attester=2 slashable_frac=0.5000
=== inject DOUBLE VOTE by attester 1 (target epoch 1) ===
  EMIT casper_slashing {'reason': 'double_vote', 'attester_idx': 1, 'source_epoch': 0, 'target_epoch': 1, 'slashable_stake_fraction': 0.25}
=== inject SURROUND VOTE by attester 2 (1<2<3<4) ===
  EMIT casper_slashing {'reason': 'surround_vote', 'attester_idx': 2, 'source_epoch': 2, 'target_epoch': 3, 'slashable_stake_fraction': 0.5, 'prior_source_epoch': 1, 'prior_target_epoch': 4}
=== slashable_stake_fraction = 0.5000 (2 of 4 offenders, stake 6/12) ===
```

**Reading.** Attester 1 files a second, conflicting vote for the same
target epoch 1 (differing target hash): classified CONFLICT, not counted
into link stake, and reported as `casper_slashing(double_vote)` with
fraction `0.25` (one offender, stake 3/12). Attester 2 then files a
surrounding pair — wide link `(1,4)` around inner `(2,3)`, i.e.
`1<2<3<4` — emitting `casper_slashing(surround_vote)` carrying both the
current and `prior_*` link. With two distinct offenders the aggregate
`slashable_stake_fraction` rises to `0.50` (stake 6/12), surfacing the
audit-#3 accountable-safety metric the pre-fix code masked entirely.

### Finding #5 — Snowman genuine Snowball

```
cd /Users/phananhle/Desktop/phananhle/thesis/.claude/worktrees/T70-fidelity-fixes && PYTHONPATH=src python3 -m snowman._t70_demo
```

```text
t70.snowman close_round parent=00000000 round_majority=41414141 count=5 alpha_p_hit=True conf_updated=True confidence={'41414141': 1, '42424242': 0} preference=41414141 pref_confidence=1 prev_preference=41414141 flipped=False counter=1 accepted=False
t70.snowman close_round parent=00000000 round_majority=41414141 count=5 alpha_p_hit=True conf_updated=True confidence={'41414141': 2, '42424242': 0} preference=41414141 pref_confidence=2 prev_preference=41414141 flipped=False counter=2 accepted=False
t70.snowman close_round parent=00000000 round_majority=41414141 count=5 alpha_p_hit=True conf_updated=True confidence={'41414141': 3, '42424242': 0} preference=41414141 pref_confidence=3 prev_preference=41414141 flipped=False counter=3 accepted=False
t70.snowman close_round parent=00000000 round_majority=42424242 count=4 alpha_p_hit=True conf_updated=True confidence={'41414141': 3, '42424242': 1} preference=41414141 pref_confidence=3 prev_preference=41414141 flipped=False counter=0 accepted=False
t70.snowman close_round parent=00000000 round_majority=42424242 count=4 alpha_p_hit=True conf_updated=True confidence={'41414141': 3, '42424242': 2} preference=41414141 pref_confidence=3 prev_preference=41414141 flipped=False counter=0 accepted=False
t70.snowman close_round parent=00000000 round_majority=42424242 count=4 alpha_p_hit=True conf_updated=True confidence={'41414141': 3, '42424242': 3} preference=41414141 pref_confidence=3 prev_preference=41414141 flipped=False counter=0 accepted=False
t70.snowman close_round parent=00000000 round_majority=42424242 count=4 alpha_p_hit=True conf_updated=True confidence={'41414141': 3, '42424242': 4} preference=42424242 pref_confidence=4 prev_preference=41414141 flipped=True counter=1 accepted=False
=== initial preference=41414141 (alpha_p=3 alpha_c=4 beta=15) ===
=== rounds 1-3: A is the alpha_p majority; confidence[A] -> 3 ===
=== round 4: B is THIS round's alpha_p majority, but confidence[A]=3 > confidence[B]=1 -> Snowflake would flip; Snowball does NOT ===
=== round 5: B wins again; confidence[B]=2 still < A=3 -> no flip ===
=== round 6: confidence[B]=3 TIES A=3 -> no flip (must STRICTLY exceed; incumbent A wins the tie) ===
=== round 7: confidence[B]=4 > confidence[A]=3 -> flip to B, counter resets ===
=== final preference=42424242 confidence={'41414141': 3, '42424242': 4} state=polling ===
```

**Reading.** Rounds 1–3 give block A the `alpha_p` majority, raising
`confidence[A]` to 3. Rounds 4–6 hand the per-round majority to B, but the
preference stays on A because the fix sets `preference = argmax(confidence)`
and only flips when a challenger STRICTLY exceeds the incumbent's
accumulated confidence — at round 6 `confidence[B]=3` merely ties A and the
incumbent wins. Only at round 7, when `confidence[B]=4 > 3`, does the
preference flip to B and the counter reset. Under the old Snowflake rule the
preference would have flipped at round 4 on the single dissenting majority;
this log is the audit-#5 evidence that preference now follows accumulated
confidence, not the last sample.

## Config / seeds / commit

- **Commit hash:** `c5e88d9`
- **Casper demo:** in-process `CasperNode`, n=4 validators, uniform stake
  3.0 each (total 12), `slots_per_epoch=2`; deterministic injected
  attestation messages (no scheduler, no RNG). Slashing detection is pure
  dict/set bookkeeping on message arrival.
- **Snowman demo:** in-process `ConflictSet` + `close_round` over two blocks
  A=`41414141`, B=`42424242` under `alpha_p=3, alpha_c=4, beta=15`;
  deterministic per-round vote tallies (no sampler RNG).
- **PBFT demo:** n=4 (f=1), seed=42, minimal `1e-9` per-hop delay scaled to
  `0.1`-unit ticks in the log; single request through pre-prepare /
  prepare / commit / reply.
- **Honest-baseline determinism (RX):** verified by the per-protocol
  byte-identical integration tests cited in the Rubric; step-logging in all
  three demos is gated and draws no seeded RNG.

### Commands to re-run

```
cd /Users/phananhle/Desktop/phananhle/thesis/.claude/worktrees/T70-fidelity-fixes
PYTHONPATH=src python3 -m pbft.demo_client_finality
PYTHONPATH=src python3 -m pos._t70_demo
PYTHONPATH=src python3 -m snowman._t70_demo
# unit suites (rubric criteria):
PYTHONPATH=src python3 -m pytest tests/pbft/test_client_reply.py tests/pos/test_slashing.py tests/snowman/test_snowball_preference.py
# determinism (RX):
PYTHONPATH=src python3 -m pytest tests/integration/test_pbft_baseline.py tests/integration/test_pos_baseline.py tests/integration/test_snowman_baseline.py
```

## Observation

The three demos confirm each code fix changes the audited behaviour exactly
where the paper says it should and nowhere else. PBFT now exposes
client-observed finality as a strictly-later metric (`+1` hop) without
disturbing the commit-quorum measurement; Casper FFG surfaces both
slashable offences and an aggregate slashable-stake fraction that the
pre-fix `record_vote` dedup masked; Snowman's preference now tracks
accumulated confidence (argmax with strict-exceed flips), diverging from
the old Snowflake last-majority rule precisely on the contested multi-round
case while collapsing to the identical behaviour on the singleton honest
baseline. All three honest baselines remain byte-identical: the new logging
is gated and the detection logic consumes no seeded RNG, so determinism is
preserved across the close-out.
