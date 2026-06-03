"""T41 Snowman scaling-workload regression + reducer invariants.

Asserts (1) the slot-indexed batch workload does NOT perturb any pre-T41
landed reducer column at seed=42, n=7 (block content must not change
Snowman consensus timing), (2) goodput tracks the offered rate, and (3)
the workload-carrying run stays byte-identical across two runs (records +
reducer row).

n=7 is chosen as the regression anchor: it is a *main-file* n (n=4 is
sanity-only), so its columns flow into results/baseline.csv.
"""
import math
import unittest

from output.schema import ScenarioMeta
from snowman.baseline import _T_MAX, run_scenario
from snowman.summarise import summarise


def _meta_n7_seed42() -> ScenarioMeta:
    return ScenarioMeta(run_id="snowman-n7", protocol="snowman", n=7,
                        variant=None, seed=42, t_max=_T_MAX,
                        arrival_process="poisson", tx_bytes=512,
                        conflict_rate=0.0, offered_rate=100.0,
                        interval=1.0, slots_per_epoch=None)


# Landed reducer columns captured from the PRE-T41 (empty-block) run at
# seed=42, n=7. Snowman consensus timing depends only on the round /
# poll FSM, never on block payload, so adding slot-indexed batches must
# leave every one of these byte-identical.
_LANDED_PRE_T41 = {
    "commit_latency_ms":      1000.0000460000037,
    "finality_latency_ms":    1000.0000460000037,
    "tps":                    6.65,
    "consensus_msgs_per_acu": 180.85714285714286,
    "success_rate":           1.0,
    "fork_rate":              0.0,
    "K":                      6,
    "alpha_p":                4,
    "alpha_c":                5,
    "beta":                   15,
    "alpha_c_over_K":         0.8333333333333334,
}


class TestSnowmanWorkloadRegression(unittest.TestCase):
    def test_landed_columns_unchanged_n7_seed42(self):
        """Block content must not change Snowman consensus timing: every
        pre-T41 landed reducer column is identical after slot-indexed
        batches are wired in."""
        meta = _meta_n7_seed42()
        records, result, _ = run_scenario(meta)
        row = summarise(records, result, meta)
        for col, expected in _LANDED_PRE_T41.items():
            with self.subTest(column=col):
                self.assertEqual(row[col], expected,
                                 f"{col} moved: {row[col]} != {expected}")


class TestSnowmanGoodput(unittest.TestCase):
    def test_goodput_tracks_offered_rate(self):
        """Snowman decides ~1 block/slot and nearly every slot's block
        decides, so goodput ~= offered_rate=100. Band: within ~15% of
        100, i.e. (85, 115], and structurally in (0, 110] (one block per
        ~1s slot caps committed batches at the offered draws)."""
        meta = _meta_n7_seed42()
        records, result, _ = run_scenario(meta)
        row = summarise(records, result, meta)
        gp = row["goodput"]
        self.assertTrue(math.isfinite(gp))
        self.assertGreater(gp, 0.0)
        self.assertLessEqual(gp, 110.0)
        self.assertGreaterEqual(gp, 85.0)   # within 15% below offered_rate
        self.assertLessEqual(gp, 115.0)     # within 15% above offered_rate
        # Snowman: n_opportunities = distinct decided blocks; one per slot.
        decided = [r for r in records if r.event_type == "decided"]
        distinct = len({r.fields.get("instance_id") for r in decided})
        self.assertGreater(distinct, 0)


class TestSnowmanWorkloadDeterminism(unittest.TestCase):
    def test_records_and_reducer_row_identical(self):
        """Two runs of one workload-carrying scenario produce identical
        event records AND identical reducer rows."""
        meta = _meta_n7_seed42()
        a_records, a_result, _ = run_scenario(meta)
        b_records, b_result, _ = run_scenario(meta)
        self.assertEqual(a_records, b_records)
        self.assertEqual(summarise(a_records, a_result, meta),
                         summarise(b_records, b_result, meta))


if __name__ == "__main__":
    unittest.main()
