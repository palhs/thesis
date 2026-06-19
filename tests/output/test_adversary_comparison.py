"""Unit + regression tests for src/output/adversary_comparison.py (T55).

Data layer only (no render layer in T55 — tables only). Three tiers, mirroring
test_adversary_analysis.py / test_delay_analysis.py:

  TIER 1 — synthetic cases pin the NEW logic (magnitude reducers, ranking
           sort/tie, comparison-row structure) with controlled in-memory rows.
  TIER 2 — TestRealDataset locks the verified numbers against the committed
           Family-C CSVs and self-skips if they are absent, plus a consistency
           check that the f_max brackets equal the committed T54
           degradation_ranking.csv (the "consumes" contract).
  TIER 3 — byte-stability gate: write each CSV twice, assert identical bytes.
"""
import csv
import math
import os
import tempfile
import unittest

from output import adversary_comparison as ac
from output import adversary_analysis as aa


# --------------------------------------------------------------------------- #
# Synthetic row builders
# --------------------------------------------------------------------------- #

def _delay_row(protocol, n, seed, phi, dm, fdr, success=1.0):
    return {"family": "delay", "protocol": protocol, "n": n, "seed": seed,
            "byzantine_fraction": phi, "delay_mult": dm, "success_rate": success,
            "finality_delay_ratio": fdr}


def _offline_row(protocol, n, seed, phi, success, tr):
    return {"family": "offline", "protocol": protocol, "n": n, "seed": seed,
            "byzantine_fraction": phi, "success_rate": success,
            "throughput_ratio": tr}


def _equiv_row(protocol, n, seed, phi, *, success=1.0, sv=0,
               conflicting=0, slashable=0.0):
    return {"family": "equivocate", "protocol": protocol, "n": n, "seed": seed,
            "byzantine_fraction": phi, "success_rate": success,
            "safety_violation": sv, "conflicting_instances": conflicting,
            "max_slashable_stake_fraction": slashable, "view_change_count": 0,
            "run_horizon_s": 230.0, "K": 9, "alpha_p": 5, "alpha_c": 8,
            "beta": 15}


# --------------------------------------------------------------------------- #
# TIER 1 — magnitude reducers
# --------------------------------------------------------------------------- #

class TestDelayFinalityBlowup(unittest.TestCase):
    def test_max_of_cell_means_nan_skipped_and_baseline_excluded(self):
        rows = [
            _delay_row("snowman", 10, 0, 0.0, 0.0, 1.0),     # baseline phi=0 excluded
            _delay_row("snowman", 10, 0, 0.2, 2, 10.0),      # cell A
            _delay_row("snowman", 10, 1, 0.2, 2, 20.0),      # cell A mean = 15
            _delay_row("snowman", 10, 0, 0.2, 10, 30.0),     # cell B
            _delay_row("snowman", 10, 1, 0.2, 10, float("nan")),  # NaN skipped -> mean 30
        ]
        self.assertAlmostEqual(ac.delay_finality_blowup(rows, "snowman", 10), 30.0)

    def test_all_nan_is_nan(self):
        rows = [_delay_row("casper-ffg", 10, 0, 0.2, 2, float("nan"))]
        self.assertTrue(math.isnan(ac.delay_finality_blowup(rows, "casper-ffg", 10)))


class TestDelayMinSuccess(unittest.TestCase):
    def test_worst_cell_pooled_over_magnitude(self):
        # phi=0.1: 1 fail of 2 -> 0.5; phi=0.2: 2 of 2 -> 1.0; worst = 0.5.
        rows = [_delay_row("casper-ffg", 10, 0, 0.1, 2, float("nan"), success=0.0),
                _delay_row("casper-ffg", 10, 1, 0.1, 4, 1.0, success=1.0),
                _delay_row("casper-ffg", 10, 0, 0.2, 2, 1.0, success=1.0),
                _delay_row("casper-ffg", 10, 1, 0.2, 4, 1.0, success=1.0)]
        mn, lo, hi = ac.delay_min_success(rows, "casper-ffg", 10)
        self.assertAlmostEqual(mn, 0.5)
        self.assertLess(lo, mn)
        self.assertGreater(hi, mn)


