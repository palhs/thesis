"""End-to-end: the real Network drives Nodes through the six-phase bootstrap.

Replaces the LoopbackNetwork stub (tests/nodes/_helpers.py) with the real
T23 Network. Exercises network-model.md delivery + the network-level
determinism contract (network-model-phases.md §6.4).
"""
import math
import unittest

from network import DelayDist, Network, Phase
from scheduler import Delivery, Scheduler
from _helpers import PingPongNode

_D = DelayDist("constant", {"delay": 10.0})
# A stochastic delay: unlike _D, sample() draws from net_rng. Required to
# exercise the seed -> output dependency the determinism contract rests on
# (a constant delay ignores net_rng, so different seeds would be invisible).
_UNIFORM = DelayDist("uniform", {"low": 5.0, "high": 50.0})


def _run(global_seed, phases=None, budget=4):
    """Six-phase bootstrap (simulation-design.md §7.2) over the real Network."""
    sched = Scheduler()
    net = Network(sched, phases or (Phase(0.0, math.inf, _D),), global_seed)
    nodes = [
        PingPongNode(0, peer_id=1, budget=budget, global_seed=global_seed),
        PingPongNode(1, peer_id=0, budget=budget, global_seed=global_seed),
    ]
    deliveries: list = []
    sched.event_sink = lambda t, nid, seq, ev: (
        deliveries.append((ev.msg.src, ev.msg.dst, ev.msg.type,
                           ev.msg.t_sent, t))
        if isinstance(ev, Delivery) else None)
    for n in nodes:                       # phase 2: register
        net.register(n)
    sched.bind_network(net)               # phase 3: PhaseAdvance dispatch target
    for n in nodes:                       # phase 3: split bind
        sched.bind(n)
        net.bind(n)
    net.start()                           # phase 5: arm phase rollover
    for n in nodes:                       # phase 5: kickoff
        n.start(0.0)
    result = sched.run()                  # phase 6
    return result, deliveries


class TestNetworkE2E(unittest.TestCase):
    def test_run_reaches_quiescence(self):
        result, _ = _run(global_seed=42)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_deliveries_respect_constant_delay(self):
        _, deliveries = _run(global_seed=42)
        self.assertTrue(deliveries)
        for (_src, _dst, _type, t_sent, t_delivered) in deliveries:
            self.assertEqual(t_delivered - t_sent, 10.0)

    def test_same_seed_runs_are_byte_identical(self):
        # determinism contract (network-model-phases.md §6.4): same seed ->
        # identical delivery stream. Uses a stochastic delay so the RNG-driven
        # delay-sampling path is what is shown to replay, not just the
        # no-RNG constant path.
        phases = (Phase(0.0, math.inf, _UNIFORM),)
        _, a = _run(global_seed=42, phases=phases)
        _, b = _run(global_seed=42, phases=phases)
        self.assertEqual(a, b)

    def test_different_seeds_produce_different_runs(self):
        # Opposite of the contract above: the seed knob must actually move
        # the output. With a stochastic delay, two distinct seeds drive two
        # distinct net_rng streams -> distinct delivery timings. (A constant
        # delay could not show this — it never reads net_rng.)
        phases = (Phase(0.0, math.inf, _UNIFORM),)
        _, a = _run(global_seed=42, phases=phases)
        _, b = _run(global_seed=7, phases=phases)
        self.assertNotEqual(a, b)

    def test_multi_phase_run_reaches_quiescence(self):
        # slow phase then fast phase; advance_phase fires mid-run.
        #
        # The 25.0 boundary is hand-picked and coupled to `budget`: with
        # budget=4 and delay 10, the ping-pong sends at t=0,10,20 (phase 0)
        # and t=30,32,34,36 (phase 1), so t=25 falls in the t=20..t=30 gap
        # and both phases are exercised. If `budget` is lowered the run may
        # end before t=25 and phase 1 is never reached -> observed=={10.0}
        # and the assertion below fails. Change `budget` or either delay
        # and re-derive that the last send still lands at or after t=25.
        phases = (
            Phase(0.0, 25.0, DelayDist("constant", {"delay": 10.0})),
            Phase(25.0, math.inf, DelayDist("constant", {"delay": 2.0})),
        )
        result, deliveries = _run(global_seed=42, phases=phases)
        self.assertEqual(result.stopped_by, "quiescence")
        # at least one delivery used each phase's delay
        observed = {round(td - ts, 6) for (*_x, ts, td) in deliveries}
        self.assertEqual(observed, {10.0, 2.0})


if __name__ == "__main__":
    unittest.main()
