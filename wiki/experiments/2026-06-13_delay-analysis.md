# [2026-06-13] T49 — Graceful degradation under delay & loss: mechanism analysis

The mechanism analysis behind the T48 descriptive ranking
([[experiments/2026-06-13_delay-comparison]]). T48 landed the numbers and
figures and deferred the "which degrades most gracefully and *why*" question
here. This page answers it from the T46/T47 datasets and the simulator code,
with no new runs and no new plots (Ch. 4 prose + plots are T50). It addresses
**RQ4** ([[concepts/research-questions]]): resilience under adverse networks.

Every quantitative claim below is sourced from `results/delay/resilience_ranking.csv`,
the T47 results table ([[experiments/2026-06-12_delay-heavy]] §Results), or the
T46 latency table ([[experiments/2026-06-10_delay-moderate]] §Results).

## The two stress axes are not the same question

Delay and loss attack different properties, and conflating them hides the
verdict:

- **Delay attacks latency.** Under the moderate (T46) and heavy-tail loss-free
  (T47 control) timelines every honest instance still finalizes
  (`finalization_rate = 1.0` for all control rows); only *time-to-finality*
  moves. `moderate_latency.pdf` (Fig. 5) shows the loss-free separation the
  resilience ratios extend from — PBFT ≈ 2 s < FFG ≈ 6 s < Snowman ≈ 12–16 s,
  with Snowman's exponential-tail bar visibly taller than its uniform bar at
  n=10 (the only protocol whose latency reads the delay *distribution*, not
  just its mean). This axis answers RQ1, not resilience.
- **Loss attacks liveness.** Under per-message drop (`p_drop ∈ {0.05, 0.10,
  0.20}`) instances stop finalizing. This is where "graceful degradation"
  lives, so the robustness verdict is read off `finalization_rate` vs `p_drop`,
  not off latency.

The headline finding ties the two axes together: **the protocols that stay
alive under loss are exactly the ones that pay the most latency to do it.**
Resilience here is *bought with latency* — see §Tradeoff.

## Breakpoints (where each protocol stops finalizing)

Using survival-depth `p*` (deepest `p_drop` with mean `fr > 0`) and the cliff
location as the breakpoint measures, per
[[experiments/2026-06-13_delay-comparison]] §Locked methodology. The shapes
below are read directly off `finalization_degradation.pdf` (§Figure evidence
Fig. 1): the headline degradation curves.

| protocol | n | fr@.05 | fr@.10 | fr@.20 | survival `p*` | shape |
| :-- | --: | --: | --: | --: | --: | :-- |
| PBFT       | 10 | 0.169 | 0.161 | **0.104** | 0.20 | smooth decline, alive at 20 % |
| PBFT       | 25 | 0.533 | 0.211 | **0.056** | 0.20 | smooth decline, alive at 20 % |
| Snowman    | 10 | 0.195 | 0.000 | 0.000 | 0.05 | high-ish plateau → cliff at 10 % |
| Snowman    | 25 | **0.904** | 0.047 | 0.000 | 0.10 | very high plateau → cliff at 10 % |
| Casper FFG | 10 | 0.070 | 0.018 | 0.000 | 0.10 | collapsed by the first loss step |
| Casper FFG | 25 | 0.051 | 0.006 | 0.000 | 0.10 | collapsed by the first loss step |

PBFT is the only protocol still finalizing anything at the deepest tested loss
(20 %), at both committee sizes. Casper FFG's nominal survival depth of 0.10 is
a near-zero residual (`fr ≈ 0.006–0.018`): it is effectively dead at 5 %.
Snowman cliffs — it holds a plateau then drops to zero within one loss step.

## Mechanism — why each protocol degrades as it does

### PBFT — most robust, via leader rotation (a retry mechanism)

PBFT has a genuine recovery path: the per-instance view-change timer
(`src/pbft/node.py` `_arm_view_change_timer`, delay `vc_delay · 2^view`,
`vc_delay = 90 s` in T47). When dropped `PREPARE`/`COMMIT` messages stall an
instance below its `2f+1` quorum, the timer fires, replicas broadcast
`VIEW-CHANGE`, and a `NEW-VIEW` rotates the primary and **reissues the
instance** under a fresh leader. This is not retransmission of the same lost
message — it is a fresh round with a fresh set of messages, hence a fresh
chance to assemble the quorum. The exponential `2^view` backoff guarantees a
later view's timer is long enough for the commit to finish, so recovery
terminates deterministically (the spurious-rotation guard validated at
`p_drop = 0`: `view_change_count ≈ 0`).

