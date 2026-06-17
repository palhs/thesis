"""Smoke test for the Family C dose-response plots (T51)."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from output import adversary_plots as ap


def _tiny_csv(path: Path) -> None:
    cols = ["protocol", "n", "seed", "byzantine_fraction", "delay_mult",
            "finality_delay_ratio"]
    rows = []
    for proto in ("pbft", "casper-ffg", "snowman"):
        for n in (10, 25):
            for f in (0.0, 0.10, 0.20, 0.30):
                for m in ((0.0,) if f == 0.0 else (2.0, 4.0, 6.0, 8.0, 10.0)):
                    ratio = 1.0 if f == 0.0 else 1.0 + f * m
                    rows.append({"protocol": proto, "n": n, "seed": 0,
                                 "byzantine_fraction": f, "delay_mult": m,
                                 "finality_delay_ratio": ratio})
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


class TestPlots(unittest.TestCase):
    def test_render_all_figures(self):
        with tempfile.TemporaryDirectory() as d:
            csv_path = Path(d) / "delayed_voters.csv"
            plot_dir = Path(d) / "plots"
            _tiny_csv(csv_path)
            names = ap.render_all(str(csv_path), str(plot_dir))
            self.assertTrue(names)
            for name in names:
                self.assertTrue((plot_dir / f"{name}.pdf").exists(), name)
                self.assertTrue((plot_dir / f"{name}.png").exists(), name)


if __name__ == "__main__":
    unittest.main()
