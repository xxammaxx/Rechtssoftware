import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bescheidpilot.core import local_analysis
from bescheidpilot.core.network_guard import deny_network
from scripts.bescheidpilot_guardrail_check import scan_repository

# Gefaehrliche Remote-LLM Environment Variables (vollstaendige Denylist)
REMOTE_LLM_ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "COHERE_API_KEY",
    "PERPLEXITY_API_KEY",
    "TOGETHER_API_KEY",
    "HF_TOKEN",
    "HUGGINGFACE_API_TOKEN",
    "AZURE_OPENAI_API_KEY",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "BEDROCK_API_KEY",
    "LLM_API_KEY",
    "REMOTE_LLM_URL",
    "LLM_BASE_URL",
)

# Gefaehrliche Remote-LLM SDK-Module
REMOTE_LLM_MODULES = (
    "openai",
    "anthropic",
    "google.generativeai",
    "genai",
    "mistralai",
    "groq",
    "cohere",
    "huggingface_hub",
    "boto3",
)

# Gefaehrliche Import-Muster im Produktcode
REMOTE_LLM_IMPORT_PATTERNS = (
    "from openai",
    "import openai",
    "from anthropic",
    "import anthropic",
    "from google.generativeai",
    "import google.generativeai",
    "from mistralai",
    "import mistralai",
    "from groq",
    "import groq",
    "from cohere",
    "import cohere",
    "from huggingface_hub",
    "import huggingface_hub",
    "AzureOpenAI",
    "ChatOpenAI",
    "RemoteRunnable",
)


