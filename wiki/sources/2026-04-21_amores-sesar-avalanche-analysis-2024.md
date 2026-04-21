# [10] Amores-Sesar, Cachin & Schneider — An Analysis of Avalanche Consensus (2024)

**Category:** Protocol (formal analysis) · **Venue:** arXiv:2401.02811.

## Full citation

I. Amores-Sesar, C. Cachin, and P. Schneider, "An Analysis of Avalanche
Consensus," arXiv preprint arXiv:2401.02811, 2024.

## Key takeaways

1. **Rigorous safety/liveness re-analysis of [9].** Revisits the
   Snowflake/Snowball/Avalanche cascade with explicit adversary modelling
   and tightens (in some places, weakens) the bounds stated informally in
   the original paper. This is the balanced-treatment companion cited
   throughout [[algorithms/avalanche]].
2. **Async-liveness gap.** Shows that under worst-case asynchronous
   adversarial message delay, the informal liveness claims of [9] are
   optimistic: the number of rounds required for convergence can grow
   beyond what the original analysis suggested. Foregrounded as a
   weakness on [[algorithms/avalanche]] §weaknesses-to-foreground and is
   a primary target of the adversarial-delay experiments T46–T49.
3. **Refined safety-probability bounds.** Produces tighter bounds on the
   probability of two honest validators finalising conflicting values,
   as a function of `(K, α_c, β)` and Byzantine fraction. These bounds
   feed into [[concepts/quorum-arithmetic]] §avalanche as the formal
   statement backing the `1 − ε < (1 − α_c/K)^β` heuristic used on
   [[algorithms/avalanche]].
4. **No new protocol proposed.** Strictly a formal-analysis contribution
   — the paper critiques and tightens the theoretical understanding of
   the existing Avalanche cascade rather than offering a variant.
   Simulator design therefore does not change on account of [10]; what
   changes is which claims the thesis can make about Avalanche safety
   and liveness under adversarial conditions.
5. **Citation role in the thesis.** Cited wherever [[algorithms/avalanche]]
   needs to hedge an informal claim from [9] — specifically around
   async-liveness conditions and the parameter-sensitivity of the
   safety-probability bound. Per the citation policy on
   [[concepts/annotated-bibliography]] §citation-policy, [9] and [10]
   are cited together for balanced treatment.

## Limitations / gaps

Theoretical — no implementation, no empirical measurements. Bounds are
asymptotic in some regimes; constants of proportionality are not tight
enough to predict simulator outputs quantitatively. The simulator is
therefore the empirical counterpart to [10]'s formal treatment.

## Links to affected wiki pages

- [[algorithms/avalanche]] — primary consumer; async-liveness gap and
  refined bounds.
- [[concepts/quorum-arithmetic]] — formal backing for the `ε` bound.
- [[concepts/fault-model]] — adversary-strength framing.
- [[sources/2026-04-21_team-rocket-avalanche-2019]] — the paper being
  reanalysed.
- [[concepts/annotated-bibliography]] — paired with [9] for balanced
  citation of Avalanche safety/liveness claims.
