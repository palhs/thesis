"""Stress tests for the Scheduler — extreme-scale / high-churn scenarios
the small-scale correctness suite does not exercise.

Added during the 2026-05-20 T25 review per the T25-coverage-gaps.md
walkthrough. Closes / regression-sentinels the following gap items:

  ST-2  Tombstone density under high churn
        — regression sentinel for the TASKS.md Backlog item
          "Scheduler heap growth under high timer churn" (S-5).
  ST-3  Same-t many-events dispatch order at scale.
  ST-4  Mixed event classes at the same t — PhaseAdvance first
        — also closes S-4 (the half-open [t_start, t_end) boundary
          assumption the Network relies on).
  ST-7  Bounded reentrancy chain at delay=0 terminates correctly.

Stress tests are deliberately bigger than the unit-suite (~2k events
per case for ST-2; 100 events for ST-3 / ST-7) but stay millisecond-fast.
"""
import random
import unittest

from scheduler import Delivery, PhaseAdvance, Scheduler
from _stubs import RecordingNetwork, RecordingNode, SimpleMessage


class TestSchedulerStress(unittest.TestCase):
    def test_tombstone_density_under_high_churn(self):
        """Many set_timer cycles per node + one final live timer per node.

        Mirrors the high-churn pattern T28+ view-change timers will exhibit
        (every round, every validator resets the same timer). Verifies the
        lazy-tombstone mechanism stays correct at load:
          - every live timer fires exactly once, with the latest payload;
          - every superseded entry is tombstoned, not dispatched;
          - the (live, tombstoned) counters add up to total heap entries.
        """
        N_NODES, CYCLES = 20, 100
        s = Scheduler()
        nodes = [RecordingNode(i) for i in range(N_NODES)]
        for n in nodes:
            s.bind(n)
        # Every set_timer with the same timer_id overwrites the registry seq
        # for that timer, so each prior set leaves a heap entry whose seq no
        # longer matches the registry — a tombstone on pop.
        for n in nodes:
            for c in range(CYCLES):
                n.set_timer("view", delay=1.0, payload=c, t=0.0)
        # Final reset, distinct delay so its fire time differs from the
        # tombstoned wave at t=1.0:
        for n in nodes:
            n.set_timer("view", delay=2.0, payload="final", t=0.0)
        result = s.run()
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(result.events_processed, N_NODES)            # 1/node
        self.assertEqual(result.events_tombstoned, N_NODES * CYCLES)  # rest
        # Each node fired exactly once, with the final payload, at t=2.0:
        for n in nodes:
            self.assertEqual(len(n.calls), 1)
            kind, timer_id, payload, t = n.calls[0]
            self.assertEqual((kind, timer_id, payload, t),
                             ("on_timer", "view", "final", 2.0))

    def test_same_t_many_events_dispatched_in_canonical_node_seq_order(self):
        """100 events at the same t across 20 node_ids, submitted scrambled.

        Asserts dispatch order is the canonical (node_id, seq) sort despite
        scrambled submission. The existing 3-event ordering test proves the
        rule; this proves it holds at non-trivial fan-out.
        """
        N_NODES, EVENTS_PER_NODE = 20, 5
        s = Scheduler()
        nodes = [RecordingNode(i) for i in range(N_NODES)]
        for n in nodes:
            s.bind(n)
        captured: list[tuple] = []
        s.event_sink = lambda t, nid, seq, ev: captured.append((t, nid, seq))

        submissions = [(nid, k) for nid in range(N_NODES)
                       for k in range(EVENTS_PER_NODE)]
        random.Random(42).shuffle(submissions)
        for (nid, _k) in submissions:
            s.schedule(Delivery(SimpleMessage(src=0, dst=nid, payload="x")),
                       t=5.0, node_id=nid)

        result = s.run()
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(result.events_processed, N_NODES * EVENTS_PER_NODE)
        # The captured stream is the canonical (t, node_id, seq) sort:
        self.assertEqual(captured, sorted(captured))
        # Events for a given node_id appear contiguously, in node_id order:
        nid_stream = [nid for (_t, nid, _s) in captured]
        expected = [nid for nid in range(N_NODES)
                    for _ in range(EVENTS_PER_NODE)]
        self.assertEqual(nid_stream, expected)

    def test_phaseadvance_dispatched_before_real_events_at_same_t(self):
        """At a single t, PhaseAdvance (node_id = PHASE_NODE_ID = -1) must
        dispatch before any real-node event.

        The Network's half-open [t_start, t_end) phase boundary
        (network-model-phases §5) relies on this — without it, an event
        scheduled at exactly t = phase[i].t_end could observe the *old*
        phase's parameters. The (t, node_id, seq) tuple sort gives the
        ordering for free, but no test exercises the mixed-class same-t
        scenario directly (gap S-4).
        """
        s = Scheduler()
        n0, n1 = RecordingNode(0), RecordingNode(1)
        s.bind(n0)
        s.bind(n1)
        net = RecordingNetwork()
        s.bind_network(net)

        order: list[str] = []
        s.event_sink = lambda t, nid, seq, ev: order.append(type(ev).__name__)

        # Submit in deliberately non-canonical order — PhaseAdvance last:
        s.schedule(Delivery(SimpleMessage(0, 1, "to-1")),
                   t=10.0, node_id=1)
        s.schedule(Delivery(SimpleMessage(0, 0, "to-0")),
                   t=10.0, node_id=0)
        s.schedule(PhaseAdvance(1), t=10.0,
                   node_id=Scheduler.PHASE_NODE_ID)
        s.run()

        # PhaseAdvance first (node_id = -1), then deliveries in node_id order:
        self.assertEqual(order, ["PhaseAdvance", "Delivery", "Delivery"])
        # Network saw the phase advance before either node saw on_message:
        self.assertEqual(net.calls, [("advance_phase", 1)])
        self.assertEqual(n0.calls[0][0], "on_message")
        self.assertEqual(n1.calls[0][0], "on_message")


