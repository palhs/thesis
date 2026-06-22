# Chapter 5 — Synthesis

## 5.1 Chapter roadmap

Chapter 4 closed on a question it had assembled but deliberately did not answer.
Each of its three movements isolated one stress axis and reported how the
protocols behaved under it: validator-set size in the baseline, network delay in
the second sweep, and adversarial behavior in the third. Read separately, each
sweep produced a clear per-axis verdict. Read together, they raise the question
this chapter takes up — whether any one family occupies a dominant position once
the baseline, delay, and adversarial regimes are considered jointly, the
Pareto-frontier synthesis of RQ5 [[wiki/concepts/research-questions]].

RQ5 asks whether a consistent Pareto frontier of the performance–security
tradeoff exists across the families and whether any family dominates the others
across all operating regimes [[wiki/concepts/research-questions]]. The frontier
reported here is traced over the three protocols evaluated throughout this study:
PBFT, Casper FFG, and Snowman. This chapter introduces no new measurements; it
collates the per-axis results of Chapter 4 into a single comparison and reads the
shape of the tradeoff off them, drawing on the consolidated findings of
[[wiki/concepts/key-findings]].

The answer is that no family dominates. Each of the three protocols is the strict
best on at least one axis that no other matches, so each is a non-dominated point
on the frontier; and the frontier itself has a definite shape: no configuration
is at once cheap, fast, and resilient. The contribution of the
synthesis is therefore not the bare no-dominance verdict, which a reader of the
design space might anticipate, but the map of which structural choice places each
family where on the frontier, and the inversions that map reveals.

## 5.2 The comparison and its axes

A synthesis over heterogeneous sweeps requires a common frame. The frame used
here is the performance–security plane: each protocol is characterized by its
position on a set of axes drawn from the three sweeps, and one family is said to
dominate another when it is no worse on every axis and strictly better on at
least one. A family that no other dominates lies on the Pareto frontier. The
axes are the quantities Chapter 4 already reports: baseline commit latency and
communication overhead from the scaling sweep, time-to-finality under network
delay and finalization under packet loss from the delay sweep, and liveness and
safety under each adversarial strategy from the adversarial sweep. The synthesis
adds a reading, not a measurement. These axes are the primary metrics of the four
data-generating research questions rather than a set chosen to make the families
differ, so a family that dominated would do so on the very quantities the
evaluation was designed to measure.

Two conventions fixed in Chapter 3 and carried through Chapter 4 govern the
comparison and are restated because the reading rests on them. Cross-protocol
latency is read from `commit_latency_ms`, the canonical time-to-finality column,
so that the three protocols' irreversibility milestones are compared like for
like [[wiki/concepts/output-format]]; cross-protocol throughput is read from
`goodput`, the rate of committed transaction bytes, rather than from the
protocol-granularity decision-event rate [[wiki/concepts/evaluation-metrics]].
Every comparative verdict below inherits one further qualification: the simulator
charges network latency but no signature-verification or other compute cost, so
cost and per-validator comparisons flatter the protocols whose equivocation
handling is compute-bound, namely PBFT and Casper FFG, while the message-count,
liveness, and safety verdicts are unaffected [[wiki/concepts/network-model]].

## 5.3 Where each family sits on the frontier

### 5.3.1 PBFT: fast and live, but the fork is unaccountable

