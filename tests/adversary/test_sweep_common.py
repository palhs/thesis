import unittest
from adversary.sweep_common import (ADV_COMMON_COLUMNS, strategy_label,
                                     is_heavy_snowman)


class TestSweepCommon(unittest.TestCase):
    def test_common_columns_are_neutral(self):
        assert "adversary_strategy" in ADV_COMMON_COLUMNS
        assert "adversary_node_count" in ADV_COMMON_COLUMNS
        assert "byzantine_fraction" in ADV_COMMON_COLUMNS
        assert "delay_mult" not in ADV_COMMON_COLUMNS
        assert "slow_node_count" not in ADV_COMMON_COLUMNS

    def test_strategy_label(self):
        assert strategy_label(0.0, "withhold-participation") == "none"
        assert strategy_label(0.2, "withhold-participation") == \
            "withhold-participation"

    def test_is_heavy_snowman(self):
        assert is_heavy_snowman("snowman", 25) is True
        assert is_heavy_snowman("snowman", 10) is False
        assert is_heavy_snowman("pbft", 25) is False
