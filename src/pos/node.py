"""Simplified Casper FFG validator (design spec §6).

A `CasperNode(Node)` runs a slot timer: every `slot_duration` seconds the
round-robin proposer (`slot mod n`) builds a block on `chain.head` and
broadcasts BLOCK-PROPOSAL; once per epoch, at `attest_offset` into the
epoch, every node broadcasts an ATTESTATION carrying an FFG
`<source, target>` checkpoint vote. Per-target-epoch `EpochState` instances
aggregate stake-weighted votes; a supermajority link (>= 2/3 of total
stake) justifies the target, and two consecutive justifications finalise
the source (emitting the mandatory `decided` event once per epoch).

Genesis (slot 0, epoch 0) is pre-installed in every node's `Chain` and is
justified+finalised by construction, bootstrapping the FFG justify chain
(Decision F). T32 is honest-path only — no slashing detection, no
LMD-GHOST fork choice (Decision B).
"""
from __future__ import annotations

import logging
from typing import Any

from nodes import Message, Node

from .chain import Block, Chain, GENESIS_HASH, block_hash
from .epoch import EpochFSM, EpochState, VoteStatus
from .finality import evaluate as evaluate_ffg
from .messages import AttestationPayload, BlockProposalPayload, FFGVote
from .selection import stake_weighted_proposer


# Step-logging for the T70 accountable-safety demo. Library code never
# configures logging or attaches handlers — the demo enables it. All
# log.info(...) calls below are side-effect-free w.r.t. RNG and node state.
log = logging.getLogger("t70.casper")


CASPER_BLOCK_ACCEPTED = "casper_block_accepted"
CASPER_ATTESTED = "casper_attested"
CASPER_JUSTIFIED = "casper_justified"
CASPER_FINALISED = "casper_finalised"
CASPER_REJECTED = "casper_rejected"
CASPER_SLASHING = "casper_slashing"


def _hexor(h: bytes | None) -> str | None:
    return h.hex() if h is not None else None


