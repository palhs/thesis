# Chapter 5 — Synthesis

## 5.1 The joint reading

Chapter 4 isolated one stress axis at a time and each produced a clear per-axis
verdict but no joint reading. This chapter takes up **RQ5**: whether a consistent
Pareto frontier of the performance–security tradeoff exists across the three protocols
evaluated, and whether any one dominates the others across all regimes. It introduces
no new measurements — it collates the per-axis results of Chapter 4 onto a single
plane (Table 5.1, Figure 5.1) and reads the shape of the tradeoff off them, applying
the Pareto-dominance definition and the conventions fixed in Chapter 3 (§3.5). The
axes are the primary metrics of the four data-generating questions, not a set chosen
to make the families differ, so a family that dominated would do so on the very
quantities the evaluation was designed to measure. The verdicts are about the
*implemented* protocol — classical `O(n²)` PBFT, the Casper FFG gadget without
LMD-GHOST, and a linearized small-`n` Snowman — not the family in the abstract, since
a family-mate can invert a verdict (§6.2).

## 5.2 The cross-regime frontier

Table 5.1 collects the per-family positions on the eight cross-regime axes; every
per-family number lives in the table, and the conclusions of §5.3 read them off it
rather than restating them. Two of the eight axes are not symmetric measured contests.
Accountable safety is *definitional* — only a slashing-based protocol can make a
failure attributable, so Casper FFG holds it by construction. Equivocation safety is
*analytical* — Snowman ranks first on the bound `ε ≈ (1−α_c/K)^β` (≈ 10⁻¹⁵) the
simulator never witnesses, a different *kind* of guarantee than PBFT's measured
deterministic fork, not a stronger one on a shared scale. Figure 5.1 renders the eight
axes as a radar for shape only: ordinal-rank normalization discards magnitude (Snowman's
≈ 14× overhead deficit collapses to one inner-ring point), so the evidence is the table.

**Figure 5.1 — Cross-family performance–security frontier (illustrative, ordinal
only).** The three families scored on the eight cross-regime axes of Table 5.1,
normalized by *ordinal rank* per axis: the outer ring marks the strict best on an
axis, the center the worst, ties shared. The polygons overlap and none encloses
another — each family reaches the outer ring on at least one axis no other matches
(PBFT on the loss and liveness axes; Casper FFG on delay-robustness, communication
overhead, and accountable safety; Snowman on the analytical equivocation-safety axis) —
so each is non-dominated and no family dominates. Source: [[wiki/concepts/key-findings]],
[[wiki/experiments/2026-06-13_delay-comparison]],
[[wiki/experiments/2026-06-19_adversary-comparison]],
[[wiki/experiments/2026-06-19_adversarial-degradation]].

**Table 5.1 — Cross-regime comparison of the three families on the
performance–security plane (`n = 10 / 25`, 20 seeds; 8 for the Snowman `n = 25` delay
cell).** Each row is one axis from the Chapter 4 sweeps; the final column names the
family or families strict best on that axis. No family wins every row, and each of the
three wins at least one row no other does, so each is non-dominated. Two rows are not
symmetric measured contests (§5.2): the equivocation-safety row ranks Snowman first on
its analytical bound `ε` (reported, not witnessed), and the accountable-safety row
names a capability only a slashing-based protocol can offer. The loss-resilience row
reports the `n = 10` ranking, where PBFT leads cleanly; at `n = 25` PBFT and Snowman
are a statistical tie at the top (Snowman AURC 0.369 [0.366, 0.372], PBFT 0.351 [0.327,
0.376]) on a reduced Snowman seed count. Values pair the committee sizes only where
they differ. Source: [[wiki/concepts/key-findings]],
[[wiki/experiments/2026-06-13_delay-comparison]],
[[wiki/experiments/2026-06-19_adversary-comparison]],
[[wiki/experiments/2026-06-19_adversarial-degradation]].

