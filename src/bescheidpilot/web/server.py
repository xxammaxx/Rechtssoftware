"""Local-only Web Demo Shell for BescheidPilot text MVP.

Usage:
    python -m bescheidpilot.web.server

Starts on 127.0.0.1:8765 — never on 0.0.0.0.
No network, no upload, no cloud. Human review mandatory.
"""

from __future__ import annotations

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bescheidpilot.core import (
    analyze_bescheid_text,
    create_answer_draft,
    render_analysis_export,
)
from bescheidpilot.core.network_guard import deny_network

HOST = "127.0.0.1"
PORT = 8765
WEB_DIR = Path(__file__).resolve().parent
INDEX_PATH = WEB_DIR / "templates" / "index.html"

# Allowlisted demo fixtures — only these paths are readable via the demo endpoint.
# Keys are stable demo IDs, values are paths relative to the project root.
_FIXTURES_DIR = (WEB_DIR / ".." / ".." / ".." / "tests" / "fixtures" / "validation").resolve()
DEMO_FIXTURES: dict[str, Path] = {
    "jobcenter_mitwirkung": _FIXTURES_DIR / "validation_001_jobcenter_mitwirkung.txt",
    "anhoerung_stellungnahme": _FIXTURES_DIR / "validation_002_anhoerung_stellungnahme.txt",
    "sozialamt_nachforderung": _FIXTURES_DIR / "validation_004_sozialamt_unterlagen.txt",
    "inkasso_mahnung": _FIXTURES_DIR / "validation_006_inkasso_mahnung.txt",
    "aenderungsbescheid": _FIXTURES_DIR / "validation_007_rueckforderung.txt",
}

# Human-readable labels for demo fixture selection
DEMO_FIXTURE_LABELS: dict[str, str] = {
    "jobcenter_mitwirkung": "Jobcenter — Mitwirkung",
    "anhoerung_stellungnahme": "Anhörung — Stellungnahme",
    "sozialamt_nachforderung": "Sozialamt — Nachforderung",
    "inkasso_mahnung": "Inkasso — Mahnung",
    "aenderungsbescheid": "Änderungsbescheid",
}


class BescheidPilotHandler(SimpleHTTPRequestHandler):
    """Request handler that serves the demo page and analysis API."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Override to avoid logging sensitive data."""
        if "/analyze" in str(args):
            return  # don't log analysis requests with potential text
        super().log_message(format, *args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            self._serve_html()
        elif parsed.path == "/analyze":
            self._send_json({"error": "Use POST for analysis"})
        elif parsed.path == "/demo-fixtures":
            self._serve_fixture_list()
        elif parsed.path.startswith("/demo-fixture/"):
            fixture_id = parsed.path[len("/demo-fixture/") :].strip()
            self._serve_fixture(fixture_id)
        else:
            super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/analyze":
            self._handle_analyze()
        else:
            self._send_json({"error": "Not found"}, status=404)

    def _serve_html(self) -> None:
        try:
            content = INDEX_PATH.read_text(encoding="utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        except FileNotFoundError:
            self.send_error(404)

    def _serve_fixture_list(self) -> None:
        """Return the allowlisted demo fixture IDs and labels."""
        result = {
            fid: {"id": fid, "label": DEMO_FIXTURE_LABELS.get(fid, fid)} for fid in DEMO_FIXTURES
        }
        self._send_json(result)

    def _serve_fixture(self, fixture_id: str) -> None:
        """Serve a single allowlisted fixture. Rejects unknown or traversal IDs."""
        # Security: only exact allowlist match — no path traversal, no free paths.
        fixture_path = DEMO_FIXTURES.get(fixture_id)
        if fixture_path is None:
            self._send_json({"error": "Unknown fixture"}, status=404)
            return

        # Extra safety: resolve and verify the resolved path is still in the allowlist
        try:
            resolved = fixture_path.resolve()
        except Exception:
            self._send_json({"error": "Invalid fixture path"}, status=400)
            return

        allowed = {p.resolve() for p in DEMO_FIXTURES.values()}
        if resolved not in allowed:
            self._send_json({"error": "Fixture path not allowed"}, status=403)
            return

        if not resolved.is_file():
            self._send_json({"error": "Fixture file not found"}, status=404)
            return

        try:
            text = resolved.read_text(encoding="utf-8")
        except Exception:
            self._send_json({"error": "Cannot read fixture"}, status=500)
            return

        self._send_json({"id": fixture_id, "text": text})

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_analyze(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_json({"error": "Empty request"}, status=400)
            return

        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, status=400)
            return

        text = data.get("text", "").strip()
        include_draft = data.get("include_draft", False)

        if not text:
            self._send_json({"error": "No text provided"}, status=400)
            return

        try:
            with deny_network():
                result = analyze_bescheid_text(text)
        except Exception:
            self._send_json({"error": "Analysis failed"}, status=500)
            return

        # Build response
        response: dict[str, Any] = {
            "status": "requires_review" if result.review_required else "ok",
            "final_decision": result.final_decision,
            "review_required": result.review_required,
            "authority": result.authority,
            "document_type": result.document_type,
            "letter_date": result.letter_date,
            "deadline": result.deadline,
            "required_action": result.required_action,
            "missing_documents": result.missing_documents,
            "risk_level": result.risk_level,
            "review_items": [
                {
                    "field": ri.field,
                    "value": ri.value,
                    "status": ri.status,
                    "reason": ri.reason,
                    "severity": ri.severity,
                    "evidence_present": ri.evidence_present,
                }
                for ri in result.review_items
            ],
            "evidence": [
                {
                    "field": ev.field,
                    "value": ev.value,
                    "quote": ev.quote[:150],
                    "confidence": ev.confidence,
                }
                for ev in result.evidence
            ],
            "warnings": result.warnings,
        }

        export_result = result
        if include_draft:
            draft = create_answer_draft(result)
            from dataclasses import replace

            export_result = replace(result, answer_draft=draft)
            response["draft"] = {
                "title": draft.title,
                "body": draft.body,
                "status": draft.status,
                "requires_review": draft.requires_review,
                "final_decision": draft.final_decision,
                "warnings": draft.warnings,
            }

        response["export_text"] = render_analysis_export(export_result, include_draft=include_draft)

        self._send_json(response)


def run_server(host: str = HOST, port: int = PORT) -> None:
    """Start the local-only BescheidPilot web demo server."""
    server = HTTPServer((host, port), BescheidPilotHandler)
    print("=" * 60)
    print("BescheidPilot Web UI Demo")
    print(f"Server läuft lokal auf {host}:{port}")
    print("Der Bescheid verlässt das Gerät nicht.")
    print("Keine Uploads. Keine Cloud-KI. Keine Cloud-OCR.")
    print("=" * 60)
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="BescheidPilot Web UI Demo Server")
    parser.add_argument("--host", default=HOST, help=f"Bind address (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port (default: {PORT})")
    args = parser.parse_args(argv)

    if args.host != "127.0.0.1" and args.host != "localhost":
        print(
            "WARNUNG: Der Server sollte nur auf 127.0.0.1 oder localhost laufen.",
            file=sys.stderr,
        )

    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
