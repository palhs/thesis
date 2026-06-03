# tests/pbft/test_batch_payload.py
"""T41 — PBFT batch-payload acceptance.

The T41 baseline feeds the primary a transaction *batch* per proposal
opportunity. PBFTNode treats the PRE-PREPARE `request_payload` as an opaque
`bytes` blob and only `digest()`s it, so the baseline encodes each batch (a
`tuple[bytes, ...]` from the workload generator) canonically as
`b"".join(batch)` before it reaches the node.

This suite pins that contract at the node boundary:
  - the canonical batch encoding digests deterministically;
  - a PRE-PREPARE carrying a batch-derived payload is accepted (reaches
    PRE_PREPARED, no rejection) exactly as a single-request payload was.

Shares the T31 fixtures in tests/pbft/_helpers.py.
"""
from __future__ import annotations

import unittest

from pbft.digest import digest
from pbft.instance import InstanceState
from pbft.node import PBFT_PRE_PREPARED, PBFT_REJECTED
from workload import WorkloadConfig, generate_batches

from _helpers import capturers, kickoff, make_node, pre_prepare


def _encode(batch: tuple[bytes, ...]) -> bytes:
    """The baseline's canonical batch -> bytes encoding (b"".join)."""
    return b"".join(batch)


class TestBatchDigest(unittest.TestCase):
    def test_batch_digests_deterministically(self):
        """The same batch encodes and digests to the same bytes every time
        — the byte-identical-replay contract the whole pipeline relies on."""
        cfg = WorkloadConfig("poisson", 100.0, 512, 0.0)
        batches = generate_batches(cfg, global_seed=42,
                                   n_opportunities=5, interval=1.0)
        for batch in batches:
            blob = _encode(batch)
            self.assertIsInstance(blob, bytes)
            # Length is the sum of the constituent tx lengths (join adds no
            # separator), and the digest is stable across calls.
            self.assertEqual(len(blob), sum(len(tx) for tx in batch))
            self.assertEqual(digest(blob), digest(_encode(batch)))

    def test_distinct_batches_distinct_digests(self):
        """Two different non-empty batches encode to different digests, so
        distinct proposals carry distinct request_digests."""
        cfg = WorkloadConfig("poisson", 100.0, 512, 0.0)
        batches = generate_batches(cfg, global_seed=42,
                                   n_opportunities=8, interval=1.0)
        nonempty = [b for b in batches if b]
        self.assertGreaterEqual(len(nonempty), 2)
        digs = {digest(_encode(b)) for b in nonempty}
        self.assertEqual(len(digs), len(nonempty))


class TestBatchPrePrepareAccepted(unittest.TestCase):
    def test_pre_prepare_carrying_batch_is_accepted(self):
        """A recipient validator accepts a PRE-PREPARE whose payload is a
        batch-derived blob: it reaches PRE_PREPARED and emits no rejection,
        exactly as the single-request honest path did."""
        cfg = WorkloadConfig("poisson", 100.0, 512, 0.0)
        batches = generate_batches(cfg, global_seed=42,
                                   n_opportunities=4, interval=1.0)
        batch = next(b for b in batches if b)   # a non-empty batch
        blob = _encode(batch)

        node = make_node(1, n=4, view=0)        # node 1 is not the primary
        cap = capturers(node)
        kickoff(node)
        node.on_message(pre_prepare(0, 0, 0, blob, dst=1), t=1.0)

        inst = node.inst[(0, 0)]
        self.assertIs(inst.state, InstanceState.PRE_PREPARED)
        self.assertEqual(inst.digest, digest(blob))
        kinds = [e[0] for e in cap.emitted]
        self.assertIn(PBFT_PRE_PREPARED, kinds)
        self.assertNotIn(PBFT_REJECTED, kinds)


if __name__ == "__main__":
    unittest.main()
