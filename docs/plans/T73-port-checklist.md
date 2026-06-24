# T73 — Port checklist (markdown → `.tex` / Overleaf)

What the **human** applies to `../thesis-tex/MIT-thesis-template/chapter*.tex` (and
`appendixa.tex`) to mirror the T73 markdown edits. The agent edited **markdown only**.
Citations port via `wiki/concepts/citation-keys.md`; `[[wiki/...]]` links are dropped on
port. Grouped by `.tex` target. Numbers in `[N]` are the markdown bibliography indices.

> **One-line summary of T73:** the Narwhal+Tusk / four-family / DAG-based scaffolding is
> stripped from the body; the thesis presents and evaluates **three** families throughout,
> and the DAG family is acknowledged in **exactly one place** — a new Ch6 §6.3.2 further-work
> sentence. Figures are out of scope (a later pass); see the **Figures / deferred** section.

---

## `chapter1.tex`

- **§1.1 family list** — "Four families occupy four distinct points" → "Three families occupy
  distinct points". **Delete the `DAG-based` bullet** (the fourth list item, cite `[11]`).
- **§1.2 (motivation)** — in the Sui sentence, delete "secured by a DAG-based protocol `[13]`,"
  so it reads "Sui suffered a crash-loop network halt in November 2024 `[23]`." (Keep the Sui
  incident; drop only the DAG family attribution.)
- **§1.3 problem statement** — family list "the four L1 consensus families — PBFT-style,
  PoS-finality, Avalanche-style, and DAG-based" → "the three L1 consensus families —
  PBFT-style, PoS-finality, and Avalanche-style". Remove the `DAG-based` item + its
  `\cite`/wikilink.
- **§1.5 RQ5** — "across the four families" → "across the three families evaluated"; **delete**
  the trailing sentence "With the DAG-based family deferred, the frontier reported here is
  traced over the three implemented families, and the high-throughput corner the DAG family
  would occupy is left pending."
- **§1.6 contribution 2** — reword to three families, all implemented; **delete** "Three of the
  four are implemented … the DAG-based representative, Narwhal+Tusk, is scaffolded but its
  implementation is deferred."
- **§1.6 roadmap** — "Chapter 2 reviews the four families" → "three families".

## `chapter2.tex`

- **§2.2 (fork in the road)** — "The other three families" → "two families"; "to the four
  families" → "three families" (twice: body + Figure 2.1 caption). **Delete the `DAG-based`
  bullet** (cite `[11]`–`[13]`). "examines all four" → "all three".
- **§2.3 heading** — "The four families" → "The three families". Body: "through all four
  families" → "three"; "the three deterministic families" → "two deterministic families"
  (3 places: §2.3 intro, the `ε` notation row, the "At `n = 7`" paragraph); "how the four
  differ" → "how the three differ".
- **Table 2.1** — **drop the `DAG-based` column** (last column) from every row + the header.
- **Per-family paragraphs (variant trim, Tier-1):**
  - `PBFT-style`: delete the "Beyond classical PBFT … HotStuff `[5]` … Tendermint `[6]`"
    opening; keep from "The documented weakness — a *delayed-voting* adversary …".
  - `PoS-finality`: replace the "Gasper `[8]` composes Casper FFG with the LMD-GHOST …"
    opening with "Casper FFG, the finality gadget of the deployed Ethereum specification `[8]`,
    has accountable safety as its signature property: …" (keep the accountable-safety claim
    and the equivocation / silent-non-participation weakness verbatim).
  - `Avalanche-style`: "the linearized variant of the Slush → Snowflake → Snowball → Avalanche
    cascade `[9]`" → "the linearized Avalanche variant `[9]`".
  - **Delete the entire `DAG-based` per-family paragraph** (Bullshark/Mysticeti/Narwhal,
    data-availability-withholding; cite `[11]`–`[13]`).
- **§2.4.1** — "The four families have all been measured" → "three"; **delete** the sentence
  "The DAG-based papers report kilo-transactions per second … `[11]`–`[13]`."
- **Table 2.2** — **drop the three rows** `Narwhal+Tusk` (`[11]`), `Bullshark` (`[12]`),
  `Mysticeti` (`[13]`). Following prose: the example "whether Mysticeti's >200 ktps …" →
  "whether PBFT's thousands of ops/s on a LAN …".
- **§2.4.2** — "not the four BFT families" → "three"; "PBFT-style, PoS-finality,
  Avalanche-style, and DAG-based protocols" → "PBFT-style, PoS-finality, and Avalanche-style
  protocols".
- **§2.5** — "The four families respond" → "three"; **delete** the clause "— three implemented
  at this stage, the DAG-based family scaffolded and deferred —".

## `chapter3.tex`