PBFT occupies the low-latency, high-liveness corner of the frontier. At the
honest baseline it commits in approximately one second, level with Snowman and
about five times faster than Casper FFG's epoch-granularity finality of roughly
five seconds, and its latency is flat in the validator set
[[wiki/experiments/2026-06-03_scaling-baseline]] [[wiki/concepts/key-findings]].
Its communication overhead grows linearly per committed unit, at approximately
`2n` messages, the atomic-commit-unit denominator absorbing one factor of the
all-to-all `O(n²)` instance cost [[wiki/experiments/2026-06-08_baseline-cis]].
Under network delay it is the least exposed of the three, adding about
nine-tenths of a second under moderate uniform delay where Snowman pays an order
of magnitude [[wiki/experiments/2026-06-13_delay-analysis]]. It is the most
loss-resilient protocol, the only one still finalizing at twenty-percent packet
loss, ranked first by area under the finalization-rate curve at `n = 10` and tied
for first at `n = 25` [[wiki/experiments/2026-06-13_delay-comparison]]. Against
the two liveness adversaries it is the strongest of the three — immune to delayed
voting at unit finality cost and undegraded under silent non-participation through
`φ = 0.33`, collapsing only at `φ = 0.40`, the first sampled fraction past its
`2f+1` quorum bound [[wiki/experiments/2026-06-19_adversary-comparison]]. These
liveness verdicts are established against adversaries that leave the view-0
primary honest; the leader-disruption surface, plausibly the sharpest attack on a
leader-based protocol, is catalogued but not measured, so PBFT's liveness standing
is bounded to non-leader-targeting strategies [[wiki/concepts/adversary-model]].

The mechanism that buys this liveness is the one that disqualifies PBFT on the
axis it loses. Its leader-based, exact-quorum commit rule recovers from a stalled
or slow leader by view-change rotation, which is why it survives delay, loss, and
silence; but that commit rule is non-accountable, and under equivocation past the
fault threshold it produces a deterministic fork — 229 conflicting committed
instances at `φ = 0.40` — with no slashable evidence identifying the equivocators
[[wiki/experiments/2026-06-19_adversarial-degradation]]. View-change activity
makes the double edge visible: the mechanism fires for successful recovery at
fractions up to one-third and degenerates into thrashing above it
[[wiki/concepts/key-findings]]. PBFT is thus the performance and liveness leader
of the three and at the same time the only family whose safety failure is both
certain above the threshold and unattributable [[wiki/algorithms/pbft]].

### 5.3.2 Casper FFG: never fastest, but the only accountable failure

Casper FFG wins no latency or resilience axis outright, yet it is non-dominated on
two counts. The first is cost: per committed unit it is the cheapest of the three,
at approximately `1.2n` messages against PBFT's `2n` and far below Snowman's
polling overhead [[wiki/experiments/2026-06-08_baseline-cis]]. On the latency and
resilience axes, by contrast, it trails. It is the slowest of the three at the
baseline, finalizing at epoch granularity in roughly five seconds, and the lowest
in honest goodput [[wiki/experiments/2026-06-03_scaling-baseline]]. It is the least loss-resilient,
ranked last by area under the finalization-rate curve at both committee sizes and
the first to fall silent under packet loss
[[wiki/experiments/2026-06-13_delay-comparison]]. Under silence it degrades
gracefully, its sustained throughput falling in proportion to the participating
stake, approximately `1 − φ`, and surviving to `φ = 0.33`
[[wiki/experiments/2026-06-19_adversary-comparison]].

The second count appears on the equivocation axis. Where PBFT forks
without attribution, Casper FFG's slashing conditions convert an equivocation
into accountable evidence: at `φ = 0.40` the protocol holds with no in-model fork
while exposing a slashable stake fraction at or above one-third
[[wiki/experiments/2026-06-19_adversarial-degradation]]. No other family in the
study offers an accountable safety failure, and that is the corner of the
frontier Casper FFG occupies alone [[wiki/algorithms/pos]]. The cost it pays is
concentrated on liveness under loss, and that cost is the measured analogue of
the failure that motivated this study: an epoch whose attestations fail to reach
a quorum — dropped by a lossy network here, delayed under attestation-processing
pressure in Ethereum's multi-epoch finality stall of May 2023 there — leaves
finality stalled, the same class of failure observed in deployment
[[wiki/algorithms/pos]].

### 5.3.3 Snowman: safest under equivocation, costliest under delay

