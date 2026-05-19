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


if __name__ == "__main__":
    unittest.main()
