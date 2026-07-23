"""CSRF protection service for M6-UI and M7-A.

Implements token-based CSRF protection for POST routes.
Uses HMAC-signed tokens with browser nonce cookies.

Provides two API surfaces:
- Simplified: create_token(scope) / validate(token, scope)
  (used by M7-A UI routes — self-contained HMAC tokens)
- Browser-bound: generate_browser_nonce / generate_form_token / validate_token
  (used by M6-UI routes — cookie-bound tokens)
"""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass

from fastapi import HTTPException


@dataclass(frozen=True)
class CsrfConfig:
    """Configuration for CSRF token generation and validation."""

    secret: str
    token_lifetime_seconds: int = 3600  # 1 hour


class CsrfTokenService:
    """Generates and validates CSRF tokens.

    Token format: base64(nonce + ":" + hmac_signature)
    Bound to a browser nonce stored in a cookie.

    Token rotation: new token generated on first access per nonce.
    Validation uses constant-time comparison.
    """

    def __init__(self, config: CsrfConfig) -> None:
        self._config = config
        self._key = config.secret.encode("utf-8")

    # ── Simplified API (M7-A) ────────────────────

    def create_token(self, scope: str) -> str:
        """Create a self-contained CSRF token bound to a scope string.

        Token format: timestamp:scope:hmac_signature
        Self-validating — no server-side state or browser cookie needed.
        """
        now = int(time.time())
        payload = f"{now}:{scope}"
        signature = self._sign(payload)
        return f"{now}:{scope}:{signature}"

    def validate(self, token: str, scope: str) -> None:
        """Validate a CSRF token against a scope string.

        Raises HTTPException(403) on any validation failure.
        """
        try:
            last_colon = token.rfind(":")
            if last_colon == -1:
                raise HTTPException(status_code=403, detail="Ungültiges CSRF-Token")
            payload_part = token[:last_colon]
            signature = token[last_colon + 1 :]

            parts = payload_part.split(":", 1)
            if len(parts) != 2:
                raise HTTPException(status_code=403, detail="Ungültiges CSRF-Token")

            timestamp_str, token_scope = parts
            timestamp = int(timestamp_str)

            if time.time() - timestamp > self._config.token_lifetime_seconds:
                raise HTTPException(status_code=403, detail="CSRF-Token abgelaufen")

            if not hmac.compare_digest(token_scope, scope):
                raise HTTPException(status_code=403, detail="Ungültiges CSRF-Token")

            expected_sig = self._sign(payload_part)
            if not hmac.compare_digest(signature, expected_sig):
                raise HTTPException(status_code=403, detail="Ungültiges CSRF-Token")
        except HTTPException:
            raise
        except (ValueError, IndexError):
            raise HTTPException(status_code=403, detail="Ungültiges CSRF-Token") from None

    # ── Browser-bound API (M6-UI) ─────────────────

    def generate_browser_nonce(self) -> str:
        """Generate a cryptographically random browser nonce.

        Returns a hex string suitable for use as a cookie value.
        """
        return secrets.token_hex(32)

    def generate_form_token(self, browser_nonce: str, action_path: str = "/ui/") -> str:
        """Generate a time-bound, signed form token for a browser nonce.

        Token is bound to: browser_nonce + action_path + HTTP method (POST).
        Format: timestamp:nonce:POST:path:signature (path may contain colons)
        """
        now = int(time.time())
        payload = f"{now}:{browser_nonce}:POST:{action_path}"
        signature = self._sign(payload)
        token_raw = f"{now}:{browser_nonce}:POST:{action_path}:{signature}"
        return token_raw

    def validate_token(self, form_token: str, browser_nonce: str, action_path: str = "") -> bool:
        """Validate a form token against a browser nonce and action path.

        Uses constant-time comparison for the HMAC.
        Token format: timestamp:nonce:POST:path:signature
        Since paths may contain colons, we split from the right.
        """
        try:
            # Split from right: last part is signature
            last_colon = form_token.rfind(":")
            if last_colon == -1:
                return False
            payload_part = form_token[:last_colon]
            signature = form_token[last_colon + 1 :]

            # Parse payload: timestamp:nonce:POST:path
            parts = payload_part.split(":", 3)
            if len(parts) != 4:
                return False

            timestamp_str, token_nonce, method, token_path = parts
            timestamp = int(timestamp_str)

            # Check expiry
            if time.time() - timestamp > self._config.token_lifetime_seconds:
                return False

            # Check nonce binding
            if not hmac.compare_digest(token_nonce, browser_nonce):
                return False

            # Check method
            if method != "POST":
                return False

            # Check path binding if caller provided one
            if action_path and not hmac.compare_digest(token_path, action_path):
                return False

            # Verify signature
            expected_sig = self._sign(payload_part)
            return hmac.compare_digest(signature, expected_sig)

        except Exception:
            return False

    def _sign(self, payload: str) -> str:
        """Create an HMAC-SHA256 signature for a payload."""
        return hmac.new(
            self._key,
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def generate_idempotency_key() -> str:
        """Generate a unique idempotency key for form submissions.

        Used to prevent duplicate processing of state-changing operations.
        """
        return secrets.token_hex(16)
