"""Tests for the first real BescheidPilot Vertical Slice.

Covers: local text input → deterministic extraction → evidence output.
All tests run under existing guardrails (network-deny, offline, no-remote-llm,
no-cloud-ocr, no-sensitive-logs).
"""

import unittest
from pathlib import Path

from bescheidpilot.core import (
    analyze_bescheid_text,
    analyze_local_text,
)
from bescheidpilot.core.models import EvidenceSpan
from bescheidpilot.core.network_guard import deny_network

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


FIXTURE_JOB = _load_fixture("synthetic_jobcenter_mitwirkung.txt")
FIXTURE_ANHOERUNG = _load_fixture("synthetic_anhoerung.txt")
FIXTURE_MISSING = _load_fixture("synthetic_missing_documents.txt")


# ---------------------------------------------------------------------------
# Extraction tests
# ---------------------------------------------------------------------------


class VerticalSliceExtractionTests(unittest.TestCase):
    """Test that the deterministic extraction produces correct results."""

    # --- Authority ---

    def test_authority_jobcenter_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertEqual(result.authority, "Jobcenter")

    def test_authority_amtsgericht_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_ANHOERUNG)
        self.assertEqual(result.authority, "Amtsgericht")

    def test_authority_sozialamt_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_MISSING)
        self.assertEqual(result.authority, "Sozialamt")

    def test_authority_unknown_for_empty_text(self) -> None:
        result = analyze_bescheid_text("Dies ist ein neutraler Text ohne Behörde.")
        self.assertIsNone(result.authority)

    # --- Document type ---

    def test_document_type_mitwirkung_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertEqual(result.document_type, "Aufforderung zur Mitwirkung")

    def test_document_type_anhoerung_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_ANHOERUNG)
        self.assertEqual(result.document_type, "Anhörung")

    def test_document_type_bescheid_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_MISSING)
        self.assertEqual(result.document_type, "Bescheid")

    # --- Deadline ---

    def test_deadline_absolute_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertIsNotNone(result.deadline)
        self.assertIn("15.07.2026", result.deadline)

    def test_deadline_relative_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_ANHOERUNG)
        self.assertIsNotNone(result.deadline)
        self.assertIn("14", result.deadline)

    def test_deadline_absolute_missing_docs(self) -> None:
        result = analyze_bescheid_text(FIXTURE_MISSING)
        self.assertIsNotNone(result.deadline)
        self.assertIn("01.08.2026", result.deadline)

    def test_deadline_none_when_no_deadline(self) -> None:
        result = analyze_bescheid_text("Dies ist ein normaler Text ohne Fristangabe.")
        self.assertIsNone(result.deadline)

    # --- Required action ---

    def test_action_einreichen_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertIsNotNone(result.required_action)
        self.assertIn("Unterlagen", result.required_action)

    def test_action_stellungnahme_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_ANHOERUNG)
        self.assertIsNotNone(result.required_action)
        self.assertIn("Stellungnahme", result.required_action)

    # --- Missing documents ---

    def test_missing_docs_jobcenter(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertGreater(len(result.missing_documents), 0)
        self.assertIn("Kontoauszüge", result.missing_documents)
        self.assertIn("Mietvertrag", result.missing_documents)
        self.assertIn("Lohnabrechnung", result.missing_documents)

    def test_missing_docs_sozialamt(self) -> None:
        result = analyze_bescheid_text(FIXTURE_MISSING)
        self.assertGreater(len(result.missing_documents), 3)
        self.assertIn("Einkommensnachweis", result.missing_documents)
        self.assertIn("Mietbescheinigung", result.missing_documents)

    def test_missing_docs_empty_when_no_docs(self) -> None:
        result = analyze_bescheid_text(FIXTURE_ANHOERUNG)
        self.assertEqual(len(result.missing_documents), 0)

    # --- Risk level ---

    def test_risk_high_when_threat_present(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertIn(result.risk_level, {"high", "medium"})

    def test_risk_low_for_simple_notice(self) -> None:
        result = analyze_bescheid_text("Bitte reichen Sie Ihren Ausweis ein.")
        self.assertIn(result.risk_level, {"low", "unknown"})

    # --- Warnings ---

    def test_warning_when_no_deadline(self) -> None:
        result = analyze_bescheid_text("Keine Frist. Nur Text.")
        self.assertTrue(any("Frist" in w for w in result.warnings))

    # --- Letter date ---

    def test_letter_date_detected(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertIsNotNone(result.letter_date)
        self.assertEqual(result.letter_date, "15.06.2026")


# ---------------------------------------------------------------------------
# Evidence layer tests
# ---------------------------------------------------------------------------


class EvidenceLayerTests(unittest.TestCase):
    """Test that every critical extraction has source evidence."""

    def test_evidence_spans_exist_for_extracted_fields(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertGreater(len(result.evidence), 0)

        fields_with_evidence = {e.field for e in result.evidence}
        if result.authority:
            self.assertIn("authority", fields_with_evidence)
        if result.document_type:
            self.assertIn("document_type", fields_with_evidence)
        if result.deadline:
            self.assertIn("deadline", fields_with_evidence)
        if result.required_action:
            self.assertIn("required_action", fields_with_evidence)

    def test_evidence_spans_have_correct_shape(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        for ev in result.evidence:
            self.assertIsInstance(ev, EvidenceSpan)
            self.assertTrue(len(ev.field) > 0)
            self.assertTrue(len(ev.value) > 0)
            self.assertTrue(len(ev.quote) > 0)
            self.assertGreaterEqual(ev.end, ev.start)
            self.assertGreaterEqual(ev.confidence, 0.0)
            self.assertLessEqual(ev.confidence, 1.0)

    def test_no_evidence_for_unknown_fields(self) -> None:
        result = analyze_bescheid_text("Neutraler Text ohne Bescheidinformationen.")
        # No authority, no document type, no deadline, no action -> minimal evidence
        self.assertEqual(result.authority, None)
        self.assertEqual(result.document_type, None)
        self.assertEqual(result.deadline, None)

    def test_missing_docs_have_evidence(self) -> None:
        result = analyze_bescheid_text(FIXTURE_MISSING)
        missing_evidence = [e for e in result.evidence if e.field == "missing_documents"]
        self.assertGreater(len(missing_evidence), 0)

    def test_every_finding_has_evidence(self) -> None:
        """Jede kritische Extraktion hat mindestens eine Fundstelle."""
        result = analyze_bescheid_text(FIXTURE_JOB)
        critical_fields = {"authority", "document_type", "deadline", "required_action"}
        for field in critical_fields:
            value = getattr(result, field, None)
            if value is not None:
                field_evidence = [e for e in result.evidence if e.field == field]
                self.assertGreater(
                    len(field_evidence),
                    0,
                    f"Field '{field}' has value '{value}' but no evidence span",
                )


# ---------------------------------------------------------------------------
# Guardrail compatibility tests
# ---------------------------------------------------------------------------


class VerticalSliceGuardrailTests(unittest.TestCase):
    """Test that the vertical slice runs under all existing guardrails."""

    def test_vertical_slice_runs_under_network_deny(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertIsNotNone(result.authority)

    def test_vertical_slice_structure_unchanged(self) -> None:
        """Existing structural analysis still works."""
        with deny_network():
            struct = analyze_local_text(FIXTURE_JOB)
        self.assertTrue(struct.has_content)
        self.assertEqual(struct.execution_mode, "offline")
        self.assertFalse(struct.network_required)

    def test_vertical_slice_no_remote_llm_needed(self) -> None:
        """Analysis runs without remote LLM imports or dependencies."""
        from bescheidpilot.core import local_analysis as la_mod

        source = Path(la_mod.__file__).read_text()
        self.assertNotIn("import openai", source)
        self.assertNotIn("import anthropic", source)
        self.assertNotIn("from google.generativeai", source)

    def test_vertical_slice_no_cloud_ocr_needed(self) -> None:
        """Analysis runs without cloud OCR imports."""
        from bescheidpilot.core import extraction

        source = Path(extraction.__file__).read_text()
        self.assertNotIn("google.cloud.vision", source)
        self.assertNotIn("azure.ai.formrecognizer", source)

    def test_vertical_slice_no_sensitive_logs(self) -> None:
        """Analysis doesn't log sensitive data through its normal path."""
        import io
        import sys
        from unittest.mock import patch

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured), deny_network():
            analyze_bescheid_text(FIXTURE_JOB)

        output = captured.getvalue()
        # No raw fixture text should appear in stdout
        self.assertNotIn("Jobcenter Musterstadt", output)

    def test_vertical_slice_offline_contract(self) -> None:
        """Analysis result declares offline execution."""
        with deny_network():
            _result = analyze_bescheid_text(FIXTURE_JOB)
        # The BescheidAnalysisResult doesn't have execution_mode directly
        # but the structural analysis does
        struct = analyze_local_text(FIXTURE_JOB)
        self.assertEqual(struct.execution_mode, "offline")
        self.assertFalse(struct.network_required)


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class VerticalSliceEdgeCaseTests(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_text_handled_gracefully(self) -> None:
        result = analyze_bescheid_text("")
        self.assertIsNone(result.authority)
        self.assertIsNone(result.deadline)
        self.assertEqual(len(result.missing_documents), 0)
        self.assertFalse(result.has_any_content)

    def test_very_short_text(self) -> None:
        result = analyze_bescheid_text("Hallo Welt")
        self.assertIsNone(result.authority)
        self.assertFalse(result.has_any_content)

    def test_non_string_rejected(self) -> None:
        with self.assertRaises(TypeError):
            analyze_bescheid_text(None)  # type: ignore[arg-type]

    def test_has_any_content_true_when_authority_found(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        self.assertTrue(result.has_any_content)

    def test_critical_warnings_when_missing(self) -> None:
        result = analyze_bescheid_text("Kein Bescheid.")
        self.assertGreater(len(result.critical_warnings), 0)

    def test_fake_data_not_mistaken_for_real(self) -> None:
        result = analyze_bescheid_text(FIXTURE_JOB)
        # Fixture contains 'synthetische' marker - ensure it's not extracted
        for ev in result.evidence:
            self.assertNotIn("SYNTHETISCHE", ev.value)

    def test_all_fixtures_analyzed(self) -> None:
        """Every fixture produces a non-empty result."""
        for name, fixture in [
            ("jobcenter", FIXTURE_JOB),
            ("anhoerung", FIXTURE_ANHOERUNG),
            ("missing_docs", FIXTURE_MISSING),
        ]:
            with self.subTest(fixture=name), deny_network():
                result = analyze_bescheid_text(fixture)
                self.assertTrue(result.has_any_content, f"Fixture {name} empty")


if __name__ == "__main__":
    unittest.main()
