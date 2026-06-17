"""The equivocate-vote adversary: three node subclasses + shared helpers (T53).

Behaviour lives here as thin subclasses of the honest node classes; the honest
FSMs under src/{pbft,pos,snowman}/ are never edited (B-hybrid, design §2). Each
subclass overrides only its payload-emitting methods to fork a conflicting
payload across a deterministic half-half split of its recipients — NO adversary
RNG, so per-cell replay is byte-identical (design §7).

Design contract: docs/plans/2026-06-18-t53-equivocating-nodes-design.md
"""
from __future__ import annotations

from pbft import PBFTNode
from pbft.digest import digest as _pbft_digest
from pbft.messages import CommitPayload, PreparePayload, PrePreparePayload


def split_recipients(node) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Split peers-minus-self into (lo, hi) halves; pure fn of (node.n, node.id)."""
    peers = tuple(i for i in range(node.n) if i != node.id)
    mid = len(peers) // 2
    return peers[:mid], peers[mid:]


def conflicting_bytes(tag: str, k1: int, k2: int) -> tuple[bytes, bytes]:
    """Two distinct request/tx blobs, a pure fn of the instance key, so every
    colluding Byzantine node derives the SAME pair independently."""
    return (f"EQV-A:{tag}:{k1}:{k2}".encode(),
            f"EQV-B:{tag}:{k1}:{k2}".encode())


class EquivocatingPBFTNode(PBFTNode):
    """Byzantine PBFT replica: conflicting PRE-PREPARE (as primary) + forked
    PREPARE/COMMIT votes (design §3.1). Honest PBFTNode FSM otherwise."""

    def _propose(self, t):
        if self.view_changing or not self.workload \
                or not self._is_primary(self.view):
            return
        self.workload.pop(0)
        seq = self.next_seq
        self.next_seq += 1
        reqA, reqB = conflicting_bytes("pbft", self.view, seq)
        lo, hi = split_recipients(self)
        for dst in lo:
            self.send(dst, "PRE-PREPARE",
                      PrePreparePayload(self.view, seq,
                                        _pbft_digest(reqA), reqA), t)
        for dst in hi:
            self.send(dst, "PRE-PREPARE",
                      PrePreparePayload(self.view, seq,
                                        _pbft_digest(reqB), reqB), t)
        self._accept_pre_prepare(self.view, seq, _pbft_digest(reqA), reqA,
                                 src=self.id, t=t)
        self.set_timer("propose", self.propose_delay, None, t)

    def _broadcast_prepare(self, inst, t):
        reqA, reqB = conflicting_bytes("pbft", inst.view, inst.seq)
        lo, hi = split_recipients(self)
        for dst in lo:
            self.send(dst, "PREPARE",
                      PreparePayload(inst.view, inst.seq,
                                     _pbft_digest(reqA)), t)
        for dst in hi:
            self.send(dst, "PREPARE",
                      PreparePayload(inst.view, inst.seq,
                                     _pbft_digest(reqB)), t)
        inst.prepares[self.id] = inst.digest

    def _broadcast_commit(self, inst, t):
        reqA, reqB = conflicting_bytes("pbft", inst.view, inst.seq)
        lo, hi = split_recipients(self)
        for dst in lo:
            self.send(dst, "COMMIT",
                      CommitPayload(inst.view, inst.seq,
                                    _pbft_digest(reqA)), t)
        for dst in hi:
            self.send(dst, "COMMIT",
                      CommitPayload(inst.view, inst.seq,
                                    _pbft_digest(reqB)), t)
        inst.commits[self.id] = inst.digest