Snowman occupies a corner defined by a single mechanism pulling in opposite
directions on different axes. Its `K`-peer subsampling gives it the strongest
safety posture against equivocation of the three: it presents no fork surface,
and its probabilistic safety bound is vanishing, with an analytical `ε` near
`5 × 10⁻¹⁵` at `n = 10`
[[wiki/experiments/2026-06-19_adversarial-degradation]]. That bound is reported
rather than empirically witnessed; an empirical fork count of zero at the
baseline confidence depth is a non-witness of the bound, not a confirmation of it
[[wiki/concepts/output-format]]. On the light-loss plateau at `n = 25` it retains
the highest finalization rate of the three — 0.904 at five-percent loss against
PBFT's 0.533 — the redundancy of its polling scaling with the committee
[[wiki/experiments/2026-06-13_delay-comparison]].

The same subsampling makes it the costliest protocol under delay and the most
fragile under silence. Because acceptance requires `β` sequential polling rounds
and each round waits on the slowest of `K` sampled peers, delay compounds: under
moderate uniform delay Snowman's time-to-finality grows roughly twelve- to
thirteenfold, against a fraction of that for the other two, and under a
delayed-voting adversary its finality cost reaches a factor of sixty-two
[[wiki/experiments/2026-06-13_delay-analysis]]
[[wiki/experiments/2026-06-19_adversary-comparison]]. When peers fall silent
rather than merely slow, the polls starve: Snowman cliffs earliest of the three,
finalizing under a silent tenth of the validators but starving once the silent
fraction reaches `φ = 0.20` at `n = 10`, below the one-third the other two
tolerate [[wiki/experiments/2026-06-19_adversary-comparison]]. The cliff is
committee-size dependent: the larger `n = 25` sample absorbs more non-responders
per poll and defers the starvation point to `φ = 0.33`, yet Snowman still fails
one sampled step before the quorum protocols, remaining the earliest of the three
to lose liveness under silence [[wiki/experiments/2026-06-17_offline-validators]]. The inversion is the
sharpest single result of the campaign — the identical structural choice makes
Snowman the most delay-tolerant family when peers are merely slow and the least
tolerant when they go silent [[wiki/algorithms/avalanche]]
[[wiki/concepts/key-findings]].

## 5.4 The frontier and the no-dominance verdict

Collecting the per-family positions gives the frontier its shape (Table 5.1). No
row of the table is won by a single family across the board, and three families
each win a row no other does: PBFT the delay, loss, and liveness axes; Casper FFG
the communication-overhead and accountability axes; Snowman the
equivocation-safety axis. Each is therefore non-dominated, and no family
dominates — the direct answer to RQ5 over the three protocols evaluated
[[wiki/concepts/research-questions]] [[wiki/concepts/key-findings]]. This verdict
does not rest on the one row only a slashing-based protocol can win: setting the
accountable-safety axis aside, each family is still non-dominated on a measured
axis — Casper FFG on communication overhead, Snowman on equivocation safety, and
PBFT on delay, loss, and liveness — so the multi-cornered shape survives the
removal of the definitional row [[wiki/concepts/key-findings]].

**Table 5.1 — Cross-regime comparison of the three families on the
performance–security plane (`n = 10 / 25`, 20 seeds).** Each row is one axis from
the Chapter 4 sweeps; the final column names the family or families that are
strict best on that axis. No family wins every row, and each of the three wins at
least one row no other does, so each is non-dominated. Two rows are not symmetric
contests: the equivocation-safety row ranks Snowman first on its analytical bound
`ε`, reported rather than empirically witnessed (§5.3.3), and the
accountable-safety row names a capability only a slashing-based protocol can
offer, so Casper FFG holds it uncontested by construction rather than by winning a
comparison. The loss-resilience row reports the `n = 10` ranking, where PBFT leads
cleanly; at `n = 25` PBFT and Snowman are a statistical tie at the top, their
area-under-the-retention-curve confidence intervals overlapping (Snowman
0.369 [0.366, 0.372], PBFT 0.351 [0.327, 0.376]) on a reduced Snowman seed count
[[wiki/experiments/2026-06-13_delay-comparison]]. Values pair the committee sizes
only where they differ; full per-`n` figures are in the cited pages.
Source: [[wiki/concepts/key-findings]],
[[wiki/experiments/2026-06-13_delay-comparison]],
[[wiki/experiments/2026-06-19_adversary-comparison]].

