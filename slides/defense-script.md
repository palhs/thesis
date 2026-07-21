# Speaking script — thesis defense (10 minutes)

Deck: `slides/thesis-defense.html` · **11 talk slides + 3 Q&A appendix slides** ·
core **9:50** of a 10:00 slot.
This is the script to MEMORIZE via the anchor-skeleton structure. Q&A prep is a
separate session, kept in `slides/qa-prep.md` — not here.

2026-07-21 — **S7/S8/S9 now carry their spoken lines ON-SLIDE** (sayboxes):
every anchor and per-press beat below for those three slides sits verbatim in a
bordered reading box on the pane itself — visible on pane entry, costs no Space
press, one ▶ line = one press. S7's box swaps its middle line with the A/B/C
chips; S8's sits under each tab's chart (charts shrunk 600 → 490 px to fit);
S9's opening line, † caveat, core anchor, per-protocol sentences and the
transition all read directly off the slide. Memorization for S7–S9 is now
optional — read the boxes.

2026-07-19 — **RESTRUCTURED 15 → 10 MINUTES.** The 15-minute deck + script are
frozen as `thesis-defense-old.html` / `defense-script-old.md`. What changed:

- **S2B "The three contenders" and S3 "Three yardsticks" left the spoken talk**
  (−1:30). They live on as **appendix slides A1/A2 after the Thank-you slide** —
  Space can never reach them; jump with ↓ during Q&A. Their content is covered
  in-flow: the colour legend moved to S1 (small caption next to the pills), the
  protocol introductions moved into the S5 pane-opening anchors, and the
  yardstick/gap argument compressed into S2's transition anchor + its on-slide
  sub-line.
- **All former `(cuttable)` beats in S8 are gone as presses** — their on-slide
  detail (latency/goodput stat box, delay-vs-messages badge, tail numbers) now
  reveals together with the preceding press, as a reading layer only.
