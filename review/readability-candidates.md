# Readability-pass candidates — full thesis

Find-pass output per `docs/readability-pass.md` (Step 1 detection only — no edits made).
6 chapters, **59 candidates**. Mark `[x]` the ones to fix; leave `[ ]` to skip.

> **Locate by quote, not line number.** ch3 (and possibly others) are being
> actively edited; line numbers drift. The first-~15-words quote is the stable anchor.

Signals legend: **D**=≥2 em-dashes · **;**=semicolon joining 2 independent clauses ·
**L**=>~45 words · **C**=buried causal chain · **S**=scaffolding phrase · **A**=coined abstraction w/o anchor

---

## Cross-chapter top offenders (worst first)

1. `[ ]` **ch6:26–48** — RQ1–RQ3 findings + RQ5 verdict crammed into two periods (>120 words).
2. `[ ]` **ch3 Casper FFG coherence passage** — D+;+S+L+C at once; flagged "worst single passage". (Already drafted a rewrite earlier this session, not yet applied.)
3. `[ ]` **ch4:84–89** — latency calibration ~75 words, 3 dashes, crossover + Ethereum nested in asides.
4. `[ ]` **ch5:223–231** — operator tradeoff (Fig 4.13), ~75 words, load-bearing measurement caveat.

---

## Safety review (1 subagent, read-only adversarial pass)

Counts: **29 SAFE · 2 DROP · 12 CAUTION · 16 GUARDRAIL-GAP**. No candidate is unsafe
*if* its keep-list is honored; the gaps below are keep-items the find-pass missed.
Unmarked candidates below = SAFE.

**DROP (false positive — read cleanly in one pass, skip):**
- ch5:22–28 — "strict best on at least one axis… so each non-dominated" is one clean chain.
- ch5:41–44 — "primary metrics of the RQs rather than chosen to make families differ" — single clear contrast.

**CAUTION (transform risk — two clauses are distinct claims, don't merge / don't mis-split):**
- ch1:81–87 · perf vs security cite different property sets — keep clauses separate.
- ch1:163–167 · "all three implemented" asserts *completeness*, NOT pure restatement — likely keep, not cut.
- ch2:108–112 · equivocation+slashing-dependence vs silent-non-participation are distinct; keep "if prolonged", "window widens".
- ch2:151–156 · two whether-clauses (PBFT / Avalanche 1.35 s) — keep both numbers.
- ch3 coherence · verify cut doesn't drop runner-refuses-to-*start* semantics (the mechanism, not labeling).
- ch3 isolation/reconcile · keep "Isolation is not commensurability" + §3.5 forward ref through the promotion.
- ch4:103–110 · FFG finality-tail (≈80 vs ≈95) is a 3rd distinct claim trailing the split — don't drop.
- ch4:775–786 · 4 stacked hedges incl. no-compute-cost scope — all must survive verbatim.
- ch5:223–231 · "deepest surviving loss / seeds that still finalize / not a single point" bounds 2.16 & 3.57 — keep intact.
- ch5:65–73 · 3 cites at 66/69/73 — each must stay attached to its own clause after split.
- ch6:26–35 · every number must land in the correct sub-sentence (high number-density).
- ch6:35–48 · no hedge may migrate off its protocol when splitting the 3-protocol enumeration.

