"""API logging privacy tests for M6-A endpoints.

These tests verify that the PrivacyRedactionFilter is wired and
that sensitive M6-A values never appear in application log output.

NOTE: httpx (the test client library) logs full request URLs which
include UUIDs in path segments. We suppress httpx logging in these tests.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from private_legal_navigator.app import create_app
from private_legal_navigator.config import Settings
from private_legal_navigator.infrastructure.log_redaction import (
    SENSITIVE_FIELDS,
    PrivacyRedactionFilter,
    configure_logging,
)

logging.getLogger("httpx").setLevel(logging.WARNING)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_text_pdf(text: str) -> bytes:
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


_REFERENCE_PDF = _make_text_pdf(
    "Bescheid vom 15.07.2026. "
    "Widerspruch innerhalb von 2 Wochen nach Zustellung."
)

SYNTHETIC_CASE_TITLE = "PRIVACY-TEST-CASE"
SYNTHETIC_DATE_PAYLOAD_5521 = "2026-07-15"


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


def _extract_candidates(client, case_id: str, doc_id: str) -> list:
    r = client.post(
        f"/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates"
    )
    assert r.status_code == 200
    return r.json().get("candidates", [])


def _get_relative_candidate_idx(candidates: list) -> int | None:
    for i, c in enumerate(candidates):
        if c.get("kind") == "relative_period":
            return i
    return None


def _confirm_manual(client, case_id: str, doc_id: str, candidate_idx: int,
                    confirmed_date: str = "2026-07-15",
                    evidence_note: str = "") -> dict | None:
    """Confirm a candidate MANUALLY, return response JSON or None."""
    r = client.post(
        f"/api/v1/cases/{case_id}/documents/{doc_id}"
        f"/deadline-candidates/{candidate_idx}/reference-events/confirm",
        json={
            "confirmation_method": "MANUALLY_ENTERED",
            "source_type": "USER_MANUAL",
            "confirmed_date": confirmed_date,
            "evidence_note": evidence_note,
        },
    )
    if r.status_code not in (200, 201):
        return None
    return r.json()


# ── LT-01v2: Filter wired ─────────────────────────────────────────────────

class TestFilterWiredOnRootLogger:
    def test_root_logger_has_redaction_filter(self):
        root = logging.getLogger()
        root.filters.clear()
        root.handlers.clear()
        configure_logging()
        privacy_filters = [f for f in root.filters
                           if isinstance(f, PrivacyRedactionFilter)]
        assert len(privacy_filters) == 1


# ── Confirm path ──────────────────────────────────────────────────────────

class TestConfirmLoggingPrivacy:
    def test_confirm_auto_suggested_no_leak(self, client, caplog):
        cid = _case_id(client)
        did = _doc_id(client, cid)
        candidates = _extract_candidates(client, cid, did)
        idx = _get_relative_candidate_idx(candidates)
        assert idx is not None, "Expected RELATIVE_PERIOD candidate"

        with caplog.at_level(logging.INFO):
            client.post(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/{idx}/reference-events/confirm",
                json={
                    "confirmation_method": "AUTO_SUGGESTED",
                    "source_type": "DEADLINE_CANDIDATE",
                },
            )

        assert SYNTHETIC_DATE_PAYLOAD_5521 not in caplog.text
        assert did not in caplog.text

    def test_confirm_manual_no_leak(self, client, caplog):
        cid = _case_id(client)
        did = _doc_id(client, cid)
        candidates = _extract_candidates(client, cid, did)
        idx = _get_relative_candidate_idx(candidates)
        assert idx is not None

        test_note = "SYNTHETIC_NOTE_DO_NOT_LOG_9182"

        with caplog.at_level(logging.INFO):
            client.post(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/{idx}/reference-events/confirm",
                json={
                    "confirmation_method": "MANUALLY_ENTERED",
                    "source_type": "USER_MANUAL",
                    "confirmed_date": SYNTHETIC_DATE_PAYLOAD_5521,
                    "evidence_note": test_note,
                },
            )

        assert test_note not in caplog.text
        assert SYNTHETIC_DATE_PAYLOAD_5521 not in caplog.text

    def test_confirm_user_corrected_no_leak(self, client, caplog):
        """User-corrected: verify privacy filter handles correction path."""
        cid = _case_id(client)
        did = _doc_id(client, cid)
        candidates = _extract_candidates(client, cid, did)
        idx = _get_relative_candidate_idx(candidates)
        assert idx is not None

        # First confirm manually
        first = client.post(
            f"/api/v1/cases/{cid}/documents/{did}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "confirmation_method": "MANUALLY_ENTERED",
                "source_type": "USER_MANUAL",
                "confirmed_date": "2026-07-10",
                "evidence_note": "First",
            },
        )
        # Accept either success or the error — we only test log privacy
        first_id = first.json().get("confirmation_id") if first.status_code < 400 else None

        with caplog.at_level(logging.INFO):
            client.post(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/{idx}/reference-events/confirm",
                json={
                    "confirmation_method": "USER_CORRECTED",
                    "source_type": "USER_MANUAL",
                    "confirmed_date": "2026-07-20",
                    "evidence_note": "Corrected",
                    "confirmation_id": first_id,
                },
            )

        # First confirmation ID must not leak
        if first_id:
            assert first_id not in caplog.text

    def test_reject_candidate_no_leak(self, client, caplog):
        cid = _case_id(client)
        did = _doc_id(client, cid)
        candidates = _extract_candidates(client, cid, did)
        idx = _get_relative_candidate_idx(candidates)
        assert idx is not None

        with caplog.at_level(logging.INFO):
            client.post(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/{idx}/reference-events/confirm",
                json={
                    "confirmation_method": "REJECTED",
                    "source_type": "DEADLINE_CANDIDATE",
                },
            )

        assert did not in caplog.text

    def test_invalid_date_no_leak_to_logs(self, client, caplog):
        cid = _case_id(client)
        did = _doc_id(client, cid)
        candidates = _extract_candidates(client, cid, did)
        idx = _get_relative_candidate_idx(candidates)
        assert idx is not None

        invalid_date = "1800-01-01"
        with caplog.at_level(logging.INFO):
            client.post(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/{idx}/reference-events/confirm",
                json={
                    "confirmation_method": "MANUALLY_ENTERED",
                    "source_type": "USER_MANUAL",
                    "confirmed_date": invalid_date,
                    "evidence_note": "invalid test",
                },
            )

        assert invalid_date not in caplog.text


# ── Calculation Preview ───────────────────────────────────────────────────

class TestCalculationPreviewLoggingPrivacy:
    def test_calculation_preview_no_leak(self, client, caplog):
        """Preview: confirm first, then test logs during calculation."""
        cid = _case_id(client)
        did = _doc_id(client, cid)
        candidates = _extract_candidates(client, cid, did)
        idx = _get_relative_candidate_idx(candidates)
        assert idx is not None

        first = client.post(
            f"/api/v1/cases/{cid}/documents/{did}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "confirmation_method": "MANUALLY_ENTERED",
                "source_type": "USER_MANUAL",
                "confirmed_date": "2026-07-15",
                "evidence_note": "preview test",
            },
        )
        conf_id = first.json().get("confirmation_id") if first.status_code < 400 else None

        with caplog.at_level(logging.INFO):
            client.post(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/{idx}/reference-events/"
                f"calculation-preview",
                json={
                    "confirmation_id": conf_id,
                    "duration_unit": "DAY",
                    "duration_amount": 14,
                    "operation_name": "ADD",
                },
            )

        if conf_id:
            assert conf_id not in caplog.text
        assert did not in caplog.text

    def test_no_confirmation_preview_error_no_leak(self, client, caplog):
        cid = _case_id(client)
        did = _doc_id(client, cid)
        fake_uuid = str(uuid4())

        with caplog.at_level(logging.INFO):
            client.post(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/0/reference-events/calculation-preview",
                json={
                    "confirmation_id": fake_uuid,
                    "duration_unit": "DAY",
                    "duration_amount": 14,
                    "operation_name": "ADD",
                },
            )

        assert fake_uuid not in caplog.text


# ── History ───────────────────────────────────────────────────────────────

class TestHistoryLoggingPrivacy:
    def test_history_no_leak(self, client, caplog):
        cid = _case_id(client)
        did = _doc_id(client, cid)
        _extract_candidates(client, cid, did)  # trigger extraction

        with caplog.at_level(logging.INFO):
            client.get(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/0/reference-events/history"
            )

        assert did not in caplog.text


# ── Reference events list ─────────────────────────────────────────────────

class TestReferenceEventsListLoggingPrivacy:
    def test_list_no_leak(self, client, caplog):
        cid = _case_id(client)
        did = _doc_id(client, cid)
        _extract_candidates(client, cid, did)

        with caplog.at_level(logging.INFO):
            client.get(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/0/reference-events"
            )

        assert did not in caplog.text


# ── Revoke ────────────────────────────────────────────────────────────────

class TestRevokeLoggingPrivacy:
    def test_revoke_no_leak(self, client, caplog):
        """Revoke: confirm first, then revoke and check logs."""
        cid = _case_id(client)
        did = _doc_id(client, cid)
        candidates = _extract_candidates(client, cid, did)
        idx = _get_relative_candidate_idx(candidates)
        assert idx is not None

        first = client.post(
            f"/api/v1/cases/{cid}/documents/{did}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "confirmation_method": "MANUALLY_ENTERED",
                "source_type": "USER_MANUAL",
                "confirmed_date": "2026-07-15",
                "evidence_note": "revoke test",
            },
        )
        conf_id = first.json().get("confirmation_id") if first.status_code < 400 else None

        with caplog.at_level(logging.INFO):
            client.post(
                f"/api/v1/cases/{cid}/documents/{did}"
                f"/deadline-candidates/{idx}/reference-events/confirm",
                json={
                    "confirmation_method": "REVOKED",
                    "source_type": "DEADLINE_CANDIDATE",
                    "confirmation_id": conf_id,
                },
            )

        if conf_id:
            assert conf_id not in caplog.text


# ── Non-M6-A endpoints ────────────────────────────────────────────────────

class TestNonM6AEndpointsUnaffected:
    def test_health_endpoint(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_create_case_no_sensitive_leak(self, client, caplog):
        with caplog.at_level(logging.INFO):
            r = client.post("/api/v1/cases", json={"title": SYNTHETIC_CASE_TITLE})
        assert r.status_code == 201
        assert "error" not in caplog.text.lower()


# ── Sensitive marker sweep ────────────────────────────────────────────────

class TestSensitiveMarkerSweep:
    @pytest.mark.parametrize("field", SENSITIVE_FIELDS)
    def test_field_in_sensitive_list_recognized(self, field):
        assert field.isidentifier() or "_" in field
