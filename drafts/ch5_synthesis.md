# Chapter 5 — Synthesis

## 5.1 The joint reading

Chapter 4 isolated one stress axis at a time — validator-set size, network delay,
and adversarial behavior — each yielding a clear per-axis verdict but no joint
reading. This chapter takes up RQ5: whether a consistent Pareto frontier of the
performance–security tradeoff exists across the three protocols evaluated (PBFT,
Casper FFG, and Snowman) and whether any one dominates the others across all
regimes [[wiki/concepts/research-questions]]. It introduces no new measurements;
it collates the per-axis results of Chapter 4 onto a single plane (Table 5.1,
Figure 5.1) and reads the shape of the tradeoff off them, applying the
Pareto-dominance definition and the measurement conventions fixed in Chapter 3
(§3.5–§3.6). The axes are the primary metrics of the four data-generating research
questions rather than a set chosen to make the families differ, so a family that
dominated would do so on the very quantities the evaluation was designed to
measure. The synthesis adds a reading, not a measurement
[[wiki/concepts/output-format]].

## 5.2 The cross-regime frontier

Table 5.1 collects the per-family positions on the eight cross-regime axes, and
Figure 5.1 renders the same data as an overlaid radar. Together they are the
anchor for the rest of the chapter: every per-family number — baseline latency,
the `2n` / `1.2n` / `2Kβ` overhead split, the time-to-finality multipliers under
delay, the loss-resilience ordering, the silence cliffs, the 229-instance fork,
the `ε` safety bound, and the slashable-stake fraction — lives in the table and
caption, and the conclusions of §5.3 read off them rather than restating them.

**Table 5.1 — Cross-regime comparison of the three families on the
performance–security plane (`n = 10 / 25`, 20 seeds; 8 for the Snowman `n = 25`
delay cell).** Each row is one axis from the Chapter 4 sweeps; the final column
names the family or families that are strict best on that axis. No family wins
every row, and each of the three wins at least one row no other does, so each is
non-dominated. Two rows are not symmetric contests: the equivocation-safety row
ranks Snowman first on its analytical bound `ε` (reported, not witnessed; §3.5),
and the accountable-safety row names a capability only a slashing-based protocol
can offer, so Casper FFG holds it uncontested by construction rather than by
winning a comparison. The loss-resilience row reports the `n = 10` ranking, where
PBFT leads cleanly. At `n = 25` PBFT and Snowman are a statistical tie at the top,
their area-under-the-retention-curve confidence intervals overlapping (Snowman
0.369 [0.366, 0.372], PBFT 0.351 [0.327, 0.376]) on a reduced Snowman seed count
[[wiki/experiments/2026-06-13_delay-comparison]]. Values pair the committee sizes
only where they differ; full per-`n` figures are in the cited pages.
Source: [[wiki/concepts/key-findings]],
[[wiki/experiments/2026-06-13_delay-comparison]],
[[wiki/experiments/2026-06-19_adversary-comparison]],
[[wiki/experiments/2026-06-19_adversarial-degradation]].

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

**Figure 5.1 — Cross-family performance–security frontier.** The three families
evaluated, scored on the eight cross-regime axes of Table 5.1 and normalized by
ordinal rank per axis: the outer ring marks the strict best on an axis and the
center the worst, with ties shared. The polygons overlap and none encloses
another. Each family reaches the outer ring on at least one axis no other
matches — PBFT on the delay, loss, and liveness axes, Casper FFG on communication
overhead and accountable safety, Snowman on equivocation safety — so each is
non-dominated and no family dominates, the verdict of Table 5.1 read directly off
one image. The rank scale sets aside the magnitudes that drive it, which are the
Chapter 4 headlines: Snowman's time-to-finality grows roughly sixty-twofold under
delayed voting and its polling overhead reaches about fourteen times PBFT's, PBFT
forks into 229 conflicting committed instances past its threshold, and Snowman's
analytical safety bound is near `5 × 10⁻¹⁵` while Casper FFG exposes at least
one-third of stake as slashable. Two axes are not symmetric contests, as in
Table 5.1: equivocation safety ranks Snowman first on its reported analytical
bound rather than an empirical witness, and accountable safety names a capability
only a slashing-based protocol offers. Source:
[[wiki/concepts/key-findings]], [[wiki/experiments/2026-06-13_delay-comparison]],
[[wiki/experiments/2026-06-19_adversary-comparison]],
[[wiki/experiments/2026-06-19_adversarial-degradation]].

