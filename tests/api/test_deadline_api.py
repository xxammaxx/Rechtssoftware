"""Integration tests for M5 Deadline Candidate Extraction API.

SYNTHETISCH – KEINE ECHTEN PERSONEN- ODER FALLDATEN
"""

import io

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
        json={"title": "SYNTHETISCH – M5 Deadline Test Case"},
    )
    assert resp.status_code == 201
    return resp.json()["case_id"]


@pytest.fixture
def document_id(client, case_id):
    """Upload a synthetic PDF document and return its ID."""
    # Minimal valid PDF
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


class TestDeadlineExtractionEndpoint:
    """Integration tests for POST /cases/{case_id}/documents/{doc_id}/deadline-candidates"""

    def test_extraction_success(self, client, case_id, document_id):
        """Successful extraction returns 200 with structured result."""
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_id"] == document_id
        assert "candidates" in data
        assert "warnings" in data
        assert data["human_review_required"] is True

    def test_legal_calculation_warning_present(self, client, case_id, document_id):
        """Every response must include LEGAL_CALCULATION_NOT_PERFORMED warning."""
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        data = resp.json()
        warning_codes = [w["code"] for w in data["warnings"]]
        assert "LEGAL_CALCULATION_NOT_PERFORMED" in warning_codes

    def test_document_not_found_returns_404(self, client, case_id):
        """Non-existent document ID returns 404."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/00000000-0000-0000-0000-000000000000/deadline-candidates"
        )
        assert resp.status_code == 404

    def test_non_existent_document_in_wrong_case(self, client, case_id, document_id):
        """The endpoint resolves by document_id only, consistent with existing routes.
        A valid document_id returns 200 even in a different case context."""
        # Create a second case
        resp2 = client.post(
            "/api/v1/cases",
            json={"title": "SYNTHETISCH – Second Case"},
        )
        assert resp2.status_code == 201
        second_case_id = resp2.json()["case_id"]
        # The document exists (from first case's fixture), but we ask in second case
        resp = client.post(
            f"/api/v1/cases/{second_case_id}/documents/{document_id}/deadline-candidates"
        )
        # Document exists regardless of case — consistent with existing API pattern
        assert resp.status_code == 200

    def test_empty_candidates_list_valid(self, client, case_id, document_id):
        """Document without dates should return empty candidates list."""
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        data = resp.json()
        assert isinstance(data["candidates"], list)
        # Empty is valid — no text in this synthetic PDF

    def test_error_envelope_no_text_leak(self, client, case_id):
        """Error responses must not contain document text snippets."""
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents/00000000-0000-0000-0000-000000000000/deadline-candidates"
        )
        data = resp.json()
        assert "error" in data
        # Must NOT contain raw document text
        assert "raw_text" not in str(data)
        assert "text_content" not in str(data)

    def test_response_valid_json_schema(self, client, case_id, document_id):
        """Response matches expected JSON structure."""
        resp = client.post(f"/api/v1/cases/{case_id}/documents/{document_id}/deadline-candidates")
        data = resp.json()
        # Check structure
        assert "document_id" in data
        assert "candidates" in data
        assert "warnings" in data
        assert "human_review_required" in data
        # candidate fields
        for c in data["candidates"]:
            assert "kind" in c
            assert "raw_text" in c
            assert "start_offset" in c
            assert "end_offset" in c
            assert "certainty" in c
            assert "rule_id" in c
            # kind must be one of the valid enum values
            assert c["kind"] in ("explicit_date", "relative_period", "qualitative_reference")
            # certainty must be one of the valid enum values
            assert c["certainty"] in ("exact", "unresolved", "ambiguous")
        # warning fields
        for w in data["warnings"]:
            assert "code" in w
            assert "message" in w

    def test_invalid_uuid_format(self, client):
        """Invalid UUID in path should be handled gracefully."""
        resp = client.post("/api/v1/cases/not-a-uuid/documents/not-a-uuid/deadline-candidates")
        assert resp.status_code >= 400
