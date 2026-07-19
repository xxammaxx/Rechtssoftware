"""Unit tests for security dependency edge cases."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from private_legal_navigator.config import Settings


@pytest.fixture
def settings(tmp_path):
    data_dir = tmp_path / "pln_data"
    data_dir.mkdir()
    return Settings(data_dir=data_dir, host="127.0.0.1", port=8000)


@pytest.fixture
async def client(settings: Settings):
    from private_legal_navigator.app import create_app

    app = create_app(settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as ac:
        yield ac


class TestContentTypeEdgeCases:
    """Test Content-Type validation edge cases."""

    async def test_content_type_with_charset_accepted(self, client: AsyncClient):
        """Content-Type with charset parameter should be accepted."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/confirm",
            data={"csrf_token": "dummy", "idempotency_key": uuid.uuid4().hex},
            headers={
                "Origin": "http://127.0.0.1:8000",
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
            },
        )
        # Should pass content-type check (403 is CSRF, not 415)
        assert resp.status_code != 415

    async def test_no_content_type_header_rejected(self, client: AsyncClient):
        """Missing Content-Type should be rejected."""
        # httpx sets Content-Type automatically for data=, so test indirectly
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/confirm",
            content=b"",
            headers={
                "Origin": "http://127.0.0.1:8000",
                "Content-Type": "",  # Explicitly empty
            },
        )
        assert resp.status_code in (400, 415)


class TestBodySizeEdgeCases:
    """Test body size limit edge cases."""

    async def test_content_length_missing_accepted(self, client: AsyncClient):
        """Missing Content-Length header should be accepted (checked at lower layer)."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/confirm",
            data={"csrf_token": "dummy", "idempotency_key": uuid.uuid4().hex},
            headers={
                "Origin": "http://127.0.0.1:8000",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        assert resp.status_code != 413  # Not rejected for missing length

    async def test_content_length_zero(self, client: AsyncClient):
        """Zero Content-Length should be accepted by the guard."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/confirm",
            content=b"",
            headers={
                "Origin": "http://127.0.0.1:8000",
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": "0",
            },
        )
        # 0-length body is valid per our guard (only checks > MAX)
        assert resp.status_code != 413


class TestOriginRefererEdgeCases:
    """Test Origin/Referer validation edge cases."""

    async def test_referer_fallback_accepted(self, client: AsyncClient):
        """Referer should be accepted when Origin is absent."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/confirm",
            data={"csrf_token": "dummy", "idempotency_key": uuid.uuid4().hex},
            headers={
                "Referer": "http://127.0.0.1:8000/ui/cases",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        # Should not be rejected for origin (403 is CSRF, which is fine)
        assert resp.status_code != 403 or "Ungültige Anfrageherkunft" not in resp.text


class TestCSRFEdgeCases:
    """Additional CSRF edge cases."""

    async def test_csrf_token_truncation(self, client: AsyncClient):
        """CSRF token with wrong length should fail gracefully."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/confirm",
            data={
                "csrf_token": "tooshort",
                "idempotency_key": uuid.uuid4().hex,
                "confirmed_date": "2026-01-15",
            },
            headers={
                "Origin": "http://127.0.0.1:8000",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        assert resp.status_code in (400, 403)

    async def test_browser_nonce_missing_cookie(self, client: AsyncClient):
        """CSRF validation must fail when browser nonce cookie is absent."""
        case_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        resp = await client.post(
            f"/ui/cases/{case_id}/documents/{doc_id}/candidates/0/confirm",
            data={
                "csrf_token": "some_token",
                "idempotency_key": uuid.uuid4().hex,
            },
            headers={
                "Origin": "http://127.0.0.1:8000",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        assert resp.status_code == 403
