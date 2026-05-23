import unittest

from pos.messages import AttestationPayload
from pos.chain import GENESIS_HASH
from _helpers import make_node, capturers, kickoff


class TestAttesting(unittest.TestCase):
    def _advance_to(self, n, last_slot):
        """Fire the slot timer for slots 1..last_slot."""
        for s in range(1, last_slot + 1):
            n._on_timer("slot", s, t=float(s))

    def test_attestation_emitted_once_per_epoch(self):
        # slots_per_epoch=2, attest_offset=1 -> attest on slots 3,5,7,...
        n = make_node(0, 2, slots_per_epoch=2, attest_offset=1)
        cap = capturers(n); kickoff(n)
        self._advance_to(n, 4)
        # epoch 1 (slots 2,3) attested at slot 3; epoch 2 not yet (slot 5).
        self.assertEqual(cap.count_broadcast("ATTESTATION"), 1)

    def test_attestation_payload_carries_ffg_link(self):
        n = make_node(0, 2, slots_per_epoch=2, attest_offset=1)
        cap = capturers(n); kickoff(n)
        self._advance_to(n, 3)
        att = [b for b in cap.broadcasts if b[0] == "ATTESTATION"][0][1]
        self.assertIsInstance(att, AttestationPayload)
        self.assertEqual(att.ffg.source_epoch, 0)        # genesis epoch
        self.assertEqual(att.ffg.target_epoch, 1)
        self.assertEqual(att.ffg.source_hash, GENESIS_HASH)
        self.assertEqual(att.attester_idx, 0)

    def test_node_self_records_own_ffg_vote(self):
        n = make_node(0, 2, slots_per_epoch=2, attest_offset=1)
        capturers(n); kickoff(n)
        self._advance_to(n, 3)
        es = n.epoch_states[1]
        self.assertEqual(es.link_stake(0), 3.0)          # own stake counted

    def test_casper_attested_event_emitted(self):
        n = make_node(0, 2, slots_per_epoch=2, attest_offset=1)
        cap = capturers(n); kickoff(n)
        self._advance_to(n, 3)
        self.assertEqual(cap.count("casper_attested"), 1)


if __name__ == "__main__":
    unittest.main()
