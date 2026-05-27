"""QUERY + QUERY-RESPONSE handling (design spec §6.3)."""
import unittest

from _helpers import build_run_harness, capturers, kickoff, make_node
from nodes.message import Message
from snowman.block import GENESIS_ID, hash_block
from snowman.messages import (
    BlockAnnouncementPayload, QueryPayload, QueryResponsePayload,
)


def _announce(node, block_id, parent_id=GENESIS_ID, slot=1, proposer_idx=1,
              t=1.0):
    payload = BlockAnnouncementPayload(
        slot=slot, block_id=block_id, parent_id=parent_id,
        transactions=(), proposer_idx=proposer_idx)
    node.on_message(Message(src=proposer_idx, dst=node.id,
                            type="BLOCK-ANNOUNCEMENT",
                            payload=payload, t_sent=0.0), t=t)


class TestQueryHarness(unittest.TestCase):
    def test_poll_started_after_announce(self):
        logger, _, _ = build_run_harness(n=4, t_max=2.0)
        starts = [e for e in logger.records
                  if e.event_type == "snowman_poll_started"]
        self.assertGreater(len(starts), 0)
        for s in starts:
            self.assertEqual(len(s.fields["peers"]), 3)
            self.assertNotIn(s.node_id, s.fields["peers"])


class TestQueryUnit(unittest.TestCase):
    def test_query_handler_responds_with_current_preference(self):
        node = make_node(node_id=0, n=4)
        cap = capturers(node)
        kickoff(node)
        block_id = hash_block(slot=1, parent_id=GENESIS_ID, proposer_idx=1,
                              transactions=())
        _announce(node, block_id)
        query = QueryPayload(request_id=42, block_id=block_id)
        node.on_message(Message(src=2, dst=0, type="QUERY",
                                payload=query, t_sent=0.0), t=1.0)
        # One QUERY-RESPONSE sent back to src=2 with the current preference.
        responses = [s for s in cap.sends if s[1] == "QUERY-RESPONSE"]
        self.assertEqual(len(responses), 1)
        dst, _, payload, _ = responses[0]
        self.assertEqual(dst, 2)
        self.assertIsInstance(payload, QueryResponsePayload)
        self.assertEqual(payload.request_id, 42)
        self.assertEqual(payload.preferred_block_id, block_id)

    def test_query_unknown_block_returns_permissive_default(self):
        """Per design spec §3 + message-types §5 Revisions: unknown
        block_id -> respond with the queried block_id itself."""
        node = make_node(node_id=0, n=4)
        cap = capturers(node)
        kickoff(node)
        unknown_id = b"u" * 32
        query = QueryPayload(request_id=7, block_id=unknown_id)
        node.on_message(Message(src=1, dst=0, type="QUERY",
                                payload=query, t_sent=0.0), t=1.0)
        responses = [s for s in cap.sends if s[1] == "QUERY-RESPONSE"]
        self.assertEqual(len(responses), 1)
        _, _, payload, _ = responses[0]
        self.assertEqual(payload.preferred_block_id, unknown_id)

    def test_stale_response_dropped(self):
        """A QUERY-RESPONSE with a request_id that does not match any
        in-flight poll is silently dropped."""
        node = make_node(node_id=0, n=4)
        cap = capturers(node)
        kickoff(node)
        # No polls; any response should drop silently (no emit, no send).
        stale = QueryResponsePayload(request_id=999,
                                     preferred_block_id=b"x" * 32)
        before = len(cap.emitted) + len(cap.sends)
        node.on_message(Message(src=1, dst=0, type="QUERY-RESPONSE",
                                payload=stale, t_sent=0.0), t=1.0)
        after = len(cap.emitted) + len(cap.sends)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
