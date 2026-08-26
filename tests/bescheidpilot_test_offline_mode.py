import os
import socket
import unittest
from dataclasses import asdict
from unittest.mock import patch

from bescheidpilot.core import local_analysis
from bescheidpilot.core.network_guard import NetworkAccessDenied, deny_network

REMOTE_CONFIGURATION_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "API_URL",
    "BASE_URL",
    "REMOTE_URL",
    "OCR_API_KEY",
)


class OfflineModeRealityTests(unittest.TestCase):
    def test_analysis_runs_offline_without_remote_configuration(self) -> None:
        environment = {
            key: value for key, value in os.environ.items() if key not in REMOTE_CONFIGURATION_KEYS
        }

        with patch.dict(os.environ, environment, clear=True), deny_network():
            result = local_analysis.analyze_local_text(
                "Synthetischer Bescheid.\n\nLokale Testanalyse."
            )

        self.assertTrue(result.has_content)
        self.assertEqual(result.execution_mode, "offline")
        self.assertFalse(result.network_required)

    def test_remote_configuration_values_are_not_consumed(self) -> None:
        remote_environment = {
            "OPENAI_API_KEY": "must-not-be-read",
            "ANTHROPIC_API_KEY": "must-not-be-read",
            "GEMINI_API_KEY": "must-not-be-read",
            "MISTRAL_API_KEY": "must-not-be-read",
            "GROQ_API_KEY": "must-not-be-read",
            "API_URL": "https://example.invalid/api",
            "BASE_URL": "https://example.invalid/base",
            "REMOTE_URL": "https://example.invalid/remote",
            "OCR_API_KEY": "must-not-be-read",
        }

        with patch.dict(os.environ, remote_environment, clear=True), deny_network():
            result = local_analysis.analyze_local_text("Lokaler Eingabetext")

        self.assertEqual(result.analysis_mode, "local-structure-baseline")
        self.assertEqual(result.execution_mode, "offline")
        self.assertFalse(result.network_required)

    def test_offline_result_contains_no_remote_configuration(self) -> None:
        with deny_network():
            result = local_analysis.analyze_local_text("Nur lokaler Text")

        serialized = repr(asdict(result))

        for key in REMOTE_CONFIGURATION_KEYS:
            self.assertNotIn(key, serialized)

    def test_offline_run_fails_closed_on_network_requirement(self) -> None:
        def network_required(_: str):
            socket.create_connection(("example.invalid", 443))

        with (
            patch(
                "bescheidpilot.core.local_analysis._analyze_structure",
                side_effect=network_required,
            ),
            deny_network(),
            self.assertRaises(NetworkAccessDenied),
        ):
            local_analysis.analyze_local_text("synthetic local input")


if __name__ == "__main__":
    unittest.main()