class TestOfflineReducers(unittest.TestCase):
    def _rows(self):
        return [
            _offline_row("snowman", 10, 0, 0.0, 1.0, 1.0),    # baseline excluded
            _offline_row("snowman", 10, 0, 0.10, 1.0, 0.8),   # surviving
            _offline_row("snowman", 10, 0, 0.20, 0.0, float("nan")),  # dead
            _offline_row("snowman", 10, 0, 0.33, 1.0, 0.5),   # surviving (deepest)
        ]

    def test_survival_phi_is_deepest_alive(self):
        self.assertEqual(ac.offline_survival_phi(self._rows(), "snowman", 10), 0.33)

    def test_worst_surviving_throughput_skips_dead_cell(self):
        # 0.20 is dead (success 0) -> excluded; worst of {0.8, 0.5} = 0.5.
        self.assertAlmostEqual(
            ac.offline_worst_surviving_throughput(self._rows(), "snowman", 10), 0.5)


class TestEquivMagnitudes(unittest.TestCase):
    def test_max_conflicting_and_slashable(self):
        rows = [_equiv_row("pbft", 10, 0, 0.33, conflicting=0),
                _equiv_row("pbft", 10, 0, 0.40, conflicting=229),
                _equiv_row("casper-ffg", 10, 0, 0.40, slashable=0.40),
                _equiv_row("casper-ffg", 10, 0, 0.50, slashable=0.50)]
        self.assertEqual(ac.equiv_max_conflicting(rows, "pbft", 10), 229.0)
        self.assertEqual(ac.equiv_max_conflicting(rows, "casper-ffg", 10), 0.0)
        self.assertAlmostEqual(ac.equiv_max_slashable(rows, "casper-ffg", 10), 0.50)


# --------------------------------------------------------------------------- #
# TIER 1 — ranking sort / tie / deferral
# --------------------------------------------------------------------------- #

