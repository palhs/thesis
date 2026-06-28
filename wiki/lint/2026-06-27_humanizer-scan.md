# Humanizer detection scan — drafts/ch1–ch6

**Date:** 2026-06-27
**Branch:** `task/sentence-density-pass` (at commit `283365d`)
**Type:** detection-only report — NO files were edited in this pass.
**Method:** 4 parallel subagents applied the `/humanizer` rubric
(`.claude/skills/humanizer/SKILL.md`, 29 patterns) to the current working-tree
drafts. Register-aware: the skill's "PERSONALITY AND SOUL" advice (first person,
opinions, casual voice, contractions) was **deliberately ignored** — it lowers
the formal academic register fixed by `docs/draft-style.md` and is disallowed
(`docs/draft-narrative.md` §8; consistent with the T73 log note that a prior
`/humanizer` run "warranted no register-safe edits"). Each hit was labelled
**tell** (genuine AI giveaway) or **legit** (defensible academic usage).

## Headline

The prose is **semantically clean**. The residual AI-detection risk is almost
entirely **structural / cadence**, concentrated in three things. A semantic
detector finds little; a density/structure detector keys on em-dashes.

## Clean across the whole thesis (≈0 hits, good)

- **P7 AI-vocabulary** (crucial, pivotal, underscore, delve, leverage, showcase,
  landscape, testament, seamless, enhance, holistic, intricate, interplay): ~0.
  Only `robust` appears (ch4 ×12, ch6 ×3, ch3 ×2) — the precise BFT term of art
  (= fault tolerance), used consistently; legit by meaning, flaggable only by a
  naive keyword counter.
- **P1 significance/legacy inflation:** 0. No "pivotal moment / evolving landscape".
- **P25 generic-positive conclusion:** 0. Ch6 §6.4 closes on a concrete claim
  ("a map of mechanisms"), not "the future looks bright".
- **P8 copula avoidance** (serves as / stands as / boasts): 0.
- **P12 false ranges:** 0 — every "from X to Y" is a genuine numeric scale.
- **P23 filler, P24 over-hedging, P27 authority tropes, P11 synonym cycling,
  P29 fragmented headers, P6 formulaic challenges:** ~0.

## The three concentrated tells (worth fixing, in priority order)

### 1. 🔴 Em-dash density — the dominant tell, every chapter ranked it #1

| | ch1 | ch2 | ch3 | ch4 | ch5 | ch6 | **Total** |
|---|--:|--:|--:|--:|--:|--:|--:|
| em-dash (—) | 12 | 10 | **69** | **85** (62 prose) | 14 | 5 | **195** |

The earlier reduction pass (commit `5bfff2e`) was deliberately conservative —
it converted only the **23 "easy" pairs** (no internal comma). It left two
buckets untouched, and **ch3 (69) and ch4 (62 prose) are still heavy**, with
several sentences carrying two em-dashes (ch4 lines 15, 266, 432; ch3 33–34, 302).
The untouched buckets:
- **~22 em-dash pairs whose insert contains an internal comma** — cannot become
  commas (ambiguous), but can become parentheses.
- **~35 single break/summary em-dashes** — can become `:` / `,` / `.` per case.

This is the single biggest lever for lowering a Turnitin/AI-density flag.

### 2. 🟠 Repeated verbatim phrasings + count-announcer frame + closing antithesis

Surgical, ~6–8 spots:
- **ch5:** "X occupies a corner" ×3 (the three §5.3 subsection openers,
  ~l.58/112/121) — vary them. "reported rather than empirically witnessed" ×3
  (~l.128/178/216) — vary.
- **ch6 §6.4 closer:** negative parallelism "not a winner, but a map" (l.165) and
  "not interchangeable faults … they are the separable consequences" (l.172–174)
  — the strongest single cadence tell in ch6; recast the antithesis.
- **ch4:** count-announcer frame "\<cardinal\> \<noun\>: first… second…" survives
  the "Two X…" de-templating ("two findings stand out: first…", l.328). One
  short punch line "The fork is deterministic." (l.618).
- **ch1/ch2:** "not a benchmark … but a … framework" (ch1 l.79); "not a single
  protocol but a design space" (ch2 l.12); "No foundational result permits a free
  lunch:" (ch2 l.29); rhetorical heading "The fork in the road" (ch2 §2.2).
- **ch4 -ing tails:** bare ", confirming X" closers (l.105/199/281) — mild.

### 3. 🟡 Bold inline-header bullet lists (P15/P16) — RECOMMEND LEAVE

- **ch3:** 27 inline-header bullets ("- **① Single primary…**", threats-to-validity,
  Family A/B/C) + 51 bold spans. **ch1:** 12 (the numbered Contributions list).
  ch4/ch5/ch6 clean (only Figure/Table caption labels).
- Structurally matches the AI list pattern, but here it is **legitimate technical
  enumeration** (deviation ledgers, named exclusions). Converting to prose would
  destroy skim-utility for the examiner. Low actual risk. Recommend keeping.

## Recommended next-session plan (not yet executed)

1. **Aggressive em-dash pass on ch3 + ch4** (highest impact): convert the ~22
   comma-containing pairs to parentheses and triage the ~35 single dashes to
   `:`/`,`/`.`. Apply the same hard invariants used all session: per-file
   number-multiset and `[[wiki/...]]` citation-multiset identical to HEAD;
   en-dash (`–`) count unchanged; no contraction/first-person added; no double
   punctuation. Reuse the `:`-not-`.` rule for any count-announcer.
2. **De-duplicate the repeated phrasings** (ch5 "occupies a corner" ×3,
   "reported rather than empirically witnessed" ×3; ch4 short punch line).
3. **Recast the ch6 §6.4 closing antithesis** (the two "not X but Y" sentences).
4. **Leave** the bold/bullet enumeration lists (P15/P16) — defensible, useful.

## Branch state at end of this session

`task/sentence-density-pass`, 5 commits, **NOT pushed**, no `TASKS.md` entry yet
(ad-hoc, human-directed). Commits:
1. `72845da` density (B-split + C-move) ch1,ch3–ch6
2. `5bfff2e` em-dash reduction (conservative, 23 easy pairs) 241→195
3. `300bc21` strip inline repo paths from prose + merge 2 short fragments
4. `e16f471` de-template "Two X…" openers (Ch4)
5. `283365d` colon-join announcers + extend de-templating to Ch3/Ch5
(this report adds a 6th, lint-type commit)

Open decisions for the human: push the branch? add a `TASKS.md` In Review entry?
also note the **placeholder abstract** (kinetic-theory-of-gases) and
acknowledgments `TODO(human:)` markers still need replacing before submission —
out of scope for this readability work but the #1 committee-skim issue.
