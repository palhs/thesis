# DAG-Based BFT Consensus

Decoupling data availability from ordering. DAG-based BFT answers the
Byzantine Generals Problem with a *structural* reorganisation rather
than a new voting scheme: observe that classical BFT cost is dominated
by (a) reliably disseminating transaction batches and (b) agreeing on
their order, and that entangling the two is the source of latency and
bandwidth inefficiency. Narwhal [11] separates data availability from
consensus by maintaining a reliably-broadcast DAG of transaction
batches; Bullshark [12] and Mysticeti [13] then derive a total order
*from the DAG* without additional communication in the common case.

DAG-based protocols occupy the high-throughput, asynchrony-tolerant
corner of the design space mapped in [[concepts/consensus-families]].
They retain deterministic finality and the `3f+1` threshold of
[[algorithms/pbft]], yet reach sustained throughput an order of
magnitude above classical BFT by letting block proposal and ordering
proceed in parallel rather than in lock-step. The cost paid is in
per-node storage and the depth of the pipeline before order is fixed.

## Family scope

Three representative protocols share the DAG-over-mempool idea; they
differ in how aggressively they elide explicit voting:

| Protocol | Source | Role |
| :---- | :---- | :---- |
| **Narwhal + Tusk** | Danezis et al., EuroSys 2022 [11] | Reference mempool + ordering — establishes the DAG + anchor-commit pattern. |
| **Bullshark** | Spiegelman et al., CCS 2022 [12] | Narwhal DAG + two-round fast path in synchrony; message-free async fallback. |
| **Mysticeti** | Babel et al., 2023 [13] | **Uncertified** DAG; implicit references replace the certification step; three-round theoretical lower bound. |

For this thesis the planned simulator target is simplified
**Narwhal + Tusk** (implementation task **T38.1**, currently Blocked —
see §Simulator mapping) — it is the clearest decomposition of the
two-layer structure and the easiest to align with the single-layer
simulators for
[[algorithms/pbft]], [[algorithms/pos]], and [[algorithms/avalanche]].
Bullshark and Mysticeti are retained above as family context.

## Model and assumptions

- **Synchrony.** None required for safety — see
  [[concepts/synchrony-models]]. Unlike PBFT, DAG-based protocols do
  *not* require a GST assumption for safety; asynchrony affects only
  the latency with which certificates are completed and anchors are
  committed. This is what the `Asynchronous` row in
  [[concepts/consensus-families]] encodes.
- **Fault model.** Up to `f < n/3` Byzantine validators
  ([[concepts/fault-model]]) — **identical to the PBFT family**, which
  is the structural surprise: the gains are architectural, not in
  threshold.
- **Reliable broadcast.** Every validator can eventually broadcast a
  block to all honest validators. Narwhal implements this via
  quorum-certificate signatures; Mysticeti replaces it with *implicit*
  DAG references.
- **Bounded per-validator storage.** Each validator keeps the DAG of
  the most recent rounds until they are committed; committed rounds
  can be pruned.
- **Authenticated channels.** Signatures authenticate each block; the
  certificate step relies on signature aggregation over `2f+1` replies.

## The DAG and its ordering

The architecture splits consensus into two conceptually independent
layers. The first constructs a DAG that everyone agrees exists; the
second derives a total order from that DAG.

### Narwhal — the DAG mempool

Time is partitioned into **rounds**. Per round, every validator
constructs a block (a *certificate of availability*) that references at
least `2f+1` blocks from the previous round. A block becomes a
certificate once the validator collects `2f+1` signatures attesting
availability of its contents. The resulting structure is a sequence of
rounds, each containing up to `n` certificates, with edges between
consecutive rounds representing parent references.

**Key property:** no ordering is decided at this stage — only
availability. The ordering problem is deferred to the next layer, and
that deferral is what allows parallel per-validator block construction.

### Tusk and Bullshark — zero-message ordering

On top of the Narwhal DAG, **Tusk** [11] derives a total order via a
deterministic leader schedule: every `r` rounds, a designated **anchor**
certificate is nominated; a validator commits the anchor (and thus a
total order on *all* its DAG ancestors) if a supermajority of
certificates in a subsequent round reference it. **Bullshark** [12]
refines this with a two-round fast path during synchronous periods and
a fall-back protocol for asynchrony — both require **no extra messages
beyond the DAG itself**.

### Mysticeti — uncertified DAGs for minimum latency

**Mysticeti** [13] removes the explicit certification step: blocks are
broadcast without waiting for `2f+1` signatures, and the DAG edges
themselves serve as implicit availability proofs. The commit rule is
strengthened so every block can in principle be committed without
delay, reaching the **three-round theoretical lower bound** for BFT
consensus. Mysticeti reports WAN latency of ~0.5 s for consensus commit
at throughput exceeding 200,000 transactions per second [13].

### DAG structure

