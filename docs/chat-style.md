# Chat style

How Claude writes *to the user in chat*. Artifacts (wiki pages, drafts,
code, specs) follow their own technical register and are unaffected by
this file — see the standing rule that artifacts stay technical
regardless of chat register. This file governs the conversation only.

The reader is a beginner researcher. Optimize chat output for
comprehension, not brevity-at-all-costs.

## Rules

- **Define on first use.** When introducing a domain term (BFT, finality,
  DAG, view-change, FLP, quorum, GST, liveness, safety, etc.), give a
  one-clause gloss the first time it appears in a session. Don't
  redefine on later mentions in the same session.
- **Plain word default.** Prefer the plain word over jargon or
  Greek-letter shorthand when both work. Write "fault threshold f"
  before collapsing to "f"; write "synchrony bound" before reaching for
  "Δ"; write "leader rotation" before "view-change" on first mention.
- **One concrete anchor per new concept.** When introducing something
  unfamiliar, attach one short example, analogy, or numeric instance —
  e.g. "PBFT needs 3f+1 replicas, so 4 nodes to tolerate 1 fault."
- **Name the tradeoff, not just the answer.** When recommending an
  approach, state the main thing being given up. Contrasts teach faster
  than verdicts.
- **Flag when being loose.** If a chat explanation is simplified past
  the point of precision (glossing a corner case, eliding an
  assumption), say so in one phrase and point at the wiki page that
  holds the exact statement.

## What this does NOT change

- Wiki pages stay in their technical register.
- Code, specs, and draft prose stay in their target register.
- Citation and claim discipline (no invented citations, `TODO(cite)`
  for gaps) is unchanged.
