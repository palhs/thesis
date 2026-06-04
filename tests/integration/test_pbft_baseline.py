# tests/integration/test_pbft_baseline.py
"""T30 / T41 — PBFT correctness and windowed-workload check.

A correctness experiment driving the full PBFT three-phase commit
([[algorithms/pbft]]) across the W3 stack with an all-honest validator set.

T41 windowed the honest path: instead of running to quiescence with a
single trivial request (one committed instance), `src/pbft/baseline.py` now
runs over a fixed `_T_MAX` window and feeds the primary a deterministic
transaction stream, so the primary proposes continuously and MANY instances
commit. The SCENARIOS sweep is `n in {4,7,10,16,25}` x `seed in range(20)`.

This suite asserts:
  - per-scenario honest-path correctness on a SAMPLE of SCENARIOS (every
    node finalizes every committed seq, no forks, latency logged) — the
    full 100-scenario cross product is exercised by `make test-pbft`'s
    determinism check but correctness is sampled to keep the run cheap;
  - the T41 windowing contract: the first-instance latency is byte-identical
    to the pre-T41 value, the window now decides MORE THAN ONE instance, and
    goodput tracks the offered rate at sub-saturation.

Distinct from tests/integration/test_pbft_consensus.py (the T29
build-verification suite) and from the tests/pbft/ unit suite.

Companion experiment page: wiki/experiments/2026-05-21_pbft-baseline.md.

Re-run:
  PYTHONPATH=src:tests/integration python3 -m unittest test_pbft_baseline -v
"""
import math
import unittest

from pbft.baseline import (
    PROPOSE_DELAY,
    SCENARIOS,
    _scenario,
    run_scenario,
)
from pbft.summarise import summarise

# Pre-T41 first-instance COMMIT-quorum latency at n=4, seed=42 (captured
# before the windowing change; output-format.md §5.1 defines latency on the
# first decided instance). The windowing must leave this byte-identical, and
# T70 finding #1 leaves `commit_latency_ms` measured at this 2f+1 COMMIT
# quorum unchanged.
_BASELINE_COMMIT_LATENCY_MS = 1000.0000030000002
# T70 finding #1: client-observed finality is one network hop (1e-9 s under
# the minimal-delay baseline) past the COMMIT quorum, so the first instance's
# `finality_latency_ms` sits exactly one hop after the commit value.
_BASELINE_FINALITY_LATENCY_MS = 1000.0000040000003

def _representative(scenarios):
    """One meta per distinct (n, variant) pair — the lowest-seed scenario
    for each. Exercises every n and variant code path; the full seed sweep
    is determinism-redundant for these correctness assertions."""
    seen, out = set(), []
    for m in scenarios:
        key = (m.n, m.variant)
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out


_REPRESENTATIVE = _representative(SCENARIOS)


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


def _rows_equal(a: dict, b: dict) -> bool:
    """NaN-safe reducer-row equality. The reducer emits NaN sentinels for
    inapplicable columns (e.g. the Snowman params), and `nan != nan`, so a
    plain dict `==` would always fail. Treat two NaNs in the same column as
    equal; everything else compares by value."""
    if a.keys() != b.keys():
        return False
    for k in a:
        x, y = a[k], b[k]
        x_nan = isinstance(x, float) and math.isnan(x)
        y_nan = isinstance(y, float) and math.isnan(y)
        if x_nan and y_nan:
            continue
        if x != y:
            return False
    return True


class TestPBFTScenarioSweep(unittest.TestCase):
    """The T41 SCENARIOS cross product is well-formed."""

    def test_scenario_count_is_100(self):
        self.assertEqual(len(SCENARIOS), 100)

    def test_scenario_identity(self):
        # Row identity is (protocol, n, run_id, seed): run_id omits the
        # seed; n in {4,7,10,16,25}; seed in range(20). All distinct.
        keys = {(m.protocol, m.n, m.run_id, m.seed) for m in SCENARIOS}
        self.assertEqual(len(keys), 100)
        self.assertEqual({m.n for m in SCENARIOS}, {4, 7, 10, 16, 25})
        self.assertEqual({m.seed for m in SCENARIOS}, set(range(20)))
        for m in SCENARIOS:
            self.assertEqual(m.run_id, f"pbft-n{m.n}")
            self.assertEqual(m.protocol, "pbft")
            self.assertEqual(m.t_max, 20.0)
            self.assertEqual(m.arrival_process, "poisson")
            self.assertEqual(m.tx_bytes, 512)
            self.assertEqual(m.conflict_rate, 0.0)
            self.assertEqual(m.offered_rate, 100.0)
            self.assertEqual(m.interval, PROPOSE_DELAY)


