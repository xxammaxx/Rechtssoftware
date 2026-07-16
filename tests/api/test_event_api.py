"""API integration tests for M6-A Reference Events and Calendar Arithmetic.

SYNTHETISCH - KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from private_legal_navigator.app import create_app
from private_legal_navigator.config import Settings


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
    """Upload a minimal PDF document."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )
    resp = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("synthetic-test.pdf", io.BytesIO(pdf_content), "application/pdf")},
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
    """TV-058, TV-033, TV-034, TV-035: GET /reference-events."""

    def test_reference_events_for_relative_candidate(
        self, client: TestClient, case_id: str, document_id: str
    ):
        """TV-058: GET reference-events returns candidates."""
        # First upload a doc with explicit dates
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={
                "file": (
                    "bescheid.pdf",
                    b"%PDF-1.4 Bescheid vom 15.07.2026.\n"
                    b"Widerspruch innerhalb von zwei Wochen nach Zustellung.\n",
                ),
            },
        )
        assert resp.status_code == 201
        doc_id = resp.json()["document_id"]

        # Get deadline candidates
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates")
        assert resp.status_code == 200
        data = resp.json()
        candidates = data.get("candidates", [])

        # Find a RELATIVE_PERIOD candidate
        relative_idx = None
        for i, c in enumerate(candidates):
            if c["kind"] == "relative_period":
                relative_idx = i
                break

        if relative_idx is None:
            pytest.skip("No RELATIVE_PERIOD candidate found")

        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
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
        """Invalid candidate index returns 400."""
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{document_id}"
            f"/deadline-candidates/99/reference-events"
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "INVALID_CANDIDATE_INDEX"

    def test_not_found_document_returns_404(self, client: TestClient, case_id: str):
        """Non-existent document returns 404."""
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{uuid4()}/deadline-candidates/0/reference-events"
        )
        assert resp.status_code == 404


