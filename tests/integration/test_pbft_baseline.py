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

Companion experiment page: wiki/experiments/2026-05-21_pbft-baseline.md.

Re-run:
  PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_baseline -v
"""
import math
import unittest
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from pbft import PBFTNode, digest


# The network model requires t_delivered > t_sent, so a literal-zero delay
# is unrepresentable; 1e-9 is the minimum constant delay (matches the T29
# Scenario A baseline). Honest run: no drop, no partition.
_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)

# Honest validator-set sizes. f = (n-1)//3, commit quorum = 2f+1:
# n=4 -> f=1, quorum 3; n=7 -> f=2, quorum 5; n=10 -> f=3, quorum 7.
_HONEST_N = (4, 7, 10)

# The single request the honest run commits; rides on node 0's workload.
_REQUEST = b"X"

# The primary's propose timer fires at this t, emitting the PRE-PREPARE for
# seq 0; every `decided` event therefore carries t > _PROPOSE_DELAY.
_PROPOSE_DELAY = 1.0


def _config(n: int) -> Config:
    return Config(
        n=n,
        t_max=math.inf,
        seeds=SeedsConfig(n_runs=1),
        network=_MINIMAL_DELAY,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _factory(n: int):
    """build_run wants (node_id, global_seed) -> Node. All-honest PBFTNodes;
    the single request rides on node 0; vc_delay is generous so no honest
    run ever triggers a view-change."""
    def make(node_id: int, global_seed: int) -> PBFTNode:
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n,
                        workload=[_REQUEST] if node_id == 0 else None,
                        propose_delay=_PROPOSE_DELAY, initial_view=0,
                        vc_delay=1000.0)
    return make


def _run(n: int, global_seed: int = 42):
    """Build, attach an EventLogger, run to quiescence -> (logger, result)."""
    logger = EventLogger()
    handle = build_run(_config(n), global_seed, _factory(n))
    handle.scheduler.event_sink = logger.sink
    result = handle.scheduler.run()
    return logger, result


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
        for n in _HONEST_N:
            with self.subTest(n=n):
                logger, result = _run(n)
                self.assertEqual(result.stopped_by, "quiescence")
                self.assertEqual(
                    _count_event(logger.records, "pbft_pre_prepared"), n)
                self.assertEqual(
                    _count_event(logger.records, "pbft_prepared"), n)
                self.assertEqual(
                    _count_event(logger.records, "pbft_committed"), n)
                decided = _decided(logger.records)
                self.assertEqual(len(decided), n)
                # Every validator 0..n-1 reaches `decided`, exactly once.
                self.assertEqual(sorted(r.node_id for r in decided),
                                 list(range(n)))

    def test_no_forks(self):
        """Outcome 2: no forks. Every `decided` for a given seq carries the
        same value, that value is the proposed request's digest, and no
        node-disagreement surfaces as a rejection or a view-change."""
        for n in _HONEST_N:
            with self.subTest(n=n):
                logger, _ = _run(n)
                by_seq: dict[int, set[str]] = {}
                for r in _decided(logger.records):
                    seq = r.fields["instance_id"][1]
                    by_seq.setdefault(seq, set()).add(r.fields["value"])
                # Single-request honest run: exactly seq 0, one value, and
                # that value is the digest of the proposed request.
                self.assertEqual(list(by_seq), [0])
                self.assertEqual(by_seq[0], {digest(_REQUEST).hex()})
                # An honest run neither rejects messages nor changes view.
                self.assertEqual(
                    _count_event(logger.records, "pbft_rejected"), 0)
                self.assertEqual(
                    _count_event(logger.records, "pbft_view_change"), 0)
                self.assertEqual(
                    _count_msg_type(logger.records, "VIEW-CHANGE"), 0)
                self.assertEqual(
                    _count_msg_type(logger.records, "NEW-VIEW"), 0)

    def test_finalization_latency_logged(self):
        """Outcome 3: finalization latency is logged. The `decided` event's
        `t` is the per-node finalization time measured from run start
        (t=0); every node's is finite, positive, and strictly later than
        the t=_PROPOSE_DELAY proposal of seq 0."""
        for n in _HONEST_N:
            with self.subTest(n=n):
                logger, _ = _run(n)
                decided = _decided(logger.records)
                self.assertEqual(len(decided), n)
                for r in decided:
                    self.assertTrue(math.isfinite(r.t))
                    self.assertGreater(r.t, _PROPOSE_DELAY)

    def test_determinism(self):
        """Two seed-identical runs produce byte-identical event streams —
        the harness reproducibility contract holds for the PBFT honest
        path at every n."""
        for n in _HONEST_N:
            with self.subTest(n=n):
                a, _ = _run(n, global_seed=42)
                b, _ = _run(n, global_seed=42)
                self.assertEqual(list(a.records), list(b.records))


if __name__ == "__main__":
    unittest.main()
