"""Test doubles + bootstrap harness for the T25 cross-component suite.

T25 wires the three W4 subsystems together for the first time: the
discrete-event scheduler (T21), the shared-layer Node (T22), and the honest
Network (T23). The per-subsystem suites each drive a 2-node ping-pong; this
suite drives 4/7/10-node scenarios through the same six-phase bootstrap
(simulation-design.md §7.2).

No real protocol FSM exists yet (PBFT = T28, etc.), so the nodes here are
minimal: `BroadcastNode` exercises message exchange, `TimerNode` exercises
the scheduler's `(t, node_id, seq)` dispatch order.
"""
from __future__ import annotations

from nodes import Node
from scheduler import Delivery, PhaseAdvance, Scheduler, TimerFire
from network import Network


class BroadcastNode(Node):
    """On start, broadcasts one TOKEN to every peer; records each inbound
    message. Non-recursive — recipients do not re-broadcast — so a run
    reaches quiescence after exactly one round of `n*(n-1)` deliveries."""

    def __init__(self, node_id, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.received: list[tuple[int, str]] = []   # (src, type) per inbound

    def _on_start(self, t):
        self.broadcast("TOKEN", {"from": self.id}, t)

    def _on_message(self, msg, t):
        self.received.append((msg.src, msg.type))

    def _on_timer(self, timer_id, payload, t):
        pass


class TimerNode(Node):
    """On start, sets three timers in a deliberately non-canonical order:
    the LATE timer (fires at t=200) is submitted *before* the two EARLY
    timers (fire at t=100), and the two EARLY timers share a fire time so
    the per-Node `seq` tie-break is what separates them. Every fired timer
    appends to the shared `fired` list, so the test can assert dispatch
    order is `(t, node_id, seq)` regardless of submission order."""

    FIRE_EARLY = 100.0
    FIRE_LATE = 200.0

    # Submission order within _on_start (see _on_start below). The scheduler
    # assigns per-Node seq in this order; canonical dispatch order is NOT this.
    SUBMIT_ORDER = ("late", "early1", "early2")

    def __init__(self, node_id, fired, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.fired = fired   # shared list, mutated by every node's _on_timer

    def _on_start(self, t):
        self.set_timer("late", self.FIRE_LATE - t, {"tag": "late"}, t)
        self.set_timer("early1", self.FIRE_EARLY - t, {"tag": "early1"}, t)
        self.set_timer("early2", self.FIRE_EARLY - t, {"tag": "early2"}, t)

    def _on_message(self, msg, t):
        pass

    def _on_timer(self, timer_id, payload, t):
        self.fired.append((t, self.id, payload["tag"]))


def build_and_run(nodes, phases, global_seed):
    """Six-phase bootstrap (simulation-design.md §7.2) over the real
    Scheduler + Network, then run to a stop condition.

    `nodes` is started in list order — callers that need a scrambled start
    order (the ordering test) pass the list pre-shuffled. Returns the
    `RunResult`, the captured delivery stream, and the captured dispatch
    stream (one `(t, node_id, seq, event_class)` tuple per heap event).
    """
    sched = Scheduler()
    net = Network(sched, tuple(phases), global_seed)
    deliveries: list = []
    dispatched: list = []

    def sink(t, nid, seq, ev):
        # event_sink also receives Node.emit side-channel events as a bare
        # ("emit", ...) tuple (scheduler.py bind()); those are not heap
        # events, so the isinstance filters exclude them.
        if isinstance(ev, Delivery):
            deliveries.append(
                (ev.msg.src, ev.msg.dst, ev.msg.type, ev.msg.t_sent, t))
        if isinstance(ev, (Delivery, TimerFire, PhaseAdvance)):
            dispatched.append((t, nid, seq, type(ev).__name__))

    sched.event_sink = sink
    for n in nodes:                       # phase 2: register
        net.register(n)
    sched.bind_network(net)               # phase 3: PhaseAdvance target
    for n in nodes:                       # phase 3: split bind
        sched.bind(n)
        net.bind(n)
    net.start()                           # phase 5: arm phase rollover
    for n in nodes:                       # phase 5: kickoff
        n.start(0.0)
    result = sched.run()                  # phase 6
    return result, deliveries, dispatched
