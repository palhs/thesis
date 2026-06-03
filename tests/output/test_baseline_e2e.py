"""End-to-end determinism + structure test for the unified output
orchestrator.

Routine `make test` must stay fast, so the determinism / routing / header
/ sorting checks run against a SMALL monkeypatched scenario subset (a few
sims), not the full ~320-run T41 sweep. The real sweep SIZES are guarded
separately by `TestSweepCounts`, which asserts the `SCENARIOS` tuple
lengths arithmetically WITHOUT executing any simulation. The full 300-row
/ 20-row dataset is generated and verified once by the Phase 7 dataset run
(`PYTHONPATH=src python3 -m output.baseline`), not on every test run.
"""
from __future__ import annotations

import csv as _csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import output.baseline as base
import pbft.baseline as pbft_baseline
import pos.baseline as pos_baseline
import snowman.baseline as snowman_baseline
from output.schema import COLUMN_ORDER, ScenarioMeta


def _meta(run_id, protocol, n, seed, *, variant=None, slots_per_epoch=None):
    """A workload-axis ScenarioMeta matching the baselines' generator
    params (poisson/100/512/0.0, interval 1.0) so the reducers regenerate
    the identical stream the proposers consumed."""
    return ScenarioMeta(
        run_id=run_id, protocol=protocol, n=n, variant=variant, seed=seed,
        t_max=20.0, arrival_process="poisson", tx_bytes=512,
        conflict_rate=0.0, offered_rate=100.0, interval=1.0,
        slots_per_epoch=slots_per_epoch,
    )


# Reduced subsets: one PBFT + one Casper FFG row in the main file, plus a
# Snowman n=7 main row and two Snowman n=4 rows routed to the sanity file.
# Main file = 3 rows; sanity file = 2 rows.
_RED_PBFT = (_meta("pbft-n4", "pbft", 4, 0),)
_RED_POS = (_meta("casper-ffg-n4-uniform", "casper-ffg", 4, 0,
                  variant="uniform", slots_per_epoch=2),)
_RED_SNOWMAN = (
    _meta("snowman-n4", "snowman", 4, 0),
    _meta("snowman-n4", "snowman", 4, 1),
    _meta("snowman-n7", "snowman", 7, 0),
)


