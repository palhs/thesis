# Q&A prep — thesis defense

Companion to `defense-script.md` (its header points here; the script holds
only the 10-minute talk). Format per entry: expected question → ~30-second
spoken answer → what to point at → verify-before-quoting notes.

---

## Q1 · "PBFT has view-change — what do Casper FFG and Snowman do when they stall?"

*Trigger: the S5 spec-strip `recovery` field, the S8-loss ranking, or the
view-change vignette (now appendix A3). A sharp committee will also connect S2 (Ethereum's
05/2023 finality stall RECOVERED on mainnet) with the FFG "recovery none"
label and probe the apparent contradiction.*

**Spoken answer (~30 s):**

> Three different recovery philosophies. PBFT rotates the faulty **role** —
> a timer fires, view-change elects a new leader, the round replays; that is
> a structural recovery measured in rounds. Casper FFG, as specified in the
> 2017 paper's core gadget and as I simulate it, has none — a missed
> checkpoint simply waits for the next epoch, and if two-thirds of stake is
> genuinely gone the chain stalls indefinitely. Production Gasper adds an
> **economic** repair the paper sketches in its discussion section: the
> inactivity leak — validators that stop voting bleed stake until the active
> set regains its two-thirds, which is how Ethereum mainnet exits real
> stalls. That mechanism is outside my simulation scope, and I list it under
> simplified implementations. Snowman's recovery is **implicit**: every poll
> round is a fresh random sample, so it is already an endless retry and
> self-heals the moment conditions improve — but it has no timer, no role to
> rotate, and no way to force progress while the fault persists, which is
> exactly the plateau-then-cliff in the loss results.

One-line close (ties to S9): *rotate the role · bleed the absentees ·
resample and wait — the recovery style mirrors each family's design choice.*

**Point at:** S5's mouse-only **Recovery ▸ Q&A** chip (4th chip, dashed
border — a three-panel visual built for exactly this question: rotate the
role / bleed the absentees / resample and wait, with the leak's safety cost
in red). Also: appendix A3 (the animated view-change vignette, ↓ past
Thank-you), the three spec-strip `recovery` fields, S8 Loss tab for the
consequence, S11 for the scope boundary. The chip is not in the Space
order — it opens only by mouse click, so the 10-minute talk never
touches it.

**If pressed further ("doesn't the leak fix FFG's weakness?"):**

> The leak is itself the thesis's central finding replayed: it buys
> liveness recovery by weakening accountable safety. The paper's own §4.2
> shows that under a partition both sides leak each other's deposits, each
> side reaches a supermajority, and **two conflicting checkpoints finalize
> with no validator slashed** (its Figure 6). Recovery mechanisms are not
> free in this family either — the currency is just accountability instead
> of messages.