class TestRankingSynthetic(unittest.TestCase):
    def _equiv_dataset(self):
        """Reproduce the real equivocate posture in miniature: Snowman resists
        (no break), FFG accountable break at 0.40, PBFT fork at 0.40."""
        rows = []
        grid = (0.0, 0.10, 0.20, 0.33, 0.40, 0.50)
        for phi in grid:
            # snowman: never violates (grid stops at .33 in reality; full grid ok)
            if phi <= 0.33:
                rows.append(_equiv_row("snowman", 10, 0, phi, sv=0))
            # casper-ffg: slashable = phi-ish, crosses 1/3 at 0.40, never forks
            rows.append(_equiv_row("casper-ffg", 10, 0, phi, slashable=phi))
            # pbft: fork (sv=1, conflicting=229) only at phi >= 0.40
            sv = 1 if phi >= 0.40 else 0
            rows.append(_equiv_row("pbft", 10, 0, phi, sv=sv,
                                   conflicting=(229 if sv else 0)))
        return rows

    def test_equivocate_order_snowman_ffg_pbft_all_tied_on_hold(self):
        rank = ac.ranking_for(self._equiv_dataset(), "equivocate", 10)
        measured = [r for r in rank if r.rank != ""]
        self.assertEqual([r.protocol for r in measured],
                         ["snowman", "casper-ffg", "pbft"])
        self.assertEqual([r.rank for r in measured], [1, 2, 3])
        # all three hold to 0.33 -> threshold tie flagged on every measured row
        self.assertTrue(all(r.tie for r in measured))
        self.assertEqual([r.f_max_hold for r in measured], [0.33, 0.33, 0.33])
        # Snowman right-censored; FFG/PBFT break at 0.40
        self.assertIsNone(measured[0].f_max_break)
        self.assertEqual(measured[1].f_max_break, 0.40)
        self.assertEqual(measured[2].f_max_break, 0.40)
        # safety_broken: PBFT + FFG, not Snowman
        self.assertFalse(measured[0].safety_broken)
        self.assertTrue(measured[1].safety_broken)
        self.assertTrue(measured[2].safety_broken)
        # count vs stake routing
        self.assertEqual(measured[1].accounting, "stake")    # casper-ffg
        self.assertEqual(measured[2].accounting, "count")    # pbft

    def test_nwt_deferral_row_present_and_explicit(self):
        rank = ac.ranking_for(self._equiv_dataset(), "equivocate", 10)
        nwt = [r for r in rank if r.protocol == "narwhal-tusk"]
        self.assertEqual(len(nwt), 1)
        self.assertEqual(nwt[0].rank, "")            # not a number
        self.assertTrue(math.isnan(nwt[0].f_max_hold))
        self.assertIn("T38.1", nwt[0].note)

    def test_delay_tiebreak_lower_blowup_ranks_higher(self):
        # both hold to 0.3 (no break); PBFT blowup 1.0 beats Snowman 50.0.
        rows = []
        for phi in (0.0, 0.10, 0.20, 0.30):
            for proto, fdr in (("pbft", 1.0), ("snowman", 50.0)):
                rows.append(_delay_row(proto, 10, 0, phi, 2, fdr))
        rank = [r for r in ac.ranking_for(rows, "delay", 10) if r.rank != ""]
        self.assertEqual([r.protocol for r in rank], ["pbft", "snowman"])
        self.assertTrue(all(r.tie for r in rank))    # tied on hold=0.3
        self.assertEqual([r.ranked_on for r in rank], ["liveness_f_max_hold"] * 2)
        self.assertAlmostEqual(rank[0].signature_value, 1.0)
        self.assertAlmostEqual(rank[1].signature_value, 50.0)

    def test_offline_survival_key_ranks_graceful_above_cliff(self):
        # A protocol that degrades gracefully but survives deep (ffg-like) must
        # outrank one that holds full liveness then hard-cliffs early (snowman-
        # like). Ranking on the survival boundary, not the full-liveness onset.
        # success_rate is a per-run 0/1 flag (liveness_rate means it), so a
        # degraded cell needs a 0/1 MIX across seeds (mean in (0,1)).
        def cell(proto, phi, succ_flags, tr):
            # succ_flags: list of 0/1 over seeds; tr: throughput on each row.
            return [_offline_row(proto, 10, s, phi, float(f),
                                 tr if f else float("nan"))
                    for s, f in enumerate(succ_flags)]
        rows = []
        # pbft: full liveness to 0.33 then dead at 0.40 -> survival 0.33.
        for phi in (0.0, 0.10, 0.20, 0.33):
            rows += cell("pbft", phi, [1, 1], 1.0)
        rows += cell("pbft", 0.40, [0, 0], float("nan"))
        # casper-ffg: graceful (mean 0.5) through 0.33 then dead -> survival 0.33,
        # but full-liveness onset breaks at 0.10 (f_max_hold = 0.0).
        rows += cell("casper-ffg", 0.0, [1, 1], 1.0)
        for phi in (0.10, 0.20, 0.33):
            rows += cell("casper-ffg", phi, [1, 0], 0.5)
        rows += cell("casper-ffg", 0.40, [0, 0], float("nan"))
        # snowman: full to 0.10 then hard cliff at 0.20 -> survival 0.10.
        rows += cell("snowman", 0.0, [1, 1], 1.0)
        rows += cell("snowman", 0.10, [1, 1], 0.9)
        rows += cell("snowman", 0.20, [0, 0], float("nan"))
        rank = {r.protocol: r for r in ac.ranking_for(rows, "offline", 10)
                if r.rank != ""}
        self.assertEqual(rank["pbft"].rank, 1)
        self.assertEqual(rank["casper-ffg"].rank, 2)   # survives to 0.33 like pbft
        self.assertEqual(rank["snowman"].rank, 3)      # cliffs at 0.20
        self.assertEqual(rank["casper-ffg"].ranked_on, "liveness_survival_phi")
        self.assertEqual(rank["casper-ffg"].rank_value, 0.33)   # survival, not onset
        self.assertEqual(rank["casper-ffg"].f_max_hold, 0.0)    # onset carried separately
        self.assertTrue(rank["pbft"].tie and rank["casper-ffg"].tie)  # share survival 0.33
        self.assertFalse(rank["snowman"].tie)


