"""Unit tests for the Network class (network-model.md, T23)."""
import math
import unittest

from network import DelayDist, Network, Partition, Phase
from scheduler import Delivery, Scheduler
from _helpers import StubNode

SEED = 42
_D = DelayDist("constant", {"delay": 10.0})


def _single_phase():
    return (Phase(0.0, math.inf, _D),)


class TestNetworkWiring(unittest.TestCase):
    def test_register_populates_registry(self):
        net = Network(Scheduler(), _single_phase(), SEED)
        n = StubNode(3)
        net.register(n)
        self.assertIs(net.registry[3], n)

    def test_bind_wires_send_and_broadcast(self):
        sched = Scheduler()
        net = Network(sched, _single_phase(), SEED)
        n = StubNode(0)
        net.register(n)
        net.bind(n)
        net.start()
        peer = StubNode(1)
        net.register(peer)
        # send now routes through the Network -> schedules a Delivery
        n.send(1, "X", None, 0.0)
        self.assertEqual(len(sched.heap), 1)

    def test_bind_broadcast_lambda_invoked_through_node(self):
        # T25-walkthrough W-1: the bind() lambda for broadcast was never
        # actually invoked by the network suite (only submit_broadcast was
        # called directly). Pins the lambda body that routes
        # `node.broadcast(...)` -> `submit_broadcast(node.id, ...)`.
        sched = Scheduler()
        net = Network(sched, _single_phase(), SEED)
        sender = StubNode(0)
        net.register(sender)
        net.register(StubNode(1))
        net.register(StubNode(2))
        net.bind(sender)
        net.start()
        sender.broadcast("ANN", {"k": 1}, 0.0)
        self.assertEqual(len(sched.heap), 2)               # sender excluded
        dsts = sorted(ev.msg.dst for (_t, _n, _s, ev) in sched.heap)
        self.assertEqual(dsts, [1, 2])
        for (_t, _n, _s, ev) in sched.heap:
            self.assertEqual(ev.msg.src, 0)                # set by the lambda

    def test_network_rng_is_process_stable(self):
        # blake2b-seeded: identical across constructions, not hash()-randomised
        a = Network(Scheduler(), _single_phase(), SEED)
        b = Network(Scheduler(), _single_phase(), SEED)
        self.assertEqual(a.net_rng.getstate(), b.net_rng.getstate())


class TestPhaseAdvance(unittest.TestCase):
    def _two_phase(self):
        return (Phase(0.0, 100.0, _D), Phase(100.0, math.inf, _D))

    def test_start_schedules_interior_boundary_only(self):
        sched = Scheduler()
        net = Network(sched, self._two_phase(), SEED)
        net.start()
        # exactly one PhaseAdvance, at the single interior boundary t=100
        self.assertEqual(len(sched.heap), 1)
        t, node_id, _seq, ev = sched.heap[0]
        self.assertEqual(t, 100.0)
        self.assertEqual(node_id, Scheduler.PHASE_NODE_ID)
        self.assertEqual(ev.phase_id, 1)

    def test_start_validates_timeline(self):
        # non-contiguous timeline -> ValueError from start()
        bad = (Phase(0.0, 100.0, _D), Phase(150.0, math.inf, _D))
        net = Network(Scheduler(), bad, SEED)
        with self.assertRaises(ValueError):
            net.start()

    def test_start_rejects_double_call(self):
        # Second start would re-schedule every interior PhaseAdvance,
        # double-firing rollovers and corrupting the heap.
        net = Network(Scheduler(), _single_phase(), SEED)
        net.start()
        with self.assertRaises(RuntimeError) as cm:
            net.start()
        self.assertIn("twice", str(cm.exception))

    def test_advance_phase_moves_pointer(self):
        net = Network(Scheduler(), self._two_phase(), SEED)
        net.start()
        self.assertEqual(net._phase_idx, 0)
        net.advance_phase(1)
        self.assertEqual(net._phase_idx, 1)

    def test_advance_phase_out_of_range_raises(self):
        net = Network(Scheduler(), self._two_phase(), SEED)
        net.start()
        with self.assertRaises(ValueError):
            net.advance_phase(2)
        with self.assertRaises(ValueError):
            net.advance_phase(-1)

    def test_advance_phase_non_monotonic_raises(self):
        net = Network(Scheduler(), self._two_phase(), SEED)
        net.start()
        # 0 -> 0 is a repeat, non-monotonic
        with self.assertRaises(RuntimeError):
            net.advance_phase(0)

    def test_phase_advances_through_scheduler_run(self):
        # end-to-end pointer move: the PhaseAdvance event drives advance_phase
        sched = Scheduler()
        net = Network(sched, self._two_phase(), SEED)
        sched.bind_network(net)
        net.start()
        sched.run()                       # only the PhaseAdvance is queued
        self.assertEqual(net._phase_idx, 1)

    def test_advance_phase_in_range_skip_raises(self):
        # skip 0 -> 2 on a 3-phase timeline: in range but non-monotonic
        three = (Phase(0.0, 50.0, _D), Phase(50.0, 100.0, _D),
                 Phase(100.0, math.inf, _D))
        net = Network(Scheduler(), three, SEED)
        net.start()
        with self.assertRaises(RuntimeError):
            net.advance_phase(2)

    def test_single_phase_schedules_no_phase_advance(self):
        sched = Scheduler()
        net = Network(sched, _single_phase(), SEED)
        net.start()
        self.assertEqual(len(sched.heap), 0)