class NoRemoteLLMGuardrailTests(unittest.TestCase):
    """Guardrail: BescheidPilot darf keine sensiblen Bescheidinhalte an
    Remote-LLM-Provider senden."""

    # --- 1. Environment-Variable-Tests ---

    def test_local_analysis_runs_without_remote_llm_env_vars(self) -> None:
        """Lokale Analyse laeuft auch dann, wenn Remote-LLM-API-Keys fehlen."""
        environment = {
            key: value for key, value in os.environ.items() if key not in REMOTE_LLM_ENV_VARS
        }

        with patch.dict(os.environ, environment, clear=True), deny_network():
            result = local_analysis.analyze_local_text(
                "Synthetischer Bescheid fuer No-Remote-LLM-Test.\n\nBitte Unterlagen einreichen."
            )

        self.assertTrue(result.has_content)
        self.assertEqual(result.execution_mode, "offline")
        self.assertFalse(result.network_required)

    def test_remote_llm_env_vars_are_not_required(self) -> None:
        """Keine Remote-LLM-Environment-Variable ist fuer den lokalen
        Harness erforderlich."""
        for var in REMOTE_LLM_ENV_VARS:
            self.assertNotIn(
                var,
                os.environ,
                f"{var} sollte nicht gesetzt sein (lokaler Betrieb)",
            )

    # --- 2. API-Key-Unabhaengigkeit ---

    def test_analysis_completes_with_fake_remote_llm_keys_present(self) -> None:
        """Lokale Analyse ignoriert gesetzte Remote-LLM-API-Keys und laeuft
        weiterhin offline."""
        fake_remote_env = dict.fromkeys(
            REMOTE_LLM_ENV_VARS, "must-not-be-consumed-by-local-analysis"
        )

        with patch.dict(os.environ, fake_remote_env, clear=True), deny_network():
            result = local_analysis.analyze_local_text("Lokaler Bescheidtext")

        self.assertEqual(result.analysis_mode, "local-structure-baseline")
        self.assertEqual(result.execution_mode, "offline")
        self.assertFalse(result.network_required)

    def test_analysis_result_contains_no_remote_llm_configuration(self) -> None:
        """Das Analyse-Ergebnis enthaelt keine Remote-LLM-Konfiguration."""
        from dataclasses import asdict

        with deny_network():
            result = local_analysis.analyze_local_text("Nur lokaler Text")

        serialized = repr(asdict(result))

        for var in REMOTE_LLM_ENV_VARS:
            self.assertNotIn(var, serialized)

    # --- 3. Remote-Provider-Fixture-Blockierung (Guardrail-Scan) ---

    def test_remote_llm_provider_in_product_code_is_blocking(self) -> None:
        """Remote-LLM-SDK-Import in Produktcode wird als blockierend erkannt."""
        for module_name in REMOTE_LLM_MODULES:
            with (
                self.subTest(module=module_name),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(
                    f"import {module_name}\n\nclient = {module_name}.Client()\n",
                    encoding="utf-8",
                )

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    f"Expected scan to FAIL for remote LLM module: {module_name}",
                )
                self.assertTrue(
                    any("forbidden" in finding.rule.lower() for finding in report.findings),
                    f"No blocking finding for module: {module_name}",
                )

    def test_remote_llm_api_key_access_in_product_code_is_blocking(self) -> None:
        """Zugriff auf Remote-LLM-API-Keys im Produktcode wird blockiert."""
        api_key_access_patterns = [
            f'import os\n\nkey = os.environ["{var}"]\n' for var in REMOTE_LLM_ENV_VARS
        ]

        for pattern in api_key_access_patterns:
            with (
                self.subTest(pattern=pattern[:80]),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(pattern, encoding="utf-8")

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    "Expected scan to FAIL for API key access",
                )

    def test_remote_llm_base_url_in_product_code_is_blocking(self) -> None:
        """Remote-LLM-Base-URL im Produktcode wird blockiert."""
        base_url_patterns = [
            'LLM_BASE_URL = "https://api.openai.com/v1"\n',
            'REMOTE_LLM_URL = "https://api.anthropic.com"\n',
            'LLM_API_KEY = "sk-test"\n',
        ]

        for pattern in base_url_patterns:
            with (
                self.subTest(pattern=pattern.strip()),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(pattern, encoding="utf-8")

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    f"Expected scan to FAIL for remote LLM URL/key: {pattern.strip()[:60]}",
                )

    # --- 4. Remote-Fallback-Erkennung ---

    def test_llm_fallback_pattern_in_product_code_is_blocking(self) -> None:
        """Remote-LLM-Fallback-Konfiguration wird als Fehler erkannt."""
        fallback_patterns = [
            ("FALLBACK_PROVIDER = 'openai'\nPRIMARY_PROVIDER = 'local'\n"),
            (
                "import os\n\n"
                "if not os.environ.get('LOCAL_MODEL_PATH'):\n"
                "    import openai\n"
                "    client = openai.OpenAI()\n"
            ),
            (
                "REMOTE_LLM_FALLBACK = {\n"
                "    'primary': 'local',\n"
                "    'fallback': 'https://api.openai.com/v1'\n"
                "}\n"
            ),
        ]

        for pattern in fallback_patterns:
            with (
                self.subTest(pattern=pattern[:80]),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                product_file = root / "src" / "bescheidpilot" / "core" / "analysis.py"
                product_file.parent.mkdir(parents=True, exist_ok=True)
                product_file.write_text(pattern, encoding="utf-8")

                report = scan_repository(root)

                self.assertFalse(
                    report.passed,
                    "Expected scan to FAIL for LLM fallback pattern",
                )

    # --- 5. Produktcode-Scan auf aktive Remote-LLM-Imports ---

    def test_current_product_code_has_no_remote_llm_imports(self) -> None:
        """Der aktuelle Produktcode enthaelt keine aktiven Remote-LLM-SDK-Imports."""
        root = Path(__file__).resolve().parents[1]
        product_roots = {"src", "app", "lib", "packages", "crates"}

        for product_root in product_roots:
            product_dir = root / product_root
            if not product_dir.is_dir():
                continue
            for py_file in product_dir.rglob("*.py"):
                content = py_file.read_text(encoding="utf-8")
                for pattern in REMOTE_LLM_IMPORT_PATTERNS:
                    self.assertNotIn(
                        pattern,
                        content,
                        f"Remote LLM import '{pattern}' found in {py_file}",
                    )

    # --- 6. Sensible Textweitergabe-Pruefung ---

    def test_sensitive_bescheid_text_not_passed_to_remote_provider_functions(
        self,
    ) -> None:
        """Sensible Beispiel-Bescheidtexte werden nicht an Remote-Provider-
        Funktionen uebergeben."""

        sensitive_text = (
            "Bescheid vom 01.06.2026\n"
            "Aktenzeichen: 12345-ABC\n"
            "Sie werden aufgefordert, innerhalb von 14 Tagen\n"
            "Ihren Widerspruch zu begruenden.\n"
            "Bei Nichtbeachtung droht ein Versaeumnisurteil."
        )

        # Simuliere eine Remote-Provider-Funktion
        remote_call_log = []

        def fake_openai_completion(prompt: str) -> dict:
            remote_call_log.append(("openai", prompt))
            return {"response": "synthetic"}

        def fake_anthropic_message(prompt: str) -> dict:
            remote_call_log.append(("anthropic", prompt))
            return {"response": "synthetic"}

        # Der lokale Analysepfad MUSS ohne Remote-Provider auskommen
        with deny_network():
            result = local_analysis.analyze_local_text(sensitive_text)

        # Beweise: sensible Daten wurden NICHT an Remote-Funktionen uebergeben
        self.assertTrue(result.has_content)
        self.assertEqual(
            len(remote_call_log),
            0,
            "Sensible Bescheiddaten duerfen nicht an Remote-Provider uebergeben werden",
        )

    def test_analysis_without_network_never_calls_remote_llm(self) -> None:
        """Unter Network-Deny duerfen keinerlei Remote-LLM-Aufrufe
        stattfinden."""
        text = "Synthetischer Bescheid mit sensiblen Inhalten.\nFrist: 14 Tage."

        with deny_network():
            result = local_analysis.analyze_local_text(text)

        self.assertTrue(result.has_content)
        self.assertFalse(result.network_required)
        self.assertEqual(result.execution_mode, "offline")


class NoRemoteLLMStaticScanTests(unittest.TestCase):
    """Zusaetzliche statische Scan-Tests fuer Remote-LLM-Risiken."""

    def test_guardrail_scan_has_no_blocking_product_findings(self) -> None:
        """Der aktuelle Repository-Scan darf keine blockierenden
        Remote-LLM-Produktfunde enthalten."""
        root = Path(__file__).resolve().parents[1]
        report = scan_repository(root / "src")

        self.assertTrue(report.passed, f"Blockierende Produktfunde: {report.findings}")

    def test_missing_llm_providers_are_covered(self) -> None:
        """Prueft, dass die wichtigsten Remote-LLM-Provider in den
        Scan-Regeln enthalten sind."""
        required_providers = {
            "openai",
            "anthropic",
            "google.genai",
            "google.generativeai",
            "groq",
            "mistral",
            "mistralai",
            "cohere",
            "ollama",
        }

        from scripts.bescheidpilot_guardrail_check import REMOTE_PROVIDER_MODULES

        missing = required_providers - REMOTE_PROVIDER_MODULES
        self.assertEqual(
            len(missing),
            0,
            f"Folgende Provider fehlen in REMOTE_PROVIDER_MODULES: {missing}",
        )

    def test_missing_llm_env_vars_are_covered(self) -> None:
        """Prueft, dass die wichtigsten Remote-LLM-API-Key-Variablen in den
        Scan-Regeln enthalten sind."""
        required_env_vars = {
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "GROQ_API_KEY",
            "MISTRAL_API_KEY",
            "COHERE_API_KEY",
        }

        from scripts.bescheidpilot_guardrail_check import REMOTE_CONFIGURATION_KEYS

        missing = required_env_vars - REMOTE_CONFIGURATION_KEYS
        self.assertEqual(
            len(missing),
            0,
            f"Folgende Env-Vars fehlen in REMOTE_CONFIGURATION_KEYS: {missing}",
        )


if __name__ == "__main__":
    unittest.main()
