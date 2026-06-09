"""Unit tests for src/output/aggregate.py (T44 aggregated CSV).

Checks the wide aggregated layout: one row per run_id, CI-bound columns
present for every metric, total row ordering, byte-stable regeneration,
and (when the committed dataset is present) that the realised seed count
is the expected 20.
"""

import csv
import os
import tempfile
import unittest

from output import aggregate, analysis


def _row(protocol, run_id, n, seed, **metrics):
    base = {"protocol": protocol, "run_id": run_id, "n": str(n), "seed": str(seed)}
    for m in analysis.METRICS:
        base[m] = ""
    base.update({k: str(v) for k, v in metrics.items()})
    return base


def _write_src(rows):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    cols = ["protocol", "run_id", "n", "seed", *analysis.METRICS]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path


class TestHeader(unittest.TestCase):
    def test_header_has_ci_columns_for_every_metric(self):
        h = aggregate._header()
        for m in analysis.METRICS:
            for suf in ("mean", "ci_lo", "ci_hi", "cv"):
                self.assertIn(f"{m}_{suf}", h)
        self.assertEqual(h[:4], ["run_id", "protocol", "n", "n_runs"])


class TestBuildRows(unittest.TestCase):
    def test_one_row_per_run_id(self):
        rows = ([_row("pbft", "pbft-n7", 7, s, goodput=10.0) for s in range(5)]
                + [_row("pbft", "pbft-n10", 10, s, goodput=20.0) for s in range(5)])
        src = _write_src(rows)
        try:
            built = aggregate.build_rows(src)
        finally:
            os.remove(src)
        self.assertEqual(len(built), 2)
        self.assertEqual([r["run_id"] for r in built], ["pbft-n7", "pbft-n10"])
        self.assertEqual(built[0]["n_runs"], 5)

    def test_ci_brackets_mean(self):
        rows = [_row("pbft", "pbft-n7", 7, s, goodput=v)
                for s, v in enumerate([8, 9, 10, 11, 12])]
        src = _write_src(rows)
        try:
            r = aggregate.build_rows(src)[0]
        finally:
            os.remove(src)
        self.assertAlmostEqual(r["goodput_mean"], 10.0)
        self.assertLess(r["goodput_ci_lo"], r["goodput_mean"])
        self.assertGreater(r["goodput_ci_hi"], r["goodput_mean"])

    def test_ordered_by_protocol_then_n(self):
        rows = []
        for proto, n in [("snowman", 7), ("pbft", 25), ("pbft", 4)]:
            rows += [_row(proto, f"{proto}-n{n}", n, s, goodput=1.0)
                     for s in range(2)]
        src = _write_src(rows)
        try:
            built = aggregate.build_rows(src)
        finally:
            os.remove(src)
        self.assertEqual([(r["protocol"], r["n"]) for r in built],
                         [("pbft", 4), ("pbft", 25), ("snowman", 7)])


class TestRealDataset(unittest.TestCase):
    def setUp(self):
        if not os.path.exists(aggregate.SRC):
            self.skipTest("baseline.csv not present")

    def test_15_scenarios_at_20_seeds(self):
        built = aggregate.build_rows()
        self.assertEqual(len(built), 15)
        for r in built:
            self.assertEqual(r["n_runs"], 20)

    def test_write_is_byte_identical_on_rerun(self):
        with tempfile.TemporaryDirectory() as d:
            a = os.path.join(d, "a.csv")
            b = os.path.join(d, "b.csv")
            aggregate.write(dst=a)
            aggregate.write(dst=b)
            self.assertEqual(open(a, "rb").read(), open(b, "rb").read())

    def test_committed_artifact_matches_rebuild(self):
        if not os.path.exists(aggregate.DST):
            self.skipTest("aggregated.csv not yet committed")
        with tempfile.TemporaryDirectory() as d:
            fresh = os.path.join(d, "fresh.csv")
            aggregate.write(dst=fresh)
            self.assertEqual(open(fresh).read(), open(aggregate.DST).read())


if __name__ == "__main__":
    unittest.main()
