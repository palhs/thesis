"""Simplified Casper FFG consensus — T32, T33, T34."""
from .finality import FFGTransitions, evaluate, meets_supermajority
from .node import CasperNode
from .selection import round_robin_proposer, stake_weighted_proposer

__all__ = [
    "CasperNode",
    "FFGTransitions",
    "evaluate",
    "meets_supermajority",
    "round_robin_proposer",
    "stake_weighted_proposer",
]
