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

## What this does NOT change

- Wiki pages keep their technical/synthesis register.
- Chat follows `docs/chat-style.md`.
- Code and specs keep their target register.
- The Writer workflow (Outline → Confirm → Draft) is unchanged; this file
  only fixes the style the Draft phase writes in.
