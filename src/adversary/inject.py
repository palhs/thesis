"""The delay-emission injection seam (T51, spec §3.1).

``inject_delay`` re-wraps each slow node's honest bound ``send`` / ``broadcast``
(set by ``Network.bind`` during ``build_run``) so that every outbound emission
is delivered ``mult·ref`` seconds late. The honest network adds its normal
delivery delay on top. Because ``mult`` is FIXED, the shift is a deterministic
constant -- no adversary RNG is consumed, so each slow node's protocol RNG
stream is byte-identical to honest; the node is only *late* (spec §8).

This realises the node-model.md §9 ``delayer`` cell (gate ``broadcast`` /
``send``). Intercepting at the bound outbound API is behaviourally identical to
FSM-level dispatch for delay -- which neither changes payloads nor drops/forks
messages -- and far less invasive (spec §3.2 / the node-model.md §9 Revision).
T52 reuses THIS seam: ``inject_offline`` re-wraps the same bound outbound API
to DROP every emission (offline = drop, no FSM hook). Only T53 (equivocate),
which forks payloads per-recipient, will need deeper FSM hooks.

Empty ``slow_ids`` is a strict no-op: the f=0 control is byte-identical to a
plain honest static-baseline run (the finality_delay_ratio denominator anchor).
"""
from __future__ import annotations

from config.schema import RunHandle

from .profiles import DelayProfile, OfflineProfile


def _delayed_send(honest_send, shift):
    """A send that shifts t_sent forward by `shift` (factory avoids the
    closure late-binding trap in the inject loop)."""
    def send(dst, type, payload, t):
        honest_send(dst, type, payload, t + shift)
    return send


def _delayed_broadcast(honest_broadcast, shift):
    """A broadcast that shifts t_sent forward by `shift`."""
    def broadcast(type, payload, t):
        honest_broadcast(type, payload, t + shift)
    return broadcast


def _wrap_outbound(handle, ids, profile, send_factory, broadcast_factory,
                   *, who: str) -> None:
    """Shared bind-seam wrap: attach `profile` to each node in `ids` and rebind
    its honest `send`/`broadcast` through the supplied factories. Call AFTER
    build_run, BEFORE run_to_completion. No-op when `ids` is empty.

    `who` only labels the double-injection error. The factories take the node's
    honest bound fn and return the replacement (delay shifts t; offline drops).
    """
    if not ids:
        return
    for nid in ids:
        node = handle.nodes[nid]
        if node.adversary is not None:
            raise RuntimeError(
                f"{who}: node {nid} already has an adversary profile "
                f"{node.adversary!r}; double-injection would silently stack")
        node.adversary = profile
        node.send = send_factory(node.send)
        node.broadcast = broadcast_factory(node.broadcast)


def inject_delay(handle: RunHandle, slow_ids: tuple[int, ...],
                 mult: float, ref: float, intensity: float) -> None:
    """Re-wrap slow nodes' outbound API to emit `mult·ref` s late. (T51 §3.1.)

    Behaviour byte-identical to the pre-refactor inject_delay — guarded by the
    existing TestInjectDelay suite and the T51 byte-identical CSV re-run.

    Call AFTER ``build_run`` and BEFORE ``run_to_completion``. Mutates the
    nodes in place. A no-op when ``slow_ids`` is empty.

    - ``handle``    -- the RunHandle from build_run (honest, fully bound).
    - ``slow_ids``  -- the slow-node ids (from ``select.slow_node_ids``).
    - ``mult``      -- m, the delay multiple.
    - ``ref``       -- the protocol round cadence in seconds. All slow nodes
                       in a single-protocol run share one cadence, so a scalar
                       ref (not a per-node map) is sufficient here; shift =
                       mult·ref. (Ratifies the spec §3.1 ``ref_by_node`` sketch
                       down to the uniform-cadence case T51 actually needs.)
    - ``intensity`` -- the realized slow-node fraction f, recorded on the
                       profile for provenance.
    """
    if not slow_ids:
        return
    shift = mult * ref
    profile = DelayProfile(nodes=tuple(slow_ids), intensity=intensity,
                           mult=mult)
    _wrap_outbound(handle, slow_ids, profile,
                   lambda honest: _delayed_send(honest, shift),
                   lambda honest: _delayed_broadcast(honest, shift),
                   who="inject_delay")


def _dropped_send(honest_send):
    """A send that drops the emission entirely (offline node, T52)."""
    def send(dst, type, payload, t):
        return
    return send


def _dropped_broadcast(honest_broadcast):
    """A broadcast that drops the emission entirely (offline node, T52)."""
    def broadcast(type, payload, t):
        return
    return broadcast


def inject_offline(handle: RunHandle, offline_ids: tuple[int, ...],
                   intensity: float) -> None:
    """Re-wrap offline nodes' outbound API to drop every emission (T52 §3.2).

    The node still receives and runs its FSM; it just emits nothing, so it
    contributes to no quorum/poll — the consensus definition of a silent
    crash-faulty / non-participating validator (adversary-model.md §4). No
    magnitude axis. No adversary RNG consumed → per-cell byte-identical re-run;
    empty `offline_ids` is a strict no-op (== honest static-baseline).
    """
    profile = OfflineProfile(nodes=tuple(offline_ids), intensity=intensity)
    _wrap_outbound(handle, offline_ids, profile,
                   _dropped_send, _dropped_broadcast, who="inject_offline")