The evidence is the view-change count tracking the loss level exactly:
`0 → 16 → 30` (n=10) and `0 → 28 → 63 → 75` (n=25) as loss climbs — annotated
directly on `cost_of_survival.pdf` (Fig. 4). Each rotation is a retry, and
enough retries eventually land a quorum even under 20 % loss; on
`latency_cliff.pdf` (Fig. 2) PBFT is the only protocol whose curve stays
*solid* (finalizing) across every loss level, never hitting the `×`
liveness-lost marker. **Price:** `commit_latency_ms` inflates ≈ 2.84× (n=10) to 3.57×
(n=25) at the worst surviving loss level — every rotation adds rounds. PBFT
trades latency for liveness, and it is the only protocol that converts that
latency into deep survival.

### Snowman — high plateau, hard cliff, no recovery path

Snowman's robustness comes not from recovery but from **redundancy inside a
single poll round**, and it has no recovery path when that redundancy is
exhausted: a poll closes only when `α_c` agreeing responses arrive
(`early_close`, `src/snowman/poll.py` `on_response`) or all `K` responses
arrive — **there is no poll timeout and no retransmission**
(`src/snowman/node.py`: the only timer is the slot timer, never a poll timer).
A poll that never collects `α_c` responses simply stalls forever, the block's
confidence counter never advances, and it never reaches `β = 15` to accept.

This makes the degradation quantitatively predictable. The rescaling rule
(`src/snowman/parameters.py`: `K = min(20, n−1)`, `α_c = ⌈0.8·K⌉`) gives:

| n | K | α_c | per-round loss slack `K − α_c` |
| --: | --: | --: | --: |
| 10 | 9  | 8  | **1** |
| 25 | 20 | 16 | **4** |

A response counts only if **both** its `QUERY` and its `QUERY-RESPONSE` survive
the per-message drop, so per-peer round-trip survival is `(1 − p)²`. Expected
arrivals per round are `K · (1 − p)²`, and the round closes iff that clears
`α_c`:

- **n=25, p=0.05:** `20 · 0.9025 = 18.1 ≥ 16` → rounds close reliably →
  `fr = 0.904`.
- **n=25, p=0.10:** `20 · 0.81 = 16.2 ≈ 16` → marginal → cliff to `fr = 0.047`.
- **n=10, p=0.05:** `9 · 0.9025 = 8.1 ≈ 8` → marginal already → `fr = 0.195`.
- **n=10, p=0.10:** `9 · 0.81 = 7.3 < 8` → rounds cannot close → `fr = 0`.

The `β = 15` sequential rounds then compound: a block needs ~15 consecutive
rounds to close, so block-acceptance probability is roughly `q^15` in the
per-round close probability `q`. That compounding is why the transition is a
**cliff, not a slope** — once `q` slips below ~1, `q^15` falls off a wall. This
is also why committee size is such a sharp lever for Snowman: a larger `K` buys
more slack (`K − α_c`: 1 → 4) against dropped messages, lifting the plateau
from `fr = 0.195` (n=10) to `0.904` (n=25) at 5 % loss. On
`finalization_degradation.pdf` (Fig. 1, n=25 facet) this is the green curve
starting *highest* at 5 % then plunging through the blue PBFT line by 10 % — a
visible cliff, not a slope. **Price:** ≈ 2.16× (n=10) to 3.11× (n=25) added
latency at the worst surviving level — and the surviving blocks are the slowest
of all three protocols (control ≈ 72 s, the top band of `latency_cliff.pdf`).

### Casper FFG — most fragile, no recovery path and a two-epoch dependency

Casper FFG collapses at the first loss step (`fr ≈ 0.05–0.07` at 5 %). It has
the least slack of the three and no recovery mechanism at all. Finalization
requires a supermajority FFG link — ≥ 2/3 of total stake attesting the same
`<source, target>` checkpoint (`src/pos/node.py` `_run_ffg_transitions`) — and
then **two consecutive** justifications (justify → finalise), so the
supermajority must be reassembled across two epochs in a row. Attestations are
broadcast once per epoch; when enough drop, the link never reaches 2/3, the
epoch never justifies, and there is **no leader to rotate and no resampling**
to retry with. The two-epoch dependency compounds the per-epoch failure
probability, which is why 5 % loss already drives it to near-zero.

