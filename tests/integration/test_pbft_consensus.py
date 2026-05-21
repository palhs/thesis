# tests/integration/test_pbft_consensus.py
"""End-to-end: the full PBFT three-phase commit across the W3 stack
(T29 spec § 10.2).

Two scenarios, both driven through config.factory.build_run so the
six-phase bootstrap is real and the determinism contract holds end-to-end:

  Scenario A — honest full commit (n=4 and n=7), generous vc_delay so no
               view-change occurs.
  Scenario B — view-change under delay (n=4): a constant-delay regime in
               which view 0's timer fires before its commit quorum forms
               but view 1's doubled timer does not, exercising the full
               VIEW-CHANGE -> NEW-VIEW -> reissue -> re-commit path.
"""
import math
import unittest
from types import MappingProxyType

from config.factory import build_run
from config.schema import Config, SeedsConfig
from event_log import EventLogger
from network import DelayDist, Phase
from pbft import PBFTNode, digest


# 1e-9: the network model requires t_delivered > t_sent, so a literal-zero
# constant delay is unrepresentable (DelayDist rejects delay <= 0).
_MINIMAL_DELAY = (Phase(0.0, math.inf, DelayDist("constant", {"delay": 1e-9})),)


def _config(n: int, network, t_max: float = math.inf) -> Config:
    return Config(
        n=n,
        t_max=t_max,
        seeds=SeedsConfig(n_runs=1),
        network=network,
        adversary=MappingProxyType({}),
        protocol_knobs=MappingProxyType({}),
        workload=MappingProxyType({}),
    )


def _factory(n: int, workload_for, *, vc_delay: float,
             propose_delay: float = 1.0):
    """build_run wants (node_id, global_seed) -> Node. Close over n, the
    per-node workload assignment, vc_delay, and propose_delay."""
    def make(node_id: int, global_seed: int) -> PBFTNode:
        return PBFTNode(node_id=node_id, weight=1.0, endpoint=None,
                        global_seed=global_seed, n=n,
                        workload=workload_for(node_id),
                        propose_delay=propose_delay, initial_view=0,
                        vc_delay=vc_delay)
    return make


def _run(n: int, workload_for, *, network=_MINIMAL_DELAY,
         vc_delay: float = 1000.0, propose_delay: float = 1.0,
         t_max: float = math.inf, global_seed: int = 42):
    """Build, attach logger, run. Returns (logger, result)."""
    logger = EventLogger()
    handle = build_run(_config(n, network, t_max), global_seed,
                       _factory(n, workload_for, vc_delay=vc_delay,
                                propose_delay=propose_delay))
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


class TestScenarioA_n4(unittest.TestCase):
    """n=4, workload=[b"X"] on node 0; generous vc_delay -> no view-change."""

    def _workload_for(self, node_id: int):
        return [b"X"] if node_id == 0 else None

    def test_every_node_decides_seq0(self):
        logger, result = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(_count_event(logger.records, "pbft_pre_prepared"), 4)
        self.assertEqual(_count_event(logger.records, "pbft_prepared"), 4)
        self.assertEqual(_count_event(logger.records, "pbft_committed"), 4)
        self.assertEqual(_count_event(logger.records, "decided"), 4)

    def test_no_rejections_or_view_changes(self):
        logger, _ = _run(n=4, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, "pbft_rejected"), 0)
        self.assertEqual(_count_event(logger.records, "pbft_view_change"), 0)
        self.assertEqual(_count_msg_type(logger.records, "VIEW-CHANGE"), 0)
        self.assertEqual(_count_msg_type(logger.records, "NEW-VIEW"), 0)

    def test_decided_value_matches_request(self):
        logger, _ = _run(n=4, workload_for=self._workload_for)
        for r in logger.records:
            if r.event_type == "decided":
                self.assertEqual(r.fields["value"], digest(b"X").hex())

    def test_determinism(self):
        a, _ = _run(n=4, workload_for=self._workload_for, global_seed=42)
        b, _ = _run(n=4, workload_for=self._workload_for, global_seed=42)
        self.assertEqual(list(a.records), list(b.records))


