"""T38 honest-path build-verification baseline at n in {4, 7, 10}.

Asserts the four T38 outcomes per scenario (design spec §8.2):
  1. Every honest node ACCEPTS every announced block.
  2. Zero forks — every node's `decided` for a given block agrees on value.
  3. Finalisation latency is logged on every decided event.
  4. Two runs with the same (config, global_seed) are byte-identical.

Scenarios + the build/run shape live in `src/snowman/baseline.py` (T40
harmonisation); this test imports SCENARIOS + run_scenario and asserts
the four outcomes scenario-by-scenario via subTest.

Mirrors tests/integration/test_pos_baseline.py.
"""
import math
import unittest

from snowman.baseline import SCENARIOS, run_scenario


def _by(records, event_type):
    return [r for r in records if r.event_type == event_type]


class TestSnowmanHonestBaseline(unittest.TestCase):

    def test_every_node_accepts_every_announced_block(self):
        """Outcome 1: every honest node decides every announced block."""
        for meta in SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                records, result, _ = run_scenario(meta)
                n = meta.n
                self.assertEqual(result.stopped_by, "deadline")
                announced = {r.fields["block_id"]
                             for r in _by(records, "snowman_announced")}
                self.assertGreater(len(announced), 0)
                decided_by_node: dict[int, set] = {}
                for r in _by(records, "decided"):
                    decided_by_node.setdefault(
                        r.node_id, set()).add(r.fields["instance_id"])
                self.assertEqual(sorted(decided_by_node), list(range(n)),
                                 f"{meta.run_id}: not every node emitted decided")
                for node_id in range(n):
                    self.assertEqual(decided_by_node[node_id], announced,
                                     f"{meta.run_id}: node {node_id} missed blocks")

    def test_no_forks(self):
        """Outcome 2: every node decides the same value for every block."""
        for meta in SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                records, _, _ = run_scenario(meta)
                by_block: dict[bytes, set] = {}
                for r in _by(records, "decided"):
                    by_block.setdefault(
                        r.fields["instance_id"], set()).add(r.fields["value"])
                self.assertGreater(len(by_block), 0)
                for block_id, values in by_block.items():
                    self.assertEqual(
                        len(values), 1,
                        f"{meta.run_id}: fork at block {block_id!r}: {values}")
                self.assertEqual(
                    len(_by(records, "snowman_rejected")), 0,
                    f"{meta.run_id}: unexpected rejection on honest path")

    def test_finality_latency_logged(self):
        """Outcome 3: every decided event has a finite, positive timestamp."""
        for meta in SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                records, _, _ = run_scenario(meta)
                decided = _by(records, "decided")
                self.assertGreater(len(decided), 0)
                for r in decided:
                    self.assertTrue(math.isfinite(r.t))
                    self.assertGreater(r.t, 0.0)

    def test_determinism_byte_identical(self):
        """Outcome 4: two seed-identical runs produce byte-identical event
        streams — covers the RNG K-peer sampling path that PBFT and Casper
        FFG baselines do not (week7-decision §5.1 watch-for closure)."""
        for meta in SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                a_records, _, _ = run_scenario(meta)
                b_records, _, _ = run_scenario(meta)
                self.assertEqual(a_records, b_records,
                                 f"{meta.run_id}: determinism broken")


if __name__ == "__main__":
    unittest.main()