The T47 source-checkpoint guard ([[algorithms/pos]] §Revisions) converts what
would have been a crash under heavy delay into exactly this honest stall (a
node can justify an epoch before its checkpoint block is delivered locally; it
now skips the attestation and retries a later slot). Larger `n` is a mild
*liability* (`0.070 → 0.051` at 5 %): more attestation links means more
independent messages that can drop, with no compensating redundancy.
**Price:** almost none — ≈ 1.03× (n=10) to 1.10× (n=25) added latency. FFG is
the cheapest protocol under loss precisely because it does nothing extra to
survive it.

## Verdict and the n=25 crossover

Defining **most graceful** as *smooth degradation that survives to deep loss*
(distinct from a high light-loss value that then cliffs):

> **PBFT degrades most gracefully.** It declines smoothly and is the only
> protocol still finalizing at 20 % loss, at both committee sizes. Snowman is
> *high-but-brittle* — best-in-class at light loss when `n` is large, but it
> cliffs to zero within one loss step. Casper FFG is *fragile* — it never
> establishes a resilient plateau and collapses at the first loss step.

This matches T48's AURC ranking (PBFT ≥ Snowman > Casper FFG) and explains its
one subtlety: the **n=25 PBFT/Snowman statistical tie is a genuine
virtue-crossover, not noise.** Snowman wins area-under-curve because it retains
0.90 at 5 % loss (vs PBFT's 0.53), but PBFT wins survival-depth because it is
alone alive at 20 %. The two metrics reward different virtues — a high plateau
vs a long tail — so neither protocol is crowned outright. Mechanistically:
Snowman's per-round redundancy is excellent until it is suddenly exhausted
(`q^15` cliff), whereas PBFT's rotation keeps retrying indefinitely, just
slower and slower. `finalization_degradation.pdf` (Fig. 1) shows the crossover
geometrically: at n=25 the green (Snowman) and blue (PBFT) curves swap order
between 5 % and 10 % loss, while orange (FFG) sits below both throughout.

## Tradeoff — resilience is bought with latency (reader takeaway)

The single most important thing for a reader to acknowledge: **loss resilience
is not free — it is paid for in finality latency.** Lining up added-latency
ratio against survival depth makes the price explicit:

| protocol | n | added-latency × (worst surviving loss) | survival `p*` | what the latency bought |
| :-- | --: | --: | --: | :-- |
| PBFT       | 10 | 2.84× | 0.20 | deep survival |
| PBFT       | 25 | 3.57× | 0.20 | deep survival |
| Snowman    | 25 | 3.11× | 0.10 | a high plateau, then a cliff |
| Snowman    | 10 | 2.16× | 0.05 | a thin plateau, then a cliff |
| Casper FFG | 25 | 1.10× | 0.10 | nothing (near-zero residual) |
| Casper FFG | 10 | 1.03× | 0.10 | nothing (near-zero residual) |

PBFT and Snowman both pay 2–3.6× latency under loss; PBFT converts it into
survival at every loss level, Snowman into a high-but-fragile plateau. Casper
FFG refuses the trade — it stays cheap (≈ 1.0–1.1×) and dies first. There is no
cell in the dataset that is both cheap *and* resilient: an operator choosing a
protocol for a lossy network is choosing how much latency to spend on liveness,
not whether to spend it. `operator_pareto.pdf` (Fig. 3) is this tradeoff in one
view — finality retained (y) against added-latency ratio (x, log), "upper-left
is better": no marker lands in the cheap-and-resilient upper-left corner;
points trade rightward (more latency) for height (more retained finality), and
the dead cells are parked on the right-hand "no finality" band.

## Figure evidence (T48 plots → mechanism)

The five T48 figures (`results/delay/plots/*.pdf`, rendered by
`src/output/delay_plots.py`) are the visual evidence for the mechanism claims
above. This task adds no new figures (T50 owns the Ch. 4 plot set); it maps the
existing ones to the "why". The mapping below is the hand-off T50 builds on.

| # | figure | what it plots | mechanism claim it visualizes |
| :-- | :-- | :-- | :-- |
| 1 | `finalization_degradation` | `finalization_rate` vs `p_drop`, faceted n=10/n=25, 95 % CI | The three degradation *shapes*: PBFT shallow tail above zero to 20 %; Snowman high plateau → cliff; FFG immediate collapse. The **n=25 crossover** is the green/blue curve swap between 5 % and 10 %. (§Breakpoints, §Verdict) |
| 2 | `latency_cliff` | `commit_latency_ms` (log) vs `p_drop`; solid = finalizing, `×` = liveness lost | Graceful-vs-cliff made visual: PBFT's curve is *solid across every loss level* (never an `×`); Snowman/FFG curves end in an `×` at their survival depth. The `×` positions **are** the breakpoints. (§Mechanism) |
| 3 | `operator_pareto` | finality retained (y) vs added-latency ratio (x, log); dead cells on a "no finality" band | The headline tradeoff: **no point is both cheap and resilient**; markers trade rightward latency for vertical retained-finality. (§Tradeoff) |
| 4 | `cost_of_survival` | `total_msgs_per_acu` (log) vs `p_drop`, PBFT view-change counts annotated | The view-change *retry* mechanism: PBFT's `16/30` (n=10) and `28/63/75` (n=25) vc annotations climb with loss — recovery is rotation, and it is not free. (§Mechanism/PBFT) |
| 5 | `moderate_latency` | `commit_latency_ms` (log) under the two moderate T46 timelines, uniform vs exponential, faceted by n | Context: the loss-free latency separation (PBFT ≈ 2 s < FFG ≈ 6 s < Snowman ≈ 12–16 s) the resilience ratios extend; Snowman's tail-sensitivity (exponential > uniform). (§The two stress axes) |

Reading the two headline figures together is the whole story: `latency_cliff`
shows PBFT paying the most latency-growth yet keeping a solid (alive) line,
while `finalization_degradation` shows that solid line is also the only one
still above zero at 20 % loss — latency spent, liveness bought.

## Theory-vs-data validation

The mechanism claims here were checked against the raw per-trial CSVs by an
adversarial pass (2026-06-14, 29-agent workflow): per-protocol first-principles
re-derivation vs `results/{baseline,delay}/*.csv`, an independent skeptic
recomputing every figure to refute it, then a completeness critic.

**Validated.** Every figure cited on this page reproduces exactly from the raw
CSVs (zero seed variance on structural metrics), and the mechanism claims survive:
PBFT alone has `fr > 0` at `p_drop = 0.20` (vc 0→16→30 / 0→28→63→75); FFG collapses
by 0.05; Snowman's cliff lands in `(0.05, 0.10]` at **both** `n` with the four-cell
order `n25@.05 > n10@.05 > n25@.10 > n10@.10` reproduced — the `K·(1−p)²`-vs-`α_c`
slack model predicts the cliff *location* and the committee-size ordering unfitted;
exponential-tail and honest safety (`success=1`, `fork=0`) hold.

**Two in-scope caveats.** (1) **`q^15` is qualitative** — it predicts the cliff
*shape/location*, but `q^15` is a single-block accept probability while
`finalization_rate = finalized/total` is a run-wide fraction, so the bare `q^15`
under-predicts the fr *magnitude* by ~7–18×. (2) **Snowman `lat×` ratios are
survivorship-biased** — computed only over surviving seeds (`commit_latency_ms` is
NaN where `fr = 0`) with up to ~4 % clip; a price among survivors, not an
unconditional mean (as for FFG's per-loss latency).

**Out of scope → Backlog (2026-06-14).** The pass also flagged framework issues
that are not T49's: `finality_latency_ms` == `commit_latency_ms` for all protocols
(finality≠commit gap unimplemented), `bytes_per_acu` payload-dominated (not
O(n²)/O(K·β)), protocol-dependent `tps`/`goodput` crediting,
`metric-reconciliation.md` overhead-formula + ε(n=10) doc slips, and absent
mandated columns (Snowman ε bound, `f_max_*`). See `TASKS.md` §Backlog.

## Scope and caveats

- **Loss is modelled as permanent per-message drop with no transport-layer
  retransmission.** The simulator's `p_drop` deletes a message outright
  ([[concepts/network-model-phases]] §3); there is no TCP-style resend beneath
  the consensus layer. So these `finalization_rate` curves measure each
  protocol's **consensus-layer** tolerance to lost messages — a stress test of
  its own recovery logic — and are an **upper bound on fragility** relative to
  a real deployment running over a retransmitting transport. The *ordering*
  (PBFT most robust, FFG most fragile) is a property of the recovery mechanisms
  and is expected to survive a retransmit layer; the *absolute* collapse loss
  levels (5–20 %) would shift higher with retransmission. This is the central
  interpretive caveat for any reader quoting the breakpoints.
- **Honest nodes only.** This is network adversity (delay/loss), not Byzantine
  behaviour — adversarial degradation is Family C (T51–T56).
- **Narwhal+Tusk absent** (T38.1 blocked); the comparison is three-protocol.
- **`partial-sync-gst` timeline excluded** — it measures GST recovery, a
  different story than steady-state delay/loss degradation (TASKS.md Backlog
  2026-06-12).
- **Snowman n=25 over 8 seeds** (the cost wall, [[experiments/2026-06-12_delay-heavy]]
  §Cells), hence its wider CIs; PBFT/FFG and all n=10 cells over 20 seeds.

## Re-run

No new code or runs. The analysis reads frozen artifacts:

```
results/delay/resilience_ranking.csv          # T48, the ranking this explains
results/delay/delay_heavy.csv                 # T47, the loss sweep
results/delay/delay.csv                        # T46, the moderate-delay context
results/delay/plots/*.pdf                      # T48, the 5 figures §Figure evidence maps
PYTHONPATH=src python3 -m output.delay_analysis   # regenerates the ranking CSV
PYTHONPATH=src python3 -m output.delay_plots      # regenerates the 5 figures
```

## Auggie verification

Per the Engineer protocol, every `mcp__auggie__codebase-retrieval` call made
during the task (query, one-line result, phase). This task changed **no code**,
so the post-edit re-query is N/A (no new callsites to locate); the analysis is
verified instead by cross-checking every cited number against the source CSV /
experiment tables (done — all match).

- **pickup-index** — query: *"mechanistic details of how PBFT (view-change /
  timeouts / retransmission under loss), Casper FFG (attestation/epoch
  finalization, why no recovery path), and Snowman (K-peer poll under loss,
  query/response timeout, why redundancy scales with K) degrade under delay and
  packet loss — files, classes, timeout/retry logic, Calibration params."*
  Result: mapped PBFT's `_arm_view_change_timer` / `_initiate_view_change` /
  `vc_delay·2^view` backoff (`src/pbft/node.py`) as a leader-rotation retry;
  Casper FFG's `_run_ffg_transitions` 2/3-stake link + two-round justify→finalise
  with the `source_checkpoint_unavailable` honest-stall guard (`src/pos/node.py`);
  and Snowman's `_start_poll_round`/`_handle_response` close-on-`α_c`-or-`K`
  logic (`src/snowman/{node,poll}.py`) — establishing the three recovery-mechanism
  story (rotation / in-round redundancy / none).
- **pickup-index (follow-up, grep + read)** — confirmed Snowman has **no poll
  timeout** (the only `set_timer` is `"slot"`; a poll closes solely via
  `on_response` early-close or `responses_received == K`) and read
  `snowman_parameters(n)` to fix the exact `(K, α_p, α_c)` values
  (`K=min(20,n−1)`, `α_c=⌈0.8·K⌉`) underpinning the `K − α_c` slack model in
  §Mechanism/Snowman.

## Cross-references

- [[experiments/2026-06-13_delay-comparison]] — T48, the descriptive ranking
  (AURC + survival-depth) **and the 5 figures** (`results/delay/plots/`) this
  explains the mechanism behind; see §Figure evidence for the figure→claim map.
- [[experiments/2026-06-12_delay-heavy]] — T47, the heavy-tail + packet-loss
  dataset (`finalization_rate`, `view_change_count`) this analysis reads.
- [[experiments/2026-06-10_delay-moderate]] — T46, the moderate-delay latency
  context (the loss-free latency baseline the added-latency ratios extend).
- [[algorithms/pbft]] — PBFT view-change as the liveness-recovery mechanism.
- [[algorithms/pos]] §Revisions — the FFG source-checkpoint honest-stall guard.
- [[concepts/metric-reconciliation]] — the Snowman `(K, α_c, β)` rescaling rule.
- [[concepts/network-model-phases]] §3 — the per-message Bernoulli drop model
  (no transport retransmission) that the §Scope caveat turns on.
- [[concepts/research-questions]] — RQ4 (resilience under adverse networks).
