"""Snowman poll round (design spec §5).

A Poll is an in-flight round for one block_id; on_response records each
QUERY-RESPONSE and signals the success-path early-close trigger.
close_round applies the full Snowball update for one closed round.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .block import ConflictSet, CSState

log = logging.getLogger("t70.snowman")


@dataclass
class Poll:
    """In-flight poll round for one block_id (design spec §5)."""
    block_id: bytes
    request_id: int
    peers: tuple[int, ...]
    agree_per_block: dict[bytes, int] = field(default_factory=dict)
    responses_received: int = 0
    closed: bool = False


@dataclass(frozen=True)
class PollOutcome:
    flipped: bool
    new_preference: bytes
    counter: int
    accepted: bool


def on_response(
    *,
    poll: Poll,
    preferred_block_id: bytes,
    current_preference: bytes,
    alpha_c: int,
    K: int,
) -> bool:
    """Record one QUERY-RESPONSE; return True iff the success-path
    early-close trigger fires.

    The caller closes the round on either (a) this returning True, or
    (b) poll.responses_received == K (quorum). On a closed Poll, this
    function is a no-op returning False.
    """
    if poll.closed:
        return False
    poll.agree_per_block[preferred_block_id] = (
        poll.agree_per_block.get(preferred_block_id, 0) + 1
    )
    poll.responses_received += 1
    if poll.agree_per_block.get(current_preference, 0) >= alpha_c:
        poll.closed = True
        return True
    return False


def close_round(
    *,
    conflict_set: ConflictSet,
    poll: Poll,
    alpha_p: int,
    alpha_c: int,
    beta: int,
) -> PollOutcome:
    """Apply the genuine Snowball update for one closed round (design spec §5).

    Snowball (Rocket et al., Avalanche) accumulates per-block confidence
    across ALL rounds and sets the preference to the highest-confidence
    block — it does NOT flip to whichever block happened to win this single
    round's sample (that is Snowflake). Three-step rule:

      1. Identify this round's majority block b* = argmax agree_per_block.
         Tie-break: highest count, then lowest block_id bytes (lex). If
         count_majority >= alpha_p, increment confidence[b*] (the monotonic
         accumulator). Then set preference to the block with the HIGHEST
         accumulated confidence (argmax over confidence; tie-break lowest
         block_id). Flip only when a challenger's confidence STRICTLY exceeds
         the current preference's. On an actual preference change, reset the
         consecutive-success counter to 0.
      2. Check agree[preference] against alpha_c; if >=, counter += 1;
         else counter = 0. (alpha_c / beta consecutive-success semantics
         are unchanged.)
      3. If counter >= beta, state -> ACCEPTED.

    On a singleton conflict set the argmax-confidence block is always the
    sole block, so preference never changes and behaviour is identical to
    the pre-Snowball code path (audit finding #5, R5.4).
    """
    poll.closed = True
    prev_preference = conflict_set.preference

    # Zero-response close (T52: a query-timeout round where every sampled peer
    # was offline). No majority, so no confidence bump and no flip; the
    # preference's agree count is 0 < alpha_c, so the consecutive-success
    # counter resets and the block is not accepted. The normal close paths
    # (early-close / K responses) always have >= 1 response, so this branch is
    # exercised only by the timeout-on-total-silence case.
    if not poll.agree_per_block:
        conflict_set.counter = 0
        if log.isEnabledFor(logging.INFO):
            log.info(
                "close_round parent=%s round_majority=<none> count=0 "
                "alpha_p_hit=False conf_updated=False confidence=%s "
                "preference=%s pref_confidence=%d prev_preference=%s "
                "flipped=False counter=0 accepted=False",
                conflict_set.parent_id.hex()[:8],
                {bid.hex()[:8]: c
                 for bid, c in conflict_set.confidence.items()},
                conflict_set.preference.hex()[:8],
                conflict_set.confidence.get(conflict_set.preference, 0),
                prev_preference.hex()[:8],
            )
        return PollOutcome(
            flipped=False,
            new_preference=conflict_set.preference,
            counter=conflict_set.counter,
            accepted=False,
        )

    # Step 1a: this round's majority + alpha_p -> bump confidence accumulator.
    majority_block, count_majority = min(
        poll.agree_per_block.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )
    conf_updated = False
    if count_majority >= alpha_p:
        conflict_set.confidence[majority_block] = (
            conflict_set.confidence.get(majority_block, 0) + 1
        )
        conf_updated = True

    # Step 1b: preference = argmax accumulated confidence (Snowball).
    # Flip only when a challenger STRICTLY exceeds the current preference's
    # confidence (tie-break: lowest block_id). The current preference is the
    # incumbent, so a tie keeps it.
    pref_conf = conflict_set.confidence.get(conflict_set.preference, 0)
    best_block, best_conf = conflict_set.preference, pref_conf
    for block_id, conf in conflict_set.confidence.items():
        # Strict-exceed only: an exact tie keeps the incumbent preference,
        # which gives the lowest-block_id tie-break once the incumbent itself
        # is the lowest-id holder of the max (it always is, since it would
        # only have become preference by strictly exceeding earlier).
        if conf > best_conf:
            best_block, best_conf = block_id, conf
    flipped = False
    if best_block != conflict_set.preference:
        conflict_set.preference = best_block
        conflict_set.counter = 0
        flipped = True

    # Step 2: alpha_c on the (possibly-new) preference.
    pref_agree = poll.agree_per_block.get(conflict_set.preference, 0)
    if pref_agree >= alpha_c:
        conflict_set.counter += 1
    else:
        conflict_set.counter = 0

    # Step 3: beta -> ACCEPTED.
    accepted = False
    if (conflict_set.counter >= beta
            and conflict_set.state is CSState.POLLING):
        conflict_set.state = CSState.ACCEPTED
        accepted = True

    # Gated step-logging (t70.snowman). Side-effect-free: no RNG, no state.
    if log.isEnabledFor(logging.INFO):
        log.info(
            "close_round parent=%s round_majority=%s count=%d alpha_p_hit=%s "
            "conf_updated=%s confidence=%s preference=%s pref_confidence=%d "
            "prev_preference=%s flipped=%s counter=%d accepted=%s",
            conflict_set.parent_id.hex()[:8],
            majority_block.hex()[:8],
            count_majority,
            count_majority >= alpha_p,
            conf_updated,
            {bid.hex()[:8]: c for bid, c in conflict_set.confidence.items()},
            conflict_set.preference.hex()[:8],
            conflict_set.confidence.get(conflict_set.preference, 0),
            prev_preference.hex()[:8],
            flipped,
            conflict_set.counter,
            accepted,
        )

    return PollOutcome(
        flipped=flipped,
        new_preference=conflict_set.preference,
        counter=conflict_set.counter,
        accepted=accepted,
    )
