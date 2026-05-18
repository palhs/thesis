"""End-to-end test: the Scheduler drives a 2-node ping-pong simulation.

Exercises the full six-phase bootstrap (simulation-design.md §7.2) and the
determinism contract (simulation-design-runtime.md §1).
"""
import unittest

from scheduler import Delivery, PhaseAdvance, Scheduler
from _stubs import SimpleMessage


class EchoNode:
    """Stub protocol Node: node 0 kicks off, node 1 echoes PING -> PONG.

    set_timer / cancel_timer / emit are injected by Scheduler.bind;
    send / broadcast by LoopbackNetwork.bind. Both happen in phase 3,
    before start() runs in phase 5.
    """

    def __init__(self, node_id: int) -> None:
        self.id = node_id

    def start(self, t: float) -> None:
        if self.id == 0:
            self.set_timer("kickoff", 5.0, None, t)   # noqa: attr injected

    def on_timer(self, timer_id, payload, t) -> None:
        if timer_id == "kickoff":
            self.broadcast("PING", t)                  # noqa: attr injected

    def on_message(self, msg, t) -> None:
        if msg.payload == "PING":
            self.send(msg.src, "PONG", t)              # noqa: attr injected
        # PONG is terminal — no further events.


class LoopbackNetwork:
    """Stub Network with a fixed delivery delay. Real Network lands in T23."""

    DELAY: float = 10.0
    PHASE_AT: float = 20.0

    def __init__(self, scheduler: Scheduler) -> None:
        self.scheduler = scheduler
        self.members: dict[int, EchoNode] = {}
        self.phases_advanced: list[int] = []

    def register(self, node: EchoNode) -> None:
        self.members[node.id] = node

    def bind(self, node: EchoNode) -> None:
        node.send = lambda dst, payload, t: self._unicast(node.id, dst,
                                                          payload, t)
        node.broadcast = lambda payload, t: self._broadcast(node.id,
                                                            payload, t)

    def start(self) -> None:
        self.scheduler.schedule(PhaseAdvance(1), self.PHASE_AT,
                                Scheduler.PHASE_NODE_ID)

    def advance_phase(self, phase_id: int) -> None:
        self.phases_advanced.append(phase_id)

    def _unicast(self, src, dst, payload, t) -> None:
        msg = SimpleMessage(src, dst, payload)
        self.scheduler.schedule(Delivery(msg), t + self.DELAY, dst)

    def _broadcast(self, src, payload, t) -> None:
        for node_id in self.members:        # insertion order: deterministic
            if node_id != src:
                self._unicast(src, node_id, payload, t)


def run_pingpong() -> tuple:
    """Run one full bootstrap + run cycle. Returns (sink_stream, result, net)."""
    stream: list[str] = []
    # Phase 1 — construct.
    scheduler = Scheduler()
    network = LoopbackNetwork(scheduler)
    nodes = [EchoNode(0), EchoNode(1)]
    # Phase 2 — register.
    for node in nodes:
        network.register(node)
    # Phase 3 — bind (split ownership) + network dispatch handle.
    for node in nodes:
        scheduler.bind(node)
        network.bind(node)
    scheduler.bind_network(network)
    # Phase 4 — observe.
    scheduler.event_sink = lambda t, nid, seq, ev: stream.append(
        f"{t}|{nid}|{seq}|{ev!r}"
    )
    # Phase 5 — kickoff.
    network.start()
    for node in nodes:
        node.start(0.0)
    # Phase 6 — run.
    result = scheduler.run()
    return stream, result, network


class TestEndToEnd(unittest.TestCase):
    def test_pingpong_runs_to_quiescence(self):
        stream, result, network = run_pingpong()
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(result.events_processed, 4)
        self.assertEqual(result.events_tombstoned, 0)
        self.assertEqual(result.now, 25.0)
        self.assertEqual(network.phases_advanced, [1])

    def test_pingpong_event_stream_is_exact(self):
        stream, _, _ = run_pingpong()
        expected = [
            "5.0|0|1|TimerFire(timer_id='kickoff', payload=None)",
            "15.0|1|1|Delivery(msg=SimpleMessage(src=0, dst=1, payload='PING'))",
            "20.0|-1|1|PhaseAdvance(phase_id=1)",
            "25.0|0|2|Delivery(msg=SimpleMessage(src=1, dst=0, payload='PONG'))",
        ]
        self.assertEqual(stream, expected)

    def test_two_runs_are_byte_identical(self):
        first, _, _ = run_pingpong()
        second, _, _ = run_pingpong()
        self.assertEqual(first, second)   # determinism contract, runtime §1


if __name__ == "__main__":
    unittest.main()