class CasperNode(Node):
    """Simplified Casper FFG validator.

    Constructor parameters (positional set from Node.__init__, keyword-only
    past it; see design spec §6.1):
      n:               validator count (drives the slot mod n proposer
                       rule and the 2/3 stake quorum threshold).
      stake_table:     {node_id: stake} for every validator. A node needs
                       the full table to weight peer attestations; its
                       own `Node.weight` must equal `stake_table[node_id]`.
      slot_duration:   seconds between consecutive slot timer fires.
      slots_per_epoch: number of slots per epoch; the first block of each
                       epoch is its checkpoint.
      attest_offset:   slot offset within an epoch at which the node
                       attests (default: slots_per_epoch // 2, so the
                       checkpoint block has time to propagate).
      workload:        optional list indexed by slot; element = batch
                       tuple (`tuple[bytes, ...]`) of the transactions a
                       block proposed at that slot carries. The slot-`s`
                       proposer reads `workload[s]`, so the block content
                       is deterministic regardless of which node proposes.
                       None/empty or a slot past the end => empty block.
    """

    def __init__(self, node_id: int, weight: float, endpoint: object,
                 global_seed: int, *,
                 n: int,
                 stake_table: dict[int, float],
                 slot_duration: float = 1.0,
                 slots_per_epoch: int = 2,
                 attest_offset: int | None = None,
                 workload: list[bytes] | None = None) -> None:
        super().__init__(node_id, weight, endpoint, global_seed)
        self.global_seed: int = global_seed
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")
        if not 0 <= node_id < n:
            raise ValueError(f"node_id {node_id} outside [0, {n})")
        if slot_duration <= 0:
            raise ValueError(
                f"slot_duration must be positive, got {slot_duration}")
        if slots_per_epoch <= 0:
            raise ValueError(
                f"slots_per_epoch must be positive, got {slots_per_epoch}")
        if set(stake_table.keys()) != set(range(n)):
            raise ValueError(
                f"stake_table keys must be range({n}), "
                f"got {sorted(stake_table.keys())}")
        for vid, s in stake_table.items():
            if s < 0 or s != s or s == float("inf") or s == float("-inf"):
                raise ValueError(
                    f"stake_table[{vid}]={s} must be finite and non-negative")
        if sum(stake_table.values()) <= 0:
            raise ValueError(
                "stake_table total must be positive — an all-zero "
                "validator set would let the 2/3 threshold be met "
                "vacuously by an empty quorum")
        if stake_table[node_id] != weight:
            raise ValueError(
                f"stake_table[{node_id}]={stake_table[node_id]} "
                f"must equal weight={weight}")
        offset = (attest_offset if attest_offset is not None
                  else slots_per_epoch // 2)
        if not 0 <= offset < slots_per_epoch:
            raise ValueError(
                f"attest_offset {offset} outside [0, {slots_per_epoch})")
        self.n: int = n
        self.stake_table: dict[int, float] = dict(stake_table)
        self.total_stake: float = sum(stake_table.values())
        self.slot_duration: float = slot_duration
        self.slots_per_epoch: int = slots_per_epoch
        self.attest_offset: int = offset
        self.workload: list[bytes] = list(workload or [])
        # Cross-instance state (design spec §6.2).
        self.chain: Chain = Chain(slots_per_epoch)
        self.epoch_states: dict[int, EpochState] = {}
        # Bootstrap epoch 0 as justified+finalised (Decision F).
        genesis_state = EpochState(0)
        genesis_state.state = EpochFSM.FINALISED
        genesis_state.checkpoint_hash = GENESIS_HASH
        self.epoch_states[0] = genesis_state
        self.highest_justified: int = 0
        self.highest_finalised: int = 0
        self.decided_epochs: set[int] = set()
        # Accountable-safety state (T70, audit finding #3). Slashing spans
        # epochs (surround votes relate two different target epochs), so the
        # history lives on the node, not in any single per-epoch EpochState.
        #   vote_history: attester_idx -> list of FFGVote filed by that
        #                 attester (one entry per accepted distinct vote).
        #   _slashable:   attester_idx of every validator with >=1 detected
        #                 offence; backs slashable_stake_fraction().
        self.vote_history: dict[int, list[FFGVote]] = {}
        self._slashable: set[int] = set()

    # --- Lifecycle hooks (design spec §6.3, §6.4). ---

    def _on_start(self, t: float) -> None:
        """Schedule slot 1. Slot 0 is genesis; the loop proposes from 1."""
        self.set_timer("slot", self.slot_duration, 1, t)

    def _on_message(self, msg: Message, t: float) -> None:
        if msg.type == "BLOCK-PROPOSAL":
            self._handle_block_proposal(msg, t)
        elif msg.type == "ATTESTATION":
            self._handle_attestation(msg, t)
        else:
            self._reject(t, "unknown_type",
                         msg_type=msg.type, src=msg.src)

    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        if timer_id == "slot":
            self._on_slot(payload, t)
        # else: silent no-op.

    def _on_slot(self, slot: int, t: float) -> None:
        epoch = slot // self.slots_per_epoch
        if self._proposer_of(slot) == self.id:
            self._propose(slot, epoch, t)
        if epoch >= 1 and slot % self.slots_per_epoch == self.attest_offset:
            self._attest(epoch, slot, t)
        # Re-arm the slot timer unconditionally (proposer rotation).
        self.set_timer("slot", self.slot_duration, slot + 1, t)

    # --- Proposer selection (T33: stake-weighted random). ---

    def _proposer_of(self, slot: int) -> int:
        return stake_weighted_proposer(slot, self.stake_table,
                                       self.global_seed)

    # --- Propose (design spec §6.4 step 2). ---

    def _propose(self, slot: int, epoch: int, t: float) -> None:
        parent = self.chain.head
        txs: tuple[bytes, ...] = (
            self.workload[slot]
            if (self.workload and slot < len(self.workload)) else ()
        )
        bh = block_hash(slot=slot, parent_hash=parent.block_hash,
                        proposer_idx=self.id, transactions=txs)
        block = Block(slot=slot, epoch=epoch,
                      parent_hash=parent.block_hash, block_hash=bh,
                      transactions=txs, proposer_idx=self.id)
        payload = BlockProposalPayload(slot=slot, epoch=epoch,
                                       parent_hash=parent.block_hash,
                                       block_hash=bh, transactions=txs,
                                       proposer_idx=self.id)
        self.broadcast("BLOCK-PROPOSAL", payload, t)
        # Self-record (Decision C: Network.broadcast excludes the sender).
        self._accept_block(block, t)

    # --- Attest (design spec §6.4 step 3, Decision J). ---

    def _attest(self, epoch: int, slot: int, t: float) -> None:
        try:
            target_cp = self.chain.checkpoint(epoch)
        except KeyError:
            self._reject(t, "checkpoint_unavailable", epoch=epoch, slot=slot)
            return
        source_epoch = self.highest_justified
        # Symmetric to the target guard above: under heavy network delay a
        # node can mark an epoch justified (from aggregated FFG votes) before
        # that epoch's checkpoint BLOCK has been delivered locally, so the
        # source-checkpoint lookup can miss. A validator cannot form a valid
        # FFG vote without its source block, so it skips this slot's
        # attestation and retries on a later slot once the block arrives.
        # No-op under low delay (source block always present), so the T46 /
        # honest baselines are byte-identical. Exposed by the T47 heavy-tail
        # regime (see pos.md ## Revisions 2026-06-12).
        try:
            source_cp = self.chain.checkpoint(source_epoch)
        except KeyError:
            self._reject(t, "source_checkpoint_unavailable",
                         epoch=epoch, slot=slot, source_epoch=source_epoch)
            return
        ffg = FFGVote(source_epoch=source_epoch,
                      source_hash=source_cp.block_hash,
                      target_epoch=epoch,
                      target_hash=target_cp.block_hash)
        payload = AttestationPayload(slot=slot, epoch=epoch, ffg=ffg,
                                     attester_idx=self.id)
        self.broadcast("ATTESTATION", payload, t)
        self.emit(CASPER_ATTESTED, {"epoch": epoch, "slot": slot}, t)
        # Self-record (Decision C).
        self._file_ffg_vote(ffg, attester_idx=self.id, t=t)

    def _file_ffg_vote(self, ffg: FFGVote, attester_idx: int,
                       t: float) -> None:
        """Record one FFG vote into the target epoch's state and run the
        justify -> finalise transition check.

        Three outcomes (audit finding #3):
          - DUPLICATE: byte-identical re-delivery -> idempotent no-op, as
            before (Decision I). No history append, no detection, no emit.
          - CONFLICT:  same attester voted differently for this target epoch
            before -> a slashable signal. Run slashing detection against the
            attester's prior votes; the link stake is NOT re-counted (the
            offending second vote never justifies anything).
          - NEW:       a fresh, non-conflicting vote -> count its stake, run
            the FFG transition, and append it to the attester's history (so
            later votes can be checked for surround against it).
        """
        es = self._epoch_state(ffg.target_epoch)
        stake = self.stake_table[attester_idx]
        status = es.record_vote(ffg.source_epoch, attester_idx, stake,
                                source_hash=ffg.source_hash,
                                target_hash=ffg.target_hash)
        if status is VoteStatus.DUPLICATE:
            return                              # idempotent re-delivery
        if status is VoteStatus.CONFLICT:
            # Same target epoch, differing link: an outright DOUBLE VOTE.
            log.info(
                "double_vote attester=%d target_epoch=%d "
                "src=%d->tgt_hash=%s (conflicts prior vote)",
                attester_idx, ffg.target_epoch, ffg.source_epoch,
                _hexor(ffg.target_hash))
            self._flag_slashing("double_vote", attester_idx,
                                ffg=ffg, target_epoch=ffg.target_epoch, t=t)
            # The conflicting vote is still recorded in history so that a
            # subsequent vote can be surround-checked against it too.
            self._check_surround(attester_idx, ffg, t)
            self.vote_history.setdefault(attester_idx, []).append(ffg)
            return
        # status is NEW: honest path plus cross-epoch surround check.
        self._check_surround(attester_idx, ffg, t)
        self.vote_history.setdefault(attester_idx, []).append(ffg)
        self._run_ffg_transitions(ffg.source_epoch, ffg.target_epoch, t)

    # --- Accountable-safety detection (T70, audit finding #3). ---

    def _check_surround(self, attester_idx: int, ffg: FFGVote,
                        t: float) -> None:
        """Compare `ffg` against every prior vote by `attester_idx` for a
        SURROUND offence: links (s1,t1) and (s2,t2) with
        s1 < s2 < t2 < t1 (either ordering of new vs prior)."""
        s2, t2 = ffg.source_epoch, ffg.target_epoch
        for prior in self.vote_history.get(attester_idx, ()):
            s1, t1 = prior.source_epoch, prior.target_epoch
            if (s1 < s2 < t2 < t1) or (s2 < s1 < t1 < t2):
                log.info(
                    "surround_vote attester=%d wide=(%d,%d) inner=(%d,%d)",
                    attester_idx,
                    *( (s1, t1, s2, t2) if s1 < s2 else (s2, t2, s1, t1) ))
                self._flag_slashing(
                    "surround_vote", attester_idx,
                    ffg=ffg, prior=prior, t=t,
                    target_epoch=ffg.target_epoch)
                return

    def _flag_slashing(self, reason: str, attester_idx: int, *,
                       ffg: FFGVote, t: float,
                       prior: FFGVote | None = None,
                       target_epoch: int | None = None) -> None:
        """Mark `attester_idx` slashable and emit a `casper_slashing` event
        carrying the updated slashable-stake fraction."""
        self._slashable.add(attester_idx)
        frac = self.slashable_stake_fraction()
        fields: dict[str, Any] = {
            "reason": reason,
            "attester_idx": attester_idx,
            "source_epoch": ffg.source_epoch,
            "target_epoch": (target_epoch if target_epoch is not None
                             else ffg.target_epoch),
            "slashable_stake_fraction": frac,
        }
        if prior is not None:
            fields["prior_source_epoch"] = prior.source_epoch
            fields["prior_target_epoch"] = prior.target_epoch
        self.emit(CASPER_SLASHING, fields, t)
        log.info("slashing reason=%s attester=%d slashable_frac=%.4f",
                 reason, attester_idx, frac)

    def slashable_stake_fraction(self) -> float:
        """Fraction of total stake held by validators with >=1 detected
        slashable offence. Read accessor; never mutates state."""
        if self.total_stake <= 0:
            return 0.0
        slashed = sum(self.stake_table[a] for a in self._slashable)
        return slashed / self.total_stake

    def _run_ffg_transitions(self, source_epoch: int,
                             target_epoch: int, t: float) -> None:
        """Casper FFG two-round gadget (design spec §5.3): delegate the
        rule to `finality.evaluate` and apply the resulting transitions."""
        tgt = self._epoch_state(target_epoch)
        src = self._epoch_state(source_epoch)
        transitions = evaluate_ffg(
            source_epoch=source_epoch, target_epoch=target_epoch,
            link_stake=tgt.link_stake(source_epoch),
            total_stake=self.total_stake,
            source_state=src.state, target_state=tgt.state,
        )
        if not transitions.justified:
            return
        tgt.state = EpochFSM.JUSTIFIED
        self.highest_justified = max(self.highest_justified, target_epoch)
        self.emit(CASPER_JUSTIFIED,
                  {"epoch": target_epoch,
                   "checkpoint_hash": _hexor(tgt.checkpoint_hash)}, t)
        if transitions.finalised_source:
            src.state = EpochFSM.FINALISED
            self.highest_finalised = max(self.highest_finalised,
                                         source_epoch)
            self._finalise(source_epoch, src.checkpoint_hash, t)

    def _finalise(self, epoch: int, checkpoint_hash: bytes | None,
                  t: float) -> None:
        self.emit(CASPER_FINALISED,
                  {"epoch": epoch,
                   "checkpoint_hash": _hexor(checkpoint_hash)}, t)
        if epoch not in self.decided_epochs:
            self.decided_epochs.add(epoch)
            self._emit_decided(value=_hexor(checkpoint_hash),
                               instance_id=epoch, t=t)

    def _reject(self, t: float, reason: str, **fields) -> None:
        self.emit(CASPER_REJECTED, {"reason": reason, **fields}, t)

    # --- Message handlers (design spec §7). ---

    def _handle_block_proposal(self, msg: Message, t: float) -> None:
        bp = msg.payload
        if not isinstance(bp, BlockProposalPayload):
            self._reject(t, "malformed_payload",
                         msg_type="BLOCK-PROPOSAL", src=msg.src)
            return
        if msg.src != self._proposer_of(bp.slot):
            self._reject(t, "non_proposer", slot=bp.slot, src=msg.src)
            return
        if bp.epoch != bp.slot // self.slots_per_epoch:
            self._reject(t, "epoch_mismatch", slot=bp.slot, src=msg.src)
            return
        if block_hash(slot=bp.slot, parent_hash=bp.parent_hash,
                      proposer_idx=bp.proposer_idx,
                      transactions=bp.transactions) != bp.block_hash:
            self._reject(t, "hash_mismatch", slot=bp.slot, src=msg.src)
            return
        block = Block(slot=bp.slot, epoch=bp.epoch,
                      parent_hash=bp.parent_hash, block_hash=bp.block_hash,
                      transactions=bp.transactions,
                      proposer_idx=bp.proposer_idx)
        self._accept_block(block, t)

    def _handle_attestation(self, msg: Message, t: float) -> None:
        ap = msg.payload
        if not isinstance(ap, AttestationPayload):
            self._reject(t, "malformed_payload",
                         msg_type="ATTESTATION", src=msg.src)
            return
        if not 0 <= ap.attester_idx < self.n:
            self._reject(t, "attester_out_of_range", src=msg.src)
            return
        if ap.ffg.target_epoch != ap.epoch:
            self._reject(t, "epoch_mismatch", src=msg.src)
            return
        self._file_ffg_vote(ap.ffg, ap.attester_idx, t)

    def _accept_block(self, block: Block, t: float) -> None:
        """Shared block-acceptance seam: link into the chain, set the
        checkpoint hash on epoch boundaries, emit casper_block_accepted."""
        self.chain.add(block)
        if block.slot % self.slots_per_epoch == 0:
            self._epoch_state(block.epoch).checkpoint_hash = block.block_hash
        self.emit(CASPER_BLOCK_ACCEPTED,
                  {"slot": block.slot, "epoch": block.epoch,
                   "block_hash": block.block_hash.hex()}, t)

    # --- Internal helpers. ---

    def _epoch_state(self, epoch: int) -> EpochState:
        """Lazy-create the EpochState for `epoch` (Decision H — an
        ATTESTATION may arrive before the local checkpoint block)."""
        return self.epoch_states.setdefault(epoch, EpochState(epoch))