# --------------------------------------------------------------------------- #
# TIER 1 — comparison table structure
# --------------------------------------------------------------------------- #

class TestComparisonStructure(unittest.TestCase):
    def test_metric_sets_per_adversary_and_nwt_rows(self):
        rows = []
        for phi in (0.0, 0.20):
            rows.append(_delay_row("pbft", 10, 0, phi, 2, 1.0))
            rows.append(_offline_row("pbft", 10, 0, phi, 1.0, 1.0))
            rows.append(_equiv_row("pbft", 10, 0, phi))
        cmp = ac.build_comparison(rows)
        metrics = {(c.adversary, c.metric) for c in cmp if c.protocol == "pbft"}
        self.assertIn(("delay-emission", "worst_finality_delay_ratio"), metrics)
        self.assertIn(("delay-emission", "min_success_rate"), metrics)
        self.assertIn(("withhold-participation", "liveness_survival_phi"), metrics)
        self.assertIn(("withhold-participation", "worst_surviving_throughput_ratio"),
                      metrics)
        self.assertIn(("equivocate-vote", "safety_f_max_hold"), metrics)
        self.assertIn(("equivocate-vote", "conflicting_instances_max"), metrics)
        # one explicit NWT deferral row per adversary
        nwt = [c for c in cmp if c.protocol == "narwhal-tusk"]
        self.assertEqual({c.adversary for c in nwt},
                         set(ac.ADVERSARY_LABEL.values()))
        self.assertTrue(all(c.value is None for c in nwt))


# --------------------------------------------------------------------------- #
# TIER 2 — real-dataset locked numbers
# --------------------------------------------------------------------------- #

class TestRealDataset(unittest.TestCase):
    def setUp(self):
        self.rows = ac.load_adversary_rows()
        if not any(r["family"] == "equivocate" for r in self.rows):
            self.skipTest("adversary CSVs not present")

    def _rank(self, adversary, n):
        return {r.protocol: r for r in ac.ranking_for(self.rows, adversary, n)}

    def test_delay_blowup_locked(self):
        self.assertAlmostEqual(
            ac.delay_finality_blowup(self.rows, "snowman", 10), 61.946564, places=4)
        self.assertAlmostEqual(
            ac.delay_finality_blowup(self.rows, "snowman", 25), 49.1057246, places=4)
        self.assertAlmostEqual(
            ac.delay_finality_blowup(self.rows, "pbft", 10), 1.0)

    def test_delay_ranking_pbft_then_snowman_tied_ffg_last(self):
        r = ac.ranking_for(self.rows, "delay", 10)
        measured = [x for x in r if x.rank != ""]
        self.assertEqual([x.protocol for x in measured],
                         ["pbft", "snowman", "casper-ffg"])
        self.assertTrue(measured[0].tie and measured[1].tie)   # share hold=0.3
        self.assertFalse(measured[2].tie)

    def test_offline_starvation_and_survival(self):
        self.assertAlmostEqual(
            ac.offline_worst_surviving_throughput(self.rows, "snowman", 25),
            0.00397315, places=5)
        self.assertEqual(ac.offline_survival_phi(self.rows, "pbft", 10), 0.33)
        self.assertEqual(ac.offline_survival_phi(self.rows, "snowman", 10), 0.10)

    def test_offline_ranking_survival_keyed_pbft_ffg_snowman(self):
        # Keyed on survival depth: PBFT and FFG both reach the 1/3 quorum cliff
        # (survive to 0.33), Snowman cliffs at 0.20 (n=10) -> ranks last.
        by = self._rank("offline", 10)
        self.assertEqual(by["pbft"].rank, 1)
        self.assertEqual(by["casper-ffg"].rank, 2)   # survives deep despite early decay
        self.assertEqual(by["snowman"].rank, 3)
        self.assertEqual(by["casper-ffg"].ranked_on, "liveness_survival_phi")
        self.assertEqual(by["casper-ffg"].rank_value, 0.33)   # survival boundary
        self.assertEqual(by["casper-ffg"].f_max_hold, 0.0)    # onset carried for context
        self.assertTrue(by["pbft"].tie and by["casper-ffg"].tie)

    def test_equivocate_ranking_snowman_ffg_pbft(self):
        r = ac.ranking_for(self.rows, "equivocate", 10)
        measured = [x for x in r if x.rank != ""]
        self.assertEqual([x.protocol for x in measured],
                         ["snowman", "casper-ffg", "pbft"])
        self.assertEqual(ac.equiv_max_conflicting(self.rows, "pbft", 10), 229.0)
        self.assertTrue(self._rank("equivocate", 10)["pbft"].safety_broken)
        self.assertFalse(self._rank("equivocate", 10)["snowman"].safety_broken)

    def test_brackets_match_committed_degradation_ranking(self):
        """The 'consumes degradation_ranking.csv' contract: T55's f_max brackets
        equal the committed T54 artifact (read from disk)."""
        path = aa.RANKING_CSV
        if not os.path.exists(path):
            self.skipTest("degradation_ranking.csv absent")
        with open(path, newline="") as f:
            t54 = list(csv.DictReader(f))

        def t54_row(family, metric, protocol, n):
            for r in t54:
                if (r["family"] == family and r["metric"] == metric
                        and r["protocol"] == protocol and int(r["n"]) == n):
                    return r
            return None

        # equivocate safety: PBFT [0.33, 0.40]
        r54 = t54_row("equivocate", "safety", "pbft", 10)
        rank = self._rank("equivocate", 10)["pbft"]
        self.assertEqual(float(r54["f_max_hold"]), rank.f_max_hold)
        self.assertEqual(float(r54["f_max_break"]), rank.f_max_break)
        # offline liveness: Casper FFG hold 0.0
        r54 = t54_row("offline", "liveness", "casper-ffg", 10)
        self.assertEqual(float(r54["f_max_hold"]),
                         self._rank("offline", 10)["casper-ffg"].f_max_hold)


