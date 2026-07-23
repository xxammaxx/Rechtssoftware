"""Unit tests for security dependency edge cases."""

import uuid
from unittest.mock import AsyncMock, MagicMock

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


# ── Direct dependency unit tests (cover non-POST early-return branches) ──


class TestSecurityDependencyEarlyReturns:
    """Cover the ``if request.method != 'POST': return`` branches."""

    @pytest.mark.anyio
    async def test_content_type_skips_non_post(self):
        """require_form_content_type returns immediately for GET requests."""
        from private_legal_navigator.middleware.security_dependencies import (
            require_form_content_type,
        )

        req = MagicMock()
        req.method = "GET"
        # Must not raise — just returns
        await require_form_content_type(req)

    @pytest.mark.anyio
    async def test_body_size_skips_non_post(self):
        """require_body_size_limit returns immediately for GET requests."""
        from private_legal_navigator.middleware.security_dependencies import (
            require_body_size_limit,
        )

        req = MagicMock()
        req.method = "GET"
        await require_body_size_limit(req)

    @pytest.mark.anyio
    async def test_origin_check_skips_non_post(self):
        """require_origin_or_referer returns immediately for GET requests."""
        from private_legal_navigator.middleware.security_dependencies import (
            require_origin_or_referer,
        )

        req = MagicMock()
        req.method = "GET"
        await require_origin_or_referer(req)

    @pytest.mark.anyio
    async def test_csrf_skips_non_post(self):
        """require_csrf_token returns immediately for GET requests."""
        from private_legal_navigator.middleware.security_dependencies import (
            require_csrf_token,
        )

        req = MagicMock()
        req.method = "GET"
        await require_csrf_token(req)

    @pytest.mark.anyio
    async def test_csrf_missing_service_returns_500(self):
        """require_csrf_token returns 500 when csrf_service is not on app state."""
        from fastapi import HTTPException

        from private_legal_navigator.middleware.security_dependencies import (
            require_csrf_token,
        )

        req = MagicMock()
        req.method = "POST"
        req.app.state = MagicMock()
        del req.app.state.csrf_service  # Simulate missing service

        with pytest.raises(HTTPException) as exc_info:
            await require_csrf_token(req)
        assert exc_info.value.status_code == 500

    @pytest.mark.anyio
    async def test_csrf_form_read_failure_returns_400(self):
        """require_csrf_token returns 400 when request.form() raises."""
        from fastapi import HTTPException

        from private_legal_navigator.middleware.security_dependencies import (
            require_csrf_token,
        )

        req = MagicMock()
        req.method = "POST"
        # Set up state so the csrf_service check passes
        req.app.state.csrf_service = MagicMock()
        # Make request.form() raise
        req.form = AsyncMock(side_effect=ValueError("form parse error"))

        with pytest.raises(HTTPException) as exc_info:
            await require_csrf_token(req)
        assert exc_info.value.status_code == 400


class TestSecurityDependencyErrorBranches:
    """Cover remaining error-branch statements."""

    @pytest.mark.anyio
    async def test_body_size_exceeded_returns_413(self):
        """Content-Length > MAX_BODY_BYTES must return 413 (line 47)."""
        from fastapi import HTTPException

        from private_legal_navigator.middleware.security_dependencies import (
            require_body_size_limit,
        )

        req = MagicMock()
        req.method = "POST"
        req.headers = {"content-length": "999999"}

        with pytest.raises(HTTPException) as exc_info:
            await require_body_size_limit(req)
        assert exc_info.value.status_code == 413

    @pytest.mark.anyio
    async def test_referer_mismatch_returns_403(self):
        """Referer header not matching origin must return 403 (line 70)."""
        from fastapi import HTTPException

        from private_legal_navigator.middleware.security_dependencies import (
            require_origin_or_referer,
        )

        req = MagicMock()
        req.method = "POST"
        req.headers = {"referer": "https://evil.example.com"}
        req.base_url = "http://127.0.0.1:8000/"

        with pytest.raises(HTTPException) as exc_info:
            await require_origin_or_referer(req)
        assert exc_info.value.status_code == 403
