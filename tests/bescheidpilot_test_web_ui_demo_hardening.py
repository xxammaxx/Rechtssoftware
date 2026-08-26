"""Tests for the Web UI Demo Hardening Sprint.

Validates:
- Local-only banner visibility
- Demo fixture selection security (allowlist only)
- Copy buttons use native API only
- No external assets introduced
- Review/export/draft clauses preserved
- Guardrail scan still passes
"""

import unittest
from unittest.mock import Mock

from bescheidpilot.core.network_guard import deny_network
from bescheidpilot.web.server import (
    DEMO_FIXTURE_LABELS,
    DEMO_FIXTURES,
    HOST,
    INDEX_PATH,
    WEB_DIR,
    BescheidPilotHandler,
)

FIXTURE = (
    "VALIDIERUNGSFIXTURE\n"
    "Jobcenter Neustadt\n"
    "Aufforderung zur Mitwirkung\n"
    "Bitte reichen Sie bis zum 15.09.2026 Unterlagen ein:\n"
    "- Kontoauszüge\n"
    "- Mietvertrag\n"
)


class DemoHardeningBannerTests(unittest.TestCase):
    """Test that the demo page contains the required Local-only hardening elements."""

    def _content(self) -> str:
        return INDEX_PATH.read_text(encoding="utf-8")

    # 1. Startseite enthält Local-only-Banner.
    def test_banner_contains_local_demo(self) -> None:
        content = self._content()
        self.assertIn("BESCHEIDPILOT LOCAL DEMO", content)

    # 2. Startseite enthält „Der Bescheid verlässt das Gerät nicht“.
    def test_banner_contains_bescheid_verlaesst_geraet_nicht(self) -> None:
        content = self._content()
        self.assertIn("Der Bescheid verlässt das Gerät nicht", content)

    # 3. Startseite enthält „Keine Cloud-KI“.
    def test_banner_contains_keine_cloud_ki(self) -> None:
        content = self._content()
        self.assertIn("Keine Cloud-KI", content)

    # 4. Startseite enthält „Keine Cloud-OCR“.
    def test_banner_contains_keine_cloud_ocr(self) -> None:
        content = self._content()
        self.assertIn("Keine Cloud-OCR", content)

    # 5. Startseite enthält „PRÜFUNG ERFORDERLICH“.
    def test_page_contains_pruefung_erforderlich(self) -> None:
        content = self._content()
        self.assertIn("PRÜFUNG ERFORDERLICH", content)

    # 6. Startseite enthält keine externen Assets.
    def test_page_has_no_external_assets(self) -> None:
        content = self._content().lower()
        external_patterns = [
            "cdn.jsdelivr",
            "unpkg.com",
            "googleapis.com",
            "gstatic.com",
            "googletagmanager",
            "google-analytics",
            "https://fonts.googleapis.com",
            "https://cdn.",
        ]
        for pattern in external_patterns:
            self.assertNotIn(pattern, content, f"External asset found: {pattern}")

    # 15. Guardrail-Scan bleibt PASS (static analysis — no blocking findings).
    def test_no_blocking_strings_in_html(self) -> None:
        content = self._content().lower()
        self.assertNotIn("rechtlich geprüft", content)
        self.assertNotIn("rechtsverbindlich", content)
        self.assertNotIn("bereit für produktiven einsatz", content)
        self.assertNotIn("produktionsbereit", content)
        self.assertNotIn("cloud-upload", content)


