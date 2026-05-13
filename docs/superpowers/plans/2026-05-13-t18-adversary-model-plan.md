# T18 Adversary Model Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task.

**Goal:** Author the adversary-model design contract as a split-pair of wiki concept pages (`wiki/concepts/adversary-model.md` and `wiki/concepts/adversary-model-runtime.md`), plus three companion-file updates, satisfying the three T18 verify clauses in TASKS.md.

**Architecture:** Prose-authoring task driven by a fully-prescriptive upstream spec at `docs/superpowers/specs/2026-05-13-t18-adversary-model-design.md`. Two wiki pages mirroring the [[concepts/network-model]] / [[concepts/network-model-phases]] split precedent: catalog (Page A) + runtime contract (Page B). Five companion files touched. Direct-to-main commits per project pattern.

**Tech Stack:** Markdown (GitHub-flavored) with Obsidian-style `[[wikilinks]]`, IEEE-style `[N]` bracketed citations, fenced Python code blocks for the reference sketch. No code execution. No tests in the TDD sense — verification is qualitative against the spec agenda and the TASKS.md verify clauses.

**Adaptation note for the executor.** Standard writing-plans bite-sized TDD shape ("write failing test → make it pass → commit") does not map onto prose. The substituted shape per task is: **(a) read the upstream wiki pages this section cites** per `docs/retrieval.md` Engineer pattern; **(b) write the section** per the spec's prescriptive agenda; **(c) verify** (line count, wikilink targets exist, `[N]` citations resolve in `concepts/annotated-bibliography.md`, table column completeness); **(d) commit** at task boundaries (not at every step — see commit cadence below).

**Commit cadence.** Eight commits total across the work (matching project precedent — T17 shipped in ~2 commits; T18 is a larger surface so spread to 8). Commit messages follow `task 18: <imperative>` per `docs/workflow.md` §commit-convention. The final In-Review commit is `task 18: define adversary catalog` and is paired with the TASKS.md status flip from `[~]` to `[?]`.

**Branch.** Direct-to-main per project pattern (recent commits `8329514`, `505d6db`, `c0a7529` are all direct-to-main). No task branch.

**Definition of done.** Three TASKS.md T18 verify clauses, mapped to deliverables:

| Verify clause | Deliverable in plan |
| :-- | :-- |
| Every generic adversary has a per-protocol semantics row or an `N/A` justification | Task 3 (Page A §§3–6 hybrid tables; Snowman × disrupt-leader `N/A` carries reason; Snowman × equivocate-vote carries reduction text) |
| Every protocol-specific adversary traces to its source paper | Task 4 (Page A §7 source column = `[9]`, `[11]`, `[7]`); Task 8 (verify each resolves in `annotated-bibliography.md`) |
| T51–T53 can be expressed as `(adversary_id, protocol_id, intensity)` triples drawn from this catalog without gaps | Task 5 (Page B §2 intensity normalization) + Task 8 (count check: 18 valid pairs) |

---

## Task 0: Preflight — read context, confirm starting state

**Files (read-only):**
- Read: `/Users/phananhle/Desktop/phananhle/thesis/CLAUDE.md` (imported docs included)
- Read: `/Users/phananhle/Desktop/phananhle/thesis/docs/superpowers/specs/2026-05-13-t18-adversary-model-design.md`
- Read: `/Users/phananhle/Desktop/phananhle/thesis/wiki/index.md`
- Read: `/Users/phananhle/Desktop/phananhle/thesis/wiki/concepts/node-model.md` (full; §9 and §10 Revisions are load-bearing for this task)
- Read: `/Users/phananhle/Desktop/phananhle/thesis/wiki/concepts/network-model.md` and `network-model-phases.md` (style precedent for split-pair)
- Read: `/Users/phananhle/Desktop/phananhle/thesis/wiki/concepts/message-types.md` (style precedent for hybrid table + prose per protocol section)
- Read: `/Users/phananhle/Desktop/phananhle/thesis/wiki/concepts/annotated-bibliography.md` (verify `[4]`, `[7]`, `[9]`, `[11]` are present)

**Step 1: Confirm spec on disk.**

Run: `ls -la /Users/phananhle/Desktop/phananhle/thesis/docs/superpowers/specs/2026-05-13-t18-adversary-model-design.md`
Expected: file exists, ~566 lines, committed in `304dbf1`.

**Step 2: Confirm git state.**

Run: `git -C /Users/phananhle/Desktop/phananhle/thesis branch --show-current && git -C /Users/phananhle/Desktop/phananhle/thesis log --oneline -3`
Expected: branch `main`; HEAD = `304dbf1 task 18: define adversary catalog design`.

**Step 3: Confirm T18 status.**

Run: `grep -n '\\*\\*T18\\*\\*' /Users/phananhle/Desktop/phananhle/thesis/TASKS.md`
Expected: line shows `[~] **T18** ...` (In Progress; do not re-flip).

**Step 4: Confirm target files do not yet exist.**

Run: `ls /Users/phananhle/Desktop/phananhle/thesis/wiki/concepts/adversary-model*.md 2>&1`
Expected: `No such file or directory` — both target files are unwritten.

**Step 5:** No commit. This task is read-only orientation.

---

## Task 1: Scaffold both pages + author §1 Framing on each

**Files:**
- Create: `wiki/concepts/adversary-model.md` (skeleton + §1 only)
- Create: `wiki/concepts/adversary-model-runtime.md` (skeleton + §1 only)

**Step 1: Read upstream context for cross-links.**

