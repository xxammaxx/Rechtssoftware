import tempfile
import unittest
from pathlib import Path

from scripts.bescheidpilot_guardrail_check import scan_repository


class StaticGuardrailTests(unittest.TestCase):
    def test_current_repository_has_no_product_code_violation(self) -> None:
        root = Path(__file__).resolve().parents[1]

        report = scan_repository(root / "src")

        self.assertTrue(report.passed, report.findings)
        self.assertGreaterEqual(report.product_files_scanned, 1)

    def test_network_import_in_product_code_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
            product_file.parent.mkdir(parents=True)
            product_file.write_text(
                "import socket\n\nsocket.create_connection(('example.invalid', 443))\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(any("forbidden network" in finding.rule for finding in report.findings))

    def test_remote_provider_in_product_code_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
            product_file.parent.mkdir(parents=True)
            product_file.write_text(
                "from openai import OpenAI\n\nclient = OpenAI()\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(any("provider import" in finding.rule for finding in report.findings))

    def test_remote_url_in_product_code_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
            product_file.parent.mkdir(parents=True)
            product_file.write_text(
                "REMOTE_ENDPOINT = 'https://example.invalid/upload'\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(any(finding.rule == "remote URL literal" for finding in report.findings))

    def test_upload_and_telemetry_calls_in_product_code_are_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
            product_file.parent.mkdir(parents=True)
            product_file.write_text(
                "upload_document(payload)\nsend_telemetry({'status': 'ok'})\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertGreaterEqual(
            sum(finding.rule == "upload or telemetry call" for finding in report.findings),
            2,
        )

    def test_cloud_ocr_provider_in_product_code_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "ocr.py"
            product_file.parent.mkdir(parents=True)
            product_file.write_text(
                "from google.cloud import vision\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(any("provider import" in finding.rule for finding in report.findings))

    def test_websocket_in_product_code_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "analysis.js"
            product_file.parent.mkdir(parents=True)
            product_file.write_text(
                "const channel = new WebSocket('wss://example.invalid');\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(any(finding.rule == "network client" for finding in report.findings))

    def test_network_dependency_in_manifest_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "package.json"
            manifest.write_text(
                '{"dependencies": {"axios": "1.0.0"}}\n',
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(any(finding.rule == "network dependency" for finding in report.findings))

    def test_remote_api_key_requirement_in_product_code_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
            product_file.parent.mkdir(parents=True)
            product_file.write_text(
                "import os\n\nkey = os.environ['OPENAI_API_KEY']\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(
            any(
                finding.rule == "remote credential/configuration dependency"
                for finding in report.findings
            )
        )

    def test_explicit_offline_blocker_in_product_code_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
            product_file.parent.mkdir(parents=True)
            product_file.write_text(
                "ERROR_MESSAGE = 'Requires network to analyze a notice'\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(any(finding.rule == "offline blocker" for finding in report.findings))

    def test_documentation_and_test_references_are_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            documentation = root / "docs" / "audit.md"
            test_file = root / "tests" / "test_fixture.py"
            documentation.parent.mkdir(parents=True)
            test_file.parent.mkdir(parents=True)
            documentation.write_text(
                "Reject https://example.invalid, remote uploads, and "
                "documentation that says requires network.\n",
                encoding="utf-8",
            )
            test_file.write_text(
                "import socket  # deliberate negative fixture\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertTrue(report.passed)
        self.assertGreaterEqual(report.context_hits["documentation"], 1)
        self.assertGreaterEqual(report.context_hits["test"], 1)


if __name__ == "__main__":
    unittest.main()
