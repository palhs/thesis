"""beta-acceptance and the decided event (design spec §6.3)."""
import unittest

from _helpers import build_run_harness


class TestAcceptance(unittest.TestCase):
    def test_decided_emitted_for_every_announced_block(self):
        """At n=4 with delay=1e-9 and POLL_DELAY=1e-9, every announced
        block converges within a fraction of one slot, so every node
        decides every announced block."""
        logger, _, _ = build_run_harness(n=4, t_max=3.0)
        announced = {e.fields["block_id"] for e in logger.records
                     if e.event_type == "snowman_announced"}
        self.assertGreater(len(announced), 0)
        decided_by_node: dict[int, set[bytes]] = {}
        for e in logger.records:
            if e.event_type == "decided":
                decided_by_node.setdefault(
                    e.node_id, set()).add(e.fields["instance_id"])
        for node_id in range(4):
            self.assertEqual(decided_by_node.get(node_id, set()), announced,
                             f"node {node_id} did not decide every block")

    def test_no_forks_one_decided_value_per_block(self):
        """For each block, every node decides the same `value`."""
        logger, _, _ = build_run_harness(n=4, t_max=3.0)
        by_block: dict[bytes, set[bytes]] = {}
        for e in logger.records:
            if e.event_type == "decided":
                by_block.setdefault(
                    e.fields["instance_id"], set()).add(e.fields["value"])
        self.assertGreater(len(by_block), 0)
        for block_id, values in by_block.items():
            self.assertEqual(len(values), 1, f"fork at block {block_id!r}")

    def test_accepted_block_runs_exactly_beta_polls(self):
        """Every decided (node, block) pair has been polled exactly beta
        times before acceptance — counter advances 1 per round."""
        logger, _, _ = build_run_harness(n=4, t_max=3.0)
        poll_starts: dict[tuple[int, bytes], int] = {}
        decided_by: set[tuple[int, bytes]] = set()
        for e in logger.records:
            if e.event_type == "snowman_poll_started":
                key = (e.node_id, e.fields["block_id"])
                poll_starts[key] = poll_starts.get(key, 0) + 1
            elif e.event_type == "decided":
                decided_by.add((e.node_id, e.fields["instance_id"]))
        self.assertGreater(len(decided_by), 0)
        for key in decided_by:
            self.assertEqual(poll_starts.get(key), 15,
                             f"{key}: expected 15 polls, "
                             f"got {poll_starts.get(key)}")


if __name__ == "__main__":
    unittest.main()
