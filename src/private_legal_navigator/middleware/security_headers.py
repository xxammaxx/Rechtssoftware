"""Security headers middleware for M6-UI.

Adds mandatory security headers to all HTML responses.
CSP is delivered as HTTP header only — no meta tags.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all responses.

    Headers are applied unconditionally — even on error responses.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Content-Security-Policy: strict deny-by-default
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "base-uri 'none'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "img-src 'self'; "
            "style-src 'self'; "
            "script-src 'self'; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'"
        )

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Cache-Control: no-store for all UI routes
        if request.url.path.startswith("/ui/"):
            response.headers["Cache-Control"] = "no-store, max-age=0"

        return response
