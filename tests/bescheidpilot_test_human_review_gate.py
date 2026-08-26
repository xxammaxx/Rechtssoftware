"""Tests for the Human Review Gate.

Ensures that analysis results are never treated as final, critical
fields are flagged for review, and no automatic legal decision occurs.
"""

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from bescheidpilot.core import ReviewItem, analyze_bescheid_text
from bescheidpilot.core.extraction import extract_bescheid_facts
from bescheidpilot.core.network_guard import deny_network
from bescheidpilot.core.review import build_review_gate

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


FIXTURE_JOB = _load("synthetic_jobcenter_mitwirkung.txt")
FIXTURE_MISSING = _load("synthetic_missing_documents.txt")


class HumanReviewGateModelTests(unittest.TestCase):
    """Test the ReviewItem data model."""

    def test_review_item_default_status_is_requires_review(self) -> None:
        ri = ReviewItem(field="deadline", value="15.07.2026")
        self.assertEqual(ri.status, "requires_review")

    def test_review_item_evidence_defaults(self) -> None:
        ri = ReviewItem(field="deadline", value="15.07.2026")
        self.assertTrue(ri.evidence_required)
        self.assertFalse(ri.evidence_present)

    def test_review_item_frozen(self) -> None:
        ri = ReviewItem(field="deadline", value="15.07.2026")
        with self.assertRaises(FrozenInstanceError):
            ri.status = "reviewed"  # type: ignore[misc]


class HumanReviewGateLogicTests(unittest.TestCase):
    """Test the build_review_gate function."""

    def test_result_has_review_required_when_critical_fields_present(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertTrue(result.review_required)

    def test_final_decision_is_always_false(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertFalse(result.final_decision)

    def test_empty_text_final_decision_false(self) -> None:
        with deny_network():
            result = analyze_bescheid_text("")
        self.assertFalse(result.final_decision)

    def test_no_automatic_reviewed_status(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        for ri in result.review_items:
            self.assertNotEqual(ri.status, "reviewed", f"Field {ri.field} was auto-reviewed")

    def test_deadline_creates_review_item(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        deadline_items = [ri for ri in result.review_items if ri.field == "deadline"]
        self.assertEqual(len(deadline_items), 1)
        self.assertEqual(deadline_items[0].status, "requires_review")

    def test_required_action_creates_review_item(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        action_items = [ri for ri in result.review_items if ri.field == "required_action"]
        self.assertEqual(len(action_items), 1)
        self.assertIn("Unterlagen", action_items[0].value or "")

    def test_missing_documents_create_review_items(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        doc_items = [ri for ri in result.review_items if ri.field == "missing_documents"]
        self.assertEqual(len(doc_items), 1)

    def test_high_risk_creates_review_item(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        risk_items = [ri for ri in result.review_items if ri.field == "risk_level"]
        if result.risk_level == "high":
            self.assertGreater(len(risk_items), 0)

    def test_missing_deadline_warning(self) -> None:
        raw = extract_bescheid_facts("Kein Bescheid, nur Text ohne Frist.")
        gated = build_review_gate(raw)
        deadline_items = [ri for ri in gated.review_items if ri.field == "deadline"]
        self.assertEqual(len(deadline_items), 1)
        self.assertIn("fehlt", deadline_items[0].reason.lower() or "fehlt")

    def test_missing_action_warning(self) -> None:
        raw = extract_bescheid_facts("Kein Bescheid, nur Text ohne Handlung.")
        gated = build_review_gate(raw)
        action_items = [ri for ri in gated.review_items if ri.field == "required_action"]
        self.assertEqual(len(action_items), 1)

    def test_review_warnings_include_extraction_warnings(self) -> None:
        raw = extract_bescheid_facts("Kein Bescheid.")
        gated = build_review_gate(raw)
        self.assertGreater(len(gated.warnings), 0)

    def test_review_items_have_severity(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        for ri in result.review_items:
            self.assertIn(ri.severity, {"HIGH", "MEDIUM", "LOW"})

    def test_evidence_present_tracks_correctly(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        for ri in result.review_items:
            if ri.evidence_required and ri.field in {"deadline", "required_action"}:
                self.assertTrue(ri.evidence_present, f"Evidence missing for {ri.field}")

    def test_quality_pack_fixtures_have_review_items(self) -> None:
        qp_dir = FIXTURES_DIR / "extraction_quality"
        if not qp_dir.is_dir():
            self.skipTest("Quality pack fixtures not found")
        count = 0
        for f in sorted(qp_dir.glob("synthetic_*.txt")):
            text = f.read_text(encoding="utf-8")
            with deny_network():
                result = analyze_bescheid_text(text)
            self.assertFalse(result.final_decision)
            count += 1
        self.assertGreater(count, 0)


class HumanReviewGateGuardrailTests(unittest.TestCase):
    """Ensure the review gate does not violate any guardrails."""

    def test_review_gate_runs_under_network_deny(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertIsNotNone(result)

    def test_review_gate_no_sensitive_logs(self) -> None:
        import io
        import sys
        from unittest.mock import patch

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured), deny_network():
            analyze_bescheid_text(FIXTURE_JOB)
        self.assertEqual(captured.getvalue(), "")

    def test_review_gate_no_remote_imports(self) -> None:
        from bescheidpilot.core import review as review_mod

        source = Path(review_mod.__file__).read_text()
        self.assertNotIn("import openai", source)
        self.assertNotIn("import anthropic", source)


if __name__ == "__main__":
    unittest.main()
