# Chapter 5 — Synthesis

## 5.1 The joint reading

Chapter 4 examined one stress axis at a time. Each axis produced a clear per-axis
verdict, but the axes were never read together. That joint reading is the work of this
chapter, which takes up **RQ5**: whether a consistent Pareto frontier of the
performance–security tradeoff exists across the three protocols evaluated, and whether
any one dominates the others across all regimes. No new measurements are introduced
here. The per-axis results of Chapter 4 are collated onto a single plane (Table 5.1,
Figure 5.1), and the shape of the tradeoff is read off them under the Pareto-dominance
definition and the conventions fixed in Chapter 3 (§3.5). The axes are the primary
metrics of the four data-generating questions, not a set chosen to make the families
differ; a family that dominated would therefore do so on the very quantities the
evaluation was designed to measure. These verdicts concern the *implemented* protocol:
classical `O(n²)` PBFT, the Casper FFG gadget without LMD-GHOST, and a linearized
small-`n` Snowman. They do not concern the family in the abstract, because a
family-mate can invert a verdict (§6.2).

## 5.2 The cross-regime frontier

Table 5.1 positions each family on eight cross-regime axes. Two of those axes are not
symmetric measured contests. Accountable safety is definitional: only a slashing-based
protocol can make a failure attributable, so Casper FFG holds it by construction.
Equivocation safety is analytical: Snowman ranks first on the bound `ε` the simulator
never witnesses, a different kind of guarantee from PBFT's measured deterministic fork,
not a stronger one on a shared scale. Figure 5.1 renders the eight axes as a radar for
shape only; ordinal-rank normalization discards magnitude (Snowman's ≈ 14× overhead
deficit collapses to one inner-ring point), so the evidence is the table.

**Figure 5.1 — Cross-family performance–security frontier (illustrative, ordinal
only).** The three families scored on the eight cross-regime axes of Table 5.1,
normalized by ordinal rank per axis: the outer ring marks the strict best on an axis,
the center the worst, ties shared. No polygon encloses another; each reaches the outer
ring on at least one axis the others do not, so no family dominates. Source:
[[wiki/concepts/key-findings]], [[wiki/experiments/2026-06-13_delay-comparison]],
[[wiki/experiments/2026-06-19_adversary-comparison]],
[[wiki/experiments/2026-06-19_adversarial-degradation]].

**Table 5.1 — Cross-regime comparison of the three families on the
performance–security plane (`n = 10 / 25`, 20 seeds).** Two rows are not
symmetric measured contests (§5.2): the equivocation-safety row ranks Snowman first on
its analytical bound `ε` (reported, not witnessed), and the accountable-safety row
names a capability only a slashing-based protocol can offer. The loss-resilience Best
column reports the `n = 10` ranking; at `n = 25` PBFT and Snowman are a statistical
tie (AURC 0.351 [0.327, 0.376] vs. 0.369 [0.366, 0.372], reduced seed count).
Source: [[wiki/concepts/key-findings]],
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

**No family dominates.** Each family holds at least one axis no other matches, so none
is dominated. This is a direct answer to RQ5. The claim is not equally strong for all three:
strip the two non-measured rows and PBFT and Casper FFG each hold two measured corners,
but Snowman holds none; its non-domination rests on an analytical bound the simulator
cannot confirm rather than a measured contest.

**Every defense is also an exposure.** Each family sits at the outer ring on some axes
and at the center on others because the same structural choice drives both positions.
Snowman is the sharpest instance. The `K`-peer subsampling that keeps it live
(finalizing, only far slower) under slow peers is the same mechanism that makes it the
least tolerant once those peers go silent: a poll that waits on the slowest sampled
peer tolerates a slow answer but starves on no answer. That wait is also why Snowman
pays the steepest finality slowdown under delay, ×12–15. PBFT shows the same inversion
across the security boundary. The leader-based exact-quorum commit rule that carries it
through delay, loss, and silence is the rule that, past the fault threshold, forks
without leaving slashable evidence. Casper FFG completes the pattern. Its slot-bound,
epoch-paced finality makes it cheapest in communication overhead and the least
perturbed by network delay (the slot clock moves ×1.3, where PBFT nearly doubles and
Snowman grows by an order of magnitude), and that same conservatism leaves it first to
collapse under packet loss, even as it holds the accountable-failure corner only a
slashing-based protocol can occupy. The pattern holds across all three families. The
same design parameter that creates resilience on one axis creates vulnerability on
another, because the mechanisms that tolerate one failure mode are structurally
incompatible with tolerating another.

**The cheap, fast, and resilient corner is empty.** Resilience under loss is bought
with latency: the protocols that retain finalization deepest into packet loss are
exactly the ones that pay the most in time-to-finality, while the family that refuses
the trade and stays near unit latency dies first (§4.3.3). No measured configuration
escapes the purchase, so the frontier carries a gap rather than a point: the corner
that would be cheap, fast, and resilient at once is unoccupied.

## 5.4 Implications and hand-off

The no-dominance result is a selection guide: the dominant threat is matched to the
protocol that defends against it, with attribution requirements going to Casper FFG,
liveness under turbulence to PBFT, and equivocation resistance to Snowman. The
incidents that opened this study (§1.2) fit the same map. A liveness halt under load
and a multi-epoch finality stall look like two separate problems; each is a protocol at
its structural limit. Chapter 6 draws where those limits hold and what the evaluation
leaves open.
