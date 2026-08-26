"""Privacy tests for validation fixtures.

Ensures no real personal data enters the repository through
validation fixtures.
"""

import unittest
from pathlib import Path

from bescheidpilot.core.redaction import contains_sensitive_pattern, redact_sensitive_text

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "validation"
GS_PATH = FIXTURES_DIR / "goldstandard.validation.json"


class ValidationFixturePrivacyTests(unittest.TestCase):
    """Every validation fixture must comply with the anonymization policy."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures = sorted(FIXTURES_DIR.glob("validation_*.txt"))

    def test_all_fixtures_have_required_header(self) -> None:
        for f in self.fixtures:
            with self.subTest(fixture=f.name):
                text = f.read_text(encoding="utf-8")
                self.assertIn("VALIDIERUNGSFIXTURE", text)
                self.assertIn("KEIN ORIGINALDOKUMENT", text)
                self.assertIn("KEINE ECHTEN PERSONENDATEN", text)

    def test_no_real_email_patterns(self) -> None:
        import re

        email_re = re.compile(r"\b\w+@\w+\.\w{2,}\b")
        for f in self.fixtures:
            with self.subTest(fixture=f.name):
                text = f.read_text(encoding="utf-8")
                self.assertIsNone(email_re.search(text), f"Email-like pattern in {f.name}")

    def test_no_real_iban_patterns(self) -> None:
        import re

        iban_re = re.compile(r"\bDE\d{2}\s?\d{4}\s?\d{4}")
        for f in self.fixtures:
            with self.subTest(fixture=f.name):
                text = f.read_text(encoding="utf-8")
                self.assertIsNone(iban_re.search(text), f"IBAN-like pattern in {f.name}")

    def test_no_real_phone_numbers(self) -> None:
        import re

        phone_re = re.compile(r"\b(?:\+49|0)\d{2,4}\s?\d{3,8}\b")
        for f in self.fixtures:
            with self.subTest(fixture=f.name):
                text = f.read_text(encoding="utf-8")
                self.assertIsNone(phone_re.search(text), f"Phone-like pattern in {f.name}")

    def test_redaction_can_handle_fixtures(self) -> None:
        for f in self.fixtures:
            with self.subTest(fixture=f.name):
                text = f.read_text(encoding="utf-8")
                redacted = redact_sensitive_text(text)
                self.assertIsInstance(redacted, str)

    def test_contains_sensitive_pattern_works(self) -> None:
        for f in self.fixtures:
            with self.subTest(fixture=f.name):
                text = f.read_text(encoding="utf-8")
                result = contains_sensitive_pattern(text)
                self.assertIsInstance(result, bool)

    def test_goldstandard_exists_and_valid(self) -> None:
        self.assertTrue(GS_PATH.is_file())
        import json

        gs = json.loads(GS_PATH.read_text(encoding="utf-8"))
        self.assertIn("fixtures", gs)
        self.assertGreater(len(gs["fixtures"]), 5)

    def test_goldstandard_no_real_personal_data(self) -> None:
        import json

        gs = json.loads(GS_PATH.read_text(encoding="utf-8"))
        raw = json.dumps(gs)
        self.assertNotIn("@gmail", raw.lower())
        self.assertNotIn("@yahoo", raw.lower())


if __name__ == "__main__":
    unittest.main()
