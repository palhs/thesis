# Draft style

How the Writer authors prose in `drafts/ch*.md`. This governs draft chapter
prose only. The wiki keeps its own technical/synthesis register; chat follows
`docs/chat-style.md`; code and specs follow theirs. The Writer role in
`docs/roles.md` writes every chapter against this file.

## Audience

The examination committee — the thesis advisor and examiners. Assume fluency
in distributed systems and consensus. Standard field terminology (Byzantine
fault tolerance, quorum, safety and liveness, finality, GST, view-change,
equivocation, DAG) is used without a first-use gloss. Do not pad chapters with
tutorial explanation of standard concepts. Define a term only when it is
genuinely non-standard or is used in a narrow sense specific to this thesis.

Technical terminology is exempt, but general (non-technical) vocabulary is
constrained to the IELTS 7.0 band. Prefer common, widely understood words
over rarer or more ornate near-synonyms: "show" or "demonstrate" rather than
"evince"; "use" rather than "utilise"; "because" rather than "inasmuch as";
"large" rather than "voluminous". Formality is achieved through sentence
structure and precision (see Register), not through reaching for a more
obscure word.

This is the opposite of `docs/chat-style.md`, which defines terms for a
beginner reader. The two audiences differ — do not apply chat-style glossing
to drafts.

## Register

Formal academic. The canonical example, same content in the chosen register:

> The comparative evaluation reported in this chapter is conducted by means of
> a discrete-event simulator rather than a production deployment. This
> methodological choice is dictated by the requirement for controlled fault
> injection: the adversarial conditions under examination — equivocation,
> message delay, and validator unavailability — cannot be reproduced
> deterministically on a live network, where confounding variables preclude
> the attribution of an observed degradation to a specific cause.

- Periodic sentences and nominalization are acceptable where they buy
  precision; do not sacrifice exactness for brevity.
- Measured and impersonal. No hype, no marketing adjectives, no rhetorical
  questions.
- Each paragraph advances one point; claims are stated, then supported.

## Voice

Impersonal. The agent of a sentence is the work, not the author: "Four
protocols were implemented", "this chapter compares", "the experiment
measures". Do not use first person — neither "we" nor "I" — in chapter prose.
Where the passive becomes genuinely tortured or ambiguous, recast around a
named agent ("the simulator", "Chapter 3") rather than slipping into "we".

## Word choice

- Spelling: US English (the MIT thesis template).
- Use the wiki's canonical term for each concept, consistently. Where
  `docs/chat-style.md` prefers a plain word for chat (e.g. "leader rotation"),
  drafts still use the precise technical term ("view-change"). Chat and drafts
  diverge here by design.
- No contractions ("do not", not "don't").
- Prefer the precise technical term over an informal synonym; the concrete
  over the vague.

## Claims and citations

Unchanged from `docs/wiki-spec.md`: every claim cites a wiki page inline as
`[[wiki/...]]`; missing external citations are marked `TODO(cite)`; do not
invent citations. Drafts introduce no claim not traceable to a wiki page.

## Figures and diagrams

Diagram sources live in `wiki/diagrams/<group>/<slug>.md` as Mermaid
fenced blocks. Mermaid is the single DSL the thesis uses; the curated
Mermaid syntax reference for this project is in
[`docs/mermaid-syntax.md`](mermaid-syntax.md). Authors of a new diagram
read that file first.

Two Mermaid diagram types are in scope:

- **`sequenceDiagram`** — every sequence and interaction diagram
  (scheduler contracts, protocol main loops, the macro runtime view).
- **`flowchart`** — taxonomy and component diagrams (Chapter 2 family
  tree, future architecture/component figures).

Drafts do not embed the DSL; they reference the rendered figure.

Rendered PDFs are co-located with their source: `wiki/diagrams/<group>/<slug>.pdf`
sits beside `wiki/diagrams/<group>/<slug>.md`. PDFs are tracked in git.
Agents never invent a PDF path that does not match the diagram's wiki
slug. (Vector PDF, not PNG: Mermaid output is line art and text; vector
stays crisp at any zoom and keeps figure text selectable.)

Hand-off pattern (single route, no human bottleneck):

- **Agent export via `mmdc`.** The agent that authors the diagram also
  renders the PDF in the same pass, using the invocation pinned in
  [`docs/mermaid-syntax.md`](mermaid-syntax.md) (and mirrored in
  [[diagrams/index]] § Export for thesis figures). The PDF is committed
  alongside the `.md`; the draft cites the rendered figure with no
  pending-export marker.

Citation pattern in prose: `Figure 3.1 ([[diagrams/protocols/pbft]])`. The
wikilink is the back-reference to source-of-truth; the figure number is the
front-stage handle. Final cross-reference numbering, captions, and the
list-of-figures are T62 (W12 figure polish); the LaTeX-side
`\includegraphics` lines and the copy of `wiki/diagrams/**/*.pdf` into
`../thesis-tex/MIT-thesis-template/figures/` are downstream of T62 as well.

L-W12 verifies that every figure reference has a PDF on disk before
submission (`docs/lint-protocol.md` check 8). Historical drafts may
carry `TODO(human-export)` markers from the prior Swimlanes pipeline;
those are tracked like `TODO(cite)` and must be cleared before
submission — the migration plan that retired Swimlanes is
[`docs/plans/2026-05-26-swimlanes-to-mermaid.md`](plans/2026-05-26-swimlanes-to-mermaid.md).

## What this does NOT change

- Wiki pages keep their technical/synthesis register.
- Chat follows `docs/chat-style.md`.
- Code and specs keep their target register.
- The Writer workflow (Outline → Confirm → Draft) is unchanged; this file
  only fixes the style the Draft phase writes in.