| Axis (regime) | PBFT | Casper FFG | Snowman | Best |
| :-- | :-- | :-- | :-- | :-- |
| Baseline commit latency | ≈ 1 s | ≈ 5 s | ≈ 1 s | PBFT ≈ Snowman |
| Communication overhead per unit | ≈ `2n` | ≈ `1.2n` | ≈ `2Kβ` (≈ 14× PBFT at `n = 16`) | Casper FFG |
| Finality slowdown under delay (× baseline) | ×1.9 | ×1.3 | ×12–15 | Casper FFG |
| Loss resilience (AURC; survival depth) | first; alive at 20% loss | last | AURC tie at `n = 25`; cliffs by 10% loss | PBFT |
| Liveness under delayed voting | immune (1.0×) | dips (success → 0.60) | survives at ×62 finality | PBFT |
| Liveness under silence | clean to `φ = 0.33`, cliff at `φ = 0.40` | graceful to `φ = 0.33` | cliff at `φ = 0.20` (`n = 10`) / `φ = 0.33` (`n = 25`) | PBFT ≈ FFG |
| Safety under equivocation | deterministic fork at `φ = 0.40` | accountable, no fork | no fork surface; `ε ≈ 5 × 10⁻¹⁵` / `3 × 10⁻¹¹` | Snowman |
| Accountable safety | none (unattributable fork) | slashable ≥ ⅓ stake | not applicable (probabilistic) | Casper FFG |

## 5.3 Conclusions drawn from the frontier

Three conclusions follow from the frontier of §5.2.

**No family dominates.** No row of Table 5.1 is won by a single family across the
board, and each of the three wins at least one row no other does: PBFT the loss and
liveness axes; Casper FFG the delay-robustness, communication-overhead, and
accountability axes; Snowman the equivocation-safety axis. Each is therefore
non-dominated. This answers RQ5 directly over the three protocols evaluated: a
consistent performance–security frontier exists, and no family dominates it. The
verdict's strength does differ by axis — stripping the two non-measured axes, PBFT keeps
two measured corners (loss and delayed-voting liveness) and Casper FFG two (delay
robustness and communication overhead), but Snowman keeps none, so its claim to
non-domination rests on an analytical bound the simulator cannot confirm rather than on
a measured contest.

**Every defense is also an exposure.** The frontier has its shape because the
structural choice that places a family at the outer ring on one axis is the same choice
that pins it to the center on another. The sharpest instance is Snowman: the `K`-peer
subsampling that keeps it live (finalizing, only far slower) under slow rather than
silent peers is the identical mechanism that makes it the least tolerant once those
peers go silent, since a poll that waits on the slowest sampled peer tolerates a slow
answer but starves on no answer. That same wait is why Snowman pays the steepest
finality slowdown under delay, ×12–15: liveness is held, latency surrendered. PBFT shows
the same inversion across the security boundary: the leader-based,
exact-quorum commit rule whose view-change recovery carries it through delay, loss, and
silence is the rule that, past the fault threshold, forks without leaving slashable
evidence. Casper FFG completes the pattern from the middle: the slot-bound, epoch-paced
finality that makes it the cheapest in communication overhead and the least perturbed by
network delay, its slot clock barely moving (×1.3) where PBFT nearly doubles and Snowman
blows up by an order of magnitude, is the same conservatism that leaves it trailing on
baseline latency and the first to collapse under packet loss, even as it holds the
accountable-failure corner only a slashing-based protocol can occupy. The
contribution of this synthesis is that map of structural commitments to their paired
exposures, not the bare statement that no family wins.

**The cheap, fast, and resilient corner is empty.** Resilience under loss is bought
with latency: the protocols that retain finalization deepest into packet loss are
exactly the ones that pay the most time-to-finality to do so, while the family that
refuses the trade and stays near unit latency dies first (§4.3.3). No measured
configuration escapes the purchase, so the frontier carries a gap rather than a point:
the corner that would be cheap, fast, and resilient at once is unoccupied.

## 5.4 Implications and hand-off

The practical content of the no-dominance result is the mapping itself. Because each
structural choice that defends a family on one axis exposes it on another, protocol
selection cannot be reduced to a single ranking and must instead be read against the
deployment's dominant threat: a system that above all must not fork without attribution
is served by Casper FFG's accountable failure; one that must hold liveness through
network turbulence by PBFT's view-change recovery; one that must resist equivocation
outright by Snowman's subsampling. Each choice accepts the cost the same mechanism
imposes elsewhere. The deployment incidents that opened this study (§1.2) are
heterogeneous in exactly this way: a liveness halt under load on one network and a
multi-epoch finality stall on another are not competing symptoms of one immature
technology but the same class of failure seen from two distinct structural commitments,
the predictable consequence of the mechanisms Table 5.1 maps. What remains is to draw
the answers together, state the boundaries within which they hold, and identify the
directions the evaluation leaves open — the work of Chapter 6.
