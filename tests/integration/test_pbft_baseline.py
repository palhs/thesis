# tests/integration/test_pbft_baseline.py
"""T30 — PBFT correctness under honest nodes.

A correctness experiment driving the full PBFT three-phase commit
([[algorithms/pbft]]) across the W3 stack with an all-honest validator set
at n in {4, 7, 10}. Asserts the three T30 outcomes: every node finalizes,
no forks, finalization latency logged.

Distinct from tests/integration/test_pbft_consensus.py (the T29
build-verification suite, n=4/7 plus a view-change scenario) and from the
tests/pbft/ unit suite (T28/T29, extended by T31). T30 adds no src/ code —
the protocol is complete; this is the honest-path correctness check.

Scenarios + the build/run shape live in `src/pbft/baseline.py` (T40
harmonisation); this test imports SCENARIOS + run_scenario and asserts
the three outcomes scenario-by-scenario via subTest.

Companion experiment page: wiki/experiments/2026-05-21_pbft-baseline.md.

Re-run:
  PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_baseline -v
"""
import math
import unittest

from pbft import digest
from pbft.baseline import PROPOSE_DELAY, REQUEST, SCENARIOS, run_scenario


def _count_event(records, event_type: str) -> int:
    return sum(1 for r in records if r.event_type == event_type)


def _count_msg_type(records, msg_type: str) -> int:
    # The EventLogger normalises a Delivery into an EventRecord with
    # event_type == "delivery" and the wire type under fields["msg_type"].
    return sum(1 for r in records
               if r.event_type == "delivery"
               and r.fields.get("msg_type") == msg_type)


def _decided(records):
    return [r for r in records if r.event_type == "decided"]


class TestPBFTHonestBaseline(unittest.TestCase):
    """Honest PBFT at n in {4, 7, 10}: finalizes, no forks, latency logged."""

    def test_every_node_finalizes(self):
        """Outcome 1: all n nodes finalize seq 0 — the full
        pre_prepared -> prepared -> committed -> decided pipeline fires once
        per node, and the run halts on quiescence (no stall)."""
        for meta in SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                records, result, _ = run_scenario(meta)
                n = meta.n
                self.assertEqual(result.stopped_by, "quiescence")
                self.assertEqual(
                    _count_event(records, "pbft_pre_prepared"), n)
                self.assertEqual(
                    _count_event(records, "pbft_prepared"), n)
                self.assertEqual(
                    _count_event(records, "pbft_committed"), n)
                decided = _decided(records)
                self.assertEqual(len(decided), n)
                # Every validator 0..n-1 reaches `decided`, exactly once.
                self.assertEqual(sorted(r.node_id for r in decided),
                                 list(range(n)))

    def test_no_forks(self):
        """Outcome 2: no forks. Every `decided` for a given seq carries the
        same value, that value is the proposed request's digest, and no
        node-disagreement surfaces as a rejection or a view-change."""
        for meta in SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                records, _, _ = run_scenario(meta)
                by_seq: dict[int, set[str]] = {}
                for r in _decided(records):
                    seq = r.fields["instance_id"][1]
                    by_seq.setdefault(seq, set()).add(r.fields["value"])
                # Single-request honest run: exactly seq 0, one value, and
                # that value is the digest of the proposed request.
                self.assertEqual(list(by_seq), [0])
                self.assertEqual(by_seq[0], {digest(REQUEST).hex()})
                # An honest run neither rejects messages nor changes view.
                self.assertEqual(
                    _count_event(records, "pbft_rejected"), 0)
                self.assertEqual(
                    _count_event(records, "pbft_view_change"), 0)
                self.assertEqual(
                    _count_msg_type(records, "VIEW-CHANGE"), 0)
                self.assertEqual(
                    _count_msg_type(records, "NEW-VIEW"), 0)

    def test_finalization_latency_logged(self):
        """Outcome 3: finalization latency is logged. The `decided` event's
        `t` is the per-node finalization time measured from run start
        (t=0); every node's is finite, positive, and strictly later than
        the t=PROPOSE_DELAY proposal of seq 0."""
        for meta in SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                records, _, _ = run_scenario(meta)
                n = meta.n
                decided = _decided(records)
                self.assertEqual(len(decided), n)
                for r in decided:
                    self.assertTrue(math.isfinite(r.t))
                    self.assertGreater(r.t, PROPOSE_DELAY)

    def test_determinism(self):
        """Two seed-identical runs produce byte-identical event streams —
        the harness reproducibility contract holds for the PBFT honest
        path at every n."""
        for meta in SCENARIOS:
            with self.subTest(run_id=meta.run_id):
                a_records, _, _ = run_scenario(meta)
                b_records, _, _ = run_scenario(meta)
                self.assertEqual(a_records, b_records)


if __name__ == "__main__":
    unittest.main()
