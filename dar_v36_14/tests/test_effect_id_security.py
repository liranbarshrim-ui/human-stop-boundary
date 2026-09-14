import unittest

from dar.canonical import CanonicalizationError, canonical_effect_id


class EffectIdSecurityTests(unittest.TestCase):
    def assert_rejected(self, value):
        with self.assertRaises(CanonicalizationError):
            canonical_effect_id(value)

    def test_ascii_protocol_identifiers_are_accepted(self):
        self.assertEqual(canonical_effect_id("wire-001"), "wire-001")
        self.assertEqual(canonical_effect_id("payment.v2:001"), "payment.v2:001")

    def test_zero_width_and_control_characters_are_rejected(self):
        for value in ("wire-\u200b001", "wire-\u200d001", "wire-\u0000001", "wire-\u007f001"):
            self.assert_rejected(value)

    def test_whitespace_and_bidi_marks_are_rejected(self):
        for value in (" wire-001", "wire-001 ", "wire-001\u200e", "wire-001\u200f", "wire-001\u202e"):
            self.assert_rejected(value)

    def test_unicode_homoglyphs_are_rejected(self):
        self.assert_rejected("wіre-001")  # Cyrillic U+0456 instead of Latin i
        self.assert_rejected("wıre-001")  # Latin dotless i

    def test_nfc_equivalent_ascii_policy_has_no_unicode_escape_hatch(self):
        self.assert_rejected("caf\u00e9")
        self.assert_rejected("cafe\u0301")


if __name__ == "__main__":
    unittest.main()
