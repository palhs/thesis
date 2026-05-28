"""End-to-end determinism test for the unified output orchestrator.
Drives output.baseline.main into a tmp directory twice; asserts the
two results/baseline.csv files are byte-identical.
"""
from __future__ import annotations

import csv as _csv
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import output.baseline as base
from output.schema import COLUMN_ORDER


class TestBaselineE2E(unittest.TestCase):
    def _run_once(self, out_dir: Path) -> tuple[bytes, bytes]:
        main_csv   = out_dir / "baseline.csv"
        sanity_csv = out_dir / "snowman_n4_sanity.csv"
        with patch.object(base, "_OUT",  main_csv), \
             patch.object(base, "_SANE", sanity_csv), \
             patch("output.csv._resolve_commit_hash",
                   return_value="abc12345"):
            base.main()
        return main_csv.read_bytes(), sanity_csv.read_bytes()

    def test_byte_identical(self):
        with TemporaryDirectory() as td1, TemporaryDirectory() as td2:
            main1, sane1 = self._run_once(Path(td1))
            main2, sane2 = self._run_once(Path(td2))
        self.assertEqual(main1, main2)
        self.assertEqual(sane1, sane2)

    def test_row_count(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                rows = list(_csv.DictReader(fh))
            with (Path(td) / "snowman_n4_sanity.csv").open() as fh:
                sane_rows = list(_csv.DictReader(fh))
        # 3 PBFT + 4 POS + 2 Snowman (n=4 skipped) = 9 rows.
        self.assertEqual(len(rows), 9)
        self.assertEqual(len(sane_rows), 1)

    def test_no_snowman_n4_in_main_file(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                rows = list(_csv.DictReader(fh))
        snowman_ns = sorted(int(r["n"]) for r in rows
                            if r["protocol"] == "snowman")
        self.assertEqual(snowman_ns, [7, 10])

    def test_sanity_row_has_degenerate_flag(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "snowman_n4_sanity.csv").open() as fh:
                reader = _csv.DictReader(fh)
                self.assertIn("snowman_degenerate_n4",
                              reader.fieldnames or [])
                row = next(iter(reader))
        self.assertEqual(row["snowman_degenerate_n4"], "True")
        self.assertEqual(row["protocol"], "snowman")
        self.assertEqual(row["n"], "4")

    def test_header_is_column_order(self):
        with TemporaryDirectory() as td:
            self._run_once(Path(td))
            with (Path(td) / "baseline.csv").open() as fh:
                reader = _csv.DictReader(fh)
                self.assertEqual(reader.fieldnames, list(COLUMN_ORDER))


if __name__ == "__main__":
    unittest.main()
