"""The honest inter-node delivery layer (network-model.md, T15/T23).

Design spec: docs/superpowers/specs/2026-05-19-t23-network-design.md
"""
from __future__ import annotations

import hashlib
import random

from nodes import Message, Node
from scheduler import Delivery, PhaseAdvance, Scheduler

from .phases import NodeId, Phase, SimTime, validate_timeline


def _network_seed(global_seed: int) -> int:
    """Process-stable 64-bit seed for the network RNG (design spec Decision D).

    blake2b, not hash() — Python's hash() of a str is process-randomised
    (PYTHONHASHSEED), which would break byte-identical replay. Mirrors the
    node-model.md §8 fix applied to the per-Node RNG.
    """
    digest = hashlib.blake2b(b"network:" + str(global_seed).encode(),
                             digest_size=8).digest()
    return int.from_bytes(digest, "big")


class Network:
    """System-level honest delivery infrastructure shared by every Node.

    Honest infrastructure only — all adversary semantics are owned by T18
    and attach at the Node level (network-model.md §6).
    """

    def __init__(self, scheduler: Scheduler,
                 phases: tuple[Phase, ...], global_seed: int) -> None:
        self.scheduler = scheduler
        self.phases: tuple[Phase, ...] = tuple(phases)
        self.registry: dict[NodeId, Node] = {}
        self.net_rng = random.Random(_network_seed(global_seed))
        self._phase_idx: int = 0
        self._started: bool = False

    def register(self, node: Node) -> None:
        """Bootstrap phase 2: make `node` resolvable as a delivery target."""
        if node.id in self.registry:
            raise ValueError(
                f"Network.register: NodeId {node.id} already registered")
        self.registry[node.id] = node

    def bind(self, node: Node) -> None:
        """Bootstrap phase 3: wire the network half of the outbound API.

        The scheduler's bind() wires set_timer/cancel_timer/emit; this wires
        send/broadcast (simulation-design.md §7.2 split bind). `type` shadows
        the builtin to match the node-model.md §7 signature.
        """
        node.send = lambda dst, type, payload, t: self.submit_unicast(
            node.id, dst, type, payload, t)
        node.broadcast = lambda type, payload, t: self.submit_broadcast(
            node.id, type, payload, t)

    def start(self) -> None:
        """Bootstrap phase 5: validate the timeline and arm phase rollover.

        Schedules one PhaseAdvance per *interior* boundary. The final phase's
        t_end (possibly math.inf) is never scheduled — there is no phase after
        it, and Scheduler.schedule rejects non-finite t. validate_timeline's
        finite-interior-boundary check guarantees every scheduled t is finite.
        """
        if self._started:
            raise RuntimeError("Network.start() called twice")
        validate_timeline(self.phases, set(self.registry))
        for i in range(len(self.phases) - 1):
            self.scheduler.schedule(
                PhaseAdvance(i + 1), self.phases[i].t_end,
                Scheduler.PHASE_NODE_ID)
        self._started = True

    def advance_phase(self, phase_id: int) -> None:
        """Scheduler-dispatched PhaseAdvance handler: move the active-phase
        pointer (design spec §3a / Decision C).

        No boundary race: PhaseAdvance carries node_id = -1, which sorts
        before every real NodeId at the same t, so the pointer advances
        before any Delivery/TimerFire at that t — realising the half-open
        [t_start, t_end) convention.
        """
        if not (0 <= phase_id < len(self.phases)):
            raise ValueError(
                f"advance_phase: phase_id={phase_id} out of range "
                f"[0, {len(self.phases)})")
        if phase_id != self._phase_idx + 1:
            raise RuntimeError(
                f"advance_phase: non-monotonic transition "
                f"{self._phase_idx} -> {phase_id} (expected +1)")
        self._phase_idx = phase_id

    def _guard_started(self) -> None:
        if not self._started:
            raise RuntimeError("Network.submit_* called before start()")

    def submit_unicast(self, src: NodeId, dst: NodeId,
                       type: str, payload: object,
                       t_sent: SimTime) -> None:
        """Outbound API: deliver `payload` to one peer (node-model.md §7)."""
        self._guard_started()
        self._try_deliver(src, dst, type, payload, t_sent)

    def submit_broadcast(self, src: NodeId,
                         type: str, payload: object,
                         t_sent: SimTime) -> None:
        """Outbound API: deliver `payload` to the full registry minus sender.

        v1 broadcast set = every registered Node except `src` (design spec
        Decision B; the FSM active-validator-set seam arrives with T28).
        Recipients are iterated in sorted(NodeId) order so per-recipient
        delay samples are consumed deterministically (network-model-phases.md
        §6.3). broadcast is per-recipient independent — not atomic.
        """
        self._guard_started()
        for dst in sorted(self.registry):
            if dst != src:
                self._try_deliver(src, dst, type, payload, t_sent)

    def _try_deliver(self, src: NodeId, dst: NodeId,
                     type: str, payload: object,
                     t_sent: SimTime) -> None:
        """The five-step delivery pipeline (network-model.md §1).

        Sampling order is pinned (network-model-phases.md §6.2): drop coin
        (consumes RNG) -> partition check (no RNG) -> delay sample (consumes
        RNG). A partition-dropped message consumes no delay sample.
        """
        if dst not in self.registry:                       # 1. resolve
            raise KeyError(
                f"submit: dst={dst} not registered (configuration error)")
        phase = self.phases[self._phase_idx]
        if self.net_rng.random() < phase.p_drop:           # 2. drop coin
            return
        if any(p.blocks(src, dst) for p in phase.partitions):  # 3. partition
            return
        delay = phase.delay.sample(self.net_rng)           # 4. delay
        msg = Message(src=src, dst=dst, type=type, payload=payload,
                      t_sent=t_sent)
        self.scheduler.schedule(Delivery(msg), t_sent + delay, dst)  # 5.