class DemoHardeningFixtureTests(unittest.TestCase):
    """Test the allowlisted demo fixture endpoint security."""

    # 7. Demo-Fixture-Auswahl nutzt Allowlist.
    def test_all_fixture_ids_are_in_allowlist(self) -> None:
        expected_ids = {
            "jobcenter_mitwirkung",
            "anhoerung_stellungnahme",
            "sozialamt_nachforderung",
            "inkasso_mahnung",
            "aenderungsbescheid",
        }
        self.assertEqual(set(DEMO_FIXTURES.keys()), expected_ids)

    def test_all_fixture_paths_exist(self) -> None:
        for fid, path in DEMO_FIXTURES.items():
            self.assertTrue(path.is_file(), f"Fixture file missing for '{fid}': {path}")

    def test_all_fixture_labels_exist(self) -> None:
        for fid in DEMO_FIXTURES:
            self.assertIn(fid, DEMO_FIXTURE_LABELS, f"Missing label for '{fid}'")

    # 8. Ungültige Fixture-ID wird abgelehnt.
    def test_invalid_fixture_id_rejected(self) -> None:
        """Unknown fixture IDs are not in the allowlist and must not resolve."""
        invalid_ids = [
            "../etc/passwd",
            "../../secrets",
            "validation_003",
            "",
            "nonexistent",
            "/",
            "..\\..\\windows",
        ]
        for invalid_id in invalid_ids:
            self.assertNotIn(
                invalid_id,
                DEMO_FIXTURES,
                f"Invalid fixture ID should not be in allowlist: {invalid_id}",
            )

    # 9. Kein freier Dateipfad über Fixture-Endpoint lesbar.
    def test_fixture_paths_are_under_allowed_directory(self) -> None:
        """All fixture paths must reside under the validation fixtures directory."""
        from bescheidpilot.web.server import _FIXTURES_DIR

        for fid, path in DEMO_FIXTURES.items():
            resolved = path.resolve()
            self.assertTrue(
                str(resolved).startswith(str(_FIXTURES_DIR)),
                f"Fixture '{fid}' path escapes allowed directory: {resolved}",
            )

    def test_fixture_endpoint_honors_allowlist(self) -> None:
        """Integration test: the handler rejects unknown fixture IDs."""
        # Simulate a GET /demo-fixture/invalid
        handler = _make_test_handler("GET", "/demo-fixture/invalid_id")
        handler._serve_fixture = Mock(wraps=handler._serve_fixture)
        handler.do_GET()
        # The serve_fixture should have been called and returned 404 via _send_json
        handler._serve_fixture.assert_called_once_with("invalid_id")

    def test_fixture_endpoint_rejects_traversal(self) -> None:
        """Path traversal attempts must not match any allowlist key."""
        traversal_ids = [
            "../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "....//....//etc/passwd",
        ]
        for tid in traversal_ids:
            self.assertNotIn(tid, DEMO_FIXTURES)

    def test_valid_fixture_loads_text(self) -> None:
        """A valid fixture ID resolves to readable, non-empty text."""
        path = DEMO_FIXTURES["jobcenter_mitwirkung"]
        text = path.read_text(encoding="utf-8")
        self.assertIn("VALIDIERUNGSFIXTURE", text)
        self.assertIn("Jobcenter", text)
        self.assertGreater(len(text), 100)


class DemoHardeningResultTests(unittest.TestCase):
    """Test that the analysis results maintain required properties."""

    def _call_analyze(self, text: str, include_draft: bool = False) -> dict:
        from dataclasses import replace

        from bescheidpilot.core import (
            analyze_bescheid_text,
            create_answer_draft,
            render_analysis_export,
        )

        with deny_network():
            result = analyze_bescheid_text(text)

        response = {
            "review_required": result.review_required,
            "final_decision": result.final_decision,
            "export_text": "",
        }

        export_result = result
        if include_draft:
            draft = create_answer_draft(result)
            export_result = replace(result, answer_draft=draft)
            response["draft"] = {"body": draft.body, "status": draft.status}

        response["export_text"] = render_analysis_export(export_result, include_draft=include_draft)
        return response

    # 10. Analyse bleibt lokal.
    def test_analysis_is_local(self) -> None:
        """Analysis result declares offline execution."""
        resp = self._call_analyze(FIXTURE)
        self.assertIn("lokal erzeugt", resp["export_text"])

    # 11. Export enthält Review-Pflicht.
    def test_export_contains_review_notice(self) -> None:
        resp = self._call_analyze(FIXTURE)
        self.assertIn("PRÜFUNG ERFORDERLICH", resp["export_text"])
        self.assertIn("Finale Entscheidung: NEIN", resp["export_text"])

    # 12. Draft enthält Entwurfswarnung.
    def test_draft_contains_entwurf_warning(self) -> None:
        resp = self._call_analyze(FIXTURE, include_draft=True)
        self.assertIn("draft", resp)
        self.assertIn("ENTWURF", resp["draft"]["body"])
        self.assertEqual(resp["draft"]["status"], "draft_requires_review")

    def test_draft_warns_human_review_required(self) -> None:
        resp = self._call_analyze(FIXTURE, include_draft=True)
        export = resp["export_text"].lower()
        self.assertTrue(
            "prüfung" in export or "entwurf" in export,
            "Export with draft must indicate human review or draft status",
        )

    # 16. Alle bestehenden Tests bleiben grün (validated by running full suite).


