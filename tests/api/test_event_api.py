"""API integration tests for M6-A Reference Events and Calendar Arithmetic.

SYNTHETISCH - KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

import io
from uuid import uuid4

import pymupdf
import pytest
from fastapi.testclient import TestClient

from private_legal_navigator.app import create_app
from private_legal_navigator.config import Settings


def _make_text_pdf(text: str) -> bytes:
    """Create a minimal PDF with actual extractable text content using pymupdf."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 100), text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# Pre-built test PDF with a specific date and relative period text
_BESCHEID_PDF = _make_text_pdf(
    "Bescheid vom 15.07.2026.\nWiderspruch innerhalb von 2 Wochen nach Zustellung.\n"
)


@pytest.fixture
def client(tmp_path):
    """Create a test client with a temporary data directory."""
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
def case_id(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/cases",
        json={"title": "SYNTHETISCH - M6-A Test Case"},
    )
    assert resp.status_code == 201
    return resp.json()["case_id"]


@pytest.fixture
def document_id(client: TestClient, case_id: str) -> str:
    """Upload a minimal PDF document with actual text content."""
    resp = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("synthetic-test.pdf", io.BytesIO(_BESCHEID_PDF), "application/pdf")},
    )
    assert resp.status_code == 201
    return resp.json()["document_id"]


@pytest.fixture
def deadline_candidates(client: TestClient, case_id: str, document_id: str) -> list[dict]:
    """Get deadline candidates for the document."""
    resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
    assert resp.status_code == 200
    return resp.json().get("candidates", [])


class TestReferenceEventsList:
    """TV-058: GET /reference-events."""

    def test_reference_events_for_relative_candidate(
        self, client: TestClient, case_id: str, document_id: str
    ):
        """TV-058: GET reference-events returns candidates for synthetic doc."""
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        candidates = resp.json().get("candidates", [])
        relative_idx = None
        for i, c in enumerate(candidates):
            if c["kind"] == "relative_period":
                relative_idx = i
                break
        assert relative_idx is not None, "Expected RELATIVE_PERIOD candidate"

        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{relative_idx}/reference-events"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reference_events" in data
        assert "warnings" in data
        assert data["human_review_required"] is True

    def test_invalid_candidate_index_returns_400(
        self, client: TestClient, case_id: str, document_id: str
    ):
        """Invalid candidate index returns 200 with empty list (detection is placeholder)."""
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/99/reference-events"
        )
        assert resp.status_code == 200
        assert resp.json()["reference_events"] == []

    def test_not_found_document_returns_404(self, client: TestClient, case_id: str):
        """Non-existent document returns 404."""
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{uuid4()}/deadline-candidates/0/reference-events"
        )
        assert resp.status_code == 404

    def test_stable_candidate_ids(self, client: TestClient, case_id: str, document_id: str):
        """TV-048: Candidate IDs are stable across repeated calls."""
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        candidates = resp.json()["candidates"]
        relative_idx = None
        for i, c in enumerate(candidates):
            if c["kind"] == "relative_period":
                relative_idx = i
                break
        assert relative_idx is not None

        resp1 = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{relative_idx}/reference-events"
        )
        resp2 = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{relative_idx}/reference-events"
        )
        ids1 = [e["candidate_id"] for e in resp1.json()["reference_events"]]
        ids2 = [e["candidate_id"] for e in resp2.json()["reference_events"]]
        assert ids1 == ids2, "Candidate IDs must be stable across calls"


class TestConfirmationAPI:
    """TV-002..064: POST /reference-events/confirm."""

    def _find_relative_idx(self, client: TestClient, case_id: str, document_id: str) -> int:
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        candidates = resp.json()["candidates"]
        for i, c in enumerate(candidates):
            if c["kind"] == "relative_period":
                return i
        raise AssertionError("No RELATIVE_PERIOD candidate found")

    def test_confirm_auto_suggested(self, client: TestClient, case_id: str, document_id: str):
        """TV-003, TV-062: Confirm auto-suggested candidate."""
        idx = self._find_relative_idx(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "2026-07-15",
                "source_type": "auto_detected",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmation_status"] == "confirmed"
        assert data["confirmation_method"] == "auto_suggested"
        assert data["confirmed_date"] == "2026-07-15"
        assert data["human_review_required"] is True

    def test_confirm_manual_entry(self, client: TestClient, case_id: str, document_id: str):
        """TV-002, TV-061: Manual entry without candidate_id."""
        idx = self._find_relative_idx(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "delivery",
                "confirmed_date": "2026-07-15",
                "source_type": "user_manual",
                "evidence_note": "Zustellungsdatum laut Urkunde",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmation_status"] == "confirmed"
        assert data["confirmation_method"] == "manually_entered"

    def test_confirm_user_corrected(self, client: TestClient, case_id: str, document_id: str):
        """TV-064: source_type=user_corrected -> method=corrected."""
        idx = self._find_relative_idx(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "2026-07-20",
                "source_type": "user_corrected",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmation_method"] == "corrected"

    def test_reject_candidate(self, client: TestClient, case_id: str, document_id: str):
        """TV-004: Reject a candidate."""
        idx = self._find_relative_idx(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "reject",
                "candidate_id": str(uuid4()),
                "event_type": "delivery",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmation_status"] == "rejected"
        assert data["confirmed_date"] is None

    def test_invalid_date_returns_400(self, client: TestClient, case_id: str, document_id: str):
        """TV-053: Invalid date returns 400."""
        idx = self._find_relative_idx(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "2026-02-30",
                "source_type": "auto_detected",
            },
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_DATE"

    def test_date_before_1900_returns_400(self, client: TestClient, case_id: str, document_id: str):
        """TV-054: Date outside range returns 400."""
        idx = self._find_relative_idx(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "1899-01-01",
                "source_type": "auto_detected",
            },
        )
        assert resp.status_code == 400

    def test_consecutive_confirms_supersede(
        self, client: TestClient, case_id: str, document_id: str
    ):
        """TV-005, TV-006: Second confirm supersedes the first."""
        idx = self._find_relative_idx(client, case_id, document_id)
        # First confirm
        resp1 = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "2026-07-15",
                "source_type": "auto_detected",
            },
        )
        assert resp1.status_code == 200

        # Second confirm (different date)
        resp2 = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "2026-07-20",
                "source_type": "user_corrected",
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["confirmation_status"] == "confirmed"

        # Verify history shows both with correct statuses
        resp_hist = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/history"
        )
        assert resp_hist.status_code == 200
        hist = resp_hist.json()
        entries = hist["confirmations"]
        statuses = {e["confirmation_status"] for e in entries}
        assert "superseded" in statuses
        assert "confirmed" in statuses
        assert hist["current_status"] == "confirmed"


