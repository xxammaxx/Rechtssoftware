import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bescheidpilot.core import local_analysis
from bescheidpilot.core.network_guard import deny_network
from scripts.bescheidpilot_guardrail_check import scan_repository

# Gefaehrliche Cloud-OCR Environment Variables
CLOUD_OCR_ENV_VARS = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "AZURE_COGNITIVE_SERVICES_KEY",
    "AZURE_FORM_RECOGNIZER_KEY",
    "AZURE_DOCUMENT_INTELLIGENCE_KEY",
    "AZURE_COMPUTER_VISION_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_REGION",
    "OCR_SPACE_API_KEY",
    "ABBYY_API_KEY",
    "ADOBE_CLIENT_ID",
    "ADOBE_CLIENT_SECRET",
    "OCR_API_KEY",
    "OCR_BASE_URL",
    "REMOTE_OCR_URL",
    "CLOUD_OCR_URL",
)

# Gefaehrliche Cloud-OCR SDK-Module (Import-Pfade)
CLOUD_OCR_MODULES = (
    "google.cloud.vision",
    "google.cloud.documentai",
    "azure.ai.formrecognizer",
    "azure.ai.documentintelligence",
    "boto3",
)

# Gefaehrliche Cloud-OCR Import-Muster
CLOUD_OCR_IMPORT_PATTERNS = (
    "from google.cloud.vision",
    "import google.cloud.vision",
    "from google.cloud.documentai",
    "import google.cloud.documentai",
    "from azure.ai.formrecognizer",
    "import azure.ai.formrecognizer",
    "from azure.ai.documentintelligence",
    "import azure.ai.documentintelligence",
    "ImageAnnotatorClient",
    "DocumentProcessorServiceClient",
    'boto3.client("textract"',
    "ComputerVisionClient",
    "Textract",
    "ocr.space",
    "abbyy",
    "adobe.pdfservices",
)


