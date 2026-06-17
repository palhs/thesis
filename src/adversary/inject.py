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
T52/T53 will need deeper FSM hooks; T51 does not.

Empty ``slow_ids`` is a strict no-op: the f=0 control is byte-identical to a
plain honest static-baseline run (the finality_delay_ratio denominator anchor).
"""
from __future__ import annotations

from config.schema import RunHandle

from .profiles import DelayProfile


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


def inject_delay(handle: RunHandle, slow_ids: tuple[int, ...],
                 mult: float, ref: float, intensity: float) -> None:
    """Re-wrap the slow nodes' outbound API to emit `mult·ref` s late.

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
    for nid in slow_ids:
        node = handle.nodes[nid]
        if node.adversary is not None:
            raise RuntimeError(
                f"inject_delay: node {nid} already has an adversary profile "
                f"{node.adversary!r}; double-injection would silently stack "
                f"the delay shift")
        node.adversary = profile
        node.send = _delayed_send(node.send, shift)
        node.broadcast = _delayed_broadcast(node.broadcast, shift)
