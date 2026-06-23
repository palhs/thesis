"""Smoke test for the T62 Chapter-5 synthesis figure (render layer)."""
from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from output import synthesis_plots as sp


class TestSynthesisPlots(unittest.TestCase):
    def test_render_all(self):
        with tempfile.TemporaryDirectory() as d:
            plot_dir = Path(d) / "plots"
            names = sp.render_all(str(plot_dir))
            self.assertTrue(names)
            for name in names:
                self.assertTrue((plot_dir / f"{name}.pdf").exists(), name)
                self.assertTrue((plot_dir / f"{name}.png").exists(), name)

    def test_no_family_dominates(self):
        # The figure's whole point: no family's rank vector dominates another's
        # (>= on every axis). If a future edit makes one enclose another, the
        # no-dominance verdict the figure renders would be false.
        protos = list(sp.RANK)
        for a in protos:
            for b in protos:
                if a == b:
                    continue
                va, vb = sp.RANK[a], sp.RANK[b]
                self.assertFalse(all(x >= y for x, y in zip(va, vb)),
                                 f"{a} dominates {b}")


if __name__ == "__main__":
    unittest.main()
