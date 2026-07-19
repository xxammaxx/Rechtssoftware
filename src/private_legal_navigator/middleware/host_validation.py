"""Host-Header validation middleware for M6-UI.

Rejects requests with unknown Host headers before any processing.
Only applies to /ui/* paths — the JSON API (/api/v1/*) is not subject
to host validation in this layer.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class HostValidationMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose Host header is not in the explicit allowlist.

    Only validates requests to /ui/* paths.
    Uses exact matching including port. No wildcards, no suffix matching,
    no subdomain matching, no trust in X-Forwarded-* headers.
    """

    def __init__(self, app: ASGIApp, *, allowed_hosts: list[str]) -> None:
        super().__init__(app)
        self._allowed = frozenset(allowed_hosts)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only validate hosts for UI routes
        if request.url.path.startswith("/ui/"):
            host = request.headers.get("host", "")

            if host not in self._allowed:
                body = (
                    '<!DOCTYPE html><html lang="de"><head>'
                    "<title>Ungültige Anfrage</title></head><body>"
                    "<h1>Ungültige Anfrage</h1>"
                    "<p>Die angeforderte Adresse ist nicht erreichbar.</p>"
                    "</body></html>"
                )
                return Response(
                    content=body,
                    status_code=400,
                    media_type="text/html; charset=utf-8",
                )

        return await call_next(request)
