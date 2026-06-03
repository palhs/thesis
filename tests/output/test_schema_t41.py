"""T41 — schema extension: workload axis columns + goodput/bytes_per_acu.

Asserts the new columns appear in COLUMN_ORDER and that ScenarioMeta
carries the five new workload/interval fields with defaults.
"""
from __future__ import annotations

import unittest

from output.schema import COLUMN_ORDER, ScenarioMeta


class TestSchemaT41(unittest.TestCase):
    def test_new_columns_present(self):
        for c in ("workload_arrival_process", "workload_tx_bytes",
                  "workload_conflict_rate", "workload_offered_rate",
                  "goodput", "bytes_per_acu"):
            self.assertIn(c, COLUMN_ORDER)

    def test_meta_carries_workload_and_interval(self):
        m = ScenarioMeta(run_id="x", protocol="pbft", n=4, variant=None,
                         seed=0, t_max=20.0)
        # all new fields have defaults; explicit set works too
        self.assertEqual(m.arrival_process, "poisson")
        self.assertEqual(m.tx_bytes, 512)
        self.assertEqual(m.conflict_rate, 0.0)
        self.assertEqual(m.offered_rate, 100.0)
        self.assertEqual(m.interval, 1.0)

    def test_meta_explicit_set(self):
        m = ScenarioMeta(run_id="x", protocol="pbft", n=4, variant=None,
                         seed=0, t_max=20.0, arrival_process="deterministic",
                         tx_bytes=1024, conflict_rate=0.25,
                         offered_rate=250.0, interval=0.5)
        self.assertEqual(m.arrival_process, "deterministic")
        self.assertEqual(m.tx_bytes, 1024)
        self.assertEqual(m.conflict_rate, 0.25)
        self.assertEqual(m.offered_rate, 250.0)
        self.assertEqual(m.interval, 0.5)


if __name__ == "__main__":
    unittest.main()
