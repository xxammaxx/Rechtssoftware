"""Tests for the Extraction Quality Pack — 15 synthetic Bescheid variants."""

import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from bescheidpilot.core import analyze_bescheid_text
from bescheidpilot.core.network_guard import deny_network

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "extraction_quality"
GOLDSTANDARD_PATH = FIXTURES_DIR / "goldstandard.json"


def _load_goldstandard():
    return json.loads(GOLDSTANDARD_PATH.read_text(encoding="utf-8"))


class ExtractionQualityPackTests(unittest.TestCase):
    """Validates all 15 fixtures against goldstandard expectations."""

    @classmethod
    def setUpClass(cls):
        cls.gold = _load_goldstandard()
        cls.fixtures = cls.gold["fixtures"]

    def _get_result(self, fixture_name: str):
        path = FIXTURES_DIR / fixture_name
        text = path.read_text(encoding="utf-8")
        with deny_network():
            return analyze_bescheid_text(text)

    # --- Fixture integrity ---

    def test_all_fixtures_loadable(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            path = FIXTURES_DIR / name
            with self.subTest(fixture=name):
                self.assertTrue(path.is_file(), f"Missing fixture: {name}")
                text = path.read_text(encoding="utf-8")
                self.assertIn("SYNTHETISCHE", text)

    def test_no_fixture_contains_real_personal_data(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            path = FIXTURES_DIR / name
            with self.subTest(fixture=name):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("@gmail", text)
                self.assertNotIn("@yahoo", text)

    # --- Authority ---

    def test_authority_extraction(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            exp = entry["expected"]
            if "authority" not in exp:
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                if exp["authority"] is None:
                    self.assertIsNone(result.authority)
                else:
                    self.assertEqual(result.authority, exp["authority"])

    # --- Document type ---

    def test_document_type_extraction(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            dt_contains = entry["expected"].get("document_type_contains")
            if not dt_contains:
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                self.assertIsNotNone(result.document_type)
                self.assertIn(dt_contains.lower(), result.document_type.lower())

    # --- Deadline (explicit null) ---

    def test_deadline_explicit_null(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            exp = entry["expected"]
            if "deadline" not in exp or exp["deadline"] is not None:
                continue
            limitation = entry.get("known_limitation", "")
            if "deadline" in limitation.lower():
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                self.assertIsNone(result.deadline)

    # --- Deadline (contains) ---

    def test_deadline_contains(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            dc = entry["expected"].get("deadline_contains")
            if not dc:
                continue
            limitation = entry.get("known_limitation", "")
            if "deadline" in limitation.lower():
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                self.assertIsNotNone(result.deadline)
                self.assertIn(dc, result.deadline)

    # --- Required action (explicit null) ---

    def test_required_action_explicit_null(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            exp = entry["expected"]
            if "required_action" not in exp or exp["required_action"] is not None:
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                self.assertIsNone(result.required_action)

    # --- Required action (contains) ---

    def test_required_action_contains(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            ac = entry["expected"].get("required_action_contains")
            if not ac:
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                self.assertIsNotNone(result.required_action)
                self.assertIn(ac.lower(), result.required_action.lower())

    # --- Missing documents ---

    def test_missing_documents_contains(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            expected_docs = entry["expected"].get("missing_documents_contains", [])
            if not expected_docs:
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                for doc in expected_docs:
                    self.assertIn(doc, result.missing_documents)

    # --- Risk level ---

    def test_risk_level_minimum(self) -> None:
        levels = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
        for entry in self.fixtures:
            name = entry["fixture"]
            min_level = entry["expected"].get("risk_level_min")
            if not min_level:
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                self.assertGreaterEqual(
                    levels.get(result.risk_level, -1),
                    levels.get(min_level, -1),
                )

    # --- Evidence ---

    def test_must_have_evidence(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            must_have = entry.get("must_have_evidence_for", [])
            if not must_have:
                continue
            with self.subTest(fixture=name):
                result = self._get_result(name)
                for field in must_have:
                    value = getattr(result, field, None)
                    if value and not (isinstance(value, list) and not value):
                        field_evidence = [e for e in result.evidence if e.field == field]
                        self.assertGreater(len(field_evidence), 0)

    def test_evidence_spans_valid(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            with self.subTest(fixture=name):
                result = self._get_result(name)
                for ev in result.evidence:
                    self.assertGreater(len(ev.field), 0)
                    self.assertGreater(len(ev.value), 0)
                    self.assertGreaterEqual(ev.end, ev.start)
                    self.assertGreaterEqual(ev.confidence, 0.0)
                    self.assertLessEqual(ev.confidence, 1.0)

    # --- Guardrails ---

    def test_all_fixtures_run_under_network_deny(self) -> None:
        for entry in self.fixtures:
            name = entry["fixture"]
            with self.subTest(fixture=name), deny_network():
                result = self._get_result(name)
                self.assertIsNotNone(result)

    def test_no_sensitive_output(self) -> None:
        for entry in self.fixtures[:3]:
            name = entry["fixture"]
            with self.subTest(fixture=name):
                captured = io.StringIO()
                with patch.object(sys, "stdout", captured), deny_network():
                    self._get_result(name)
                self.assertEqual(captured.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
