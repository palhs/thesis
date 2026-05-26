"""Casper FFG threshold-finality rule (T34).

Pure function over (source state, target state, link stake, total stake).
Says what should happen — `FFGTransitions(justified, finalised_source)` —
without mutating anything. The caller owns the FSM and the side effects
(state writes, emits, highest-watermark bookkeeping).

The rule, mechanically:

1. Target justifies on a `>= 2/3` stake link from a source that is already
   justified or finalised.
2. The source finalises iff the target is its immediate successor AND the
   source is still in the JUSTIFIED state (so a re-justification of an
   already-FINALISED source does not re-finalise it — idempotent).

Genesis (epoch 0) is pre-finalised at `CasperNode.__init__` time and is
never seen as a target by this rule; `evaluate` documents `target_epoch >=
1` as a precondition.

The supermajority test is division-free (`3 * stake >= 2 * total`) so
whole-number stakes compare exactly without floating-point rounding.
"""
from __future__ import annotations

from dataclasses import dataclass

from .epoch import EpochFSM


def meets_supermajority(stake: float, total_stake: float) -> bool:
    """True iff `stake` is at least 2/3 of `total_stake`."""
    return 3.0 * stake >= 2.0 * total_stake


@dataclass(frozen=True)
class FFGTransitions:
    """What the FFG rule says happened on one vote application.

    `justified` is True iff the target epoch crosses UNJUSTIFIED ->
    JUSTIFIED on this vote. `finalised_source` is True iff that
    justification additionally finalises the source epoch (consecutive-link
    rule). `finalised_source` implies `justified`.
    """
    justified: bool
    finalised_source: bool


_NONE = FFGTransitions(justified=False, finalised_source=False)


def evaluate(*, source_epoch: int, target_epoch: int,
             link_stake: float, total_stake: float,
             source_state: EpochFSM,
             target_state: EpochFSM) -> FFGTransitions:
    """Return the transitions implied by one vote on `source -> target`.

    Two-clause rule:

    1. The target justifies iff (a) it is currently UNJUSTIFIED, (b) the
       source is currently JUSTIFIED or FINALISED, and (c) `link_stake`
       meets the 2/3 supermajority of `total_stake`.
    2. Conditional on (1), the source finalises iff the target is its
       immediate successor AND the source is still strictly JUSTIFIED —
       an already-FINALISED source does not re-finalise (idempotent).

    Preconditions: `target_epoch >= 1` (genesis is bootstrapped to
    FINALISED at `CasperNode.__init__` time, not rule-derived);
    `total_stake > 0` (enforced upstream at `CasperNode.__init__` so the
    empty-quorum case never reaches the rule).
    """
    if target_state is not EpochFSM.UNJUSTIFIED:
        return _NONE
    if source_state not in (EpochFSM.JUSTIFIED, EpochFSM.FINALISED):
        return _NONE
    if not meets_supermajority(link_stake, total_stake):
        return _NONE
    finalised_source = (
        target_epoch == source_epoch + 1
        and source_state is EpochFSM.JUSTIFIED
    )
    return FFGTransitions(justified=True, finalised_source=finalised_source)
