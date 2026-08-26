"""Tests for local review-required answer draft generation."""

import unittest
from pathlib import Path

from bescheidpilot.core import (
    analyze_bescheid_text,
    render_analysis_export,
)
from bescheidpilot.core.draft import create_answer_draft
from bescheidpilot.core.models import AnswerDraft
from bescheidpilot.core.network_guard import deny_network

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_JOB = (FIXTURES_DIR / "synthetic_jobcenter_mitwirkung.txt").read_text(encoding="utf-8")
FIXTURE_ANHOERUNG = (FIXTURES_DIR / "synthetic_anhoerung.txt").read_text(encoding="utf-8")


class AnswerDraftModelTests(unittest.TestCase):
    """Test the AnswerDraft data model."""

    def test_draft_default_status(self) -> None:
        draft = AnswerDraft(title="Test", body="Body")
        self.assertEqual(draft.status, "draft_requires_review")
        self.assertTrue(draft.requires_review)
        self.assertFalse(draft.final_decision)


class AnswerDraftCreationTests(unittest.TestCase):
    """Test create_answer_draft()."""

    @classmethod
    def setUpClass(cls):
        with deny_network():
            cls.result_job = analyze_bescheid_text(FIXTURE_JOB)
            cls.result_anhoerung = analyze_bescheid_text(FIXTURE_ANHOERUNG)
        cls.draft_job = create_answer_draft(cls.result_job)

    def test_draft_is_answer_draft(self) -> None:
        self.assertIsInstance(self.draft_job, AnswerDraft)

    def test_draft_contains_entwurf(self) -> None:
        self.assertIn("ENTWURF", self.draft_job.body)

    def test_draft_contains_human_review_required(self) -> None:
        self.assertIn("MENSCHLICHE PRÜFUNG ERFORDERLICH", self.draft_job.body)

    def test_draft_contains_disclaimer(self) -> None:
        self.assertIn("ersetzt keine Rechtsberatung", self.draft_job.body)

    def test_draft_final_decision_false(self) -> None:
        self.assertFalse(self.draft_job.final_decision)

    def test_draft_requires_review_true(self) -> None:
        self.assertTrue(self.draft_job.requires_review)

    def test_draft_uses_authority(self) -> None:
        self.assertIn("Jobcenter", self.draft_job.body)

    def test_draft_uses_deadline(self) -> None:
        self.assertIn("15.07.2026", self.draft_job.body)

    def test_draft_uses_action(self) -> None:
        self.assertIn("Unterlagen", self.draft_job.body)

    def test_draft_uses_missing_documents(self) -> None:
        self.assertIn("Kontoauszüge", self.draft_job.body)

    def test_draft_no_fake_facts(self) -> None:
        self.assertNotIn("gerichtlich", self.draft_job.body.lower())
        self.assertNotIn("verurteilt", self.draft_job.body.lower())

    def test_draft_no_legal_claim(self) -> None:
        self.assertNotIn("rechtlich geprüft", self.draft_job.body.lower())
        self.assertNotIn("rechtsverbindlich", self.draft_job.body.lower())

    def test_draft_no_auto_submission_claim(self) -> None:
        self.assertNotIn("automatisch versendet", self.draft_job.body.lower())
        self.assertNotIn("automatisch an behörde", self.draft_job.body.lower())
        self.assertNotIn("automatisch übermittelt", self.draft_job.body.lower())

    def test_missing_deadline_produces_placeholder(self) -> None:
        with deny_network():
            result = analyze_bescheid_text("Kein Bescheid. Nur Text.")
        draft = create_answer_draft(result)
        self.assertIn("BITTE MANUELL PRÜFEN", draft.body)
        self.assertGreater(len(draft.warnings), 0)

    def test_missing_action_produces_placeholder(self) -> None:
        with deny_network():
            result = analyze_bescheid_text("Kein Bescheid. Nur Text.")
        draft = create_answer_draft(result)
        self.assertIn("BITTE MANUELL PRÜFEN", draft.body)

    def test_draft_based_on_fields(self) -> None:
        self.assertIn("authority", self.draft_job.based_on_fields)
        self.assertIn("deadline", self.draft_job.based_on_fields)

    def test_draft_has_title(self) -> None:
        self.assertIn("Rückmeldung", self.draft_job.title)
        self.assertIn("Mitwirkung", self.draft_job.title)


class AnswerDraftExportTests(unittest.TestCase):
    """Test draft integration with export."""

    def test_export_without_draft(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        export = render_analysis_export(result, include_draft=False)
        self.assertNotIn("ANTWORTENTWURF", export)

    def test_export_with_draft_none(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        export = render_analysis_export(result, include_draft=True)
        self.assertIn("Kein Antwortentwurf vorhanden", export)

    def test_export_with_attached_draft(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        draft = create_answer_draft(result)
        # Attach draft via frozen replace pattern
        from dataclasses import replace

        result_with_draft = replace(result, answer_draft=draft)
        export = render_analysis_export(result_with_draft, include_draft=True)
        self.assertIn("ANTWORTENTWURF", export)
        self.assertIn("ENTWURF", export)


class AnswerDraftGuardrailTests(unittest.TestCase):
    """Ensure draft generation does not violate guardrails."""

    def test_draft_runs_under_network_deny(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
            draft = create_answer_draft(result)
        self.assertIsInstance(draft, AnswerDraft)

    def test_draft_no_sensitive_logs(self) -> None:
        import io
        import sys
        from unittest.mock import patch

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured), deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
            create_answer_draft(result)
        self.assertEqual(captured.getvalue(), "")

    def test_draft_no_network_imports(self) -> None:
        source = Path(__file__).resolve().parents[1] / "src" / "bescheidpilot" / "core" / "draft.py"
        content = source.read_text(encoding="utf-8")
        self.assertNotIn("import openai", content)
        self.assertNotIn("import requests", content)


if __name__ == "__main__":
    unittest.main()