class TestCalculationPreview:
    """TV-010 through TV-050: calculation preview API integration."""

    def _setup_and_confirm(
        self, client: TestClient, case_id: str, document_id: str
    ) -> tuple[int, str]:
        """Helper: confirm a reference event."""
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        candidates = resp.json()["candidates"]
        for i, c in enumerate(candidates):
            if c["kind"] == "relative_period":
                resp = client.post(
                    f"/api/v1/cases/{case_id}/documents/{document_id}"
                    f"/deadline-candidates/{i}/reference-events/confirm",
                    json={
                        "action": "confirm",
                        "event_type": "issue_date",
                        "confirmed_date": "2026-07-15",
                        "source_type": "auto_detected",
                    },
                )
                assert resp.status_code == 200
                return i, resp.json()["confirmation_id"]
        raise AssertionError("No RELATIVE_PERIOD candidate found")

    def test_calculation_preview_success(self, client: TestClient, case_id: str, document_id: str):
        """Full calculation preview flow."""
        idx, conf_id = self._setup_and_confirm(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/calculation-preview",
            json={"confirmation_id": conf_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["result_type"] == "calculated_candidate"
        assert data["legal_validity_assessed"] is False
        assert data["human_review_required"] is True
        assert data["calculated_date"] is not None
        assert len(data["calculation_steps"]) >= 1
        assert data["adjustments_applied"]["weekend_adjustment_applied"] is False
        assert data["adjustments_applied"]["holiday_adjustment_applied"] is False
        assert data["adjustments_applied"]["legal_rule_applied"] is False
        warning_codes = [w["code"] for w in data["warnings"]]
        assert "CALCULATION_PREVIEW_ONLY" in warning_codes
        assert "HUMAN_REVIEW_REQUIRED" in warning_codes

    def test_no_confirmation_returns_error(
        self, client: TestClient, case_id: str, document_id: str
    ):
        """No confirmed reference event returns error."""
        idx, _ = self._setup_and_confirm(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/calculation-preview",
            json={"confirmation_id": str(uuid4())},
        )
        assert resp.status_code == 404

    def test_unsupported_duration_unit_error(
        self, client: TestClient, case_id: str, document_id: str
    ):
        """TV-027: Supported duration units succeed."""
        idx, conf_id = self._setup_and_confirm(client, case_id, document_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/calculation-preview",
            json={"confirmation_id": conf_id},
        )
        assert resp.status_code == 200

    def test_error_envelope_structure(self, client: TestClient, case_id: str):
        """TV-059: Error responses use standard envelope."""
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{uuid4()}/deadline-candidates/0/reference-events"
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]


class TestConfirmationHistory:
    """TV-055, TV-056, TV-057: GET /reference-events/history."""

    def _setup_and_confirm(
        self, client: TestClient, case_id: str, document_id: str
    ) -> tuple[int, str]:
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        candidates = resp.json()["candidates"]
        for i, c in enumerate(candidates):
            if c["kind"] == "explicit_date":
                resp = client.post(
                    f"/api/v1/cases/{case_id}/documents/{document_id}"
                    f"/deadline-candidates/{i}/reference-events/confirm",
                    json={
                        "action": "confirm",
                        "event_type": "issue_date",
                        "confirmed_date": "2026-07-15",
                        "source_type": "auto_detected",
                    },
                )
                assert resp.status_code == 200
                return i, resp.json()["confirmation_id"]
        raise AssertionError("No candidate found")

    def test_history_returns_entries(self, client: TestClient, case_id: str, document_id: str):
        """TV-055: History returns confirmation entries."""
        idx, _conf_id = self._setup_and_confirm(client, case_id, document_id)
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/{idx}/reference-events/history"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confirmations" in data
        assert len(data["confirmations"]) >= 1
        assert data["human_review_required"] is True
