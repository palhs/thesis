import unittest

from adversary.equivocate_sweep import (_run_cell, _build_cells, _ALL_COLUMNS,
                                        _HEADLINE_COLUMNS)
from adversary import equivocate_config as ec


class TestEquivocateSweep(unittest.TestCase):
    def test_smoke_row_shape(self):
        """A single control cell projects to a row carrying every column,
        including the three safety headline columns."""
        row = _run_cell(("pbft", 4, 0.0, 0), {"commit_hash": "test"})
        for col in _ALL_COLUMNS:
            self.assertIn(col, row, f"missing column {col}")
        for col in _HEADLINE_COLUMNS:
            self.assertIn(col, row)
        self.assertEqual(_HEADLINE_COLUMNS,
                         ("safety_violation", "conflicting_instances",
                          "max_slashable_stake_fraction"))

    def test_control_is_safe(self):
        """f=0 is the honest control: strategy 'none', no safety violation."""
        row = _run_cell(("pbft", 4, 0.0, 0), {"commit_hash": "test"})
        self.assertEqual(row["adversary_strategy"], "none")
        self.assertEqual(row["safety_violation"], False)
        self.assertEqual(row["conflicting_instances"], 0)

    def test_cells_cover_grid(self):
        """One seed: per protocol len(F_VALUES[p]) * len(N_VALUES) cells, all
        4-tuples."""
        cells = _build_cells((0,))
        expected = sum(len(ec.F_VALUES[p]) * len(ec.N_VALUES)
                       for p in ("pbft", "casper-ffg", "snowman"))
        self.assertEqual(len(cells), expected)
        for c in cells:
            self.assertEqual(len(c), 4)

    def test_ffg_control_strategy_none(self):
        """FFG control row also reads strategy 'none' and is safe."""
        row = _run_cell(("casper-ffg", 4, 0.0, 0), {"commit_hash": "test"})
        self.assertEqual(row["adversary_strategy"], "none")
        self.assertEqual(row["safety_violation"], False)

    def test_attack_row_strategy_label(self):
        """An f>0 PBFT cell carries the equivocate-vote strategy tag."""
        row = _run_cell(("pbft", 10, 0.20, 0), {"commit_hash": "test"})
        self.assertEqual(row["adversary_strategy"], "equivocate-vote")
        self.assertEqual(row["byzantine_fraction"], 0.20)


if __name__ == "__main__":
    unittest.main()