| Axis (regime) | PBFT | Casper FFG | Snowman | Best |
| :-- | :-- | :-- | :-- | :-- |
| Baseline commit latency | ≈ 1 s | ≈ 5 s | ≈ 1 s | PBFT ≈ Snowman |
| Communication overhead per unit | ≈ `2n` | ≈ `1.2n` | ≈ `2Kβ` (≈ 14× PBFT at `n = 16`) | Casper FFG |
| Time-to-finality under delay | + ≈ 0.9 s | + ≈ 27% | × 12–13 | PBFT |
| Loss resilience (AURC; survival depth) | first; alive at 20% loss | last | AURC tie at `n = 25`; cliffs by 10% loss | PBFT |
| Liveness under delayed voting | immune (1.0×) | dips (success → 0.60) | survives at ×62 finality | PBFT |
| Liveness under silence | clean to `φ = 0.33`, cliff at `φ = 0.40` | graceful to `φ = 0.33` | cliff at `φ = 0.20` (`n = 10`) / `φ = 0.33` (`n = 25`) | PBFT ≈ FFG |
| Safety under equivocation | deterministic fork at `φ = 0.40` | accountable, no fork | no fork surface; `ε ≈ 5 × 10⁻¹⁵` / `3 × 10⁻¹¹` | Snowman |
| Accountable safety | none (unattributable fork) | slashable ≥ ⅓ stake | not applicable (probabilistic) | Casper FFG |

Two features of the frontier carry more weight than the bare verdict. The first
is a gap in it rather than a point on it: the operator tradeoff of Figure 4.13
shows that the protocols which retain finalization under loss are exactly the ones
that pay the most latency to do so — PBFT and Snowman inflating time-to-finality
by factors of 2.16 (Snowman, `n = 10`) to 3.57 (PBFT, `n = 25`), each measured at
that protocol's own deepest surviving loss level rather than a common one and over
the seeds that still finalize there, so the two figures are not read off a single
point of Figure 4.13, while Casper FFG, which refuses that trade and stays near
unit latency, dies first [[wiki/experiments/2026-06-13_delay-comparison]]. The cheap-and-resilient corner
of the plane is empty: resilience is bought with latency, and no measured
configuration escapes the purchase [[wiki/concepts/key-findings]]. The second is
that the rankings invert across axes — the family first against delay and silence
is last against equivocation, the family first against equivocation is last
against silence, and the family never first is never catastrophic either
[[wiki/experiments/2026-06-19_adversary-comparison]]. The frontier is consistent,
holding a stable shape across the regimes, but it is genuinely multi-cornered, and
a deployment's position on it is fixed by which threat it must tolerate rather
than by a single best protocol.

## 5.5 Implications and hand-off

The practical content of the no-dominance result is the mapping itself. Because
each structural choice that defends a family on one axis exposes it on another,
protocol selection cannot be reduced to a single ranking and must instead be read
against the deployment's dominant threat: a system that above all must not fork
without attribution is served by Casper FFG's accountable failure; one that must
hold liveness through network turbulence by PBFT's view-change recovery; one that
must resist equivocation outright by Snowman's subsampling — and each of these
choices accepts the cost the same mechanism imposes elsewhere. The deployment
incidents that opened this study (§1.2) are heterogeneous in exactly this way: a
liveness halt under load on one network and a multi-epoch finality stall on
another are different failure classes, and the synthesis here is that they are not
competing symptoms of one immature technology but the predictable shadows of
distinct structural commitments [[wiki/concepts/key-findings]].

This chapter answered the last of the five research questions and, with it, closed
the comparative arc that began with the design space of Chapter 2. What remains is
to draw the individual answers together, to state plainly the boundaries within
which they hold, and to identify the directions the evaluation leaves open — the
work of Chapter 6.
