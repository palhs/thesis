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

Diagram sources live in `wiki/diagrams/<group>/<slug>.md` as DSL blocks.
Two DSLs are in use:

- **Swimlanes.io** for sequence and interaction diagrams (scheduler
  contracts, protocol main loops). No clean CLI exists, so export is
  human-only.
- **Mermaid** for taxonomy and component diagrams (Chapter 2 family
  tree, future architecture/component figures). Renders via the
  Mermaid CLI (`mmdc`), so the agent that authors the diagram also
  produces the PDF in the same pass.

Drafts do not embed the DSL; they reference the rendered figure.

Rendered PDFs are co-located with their source: `wiki/diagrams/<group>/<slug>.pdf`
sits beside `wiki/diagrams/<group>/<slug>.md`. PDFs are tracked in git.
Agents never invent a PDF path that does not match the diagram's wiki
slug. (Vector PDF, not PNG: both Swimlanes and Mermaid output are line
art and text; vector stays crisp at any zoom and keeps figure text
selectable.)

Hand-off pattern differs by DSL:

- **Swimlanes (human-export).** The Writer cites the figure in prose
  at the point it is needed, then drops a `TODO(human-export)` line
  directly under the paragraph with two fields: the source wiki page
  (`wiki/diagrams/<group>/<slug>.md`) and the intended caption. The
  target PDF path is implied by the wiki slug. The human exports the
  PDF from swimlanes.io to the co-located path.
- **Mermaid (agent-export).** The agent renders to PDF via `mmdc` as
  part of the same task that authors the diagram source (invocation
  pinned in [[diagrams/index]] § Export for thesis figures), commits
  the PDF alongside the `.md`, and cites the rendered figure in the
  draft without any `TODO(human-export)` marker.

Citation pattern in prose: `Figure 3.1 ([[diagrams/protocols/pbft]])`. The
wikilink is the back-reference to source-of-truth; the figure number is the
front-stage handle. Final cross-reference numbering, captions, and the
list-of-figures are T62 (W12 figure polish); the LaTeX-side
`\includegraphics` lines and the copy of `wiki/diagrams/**/*.pdf` into
`../thesis-tex/MIT-thesis-template/figures/` are downstream of T62 as well.

`TODO(human-export)` markers are tracked like `TODO(cite)`. L-W12 verifies
no marker remains and that every figure reference has a PDF on disk before
submission (see `docs/lint-protocol.md` check 8).

## What this does NOT change

- Wiki pages keep their technical/synthesis register.
- Chat follows `docs/chat-style.md`.
- Code and specs keep their target register.
- The Writer workflow (Outline → Confirm → Draft) is unchanged; this file
  only fixes the style the Draft phase writes in.