# --------------------------------------------------------------------------- #
# TIER 3 — byte-stability
# --------------------------------------------------------------------------- #

class TestByteStability(unittest.TestCase):
    def setUp(self):
        if not any(r["family"] == "equivocate" for r in ac.load_adversary_rows()):
            self.skipTest("adversary CSVs not present")

    def _stable(self, writer):
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = os.path.join(d, "a.csv"), os.path.join(d, "b.csv")
            writer(p1)
            writer(p2)
            with open(p1, "rb") as f1, open(p2, "rb") as f2:
                self.assertEqual(f1.read(), f2.read())

    def test_comparison_csv_byte_stable(self):
        self._stable(ac.write_comparison_csv)

    def test_ranking_csv_byte_stable(self):
        self._stable(ac.write_ranking_csv)

    def test_csvs_round_trip_with_commas_in_notes(self):
        # Byte-stability alone would pass even if both writes were identically
        # mis-quoted; this proves the comma-bearing notes parse back intact.
        with tempfile.TemporaryDirectory() as d:
            cmp_p = ac.write_comparison_csv(os.path.join(d, "cmp.csv"))
            rank_p = ac.write_ranking_csv(os.path.join(d, "rank.csv"))
            with open(cmp_p, newline="") as f:
                cmp = list(csv.DictReader(f))
            with open(rank_p, newline="") as f:
                rank = list(csv.DictReader(f))
            self.assertTrue(all(len(r) == len(ac._CMP_FIELDS) for r in cmp))
            self.assertTrue(all(len(r) == len(ac._RANK_FIELDS) for r in rank))
            # the PBFT safety invariant note carries a comma "(view,seq)"
            inv_notes = [r["note"] for r in cmp
                         if r["metric"] == "safety_f_max_hold"
                         and r["protocol"] == "pbft"]
            self.assertTrue(any("(view,seq)" in nt for nt in inv_notes))
            # a ranking tie note carries "tied on ..., ordered by ..."
            self.assertTrue(any("ordered by" in r["note"] for r in rank))


if __name__ == "__main__":
    unittest.main()
