# Avalanche-Family Consensus

BFT via repeated random subsampling. Avalanche departs from the
quorum-based reasoning of [[algorithms/pbft]] and [[algorithms/pos]]:
rather than collecting a supermajority, each validator repeatedly polls a
small random sample of peers and accumulates confidence over many short
rounds. The family — Slush → Snowflake → Snowball → Avalanche — was
introduced by "Team Rocket" (Rocket, Yin, Sekniqi, van Renesse, Sirer)
and later formalised at Cornell [1]; it is deployed in production as the
Avalanche network's consensus layer, where a linearised variant called
**Snowman** replaced the original DAG protocol on all three primary
chains (C-Chain, P-Chain, and — since the Cortina upgrade in April 2023
— X-Chain) [3]. Subsequent formal analysis [2] sharpens the resilience
claims and tightens the adversary model.

Avalanche occupies the probabilistic, no-quorum corner of the design
space mapped in [[concepts/consensus-families]]. Its defining tradeoff:
**no single round is a quorum**, but the probability that all honest
validators converge on the same value grows exponentially in the number
of rounds. Finality is statistical — any desired `1 − ε` is reachable by
parameter tuning rather than by waiting for deterministic events. This
is the `A` corner of [[concepts/cap-theorem]].

## Family scope

Four protocols share the subsampling kernel; the production variant is
a fifth layer on top:

| Protocol | Source | Role |
| :---- | :---- | :---- |
| **Slush** | [1] | Minimal subsampling; flip colour if `α`-of-`k` disagree. |
| **Snowflake** | [1] | Slush + consecutive-agreement counter `β` before deciding. |
| **Snowball** | [1] | Snowflake + persistent preference informed by all prior `α`-majorities. |
| **Avalanche** | [1] | Snowball lifted onto a DAG of conflicting transactions. |
| **Snowman** | [3] | Linearised production variant; Snowball engine on a totally-ordered chain. Operates on C-Chain, P-Chain, and post-Cortina X-Chain. |

For this thesis Snowman is the production reference point (because its
chain structure is directly comparable to PBFT and PoS-finality);
DAG-Avalanche [1] remains the canonical theoretical object and the
target of the formal analyses in [1] and [2].

## Model and assumptions

- **Synchrony.** None required for safety — see [[concepts/synchrony-models]].
  The statistical argument holds under adversarial message delay, at the
  cost of extended time to accumulate `β` consecutive agreements. This is
  what the `Asynchronous / probabilistic` row in
  [[concepts/consensus-families]] encodes.
- **Fault model.** A fixed Byzantine fraction of validators
  ([[concepts/fault-model]]). The safe fraction is parameter-dependent,
  *not* a fixed `1/3` — for production parameters (`K=20`,
  `α_c ≈ 0.8K`, `β ≈ 15`) the safety-violation probability stays
  negligible while the Byzantine fraction remains well below the
  critical threshold [3]. Formal bounds under various adversary models
  live in [1] and [2].
- **Random peer sampling.** Each validator samples uniformly at random
  from a reasonably-known peer set without persistent bias. Sybil
  resistance is **external** — on AVAX it is stake-weighted sampling.
- **Probabilistic finality.** A value is accepted when its confidence
  exceeds a threshold; the probability of later reversal decays
  exponentially in `β`. There is no hard finality — only a tunable `ε`.
- **Global parameters.** `K`, `α_p`, `α_c`, `β` are network-wide.
  Heterogeneous parameters cause consensus failures [3]; the simulator
  respects this constraint.

## The subsampling cascade

The four family members build on each other. Only the last two are
candidate simulator targets; the first two are presented as the
conceptual scaffold.

### Slush — the primitive

Each validator holds a colour. Per round:

1. Pick `k` peers uniformly at random.
2. Query their colour.
3. If `α`-of-`k` responses agree on a colour different from the
   validator's own, flip.

After `m` rounds the validator outputs its current colour.

### Snowflake — consecutive agreement

Adds a counter. A validator only decides a colour after `β` consecutive
rounds of `α`-majority agreement on that colour. Every flip resets the
counter. Eliminates premature commitment from transient noise.

### Snowball — persistent preference