- **§3.1** — "the four families run" → "three"; "to the four BFT families (three implemented
  here, the fourth scaffolded — §3.3.4)" → "to the three BFT families"; **delete** the
  "Three protocols are implemented at this stage … The fourth, Narwhal+Tusk (§3.3.4), is a
  deferred placeholder … written so that they need no revision …" framing, replaced by the
  short "Three protocols are implemented: PBFT, Casper FFG, and Snowman. One system model …
  apply uniformly across them."
- **§3.2** — "The four consensus families" / "Because the four" / "runs all four identically"
  → three (3×); "admits four protocols" → "three"; "identical for all four protocols" →
  "three"; "Running four kinds of decision" → "three"; "the four Byzantine strategies a
  profile can apply" → "the Byzantine strategies a profile can apply".
- **§3.2 → MOVE TO `appendixa.tex`** (cut from the chapter body, leave the one-sentence
  pointers already in the markdown): **(a)** the seven-key YAML config block, and **(b)** the
  three-row validator-capability table. Exact content to place in Appendix A is reproduced at
  the bottom of this file (**Appendix A payload**). The body now reads "… seven top-level keys
  — `n`, `t_max`, `seeds`, `network`, `adversary`, `protocol_knobs`, and `workload` —
  reproduced in full as the input contract in Appendix A." and "… each owned by a different
  component (the full capability contract is tabulated in Appendix A)."
- **§3.3** — delete the `[[wiki/algorithms/dag-based]]` citation from the representative
  sentence (no `\cite` replacement — the DAG page is uncited now). "summarizes the four
  protocols" → "three"; **delete** the sentence "The Narwhal+Tusk column and subsection are
  deferred until its implementation exists (§3.3.4)."
- **Table 3.1 (Family-to-protocol mapping)** — **drop the `DAG-based | Narwhal+Tusk — deferred`
  row**.
- **Table 3.2 (implemented protocols)** — **drop the `Narwhal+Tusk` column** (all `—` cells).
- **§3.3.4** — **delete the entire `Narwhal+Tusk` subsection.** Renumber nothing else (it was
  the last subsection of §3.3).
- **§3.4.2** — workload bullet "512-byte transactions matching the Narwhal benchmark `[11]`" →
  "fixed 512-byte transactions" (drop `[11]`).
- **§3.4.4** — "identical for all four" → "all three"; **"the other three protocols" → "the
  other two protocols"** (PBFT is the worked example); merged the two aggregation paragraphs
  (prose-only condensation, no content lost).
- **§3.5** — "The four protocols do not emit commensurable events … Narwhal+Tusk commits an
  anchor-batch over a DAG" → "The three protocols …" (drop the anchor-batch clause); "differ
  structurally in four ways — linear-chain versus DAG output … Narwhal mempool-versus-consensus
  message split …" → "differ structurally — per-block vs per-epoch finality and Snowman
  rescaling"; "The device that makes the four commensurable" → "three"; ACU list drop "and one
  anchor-batch for Narwhal+Tusk"; "four stated conventions — the ACU denominator, the Narwhal
  mempool-versus-consensus split, …" → "three stated conventions — the ACU denominator, the
  Snowman parameter rescaling, and the Casper FFG calibration". **Keep "Four metric families"**
  (latency/throughput/overhead/reliability — not consensus families).
- **§3.5 intro to Tables 3.3/3.4** — delete "; the Narwhal+Tusk column is deferred until that
  family is implemented."
- **Table 3.3 (latency/throughput)** — **drop the `Narwhal+Tusk` column**.
- **Table 3.4 (overhead/reliability)** — **drop the `Narwhal+Tusk` column**; `total_msgs_per_acu`
  PBFT cell "equals `consensus_msgs_per_acu` until a separate mempool layer exists, which only
  the Narwhal+Tusk family introduces" → "equals `consensus_msgs_per_acu`, as none of the three
  carries a separate mempool layer".
- **§3.5 deferred-columns paragraph** — "Three column groups … the mempool throughput and
  mempool-message split (`mempool_tps`, `mempool_msgs_per_acu`) with the Narwhal+Tusk
  implementation; and …" → "Two column groups … : the adversarial-threshold columns … and the
  empirical and analytical Snowman safety columns".
- **§3.6** — first paragraph "are family-agnostic: the four families' … layered-versus-single-
  layer message split … written to need no revision when the deferred Narwhal+Tusk subsection
  (§3.3.4) is filled" → "absorb the three families' structural asymmetries … per-protocol
  message accounting … so no experiment sees them". No-compute exclusion: delete "and Narwhal's
  data-availability mempool". **Coverage bound 1** "RQ4 fault survey scoped to three families.
  Deferring the DAG-based family … data-availability withholding … `[[…#7-2-narwhal-tusk-…]]`"
  → "The adversarial survey exercises only the three implemented families, so the RQ4 verdicts
  are scoped to those three." **Coverage bound 3** "RQ5 synthesis traced over three families.
  Because the DAG-based family is deferred … high-throughput corner the DAG family would occupy
  unmeasured." → "The cross-family Pareto synthesis of Chapter 5 is traced over the three
  families evaluated." **Coverage bound 2 (twelve of eighteen) is unchanged.**

