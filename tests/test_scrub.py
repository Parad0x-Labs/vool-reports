import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from scrub import kind_label, scrub  # noqa: E402


class ScrubTests(unittest.TestCase):
    def test_masks_private_data(self):
        text = (
            "token ghp_" + "a" * 36 + " key sk-" + "b" * 30 + "\n"
            "password: hunter22 my PIN is 4433, card 4111 1111 1111 1111\n"
            "IBAN GB82 WEST 1234 5698 7654 32, mail me at jo@example.com, call +370 612 34567\n"
            "wallet 0x" + "ab" * 20 + " path /Users/jo/notes and C:\\Users\\jo\\x\n"
        )
        masked, hits = scrub(text)
        for leak in ["ghp_", "sk-bbb", "hunter22", "4433", "4111", "GB82", "jo@example.com", "612 34567", "0xabab", "/Users/jo", "Users\\jo"]:
            self.assertNotIn(leak, masked, leak)
        self.assertEqual(set(hits), {"github_token", "api_key", "labelled_secret", "pin", "card", "iban", "email", "phone", "evm_address", "home_path"})

    def test_leaves_ordinary_report_alone(self):
        text = (
            "## Environment\n- VOOL version: 0.7.1\n- RAM (GB): 16\n- model: qwen3:8b\n"
            "- tokens: 1234 | time: 5600 ms\nThe pin is set in the sidebar. Order 1234567890123 failed.\n"
            "bug-report-fingerprint: 59842839426e2884ff178db15ab4f723\n"
        )
        masked, hits = scrub(text)
        self.assertEqual(masked, text)
        self.assertEqual(hits, [])

    def test_already_masked_text_is_stable(self):
        once, _ = scrub("password: hunter22 at /home/jo/x")
        twice, hits = scrub(once)
        self.assertEqual(once, twice)
        self.assertEqual(hits, [])

    def test_kind_label(self):
        self.assertEqual(kind_label("[wrong-answer] Out of date"), "wrong-answer")
        self.assertEqual(kind_label("[bug] crash"), "bug")


if __name__ == "__main__":
    unittest.main()