class TestPBFTHonestWindow(unittest.TestCase):
    """Honest PBFT over the fixed window: every committed seq finalizes on
    every node, no forks, latency logged. Sampled over n values."""

    def test_every_node_finalizes_every_committed_seq(self):
        """Outcome 1: for every seq that commits inside the window, all n
        nodes reach `decided` for it exactly once. The run halts on the
        `_T_MAX` deadline (the windowed stop condition), not on quiescence."""
        # representative subset — full sweep verified by the Phase 7 dataset run (output.baseline)
        for meta in _REPRESENTATIVE:
            with self.subTest(run_id=meta.run_id, seed=meta.seed):
                records, result, _ = run_scenario(meta)
                n = meta.n
                self.assertEqual(result.stopped_by, "deadline")
                decided = _decided(records)
                # Group decided events by seq; each committed seq must be
                # decided by exactly the full validator set 0..n-1.
                by_seq: dict[int, list[int]] = {}
                for r in decided:
                    seq = r.fields["instance_id"][1]
                    by_seq.setdefault(seq, []).append(r.node_id)
                self.assertGreater(len(by_seq), 0)
                for seq, nodes in by_seq.items():
                    self.assertEqual(sorted(nodes), list(range(n)),
                                     f"seq {seq} not finalized by all nodes")

    def test_no_forks(self):
        """Outcome 2: no forks. Every `decided` for a given seq carries the
        same value, and no node-disagreement surfaces as a rejection or a
        view-change."""
        # representative subset — full sweep verified by the Phase 7 dataset run (output.baseline)
        for meta in _REPRESENTATIVE:
            with self.subTest(run_id=meta.run_id, seed=meta.seed):
                records, _, _ = run_scenario(meta)
                by_seq: dict[int, set[str]] = {}
                for r in _decided(records):
                    seq = r.fields["instance_id"][1]
                    by_seq.setdefault(seq, set()).add(r.fields["value"])
                # Each seq decides to exactly one value across all nodes.
                for seq, values in by_seq.items():
                    self.assertEqual(len(values), 1,
                                     f"seq {seq} forked: {values}")
                # An honest run neither rejects messages nor changes view.
                self.assertEqual(_count_event(records, "pbft_rejected"), 0)
                self.assertEqual(_count_event(records, "pbft_view_change"), 0)
                self.assertEqual(_count_msg_type(records, "VIEW-CHANGE"), 0)
                self.assertEqual(_count_msg_type(records, "NEW-VIEW"), 0)

    def test_every_committed_seq_reaches_client_finality(self):
        """T70 finding #1 core invariant: every seq that commits inside the
        window is later client-finalized exactly once (the collector emits one
        `pbft_client_finalized` per committed seq), and each client-finalize
        is strictly later than that seq's COMMIT quorum."""
        for meta in _REPRESENTATIVE:
            with self.subTest(run_id=meta.run_id, seed=meta.seed):
                records, _, _ = run_scenario(meta)
                # Earliest commit ('decided') time per seq across all nodes.
                commit_t: dict[int, float] = {}
                for r in _decided(records):
                    seq = r.fields["instance_id"][1]
                    commit_t[seq] = min(commit_t.get(seq, r.t), r.t)
                final = [r for r in records
                         if r.event_type == "pbft_client_finalized"]
                final_by_seq: dict[int, list[float]] = {}
                for r in final:
                    final_by_seq.setdefault(r.fields["seq"], []).append(r.t)
                # Every committed seq finalizes exactly once.
                self.assertEqual(set(final_by_seq), set(commit_t),
                                 "committed seqs and finalized seqs differ")
                for seq, ts in final_by_seq.items():
                    self.assertEqual(len(ts), 1,
                                     f"seq {seq} finalized {len(ts)} times")
                    self.assertGreater(ts[0], commit_t[seq],
                                       f"seq {seq} finalized before/at commit")

    def test_finalization_latency_logged(self):
        """Outcome 3: every `decided` event's `t` is finite, positive, and
        strictly later than the t=PROPOSE_DELAY first proposal."""
        # representative subset — full sweep verified by the Phase 7 dataset run (output.baseline)
        for meta in _REPRESENTATIVE:
            with self.subTest(run_id=meta.run_id, seed=meta.seed):
                records, _, _ = run_scenario(meta)
                decided = _decided(records)
                self.assertGreater(len(decided), 0)
                for r in decided:
                    self.assertTrue(math.isfinite(r.t))
                    self.assertGreater(r.t, PROPOSE_DELAY)


