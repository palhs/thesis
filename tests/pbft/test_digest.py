# tests/pbft/test_digest.py
"""32-byte blake2b digest helper used by PRE-PREPARE construction and
validation (T28 spec § 6)."""
import unittest

from pbft.digest import digest


class TestDigest(unittest.TestCase):
    def test_output_width_is_32_bytes(self):
        self.assertEqual(len(digest(b"")), 32)
        self.assertEqual(len(digest(b"hello")), 32)

    def test_deterministic_across_calls(self):
        # Same input -> same output, across calls and within a process.
        self.assertEqual(digest(b"hello"), digest(b"hello"))

    def test_distinct_inputs_yield_distinct_outputs(self):
        # Collision resistance check is not the unit's job; this is a
        # sanity guard that we did not accidentally return a constant.
        self.assertNotEqual(digest(b"A"), digest(b"B"))

    def test_accepts_bytes_only(self):
        with self.assertRaises(TypeError):
            digest("not-bytes")             # str, not bytes


if __name__ == "__main__":
    unittest.main()