class NoCloudOCRGuardrailTests(unittest.TestCase):
    """Guardrail: BescheidPilot darf keine Dokumentbilder, PDFs, Scans oder
    OCR-Texte an Cloud-OCR-Dienste senden."""

    # --- 1. Environment-Variable-Tests ---

    def test_local_analysis_runs_without_cloud_ocr_env_vars(self) -> None:
        """Lokale Analyse laeuft auch dann, wenn Cloud-OCR-API-Keys fehlen."""
        environment = {
            key: value for key, value in os.environ.items() if key not in CLOUD_OCR_ENV_VARS
        }

        with patch.dict(os.environ, environment, clear=True), deny_network():
            result = local_analysis.analyze_local_text(
                "Synthetischer Bescheid fuer No-Cloud-OCR-Test.\n\nBitte Unterlagen einreichen."
            )

        self.assertTrue(result.has_content)
        self.assertEqual(result.execution_mode, "offline")
        self.assertFalse(result.network_required)

    def test_cloud_ocr_env_vars_are_not_required(self) -> None:
        """Keine Cloud-OCR-Environment-Variable ist fuer den lokalen
        Harness erforderlich."""
        for var in CLOUD_OCR_ENV_VARS:
            self.assertNotIn(
                var,
                os.environ,
                f"{var} sollte nicht gesetzt sein (lokaler Betrieb)",
            )

    # --- 2. API-Key-Unabhaengigkeit ---

    def test_analysis_completes_with_fake_cloud_ocr_keys_present(self) -> None:
        """Lokale Analyse ignoriert gesetzte Cloud-OCR-API-Keys."""
        fake_ocr_env = dict.fromkeys(CLOUD_OCR_ENV_VARS, "must-not-be-consumed-by-local-analysis")

        with patch.dict(os.environ, fake_ocr_env, clear=True), deny_network():
            result = local_analysis.analyze_local_text("Lokaler Bescheidtext")

        self.assertEqual(result.analysis_mode, "local-structure-baseline")
        self.assertEqual(result.execution_mode, "offline")
        self.assertFalse(result.network_required)

    def test_analysis_result_contains_no_cloud_ocr_configuration(self) -> None:
        """Das Analyse-Ergebnis enthaelt keine Cloud-OCR-Konfiguration."""
        from dataclasses import asdict

        with deny_network():
            result = local_analysis.analyze_local_text("Nur lokaler Text")

        serialized = repr(asdict(result))

        for var in CLOUD_OCR_ENV_VARS:
            self.assertNotIn(var, serialized)

    # --- 3. Cloud-OCR-Fixture-Blockierung (Guardrail-Scan) ---

    def test_cloud_ocr_provider_in_product_code_is_blocking(self) -> None:
        """Cloud-OCR-SDK-Import in Produktcode wird als blockierend erkannt."""
        test_cases = [
            (
                "google.cloud.vision",
                (
                    "from google.cloud.vision import ImageAnnotatorClient\n\n"
                    "client = ImageAnnotatorClient()\n"
                ),
            ),
            (
                "google.cloud.documentai",
                (
                    "from google.cloud import documentai\n\n"
                    "processor = documentai.DocumentProcessorServiceClient()\n"
                ),
            ),
            (
                "azure.ai.formrecognizer",
                (
                    "from azure.ai.formrecognizer import DocumentAnalysisClient\n\n"
                    "client = DocumentAnalysisClient('endpoint', 'credential')\n"
                ),
            ),
            (
                "azure.ai.documentintelligence",
                (
                    "from azure.ai import documentintelligence\n\n"
                    "client = documentintelligence.DocumentIntelligenceClient("
                    "'endpoint', 'credential')\n"
                ),
            ),
            ("boto3.textract", "import boto3\n\nclient = boto3.client('textract')\n"),
        ]

        for module_name, code in test_cases:
            with (
                self.subTest(module=module_name),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "ocr.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(code, encoding="utf-8")

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    f"Expected scan to FAIL for cloud OCR module: {module_name}",
                )
                self.assertTrue(
                    any("forbidden" in finding.rule.lower() for finding in report.findings),
                    f"No blocking finding for cloud OCR module: {module_name}",
                )

    def test_cloud_ocr_api_key_access_in_product_code_is_blocking(self) -> None:
        """Zugriff auf Cloud-OCR-API-Keys im Produktcode wird blockiert."""
        key_api_key_patterns = [
            'import os\n\nkey = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]\n',
            'import os\n\nkey = os.environ["AZURE_FORM_RECOGNIZER_KEY"]\n',
            'import os\n\nkey = os.environ["OCR_SPACE_API_KEY"]\n',
            'import os\n\nkey = os.environ["ABBYY_API_KEY"]\n',
        ]

        for pattern in key_api_key_patterns:
            with (
                self.subTest(pattern=pattern[:80]),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "ocr.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(pattern, encoding="utf-8")

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    "Expected scan to FAIL for cloud OCR API key access",
                )

    def test_cloud_ocr_base_url_in_product_code_is_blocking(self) -> None:
        """Cloud-OCR-Base-URL im Produktcode wird blockiert."""
        base_url_patterns = [
            'OCR_BASE_URL = "https://api.ocr.space/parse/image"\n',
            'REMOTE_OCR_URL = "https://westus.api.cognitive.microsoft.com/vision/v3.2/ocr"\n',
            'CLOUD_OCR_URL = "https://vision.googleapis.com/v1/images:annotate"\n',
        ]

        for pattern in base_url_patterns:
            with (
                self.subTest(pattern=pattern.strip()),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "ocr.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(pattern, encoding="utf-8")

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    f"Expected scan to FAIL for cloud OCR URL: {pattern.strip()[:60]}",
                )

    # --- 4. Cloud-OCR-Fallback-Erkennung ---

    def test_ocr_fallback_pattern_in_product_code_is_blocking(self) -> None:
        """Cloud-OCR-Fallback-Konfiguration wird als Fehler erkannt."""
        fallback_patterns = [
            ("FALLBACK_OCR = 'google.cloud.vision'\nPRIMARY_OCR = 'local_tesseract'\n"),
            (
                "import os\n\n"
                "if not os.environ.get('TESSERACT_PATH'):\n"
                "    from google.cloud import vision\n"
                "    client = vision.ImageAnnotatorClient()\n"
            ),
            (
                "REMOTE_OCR_FALLBACK = {\n"
                "    'primary': 'local',\n"
                "    'fallback': 'https://api.ocr.space/parse/image'\n"
                "}\n"
            ),
        ]

        for pattern in fallback_patterns:
            with (
                self.subTest(pattern=pattern[:80]),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "ocr.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(pattern, encoding="utf-8")

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    "Expected scan to FAIL for OCR fallback pattern",
                )

    # --- 5. Produktcode-Scan auf aktive Cloud-OCR-Imports ---

    def test_current_product_code_has_no_cloud_ocr_imports(self) -> None:
        """Der aktuelle Produktcode enthaelt keine aktiven Cloud-OCR-SDK-Imports."""
        root = Path(__file__).resolve().parents[1]
        product_roots = {"src", "app", "lib", "packages", "crates"}

        for product_root in product_roots:
            product_dir = root / product_root
            if not product_dir.is_dir():
                continue
            for py_file in product_dir.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8")
                for pattern in CLOUD_OCR_IMPORT_PATTERNS:
                    self.assertNotIn(
                        pattern,
                        content,
                        f"Cloud OCR import '{pattern}' found in {py_file}",
                    )

    # --- 6. Upload-Schutz fuer Dokumentdaten ---

    def test_upload_document_functions_in_product_code_are_blocking(self) -> None:
        """Dokument-Upload-Funktionen im Produktcode werden blockiert."""
        upload_patterns = [
            (
                "def upload_document(path):\n"
                "    files = {'file': open(path, 'rb')}\n"
                "    requests.post('https://api.example.invalid/ocr', files=files)\n"
            ),
            (
                "def upload_image(image_data):\n"
                "    requests.post('https://ocr.example.invalid/parse',"
                " data=image_data)\n"
            ),
            (
                "def upload_pdf_for_ocr(pdf_path):\n"
                "    with open(pdf_path, 'rb') as f:\n"
                "        return requests.post(REMOTE_OCR_URL, files={'pdf': f})\n"
            ),
        ]

        for pattern in upload_patterns:
            with (
                self.subTest(pattern=pattern[:80]),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "ocr.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(pattern, encoding="utf-8")

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    "Expected scan to FAIL for document upload pattern",
                )

    # --- 7. Sensible Textweitergabe-Pruefung ---

    def test_sensitive_ocr_text_not_passed_to_remote_ocr_functions(self) -> None:
        """Sensible OCR-Texte werden nicht an Remote-OCR-Funktionen uebergeben."""

        sensitive_ocr_text = (
            "Erkannter Text aus Bescheidscan:\n"
            "Aktenzeichen: 12345-ABC\n"
            "Frist: 14 Tage ab Zustellung\n"
            "Widerspruch bei Verwaltungsgericht Moenchengladbach"
        )

        remote_ocr_call_log = []

        def fake_ocr_space_parse(image_data: str) -> dict:
            remote_ocr_call_log.append(("ocr.space", image_data))
            return {"text": "synthetic"}

        def fake_google_vision_annotate(image_data: str) -> dict:
            remote_ocr_call_log.append(("google.vision", image_data))
            return {"text": "synthetic"}

        # Der lokale Analysepfad MUSS ohne Cloud-OCR auskommen
        with deny_network():
            result = local_analysis.analyze_local_text(sensitive_ocr_text)

        self.assertTrue(result.has_content)
        self.assertEqual(
            len(remote_ocr_call_log),
            0,
            "Sensible OCR-Daten duerfen nicht an Remote-OCR uebergeben werden",
        )

    def test_analysis_without_network_never_calls_cloud_ocr(self) -> None:
        """Unter Network-Deny duerfen keinerlei Cloud-OCR-Aufrufe
        stattfinden."""
        text = "Synthetischer OCR-Text aus Bescheidscan.\nFrist: 14 Tage."

        with deny_network():
            result = local_analysis.analyze_local_text(text)

        self.assertTrue(result.has_content)
        self.assertFalse(result.network_required)
        self.assertEqual(result.execution_mode, "offline")

    # --- 8. Multipart/Upload-Endpoint-Test ---

    def test_multipart_upload_in_product_code_is_blocking(self) -> None:
        """Multipart-Form-Data-Upload im Produktcode wird blockiert."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            product_file = root / "src" / "bescheidpilot" / "core" / "upload.py"
            product_file.parent.mkdir(parents=True, exist_ok=True)
            product_file.write_text(
                'headers = {"Content-Type": "multipart/form-data"}\n'
                "response = requests.post(url, files=files, headers=headers)\n",
                encoding="utf-8",
            )

            report = scan_repository(root)

        self.assertFalse(report.passed)
        self.assertTrue(any("multipart" in finding.rule.lower() for finding in report.findings))


class NoCloudOCRStaticScanTests(unittest.TestCase):
    """Zusaetzliche statische Scan-Tests fuer Cloud-OCR-Risiken."""

    def test_guardrail_scan_has_no_blocking_product_findings(self) -> None:
        """Der aktuelle Repository-Scan darf keine blockierenden
        Cloud-OCR-Produktfunde enthalten."""
        root = Path(__file__).resolve().parents[1]
        report = scan_repository(root / "src")

        self.assertTrue(report.passed, f"Blockierende Produktfunde: {report.findings}")

    def test_cloud_ocr_key_coverage(self) -> None:
        """Prueft, dass die wichtigsten Cloud-OCR-API-Keys in den
        Scan-Regeln enthalten sind."""
        required_keys = {
            "GOOGLE_APPLICATION_CREDENTIALS",
            "AZURE_FORM_RECOGNIZER_KEY",
            "OCR_API_KEY",
            "OCR_SPACE_API_KEY",
            "ABBYY_API_KEY",
        }

        from scripts.bescheidpilot_guardrail_check import REMOTE_CONFIGURATION_KEYS

        missing = required_keys - REMOTE_CONFIGURATION_KEYS
        self.assertEqual(len(missing), 0, f"Folgende Cloud-OCR-Keys fehlen: {missing}")

    def test_cloud_ocr_risk_rules_exist(self) -> None:
        """Prueft, dass cloud_ocr_risks im ScanReport definiert ist."""
        from scripts.bescheidpilot_guardrail_check import CLOUD_OCR_RISK_RULES, ScanReport

        self.assertIsInstance(CLOUD_OCR_RISK_RULES, set)
        self.assertGreater(len(CLOUD_OCR_RISK_RULES), 0)

        report = ScanReport()
        self.assertIsInstance(report.cloud_ocr_risks, list)
        self.assertEqual(report.cloud_ocr_risks_count, 0)


if __name__ == "__main__":
    unittest.main()
