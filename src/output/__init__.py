"""T40 — Unified output subsystem.

Today: one writer (write_unified_csv) + one orchestrator (baseline.main)
+ one schema bridge (ScenarioMeta, COLUMN_ORDER).
"""
from .csv import write_unified_csv
from .schema import COLUMN_ORDER, ScenarioMeta

__all__ = ("write_unified_csv", "ScenarioMeta", "COLUMN_ORDER")
