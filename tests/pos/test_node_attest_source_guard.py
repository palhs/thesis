"""T47 — Casper FFG source-checkpoint guard in `_attest`.

Under heavy network delay a node can mark an epoch justified (from
aggregated FFG votes) before that epoch's checkpoint BLOCK has been
delivered locally, so `checkpoint(highest_justified)` can miss. The guard
makes the node skip that slot's attestation gracefully (emit
`casper_rejected`, reason `source_checkpoint_unavailable`) instead of
crashing the run with a KeyError — symmetric to the pre-existing target
guard. No-op under low delay (the source block is always present).
"""
import unittest

from pos import stake_weighted_proposer
from _helpers import make_node, uniform_stake, capturers, kickoff

_GLOBAL_SEED = 42
_SLOT_2_PROPOSER_N2 = stake_weighted_proposer(2, uniform_stake(2), _GLOBAL_SEED)


class TestSourceCheckpointGuard(unittest.TestCase):
    def _node_with_epoch1_checkpoint(self):
        # Drive the slot-2 proposer to slot 2 so the epoch-1 checkpoint block
        # (slot 2) is self-recorded into its chain.
        n = make_node(_SLOT_2_PROPOSER_N2, 2,
                      slots_per_epoch=2, attest_offset=1)
        capturers(n); kickoff(n)
        n._on_timer("slot", 1, t=1.0)
        n._on_timer("slot", 2, t=2.0)
        n.chain.checkpoint(1)        # precondition: target checkpoint exists
        return n

    def test_missing_source_checkpoint_rejects_not_raises(self):
        n = self._node_with_epoch1_checkpoint()
        cap = capturers(n)           # fresh capture for the attest call
        # highest_justified points at an epoch whose checkpoint block (slot
        # 18) was never delivered — the heavy-delay condition.
        n.highest_justified = 9
        with self.assertRaises(KeyError):
            n.chain.checkpoint(9)    # confirm the source really is absent

        n._attest(epoch=1, slot=3, t=3.0)   # must not raise

        rejects = [e for e in cap.emitted
                   if e[0] == "casper_rejected"
                   and e[1].get("reason") == "source_checkpoint_unavailable"]
        self.assertEqual(len(rejects), 1)
        self.assertEqual(rejects[0][1]["source_epoch"], 9)
        # No attestation is broadcast when the source block is unavailable.
        self.assertEqual(cap.count_broadcast("ATTESTATION"), 0)

    def test_present_source_checkpoint_still_attests(self):
        # The guard is a no-op when the source checkpoint is present: the
        # genesis source (epoch 0) always resolves, so a normal attest still
        # broadcasts ATTESTATION.
        n = self._node_with_epoch1_checkpoint()
        cap = capturers(n)
        n.highest_justified = 0      # genesis — always resolvable
        n._attest(epoch=1, slot=3, t=3.0)
        self.assertEqual(cap.count_broadcast("ATTESTATION"), 1)
        self.assertEqual(cap.count("casper_attested"), 1)


if __name__ == "__main__":
    unittest.main()
