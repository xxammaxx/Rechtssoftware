"""Anonymized document validation test harness.

Validates extraction quality against the validation goldstandard.
"""

import json
import unittest
from pathlib import Path

from bescheidpilot.core import (
    analyze_bescheid_text,
    render_analysis_export,
)
from bescheidpilot.core.network_guard import deny_network

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "validation"
GS_PATH = FIXTURES_DIR / "goldstandard.validation.json"


def _load_goldstandard():
    return json.loads(GS_PATH.read_text(encoding="utf-8"))


class AnonymizedDocumentValidationTests(unittest.TestCase):
    """Validates extraction against 10 reconstruction-based fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.gold = _load_goldstandard()
        cls.fixtures = cls.gold["fixtures"]

    def _get_result(self, name: str):
        path = FIXTURES_DIR / name
        text = path.read_text(encoding="utf-8")
        with deny_network():
            return analyze_bescheid_text(text)

    def test_all_fixtures_exist(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            path = FIXTURES_DIR / name
            with self.subTest(fixture=name):
                self.assertTrue(path.is_file(), f"Missing: {name}")

    def test_all_analyze_under_network_deny(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                self.assertIsNotNone(result)

    def test_final_decision_always_false(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                self.assertFalse(result.final_decision, f"final_decision=True in {name}")

    def test_review_required_when_critical(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            has_critical = any(
                entry["expected"].get(k) is not None
                for k in ("authority", "deadline", "required_action")
            )
            if not has_critical:
                continue
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                self.assertTrue(result.review_required, f"review_required=False in {name}")

    def test_authority_extraction(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            exp_auth = entry["expected"].get("authority")
            if exp_auth is None:
                continue
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                self.assertEqual(result.authority, exp_auth, f"Authority mismatch in {name}")

    def test_document_type_contains(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            dtc = entry["expected"].get("document_type_contains")
            if not dtc:
                continue
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                self.assertIsNotNone(result.document_type, f"No doctype in {name}")
                self.assertIn(dtc.lower(), result.document_type.lower())

    def test_deadline_explicit_null(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            exp = entry["expected"]
            if "deadline" not in exp or exp["deadline"] is not None:
                continue
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                self.assertIsNone(result.deadline, f"Expected no deadline in {name}")

    def test_deadline_contains(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            dc = entry["expected"].get("deadline_contains")
            if not dc:
                continue
            limits = entry.get("known_limits", [])
            if any("deadline" in limit.lower() or "termin" in limit.lower() for limit in limits):
                continue
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                self.assertIsNotNone(result.deadline, f"No deadline in {name}")
                self.assertIn(dc, result.deadline)

    def test_missing_documents(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            exp_docs = entry["expected"].get("missing_documents_contains", [])
            if not exp_docs:
                continue
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                for doc in exp_docs:
                    self.assertIn(doc, result.missing_documents, f"Missing doc '{doc}' in {name}")

    def test_evidence_for_critical(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            must_have = entry.get("must_have_evidence_for", [])
            if not must_have:
                continue
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                for field in must_have:
                    value = getattr(result, field, None)
                    if value and not (isinstance(value, list) and not value):
                        field_ev = [e for e in result.evidence if e.field == field]
                        self.assertGreater(len(field_ev), 0, f"No evidence for '{field}' in {name}")

    def test_export_works(self) -> None:
        for entry in self.fixtures[:3]:
            name = entry["fixture"]
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                export = render_analysis_export(result)
                self.assertIn("Finale Entscheidung: NEIN", export)

    def test_critical_errors_blocking(self) -> None:
        """No fixture should trigger critical errors."""
        critical_count = 0
        for entry in self.fixtures:
            name = entry["fixture"]
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)

            # Check critical error conditions
            if result.final_decision:
                critical_count += 1
                self.fail(f"CRITICAL: final_decision=True in {name}")

            has_critical = bool(result.authority or result.deadline or result.required_action)
            if has_critical and not result.review_required:
                critical_count += 1
                self.fail(f"CRITICAL: review_required=False in {name}")

        self.assertEqual(critical_count, 0, f"{critical_count} critical errors")


if __name__ == "__main__":
    unittest.main()