class TestBaselineE2E(unittest.TestCase):
    """Structure + determinism on the reduced subset."""

    def _run_once(self, out_dir: Path) -> tuple[bytes, bytes]:
        main_csv = out_dir / "baseline.csv"
        sanity_csv = out_dir / "snowman_n4_sanity.csv"
        with patch.object(base, "_OUT", main_csv), \
             patch.object(base, "_SANE", sanity_csv), \
             patch.object(pbft_baseline, "SCENARIOS", _RED_PBFT), \
             patch.object(pos_baseline, "SCENARIOS", _RED_POS), \
             patch.object(snowman_baseline, "SCENARIOS", _RED_SNOWMAN), \
             patch("output.csv._resolve_commit_hash", return_value="abc12345"):
            base.main()
        return main_csv.read_bytes(), sanity_csv.read_bytes()

    def test_byte_identical(self):
        with TemporaryDirectory() as td1, TemporaryDirectory() as td2:
            main1, sane1 = self._run_once(Path(td1))
            main2, sane2 = self._run_once(Path(td2))
        self.assertEqual(main1, main2)
        self.assertEqual(sane1, sane2)

    def test_reduced_row_counts(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                rows = list(_csv.DictReader(fh))
            with (Path(td) / "snowman_n4_sanity.csv").open() as fh:
                sane_rows = list(_csv.DictReader(fh))
        # 1 PBFT + 1 Casper FFG + 1 Snowman n=7 (the two n=4 rows route out).
        self.assertEqual(len(rows), 3)
        # Both Snowman n=4 seeds land in the sanity sibling.
        self.assertEqual(len(sane_rows), 2)

    def test_no_snowman_n4_in_main_file(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                rows = list(_csv.DictReader(fh))
        snowman_ns = sorted({int(r["n"]) for r in rows
                             if r["protocol"] == "snowman"})
        self.assertEqual(snowman_ns, [7])

    def test_sanity_rows_all_degenerate_n4(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "snowman_n4_sanity.csv").open() as fh:
                reader = _csv.DictReader(fh)
                self.assertIn("snowman_degenerate_n4", reader.fieldnames or [])
                rows = list(reader)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["snowman_degenerate_n4"], "True")
            self.assertEqual(row["protocol"], "snowman")
            self.assertEqual(row["n"], "4")
        self.assertEqual(sorted(int(r["seed"]) for r in rows), [0, 1])

    def test_sanity_header_is_column_order_plus_flag(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "snowman_n4_sanity.csv").open() as fh:
                reader = _csv.DictReader(fh)
                self.assertEqual(
                    reader.fieldnames,
                    list(COLUMN_ORDER) + ["snowman_degenerate_n4"],
                )

    def test_sanity_rows_sorted(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "snowman_n4_sanity.csv").open() as fh:
                rows = list(_csv.DictReader(fh))
        keys = [(r["protocol"], int(r["n"]), r["run_id"], int(r["seed"]))
                for r in rows]
        self.assertEqual(keys, sorted(keys))

    def test_header_is_column_order(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                reader = _csv.DictReader(fh)
                self.assertEqual(reader.fieldnames, list(COLUMN_ORDER))

    def test_commit_hash_consistent_across_files(self):
        """Regression guard for the determinism bug fixed in
        `task 40: thread commit_hash …`. `main()` resolves the hash once
        at the top and threads it through both files. Asserts only
        internal consistency, not the resolved value, so it is
        tree-state-tolerant. Does NOT monkeypatch `_resolve_commit_hash`.
        """
        with TemporaryDirectory() as td:
            main_csv = Path(td) / "baseline.csv"
            sanity_csv = Path(td) / "snowman_n4_sanity.csv"
            with patch.object(base, "_OUT", main_csv), \
                 patch.object(base, "_SANE", sanity_csv), \
                 patch.object(pbft_baseline, "SCENARIOS", _RED_PBFT), \
                 patch.object(pos_baseline, "SCENARIOS", _RED_POS), \
                 patch.object(snowman_baseline, "SCENARIOS", _RED_SNOWMAN):
                base.main()
            with main_csv.open() as fh:
                main_hashes = {r["commit_hash"] for r in _csv.DictReader(fh)}
            with sanity_csv.open() as fh:
                sanity_hashes = {r["commit_hash"]
                                 for r in _csv.DictReader(fh)}
        self.assertEqual(len(main_hashes), 1,
                         f"baseline.csv carries multiple commit_hash "
                         f"values: {main_hashes!r}")
        self.assertEqual(sanity_hashes, main_hashes,
                         f"sanity commit_hash {sanity_hashes!r} differs "
                         f"from baseline.csv {main_hashes!r}")


class TestSweepCounts(unittest.TestCase):
    """Guards the real T41 sweep SIZES arithmetically — no simulation runs.
    The full dataset (300 main + 20 sanity) is verified once by the Phase 7
    dataset run, not on every `make test`."""

    def test_pbft_scenario_count(self):
        # n in {4,7,10,16,25} x seed in range(20) = 100.
        self.assertEqual(len(pbft_baseline.SCENARIOS), 100)

    def test_pos_scenario_count(self):
        # 5 uniform n x 20 seeds + n=4 nonuniform x 20 seeds = 120.
        self.assertEqual(len(pos_baseline.SCENARIOS), 120)

    def test_snowman_scenario_count(self):
        # n in {4,7,10,16,25} x seed in range(20) = 100.
        self.assertEqual(len(snowman_baseline.SCENARIOS), 100)

    def test_full_main_and_sanity_counts_by_enumeration(self):
        all_metas = (list(pbft_baseline.SCENARIOS)
                     + list(pos_baseline.SCENARIOS)
                     + list(snowman_baseline.SCENARIOS))
        snowman_n4 = [m for m in all_metas
                      if m.protocol == "snowman" and m.n == 4]
        main = [m for m in all_metas
                if not (m.protocol == "snowman" and m.n == 4)]
        # 300 main rows (Snowman n=4 routed to sanity), 20 sanity rows.
        self.assertEqual(len(main), 300)
        self.assertEqual(len(snowman_n4), 20)


if __name__ == "__main__":
    unittest.main()
