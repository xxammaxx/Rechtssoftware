import http.client
import socket
import unittest
import urllib.request
from unittest.mock import patch

from bescheidpilot.core import local_analysis
from bescheidpilot.core.network_guard import NetworkAccessDenied, deny_network


class NetworkDenyGuardrailTests(unittest.TestCase):
    def test_local_analysis_completes_with_network_denied(self) -> None:
        text = "Bescheid vom 1. Juni 2026.\n\nBitte Unterlagen einreichen."

        with deny_network():
            result = local_analysis.analyze_local_text(text)

        self.assertEqual(result.analysis_mode, "local-structure-baseline")
        self.assertEqual(result.character_count, len(text))
        self.assertEqual(result.line_count, 3)
        self.assertEqual(result.paragraph_count, 2)
        self.assertTrue(result.has_content)

    def test_local_analysis_rejects_non_text_input(self) -> None:
        with self.assertRaises(TypeError):
            local_analysis.analyze_local_text(None)  # type: ignore[arg-type]

    def test_raw_socket_creation_is_denied(self) -> None:
        with deny_network(), self.assertRaises(NetworkAccessDenied):
            socket.socket()

    def test_socket_connection_is_denied(self) -> None:
        with deny_network(), self.assertRaises(NetworkAccessDenied):
            socket.create_connection(("example.invalid", 443))

    def test_dns_resolution_is_denied(self) -> None:
        with deny_network(), self.assertRaises(NetworkAccessDenied):
            socket.getaddrinfo("example.invalid", 443)

    def test_urllib_request_is_denied(self) -> None:
        with deny_network(), self.assertRaises(NetworkAccessDenied):
            urllib.request.urlopen("https://example.invalid", timeout=0.1)

    def test_http_connection_is_denied(self) -> None:
        connection = http.client.HTTPConnection("example.invalid")

        with deny_network(), self.assertRaises(NetworkAccessDenied):
            connection.connect()

    def test_https_connection_is_denied(self) -> None:
        connection = http.client.HTTPSConnection("example.invalid")

        with deny_network(), self.assertRaises(NetworkAccessDenied):
            connection.connect()

    def test_analysis_fails_if_internal_code_attempts_network(self) -> None:
        def network_attempt(_: str):
            socket.create_connection(("example.invalid", 443))

        with (
            patch(
                "bescheidpilot.core.local_analysis._analyze_structure",
                side_effect=network_attempt,
            ),
            deny_network(),
            self.assertRaises(NetworkAccessDenied),
        ):
            local_analysis.analyze_local_text("synthetic local input")


if __name__ == "__main__":
    unittest.main()