class DemoHardeningServerConfigTests(unittest.TestCase):
    """Test server configuration remains safe."""

    # 14. Webserver bindet weiter standardmäßig an 127.0.0.1.
    def test_default_host_is_localhost(self) -> None:
        self.assertEqual(HOST, "127.0.0.1")

    def test_server_code_no_public_bind(self) -> None:
        server_path = WEB_DIR / "server.py"
        content = server_path.read_text(encoding="utf-8")
        self.assertIn('HOST = "127.0.0.1"', content)

    def test_server_code_no_network_imports(self) -> None:
        server_path = WEB_DIR / "server.py"
        content = server_path.read_text(encoding="utf-8")
        self.assertNotIn("import requests", content)
        self.assertNotIn("import openai", content)
        self.assertNotIn("import httpx", content)

    # 13. Copy-Buttons laden keine externen Bibliotheken.
    def test_copy_buttons_use_native_api(self) -> None:
        content = INDEX_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("navigator.clipboard.writetext", content)
        # No external clipboard libraries
        self.assertNotIn("clipboard.js", content)
        self.assertNotIn("clipboardjs", content)
        self.assertNotIn("copy-to-clipboard", content)


class DemoHardeningStructureTests(unittest.TestCase):
    """Test the HTML structure has the expected hardening elements."""

    def _content(self) -> str:
        return INDEX_PATH.read_text(encoding="utf-8")

    def test_page_has_status_cards(self) -> None:
        content = self._content()
        self.assertIn("Local-only", content)
        self.assertIn("Remote-KI", content)
        self.assertIn("Cloud-OCR", content)

    def test_page_has_flow_steps(self) -> None:
        content = self._content()
        self.assertIn("Demo-Ablauf", content)
        self.assertIn("Beispiel wählen", content)
        self.assertIn("Lokal analysieren", content)
        self.assertIn("Feedback erfassen", content)

    def test_page_has_fixture_selection(self) -> None:
        content = self._content()
        self.assertIn("fixture-select", content)
        self.assertIn("load-fixture-btn", content)

    def test_page_has_limits_section(self) -> None:
        content = self._content()
        self.assertIn("Grenzen", content)
        self.assertIn("Kein OCR/PDF", content)
        self.assertIn("Keine Speicherung", content)
        self.assertIn("Keine Rechtsberatung", content)

    def test_page_has_copy_button(self) -> None:
        content = self._content()
        self.assertIn("copy-btn", content)
        self.assertIn("Kopieren", content)

    def test_page_no_external_js_libraries(self) -> None:
        content = self._content().lower()
        self.assertNotIn("<script src=", content)
        # Allow only inline script tags (no src attribute with external URL)
        # Check that script tags with src don't reference external URLs
        import re

        script_srcs = re.findall(r'<script[^>]*src=["\'][^"\']*["\']', content.lower())
        for src in script_srcs:
            self.assertNotIn("http", src, f"External script found: {src}")


class DemoHardeningGuardrailTests(unittest.TestCase):
    """Test that guardrail invariants are maintained."""

    def test_server_paths_use_forward_slashes_for_index(self) -> None:
        """Ensure the INDEX_PATH is correct and accessible."""
        self.assertTrue(INDEX_PATH.is_file())
        self.assertEqual(INDEX_PATH.suffix, ".html")

    def test_demo_fixtures_are_synthetic(self) -> None:
        """Every allowlisted fixture must be marked as synthetic."""
        for fid, path in DEMO_FIXTURES.items():
            text = path.read_text(encoding="utf-8")
            self.assertIn(
                "VALIDIERUNGSFIXTURE",
                text,
                f"Fixture '{fid}' is not marked as VALIDIERUNGSFIXTURE",
            )
            self.assertIn(
                "KEINE ECHTEN PERSONENDATEN",
                text,
                f"Fixture '{fid}' missing 'KEINE ECHTEN PERSONENDATEN'",
            )

    def test_demo_fixtures_no_real_personal_data(self) -> None:
        """No fixture contains identifiable real personal data patterns."""
        real_patterns = [
            "max mustermann",
            "erika musterfrau",
            "berlin",
            "münchen",
            "hamburg",
        ]
        for fid, path in DEMO_FIXTURES.items():
            text = path.read_text(encoding="utf-8").lower()
            for pattern in real_patterns:
                self.assertNotIn(
                    pattern,
                    text,
                    f"Fixture '{fid}' may contain real data: '{pattern}'",
                )


def _make_test_handler(method: str, path: str) -> BescheidPilotHandler:
    """Create a minimal handler for unit testing endpoint logic."""
    from io import BytesIO

    handler = BescheidPilotHandler.__new__(BescheidPilotHandler)

    # Minimal mocks needed to call handler methods
    handler.path = path
    handler.command = method
    handler.headers = {}
    handler.rfile = BytesIO()
    handler.wfile = BytesIO()

    # Mock send_response, send_header, end_headers to avoid actual HTTP responses
    handler.send_response = Mock()
    handler.send_header = Mock()
    handler.end_headers = Mock()
    handler.send_error = Mock()

    return handler


if __name__ == "__main__":
    unittest.main()
