# src/pbft/messages.py
"""PBFT wire-payload dataclasses (T28 spec § 4).

Realises `wiki/concepts/message-types.md` § 3 for the PBFT row set. T28
only constructs `PrePreparePayload`; the other four are declared so T29
grows by filling in handlers, not by adding new dataclasses.

The shared `Message` envelope (src.nodes.message.Message) carries these
as its `payload` field; envelope-level `src` / `dst` / `t_sent` are never
duplicated in the payload (`message-types.md` § 1).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PrePreparePayload:
    """`PRE-PREPARE` wire payload (message-types.md § 3).

    `request_payload` is `bytes` here (the v1 abstraction does not split
    transactions); widens to `list[Transaction]` if T19/T27 grows a
    per-transaction model (spec § 4 / § 12).
    """
    view: int
    seq: int
    request_digest: bytes
    request_payload: bytes


# --- T29 placeholders. Declared, not consumed in T28. ---

@dataclass(frozen=True)
class PreparePayload:
    view: int
    seq: int
    request_digest: bytes


@dataclass(frozen=True)
class CommitPayload:
    view: int
    seq: int
    request_digest: bytes


@dataclass(frozen=True)
class ViewChangePayload:
    new_view: int
    last_stable_seq: int
    prepared: list[tuple[int, int, bytes, bytes]] = field(default_factory=list)
    # each tuple: (view, seq, request_digest, request_payload)


@dataclass(frozen=True)
class NewViewPayload:
    new_view: int
    vc_proofs: list[ViewChangePayload] = field(default_factory=list)
    reissued: list[PrePreparePayload] = field(default_factory=list)


# --- T70 finding #1: client-observed finality. ---

@dataclass(frozen=True)
class ReplyPayload:
    """`REPLY` wire payload (T70 finding #1).

    The paper's client-observed finality is one network hop past the
    internal 2f+1 COMMIT quorum: on COMMITTED-local each replica sends a
    REPLY to the client, which finalizes the request on f+1 matching
    replies. The harness has no separate client node, so the primary of
    the committing view (node = view mod n) doubles as the client-reply
    collector. `replica_id` lets the collector count REPLYs from distinct
    replicas (a single replica's duplicate REPLY counts once).
    """
    view: int
    seq: int
    request_digest: bytes
    replica_id: int