- **S7 collapsed to one press per family** (was three).
- **S6 recut 6 → 4 presses** (same day, three passes): pass 2 fixed the
  press structure (one idea per press) and the diagram's self-contradiction
  — the slot no longer sits inside a box labelled "fixed infrastructure";
  the outer box is now **simulator** with a solid-border **fixed core**
  ("identical in every run") and the dashed **swapped per run / protocol
  under test** slot. Visual code: solid = fixed, dashed = varies. Pass 3
  made the slide tell the machine's story in execution order (mechanics
  verified against `src/config/factory.py`, `src/network/network.py`,
  `src/event_log/logger.py`, `src/output/aggregate.py`): config drawn as a
  **stack** ("one config = one scenario") → ① build from the config's
  constants → ② the **run loop** (scheduler → protocol → network → back on
  the queue, logger tapping) drawn as three marching arrows, ending in one
  result row → ③ the one-variable punch (matching dashed ring on the
  config's `protocol` field + attribution badge) → ④ ×20 seeds → new
  **aggregate box** (mean · 95% CI per scenario), ACU folded into the same
  beat. Cost: S6 0:45 → 0:55, funded by compressing S7 0:25 → 0:15.
  Final polish: beats re-anchored on the config's five fields — ① names
  what each of four fields sets in the machine (n → validators, timeline →
  network, adversary → flipped validators, seed → RNG) and holds back
  `protocol`, which ③ pays off as the slot-filler; the opening anchor now
  carries the whole arc ("a config goes in, one aggregated line comes
  out"). The S7 compression that funded this was later undone by the S5
  view-change move — see that bullet.
- **S5 PBFT view-change vignette moved to appendix A3** (2026-07-19, after
  the S6 recut): the fault scene was the only mid-walkthrough register
  switch — the other two protocols read happy-path only — so the PBFT pane
  now matches them: 3 presses, mechanism only. The full animated sequence
  lives on as **appendix slide A3** (autoplays on entry, ↓ only), and the
  Recovery ▸ Q&A chip's PBFT panel points to it. First spoken mention of
  view-change is now the S8 loss beat, which self-glosses ("view-change
  rotates the leader"). Timing: S5 1:30 → 1:20; the freed 10 s refunds
  S7 back to 0:25 (undoing the compression that funded S6) — S8 still
  enters at 4:40.
- **S2 incident beats merged 3 → 1** (2026-07-20): the per-network presses
  (Solana / Ethereum / Cosmos+Sui) are now one press that cascades the whole
  timeline in; spoken generically — the point is "many networks fail", the
  on-slide labels carry the specifics. S2 is now 3 presses total (incidents ·
  frame · big question). Timing: S2 speak 1:00 → 0:50.
- **S5 FFG pane gained a first press — "the chain underneath"** (2026-07-20):
  grey slot-blocks fill the gaps between checkpoints, two proposer arrows
  from the validator row, caption "checkpoint = epoch-boundary block".
  Motivation: the pane opened on free-floating checkpoints, so the audience
  couldn't tell where blocks/transactions come from (unlike PBFT's
  client→primary flow). Colour code: grey = block production, purple = FFG
  votes. FFG pane is now 5 presses; the opening anchor carries the PBFT
  contrast ("PBFT decides each block; Casper finalizes checkpoints on a
  chain it doesn't build"). Timing: S5 speak 1:20 → 1:30, funded by the S2
  merge above — everything from S5's leave onward is unchanged.
- **S4 RQ wording tightened + 5 presses merged → 1** (2026-07-21): the
  WHEN/WHAT/HOW-MUCH/WHO/WHICH lead-word device is gone — each line is now a
  plain full question (the RQ pill moved left as the anchor column), closer to
  the report §1.5 phrasing; RQ5 is now the four-word "Does any protocol
  dominate?", which S9 answers verbatim. All five lines cascade in on a
  single Space (internal 200 ms pacing preserved — same pattern as the S2
  incident merge). S4 is now 1 press. Timing unchanged (speak 0:30): reading
  the five questions fills the slot; seconds saved become buffer at S5.
  Follow-up same day: RQ2 re-worded "How much throughput do Byzantine nodes
  cost?" → "How does throughput degrade as Byzantine nodes approach the
  fault threshold?" — the first form promised a headline number the Tab C
  matrix never shows (it shows degradation *shape*: immune / graceful decay /
  starves, success rates + φ*); the new form matches both the pane and the
  report §1.5 RQ2 phrasing. Also: the four S8 tab chips now carry small RQ
  tags (A · RQ3, B-Delay · RQ1, B-Loss · RQ1, C · RQ2·RQ4) so the jury can
  map tab → RQ without the spoken cue; Sweep ▸ Q&A stays untagged.
- **S11 lists trimmed 6+5 → 3+3** (2026-07-21): limitations kept = simplified
  one-per-family implementations · n ≤ 25 · ε never witnessed; future work
  kept = empirical ε witness · threshold-signature aggregation · DAG family.
  Dropped from the slide (still in report ch. 6): loss-is-permanent-drop,
  view-0 adversary placement, no compute/bandwidth model, saturation
  throughput, adaptive timeouts. The loss-permanent-drop clause survives as
  a SPOKEN-ONLY guard in the S11 beat — it shields the FFG-collapses-at-5%
  headline. Press structure unchanged (3 presses).
- Everything else kept its press structure; the speech is compressed.
- New safety valve (replaces the old S8 cut rule): **enter S8 later than 5:10 →
  drop the two remaining `(cuttable)` beats** (S10 callback, S11 future-work).
- Numbering is now `NN / 11`; appendix slides show `Q&A appendix` in the corner.

Earlier history (detail layer, S5 view-change vignette, S9 spoken † caveat,
S10 callback rewording, S8 glosses…) is preserved in `defense-script-old.md`.

## How to use

- **ANCHOR** (quoted text) = memorize **verbatim**. Each slide has an opening
  anchor and a transition anchor — those are where you're most likely to
  freeze; the middle is spoken freely following the beats.
- **Beat** (bullet) = free-form talking point, 5–10 cue words, in spoken
  register: English phrasing matching the exact wording on the slide.
  **Every bold number — say it exactly, no rounding or drifting.**
- `▶` = **one Space press**. The deck runs in step mode: each Space reveals
  exactly one beat; when a pane runs out of steps, Space auto-advances to the
  next chip/tab, and when chips/tabs run out, to the next slide. **The whole
  talk uses a single key.** Space stops dead at the Thank-you slide — it can
  never fall into the appendix. The mouse and ↓/↑ are for Q&A only.
  - Space / → / PageDown = next step · Shift+Space / ← / PageUp = step back
  - ↓ / ↑ = jump whole slides (use in Q&A; ↓ past Thank-you = appendix)
- `(cuttable)` = optional beat. **The single cut rule: if you enter S8 later
  than 5:10 → drop every `(cuttable)` beat from there on.** No other
  decisions exist.
- Timing is written at the top of each slide: `enter · speak · leave`. Glance
  once at each slide transition.

---

## S1 · Title — enter 0:00 · speak 0:30 · leave 0:30

*(slide auto-plays its full animation, no Space needed mid-slide)*

**OPENING ANCHOR:**
> "Dear committee members, my name is Le Ngoc Phan Anh, student ID BI12-010.
> My thesis is *Performance–Security Evaluation of Layer-1 Consensus under
> Delay and Adversarial Conditions* — a simulation-based comparative study,
> carried out under the supervision of Dr. Giang Anh Tuan."

- three protocols — **PBFT** (amber) · **Casper FFG** (violet) · **Snowman**
  (ice) — one colour per protocol, on every chart to the end (the caption
  next to the pills says it; half a sentence, S5 introduces them properly)

**TRANSITION ANCHOR:**
> "Let me begin with why this thesis exists."

`▶ → S2`

---

## S2 · Proven safe. Still halting. — enter 0:30 · speak 0:50 · leave 1:20

**OPENING ANCHOR:**
> "Over the past few years, we have watched some of the largest networks in
> the industry fail in production. A few examples."

- `▶` (whole incident timeline cascades in on one press) — network after
  network, year after year: halts, reorgs, finality stalls — Solana,
  Ethereum, Cosmos Hub, Sui — and each one interrupts the services built
  on top *(sweep the timeline with one gesture; speak generically — the
  on-slide labels carry the dates and specifics, do not read the incidents
  out one by one)*
- `▶` (text box) — and pinning down WHAT broke each of them is genuinely
  hard: every one of these systems runs a protocol with a **safety proof**;
  the proofs are NOT wrong — what breaks are their **assumptions** —
  bounded delay, enough honest validators; in real operation delay, loss
  and malicious nodes act **at once**, the conditions overlap, so you
  cannot tell which condition caused which failure *(this beat is where the
  slide title "Proven safe. Still halting." pays off — gesture at it)*

`▶` (big question appears) — **TRANSITION ANCHOR** *(carries the old
"yardsticks" argument in compressed form — the sub-line on the slide backs
it up)*:
> "So: which condition breaks which protocol? Published numbers cannot
> answer this — each family measures itself in its own way, so their
> numbers can never be compared side by side. That is the gap: I built
> one harness that tests all three families under exactly the same
> conditions."

`▶ → S4`

📎 *Detail held back for Q&A, not spoken: the measure-it-differently
examples (throughput vs. finality delay vs. ε at one parameter setting)
are on the slide's sub-line; the prior-work point — the one matched
harness before this, Gervais et al., covers Proof-of-Work only — lives on
appendix A2 and `qa-prep.md`. Reach for it only if asked "why not use
published numbers / what is the research gap".*

---

## S4 · The goal — 5 questions — enter 1:20 · speak 0:30 · leave 1:50

**OPENING ANCHOR:**
> "The goal fits in one line: one simulator, three protocols, one shared set
> of assumptions. Five questions."

*(ONE press — all five questions cascade in, top to bottom; read them
straight off the slide, one breath per line, nothing between them; slide
text matches report §1.3)*

- `▶` (five RQs cascade on one press) — read each line as a plain question:
  "How much does finality slow when the network slows? How does throughput
  degrade as Byzantine nodes approach the fault threshold? How many messages
  does one commit cost? Which adversary breaks which protocol — and which
  property?" — then land on the last line and hold it half a beat:
  "**Does any protocol dominate?**" *(that question is answered verbatim
  on S9)*

**TRANSITION ANCHOR:**
> "Before measuring, we need to see just how differently these three
> protocols operate."

`▶ → S5`

---

## S5 · Three families, three protocols — enter 1:50 · speak 1:30 · leave 3:20

*(opens on the PBFT diagram: 4 nodes already visible. The pane-opening
anchors now carry the protocol introductions that used to live on S2B —
year, authors, where it runs — one breath each, then straight into the
mechanism. All three panes are now **happy-path only** — the same register
throughout; PBFT's fault scene lives in appendix A3.)*

**OPENING ANCHOR:**
> "For each family I picked one representative. First — PBFT, 1999, Castro
> and Liskov: the classic leader-driven family, whose descendants run Cosmos
> and Aptos today."

**PBFT** — n=4, node 3 offline (f=1):
- `▶` client sends a request to the **primary** → primary broadcasts
  **PRE-PREPARE**
- `▶` **PREPARE**, then **COMMIT** — two identical **all-to-all** rounds →
  the source of the **O(n²)** cost
- `▶` decided at quorum **2f+1** — **3 of 4** — even with 1 node dead;
  finality **deterministic**, once committed, permanent

`▶` (deck auto-switches to the **Casper FFG** chip):
> "Second — Casper FFG, 2017, Buterin and Griffith: Ethereum's finality
> layer since the Merge. And here is the key contrast with PBFT: PBFT
> decides each block, one at a time, as it happens. Casper builds nothing —
> it is a finality layer bolted onto a chain that keeps producing blocks."
- `▶` (grey layer fills in) — every **slot**, one proposer adds one block;
  **transactions live in those blocks**; a **checkpoint** is just the
  epoch-boundary block — the grey chain grows regardless of FFG, FFG only
  votes on the checkpoints *(grey = block production, purple = FFG votes)*
- `▶` validators (weighted by **stake**) send attestations that accumulate
  on the link between two checkpoints; once **⅔ of stake**...
- `▶` ...the checkpoint is **justified**
- `▶` a justified child ⇒ the parent is **finalized** — a two-step commit
- `▶` finality trails **behind** the chain tip; cost only **~1.15n**
  messages; **slashing** → safety violations become attributable

`▶` (deck auto-switches to the **Snowman** chip):
> "Third — Snowman, 2019, from Avalanche — its production engine since 2020.
> There is no leader at all."
- `▶` each round: poll **K random peers**; if ≥ **α_c** reply identically →
  confidence counter **1/15**
- `▶` next round — an entirely FRESH sample → **2/15**
- `▶` switching preference midway → counter **resets to 0** — where the
  price is paid
- `▶` after **β = 15** consecutive rounds → **ACCEPTED**; finality
  **probabilistic**: ε ≤ (1−α_c/K)^β; per-validator cost **independent of n**

**TRANSITION ANCHOR:**
> "Three mechanisms so different that their native metrics cannot be
> compared. For a fair comparison, everything around the protocol must be
> identical — that is the harness's job."

`▶ → S6`

📎 *On the slide, no need to read aloud: spec strip under the caption
(synchrony · proposer · quorum · finality · pressure point · recovery, from
Table 2.1). For recovery questions there is a 4th, MOUSE-ONLY chip —
**Recovery ▸ Q&A** (dashed border) — Space never enters it; the animated
PBFT view-change sequence is **appendix A3** (↓). Spoken answer:
`qa-prep.md` Q1.*

---

## S6 · One harness — enter 3:20 · speak 0:55 · leave 4:15

*(opens with the config stack already visible; **4 presses, one full idea
each**, telling the machine's story in execution order: generate configs →
① build from the constants → ② the run loop driven by them → ③ the
held-back field fills the slot → ④ repeat & aggregate. The extra 10 s over
the old cut is funded by the S5 view-change move. No half-sentences:
finish each idea, then press.)*

**OPENING ANCHOR:**
> "Every experiment runs through exactly one pipeline: a config goes in,
> one aggregated line comes out."

- (already visible) **step 0 — generate the configs**: 5 fields — protocol ·
  n · timeline · adversary · seed; **one config = one scenario**, sweeping
  the fields generates the whole grid *(spoken word "config", not "file" —
  the sweep script generates the cells)*
- `▶` **① BUILD**: launching one config **builds the simulator with its
  values as the machine's constants** — **n** spawns the validators · the
  **timeline** arms the network with its delay/loss phases · the
  **adversary** flips that fraction of validators to a Byzantine behavior ·
  the **seed** pins every random draw — fully deterministic. *(the one
  field left — protocol — drops into the dashed slot; name it, hold the
  "why dashed" for press ③)*
- `▶` **② THE RUN LOOP** *(three marching arrows appear — trace them with
  the pointer)*: those constants now drive the loop — the **scheduler**
  pops the earliest event in **virtual time** and hands it to the protocol
  → the protocol answers with messages into the **network**, which rolls
  drop and delay **from the config's current timeline phase** and puts
  each delivery **back on the queue** → the **logger** records every event
  as it passes; when the run stops → the log condenses to **one result
  row**, stamped **commit_hash + seed** — re-runnable bit-for-bit
- `▶` **③ THE ONE VARIABLE** *(the config's `protocol` field gets the same
  dashed ring as the slot — point at both)*: the held-back field pays off —
  four fields set the machine, this one only fills the slot; the loop is
  **identical in every scenario**; **dashed border = the one thing that
  swaps** — the **protocol under test** ⇒ output differences are
  **attributable to the protocol**
- `▶` **④ REPEAT & AGGREGATE**: rerun **×20 seeds** per cell *(slide notes
  30 near threshold — don't read)*; the twenty result rows collapse to
  **mean + 95% CI** per scenario — every count in the common unit, **ACU,
  atomic commit unit**: 1 PBFT block ≡ 1 finalized FFG checkpoint ≡
  1 accepted Snowman block

📎 *ACU caption carries the CI detail — 95% Student-t · 95% Wilson. Point
at it only if asked about statistical confidence.*

📎 *Lost mid-slide? The recovery line that always works: "configs → build
from the constants → loop in virtual time → protocol fills the dashed
slot → twenty seeds → aggregate."*

**TRANSITION ANCHOR:**
> "On that harness, three experiment families — each sweeping exactly one
> axis."

`▶ → S7`

---

## S7 · Three run families — enter 4:15 · speak 0:25 · leave 4:40

*(one press reveals a whole family pane — one breath per pane; the footer
and details are a reading layer only)*

**OPENING ANCHOR:**
> "Three run families — each sweeps one axis while everything else stays
> pinned."

- `▶` **A — Scaling**: n = **4 → 25**, clean network, all honest → **RQ3**
- `▶` (switch to **B**) `▶` **B — Delay**: timelines up to heavy-tail
  **1–5 s**, plus loss **5/10/20%**; n ∈ {10, 25} → **RQ1**
- `▶` (switch to **C**) `▶` **C — Adversarial**: adversary fraction
  **φ = 0 → 0.30** (equivocation adds **0.40/0.50**); three behaviors →
  **RQ2 · RQ4** *(footer — 100 tx/s, 512 B, 20 seeds — is for reading, skip)*

**TRANSITION ANCHOR:**
> "That is how we measure. Now the main part — the results."

`▶ → S8`

---

## S8 · Results — 4 tabs — enter 4:40 · speak 3:00 · leave 7:40

**⏱ THE ONLY DECISION POINT: check the clock when entering this slide.
Later than 5:10 → drop every `(cuttable)` beat from here on (there are two:
S10 callback, S11 future work).**

**OPENING ANCHOR:**
> "The results sit in four tabs, in the same order as the three run
> families."

**Tab A — Scaling (RQ3)** (open by default, now 2 presses):
- `▶` messages per ACU at **n = 25**, log axis: Casper FFG **≈29** ·
  PBFT **≈50** · Snowman **≈601**
- `▶` trends match theory — **1.15n · 2n · 2Kβ**, **per-validator**: PBFT's
  **2n** × n validators = the **O(n²)** from the diagram slide; FFG is
  cheapest because the epoch votes **once** — one attestation round per
  epoch against PBFT's two all-to-all phases per block — and that same
  epoch pacing is why its finality is **≈5 s**, not 1 s: cheap and slow are
  one design choice; the
  **order-of-magnitude** gap is the price of subsampling *(this press also
  reveals the latency/goodput stat box — reading layer, do NOT speak its
  numbers beyond the ≈5 s already used; full glosses live in qa-prep Q7)*

`▶` (switch to tab **B — Delay, RQ1**, 2 presses):
- `▶` slowdown vs. zero-delay baseline: FFG **×1.3** · PBFT **×1.9** —
  round-bounded, insensitive to tail shape
- `▶` Snowman **×12–15** — each round polls a random sample and must hear
  back from **most of it**, **15 successful rounds in a row** — so it keeps
  running into the heavy tail, round after round *(this press also reveals
  the tail numbers + the "delay costs time, not messages" badge — reading
  layer, do NOT speak)*

`▶` (switch to tab **B — Loss**, 3 presses):
- `▶` three finalization-rate curves across loss **0 → 20%**
- `▶` ranking **PBFT > Snowman > FFG** — PBFT alone still finalizes at
  **20%** thanks to its recovery path (**view-change** rotates the leader);
  Snowman plateaus-then-cliffs at **10%**; FFG collapses at the first
  **5%** step — it has neither *(n=25 AURC-tie note on slide: read only if
  asked about stability in n)*
- `▶` no protocol **forks** — the chain never splits; loss consumes
  **liveness** — progress stops — not **safety** — nothing committed is
  ever contradicted. And **in exchange for resilience, PBFT pays more
  cost** — msgs per committed unit climb with loss (view-change retries;
  the dashed line that appears on this press) *(detail — collapsing
  protocols inflate faster, PBFT cheapest at 20%, ×2–3.5 latency,
  Fig A.3 — reading layer, do NOT speak)*

`▶` (switch to tab **C — Adversarial, RQ2+RQ4** — 3×3 matrix, 4 presses):
- `▶` **delayed voting**: PBFT immune, success **1.0** · FFG drops to
  **0.60–0.65** — the rotating proposer gets stalled · Snowman survives but
  crawls — **×62 / ×49** slower
- `▶` **silent**: PBFT clean up to **φ = 0.33**, quorum cliff at **0.40** ·
  FFG decays toward **0.33** · Snowman starves first — **φ\* = 0.10 / 0.20**
- `▶` **equivocation** — conflicting votes for two blocks at once — beyond
  ⅓: PBFT **forks** at **0.40**, NOT attributable · FFG: a fork is
  possible past ⅓, but **accountable** — any fork costs
  **≥⅓ of stake, provably slashable**; measured: no fork, slashable stake
  crosses ⅓ at 0.40 · Snowman: no fork surface —
  bound **ε ≈ 5×10⁻¹⁵ / 3×10⁻¹¹**
- `▶` (legend appears — point) green holds · yellow degrades · red breaks

**TRANSITION ANCHOR:**
> "Four tabs — no protocol wins all four. That is precisely the answer to
> RQ5."

`▶ → S9`

📎 *On S8 there is a 5th, MOUSE-ONLY chip — **Sweep ▸ Q&A** — Space never
enters it. It holds the full Family-A sweep (messages per ACU, n = 4 → 25,
log scale): measured markers sitting on the dashed published asymptotics,
same ranking at every n. Jump here for "does the ranking hold at every n,
or only at n = 25?".*

---

## S9 · RQ5 — no one dominates — enter 7:40 · speak 0:55 · leave 8:35

- `▶` an **8-axis** radar from Table 5.1 — ordinal, illustrative; the table
  in the report is the evidence — *then the † caveat in ONE sentence
  (point at the † note under the radar):*
  > "One caveat: the two †-marked axes — accountable safety and equivocation
  > safety — are not measured contests but a by-definition and an analytical
  > result; strip them, and Snowman holds no measured corner."

`▶` — **CORE-IDEA ANCHOR (memorize verbatim):**
> "The central finding: the SAME design choice produces both each
> protocol's strength and its weakness."

*(one sentence per protocol, no more)*
- `▶` **Snowman** — K-peer subsampling: thrives when peers are SLOW,
  starves when peers are SILENT
- `▶` **PBFT** — leader-quorum commit: rides out delay, loss, silence — but
  past ⅓ equivocation it forks with no attribution
- `▶` **Casper FFG** — epoch-paced finality: cheapest, least
  delay-sensitive — first to collapse under loss; in exchange, the ONLY one
  with accountable safety

**TRANSITION ANCHOR:**
> "No winner — so how do you use these results? As a selection map."

`▶ → S10`

---

## S10 · Selection map — enter 8:35 · speak 0:30 · leave 9:05

*(one line per press)*

- `▶` need **accountability** → **Casper FFG** — slashing prices a
  violation at ≥⅓ of stake
- `▶` need to **survive network disturbance** → **PBFT** — the only one
  with a recovery path
- `▶` need **equivocation resistance** → **Snowman** — no fork surface
- `▶` (cuttable — callback) the opening incidents: **Ethereum** and
  **Cosmos** run the two families whose structural limits these results
  map; **Solana** and **Sui** show the same failure class outside the
  harness — motivation, not scope (if pressed: `qa-prep.md` Q2)
- `▶` contributions, one breath: simulator · **3** implementations ·
  dataset + analysis · methodology extending Gervais et al. to BFT

**TRANSITION ANCHOR:**
> "Within what scope do these results hold — the limitations."

`▶ → S11`

---

## S11 · Limitations & future work — enter 9:05 · speak 0:35 · leave 9:40

- `▶` **limitations**, one breath — the slide holds the top three:
  we tested simplified versions, so results speak for THESE three
  protocols, not their whole families · at most **25 validators** — beyond
  that, no data · Snowman's safety rests on a formula our experiments
  never actually tested. Then ONE spoken-only guard, not on the slide:
  loss is a PERMANENT drop — no retransmission — so the loss curves
  are upper bounds on fragility *(keep this sentence — it shields the
  FFG-collapses-at-5% headline; full limitation list lives in report ch. 6)*
- `▶` (cuttable) **future work**, one sentence: test ε directly ·
  add the signature aggregation real systems use · implement a new
  protocol family *(kept vague on purpose — name DAG / Narwhal + Tusk
  only if the jury asks which family)*

`▶` — **CLOSING ANCHOR (memorize verbatim):**
> "The contribution of this thesis is a mechanism map of the
> performance–security frontier — not the naming of a single winner."

`▶ → S12`

---

## S12 · Thank you — 9:50

**ANCHOR:**
> "Thank you, committee members, for your attention. I am ready for your
> questions."

*(Space is dead past this slide — it cannot fall into the appendix.)*

---

## Q&A appendix (after S12 — ↓/↑ and mouse only)

- **A1 · The three contenders** — the old S2B card slide: year, authors,
  mechanism one-liner, where each runs in production. Jump here for "why
  these three protocols / what do they represent".
- **A2 · Three yardsticks** — the old S3 gap slide: what each family
  reports, what each number omits, the Gervais et al. precedent. Jump here
  for "what exactly is the research gap / why not use published numbers".
- **A3 · PBFT view-change** — the animated fault vignette that used to be
  the PBFT pane's 4th press: primary silent → timeout Δ → VIEW-CHANGE
  (all-to-all, 2f+1) → NEW-VIEW → phases replay. Jump here for "what
  exactly is the recovery path" or to back up the S8 loss result; the
  compare-all-three view stays on the S5 Recovery ▸ Q&A chip.
- **A4 · Justified ≠ safe** — two-panel Casper vignette. Panel ①: C justified
  on branch X at epoch e, the finalize link C → C′ never reaches ⅔, and the
  next epoch votes the *same source A to a later target D* on branch Y —
  no double vote (targets e ≠ e+1), no surround (same source) — C is
  legally abandoned, nobody slashed. Panel ②: once ⅔ sign C → C′ (direct
  child ⇒ C finalized), every escape link must surround (e−1 → e+2 around
  e → e+1) or double-vote (second target at e+1) → ≥⅓ slashable. Jump here
  for "what does justified actually guarantee / why two rounds / what is
  accountable safety".
- All four autoplay their full reveal on entry — no stepping needed.
- Plus, on S5: the mouse-only **Recovery ▸ Q&A** chip (dashed border).
- Plus, on S8: the mouse-only **Sweep ▸ Q&A** chip — the full n = 4 → 25
  sweep behind Tab A's endpoint bars (see the 📎 note under S8).
- Corner badge shows `Q&A appendix` instead of a slide number, so the
  committee sees these are backup, not skipped content.

---

## Practice notes

- Memorize first: 2 anchors/slide (~22 sentences) + 2 special anchors (S9
  core idea, S11 closing). The S2 transition anchor is three short moves —
  question → each family measures itself differently → "that is the gap:
  one harness"; if you can say those three moves, the sentence rebuilds
  itself.
- Practice with the deck open: each beat = one Space — the press order IS
  the talk's table of contents.
- The old 15-minute rehearsal video (`defense-rehearsal.mp4`) no longer
  matches the deck — re-record after the first full 10-minute pass.
- Handheld cheat sheet: EXTRACT it AFTER the first full practice pass —
  only the spots you keep forgetting, never extract in advance.
