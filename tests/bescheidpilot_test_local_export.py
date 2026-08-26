"""Tests for local structured analysis export."""

import tempfile
import unittest
from pathlib import Path

from bescheidpilot.core import (
    analyze_bescheid_text,
    render_analysis_export,
    write_analysis_export,
)
from bescheidpilot.core.network_guard import deny_network

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


FIXTURE_JOB = _load("synthetic_jobcenter_mitwirkung.txt")


class LocalExportRenderingTests(unittest.TestCase):
    """Tests for render_analysis_export()."""

    @classmethod
    def setUpClass(cls):
        with deny_network():
            cls.result = analyze_bescheid_text(FIXTURE_JOB)
        cls.export = render_analysis_export(cls.result)

    def test_export_returns_text(self) -> None:
        self.assertIsInstance(self.export, str)
        self.assertGreater(len(self.export), 200)

    def test_export_contains_status(self) -> None:
        self.assertIn("PRÜFUNG ERFORDERLICH", self.export)

    def test_export_contains_final_decision_no(self) -> None:
        self.assertIn("Finale Entscheidung: NEIN", self.export)

    def test_export_contains_mandatory_notice(self) -> None:
        self.assertIn("ersetzt keine Rechtsberatung", self.export)
        self.assertIn("müssen durch einen Menschen geprüft werden", self.export)

    def test_export_contains_authority(self) -> None:
        self.assertIn("Behörde: Jobcenter", self.export)

    def test_export_contains_document_type(self) -> None:
        self.assertIn("Aufforderung zur Mitwirkung", self.export)

    def test_export_contains_deadline(self) -> None:
        self.assertIn("Frist:", self.export)
        self.assertIn("15.07.2026", self.export)

    def test_export_contains_action(self) -> None:
        self.assertIn("Handlung:", self.export)
        self.assertIn("Unterlagen", self.export)

    def test_export_contains_missing_documents(self) -> None:
        self.assertIn("Kontoauszüge", self.export)
        self.assertIn("Mietvertrag", self.export)

    def test_export_contains_review_items(self) -> None:
        self.assertIn("REVIEW-PFLICHT", self.export)
        self.assertIn("deadline:", self.export)
        self.assertIn("requires_review", self.export)

    def test_export_contains_evidence_spans(self) -> None:
        self.assertIn("FUNDSTELLEN", self.export)

    def test_export_contains_warnings_section_if_warnings_exist(self) -> None:
        result = self.result
        has_warnings = bool(result.warnings) or bool(result.critical_warnings)
        if has_warnings:
            self.assertIn("WARNUNGEN", self.export)

    def test_export_contains_limits_section(self) -> None:
        self.assertIn("GRENZEN", self.export)
        self.assertIn("lokal erzeugt", self.export)

    def test_export_never_claims_legally_reviewed(self) -> None:
        self.assertNotIn("rechtlich geprüft", self.export.lower())
        self.assertNotIn("rechtsverbindlich", self.export.lower())

    def test_export_never_claims_final(self) -> None:
        self.assertNotRegex(self.export, r"Finale Entscheidung:\s*JA")


class LocalExportFileWriteTests(unittest.TestCase):
    """Tests for write_analysis_export()."""

    @classmethod
    def setUpClass(cls):
        with deny_network():
            cls.result = analyze_bescheid_text(FIXTURE_JOB)

    def test_write_creates_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "export.txt")
            with deny_network():
                write_analysis_export(self.result, path)
            self.assertTrue(Path(path).is_file())
            content = Path(path).read_text(encoding="utf-8")
            self.assertIn("BESCHEIDPILOT ANALYSE-EXPORT", content)

    def test_write_utf8_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "export_utf8.txt")
            write_analysis_export(self.result, path)
            content = Path(path).read_text(encoding="utf-8")
            self.assertIn("Prüfung", content)

    def test_rejects_url_path(self) -> None:
        for bad_path in [
            "https://example.com/export.txt",
            "http://localhost/out.txt",
            "ftp://server/export.txt",
        ]:
            with self.subTest(path=bad_path), self.assertRaises(ValueError):
                write_analysis_export(self.result, bad_path)

    def test_rejects_empty_path(self) -> None:
        for bad in ["", "   ", "\t"]:
            with self.subTest(path=repr(bad)), self.assertRaises(ValueError):
                write_analysis_export(self.result, bad)

    def test_rejects_nonexistent_directory(self) -> None:
        with self.assertRaises(FileNotFoundError):
            write_analysis_export(self.result, "/nonexistent_dir_xyz123/output.txt")


class LocalExportGuardrailTests(unittest.TestCase):
    """Ensure export does not violate guardrails."""

    def test_export_runs_under_network_deny(self) -> None:
        with deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
            export = render_analysis_export(result)
        self.assertIsInstance(export, str)

    def test_export_no_sensitive_logs(self) -> None:
        import io
        import sys
        from unittest.mock import patch

        captured = io.StringIO()
        with patch.object(sys, "stdout", captured), deny_network():
            result = analyze_bescheid_text(FIXTURE_JOB)
            render_analysis_export(result)
        self.assertEqual(captured.getvalue(), "")

    def test_export_no_network_imports(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "src" / "bescheidpilot" / "core" / "export.py"
        )
        content = source.read_text(encoding="utf-8")
        self.assertNotIn("import requests", content)
        self.assertNotIn("import openai", content)

    def test_quality_pack_fixtures_exportable(self) -> None:
        qp_dir = FIXTURES_DIR / "extraction_quality"
        if not qp_dir.is_dir():
            self.skipTest("Quality pack fixtures not found")
        for f in sorted(qp_dir.glob("synthetic_*.txt"))[:3]:
            with self.subTest(fixture=f.name):
                text = f.read_text(encoding="utf-8")
                with deny_network():
                    result = analyze_bescheid_text(text)
                    export = render_analysis_export(result)
                self.assertIn("Finale Entscheidung: NEIN", export)
                self.assertNotIn("Finale Entscheidung: JA", export)


if __name__ == "__main__":
    unittest.main()
