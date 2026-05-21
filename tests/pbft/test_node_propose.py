# tests/pbft/test_node_propose.py
"""PBFTNode construction, primary detection, and (Task 6) propose path."""
import unittest

from pbft.node import PBFTNode


def _node(node_id: int, n: int, *, workload=None, propose_delay=1.0,
          initial_view=0, weight=1.0, global_seed=42) -> PBFTNode:
    return PBFTNode(node_id=node_id, weight=weight, endpoint=None,
                    global_seed=global_seed, n=n, workload=workload,
                    propose_delay=propose_delay, initial_view=initial_view)


class TestPBFTNodeConstructor(unittest.TestCase):
    def test_defaults_for_non_primary(self):
        # workload=None -> empty list copy; never blocks construction.
        n = _node(1, n=4)
        self.assertEqual(n.n, 4)
        self.assertEqual(n.f, 1)             # (4-1)//3 = 1
        self.assertEqual(n.view, 0)
        self.assertFalse(n.view_changing)
        self.assertEqual(n.workload, [])
        self.assertEqual(n.propose_delay, 1.0)
        self.assertEqual(n.next_seq, 0)
        self.assertEqual(n.inst, {})

    def test_workload_is_copied(self):
        # Caller's list must not be mutated when the primary drains.
        src = [b"A", b"B"]
        n = _node(0, n=4, workload=src)
        n.workload.append(b"C")
        self.assertEqual(src, [b"A", b"B"])  # untouched

    def test_f_for_n_7(self):
        self.assertEqual(_node(0, n=7).f, 2)     # (7-1)//3 = 2

    def test_rejects_non_positive_n(self):
        with self.assertRaises(ValueError):
            _node(0, n=0)
        with self.assertRaises(ValueError):
            _node(0, n=-1)

    def test_rejects_node_id_outside_range(self):
        with self.assertRaises(ValueError):
            _node(4, n=4)                    # id == n is out of range
        # Negative node_id is caught upstream by Node.__init__; PBFTNode
        # narrows it to "must be < n".

    def test_rejects_non_positive_propose_delay(self):
        with self.assertRaises(ValueError):
            _node(0, n=4, propose_delay=0.0)
        with self.assertRaises(ValueError):
            _node(0, n=4, propose_delay=-1.0)


class TestIsPrimary(unittest.TestCase):
    def test_v_mod_n_rule_n4(self):
        nodes = [_node(i, n=4) for i in range(4)]
        # view 0 -> node 0; view 1 -> node 1; view 5 -> node 1.
        self.assertTrue(nodes[0]._is_primary(0))
        self.assertFalse(nodes[1]._is_primary(0))
        self.assertTrue(nodes[1]._is_primary(1))
        self.assertTrue(nodes[1]._is_primary(5))

    def test_v_mod_n_rule_n7(self):
        nodes = [_node(i, n=7) for i in range(7)]
        for v in range(14):
            primary_id = v % 7
            for i in range(7):
                self.assertEqual(nodes[i]._is_primary(v), i == primary_id,
                                 f"view={v} node={i} primary_id={primary_id}")


if __name__ == "__main__":
    unittest.main()
