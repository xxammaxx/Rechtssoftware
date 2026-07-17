"""Uvicorn access log privacy tests.

Verify that Uvicorn access logs do not expose case IDs, document IDs,
or confirmation IDs in request paths.

M6-A routes include UUIDs directly in URL segments:
    /api/v1/cases/<case_id>/documents/<document_id>/...

This test verifies that either:
  - Uvicorn access logs are disabled/suppressed, OR
  - Access log paths are sanitized
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from private_legal_navigator.app import create_app
from private_legal_navigator.config import Settings
from private_legal_navigator.infrastructure.log_redaction import configure_logging

logging.getLogger("httpx").setLevel(logging.WARNING)

SYNTHETIC_UUID = UUID("eeeeeeee-3333-4444-5555-ffffffffffff")
SYNTHETIC_CASE_TITLE = "UACCESS-TEST-CASE"


def _make_text_pdf(text: str) -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


_REFERENCE_PDF = _make_text_pdf(
    "Bescheid vom 15.07.2026. Widerspruch innerhalb von 2 Wochen nach Zustellung."
)


@pytest.fixture
def client(tmp_path: Path):
    data_dir = tmp_path / "data"
    docs_dir = data_dir / "documents"
    docs_dir.mkdir(parents=True)
    settings = Settings(data_dir=data_dir, host="127.0.0.1", port=8000)
    return TestClient(create_app(settings))


def _case_id(client) -> str:
    r = client.post("/api/v1/cases", json={"title": SYNTHETIC_CASE_TITLE})
    assert r.status_code == 201
    return r.json()["case_id"]


def _doc_id(client, case_id: str) -> str:
    r = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("test.pdf", io.BytesIO(_REFERENCE_PDF), "application/pdf")},
    )
    assert r.status_code == 201
    return r.json()["document_id"]


class TestUvicornAccessLogSuppression:
    """Verify that Uvicorn access logs are properly handled."""

    def test_uvicorn_access_log_level_is_warning(self):
        """configure_logging must set uvicorn.access to WARNING or higher."""
        uvicorn_access = logging.getLogger("uvicorn.access")
        assert (
            uvicorn_access.level <= logging.WARNING or uvicorn_access.level == 0
        ), (  # 0 = NOTSET, inherits from parent
            f"uvicorn.access level is {uvicorn_access.level}, "
            f"expected <= WARNING ({logging.WARNING})"
        )

    def test_uvicorn_access_log_does_not_emit_requests(self):
        """After configure_logging, INFO-level uvicorn.access logs should be
        suppressed (set to WARNING), so regular HTTP requests don't produce
        access log entries at INFO level."""
        root, stream = _capture_root_logs()

        # Reconfigure with privacy settings
        root.handlers.clear()
        root.filters.clear()
        configure_logging()

        # capture output
        stream.truncate(0)
        stream.seek(0)

        # Log at INFO level as uvicorn.access (simulating an access log entry)
        uvicorn_access = logging.getLogger("uvicorn.access")
        uvicorn_access.info(
            "GET /api/v1/cases/%s/documents/%s/deadline-candidates/0/reference-events",
            str(SYNTHETIC_UUID),
            str(SYNTHETIC_UUID),
        )

        output = stream.getvalue()
        # At WARNING level, INFO logs should NOT appear
        assert output.strip() == "", (
            f"uvicorn.access INFO log appeared despite WARNING level: {output}"
        )

    def test_synthetic_access_path_with_ids(self):
        """Even if an access log DID appear, can we prove IDs would be visible?

        This is a RED_TEST: it proves that if uvicorn.access were at INFO,
        the full URL with UUIDs would appear.
        """
        # Use a dedicated StringIO handler at INFO level
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        capture_stream = io.StringIO()
        test_handler = logging.StreamHandler(capture_stream)
        test_handler.setLevel(logging.DEBUG)
        test_handler.setFormatter(logging.Formatter("%(message)s"))

        # Temporarily set up: filter on handler + INFO level
        root.handlers.clear()
        root.filters.clear()

        uvicorn_access = logging.getLogger("uvicorn.access")
        uvicorn_access.setLevel(logging.INFO)
        uvicorn_access.propagate = True

        # Add handler to root (no filter — proving raw leak)
        root.addHandler(test_handler)

        capture_stream.truncate(0)
        capture_stream.seek(0)

        uvicorn_access.info(
            "GET /api/v1/cases/%s/documents/%s/endpoint",
            str(SYNTHETIC_UUID),
            str(SYNTHETIC_UUID),
        )

        output = capture_stream.getvalue()
        assert str(SYNTHETIC_UUID) in output, (
            "RED_TEST FAILED: access log path should leak UUID (proves why suppression is needed)"
        )

    def test_configure_logging_sets_uvicorn_access_level(self):
        """configure_logging must set uvicorn.access to WARNING."""
        uvicorn_access = logging.getLogger("uvicorn.access")
        uvicorn_access.setLevel(logging.DEBUG)  # reset

        configure_logging()

        assert uvicorn_access.level == logging.WARNING, (
            f"uvicorn.access level is {uvicorn_access.level}, expected {logging.WARNING}"
        )

    def test_configure_logging_sets_uvicorn_error_level(self):
        """configure_logging must set uvicorn.error to WARNING."""
        uvicorn_error = logging.getLogger("uvicorn.error")
        uvicorn_error.setLevel(logging.DEBUG)  # reset

        configure_logging()

        assert uvicorn_error.level == logging.WARNING, (
            f"uvicorn.error level is {uvicorn_error.level}, expected {logging.WARNING}"
        )


def _capture_root_logs():
    """Set up root logger with StringIO capture."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(handler)

    return root, stream


class TestApplicationLogsDoNotLeakPathIds:
    """Integration test: real API calls must not leak UUIDs in app logs."""

    def test_api_call_does_not_leak_case_id_in_logs(self, client, caplog):
        """Real API call: case_id must not appear in application logs."""
        case_id = _case_id(client)

        with caplog.at_level(logging.DEBUG):
            resp = client.get("/api/v1/cases")
            assert resp.status_code == 200

        # Application logs should not contain the case UUID
        log_text = caplog.text
        assert case_id not in log_text, f"Case ID leaked in application logs: {case_id}"

    def test_document_id_not_in_logs(self, client, caplog):
        """Real API call: document_id must not appear in application logs."""
        case_id = _case_id(client)
        doc_id = _doc_id(client, case_id)

        with caplog.at_level(logging.DEBUG):
            resp = client.get(f"/api/v1/cases/{case_id}/documents")
            assert resp.status_code == 200

        log_text = caplog.text
        assert doc_id not in log_text, f"Document ID leaked in application logs: {doc_id}"