**Grounding — verified 2026-07-15 against `raw/casper.pdf`:**
- Simulated behaviour: `drafts/ch4_results.md` §4.3 ("PBFT has a genuine
  recovery path … Snowman has in-round redundancy but no cross-round
  recovery … Casper FFG has neither").
- Inactivity leak: [7] Buterin & Griffith 2017, **§4.2 "Catastrophic
  Crashes" (p. 8)** — "recover … by instituting an 'inactivity leak' which
  slowly drains the deposit of any validator that does not vote … until …
  the validators who are voting are a supermajority"; simplest formula:
  per missed epoch a validator loses `D·p`. The **Conclusions (p. 9)** list
  the leak as an *extension* to Casper, not the core gadget — so the S5
  spec-strip "recovery: none" is correct for the simulated core protocol.
- Leak-weakens-accountability: same §4.2 — two conflicting finalized
  checkpoints, no slashing, validators "should simply favor whatever
  finalized checkpoint [they] saw first" (paper's Figure 6).
- Wiki-backed since 2026-07-15: `wiki/algorithms/pos.md` carries the leak
  under "Not implemented (deferred)" with the same section/page references.
- 05/2023 stall specifics: the leak activated during the incident but the
  stall also ended via client fixes — say "the leak is the in-protocol
  part of how mainnet recovers", do not attribute that incident's end to
  the leak alone.

---

## Q2 · "You open with Solana, but none of your three protocols is Solana's — what does your thesis say about those incidents?"

*Trigger: the S2 incident timeline, or the S10 callback line (which names
Ethereum + Cosmos as in-scope and Solana + Sui as beyond the harness). Also
reachable via S11 if the committee connects Sui to the DAG future-work item.*

**Spoken answer (~30 s):**

> Solana appears as motivation, not as a subject. Its consensus — Tower BFT
> with Proof of History — is a distinct design I did not implement, so my
> results make no claim about *why* Solana halted. What the Solana incidents
> establish is the phenomenon: safety proofs hold, but their assumptions —
> bounded delay, enough honest validators — are routinely violated in
> deployment. My thesis isolates those conditions for three families.
> Ethereum's incidents fall inside that scope directly — Casper FFG is one
> of my three protocols; Cosmos runs Tendermint, a direct PBFT descendant.
> Solana and Sui show the failure class is industry-wide, not specific to
> any one design — and extending the harness to further families is exactly
> the future-work direction; Sui's family, the DAG protocols, is already
> named there.

One-line close: *the harness is the contribution — each new family is one
more module in the protocol slot, not a new thesis.*

**Point at:** S2 timeline (the four incident groups), the S10 callback line
(it states the in-scope/out-of-scope split explicitly), S11 future work
(DAG family — Narwhal+Tusk — is Sui's family).

**Verify-before-quoting notes:**

- Scope mapping: Ethereum → Casper FFG (tested directly); Cosmos Hub →
  Tendermint, PBFT lineage (appendix slide A1 — the old S2B — says this on-slide; ↓ past Thank-you); Solana → Tower BFT +
  Proof of History (NOT implemented); Sui → Narwhal/Bullshark, DAG family
  (NOT implemented; S11 lists Narwhal+Tusk as future work).
- The wiki has **no page on Solana or Tower BFT** (checked 2026-07-16) — do
  not improvise mechanism claims about why Solana halted (leader schedule,
  fork choice, etc.); the defensible answer is scope-only, as written above.
- Do not claim any specific mainnet incident is "explained" by a simulator
  result — the S2 beat itself says real networks mix disturbances, so
  incident-level attribution is exactly what the thesis says cannot be done
  from public post-mortems.

---

## Q3 · "Why does the adversary sweep stop at φ = 0.30 for delayed-voting and silent, but equivocation gets extra points at 0.40 and 0.50?"

*Trigger: S7 chip C (the sweep definition "φ = 0 → 0.30, equivocation adds
0.40/0.50") or the S8 adversarial matrix (PBFT's quorum cliff at 0.40 and
the fork at 0.40 only exist because of those extra points).*

**Spoken answer:** TODO — not drafted yet. Before drafting, verify the
actual design rationale in the experiment-design pages
(`wiki/experiments/`, `drafts/ch3_*`) rather than inventing one.

**Point at:** S7 chip C (sweep definition), S8 tab C (the 0.40/0.50 cells).

---

## Q4 · "Define that metric" — S8 detail-layer terms (goodput · φ* · success rate · AURC)

*Trigger: these four sit in S8's committee-read layer and are deliberately
NOT glossed in the talk (decision 2026-07-16 — only argument-carrying terms
get spoken glosses; definitions-on-demand live here). Where each appears:
goodput — Tab A stat box + cuttable beat ("≈95 · 95 · 80 tx/s out of 100
offered"); φ\* "survival depth" — Tab C Snowman-silent cell (0.10 / 0.20);
success rate — Tab C cells ("success 1.0", "0.60–0.65"); AURC — Tab B-Loss
committee-read line ("AURC tie 0.351 vs 0.369").*

**Spoken answers:** TODO — one to two sentences each, not drafted yet.
Verify each definition before drafting; do not improvise expansions:

- **goodput** — verify in report §4.2 + ch6 limitations (goodput is reported
  *below saturation*, Poisson stream, zero conflict rate — the caveat is
  part of the honest answer).
- **φ\* (survival depth)** — verify the exact definition in §4.4.
- **success rate** — verify in §4.4 / Table 4.1 what counts as "success"
  (fraction of seeds that finalize? within what horizon?).
- **AURC** — verify the expansion and construction in §4.3.2 (area under
  the rate curve across loss levels?) before quoting any number.

---

## Q5 · "Your scaling chart only shows n = 25 — how do I know the trend holds from 4 to 25?"

*Trigger: S8 Tab A shows a single-endpoint bar chart (n = 25) with fitted
slope labels (≈ 2n · ≈ 1.15n · ≈ 2Kβ). The "measured trends match published
asymptotics" line is an assertion; a committee member may ask to see it.*

**Spoken answer (~30 s):**

> The full sweep is five points — n = 4, 7, 10, 16, 25, twenty seeds each —
> and the endpoint bars are just the right edge of that chart. Across the
> whole range the ranking never changes: Casper FFG cheapest, PBFT second,
> Snowman an order of magnitude out. And the measured points sit on the
> published asymptotics the whole way: PBFT lands exactly on 2n − 2/n —
> 7.5 messages per unit at n = 4, 49.9 at n = 25 — and Snowman exactly on
> 2Kβ with β = 15. Casper FFG reads slightly above its 1.125n line at every
> n; that is a fixed per-run overhead — block proposals and boundary
> epochs — which only shows because FFG's message base is the smallest.
> One caveat: Snowman has no n = 4 point, because the parameter rescaling
> K = min(20, n − 1) degenerates to unanimity there.

One-line close: *the endpoint is where the gap is widest; the sweep is
where the law is checked.*

**Point at:** S8's mouse-only **Sweep ▸ Q&A** chip (5th chip, dashed
border) — the full 4 → 25 line chart, measured markers over dashed
predictions, log scale; mirrors thesis Figure 4.1. The chip is not in the
Space order — it opens only by mouse click, so the 10-minute talk never
touches it.

**If pressed further ("and beyond 25?"):**

> Beyond the sweep I only have the asymptotics, not measurements — that is
> a stated limitation (§6): the sweep is sub-production scale, and
> extrapolation rests on the published message-complexity laws, not on my
> data. One structural note the chart makes visible: K caps at 20 above
> n = 21, so Snowman's 2Kβ line flattens just past the sweep — the
> per-validator constancy Avalanche advertises begins roughly where my
> sweep ends.

**Grounding — verified 2026-07-17 against `results/baseline/aggregated.csv`:**
- Measured `total_msgs_per_acu_mean` (uniform workload): PBFT 7.5 / 13.71 /
  19.8 / 31.88 / 49.92; Casper FFG 5.16 / 8.79 / 12.26 / 19.10 / 29.28;
  Snowman — / 180.86 / 270.9 / 450.94 / 600.96 at n = 4 / 7 / 10 / 16 / 25.
- PBFT law: 2n − 2/n reproduces every PBFT value exactly (e.g. n = 4:
  8 − 0.5 = 7.5). Snowman law: 2Kβ, K = min(20, n − 1), β = 15 reproduces
  every Snowman value (n = 7: 2·6·15 = 180 ≈ 180.86).
- FFG-above-the-line explanation: `drafts/ch4_results.md` §4.2 (fixed
  per-unit overhead, un-amortized boundary epochs of a finite run).
- n = 4 Snowman exclusion: `drafts/ch4_results.md` §4.2 ("threshold
  collapses to a degenerate boundary").
- Sub-production-scale caveat: `drafts/ch6_conclusion.md` limitations
  ("Snowman's measured performance may partly reflect a small-n artifact").
- Thesis figure: Figure 4.1, `results/baseline/plots/theory_vs_measured.pdf`.

---

## Q6 · "Where is the theory? Why 3f+1 — and what do FLP and partial synchrony have to do with your three families?"

*Trigger: the deck deliberately carries no theory slide (decision 2026-07-18
— foundations live here, only the general surface stays visible: the S5
spec-strip `synchrony` and `finality` rows). A committee member testing
fundamentals will ask for the classical results behind the ⅔ quorums and the
ε bound.*

**Spoken answer (~30 s):**

> Three classical results bound every protocol on these slides. First, the
> Byzantine Generals result: deterministic agreement with f arbitrary faults
> needs n ≥ 3f + 1 replicas — that is why every quorum in the deck is
> two-thirds, 2f + 1 out of 3f + 1. Second, FLP: under full asynchrony no
> deterministic protocol guarantees both safety and liveness against even
> one crash fault. Third, the escape — partial synchrony: after some unknown
> stabilization time the network behaves, and consensus becomes solvable for
> f < n/3. The three families are three ways of paying that impossibility.
> PBFT keeps the classical fault model and the 3f+1 quorum, relaxing only
> timing. Casper FFG keeps both and adds an economic layer — slashing turns
> Byzantine behavior from an assumption into a disincentivized act. Snowman
> abandons the quorum entirely: repeated random sampling buys asynchrony
> tolerance and n-independent per-validator cost, and pays with a non-zero
> safety probability ε. The synchrony row on S5 is the visible tip of
> exactly this trade.

**If pressed further (CAP):**

> CAP is the deployment-facing restatement: under a partition a chain must
> give up consistency or availability — partition-tolerance is not optional.
> The loss results replay it: Casper FFG halts rather than fork
> (consistency-leaning), Snowman keeps answering on a bounded ε
> (availability-leaning), PBFT recovers by view-change until the quorum
> itself is gone.

One-line close: *one impossibility, three ways to pay for it — timing,
stake, or certainty.*

**Point at:** S5 spec-strip `synchrony` row (partial · partial · async) and
`finality` row (ε = 0 · ε = 0 · ε > 0 bounded); S8 Loss tab for the CAP
replay if pressed.

**Verify-before-quoting notes:**

- Grounding: report §1.1 ([1] 3f+1 Byzantine threshold, [2] FLP, [3]
  partial synchrony) and §2.1 (the three relaxations, CAP [18]); wiki pages
  `concepts/byzantine-generals`, `concepts/flp-impossibility`,
  `concepts/synchrony-models`, `concepts/cap-theorem`.
- FLP precisely: *no deterministic protocol, one **crash** fault, full
  asynchrony* — do not overstate it as "consensus is impossible" or say
  "Byzantine fault"; randomization (Snowman) and partial synchrony (PBFT,
  FFG) are the two standard escapes, and the deck's families use one each.
- The CAP mapping (FFG consistency-leaning, Snowman availability-leaning)
  is an interpretive gloss, not a report claim — flag it as a reading if
  challenged; the report states CAP only as the general cost of partition
  (§2.1).
