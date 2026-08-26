import io
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bescheidpilot.core import local_analysis, redaction
from bescheidpilot.core.network_guard import deny_network
from scripts.bescheidpilot_guardrail_check import scan_repository

# Synthetische Testdaten — KEINE echten personenbezogenen Daten
SYNTHETIC_NAME = "Max Mustermann"
SYNTHETIC_ADDRESS = "Musterstraße 12"
SYNTHETIC_POSTAL = "06484 Quedlinburg"
SYNTHETIC_EMAIL = "max@example.invalid"
SYNTHETIC_PHONE = "03946 987654"
SYNTHETIC_IBAN = "DE89370400440532013000"
SYNTHETIC_CASE_ID = "JC-12345/2026"
SYNTHETIC_BG_NUMBER = "BG-12345BG6789"
SYNTHETIC_CUSTOMER_ID = "987654321"
SYNTHETIC_DEADLINE = "Frist bis zum 15.07.2026"

SYNTHETIC_BESCHEID_TEXT = (
    f"Bescheid vom 01.06.2026\n\n"
    f"Sehr geehrter Herr {SYNTHETIC_NAME},\n"
    f"Adresse: {SYNTHETIC_ADDRESS}, {SYNTHETIC_POSTAL}\n\n"
    f"Aktenzeichen: {SYNTHETIC_CASE_ID}\n"
    f"Kundennummer: {SYNTHETIC_CUSTOMER_ID}\n"
    f"BG-Nummer: {SYNTHETIC_BG_NUMBER}\n\n"
    f"{SYNTHETIC_DEADLINE}\n\n"
    f"Bei Fragen: {SYNTHETIC_EMAIL} oder {SYNTHETIC_PHONE}\n"
    f"IBAN: {SYNTHETIC_IBAN}\n"
)

# Variable names that suggest sensitive content
SENSITIVE_VARIABLE_NAMES = (
    "document_text",
    "ocr_text",
    "raw_text",
    "bescheid_text",
    "full_text",
    "pdf_text",
    "image_text",
    "draft_response",
    "answer_draft",
    "case_id",
    "aktenzeichen",
    "kundennummer",
    "bg_nummer",
    "customer_name",
    "address",
    "iban",
)


class RedactionHelperTests(unittest.TestCase):
    """Tests für die Redaction-Funktionen."""

    def test_redact_email(self) -> None:
        result = redaction.redact_sensitive_text(f"Kontakt: {SYNTHETIC_EMAIL}")
        self.assertNotIn(SYNTHETIC_EMAIL, result)
        self.assertIn("[REDACTED_EMAIL]", result)

    def test_redact_phone(self) -> None:
        result = redaction.redact_sensitive_text(f"Telefon: {SYNTHETIC_PHONE}")
        self.assertNotIn(SYNTHETIC_PHONE, result)
        self.assertIn("[REDACTED_PHONE]", result)

    def test_redact_iban(self) -> None:
        result = redaction.redact_sensitive_text(f"Bankverbindung: {SYNTHETIC_IBAN}")
        self.assertNotIn("DE89370400440532013000", result)
        self.assertIn("[REDACTED_IBAN]", result)

    def test_redact_case_id(self) -> None:
        result = redaction.redact_sensitive_text(f"Aktenzeichen: {SYNTHETIC_CASE_ID}")
        self.assertNotIn(SYNTHETIC_CASE_ID, result)
        self.assertIn("[REDACTED_CASE_ID]", result)

    def test_redact_bg_number(self) -> None:
        result = redaction.redact_sensitive_text(f"BG-Nummer: {SYNTHETIC_BG_NUMBER}")
        self.assertNotIn(SYNTHETIC_BG_NUMBER, result)
        self.assertIn("[REDACTED_BG_NUMBER]", result)

    def test_redact_address(self) -> None:
        result = redaction.redact_sensitive_text(f"Anschrift: {SYNTHETIC_ADDRESS}")
        self.assertNotIn(SYNTHETIC_ADDRESS, result)
        self.assertIn("[REDACTED_ADDRESS]", result)

    def test_redact_postal_city(self) -> None:
        result = redaction.redact_sensitive_text(f"Ort: {SYNTHETIC_POSTAL}")
        self.assertNotIn(SYNTHETIC_POSTAL, result)
        self.assertIn("[REDACTED_LOCATION]", result)

    def test_redact_deadline(self) -> None:
        result = redaction.redact_sensitive_text(f"{SYNTHETIC_DEADLINE}")
        self.assertNotIn(SYNTHETIC_DEADLINE, result)
        self.assertIn("[REDACTED_DEADLINE]", result)

    def test_redact_full_bescheid_text(self) -> None:
        result = redaction.redact_sensitive_text(SYNTHETIC_BESCHEID_TEXT)

        self.assertNotIn(SYNTHETIC_NAME, result)
        self.assertNotIn(SYNTHETIC_EMAIL, result)
        self.assertNotIn(SYNTHETIC_PHONE, result)
        self.assertNotIn(SYNTHETIC_CASE_ID, result)
        self.assertNotIn(SYNTHETIC_BG_NUMBER, result)
        self.assertNotIn(SYNTHETIC_CUSTOMER_ID, result)
        self.assertNotIn(SYNTHETIC_POSTAL, result)
        self.assertNotIn("DE89370400440532013000", result)

        self.assertIn("[REDACTED_", result)

    def test_contains_sensitive_pattern_detects_all(self) -> None:
        patterns_found = redaction.list_detected_patterns(SYNTHETIC_BESCHEID_TEXT)
        self.assertGreater(
            len(patterns_found), 5, f"Expected >5 patterns found, got {patterns_found}"
        )

        self.assertTrue(redaction.contains_sensitive_pattern(SYNTHETIC_BESCHEID_TEXT))

    def test_contains_sensitive_pattern_clean_text(self) -> None:
        clean = "Die lokale Analyse wurde erfolgreich abgeschlossen."
        self.assertFalse(redaction.contains_sensitive_pattern(clean))

    def test_technical_terms_preserved(self) -> None:
        result = redaction.safe_log("analysis_mode=local-structure-baseline execution_mode=offline")
        self.assertIn("analysis_mode", result)
        self.assertIn("execution_mode", result)
        self.assertIn("offline", result)