```
  round r       round r+1      round r+2      round r+3
  [v1]----\     [v1]----\      [v1*]----\     [v1]
  [v2]-----\    [v2]-----\     [v2]------\    [v2]
  [v3]------+-> [v3]------+--> [v3]-------+-> [v3]
  [v4]-----/    [v4]-----/     [v4]------/    [v4]
                                ^
                                |
                anchor certificate v1* in round r+2:
                commit v1* iff >= 2f+1 certs in round r+3 reference it;
                total order derived from DAG ancestors of v1*.
```

## Safety argument

The quorum-intersection logic of [[concepts/quorum-arithmetic]] carries
over, but it is now applied at two points:

1. **Certificate formation.** A block becomes a certificate only after
   `2f+1` signatures attest its content. Equivocating content cannot
   reach certificate status because any two `2f+1` quorums in a `3f+1`
   set share at least `f+1` replicas, and an honest replica refuses to
   sign two different contents for the same `(validator, round)`.
2. **Anchor commitment.** An anchor commits only if `2f+1` certificates
   in a subsequent round reference it. Two conflicting anchors cannot
   both collect `2f+1` references by the same intersection argument.

Safety therefore holds **categorically up to `f < n/3`**, identically
to [[algorithms/pbft]], but independently of synchrony — the
combinatorial guarantee does not invoke any timing assumption.

## Behaviour under network delay

DAG-based protocols exhibit the most graceful degradation under delay
of any family in this thesis.

