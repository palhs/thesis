# PBFT-Family Consensus

Deterministic BFT under partial synchrony. The PBFT family answers the
[[concepts/byzantine-generals]] problem by stabilising a three-phase commit
behind a rotating primary; after a Global Stabilisation Time (GST) the
protocol terminates in bounded rounds. It is the safety-first corner of the
design space mapped in [[concepts/consensus-families]] and serves as the
baseline in this thesis against probabilistic ([[algorithms/avalanche]]) and
DAG-based ([[algorithms/dag-based]]) families.

## Family scope

Three representative protocols share the same skeleton (leader proposes;
`3f+1` replicas vote in disciplined phases; view change recovers liveness)
but make different cost tradeoffs:

| Protocol | Source | Key change vs. classical PBFT |
| :---- | :---- | :---- |
| **PBFT** | Castro & Liskov, OSDI 1999 [4] | Original three-phase commit; `O(n²)` normal, `O(n³)` view change. |
| **Tendermint** | Buchman, Kwon & Milosevic, 2018 [6] | Round-robin primaries; `O(n²)` view change; deployed in Cosmos SDK. |
| **HotStuff** | Yin et al., PODC 2019 [5] | Linearised view change `O(n)` via threshold signatures; phases pipelined across consecutive blocks. |

## Model and assumptions

- **Synchrony.** Partial synchrony — see [[concepts/synchrony-models]]. The
  network may be arbitrarily slow before an unknown GST, after which message
  delivery is bounded by some `Δ`. Safety holds at all times; liveness holds
  only after GST.
- **Fault model.** Up to `f` of `n = 3f+1` replicas are Byzantine
  ([[concepts/fault-model]]); the rest follow the protocol. Collusion,
  equivocation, and arbitrary message forgery are all in scope.
- **Channels.** Authenticated and signed; forgery is computationally
  infeasible, so every recipient can verify the source of every message.
- **Validator set.** Fixed within a view. Rotation, where it exists, occurs
  only at epoch boundaries (in PoS variants) or is out of scope (classical
  PBFT).

## Three-phase commit

PBFT operates in a sequence of **views**, each led by a designated
**primary** replica. Within a view, every client request traverses three
message phases before commit.

### Pre-prepare

The primary assigns a sequence number to the request and multicasts a
`PRE-PREPARE(view, seq, request)` to all replicas.

### Prepare

Each replica that accepts the pre-prepare multicasts a
`PREPARE(view, seq, digest)`. A replica is **prepared** for the request
when it has collected `2f` matching `PREPARE` messages plus the original
pre-prepare — i.e. a quorum of `2f+1`.

### Commit

Each prepared replica multicasts `COMMIT(view, seq, digest)`. On receiving
`2f+1` matching commits it executes the request and replies to the client.
The client accepts the result once it has `f+1` matching replies.

### Message flow (n=4, f=1)

```
Client     Primary (R0)    R1          R2          R3
  |            |            |           |           |
  |--request-->|            |           |           |
  |            |--pre-prep->|---------->|---------->|   # Pre-Prepare
  |            |            |           |           |
  |            |<--prepare--|<----------|<----------|
  |            |--prepare-->|---------->|---------->|   # Prepare   (2f+1)
  |            |            |           |           |
  |            |<--commit---|<----------|<----------|
  |            |--commit--->|---------->|---------->|   # Commit    (2f+1)
  |            |            |           |           |
  |<-----reply (f+1 matching)-----------|-----------|
```

## Safety argument

The two-round quorum structure is what gives PBFT its safety guarantee. The
full derivation lives in [[concepts/quorum-arithmetic]]; the summary:

- Any two quorums of size `2f+1` in a `3f+1` replica set intersect in at
  least `f+1` replicas.
- At most `f` of those can be Byzantine, so at least one honest replica
  sits in the intersection.
- An honest replica refuses to prepare a second value for the same
  `(view, seq)`; hence two conflicting values cannot both collect `2f+1`
  prepares — i.e. Agreement (see [[concepts/consensus-properties]]) is
  preserved across any two commits at the same sequence number.

Safety is independent of synchrony: it holds under arbitrary message delay,
loss, or reordering. Only liveness depends on GST.

## View change

View change is PBFT's liveness-recovery mechanism — the cost the family
pays for handling a faulty or stalled primary.

- **Trigger.** A replica that has not observed progress before its local
  timeout broadcasts `VIEW-CHANGE(v+1, evidence)` where `evidence`
  contains the most recent prepared requests it can prove.
- **Mechanism.** The next primary waits for `2f+1` matching `VIEW-CHANGE`
  messages, then broadcasts `NEW-VIEW(v+1, proofs)` re-anchoring every
  prepared-but-not-committed request. Replicas replay those requests in
  the new view and the three-phase commit resumes.
- **Cost.** `O(n³)` messages in classical PBFT — the single most expensive
  operation in the protocol. HotStuff reduces this to `O(n)` by attaching
  threshold signatures to each evidence slot [5]; Tendermint keeps view
  change at `O(n²)` but makes it cheap by rotating primaries round-robin
  so no single replica is structurally privileged [6].

## Behaviour under network delay

Delay affects PBFT along two dimensions.

- **Quorum stall.** Because each phase requires synchronous collection of
  `2f+1` messages, a single slow link at the tail of the delay distribution
  is enough to stall an entire block. End-to-end commit latency grows
  linearly with the 67th-percentile link delay, not the mean.
- **Spurious view change.** If delay exceeds the view-change timeout,
  replicas initiate a view change even when the primary is honest. The
  wasted `O(n²)`–`O(n³)` traffic suppresses throughput under bursty delay.

