"""CSRF protection service for M6-UI.

Implements token-based CSRF protection for future POST routes.
Uses HMAC-signed tokens with browser nonce cookies.

This module provides the TOKEN SERVICE only.
It is NOT wired into any middleware or route in Slice 1
(no POST routes exist yet).
"""

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass


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