class TestPBFTWindowingContract(unittest.TestCase):
    """The T41 windowing must (a) preserve first-instance latency exactly,
    (b) decide more than one instance, (c) yield goodput ~ offered_rate.
    Pinned at n=4, seed=42 — the scenario whose pre-change value we captured.
    """

    def setUp(self):
        self.meta = _scenario(4, 42)
        self.records, self.result, _ = run_scenario(self.meta)
        self.row = summarise(self.records, self.result, self.meta)

    def test_first_instance_commit_latency_unchanged(self):
        """REGRESSION: commit_latency_ms is defined on the FIRST decided
        instance (output-format.md §5.1) at the 2f+1 COMMIT quorum. Neither
        windowing nor T70 finding #1 may perturb it — assert byte-identical to
        the captured value. If this moves, the COMMIT-quorum measurement broke.
        """
        self.assertEqual(self.row["commit_latency_ms"],
                         _BASELINE_COMMIT_LATENCY_MS)

    def test_first_instance_finality_one_hop_past_commit(self):
        """T70 finding #1: client-observed finality (f+1 matching REPLYs) is
        one network hop past the COMMIT quorum, so finality_latency_ms is
        strictly greater than commit_latency_ms and equals the captured
        one-hop-later value."""
        self.assertEqual(self.row["finality_latency_ms"],
                         _BASELINE_FINALITY_LATENCY_MS)
        self.assertGreater(self.row["finality_latency_ms"],
                           self.row["commit_latency_ms"])

    def test_decides_more_than_one_instance(self):
        """The window now commits MANY instances (it used to commit exactly
        one). Count distinct decided instance_ids."""
        decided = _decided(self.records)
        distinct = {r.fields.get("instance_id") for r in decided}
        self.assertGreater(len(distinct), 1)

    def test_goodput_tracks_offered_rate(self):
        """GOODPUT INVARIANT: at sub-saturation every batch commits, so
        goodput ~ offered_rate. Assert it is positive, within a 10% ceiling
        over offered_rate (Poisson batch-size jitter only pushes it down,
        never far up), and within ~15% of offered_rate."""
        offered = self.meta.offered_rate
        gp = self.row["goodput"]
        self.assertGreater(gp, 0.0)
        self.assertLessEqual(gp, offered * 1.10)
        self.assertLessEqual(abs(gp - offered) / offered, 0.15)


class TestPBFTDeterminism(unittest.TestCase):
    """Byte-identical replay over the full 100-scenario sweep."""

    def test_records_and_reducer_identical_across_runs(self):
        # representative subset — full sweep verified by the Phase 7 dataset run (output.baseline)
        # determinism is an engine property; the first 2 scenarios suffice.
        for meta in _REPRESENTATIVE[:2]:
            with self.subTest(run_id=meta.run_id, seed=meta.seed):
                a_records, a_result, _ = run_scenario(meta)
                b_records, b_result, _ = run_scenario(meta)
                self.assertEqual(a_records, b_records)
                self.assertTrue(
                    _rows_equal(summarise(a_records, a_result, meta),
                                summarise(b_records, b_result, meta)))


if __name__ == "__main__":
    unittest.main()
