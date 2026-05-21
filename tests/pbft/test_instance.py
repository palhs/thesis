# tests/pbft/test_instance.py
"""Per-(view, seq) PBFT instance state (T28 spec § 5)."""
import unittest

from pbft.instance import Instance, InstanceState


class TestInstanceState(unittest.TestCase):
    def test_members_present(self):
        # Four states declared up front (skeleton-cut, Decision A);
        # PREPARED and COMMITTED stay unreachable in T28.
        self.assertEqual(InstanceState.IDLE.value, 0)
        self.assertEqual(InstanceState.PRE_PREPARED.value, 1)
        self.assertEqual(InstanceState.PREPARED.value, 2)
        self.assertEqual(InstanceState.COMMITTED.value, 3)

    def test_distinct_identities(self):
        members = {InstanceState.IDLE, InstanceState.PRE_PREPARED,
                   InstanceState.PREPARED, InstanceState.COMMITTED}
        self.assertEqual(len(members), 4)


class TestInstance(unittest.TestCase):
    def test_defaults(self):
        i = Instance(view=0, seq=0)
        self.assertEqual(i.view, 0)
        self.assertEqual(i.seq, 0)
        self.assertIs(i.state, InstanceState.IDLE)
        self.assertIsNone(i.digest)
        self.assertEqual(i.prepares, {})       # T29-owned, must start empty
        self.assertEqual(i.commits, {})        # T29-owned, must start empty

    def test_prepares_commits_are_independent_per_instance(self):
        # Default factory: every Instance gets its own dict, not a shared one.
        a, b = Instance(view=0, seq=0), Instance(view=0, seq=1)
        a.prepares[1] = b"\x00" * 32
        self.assertEqual(a.prepares, {1: b"\x00" * 32})
        self.assertEqual(b.prepares, {})

    def test_state_is_mutable(self):
        # The dataclass is not frozen; T28's _accept_pre_prepare assigns
        # state and digest in place.
        i = Instance(view=0, seq=0)
        i.state = InstanceState.PRE_PREPARED
        i.digest = b"\x11" * 32
        self.assertIs(i.state, InstanceState.PRE_PREPARED)
        self.assertEqual(i.digest, b"\x11" * 32)


class TestT29MatchingHelpers(unittest.TestCase):
    """T29 spec § 5: request_payload field + digest-matching vote counts."""

    def test_request_payload_defaults_none(self):
        from pbft.instance import Instance
        self.assertIsNone(Instance(view=0, seq=0).request_payload)

    def test_matching_prepares_counts_only_digest_matches(self):
        from pbft.instance import Instance
        inst = Instance(view=0, seq=0)
        inst.digest = b"A" * 32
        inst.prepares = {0: b"A" * 32, 1: b"A" * 32, 2: b"B" * 32}
        self.assertEqual(inst.matching_prepares(), 2)

    def test_matching_is_zero_while_digest_none(self):
        from pbft.instance import Instance
        inst = Instance(view=0, seq=0)
        inst.prepares = {0: b"A" * 32}
        self.assertEqual(inst.matching_prepares(), 0)
        self.assertEqual(inst.matching_commits(), 0)


if __name__ == "__main__":
    unittest.main()
