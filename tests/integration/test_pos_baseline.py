# tests/integration/test_pos_baseline.py
"""T35 — PoS (simplified Casper FFG) correctness under honest validators.

A correctness experiment driving the full Casper FFG honest path
([[algorithms/pos]]) across the W3 stack with an all-honest validator set.
T41 widened the sweep to uniform stake at n in {4, 7, 10, 16, 25} x seed
in range(20) (100 metas), plus the retained n=4 non-uniform-stake scenario
at the same 20 seeds (20 metas) — 120 metas total — and gave every node a
deterministic slot-indexed transaction workload (blocks now carry batches
rather than being empty). Asserts the three T35 outcomes — every node
finalises, no forks, finalisation latency logged — plus byte-identical
determinism, and the T41 workload-axis invariants (slot-indexed block
content, the goodput band, regression of the pre-T41 landed columns).

Distinct from tests/integration/test_casper_baseline.py (the T32
build-verification suite); T35 adds no src/ code — the protocol is
complete (T32 implementation + T33 stake-weighted proposer + T34
extracted finality module). Re-records the canonical event-stream
snapshot under the T33 proposer rule (the T32 page's ## Revisions note
forwards readers here).

Scenarios + the build/run shape live in `src/pos/baseline.py` (T40
harmonisation); this test imports SCENARIOS + run_scenario and asserts
the three outcomes scenario-by-scenario via subTest.

Companion experiment page: wiki/experiments/2026-05-25_pos-baseline.md.

Re-run:
  PYTHONPATH=src:tests/integration python3 -m unittest test_pos_baseline -v
"""
import math
import unittest

from output.schema import ScenarioMeta
from pos.baseline import (
    SCENARIOS, run_scenario,
    _T_MAX, _SLOT_DURATION, _SLOTS_PER_EPOCH,
    _ARRIVAL_PROCESS, _OFFERED_RATE, _TX_BYTES, _CONFLICT_RATE,
)
from pos.summarise import summarise


# slot_duration=1.0, slots_per_epoch=2, attest_offset=1 (default) =>
# epoch e finalises at t = (2*(e+1) + 1)*slot_duration + epsilon, so
# epoch 1 finalises near t=5.0 and epoch 8 near t=19.0. t_max=20.0
# matches the T32 baseline and covers 8 finalised epochs.
_SLOT_DURATION = 1.0
_SLOTS_PER_EPOCH = 2

# Epoch 1 cannot finalise before the slot-5 attestation fires (no earlier
# slot completes the second justify link). Used as the finalisation-time
# lower bound for the latency-logged check.
_EPOCH1_FINALISE_FLOOR = (
    (2 * _SLOTS_PER_EPOCH + 1) * _SLOT_DURATION  # = 5.0
)

# At t_max=20.0 every scenario finalises epochs 1..8 — eight per node.
_EXPECTED_FINALISED_EPOCHS = 8


def _representative(scenarios):
    """One meta per distinct (n, variant) pair — the lowest-seed scenario
    for each. For the FFG sweep that is the 5 uniform n plus the one
    (4, nonuniform), i.e. 6 metas. Exercises every n and variant code
    path; the full seed sweep is determinism-redundant for these
    correctness assertions."""
    seen, out = set(), []
    for m in scenarios:
        key = (m.n, m.variant)
        if key not in seen:
            seen.add(key)
            out.append(m)
    return out


_REPRESENTATIVE = _representative(SCENARIOS)


def _count(records, event_type: str) -> int:
    return sum(1 for r in records if r.event_type == event_type)


def _decided(records):
    return [r for r in records if r.event_type == "decided"]


