# Speaking script — thesis defense (15 minutes)

Deck: `slides/thesis-defense.html` · 12 slides · core **14:00** + ~1:30 optional beats.
This is the script to MEMORIZE via the anchor-skeleton structure. Q&A prep is a
separate session, kept in a separate file — not here.

2026-07-14 — **detail layer** (advisor feedback "slides carry too little
information"): the deck gained a spec strip (S5), secondary numbers in
badges/captions (S6, S8), and a best-per-axis line + stat line (S9). **Beat
count and Space order are UNCHANGED** — every new annotation is either
static or reveals with an existing beat. Speaking rule: the detail layer is
FOR THE COMMITTEE TO READ, not to be read aloud; only point at it when asked.
The `📎` note under each slide lists what newly appears.

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
  than 8:00 → drop every `(cuttable)` beat from there on.** No other
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

- three protocols — **PBFT** (yellow) · **Casper FFG** (purple) · **Snowman**
  (green) — these three colors persist across every slide

**TRANSITION ANCHOR:**
> "Let me begin with why this thesis exists."

`▶ → S2`

---

## S2 · Proven safe. Still halting. — enter 0:30 · speak 1:30 · leave 2:00

**OPENING ANCHOR:**
> "Layer-1 consensus protocols all come with safety proofs — proven safe.
> But here are four years of real-world operation."

- `▶` Solana — network-wide halt **17 hours, Sep 2021** — then again
  **Apr 2022 · Feb 2023 · Feb 2024**
- `▶` Ethereum — **7-block** reorg, **May 2022** · finality stall across
  multiple epochs **May 2023**
- `▶` Cosmos Hub halt **Jun 2024** · Sui validator crash-loop **Nov 2024**
- `▶` (text box) — the proofs are NOT wrong; what breaks are the proofs'
  **assumptions**: bounded delay, enough honest validators — routinely
  violated in deployment; real networks mix multiple disturbances at once →
  impossible to isolate which condition caused which incident

`▶` (big question appears) — **TRANSITION ANCHOR:**
> "So: which condition breaks which protocol? Answering that requires a
> single harness, stressing all three families in exactly the same way.
> That is what this thesis does."

`▶ → S3`

---

## S3 · Three yardsticks that can't be placed side by side — enter 2:00 · speak 0:45 · leave 2:45

**OPENING ANCHOR:**
> "No one has answered that question, because today the three families are
> measured with three different yardsticks."

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

## S4 · The goal — 5 questions — enter 2:45 · speak 0:45 · leave 3:30

**OPENING ANCHOR:**
> "The goal fits in one line: one simulator, three protocols, one shared set
> of assumptions."

- `▶` **WHEN** — when the network slows down, how much does finality slow → RQ1
- `▶` **WHAT** — what happens to throughput as the Byzantine fraction rises → RQ2
- `▶` **HOW MUCH** — how many messages does each unit of commit cost → RQ3
- `▶` **WHO** — which adversary breaks which protocol, on which property → RQ4
- `▶` **WHICH** — does any protocol win across the board → RQ5

**TRANSITION ANCHOR:**
> "Before measuring, we need to see just how differently these three
> protocols operate."

`▶ → S5`

---

## S5 · Three families, three protocols — enter 3:30 · speak 2:00 · leave 5:30

*(opens on the PBFT diagram: 4 nodes already visible)*

**OPENING ANCHOR:**
> "For each family I picked one representative. First — PBFT, the classic
> leader-driven family."

**PBFT** — n=4, node 3 offline (f=1):
- `▶` client sends a request to the **primary** → primary broadcasts
  **PRE-PREPARE**
- `▶` **PREPARE all-to-all** — every node messages every node → this is the
  source of the **O(n²)** cost
- `▶` **COMMIT all-to-all** — a second round, identical
- `▶` decided when each phase reaches quorum **2f+1** — that is **3 of 4**
  nodes with matching votes, even with 1 node dead; finality is
  **deterministic** — once committed, permanent

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
pressure point (from Table 2.1). If the committee asks "how else do they
differ," point here.*

---

## S6 · One harness — enter 5:30 · speak 1:15 · leave 6:45

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

## S7 · Three run families — enter 6:45 · speak 0:45 · leave 7:30

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

## S8 · Results — 4 tabs — enter 7:30 · speak 4:00 (+1:30 optional) · leave 11:30

**⏱ THE ONLY DECISION POINT: check the clock when entering this slide.
Later than 8:00 → drop every `(cuttable)` beat from here on.**

**OPENING ANCHOR:**
> "The results sit in four tabs, in the same order as the three run
> families."

**Tab A — Scaling (RQ3)** (open by default):
- `▶` messages per ACU at **n = 25**, log axis: Casper FFG **≈29** ·
  PBFT **≈50** · Snowman **≈601**
- `▶` measured trends match the theory — **1.15n · 2n · 2Kβ** — the
  **order-of-magnitude** gap is the price of subsampling
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
- `▶` no protocol forks — loss consumes **liveness**, not **safety**;
  (cuttable) the survivors pay **×2–3.5** latency

`▶` (switch to tab **C — Adversarial, RQ2+RQ4** — 3×3 matrix):
- `▶` **delayed voting**: PBFT immune, success **1.0** · FFG drops to
  **0.60–0.65** — the rotating proposer gets stalled · Snowman survives but
  crawls — **×62 / ×49** slower
- `▶` **silent**: PBFT clean up to **φ = 0.33**, quorum cliff at **0.40** ·
  FFG decays gradually toward **0.33** · Snowman starves first — survival
  depth **φ\* = 0.10 / 0.20**
- `▶` **equivocation** (beyond ⅓): PBFT **forks** deterministically at
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

## S9 · RQ5 — no one dominates — enter 11:30 · speak 1:00 · leave 12:30

- `▶` an **8-axis** radar from Table 5.1 — ordinal ranking, illustrative
  only; the table in the report is the evidence *(below the radar there is
  now a "best per axis" line — Table 5.1's Best column colored by protocol;
  each insight block on the right gained a stat line. Both are for the
  committee to read.)*

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

## S10 · Selection map — enter 12:30 · speak 0:40 · leave 13:10

- `▶` if the main threat requires **accountability** → **Casper FFG** —
  slashing prices a safety violation at ≥⅓ of stake
- `▶` need to **survive network disturbance** → **PBFT** — the only one with
  a recovery path
- `▶` need **equivocation resistance** → **Snowman** — no fork surface to
  attack
- `▶` (callback) each incident on the opening slide is exactly one protocol
  hitting its **structural limit**
- `▶` contributions: simulator · **3** implementations · dataset + analysis ·
  methodology — extending Gervais et al. from PoW to the BFT families

**TRANSITION ANCHOR:**
> "Within what scope do these results hold — let me state the limitations
> explicitly."

`▶ → S11`

---

## S11 · Limitations & future work — enter 13:10 · speak 0:50 · leave 14:00

- `▶` **limitations**: simplified implementations, one representative per
  family — conclusions are about THESE protocols, not abstract families ·
  **n ≤ 25**, beyond that is a sensitivity argument · Snowman safety is an
  analytical bound, no empirical witness · the adversary spares the view-0
  leader · compute/bandwidth not modeled
- `▶` **future work**: BLS/HotStuff-style threshold signatures ·
  saturation-throughput model · adaptive timeouts in the timeout-stressed
  regime · empirical witness for ε · extending the harness to the DAG
  family (Narwhal+Tusk)

`▶` — **CLOSING ANCHOR (memorize verbatim):**
> "The contribution of this thesis is a mechanism map of the
> performance–security frontier — not the naming of a single winner."

`▶ → S12`

---

## S12 · Thank you — 14:00

**ANCHOR:**
> "Thank you, committee members, for your attention. I am ready for your
> questions."

*(Q&A: use ↓/↑ to jump slides, click chips/tabs with the mouse to open
whichever diagram/result is being asked about.)*

---

## Practice notes

- Memorize first: 2 anchors/slide (~24 sentences) + 2 special anchors (S9
  core idea, S11 closing).
- Practice with the deck open: each beat = one Space — the press order IS
  the talk's table of contents.
- Handheld cheat sheet: EXTRACT it AFTER the first full practice pass —
  only the spots you keep forgetting, never extract in advance.
