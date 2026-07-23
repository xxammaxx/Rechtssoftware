"""Tests for M6-UI security middleware."""

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from private_legal_navigator.middleware.host_validation import HostValidationMiddleware
from private_legal_navigator.middleware.security_headers import SecurityHeadersMiddleware


async def _ui_cases(request: Request) -> PlainTextResponse:
    return PlainTextResponse("cases")


async def _api_cases(request: Request) -> PlainTextResponse:
    return PlainTextResponse("api cases")


async def _ui_error(request: Request) -> PlainTextResponse:
    raise RuntimeError("test")
    return PlainTextResponse("")  # unreachable


@pytest.fixture
def host_app():
    """App with HostValidationMiddleware using explicit allowlist."""
    app = Starlette(
        routes=[
            Route("/ui/cases", _ui_cases),
            Route("/api/v1/cases", _api_cases),
        ],
        middleware=[
            __import__("starlette").middleware.Middleware(
                HostValidationMiddleware,
                allowed_hosts=["127.0.0.1:8000", "localhost:8000", "[::1]:8000"],
            ),
        ],
    )
    return app


@pytest.fixture
def security_app():
    """App with SecurityHeadersMiddleware."""
    app = Starlette(
        routes=[
            Route("/ui/cases", _ui_cases),
            Route("/ui/error", _ui_error),
        ],
        middleware=[
            __import__("starlette").middleware.Middleware(
                SecurityHeadersMiddleware,
            ),
        ],
    )
    return app


class TestHostValidation:
    """Tests for HostValidationMiddleware."""

    def test_ui_rejects_unknown_host(self, host_app) -> None:
        client = TestClient(host_app)
        resp = client.get("/ui/cases", headers={"host": "evil.com:8000"})
        assert resp.status_code == 400

    def test_ui_accepts_localhost(self, host_app) -> None:
        client = TestClient(host_app)
        resp = client.get("/ui/cases", headers={"host": "localhost:8000"})
        assert resp.status_code == 200

    def test_ui_accepts_127_0_0_1(self, host_app) -> None:
        client = TestClient(host_app)
        resp = client.get("/ui/cases", headers={"host": "127.0.0.1:8000"})
        assert resp.status_code == 200

    def test_ui_accepts_ipv6_loopback(self, host_app) -> None:
        client = TestClient(host_app)
        resp = client.get("/ui/cases", headers={"host": "[::1]:8000"})
        assert resp.status_code == 200

    def test_ui_rejects_wrong_port(self, host_app) -> None:
        client = TestClient(host_app)
        resp = client.get("/ui/cases", headers={"host": "localhost:9999"})
        assert resp.status_code == 400

    def test_api_not_affected_by_host_validation(self, host_app) -> None:
        """API routes should not be subject to host validation."""
        client = TestClient(host_app)
        resp = client.get("/api/v1/cases", headers={"host": "evil.com:8000"})
        assert resp.status_code == 200

    def test_ui_empty_host_rejected(self, host_app) -> None:
        client = TestClient(host_app)
        resp = client.get("/ui/cases", headers={"host": ""})
        assert resp.status_code == 400

    def test_ui_does_not_trust_forwarded_host(self, host_app) -> None:
        """X-Forwarded-Host should be ignored."""
        client = TestClient(host_app)
        resp = client.get(
            "/ui/cases",
            headers={
                "host": "evil.com:8000",
                "x-forwarded-host": "localhost:8000",
            },
        )
        assert resp.status_code == 400


class TestSecurityHeaders:
    """Tests for SecurityHeadersMiddleware."""

    def test_security_headers_present_on_success(self, security_app) -> None:
        client = TestClient(security_app)
        resp = client.get("/ui/cases")
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert resp.headers["x-frame-options"] == "DENY"
        assert resp.headers["referrer-policy"] == "no-referrer"
        assert "default-src 'none'" in resp.headers["content-security-policy"]

    def test_csp_contains_no_unsafe_inline(self, security_app) -> None:
        client = TestClient(security_app)
        resp = client.get("/ui/cases")
        csp = resp.headers["content-security-policy"]
        assert "unsafe-inline" not in csp

    def test_csp_contains_no_unsafe_eval(self, security_app) -> None:
        client = TestClient(security_app)
        resp = client.get("/ui/cases")
        csp = resp.headers["content-security-policy"]
        assert "unsafe-eval" not in csp

    def test_csp_has_no_wildcard_font_src(self, security_app) -> None:
        client = TestClient(security_app)
        resp = client.get("/ui/cases")
        csp = resp.headers["content-security-policy"]
        # font-src must be 'self', not '*'
        assert "font-src 'self'" in csp

    def test_cross_origin_headers_present(self, security_app) -> None:
        client = TestClient(security_app)
        resp = client.get("/ui/cases")
        assert resp.headers["cross-origin-opener-policy"] == "same-origin"
        assert resp.headers["cross-origin-resource-policy"] == "same-origin"

    def test_permissions_policy_present(self, security_app) -> None:
        client = TestClient(security_app)
        resp = client.get("/ui/cases")
        pp = resp.headers["permissions-policy"]
        assert "camera=()" in pp
        assert "microphone=()" in pp
        assert "geolocation=()" in pp

    def test_cache_control_no_store_on_ui(self, security_app) -> None:
        client = TestClient(security_app)
        resp = client.get("/ui/cases")
        assert "no-store" in resp.headers.get("cache-control", "")