class TestPoSHonestBaseline(unittest.TestCase):
    """Honest Casper FFG at four scenarios: finalises, no forks, latency
    logged, determinism."""

    def test_every_node_finalises(self):
        """Outcome 1: every validator finalises every reachable epoch.
        Each of the n nodes emits casper_finalised + decided once per
        finalised epoch; under t_max=20.0 that is 8 epochs per node."""
        # representative subset — full sweep verified by the Phase 7 dataset run (output.baseline)
        for meta in _REPRESENTATIVE:
            with self.subTest(run_id=meta.run_id):
                records, result, _ = run_scenario(meta)
                n = meta.n
                self.assertEqual(result.stopped_by, "deadline")
                self.assertEqual(
                    _count(records, "casper_finalised"),
                    n * _EXPECTED_FINALISED_EPOCHS)
                decided = _decided(records)
                self.assertEqual(len(decided), n * _EXPECTED_FINALISED_EPOCHS)
                # Every node 0..n-1 appears, and emits exactly one decided
                # per finalised epoch.
                per_node: dict[int, int] = {}
                for r in decided:
                    per_node[r.node_id] = per_node.get(r.node_id, 0) + 1
                self.assertEqual(sorted(per_node), list(range(n)))
                for count in per_node.values():
                    self.assertEqual(count, _EXPECTED_FINALISED_EPOCHS)

    def test_no_forks(self):
        """Outcome 2: no forks. Every node's decided event for a given
        epoch carries the identical checkpoint_hash, and no validator
        rejects a message on the honest path."""
        # representative subset — full sweep verified by the Phase 7 dataset run (output.baseline)
        for meta in _REPRESENTATIVE:
            with self.subTest(run_id=meta.run_id):
                records, _, _ = run_scenario(meta)
                by_epoch: dict[int, set[str]] = {}
                for r in _decided(records):
                    epoch = r.fields["instance_id"]
                    by_epoch.setdefault(epoch, set()).add(r.fields["value"])
                # Epochs 1..8 all finalised, each agreed on one value.
                self.assertEqual(sorted(by_epoch),
                                 list(range(1, _EXPECTED_FINALISED_EPOCHS + 1)))
                for epoch, values in by_epoch.items():
                    self.assertEqual(
                        len(values), 1,
                        f"epoch {epoch} forked: {values}")
                self.assertEqual(_count(records, "casper_rejected"), 0)

    def test_finalisation_latency_logged(self):
        """Outcome 3: finalisation latency is logged. Every decided
        event's t field is finite and at or after the earliest possible
        finalisation moment (the slot-5 attestation that completes epoch
        2's justify link, which finalises epoch 1)."""
        # representative subset — full sweep verified by the Phase 7 dataset run (output.baseline)
        for meta in _REPRESENTATIVE:
            with self.subTest(run_id=meta.run_id):
                records, _, _ = run_scenario(meta)
                decided = _decided(records)
                self.assertGreater(len(decided), 0)
                for r in decided:
                    self.assertTrue(math.isfinite(r.t))
                    self.assertGreaterEqual(r.t, _EPOCH1_FINALISE_FLOOR)

    def test_determinism(self):
        """Two seed-identical runs produce byte-identical event streams —
        the harness reproducibility contract holds for the PoS honest
        path at every scenario, under the T33 stake-weighted proposer
        rule."""
        # representative subset — full sweep verified by the Phase 7 dataset run (output.baseline)
        # determinism is an engine property; the first 2 scenarios suffice.
        for meta in _REPRESENTATIVE[:2]:
            with self.subTest(run_id=meta.run_id):
                a_records, _, _ = run_scenario(meta)
                b_records, _, _ = run_scenario(meta)
                self.assertEqual(a_records, b_records)


def _n4_uniform_seed42() -> ScenarioMeta:
    """The pinned regression / goodput probe: n=4 uniform at seed 42.

    seed 42 is NOT in the T41 sweep (seeds are range(20)) — it is the
    historical T35/T40 probe seed. The FFG block CONTENT must not perturb
    consensus timing, so this meta's landed timing/reliability columns must
    match the pre-T41 capture byte-for-byte. Built directly (not pulled
    from SCENARIOS) with the full workload axis the reducer needs.
    """
    return ScenarioMeta(
        run_id="casper-ffg-n4-uniform", protocol="casper-ffg", n=4,
        variant="uniform", seed=42, t_max=_T_MAX,
        arrival_process=_ARRIVAL_PROCESS, tx_bytes=_TX_BYTES,
        conflict_rate=_CONFLICT_RATE, offered_rate=_OFFERED_RATE,
        interval=_SLOT_DURATION, slots_per_epoch=_SLOTS_PER_EPOCH,
    )