Both §1 sections cite [[concepts/node-model#adversary-attachment]], [[concepts/fault-model]], [[concepts/evaluation-metrics]], and (for Page A) [[concepts/adversary-model-runtime]] forward-pointer; (for Page B) [[concepts/network-model]] / [[concepts/network-model-phases]] precedent. Confirm each target page exists by `ls wiki/concepts/`.

**Step 2: Write Page A skeleton + §1.**

Use `Write` tool. Top-level structure exactly as spec §4:

```
# Adversary Model

<§1 prose: ~25 lines per spec §4.§1>

## 1. Framing and scope
## 2. Generic capability × protocol matrix
## 3. delay-emission
## 4. withhold-participation
## 5. equivocate-vote
## 6. disrupt-leader
## 7. Protocol-specific surfaces
## 8. Revisions
## 9. Sources
```

§1 prose covers: (a) two-layer organisation (generic × protocol matrix, then protocol-specific surfaces); (b) static-only profile contract per spec §3 D2; (c) per-protocol natural intensity unit per spec §3 D1; (d) forward pointer to [[concepts/adversary-model-runtime]]; (e) cross-links to [[concepts/node-model#adversary-attachment]], [[concepts/fault-model]], [[concepts/evaluation-metrics]].

Style precedent: open with one paragraph stating what the page is and isn't (mirroring [[concepts/network-model]] §1's opening). Technical register, no thesis-prose softening.

**Step 3: Write Page B skeleton + §1.**

Top-level structure exactly as spec §5:

```
# Adversary Model — Runtime

<§1 prose: ~15 lines per spec §5.§1>

## 1. Framing — relationship to main page
## 2. Intensity normalization
## 3. Effect schema
## 4. AdversaryProfile reference sketch
## 5. Determinism interaction with T27
## 6. Open to revision
## 7. Sources
```

§1 prose: catalog ↔ runtime split statement; same precedent as [[concepts/network-model]] / [[concepts/network-model-phases]] and [[concepts/simulation-design]] / [[concepts/simulation-design-runtime]]; one-paragraph "this is the runtime companion to [[concepts/adversary-model]]" statement.

**Step 4: Verify wikilink targets.**

Run for each wikilink target referenced in either §1:
`ls wiki/concepts/<target>.md`
Expected: each target file exists. If any is missing, stop and ask — do not write to a dangling target.

**Step 5: Verify line counts.**

Run: `wc -l wiki/concepts/adversary-model.md wiki/concepts/adversary-model-runtime.md`
Expected: each file under 50 lines at this point (skeleton + §1 only).

**Step 6: Commit.**

```bash
git -C /Users/phananhle/Desktop/phananhle/thesis add wiki/concepts/adversary-model.md wiki/concepts/adversary-model-runtime.md
git -C /Users/phananhle/Desktop/phananhle/thesis commit -m "$(cat <<'EOF'
task 18: scaffold adversary-model split-pair

Two new concept pages following the network-model / network-model-phases
split precedent. §1 Framing on each page; remaining sections are
empty headings, to be filled in subsequent commits.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Page A §2 — Generic capability × protocol matrix

**Files:**
- Modify: `wiki/concepts/adversary-model.md` (replace `## 2. Generic capability × protocol matrix` heading with full section)

**Step 1: Read upstream sources for matrix cells.**

The matrix mechanism phrases must trace to the four algorithm pages:
- `wiki/algorithms/pbft.md` §Behaviour-under-adversarial-conditions
- `wiki/algorithms/pos.md` §Behaviour-under-adversarial-conditions
- `wiki/algorithms/avalanche.md` §Behaviour-under-adversarial-conditions
- `wiki/algorithms/dag-based.md` §Behaviour-under-adversarial-conditions

Also re-read: `wiki/concepts/node-model.md` §9 attachment matrix (the existing matrix that this page expands — language must compose, not contradict).

**Step 2: Write §2 content.**

Per spec §4.§2 (~30 lines). Structure:

```markdown
## 2. Generic capability × protocol matrix

The four generic capabilities and their per-protocol bindings. Rows are
protocol-agnostic capability classes; columns are the four protocols in
scope. Cells carry a terse mechanism phrase (the §§3–6 sections below
expand each row with intensity, S/L classification, invariant, and source).

| Capability | PBFT | Casper FFG | Snowman | Narwhal+Tusk |
| :-- | :-- | :-- | :-- | :-- |
| **delay-emission** | gate `PREPARE`/`COMMIT` broadcast | gate attestation broadcast | gate `QUERY-RESPONSE` send | gate certificate broadcast |
| **withhold-participation** | silent non-participation | non-participation; ≥1/3 stalls finalisation | skip `QUERY-RESPONSE` | withholding |
| **equivocate-vote** | conflicting `PRE-PREPARE` to disjoint subsets | double-vote / surround-vote (slashable) | reduces to "lying responder" (see §5) | distinct headers to disjoint peers |
| **disrupt-leader** | as primary: slow/refuse `PRE-PREPARE` | as slot proposer: refuse or equivocate | **N/A** — no leader role (see §6) | as anchor leader: withhold or refuse to reference anchor |

Two asymmetric cells are first-class findings, not gaps:

- **Snowman × `disrupt-leader` is structurally `N/A`** because Snowman
  has no leader role ([[concepts/node-model]] §5). Sampling is
  leaderless. The asymmetry is the comparative claim.
- **Snowman × `equivocate-vote` reduces to "lying responder"** because
  Snowman's vote-counting has no inter-message intersection step; the
  protocol cannot distinguish equivocation from selective response
  ([[concepts/node-model]] §9 ll. 470–473). The reduction is the
  comparative claim.

This matrix is the Chapter 4 comparison surface. Asymmetric cells
encode structural property differences between the four families.
[[concepts/node-model]] §9 owns the *attachment surface* (which `Node`
method each capability gates); §§3–6 below own the *binding semantics*.
```

**Step 3: Verify line count.**

Run: `wc -l wiki/concepts/adversary-model.md`
Expected: ≤ 80 lines (skeleton + §1 + §2).

**Step 4: Verify wikilinks resolve.**

For each `[[…]]` in this section, run `ls wiki/<target>.md` and confirm the file exists.

**Step 5: No commit yet.** §2 commits with §§3–6 (Task 3) as one logical unit ("generic capability matrix + expansions").

---

## Task 3: Page A §§3–6 — Generic capability expansions

**Files:**
- Modify: `wiki/concepts/adversary-model.md` (replace headings for §3, §4, §5, §6 with full sections)

This is the largest task in the plan. ~165 lines added total (40 + 40 + 45 + 40 per spec §4).

**Step 1: Read upstream sources.**

Re-read sections of the four algorithm pages already read in Task 2 — for each capability, gather the specific mechanism details, intensity ranges, and S/L classifications.

For invariant column, re-read `wiki/concepts/evaluation-metrics.md` and `wiki/concepts/metric-reconciliation.md` (these define the metric names that appear in the invariant column).

For Casper accountable-safety cost, re-read `wiki/algorithms/pos.md` §accountable-safety (the ~α/3 stake-burn claim).

**Step 2: Write §3 `delay-emission` (~40 lines).**

Structure per spec §4.§3:

```markdown
## 3. delay-emission

Adversary gates outbound emissions past the protocol's timing tolerance.
Liveness attack class; safety is unaffected in all four bindings.

| Protocol | Mechanism | Intensity range | S/L | Invariant checked | Source |
| :-- | :-- | :-- | :-- | :-- | :-- |
| PBFT | gate `PREPARE` / `COMMIT` broadcast past view-change timeout | f ∈ [0, 0.33] of n replicas | L | view-change rate ≤ baseline + 3σ | [4] |
| Casper FFG | gate attestation broadcast past slot boundary | f ∈ [0, 0.33] of stake | L | finality lag ≤ 2 epochs from honest baseline | [7] |
| Snowman | gate `QUERY-RESPONSE` `send` past poll deadline | f ∈ [0, 0.33] of validators | L | accept_time p95 ≤ 5× honest baseline | [9] |
| Narwhal+Tusk | gate certificate broadcast past round boundary | f ∈ [0, 0.33] of n replicas | L | throughput ≥ (1 − f) · honest baseline | [11] |

<~80 words prose covering: α-threshold near-miss behaviour where Snowman's preference oscillates without accepting; Snowman tail "don't-know" reply interaction at the asynchrony boundary; PBFT view-change-rate as the operationalisation of the liveness invariant; Narwhal's throughput-proportional degradation absorbing the attack until f approaches 1/3.>
```

**Step 3: Verify §3.**

- Table has 6 columns × 4 rows.
- Source column entries `[4]`, `[7]`, `[9]`, `[11]` resolve in `wiki/concepts/annotated-bibliography.md`. Run: `grep -E "^\\[4\\]|^\\[7\\]|^\\[9\\]|^\\[11\\]" wiki/concepts/annotated-bibliography.md` — expect 4 lines.
- Line count of section: 40–45 lines.

**Step 4: Write §4 `withhold-participation` (~40 lines).**

Per spec §4.§4. Same 6-column table shape. Prose covers: `halted{crashed}` lifecycle encoding per [[concepts/node-model#halt-reasons]]; skip-vs-slow distinction from §3; Casper ≥1/3 finalisation-stall threshold per [[algorithms/pos#behaviour-under-adversarial-conditions]]; Narwhal throughput-proportional degradation per [[algorithms/dag-based#behaviour-under-adversarial-conditions]].

Table rows:

| Protocol | Mechanism | Intensity range | S/L | Invariant checked | Source |
| :-- | :-- | :-- | :-- | :-- | :-- |
| PBFT | silent abstain from `PREPARE` / `COMMIT`; or `halted{crashed}` | f ∈ [0, 0.33] of n | L | progress per view ≥ baseline · (1 − f) | [4] |
| Casper FFG | skip attestation; or `halted{crashed}` | f ∈ [0, 0.33] of stake | L | finality lag ≤ 2 epochs while f < 1/3; finalisation stalls at f ≥ 1/3 | [7] |
| Snowman | skip `QUERY-RESPONSE`; or `halted{crashed}` | f ∈ [0, 0.33] of validators | L | accept rate ≥ (1 − f) · honest baseline | [9] |
| Narwhal+Tusk | skip certificate broadcast; or `halted{crashed}` | f ∈ [0, 0.33] of n | L | throughput ≥ (1 − f) · honest baseline | [11] |

**Step 5: Verify §4** (same checks as §3).

**Step 6: Write §5 `equivocate-vote` (~45 lines).**

Per spec §4.§5. Longest of the four. The Snowman cell carries the reduction text:

| Protocol | Mechanism | Intensity range | S/L | Invariant checked | Source |
| :-- | :-- | :-- | :-- | :-- | :-- |
| PBFT | as primary: emit conflicting `PRE-PREPARE` to disjoint subsets | f ∈ [0, 0.33] of n; primary slot only | L (safety holds; triggers view change) | no two-honest commit conflict at same (view, seq) | [4] |
| Casper FFG | double-vote or surround-vote at attestation | f ∈ [0, 0.33] of stake | S above threshold; L below | accountable-safety: any two-conflicting-finalised → ≥1/3 stake slashable | [7] |
| Snowman | *reduces to* "lying responder" — return non-preference colour | f ∈ [0, 0.33] of validators | L (no fork-induction surface) | empirical safety-violation rate ≤ (1 − α_c/K)^β | [9] |
| Narwhal+Tusk | broadcast distinct headers to disjoint peer subsets | f ∈ [0, 0.33] of n | L (blocked at cert step) | no conflicting header reaches 2f+1 signatures | [11] |

Prose (~80 words) covers: **(a)** the reduction — Snowman has no inter-message intersection step (no quorum-collection round where two messages from one validator are compared), so signing incompatible messages is mechanically indistinguishable from selective response; the Snowman row of this matrix and §6's Snowman row of `withhold-participation` therefore overlap mechanically while differing in *intent* (cf. [[concepts/node-model]] §9 ll. 470–473); **(b)** Casper's safety-cost budget — successful safety violation costs ~α/3 of stake destroyed via slashing per [[algorithms/pos#accountable-safety]], a metric absent from the other three families; **(c)** Narwhal's certificate-step block — the `2f+1`-signature requirement prevents any conflicting header version from reaching certificate status per [[algorithms/dag-based#safety-argument]]; **(d)** PBFT's view-change-as-detector — equivocation forces a view change rather than corrupting safety, so the operational invariant is "view change frequency tracks equivocator rate."

**Step 7: Verify §5** (same checks as §3; additionally verify the reduction prose is present and cross-references [[concepts/node-model]] §9 correctly).

**Step 8: Write §6 `disrupt-leader` (~40 lines).**

Per spec §4.§6. The Snowman cell carries the `N/A` with structural reason:

| Protocol | Mechanism | Intensity range | S/L | Invariant checked | Source |
| :-- | :-- | :-- | :-- | :-- | :-- |
| PBFT | as primary: slow / refuse `PRE-PREPARE` to force view change | f ∈ [0, 0.33] of n; primary slot only | L | view-change rate tracks adversary fraction | [4] |
| Casper FFG | as slot proposer: refuse block production; or propose conflicting blocks (slashable) | f ∈ [0, 0.33] of stake; proposer slot only | L (slashable in equivocation case) | block proposal failure rate tracks adversary fraction | [7] |
| Snowman | **N/A** — no leader role | — | — | — | — |
| Narwhal+Tusk | as anchor leader: withhold or refuse to reference the anchor | f ∈ [0, 0.33] of n; anchor slot only | L | anchor-commit lag bounded by 2× anchor period | [11] |

Prose (~80 words) covers: Snowman's `N/A` reason — sampling is leaderless per [[concepts/node-model]] §5; the Bullshark / Mysticeti anchor-leader caveat (both have anchor leaders too, so the `N/A` is Snowman-specific, not "leaderless-protocols-in-general"; flagged for forward compatibility per [[algorithms/dag-based#family-scope]]); the slashable-equivocation overlap with §5 for Casper (proposer equivocation is also slashable; §7.3 covers the explicit slashing-payload formulation).

**Step 9: Verify §6** (same checks as §3; verify all four `N/A` cells in the Snowman row carry the em-dash placeholder and the prose explains the reason).

**Step 10: Verify total line count after §§3–6.**

Run: `wc -l wiki/concepts/adversary-model.md`
Expected: ~210–230 lines (skeleton + §1 + §2 + §§3–6).

**Step 11: Commit.**

```bash
git -C /Users/phananhle/Desktop/phananhle/thesis add wiki/concepts/adversary-model.md
git -C /Users/phananhle/Desktop/phananhle/thesis commit -m "$(cat <<'EOF'
task 18: add generic capability matrix + per-capability expansions

§2 matrix and §§3–6 per-capability hybrid tables on adversary-model.md.
Four generic capabilities (delay-emission, withhold-participation,
equivocate-vote, disrupt-leader) × four protocols (PBFT, Casper FFG,
Snowman, Narwhal+Tusk), with one structural N/A (Snowman ×
disrupt-leader) and one noted reduction (Snowman × equivocate-vote →
lying responder). Each cell carries mechanism, intensity range, S/L
classification, invariant, source.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Page A §7 — Protocol-specific surfaces; §8 stub; §9 Sources

**Files:**
- Modify: `wiki/concepts/adversary-model.md` (replace remaining headings)

**Step 1: Read upstream sources for §7 entries.**

- `wiki/algorithms/avalanche.md` §Behaviour-under-adversarial-conditions (sample-partitioning) — for §7.1
- `wiki/algorithms/dag-based.md` §Behaviour-under-adversarial-conditions (withholding) and `wiki/concepts/node-model.md` §9 ll. 483–485 — for §7.2
- `wiki/algorithms/pos.md` §slashing-conditions — for §7.3

**Step 2: Write §7 — three subsections.**

Per spec §4.§7. ~45 lines total. Each subsection carries: action, victim protocol, S/L, intensity range, invariant, source.

```markdown
## 7. Protocol-specific surfaces

Three adversaries are structurally unique to one protocol because they
exploit a property the other three families do not share (sampled
quorum; two-layer availability/ordering split; on-chain slashing). They
live here rather than in the §2 matrix because the matrix exists for
cross-protocol comparison; single-protocol attacks would be 3-N/A rows.

### 7.1 Snowman colluding sub-sampler

**Action.** Multiple `Node`s' adversary profiles coordinate
`QUERY-RESPONSE` colours to bias `α_c` counts in honest validators'
samples per [[algorithms/avalanche#behaviour-under-adversarial-conditions]]
(sample-partitioning).

**Victim.** Snowman only.
**Intensity.** f ∈ [0, 0.33] of validators in the colluding pool.
**S/L.** Safety (probabilistic).
**Invariant.** Empirical safety-violation rate ≤ theoretical bound
`(1 − α_c/K)^β` from [[algorithms/avalanche#probabilistic-safety]].
**Source.** [9].

**Structural uniqueness.** Snowman is the only family member that draws
a random sub-sample per query; the other three families operate over
fixed quorums (PBFT replica set, Casper validator set per epoch,
Narwhal committee). Coordination is "shared params + derived RNG seed"
per [[concepts/adversary-model-runtime#determinism-interaction-with-t27]].

### 7.2 Narwhal+Tusk data-availability withholding

**Action.** Adversary worker certifies the header (gathers `2f+1`
signatures) but refuses to serve batch contents on subsequent `send`
requests per [[algorithms/dag-based#behaviour-under-adversarial-conditions]]
and [[concepts/node-model]] §9 ll. 483–485.

**Victim.** Narwhal+Tusk only.
**Intensity.** f ∈ [0, 0.33] of n replicas.
**S/L.** Liveness (consensus stalls when missing batches block ordering).
**Invariant.** Batch availability rate ≥ honest baseline minus f.
**Source.** [11].

**Structural uniqueness.** Only Narwhal+Tusk separates data availability
from ordering. PBFT, Casper FFG, and Snowman all carry payload in the
consensus messages themselves; there is no "certify but withhold" gap
because there is no distinct availability layer to attack.

### 7.3 Casper FFG slashable-equivocation refinements

**Action.** Surround vote (`<S₁, T₁>` surrounding own `<S₂, T₂>` with
`S₁ < S₂ < T₂ < T₁`) and double vote (two distinct votes with the same
target epoch), each with explicit slashing-evidence payload per
[[algorithms/pos#slashing-conditions]].

**Victim.** Casper FFG only.
**Intensity.** f ∈ [0, 0.33] of stake.
**S/L.** Safety above threshold; cost-bounded.
**Invariant.** Successful safety violation → ≥1/3 stake slashable
(accountable safety theorem per [[algorithms/pos#accountable-safety]]).
**Source.** [7].

**Structural uniqueness.** Casper is the only family with on-chain
slashing. PBFT equivocation triggers a view change with no economic
penalty; Narwhal equivocation is blocked at certificate formation;
Snowman has no inter-message intersection to detect equivocation
against.
```

**Step 3: Write §8 stub.**

```markdown
## 8. Revisions

Reserved per the W3 design-contract precedent ([[concepts/node-model#revisions]]
established the pattern). Initially empty.
```

**Step 4: Write §9 Sources.**

```markdown
## 9. Sources

Citations `[4]`, `[7]`, `[9]`, `[11]` resolve via
[[concepts/annotated-bibliography]] to:

- [[sources/2026-04-21_castro-liskov-pbft-1999]] (`[4]`)
- [[sources/2026-04-21_buterin-griffith-casper-ffg-2017]] (`[7]`)
- [[sources/2026-04-21_team-rocket-avalanche-2019]] (`[9]`)
- [[sources/2026-04-21_danezis-narwhal-tusk-2022]] (`[11]`)
```

**Step 5: Verify Page A line count.**

Run: `wc -l wiki/concepts/adversary-model.md`
Expected: 270–295 lines. Must be ≤ 300 per [[docs/wiki-spec]] §page-size. If over, trim prose in the longest §3–§6 section; do not split.

**Step 6: Verify all wikilinks in Page A resolve.**

Run: extract every `[[…]]` from `adversary-model.md` and confirm each target file exists:

```bash
grep -oE '\[\[[^]]+\]\]' wiki/concepts/adversary-model.md | sort -u
```

For each wikilink (stripping `#anchor` fragments), check `ls wiki/<target>.md`. Any dangling target → stop and ask.

**Step 7: Verify all [N] citations resolve in annotated-bibliography.**

Run: `grep -E "^\\[(4|7|9|11)\\]" wiki/concepts/annotated-bibliography.md`
Expected: 4 lines, one per citation used. If any missing → stop and ask (this would be a real wiki integrity bug, not just a T18 issue).

**Step 8: Commit (closes Page A).**

```bash
git -C /Users/phananhle/Desktop/phananhle/thesis add wiki/concepts/adversary-model.md
git -C /Users/phananhle/Desktop/phananhle/thesis commit -m "$(cat <<'EOF'
task 18: complete adversary-model.md (Page A)

§7 protocol-specific surfaces (Snowman colluding sub-sampler [9],
Narwhal data-availability withholding [11], Casper slashable-
equivocation refinements [7]) plus §8 Revisions stub and §9 Sources.

Page A complete; satisfies T18 verify clauses 1–2 (every generic
adversary has a per-protocol row or structural N/A; every protocol-
specific adversary traces to its source paper).

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Page B §§2–3 — Intensity normalization + Effect schema

**Files:**
- Modify: `wiki/concepts/adversary-model-runtime.md` (replace §2 and §3 headings)

**Step 1: Read upstream sources.**

- `wiki/concepts/evaluation-metrics.md` — for column names in §3 effect schema
- `wiki/concepts/metric-reconciliation.md` — for per-protocol formulas the column names map onto
- Re-read spec §5.§2 and §5.§3

**Step 2: Write §2 Intensity normalization (~50 lines).**

```markdown
## 2. Intensity normalization

Each `(adversary_id, protocol_id, intensity)` triple consumed by T51–T53
carries an intensity `f ∈ [0, 1]` whose unit is the protocol's *natural*
fault-threshold denominator:

| Protocol | `f` unit | Why this unit |
| :-- | :-- | :-- |
| PBFT | fraction of n replicas | Simulator uses equal-weight validators; replicas = nodes. Native fault threshold is f < n/3 by count. |
| Casper FFG | fraction of total stake | Casper's threshold is stake-weighted; the accountable-safety cost (~α/3 stake burned per [[algorithms/pos#accountable-safety]]) is stake-denominated by definition. |
| Snowman | fraction of validators | Snowman's sub-sampling is node-uniform (modulo external sybil resistance) per [[algorithms/avalanche#model-and-assumptions]]; biasing stake without biasing validator count does not perturb the sampler. |
| Narwhal+Tusk | fraction of n replicas | Same as PBFT in the simulator scope. |

The triple shape for T51–T53 is therefore:

`(adversary_id: AdversaryKind, protocol_id: ProtocolId, f: float)`

with the meaning of `f` resolved by `protocol_id` via the table above.

**Cross-protocol plot policy.** Plots that span more than one protocol on
the x-axis must caption which unit they report. The default is to plot
each protocol on its own panel; a single-panel comparison requires either
(a) restricting to PBFT + Narwhal+Tusk (where the unit is identical) or
(b) explicitly captioning "stake-fraction for Casper; validator-fraction
for Snowman; replica-fraction for PBFT and Narwhal." Per-plot
re-mapping happens at plot-generation time, not in the catalog.

**Why per-protocol natural rather than a single forced unit.**

A single stake-fraction unit would force Snowman's sample-bias mechanism
through an indirection (bias x% of stake → bias x% of sampling pool
under equal-weight) that has no semantic content in the simulator and
loses the natural threshold framing for PBFT and Narwhal+Tusk. A single
node-count unit would erase Casper's stake-burn cost reporting. The
per-protocol-natural choice respects each family's native fault model;
the cost is a per-protocol re-mapping step at plot-generation time,
surfaced explicitly above.
```

**Step 3: Verify §2** (line count, wikilinks).

**Step 4: Write §3 Effect schema (~40 lines).**

```markdown
## 3. Effect schema

Every adversary run populates the same CSV column set. Column names match
[[concepts/evaluation-metrics]] and [[concepts/metric-reconciliation]];
T18 does not introduce new metric definitions.

**Per-capability expected perturbation.** Which columns each capability
is *expected* to shift:

| Capability | Columns expected to perturb |
| :-- | :-- |
| `delay-emission` | `time_to_finality_p50`, `time_to_finality_p95`, `consensus_msgs_per_acu` |
| `withhold-participation` | `liveness_failures`, `finality_lag_epochs` (Casper only), `throughput_per_validator` |
| `equivocate-vote` | `safety_violations`, `slashing_events` (Casper only), `view_changes` (PBFT only), `equivocations_blocked` (Narwhal only) |
| `disrupt-leader` | `view_changes` (PBFT), `anchor_commit_lag` (Narwhal), `block_proposal_failures` (Casper) |
| `snowman-collusion` (§7.1) | `safety_violations`, `accept_time_p95` |
| `narwhal-data-withhold` (§7.2) | `batch_availability_rate`, `consensus_stall_events` |
| `casper-slashing` (§7.3) | `slashing_events`, `safety_violations`, `safety_cost_stake_burned` |

**Invariant vs effect.** The §§3–7 of the catalog page carry the
*invariant* column (what passes or fails per cell). This effect-schema
table carries the *effect* (which metric column moves). The two are
related but distinct: an invariant says "view-change rate ≤ baseline +
3σ"; the effect says "the column `view_changes` is the one that moves."
T55 reads invariants for detection logic; T40 reads the effect schema
for CSV column finalisation.
```

**Step 5: Verify §3** (line count, wikilinks, column names cross-checked against `evaluation-metrics.md`).

If `evaluation-metrics.md` does not yet contain all column names referenced (e.g. `safety_cost_stake_burned`, `equivocations_blocked`, `anchor_commit_lag`), surface this as an open question and add an entry to the §6 register in Task 7; do not silently add new columns to `evaluation-metrics.md` from this task.

**Step 6: Commit.**

```bash
git -C /Users/phananhle/Desktop/phananhle/thesis add wiki/concepts/adversary-model-runtime.md
git -C /Users/phananhle/Desktop/phananhle/thesis commit -m "$(cat <<'EOF'
task 18: add intensity normalization + effect schema (runtime page §§2–3)

§2 pins per-protocol natural intensity unit (replicas for PBFT/Narwhal,
stake for Casper, validators for Snowman) with cross-protocol plot
policy. §3 maps capabilities to expected CSV column perturbations,
cross-linked to evaluation-metrics and metric-reconciliation.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Page B §4 — AdversaryProfile reference sketch

**Files:**
- Modify: `wiki/concepts/adversary-model-runtime.md` (replace §4 heading)

**Step 1: Read upstream sources.**

- `wiki/concepts/node-model.md` §9 (existing `class AdversaryProfile(Protocol)` skeleton — must extend, not contradict)
- `wiki/concepts/node-model.md` §10 reference sketch (style precedent for "illustrative non-binding" framing)
- Spec §5.§4 (full Python sketch)

**Step 2: Write §4 (~70 lines).**

Reproduce the Python sketch from spec §5.§4 verbatim inside a fenced code block. Prefix with the "illustrative non-binding" framing paragraph established by [[concepts/node-model#reference-sketch-illustrative-non-binding]].

```markdown
## 4. AdversaryProfile reference sketch (illustrative, non-binding)

Per the W3 design-contract style established for this thesis's hand-off
to W4 code ([[concepts/node-model#reference-sketch-illustrative-non-binding]],
[[concepts/network-model#reference-sketch]], [[concepts/simulation-design-runtime#reference-sketch]]),
this sketch is **not a specification**. It exists so T22 (`src/nodes/`)
has a starting shape and so a reader scanning this page cold can picture
the artifact. T22 may diverge; divergences land as `## Revisions`
entries per [[docs/wiki-spec]] §revisions-rule.

```python
# Reference sketch — illustrative, non-binding.
# Implementation (T22) may diverge; document via §6 Revisions register.

from dataclasses import dataclass, field
from typing import Protocol, Optional
from enum import Enum

class AdversaryKind(Enum):
    DELAY = 0
    WITHHOLD = 1
    EQUIVOCATE = 2
    DISRUPT_LEADER = 3
    SNOWMAN_COLLUSION = 4
    NARWHAL_DATA_WITHHOLD = 5
    CASPER_SLASHING = 6

class AdversaryProfile(Protocol):
    kind: AdversaryKind
    nodes: tuple[int, ...]      # NodeIds; fixed at sim-start
    intensity: float            # per-protocol natural unit (see §2)

# ... (seven concrete @dataclass(frozen=True) bodies — see spec §5.§4)
\```

**Attachment.** [[concepts/node-model#node-level-slot]] declares the
`self.adversary: Optional[AdversaryProfile]` slot. When non-`None`, the
FSM module routes outbound emissions and state-mutation decisions
through the profile before honest behaviour.

**Static-only contract.** Profile fields are read once at relevant
emission points; there is no `on_observe()` callback (per spec §3 D2).
T22 implements `self.adversary` as an opaque strategy slot reading
these fields; T18 fills the slot.
```

(In the actual write, replace the `# ... (seven concrete ...)` placeholder with the full seven dataclass bodies copied from spec §5.§4.)

**Step 3: Verify §4** (line count ~70; wikilinks resolve; Python code block opens and closes correctly with triple-backticks; dataclass count = 7).

**Step 4: No commit yet.** §4 commits with §5 in Task 7.

---

## Task 7: Page B §§5–7 — Determinism interaction + Open to revision + Sources

**Files:**
- Modify: `wiki/concepts/adversary-model-runtime.md` (replace §5, §6, §7 headings)

**Step 1: Read upstream sources.**

- `wiki/concepts/node-model.md` §8 (determinism rules, per-Node RNG seeding)
- `wiki/concepts/simulation-design-runtime.md` §determinism-contract
- Spec §5.§5 and §5.§6

**Step 2: Write §5 Determinism interaction (~25 lines).**

```markdown
## 5. Determinism interaction with T27

The static-only profile contract (§4) gives the determinism rule for free:
identical `(config, seed)` produces byte-identical adversary-injected
events at byte-identical times.

**Per-Node adversary RNG.** Each `Node`'s RNG is seeded from the sim seed
per [[concepts/node-model#determinism-and-reproducibility]] §8.1. When
the FSM dispatches through `self.adversary`, any randomness (e.g.
choosing which subset to send equivocating messages to) draws from this
per-Node RNG, not from a global source.

**Colluding-group seed derivation.** Adversaries that coordinate across
multiple `Node`s (e.g. `SnowmanCollusionProfile`) derive a shared RNG
seed from `hash(sim_seed, group_id)`. The `group_id` field is fixed at
sim-start; the derivation is deterministic. Two colluding nodes drawing
from the same derived seed in the same order make identical decisions
without runtime coordination.

**Replay invariant.** A run with `(config, seed)` produces an event log
byte-identical to any other run with the same `(config, seed)`.
Adversary-injected events are part of the log; the invariant covers
them.

Cross-links: [[concepts/node-model#determinism-and-reproducibility]],
[[concepts/simulation-design-runtime#determinism-contract]].
```

**Step 3: Verify §5** (line count, wikilinks).

**Step 4: Write §6 Open to revision (~35 lines).**

Mirror spec §7. Each spec §7 item becomes a §6 bullet on the runtime page:

```markdown
## 6. Open to revision

The catalog deliberately leaves these items open for downstream tasks.
Each promotes to a `## Revisions` entry on this page (or on
[[concepts/adversary-model]]) when resolved.

- **Adversary timing.** Static-only for T18. Promote to bounded-adaptive
  only if T22 implementation or T51 results expose a specific gap (an
  attack class with no static analogue).
- **Coordination protocol for Snowman colluding sub-sampler.** Currently
  "shared params + derived RNG seed" (§5). If T51 surfaces stale-state
  attacks (e.g. coordinated lag in adopting a new round number), the
  coordination model may need richer shared state.
- **Intensity range bounds per cell.** All cells in
  [[concepts/adversary-model]] §§3–7 carry `f ∈ [0, 0.33]` as a
  placeholder. T51–T53 calibration tightens per-cell ranges.
- **`AdversaryProfile` final type.** `typing.Protocol` now (§4). T22 may
  promote to `abc.ABC` if dispatch needs concrete inheritance — but the
  static-only contract makes this unlikely.
- **Safety-cost-budget column.** Currently lives in
  [[concepts/evaluation-metrics]]. T40 (CSV finalisation) may move it to
  a dedicated effect-schema slot.
- **LMD-GHOST reorg-inducer.** The brainstorm audit subsumed it under
  `delay-emission` ([[concepts/adversary-model#3-delay-emission]]). If
  W10 Casper results show structurally-distinct reorg dynamics, promote
  to a fourth protocol-specific entry under
  [[concepts/adversary-model#7-protocol-specific-surfaces]] §7.4.
- **Bullshark / Mysticeti out-of-scope.** Reaffirmed by spec §3 D5.
  Revisit only if family scope widens past Narwhal+Tusk.
- **Snowman `α_p` vs `α_c` boundary exploit.** Audit subsumed under
  colluding-sub-sampler. If T51 results expose a distinct attack at the
  preference-flip threshold, promote to §7.4.
- [Add here any column names referenced by §3 effect schema that are
  not yet defined in [[concepts/evaluation-metrics]] — only if Task 5
  Step 5 surfaced any.]
```

**Step 5: Write §7 Sources (~10 lines).**

```markdown
## 7. Sources

Inherits the bibliography of [[concepts/adversary-model#9-sources]]. No
additional sources are introduced on this page.
```

**Step 6: Verify Page B line count.**

Run: `wc -l wiki/concepts/adversary-model-runtime.md`
Expected: 240–270 lines. Must be ≤ 300.

**Step 7: Verify all wikilinks in Page B resolve.**

Same procedure as Task 4 Step 6.

**Step 8: Commit (closes Page B).**

```bash
git -C /Users/phananhle/Desktop/phananhle/thesis add wiki/concepts/adversary-model-runtime.md
git -C /Users/phananhle/Desktop/phananhle/thesis commit -m "$(cat <<'EOF'
task 18: complete adversary-model-runtime.md (Page B)

§4 AdversaryProfile reference sketch (typing.Protocol + 7 frozen
dataclasses, illustrative non-binding); §5 determinism interaction
with T27 (per-Node RNG, colluding-group seed derivation, replay
invariant); §6 open-to-revision register (8 deferred items); §7
sources inherited from Page A.

Page B complete.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Companion files — index, log, node-model Revisions

**Files:**
- Modify: `wiki/index.md` (add 2 entries)
- Modify: `wiki/log.md` (add 1 entry)
- Modify: `wiki/concepts/node-model.md` (add `## Revisions` entry)

**Step 1: Read upstream for log/index format.**

- `wiki/index.md` (existing layout — under `## Concepts` section, alphabetically by slug)
- `wiki/log.md` (last 3 entries — for format precedent)
- `wiki/concepts/node-model.md` §10 Revisions (precedent for Revisions entry format; see existing 2026-05-13 §6 entry there)

**Step 2: Add two entries to `wiki/index.md` under `## Concepts`.**

Insert in alphabetical position (immediately after `[[concepts/annotated-bibliography]]` line):

```markdown
- [[concepts/adversary-model]] — Adversary catalog: four-row generic capability × protocol matrix (delay-emission, withhold-participation, equivocate-vote, disrupt-leader) plus three protocol-specific surfaces (Snowman colluding sub-sampler, Narwhal data-availability withholding, Casper slashable-equivocation refinements). One structural N/A (Snowman × disrupt-leader), one noted reduction (Snowman × equivocate-vote → lying responder). 18 valid (adversary, protocol) pairs.
- [[concepts/adversary-model-runtime]] — Runtime companion to `adversary-model`: per-protocol natural intensity unit; uniform effect schema mapping capabilities to expected CSV column perturbations; `AdversaryProfile` reference sketch (`typing.Protocol` + 7 frozen dataclasses, illustrative non-binding); determinism interaction with T27 (per-Node RNG + colluding-group seed derivation); open-to-revision register.
```

**Step 3: Append one entry to `wiki/log.md`.**

Per `docs/wiki-spec.md` §log-format:

```markdown
## [2026-05-13] code | task 18 — adversary model design contract

- role: Engineer
- touched: wiki/concepts/adversary-model.md (new), wiki/concepts/adversary-model-runtime.md (new), wiki/index.md, wiki/concepts/node-model.md (§10 Revisions entry), docs/superpowers/specs/2026-05-13-t18-adversary-model-design.md (committed earlier), docs/superpowers/plans/2026-05-13-t18-adversary-model-plan.md (committed earlier)
- notes: Filed the adversary catalog as a split-pair design contract (catalog + runtime). 4 generic capabilities × 4 protocols + 3 protocol-specific surfaces; 18 valid (adversary, protocol) pairs sized for T51–T53. Locks 7 design decisions including per-protocol natural intensity unit (replicas / stake / validators), static-only adversary profile, and `typing.Protocol` + frozen-dataclass reference sketch. node-model §9 contracts to attachment-surface-only (Revisions entry added there).
```

**Step 4: Add `## Revisions` entry to `wiki/concepts/node-model.md`.**

Per spec §8. Append to the existing `## Revisions` section (which already contains the 2026-05-13 §6 entry):

```markdown
### 2026-05-13 — §9 scope contracts to attachment surface only

T18 ([[concepts/adversary-model]]) now owns adversary binding
semantics. §9 retains the attachment-surface declaration (per-protocol
FSM/outbound touchpoint matrix, `self.adversary` slot, protocol-
specific slot list) but no longer owns the cross-protocol semantic
detail. Per-cell binding semantics (mechanism, intensity range,
safety/liveness classification, invariant) live in
[[concepts/adversary-model]] §§3–7. The §9 matrix here remains as the
declaration of *which* `Node` method each capability gates; the
binding details for *what* the gated method does in each protocol are
on the adversary-model page.

No other §s are affected. Determinism rules (§8), inbound API (§6),
outbound API (§7), and role taxonomy (§5) are unchanged.
```

**Step 5: Verify index.md size unchanged in structural shape.**

Run: `wc -l wiki/index.md`
Expected: previous count + 2 lines. Must remain ≤ 500 per [[docs/retrieval]] guidance.

**Step 6: Verify log.md format.**

Run: `grep -E '^## \\[' wiki/log.md | tail -5`
Expected: the new entry appears as the most recent, with the `## [YYYY-MM-DD] <type> | task <N> — <title>` prefix.

**Step 7: Commit.**

```bash
git -C /Users/phananhle/Desktop/phananhle/thesis add wiki/index.md wiki/log.md wiki/concepts/node-model.md
git -C /Users/phananhle/Desktop/phananhle/thesis commit -m "$(cat <<'EOF'
task 18: companion updates — index, log, node-model revisions

wiki/index.md gains entries for adversary-model and
adversary-model-runtime under Concepts. wiki/log.md gains one task-18
entry per docs/wiki-spec §log-format. node-model.md §10 Revisions
gains a 2026-05-13 entry noting that §9 scope contracts to attachment-
surface-only, with binding semantics moving to adversary-model.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Verification + TASKS.md flip + final In-Review commit

**Files:**
- Modify: `TASKS.md` (flip T18 from `[~]` to `[?]`)

**Step 1: Re-verify all three T18 verify clauses against on-disk state.**

Verify clause 1 — "every generic adversary has a per-protocol semantics row or an N/A justification":

```bash
# Each of §§3–6 of adversary-model.md must contain a 4-row table.
# Each row must be either a mechanism phrase OR an N/A with prose
# justification.
grep -A 6 "^## 3\\. delay-emission" wiki/concepts/adversary-model.md
grep -A 6 "^## 4\\. withhold-participation" wiki/concepts/adversary-model.md
grep -A 6 "^## 5\\. equivocate-vote" wiki/concepts/adversary-model.md
grep -A 6 "^## 6\\. disrupt-leader" wiki/concepts/adversary-model.md
```

Manually confirm: each shows a table with PBFT, Casper FFG, Snowman, Narwhal+Tusk rows; §6's Snowman row shows `**N/A**` and the prose below the table explains the structural reason.

Verify clause 2 — "every protocol-specific adversary traces to its source paper":

```bash
grep -E "Source.*\\[(7|9|11)\\]" wiki/concepts/adversary-model.md
```

Expected: 3 lines (one per §7.1, §7.2, §7.3). Confirm the citations resolve in `annotated-bibliography.md`:

```bash
grep -E "^\\[(7|9|11)\\]" wiki/concepts/annotated-bibliography.md
```

Expected: 3 lines.

Verify clause 3 — "T51–T53 can be expressed as `(adversary_id, protocol_id, intensity)` triples drawn from this catalog without gaps":

Count valid pairs manually:
- Generic: 4 capabilities × 4 protocols = 16 cells; minus 1 N/A (Snowman × disrupt-leader) = **15 valid generic pairs**.
- Protocol-specific: 3.
- **Total: 18 valid pairs.**

Confirm both pages reference this number:
```bash
grep -n "18 valid" wiki/concepts/adversary-model*.md
```

Expected: at least one match, surfaced in §1 framing or §2 caption of Page A, or in §2 of Page B. If no match, add one sentence to Page A §1 stating "The catalog admits 18 valid `(adversary_id, protocol_id)` pairs; intensity per pair is per §2 of [[concepts/adversary-model-runtime]]."

**Step 2: Verify both page line counts.**

```bash
wc -l wiki/concepts/adversary-model.md wiki/concepts/adversary-model-runtime.md
```

Expected: both ≤ 300. If either exceeds, trim prose in the longest section (do not split — splitting would be a Revisions cycle on the layout decision).

**Step 3: Verify all wikilinks in both pages resolve.**

```bash
for f in wiki/concepts/adversary-model.md wiki/concepts/adversary-model-runtime.md; do
  echo "=== $f ==="
  grep -oE '\[\[[^]]+\]\]' "$f" | sort -u
done
```

For each unique wikilink, strip the `#anchor` fragment and verify `ls wiki/<target>.md` succeeds.

**Step 4: Verify all `[N]` citations resolve.**

```bash
grep -hoE '\[[0-9]+\]' wiki/concepts/adversary-model*.md | sort -u
```

For each citation `[N]`, verify it resolves in `wiki/concepts/annotated-bibliography.md`:

```bash
grep -E "^\\[<N>\\]" wiki/concepts/annotated-bibliography.md
```

**Step 5: Flip T18 status in TASKS.md.**

`TASKS.md` line 98 currently reads:
```
- `[~]` **T18** `H` Engineer — Define adversarial behavior categories (per-protocol)
```

Edit to:
```
- `[?]` **T18** `H` Engineer — Define adversarial behavior categories (per-protocol)
```

(Using `Edit` tool with exact string match. The `[~]` → `[?]` flip is the only change.)

**Step 6: Final In-Review commit.**

```bash
git -C /Users/phananhle/Desktop/phananhle/thesis add TASKS.md
git -C /Users/phananhle/Desktop/phananhle/thesis commit -m "$(cat <<'EOF'
task 18: define adversary catalog

Status: In Progress → In Review.

Adversary catalog complete as a split-pair design contract:
- wiki/concepts/adversary-model.md (~280 lines): four-row generic
  capability × protocol matrix + three protocol-specific surfaces.
- wiki/concepts/adversary-model-runtime.md (~250 lines): intensity
  normalization, effect schema, AdversaryProfile reference sketch,
  determinism interaction, open-to-revision register.

T18 verify clauses satisfied:
1. Every generic adversary has a per-protocol semantics row or an
   N/A justification (one N/A: Snowman × disrupt-leader; one noted
   reduction: Snowman × equivocate-vote → lying responder).
2. Every protocol-specific adversary traces to its source paper
   ([9], [11], [7]).
3. T51–T53 can size against 18 valid (adversary_id, protocol_id)
   pairs.

Companion updates:
- wiki/index.md: +2 Concepts entries.
- wiki/log.md: +1 entry per docs/wiki-spec §log-format.
- wiki/concepts/node-model.md §10 Revisions: §9 scope contracts to
  attachment-surface-only.

Awaiting human review.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

**Step 7: Report to human.**

Stop here. Do **not** push without explicit authorization (per project hard rules).

Summary to post:
- Files touched: list each commit and what it changed.
- Wiki pages added: 2 (`adversary-model.md`, `adversary-model-runtime.md`).
- Wiki pages updated: 2 (`index.md`, `log.md`).
- Wiki pages with Revisions entries: 1 (`node-model.md`).
- Decisions made: 7 (D1–D7 from the spec, re-stated tersely).
- Open questions deferred: 8 items in Page B §6 Open to revision.
- Commits: 7 work commits on top of the spec commit (`304dbf1`). Total branch state vs `origin/main` per `git log --oneline origin/main..HEAD`.

---

## Definition of done

All checked items below must be true before the user marks T18 `[x]` Completed (a flip humans do, never the agent — per `CLAUDE.md` §Hard-rules):

- [ ] `wiki/concepts/adversary-model.md` exists, ≤300 lines, all wikilinks resolve, all `[N]` citations resolve in `annotated-bibliography.md`.
- [ ] `wiki/concepts/adversary-model-runtime.md` exists, ≤300 lines, all wikilinks resolve.
- [ ] `wiki/index.md` lists both new pages under `## Concepts`.
- [ ] `wiki/log.md` has one new entry matching `docs/wiki-spec.md` §log-format.
- [ ] `wiki/concepts/node-model.md` §10 Revisions has the 2026-05-13 §9 entry.
- [ ] `TASKS.md` T18 status is `[?]` (In Review).
- [ ] T18 verify clauses 1–3 all satisfied (see Task 9 Step 1).
- [ ] No new metric column names introduced to `evaluation-metrics.md` from this task (or, if Task 5 Step 5 surfaced any gaps, they are flagged in Page B §6 open-to-revision rather than silently added).
- [ ] All commits authored as `task 18: <imperative>` with Co-Authored-By trailer.
- [ ] Branch state matches plan: 7 work commits on `main` past the spec commit (`304dbf1`).

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-13-t18-adversary-model-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** — dispatch a fresh subagent per task (Tasks 1–9 above), review the diff between tasks, fast iteration. Best when you want to see and react to each commit as it lands. **Sub-skill:** `superpowers:subagent-driven-development`.

**2. Parallel Session (separate)** — open a new Claude Code session, point it at this plan file, let it execute Tasks 1–9 end-to-end with the plan as its instruction set. Best when you want the whole T18 page write to happen unattended. **Sub-skill:** `superpowers:executing-plans`.

Which approach?
