# tests/integration/test_pbft_proposal.py
"""End-to-end: PBFT pre-prepare phase across the W3 stack (T28 spec § 9.2).

Two scenarios, both driven through config.factory.build_run so the
six-phase bootstrap is real and the determinism contract holds end-to-end:

  Scenario A — n=4, workload=[b"A", b"B", b"C"]
  Scenario B — n=7, workload=[b"X"]

Both run under a single phase, minimal (1e-9) delay, zero drop. The propose-timer
chain ends on workload drain; the run reaches quiescence without a t_max.
"""
import math
import unittest
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from pbft import PBFT_PRE_PREPARED, PBFT_REJECTED, PBFTNode, digest


# 1e-9: the network model requires t_delivered > t_sent, so a literal-zero constant delay is unrepresentable (DelayDist rejects delay <= 0). 1e-9 is the model's minimum.
_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)


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


def _factory(n: int, workload_for):
    """build_run wants (node_id, global_seed) -> Node. Close over n +
    workload assignment. propose_delay=1.0; initial_view=0; weight=1.0."""
    def make(node_id: int, global_seed: int) -> PBFTNode:
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n,
                        workload=workload_for(node_id),
                        propose_delay=1.0, initial_view=0)
    return make


def _run(n: int, workload_for, global_seed=42):
    """Build, attach logger, run to quiescence. Returns (logger, result)."""
    logger = EventLogger()
    handle = build_run(_config(n), global_seed, _factory(n, workload_for))
    handle.scheduler.event_sink = logger.sink
    result = handle.scheduler.run()
    return logger, result


def _count_event(records, event_type: str) -> int:
    return sum(1 for r in records if r.event_type == event_type)


def _count_msg_type(records, msg_type: str) -> int:
    # The EventLogger normalises a Delivery into an EventRecord with
    # event_type == "delivery" and the wire type under fields["msg_type"]
    # (src/event_log/logger.py sink()).
    return sum(1 for r in records
               if r.event_type == "delivery"
               and r.fields.get("msg_type") == msg_type)


class TestScenarioA_n4(unittest.TestCase):
    """n=4, workload=[b"A", b"B", b"C"]; primary = node 0."""

    WORKLOAD = [b"A", b"B", b"C"]

    def _workload_for(self, node_id: int):
        return self.WORKLOAD if node_id == 0 else None

    def test_run_reaches_quiescence(self):
        _, result = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_all_four_nodes_pre_prepared_for_every_seq(self):
        # 4 nodes x 3 seqs = 12 pbft_pre_prepared events.
        logger, _ = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, PBFT_PRE_PREPARED), 12)

    def test_no_rejections(self):
        logger, _ = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, PBFT_REJECTED), 0)

    def test_no_voting_messages_emitted(self):
        # PREPARE / COMMIT / VIEW-CHANGE / NEW-VIEW must be zero in T28.
        logger, _ = _run(n=4, workload_for=self._workload_for)
        for typ in ("PREPARE", "COMMIT", "VIEW-CHANGE", "NEW-VIEW"):
            self.assertEqual(_count_msg_type(logger.records, typ), 0,
                             f"unexpected {typ} delivery in T28")

    def test_pre_prepare_deliveries_count(self):
        # 3 broadcasts x 3 non-primary recipients = 9 PRE-PREPARE deliveries.
        # The primary's self-loop is in-process and does NOT generate a
        # Delivery event (Network.submit_broadcast excludes the sender).
        logger, _ = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(_count_msg_type(logger.records, "PRE-PREPARE"), 9)

    def test_digests_match_workload(self):
        logger, _ = _run(n=4, workload_for=self._workload_for)
        seen_digests = {r.fields["digest"]
                        for r in logger.records
                        if r.event_type == PBFT_PRE_PREPARED}
        expected = {digest(b).hex() for b in self.WORKLOAD}
        self.assertEqual(seen_digests, expected)

    def test_determinism_byte_identical_records(self):
        # Two seed-identical runs produce the same record stream
        # (records compared as tuples).
        la, _ = _run(n=4, workload_for=self._workload_for, global_seed=42)
        lb, _ = _run(n=4, workload_for=self._workload_for, global_seed=42)
        self.assertEqual(list(la.records), list(lb.records))


class TestScenarioB_n7(unittest.TestCase):
    """n=7, workload=[b"X"]; primary = node 0; f = 2."""

    WORKLOAD = [b"X"]

    def _workload_for(self, node_id: int):
        return self.WORKLOAD if node_id == 0 else None

    def test_run_reaches_quiescence(self):
        _, result = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(result.stopped_by, "quiescence")

    def test_all_seven_nodes_pre_prepared_for_seq_0(self):
        logger, _ = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, PBFT_PRE_PREPARED), 7)

    def test_no_rejections(self):
        logger, _ = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, PBFT_REJECTED), 0)

    def test_pre_prepare_deliveries_count(self):
        # 1 broadcast x 6 non-primary recipients = 6 PRE-PREPARE deliveries.
        logger, _ = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(_count_msg_type(logger.records, "PRE-PREPARE"), 6)

    def test_determinism_byte_identical_records(self):
        la, _ = _run(n=7, workload_for=self._workload_for, global_seed=42)
        lb, _ = _run(n=7, workload_for=self._workload_for, global_seed=42)
        self.assertEqual(list(la.records), list(lb.records))


if __name__ == "__main__":
    unittest.main()