## 5.3 Conclusions drawn from the frontier

Three conclusions follow from the frontier of §5.2. The first answers RQ5; the
second reads the mechanism behind the shape; the third names what the shape
leaves empty.

**No family dominates.** No row of Table 5.1 is won by a single family across the
board, and each of the three wins at least one row no other does: PBFT the delay,
loss, and liveness axes; Casper FFG the communication-overhead and accountability
axes; Snowman the equivocation-safety axis. Each is therefore non-dominated. This
answers RQ5 directly over the three protocols evaluated: a consistent
performance–security frontier exists, and no family dominates it. The verdict does
not rest on the one row only a slashing-based protocol can win. Setting the
accountable-safety axis aside, each family is still non-dominated on a measured
axis — Casper FFG on communication overhead, Snowman on equivocation safety, PBFT
on delay, loss, and liveness — so the multi-cornered shape survives the removal of
the definitional row.

**Every defense is also an exposure.** The frontier has the shape it does because
the structural choice that places a family at the outer ring on one axis is the
same choice that pins it to the center on another, and the rankings invert
accordingly. The sharpest single instance is Snowman: the `K`-peer subsampling
that makes it the most delay-tolerant family when peers are merely slow is the
identical mechanism that makes it the least tolerant when those peers go silent,
because a poll that waits on the slowest sampled peer still tolerates a slow
answer but starves on no answer. PBFT shows the same inversion across the
security boundary: the leader-based, exact-quorum commit rule whose view-change
recovery carries it through delay, loss, and silence is the rule that, past the
fault threshold, forks without leaving slashable evidence. Casper FFG sits at
neither extreme — never first on any axis, yet never catastrophic on any either,
trailing on latency and loss-resilience while holding the accountable-failure
corner that only a slashing-based protocol can occupy, where an equivocation
becomes attributable, slashable stake rather than an unattributable fork. The
contribution of this synthesis is that map of structural commitments to their
paired exposures, not the bare statement that no family wins.

**The cheap, fast, and resilient corner is empty.** Resilience under loss is
bought with latency: the protocols that retain finalization deepest into packet
loss are exactly the ones that pay the most time-to-finality to do so, while the
family that refuses the trade and stays near unit latency dies first
(Figure 4.5c). No measured configuration escapes the purchase, so the frontier
carries a gap rather than a point — the corner that would be cheap, fast, and
resilient at once is unoccupied.

## 5.4 Implications and hand-off

The practical content of the no-dominance result is the mapping itself. Because
each structural choice that defends a family on one axis exposes it on another,
protocol selection cannot be reduced to a single ranking and must instead be read
against the deployment's dominant threat: a system that above all must not fork
without attribution is served by Casper FFG's accountable failure; one that must
hold liveness through network turbulence by PBFT's view-change recovery; one that
must resist equivocation outright by Snowman's subsampling. Each of these choices
accepts the cost the same mechanism imposes elsewhere. The deployment incidents
that opened this study (§1.2) are heterogeneous in exactly this way: a liveness
halt under load on one network and a multi-epoch finality stall on another are not
competing symptoms of one immature technology but the same class of failure seen
from two distinct structural commitments, the predictable shadows of the
mechanisms Table 5.1 maps [[wiki/concepts/key-findings]].

This chapter answered the last of the five research questions and, with it, closed
the comparative arc that began with the design space of Chapter 2. What remains is
to draw the individual answers together, to state plainly the boundaries within
which they hold, and to identify the directions the evaluation leaves open — the
work of Chapter 6.