## `chapter4.tex`

- **Intro** — delete "with the Narwhal+Tusk column reserved until that implementation lands,";
  keep "Three protocols are evaluated throughout — PBFT, Casper FFG, and Snowman — consistent
  with the chapter scope set in §3.6."
- **§4.4 qualification** — "First, the survey covers three families: Narwhal+Tusk is
  unimplemented, so its catalogued weakness — data-availability withholding … — is absent, and
  the adversarial verdict is scoped to the three families measured" → "First, the adversarial
  verdict is scoped to the three families evaluated". (The data-availability-withholding point
  moves to Ch6 §6.3.2.)
- **Figures untouched this pass.** (§4.2.6 latency-note was already cut in the step-0 commit.)

## `chapter5.tex`

- No Narwhal content. **Tier-1 condensation only:**
  - **§5.2** — the two-sentence convention restatement ("Two conventions fixed in Chapter 3 …")
    collapsed to one cross-reference sentence pointing at §3.5–§3.6 (conventions named:
    `commit_latency_ms`, `goodput`, no-compute caveat). Pareto-dominance definition kept.
  - **§5.3.1 / §5.3.2** — magnitude enumerations that Table 5.1 already carries were trimmed
    (prose-only; mechanism/inversion sentences, the May-2023 callback, and all contribution
    numbers — 229 forks, ×62, ε≈5×10⁻¹⁵, ≈1−φ — kept). §5.3.3 kept intact.

## `chapter6.tex`

- **§6.1** — the two-paragraph per-RQ prose walk condensed to **one paragraph** (Table 6.1
  carries the per-RQ detail; RQ2's ≈`1−φ` and the RQ4/RQ5 contribution kept). Table 6.1 and
  the incidents-revisited closing paragraph unchanged.
- **§6.3.1** — the BLS/signature-aggregation "hold optimization level constant" point (made
  ~4× in the original) condensed to one statement across two tightened paragraphs.
- **§6.3.2 — ADD the single DAG sentence** (the only Narwhal/DAG mention in the whole thesis):
  > "A fourth is to extend the harness to a DAG-based family (Narwhal+Tusk), whose
  > data-availability-withholding adversary the present sweep does not cover; adding it would
  > populate the high-throughput corner that the three-family frontier leaves unmeasured."
  Markdown cites `[[wiki/concepts/adversary-model]]`. **Optional:** add `\cite{<narwhal-key>}`
  (markdown `[11]`) here if you want the Narwhal+Tusk source to remain in the bibliography
  (see References note below).

---

## References / `.bib` note

Citations `[11]` (Narwhal+Tusk), `[12]` (Bullshark), `[13]` (Mysticeti) are **no longer cited
anywhere in the body** after T73 (their Ch1/Ch2 prose, the §3.4.2 benchmark note, and Table 2.2
rows were removed). With `biblatex` they will silently drop from the printed bibliography.
Decide one of:
1. accept the drop (DAG papers no longer referenced); **or**
2. keep `[11]` by adding a `\cite` to the new Ch6 §6.3.2 DAG sentence (recommended if you want
   the further-work direction anchored to its source); **or**
3. `\nocite` the ones you want retained as further-reading.

## Figures / deferred (later pass — NOT this task)

- **Figure 2.1 (`bft-families-tree`)** still **renders four families**; the caption now says
  "three families". The DAG branch must be pruned from the diagram source in the figure pass so
  the figure and caption agree. (Out of scope for T73 per the plan.)
- No data-plot figures changed. Chapter 4 figures are untouched.

---

## Appendix A payload (move from `chapter3.tex` §3.2 → `appendixa.tex`)

**(a) The seven-key run configuration contract (YAML input contract):**

```yaml
n: 10                      # validator-set size
t_max: 20.0                # virtual-time deadline
seeds:
  n_runs: 20               # the harness enumerates seeds 0 … n_runs-1
network:
  phases:                  # a TIME-STAMPED sequence of phases, not a static setting
    - t_start: 0.0
      t_end:   20.0
      delay: { kind: "...", params: { ... } }
      p_drop: 0.0          # optional — per-phase message-loss probability
      partitions: []       # optional — disjoint validator groups
adversary:      { ... }    # opaque block — interpreted per protocol/adversary
protocol_knobs: { ... }    # opaque block
workload:       { ... }    # opaque block
```

**(b) The validator three-capability contract (split-ownership invariant):**

| Capability granted to a validator | Owned by | Purpose |
|:--|:--|:--|
| set / cancel a timer | scheduler | a validator schedules its own future wake-ups |
| send / broadcast a message | network | a validator communicates with other validators |
| emit an event (`decided`, `halted`, …) | logger | a validator records what happened |
