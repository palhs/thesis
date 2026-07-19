# Speaking script — thesis defense (15 minutes)

Deck: `slides/thesis-defense.html` · 13 slides · core **15:10** + ~1:30 optional beats.
This is the script to MEMORIZE via the anchor-skeleton structure. Q&A prep is a
separate session, kept in `slides/qa-prep.md` — not here.

2026-07-14 — **new slide S2B "The three contenders"** (position 03/13): intro
cards for PBFT · Casper FFG · Snowman — year, authors, one-line mechanism,
where each runs in production — plus the colour-legend line. **4 new beats**;
every timing below it shifted **+0:45**, and the S8 cut-rule threshold moved
**8:00 → 8:45**. Core is now 14:45 of a 15:00 slot — the next rehearsal pass
should reclaim ~45 s (candidates: S5 per-protocol intros now that S2B carries
the introductions, and the S8 cuttable beats).

2026-07-14 (later) — **S5 PBFT pane now shows view-change** (the committee
will probe recovery; S8's loss ranking leans on it). Beat count unchanged
(still 4): PREPARE and COMMIT merged into one beat ("two identical all-to-all
rounds"), freeing the last beat for a view-change vignette — the happy path
**fades out entirely** (scene swap, not a dim), the primary goes silent,
timeouts fire, VIEW-CHANGE (all-to-all) elects N1, the block replays. The
spec strip gained a **recovery** field on all three panes. S5 stays 2:00 —
no downstream retiming.

2026-07-14 — **detail layer** (advisor feedback "slides carry too little
information"): the deck gained a spec strip (S5), secondary numbers in
badges/captions (S6, S8), and a best-per-axis line + stat line (S9). **Beat
count and Space order are UNCHANGED** — every new annotation is either
static or reveals with an existing beat. Speaking rule: the detail layer is
FOR THE COMMITTEE TO READ, not to be read aloud; only point at it when asked.
The `📎` note under each slide lists what newly appears.

2026-07-16 — **S10 callback reworded** (deck + this script). The old line —
"each opening incident is a protocol at its structural limit" — over-claimed:
Solana (Tower BFT) and Sui (Narwhal/Bullshark) are not among the three tested
families. New line credits Ethereum + Cosmos as in-scope and frames Solana +
Sui as same-phenomenon motivation beyond the harness. Spoken defense for the
scope question added as `qa-prep.md` **Q2**. Beat count and timing unchanged.

2026-07-16 (later) — **S2 beats reworded** to the rehearsed spoken flow: the
Cosmos/Sui beat now closes with the service-interruption consequence, and the
text-box beat runs proofs-not-wrong → assumptions → many disturbances at once
(delay · loss · malicious nodes) → can't attribute. The opening anchor also
dropped the "— proven safe" echo (the slide title already carries it); beat
count, Space order, and timing unchanged.

2026-07-16 (later) — **S8 gained three spoken glosses** (terms that first
appear at S8 and carry the main argument): per-validator counts on Tab A
(reconciles 2n with S5's O(n²) — verified against ch3 §"total_msgs_per_acu"),
fork + liveness/safety on Tab B-Loss, equivocation on Tab C. Detail-layer
terms (goodput, φ*, success rate, AURC) are deliberately NOT glossed in the
talk — they are Q&A material, listed in `qa-prep.md` **Q4**. Beat count,
Space order, and timing unchanged (glosses are half-sentence).

2026-07-16 (later) — **S4 beats RQ3–RQ5 reworded plain-first**: those beats
now give the plain-language meaning first and land on the slide's term
(committed unit, adversary), since ACU is only defined at S6. RQ1/RQ2 keep
their original compact phrasing (finality and throughput are already glossed
by S2/S3). Slide text unchanged — it matches report §1.3. Beat count, Space
order, and timing unchanged.

2026-07-18 — **S9 †-caveat now SPOKEN + S11 sixth limitation** (deck-vs-report
alignment pass). S9: the two non-measured axes (accountable · equivocation)
carry a **†** on the radar and a third note line under it; the caveat is
spoken in full (+0:20) — report §5.3 states it prominently, so the committee
hears it from us before they can ask. S11: the permanent-loss limitation from
ch6 §6.2 restored as a sixth bullet and one spoken clause (+0:05) — it is the
shield for the FFG-collapses-at-5%-loss headline. No new beats or Space
presses; S9→S12 timings shifted **+0:25**, core now **15:10** of a 15:00
slot — the pending reclaim (2026-07-14 entry: S5 intros, S8 cuttable beats)
grows to ~70 s.

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
  talk uses a single key.** The mouse is only needed in Q&A to jump freely
  between chips/tabs.
  - Space / → / PageDown = next step · Shift+Space / ← / PageUp = step back
  - ↓ / ↑ = jump whole slides (use in Q&A)
- `(cuttable)` = optional beat. **The single cut rule: if you enter S8 later
  than 8:45 → drop every `(cuttable)` beat from there on.** No other
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
  (ice) — name them only; S2B introduces them properly

**TRANSITION ANCHOR:**
> "Let me begin with why this thesis exists."

`▶ → S2`

---

## S2 · Proven safe. Still halting. — enter 0:30 · speak 1:30 · leave 2:00

**OPENING ANCHOR:**
> "Layer-1 consensus protocols all come with safety proofs. But here are
> four years of real-world operation."

- `▶` Solana — network-wide halt **17 hours, Sep 2021** — then again
  **Apr 2022 · Feb 2023 · Feb 2024**
- `▶` Ethereum — **7-block** reorg, **May 2022** · finality stall across
  multiple epochs **May 2023**
- `▶` Cosmos Hub halt **Jun 2024** · Sui validator crash-loop **Nov 2024** —
  each incident interrupts the services built on top
- `▶` (text box) — the proofs are NOT wrong; what breaks are their
  **assumptions** — bounded delay, enough honest validators; in real
  operation many disturbances act at once — network delay, message loss,
  malicious nodes — so it's very hard to tell which condition caused which
  failure

`▶` (big question appears) — **TRANSITION ANCHOR:**
> "So: which condition breaks which protocol? Answering that requires a
> single harness, stressing all three families in exactly the same way.
> That is what this thesis does."

`▶ → S2B`

---

## S2B · The three contenders — enter 2:00 · speak 0:45 · leave 2:45

**OPENING ANCHOR:**
> "The three protocols under test — one representative per family, from
> three different eras, all running real networks today."

- `▶` **PBFT — 1999**, Castro & Liskov (MIT) — the first practical Byzantine
  fault-tolerant protocol; its descendants run **Cosmos** (Tendermint) and
  **Diem → Aptos** (HotStuff)
- `▶` **Casper FFG — 2017**, Buterin & Griffith — a finality gadget laid over
  a running chain; the finality layer inside Gasper, securing **Ethereum**
  mainnet since the Merge, **09/2022**
- `▶` **Snowman — 2019**, "Team Rocket" / Ava Labs — consensus by repeated
  random polls; the production engine of **Avalanche** — C-Chain & P-Chain —
  since **2020**
- `▶` (legend line appears — point at the dots) one colour per protocol —
  **amber · violet · ice** — they tag every chart to the end of the talk

**TRANSITION ANCHOR:**
> "Three live networks — so can't we just read their published numbers side
> by side? Let's try."

`▶ → S3`

---

## S3 · Three yardsticks that can't be placed side by side — enter 2:45 · speak 0:45 · leave 3:30

**OPENING ANCHOR:**
> "Today the three families are measured with three different yardsticks."

- `▶` PBFT-style reports **throughput** — ops/s on low-latency LANs — says
  nothing about finality delay
- `▶` PoS finality reports **finality delay** — **~12 minutes, 2 epochs** —
  says nothing about throughput
- `▶` Avalanche-style reports a **safety-failure probability ε** — at ONE
  fixed (K, β) setting — change the parameters and the number changes
- `▶` (punchline) — plenty of numbers, but designed to never be comparable;
  surveys only place other people's numbers side by side; the only prior
  matched harness — **Gervais et al.** — covers Proof-of-Work only

**TRANSITION ANCHOR:**
> "No unified picture exists — so I built one."

`▶ → S4`

---

## S4 · The goal — 5 questions — enter 3:30 · speak 0:45 · leave 4:15

**OPENING ANCHOR:**
> "The goal fits in one line: one simulator, three protocols, one shared set
> of assumptions."

*(spoken rule for this slide: plain words first, then land on the slide's
term — the audience hears the meaning and sees the word)*

- `▶` **WHEN** — when the network slows down, how much does finality slow → RQ1
- `▶` **WHAT** — what happens to throughput as the Byzantine fraction rises → RQ2
- `▶` **HOW MUCH** — for every block the network commits, how many messages
  did it have to send — the cost per **committed unit** (defined precisely
  on the harness slide) → RQ3
- `▶` **WHO** — which kind of attacker — **adversary** — breaks which
  protocol, and what does it break: speed, or safety → RQ4
- `▶` **WHICH** — after all of that, does any protocol **win overall** → RQ5

**TRANSITION ANCHOR:**
> "Before measuring, we need to see just how differently these three
> protocols operate."

`▶ → S5`

---

## S5 · Three families, three protocols — enter 4:15 · speak 2:00 · leave 6:15

*(opens on the PBFT diagram: 4 nodes already visible)*

**OPENING ANCHOR:**
> "For each family I picked one representative. First — PBFT, the classic
> leader-driven family."

**PBFT** — n=4, node 3 offline (f=1):
- `▶` client sends a request to the **primary** → primary broadcasts
  **PRE-PREPARE**
- `▶` **PREPARE**, then **COMMIT** — two identical **all-to-all** rounds,
  every node messages every node → this is the source of the **O(n²)** cost
- `▶` decided when each phase reaches quorum **2f+1** — that is **3 of 4**
  nodes with matching votes, even with 1 node dead; finality is
  **deterministic** — once committed, permanent
- `▶` (scene swaps — the happy path fades out, the fault scene plays) the
  OTHER fault — the **primary** goes silent: replicas **time out** →
  **VIEW-CHANGE**, itself an all-to-all round, elects a new primary → the
  block replays and finishes. **This is PBFT's recovery path — hold onto it
  for the loss results**

`▶` (deck auto-switches to the **Casper FFG** chip):
> "Second — Casper FFG, Ethereum's finality layer."
- `▶` validators (weighted by **stake**) send attestations that accumulate on
  the link between two checkpoints; once **⅔ of stake**...
- `▶` ...the checkpoint is **justified**
- `▶` a justified child ⇒ the parent is **finalized** — a two-step commit
- `▶` the newest checkpoint is always pending — finality trails **behind**
  the chain tip; cost is only **~1.15n** messages; **slashing** → safety
  violations become attributable

`▶` (deck auto-switches to the **Snowman** chip):
> "Third — Snowman from Avalanche. There is no leader at all."
- `▶` each round: poll **K random peers**; if ≥ **α_c** reply identically →
  confidence counter **1/15**
- `▶` next round — an entirely FRESH sample → **2/15**
- `▶` switching preference midway → counter **resets to 0** — this is where
  the price is paid
- `▶` after **β = 15** consecutive rounds → **ACCEPTED**; finality is
  **probabilistic**: ε ≤ (1−α_c/K)^β; per-validator cost is **independent
  of n**

**TRANSITION ANCHOR:**
> "Three mechanisms so different that their native metrics cannot be
> compared. For a fair comparison, everything around the protocol must be
> identical — that is the harness's job."

`▶ → S6`

📎 *New on the slide (pre-rendered per pane, no need to read aloud): a spec
strip under the caption — synchrony · proposer · quorum · finality ·
pressure point (from Table 2.1) · **recovery** (view-change / none — waits an
epoch / re-poll only, no fallback). If the committee asks "how else do they
differ" or presses on recovery, point here. For the recovery question
specifically there is a 4th, MOUSE-ONLY chip — **Recovery ▸ Q&A** (dashed
border) — with a three-panel comparison; Space never enters it, so it is
invisible to the 15-minute talk. Spoken answer: `qa-prep.md` Q1.*

---

## S6 · One harness — enter 6:15 · speak 1:15 · leave 7:30

*(opens with the config box already visible)*

**OPENING ANCHOR:**
> "Every experiment runs through exactly one pipeline."

- (already visible) the config has 5 parts: protocol · n · timeline ·
  adversary · seed
- `▶` **fixed** infrastructure: a virtual-time scheduler — deterministic ·
  configurable network delay/loss · logger
- `▶` exactly ONE swappable spot: the **protocol slot**
- `▶` each run → **one result row**, with **commit_hash + seed** → every row
  is reproducible
- `▶` repeated **×20 seeds** per cell, for every run family *(slide also
  notes: 30 seeds at near-threshold points — no need to read aloud)*
- `▶` identical infrastructure ⇒ output differences are **attributable to
  the protocol**
- `▶` the common denominator — **ACU, atomic commit unit**: 1 PBFT block ≡
  1 finalized FFG checkpoint ≡ 1 accepted Snowman block — every cost, every
  latency is measured in this unit

📎 *New on the slide: the ACU caption gained an aggregation sentence — 95%
Student-t (continuous metrics) · 95% Wilson (proportion metrics). Point at
it only if asked about statistical confidence.*

**TRANSITION ANCHOR:**
> "On that harness, I designed three experiment families — each sweeping
> exactly one axis."

`▶ → S7`

---

## S7 · Three run families — enter 7:30 · speak 0:45 · leave 8:15

**OPENING ANCHOR:**
> "Three run families — each sweeps one axis while the other axes stay
> pinned."

**A — Scaling** (open by default):
- `▶` sweeps **n = 4 → 25**
- `▶` pinned: clean network, all honest
- `▶` → answers **RQ3**

`▶` (switch to chip **B — Delay**):
- `▶` sweeps timelines: baseline → uniform **100–500 ms** → heavy-tail
  **1–5 s**, plus loss **5/10/20%**
- `▶` pinned: n ∈ {10, 25}, all honest
- `▶` → **RQ1**

`▶` (switch to chip **C — Adversarial**):
- `▶` sweeps the adversary fraction **φ = 0 → 0.30** (equivocation adds
  **0.40/0.50**)
- `▶` three behaviors: delayed-voting · silent · equivocation
- `▶` → **RQ2 · RQ4**
- (footer, read quickly) shared across all cells: Poisson **100 tx/s** · tx
  **512 bytes** · **20 seeds**/cell (**30** at family C's near-threshold
  points) · common random numbers → paired comparisons

**TRANSITION ANCHOR:**
> "That is how we measure. Now the main part — the results."

`▶ → S8`

---

## S8 · Results — 4 tabs — enter 8:15 · speak 4:00 (+1:30 optional) · leave 12:15

**⏱ THE ONLY DECISION POINT: check the clock when entering this slide.
Later than 8:45 → drop every `(cuttable)` beat from here on.**

**OPENING ANCHOR:**
> "The results sit in four tabs, in the same order as the three run
> families."

**Tab A — Scaling (RQ3)** (open by default):
- `▶` messages per ACU at **n = 25**, log axis: Casper FFG **≈29** ·
  PBFT **≈50** · Snowman **≈601**
- `▶` measured trends match the theory — **1.15n · 2n · 2Kβ** — these are
  **per-validator** counts: PBFT's **2n**, times n validators, is exactly
  the **O(n²)** total from the diagram slide; the **order-of-magnitude**
  gap is the price of subsampling
- `▶` (cuttable) latency is flat in n — PBFT & Snowman **≈1 s**, FFG
  **≈5 s** due to epoch-granularity finality; goodput **≈95 · 95 · 80 tx/s**
  out of 100 offered *(this beat now also reveals the stat box on the
  right — skimming it is enough)*

`▶` (switch to tab **B — Delay, RQ1**):
- `▶` slowdown vs. the zero-delay baseline: FFG **×1.3** · PBFT **×1.9** —
  round-bounded, insensitive to tail shape
- `▶` Snowman **×12–15** — each round waits for the SLOWEST peer in the
  K-peer sample
- `▶` (cuttable) the tail hits every round: exponential-tail **15.3 s** vs
  uniform **12.6 s** at n=10 *(this beat now also reveals a badge: delay
  slows down TIME, it does not cost extra messages — PBFT ±0.1% · SNW +2% ·
  FFG −12%)*

`▶` (switch to tab **B — Loss**):
- `▶` three finalization-rate curves across loss **0 → 20%**
- `▶` ranking **PBFT > Snowman > FFG** — PBFT is the only one still
  finalizing at **20%** thanks to a recovery path (**view-change** rotates
  the leader); Snowman plateaus-then-cliffs at **10%** (in-round redundancy,
  no cross-round recovery); FFG collapses at the first **5%** step (has
  neither) *(slide also notes: at n=25 PBFT ≈ Snowman — AURC tie 0.351 vs
  0.369; if the committee asks whether the ranking is stable in n, point at
  this line)*
- `▶` no protocol **forks** — the chain never splits into two conflicting
  histories; loss consumes **liveness** — the chain stops making progress —
  not **safety** — nothing already committed is ever contradicted;
  (cuttable) the survivors pay **×2–3.5** latency

`▶` (switch to tab **C — Adversarial, RQ2+RQ4** — 3×3 matrix):
- `▶` **delayed voting**: PBFT immune, success **1.0** · FFG drops to
  **0.60–0.65** — the rotating proposer gets stalled · Snowman survives but
  crawls — **×62 / ×49** slower
- `▶` **silent**: PBFT clean up to **φ = 0.33**, quorum cliff at **0.40** ·
  FFG decays gradually toward **0.33** · Snowman starves first — survival
  depth **φ\* = 0.10 / 0.20**
- `▶` **equivocation** — a node sends conflicting votes for two blocks at
  once — (beyond ⅓): PBFT **forks** deterministically at
  **0.40** — NOT attributable · FFG does not fork — **≥⅓ of stake is
  slashable**, accountable · Snowman has no fork surface — bound
  **ε ≈ 5×10⁻¹⁵ / 3×10⁻¹¹**
- `▶` (legend appears — point at the colors) green holds · yellow degrades ·
  red breaks

**TRANSITION ANCHOR:**
> "Four tabs — no protocol wins all four. That is precisely the answer to
> RQ5."

`▶ → S9`

---

## S9 · RQ5 — no one dominates — enter 12:15 · speak 1:20 · leave 13:35

- `▶` an **8-axis** radar from Table 5.1 — ordinal ranking, illustrative
  only; the table in the report is the evidence *(below the radar there is
  now a "best per axis" line — Table 5.1's Best column colored by protocol —
  plus a **† note** on the two non-measured axes; each insight block on the
  right gained a stat line. The first and last are for the committee to
  read; the † caveat is SPOKEN, next.)*

*(same beat — no new press)* **the † caveat, spoken (~0:20, point at the
† note under the radar):**
> "One caveat before the verdict: two of these eight axes are not measured
> contests. Accountable safety — Casper FFG holds it **by definition**: only
> a slashing protocol can attribute a failure. Equivocation safety — Snowman
> ranks first on an **analytical bound**, a number of order ten-to-the-minus-
> fifteen my simulator can never witness. Strip those two, and PBFT and
> Casper FFG each still hold two measured corners — **Snowman holds none**;
> its place on the frontier rests entirely on that unwitnessed ε. So
> no-dominance is the honest verdict — but it is not a symmetric one."

`▶` — **CORE-IDEA ANCHOR (memorize verbatim):**
> "The central finding: the SAME design choice produces both each
> protocol's strength and its weakness."

- `▶` **Snowman** — K-peer subsampling: thrives when peers are SLOW, but
  starves when peers are SILENT — the sample can't find anyone to ask
- `▶` **PBFT** — leader-quorum commit: rides out delay, loss, silence — but
  past the equivocation threshold it forks with no attribution
- `▶` **Casper FFG** — epoch-paced finality: cheapest, least
  delay-sensitive — but first to collapse under loss; in exchange, the ONLY
  one with accountable safety

**TRANSITION ANCHOR:**
> "No winner — so how do you use these results? As a selection map."

`▶ → S10`

---

## S10 · Selection map — enter 13:35 · speak 0:40 · leave 14:15

- `▶` if the main threat requires **accountability** → **Casper FFG** —
  slashing prices a safety violation at ≥⅓ of stake
- `▶` need to **survive network disturbance** → **PBFT** — the only one with
  a recovery path
- `▶` need **equivocation resistance** → **Snowman** — no fork surface to
  attack
- `▶` (callback) the opening incidents, revisited — **Ethereum** and
  **Cosmos** run the two families whose **structural limits** the results
  just mapped; **Solana** and **Sui** show the same failure class in
  families **outside the harness** — motivation, not scope (if pressed:
  `qa-prep.md` Q2)
- `▶` contributions: simulator · **3** implementations · dataset + analysis ·
  methodology — extending Gervais et al. from PoW to the BFT families

**TRANSITION ANCHOR:**
> "Within what scope do these results hold — let me state the limitations
> explicitly."

`▶ → S11`

---

## S11 · Limitations & future work — enter 14:15 · speak 0:55 · leave 15:10

- `▶` **limitations**: simplified implementations, one representative per
  family — conclusions are about THESE protocols, not abstract families ·
  **n ≤ 25**, beyond that is a sensitivity argument · Snowman safety is an
  analytical bound, no empirical witness · loss is a PERMANENT drop — no
  retransmission, so the loss curves are upper bounds on fragility · the
  adversary spares the view-0 leader · compute/bandwidth not modeled
- `▶` **future work**: BLS/HotStuff-style threshold signatures ·
  saturation-throughput model · adaptive timeouts in the timeout-stressed
  regime · empirical witness for ε · extending the harness to the DAG
  family (Narwhal+Tusk)

`▶` — **CLOSING ANCHOR (memorize verbatim):**
> "The contribution of this thesis is a mechanism map of the
> performance–security frontier — not the naming of a single winner."

`▶ → S12`

---

## S12 · Thank you — 15:10

**ANCHOR:**
> "Thank you, committee members, for your attention. I am ready for your
> questions."

*(Q&A: use ↓/↑ to jump slides, click chips/tabs with the mouse to open
whichever diagram/result is being asked about.)*

---

## Practice notes

- Memorize first: 2 anchors/slide (~26 sentences) + 2 special anchors (S9
  core idea, S11 closing).
- Practice with the deck open: each beat = one Space — the press order IS
  the talk's table of contents.
- Handheld cheat sheet: EXTRACT it AFTER the first full practice pass —
  only the spots you keep forgetting, never extract in advance.