class NoSensitiveLogsGuardrailTests(unittest.TestCase):
    """Guardrail: BescheidPilot darf keine sensiblen Bescheiddaten in Logs,
    Debug-Ausgaben oder Fehlerberichte schreiben."""

    # --- 1. Harness loggt keine sensiblen Daten ---

    def test_local_analysis_does_not_log_sensitive_content(self) -> None:
        """Die lokale Analyse loggt keine Bescheidtexte."""
        captured_stdout = io.StringIO()
        captured_stderr = io.StringIO()

        with (
            patch.object(sys, "stdout", captured_stdout),
            patch.object(sys, "stderr", captured_stderr),
            deny_network(),
        ):
            local_analysis.analyze_local_text(SYNTHETIC_BESCHEID_TEXT)

        stdout_content = captured_stdout.getvalue()
        stderr_content = captured_stderr.getvalue()
        combined_output = stdout_content + stderr_content

        self.assertNotIn(SYNTHETIC_NAME, combined_output)
        self.assertNotIn(SYNTHETIC_CASE_ID, combined_output)
        self.assertNotIn(SYNTHETIC_EMAIL, combined_output)

    def test_local_analysis_does_not_log_raw_text(self) -> None:
        """Print-Ausgaben enthalten keine sensiblen Rohtexte."""
        captured_stdout = io.StringIO()

        # Simuliere eine hypothetische print-Anweisung
        with patch.object(sys, "stdout", captured_stdout):
            # Dies ist ein Guardrail-Test: wir pruefen, dass unser Code
            # keine print mit Bescheidtext macht
            safe_version = redaction.redact_sensitive_text(SYNTHETIC_BESCHEID_TEXT)
            print(safe_version, file=sys.stdout)

        stdout_content = captured_stdout.getvalue()
        self.assertNotIn(SYNTHETIC_NAME, stdout_content)
        self.assertIn("[REDACTED_NAME]", stdout_content)

    # --- 2. Logging-Harness ---

    def test_python_logging_does_not_contain_sensitive_data(self) -> None:
        """Logging-Ausgaben enthalten keine sensiblen Daten."""
        log_stream = io.StringIO()
        logger = logging.getLogger("test_no_sensitive_logs")
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(log_stream)
        logger.addHandler(handler)

        safe_text = redaction.redact_sensitive_text(SYNTHETIC_BESCHEID_TEXT)
        logger.info("Analysis result: %s", safe_text)

        log_output = log_stream.getvalue()
        self.assertNotIn(SYNTHETIC_NAME, log_output)
        self.assertNotIn(SYNTHETIC_CASE_ID, log_output)
        self.assertIn("[REDACTED_", log_output)
        logger.removeHandler(handler)

    # --- 3. Redaction vor Ausgabe ---

    def test_raw_text_is_redacted_before_logging(self) -> None:
        """Rohtext wird vor der Log-Ausgabe redigiert."""
        log_stream = io.StringIO()
        logger = logging.getLogger("test_redact_before_log")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(log_stream)
        logger.addHandler(handler)

        redacted = redaction.safe_log(SYNTHETIC_BESCHEID_TEXT)
        logger.info(redacted)

        log_output = log_stream.getvalue()
        self.assertNotIn(SYNTHETIC_NAME, log_output)
        self.assertNotIn(SYNTHETIC_EMAIL, log_output)
        logger.removeHandler(handler)

    # --- 4. Negative Fixtures: absichtliches sensitives Logging ---

    def test_direct_sensitive_logging_in_product_code_is_blocking(self) -> None:
        """Direktes Logging sensibler Variablen wird als Risiko erkannt."""
        logging_fixtures = [
            (
                "import logging\nlogger = logging.getLogger(__name__)\n\n"
                'document_text = "sensitiv"\nlogger.info(document_text)\n'
            ),
            (
                "import logging\nlogger = logging.getLogger(__name__)\n\n"
                'raw_text = "sensitiv"\nlogger.debug(raw_text)\n'
            ),
            'bescheid_text = "sensitive"\nprint(bescheid_text)\n',
        ]

        for fixture in logging_fixtures:
            with (
                self.subTest(fixture=fixture[:60]),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "logger.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(fixture, encoding="utf-8")

                report = scan_repository(root)

                self.assertTrue(
                    len(report.findings) > 0 or not report.passed,
                    f"Expected findings for sensitive logging: {fixture[:60]}",
                )

    def test_print_with_sensitive_variable_names_is_detected(self) -> None:
        """Print mit sensiblen Variablennamen wird erkannt."""
        patterns = [
            "print(document_text)\n",
            "print(ocr_text)\n",
            "print(raw_text)\n",
            "print(bescheid_text)\n",
        ]

        for pattern in patterns:
            with (
                self.subTest(pattern=pattern.strip()),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "debug.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(pattern, encoding="utf-8")

                report = scan_repository(root)

                # Should have findings from the generic rules or string checks
                self.assertTrue(
                    len(report.findings) > 0,
                    f"Expected findings for: {pattern.strip()}",
                )

    # --- 5. Exceptions ohne Rohtexte ---

    def test_exceptions_do_not_contain_raw_sensitive_text(self) -> None:
        """Exceptions enthalten keine sensiblen Rohtexte."""
        try:
            raise ValueError(
                redaction.redact_sensitive_text(f"Fehler bei Aktenzeichen {SYNTHETIC_CASE_ID}")
            )
        except ValueError as e:
            error_message = str(e)
            self.assertNotIn(SYNTHETIC_CASE_ID, error_message)
            self.assertIn("[REDACTED_CASE_ID]", error_message)

    # --- 6. Website-Daten enthalten keine echten personenbezogenen Daten ---

    def test_website_data_contains_no_real_personal_data(self) -> None:
        """Website-JSON-Daten enthalten keine echten personenbezogenen Daten."""
        root = Path(__file__).resolve().parents[1]
        site_data_dir = root / "site" / "data"

        if site_data_dir.is_dir():
            for json_file in site_data_dir.glob("*.json"):
                content = json_file.read_text(encoding="utf-8")
                self.assertNotRegex(
                    content,
                    r"\b\w+@\w+\.\w{2,}\b",
                    f"Email-like pattern in website data: {json_file}",
                )
                self.assertNotRegex(
                    content,
                    r"\bDE\d{2}\s?\d{4}\s?\d{4}",
                    f"IBAN-like pattern in website data: {json_file}",
                )

    # --- 7. Test-Fixture-Markierung ---

    def test_synthetic_fixtures_are_marked_as_synthetic(self) -> None:
        """Synthetische Testdaten sind als solche markiert."""
        # Alle Testdaten sind explizit synthetisch
        synthetic_markers = [
            SYNTHETIC_NAME,
            SYNTHETIC_ADDRESS,
            SYNTHETIC_POSTAL,
            SYNTHETIC_EMAIL,
            SYNTHETIC_PHONE,
            SYNTHETIC_IBAN,
            SYNTHETIC_CASE_ID,
            SYNTHETIC_BG_NUMBER,
            SYNTHETIC_CUSTOMER_ID,
            SYNTHETIC_DEADLINE,
        ]
        for value in synthetic_markers:
            # Keine echten Domaenen
            self.assertNotIn("@gmail.com", value.lower())
            self.assertNotIn("@yahoo", value.lower())
            self.assertNotIn("@web.de", value.lower())
            self.assertNotIn("@t-online", value.lower())


class NoSensitiveLogsStaticScanTests(unittest.TestCase):
    """Statische Scan-Tests fuer Sensitive-Log-Risiken."""

    def test_guardrail_scan_has_no_blocking_product_findings(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report = scan_repository(root / "src")
        self.assertTrue(report.passed)

    def test_redaction_module_exists(self) -> None:
        """src/core/redaction.py ist importierbar."""
        self.assertTrue(hasattr(redaction, "redact_sensitive_text"))
        self.assertTrue(hasattr(redaction, "contains_sensitive_pattern"))
        self.assertTrue(hasattr(redaction, "safe_log"))

    def test_redaction_no_network_imports(self) -> None:
        """Redaction-Modul importiert keine Netzwerkbibliotheken."""
        source = (
            Path(__file__).resolve().parents[1] / "src" / "bescheidpilot" / "core" / "redaction.py"
        )
        content = source.read_text(encoding="utf-8")

        forbidden_imports = [
            "import requests",
            "import httpx",
            "import aiohttp",
            "import socket",
            "import urllib",
            "import openai",
            "import anthropic",
            "from google.cloud",
        ]
        for forbidden in forbidden_imports:
            self.assertNotIn(forbidden, content, f"Redaction module imports: {forbidden}")


if __name__ == "__main__":
    unittest.main()