from network.network import _network_seed   # noqa: E402  (test-only import)
import random as _random                    # noqa: E402


class TestDelivery(unittest.TestCase):
    def _net(self, phases=None, ids=(0, 1, 2)):
        sched = Scheduler()
        net = Network(sched, phases or _single_phase(), SEED)
        for i in ids:
            net.register(StubNode(i))
        net.start()
        return sched, net

    def test_submit_before_start_raises(self):
        net = Network(Scheduler(), _single_phase(), SEED)
        net.register(StubNode(0))
        net.register(StubNode(1))
        with self.assertRaises(RuntimeError):
            net.submit_unicast(0, 1, "X", None, 0.0)

    def test_unicast_schedules_one_delivery(self):
        sched, net = self._net()
        net.submit_unicast(0, 1, "PING", {"k": 1}, 5.0)
        self.assertEqual(len(sched.heap), 1)
        t, node_id, _seq, ev = sched.heap[0]
        self.assertEqual(t, 15.0)                 # 5.0 + constant 10.0
        self.assertEqual(node_id, 1)              # Delivery node_id = dst
        self.assertEqual((ev.msg.src, ev.msg.dst, ev.msg.type), (0, 1, "PING"))
        self.assertEqual(ev.msg.t_sent, 5.0)

    def test_unknown_dst_raises_keyerror(self):
        _sched, net = self._net()
        with self.assertRaises(KeyError):
            net.submit_unicast(0, 99, "X", None, 0.0)

    def test_unknown_dst_consumes_no_rng(self):
        # the resolve-failure (KeyError) path fires before any RNG draw —
        # determinism contract (network-model-phases.md §6.2)
        _sched, net = self._net()
        before = net.net_rng.getstate()
        with self.assertRaises(KeyError):
            net.submit_unicast(0, 99, "X", None, 0.0)
        self.assertEqual(net.net_rng.getstate(), before)

    def test_broadcast_reaches_registry_minus_sender(self):
        sched, net = self._net(ids=(0, 1, 2))
        net.submit_broadcast(1, "ANN", None, 0.0)
        dsts = sorted(ev.msg.dst for (_t, _n, _s, ev) in sched.heap)
        self.assertEqual(dsts, [0, 2])            # sender 1 excluded

    def test_full_drop_phase_suppresses_delivery(self):
        # p_drop just below 1.0 so every coin lands "drop"
        phases = (Phase(0.0, math.inf, _D, p_drop=0.999999),)
        sched, net = self._net(phases=phases)
        for _ in range(50):
            net.submit_unicast(0, 1, "X", None, 0.0)
        self.assertEqual(len(sched.heap), 0)

    def test_partition_suppresses_delivery(self):
        part = Partition(groups=((0,), (1,)))
        phases = (Phase(0.0, math.inf, _D, partitions=(part,)),)
        sched, net = self._net(phases=phases)
        net.submit_unicast(0, 1, "X", None, 0.0)  # cross-group -> blocked
        self.assertEqual(len(sched.heap), 0)

    def test_partition_drop_consumes_no_delay_sample(self):
        # network-model-phases.md §6.2: a partitioned message consumes the
        # drop coin but NOT a delay sample.
        part = Partition(groups=((0,), (1,)))
        phases = (Phase(0.0, math.inf, _D, partitions=(part,)),)
        _sched, net = self._net(phases=phases)
        net.submit_unicast(0, 1, "X", None, 0.0)
        ref = _random.Random(_network_seed(SEED))
        ref.random()                              # exactly one drop coin
        self.assertEqual(net.net_rng.getstate(), ref.getstate())

    def test_active_phase_governs_delay(self):
        # after advance_phase, sends draw from the second phase's DelayDist
        slow = DelayDist("constant", {"delay": 10.0})
        fast = DelayDist("constant", {"delay": 1.0})
        phases = (Phase(0.0, 100.0, slow), Phase(100.0, math.inf, fast))
        sched, net = self._net(phases=phases)
        net.submit_unicast(0, 1, "X", None, 0.0)
        net.advance_phase(1)
        net.submit_unicast(0, 1, "X", None, 100.0)
        # the two-phase timeline also queues a PhaseAdvance at t=100; keep
        # only the Delivery events for the delay comparison.
        delays = sorted(t - ev.msg.t_sent for (t, _n, _s, ev) in sched.heap
                        if isinstance(ev, Delivery))
        self.assertEqual(delays, [1.0, 10.0])

    def test_phase_parameters_baked_at_submit_time(self):
        # T25-walkthrough NW-5: a Delivery scheduled in phase[i] keeps its
        # phase[i] fire time even after advance_phase(i+1). The §1 pipeline
        # reads self.phases[self._phase_idx] AT SUBMIT TIME and commits the
        # delay; the heap entry is immutable thereafter.
        #
        # test_active_phase_governs_delay (above) pins that a NEW submit
        # after advance_phase uses the new phase's delay. This pins the
        # converse: a PRIOR submit's already-scheduled Delivery is NOT
        # retroactively re-sampled.
        slow = DelayDist("constant", {"delay": 100.0})
        fast = DelayDist("constant", {"delay": 1.0})
        phases = (Phase(0.0, 50.0, slow), Phase(50.0, math.inf, fast))
        sched, net = self._net(phases=phases, ids=(0, 1))

        net.submit_unicast(0, 1, "X", None, 49.0)
        deliveries_before = [(t, ev.msg.t_sent)
                             for (t, _n, _s, ev) in sched.heap
                             if isinstance(ev, Delivery)]
        self.assertEqual(deliveries_before, [(149.0, 49.0)])  # 49 + 100

        net.advance_phase(1)
        deliveries_after = [(t, ev.msg.t_sent)
                            for (t, _n, _s, ev) in sched.heap
                            if isinstance(ev, Delivery)]
        # Same fire time — phase 1's delay 1.0 was never applied.
        self.assertEqual(deliveries_after, [(149.0, 49.0)])

    def test_drop_and_partition_compose_per_sampling_order(self):
        # T25-walkthrough NW-6: §6.2 sampling order under composition.
        # With BOTH p_drop > 0 AND a partition active, the order is
        # drop coin (consumes 1 RNG draw) -> partition check (no RNG) ->
        # delay sample (never reached, partition blocks). Regardless of
        # how the drop coin lands, a partition-bound message consumes
        # exactly one RNG draw and zero delay samples.
        #
        # The existing test_partition_drop_consumes_no_delay_sample pins
        # this for p_drop = 0; this is the composed case.
        part = Partition(groups=((0,), (1,)))
        phases = (Phase(0.0, math.inf, _D, p_drop=0.5,
                        partitions=(part,)),)
        sched, net = self._net(phases=phases, ids=(0, 1))
        net.submit_unicast(0, 1, "X", None, 0.0)        # partition-bound
        ref = _random.Random(_network_seed(SEED))
        ref.random()                                     # exactly one coin
        self.assertEqual(net.net_rng.getstate(), ref.getstate())
        self.assertEqual(len(sched.heap), 0)             # nothing scheduled

    def test_broadcast_rng_consumption_independent_of_registration_order(self):
        # T25-walkthrough NW-8: §6.3 forbidden surface — broadcast iterates
        # `sorted(NodeId)` so the kth delay sample is consumed by the kth
        # sorted recipient, regardless of registration order. A regression
        # that dropped sorted() (e.g. `for dst in self.registry`) would
        # still deliver to the same SET of recipients (so the existing
        # test_broadcast_reaches_registry_minus_sender still passes) but
        # would shuffle the dst -> delay-sample mapping across registration
        # orders, breaking byte-identical replay. Stochastic delay is
        # required — a constant delay never reads net_rng and could not
        # show this.
        stochastic = DelayDist("uniform", {"low": 1.0, "high": 100.0})
        phases = (Phase(0.0, math.inf, stochastic),)

        def run(register_order):
            sched = Scheduler()
            net = Network(sched, phases, SEED)
            for nid in register_order:
                net.register(StubNode(nid))
            net.start()
            net.submit_broadcast(0, "X", None, 0.0)
            return {ev.msg.dst: t for (t, _n, _s, ev) in sched.heap
                    if isinstance(ev, Delivery)}

        forward = run([0, 1, 2, 3])
        reverse = run([3, 2, 1, 0])
        self.assertEqual(forward, reverse)
        # And the mapping is non-trivial (different recipients get different
        # delays drawn from net_rng) — a sanity check that the test would
        # actually fail if iteration order shuffled the RNG consumption.
        self.assertEqual(len(set(forward.values())), 3)  # 3 distinct delays


class TestRegisterCollision(unittest.TestCase):
    def test_duplicate_register_rejected(self):
        # A duplicate register silently clobbers today; the gate makes it loud.
        net = Network(Scheduler(), _single_phase(), SEED)
        a = StubNode(node_id=5)
        b = StubNode(node_id=5)
        net.register(a)
        with self.assertRaises(ValueError) as cm:
            net.register(b)
        self.assertIn("5", str(cm.exception))
        # First registration still resolvable.
        self.assertIs(net.registry[5], a)


if __name__ == "__main__":
    unittest.main()
