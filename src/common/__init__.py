"""Cross-protocol simulator helpers (T39).

Today: one helper, `run_to_completion`, that pairs with
`config.factory.build_run` to collapse the bootstrap tail every caller
otherwise duplicates. See wiki/concepts/runner.md for the contract.
"""
from .runner import run_to_completion

__all__ = ["run_to_completion"]