HotStuff mitigates the first problem by pipelining phases (each phase is a
vote on the next block, so three in-flight blocks amortise the three-round
latency) and the second by linearising view change. Tendermint mitigates
the second via round-robin rotation. The thesis simulator does not
implement these variants (see §Simulator mapping); it measures classical
PBFT directly and uses view-change timeout as the primary knob against
delay variance.

## Behaviour under adversarial conditions

Within the `f < n/3` threshold, safety holds unconditionally. Liveness —
not safety — is the pressure point an adversary can exploit. Three
strategies matter for the simulator (and are concretised as operational
adversary types in [[concepts/adversary-model]], pending T18).

- **Silent non-participation.** Byzantine replicas abstain from voting,
  forcing honest replicas to wait the full timeout before initiating a
  view change. Inflates latency; does not violate safety.
- **Equivocating primary.** A Byzantine primary sends conflicting
  `PRE-PREPARE`s to disjoint subsets. Detected at the PREPARE phase — no
  `2f+1` quorum ever forms for conflicting values — triggering a view
  change. Adversary gain: a liveness stall, not a safety break.
- **Delayed voting.** Byzantine replicas wait until the last moment to
  send `PREPARE` and `COMMIT`. Every quorum round stretches to the
  Byzantine schedule; throughput degrades even though correctness is
  preserved.

**Threshold break.** When the actual Byzantine count exceeds `f = ⌊(n−1)/3⌋`
the quorum-intersection argument fails — but not by making quorums disjoint.
Any two `2f+1` quorums in a `3f+1` set still intersect in at least `f+1`
replicas. What fails at the threshold is the *honest-vetoer* guarantee: the
intersection can now be entirely Byzantine, and equivocators in it vote for
both conflicting values. Two values each collect `2f+1` prepares with no
honest replica vetoing either. This distinction fixes how the safety-
violation detector in T55 must work: look for equivocation surviving the
intersection, not for disjoint quorums.

## Communication complexity

| Protocol | Normal-case per block | View change | Latency (rounds) |
| :---- | :---- | :---- | :---- |
| **PBFT** [4] | `O(n²)` | `O(n³)` | 3 |
| **Tendermint** [6] | `O(n²)` | `O(n²)` | 3 |
| **HotStuff** [5] | `O(n)` | `O(n)` | 3 (pipelined) |

The trend is a progressive reduction in message complexity via threshold
signatures (single aggregated vote instead of `n` individual votes) and
pipelining (overlapping phases across consecutive blocks). The simulator
reports per-block message count directly so that protocols can be compared
under identical workloads.

## Simulator mapping

Only the classical PBFT variant is implemented — single primary, no
pipelining, no threshold signatures. HotStuff and Tendermint are retained
above as family context, not as simulator targets. The planned
implementation exposes two knobs:

- **View-change timeout** — to measure spurious view-change frequency
  under delay variance; target of the adaptive-timeout enhancement in T57.
- **Byzantine fraction** — to probe the threshold break (safety holds
  while `f < n/3`; equivocation-surviving-intersection failures begin
  above it, as described in §Behaviour under adversarial conditions).

These feed T28–T31 (PBFT implementation and correctness tests) and the
baseline/delay/adversarial experiment batteries in Weeks 8–10.

**Trusted view-change evidence — modeling boundary.** The simulator
carries no signatures (digests serve message integrity and deterministic
replay only); the authenticated-channels assumption of §Model and
assumptions is extended here to cover *evidence content*. A `VIEW-CHANGE`
message's prepared evidence is a plain assertion, not a cryptographic
prepared certificate (`PRE-PREPARE` plus `2f` signed `PREPARE`s), so a
Byzantine replica can fabricate it and the new primary's reissue
computation will trust it. Within-threshold *safety against forged
view-change evidence* is therefore assumed by construction, not
demonstrated, and the adversary catalog ([[concepts/adversary-model]])
deliberately carries no evidence-forgery capability. The boundary does
**not** affect the results that are genuinely exercised: honest-node
correctness, liveness behaviour, and the equivocating-*primary* attack
(conflicting `PRE-PREPARE`, detected at the prepare quorum) are all
unaffected.

## Expected findings

Hypotheses to evaluate in the results chapter:

- Safety is maintained across the full `f < n/3` range; equivocation
  appears only once the Byzantine fraction crosses the threshold. Within
  the trusted view-change-evidence boundary in §Simulator mapping, the
  equivocating-primary case is demonstrated; evidence-forgery is not.
- Throughput degrades sharply as delay variance increases, not mean delay.
- View-change frequency dominates throughput loss under adversarial delay.

## Weaknesses to foreground

- **Quadratic-or-worse messaging** limits practical validator count in the
  classical variant; mitigated by HotStuff but at the cost of threshold
  signature setup and reliance on timely leader rotation.
- **Primary-bound liveness.** A long sequence of faulty-or-slow primaries
  can delay progress indefinitely; each recovery costs a view change.
- **Timeout calibration is load-bearing.** Timeouts too short → spurious
  view changes; too long → adversarial stalls go unpunished. This makes
  adaptive timeout (T57) a natural enhancement target.

## Sources

Citations `[4]`, `[5]`, `[6]` resolve via
[[concepts/annotated-bibliography]] to the dedicated source pages
[[sources/2026-04-21_castro-liskov-pbft-1999]],
[[sources/2026-04-21_yin-hotstuff-2019]], and
[[sources/2026-04-21_buchman-tendermint-2018]] respectively.
