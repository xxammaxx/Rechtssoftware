"""API integration tests for document endpoints."""

import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from private_legal_navigator.config import Settings


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "pln_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def settings(temp_data_dir: Path) -> Settings:
    return Settings(data_dir=temp_data_dir, host="127.0.0.1", port=8000)


@pytest.fixture
async def client(settings: Settings) -> AsyncClient:
    from private_legal_navigator.app import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _create_case(client: AsyncClient, title: str = "SYNTHETISCH Case") -> str:
    resp = await client.post("/api/v1/cases", json={"title": title})
    assert resp.status_code == 201
    return resp.json()["case_id"]


class TestDocumentUpload:
    """Tests for POST /api/v1/cases/{case_id}/documents."""

    async def test_upload_pdf(self, client: AsyncClient) -> None:
        """Upload a valid PDF should succeed."""
        case_id = await _create_case(client)
        pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>"

        resp = await client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "test.pdf"
        assert data["mime_type"] == "application/pdf"
        assert "document_id" in data
        assert data["case_id"] == case_id

    async def test_upload_to_nonexistent_case(self, client: AsyncClient) -> None:
        """Upload to nonexistent case should return 404."""
        fake_id = str(uuid.uuid4())
        resp = await client.post(
            f"/api/v1/cases/{fake_id}/documents",
            files={"file": ("test.pdf", b"x", "application/pdf")},
        )
        assert resp.status_code == 404

    async def test_upload_non_pdf_rejected(self, client: AsyncClient) -> None:
        """Upload of non-PDF should be rejected."""
        case_id = await _create_case(client)
        resp = await client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("image.png", b"fake-png", "image/png")},
        )
        assert resp.status_code == 400


class TestDocumentList:
    """Tests for GET /api/v1/cases/{case_id}/documents."""

    async def test_list_empty(self, client: AsyncClient) -> None:
        """List documents for a case with none."""
        case_id = await _create_case(client)
        resp = await client.get(f"/api/v1/cases/{case_id}/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"items": [], "count": 0}

    async def test_list_with_documents(self, client: AsyncClient) -> None:
        """List documents after upload."""
        case_id = await _create_case(client)
        await client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("a.pdf", b"%PDF-1.4 a", "application/pdf")},
        )
        await client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("b.pdf", b"%PDF-1.4 b", "application/pdf")},
        )

        resp = await client.get(f"/api/v1/cases/{case_id}/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["items"]) == 2


class TestDocumentDownload:
    """Tests for GET /api/v1/cases/{case_id}/documents/{document_id}."""

    async def test_download_existing(self, client: AsyncClient) -> None:
        """Download an uploaded document."""
        case_id = await _create_case(client)
        upload_resp = await client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("bescheid.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = await client.get(f"/api/v1/cases/{case_id}/documents/{doc_id}")
        assert resp.status_code == 200
        assert resp.content == b"%PDF-1.4 content"
        assert resp.headers["content-type"] == "application/pdf"

    async def test_download_nonexistent(self, client: AsyncClient) -> None:
        """Download nonexistent document returns 404."""
        case_id = await _create_case(client)
        fake_doc_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/cases/{case_id}/documents/{fake_doc_id}")
        assert resp.status_code == 404


class TestDocumentText:
    """Tests for GET .../documents/{id}/text."""

    async def test_get_text(self, client: AsyncClient) -> None:
        """Get extracted text from an uploaded document."""
        case_id = await _create_case(client)
        upload_resp = await client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("doc.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = await client.get(
            f"/api/v1/cases/{case_id}/documents/{doc_id}/text"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["document_id"] == doc_id
        assert "text_content" in data
        assert "text_length" in data

    async def test_get_text_nonexistent(self, client: AsyncClient) -> None:
        """Get text for nonexistent document returns 404."""
        case_id = await _create_case(client)
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/cases/{case_id}/documents/{fake_id}/text"
        )
        assert resp.status_code == 404
