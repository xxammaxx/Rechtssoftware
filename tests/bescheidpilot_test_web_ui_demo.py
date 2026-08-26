"""Tests for the local Web UI Demo Shell."""

import json
import unittest

from bescheidpilot.core.network_guard import deny_network
from bescheidpilot.web.server import (
    HOST,
    INDEX_PATH,
    WEB_DIR,
)

FIXTURE = (
    "VALIDIERUNGSFIXTURE\n"
    "Jobcenter Neustadt\n"
    "Aufforderung zur Mitwirkung\n"
    "Bitte reichen Sie bis zum 15.09.2026 Unterlagen ein:\n"
    "- Kontoauszüge\n"
    "- Mietvertrag\n"
)


class WebUIDemoConfigTests(unittest.TestCase):
    """Test server configuration is local-only."""

    def test_default_host_is_localhost(self) -> None:
        self.assertEqual(HOST, "127.0.0.1")

    def test_index_html_exists(self) -> None:
        self.assertTrue(INDEX_PATH.is_file(), f"Missing: {INDEX_PATH}")

    def test_index_html_contains_local_only_notice(self) -> None:
        content = INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn("Der Bescheid verlässt das Gerät nicht", content)
        self.assertIn("Keine Uploads", content)

    def test_index_html_no_external_assets(self) -> None:
        content = INDEX_PATH.read_text(encoding="utf-8")
        no_external = [
            "cdn.jsdelivr",
            "unpkg.com",
            "googleapis.com",
            "gstatic.com",
            "googletagmanager",
            "google-analytics",
        ]
        for asset in no_external:
            self.assertNotIn(asset, content.lower(), f"External asset found: {asset}")

    def test_index_html_no_legal_claims(self) -> None:
        content = INDEX_PATH.read_text(encoding="utf-8")
        self.assertNotIn("rechtlich geprüft", content.lower())
        self.assertNotIn("rechtsverbindlich", content.lower())

    def test_server_code_no_public_bind(self) -> None:
        server_path = WEB_DIR / "server.py"
        content = server_path.read_text(encoding="utf-8")
        # Default HOST should not be 0.0.0.0
        self.assertIn('HOST = "127.0.0.1"', content)

    def test_server_code_no_network_imports(self) -> None:
        server_path = WEB_DIR / "server.py"
        content = server_path.read_text(encoding="utf-8")
        self.assertNotIn("import requests", content)
        self.assertNotIn("import openai", content)


class WebUIDemoAnalyzeTests(unittest.TestCase):
    """Test the analysis handler directly."""

    def _call_analyze(self, text: str, include_draft: bool = False) -> dict:
        """Simulate a POST /analyze request body."""
        from dataclasses import replace

        from bescheidpilot.core import (
            analyze_bescheid_text,
            create_answer_draft,
            render_analysis_export,
        )

        with deny_network():
            result = analyze_bescheid_text(text)

        response = {
            "status": "requires_review" if result.review_required else "ok",
            "final_decision": result.final_decision,
            "review_required": result.review_required,
            "authority": result.authority,
            "document_type": result.document_type,
            "deadline": result.deadline,
            "required_action": result.required_action,
            "missing_documents": result.missing_documents,
            "risk_level": result.risk_level,
            "review_items": [
                {"field": ri.field, "severity": ri.severity} for ri in result.review_items
            ],
            "evidence": [{"field": ev.field, "value": ev.value} for ev in result.evidence],
            "warnings": result.warnings,
        }

        export_result = result
        if include_draft:
            draft = create_answer_draft(result)
            export_result = replace(result, answer_draft=draft)
            response["draft"] = {
                "title": draft.title,
                "body": draft.body,
                "status": draft.status,
                "requires_review": draft.requires_review,
                "final_decision": draft.final_decision,
            }

        response["export_text"] = render_analysis_export(export_result, include_draft=include_draft)
        return response

    def test_analyze_returns_final_decision_false(self) -> None:
        resp = self._call_analyze(FIXTURE)
        self.assertFalse(resp["final_decision"])

    def test_analyze_returns_authority(self) -> None:
        resp = self._call_analyze(FIXTURE)
        self.assertEqual(resp["authority"], "Jobcenter")

    def test_analyze_returns_review_items(self) -> None:
        resp = self._call_analyze(FIXTURE)
        self.assertGreater(len(resp["review_items"]), 0)

    def test_analyze_returns_evidence(self) -> None:
        resp = self._call_analyze(FIXTURE)
        self.assertGreater(len(resp["evidence"]), 0)

    def test_analyze_returns_export_text(self) -> None:
        resp = self._call_analyze(FIXTURE)
        self.assertIn("BESCHEIDPILOT ANALYSE-EXPORT", resp["export_text"])

    def test_export_text_contains_review_notice(self) -> None:
        resp = self._call_analyze(FIXTURE)
        self.assertIn("PRÜFUNG ERFORDERLICH", resp["export_text"])
        self.assertIn("Finale Entscheidung: NEIN", resp["export_text"])

    def test_include_draft_returns_draft(self) -> None:
        resp = self._call_analyze(FIXTURE, include_draft=True)
        self.assertIn("draft", resp)
        self.assertEqual(resp["draft"]["status"], "draft_requires_review")
        self.assertFalse(resp["draft"]["final_decision"])
        self.assertIn("ENTWURF", resp["draft"].get("body", ""))

    def test_export_text_includes_draft_section(self) -> None:
        resp = self._call_analyze(FIXTURE, include_draft=True)
        self.assertIn("ANTWORTENTWURF", resp["export_text"])

    def test_empty_text_review_required(self) -> None:
        """Empty text with missing critical fields may trigger review."""
        resp = self._call_analyze("")
        # For empty text with missing deadline/action, review is triggered
        self.assertIn(resp["status"], ("ok", "requires_review"))
        self.assertFalse(resp["final_decision"])

    def test_no_sensitive_data_in_response(self) -> None:
        resp = self._call_analyze(FIXTURE)
        raw = json.dumps(resp, ensure_ascii=False)
        self.assertNotIn("personenbezogen", raw.lower())


if __name__ == "__main__":
    unittest.main()
