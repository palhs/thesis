"""Determinism contract for the delay-emission runners (T51, spec §8)."""
from __future__ import annotations

import unittest

from adversary.runners import RUNNERS


def _key(records):
    """A hashable, comparable projection of the event stream."""
    return [(r.t, r.event_type,
             tuple(sorted((k, repr(v)) for k, v in r.fields.items())))
            for r in records]


class TestDeterminism(unittest.TestCase):
    def test_attack_cell_byte_identical_rerun(self):
        # Same (n,f,m,seed) twice -> identical event stream (fixed shift
        # consumes no RNG; spec §8).
        for proto, runner in RUNNERS.items():
            a, _, _ = runner(n=7, f=0.30, m=10.0, seed=3)
            b, _, _ = runner(n=7, f=0.30, m=10.0, seed=3)
            self.assertEqual(_key(a), _key(b), msg=proto)

    def test_f0_equals_honest_static_baseline(self):
        # The f=0 control is byte-identical to a run with m varied: since
        # slow_ids is empty for f=0, inject_delay is a no-op regardless of m.
        for proto, runner in RUNNERS.items():
            a, _, _ = runner(n=7, f=0.0, m=2.0, seed=4)
            b, _, _ = runner(n=7, f=0.0, m=10.0, seed=4)
            self.assertEqual(_key(a), _key(b),
                             msg=f"{proto}: f=0 must ignore m")


if __name__ == "__main__":
    unittest.main()
