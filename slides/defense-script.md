# Speaking script — thesis defense (10 minutes)

Deck: `slides/thesis-defense.html` · **11 talk slides + 3 Q&A appendix slides** ·
core **9:50** of a 10:00 slot.
This is the script to MEMORIZE via the anchor-skeleton structure. Q&A prep is a
separate session, kept in `slides/qa-prep.md` — not here.

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

## S2 · Proven safe. Still halting. — enter 0:30 · speak 1:00 · leave 1:30

**OPENING ANCHOR:**
> "Layer-1 consensus protocols all come with safety proofs. But here are
> four years of real-world operation."

- `▶` Solana — network-wide halt **17 hours, Sep 2021** — then again
  **Apr 2022 · Feb 2023 · Feb 2024**
- `▶` Ethereum — **7-block** reorg, **May 2022** · finality stall across
  multiple epochs **May 2023**
- `▶` Cosmos Hub halt **Jun 2024** · Sui crash-loop **Nov 2024** — each one
  interrupts the services built on top *(one sentence, do not linger)*
- `▶` (text box) — the proofs are NOT wrong; what breaks are their
  **assumptions** — bounded delay, enough honest validators; in real
  operation delay, loss and malicious nodes act at once, so you cannot tell
  which condition caused which failure

`▶` (big question appears) — **TRANSITION ANCHOR** *(now also carries the old
"yardsticks" slide — the sub-line on the slide backs it up)*:
> "So: which condition breaks which protocol? You cannot answer it from
> published numbers — each family grades itself on its own yardstick:
> throughput here, finality delay there, a safety probability ε at one
> parameter setting — numbers designed never to sit side by side. The one
> matched harness before this, Gervais et al., covers Proof-of-Work only.
> So I built one harness that stresses all three families in exactly the
> same way."

`▶ → S4`

---

## S4 · The goal — 5 questions — enter 1:30 · speak 0:30 · leave 2:00

**OPENING ANCHOR:**
> "The goal fits in one line: one simulator, three protocols, one shared set
> of assumptions. Five questions."

*(one sentence per press — no elaboration; the slide text matches report §1.3)*

- `▶` **WHEN** — the network slows: how much does finality slow → RQ1
- `▶` **WHAT** — throughput as the Byzantine fraction rises → RQ2
- `▶` **HOW MUCH** — messages paid per committed unit → RQ3
- `▶` **WHO** — which adversary breaks which protocol — and does it break
  speed, or safety → RQ4
- `▶` **WHICH** — after all of that, does any protocol win overall → RQ5

**TRANSITION ANCHOR:**
> "Before measuring, we need to see just how differently these three
> protocols operate."

`▶ → S5`

---

## S5 · Three families, three protocols — enter 2:00 · speak 1:20 · leave 3:20

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
> layer since the Merge."
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
  **2n** × n validators = the **O(n²)** from the diagram slide; the
  **order-of-magnitude** gap is the price of subsampling *(this press also
  reveals the latency/goodput stat box — reading layer, do NOT speak it)*

`▶` (switch to tab **B — Delay, RQ1**, 2 presses):
- `▶` slowdown vs. zero-delay baseline: FFG **×1.3** · PBFT **×1.9** —
  round-bounded, insensitive to tail shape
- `▶` Snowman **×12–15** — each round waits for the SLOWEST peer in the
  K-peer sample *(this press also reveals the tail numbers + the
  "delay costs time, not messages" badge — reading layer, do NOT speak)*

`▶` (switch to tab **B — Loss**, 3 presses):
- `▶` three finalization-rate curves across loss **0 → 20%**
- `▶` ranking **PBFT > Snowman > FFG** — PBFT alone still finalizes at
  **20%** thanks to its recovery path (**view-change** rotates the leader);
  Snowman plateaus-then-cliffs at **10%**; FFG collapses at the first
  **5%** step — it has neither *(n=25 AURC-tie note on slide: read only if
  asked about stability in n)*
- `▶` no protocol **forks** — the chain never splits; loss consumes
  **liveness** — progress stops — not **safety** — nothing committed is
  ever contradicted

`▶` (switch to tab **C — Adversarial, RQ2+RQ4** — 3×3 matrix, 4 presses):
- `▶` **delayed voting**: PBFT immune, success **1.0** · FFG drops to
  **0.60–0.65** — the rotating proposer gets stalled · Snowman survives but
  crawls — **×62 / ×49** slower
- `▶` **silent**: PBFT clean up to **φ = 0.33**, quorum cliff at **0.40** ·
  FFG decays toward **0.33** · Snowman starves first — **φ\* = 0.10 / 0.20**
- `▶` **equivocation** — conflicting votes for two blocks at once — beyond
  ⅓: PBFT **forks** at **0.40**, NOT attributable · FFG does not fork —
  **≥⅓ of stake slashable**, accountable · Snowman: no fork surface —
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

- `▶` **limitations**, one breath: simplified implementations, one
  representative per family — conclusions are about THESE protocols ·
  **n ≤ 25** · Snowman safety is an analytical bound, no empirical witness ·
  loss is a PERMANENT drop — no retransmission, so the loss curves are
  upper bounds on fragility *(keep this clause — it shields the
  FFG-collapses-at-5% headline)* · compute/bandwidth not modeled
- `▶` (cuttable) **future work**, one sentence: threshold signatures ·
  saturation throughput · adaptive timeouts · empirical ε · the DAG family

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
- All three autoplay their full reveal on entry — no stepping needed.
- Plus, on S5: the mouse-only **Recovery ▸ Q&A** chip (dashed border).
- Plus, on S8: the mouse-only **Sweep ▸ Q&A** chip — the full n = 4 → 25
  sweep behind Tab A's endpoint bars (see the 📎 note under S8).
- Corner badge shows `Q&A appendix` instead of a slide number, so the
  committee sees these are backup, not skipped content.

---

## Practice notes

- Memorize first: 2 anchors/slide (~22 sentences) + 2 special anchors (S9
  core idea, S11 closing). The S2 transition anchor is the longest — it now
  carries the whole "gap" argument; drill it until it is one breath.
- Practice with the deck open: each beat = one Space — the press order IS
  the talk's table of contents.
- The old 15-minute rehearsal video (`defense-rehearsal.mp4`) no longer
  matches the deck — re-record after the first full 10-minute pass.
- Handheld cheat sheet: EXTRACT it AFTER the first full practice pass —
  only the spots you keep forgetting, never extract in advance.
