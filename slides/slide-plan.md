# Slide plan — 15-minute thesis defense deck

Status: BUILT (2026-07-08). Style chosen from 3 previews: custom wildcard
**"Consensus Lab"** — dark lab canvas (#0C1118), Fraunces (display serif) +
Azeret Mono (chrome), protocol hues `--c-pbft:#E8A33D` (amber) ·
`--c-ffg:#9D8CFF` (violet) · `--c-snowman:#5FD4E8` (ice cyan).
Deck: `slides/thesis-defense.html` (single self-contained file, 13 slides =
the 12 below + S12 "Thank you for listening", arrow-key nav, all interactions
per the inventory below; inline edit via E, Ctrl/Cmd+S exports). All slides +
all chip/tab states visually QA'd at 1920×1080. Fonts (Fraunces + Azeret Mono)
are inlined as base64 woff2 — the deck is fully offline; no network needed at
the defense. Remaining: author rehearsal pass + wording tweaks.

2026-07-09: speaking script added at `slides/defense-script.md` (Vietnamese,
anchor-and-beats structure, 14-min core + cut-safe beats). The deck now runs
in **presenter step mode**: one Space = one script beat (see updated
interaction inventory below); beats in the script match presses 1:1.

2026-07-14: **detail layer pass** (supervisor feedback: slides too sparse).
Structure unchanged (still 12 slides; the 16–18-slide unfold of S5/S8 panes
is deferred until after a rehearsal pass). Added, all sourced from drafts/:
S5 spec strips per protocol (Table 2.1 fields: synchrony · proposer · quorum
· finality · pressure point); S6 seed note (30 near-threshold) + CI sentence
(95% Student-t / Wilson, ch3 §3.5); S8 tab A stat box (latency ≈1 s/≈5 s,
goodput 95·95·80 tx/s, ch4 §4.2) · tab B-delay timeline subtitle + msg-cost
badge (±0.1% / +2% / −12%, ch4 §4.3.1) · tab B-loss n=25 AURC-tie note
(0.351 vs 0.369, ch5 Table 5.1) + FFG +3–10% detail · tab C legend params;
S9 best-per-axis line (Table 5.1 Best column) + stat line per insight mini.
**STEPS map and script beat counts unchanged** — new elements are static or
reuse existing data-t thresholds. Script updated with 📎 notes only. QA'd
at 1920×1080 via Playwright: all panes/tabs full-reveal + 85-press Space
walkthrough, no JS errors.

2026-07-14 (later): **new slide S2B "The three contenders"** (author request:
introduce the three protocols before their legend colours carry meaning).
Inserted between S2 and S3 as position 03/13, id `s2b`. Three cards, one per
protocol — year (big numeral), authors, one-line mechanism, "in the wild"
deployments — plus a closing colour-legend line. Facts cross-checked against
wiki (`algorithms/pbft`, `pos`, `avalanche`); source footer `report §2.2`.
Deck changes: `#s2b` CSS block, section HTML, all `NN / 12` counters
renumbered to `/ 13`, STEPS entry `s2b: [350, 650, 950, 1500, ∞]` (4 beats:
card ×3 + legend). Script: new S2B section, all later timings +0:45, cut
rule 8:00 → 8:45, core now 14:45 — rehearsal should reclaim ~45 s.
Step-mode QA'd in browser (entry + 4 presses + advance); layout verified
within the 1080px canvas.

2026-07-14 (later still): **S5 PBFT pane gained a view-change vignette**
(author: committee will probe recovery — S8's loss ranking and S10's
"only one with a recovery path" leaned on a mechanism never shown). Beat 4
is a **scene swap**: the whole happy path is wrapped in one group and the
view-change vignette in a second, both sharing `data-x="pbx"` — turning the
vignette on fades the happy path out entirely. (First attempt used a
semi-transparent veil rect; rejected — ghosted text interleaved with the
vignette labels.) The vignette: N3 back online (so {N1,N2,N3} honestly
reaches 2f+1 = 3), N0 goes silent (red ✕ on the lane, clear of the label),
timeout Δ column, VIEW-CHANGE all-to-all, NEW-VIEW (N1 = primary), phases
replay, "liveness restored" badge. Two-line column-spaced top labels.
QA'd 2026-07-15 via headless-Edge Playwright screenshots (see resume note 0):
beat 3 confirms the wrapped happy path is intact, beat 4 confirms a
ghost-free vignette (text bounding boxes measured, 0 overlaps), and
stepBack restores scene 1 (happy on, vignette off).

2026-07-15: **S5 gained a 4th, mouse-only chip — "Recovery ▸ Q&A"** (dashed
border), a Q&A backup pane for the anticipated committee question "PBFT has
view-change — what do the other two do?" (`slides/qa-prep.md` Q1). Three
panels: PBFT rotate-the-role (✕ on N0 → arc to N1), Casper FFG
bleed-the-absentees (stake bars draining at −D·p/epoch until voters ≥ ⅔ —
inactivity leak, FFG §4.2 "Catastrophic Crashes", flagged in red as an
extension NOT in the simulated core and as trading accountable safety away,
paper Fig. 6), Snowman resample-and-wait (failed α_c polls just repeat; the
same loop succeeds when the network heals). Unifying line ties to S9. The
chip is deliberately absent from `PANES.s5.order`, so Space never enters
the pane — it opens only by mouse click during Q&A; `dia-recovery` has no
STEPS entry, so it autoplays its cascade on click. Facts verified against
`raw/casper.pdf` (see TASKS.md Backlog: wiki ingest still pending).
Beat count preserved by merging the PREPARE and COMMIT beats (they were
"a second round, identical") — `STEPS['dia-pbft']` is now
`[400, 1400, 3200, 3600, ∞]`; S5 duration unchanged, no script retiming.
All three spec strips gained a terse **recovery** field (view-change /
none — waits an epoch / re-poll only, no fallback) — kept short so the
strip stays inside the 1920 stage (QA'd: right edges 1356/1536/1618).
Step-back from the vignette cleanly restores the decided state.

## How to resume in a new session

0. **Preview / QA tooling is per-machine:**
   - macOS (2026-07-14): the in-app preview helper cannot read under
     `~/Desktop` (permission), so `.claude/launch.json` serves a COPY of
     the deck from `~/.cache/thesis-slide-previews/` on port 4173. After
     editing `slides/thesis-defense.html`, re-sync before previewing:
     `cp slides/thesis-defense.html ~/.cache/thesis-slide-previews/`.
     (Playwright/one-off QA can instead serve `slides/` directly from a
     normal shell, which does have Desktop access.)
   - Windows (2026-07-15): serve the deck with `python -m http.server 8641`
     from `slides/` and open `http://localhost:8641/thesis-defense.html`.
     The in-app browser pane can VIEW and script the deck but its
     screenshot capture times out (the inlined woff2 fonts stall the
     compositor) — for visual QA use Python Playwright driving installed
     Edge, no browser download needed:
     `p.chromium.launch(channel="msedge", headless=True)`, `deck.show(i)`
     + `stepForward(root)` via `page.evaluate`, then `page.screenshot`.

1. Invoke `Skill: frontend-slides` (this deck is built with it; fixed 1920×1080
   stage, single self-contained HTML, arrow-key navigation).
2. Read this file for the full outline, content, and interaction specs.
3. **Diagram craft rule (effective-html):** slides 5, 6, 7 (and the tabbed
   results slide 8) contain SVG diagrams. Before building them, read the
   `html-diagram` skill (`~/.claude/skills/html-diagram/SKILL.md`) — this is
   what the author calls "/effective-html" — and review its
   `references/html-effectiveness/` examples plus
   `references/architecture-example.html`. Borrow from it: high-quality
   full-bleed SVG, clickable nodes, flow chips/buttons that light up and
   animate message paths, iterate on the diagram more than anything.
   **Adapt, don't copy wholesale:** the deck already has one theme and a fixed
   stage, so SKIP html-diagram's dark-mode toggle, localStorage, and pan/zoom.
   Style SVG via CSS variables of the chosen deck theme. Switch buttons on
   slides must be mouse-clickable chips; keys are owned by the presenter step
   mode (see interaction inventory) — never bind extra keys on a slide.
4. Content discipline: every displayed number/claim comes from `drafts/`
   (sources cited per slide below). Do not invent numbers. Wiki is background
   only, never displayed.

## Locked decisions

- 15 minutes, thesis defense, committee audience.
- **Low density / speaker-led** — one idea per slide, large type; author speaks
  Vietnamese, slide text in **English** (matches the submitted report).
- Charts are **redrawn in HTML/SVG from numbers stated in drafts/** (no PDF
  embeds, no invented data).
- 12 slides, 4 acts.

## Unified diagram design system (applies to S5, S6, S7, S8, S9)

Author requirement: ALL diagrams and result charts share one visual system —
the S8 result charts must look like siblings of the S5–S7 flow diagrams, not
like a charting library pasted in. Build one shared SVG component vocabulary
and reuse it everywhere:

- **One rendering medium.** Everything is hand-built SVG inside the slide
  stage (no <canvas>, no chart library, no HTML-div bar charts). Result charts
  in S8 are drawn with the same stroke weights, corner radii, node/box style,
  and label typography as the S5–S7 diagrams.
- **Fixed protocol color mapping,** declared once as CSS variables and used in
  every diagram, chart, tab, legend, and the S9 radar:
  `--c-pbft`, `--c-ffg`, `--c-snowman` (actual hues come from the chosen deck
  theme in Phase 2; they stay identical across all slides). Neutral/infra
  elements (harness box, axes, gridlines) use the theme's muted ink color.
- **One chip component.** The switch chips on S5 (protocols), S7 (run
  families), and the tabs on S8 (results) are the same visual component —
  same shape, hover, and active state. Active protocol chips are filled with
  that protocol's color.
- **One animation grammar** (from the html-diagram / effective-html
  conventions): elements draw in with stroke-dashoffset or fade+translate;
  active flows highlight by brightening the path while others dim; switching
  a chip/tab replays the entrance animation. Same durations/easing everywhere.
  In S8, bars grow from the axis and lines draw left-to-right using the same
  timing tokens as the S5 message animations.
- **One label/caption style.** Axis labels, node labels, and chart annotations
  share one font size scale and one callout style (e.g., the "×12–15" badge in
  S8 uses the same badge component as the "2f+1" badge in S5).
- Charts remain honest: axis values only from drafts/ numbers; log axes
  labelled as such.

## Deck outline (12 slides)

### Act 1 — Premise & purpose (~4.75 min)

**S1 · Title** (30s)
Thesis title, author, supervisor, date.

**S2 · Hook: "Proven safe. Still halting."** (1.5 min) — drafts/ch1 §1.2
- Incident timeline (visual, minimal text): Solana 17-hour halt 09/2021 (+
  04/2022, 02/2023, 02/2024) · Ethereum 7-block reorg 05/2022 + multi-epoch
  finality stall 05/2023 · Cosmos Hub halt 06/2024 · Sui crash-loop 11/2024.
- Framing (per author): incidents are the hook, NOT the thesis problem. The
  proofs hold; the *conditions* of the proofs (bounded delay, enough honest
  validators) are routinely exited in deployment, and live networks combine
  disturbances so you cannot isolate which condition triggers which failure.
- Slide ends on the open question that drives the deck: **"Which condition
  breaks which protocol? Answering needs one harness that stresses all three
  families the same way."** → transitions to S2B.

**S2B · The three contenders** (45s) — ch2 §2.2; facts cross-checked against
wiki `algorithms/pbft` · `pos` · `avalanche`
- Three cards, one per protocol, border + big year numeral in the protocol's
  legend colour. Each card: year · authors · family tag · one-line mechanism ·
  "in the wild" deployments:
  - **PBFT — 1999**, Castro & Liskov (MIT, OSDI '99), quorum-BFT family;
    descendants run Cosmos (Tendermint) and Diem → Aptos (HotStuff).
  - **Casper FFG — 2017**, Buterin & Griffith, PoS-finality family; finality
    layer inside Gasper, on Ethereum mainnet since the Merge (09/2022).
  - **Snowman — 2019**, "Team Rocket" / Cornell / Ava Labs, sampling family;
    production engine of Avalanche (C-Chain & P-Chain) since 2020.
- Closing legend line with colour dots: one colour per protocol — amber ·
  violet · ice — tags every chart from here to the end.
- Static cards, no chips; 4 step-mode beats (card ×3 + legend line).

**S3 · The gap: no common lens to compare the three families** (1 min) —
drafts/ch2 §2.3–2.4
- Reframed per author feedback: show what you get and what you lose if you put
  the 3 families side by side *today*. Three columns:
  - PBFT-style reports **throughput** (ops/s on a low-latency LAN) — says
    nothing about finality delay.
  - PoS-finality reports **finality delay** (~12 min, 2 epochs) — says nothing
    about throughput.
  - Avalanche-style reports **safety probability ε** at one fixed (K, β)
    parameter set — number changes if parameters change.
- Punchline: measurements are plentiful but designed never to sit next to each
  other; surveys only juxtapose others' numbers; the one matched-harness
  precedent (Gervais et al.) covers Proof-of-Work only. → no overall view;
  hence build one.

**S4 · Goal + research questions as 5W1H** (1 min) — drafts/ch1 §1.3, §1.5
- One simulator · three protocols · matched assumptions.
- RQs recast as plain questions (keep RQ numbers as small tags for
  traceability to the report):
  - **WHEN** the network slows — how much does finality slow? (RQ1)
  - **WHAT** happens to throughput as the Byzantine fraction rises? (RQ2)
  - **HOW MUCH** does each committed unit cost in messages? (RQ3)
  - **WHO** breaks each protocol — which adversary, which property? (RQ4)
  - **WHICH** protocol wins overall — does any family dominate? (RQ5)

### Act 2 — How the simulation is built & run (~4.5 min)

**S5 · Three families, three protocols — INTERACTIVE flow diagram** (2 min) —
drafts/ch3 §3.3 (Figures 3.2/3.3/3.4 descriptions), ch2 Table 2.1
- One SVG stage + **3 switch chips: [PBFT] [Casper FFG] [Snowman]**. Clicking a
  chip swaps the diagram and replays its animation; message paths highlight in
  sequence (effective-html flow-chip pattern).
  - **PBFT**: n=4 validators, Node 3 offline. Animate client→primary request,
    PRE-PREPARE broadcast, all-to-all PREPARE, all-to-all COMMIT; block decided
    at 2f+1 = 3 matching votes per phase. Caption: leader-driven, two all-to-all
    phases, deterministic finality, O(n²) messages. Final beat: **view-change
    vignette** — happy path fades out (scene swap), primary goes silent (N3 back online), timeouts
    → VIEW-CHANGE all-to-all → NEW-VIEW (N1 = primary) → phases replay →
    "liveness restored". Grounds the "recovery path" claims in S8-loss and S10.
  - **Casper FFG**: checkpoint chain over epochs. Animate attestations
    accumulating on a link; checkpoint turns *justified* at ≥⅔ stake, turns
    *finalized* when its child is justified; one pending checkpoint left
    unfinalized. Caption: stake-weighted checkpoint finality, deterministic,
    ~1.15n messages, slashing makes failure attributable.
  - **Snowman**: validator v polls K random peers per round; if ≥ α_c agree,
    confidence counter ticks up; counter resets on preference switch; accepted
    at β=15 consecutive rounds. Caption: leaderless subsampling, probabilistic
    finality ε ≤ (1−α_c/K)^β, per-validator cost independent of n.

**S6 · The harness — motion diagram, NO switch buttons** (1.5 min) —
drafts/ch3 §3.2, §3.5 (Figure 3.1 description)
- Single left-to-right animated pipeline, auto-playing (or replay-on-click):
  **config (protocol, n, timeline, adversary, seed)** → fixed infrastructure
  box [scheduler for virtual time · network with configurable delay/loss ·
  logger] with a visibly **swappable protocol slot** → **one result row**
  (records commit_hash + seed). Loop arrow: repeats per seed and per cell.
- Two spoken points rendered as short labels: (1) only the protocol slot
  varies, so output differences are attributable to the protocol; (2) shared
  denominator = **ACU** (atomic commit unit): 1 PBFT block ≡ 1 FFG finalized
  checkpoint ≡ 1 Snowman accepted block.

**S7 · Experiment design — 3 run families, WITH switch chips** (1 min) —
drafts/ch3 §3.4 (Table 3.2)
- SVG axis diagram + **3 switch chips: [A — Scaling] [B — Delay] [C —
  Adversarial]**. Each chip animates a sweep along its axis, other axes shown
  pinned:
  - **A — Scaling**: n sweeps {4, 7, 10, 16, 25}, clean network, honest set →
    answers RQ3.
  - **B — Delay**: timeline sweeps baseline → uniform 100–500 ms →
    heavy-tail 1–5 s; optional packet loss 5/10/20%; n ∈ {10, 25} → RQ1.
  - **C — Adversarial**: adversary fraction φ ∈ {0, 0.10, 0.20, 0.30} (+0.40,
    0.50 above threshold for equivocation); behaviors delayed-voting / silent /
    equivocation; n ∈ {10, 25} → RQ2, RQ4.
- Constant footer: common workload (Poisson 100 tx/s, 512-byte tx), 20
  seeds/cell, common random numbers → paired comparisons.

### Act 3 — Results (~4.5 min)

**S8 · Results — ONE slide, 4 switch tabs** (4.5 min) — merged former S8–S11
per author feedback. Tabs: **[A — Scaling] [B — Delay] [B — Loss] [C —
Adversarial]**. Each tab = one redrawn chart + one takeaway line. Charts are
built in the unified diagram design system above — same SVG vocabulary,
protocol colors, chip/tab component, and animation grammar as S5–S7 (bars grow
from the axis, lines draw in, using the same timing tokens).
- **Tab A — Scaling (RQ3)** — drafts/ch4 §4.2: log-scale bar chart of messages
  per committed unit at n=25: PBFT **≈50** · Casper FFG **≈29** · Snowman
  **≈601** — an order-of-magnitude gap; measured trends match theory (2n /
  1.15n / 2Kβ). Secondary: latency flat in n — PBFT & Snowman ≈1 s, FFG ≈5 s
  (epoch-granularity finality).
- **Tab B — Delay (RQ1)** — drafts/ch4 §4.3.1: slowdown vs zero-delay baseline:
  FFG **×1.3** · PBFT **×1.9** · Snowman **×12–15** (each of β=15 sequential
  poll rounds waits on the slowest of K sampled peers). Round-bounded protocols
  insensitive to tail shape; Snowman sharply sensitive.
- **Tab B — Loss** — drafts/ch4 §4.3.2–4.3.3: resilience ranking **PBFT >
  Snowman > FFG**. PBFT the only protocol still finalizing at 20% loss (has a
  recovery path: view-change rotates the leader); Snowman holds partially at 5%
  and cliffs by 10% at n=10 — the clear plateau-then-cliff shape is an n=25
  result (ch4 §4.3.2: "absent at n = 10"); FFG collapses at the
  first 5% step (neither). No protocol forks — loss erodes liveness, not
  safety. Survivors pay in latency (×2–3.5).
- **Tab C — Adversarial (RQ2+RQ4)** — drafts/ch4 §4.4, Table 4.1: 3×3 outcome
  matrix (strategy × protocol), color-coded outcome kind:
  - Delayed voting: PBFT immune (success 1.0) · FFG success dips to 0.60–0.65
    (rotating proposer stalls) · Snowman survives but ×62 / ×49 slower.
  - Silent: PBFT clean to φ=0.33, quorum cliff at 0.40 · FFG graceful decay to
    0.33 · Snowman starves earliest (survival depth φ* = 0.10 / 0.20).
  - Equivocation (above ⅓): PBFT deterministic **unaccountable fork** at
    φ=0.40 · FFG **no fork, ≥⅓ stake slashable** (accountable) · Snowman **no
    fork surface**, analytical bound ε ≈ 5×10⁻¹⁵ / 3×10⁻¹¹.

### Act 4 — Insight & future work (~3 min)

**S9 · Synthesis (RQ5): no protocol dominates** (1.25 min) — drafts/ch5
§5.2–5.3
- Radar, 8 axes from Table 5.1, ordinal rank (label it illustrative/ordinal —
  the table in the report is the evidence).
- Core insight: **the same design choice creates both the strength and the
  weakness.** Snowman's K-peer subsampling keeps it live under slow peers yet
  starves it under silent ones; PBFT's leader-quorum commit carries it through
  delay/loss/silence yet forks unaccountably past the threshold; FFG's
  epoch-paced finality is cheapest and least delay-sensitive yet first to
  collapse under loss (while alone holding accountable safety).

**S10 · Implications: a selection map, not a winner** (45s) — drafts/ch5 §5.4,
ch1 §1.6
- Match protocol to dominant threat: need attribution → **Casper FFG** ·
  liveness under network turbulence → **PBFT** · equivocation resistance →
  **Snowman**.
- Callback to S2: each opening incident is a protocol at its structural limit.
- Contributions strip: simulator · 3 implementations · dataset+analysis ·
  methodology (Gervais et al. extended from PoW to BFT families).

**S11 · Limitations & future work + closing** (1 min) — drafts/ch6
- Limitations: simplified one-per-family implementations; n ≤ 25 (sensitivity
  argument beyond); Snowman safety by analytical bound, not witnessed;
  adversary spares the view-0 leader; no compute/bandwidth cost.
- Future: production-level aggregation (BLS / HotStuff threshold sigs);
  saturation-throughput model; adaptive timeout in a timeout-stressing regime;
  empirical witness for ε; extend harness to a DAG family (Narwhal+Tusk).
- Closing line: the contribution is a **mechanism map** of the
  performance–security frontier, not the naming of a single winner.

## Timing budget (≈15 min)

S1 0.5 · S2 1.5 · S2B 0.75 · S3 1 · S4 1 · S5 2 · S6 1.5 · S7 1 · S8 4.5 ·
S9 1.25 · S10 0.75 · S11 1 → ≈ 16.25 min (trim in rehearsal; S8 tabs are the
flex zone, and S5's per-protocol intros can shrink now that S2B introduces
the protocols).

## Interaction inventory (for build QA)

Presenter **step mode** (2026-07-09, replaces autoplay): every animated slide
is split into steps whose boundaries are the beats of
`slides/defense-script.md` — one Space press = one beat.

- Space / → / PgDn: next step; when the active pane is out of steps, advances
  to the next chip/tab in script order (S5 pbft→ffg→snowman, S7 A→B→C,
  S8 a→bd→bl→c), then to the next slide. Rapid presses fast-forward cleanly
  (pending reveals settle instantly before the next step plays).
- Shift+Space / ← / PgUp: step back; at step 0 goes to the previous pane
  (fully revealed), then the previous slide.
- ↓ / ↑: whole-slide jump (for Q&A). Home/End unchanged.
- S5: 3 protocol chips + 1 mouse-only Q&A chip (Recovery — dashed border,
  not in `PANES.s5.order`, Space never enters it) · S7: 3 family chips ·
  S8: 4 result tabs — all still mouse-clickable for Q&A jumps; clicking one
  resets that pane to its entry step. S6 svg click replays from entry.
- Step boundaries live in the `STEPS` map (deck JS), keyed by root id /
  `tab-<key>`; thresholds are `data-t` values. Editing a diagram's timings
  may require updating its `STEPS` row + the matching script beats.
- `prefers-reduced-motion`: each root renders fully revealed; keys just
  navigate panes/slides.
