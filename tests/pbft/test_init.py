# tests/pbft/test_init.py
"""Public surface of the pbft package."""
import unittest


class TestPublicSurface(unittest.TestCase):
    def test_expected_names_reexported(self):
        import pbft
        # Constructor + FSM data plane.
        self.assertTrue(hasattr(pbft, "PBFTNode"))
        self.assertTrue(hasattr(pbft, "Instance"))
        self.assertTrue(hasattr(pbft, "InstanceState"))
        # Wire payloads (PrePrepare consumed in T28; rest declared for T29).
        for name in ("PrePreparePayload", "PreparePayload",
                     "CommitPayload", "ViewChangePayload",
                     "NewViewPayload"):
            self.assertTrue(hasattr(pbft, name), name)
        # Observable event-type constants.
        self.assertEqual(pbft.PBFT_PRE_PREPARED, "pbft_pre_prepared")
        self.assertEqual(pbft.PBFT_REJECTED, "pbft_rejected")
        # Digest helper.
        self.assertTrue(callable(pbft.digest))


if __name__ == "__main__":
    unittest.main()