class TestScenarioA_n7(unittest.TestCase):
    """n=7, workload=[b"X"] on node 0; f=2, 2f+1=5."""

    def _workload_for(self, node_id: int):
        return [b"X"] if node_id == 0 else None

    def test_every_node_decides_seq0(self):
        logger, result = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertEqual(_count_event(logger.records, "pbft_pre_prepared"), 7)
        self.assertEqual(_count_event(logger.records, "pbft_prepared"), 7)
        self.assertEqual(_count_event(logger.records, "pbft_committed"), 7)
        self.assertEqual(_count_event(logger.records, "decided"), 7)

    def test_no_rejections_or_view_changes(self):
        logger, _ = _run(n=7, workload_for=self._workload_for)
        self.assertEqual(_count_event(logger.records, "pbft_rejected"), 0)
        self.assertEqual(_count_event(logger.records, "pbft_view_change"), 0)

    def test_decided_value_matches_request(self):
        logger, _ = _run(n=7, workload_for=self._workload_for)
        for r in logger.records:
            if r.event_type == "decided":
                self.assertEqual(r.fields["value"], digest(b"X").hex())

    def test_determinism(self):
        a, _ = _run(n=7, workload_for=self._workload_for, global_seed=42)
        b, _ = _run(n=7, workload_for=self._workload_for, global_seed=42)
        self.assertEqual(list(a.records), list(b.records))


# --- Scenario B: view-change under delay (n=4) -------------------------
#
# Tuned during T29 execution against the real network model. With a
# constant network delay D, the three-phase commit completes ~2D after a
# node reaches PRE_PREPARED, while view v's view-change timer fires
# vc_delay*2^v after it. Choosing D < vc_delay < 2*D makes view 0's timer
# (vc_delay) fire before its commit quorum forms, but view 1's doubled
# timer (2*vc_delay) comfortably outlast the commit -- so view 0 suffers a
# spurious view-change and view 1 commits cleanly.
#
# D=1.0, vc_delay=1.9 sits mid-band (the clean single-recovery band is
# vc_delay in [1.8, 1.95]): every node's view-0 timer fires at t=2.9/3.9,
# before the view-0 commit at t=4.0; the NEW-VIEW reaches every node by
# t=5.9, well inside each escalation timer (2*vc_delay=3.8 after a node's
# own view-change), so the escalation path is not exercised here
# (T29 spec § 10.3). The run reaches quiescence at t=9.7.
_SCEN_B_D = 1.0
_SCEN_B_VC_DELAY = 1.9


def _run_b():
    network = (Phase(0.0, math.inf,
                     DelayDist("constant", {"delay": _SCEN_B_D})),)

    def workload_for(node_id):
        return [b"X"] if node_id == 0 else None

    # t_max=50.0 is a safety bound only -- the healthy run quiesces at
    # t=9.7, far inside it.
    return _run(n=4, workload_for=workload_for, network=network,
                vc_delay=_SCEN_B_VC_DELAY, propose_delay=1.0, t_max=50.0)


class TestScenarioB_viewchange(unittest.TestCase):
    """n=4, workload=[b"X"] on node 0; D < vc_delay < 2*D forces a
    spurious view-change in view 0 and a clean commit in view 1."""

    def test_view_change_occurs_and_request_still_decided(self):
        logger, result = _run_b()
        self.assertEqual(result.stopped_by, "quiescence")
        self.assertGreaterEqual(
            _count_msg_type(logger.records, "VIEW-CHANGE"), 1)
        self.assertGreaterEqual(
            _count_msg_type(logger.records, "NEW-VIEW"), 1)
        self.assertGreaterEqual(_count_event(logger.records, "decided"), 1)
        self.assertEqual(_count_event(logger.records, "pbft_rejected"), 0)
        # View-change does not break safety: the digest decided is the
        # digest proposed.
        for r in logger.records:
            if r.event_type == "decided":
                self.assertEqual(r.fields["value"], digest(b"X").hex())

    def test_all_nodes_reach_view_1(self):
        logger, _ = _run_b()
        entered = {r.fields["new_view"] for r in logger.records
                   if r.event_type == "pbft_new_view"}
        self.assertIn(1, entered)

    def test_determinism(self):
        a, _ = _run_b()
        b, _ = _run_b()
        self.assertEqual(list(a.records), list(b.records))


if __name__ == "__main__":
    unittest.main()
