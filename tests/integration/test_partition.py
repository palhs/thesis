"""Integration: partition phase at multi-node scale (T25).

Closes T25 review gap I-2. The Network suite tests Partition at small
node counts; this is the thesis-critical scenario — partitioned
consensus is the central adversarial case for T28+ — pinned at the
integration tier with n = 7 and a 2-group split {0,1,2} | {3,4,5,6}.

Expected reachability under the partition:
  - each node receives only from peers in its own group;
  - total deliveries = sum over groups of k_g*(k_g-1)
    = 3*2 + 4*3 = 6 + 12 = 18 (down from n*(n-1) = 42 unpartitioned).
"""
import math
import unittest

from network import DelayDist, Phase
from network.phases import Partition
from _helpers import BroadcastNode, build_and_run


_GROUPS = ((0, 1, 2), (3, 4, 5, 6))


def _group_of(nid):
    for i, g in enumerate(_GROUPS):
        if nid in g:
            return i
    return None


class TestPartitionAtMultiNodeScale(unittest.TestCase):
    def test_two_group_partition_yields_intra_group_deliveries_only(self):
        phases = (Phase(0.0, math.inf,
                        DelayDist("constant", {"delay": 10.0}),
                        partitions=(Partition(groups=_GROUPS),)),)
        nodes = [BroadcastNode(i, global_seed=42) for i in range(7)]
        result, deliveries, _ = build_and_run(nodes, phases, 42)

        self.assertEqual(result.stopped_by, "quiescence")
        # 3*2 + 4*3 = 18 intra-group deliveries; 24 cross-group attempts
        # were blocked by the partition.
        self.assertEqual(len(deliveries), 18)

        # No cross-group delivery in the recorded stream.
        for (src, dst, _type, _t_sent, _t_delivered) in deliveries:
            self.assertEqual(_group_of(src), _group_of(dst))

        # Each node's inbound set is exactly its peers within its own group.
        for node in nodes:
            mygroup = _GROUPS[_group_of(node.id)]
            expected = sorted(p for p in mygroup if p != node.id)
            self.assertEqual(sorted(s for s, _t in node.received), expected)


if __name__ == "__main__":
    unittest.main()