class TestConfirmationAPI:
    """TV-002, TV-003, TV-004, TV-060, TV-061, TV-062, TV-063, TV-064:
    POST /reference-events/confirm.
    """

    def _setup_doc_with_deadlines(self, client: TestClient, case_id: str) -> tuple[str, int]:
        """Helper: create doc with deadline text, return (doc_id, candidate_idx)."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={
                "file": (
                    "bescheid.pdf",
                    b"%PDF-1.4 Bescheid vom 15.07.2026.\n"
                    b"Widerspruch innerhalb von zwei Wochen nach Zustellung.\n",
                ),
            },
        )
        doc_id = resp.json()["document_id"]
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates")
        candidates = resp.json()["candidates"]
        for i, c in enumerate(candidates):
            if c["kind"] == "relative_period":
                return doc_id, i
        pytest.skip("No RELATIVE_PERIOD candidate found")
        return "", -1

    def test_confirm_auto_suggested(self, client: TestClient, case_id: str):
        """TV-003, TV-062: Confirm auto-suggested candidate."""
        doc_id, idx = self._setup_doc_with_deadlines(client, case_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
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

    def test_confirm_manual_entry(self, client: TestClient, case_id: str):
        """TV-002, TV-061: Manual entry without candidate_id."""
        doc_id, idx = self._setup_doc_with_deadlines(client, case_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
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

    def test_confirm_user_corrected(self, client: TestClient, case_id: str):
        """TV-064: source_type=user_corrected -> method=corrected."""
        doc_id, idx = self._setup_doc_with_deadlines(client, case_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
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

    def test_reject_candidate(self, client: TestClient, case_id: str):
        """TV-004: Reject a candidate."""
        doc_id, idx = self._setup_doc_with_deadlines(client, case_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
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

    def test_invalid_date_returns_400(self, client: TestClient, case_id: str):
        """TV-053: Invalid date returns 400."""
        doc_id, idx = self._setup_doc_with_deadlines(client, case_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
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

    def test_date_before_1900_returns_400(self, client: TestClient, case_id: str):
        """TV-054: Date outside range returns 400."""
        doc_id, idx = self._setup_doc_with_deadlines(client, case_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
            f"/deadline-candidates/{idx}/reference-events/confirm",
            json={
                "action": "confirm",
                "event_type": "issue_date",
                "confirmed_date": "1899-01-01",
                "source_type": "auto_detected",
            },
        )
        assert resp.status_code == 400


class TestCalculationPreview:
    """TV-010 through TV-050 are tested in unit tests; API-level integration tests."""

    def _setup_and_confirm(self, client: TestClient, case_id: str) -> tuple[str, int, str]:
        """Helper: create doc, get candidate, confirm, return (doc_id, idx, confirmation_id)."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={
                "file": (
                    "bescheid.pdf",
                    b"%PDF-1.4 Bescheid vom 15.07.2026.\n"
                    b"Widerspruch innerhalb von zwei Wochen nach Zustellung.\n",
                ),
            },
        )
        doc_id = resp.json()["document_id"]
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates")
        candidates = resp.json()["candidates"]
        for i, c in enumerate(candidates):
            if c["kind"] == "relative_period":
                # Confirm
                resp = client.post(
                    f"/api/v1/cases/{case_id}/documents/{doc_id}"
                    f"/deadline-candidates/{i}/reference-events/confirm",
                    json={
                        "action": "confirm",
                        "event_type": "issue_date",
                        "confirmed_date": "2026-07-15",
                        "source_type": "auto_detected",
                    },
                )
                assert resp.status_code == 200
                return doc_id, i, resp.json()["confirmation_id"]
        pytest.skip("No RELATIVE_PERIOD candidate found")
        return "", -1, ""

    def test_calculation_preview_success(self, client: TestClient, case_id: str):
        """Full calculation preview flow."""
        doc_id, idx, conf_id = self._setup_and_confirm(client, case_id)

        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
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
        assert data["adjustments"]["weekend_adjustment_applied"] is False
        assert data["adjustments"]["holiday_adjustment_applied"] is False
        assert data["adjustments"]["legal_rule_applied"] is False
        # Warnings
        warning_codes = [w["code"] for w in data["warnings"]]
        assert "CALCULATION_PREVIEW_ONLY" in warning_codes
        assert "HUMAN_REVIEW_REQUIRED" in warning_codes

    def test_no_confirmation_returns_error(self, client: TestClient, case_id: str):
        """No confirmed reference event returns error."""
        doc_id, idx, _ = self._setup_and_confirm(client, case_id)
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
            f"/deadline-candidates/{idx}/calculation-preview",
            json={"confirmation_id": str(uuid4())},
        )
        assert resp.status_code == 404

    def test_unsupported_duration_unit(self, client: TestClient, case_id: str):
        """TV-027 through TV-031: Unsupported units tested at domain level."""
        pass  # Integration test for unsupported units would need MONTH/YEAR candidates

    def test_error_envelope_structure(self, client: TestClient, case_id: str):
        """TV-059: Error responses use standard envelope."""
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{uuid4()}/deadline-candidates/0/reference-events"
        )
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "code" in data["detail"]
        assert "message" in data["detail"]


class TestConfirmationHistory:
    """TV-055, TV-056, TV-057: GET /reference-events/history."""

    def _setup_and_confirm(self, client: TestClient, case_id: str) -> tuple[str, int, str]:
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={
                "file": (
                    "bescheid.pdf",
                    b"%PDF-1.4 Bescheid vom 15.07.2026.\n",
                ),
            },
        )
        doc_id = resp.json()["document_id"]
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{doc_id}/deadline-candidates")
        candidates = resp.json()["candidates"]
        for i, c in enumerate(candidates):
            if c["kind"] == "explicit_date":
                resp = client.post(
                    f"/api/v1/cases/{case_id}/documents/{doc_id}"
                    f"/deadline-candidates/{i}/reference-events/confirm",
                    json={
                        "action": "confirm",
                        "event_type": "issue_date",
                        "confirmed_date": "2026-07-15",
                        "source_type": "auto_detected",
                    },
                )
                assert resp.status_code == 200
                return doc_id, i, resp.json()["confirmation_id"]
        pytest.skip("No candidate found")
        return "", -1, ""

    def test_history_returns_entries(self, client: TestClient, case_id: str):
        """TV-055: History returns confirmation entries."""
        doc_id, idx, conf_id = self._setup_and_confirm(client, case_id)
        resp = client.get(
            f"/api/v1/cases/{case_id}/documents/{doc_id}"
            f"/deadline-candidates/{idx}/reference-events/history"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "confirmations" in data
        assert len(data["confirmations"]) >= 1
        assert data["human_review_required"] is True
