"""SnowmanNode (design spec §6).

Implements the honest-path Snowman protocol over the W3 stack:
  - Slot timer + round-robin proposer emits BLOCK-ANNOUNCEMENT each slot.
  - Each block is polled concurrently via a per-block ("poll", block_id)
    timer. A round samples K peers, sends QUERY, collects QUERY-RESPONSE.
  - close_round applies the full Snowball update; counter >= beta -> ACCEPTED,
    emitting `decided`.
"""
from __future__ import annotations

from typing import Any, Sequence

from nodes import Message, Node

from .block import GENESIS_ID, Block, Chain, ConflictSet, CSState, hash_block
from .messages import (
    BlockAnnouncementPayload,
    QueryPayload,
    QueryResponsePayload,
)
from .parameters import snowman_parameters
from .poll import Poll, close_round, on_response


POLL_DELAY: float = 1e-9

SNOWMAN_ANNOUNCED = "snowman_announced"
SNOWMAN_POLL_STARTED = "snowman_poll_started"
SNOWMAN_POLL_CLOSED = "snowman_poll_closed"
SNOWMAN_REJECTED = "snowman_rejected"


class SnowmanNode(Node):
    """Honest Snowman validator (design spec §6)."""

    def __init__(
        self,
        node_id: int,
        weight: float,
        endpoint: object,
        global_seed: int,
        *,
        n: int,
        slot_duration: float = 1.0,
        beta: int = 15,
        K: int | None = None,
        alpha_p: int | None = None,
        alpha_c: int | None = None,
        workload: Sequence[tuple[bytes, ...]] | None = None,
        query_timeout: float | None = None,
    ) -> None:
        """workload: indexed by slot; element = batch tuple. The proposer
        at slot s carries workload[s]; missing/empty slot -> empty batch."""
        super().__init__(node_id, weight, endpoint, global_seed)
        if n < 2:
            raise ValueError(f"n must be >= 2, got {n}")
        if not 0 <= node_id < n:
            raise ValueError(f"node_id {node_id} outside [0, {n})")
        if slot_duration <= 0:
            raise ValueError(
                f"slot_duration must be positive, got {slot_duration}")
        K_d, p_d, c_d = snowman_parameters(n)
        self.n: int = n
        self.K: int = K if K is not None else K_d
        self.alpha_p: int = alpha_p if alpha_p is not None else p_d
        self.alpha_c: int = alpha_c if alpha_c is not None else c_d
        self.beta: int = beta
        self.slot_duration: float = slot_duration
        self.workload: list[tuple[bytes, ...]] = list(workload or [])
        # T52: optional query/response timeout. None => no timer is ever
        # scheduled and the code path is byte-identical to the pre-T52 node
        # (so the T51 delay sweep, which never passes this, is unchanged).
        self.query_timeout: float | None = query_timeout

        self.chain: Chain = Chain()
        self.conflict_sets: dict[bytes, ConflictSet] = {}    # parent_id -> CS
        self.polls: dict[bytes, Poll] = {}                   # block_id -> current Poll
        self._next_request_id: int = 0
        self._peers_minus_self_cache: tuple[int, ...] | None = None

    # --- Lifecycle (design spec §6.2). ---

    def _on_start(self, t: float) -> None:
        """Arm slot 0 at slot_duration."""
        self.set_timer("slot", self.slot_duration, 0, t)

    def _on_message(self, msg: Message, t: float) -> None:
        if msg.type == "BLOCK-ANNOUNCEMENT":
            self._handle_announce(msg, t)
        elif msg.type == "QUERY":
            self._handle_query(msg, t)
        elif msg.type == "QUERY-RESPONSE":
            self._handle_response(msg, t)
        else:
            self._reject(reason="unknown_type", t=t, msg_type=msg.type)

    def _on_timer(self, timer_id: Any, payload: Any, t: float) -> None:
        if timer_id == "slot":
            slot = payload
            if slot % self.n == self.id:
                self._propose(slot, t)
            self.set_timer("slot", self.slot_duration, slot + 1, t)
        elif isinstance(timer_id, tuple) and timer_id[0] == "poll":
            block_id = timer_id[1]
            self._start_poll_round(block_id, t)
        elif isinstance(timer_id, tuple) and timer_id[0] == "query_timeout":
            _, block_id, request_id = timer_id
            self._on_query_timeout(block_id, request_id, t)

    # --- Proposer (design spec §6.3). ---

    def _propose(self, slot: int, t: float) -> None:
        """Build, announce, and self-record a new block at this slot."""
        parent_id = self.chain.tip
        # T41: workload is indexed by SLOT; the block at slot s carries
        # workload[s] directly. Every round-robin proposer holds the same
        # slot-indexed list, so the block at a given slot is identical no
        # matter which node proposes it. No/empty workload -> empty batch.
        txs: tuple[bytes, ...] = (
            self.workload[slot]
            if (self.workload and slot < len(self.workload))
            else ())
        block_id = hash_block(slot=slot, parent_id=parent_id,
                              proposer_idx=self.id, transactions=txs)
        block = Block(block_id=block_id, parent_id=parent_id, slot=slot,
                      proposer_idx=self.id, transactions=txs)
        payload = BlockAnnouncementPayload(
            slot=slot, block_id=block_id, parent_id=parent_id,
            transactions=txs, proposer_idx=self.id)
        # Self-record before broadcast (Network.broadcast excludes sender).
        self._record_announce(block, t)
        self.broadcast("BLOCK-ANNOUNCEMENT", payload, t)

    # --- Inbound handlers. ---

    def _handle_announce(self, msg: Message, t: float) -> None:
        p = msg.payload
        if not isinstance(p, BlockAnnouncementPayload):
            self._reject(reason="malformed_payload", t=t, msg_type=msg.type)
            return
        block = Block(block_id=p.block_id, parent_id=p.parent_id,
                      slot=p.slot, proposer_idx=p.proposer_idx,
                      transactions=p.transactions)
        self._record_announce(block, t)

    def _handle_query(self, msg: Message, t: float) -> None:
        p = msg.payload
        if not isinstance(p, QueryPayload):
            self._reject(reason="malformed_payload", t=t, msg_type=msg.type)
            return
        cs = self._conflict_set_for(p.block_id)
        # Permissive default when the conflict set is unknown: respond with
        # the queried block_id itself (design spec §3 + message-types §5
        # Revisions). Honest-path baseline never exercises this branch.
        preferred = cs.preference if cs is not None else p.block_id
        response = QueryResponsePayload(
            request_id=p.request_id, preferred_block_id=preferred)
        self.send(msg.src, "QUERY-RESPONSE", response, t)

    def _handle_response(self, msg: Message, t: float) -> None:
        p = msg.payload
        if not isinstance(p, QueryResponsePayload):
            self._reject(reason="malformed_payload", t=t, msg_type=msg.type)
            return
        # Look up the in-flight poll by request_id (stale responses drop).
        poll: Poll | None = None
        for candidate in self.polls.values():
            if candidate.request_id == p.request_id and not candidate.closed:
                poll = candidate
                break
        if poll is None:
            return                       # stale or unknown; drop
        cs = self._conflict_set_for(poll.block_id)
        early_close = on_response(
            poll=poll, preferred_block_id=p.preferred_block_id,
            current_preference=cs.preference,
            alpha_c=self.alpha_c, K=self.K)
        if early_close or poll.responses_received == self.K:
            self._close_and_continue(poll, cs, t)

    # --- Internal helpers. ---

    def _record_announce(self, block: Block, t: float) -> None:
        """Idempotent block-registration seam: link into chain, lazy-create
        conflict set, arm first poll round. Used by both the proposer
        self-record path and the BLOCK-ANNOUNCEMENT handler."""
        cs = self.conflict_sets.setdefault(
            block.parent_id, ConflictSet(parent_id=block.parent_id))
        if block.block_id in cs.members:
            return                       # idempotent
        cs.add_block(block)
        self.chain.on_announce(block)
        self.emit(SNOWMAN_ANNOUNCED,
                  {"block_id": block.block_id,
                   "parent_id": block.parent_id,
                   "slot": block.slot,
                   "proposer_idx": block.proposer_idx}, t)
        # Arm the first poll round for this block.
        self.set_timer(("poll", block.block_id), POLL_DELAY,
                       block.block_id, t)

    def _start_poll_round(self, block_id: bytes, t: float) -> None:
        """Begin a new poll round: sample K peers, send K QUERYs, emit event."""
        cs = self._conflict_set_for(block_id)
        if cs is None or cs.state is CSState.ACCEPTED:
            return                       # nothing to poll for
        self._next_request_id += 1
        request_id = self._next_request_id
        peers = tuple(self.rng.sample(self._peers_minus_self(), self.K))
        poll = Poll(block_id=block_id, request_id=request_id, peers=peers)
        self.polls[block_id] = poll
        self.emit(SNOWMAN_POLL_STARTED,
                  {"block_id": block_id, "request_id": request_id,
                   "peers": peers}, t)
        query = QueryPayload(request_id=request_id, block_id=block_id)
        for peer_id in peers:
            self.send(peer_id, "QUERY", query, t)
        # T52: opt-in query timeout. Key on (block_id, request_id) so a stale
        # timeout from an earlier round of the same block cannot close a newer
        # one. None => no timer scheduled (T51 path unchanged).
        if self.query_timeout is not None:
            self.set_timer(("query_timeout", block_id, request_id),
                           self.query_timeout, None, t)

    def _on_query_timeout(self, block_id: bytes, request_id: int,
                          t: float) -> None:
        """T52: a poll round's query timeout fired. If the round is still the
        in-flight poll for this block, still open, and its request_id matches
        (stale-guard), close it NOW with the responses received so far via the
        same close+advance path a normal close uses. Otherwise no-op."""
        if self.query_timeout is None:
            return
        poll = self.polls.get(block_id)
        if poll is None or poll.closed or poll.request_id != request_id:
            return                       # already closed/gone or stale; no-op
        cs = self._conflict_set_for(block_id)
        if cs is None:
            return
        self._close_and_continue(poll, cs, t)

    def _close_and_continue(self, poll: Poll, cs: ConflictSet,
                            t: float) -> None:
        """Apply close_round; emit events; arm next poll or finalise.

        T52: when a query timeout is configured, cancel this round's pending
        timeout so it becomes a no-op once the round has closed (covers both
        the normal early/quorum close and the timeout-driven close itself)."""
        if self.query_timeout is not None:
            self.cancel_timer(
                ("query_timeout", poll.block_id, poll.request_id))
        outcome = close_round(
            conflict_set=cs, poll=poll,
            alpha_p=self.alpha_p, alpha_c=self.alpha_c, beta=self.beta)
        self.emit(SNOWMAN_POLL_CLOSED,
                  {"block_id": poll.block_id,
                   "request_id": poll.request_id,
                   "agree_per_block": dict(poll.agree_per_block),
                   "flipped": outcome.flipped,
                   "new_preference": outcome.new_preference,
                   "counter": outcome.counter,
                   "accepted": outcome.accepted}, t)
        if outcome.accepted:
            block = cs.members[poll.block_id]
            self.chain.on_accept(block)
            self._emit_decided(value=poll.block_id,
                               instance_id=poll.block_id, t=t)
            del self.polls[poll.block_id]
        else:
            self.set_timer(("poll", poll.block_id), POLL_DELAY,
                           poll.block_id, t)

    def _peers_minus_self(self) -> tuple[int, ...]:
        if self._peers_minus_self_cache is None:
            self._peers_minus_self_cache = tuple(
                i for i in range(self.n) if i != self.id)
        return self._peers_minus_self_cache

    def _conflict_set_for(self, block_id: bytes) -> ConflictSet | None:
        for cs in self.conflict_sets.values():
            if block_id in cs.members:
                return cs
        return None

    def _reject(self, *, reason: str, t: float, **fields: Any) -> None:
        self.emit(SNOWMAN_REJECTED, {"reason": reason, **fields}, t)
