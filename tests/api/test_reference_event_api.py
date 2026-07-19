"""Integration tests for M6-A Reference Events and Calendar Arithmetic API.

SYNTHETISCH – KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient

from private_legal_navigator.app import create_app
from private_legal_navigator.config import Settings


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temporary data directory and database."""
    data_dir = tmp_path / "data"
    docs_dir = data_dir / "documents"
    docs_dir.mkdir(parents=True)

    settings = Settings(
        data_dir=data_dir,
        host="127.0.0.1",
        port=8000,
    )
    app = create_app(settings)
    return TestClient(app)


@pytest.fixture
def case_id(client):
    """Create a test case and return its ID."""
    resp = client.post(
        "/api/v1/cases",
        json={"title": "SYNTHETISCH – M6-A Test Case"},
    )
    assert resp.status_code == 201
    return resp.json()["case_id"]


@pytest.fixture
def document_id(client, case_id):
    """Upload a PDF and return its document ID."""
    pdf_content = b"%PDF-1.4 SYNTHETISCH - Test PDF content"
    resp = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("test.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert resp.status_code == 201
    return resp.json()["document_id"]


# ── Reference Event Candidates ──


class TestListReferenceEvents:
    """GET /reference-events endpoint tests."""

    def test_no_reference_events_returns_empty(self, client, case_id, document_id):
        """TV-058: Empty reference events returns 200 with empty array."""
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reference_events" in data
        assert isinstance(data["reference_events"], list)
        assert "human_review_required" in data
        assert data["human_review_required"] is True

    def test_case_not_found(self, client, document_id):
        """404 when case does not exist."""
        fake_id = uuid.uuid4()
        resp = client.get(
            f"/api/v1/cases/{fake_id}/documents/{document_id}/deadline-candidates/0/reference-events"
        )
        assert resp.status_code == 404

    def test_document_not_found(self, client, case_id):
        """404 when document does not exist."""
        fake_id = uuid.uuid4()
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{fake_id}/deadline-candidates/0/reference-events"
        )
        assert resp.status_code == 404


# ── Confirm/Reject/Revoke ──


class TestConfirmReferenceEvent:
    """POST /reference-events/confirm endpoint tests."""

    def test_confirm_auto_suggested(self, client, case_id, document_id):
        """TV-003, TV-060: Confirm auto-suggested candidate."""
        candidate_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={
                "action": "confirm",
                "candidate_id": str(candidate_id),
                "event_type": "issue_date",
                "confirmed_date": "2026-07-15",
                "source_type": "auto_detected",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confirmation_id" in data
        assert data["human_review_required"] is True

    def test_confirm_manual_entry(self, client, case_id, document_id):
        """TV-051, TV-061: Manual entry without candidate_id."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "user_defined",
                "confirmed_date": "2026-07-15",
                "source_type": "user_manual",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["human_review_required"] is True

    def test_confirm_missing_date(self, client, case_id, document_id):
        """400 when confirmed_date is missing."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "source_type": "auto_detected",
            },
        )
        assert resp.status_code == 400

    def test_reject_event(self, client, case_id, document_id):
        """TV-004: Reject a reference event."""
        candidate_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={
                "action": "reject",
                "candidate_id": str(candidate_id),
                "event_type": "delivery",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["human_review_required"] is True

    def test_revoke_confirmation(self, client, case_id, document_id):
        """TV-005: Revoke a previous confirmation."""
        # First confirm
        confirm_resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "2026-07-15",
                "source_type": "auto_detected",
            },
        )
        assert confirm_resp.status_code == 200
        confirm_id = confirm_resp.json()["confirmation_id"]

        # Then revoke
        revoke_resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={
                "action": "revoke",
                "confirmation_id": confirm_id,
            },
        )
        assert revoke_resp.status_code == 200
        data = revoke_resp.json()
        assert data["human_review_required"] is True

    def test_revoke_not_found(self, client, case_id, document_id):
        """404 when revoking a non-existent confirmation."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={
                "action": "revoke",
                "confirmation_id": str(uuid.uuid4()),
            },
        )
        assert resp.status_code == 404

    def test_invalid_action(self, client, case_id, document_id):
        """400 for unknown action."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={"action": "unknown_action"},
        )
        assert resp.status_code == 400


# ── Calculation Preview ──


class TestCalculationPreview:
    """POST /calculation-preview endpoint tests."""

    def test_calculation_without_confirmation(self, client, case_id, document_id):
        """TV-001: Error when no confirmed reference event exists."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/calculation-preview",
            json={"confirmation_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data

    def test_calculation_with_confirmation(self, client, case_id, document_id):
        """Successful calculation with a confirmed reference event."""
        # First confirm
        confirm_resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "2026-07-15",
                "source_type": "auto_detected",
            },
        )
        assert confirm_resp.status_code == 200
        confirm_id = confirm_resp.json()["confirmation_id"]

        # Then calculate
        calc_resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/calculation-preview",
            json={"confirmation_id": confirm_id},
        )
        assert calc_resp.status_code == 200
        data = calc_resp.json()
        assert "calculated_date" in data
        assert "calculation_steps" in data
        assert data["legal_validity_assessed"] is False
        assert data["human_review_required"] is True
        assert data["adjustments_applied"]["weekend_adjustment_applied"] is False


# ── Confirmation History ──


class TestConfirmationHistory:
    """GET /reference-events/history endpoint tests."""

    def test_history_empty(self, client, case_id, document_id):
        """Empty history for candidate with no confirmations."""
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/history"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confirmations" in data
        assert isinstance(data["confirmations"], list)
        assert data["human_review_required"] is True

    def test_history_after_confirm(self, client, case_id, document_id):
        """TV-055: History shows entries after confirmations."""
        # Confirm twice
        for _ in range(2):
            resp = client.post(
                f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/confirm",
                json={
                    "action": "confirm",
                    "event_type": "issue_date",
                    "confirmed_date": "2026-07-15",
                    "source_type": "auto_detected",
                },
            )
            assert resp.status_code == 200

        hist_resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates/0/reference-events/history"
        )
        assert hist_resp.status_code == 200
        data = hist_resp.json()
        assert len(data["confirmations"]) >= 1