- **Slow validators delay only themselves.** Certificates form
  independently per validator and are simply *referenced* (not voted on)
  in later rounds. A slow validator delays only its own certificate —
  others fill their `2f+1` parent references from the certificates that
  *did* arrive in time. Throughput therefore declines **proportionally
  to the number of delayed validators**, not to the worst-case link in
  the network. Contrast: PBFT's commit latency grows with the tail of
  the link-delay distribution (see
  [[algorithms/pbft#behaviour-under-network-delay]]).
- **Pipeline depth is the only latency cost.** Commits follow anchors,
  and anchors are nominated only every few rounds. Bullshark and
  Mysticeti reduce this depth to two or three rounds in the common
  case. Under heavy asynchrony, repeated failures to commit an anchor
  push the pipeline deeper before consensus catches up — a latency
  spike, but not a throughput collapse.

## Behaviour under adversarial conditions

Three adversarial strategies are directly relevant and would concretise
as simulator behaviours once the protocol is built (the operational
taxonomy lives in [[concepts/adversary-model]]; Narwhal+Tusk's adversary
surfaces are catalogued there but deferred with T38.1).

- **Withholding.** Byzantine validators skip broadcasting their own
  certificates. As long as at least `2f+1` certificates per round are
  still produced, the DAG continues to advance and the order of
  committed transactions is unaffected — **throughput drops
  proportionally to the Byzantine fraction**, safety is untouched.
- **Equivocating broadcast.** Byzantine validators broadcast different
  block contents to different peers in the same round. Narwhal's
  certificate step — requiring `2f+1` signatures on a specific content
  hash — prevents any conflicting version from ever reaching
  certificate status. Mysticeti handles equivocation differently: by
  requiring multiple implicit references before commitment, it
  tolerates equivocation without a separate certificate step.
- **Anchor suppression.** Byzantine validators refuse to reference a
  specific honest anchor certificate. Provided at least `2f+1` honest
  validators *do* reference the anchor, commit still proceeds. If the
  adversary can suppress references at exactly the right rounds,
  commit is **delayed but not permanently prevented**.

Safety (no two honest validators commit different total orders)
follows from DAG determinism plus the `2f+1` anchor-reference rule.
Identical to PBFT, safety holds categorically up to the threshold and
is violable only above it.

## Communication complexity

| Protocol | Per-block msgs | Latency (rounds) | Throughput (reported) |
| :---- | :---- | :---- | :---- |
| **Narwhal + Tusk** [11] | `O(n)` certs + refs | ~5–7 to commit | ~140 ktps [11] |
| **Bullshark** [12] | `O(n)` (same DAG) | 2 (fast path) | ~125 ktps [12] |
| **Mysticeti** [13] | `O(n)` implicit refs | 3 (theoretical lower bound) | >200 ktps, ~0.5 s WAN [13] |

The structural advantage: **ordering adds no new message class on top
of the DAG itself** — the same messages that provide data availability
also provide the votes required for total order. Compared to PBFT's
`O(n²)` per-block quorum traffic (see
[[algorithms/pbft#communication-complexity]]), this reduces per-block
message count by an order of magnitude for large validator sets.

## Simulator mapping

**Status: not yet implemented.** Narwhal + Tusk is the one protocol in
this thesis's four-protocol scope that is *not* built. There is no
`src/narwhal_tusk/` package; the implementation task **T38.1 is
Blocked** (scheduled as the W10→W11 bridge — see
[[concepts/week7-decision]]), and the dependent Chapter 3 subsection
(T36.2) is Blocked behind it. The three implemented simulators are
[[algorithms/pbft]] (`src/pbft/`), [[algorithms/pos]] (Casper FFG,
`src/pos/`), and [[algorithms/avalanche]] (Snowman, `src/snowman/`).
This section therefore describes the **planned** mapping, not running
code; treat every claim below, and the Expected-findings hypotheses, as
a design target until T38.1 lands.

The planned implementation is a simplified **Narwhal-like mempool with a
Tusk-style commit rule**. Bullshark and Mysticeti are retained as family
context but are not planned simulator targets — they change the commit
rule without changing the DAG structure the experiments would exercise.

Knobs the implementation will expose (planned interface):

- **Round duration** — drives the delay-sensitivity profile; below
  round duration, validator delay is absorbed.
- **Certificate signature threshold** (default `2f+1`) — to probe how
  close to the threshold the DAG can operate before round formation
  stalls.
- **Anchor period** (`r` rounds, default `2` per
  [[concepts/metric-reconciliation]] §Calibration) — trades pipeline
  depth against commit-latency variance under adversarial anchor
  suppression.
- **Per-validator storage ceiling** — to expose the dual tradeoff
  against PBFT's per-block message cost.

Once built, this protocol would supply the fourth column of the
baseline/delay/adversarial comparison. The Weeks 8–10 experiment
batteries (T41–T56) ran on the three implemented protocols only, with
Narwhal+Tusk carried as explicit deferral rows.

## Expected findings

Hypotheses to evaluate in the results chapter **once Narwhal+Tusk is
implemented** (T38.1); the protocol does not yet appear in the Chapter 4
results:

- **Throughput is largely insensitive to delay up to the round
  duration** — degradation is graceful, not cliff-edge; the cleanest
  contrast with PBFT's quorum-stall behaviour.
- **Adversarial withholding reduces throughput proportionally to the
  Byzantine fraction** without endangering safety — the absence of any
  safety break inside the threshold is the structural payoff.
- **Anchor-suppression extends commit latency predictably** — the
  variance scales with anchor period, not delay.

## Weaknesses to foreground

- **Per-validator storage.** The DAG must be retained for many rounds
  before commit can prune it. This is the **dual tradeoff against
  PBFT's per-block message cost** — PBFT trades storage for messages,
  DAG-based protocols trade messages for storage.
- **Pipeline depth under heavy asynchrony.** When anchors repeatedly
  fail to commit, the pipeline extends and commit latency spikes. The
  protocol stays live but applications see long confirmation tails.
- **Reliable-broadcast dependency.** Narwhal's `2f+1`-signature
  certificate step is an explicit synchronous-ish operation; Mysticeti
  only works because implicit references collectively approximate
  reliable broadcast. Both collapse under network partitions that break
  quorum formation for extended periods.
- **Implementation complexity.** The two-layer split multiplies the
  number of protocol invariants an implementation must preserve —
  certificate formation, anchor commit, DAG pruning, per-round
  reference quotas, and rotation schedules all interact. This is why
  the planned simulator (T38.1) targets Narwhal + Tusk rather than
  Bullshark or Mysticeti.

## Sources

Citations `[11]`, `[12]`, `[13]` resolve via
[[concepts/annotated-bibliography]] to the dedicated source pages
[[sources/2026-04-21_danezis-narwhal-tusk-2022]],
[[sources/2026-04-21_spiegelman-bullshark-2022]], and
[[sources/2026-04-21_babel-mysticeti-2023]] respectively.

## Revisions

### [2026-06-22] Narwhal+Tusk is planned, not implemented (L-W10 finding H1)

The earlier version of this page (an early design page, T5/T6) described
Narwhal + Tusk in the present tense as a running simulator target: the
§Simulator-mapping section read "The implementation **is** a simplified
Narwhal-like mempool…" with experiment knobs that "feed … the
baseline/delay/adversarial experiment batteries in Weeks 8–10," and the
§Weaknesses close said "the simulator implements only Narwhal + Tusk." As
of the L-W10 wiki lint (2026-06-22) this is false: there is no
`src/narwhal_tusk/` package, the implementation task **T38.1 is Blocked**
(W10→W11 bridge, [[concepts/week7-decision]]), and the Weeks 8–10
experiments (T41–T56) ran on the three *implemented* protocols only
(PBFT, Casper FFG, Snowman), carrying Narwhal+Tusk as explicit deferral
rows. The §Simulator-mapping, §Behaviour-under-adversarial-conditions,
§Expected-findings, and §Weaknesses sections were reframed to mark the
mapping as **planned**, mirroring the
[[algorithms/pos]] §Simulator-mapping "Not implemented (deferred)"
pattern. The algorithm description (the DAG/Narwhal/Tusk/Bullshark/
Mysticeti mechanics) is unchanged — it was, and remains, accurate
reference material. No code or experiment is affected; this is a
documentation-honesty correction. When T38.1 lands it should add an
"Implemented" subsection and revise this note.
