"""Snowman poll round (design spec §5).

A Poll is an in-flight round for one block_id; on_response records each
QUERY-RESPONSE and signals the success-path early-close trigger.
close_round applies the full Snowball update for one closed round.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .block import ConflictSet, CSState


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
    """Apply the full Snowball update for one closed round (design spec §5).

    Three-step rule:
      1. Identify majority block b* = argmax agree_per_block. Tie-break:
         highest count, then lowest block_id bytes (lex). If
         count_majority >= alpha_p AND b* != current preference, flip
         preference to b* and reset counter to 0. Increment confidence[b*]
         regardless of flip.
      2. Check agree[preference] against alpha_c; if >=, counter += 1;
         else counter = 0.
      3. If counter >= beta, state -> ACCEPTED.
    """
    poll.closed = True

    # Step 1: majority + alpha_p
    majority_block, count_majority = min(
        poll.agree_per_block.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )
    flipped = False
    if count_majority >= alpha_p:
        if majority_block != conflict_set.preference:
            conflict_set.preference = majority_block
            conflict_set.counter = 0
            flipped = True
        conflict_set.confidence[majority_block] = (
            conflict_set.confidence.get(majority_block, 0) + 1
        )

    # Step 2: alpha_c on the (possibly-new) preference
    pref_agree = poll.agree_per_block.get(conflict_set.preference, 0)
    if pref_agree >= alpha_c:
        conflict_set.counter += 1
    else:
        conflict_set.counter = 0

    # Step 3: beta -> ACCEPTED
    accepted = False
    if (conflict_set.counter >= beta
            and conflict_set.state is CSState.POLLING):
        conflict_set.state = CSState.ACCEPTED
        accepted = True

    return PollOutcome(
        flipped=flipped,
        new_preference=conflict_set.preference,
        counter=conflict_set.counter,
        accepted=accepted,
    )
