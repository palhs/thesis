"""Integration: per-Node RNG separate from net_rng (T25).

Closes T25 review gap I-8. Unit tests pin that two nodes with the
same global_seed but different node_id produce different per-Node RNG
streams. This composes the contract at integration scale: changing
the per-Node global_seed (which feeds each Node's own random.Random)
must not perturb the network-sampled delivery stream, which depends
only on the Network's global_seed via _network_seed().

The test exercises this by holding the Network's global_seed constant
(=42) while constructing nodes once with global_seed=42 and once with
global_seed=99. BroadcastNode does not consume its per-Node RNG, so
the delivery stream is purely network-sampled, and the two streams
must be byte-identical.
"""
import math
import unittest

from network import DelayDist, Phase
from _helpers import BroadcastNode, build_and_run


class TestPerNodeRngIndependentOfNetRng(unittest.TestCase):
    def test_changing_per_node_seed_leaves_delivery_stream_unchanged(self):
        n = 7
        # Uniform delay (stochastic): the only RNG draws are from net_rng,
        # so any per-Node-RNG bleed would shift delivery times observably.
        phases = (Phase(0.0, math.inf,
                        DelayDist("uniform", {"low": 5.0, "high": 50.0})),)

        nodes_a = [BroadcastNode(i, global_seed=42) for i in range(n)]
        _, deliveries_a, _ = build_and_run(nodes_a, phases, 42)

        # Same network global_seed (=42). Nodes constructed with seed 99 —
        # their per-Node random.Random instances are now seeded
        # differently. The delivery stream must still match.
        nodes_b = [BroadcastNode(i, global_seed=99) for i in range(n)]
        _, deliveries_b, _ = build_and_run(nodes_b, phases, 42)

        self.assertEqual(deliveries_a, deliveries_b)


if __name__ == "__main__":
    unittest.main()
