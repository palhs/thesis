# Q&A prep — thesis defense

Companion to `defense-script.md` (its header points here; the script holds
only the 15-minute talk). Format per entry: expected question → ~30-second
spoken answer → what to point at → verify-before-quoting notes.

---

## Q1 · "PBFT has view-change — what do Casper FFG and Snowman do when they stall?"

*Trigger: S5 view-change vignette + the S5 spec-strip `recovery` field, or
the S8-loss ranking. A sharp committee will also connect S2 (Ethereum's
05/2023 finality stall RECOVERED on mainnet) with the FFG "recovery none"
label and probe the apparent contradiction.*

**Spoken answer (~30 s):**

> Three different recovery philosophies. PBFT rotates the faulty **role** —
> a timer fires, view-change elects a new leader, the round replays; that is
> a structural recovery measured in rounds. Casper FFG, as specified in the
> 2017 paper's core gadget and as I simulate it, has none — a missed
> checkpoint simply waits for the next epoch, and if two-thirds of stake is
> genuinely gone the chain stalls indefinitely. Production Gasper adds an
> **economic** repair the paper sketches in its discussion section: the
> inactivity leak — validators that stop voting bleed stake until the active
> set regains its two-thirds, which is how Ethereum mainnet exits real
> stalls. That mechanism is outside my simulation scope, and I list it under
> simplified implementations. Snowman's recovery is **implicit**: every poll
> round is a fresh random sample, so it is already an endless retry and
> self-heals the moment conditions improve — but it has no timer, no role to
> rotate, and no way to force progress while the fault persists, which is
> exactly the plateau-then-cliff in the loss results.

One-line close (ties to S9): *rotate the role · bleed the absentees ·
resample and wait — the recovery style mirrors each family's design choice.*

**Point at:** S5's mouse-only **Recovery ▸ Q&A** chip (4th chip, dashed
border — a three-panel visual built for exactly this question: rotate the
role / bleed the absentees / resample and wait, with the leak's safety cost
in red). Also: S5 PBFT beat 4 (vignette), the three spec-strip `recovery`
fields, S8 Loss tab for the consequence, S11 for the scope boundary. The
chip is not in the Space order — it opens only by mouse click, so the
15-minute talk never touches it.

**If pressed further ("doesn't the leak fix FFG's weakness?"):**

> The leak is itself the thesis's central finding replayed: it buys
> liveness recovery by weakening accountable safety. The paper's own §4.2
> shows that under a partition both sides leak each other's deposits, each
> side reaches a supermajority, and **two conflicting checkpoints finalize
> with no validator slashed** (its Figure 6). Recovery mechanisms are not
> free in this family either — the currency is just accountability instead
> of messages.

**Grounding — verified 2026-07-15 against `raw/casper.pdf`:**
- Simulated behaviour: `drafts/ch4_results.md` §4.3 ("PBFT has a genuine
  recovery path … Snowman has in-round redundancy but no cross-round
  recovery … Casper FFG has neither").
- Inactivity leak: [7] Buterin & Griffith 2017, **§4.2 "Catastrophic
  Crashes" (p. 8)** — "recover … by instituting an 'inactivity leak' which
  slowly drains the deposit of any validator that does not vote … until …
  the validators who are voting are a supermajority"; simplest formula:
  per missed epoch a validator loses `D·p`. The **Conclusions (p. 9)** list
  the leak as an *extension* to Casper, not the core gadget — so the S5
  spec-strip "recovery: none" is correct for the simulated core protocol.
- Leak-weakens-accountability: same §4.2 — two conflicting finalized
  checkpoints, no slashing, validators "should simply favor whatever
  finalized checkpoint [they] saw first" (paper's Figure 6).
- Wiki-backed since 2026-07-15: `wiki/algorithms/pos.md` carries the leak
  under "Not implemented (deferred)" with the same section/page references.
- 05/2023 stall specifics: the leak activated during the incident but the
  stall also ended via client fixes — say "the leak is the in-protocol
  part of how mainnet recovers", do not attribute that incident's end to
  the leak alone.