Adds a preference informed by *all* historical `α`-majority observations,
not just the consecutive streak. Preference updates whenever an
`α`-majority forms, independently of the counter. Exploits information
Snowflake discards on flip.

### Avalanche — DAG-ordered Snowball

Generalises Snowball from binary colours to an arbitrary DAG of
conflicting transactions. When polled about transaction `T`, a
validator replies with the consistent subset of its DAG that includes
`T`. `T`'s confidence grows whenever it is included in an `α`-majority
reply; `T` is accepted when confidence exceeds `β`. Conflicts resolve
via Snowball on the contested vertex.

### Snowman — linearised production

Same Snowball engine, operating on a totally-ordered chain instead of a
DAG. The deployed variant [3]. The official documentation splits what
the original paper called `α` into two thresholds:

- **`AlphaPreference` (`α_p`)** — sample-majority threshold that
  *switches the validator's preference*.
- **`AlphaConfidence` (`α_c`)** — sample-majority threshold that
  *increments the decision counter*.

In the original Snowball these were equal. The production decoupling
lets preference volatility and finality probability be tuned
independently [3].

### Sampling round

```
                    validator v
                         |
       random sample of k peers  (k small, e.g. 20)
          /     |     |     ...    |     \
         p1    p2    p3           pk-1    pk
          \     |     |     ...    |     /
             count responses for colour c
                         |
       if count >= α_p  ->  update preference
       if count >= α_c  ->  increment confidence counter
       if counter >= β  ->  ACCEPT c
```

## Probabilistic safety

The Avalanche documentation states the safety-violation probability for
two honest validators accepting conflicting blocks as [3]:

```
  P(safety violation)  <  ( 1 − α_c / K ) ^ β
```

Exponential in `β`. Finality approaches `1 − ε` for arbitrarily small
`ε` as `β` grows — the production defaults drive `ε` well below
operationally observable thresholds, which is the basis for the "sub-
second, immutable" finality claim in [3].

Unlike PBFT's deterministic safety derived from the `3f+1` quorum
intersection (see [[concepts/quorum-arithmetic]]), Avalanche's safety is
a **parameterised statistical property**. The thesis simulator samples
empirical `ε` by counting violations across many seeds and compares the
empirical curve against this theoretical bound. This is the Avalanche
analogue of the accountable-safety check in [[algorithms/pos]] — the
guarantee is real, but its *shape* is probability, not categoricity.

## Behaviour under network delay

Avalanche degrades gracefully under delay. Two effects to distinguish:

- **Per-round latency is tail-insensitive.** A round samples only `k`
  peers (typically `≤ 10%` of the network) and completes once the first
  `k` responses return. Slow peers do not influence the round; end-to-
  end latency grows roughly linearly with delay, not super-linearly as
  in quorum-based protocols where the slowest member of `2f+1`
  determines round completion.
- **Per-round variance grows.** Under heavy delay, sampled peers may
  not yet have the latest transaction and reply "don't know" — which
  cannot contribute to the `α`-majority. Finality stalls without a
  safety risk.

The recent formal analysis [2] showed that in worst-case asynchrony the
protocol can experience extended periods of liveness degradation that
were underestimated in the original informal treatment [1]. The
simulator probes this gap by injecting heavy asynchronous delay and
measuring time-to-accept at high Byzantine fractions.

## Behaviour under adversarial conditions

Because every round samples freshly at random, the adversary cannot
persistently bias a single validator's view. The strongest strategies
are statistical, not structural (the operational taxonomy lives in
[[concepts/adversary-model]], pending T18).

- **Selective response.** Byzantine validators reply with whichever
  colour is opposite the honest majority. Effect: subtracts
  approximately the Byzantine fraction from the `α`-majority signal.
  Safety holds so long as the honest fraction of a random sample
  exceeds `α_c` with high probability.
- **Adaptive colour flipping.** Byzantine validators coordinate to
  flip reported colour each round to maximise variance in honest
  validators' preferences. Delays but does not prevent convergence.
- **Sample-partitioning.** The adversary attempts to split honest
  validators into two preference clusters that each see only their own
  preference in sampled replies. Bounded in [1]; [2] refines these
  bounds under stronger network adversaries.

Unlike PBFT, safety in Avalanche is **probabilistic rather than
categorical**: there exists a non-zero probability that an adversarial
coincidence produces a safety violation, but this probability is driven
below any target `ε` by sufficiently many rounds.

