"""End-to-end: the EventLogger records a real 2-node run.

A real Network drives two real Nodes through the six-phase bootstrap
(simulation-design.md §7.2) with the logger wired as event_sink at phase 4.
Exercises both event_sink shapes: emit events (decided / halted) and
transport events (delivery).
"""
import math
import tempfile
import unittest
from pathlib import Path

from nodes import HaltReason, Node
from network import DelayDist, Network, Phase
from scheduler import Scheduler

from event_log import EventLogger


class PingPongNode(Node):
    """Minimal real protocol: two nodes bounce a token; each halts after
    `budget` inbound messages, emitting `decided` then `halted`."""

    def __init__(self, node_id, peer_id, budget, global_seed):
        super().__init__(node_id, weight=1.0, endpoint=None,
                         global_seed=global_seed)
        self.peer_id = peer_id
        self.budget = budget
        self.hops = 0

    def _on_start(self, t):
        if self.id == 0:
            self.send(self.peer_id, "PING", {"hop": 0}, t)

    def _on_message(self, msg, t):
        self.hops += 1
        if self.hops >= self.budget:
            self._emit_decided(value="done", instance_id=self.id, t=t)
            self.halt(HaltReason.RUN_END, t)
            return
        reply = "PONG" if msg.type == "PING" else "PING"
        self.send(msg.src, reply, {"hop": self.hops}, t)

    def _on_timer(self, timer_id, payload, t):
        pass


def _run(global_seed, budget=4):
    """Six-phase bootstrap over the real Network; logger as event_sink."""
    sched = Scheduler()
    net = Network(sched,
                  (Phase(0.0, math.inf, DelayDist("constant", {"delay": 10.0})),),
                  global_seed)
    nodes = [PingPongNode(0, peer_id=1, budget=budget, global_seed=global_seed),
             PingPongNode(1, peer_id=0, budget=budget, global_seed=global_seed)]
    logger = EventLogger()
    for n in nodes:                       # phase 2: register
        net.register(n)
    sched.bind_network(net)               # phase 3: PhaseAdvance dispatch
    for n in nodes:                       # phase 3: split bind
        sched.bind(n)
        net.bind(n)
    sched.event_sink = logger.sink        # phase 4: observe
    net.start()                           # phase 5: arm
    for n in nodes:                       # phase 5: kickoff
        n.start(0.0)
    result = sched.run()                  # phase 6
    return logger, result


class TestEventLogE2E(unittest.TestCase):
    def test_run_reaches_quiescence_and_logger_captures_events(self):
        logger, result = _run(global_seed=42)
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertGreater(len(logger), 0)

    def test_both_event_sink_shapes_are_recorded(self):
        logger, _ = _run(global_seed=42)
        seen = {r.event_type for r in logger.records}
        # emit shape: decided + halted; transport shape: delivery.
        self.assertIn("decided", seen)
        self.assertIn("halted", seen)
        self.assertIn("delivery", seen)

    def test_to_csv_produces_well_formed_file(self):
        logger, _ = _run(global_seed=42)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "baseline" / "events.csv"
            logger.to_csv(out)
            rows = out.read_text().splitlines()
        self.assertEqual(rows[0], "t,node_id,event_type,seq,fields")
        self.assertEqual(len(rows), len(logger) + 1)   # header + records

    def test_two_seed_identical_runs_yield_byte_identical_csv(self):
        # determinism contract (node-model.md §8): the logger preserves
        # byte-identical replay.
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.csv", Path(d) / "b.csv"
            la, _ = _run(global_seed=42)
            lb, _ = _run(global_seed=42)
            la.to_csv(a)
            lb.to_csv(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