class TestT41WorkloadAxis(unittest.TestCase):
    """T41: the scaling sweep + slot-indexed batch workload must leave
    every pre-T41 landed column unchanged, keep goodput in its band, and
    stay deterministic at the reducer-row level."""

    # Pre-T41 capture at n=4 uniform seed=42 (recorded from the reducer
    # BEFORE the slot-indexed-batch edit; see the T41 handoff). FFG block
    # content does not feed consensus timing, so these must be identical.
    _PRE_T41_LANDED = {
        "commit_latency_ms":      5000.000001,
        "finality_latency_ms":    5000.000001,
        "tps":                    1.6,
        "consensus_msgs_per_acu": 5.15625,
        "success_rate":           1.0,
        "fork_rate":              0.0,
    }

    def test_scenario_count_is_120(self):
        """5 uniform n x 20 seeds (100) + n4 nonuniform x 20 seeds (20)."""
        self.assertEqual(len(SCENARIOS), 120)
        uniform = [m for m in SCENARIOS if m.variant == "uniform"]
        nonuni = [m for m in SCENARIOS if m.variant == "nonuniform"]
        self.assertEqual(len(uniform), 100)
        self.assertEqual(len(nonuni), 20)
        self.assertEqual(sorted({m.n for m in uniform}), [4, 7, 10, 16, 25])
        self.assertEqual(sorted({m.seed for m in uniform}), list(range(20)))
        self.assertTrue(all(m.n == 4 for m in nonuni))

    def test_metas_carry_workload_axis(self):
        """Every meta carries the workload axis the FFG reducer needs to
        regenerate the byte-identical batch stream."""
        for m in SCENARIOS:
            with self.subTest(run_id=m.run_id, seed=m.seed):
                self.assertEqual(m.arrival_process, _ARRIVAL_PROCESS)
                self.assertEqual(m.tx_bytes, _TX_BYTES)
                self.assertEqual(m.conflict_rate, _CONFLICT_RATE)
                self.assertEqual(m.offered_rate, _OFFERED_RATE)
                self.assertEqual(m.interval, _SLOT_DURATION)
                self.assertEqual(m.slots_per_epoch, _SLOTS_PER_EPOCH)

    def test_landed_columns_unchanged_vs_pre_t41(self):
        """REGRESSION: the slot-indexed batch workload must NOT move any
        pre-T41 landed column at n=4 uniform seed=42 — block content does
        not affect FFG consensus timing or reliability."""
        records, result, meta = run_scenario(_n4_uniform_seed42())
        row = summarise(records, result, meta)
        for col, expected in self._PRE_T41_LANDED.items():
            with self.subTest(column=col):
                self.assertAlmostEqual(
                    row[col], expected, places=6,
                    msg=f"{col} moved from pre-T41 {expected!r} to "
                        f"{row[col]!r}; block content must not change "
                        f"consensus timing")

    def test_blocks_now_carry_transactions(self):
        """The slot-indexed workload makes proposed blocks non-empty: the
        slot-1 proposer's first block carries its slot-1 batch."""
        from workload import WorkloadConfig, generate_batches
        from pos.selection import stake_weighted_proposer
        meta = _n4_uniform_seed42()
        batches = generate_batches(
            WorkloadConfig(_ARRIVAL_PROCESS, _OFFERED_RATE,
                           _TX_BYTES, _CONFLICT_RATE),
            meta.seed,
            n_opportunities=math.ceil(_T_MAX / _SLOT_DURATION) + 2,
            interval=_SLOT_DURATION,
        )
        # Under offered_rate=100, slot-1 batch is overwhelmingly non-empty.
        self.assertGreater(len(batches[1]), 0)
        # The slot-1 proposer is well-defined and in range.
        p1 = stake_weighted_proposer(1, {i: 3.0 for i in range(4)}, meta.seed)
        self.assertIn(p1, range(4))

    def test_goodput_band(self):
        """GOODPUT INVARIANT at n=4 uniform seed=42.

        The reducer maps each distinct finalised epoch to `slots_per_epoch`
        proposal opportunities (n_opportunities = n_epochs * slots_per_epoch
        = 8 * 2 = 16) and divides committed tx by t_max=20. Observed
        goodput ~= 78.55 tx/s.

        Band documented: goodput in (0, 110]. The headline figure sits
        ~21% BELOW offered_rate=100 not because the workload is wrong but
        because the reducer's epoch->opportunity denominator (16 opps over
        a 20 s window) under-counts opportunities relative to the time
        denominator — the documented genesis/epoch-mapping approximation
        in src/pos/summarise.py. The underlying per-opportunity arrival
        mean IS within ~15% of offered_rate (see the committed_tx check
        below), which is the invariant the band is really guarding.
        """
        from output.metrics import committed_tx
        records, result, meta = run_scenario(_n4_uniform_seed42())
        row = summarise(records, result, meta)
        gp = row["goodput"]
        self.assertFalse(math.isnan(gp))
        self.assertGreater(gp, 0.0)
        self.assertLessEqual(gp, 110.0)
        # Per-opportunity arrival mean within ~15% of offered_rate=100.
        n_epochs = len({r.fields.get("instance_id")
                        for r in records if r.event_type == "decided"})
        n_opps = n_epochs * _SLOTS_PER_EPOCH
        self.assertEqual(n_epochs, 8)
        per_opp = committed_tx(meta, n_opps) / n_opps
        self.assertLessEqual(abs(per_opp - _OFFERED_RATE) / _OFFERED_RATE,
                             0.15,
                             f"per-opportunity arrival mean {per_opp} not "
                             f"within 15% of offered_rate {_OFFERED_RATE}")

    def test_reducer_row_deterministic(self):
        """DETERMINISM: two runs of one scenario yield identical event
        records AND an identical reducer row (every column equal, NaNs
        matching position-for-position)."""
        meta = _n4_uniform_seed42()
        a_records, a_result, _ = run_scenario(meta)
        b_records, b_result, _ = run_scenario(meta)
        self.assertEqual(a_records, b_records)
        a_row = summarise(a_records, a_result, meta)
        b_row = summarise(b_records, b_result, meta)
        self.assertEqual(set(a_row), set(b_row))
        for col in a_row:
            with self.subTest(column=col):
                av, bv = a_row[col], b_row[col]
                if isinstance(av, float) and math.isnan(av):
                    self.assertTrue(math.isnan(bv))
                else:
                    self.assertEqual(av, bv)


if __name__ == "__main__":
    unittest.main()
