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
from pos import CasperNode
from pos.chain import GENESIS_HASH, block_hash
from pos.messages import AttestationPayload, FFGVote
from snowman import SnowmanNode
from snowman.block import Block, hash_block
from snowman.messages import (
    BlockAnnouncementPayload,
    QueryPayload,
    QueryResponsePayload,
)


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


class EquivocatingCasperNode(CasperNode):
    """Byzantine Casper FFG validator: double-vote (design §3.2).

    Overrides ONLY `_attest`. After the honest CasperNode broadcasts and
    self-records its real ATTESTATION (super call), this node broadcasts a
    SECOND, CONFLICTING FFG vote for the same target epoch — same
    source/target epoch as the honest vote, but a fabricated target_hash.
    Both votes go to ALL peers (no half-half split): accountable-safety
    detection requires a single honest node to receive BOTH votes so its
    EpochState classifies the second as CONFLICT and slashes.

    A forked BLOCK-PROPOSAL is deliberately NOT modelled: `EpochState.links`
    aggregates stake by source_epoch and ignores target_hash, so a forked
    proposal would spuriously "finalise" two checkpoints under an honest
    supermajority — a model artifact, not a real safety break. The faithful
    FFG break signal is `slashable_stake_fraction` (design contract).
    """

    def _attest(self, epoch, slot, t):
        # Honest attestation first: broadcasts the real ATTESTATION and
        # self-records (super call is the unmodified honest FSM step).
        super()._attest(epoch, slot, t)
        # Mirror the honest guard: only emit the conflicting vote if the
        # honest vote itself would have been sent (both checkpoints present).
        try:
            target_cp = self.chain.checkpoint(epoch)
            source_epoch = self.highest_justified
            source_cp = self.chain.checkpoint(source_epoch)
        except KeyError:
            return
        # Fabricate a target_hash distinct from the real checkpoint's; same
        # source/target epoch so the recipient's epoch-match guard passes and
        # EpochState.record_vote classifies it as CONFLICT (same attester +
        # target_epoch, differing target_hash).
        alt_hash = block_hash(slot=slot, parent_hash=GENESIS_HASH,
                              proposer_idx=self.id,
                              transactions=(b"EQV-ALT",))
        if alt_hash == target_cp.block_hash:
            return
        alt_ffg = FFGVote(source_epoch=source_epoch,
                          source_hash=source_cp.block_hash,
                          target_epoch=epoch,
                          target_hash=alt_hash)
        self.broadcast("ATTESTATION",
                       AttestationPayload(slot=slot, epoch=epoch,
                                          ffg=alt_ffg, attester_idx=self.id),
                       t)


class EquivocatingSnowmanNode(SnowmanNode):
    """Byzantine Snowman validator: equivocating proposer + lying responder
    (design §3.3). Overrides `_propose` (forks the BLOCK-ANNOUNCEMENT into two
    blocks for the same (slot, parent) — a genuine 2-member conflict set, the
    only thing there is to lie about) and `_handle_query` (returns a
    NON-preference member). No RNG touched (the K-peer sampler in
    _start_poll_round is unchanged), so per-cell replay stays byte-identical."""

    def _propose(self, slot, t):
        parent_id = self.chain.tip
        txA, txB = conflicting_bytes("snow", slot, 0)
        bidA = hash_block(slot=slot, parent_id=parent_id,
                          proposer_idx=self.id, transactions=(txA,))
        bidB = hash_block(slot=slot, parent_id=parent_id,
                          proposer_idx=self.id, transactions=(txB,))
        blockA = Block(block_id=bidA, parent_id=parent_id, slot=slot,
                       proposer_idx=self.id, transactions=(txA,))
        payloadA = BlockAnnouncementPayload(slot=slot, block_id=bidA,
                                            parent_id=parent_id,
                                            transactions=(txA,),
                                            proposer_idx=self.id)
        payloadB = BlockAnnouncementPayload(slot=slot, block_id=bidB,
                                            parent_id=parent_id,
                                            transactions=(txB,),
                                            proposer_idx=self.id)
        self._record_announce(blockA, t)            # self-prefer A, arm poll
        lo, hi = split_recipients(self)
        for dst in lo:
            self.send(dst, "BLOCK-ANNOUNCEMENT", payloadA, t)
        for dst in hi:
            self.send(dst, "BLOCK-ANNOUNCEMENT", payloadB, t)

    def _handle_query(self, msg, t):
        p = msg.payload
        if not isinstance(p, QueryPayload):
            self._reject(reason="malformed_payload", t=t, msg_type=msg.type)
            return
        cs = self._conflict_set_for(p.block_id)
        if cs is not None and len(cs.members) >= 2:
            others = sorted(b for b in cs.members if b != cs.preference)
            preferred = others[0] if others else cs.preference
        else:
            preferred = cs.preference if cs is not None else p.block_id
        self.send(msg.src, "QUERY-RESPONSE",
                  QueryResponsePayload(request_id=p.request_id,
                                       preferred_block_id=preferred), t)
