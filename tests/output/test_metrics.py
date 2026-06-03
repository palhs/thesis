"""T41 — unit tests for output.metrics: committed_tx, goodput,
bytes_per_acu, and the _BASE_BUDGET coverage guard.

Uses constant arrival so batch sizes are exact integers
(offered_rate=10, interval=1.0 -> 10 tx/opportunity).
"""
from __future__ import annotations

import math
import re
import unittest
from pathlib import Path

from event_log import EventRecord
from output.metrics import (
    _BASE_BUDGET,
    _TX_CARRYING,
    bytes_per_acu,
    committed_tx,
    goodput,
)
from output.schema import ScenarioMeta

_SRC = Path(__file__).resolve().parents[2] / "src"


def _const_meta(offered_rate: float = 10.0, interval: float = 1.0,
                tx_bytes: int = 512) -> ScenarioMeta:
    return ScenarioMeta(
        run_id="m", protocol="pbft", n=4, variant=None, seed=42,
        t_max=20.0, arrival_process="constant", offered_rate=offered_rate,
        tx_bytes=tx_bytes, conflict_rate=0.0, interval=interval,
    )


def _delivery(mt: str) -> EventRecord:
    return EventRecord(t=0.1, node_id=0, event_type="delivery", seq=0,
                       fields={"msg_type": mt})


def _decided(inst) -> EventRecord:
    return EventRecord(t=0.4, node_id=0, event_type="decided", seq=-1,
                       fields={"instance_id": inst})


class TestCommittedTx(unittest.TestCase):
    def test_exact_constant_arrival(self):
        meta = _const_meta(offered_rate=10.0)
        # 10 tx/opportunity * 3 opportunities = 30.
        self.assertEqual(committed_tx(meta, 3), 30)

    def test_zero_opportunities(self):
        self.assertEqual(committed_tx(_const_meta(), 0), 0)
        self.assertEqual(committed_tx(_const_meta(), -1), 0)

    def test_scales_with_rate(self):
        self.assertEqual(committed_tx(_const_meta(offered_rate=5.0), 4), 20)


class TestGoodput(unittest.TestCase):
    def test_exact_value(self):
        # 10*2 = 20 committed tx over time_denom=4.0 -> 5.0.
        self.assertAlmostEqual(goodput(_const_meta(), 2, 4.0), 5.0, places=6)

    def test_nan_on_zero_time(self):
        self.assertTrue(math.isnan(goodput(_const_meta(), 2, 0.0)))

    def test_nan_on_zero_opportunities(self):
        self.assertTrue(math.isnan(goodput(_const_meta(), 0, 4.0)))


class TestBytesPerAcu(unittest.TestCase):
    def test_nan_when_no_decided(self):
        recs = [_delivery("PREPARE")]
        self.assertTrue(math.isnan(bytes_per_acu(recs, _const_meta())))

    def test_non_tx_carrying_exact(self):
        # 2 PREPARE deliveries (base 48, not tx-carrying), 2 decided.
        recs = [_delivery("PREPARE"), _delivery("PREPARE"),
                _decided((0, 0)), _decided((0, 1))]
        self.assertAlmostEqual(bytes_per_acu(recs, _const_meta()),
                               (48 + 48) / 2, places=6)

    def test_tx_carrying_adds_tx_component(self):
        # 1 PRE-PREPARE delivery: base 48 + tx (10*1.0*512 = 5120) = 5168.
        # 1 decided -> 5168.0.
        recs = [_delivery("PRE-PREPARE"), _decided((0, 0))]
        self.assertAlmostEqual(bytes_per_acu(recs, _const_meta()),
                               5168.0, places=6)

    def test_unbudgeted_msg_type_raises(self):
        recs = [_delivery("TOTALLY-UNKNOWN"), _decided((0, 0))]
        with self.assertRaises(KeyError):
            bytes_per_acu(recs, _const_meta())

    def test_decided_count_is_raw_event_count(self):
        # 2 PREPARE deliveries, 3 decided EVENTS (not deduped) -> /3.
        recs = [_delivery("PREPARE"), _delivery("PREPARE"),
                _decided((0, 0)), _decided((0, 0)), _decided((0, 1))]
        self.assertAlmostEqual(bytes_per_acu(recs, _const_meta()),
                               96 / 3, places=6)


class TestBudgetCoverage(unittest.TestCase):
    """Every msg_type the three protocols emit must be in _BASE_BUDGET."""

    def _emitted_types(self, node_file: str) -> set[str]:
        text = (_SRC / node_file).read_text()
        # First string literal arg to broadcast(...) / send(peer, "TYPE", ...)
        out: set[str] = set()
        for m in re.finditer(r"\.broadcast\(\s*\"([A-Z-]+)\"", text):
            out.add(m.group(1))
        for m in re.finditer(r"\.send\([^,]+,\s*\"([A-Z-]+)\"", text):
            out.add(m.group(1))
        return out

    def test_pbft_types_budgeted(self):
        for mt in self._emitted_types("pbft/node.py"):
            self.assertIn(mt, _BASE_BUDGET, f"PBFT {mt} unbudgeted")

    def test_pos_types_budgeted(self):
        for mt in self._emitted_types("pos/node.py"):
            self.assertIn(mt, _BASE_BUDGET, f"FFG {mt} unbudgeted")

    def test_snowman_types_budgeted(self):
        for mt in self._emitted_types("snowman/node.py"):
            self.assertIn(mt, _BASE_BUDGET, f"Snowman {mt} unbudgeted")

    def test_documented_minimum_set_present(self):
        required = {
            "PRE-PREPARE", "PREPARE", "COMMIT", "VIEW-CHANGE", "NEW-VIEW",
            "BLOCK-PROPOSAL", "ATTESTATION",
            "BLOCK-ANNOUNCEMENT", "QUERY", "QUERY-RESPONSE",
        }
        self.assertTrue(required <= set(_BASE_BUDGET))

    def test_tx_carrying_subset_of_budget(self):
        self.assertTrue(_TX_CARRYING <= set(_BASE_BUDGET))


if __name__ == "__main__":
    unittest.main()
