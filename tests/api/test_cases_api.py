"""API integration tests for the FastAPI application."""

import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from private_legal_navigator.config import Settings


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Provide an isolated temporary data directory."""
    data_dir = tmp_path / "pln_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def settings(temp_data_dir: Path) -> Settings:
    """Settings pointing to an isolated temp directory."""
    return Settings(data_dir=temp_data_dir, host="127.0.0.1", port=8000)


@pytest.fixture
async def client(settings: Settings) -> AsyncClient:
    """Async test client for the FastAPI app with isolated settings."""
    from private_legal_navigator.app import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        """GET /health should return {'status': 'ok'}."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}


class TestCreateCase:
    """Tests for POST /api/v1/cases."""

    async def test_create_case_returns_201(self, client: AsyncClient) -> None:
        """Creating a case should return 201 with case data."""
        response = await client.post(
            "/api/v1/cases",
            json={"title": "SYNTHETISCH – API-Test"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "case_id" in data
        assert data["title"] == "SYNTHETISCH – API-Test"
        assert data["status"] == "open"
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_case_empty_title(self, client: AsyncClient) -> None:
        """An empty title should be rejected with documented 422 format."""
        response = await client.post("/api/v1/cases", json={"title": ""})
        assert response.status_code == 422
        assert response.json() == {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Die Eingabedaten sind ungültig.",
            }
        }

    async def test_create_case_whitespace_title(self, client: AsyncClient) -> None:
        """A whitespace-only title should be rejected with documented 422 format."""
        response = await client.post("/api/v1/cases", json={"title": "   "})
        assert response.status_code == 422
        assert response.json() == {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Die Eingabedaten sind ungültig.",
            }
        }

    async def test_create_case_title_too_long(self, client: AsyncClient) -> None:
        """A title over 200 characters should be rejected with documented 422 format."""
        long_title = "A" * 201
        response = await client.post("/api/v1/cases", json={"title": long_title})
        assert response.status_code == 422
        assert response.json() == {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Die Eingabedaten sind ungültig.",
            }
        }


class TestListCases:
    """Tests for GET /api/v1/cases."""

    async def test_list_cases_empty(self, client: AsyncClient) -> None:
        """GET /api/v1/cases on empty DB should return empty list."""
        response = await client.get("/api/v1/cases")
        assert response.status_code == 200
        data = response.json()
        assert data == {"items": [], "count": 0}

    async def test_list_cases_with_items(self, client: AsyncClient) -> None:
        """GET /api/v1/cases should return created cases."""
        await client.post("/api/v1/cases", json={"title": "SYNTHETISCH – Eins"})
        await client.post("/api/v1/cases", json={"title": "SYNTHETISCH – Zwei"})

        response = await client.get("/api/v1/cases")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["items"]) == 2


class TestGetCase:
    """Tests for GET /api/v1/cases/{case_id}."""

    async def test_get_existing_case(self, client: AsyncClient) -> None:
        """Should retrieve a previously created case."""
        create_resp = await client.post("/api/v1/cases", json={"title": "SYNTHETISCH – Detail"})
        case_id = create_resp.json()["case_id"]

        response = await client.get(f"/api/v1/cases/{case_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == case_id
        assert data["title"] == "SYNTHETISCH – Detail"

    async def test_get_nonexistent_case_returns_404(self, client: AsyncClient) -> None:
        """Unknown case ID should return 404."""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/cases/{fake_id}")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "CASE_NOT_FOUND"

    async def test_get_invalid_uuid_format(self, client: AsyncClient) -> None:
        """An invalid UUID format should be rejected with documented 422 format."""
        response = await client.get("/api/v1/cases/not-a-valid-uuid")
        assert response.status_code == 422
        assert response.json() == {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Die Eingabedaten sind ungültig.",
            }
        }