class _ReentrantNode:
    """on_timer re-schedules itself at delay=0 until `target` fires accumulate.

    Duck-typed Node stand-in matching the inbound-hook surface Scheduler.bind
    expects. set_timer is injected by bind.
    """

    def __init__(self, node_id: int, target: int) -> None:
        self.id = node_id
        self.target = target
        self.fired = 0

    def on_message(self, msg, t):
        pass

    def on_timer(self, timer_id, payload, t):
        self.fired += 1
        if self.fired < self.target:
            # delay=0 reentrancy: schedules a fresh timer at the same t.
            # Distinct timer_id per iteration so each is a fresh live entry
            # (otherwise re-using the same id would tombstone the in-flight
            # chain instead of extending it).
            self.set_timer(f"chain-{self.fired}", 0.0, None, t)


class TestSchedulerReentrancy(unittest.TestCase):
    def test_bounded_reentrancy_chain_at_delay_zero_terminates(self):
        """A handler that schedules a delay=0 successor on each fire produces
        a chain of same-t events. Verifies (a) the chain terminates when the
        handler stops re-scheduling, (b) the virtual clock stays pinned at
        the original t (no spurious advance), (c) dispatch order within the
        chain is monotone in seq, (d) the dispatch loop is iterative — a
        100-step chain does not exceed any stack budget.
        """
        TARGET = 100
        s = Scheduler()
        n = _ReentrantNode(0, target=TARGET)
        s.bind(n)
        n.set_timer("chain-0", 0.0, None, 0.0)            # kick off

        captured: list[tuple] = []
        s.event_sink = lambda t, nid, seq, ev: captured.append((t, nid, seq))

        result = s.run()
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(n.fired, TARGET)
        self.assertEqual(result.events_processed, TARGET)
        self.assertEqual(result.now, 0.0)                 # all at t=0
        self.assertTrue(all(t == 0.0 for (t, _nid, _s) in captured))
        seqs = [seq for (_t, _nid, seq) in captured]
        self.assertEqual(seqs, sorted(seqs))              # strictly monotone

    def test_runaway_reentrancy_chain_bounded_by_stop_when(self):
        """A handler that NEVER stops re-scheduling at delay=0 would never
        reach quiescence. Verifies stop_when bounds the runaway cleanly.
        """
        s = Scheduler()
        n = _ReentrantNode(0, target=10**9)               # effectively infinite
        s.bind(n)
        n.set_timer("chain-0", 0.0, None, 0.0)
        result = s.run(stop_when=lambda: n.fired >= 50)
        self.assertEqual(result.stopped_by, "predicate")
        self.assertEqual(n.fired, 50)
        self.assertEqual(result.now, 0.0)


if __name__ == "__main__":
    unittest.main()