## Parameters and communication complexity

Four production parameters drive the whole protocol [3]:

| Parameter | Role | Typical | Cost impact |
| :---- | :---- | :---- | :---- |
| **`K` (sample size)** | Peers queried per poll | 20 | `O(K)` msgs / round / validator |
| **`α_p` (AlphaPreference)** | Preference-flip threshold | `⌊K/2⌋ + 1` | Lower → faster convergence; higher → stabler preference |
| **`α_c` (AlphaConfidence)** | Counter-increment threshold | `~0.8·K` | Directly drives safety-violation probability (bound above) |
| **`β` (Beta)** | Consecutive `α_c`-majorities required | 15–20 | Linear in latency, **exponential in safety** |

Per-validator message complexity is `O(K · β)` in the common case,
**independent of `n`**. This is the architectural reason Avalanche
scales to thousands of validators without per-block traffic blow-up —
and the direct contrast with PBFT's `O(n²)` per-block cost (see
[[algorithms/pbft#communication-complexity]]).

## Simulator mapping

The thesis implements a simplified **Snowman** variant (the linearised
production form in [3]) exposing `K`, `α_p`, `α_c`, `β`, and the
random-sampling seed as first-class experiment parameters. Full
DAG-Avalanche is out of scope — Snowman keeps the implementation
directly comparable to PBFT, PoS-finality, and DAG-based protocols
under the same Validator interface.

Knobs exposed to experiments:

- **`K`, `α_p`, `α_c`, `β`** — the four subsampling parameters above.
- **Random-sampling seed** — reproducibility + empirical-`ε` studies.
- **Byzantine fraction + strategy** — selective response, adaptive
  flip, sample-partitioning (see §Behaviour under adversarial
  conditions).

These feed T37–T40 (third-algorithm implementation) and the
baseline/delay/adversarial experiment batteries in Weeks 8–10.

## Expected findings

Hypotheses to evaluate in the results chapter:

- **Time-to-finality is essentially invariant to `n`**, holding `K`
  and `β` fixed — matching the sub-second production claim [3] and
  directly contrasting with PBFT's `O(n²)`.
- **Empirical safety-violation rate matches `(1 − α_c/K)^β`** at low
  Byzantine fractions and diverges predictably as the adversary
  approaches the parameter-dependent critical threshold.
- **Under heavy delay, correctness holds but finality latency grows**,
  while quorum-based protocols stall outright — the performance
  baseline against which PBFT and PoS-finality are compared.

## Weaknesses to foreground

- **Probabilistic finality.** No hard commitment; applications must
  choose an operational `ε` and accept that some catastrophic tail
  exists. For the thesis this is a recorded feature of the design
  space, not a defect — but it affects how "finality" can be reported
  across algorithms in a comparative table.
- **Parameter sensitivity is load-bearing.** `(K, α_p, α_c, β)` must
  be chosen globally and together; poor choices can erode `ε` by
  orders of magnitude without visibly breaking the protocol. The
  simulator treats parameter sweeps as a first-class experiment.
- **Sybil resistance is external.** Random sampling assumes an honest
  peer distribution; the protocol itself does not establish one.
  Production systems graft stake-weighted sampling [3] onto this.
- **Async-liveness gap.** [2] shows the original informal claims
  under asynchrony were optimistic. The simulator surfaces this by
  measuring time-to-accept under worst-case asynchronous adversaries.

## Sources

- [1] Team Rocket, M. Yin, K. Sekniqi, R. van Renesse, and E. G. Sirer,
  "Scalable and Probabilistic Leaderless BFT Consensus through
  Metastability," arXiv:1906.08936, 2019.
- [2] I. Amores-Sesar, C. Cachin, and P. Schneider, "An Analysis of
  Avalanche Consensus," arXiv:2401.02811, 2024.
- [3] Ava Labs, "Consensus Protocols — Avalanche Builder Hub," official
  documentation, `build.avax.network/docs/nodes/architecture/consensus`
  (accessed Apr. 2026).

Dedicated `wiki/sources/` pages for [1]–[3] will be created under T8
(annotated bibliography). Citations are carried inline here in the
interim.