**GUARDRAIL-GAP (keep-list MISSED a load-bearing item — add it before editing):**
- ch1:96–103 · + the delay-distribution list "(constant, uniform, normal, exponential, heavy-tailed)" + "configurable packet loss".
- ch2:5–17 · + [[wiki/concepts/quorum-arithmetic]], [[wiki/concepts/fault-model]].
- ch2:114–122 · + "far worse cost than the original analysis [9] implies" + "proposes a fix"; [9] appears twice.
- ch3 Snowman③ · + the ε gloss "probability ε that two honest validators accept conflicting blocks, exponentially small in β" — **ε's first-use definition; deleting breaks define-before-use.**
- ch3 three-capabilities · + "the split-ownership invariant" + "any difference between two rows is attributable to the protocol logic alone" (the attribution guarantee — the whole point).
- ch3 Snowman-safety-regime · + "empirical rate is unobservable in feasible seed counts" + "(§3.3.3)".
- ch3 CRN · + "Snowman's internal poll sub-sampling has no cross-protocol counterpart, so its variance reduction is only partial" + the 3 trailing wikilinks.
- ch4:84–89 · + "(where five slot durations equal 1000 ms)" + "not the specific fivefold gap, which moves with the calibration" (intrinsic-vs-calibration hedge).
- ch4:438–445 · + the α_c-rounding reason for 5×10⁻¹⁵ vs 3×10⁻¹¹ + "accountable — reverting requires ≥ one-third stake slashed" (don't merge with Snowman clause).
- ch4:620–627 · + size-invariance reason "set by the proposer's round cadence and the window length, not by the validator-set size".
- ch4:375–381 · + "no poll timeout / no retransmission… simply stalls" + the "used qualitatively" hedge (argument is not a fitted model).
- ch5:112–118 · [[wiki/algorithms/pos]] appears twice; keep "measured analogue" framing (not literal reproduction).
- ch5:144–150 · + committee-size mechanism "larger n=25 sample absorbs more non-responders per poll" + "still fails one sampled step before the quorum protocols".
- ch5:46–52 · + exact scope "flatters PBFT and Casper FFG on cost… while leaving message-count, liveness, and safety verdicts unaffected" (the "unaffected" half is the honesty hedge).
- ch6:64–71 · confirm edit span stops at the semicolon sentence; keep "does not bear on message-count, liveness, or safety".
- ch6:73–82 · confirm edit boundary; keep [[wiki/concepts/metric-reconciliation]] + frontier-scope claim + "robust only where they survive the governing sensitivity check".

---

## ch1 — intro (7)

- `[ ]` **52–56** · L, C, ; · "They demonstrate that the conditions under which those guarantees hold (bounded delay," · *split: guarantees' conditions routinely exited / isolating which condition triggers which failure needs controlled measurement.* · **keep:** parenthetical "(bounded delay, a sufficiently honest validator set)".
- `[ ]` **81–87** · ;, L · "Performance is measured as commit latency, sustained throughput, and communication" · *split semicolon chain; break off "metric schema defined in Ch3".* · **keep:** [[wiki/concepts/evaluation-metrics]], Ch3 ref, metric list.
- `[ ]` **85–91** · C, trailing `so that`/`rather than` · "The comparison is organized around the Pareto frontier each family traces" · *split: organized around per-family frontier / answered from data not theory.* · **keep:** "from data rather than theory" contrast.
- `[ ]` **96–103** · ;, D, L, C · "In scope are configurable network delay (constant, uniform, normal," · *split at semicolon; extrapolation caveat as own sentence.* · **keep:** [[wiki/concepts/adversary-model]], n∈{4,7,10,16,25}, 3 Byzantine behaviors, extrapolation hedge.
- `[ ]` **64–68** · C, A · "A protocol that only *slows* under load may also miss finality," · *split: failure-mode list / "invisible to benign-condition benchmarks".* · **keep:** [14],[16], [[wiki/concepts/problem-statement#the-gap]], italic *slows*.
- `[ ]` **163–167** · D, restatement, trailing `so that` · "**Implementations.** Simplified reference implementations of one representative" · *cut-redundancy: drop "all three implemented" (restates "one from each of three").* · **keep:** 3 named representatives, "single harness", reproducibility.
- `[ ]` **11–18** *(borderline)* · L, ; (×2) · "Three foundational results bound any such protocol: deterministic Byzantine" · *split 3 results into separate sentences/list.* · **keep:** n≥3f+1, f<n/3, [1][2][3], 3 wikilinks, synchrony qualifications.

## ch2 — litreview (8)

- `[ ]` **5–17** · L, C, A, S · "What they jointly produce is not a single protocol but a design space of concessions: every Layer-1…" · *split at colon; lead with 2 concession axes, demote fault-model parenthetical.* · **keep:** [1][2][3], 3f+1, f<n/3, FLP, 4 wikilinks.
- `[ ]` **19–22** · C, S, parenthetical overload · "The CAP theorem [18] makes the operational consequence concrete: under partition a chain must choose…" · *split at colon; lift PBFT-halts/Avalanche-continues into main clause.* · **keep:** [18], [[wiki/concepts/cap-theorem]], partition-tolerance qualification.
- `[ ]` **96–102** · D, C, L · "The documented weakness — a *delayed-voting* adversary in the §1.4 sense — is leader-targeted:" · *promote dash-apposition to own sentence.* · **keep:** O(n³), [4], f<n/3, [[wiki/algorithms/pbft#safety-argument]], "safety unconditional below f<n/3".
- `[ ]` **108–112** · D, ;, L, C · "The most-studied weakness is *equivocation* — slashing exists to deter it, and the safety proof…" · *split at semicolon (primary=equivocation / secondary=silent non-participation).* · **keep:** [7][8], [[wiki/algorithms/pos#behaviour-under-adversarial-conditions]], "if prolonged".
- `[ ]` **114–122** · D, ;, L, C · "The family has no fixed `f < n/3` threshold — the tolerated Byzantine fraction is set by…" · *split threshold/cost dash-pair; split at semicolon.* · **keep:** f<n/3, O(K·β), β, [9][10], Amores-Sesar/Cachin/Schneider, "two undecided validators", "polynomial in β".
- `[ ]` **52–58** · S, D, L, A · "They differ on three axes — what counts as agreement, how much is enough, and how many times…" · *split long final sentence; tighten ε=0 vs 80%/β contrast.* · **keep:** ε=0, β, "two-thirds", "80%", "small positive ε".
- `[ ]` **178–185** · D, colon-join, C · "Their per-family measurements, however abundant, do not support cross-family judgment: the obstacle is…" · *promote Gervais dash-apposition; split colon clause.* · **keep:** [17], Gervais et al., "Proof-of-Work only", "however abundant".
- `[ ]` **151–156** · L, C, S · "The table cannot answer whether PBFT's thousands of ops/s on a LAN reflects a family advantage…" · *split whether/nor into two sentences; leave closing aphorism.* · **keep:** "thousands of ops/s", "1.35 s", K, β.

## ch3 — methodology (15)

> Worst-first per subagent: #9 (coherence) is top.

- `[ ]` **coherence passage** *(was ~389–399)* · D, ;, L, C, S · "Two coherence constraints keep each protocol in its own regime while it sits" · *promote attestation-boundary causal chain; split semicolon; drop "The first governs…" scaffolding.* · **keep:** slot_duration ≥ 4·E[delay], §3.3.2 ③, [[wiki/concepts/metric-reconciliation]], [[wiki/concepts/experiment-matrix]], "runner refuses". **← rewrite already drafted this session.**
- `[ ]` **Snowman ③** *(~245–250)* · D, L, C · "**③ Confidence threshold rescaled, shape held.** `α_c = ⌈0.8·K⌉`. Snowman's safety bound is" · *split final sentence: shape-preservation / ceiling-rounding implication.* · **keep:** ε ≤ (1−α_c/K)^β, α_c=⌈0.8·K⌉, [9], α_c/K≈0.8, "never falls below 0.8", "at least as tight as production".
- `[ ]` **Snowman ④** *(~251–261)* · D, L, C · "**④ `β = 15` held fixed.** Holding `β` fixed keeps the *exponent* of the safety bound" · *split at dashes: ε-range / "smallest sets nearest unanimity" / "one Snowman in form".* · **keep:** (1−α_c/K)^β, ε ≈10⁻¹¹ at n∈{16,25} to ≈10⁻¹⁵ at n=10, n=7→α_c/K=5/6≈0.833.
- `[ ]` **opaque blocks** *(~54–58)* · D, C, S · "Second, the `adversary`, `protocol_knobs`, and `workload` blocks are deliberately opaque" · *promote dash-aside; linearize cause→effect; drop "Second,".* · **keep:** [[wiki/concepts/system-design]], "three protocols that need not share a knob schema".
- `[ ]` **isolation/reconcile** *(~100–104)* · D, A, C · "Isolation is not commensurability. Running three kinds of decision through one identical engine" · *replace noun-coinage "the reconcile" with "reconciliation step the metric schema performs"; promote dash-aside.* · **keep:** §3.5 ref, isolation-vs-commensurability distinction.
- `[ ]` **network phases** *(~50–54)* · ;, L, C, S · "First, `network` is not a static setting but a time-stamped sequence of phases," · *split at semicolon; drop "First,".* · **keep:** [[wiki/concepts/network-model-phases]], "partial-synchronous GST without mid-run intervention".
- `[ ]` **three capabilities** *(~60–67)* · D, C · "When wired, each validator is granted exactly three capabilities — the only ways" · *split dash-aside into own sentence; ownership list separate.* · **keep:** "exactly three capabilities", scheduler/network/logger, [[wiki/concepts/system-design]], Appendix A.
- `[ ]` **network timing** *(~67–70)* · D, L, ;-like · "The network models timing only — it delivers each message at most once, unordered," · *split at 2nd dash.* · **keep:** "at most once, unordered, under per-phase delay, loss, and partition", Table 3.2.
- `[ ]` **degeneracy** *(~263–268)* · D, C · "**Degeneracy (excluded).** The rescaling degenerates at `n = 4`, where it yields" · *split trailing "not because X but because Y, only Z" aside.* · **keep:** α_c=K=3, (1−α_c/K)^β, n=4 exclusion.
- `[ ]` **delay coupling** *(~399–404)* · D, L, C · "Because the slot duration grows with the delay regime, Casper FFG's time-to-finality" · *split mechanism / RQ1-interpretation; promote Ethereum-12s aside.* · **keep:** "delay coupling", "Ethereum's 12 s slot", "read as such rather than hidden".
- `[ ]` **flush/reduce** *(~437–441)* · ;, L, C · "**Flush and reduce.** The harness reduces the event stream to metrics: the commit latency" · *split consensus_msgs_per_acu derivation from latency/throughput defs.* · **keep:** t_decided−t_submit, 2(n²−1), O(n²), (2n²−2)/n=2n−2/n, ≈19.8.
- `[ ]` **Snowman safety regime** *(~569–574)* · D, L, C · "At the comparison baseline `β = 15` that analytical bound ranges from ~10⁻¹⁵ at `n = 10`" · *split bound-range / β∈{3,5}-regime / "lowering β manufactures throughput advantage".* · **keep:** β=15, ~10⁻¹⁵ to ~10⁻¹¹, β∈{3,5}, O(K·β), "never on cross-protocol throughput axis".
- `[ ]` **CRN** *(~576–580)* · D, ;, L · "Protocols are compared under the common random numbers of §3.4.2 — shared network," · *split at semicolon; promote stream-list aside.* · **keep:** §3.4.2, n_runs=20, raised to 30, "variance of cross-protocol difference".
- `[ ]` **other-protocols substitution** *(~466–472)* · D, L, ;-like · "The mean and interval are therefore properties of the aggregation, not of any single per-trial row;" · *split Family B/C/other-protocols list from "six-phase lifecycle identical".* · **keep:** 0…19, common-random-numbers, Table 3.1, AdversaryProfile to φ.
- `[ ]` **decide-differently** *(~27–30, borderline)* · D, C · "They are not one protocol run with different constants — they differ in leadership," · *linearize "Because… it needs both X and Y" cause-first.* · **keep:** §2.3/§3.3/Table 3.2, "single engine + downstream reconcile".

## ch4 — results (10)

> Already condensed once; high bar applied.

- `[ ]` **84–89** · D (3), L (~75), C · "What is intrinsic is the *qualitative* ordering, and it follows from the same formula:" · *split: linear-in-slot instances / above-1000ms-past-crossover / Ethereum-12s.* · **keep:** 2500/5000/10000 ms, 0.5/1/2 s, 0.2 s crossover, 1000 ms, 12 s, [[wiki/sources/2026-04-21_buterin-gasper-2020]].
- `[ ]` **103–110** · D, ;, L (~80), C · "The decision rate `tps` grows linearly in `n` — per-validator constant at 0.95" · *split at semicolon: tps=decision-event rate / goodput=comparable, flat in n.* · **keep:** 0.95, 0.40, ≈95 tx/s, ≈80 tx/s, Figs 4.3/4.4, §3.5.
- `[ ]` **141–145** · D, L, C · "PBFT's `2n` is its `O(n²)`-per-block cost — the all-to-all PREPARE and COMMIT" · *linearize: O(n²)/block → ACU denominator absorbs one n → per-unit O(n).* · **keep:** 2n, O(n²), O(n), [[wiki/sources/2026-04-21_castro-liskov-pbft-1999]], [[wiki/concepts/metric-reconciliation]], §3.5.
- `[ ]` **438–445** · D, L (~70), C, nesting · "First, the aligned milestones of §3.5 differ in kind: PBFT and Casper FFG offer deterministic finality," · *split: differ-in-kind / FFG accountable-revert cost / Snowman probabilistic bound.* · **keep:** (1−α_c/K)^β, 5×10⁻¹⁵ at n=10, 3×10⁻¹¹ at n=25, α_c=⌈0.8K⌉, 0.8, §3.3.3, [[wiki/sources/2026-04-21_buterin-griffith-casper-ffg-2017]].
- `[ ]` **519–525** · ;, L, C · "Snowman is the costliest case: it neither forks nor stalls, so the success rate holds," · *split at semicolon: ×62/×49 mechanism / severity near φ=0.20.* · **keep:** ×62 at n=10, ×49 at n=25, β, φ=0.20, [[wiki/experiments/2026-06-19_adversary-comparison]].
- `[ ]` **620–627** · D, L (~70), C · "The fork is deterministic — invariant across seeds because the equivocating set is fixed" · *split: seed-invariance / size-invariance / unaccountability.* · **keep:** (view,seq), count 229, both committee sizes, [[wiki/experiments/2026-06-18_equivocating-nodes]], [[wiki/experiments/2026-06-19_adversarial-degradation]].
- `[ ]` **775–786** · ; (chain), L (~110) · "Second, several measurement boundaries qualify how the numbers read. Safety results are seed-invariant," · *split semicolon-chained 4 boundaries into separate sentences/list.* · **keep:** §4.4.3/§3.4.1/§3.2, [[wiki/experiments/2026-06-19_adversarial-degradation]], 4 boundaries (seed-invariance, ε-not-witnessed, deadline-truncation, no-compute-cost).
- `[ ]` **375–381** · ;, L (~70), C · "Because a response survives only if both its query and reply survive," · *split at semicolon: per-round survival+slack / β-round cliff compounding.* · **keep:** K·(1−p)², α_c, slack K−α_c (1 at n=10, 4 at n=25), β=15, §3.3.3, [[wiki/experiments/2026-06-13_delay-analysis]].
- `[ ]` **471–477** · D, L (~70), C · "Each is swept from an honest control through a band of injected adversarial fractions `φ`" · *promote φ-vs-f gloss from dash-aside; threshold-extension separate.* · **keep:** φ-vs-f, replicas-vs-stake, one-third threshold, n∈{10,25}, 20 seeds, §3.4.2.
- `[ ]` **49–52** · D, C · "Goodput therefore carries the sole non-degenerate interval — a coefficient of variation near 2.2%" · *promote CV/half-width from dash-aside; "twenty seeds adequate" own sentence.* · **keep:** CV≈2.2%, half-width≈1%, Fig 4.1, "larger set cannot narrow a degenerate interval".

## ch5 — synthesis (12)

- `[ ]` **223–231** · L (~75), D, C, S · "The operator tradeoff of Figure 4.13 shows that the protocols which retain finalization under loss" · *split inflation-parenthetical / measurement-caveat / "FFG dies first"; linearize cause-first.* · **keep:** 2.16 (Snowman n=10), 3.57 (PBFT n=25), "measured at that protocol's own deepest surviving loss level… seeds that still finalize", "not a single point of Fig 4.13", [[wiki/experiments/2026-06-13_delay-comparison]].
- `[ ]` **135–142** · L (~60), C, ; · "Because acceptance requires `β` sequential polling rounds and each round waits on the slowest" · *split mechanism (β×slowest-of-K) / outcomes (12–15× vs ×62).* · **keep:** β, K, "twelve- to fifteenfold", "sixty-two", [[wiki/experiments/2026-06-13_delay-analysis]], [[wiki/experiments/2026-06-19_adversary-comparison]].
- `[ ]` **79–85** · ;, D, C · "Its leader-based, exact-quorum commit rule recovers from a stalled or slow leader by view-change" · *split at semicolon: recovery buys liveness / non-accountable forks.* · **keep:** 229 conflicting committed instances at φ=0.40, [[wiki/experiments/2026-06-19_adversarial-degradation]].
- `[ ]` **112–118** · L, D, C · "The cost it pays is concentrated on liveness under loss, and that cost is the measured analogue" · *promote here/there dash-aside; May-2023 analogue distinct clause.* · **keep:** "Ethereum's multi-epoch finality stall of May 2023 [21]", [[wiki/algorithms/pos]], deployment-analogue qualification.
- `[ ]` **22–28** · ;, C, S-ish · "Each of the three protocols is the strict best on at least one axis that no other matches" · *split at semicolon: each non-dominated / frontier shape.* · **keep:** none.
- `[ ]` **144–150** · L, ;, C · "When peers fall silent rather than merely slow, the polls starve: Snowman cliffs earliest" · *split: n=10 cliff (φ=0.20) / committee-size dependence (n=25→φ=0.33).* · **keep:** φ=0.20 at n=10, φ=0.33, "below the one-third the other two tolerate", [[wiki/experiments/2026-06-19_adversary-comparison]], [[wiki/experiments/2026-06-17_offline-validators]].
- `[ ]` **65–73** · L, D, multi-claim · "It is the least delay-exposed of the three, where Snowman pays an order of magnitude more" · *split: delay+loss resilience / liveness-adversary standing.* · **keep:** "twenty-percent packet loss", "area under finalization-rate curve", φ=0.33, φ=0.40, 2f+1, cites at 66/69/73.
- `[ ]` **41–44** · L, C, abstract · "These axes are the primary metrics of the four data-generating research questions" · *split: factual (axes=RQ metrics, not cherry-picked) / inference (dominance on designed quantities).* · **keep:** none.
- `[ ]` **9–12** · C, trailing appositive · "Read together, they raise the question this chapter takes up — whether any one family" · *promote RQ5 question to clean clause; demote trailing appositive.* · **keep:** [[wiki/concepts/research-questions]].
- `[ ]` **46–52** · L, ;-list · "The reading rests on the measurement conventions fixed in Chapter 3 and carried through" · *keep 3-item list; break off no-compute-cost caveat into own sentence.* · **keep:** commit_latency_ms, goodput, "leaving message-count/liveness/safety verdicts unaffected", [[wiki/concepts/output-format]], §3.5–§3.6.
- `[ ]` **244–251** · L, D, ;, C · "Because each structural choice that defends a family on one axis exposes it on another" · *keep 3-way must-not-fork/hold-liveness/resist-equivocation list; break off closing "accepts the cost…".* · **keep:** none (thesis point "accepts the cost the same mechanism imposes" — keep).
- `[ ]` **234–240** · L, D, ;-chain · "The second is that the rankings invert across axes — the family first against delay" · *split inversion-triple into own sentence; keep "consistent but multi-cornered".* · **keep:** [[wiki/experiments/2026-06-19_adversary-comparison]], "stable shape across the regimes".

## ch6 — conclusion (7)

- `[ ]` **26–35** · L (>120), D (4+), ; (×2), C · "RQ1–RQ3 fix the per-axis costs: commit latency is flat in the validator set but carried" · *split into 3 sentences (latency/throughput/overhead); promote each dash-aside breakdown.* · **keep:** +≈0.9 s, +≈27%, ×12–13, 1−φ, n=16, "order of magnitude", "roughly fourteenfold", [[wiki/concepts/key-findings]], "reported rather than empirically witnessed".
- `[ ]` **35–48** · L, D, ;, C, S · "No protocol is robust to every adversary, because the structural choice that defends" · *split 3-protocol enumeration; RQ5 verdict own sentence; cause-first.* · **keep:** "spare the view-0 primary", "analytical bound reported rather than empirically witnessed", "only accountable failure", "strict best on at least one axis", [[wiki/concepts/key-findings]], [[wiki/concepts/research-questions]].
- `[ ]` **64–71** · ;, C, L · "The simulator charges network latency but no signature-verification, execution, or bandwidth cost; this boundary bears on" · *split at semicolon; linearize: omission / flatters / doesn't bear on.* · **keep:** "flatters… compute-bound equivocation handling of PBFT and Casper FFG", "does not bear on message-count/liveness/safety", [[wiki/concepts/network-model]].
- `[ ]` **73–82** · D, L, C · "Thesis-scale committee sizes require rescaling protocol parameters — Snowman's `K`, `α_c`, and `β`," · *promote dash-listed params; split "reported as robust only where they survive" tail.* · **keep:** K, α_c, β, "Casper FFG slot-to-delay coherence rule", "robust only where they survive the governing sensitivity check", [[wiki/concepts/metric-reconciliation]].
- `[ ]` **139–146** · D, L (~50), C · "A second is an adaptive-timeout enhancement — exponential backoff with jitter, calibrated to" · *split: name enhancement / regime it needs / contrast steady-state; promote dash-aside def.* · **keep:** "calibrated to observed round-trip time", "tight view-change budget under high-jitter / post-GST recovery", "budget set generously enough recovery timers seldom fired", [[wiki/experiments/2026-06-10_delay-moderate]].
- `[ ]` **96–99** · D, C, L (~50) · "The sweep exercises the three generic capabilities of the adversary catalog and spares" · *promote "plausibly the sharpest attack" aside; split PBFT-standing consequence.* · **keep:** "spares the view-0 primary", "catalogued but not measured", "established only against adversaries that leave its leader honest", [[wiki/concepts/adversary-model]].
- `[ ]` **171–178** · C, L (~50), trailing relative · "This is more than the truism that three differently optimized protocols each win" · *split closing at "but the separable consequences"; trim trailing relative clause.* · **keep:** "on matched assumptions", "separable consequences" distinction.
