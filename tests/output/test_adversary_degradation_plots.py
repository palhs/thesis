"""Smoke test for the T54 adversarial degradation figures (render layer)."""
from __future__ import annotations
import csv, tempfile, unittest
from pathlib import Path
from output import adversary_degradation_plots as adp


def _equiv_csv(path):
    cols = ["protocol", "n", "seed", "byzantine_fraction", "success_rate",
            "run_horizon_s", "view_change_count", "max_slashable_stake_fraction",
            "safety_violation", "conflicting_instances", "K", "alpha_p",
            "alpha_c", "beta"]
    rows = []
    for proto in ("pbft", "casper-ffg", "snowman"):
        grid = (0.0, 0.10, 0.20, 0.33) if proto == "snowman" else (0.0, 0.10, 0.20, 0.33, 0.40, 0.50)
        for n in (10, 25):
            for phi in grid:
                for seed in range(3):
                    broke = proto == "pbft" and phi >= 0.40
                    rows.append({"protocol": proto, "n": n, "seed": seed,
                                 "byzantine_fraction": phi, "success_rate": 1.0,
                                 "run_horizon_s": 230.0,
                                 "view_change_count": (n if 0 < phi <= 0.33 else 0),
                                 "max_slashable_stake_fraction": phi,
                                 "safety_violation": (1 if broke else 0),
                                 "conflicting_instances": (229 if broke else 0),
                                 "K": 9, "alpha_p": 5, "alpha_c": 8, "beta": 15})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


def _simple_csv(path):
    # carries the delay/offline magnitude columns the §4.4 overlays read
    # (Snowman gets a finality blow-up + a starved-throughput cell to exercise
    # the annotation paths); the real CSVs always carry these.
    cols = ["protocol", "n", "seed", "byzantine_fraction", "success_rate",
            "delay_mult", "finality_delay_ratio", "throughput_ratio"]
    rows = []
    for proto in ("pbft", "casper-ffg", "snowman"):
        for n in (10, 25):
            for phi in (0.0, 0.10, 0.20, 0.30):
                for seed in range(3):
                    blow = proto == "snowman" and phi >= 0.20
                    rows.append({"protocol": proto, "n": n, "seed": seed,
                                 "byzantine_fraction": phi, "success_rate": 1.0,
                                 "delay_mult": 10.0,
                                 "finality_delay_ratio": (50.0 if blow else 1.0),
                                 "throughput_ratio": (0.005 if blow else 1.0)})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)


class TestPlots(unittest.TestCase):
    def test_render_all(self):
        with tempfile.TemporaryDirectory() as d:
            adv = Path(d) / "adv"; adv.mkdir()
            _equiv_csv(adv / "equivocating_nodes.csv")
            _simple_csv(adv / "delayed_voters.csv")
            _simple_csv(adv / "offline_validators.csv")
            plot_dir = Path(d) / "plots"
            names = adp.render_all(str(adv), str(plot_dir))
            self.assertTrue(names)
            for name in names:
                self.assertTrue((plot_dir / f"{name}.pdf").exists(), name)
                self.assertTrue((plot_dir / f"{name}.png").exists(), name)


if __name__ == "__main__":
    unittest.main()
