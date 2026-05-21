# tests/pbft/_helpers.py
"""Shared fixtures for the T31 PBFT unit-test battery.

The T28/T29 test files (test_node_voting.py etc.) each carry their own
_node / _capturers / _kickoff. The T31 battery — test_happy_path,
test_quorum_thresholds, test_view_change_timeout, test_message_loss,
test_multi_round, test_protocol_edge_cases — shares this module instead,
the same way every other suite uses a `_helpers.py` (tests/integration,
tests/network, tests/nodes).

Idiom (unchanged from the T29 suite): one PBFTNode in isolation, the
bind-time outbound API replaced with capturers, kickoff to RUNNING,
hand-built Messages, direct on_message / on_timer calls.

Not a test module — the `_` prefix keeps it out of `unittest discover`
(which matches test*.py).
"""
from __future__ import annotations

from typing import Any

from nodes import Message
from nodes.lifecycle import Lifecycle
from pbft.digest import digest
from pbft.messages import (
    CommitPayload,
    NewViewPayload,
    PreparePayload,
    PrePreparePayload,
    ViewChangePayload,
)
from pbft.node import PBFTNode


# --- Quorum arithmetic ----------------------------------------------------

def f_of(n: int) -> int:
    """Byzantine fault threshold f = (n-1)//3 — the value PBFTNode computes."""
    return (n - 1) // 3


def quorum(n: int) -> int:
    """PBFT prepare/commit quorum, 2f+1."""
    return 2 * f_of(n) + 1


def others(node_id: int, n: int, count: int) -> list[int]:
    """`count` distinct validator ids in [0, n) other than `node_id`,
    lowest-first. Used to pick the senders of peer votes."""
    pool = [i for i in range(n) if i != node_id]
    assert count <= len(pool), f"asked for {count} peers, only {len(pool)}"
    return pool[:count]


# --- Node construction ----------------------------------------------------

def make_node(node_id: int, n: int, *, view: int = 0,
              vc_delay: float = 10.0, propose_delay: float = 1.0,
              workload: list[bytes] | None = None) -> PBFTNode:
    """A PBFTNode with the test-standard weight/endpoint/seed."""
    return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                    global_seed=42, n=n, workload=workload,
                    propose_delay=propose_delay, initial_view=view,
                    vc_delay=vc_delay)


class Capture:
    """Records the four outbound API channels a PBFTNode drives."""

    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict, float]] = []
        self.broadcasts: list[tuple[str, object, float]] = []
        self.sends: list[tuple] = []
        self.timers: list[tuple[Any, float, object, float]] = []
        self.cancels: list[Any] = []

    def events(self, event_type: str) -> list[tuple[str, dict, float]]:
        return [e for e in self.emitted if e[0] == event_type]

    def count(self, event_type: str) -> int:
        return len(self.events(event_type))

    def broadcast_types(self) -> list[str]:
        return [b[0] for b in self.broadcasts]

    def count_broadcast(self, msg_type: str) -> int:
        return sum(1 for b in self.broadcasts if b[0] == msg_type)

    def timer_ids(self) -> list[Any]:
        return [t[0] for t in self.timers]


def capturers(node: PBFTNode) -> Capture:
    """Replace the bind-time outbound API with capturers; return the
    Capture they record into."""
    cap = Capture()
    node.emit = lambda et, fields, t: cap.emitted.append((et, fields, t))
    node.broadcast = lambda ty, p, t: cap.broadcasts.append((ty, p, t))
    node.send = lambda *a, **kw: cap.sends.append((a, kw))
    node.set_timer = lambda tid, dl, p, t: cap.timers.append((tid, dl, p, t))
    node.cancel_timer = lambda tid: cap.cancels.append(tid)
    return cap


def kickoff(node: PBFTNode) -> None:
    """Force RUNNING without firing the real propose path. Node.on_message
    refuses a CREATED node; this is the minimum incantation."""
    node.status = Lifecycle.RUNNING


# --- Message builders -----------------------------------------------------
#
# `dst` defaults to 0 and is never read by the PBFT handlers (they key off
# `src` and `payload`); tests pass the recipient's id only for realism.

def pre_prepare(src: int, view: int, seq: int, batch: bytes, *,
                dst: int = 0, digest_override: bytes | None = None) -> Message:
    d = digest_override if digest_override is not None else digest(batch)
    pp = PrePreparePayload(view=view, seq=seq, request_digest=d,
                           request_payload=batch)
    return Message(src=src, dst=dst, type="PRE-PREPARE", payload=pp,
                   t_sent=0.0)


def prepare(src: int, view: int, seq: int, batch: bytes, *,
            dst: int = 0, digest_override: bytes | None = None) -> Message:
    d = digest_override if digest_override is not None else digest(batch)
    pp = PreparePayload(view=view, seq=seq, request_digest=d)
    return Message(src=src, dst=dst, type="PREPARE", payload=pp, t_sent=0.0)


def commit(src: int, view: int, seq: int, batch: bytes, *,
           dst: int = 0, digest_override: bytes | None = None) -> Message:
    d = digest_override if digest_override is not None else digest(batch)
    cp = CommitPayload(view=view, seq=seq, request_digest=d)
    return Message(src=src, dst=dst, type="COMMIT", payload=cp, t_sent=0.0)


def view_change(src: int, new_view: int, *,
                dst: int = 0, prepared=()) -> Message:
    vc = ViewChangePayload(new_view=new_view, last_stable_seq=-1,
                           prepared=list(prepared))
    return Message(src=src, dst=dst, type="VIEW-CHANGE", payload=vc,
                   t_sent=0.0)


def new_view(src: int, nv: int, *, vc_proofs, dst: int = 0,
             reissued=()) -> Message:
    payload = NewViewPayload(new_view=nv, vc_proofs=list(vc_proofs),
                             reissued=list(reissued))
    return Message(src=src, dst=dst, type="NEW-VIEW", payload=payload,
                   t_sent=0.0)


def vc_proofs(n: int, nv: int, *, count: int | None = None
              ) -> list[ViewChangePayload]:
    """`count` (default 2f+1) empty ViewChangePayloads for `nv` — the
    proof set a valid NEW-VIEW must carry."""
    if count is None:
        count = quorum(n)
    return [ViewChangePayload(new_view=nv, last_stable_seq=-1, prepared=[])
            for _ in range(count)]
