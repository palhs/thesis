"""T70 accountable-safety demo (audit finding #3).

Constructs a 4-validator CasperNode, populates its chain off the slot loop,
then injects (a) one DOUBLE VOTE and (b) one SURROUND VOTE via crafted
ATTESTATION messages, with the `t70.casper` step logger enabled at INFO.

Not a library module — it calls logging.basicConfig, which library code must
never do. Run from the worktree with PYTHONPATH=src:

  PYTHONPATH=src python3 -m pos._t70_demo
"""
from __future__ import annotations

import logging

from nodes import Message
from pos.chain import GENESIS_HASH, block_hash
from pos.messages import AttestationPayload, BlockProposalPayload, FFGVote
from pos.node import CasperNode


def _att(src, s_ep, s_hash, t_ep, t_hash):
    ffg = FFGVote(source_epoch=s_ep, source_hash=s_hash,
                  target_epoch=t_ep, target_hash=t_hash)
    pp = AttestationPayload(slot=0, epoch=t_ep, ffg=ffg, attester_idx=src)
    return Message(src=src, dst=0, type="ATTESTATION", payload=pp, t_sent=0.0)


def _populate(node, upto_epoch):
    spe = node.slots_per_epoch
    parent = GENESIS_HASH
    hashes = {0: GENESIS_HASH}
    for s in range(1, (upto_epoch + 1) * spe + 1):
        proposer = node._proposer_of(s)
        bh = block_hash(slot=s, parent_hash=parent, proposer_idx=proposer,
                        transactions=())
        pp = BlockProposalPayload(slot=s, epoch=s // spe, parent_hash=parent,
                                  block_hash=bh, transactions=(),
                                  proposer_idx=proposer)
        node.on_message(Message(src=proposer, dst=node.id,
                                type="BLOCK-PROPOSAL", payload=pp,
                                t_sent=0.0), t=float(s))
        parent = bh
        if s == (s // spe) * spe:
            hashes[s // spe] = bh
    return hashes


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
    from nodes.lifecycle import Lifecycle
    n = CasperNode(node_id=0, weight=3.0, endpoint=None, global_seed=42,
                   n=4, stake_table={i: 3.0 for i in range(4)},
                   slots_per_epoch=2)
    # Stub the bind-time outbound API so the node runs unbound. We print the
    # casper_slashing emits explicitly; everything else is a no-op. (None of
    # this touches the seeded RNG or node consensus state.)
    def _emit(et, fields, t):
        if et == "casper_slashing":
            print(f"  EMIT casper_slashing {fields}")
    n.emit = _emit
    n.broadcast = lambda ty, p, t: None
    n.set_timer = lambda *a, **kw: None
    n.cancel_timer = lambda *a, **kw: None
    n.status = Lifecycle.RUNNING
    cps = _populate(n, upto_epoch=4)

    print("=== inject DOUBLE VOTE by attester 1 (target epoch 1) ===")
    n.on_message(_att(1, 0, cps[0], 1, cps[1]), t=10.0)           # honest
    n.on_message(_att(1, 0, cps[0], 1, b"X" * 32), t=11.0)        # conflict

    print("=== inject SURROUND VOTE by attester 2 (1<2<3<4) ===")
    n.on_message(_att(2, 1, cps[1], 4, cps[4]), t=12.0)           # wide
    n.on_message(_att(2, 2, cps[2], 3, cps[3]), t=13.0)           # inner

    print(f"=== slashable_stake_fraction = "
          f"{n.slashable_stake_fraction():.4f} "
          f"(2 of 4 offenders, stake 6/12) ===")


if __name__ == "__main__":
    main()
