"""T70 genuine-Snowball preference demo (audit finding #5).

Constructs a 2-block conflict set and drives close_round through a sequence
where Snowflake's "flip to this round's sample majority" and genuine
Snowball's "prefer the highest accumulated confidence" DIVERGE. With the
`t70.snowman` step logger enabled at INFO, each round prints the per-round
sample agree-counts, the confidence accumulator, the chosen preference and
its confidence, the counter, and whether the block was accepted.

Watch the round where block B becomes the single-round majority while A
still leads on accumulated confidence: Snowflake would flip to B, genuine
Snowball keeps A (flipped=False). Only once confidence[B] STRICTLY exceeds
confidence[A] does the preference flip.

Not a library module — it calls logging.basicConfig, which library code
must never do. Run from the worktree with PYTHONPATH=src:

  PYTHONPATH=src python3 -m snowman._t70_demo
"""
from __future__ import annotations

import logging

from snowman.block import Block, ConflictSet, CSState, GENESIS_ID
from snowman.poll import Poll, close_round

A = b"A" * 32
B = b"B" * 32

ALPHA_P = 3
ALPHA_C = 4
BETA = 15


def _cs() -> ConflictSet:
    cs = ConflictSet(parent_id=GENESIS_ID)
    cs.add_block(Block(block_id=A, parent_id=GENESIS_ID, slot=1,
                       proposer_idx=0, transactions=()))
    cs.add_block(Block(block_id=B, parent_id=GENESIS_ID, slot=1,
                       proposer_idx=1, transactions=()))
    return cs


def _round(cs: ConflictSet, agree: dict[bytes, int]) -> None:
    poll = Poll(block_id=A, request_id=1, peers=(1, 2, 3, 4, 5))
    poll.agree_per_block = dict(agree)
    poll.responses_received = sum(agree.values())
    close_round(conflict_set=cs, poll=poll,
                alpha_p=ALPHA_P, alpha_c=ALPHA_C, beta=BETA)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
    cs = _cs()
    print(f"=== initial preference={cs.preference.hex()[:8]} "
          f"(alpha_p={ALPHA_P} alpha_c={ALPHA_C} beta={BETA}) ===")

    print("=== rounds 1-3: A is the alpha_p majority; confidence[A] -> 3 ===")
    for _ in range(3):
        _round(cs, {A: 5, B: 0})

    print("=== round 4: B is THIS round's alpha_p majority, but "
          "confidence[A]=3 > confidence[B]=1 -> Snowflake would flip; "
          "Snowball does NOT ===")
    _round(cs, {B: 4, A: 1})

    print("=== round 5: B wins again; confidence[B]=2 still < A=3 -> no flip ===")
    _round(cs, {B: 4, A: 1})

    print("=== round 6: confidence[B]=3 TIES A=3 -> no flip (must STRICTLY "
          "exceed; incumbent A wins the tie) ===")
    _round(cs, {B: 4, A: 1})

    print("=== round 7: confidence[B]=4 > confidence[A]=3 -> flip to B, "
          "counter resets ===")
    _round(cs, {B: 4, A: 1})

    print(f"=== final preference={cs.preference.hex()[:8]} "
          f"confidence={ {bid.hex()[:8]: c for bid, c in cs.confidence.items()} } "
          f"state={cs.state.value} ===")


if __name__ == "__main__":
    main()
